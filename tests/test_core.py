import io
import json
import socket
import struct
import threading
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageOps
from labelstudio.app import create_app
from labelstudio.models import Document, Label, Element, Settings, PrintRequest
from labelstudio.formulas import evaluate, apply_rules, interpolate
from labelstudio.render import render_label
from labelstudio.printer import packbits, raster_page, cut_for, Transport
from labelstudio.jobs import plan
from labelstudio.data import read_data


@pytest.fixture
def client(tmp_path):
    app=create_app(tmp_path)
    with TestClient(app) as c:
        boot=c.get('/api/bootstrap').json()
        c.headers.update({'X-Studio-Request':'1','X-CSRF-Token':boot['csrf']})
        yield c


def await_job(client,ident,state,timeout=10):
    deadline=time.time()+timeout
    while time.time()<deadline:
        job=client.get('/api/jobs/'+ident).json()
        if job['state']==state:
            return job
        if job['state']=='failed':
            pytest.fail(job['error'])
        time.sleep(.04)
    pytest.fail(str(job))


@pytest.mark.parametrize('expression,row,expected',[
    ('IF(EMPTY(COL("X")), "", "A")',{'X':'ready'},'A'),
    ('IF(EMPTY(COL("X")), "", "A")',{'X':''},''),
    ('IF(True, "ok", NUMBER("not a number"))',{},'ok'),
    ('CONCAT(Rack, "-", PAD(Port, 2))',{'Rack':'A','Port':3},'A-03'),
    ('NUMBER("4") * 3 + 1',{},13),
    ('COL("نوع کابل") == "فیبر"',{'نوع کابل':'فیبر'},True),
    ('CONTAINS(LOWER(COL("Type")), "fiber")',{'Type':'FIBER-1'},True),
    ('not EMPTY(X) and X == "A"',{'X':'A'},True),
])
def test_formulas(expression,row,expected):
    assert evaluate(expression,row)==expected


@pytest.mark.parametrize('expression',['__import__("os").getcwd()', '(1).__class__', '[x for x in [1]]', 'open("file")', '"a" * 1000000000'])
def test_formula_sandbox(expression):
    with pytest.raises((ValueError,TypeError)):
        evaluate(expression,{})


def test_rules_in_order():
    assert apply_rules({'X':'A'},[{'target':'B','when':'X == "A"','value':"'first'"},
                                   {'target':'C','value':'CONCAT(B, "!")'}])['C']=='first!'
    assert interpolate('{{Rack}} {Rack}',{'Rack':'A'})=='{Rack} A'


def assets(*args):
    raise KeyError('not found')


@pytest.mark.parametrize('text',['سلام دیتاسنتر','رک A12، پورت 03','مرحبا بالعالم','DC-A01-03'])
def test_languages_render(text):
    image,meta=render_label(Label(elements=[Element(text=text)]),{},assets)
    assert ImageOps.invert(image.convert('L')).getbbox()
    assert 10<meta['length_mm']<100


def test_auto_length_and_high_resolution():
    small=Label(elements=[Element(text='A')])
    large=Label(elements=[Element(text='A'*20)])
    a,ma=render_label(small,{},assets)
    b,mb=render_label(large,{},assets)
    assert mb['length_mm']>ma['length_mm']
    high=small.model_copy(update={'quality':'high'})
    c,mc=render_label(high,{},assets)
    assert abs(c.width-a.width*2)<=1 and c.height==a.height


def test_mirror():
    normal=Label(elements=[Element(text='F')],auto_length=False)
    a,_=render_label(normal,{},assets)
    b,_=render_label(normal.model_copy(update={'mirror':True}),{},assets)
    assert ImageOps.mirror(a).tobytes()==b.tobytes()


def test_layout_overflow_and_printable_bounds():
    with pytest.raises(ValueError,match='TEXT_OVERFLOW'):
        render_label(Label(elements=[Element(text='long long long',w=2)]),{},assets)
    with pytest.raises(ValueError,match='OUTSIDE_PRINTABLE_AREA'):
        render_label(Label(elements=[Element(text='ABC',y=0,h=3,size=6)]),{},assets)
    with pytest.raises(ValueError,match='ELEMENT_OUTSIDE_LABEL'):
        render_label(Label(auto_length=False,length=10,elements=[Element(text='A'*20)]),{},assets)


