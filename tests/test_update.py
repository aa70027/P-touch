"""Release 1.1 integration tests: saved Excel changes, IP identity and updater failures."""
import hashlib
import io
import json
from pathlib import Path
import socket
import threading
import time
from unittest.mock import Mock
import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook,load_workbook
from labelstudio.app import create_app
from labelstudio.data import read_data
from labelstudio.models import Document,Element,Label,Settings
from labelstudio.profiles import PROFILES,detect_model
from labelstudio.render import render_label
from labelstudio.printer import raster_page
from labelstudio import discovery
from labelstudio import updater as update

@pytest.fixture
def client(tmp_path):
    app=create_app(tmp_path/'data')
    with TestClient(app) as client:
        client.headers.update({'X-Studio-Request':'1','X-CSRF-Token':client.get('/api/bootstrap').json()['csrf']})
        yield client

def workbook(path):
    book=Workbook();book.active.title='کابل';book.active.append(['Name','X']);book.active.append(['OLD','yes'])
    second=book.create_sheet('Ports');second.append(['Name','Port']);second.append(['PORT',2]);book.save(path)

def wait_state(updater,state=None):
    end=time.time()+5
    while updater.busy and time.time()<end:time.sleep(.01)
    value=updater.snapshot()
    if state:assert value['state']==state,value
    return value

def test_multisheet_identity_and_union(tmp_path):
    path=tmp_path/'چند شیت.xlsx';workbook(path)
    value=read_data(path,sheets=['کابل','Ports'])
    assert [r['Name'] for r in value['records']]==['OLD','PORT']
    assert [r['_sheet'] for r in value['records']]==['کابل','Ports']
    assert set(value['columns'])=={'Name','X','Port','_sheet'}
    assert value['sheet_counts']=={'کابل':1,'Ports':1}
    with pytest.raises(ValueError,match='SELECT_AT_LEAST_ONE_SHEET'):read_data(path,sheets=[])
    with pytest.raises(ValueError,match='SHEET_NOT_FOUND'):read_data(path,sheets=['Missing'])

def test_live_windows_path_refresh_preview_and_job(client,tmp_path,monkeypatch):
    path=tmp_path/'اصل.xlsx';workbook(path)
    monkeypatch.setattr('labelstudio.native.pick_file',lambda:str(path))
    source=client.post('/api/data/pick',json={}).json()
    assert source['payload']['linked_path']==str(path)
    assert source['scope']=='private'
    assert not list((tmp_path/'data'/'assets').iterdir())
    data=client.post('/api/data/read',json={'source':source['id'],'sheets':['کابل','Ports']}).json()
    assert len(data['records'])==2
    book=load_workbook(path);book['کابل']['A2']='NEW';book['Ports'].append(['ADDED',3]);book.save(path);book.close()
    document=Document(pages=[Label(elements=[Element(text='{Name}')])]).model_dump()
    preview=client.post('/api/preview',json={'source':source['id'],'sheets':['کابل','Ports'],'document':document}).json()
    assert preview['row']['Name']=='NEW'
    response=client.post('/api/jobs',json={'source':source['id'],'sheets':['کابل','Ports'],'documents':[document],'records':[{'Name':'STALE'}],'simulation':True})
    assert response.status_code==200,response.text
    job=client.get('/api/jobs/'+response.json()['id']).json()
    assert job['total']==3
    assert [r['Name'] for r in job['payload']['request']['records']]==['NEW','PORT','ADDED']
    path.unlink()
    assert client.post('/api/data/read',json={'source':source['id']}).json()['error']=='SOURCE_FILE_NOT_FOUND'

def test_file_picker_cancel_and_no_arbitrary_path(client,monkeypatch):
    monkeypatch.setattr('labelstudio.native.pick_file',lambda:None)
    assert client.post('/api/data/pick',json={'path':'C:/Windows/secret.xlsx'}).json()=={'cancelled':True}

@pytest.mark.parametrize('name',['PT-E550W','PT-P750W','PT-P710BT','PT-P900W','QL-820NWB'])
def test_model_recognition_and_physical_geometry(name):
    assert detect_model('Brother '+name+' Series')==name
    profile=next(p for p in PROFILES if p['id']==name)
    label=Label(model=name,width=profile['widths'][-1],quality='high',elements=[Element(text='سلام')])
    image,meta=render_label(label,{},lambda *_:None)
    assert meta['resolution']==[profile['high_dpi'],profile['dpi']]
    assert abs(image.height-label.width*profile['dpi']/25.4)<1
    if profile['transport']=='raster':
        packet=raster_page(image,label,'full')
        assert (b'\x1biA' in packet)==(name!='PT-P710BT')
    else:
        with pytest.raises(ValueError,match='WINDOWS_DRIVER_TRANSPORT_REQUIRED'):raster_page(image,label)

