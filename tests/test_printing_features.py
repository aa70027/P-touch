import json
import time
import pytest
from fastapi.testclient import TestClient
from PIL import ImageOps
from labelstudio.app import create_app
from labelstudio.layout import center_label
from labelstudio.models import CutSettings,Document,Element,Label,PrintRequest,Settings
from labelstudio.jobs import plan
from labelstudio.printer import cut_for
from labelstudio.render import render_label,to_persian_digits,DPM,SCALE,element_image
from labelstudio import render as renderer

def assets(*args):raise AssertionError('Unexpected asset request')

@pytest.fixture
def client(tmp_path):
    app=create_app(tmp_path)
    with TestClient(app) as c:
        c.headers.update({'X-Studio-Request':'1','X-CSRF-Token':c.get('/api/bootstrap').json()['csrf']})
        yield c

def saved_document(client,name='cable',doc=None,scope='private'):
    response=client.post('/api/resources',json={'name':name,'kind':'document','scope':scope,'payload':(doc or Document(name=name)).model_dump()})
    assert response.status_code==200,response.text
    return response.json()

def wait_job(client,ident,expected):
    end=time.time()+10
    while time.time()<end:
        status=client.get('/api/jobs/'+ident+'/status').json()
        if status['state']==expected:return status
        if status['state']=='failed':pytest.fail(str(status))
        time.sleep(.02)
    pytest.fail(str(status))

def test_file_cut_override_and_reset_persist_without_changing_layout(client):
    resource=saved_document(client)
    original=resource['payload']['pages']
    policy=CutSettings(cut_between_pages='none',cut_end_record='full',cut_between_files='half',cut_end_file='none').model_dump()
    result=client.patch('/api/resources/'+resource['id']+'/cut-settings',json={'cut_settings':policy})
    assert result.status_code==200,result.text
    assert result.json()['payload']['pages']==original
    app=create_app(client.app.state.store.root)
    assert app.state.store.resource(resource['id'],app.state.store.user('local'))['payload']['cut_settings']==policy
    assert client.get('/api/settings').json()['cut_between_pages']=='half'
    reset=client.patch('/api/resources/'+resource['id']+'/cut-settings',json={'cut_settings':None})
    assert reset.json()['payload']['cut_settings'] is None

def test_latest_general_defaults_and_legacy_files(client):
    resource=saved_document(client)
    settings=client.get('/api/settings').json();settings['cut_end_file']='none'
    assert client.put('/api/settings',json=settings).status_code==200
    assert client.get('/api/printing/defaults').json()['cut_settings']['cut_end_file']=='none'
    doc=Document.model_validate(resource['payload'])
    assert doc.cut_settings is None
    assert cut_for(doc.cut_settings or Settings(**settings),True,True,True)=='none'

def test_cut_save_changes_only_policy_not_latest_saved_layout(client):
    resource=saved_document(client)
    updated=resource['payload'];updated['pages'][0]['elements'][0]['text']='OTHER SAVED EDIT'
    client.put('/api/resources/'+resource['id'],json={'name':'cable','kind':'document','scope':'private','payload':updated})
    response=client.patch('/api/resources/'+resource['id']+'/cut-settings',json={'cut_settings':CutSettings().model_dump()})
    assert response.json()['payload']['pages'][0]['elements'][0]['text']=='OTHER SAVED EDIT'

def test_cut_permissions_and_normal_user_defaults(tmp_path):
    app=create_app(tmp_path);store=app.state.store;owner=store.user('local')
    resource=store.save_resource(owner,'document','shared',Document().model_dump(),'shared')
    from labelstudio.store import PASSWORDS
    with store.connect() as db:
        db.execute('INSERT INTO users VALUES(?,?,?,?,?,?,?)',('other','other',PASSWORDS.hash('password123'),'user','{}',0,time.time()))
    store.save_settings(store.settings().model_copy(update={'auth_enabled':True}))
    with TestClient(app) as c:
        c.headers['X-Studio-Request']='1'
        login=c.post('/api/login',json={'username':'other','password':'password123'}).json();c.headers['X-CSRF-Token']=login['csrf']
        assert c.get('/api/printing/defaults').status_code==200
        assert c.get('/api/settings').status_code==403
        assert c.patch('/api/resources/'+resource['id']+'/cut-settings',json={'cut_settings':None}).status_code==403
        assert store.resource(resource['id'],owner)['payload']['cut_settings'] is None

