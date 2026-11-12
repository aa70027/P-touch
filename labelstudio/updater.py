"""GitHub release updater and official Brother downloads, with persistent progress.

Checksums verify transfer integrity against the official HTTPS release. They are
not a publisher code signature. The native helper survives application shutdown.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
from urllib.parse import urlparse
from urllib.request import Request,urlopen
from . import __version__

REPO='aa70027/P-touch'
API='https://api.github.com/repos/'+REPO+'/releases'

def version(value):
    match=re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)(?:[-+]([0-9A-Za-z.-]+))?',value)
    if not match:raise ValueError('INVALID_RELEASE_VERSION')
    return tuple(map(int,match.groups()[:3]))+(0 if match[4] else 1,match[4] or '')

def request(url):
    return urlopen(Request(url,headers={'User-Agent':'CableLabelStudio/'+__version__,'Accept':'application/vnd.github+json' if 'api.github.com' in url else '*/*'}),timeout=30)

def release_info(prerelease=False):
    with request(API) as response:
        values=json.load(response)
    eligible=[]
    for item in values:
        if item.get('draft') or item.get('prerelease') and not prerelease:continue
        try:key=version(item['tag_name'])
        except (ValueError,KeyError):continue
        assets={a['name']:a for a in item.get('assets',[])}
        name='CableLabelStudio-'+item['tag_name'].lstrip('v')+'-Setup.exe'
        if name in assets and 'SHA256SUMS.txt' in assets:
            eligible.append((key,item,assets,name))
    if not eligible:return {'current':__version__,'available':False,'release':None}
    _,item,assets,name=max(eligible,key=lambda x:x[0])
    return dict(current=__version__,available=version(item['tag_name'])>version(__version__),release={
        'version':item['tag_name'].lstrip('v'),'url':item['html_url'],'prerelease':item['prerelease'],
        'name':name,'installer':assets[name]['browser_download_url'],'size':assets[name]['size'],
        'checksums':assets['SHA256SUMS.txt']['browser_download_url']})

def official_release_url(url):
    value=urlparse(url)
    if value.scheme!='https' or value.netloc.lower()!='github.com' or not value.path.startswith('/'+REPO+'/releases/download/'):
        raise ValueError('UNTRUSTED_UPDATE_URL')

def brother_url(url):
    value=urlparse(url);host=(value.hostname or '').lower()
    if value.scheme!='https' or not (host=='brother.com' or host.endswith('.brother.com')) or value.username or value.password:
        raise ValueError('OFFICIAL_BROTHER_HTTPS_REQUIRED')

class Updater:
    def __init__(self,root):
        self.root=Path(root)/'updates';self.root.mkdir(exist_ok=True)
        self.path=self.root/'state.json';self.log=self.root/'install.log'
        self.lock=threading.RLock();self.busy=False
        if not self.path.exists():self.write(dict(state='idle',progress=0,events=[],error=None))
        state=self.snapshot()
        if state['state'] in ('checking','downloading','verifying'):
            self.write(dict(state='error',error='UPDATE_INTERRUPTED_RETRY'))
        if state['state']=='installing' and state.get('target')==__version__:
            self.write(dict(state='complete',progress=100,error=None))

    def write(self,values):
        with self.lock:
            try:state=json.loads(self.path.read_text(encoding='utf-8-sig'))
            except (OSError,ValueError):state={}
            state.update(values);state['updated']=time.time()
            temporary=self.path.with_suffix('.tmp');temporary.write_text(json.dumps(state,ensure_ascii=False),encoding='utf-8')
            os.replace(temporary,self.path)

    def event(self,message):
        with self.lock:
            values=self.snapshot();events=values.get('events',[])
            events.append(dict(time=time.time(),message=message))
            self.write({'events':events[-200:]})

    def snapshot(self):
        with self.lock:
            try:state=json.loads(self.path.read_text(encoding='utf-8-sig'))
            except (OSError,ValueError):state=dict(state='idle',events=[])
            state['current']=__version__
            # A helper may have failed after writing 'complete', or an old executable
            # may have relaunched. Never report success for the wrong running version.
            if state.get('state')=='complete' and state.get('target') and state['target']!=__version__:
                state.update(state='error',error='UPDATED_VERSION_NOT_RUNNING')
            try:state['install_log']=self.log.read_text(encoding='utf-8-sig',errors='replace')[-100000:]
            except OSError:state['install_log']=''
            return state

    def task(self,work):
        with self.lock:
            if self.busy or self.snapshot()['state']=='installing':raise ValueError('UPDATE_ALREADY_RUNNING')
            self.busy=True
        def run():
            try:work()
            except Exception as exc:
                self.event(str(exc));self.write(dict(state='error',error=str(exc)))
            finally:
                with self.lock:self.busy=False
        threading.Thread(target=run,daemon=True,name='application-update').start()
        return self.snapshot()

    def check(self,prerelease=False):
        def work():
            self.write(dict(state='checking',progress=0,error=None));self.event('Checking '+REPO)
            info=release_info(prerelease)
            self.write(info|dict(state='available' if info['available'] else 'up_to_date',progress=100))
            self.event('Release check complete')
        return self.task(work)

    def download(self,url,destination,validate,expected_size=None):
        validate(url);digest=hashlib.sha256();total=0
        part=destination.with_suffix(destination.suffix+'.part')
        try:
            with request(url) as response,part.open('wb') as output:
                if validate==brother_url:validate(response.url)
                if 'text/html' in response.headers.get('Content-Type',''):
                    raise ValueError('DIRECT_DOWNLOAD_LINK_REQUIRED')
                size=int(response.headers.get('Content-Length') or expected_size or 0)
                while block:=response.read(256*1024):
                    total+=len(block)
                    if total>1024**3:raise ValueError('DOWNLOAD_EXCEEDS_1_GB')
                    output.write(block);digest.update(block)
                    self.write(dict(progress=min(99,int(total/max(1,size)*100)) if size else 0,bytes=total,total_bytes=size))
            if expected_size is not None and total!=expected_size:raise ValueError('INCOMPLETE_DOWNLOAD')
            os.replace(part,destination)
            return digest.hexdigest()
        finally:part.unlink(missing_ok=True)

    def install(self,prerelease,backup,active_jobs):
        if not getattr(sys,'frozen',False):raise ValueError('UPDATE_REQUIRES_INSTALLED_WINDOWS_APP')
        target=Path(sys.executable).parent
        if not (target/'package-manifest.json').exists():raise ValueError('PACKAGE_MANIFEST_REQUIRED')
        helper=target/'CableLabelStudio-Update.exe'
        if not helper.exists():raise ValueError('UPDATE_HELPER_MISSING')
        def work():
            self.write(dict(state='checking',error=None,progress=0));self.event('Rechecking official release')
            info=release_info(prerelease)
            if not info['available']:
                self.write(info|dict(state='up_to_date'));return
            release=info['release'];official_release_url(release['checksums'])
            with request(release['checksums']) as response:
                checksums=response.read(1024*1024).decode('utf-8-sig')
            expected=None
            for line in checksums.splitlines():
                parts=line.split(maxsplit=1)
                if len(parts)==2 and parts[1].lstrip('*')==release['name']:expected=parts[0].lower()
            if not expected or not re.fullmatch('[0-9a-f]{64}',expected):raise ValueError('RELEASE_CHECKSUM_MISSING')
            self.write(info|dict(state='downloading',target=release['version'],progress=0));self.event('Downloading '+release['name'])
            installer=self.root/release['name']
            actual=self.download(release['installer'],installer,official_release_url,release['size'])
            self.write(dict(state='verifying'))
            if actual!=expected:
                installer.unlink(missing_ok=True);raise ValueError('UPDATE_CHECKSUM_MISMATCH')
            if active_jobs():raise ValueError('ACTIVE_PRINT_JOBS')
            backup();self.event('Download verified; database backup created')
            self.log.unlink(missing_ok=True)
            self.write(dict(state='installing',progress=100,error=None))
            runner=self.root/'CableLabelStudio-Update.exe'
            shutil.copy2(helper,runner)
            subprocess.Popen([str(runner),str(installer),str(target),str(self.root.parent),str(self.path),str(self.log)],
                             creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        return self.task(work)

    def software(self,url):
        brother_url(url)
        def work():
            self.write(dict(state='downloading',error=None,progress=0,software_file=None));self.event('Downloading official Brother software')
            name=Path(urlparse(url).path).name
            if not re.fullmatch(r'[A-Za-z0-9_.-]+\.(exe|msi|zip)',name,re.I):raise ValueError('DIRECT_DOWNLOAD_LINK_REQUIRED')
            path=self.root/name;digest=self.download(url,path,brother_url)
            self.write(dict(state='software_ready',progress=100,software_file=name,sha256=digest))
            self.event('Brother software downloaded: '+name)
        return self.task(work)
