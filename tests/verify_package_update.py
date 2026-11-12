"""Smoke-test release 1.1.0 features using only the frozen application server."""
import io
import json
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request
import uuid
from openpyxl import Workbook,load_workbook
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from labelstudio.store import Store
from labelstudio.models import Document,Label,Element

case=root/'.installer-qa'/('package-update-'+uuid.uuid4().hex[:8]);case.mkdir(parents=True)
data=case/'data';source=case/'live.xlsx'
book=Workbook();book.active.title='First';book.active.append(['Name','_sheet','_sheet_value']);book.active.append(['OLD','keep','also-keep'])
tab=book.create_sheet('Second');tab.append(['Name']);tab.append(['SECOND']);book.save(source)
store=Store(data);item=store.save_resource(store.user('local'),'source','live.xlsx',{'linked_path':str(source),'live':True},'private')
with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
app=root/'dist'/'CableLabelStudio'/'CableLabelStudio.exe'
process=subprocess.Popen([str(app),'--data-dir',str(data),'--no-browser','--port',str(port)],creationflags=subprocess.CREATE_NO_WINDOW)
headers={'X-Studio-Request':'1'};checks=[]
def api(path,body=None):
    request=urllib.request.Request(f'http://127.0.0.1:{port}'+path,data=json.dumps(body).encode() if body is not None else None,headers=headers|({'Content-Type':'application/json'} if body is not None else {}))
    with urllib.request.urlopen(request,timeout=30) as response:return json.load(response)
try:
    end=time.time()+45
    while time.time()<end:
        try:boot=api('/api/bootstrap');break
        except Exception:time.sleep(.2)
    else:raise AssertionError('Frozen app did not start')
    headers['X-CSRF-Token']=boot['csrf']
    assert boot['version']=='1.1.0' and boot['creator']=='Amir Rahimi' and boot['license']=='MIT'
    checks.append('frozen version, creator, project and MIT metadata')
    rows=api('/api/data/read',{'source':item['id'],'sheets':['First','Second']})['records']
    assert len(rows)==2 and rows[0]['_sheet']=='First' and rows[0]['_sheet_value']=='also-keep' and rows[0]['_sheet_value_2']=='keep'
    checks.append('frozen multi-sheet reader preserves user columns and worksheet identity')
    book=load_workbook(source);book['First']['A2']='SAVED';book.save(source);book.close()
    doc=Document(pages=[Label(elements=[Element(text='{Name}')])]).model_dump()
    value=api('/api/preview',{'document':doc,'source':item['id'],'sheets':['First']})
    assert value['row']['Name']=='SAVED'
    checks.append('frozen preview rereads externally saved workbook without upload')
    doc=Document(pages=[Label(model='PT-P900W',width=36,quality='high',elements=[Element(text='سلام')])]).model_dump()
    value=api('/api/preview',{'document':doc})
    assert value['resolution']==[720,360] and value['driver_controls']
    checks.append('frozen additional-model renderer and driver capability metadata')
    assert api('/api/updates')['state']=='idle'
    checks.append('frozen persistent update API and bundled native helper')
    assert (app.parent/'CableLabelStudio-Update.exe').is_file()
finally:
    subprocess.run([str(app),'--data-dir',str(data),'--stop'],creationflags=subprocess.CREATE_NO_WINDOW,timeout=20)
    process.wait(timeout=20)
report={'passed':True,'checks':checks}
(root/'verification'/'package-update.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