def test_flag_repeats_one_field():
    label=Label(kind='cable-flag',auto_length=False,length=35,separator='',separator_line=False,elements=[Element(text='{ID}')])
    image,meta=render_label(label,{'ID':'A01'},assets)
    left=image.crop((0,0,round(35*180/25.4),image.height))
    right=image.crop((round(43*180/25.4),0,image.width,image.height))
    assert meta['length_mm']==78
    assert ImageOps.invert(left.convert('L')).getbbox()
    assert ImageOps.invert(right.convert('L')).getbbox()


@pytest.mark.parametrize('kind',['general','cable-flag','cable-wrap','patch-panel','faceplate','die-cut-flag','terminal-block','heat-shrink'])
def test_seed_templates_work(client,kind):
    resource=next(r for r in client.get('/api/resources').json() if r['payload']['pages'][0]['kind']==kind)
    result=client.post('/api/preview',json={'document':resource['payload'],'row':{'Rack':'A01','Port':'01'}})
    assert result.status_code==200,result.text


def unpackbits(data):
    result=bytearray();i=0
    while i<len(data):
        n=data[i];i+=1
        if n<=127:
            result.extend(data[i:i+n+1]);i+=n+1
        elif n>=129:
            result.extend(bytes([data[i]])*(257-n));i+=1
    return bytes(result)


@pytest.mark.parametrize('raw',[b'\x00'*16,bytes(range(16)),b'aabbccddee112233',b'\xff'*16])
def test_packbits(raw):
    assert unpackbits(packbits(raw))==raw


def test_raster_header_and_geometry():
    label=Label()
    image,_=render_label(label,{},assets)
    data=raster_page(image,label,'half')
    assert data.startswith(b'\0'*100+b'\x1b@\x1bia\x01')
    assert b'\x1biM\x00' in data and b'\x1biK\x04' in data
    assert b'\x1bid\x0e\0M\x02' in data
    assert data[-1]==0x1a
    assert b'\x1biS' not in data # Unsupported status query on E550W.
    high=label.model_copy(update={'quality':'high'})
    highimage,_=render_label(high,{},assets)
    highdata=raster_page(highimage,high,'none',last=False)
    assert b'\x1biK\x40' in highdata
    assert highdata[-1]==0x0c


def decode_raster(data):
    start=data.index(b'M\x02')+2
    rows=[]
    while start<len(data)-1:
        if data[start]==ord('Z'):
            rows.append(bytes(16));start+=1
        else:
            assert data[start]==ord('G')
            count=struct.unpack('<H',data[start+1:start+3])[0]
            rows.append(unpackbits(data[start+3:start+3+count]));start+=3+count
    return rows


def test_raster_pin_order_and_length():
    label=Label(auto_length=False,length=60)
    image=Image.new('1',(425,170),1)
    image.putpixel((30,21),0) # first printable pin, after physical left feed.
    data=raster_page(image,label)
    lines=decode_raster(data)
    assert len(lines)==425-28
    assert lines[30-14]==b'\x80'+bytes(15)
    assert sum(sum(b.bit_count() for b in row) for row in lines)==1
    index=data.index(b'\x1biz')+3
    assert struct.unpack('<I',data[index+4:index+8])[0]==len(lines)


def test_high_resolution_keeps_physical_length():
    p=Label(auto_length=False,length=60)
    a,_=render_label(p,{},assets)
    high=p.model_copy(update={'quality':'high'})
    b,_=render_label(high,{},assets)
    normal_lines=decode_raster(raster_page(a,p))
    high_lines=decode_raster(raster_page(b,high))
    # Feed is 14 dots at 180 dpi, 28 at 360. High samples are never doubled twice.
    physical_normal=(len(normal_lines)+28)*25.4/180
    physical_high=(len(high_lines)+56)*25.4/360
    assert abs(physical_normal-60)<.15 and abs(physical_high-60)<.08


@pytest.mark.parametrize('margin',[0,1,2,5])
def test_manual_length_includes_mechanical_margin(margin):
    label=Label(auto_length=False,length=60,margin_before=margin,margin_after=margin)
    image,meta=render_label(label,{},assets)
    assert meta['length_mm']==60 and meta['estimated_output_mm']==60
    assert meta['actual_margin_before_mm']==max(2,margin)
    lines=decode_raster(raster_page(image,label))
    assert abs((len(lines)+28)*25.4/180-60)<.15


