"""Smoke-test release 1.2.1 features using only the frozen application server."""
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
from labelstudio.models import Document,Label,Element,CutSettings

case=root/'.installer-qa'/('package-update-'+uuid.uuid4().hex[:8]);case.mkdir(parents=True)
data=case/'data';source=case/'live.xlsx'
book=Workbook();book.active.title='First';book.active.append(['Name','_sheet','_sheet_value']);book.active.append(['OLD','keep','also-keep'])
tab=book.create_sheet('Second');tab.append(['Name']);tab.append(['SECOND']);book.save(source)
store=Store(data);item=store.save_resource(store.user('local'),'source','live.xlsx',{'linked_path':str(source),'live':True},'private')
with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
app=root/'dist'/'CableLabelStudio'/'CableLabelStudio.exe'
process=subprocess.Popen([str(app),'--data-dir',str(data),'--no-browser','--port',str(port)],creationflags=subprocess.CREATE_NO_WINDOW)
headers={'X-Studio-Request':'1'};checks=[]
def api(path,body=None,method=None):
    request=urllib.request.Request(f'http://127.0.0.1:{port}'+path,data=json.dumps(body).encode() if body is not None else None,headers=headers|({'Content-Type':'application/json'} if body is not None else {}),method=method)
    with urllib.request.urlopen(request,timeout=30) as response:return json.load(response)
try:
    end=time.time()+45
    while time.time()<end:
        try:boot=api('/api/bootstrap');break
        except Exception:time.sleep(.2)
    else:raise AssertionError('Frozen app did not start')
    headers['X-CSRF-Token']=boot['csrf']
    assert boot['version']=='1.2.1' and boot['creator']=='Amir Rahimi' and boot['license']=='MIT'
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
    # Regression must exercise HTTPS from the frozen executable, not only from Python.
    api('/api/updates/check',{})
    deadline=time.time()+45
    while time.time()<deadline:
        status=api('/api/updates')
        if status['state'] not in ('idle','checking'):break
        time.sleep(.2)
    assert status['state'] in ('available','up_to_date') and not status.get('error'),status
    assert status.get('release',{}).get('version')
    checks.append('real GitHub HTTPS release check succeeds inside frozen executable')
    none=CutSettings(**{key:'none' for key in CutSettings.model_fields}).model_dump()
    design=Document(name='saved-cuts',pages=[Label(persian_digits=True,elements=[Element(text='{Name}-123',y=22)])])
    fixed=api('/api/design/center',{'document':design.model_dump(),'row':{'Name':'A'},'axis':'width','element_id':'text1'})['document']
    assert fixed['pages'][0]['elements'][0]['y']<22
    assert api('/api/preview',{'document':fixed,'row':{'Name':'A'}})['image'].startswith('data:image/png')
    checks.append('frozen measured centering repairs out-of-page text and renders Persian digits')
    saved=api('/api/resources',{'name':'saved-cuts','kind':'document','scope':'private','payload':fixed})
    changed=api('/api/resources/'+saved['id']+'/cut-settings',{'cut_settings':none},'PATCH')
    assert changed['payload']['pages'][0]['persian_digits']
    assert changed['payload']['cut_settings']==none
    assert api('/api/printing/defaults')['cut_settings']['cut_end_file']=='full'
    checks.append('frozen file cuts save independently of general cuts and retain page digit preference')
    second=Document(name='second',cut_settings=CutSettings(**{key:'full' for key in CutSettings.model_fields})).model_dump()
    job=api('/api/jobs',{'documents':[changed['payload'],second],'records':[{'Name':'A'}],'simulation':True})
    deadline=time.time()+30
    while time.time()<deadline:
        status=api('/api/jobs/'+job['id']+'/status')
        if status['state'] in ('simulated','failed'):break
        time.sleep(.1)
    assert status['state']=='simulated' and status['simulated']==2,status
    for number,expected in [(1,0),(2,0)]:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/jobs/{job["id"]}/artifacts/{number}/prn') as response:raw=response.read()
        assert raw[raw.index(b'\x1biM')+3]==expected
    checks.append('frozen multi-file job uses each file cut policy and exposes lightweight status')
    # The user's reported batch: one page/record, five copies, half between,
    # full only at the very end. Check wire headers and terminators, not counts alone.
    chain=Document(cut_settings=CutSettings(cut_between_pages='half',cut_end_file='full')).model_dump()
    batch=api('/api/jobs',{'documents':[chain],'records':[{}],'copies':5,'simulation':True})
    deadline=time.time()+30
    while time.time()<deadline:
        status=api('/api/jobs/'+batch['id']+'/status')
        if status['state'] in ('simulated','failed'):break
        time.sleep(.1)
    assert status['state']=='simulated' and status['simulated']==5,status
    for number in range(1,6):
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/jobs/{batch["id"]}/artifacts/{number}/prn') as response:raw=response.read()
        assert raw[raw.index(b'\x1biM')+3]==0
        assert raw[raw.index(b'\x1biK')+3]==(8 if number==5 else 4)
        assert raw[-1]==(0x1a if number==5 else 0x0c)
    checks.append('frozen five-copy batch has four half-cut chained pages and only one final full-cut command')
    subprocess.run([str(app),'--data-dir',str(data),'--stop'],creationflags=subprocess.CREATE_NO_WINDOW,timeout=20)
    process.wait(timeout=20)
    process=subprocess.Popen([str(app),'--data-dir',str(data),'--no-browser','--port',str(port)],creationflags=subprocess.CREATE_NO_WINDOW)
    deadline=time.time()+40
    while time.time()<deadline:
        try:
            current=api('/api/resources')
            if any(r['id']==saved['id'] for r in current):break
        except Exception:time.sleep(.2)
    else:raise AssertionError('Frozen application did not restart')
    restored=next(r for r in current if r['id']==saved['id'])
    assert restored['payload']['cut_settings']==none and restored['payload']['pages'][0]['persian_digits']
    checks.append('file-specific cuts and Persian digits survive a real process restart')
finally:
    subprocess.run([str(app),'--data-dir',str(data),'--stop'],creationflags=subprocess.CREATE_NO_WINDOW,timeout=20)
    process.wait(timeout=20)
report={'passed':True,'checks':checks}
(root/'verification'/'package-update.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