def test_multifile_cut_order_and_job_snapshot(client):
    first=Document(name='A',pages=[Label(repeat=2)],cut_settings=CutSettings(cut_between_pages='none',cut_end_record='half',cut_between_files='none',cut_end_file='half'))
    second=Document(name='B',cut_settings=CutSettings(cut_between_pages='full',cut_end_record='full',cut_between_files='full',cut_end_file='full'))
    request=PrintRequest(documents=[first,second],records=[{'n':1},{'n':2}],simulation=True)
    steps=list(plan(request))
    cuts=[cut_for(step['cut_settings'] or Settings(),step['end_record'],step['end_file'],step['last']) for step in steps]
    assert cuts==['none','half','none','none','full','full']
    response=client.post('/api/jobs',json=request.model_dump());assert response.status_code==200,response.text
    ident=response.json()['id'];wait_job(client,ident,'simulated')
    payload=client.get('/api/jobs/'+ident).json()['payload']
    assert payload['request']['documents'][0]['cut_settings']['cut_between_files']=='none'
    assert payload['request']['documents'][1]['cut_settings']['cut_end_file']=='full'
    # Actual generated raster headers, rather than a settings-only assertion.
    for number,cut in enumerate(cuts,1):
        raw=client.get(f'/api/jobs/{ident}/artifacts/{number}/prn').content
        offset=raw.index(b'\x1biM')+3
        assert raw[offset]==(0x40 if cut=='full' else 0)
        advanced=raw[raw.index(b'\x1biK')+3]
        assert bool(advanced&4)==(cut=='half')

def test_queued_cut_snapshot_survives_general_changes(client):
    req=PrintRequest(documents=[Document(cut_settings=CutSettings(cut_end_record='none',cut_end_file='none'))],records=[{'N':1},{'N':2}],simulation=True,mode='confirm')
    ident=client.post('/api/jobs',json=req.model_dump()).json()['id'];wait_job(client,ident,'waiting')
    settings=client.get('/api/settings').json();settings['cut_end_file']='full';client.put('/api/settings',json=settings)
    client.post('/api/jobs/'+ident+'/next',json={});wait_job(client,ident,'simulated')
    raw=client.get(f'/api/jobs/{ident}/artifacts/2/prn').content
    assert raw[raw.index(b'\x1biM')+3]==0
    status=client.get('/api/jobs/'+ident+'/status').json()
    assert 'payload' not in status and status['simulated']==2

@pytest.mark.parametrize('value',['invalid',1,{}])
def test_invalid_cut_cannot_replace_saved_policy(client,value):
    resource=saved_document(client)
    assert client.patch('/api/resources/'+resource['id']+'/cut-settings',json={'cut_settings':{'cut_end_file':value}}).status_code==422
    assert client.app.state.store.resource(resource['id'],client.app.state.store.user('local'))['payload']['cut_settings'] is None

def test_persian_digits_after_formulas_without_mutating_data(client):
    doc=Document(pages=[Label(persian_digits=True,elements=[Element(text='{B}')])],rules=[{'target':'B','when':'N == "123"','value':'CONCAT("Rack-", N)','otherwise':'"wrong"'}])
    response=client.post('/api/preview',json={'document':doc.model_dump(),'row':{'N':'123'}})
    assert response.status_code==200,response.text
    assert response.json()['row']['B']=='Rack-123'
    actual,_=render_label(doc.pages[0],{'B':'Rack-123'},assets)
    expected,_=render_label(Label(elements=[Element(text='Rack-۱۲۳')]),{},assets)
    assert actual.tobytes()==expected.tobytes()
    saved=saved_document(client,doc=doc)
    assert saved['payload']['pages'][0]['persian_digits'] is True
    assert to_persian_digits('0١2۳٤5۶7٨9')=='۰۱۲۳۴۵۶۷۸۹'

