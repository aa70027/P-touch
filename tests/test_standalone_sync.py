import csv
import io
import struct
import time
import xml.etree.ElementTree as ET
import zipfile

from fastapi.testclient import TestClient
from openpyxl import Workbook,load_workbook
from PIL import Image,ImageChops
import pytest

from labelstudio.app import create_app
from labelstudio.models import Document,Label,Element
from labelstudio.render import render_label
from labelstudio.standalone import image_lbx,SPACE
from labelstudio.store import PASSWORDS


@pytest.fixture
def context(tmp_path):
    file=tmp_path/'original.xlsx';book=Workbook();sheet=book.active;sheet.title='Records'
    sheet.append(['ID','Status','Text']);sheet.append(['A01','PENDING','First']);sheet.append(['A02','PENDING','Second'])
    book.save(file);book.close();app=create_app(tmp_path/'data');store=app.state.store
    source=store.save_resource(store.user('local'),'source',file.name,{'linked_path':str(file)},'private')
    with TestClient(app) as client:
        boot=client.get('/api/bootstrap').json();client.headers.update({'X-Studio-Request':'1','X-CSRF-Token':boot['csrf']})
        yield client,store,source,file


def export(context):
    client,store,source,file=context
    result=client.post('/api/sources/'+source['id']+'/status/export',json={'sheets':['Records'],'key_column':'ID','status_column':'Status'})
    assert result.status_code==200,result.text
    rows=list(csv.DictReader(io.StringIO(client.get(result.json()['download_url']).content.decode('utf-8-sig'))))
    return result.json(),rows


def preview(context,rows,filename='status.csv'):
    client,store,source,file=context;body=io.StringIO(newline='')
    writer=csv.DictWriter(body,fieldnames=['ExchangeID','Sheet','RecordID','PrintStatus']);writer.writeheader();writer.writerows(rows)
    return client.post('/api/sources/'+source['id']+'/status/import-preview',files={'file':(filename,body.getvalue().encode(),'text/csv')})


def edit_original(file,callback):
    book=load_workbook(file);callback(book.active);book.save(file);book.close()


def test_csv_roundtrip_review_apply_and_idempotent_replay(context):
    client,store,source,file=context;result,rows=export(context);before=file.read_bytes()
    assert result['device_state']=='not_transferred'
    rows[0]['PrintStatus']='OK';response=preview(context,rows);assert response.status_code==200,response.text
    plan=response.json();assert len(plan['updates'])==1 and not plan['conflicts']
    assert plan['automatic_device_readback'] is False and file.read_bytes()==before
    first=client.post('/api/status/imports/'+plan['id']+'/apply',json={});assert first.status_code==200,first.text
    assert first.json()['changed']==1
    repeated=client.post('/api/status/imports/'+plan['id']+'/apply',json={})
    assert repeated.json()['event']==first.json()['event']
    assert len(client.get('/api/sources/'+source['id']+'/status/history').json())==1
    book=load_workbook(file);assert book.active['B2'].value=='OK' and book.active['B3'].value=='PENDING';book.close()
    again=preview(context,rows).json();assert again['updates']==[] and again['conflicts']==[] and again['unchanged']==2


def test_csv_conflict_blocks_entire_batch(context):
    client,store,source,file=context;_,rows=export(context)
    rows[0]['PrintStatus']='OK';rows[1]['PrintStatus']='OK'
    edit_original(file,lambda sheet:setattr(sheet['B3'],'value','LOCAL'))
    before=file.read_bytes();plan=preview(context,rows).json()
    assert len(plan['updates'])==1 and plan['conflicts'][0]['reason']=='both_changed'
    response=client.post('/api/status/imports/'+plan['id']+'/apply',json={})
    assert response.status_code==422 and response.json()['error']=='STATUS_IMPORT_HAS_CONFLICTS'
    assert file.read_bytes()==before


def test_changed_print_data_cannot_be_acknowledged_with_an_old_csv(context):
    _,rows=export(context);rows[0]['PrintStatus']='OK'
    edit_original(context[3],lambda sheet:setattr(sheet['C2'],'value','Different label'))
    plan=preview(context,rows).json();assert plan['updates']==[] and plan['conflicts'][0]['reason']=='row_data_changed'


def test_row_reorder_is_matched_by_id_not_old_row_number(context):
    client,store,source,file=context;_,rows=export(context);rows[0]['PrintStatus']='OK'
    def reorder(sheet):
        first=[cell.value for cell in sheet[2]];second=[cell.value for cell in sheet[3]]
        for col,value in enumerate(second,1):sheet.cell(2,col,value)
        for col,value in enumerate(first,1):sheet.cell(3,col,value)
    edit_original(file,reorder)
    plan=preview(context,rows).json();assert not plan['conflicts']
    response=client.post('/api/status/imports/'+plan['id']+'/apply',json={});assert response.status_code==200,response.text
    book=load_workbook(file);assert book.active['A3'].value=='A01' and book.active['B3'].value=='OK' and book.active['B2'].value=='PENDING';book.close()


def test_changed_workbook_after_csv_preview_rejects_write(context):
    client,store,source,file=context;_,rows=export(context);rows[0]['PrintStatus']='OK';plan=preview(context,rows).json()
    edit_original(file,lambda sheet:setattr(sheet['C3'],'value','new content'));before=file.read_bytes()
    result=client.post('/api/status/imports/'+plan['id']+'/apply',json={})
    assert result.status_code==422 and result.json()['error']=='SOURCE_CHANGED_REFRESH_STATUS'
    assert file.read_bytes()==before


