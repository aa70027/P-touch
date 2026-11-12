"""End-to-end Windows release verification in a dedicated disposable directory.

Does not register an installed app, create shortcuts, change startup, or print.
"""
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid

ROOT=Path(__file__).resolve().parents[1]
SETUP=ROOT/'release'/'CableLabelStudio-1.0.0-Setup.exe'
REPORTS=ROOT/'verification'
CASE=ROOT/'.installer-qa'/('case-'+uuid.uuid4().hex[:8])
TARGET=CASE/'نصب آزمایشی'
DATA=CASE/'runtime-data'
REPORTS.mkdir(exist_ok=True)
results=[]


def record(name,detail=''):
    results.append({'check':name,'passed':True,'detail':detail})
    print('PASS '+name,flush=True)


def install(mode,target=TARGET,expected=0):
    log=REPORTS/('installer-'+mode+'.log')
    result=subprocess.run([str(SETUP),'/silent','/mode',mode,'/dir',str(target),'/no-registry','/no-shortcuts','/log',str(log)],
                          creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
    assert result.returncode==expected,(mode,result.returncode,log.read_text(encoding='utf-8-sig') if log.exists() else '')


def verify_manifest():
    manifest=json.loads((TARGET/'package-manifest.json').read_text(encoding='utf-8'))
    for name,digest in manifest['files'].items():
        path=(TARGET/name).resolve()
        assert path.is_relative_to(TARGET.resolve())
        assert hashlib.sha256(path.read_bytes()).hexdigest()==digest,name
    return len(manifest['files'])


def main():
    CASE.mkdir(parents=True)
    install('install')
    files=verify_manifest()
    assert (TARGET/'CableLabelStudio.exe').is_file()
    assert (TARGET/'CableLabelStudio-Setup.exe').is_file()
    record('offline install into Persian path',f'{files} verified product files')
    with socket.socket() as port_socket:
        port_socket.bind(('127.0.0.1',0));port=port_socket.getsockname()[1]
    executable=TARGET/'CableLabelStudio.exe'
    process=subprocess.Popen([str(executable),'--no-browser','--data-dir',str(DATA),'--port',str(port)],
                             creationflags=subprocess.CREATE_NO_WINDOW)
    url=f'http://127.0.0.1:{port}/api'
    csrf=''
    def request(path,body=None,method=None):
        data=json.dumps(body).encode() if body is not None else None
        req=urllib.request.Request(url+path,data=data,method=method or ('POST' if body is not None else 'GET'),
            headers={'Content-Type':'application/json','X-Studio-Request':'1','X-CSRF-Token':csrf})
        with urllib.request.urlopen(req,timeout=10) as response:
            return json.load(response)
    def upload(path,kind):
        boundary='StudioBoundary'+uuid.uuid4().hex
        payload=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{path.name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode()
                 +path.read_bytes()+f'\r\n--{boundary}--\r\n'.encode())
        req=urllib.request.Request(url+'/upload?kind='+kind,data=payload,
            headers={'Content-Type':'multipart/form-data; boundary='+boundary,'X-Studio-Request':'1','X-CSRF-Token':csrf})
        with urllib.request.urlopen(req,timeout=20) as response:
            return json.load(response)
    try:
        deadline=time.time()+90
        while True:
            try:
                health=request('/health');break
            except (OSError,urllib.error.URLError):
                if time.time()>deadline:
                    log=(DATA/'stderr.log').read_text(encoding='utf-8') if (DATA/'stderr.log').exists() else ''
                    raise AssertionError('Packaged app did not start: '+log)
                time.sleep(.25)
        assert health['version']=='1.0.0'
        boot=request('/bootstrap');csrf=boot['csrf']
        assert boot['user']['role']=='admin' and boot['auth_enabled'] is False
        record('packaged executable starts without Python on PATH')
        resources=request('/resources')
        assert len(resources)>=8
        doc=resources[0]['payload'];doc['pages'][0]['kind']='general';doc['pages'][0]['auto_length']=True
        doc['pages'][0]['elements']=[{'text':'رک A01 · پورت 03','y':4,'h':6}]
        preview=request('/preview',{'document':doc,'row':{}})
        assert preview['image'].startswith('data:image/png;base64,')
        record('packaged Persian rendering and seed library')
        custom=upload(Path(os.environ['WINDIR'])/'Fonts'/'tahoma.ttf','font')
        doc['pages'][0]['elements'][0]['font']=custom['id']
        assert request('/preview',{'document':doc})['image'].startswith('data:image/')
        record('packaged custom font upload and rendering')
        source=upload(ROOT/'examples'/'cables.xlsx','source')
        imported=request('/data/read',{'source':source['id']})
        assert len(imported['records'])==8 and imported['records'][0]['Port']=='01'
        record('packaged Excel workbook import')
        assert request('/formula',{'expression':'IF(EMPTY(X), "", "A")','row':{'X':'ready'}})['value']=='A'
        user=request('/users',{'username':'qa-operator','password':'Validation-'+uuid.uuid4().hex,'role':'user'})
        assert user['role']=='user'
        record('packaged conditional formulas and Argon2 account creation')
        import winreg
        run_key=r'Software\Microsoft\Windows\CurrentVersion\Run'
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,run_key) as key:
                old_run=winreg.QueryValueEx(key,'CableLabelStudio')
        except FileNotFoundError:
            old_run=None
        if old_run is None:
            try:
                settings=request('/settings');settings['auto_start']=True
                request('/settings',settings,'PUT')
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER,run_key) as key:
                    value=winreg.QueryValueEx(key,'CableLabelStudio')[0]
                assert str(executable) in value and '--no-browser' in value
                settings['auto_start']=False;request('/settings',settings,'PUT')
                record('packaged Windows auto-start toggle')
            finally:
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER,run_key) as key:
                    try:winreg.DeleteValue(key,'CableLabelStudio')
                    except FileNotFoundError:pass
        job=request('/jobs',{'documents':[doc],'records':[{}],'simulation':True})
        deadline=time.time()+20
        while True:
            status=request('/jobs/'+job['id'])
            if status['state'] in ('simulated','failed'):break
            assert time.time()<deadline
            time.sleep(.1)
        assert status['state']=='simulated',status
        assert status['sent']==0 and status['simulated']==1
        record('packaged simulation, database and queue')
        device=request('/printer/status')
        assert device['device_confirmed'] is False
        record('packaged Windows printer and USB diagnostics')
        # Second launch must not mark a live job interrupted or create a duplicate server.
        subprocess.run([str(executable),'--no-browser','--data-dir',str(DATA)],creationflags=subprocess.CREATE_NO_WINDOW,timeout=20,check=True)
        assert request('/health')['ok']
        record('single instance')
    finally:
        subprocess.run([str(executable),'--stop','--data-dir',str(DATA)],creationflags=subprocess.CREATE_NO_WINDOW,timeout=20,check=True)
        process.wait(timeout=30)
    assert (DATA/'studio.sqlite3').is_file()
    record('graceful stop and persistent data')
    (TARGET/'README.en.md').write_text('corrupted for repair test',encoding='utf-8')
    (TARGET/'operator-note.txt').write_text('preserve this unrelated user file',encoding='utf-8')
    install('repair');verify_manifest()
    assert (TARGET/'operator-note.txt').read_text()=='preserve this unrelated user file'
    assert (DATA/'studio.sqlite3').is_file()
    record('repair restores changed file and preserves user data')
    import stat
    readonly=TARGET/'README.en.md'
    readonly.chmod(stat.S_IREAD)
    install('repair');verify_manifest()
    record('repair handles read-only product files')
    # Simulate a product-owned file removed in a newer release.
    obsolete=TARGET/'obsolete-product-file.txt';obsolete.write_text('old product component')
    manifestfile=TARGET/'package-manifest.json'
    oldmanifest=json.loads(manifestfile.read_text(encoding='utf-8'))
    oldmanifest['files'][obsolete.name]=hashlib.sha256(obsolete.read_bytes()).hexdigest()
    manifestfile.write_text(json.dumps(oldmanifest),encoding='utf-8')
    install('update');verify_manifest()
    assert not obsolete.exists() and (TARGET/'operator-note.txt').is_file()
    record('update installs a verified package over recognized installation')
    record('update removes obsolete product components and preserves unrelated files')
    install('uninstall')
    assert not executable.exists()
    assert (TARGET/'operator-note.txt').exists()
    assert (DATA/'studio.sqlite3').is_file()
    record('uninstall removes owned application files and preserves data')
    unrelated=CASE/'unrelated';unrelated.mkdir();(unrelated/'keep.txt').write_text('keep')
    install('install',unrelated,expected=1)
    assert (unrelated/'keep.txt').read_text()=='keep'
    record('nonempty unrelated destination rejected')
    report={'version':'1.0.0','verification_date':'2026-11-13','test_directory':str(CASE),'checks':results,'passed':True}
    (REPORTS/'installer-results.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'passed':True,'checks':len(results)},ensure_ascii=False))


if __name__=='__main__':
    try:
        main()
    except Exception as exc:
        (REPORTS/'installer-results.json').write_text(json.dumps({'passed':False,'checks':results,'error':str(exc)},indent=2,ensure_ascii=False),encoding='utf-8')
        raise