def test_panel_manual_length_and_cell_pitch():
    label=Label(kind='patch-panel',auto_length=False,length=90,elements=[Element(text='{#cell}',size=8)],cells=6,pitch=12)
    _,meta=render_label(label,{},assets)
    assert meta['length_mm']==90
    with pytest.raises(ValueError,match='PANEL_LENGTH_TOO_SHORT'):
        render_label(label.model_copy(update={'length':60}),{},assets)


def test_image_and_uploaded_font(client):
    import os
    stream=io.BytesIO();Image.new('RGB',(20,20),'black').save(stream,'PNG')
    image=client.post('/api/upload?kind=image',files={'file':('test.png',stream.getvalue(),'image/png')}).json()
    fontfile=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'/'tahoma.ttf'
    font=client.post('/api/upload?kind=font',files={'file':('custom.ttf',fontfile.read_bytes(),'font/ttf')}).json()
    doc=Document(pages=[Label(elements=[Element(text='سلام',font=font['id']),Element(id='logo',type='image',asset=image['id'],x=30,y=4,w=10,h=10)])])
    result=client.post('/api/preview',json={'document':doc.model_dump()})
    assert result.status_code==200,result.text


def test_qr_and_code128():
    for kind,text,width,height in [('qr','سلام کابل',18,18),('barcode','A01-03',55,6)]:
        label=Label(elements=[Element(type=kind,text=text,w=width,h=height,y=3.05)])
        image,_=render_label(label,{},assets)
        assert ImageOps.invert(image.convert('L')).getbbox()


def test_resource_persists_after_restart(tmp_path):
    a=create_app(tmp_path)
    user=a.state.store.user('local')
    saved=a.state.store.save_resource(user,'document','persistent',Document().model_dump(),'private')
    b=create_app(tmp_path)
    assert b.state.store.resource(saved['id'],user)['name']=='persistent'


def test_interrupted_jobs_not_resent(tmp_path):
    a=create_app(tmp_path)
    with a.state.store.connect() as db:
        db.execute('INSERT INTO jobs(id,owner,state,total,created,updated,payload) VALUES(?,?,?,?,?,?,?)',('stopped','local','running',5,time.time(),time.time(),'{}'))
    b=create_app(tmp_path)
    with b.state.store.connect() as db:
        job=dict(db.execute('SELECT * FROM jobs WHERE id="stopped"').fetchone())
    assert job['state']=='interrupted' and job['sent']==0


def test_nonempty_access_error_is_actionable(client):
    source=client.post('/api/upload?kind=source',files={'file':('test.accdb',b'not-a-real-access-database','application/octet-stream')}).json()
    from labelstudio.data import access_drivers
    if not access_drivers():
        result=client.post('/api/data/read',json={'source':source['id']})
        assert result.status_code==422 and result.json()['error']=='ACCESS_DRIVER_MISSING'


def test_cut_precedence():
    s=Settings(cut_between_pages='none',cut_end_record='half',cut_between_files='full',cut_end_file='none')
    assert cut_for(s,False,False,False)=='none'
    assert cut_for(s,True,False,False)=='half'
    assert cut_for(s,True,True,False)=='full'
    assert cut_for(s,True,True,True)=='none'


def test_print_plan_order():
    req=PrintRequest(documents=[Document(name='a',pages=[Label(repeat=2),Label()]),Document(name='b')],records=[{'ID':1},{'ID':2}],copies=2,file_copies=2)
    steps=list(plan(req))
    assert len(steps)==32
    assert steps[-1]['last'] and not steps[0]['last']
    assert sum(s['end_record'] for s in steps)==8
    assert sum(s['end_file'] for s in steps)==4
    assert steps[0]['row']['ID']==1 and steps[6]['row']['ID']==2


def test_csv_and_excel(tmp_path):
    csv=tmp_path/'data.csv';csv.write_text('رک,Port\nA01,01\nA02,02\n',encoding='utf-8-sig')
    assert read_data(csv)['records'][0]=={'رک':'A01','Port':'01'}
    from openpyxl import Workbook
    book=Workbook();book.active.append(['Rack','Port']);book.active.append(['A01',2]);book.create_sheet('Other').append(['X'])
    path=tmp_path/'data.xlsx';book.save(path)
    result=read_data(path)
    assert result['records'][0]['Port']==2 and result['sheets']==['Sheet','Other']