def test_unsupported_model_capabilities():
    with pytest.raises(ValueError):Label(width=36)
    with pytest.raises(ValueError):Settings(model='PT-P710BT',connection='wifi')
    with pytest.raises(ValueError,match='MAC_REQUIRED'):Settings(auto_ip=True)
    label=Label(model='PT-P710BT');image,_=render_label(label,{},lambda *_:None)
    with pytest.raises(ValueError,match='UNSUPPORTED_CUT'):raster_page(image,label,'half')

@pytest.mark.parametrize('value',['AA-BB-CC-DD-EE-FF','aabb.ccdd.eeff','aa:bb:cc:dd:ee:ff'])
def test_mac_formats(value):assert discovery.normalize_mac(value)=='aa:bb:cc:dd:ee:ff'

@pytest.mark.parametrize('value',['AA:BB:GG:DD:EE:FF','GG001122334455','00:11:22'])
def test_invalid_mac(value):
    with pytest.raises(ValueError):discovery.normalize_mac(value)

def test_dhcp_address_changes_and_identity_block(monkeypatch):
    monkeypatch.setattr(discovery,'interfaces',lambda:[dict(network='192.168.1.0/24')])
    monkeypatch.setattr(discovery,'arp',lambda ip:'aa:bb:cc:dd:ee:ff' if ip=='192.168.1.9' else None)
    settings=Settings(connection='wifi',ip='192.168.1.5',mac='aa:bb:cc:dd:ee:ff',auto_ip=True,discovery_subnet='192.168.1.0/28')
    assert discovery.resolve(settings).ip=='192.168.1.9'
    monkeypatch.setattr(discovery,'arp',lambda ip:None)
    with pytest.raises(ValueError,match='PRINTER_MAC_NOT_FOUND'):discovery.resolve(settings)
    monkeypatch.setattr(socket,'gethostbyname',lambda _: '192.168.1.9')
    with pytest.raises(ValueError,match='PRINTER_MAC_MISMATCH'):discovery.resolve(settings.model_copy(update={'hostname':'printer.local'}))

def test_local_subnet_limit(monkeypatch):
    monkeypatch.setattr(discovery,'interfaces',lambda:[dict(network='192.168.1.0/24')])
    for network in ['8.8.8.0/24','192.168.0.0/16','10.0.0.0/24','127.0.0.0/24']:
        with pytest.raises(ValueError):discovery.validate_network(network)

def test_usb_without_driver_model_and_unknown_network(monkeypatch):
    monkeypatch.setattr(discovery,'powershell',lambda _:[dict(Name='USB Device',PNPDeviceID='USB\\VID_04F9&PID_2062',ConfigManagerErrorCode=28,Service=None)])
    value=discovery.usb_devices()[0]
    assert value['model']=='PT-P750W' and not value['driver_loaded']
    monkeypatch.setattr(discovery,'snmp_description',lambda *_:None)
    monkeypatch.setattr(socket,'create_connection',Mock(side_effect=OSError))
    value=discovery.probe('192.168.1.3')
    assert not value['identity_verified'] and not value['reachable'] and value['model'] is None

def test_snmp_identity_and_transaction(monkeypatch):
    def response(packet):
        # Extract the request ID; synthesize a correctly tagged GetResponse.
        offset=packet.index(b'\xa0');body=packet[offset+2:];request_id=body[2:6]
        oid=b'\x2b\x06\x01\x02\x01\x01\x01\x00'
        binding=discovery.tlv(0x30,discovery.tlv(6,oid)+discovery.tlv(4,b'Brother PT-E550W'))
        pdu=discovery.tlv(0xa2,discovery.tlv(2,request_id)+b'\x02\x01\x00'*2+discovery.tlv(0x30,binding))
        return discovery.tlv(0x30,b'\x02\x01\x00'+discovery.tlv(4,b'public')+pdu)
    class Sock:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def settimeout(self,*args):pass
        def sendto(self,packet,*args):self.packet=packet
        def recvfrom(self,*args):return response(self.packet),('192.168.1.3',161)
    monkeypatch.setattr(socket,'socket',lambda *_:Sock())
    assert discovery.snmp_description('192.168.1.3')=='Brother PT-E550W'

