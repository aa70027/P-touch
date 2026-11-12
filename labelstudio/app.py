import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import secrets
import sys
import time
import uuid
import zipfile
from urllib.parse import urlparse
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Depends
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
from PIL import Image
from . import __version__
from .store import Store, PASSWORDS, default_data_dir
from .models import Settings, ResourceIn, Document, Label, PrintRequest, Element
from .render import render_label, png_bytes, SYSTEM_FONTS
from .formulas import apply_rules, evaluate
from .jobs import JobQueue
from .printer import status as printer_status
from .data import read_data, access_drivers

ROOT=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent.parent))


def create_app(data_dir=None):
    store=Store(Path(data_dir or default_data_dir()))
    app=FastAPI(title='Cable Label Studio',version=__version__,docs_url=None,redoc_url=None,openapi_url=None)
    app.state.store=store
    app.state.shutdown=None
    app.state.restart=None
    app.state.local_csrf=secrets.token_urlsafe(32)
    import threading
    app.state.operations=threading.RLock()
    app.state.login_attempts={}
    from .discovery import Discovery
    from .updater import Updater
    from .profiles import PROFILES,get_profile,PROJECT
    discovery=Discovery();updater=Updater(store.root)
    app.state.updater=updater
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=['127.0.0.1','localhost','[::1]','testserver'])

    @app.middleware('http')
    async def boundary(request,call_next):
        if request.method not in ('GET','HEAD','OPTIONS'):
            origin=request.headers.get('origin')
            if origin and (urlparse(origin).netloc != request.headers.get('host') or urlparse(origin).scheme not in ('http','https')):
                return JSONResponse({'error':'ORIGIN_DENIED'},403)
            if request.headers.get('x-studio-request')!='1':
                return JSONResponse({'error':'REQUEST_HEADER_REQUIRED'},403)
        response=await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Content-Security-Policy']="default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; font-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; object-src 'none'"
        if request.url.path.startswith('/api/'):
            response.headers['Cache-Control']='no-store'
        return response

    @app.exception_handler(ValueError)
    async def bad_value(request,exc):
        return JSONResponse({'error':str(exc)},422)

    @app.exception_handler(KeyError)
    async def missing(request,exc):
        return JSONResponse({'error':str(exc).strip("'")},404)

    @app.exception_handler(PermissionError)
    async def denied(request,exc):
        return JSONResponse({'error':str(exc)},403)

    @app.exception_handler(Exception)
    async def unexpected(request,exc):
        store.logger.exception('Request failed: %s',request.url.path)
        return JSONResponse({'error':'INTERNAL_ERROR_SEE_LOG'},500)

    def current_user(request:Request):
        settings=store.settings()
        if not settings.auth_enabled:
            user=store.user('local')
            csrf=app.state.local_csrf
        else:
            session=store.session(request.cookies.get('studio_session',''))
            if not session:
                raise HTTPException(401,'LOGIN_REQUIRED')
            user,csrf=session
        if request.method not in ('GET','HEAD','OPTIONS') and not secrets.compare_digest(request.headers.get('x-csrf-token',''),csrf):
            raise HTTPException(403,'CSRF_REQUIRED')
        return user

    def admin(user=Depends(current_user)):
        if user['role']!='admin':
            raise HTTPException(403,'ADMIN_ONLY')
        return user

    def assets_for(user):
        def resolve(ident,kind):
            resource=store.resource(ident,user)
            if resource['kind']!=kind:
                raise ValueError('ASSET_TYPE_MISMATCH')
            return store.root/'assets'/resource['payload']['file']
        return resolve

    jobs=JobQueue(store,assets_for)
    app.state.jobs=jobs

    def seed():
        with store.connect() as db:
            exists=db.execute('SELECT count(*) FROM resources WHERE kind="template"').fetchone()[0]
        if exists:
            return
        examples=[('DC · General','general',65,0),('Cable · Flag','cable-flag',35,0),
                  ('Cable · Wrap','cable-wrap',38,0),('Patch panel · 6 ports','patch-panel',80,0),
                  ('Faceplate · Outlet','faceplate',45,0),('Terminal · Block','terminal-block',80,0),
                  ('Flag · Die-cut layout','die-cut-flag',35,0),('Tube · Heat-shrink layout','heat-shrink',40,0)]
        for name,kind,length,_ in examples:
            element=Element(text='{Rack}-{Port}',h=6,size=12)
            if kind in ('patch-panel','terminal-block'):
                element=Element(text='{#cell}',size=9,x=1,h=6)
            label=Label(name=name,kind=kind,length=length,auto_length=kind not in ('cable-flag','die-cut-flag'),elements=[element])
            doc=Document(name=name,pages=[label],variables={'Rack':'A01','Port':'01'})
            store.save_resource(store.user('local'),'template',name,doc.model_dump(),'shared')
    seed()

    @app.get('/api/health')
    def health():
        return {'ok':True,'version':__version__}

    @app.get('/api/bootstrap')
    def bootstrap(request:Request):
        settings=store.settings()
        session=store.session(request.cookies.get('studio_session','')) if settings.auth_enabled else None
        user=session[0] if session else store.user('local') if not settings.auth_enabled else None
        return {'version':__version__,'language':settings.language,'auth_enabled':settings.auth_enabled,
                'user':store.public_user(user) if user else None,'csrf':session[1] if session else app.state.local_csrf if user else '',
                'data_dir':str(store.root) if user and user['role']=='admin' else None,
                'project_url':PROJECT,'creator':'Amir Rahimi','license':'MIT','profiles':PROFILES,'model':settings.model,'fonts':list(SYSTEM_FONTS),'default_width':settings.default_width,'default_quality':settings.default_quality}

    class Login(BaseModel):
        username:str=Field(max_length=200)
        password:str=Field(max_length=1024)

    @app.post('/api/login')
    def login(body:Login,request:Request):
        key=request.client.host if request.client else 'local'
        attempts=[t for t in app.state.login_attempts.get(key,[]) if t>time.time()-60]
        if len(attempts)>=10:
            raise HTTPException(429,'LOGIN_RATE_LIMIT')
        result=store.login(body.username,body.password)
        if not result:
            app.state.login_attempts[key]=attempts+[time.time()]
            raise HTTPException(401,'INVALID_CREDENTIALS')
        app.state.login_attempts.pop(key,None)
        token,csrf,user=result
        response=JSONResponse({'user':user,'csrf':csrf})
        response.set_cookie('studio_session',token,httponly=True,samesite='strict',max_age=43200)
        store.audit(user['id'],'login')
        return response

    @app.post('/api/logout')
    def logout(request:Request,user=Depends(current_user)):
        with store.connect() as db:
            db.execute('DELETE FROM sessions WHERE token=?',(hashlib.sha256(request.cookies.get('studio_session','').encode()).hexdigest(),))
        response=JSONResponse({'ok':True})
        response.delete_cookie('studio_session')
        return response

    @app.get('/api/settings')
    def settings(user=Depends(admin)):
        return store.settings().model_dump()

    @app.put('/api/settings')
    def update_settings(value:Settings,user=Depends(admin)):
        old=store.settings()
        if value.auth_enabled:
            with store.connect() as db:
                count=db.execute("SELECT count(*) FROM users WHERE role='admin' AND disabled=0 AND password IS NOT NULL").fetchone()[0]
            if not count:
                raise ValueError('ADMIN_PASSWORD_REQUIRED')
        if value.auto_start!=old.auto_start:
            from .system import set_auto_start
            set_auto_start(value.auto_start,store.root)
        if value.auth_enabled!=old.auth_enabled:
            with store.connect() as db:
                db.execute('DELETE FROM sessions')
        store.save_settings(value)
        store.audit(user['id'],'settings.save')
        return {'settings':value.model_dump(),'restart_required':value.port!=old.port,'reauthenticate':value.auth_enabled!=old.auth_enabled}

    @app.get('/api/printer/status')
    def device(user=Depends(current_user)):
        return printer_status(store.settings())

    @app.get('/api/diagnostics')
    def diagnostics(user=Depends(admin)):
        from PIL import features
        from .discovery import usb_devices,interfaces
        return {'usb_devices':usb_devices(),'interfaces':interfaces(),'profiles':PROFILES,'access_drivers':access_drivers(),'shaping':'RAQM' if features.check_feature('raqm') else 'Arabic reshaper + Unicode bidi',
                'data_dir':str(store.root),'printer':printer_status(store.settings()),'platform':sys.platform,
                'driver_url':get_profile(store.settings().model)['download_url'],
                'access_url':'https://www.microsoft.com/en-us/download/details.aspx?id=54920'}

    @app.get('/api/resources')
    def resources(kind:str|None=None,user=Depends(current_user)):
        return store.resources(user,kind)

    @app.post('/api/resources')
    def create_resource(value:ResourceIn,user=Depends(current_user)):
        payload=value.payload
        if value.kind in ('document','template'):
            payload=Document.model_validate(payload).model_dump()
        return store.save_resource(user,value.kind,value.name,payload,value.scope)

    @app.put('/api/resources/{ident}')
    def update_resource(ident:str,value:ResourceIn,user=Depends(current_user)):
        old=store.resource(ident,user)
        if old['kind']!=value.kind:
            raise ValueError('RESOURCE_TYPE_MISMATCH')
        payload=Document.model_validate(value.payload).model_dump() if value.kind in ('template','document') else value.payload
        return store.save_resource(user,value.kind,value.name,payload,value.scope,ident)

    @app.delete('/api/resources/{ident}')
    def remove_resource(ident:str,user=Depends(current_user)):
        item=store.resource(ident,user)
        if item['owner']!=user['id']:
            raise PermissionError('OWNER_ONLY')
        # Keep uploaded blobs for historical print snapshots; deletion revokes discovery/access.
        with store.connect() as db:
            db.execute('DELETE FROM resources WHERE id=?',(ident,))
        store.audit(user['id'],'resource.delete',ident)
        return {'ok':True}

    @app.patch('/api/resources/{ident}/scope')
    def scope(ident:str,value:dict,user=Depends(current_user)):
        item=store.resource(ident,user)
        if value.get('scope') not in ('private','shared','inherit'):
            raise ValueError('INVALID_SCOPE')
        return store.save_resource(user,item['kind'],item['name'],item['payload'],value['scope'],ident)

    @app.post('/api/upload')
    async def upload(file:UploadFile=File(...),kind:str='image',scope:str='inherit',user=Depends(current_user)):
        allowed={'image':{'.png','.jpg','.jpeg','.bmp','.webp'},'font':{'.ttf','.otf'},
                 'source':{'.xlsx','.xlsm','.xls','.csv','.tsv','.mdb','.accdb'}}
        ext=Path(file.filename or '').suffix.lower()
        if kind not in allowed or ext not in allowed[kind] or scope not in ('private','shared','inherit'):
            raise ValueError('UNSUPPORTED_UPLOAD')
        filename=uuid.uuid4().hex+ext
        path=store.root/'assets'/filename
        total=0
        try:
            with path.open('wb') as output:
                while chunk:=await file.read(1024*1024):
                    total+=len(chunk)
                    if total>50*1024*1024:
                        raise ValueError('UPLOAD_LIMIT_50_MB')
                    output.write(chunk)
            extra={}
            if kind=='image':
                Image.MAX_IMAGE_PIXELS=20_000_000
                with Image.open(path) as image:
                    image.verify()
            if kind=='font':
                from fontTools.ttLib import TTFont
                with TTFont(path) as font:
                    extra['family']=font['name'].getDebugName(1) or Path(file.filename).stem
            return store.save_resource(user,kind,Path(file.filename).name,{'file':filename,'size':total,**extra},scope)
        except Exception:
            path.unlink(missing_ok=True)
            raise

    @app.get('/api/assets/{ident}')
    def get_asset(ident:str,user=Depends(current_user)):
        item=store.resource(ident,user)
        if item['kind'] not in ('image','font','source'):
            raise KeyError('ASSET_NOT_FOUND')
        if item['payload'].get('linked_path'):raise ValueError('LINKED_SOURCE_USE_DATA_READ')
        path=store.root/'assets'/item['payload']['file']
        media='font/ttf' if item['kind']=='font' else None
        return FileResponse(path,media_type=media,filename=item['name'],content_disposition_type='inline' if item['kind'] in ('image','font') else 'attachment')

    class DataRead(BaseModel):
        source:str
        sheet:str|None=None
        sheets:list[str]|None=None
        encoding:str='utf-8-sig'
        delimiter:str|None=None

    def source_data(source,user,sheet=None,sheets=None,encoding='utf-8-sig',delimiter=None):
        item=store.resource(source,user)
        if item['kind']!='source':raise ValueError('INVALID_SOURCE')
        path=Path(item['payload']['linked_path']) if item['payload'].get('linked_path') else store.root/'assets'/item['payload']['file']
        return read_data(path,sheet,encoding,delimiter,sheets)

    @app.post('/api/data/pick')
    def pick_source(value:dict,user=Depends(current_user)):
        from .native import pick_file
        selected=pick_file()
        if not selected:return {'cancelled':True}
        path=Path(selected).resolve()
        if path.suffix.lower() not in ('.xlsx','.xlsm','.xls','.csv','.tsv'):raise ValueError('UNSUPPORTED_DATA_FORMAT')
        # Only an actual native dialog result can create a source; no arbitrary path API.
        read_data(path)
        ident=value.get('replace')
        if ident:
            old=store.resource(ident,user)
            if old['owner']!=user['id'] or old['kind']!='source':raise PermissionError('OWNER_ONLY')
        return store.save_resource(user,'source',path.name,{'linked_path':str(path),'size':path.stat().st_size,'live':True},'private',ident)

    @app.post('/api/data/read')
    def data_read(value:DataRead,user=Depends(current_user)):
        item=store.resource(value.source,user)
        if item['kind']!='source':
            raise ValueError('INVALID_SOURCE')
        return source_data(value.source,user,value.sheet,value.sheets,value.encoding,value.delimiter)

    @app.post('/api/formula')
    def formula(value:dict,user=Depends(current_user)):
        return {'value':evaluate(str(value.get('expression','')),value.get('row',{}))}

    class Preview(BaseModel):
        document:Document
        row:dict=Field(default_factory=dict)
        page:int=Field(0,ge=0)
        source:str|None=None
        sheets:list[str]|None=None
        record_index:int=Field(0,ge=0)
        encoding:str='utf-8-sig'
        delimiter:str|None=None

    @app.post('/api/preview')
    def preview(value:Preview,user=Depends(current_user)):
        if value.page>=len(value.document.pages):
            raise ValueError('PAGE_NOT_FOUND')
        if value.source:
            records=source_data(value.source,user,sheets=value.sheets,encoding=value.encoding,delimiter=value.delimiter)['records']
            if value.record_index>=len(records):raise ValueError('SOURCE_RECORD_NO_LONGER_EXISTS')
            value.row=records[value.record_index]
        row=apply_rules(value.row,value.document.rules,value.document.variables)
        image,meta=render_label(value.document.pages[value.page],row,assets_for(user))
        return {'image':'data:image/png;base64,'+base64.b64encode(png_bytes(image)).decode(),**meta,'row':row,'source_row':value.row}

    @app.post('/api/export/png')
    def export_png(value:Preview,user=Depends(current_user)):
        if value.page>=len(value.document.pages):
            raise ValueError('PAGE_NOT_FOUND')
        if value.source:
            records=source_data(value.source,user,sheets=value.sheets,encoding=value.encoding,delimiter=value.delimiter)['records']
            if value.record_index>=len(records):raise ValueError('SOURCE_RECORD_NO_LONGER_EXISTS')
            value.row=records[value.record_index]
        row=apply_rules(value.row,value.document.rules,value.document.variables)
        image,meta=render_label(value.document.pages[value.page],row,assets_for(user))
        return Response(png_bytes(image),media_type='image/png',headers={'Content-Disposition':'attachment; filename="label.png"'})

    @app.post('/api/jobs')
    def print_job(value:PrintRequest,user=Depends(current_user)):
        with app.state.operations:
            if updater.busy or updater.snapshot().get('state')=='installing':raise ValueError('UPDATE_IN_PROGRESS')
            settings=store.settings()
            if value.source:
                data=source_data(value.source,user,sheets=value.sheets,encoding=value.encoding,delimiter=value.delimiter)
                value.records=data['records'][value.record_from:value.record_to]
                if not value.records:raise ValueError('NO_RECORDS')
            from .profiles import get_profile
            profile=get_profile(settings.model)
            if any(page.model!=settings.model for doc in value.documents for page in doc.pages) and not value.simulation:
                raise ValueError('DESIGN_MODEL_DIFFERS_FROM_PRINTER')
            if not value.simulation:
                if settings.connection=='wifi' and profile['transport']=='raster':
                    from .discovery import resolve
                    settings=resolve(settings)
                    if settings.ip!=store.settings().ip:store.save_settings(settings)
                device=printer_status(settings)
                if settings.connection=='usb' and not any(p['name']==settings.printer and p['supported'] for p in device['printers']):
                    raise ValueError('SELECT_SUPPORTED_PRINTER')
                if device['state'] in ('offline','error'):
                    raise ValueError(device['detail'])
                if settings.connection=='wifi' and profile['transport']=='raster' and not settings.ip:
                    raise ValueError('SET_PRINTER_IP')
                if any(p.kind=='heat-shrink' for d in value.documents for p in d.pages):
                    raise ValueError('HSE_PHYSICAL_MEDIA_REQUIRES_VALIDATED_PROFILE')
            if not value.simulation and profile['transport']=='raster':
                if any(getattr(settings,key) not in profile['cuts'] for key in ('cut_between_pages','cut_end_record','cut_between_files','cut_end_file')):
                    raise ValueError('UNSUPPORTED_CUT_FOR_MODEL')
            ident=jobs.create(user,value,settings)
            return {'id':ident}

    def job_for(ident,user):
        with store.connect() as db:
            row=db.execute('SELECT * FROM jobs WHERE id=?',(ident,)).fetchone()
        if not row or (row['owner']!=user['id'] and user['role']!='admin'):
            raise KeyError('JOB_NOT_FOUND')
        return dict(row)

    @app.get('/api/jobs')
    def list_jobs(user=Depends(current_user)):
        with store.connect() as db:
            rows=db.execute('SELECT id,owner,state,total,sent,confirmed,simulated,error,created,updated FROM jobs '+
                            ('' if user['role']=='admin' else 'WHERE owner=? ')+'ORDER BY created DESC LIMIT 500',() if user['role']=='admin' else (user['id'],)).fetchall()
        return [dict(row) for row in rows]

    @app.get('/api/jobs/{ident}')
    def job_detail(ident:str,user=Depends(current_user)):
        row=job_for(ident,user)
        payload=json.loads(row['payload'])
        # Administrators may supervise the queue and aggregate usage without
        # reading another user's private labels or imported records.
        row['payload']=payload if row['owner']==user['id'] else {'settings':payload['settings'],'request':None,'redacted':True}
        return row

    @app.post('/api/jobs/{ident}/{action}')
    def job_action(ident:str,action:str,user=Depends(current_user)):
        row=job_for(ident,user)
        if row['state'] not in ('queued','running','waiting'):
            raise ValueError('JOB_NOT_ACTIVE')
        if action not in ('next','cancel'):
            raise ValueError('UNKNOWN_JOB_ACTION')
        if action=='next' and row['state']!='waiting':
            raise ValueError('JOB_NOT_WAITING')
        jobs.signal(ident,action=='cancel')
        return {'ok':True}

    @app.get('/api/jobs/{ident}/artifacts/{number}/{ext}')
    def job_artifact(ident:str,number:int,ext:str,user=Depends(current_user)):
        row=job_for(ident,user)
        if row['owner']!=user['id']:
            raise PermissionError('OWNER_ONLY')
        if ext not in ('png','prn') or not 1<=number<=row['total']:
            raise KeyError('ARTIFACT_NOT_FOUND')
        path=store.root/'jobs'/ident/f'{number:06}.{ext}'
        if not path.is_file():
            raise KeyError('ARTIFACT_NOT_FOUND')
        return FileResponse(path,media_type='image/png' if ext=='png' else 'application/octet-stream',filename=path.name)

    class UserIn(BaseModel):
        username:str=Field(min_length=1,max_length=200)
        password:str=Field('',max_length=1024)
        role:str='user'
        share:dict[str,bool]=Field(default_factory=dict)
        disabled:bool=False

    def set_user(ident,value,actor):
        old=store.user(ident) if ident else None
        if value.role not in ('user','admin'):
            raise ValueError('INVALID_ROLE')
        if ident=='local' and (value.role!='admin' or value.disabled):
            raise ValueError('BUILTIN_ADMIN_REQUIRED')
        if not old and len(value.password)<8:
            raise ValueError('PASSWORD_MIN_8')
        if value.password and len(value.password)<8:
            raise ValueError('PASSWORD_MIN_8')
        if old and old['id']==actor['id'] and (value.disabled or value.role!='admin' and actor['role']=='admin'):
            raise ValueError('CANNOT_DISABLE_CURRENT_ADMIN')
        with store.connect() as db:
            if old and old['role']=='admin' and (value.disabled or value.role!='admin'):
                remaining=db.execute("SELECT count(*) FROM users WHERE role='admin' AND disabled=0 AND password IS NOT NULL AND id!=?",(ident,)).fetchone()[0]
                if not remaining:
                    raise ValueError('LAST_ADMIN_REQUIRED')
            if db.execute('SELECT id FROM users WHERE username=? AND id!=?',(value.username,ident or '')).fetchone():
                raise ValueError('USERNAME_EXISTS')
            password=PASSWORDS.hash(value.password) if value.password else old['password'] if old else None
            ident=ident or uuid.uuid4().hex
            db.execute('INSERT INTO users VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET username=excluded.username,password=excluded.password,role=excluded.role,share=excluded.share,disabled=excluded.disabled',
                       (ident,value.username,password,value.role,json.dumps(value.share),int(value.disabled),time.time()))
            if value.password or value.disabled:
                db.execute('DELETE FROM sessions WHERE user_id=?',(ident,))
        store.audit(actor['id'],'user.save',ident)
        return store.public_user(store.user(ident))

    @app.get('/api/users')
    def users(user=Depends(admin)):
        with store.connect() as db:
            return [store.public_user(dict(r)) for r in db.execute('SELECT * FROM users ORDER BY created')]

    @app.post('/api/users')
    def new_user(value:UserIn,user=Depends(admin)):
        return set_user(None,value,user)

    @app.put('/api/users/{ident}')
    def edit_user(ident:str,value:UserIn,user=Depends(admin)):
        if not store.user(ident):
            raise KeyError('USER_NOT_FOUND')
        return set_user(ident,value,user)

    @app.put('/api/profile')
    def profile(value:UserIn,user=Depends(current_user)):
        value.role=user['role']
        value.disabled=False
        return set_user(user['id'],value,user)

    @app.get('/api/reports')
    def reports(start:float=0,end:float=99999999999,user=Depends(current_user)):
        with store.connect() as db:
            rows=db.execute('''SELECT u.id,u.username,count(j.id) jobs,coalesce(sum(j.sent),0) sent,
                coalesce(sum(j.confirmed),0) confirmed,coalesce(sum(j.simulated),0) simulated,
                coalesce(sum(case when j.state='failed' then 1 else 0 end),0) failed,
                coalesce(sum(case when j.state='cancelled' then 1 else 0 end),0) cancelled,
                coalesce(sum(case when j.state='interrupted' then 1 else 0 end),0) interrupted,
                coalesce(sum(j.total),0) requested FROM users u LEFT JOIN jobs j ON j.owner=u.id AND j.created BETWEEN ? AND ?
                WHERE (?='admin' OR u.id=?) GROUP BY u.id ORDER BY sent DESC''',(start,end,user['role'],user['id'])).fetchall()
        return [dict(r) for r in rows]

    @app.get('/api/logs')
    def logs(user=Depends(admin)):
        cutoff=time.time()-store.settings().log_retention_days*86400
        with store.connect() as db:
            db.execute('DELETE FROM audit WHERE time<?',(cutoff,))
            rows=db.execute('SELECT a.*,u.username FROM audit a LEFT JOIN users u ON u.id=a.user_id ORDER BY a.id DESC LIMIT 1000').fetchall()
        path=store.root/'logs'/'application.log'
        with path.open('rb') as source:
            source.seek(max(0,path.stat().st_size-100000))
            tail=source.read().decode('utf-8',errors='replace')
        return {'audit':[dict(r) for r in rows],'application':tail}

    @app.post('/api/backup')
    def backup(user=Depends(admin)):
        name=store.backup()
        target=store.root/'backups'/(name+'.zip')
        with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
            archive.write(store.root/'backups'/name,'studio.sqlite3')
            for file in (store.root/'assets').iterdir():
                if file.is_file():
                    archive.write(file,'assets/'+file.name)
            archive.writestr('version.txt',__version__)
        store.audit(user['id'],'backup',target.name)
        return FileResponse(target,filename=target.name,media_type='application/zip')

    @app.post('/api/restart')
    def restart(user=Depends(admin)):
        with store.connect() as db:
            active=db.execute("SELECT count(*) FROM jobs WHERE state IN ('queued','running','waiting')").fetchone()[0]
        if active:
            raise ValueError('ACTIVE_PRINT_JOBS')
        if app.state.restart:
            app.state.restart()
        return {'ok':True,'url':f'http://127.0.0.1:{store.settings().port}'}

    @app.post('/api/shutdown')
    def shutdown(user=Depends(admin)):
        with store.connect() as db:
            active=db.execute("SELECT count(*) FROM jobs WHERE state IN ('queued','running','waiting')").fetchone()[0]
        if active:
            raise ValueError('ACTIVE_PRINT_JOBS')
        if app.state.shutdown:
            app.state.shutdown()
        return {'ok':True}

    @app.get('/api/printer/discovery')
    def discovery_status(user=Depends(admin)):
        return discovery.snapshot()

    @app.post('/api/printer/discovery')
    def discover(value:dict,user=Depends(admin)):
        settings=store.settings()
        return discovery.start(str(value.get('subnet') or settings.discovery_subnet),str(value.get('mac') or ''),settings.printer_port)

    @app.post('/api/printer/identify')
    def identify(value:dict,user=Depends(admin)):
        from .discovery import resolve,probe,usb_devices
        settings=store.settings()
        if settings.connection=='usb':return {'usb_devices':usb_devices(),'printer':printer_status(settings)}
        settings=resolve(settings)
        if not settings.ip:raise ValueError('SET_PRINTER_IP')
        info=probe(settings.ip,port=settings.printer_port)
        if settings.ip!=store.settings().ip:store.save_settings(settings)
        return info

    @app.post('/api/printer/preferences')
    def printer_preferences(value:dict,user=Depends(admin)):
        from .native import driver_preferences
        settings=store.settings()
        if not settings.printer:raise ValueError('SELECT_PRINTER')
        driver_preferences(settings.printer);return {'ok':True}

    @app.post('/api/printer/wifi-settings')
    def wifi_settings(value:dict,user=Depends(admin)):
        from .native import windows_settings
        windows_settings();return {'ok':True}

    def active_jobs():
        with store.connect() as db:
            return db.execute("SELECT count(*) FROM jobs WHERE state IN ('queued','running','waiting')").fetchone()[0]

    @app.get('/api/updates')
    def update_state(user=Depends(admin)):
        return updater.snapshot()

    @app.post('/api/updates/{action}')
    def update_action(action:str,value:dict,user=Depends(admin)):
        if action=='check':return updater.check(store.settings().update_prerelease)
        if action=='install':
            with app.state.operations:
                if active_jobs():raise ValueError('ACTIVE_PRINT_JOBS')
                store.audit(user['id'],'update.request')
                return updater.install(store.settings().update_prerelease,store.backup,active_jobs)
        if action=='software':return updater.software(str(value.get('url','')))
        raise ValueError('UNKNOWN_UPDATE_ACTION')

    @app.get('/api/software/download')
    def software_download(user=Depends(admin)):
        name=updater.snapshot().get('software_file')
        if not name:raise KeyError('SOFTWARE_NOT_READY')
        return FileResponse(updater.root/Path(name).name,filename=Path(name).name)

    app.mount('/static' ,StaticFiles(directory=ROOT/'web'),name='static')

    @app.get('/')
    def index():
        return FileResponse(ROOT/'web'/'index.html')

    return app
