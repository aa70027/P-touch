"""Package the editable project and verification evidence, excluding runtime data."""
import hashlib
from pathlib import Path
import zipfile

root=Path(__file__).resolve().parent
release=root/'release';release.mkdir(exist_ok=True)
target=release/'CableLabelStudio-1.1.0-Source.zip'
files=[]
for directory in ['labelstudio','web','installer','tests','examples']:
    files.extend(f for f in (root/directory).rglob('*') if f.is_file() and '__pycache__' not in f.parts and f.suffix!='.pyc')
files.extend(root/'verification'/name for name in ['designer-fa.png','designer-fa-v110.jpg','release-summary.json','windows-integration.json','update-handoff.json','package-update.json'] if (root/'verification'/name).is_file())
files.extend(f for f in root.iterdir() if f.is_file() and (f.suffix in ('.py','.md','.txt') or f.name=='.gitignore'))
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
    for file in sorted(set(files)):
        archive.write(file,'LabelStudio/'+file.relative_to(root).as_posix())
artifacts=[release/name for name in ['CableLabelStudio-1.1.0-Setup.exe','CableLabelStudio-1.1.0-Portable.zip','CableLabelStudio-1.1.0-Source.zip']]
(release/'SHA256SUMS.txt').write_text(''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.name+'\n' for f in artifacts),encoding='utf-8')
print(target.name)
