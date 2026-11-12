import argparse
import logging
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import webbrowser
from labelstudio.store import default_data_dir
from labelstudio.system import instance_name,command


def main():
    parser=argparse.ArgumentParser(description='Cable Label Studio · Windows local web label printer')
    parser.add_argument('--data-dir',type=Path,default=default_data_dir())
    parser.add_argument('--port',type=int)
    parser.add_argument('--no-browser',action='store_true')
    parser.add_argument('--stop',action='store_true')
    parser.add_argument('--wait',type=int,default=0)
    args=parser.parse_args()
    # PyInstaller windowed mode has no stdout/stderr; keep all logging UTF-8 on disk.
    args.data_dir.mkdir(parents=True,exist_ok=True)
    if sys.stdout is None:
        sys.stdout=open(args.data_dir/'stdout.log','a',encoding='utf-8')
    if sys.stderr is None:
        sys.stderr=open(args.data_dir/'stderr.log','a',encoding='utf-8')
    if args.wait:
        time.sleep(min(args.wait,10))
    import win32event,win32api,winerror
    name=instance_name(args.data_dir)
    if args.stop:
        try:
            event=win32event.OpenEvent(2,False,name+'_stop')
            win32event.SetEvent(event)
            win32api.CloseHandle(event)
        except Exception:
            pass
        return
    mutex=win32event.CreateMutex(None,False,name)
    exists=win32api.GetLastError()==winerror.ERROR_ALREADY_EXISTS
    if exists:
        if not args.no_browser:
            import sqlite3,json
            with sqlite3.connect(args.data_dir/'studio.sqlite3') as db:
                port=json.loads(db.execute('SELECT data FROM settings WHERE id=1').fetchone()[0])['port']
            webbrowser.open(f'http://127.0.0.1:{args.port or port}')
        return
    stop=win32event.CreateEvent(None,True,False,name+'_stop')
    from labelstudio.app import create_app
    import uvicorn
    app=create_app(args.data_dir)
    settings=app.state.store.settings()
    port=args.port or settings.port
    if not 1024<=port<=65535:
        raise ValueError('INVALID_PORT')
    config=uvicorn.Config(app,host='127.0.0.1',port=port,log_level='warning',access_log=False)
    server=uvicorn.Server(config)
    def halt():
        server.should_exit=True
    def restart():
        subprocess.Popen(command(args.data_dir)+['--wait','3'],creationflags=subprocess.CREATE_NO_WINDOW)
        threading.Timer(0.5,halt).start()
    app.state.restart=restart
    app.state.shutdown=lambda:threading.Timer(0.5,halt).start()
    def watch_stop():
        win32event.WaitForSingleObject(stop,win32event.INFINITE)
        halt()
    threading.Thread(target=watch_stop,daemon=True).start()
    if not args.no_browser:
        def open_ready():
            for _ in range(100):
                if server.started:
                    webbrowser.open(f'http://127.0.0.1:{port}')
                    return
                time.sleep(0.1)
        threading.Thread(target=open_ready,daemon=True).start()
    app.state.store.audit('local','application.start',f'v1.0.0 port={port}')
    try:
        server.run()
    finally:
        app.state.store.logger.info('Application stopped')
        win32api.CloseHandle(stop)
        win32api.CloseHandle(mutex)


if __name__=='__main__':
    try:
        main()
    except BaseException as error:
        logging.exception('Cable Label Studio failed')
        if getattr(sys,'frozen',False):
            import ctypes
            ctypes.windll.user32.MessageBoxW(None,str(error),'Cable Label Studio',0x10)
        raise
