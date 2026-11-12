"""Build an offline Windows application, portable ZIP and WinForms setup wizard."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parent


def main():
    os.chdir(ROOT)
    out=ROOT/'release';out.mkdir(exist_ok=True)
    art=ROOT/'build-assets';art.mkdir(exist_ok=True)
    icon=Image.new('RGBA',(256,256),'#102d35');draw=ImageDraw.Draw(icon)
    draw.rounded_rectangle((24,62,216,194),radius=15,fill='#e8b86a')
    draw.ellipse((175,111,199,135),fill='#102d35')
    for x in (55,72,85,107,121,134):draw.rectangle((x,90,x+6,166),fill='#102d35')
    icon.save(art/'app.ico',sizes=[(16,16),(32,32),(48,48),(128,128),(256,256)])
    args=[sys.executable,'-m','PyInstaller','--noconfirm','--onedir','--windowed',
          '--name','CableLabelStudio','--icon',str(art/'app.ico'),
          '--add-data',str(ROOT/'web')+';web','--collect-all','arabic_reshaper','--collect-all','bidi',
          '--hidden-import','uvicorn.logging','--hidden-import','uvicorn.loops.auto',
          '--hidden-import','uvicorn.protocols.http.h11_impl','--hidden-import','uvicorn.protocols.websockets.auto',
          '--hidden-import','uvicorn.lifespan.on','--hidden-import','pyodbc','--hidden-import','win32timezone',
          '--hidden-import','win32ui','--hidden-import','PIL.ImageWin','--hidden-import','win32com.shell.shell','--hidden-import','pythoncom','--hidden-import','PIL._imagingft','--hidden-import','qrcode','run.py']
    if '--package-only' not in sys.argv:
        subprocess.run(args,check=True)
    app=ROOT/'dist'/'CableLabelStudio'
    compiler=Path(os.environ['WINDIR'])/'Microsoft.NET'/'Framework64'/'v4.0.30319'/'csc.exe'
    subprocess.run([str(compiler),'/nologo','/target:winexe','/platform:x64','/optimize+',
                    '/reference:System.Web.Extensions.dll','/out:'+str(app/'CableLabelStudio-Update.exe'),
                    str(ROOT/'installer'/'UpdateWorker.cs')],check=True)
    for name in ['README.md' ,'README.fa.md','README.en.md','README.ar.md','ACCEPTANCE.md','LICENSE.txt','THIRD-PARTY-NOTICES.md']:
        shutil.copy2(ROOT/name,app/name)
    shutil.copytree(ROOT/'examples',app/'examples',dirs_exist_ok=True)
    licenses=app/'third-party-licenses';licenses.mkdir(exist_ok=True)
    for dist in importlib.metadata.distributions():
        for file in dist.files or []:
            if any(token in Path(str(file)).name.lower() for token in ('license','copying','notice')) and '.dist-info' in str(file):
                source=Path(dist.locate_file(file))
                if source.is_file():
                    dest=licenses/dist.metadata['Name']/Path(str(file)).name
                    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
    python_license=Path(sys.base_prefix)/'LICENSE.txt'
    if python_license.exists():shutil.copy2(python_license,licenses/'Python-LICENSE.txt')
    manifest={'product':'CableLabelStudio','version':'1.1.0','files':{}}
    for file in sorted(app.rglob('*')):
        if file.is_file() and file.name!='package-manifest.json':
            manifest['files'][file.relative_to(app).as_posix()]=hashlib.sha256(file.read_bytes()).hexdigest()
    (app/'package-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    payload=art/'payload.zip'
    with zipfile.ZipFile(payload,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for file in app.rglob('*'):
            if file.is_file():archive.write(file,file.relative_to(app).as_posix())
    shutil.copy2(payload,out/'CableLabelStudio-1.1.0-Portable.zip')
    compiler=Path(os.environ['WINDIR'])/'Microsoft.NET'/'Framework64'/'v4.0.30319'/'csc.exe'
    setup=out/'CableLabelStudio-1.1.0-Setup.exe'
    subprocess.run([str(compiler),'/nologo','/target:winexe','/platform:x64','/optimize+',
                    '/win32icon:'+str(art/'app.ico'),'/out:'+str(setup),
                    '/reference:System.Windows.Forms.dll','/reference:System.Drawing.dll',
                    '/reference:System.IO.Compression.dll','/reference:System.IO.Compression.FileSystem.dll',
                    '/reference:System.Web.Extensions.dll','/reference:Microsoft.CSharp.dll','/reference:System.Management.dll',
                    '/resource:'+str(payload)+',payload.zip',str(ROOT/'installer'/'Setup.cs')],check=True)
    checksums=[]
    for file in (setup,out/'CableLabelStudio-1.1.0-Portable.zip'):
        checksums.append(hashlib.sha256(file.read_bytes()).hexdigest()+'  '+file.name)
    (out/'SHA256SUMS.txt').write_text('\n'.join(checksums)+'\n',encoding='utf-8')
    print(json.dumps({'setup':str(setup),'portable':str(out/'CableLabelStudio-1.1.0-Portable.zip'),'files':len(manifest['files'])}))


if __name__=='__main__':main()
