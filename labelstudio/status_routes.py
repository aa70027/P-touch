"""Authenticated status management for the user's linked, original Excel file."""
import json
from pathlib import Path
import time
import uuid

from fastapi import Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel,Field

from .excel_status import apply_status,inspect_status,status_options


class StatusSelection(BaseModel):
    sheets:list[str]=Field(min_length=1,max_length=100)
    key_column:str=Field(min_length=1,max_length=200)
    status_column:str=Field(min_length=1,max_length=200)


class StatusEdit(BaseModel):
    sheet:str=Field(min_length=1,max_length=200)
    key:str=Field(min_length=1,max_length=8000)
    expected_status:str=Field(max_length=32767)
    status:str=Field(max_length=100)


class StatusApply(StatusSelection):
    fingerprint:str=Field(pattern=r'^[a-f0-9]{64}$')
    updates:list[StatusEdit]=Field(min_length=1,max_length=10000)


def register_status_routes(app,store,current_user):
    with store.connect() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS excel_status_events(
            id TEXT PRIMARY KEY,source TEXT NOT NULL,owner TEXT NOT NULL,created REAL NOT NULL,
            changed INTEGER NOT NULL,backup TEXT,before_hash TEXT NOT NULL,after_hash TEXT NOT NULL,
            changes TEXT NOT NULL)''')

    def original(ident,user):
        source=store.resource(ident,user)
        if source['owner']!=user['id']:raise PermissionError('OWNER_ONLY')
        if source['kind']!='source':raise ValueError('INVALID_SOURCE')
        if not source['payload'].get('linked_path'):raise ValueError('STATUS_REQUIRES_ORIGINAL_LINKED_EXCEL')
        return source,Path(source['payload']['linked_path'])

    @app.get('/api/sources/{ident}/status/options')
    def options(ident:str,user=Depends(current_user)):
        source,path=original(ident,user)
        result=status_options(path)
        return result|{'config':source['payload'].get('status_sync'),
                       'device':{'state':'unknown','readback_supported':False,'reason':'E550W_DATABASE_READBACK_NOT_VERIFIED'}}

    @app.post('/api/sources/{ident}/status/inspect')
    def inspect(ident:str,selection:StatusSelection,user=Depends(current_user)):
        source,path=original(ident,user)
        result=inspect_status(path,**selection.model_dump())
        # Only preferences persist here; reading never changes the original file.
        payload=source['payload']|{'status_sync':selection.model_dump()}
        store.save_resource(user,'source',source['name'],payload,source['scope'],ident)
        return result

    @app.post('/api/sources/{ident}/status/apply')
    def apply(ident:str,selection:StatusApply,user=Depends(current_user)):
        with app.state.operations:
            source,path=original(ident,user)
            result=apply_status(path,**selection.model_dump(),backup_dir=store.root/'backups')
            event=None
            if result['changed']:
                event=uuid.uuid4().hex
                with store.connect() as db:
                    db.execute('INSERT INTO excel_status_events VALUES(?,?,?,?,?,?,?,?,?)',
                               (event,ident,user['id'],time.time(),result['changed'],result['backup'],selection.fingerprint,
                                result['fingerprint'],json.dumps(result['changes'],ensure_ascii=False)))
                store.audit(user['id'],'excel.status.manual',f'{ident}:{result["changed"]}')
            return result|{'event':event,'device':{'state':'pending_transfer','readback_supported':False}}

    @app.get('/api/sources/{ident}/status/history')
    def history(ident:str,user=Depends(current_user)):
        original(ident,user)
        with store.connect() as db:
            rows=db.execute('SELECT id,created,changed,backup FROM excel_status_events WHERE source=? AND owner=? ORDER BY created DESC LIMIT 100',
                            (ident,user['id'])).fetchall()
        return [dict(row)|{'backup_url':f'/api/status/backups/{row["id"]}' if row['backup'] else None} for row in rows]

    @app.get('/api/status/backups/{event}')
    def backup(event:str,user=Depends(current_user)):
        with store.connect() as db:
            row=db.execute('SELECT * FROM excel_status_events WHERE id=? AND owner=?',(event,user['id'])).fetchone()
        if not row:raise KeyError('STATUS_BACKUP_NOT_FOUND')
        name=row['backup']
        if not name or Path(name).name!=name:raise KeyError('STATUS_BACKUP_NOT_FOUND')
        return FileResponse(store.root/'backups'/name,filename=name)
