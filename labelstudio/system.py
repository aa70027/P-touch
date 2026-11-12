import hashlib
import os
from pathlib import Path
import subprocess
import sys


def command(data_dir,background=True):
    args=[sys.executable]
    if not getattr(sys,'frozen',False):
        args += [str(Path(__file__).resolve().parent.parent/'run.py')]
    args += ['--data-dir',str(data_dir)]
    if background:
        args += ['--no-browser']
    return args


def set_auto_start(enabled,data_dir):
    import winreg
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
        if enabled:
            winreg.SetValueEx(key,'CableLabelStudio',0,winreg.REG_SZ,subprocess.list2cmdline(command(data_dir)))
        else:
            try:
                winreg.DeleteValue(key,'CableLabelStudio')
            except FileNotFoundError:
                pass


def instance_name(data_dir):
    # Per Windows user and data directory.
    suffix=hashlib.sha256((os.environ.get('USERNAME','user')+'|'+str(Path(data_dir).resolve()).casefold()).encode()).hexdigest()[:24]
    return 'Local\\CableLabelStudio_'+suffix
