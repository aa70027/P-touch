"""Local Windows file dialog in a child process; no uploaded copy is made."""
import ctypes
from ctypes import wintypes
import json
import subprocess
import sys
import threading
from pathlib import Path

_picker_lock=threading.Lock()

def file_dialog():
    import pythoncom
    pythoncom.CoInitialize()
    try:
        from win32com.shell import shell, shellcon
        result=shell.SHBrowseForFolder  # Ensure the bundled shell extension is loaded.
        import win32ui
        dialog=win32ui.CreateFileDialog(1,None,None,0x1000|0x800|0x4,
            'Excel / Data (*.xlsx;*.xlsm;*.xls;*.csv;*.tsv)|*.xlsx;*.xlsm;*.xls;*.csv;*.tsv||')
        if dialog.DoModal()!=1:
            return None
        return dialog.GetPathName()
    finally:
        pythoncom.CoUninitialize()

def pick_file():
    if not _picker_lock.acquire(blocking=False):
        raise ValueError('FILE_PICKER_ALREADY_OPEN')
    try:
        args=[sys.executable]
        if not getattr(sys,'frozen',False):
            args.append(str(Path(__file__).resolve().parent.parent/'run.py'))
        import tempfile
        with tempfile.TemporaryDirectory(prefix='CableLabelStudio-picker-') as directory:
            output=Path(directory)/'selection.json'
            proc=subprocess.run(args+['--pick-file',str(output)],timeout=300,
                                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if proc.returncode or not output.exists():
                raise ValueError('WINDOWS_FILE_PICKER_FAILED')
            return json.loads(output.read_text(encoding='utf-8'))
    except subprocess.TimeoutExpired:
        raise ValueError('FILE_PICKER_TIMEOUT')
    finally:
        _picker_lock.release()

def windows_settings():
    import os
    os.startfile('ms-settings:network-wifi')

def driver_preferences(printer):
    # Arguments are passed directly, never evaluated by a shell.
    subprocess.Popen(['rundll32.exe','printui.dll,PrintUIEntry','/e','/n',printer])


def brother_tools():
    import os
    names={'editor':['ptedit50.exe','ptedit51.exe','ptedit52.exe','ptedit53.exe','ptedit54.exe','ptedit60.exe'],
           'transfer':['PtTrMgr.exe'],'network':['BRAdmin.exe','BRAdminPro4.exe','BRAdmin4.exe']}
    result={key:None for key in names}
    for variable in ('ProgramFiles','ProgramFiles(x86)'):
        parent=Path(os.environ.get(variable,''))/'Brother'
        if not parent.is_dir():continue
        for key,executables in names.items():
            if result[key]:continue
            for executable in executables:
                candidates=list(parent.glob('*/'+executable))+list(parent.glob('*/*/'+executable))
                if candidates:result[key]=candidates[0];break
    return result


def open_brother_tool(tool,file=None):
    if tool not in ('editor','transfer','network'):raise ValueError('UNKNOWN_BROTHER_TOOL')
    target=brother_tools()[tool]
    if not target:raise ValueError('BROTHER_TOOL_NOT_INSTALLED')
    arguments=[str(target)]+([str(file)] if file is not None else [])
    # Only discovered installed Brother executables and app-owned LBX files.
    subprocess.Popen(arguments)
