import contextlib
import json
from pathlib import Path
import queue
import threading
import time
import uuid
from .formulas import apply_rules
from .models import PrintRequest, Settings
from .render import render_label,png_bytes
from .printer import Transport,DriverTransport,raster_page,cut_for
from .profiles import get_profile


def plan(request):
    total=sum(sum(p.repeat*request.copies for p in d.pages)*len(request.records) for d in request.documents)*request.file_copies
    if total>100000:
        raise ValueError('JOB_TOO_LARGE_SPLIT_BATCH')
    index=0
    for file_copy in range(request.file_copies):
        for di,document in enumerate(request.documents):
            for ri,record in enumerate(request.records):
                row=apply_rules(record,document.rules,document.variables)
                for pi,page in enumerate(document.pages):
                    for copy in range(page.repeat*request.copies):
                        index+=1
                        end_record=pi==len(document.pages)-1 and copy==page.repeat*request.copies-1
                        end_file=end_record and ri==len(request.records)-1
                        yield {'index':index,'total':total,'page':page,'row':row,'end_record':end_record,
                               'end_file':end_file,'last':index==total,'document':document.name,'record':ri+1}


class JobQueue:
    def __init__(self,store,asset_factory):
        self.store,self.asset_factory=store,asset_factory
        self.queue=queue.Queue()
        self.signals={}
        self.thread=threading.Thread(target=self.work,daemon=True,name='printer-queue')
        self.thread.start()

    def create(self,user,request,settings):
        # Full preflight before queuing: no half-printed file due to later formula/layout errors.
        assets=self.asset_factory(user)
        total=0
        for step in plan(request):
            render_label(step['page'],step['row'],assets)
            total+=1
        ident=uuid.uuid4().hex
        payload={'request':request.model_dump(),'settings':settings.model_dump()}
        now=time.time()
        with self.store.connect() as db:
            db.execute('INSERT INTO jobs(id,owner,state,total,created,updated,payload) VALUES(?,?,?,?,?,?,?)',
                       (ident,user['id'],'queued',total,now,now,json.dumps(payload,ensure_ascii=False)))
        self.signals[ident]=threading.Event()
        self.queue.put(ident)
        self.store.audit(user['id'],'print.queue',ident)
        return ident

    def update(self,ident,**values):
        values['updated']=time.time()
        with self.store.connect() as db:
            db.execute('UPDATE jobs SET '+','.join(f'{k}=?' for k in values)+' WHERE id=?',list(values.values())+[ident])

    def cancelled(self,ident):
        with self.store.connect() as db:
            row=db.execute('SELECT cancel FROM jobs WHERE id=?',(ident,)).fetchone()
        return bool(row and row['cancel'])

    def signal(self,ident,cancel=False):
        if cancel:
            self.update(ident,cancel=1)
        if ident in self.signals:
            self.signals[ident].set()

    def work(self):
        while True:
            ident=self.queue.get()
            try:
                self.run(ident)
            except Exception as exc:
                self.store.logger.exception('Print job failed %s',ident)
                self.update(ident,state='failed',error=str(exc)[:1000])
            finally:
                self.signals.pop(ident,None)
                self.queue.task_done()

    def run(self,ident):
        with self.store.connect() as db:
            job=dict(db.execute('SELECT * FROM jobs WHERE id=?',(ident,)).fetchone())
        payload=json.loads(job['payload'])
        request=PrintRequest.model_validate(payload['request'])
        settings=Settings.model_validate(payload['settings'])
        user=self.store.user(job['owner'])
        assets=self.asset_factory(user)
        driver=get_profile(settings.model)['transport']=='driver'
        if not request.simulation and settings.connection=='wifi' and not driver:
            from .discovery import resolve
            settings=resolve(settings)
        if self.cancelled(ident):
            self.update(ident,state='cancelled')
            return
        self.update(ident,state='running')
        output=self.store.root/'jobs'/ident
        output.mkdir(exist_ok=True)
        sent,simulated=0,0
        # Each confirmed record is a separate spool job so an unsent next record stays local.
        transport=None
        first=True
        try:
            for step in plan(request):
                if self.cancelled(ident):
                    self.update(ident,state='cancelled')
                    return
                page=step['page']
                image,meta=render_label(page,step['row'],assets)
                cut=cut_for(settings,step['end_record'],step['end_file'],step['last'])
                segment_last=step['last'] or (request.mode=='confirm' and step['end_record'])
                native=get_profile(page.model)['transport']=='raster'
                data=raster_page(image,page,cut,first,segment_last) if native else None
                if request.simulation:
                    (output/f'{step["index"]:06}.png').write_bytes(png_bytes(image))
                    if data is not None:(output/f'{step["index"]:06}.prn').write_bytes(data)
                    simulated+=1
                else:
                    if transport is None:
                        transport=(DriverTransport if driver else Transport)(settings,'Cable Label Studio '+ident)
                        transport.__enter__()
                    if driver:transport.send_image(image,meta)
                    else:transport.send(data)
                    sent+=1
                self.update(ident,sent=sent,simulated=simulated)
                first=False
                if segment_last and transport:
                    transport.__exit__(None,None,None)
                    transport=None
                if request.mode=='confirm' and step['end_record'] and not step['last']:
                    signal=self.signals[ident]
                    signal.clear()
                    self.update(ident,state='waiting')
                    while not signal.wait(0.5):
                        if self.cancelled(ident):
                            break
                    if self.cancelled(ident):
                        self.update(ident,state='cancelled')
                        return
                    self.update(ident,state='running')
                    first=True
            self.update(ident,state='simulated' if request.simulation else 'submitted')
            self.store.audit(user['id'],'print.simulated' if request.simulation else 'print.submitted',f'{ident}:{simulated or sent}')
        except BaseException as exc:
            if transport:
                transport.__exit__(type(exc),exc,exc.__traceback__)
                transport=None
            raise
        finally:
            if transport:
                transport.__exit__(None,None,None)
