"""Exercise actual queue-to-RAW writes without sending data to real hardware."""
import socket
import sys
import threading
import time
from types import SimpleNamespace

import pytest

from labelstudio.jobs import JobQueue
from labelstudio.models import CutSettings, Document, PrintRequest, Settings
from labelstudio.printer import Transport
from labelstudio.store import Store


@pytest.fixture
def spooler(monkeypatch):
    import labelstudio.printer as printer
    calls=[]
    def call(name, result=None):
        def method(*args):
            calls.append((name,args))
            return result
        return method
    def write(handle,data):
        calls.append(('write',(handle,data)))
        return len(data)
    stub=SimpleNamespace(OpenPrinter=call('open',77),StartDocPrinter=call('start',18),
                         WritePrinter=write,EndDocPrinter=call('end'),AbortPrinter=call('abort'),
                         ClosePrinter=call('close'),StartPagePrinter=call('start-page'),EndPagePrinter=call('end-page'))
    monkeypatch.setitem(sys.modules,'win32print',stub)
    monkeypatch.setattr(printer,'printers',lambda:[{'name':'test','supported':True,'driver':'Brother PT-E550W'}])
    return calls,stub


def wait(store,ident,state):
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        with store.connect() as db:
            row=dict(db.execute('SELECT * FROM jobs WHERE id=?',(ident,)).fetchone())
        if row['state']==state:return row
        assert row['state']!='failed',row['error']
        time.sleep(.02)
    pytest.fail(str(row))


def cuts():
    return CutSettings(cut_between_pages='half',cut_end_record='half',cut_between_files='half',cut_end_file='full')


def headers(data):
    # Read only known control fields, not accidental byte patterns in raster data.
    mode=data[data.index(b'\x1biM')+3]
    advanced=data[data.index(b'\x1biK')+3]
    return mode,advanced,data[-1]


@pytest.mark.parametrize('cut,last,expected',[
    ('half',False,(0,4,0x0c)),
    ('full',False,(0x40,0,0x0c)),
    ('none',False,(0,0,0x0c)),
    ('half',True,(0,4,0x1a)),
    ('full',True,(0,8,0x1a)),
    ('none',True,(0,0,0x1a)),
])
def test_final_strip_cut_is_separate_from_full_cut_each_label(cut,last,expected):
    from labelstudio.models import Label
    from labelstudio.printer import raster_page
    from labelstudio.render import render_label
    page=Label();image,_=render_label(page,{},lambda ident:None)
    raw=raster_page(image,page,cut,last=last)
    assert headers(raw)==expected
    assert (b'\x1biA\x01' in raw[:raw.index(b'M\x02')])==(cut=='full' and not last)


def test_five_copies_are_one_raw_document_with_only_final_full_cut(tmp_path,spooler):
    calls,_=spooler
    store=Store(tmp_path);queue=JobQueue(store,lambda user:lambda ident:None)
    request=PrintRequest(documents=[Document(cut_settings=cuts())],records=[{}],copies=5)
    ident=queue.create(store.user('local'),request,Settings(printer='test'))
    row=wait(store,ident,'submitted')
    assert row['sent']==5
    names=[name for name,args in calls]
    assert names==['open','start']+['write']*5+['end','close']
    assert next(args for name,args in calls if name=='start')[2][2]=='RAW'
    packets=[args[1] for name,args in calls if name=='write']
    assert [headers(raw) for raw in packets]==[(0,4,0x0c)]*4+[(0,8,0x1a)]
    assert all(b'\x1biA' not in raw[:raw.index(b'M\x02')] for raw in packets)
    assert packets[0].startswith(b'\0'*100+b'\x1b@')
    assert all(not raw.startswith(b'\0'*100+b'\x1b@') for raw in packets[1:])
    log=(store.root/'logs/application.log').read_text(encoding='utf-8')
    assert log.count('cut=half ')==4 and log.count('cut=full ')==1


def test_confirm_gate_keeps_all_page_copies_in_one_raw_segment(tmp_path,spooler):
    calls,_=spooler
    store=Store(tmp_path);queue=JobQueue(store,lambda user:lambda ident:None)
    request=PrintRequest(documents=[Document(cut_settings=cuts())],records=[{'n':1},{'n':2}],copies=5,mode='confirm')
    ident=queue.create(store.user('local'),request,Settings(printer='test'))
    wait(store,ident,'waiting')
    assert [name for name,args in calls]==['open','start']+['write']*5+['end','close']
    packets=[args[1] for name,args in calls if name=='write']
    assert [headers(raw) for raw in packets]==[(0,4,0x0c)]*4+[(0,4,0x1a)]
    queue.signal(ident)
    wait(store,ident,'submitted')
    assert [name for name,args in calls]==(['open','start']+['write']*5+['end','close'])*2
    packets=[args[1] for name,args in calls if name=='write']
    assert headers(packets[-1])==(0,8,0x1a)


def test_partial_write_aborts_without_retry_or_page_ending(spooler):
    calls,stub=spooler
    def incomplete(handle,data):
        calls.append(('write',(handle,data)))
        return len(data)-1
    stub.WritePrinter=incomplete
    with pytest.raises(OSError,match='INCOMPLETE_WRITE'):
        with Transport(Settings(printer='test'),'test') as transport:
            transport.send(b'abc')
    assert [name for name,args in calls]==['open','start','write','abort','close']


def test_wifi_five_copies_remain_one_unchanged_binary_stream(tmp_path):
    from labelstudio.jobs import plan
    from labelstudio.printer import cut_for,raster_page
    from labelstudio.render import render_label
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen()
    port=listener.getsockname()[1];received=[]
    def receive():
        connection,_=listener.accept()
        with connection:
            while raw:=connection.recv(65536):received.append(raw)
        listener.close()
    thread=threading.Thread(target=receive,daemon=True);thread.start()
    store=Store(tmp_path);queue=JobQueue(store,lambda user:lambda ident:None)
    settings=Settings(connection='wifi',ip='127.0.0.1',printer_port=port)
    request=PrintRequest(documents=[Document(cut_settings=cuts())],records=[{}],copies=5)
    ident=queue.create(store.user('local'),request,settings)
    wait(store,ident,'submitted');thread.join(3)
    assert not thread.is_alive()
    expected=[]
    for step in plan(request):
        image,_=render_label(step['page'],step['row'],lambda ident:None)
        cut=cut_for(step['cut_settings'],step['end_record'],step['end_file'],step['last'])
        expected.append(raster_page(image,step['page'],cut,step['index']==1,step['last']))
    assert b''.join(received)==b''.join(expected)
    assert [headers(raw) for raw in expected]==[(0,4,0x0c)]*4+[(0,8,0x1a)]