@pytest.mark.parametrize('kind,text,width,height',[('qr','Cable123',18,18),('barcode','A01-03',55,6)])
def test_code_payloads_are_not_localized(kind,text,width,height):
    page=Label(elements=[Element(type=kind,text=text,w=width,h=height,y=3.05)])
    original,_=render_label(page,{},assets)
    localized,_=render_label(page.model_copy(update={'persian_digits':True}),{},assets)
    assert original.tobytes()==localized.tobytes()

@pytest.mark.parametrize('rotation',[0,90,180,270])
def test_center_width_repairs_geometry_and_keeps_x(rotation):
    label=Label(elements=[Element(text='X',x=4,y=22,w=5,h=5,rotation=rotation)])
    fixed,info=center_label(label,{},assets,'text1','width')
    assert fixed.elements[0].x==4 and label.elements[0].y==22
    image,_=render_label(fixed,{},assets)
    box=ImageOps.invert(image.convert('L')).getbbox()
    assert abs((box[1]+box[3])/2-image.height/2)<=2

def test_center_group_keeps_spacing():
    label=Label(elements=[Element(id='one',text='1',size=5,h=3,y=0),Element(id='two',text='2',size=5,h=3,y=4)])
    fixed,_=center_label(label,{},assets)
    assert fixed.elements[1].y-fixed.elements[0].y==pytest.approx(4)
    render_label(fixed,{},assets)

def test_center_page_is_stable_and_fixes_current_auto_length():
    label=Label(elements=[Element(text='{N}',x=12,y=0)],persian_digits=True)
    fixed,meta=center_label(label,{'N':'12345'},assets,'text1','page')
    assert meta['fixed_length'] and not fixed.auto_length
    again,_=center_label(fixed,{'N':'12345'},assets,'text1','page')
    assert fixed.elements[0].x==again.elements[0].x and fixed.elements[0].y==again.elements[0].y
    source=element_image(fixed.elements[0],{'N':'12345'},assets,True)
    assert 2+fixed.elements[0].x+source.width/(DPM*SCALE)/2==pytest.approx(fixed.length/2,abs=.001)
    render_label(fixed,{'N':'12345'},assets)

def test_impossible_center_has_actionable_error():
    label=Label(width=6,elements=[Element(type='rectangle',h=10,w=10,y=0)])
    with pytest.raises(ValueError,match='CONTENT_TOO_TALL_TO_CENTER'):center_label(label,{},assets)

def test_center_api_uses_current_row_and_returns_editable_document(client):
    doc=Document(pages=[Label(elements=[Element(text='{N}',y=22)])])
    bad=client.post('/api/preview',json={'document':doc.model_dump(),'row':{'N':'12'}})
    assert bad.status_code==422
    fixed=client.post('/api/design/center',json={'document':doc.model_dump(),'row':{'N':'12'},'element_id':'text1','axis':'width'})
    assert fixed.status_code==200,fixed.text
    good=client.post('/api/preview',json={'document':fixed.json()['document'],'row':{'N':'12'}})
    assert good.status_code==200,good.text

@pytest.mark.parametrize('text,direction',[('Rack-۱۲۳','ltr'),('کابل-۱۲۳','rtl'),('۱۲۳','ltr')])
def test_localized_digits_do_not_change_latin_text_direction(monkeypatch,text,direction):
    monkeypatch.setattr(renderer.features,'check_feature',lambda _:True)
    assert renderer.text_options(text,'auto')=={'direction':direction}
