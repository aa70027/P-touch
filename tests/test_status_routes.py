import time

from fastapi.testclient import TestClient
from openpyxl import Workbook,load_workbook
import pytest

from labelstudio.app import create_app
from labelstudio.models import Document
from labelstudio.store import PASSWORDS


@pytest.fixture
def context(tmp_path):
    file=tmp_path/'original.xlsx';book=Workbook();book.active.title='Sheet1'
    book.active.append(['ID','وضعیت چاپ']);book.active.append(['A01','']);book.save(file);book.close()
    app=create_app(tmp_path/'data');store=app.state.store
    source=store.save_resource(store.user('local'),'source',file.name,{'linked_path':str(file)},'private')
    with TestClient(app) as client:
        boot=client.get('/api/bootstrap').json();client.headers.update({'X-Studio-Request':'1','X-CSRF-Token':boot['csrf']})
        yield client,store,source,file


def selection():return dict(sheets=['Sheet1'],key_column='ID',status_column='وضعیت چاپ')


def update():return dict(sheet='Sheet1',key='A01',expected_status='',status='OK')


def test_original_excel_write_and_owner_backup_through_authenticated_api(context):
    client,store,source,file=context;url='/api/sources/'+source['id']+'/status'
    options=client.get(url+'/options').json()
    assert options['columns_by_sheet']['Sheet1']==['ID','وضعیت چاپ']
    assert options['device']['state']=='unknown' and options['device']['readback_supported'] is False
    before=file.read_bytes()
    state=client.post(url+'/inspect',json=selection());assert state.status_code==200,state.text
    assert store.resource(source['id'],store.user('local'))['payload']['status_sync']==selection()
    result=client.post(url+'/apply',json=selection()|{'fingerprint':state.json()['fingerprint'],'updates':[update()]})
    assert result.status_code==200,result.text
    assert result.json()['changed']==1 and result.json()['device']['state']=='pending_transfer'
    book=load_workbook(file);assert book.active['B2'].value=='OK';book.close()
    history=client.get(url+'/history').json();assert len(history)==1
    backup=client.get(history[0]['backup_url']);assert backup.content==before
    assert 'original.xlsx' not in result.text


def test_upload_is_not_misrepresented_as_original_writeback(context):
    client,store,source,file=context
    upload=store.save_resource(store.user('local'),'source','copy.xlsx',{'file':'upload.xlsx'},'private')
    response=client.get('/api/sources/'+upload['id']+'/status/options')
    assert response.status_code==422 and response.json()['error']=='STATUS_REQUIRES_ORIGINAL_LINKED_EXCEL'


def test_foreign_shared_source_and_backup_cannot_be_written_or_downloaded(context):
    client,store,source,file=context;url='/api/sources/'+source['id']+'/status'
    store.save_resource(store.user('local'),'source',file.name,source['payload'],'shared',source['id'])
    state=client.post(url+'/inspect',json=selection()).json()
    result=client.post(url+'/apply',json=selection()|{'fingerprint':state['fingerprint'],'updates':[update()]}).json()
    with store.connect() as db:
        db.execute('INSERT INTO users VALUES(?,?,?,?,?,?,?)',('other','other',PASSWORDS.hash('password123'),'user','{}',0,time.time()))
    store.save_settings(store.settings().model_copy(update={'auth_enabled':True}))
    login=client.post('/api/login',json={'username':'other','password':'password123'}).json();client.headers['X-CSRF-Token']=login['csrf']
    assert client.get(url+'/options').status_code==403
    assert client.post(url+'/inspect',json=selection()).status_code==403
    assert client.post(url+'/apply',json=selection()|{'fingerprint':state['fingerprint'],'updates':[update()]}).status_code==403
    assert client.get('/api/status/backups/'+result['event']).status_code==404


def test_stale_workbook_rejected_through_api(context):
    client,store,source,file=context;url='/api/sources/'+source['id']+'/status'
    state=client.post(url+'/inspect',json=selection()).json()
    book=load_workbook(file);book.active['B2']='changed elsewhere';book.save(file);book.close()
    response=client.post(url+'/apply',json=selection()|{'fingerprint':state['fingerprint'],'updates':[update()]})
    assert response.status_code==422 and response.json()['error']=='SOURCE_CHANGED_REFRESH_STATUS'
    assert client.get(url+'/history').json()==[]


def test_print_simulation_does_not_mark_excel_ok(context):
    client,store,source,file=context
    response=client.post('/api/jobs',json={'documents':[Document().model_dump()],'source':source['id'],'sheets':['Sheet1'],'simulation':True})
    assert response.status_code==200,response.text
    deadline=time.monotonic()+8
    while time.monotonic()<deadline:
        state=client.get('/api/jobs/'+response.json()['id']+'/status').json()
        if state['state']=='simulated':break
        assert state['state']!='failed',state
        time.sleep(.04)
    assert state['state']=='simulated'
    book=load_workbook(file);assert book.active['B2'].value is None;book.close()
    assert client.get('/api/sources/'+source['id']+'/status/history').json()==[]
