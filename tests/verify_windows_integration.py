"""Test per-user installer registration/shortcuts without touching an existing install."""
import json
import os
from pathlib import Path
import subprocess
import time
import uuid
import winreg
from win32com.shell import shell,shellcon

root=Path(__file__).resolve().parents[1]
setup=root/'release'/'CableLabelStudio-1.1.0-Setup.exe'
key_name=r'Software\Microsoft\Windows\CurrentVersion\Uninstall\CableLabelStudio'
desktop=Path(shell.SHGetFolderPath(0,shellcon.CSIDL_DESKTOPDIRECTORY,0,0))/'Cable Label Studio.lnk'
start=Path(shell.SHGetFolderPath(0,shellcon.CSIDL_PROGRAMS,0,0))/'Cable Label Studio'
target=root/'.installer-qa'/('integration-'+uuid.uuid4().hex[:8])/'program'
report={'passed':False,'checks':[]}
reportfile=root/'verification'/'windows-integration.json'
try:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,key_name):
            raise RuntimeError('Existing installation found; integration test refuses to replace it.')
    except FileNotFoundError:
        pass
    if desktop.exists() or start.exists():
        raise RuntimeError('Existing shortcuts found; integration test refuses to replace them.')
    def run(exe,mode):
        result=subprocess.run([str(exe),'/silent','/mode',mode,'/dir',str(target),'/log',str(root/'verification'/('windows-'+mode+'.log'))],
                              creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
        assert result.returncode==0,(mode,result.returncode)
    run(setup,'install')
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,key_name) as key:
        assert winreg.QueryValueEx(key,'InstallLocation')[0]==str(target)
        assert '/mode uninstall' in winreg.QueryValueEx(key,'UninstallString')[0]
    assert desktop.exists() and (start/'Cable Label Studio.lnk').exists() and (start/'Maintenance.lnk').exists()
    report['checks'].append('per-user registration and real desktop/Start menu shortcuts')
    print('PASS Windows registration and shortcuts',flush=True)
    run(target/'CableLabelStudio-Setup.exe','repair')
    report['checks'].append('installed maintenance executable repairs its own installation')
    print('PASS installed maintenance repair',flush=True)
    run(setup,'uninstall')
    assert not desktop.exists() and not start.exists()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,key_name):
            raise AssertionError('Uninstall registry key was not removed')
    except FileNotFoundError:
        pass
    assert not (target/'CableLabelStudio.exe').exists()
    report['checks'].append('uninstall removes owned registration and shortcuts')
    report['passed']=True
    print('PASS Windows integration cleanup',flush=True)
finally:
    reportfile.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