@pytest.mark.parametrize('mutation,error',[
    (lambda rows:rows.append(dict(rows[0])),'STATUS_DUPLICATE_UPDATE'),
    (lambda rows:rows[0].update(ExchangeID='different'),'STATUS_EXCHANGE_ID_MISMATCH'),
    (lambda rows:rows[0].update(PrintStatus='x'*101),'STATUS_VALUE_INVALID'),
])
def test_invalid_imports_reject_without_modifying_excel(context,mutation,error):
    _,rows=export(context);mutation(rows);before=context[3].read_bytes();response=preview(context,rows)
    assert response.status_code==422 and response.json()['error']==error
    assert context[3].read_bytes()==before


def test_unknown_keys_and_proprietary_backups_are_not_silently_accepted(context):
    _,rows=export(context);rows[0].update(RecordID='UNKNOWN',PrintStatus='OK')
    assert preview(context,rows).json()['conflicts'][0]['reason']=='unknown_export_row'
    assert preview(context,rows,'backup.blf').json()['error']=='STATUS_IMPORT_READABLE_CSV_ONLY'


@pytest.mark.parametrize('quality',['standard','high'])
def test_native_lbx_embeds_exact_rendered_ink_and_no_machine_paths(quality):
    page=Label(quality=quality,persian_digits=True,elements=[Element(text='Rack-123',x=2,y=5)])
    image,metadata=render_label(page,{},lambda *args:None);raw=image_lbx(image,metadata,'Native test')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        assert set(archive.namelist())=={'label.xml','prop.xml','Object0.bmp'}
        assert all(item.compress_type==zipfile.ZIP_STORED for item in archive.infolist())
        bitmap=archive.read('Object0.bmp');assert struct.unpack_from('<H',bitmap,28)[0]==32
        document=ET.fromstring(archive.read('label.xml'));properties=archive.read('prop.xml')
        style=document.find('.//pt:objectStyle',SPACE);paper=document.find('.//style:paper',SPACE)
        assert paper.attrib['printerName']=='Brother PT-E550W' and paper.attrib['autoLength']=='false'
        assert b'Amir Rahimi' in properties and b'Users' not in properties
        along,across=metadata['resolution'];x=round(float(style.attrib['x'][:-2])/72*25.4*along/25.4);y=round(float(style.attrib['y'][:-2])/72*25.4*across/25.4)
        reconstructed=Image.new('L',image.size,255);picture=Image.open(io.BytesIO(bitmap)).convert('L');reconstructed.paste(picture,(x,y))
        assert ImageChops.difference(image.convert('L'),reconstructed).getbbox() is None


def test_standalone_prepare_download_mapping_and_editor_handoff(context,monkeypatch):
    import labelstudio.native as native
    client,store,source,file=context;opened=[];monkeypatch.setattr(native,'open_brother_tool',lambda tool,file=None:opened.append((tool,file)))
    document=Document(name='Standalone test',pages=[Label(elements=[Element(text='{ID}',y=5)])])
    response=client.post('/api/standalone/prepare',json={'document':document.model_dump(),'source':source['id'],'sheets':['Records']})
    assert response.status_code==200,response.text
    item=response.json();assert item['payload']['device_state']=='not_transferred' and len(item['payload']['templates'])==2
    with zipfile.ZipFile(io.BytesIO(client.get(item['download_url']).content)) as archive:
        import json
        manifest=json.loads(archive.read('manifest.json'));assert manifest['device_state']=='not_transferred' and manifest['hardware_tested'] is False
        assert manifest['templates'][0]['row']['ID']=='A01'
        assert all('README.'+lang+'.txt' in archive.namelist() for lang in ('fa','en','ar'))
        assert archive.read('label-001.lbx').startswith(b'PK')
    result=client.post('/api/standalone/'+item['id']+'/open',json={'file':'label-001.lbx'})
    assert result.json()['device_state']=='not_transferred' and opened[0][0]=='editor'
    assert opened[0][1].read_bytes().startswith(b'PK')
    assert client.post('/api/standalone/'+item['id']+'/open',json={'file':'../../outside.lbx'}).status_code==422


def test_standalone_limits_and_actual_source_range(context):
    client,store,source,file=context;document=Document().model_dump()
    body={'document':document,'records':[{}]*99}
    document['pages']*=2
    assert client.post('/api/standalone/prepare',json=body).json()['error']=='STANDALONE_MAX_99_TEMPLATES'
    document['pages']=[Label(model='PT-P750W').model_dump()]
    assert client.post('/api/standalone/prepare',json={'document':document}).json()['error']=='STANDALONE_REQUIRES_E550W'
    result=client.post('/api/standalone/prepare',json={'document':Document().model_dump(),'source':source['id'],'sheets':['Records'],'record_from':1,'record_to':2})
    assert result.status_code==200 and result.json()['payload']['records']==1


def test_foreign_user_cannot_fetch_export_plan_or_native_bundle(context):
    client,store,source,file=context;exported,rows=export(context);rows[0]['PrintStatus']='OK';plan=preview(context,rows).json()
    bundle=client.post('/api/standalone/prepare',json={'document':Document().model_dump()}).json()
    with store.connect() as db:db.execute('INSERT INTO users VALUES(?,?,?,?,?,?,?)',('other','other',PASSWORDS.hash('password123'),'user','{}',0,time.time()))
    store.save_settings(store.settings().model_copy(update={'auth_enabled':True}))
    login=client.post('/api/login',json={'username':'other','password':'password123'}).json();client.headers['X-CSRF-Token']=login['csrf']
    assert client.get(exported['download_url']).status_code==404
    assert client.post('/api/status/imports/'+plan['id']+'/apply',json={}).status_code==404
    assert client.get(bundle['download_url']).status_code==404
    assert client.get('/api/standalone').json()==[]