def test_semver_and_release_filter(monkeypatch):
    assert update.version('1.10.0')>update.version('1.9.9')
    assert update.version('1.2.0')>update.version('1.2.0-rc1')
    releases=[]
    for v,pre in [('1.0.0',False),('1.2.0',False),('2.0.0',True)]:
        releases.append(dict(tag_name='v'+v,html_url='https://github.com/aa70027/P-touch/releases/tag/v'+v,prerelease=pre,assets=[dict(name='CableLabelStudio-'+v+'-Setup.exe',size=1,browser_download_url='x'),dict(name='SHA256SUMS.txt',browser_download_url='y')]))
    class Response(io.BytesIO):pass
    monkeypatch.setattr(update,'request',lambda _:Response(json.dumps(releases).encode()))
    assert update.release_info()['release']['version']=='1.2.0'
    assert update.release_info(True)['release']['version']=='2.0.0'

def test_update_check_error_persists(tmp_path,monkeypatch):
    worker=update.Updater(tmp_path)
    monkeypatch.setattr(update,'release_info',Mock(side_effect=OSError('network down')))
    worker.check();state=wait_state(worker,'error')
    assert 'network down' in state['error']
    assert update.Updater(tmp_path).snapshot()['events']==state['events']

def test_actual_stream_download_and_interruption(tmp_path,monkeypatch):
    content=b'printer-update'*100000
    class Response(io.BytesIO):
        headers={'Content-Length':str(len(content))};url='https://download.brother.com/file.exe'
    monkeypatch.setattr(update,'request',lambda _:Response(content))
    worker=update.Updater(tmp_path);path=tmp_path/'download.exe'
    digest=worker.download(Response.url,path,update.brother_url,len(content))
    assert digest==hashlib.sha256(content).hexdigest() and path.read_bytes()==content
    with pytest.raises(ValueError,match='INCOMPLETE_DOWNLOAD'):worker.download(Response.url,path,update.brother_url,len(content)+1)
    assert not path.with_suffix('.exe.part').exists()

def test_checksum_failure_never_installs(tmp_path,monkeypatch):
    import sys
    worker=update.Updater(tmp_path)
    executable=tmp_path/'CableLabelStudio.exe';executable.touch()
    (tmp_path/'package-manifest.json').write_text('{}');(tmp_path/'CableLabelStudio-Update.exe').touch()
    monkeypatch.setattr(sys,'frozen',True,raising=False);monkeypatch.setattr(sys,'executable',str(executable))
    url='https://github.com/aa70027/P-touch/releases/download/v9.0.0/'
    release=dict(version='9.0.0',name='CableLabelStudio-9.0.0-Setup.exe',installer=url+'setup.exe',checksums=url+'SHA256SUMS.txt',size=3)
    monkeypatch.setattr(update,'release_info',lambda *_:dict(available=True,release=release))
    monkeypatch.setattr(update,'request',lambda _:io.BytesIO(('0'*64+'  '+release['name']).encode()))
    def download(url,path,*args):path.write_bytes(b'bad');return hashlib.sha256(b'bad').hexdigest()
    monkeypatch.setattr(worker,'download',download)
    launch=Mock();monkeypatch.setattr(update.subprocess,'Popen',launch);backup=Mock()
    worker.install(False,backup,lambda:False);state=wait_state(worker,'error')
    assert state['error']=='UPDATE_CHECKSUM_MISMATCH'
    launch.assert_not_called();backup.assert_not_called()

@pytest.mark.parametrize('url',['http://download.brother.com/a.exe','https://brother.com.evil.test/a.exe','https://127.0.0.1/a.exe'])
def test_software_origin(url):
    with pytest.raises(ValueError):update.brother_url(url)

def test_branding_and_new_routes(client):
    boot=client.get('/api/bootstrap').json()
    assert boot['creator']=='Amir Rahimi' and boot['license']=='MIT'
    assert boot['project_url']=='https://github.com/aa70027/P-touch'
    assert len(boot['profiles'])>=9
    assert client.get('/api/updates').status_code==200
    assert client.get('/api/printer/discovery').json()['running'] is False
    assert client.post('/api/updates/install',json={}).status_code==422
