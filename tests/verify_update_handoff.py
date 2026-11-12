"""Exercise the native update helper against a real isolated 1.0.0 installation.

Does not print or register an installation/shortcuts. Leaves its test data for audit.
"""
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import uuid
import winreg

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
case=root/'.installer-qa'/('update-handoff-'+uuid.uuid4().hex[:8]);case.mkdir(parents=True)
target=case/'program';data=case/'data';data.mkdir()
old=root/'release'/'CableLabelStudio-1.0.0-Setup.exe'
new=root/'release'/'CableLabelStudio-1.1.0-Setup.exe'
report={'passed':False,'checks':[]}
key_name=r'Software\Microsoft\Windows\CurrentVersion\Uninstall\CableLabelStudio'
def registry_snapshot():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,key_name) as key:return winreg.QueryValueEx(key,'InstallLocation')[0]
    except FileNotFoundError:return None
before=registry_snapshot()
def run_setup(exe,mode):
    value=subprocess.run([str(exe),'/silent','/mode',mode,'/dir',str(target),'/no-registry','/no-shortcuts','/data-dir',str(data),'/log',str(case/(mode+'.log'))],creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
    assert value.returncode==0,(mode,value.returncode)
def api(path,port):
    with urllib.request.urlopen(f'http://127.0.0.1:{port}/api'+path,timeout=2) as response:return json.load(response)
try:
    run_setup(old,'install')
    # Bootstrap an old real database, then configure a free port through its persisted settings.
    from labelstudio.store import Store
    store=Store(data)
    with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    settings=store.settings().model_copy(update={'port':port});store.save_settings(settings)
    store.save_resource(store.user('local'),'dataset','survive-update',{'records':[{'Cable':'A-01'}]},'private')
    app=target/'CableLabelStudio.exe'
    process=subprocess.Popen([str(app),'--no-browser','--data-dir',str(data)],creationflags=subprocess.CREATE_NO_WINDOW)
    deadline=time.time()+40
    while time.time()<deadline:
        try:
            if api('/health',port)['version']=='1.0.0':break
        except Exception:time.sleep(.2)
    else:raise AssertionError('Old application did not start')
    report['checks'].append('real 1.0.0 app started with an isolated persistent dataset')
    updates=data/'updates';updates.mkdir(exist_ok=True)
    state=updates/'state.json';state.write_text(json.dumps({'state':'installing','target':'1.1.0','events':[]}),encoding='utf-8')
    helper=updates/'CableLabelStudio-Update.exe';shutil.copy2(root/'dist'/'CableLabelStudio'/'CableLabelStudio-Update.exe',helper)
    worker=subprocess.Popen([str(helper),str(new),str(target),str(data),str(state),str(updates/'install.log')],creationflags=subprocess.CREATE_NO_WINDOW)
    assert worker.wait(timeout=180)==0,(updates/'install.log').read_text(encoding='utf-8-sig')
    deadline=time.time()+45
    while time.time()<deadline:
        try:
            if api('/health',port)['version']=='1.1.0':break
        except Exception:time.sleep(.2)
    else:raise AssertionError('Updated app did not restart on the persisted port')
    status=api('/updates',port)
    assert status['state']=='complete' and status['current']=='1.1.0',status
    assert 'Installation complete' in status['install_log']
    resources=api('/resources',port)
    assert any(r['name']=='survive-update' and r['payload']['records'][0]['Cable']=='A-01' for r in resources)
    assert registry_snapshot()==before
    report['checks'].extend(['native helper stops old service, installs and restarts new service','same-page update state/log report completion from restarted app','dataset and configured port survive; portable update does not change registration'])
    report['passed']=True
finally:
    if (target/'CableLabelStudio.exe').exists():
        subprocess.run([str(target/'CableLabelStudio.exe'),'--stop','--data-dir',str(data)],creationflags=subprocess.CREATE_NO_WINDOW,timeout=20)
        time.sleep(2)
        run_setup(new,'uninstall')
    (root/'verification'/'update-handoff.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