def test_request_origin_and_csrf(client):
    assert client.post('/api/formula',json={'expression':'1'},headers={'Origin':'https://evil.example'}).status_code==403
    assert client.post('/api/formula',json={'expression':'1'},headers={'X-CSRF-Token':'wrong'}).status_code==403
    assert client.get('/api/health',headers={'Host':'attacker.example'}).status_code==400


def test_no_driver_is_truthful(client):
    data=client.get('/api/printer/status').json()
    assert data['device_confirmed'] is False
    assert data['driver_installed']==any('E550W' in name.upper().replace('-','') for name in data['drivers'])
    result=client.post('/api/jobs',json={'documents':[{'name':'x','pages':[{}]}]})
    assert result.status_code==422


def test_driver_without_queue_and_disconnected_usb(monkeypatch):
    import labelstudio.printer as printer
    monkeypatch.setattr(printer,'printers',lambda:[])
    monkeypatch.setattr(printer,'installed_drivers',lambda:['Brother PT-E550W'])
    monkeypatch.setattr(printer,'usb_present',lambda:False)
    assert printer.status(Settings())['driver_installed'] is True
    monkeypatch.setattr(printer,'printers',lambda:[{'name':'test','supported':True,'status':0}])
    assert printer.status(Settings(printer='test'))['state']=='offline'
    monkeypatch.setattr(printer,'usb_present',lambda:True)
    assert printer.status(Settings(printer='test'))['detail']=='USB_DEVICE_DETECTED'


def test_settings_persist_and_validate_port(client):
    settings=client.get('/api/settings').json()
    settings['port']=8888;settings['ip']='192.168.1.20';settings['connection']='wifi'
    result=client.put('/api/settings',json=settings)
    assert result.status_code==200 and result.json()['restart_required']
    assert client.get('/api/settings').json()['port']==8888
    settings['ip']='invalid-ip'
    assert client.put('/api/settings',json=settings).status_code==422


def test_per_user_inherited_sharing(client):
    result=client.put('/api/users/local',json={'username':'manager','role':'admin','share':{'document':True}})
    assert result.status_code==200
    item=client.post('/api/resources',json={'name':'inherited','kind':'document','scope':'inherit','payload':Document().model_dump()}).json()
    other={'id':'other','role':'user'}
    store=client.app.state.store
    assert store.visible(store.resource(item['id'],store.user('local')),other)
    private=client.patch('/api/resources/'+item['id']+'/scope',json={'scope':'private'}).json()
    assert not store.visible(private,other)


def test_default_account_cannot_be_demoted(client):
    assert client.put('/api/users/local',json={'username':'local','role':'user'}).status_code==422


def test_simulation_does_not_count_as_print(client):
    result=client.post('/api/jobs',json={'documents':[{'name':'x','pages':[{}]}],'records':[{'Rack':'A','Port':1},{'Rack':'B','Port':2}], 'copies':2,'simulation':True})
    assert result.status_code==200,result.text
    ident=result.json()['id']
    job=await_job(client,ident,'simulated')
    assert job['total']==4 and job['simulated']==4 and job['sent']==job['confirmed']==0
    assert client.get(f'/api/jobs/{ident}/artifacts/1/png').content.startswith(b'\x89PNG')
    assert client.get(f'/api/jobs/{ident}/artifacts/1/prn').content.startswith(b'\0'*100)
    report=client.get('/api/reports').json()[0]
    assert report['sent']==0 and report['simulated']==4


def test_record_confirmation_gate_and_cancel(client):
    result=client.post('/api/jobs',json={'documents':[{'name':'x','pages':[{}]}],'records':[{'Rack':'A'},{'Rack':'B'},{'Rack':'C'}],'simulation':True,'mode':'confirm'})
    ident=result.json()['id']
    job=await_job(client,ident,'waiting')
    assert job['simulated']==1
    time.sleep(.1)
    assert client.get('/api/jobs/'+ident).json()['simulated']==1
    assert client.post('/api/jobs/'+ident+'/next',json={}).status_code==200
    deadline=time.time()+5
    while time.time()<deadline:
        job=client.get('/api/jobs/'+ident).json()
        if job['state']=='waiting' and job['simulated']==2:break
        time.sleep(.03)
    assert job['simulated']==2
    assert client.post('/api/jobs/'+ident+'/cancel',json={}).status_code==200
    job=await_job(client,ident,'cancelled')
    assert job['simulated']==2


def test_preflight_no_partial_job(client):
    result=client.post('/api/jobs',json={'documents':[{'name':'x','pages':[{}],'rules':[{'target':'A','value':'NUMBER(X)'}]}],'records':[{'X':'1'},{'X':'bad'}],'simulation':True})
    assert result.status_code==422
    assert client.get('/api/jobs').json()==[]


def test_auth_and_private_shared_resources(client):
    settings=client.get('/api/settings').json()
    settings['auth_enabled']=True
    assert client.put('/api/settings',json=settings).status_code==422
    # Set the built-in local administrator password; it retains ownership of existing files.
    assert client.put('/api/users/local',json={'username':'manager','password':'Manager123!','role':'admin'}).status_code==200
    b=client.post('/api/users',json={'username':'operator','password':'Operator123!'}).json()
    private=client.post('/api/resources',json={'name':'secret','kind':'document','scope':'private','payload':{'name':'private','pages':[{}]}}).json()
    shared=client.post('/api/resources',json={'name':'public','kind':'document','scope':'shared','payload':{'name':'shared','pages':[{}]}}).json()
    assert client.put('/api/settings',json=settings).status_code==200
    assert client.get('/api/resources').status_code==401
    login=client.post('/api/login',json={'username':'operator','password':'Operator123!'})
    assert login.status_code==200
    client.headers['X-CSRF-Token']=login.json()['csrf']
    visible=client.get('/api/resources').json()
    assert private['id'] not in [r['id'] for r in visible]
    assert shared['id'] in [r['id'] for r in visible]
    assert client.put('/api/resources/'+shared['id'],json={'name':'bad','kind':'document','payload':{'name':'x','pages':[{}]}}).status_code==403
    assert client.get('/api/settings').status_code==403
    assert client.get('/api/users').status_code==403
    assert client.get('/api/reports').json()[0]['username']=='operator'


def test_admin_queue_reports_do_not_expose_private_print_content(client):
    store=client.app.state.store
    payload={'request':{'records':[{'Secret':'private-print-data'}]},'settings':Settings().model_dump()}
    with store.connect() as db:
        db.execute('INSERT INTO jobs(id,owner,state,total,created,updated,payload) VALUES(?,?,?,?,?,?,?)',
                   ('private-job','different-user','simulated',1,time.time(),time.time(),json.dumps(payload)))
    detail=client.get('/api/jobs/private-job')
    assert detail.status_code==200
    assert detail.json()['payload']['redacted'] is True
    assert 'private-print-data' not in detail.text
    assert client.get('/api/jobs/private-job/artifacts/1/png').status_code==403


def test_upload_and_backup(client):
    stream=io.BytesIO();Image.new('RGB',(20,20),'black').save(stream,'PNG')
    uploaded=client.post('/api/upload?kind=image',files={'file':('logo.png',stream.getvalue(),'image/png')})
    assert uploaded.status_code==200,uploaded.text
    assert client.get('/api/assets/'+uploaded.json()['id']).status_code==200
    dataset=client.post('/api/upload?kind=source',files={'file':('data.csv',b'Rack,Port\nA01,01\n','text/csv')}).json()
    result=client.post('/api/data/read',json={'source':dataset['id']})
    assert result.json()['records'][0]['Port']=='01'
    backup=client.post('/api/backup',json={})
    import zipfile
    with zipfile.ZipFile(io.BytesIO(backup.content)) as archive:
        assert 'studio.sqlite3' in archive.namelist()
        assert any(n.startswith('assets/') for n in archive.namelist())


def test_tcp_transport_local_receiver():
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen()
    port=listener.getsockname()[1];received=[]
    def receive():
        conn,_=listener.accept()
        with conn:
            while data:=conn.recv(65536):received.append(data)
        listener.close()
    thread=threading.Thread(target=receive);thread.start()
    with Transport(Settings(connection='wifi',ip='127.0.0.1',printer_port=port),'test') as transport:
        transport.send(b'PRINT-TEST-ONLY')
    thread.join(3)
    assert b''.join(received)==b'PRINT-TEST-ONLY'
