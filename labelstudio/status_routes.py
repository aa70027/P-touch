"""Authenticated status management for the user's linked, original Excel file."""
import json
import csv
import hashlib
import io
import os
from pathlib import Path
import time
import uuid

from fastapi import Depends,UploadFile,File
from fastapi.responses import FileResponse,Response
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

    def binding(path):return hashlib.sha256(os.path.normcase(str(path.resolve())).encode('utf-8')).hexdigest()

    def owned_resource(ident,kind,user):
        resource=store.resource(ident,user)
        if resource['owner']!=user['id'] or resource['kind']!=kind:raise PermissionError('OWNER_ONLY')
        return resource

    @app.post('/api/sources/{ident}/status/export')
    def export_status(ident:str,selection:StatusSelection,user=Depends(current_user)):
        source,path=original(ident,user)
        snapshot=inspect_status(path,**selection.model_dump())
        if len(snapshot['records'])>65000:raise ValueError('STATUS_EXPORT_MAX_65000')
        exported=store.save_resource(user,'status_exchange',source['name'],{'source':ident,'binding':binding(path),
                       'selection':selection.model_dump(),'snapshot':snapshot},'private')
        return {'id':exported['id'],'rows':len(snapshot['records']),'download_url':'/api/status/exchanges/'+exported['id']+'/download',
                'device_state':'not_transferred'}

    @app.get('/api/status/exchanges/{exchange}/download')
    def exchange_file(exchange:str,user=Depends(current_user)):
        resource=owned_resource(exchange,'status_exchange',user)
        output=io.StringIO(newline='');writer=csv.writer(output)
        writer.writerow(['ExchangeID','Sheet','RecordID','PrintStatus'])
        for row in resource['payload']['snapshot']['records']:writer.writerow([exchange,row['sheet'],row['key'],row['status']])
        return Response(('\ufeff'+output.getvalue()).encode('utf-8'),media_type='text/csv',
                        headers={'Content-Disposition':'attachment; filename="print-status.csv"'})

    @app.post('/api/sources/{ident}/status/import-preview')
    def import_preview(ident:str,file:UploadFile=File(...),user=Depends(current_user)):
        source,path=original(ident,user)
        if not file.filename or not file.filename.lower().endswith('.csv'):raise ValueError('STATUS_IMPORT_READABLE_CSV_ONLY')
        raw=file.file.read(10*1024*1024+1)
        if len(raw)>10*1024*1024:raise ValueError('STATUS_IMPORT_MAX_10MB')
        try:reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig'),newline=''))
        except UnicodeDecodeError:raise ValueError('STATUS_CSV_UTF8_REQUIRED')
        try:
            headers=reader.fieldnames or []
            if len(headers)!=4 or set(headers)!={'ExchangeID','Sheet','RecordID','PrintStatus'}:raise ValueError('STATUS_IMPORT_HEADERS_INVALID')
            incoming=[];seen=set();exchange=None
            for row in reader:
                if None in row or any(v is None for v in row.values()):raise ValueError('STATUS_IMPORT_HEADERS_INVALID')
                if not row['ExchangeID'] or exchange is not None and row['ExchangeID']!=exchange:raise ValueError('STATUS_EXCHANGE_ID_MISMATCH')
                exchange=row['ExchangeID'];identity=(row['Sheet'],row['RecordID'])
                if identity in seen:raise ValueError('STATUS_DUPLICATE_UPDATE')
                if not row['RecordID'] or len(row['RecordID'])>8000 or len(row['PrintStatus'])>100:raise ValueError('STATUS_VALUE_INVALID')
                if any(ord(c)<32 and c not in '\n\t\r' for c in row['PrintStatus']):raise ValueError('STATUS_VALUE_INVALID')
                seen.add(identity);incoming.append(row)
                if len(incoming)>65000:raise ValueError('STATUS_EXPORT_MAX_65000')
        except csv.Error:raise ValueError('STATUS_IMPORT_HEADERS_INVALID')
        if not incoming:raise ValueError('NO_RECORDS')
        exported=owned_resource(exchange,'status_exchange',user)['payload']
        if exported['source']!=ident or exported['binding']!=binding(path):raise ValueError('STATUS_SOURCE_RELINKED')
        selection=exported['selection'];current=inspect_status(path,**selection)
        baseline={(r['sheet'],r['key']):r for r in exported['snapshot']['records']}
        latest={(r['sheet'],r['key']):r for r in current['records']}
        updates=[];conflicts=[];unchanged=0
        for row in incoming:
            identity=(row['Sheet'],row['RecordID']);before=baseline.get(identity);now=latest.get(identity);after=row['PrintStatus'];reason=None
            if before is None:reason='unknown_export_row'
            elif now is None:reason='row_removed'
            elif after==before['status'] or after==now['status']:unchanged+=1;continue
            elif now['data_fingerprint']!=before['data_fingerprint']:reason='row_data_changed'
            elif now['status']!=before['status']:reason='both_changed'
            if reason:conflicts.append(dict(sheet=identity[0],key=identity[1],reason=reason,baseline=before['status'] if before else None,current=now['status'] if now else None,incoming=after))
            else:updates.append(dict(sheet=identity[0],key=identity[1],expected_status=now['status'],status=after))
        if len(updates)>10000:raise ValueError('STATUS_SELECT_1_TO_10000_ROWS')
        plan=store.save_resource(user,'status_import',source['name'],dict(source=ident,exchange=exchange,selection=selection,
                    fingerprint=current['fingerprint'],updates=updates,conflicts=conflicts,unchanged=unchanged,state='review',
                    input_sha256=hashlib.sha256(raw).hexdigest()),'private')
        return {'id':plan['id'],'selection':selection,'updates':updates,'conflicts':conflicts,'unchanged':unchanged,
                'device_state':'unverified_csv','automatic_device_readback':False}

    @app.post('/api/status/imports/{plan}/apply')
    def apply_import(plan:str,user=Depends(current_user)):
        with app.state.operations:
            resource=owned_resource(plan,'status_import',user);payload=resource['payload']
            original(payload['source'],user)
            if payload['state']=='applied':return payload['result']
            if payload['conflicts']:raise ValueError('STATUS_IMPORT_HAS_CONFLICTS')
            if payload['updates']:
                result=apply(payload['source'],StatusApply(**payload['selection'],fingerprint=payload['fingerprint'],updates=payload['updates']),user)
            else:result={'changed':0,'event':None,'device':{'state':'unknown','readback_supported':False}}
            payload=payload|{'state':'applied','result':result}
            store.save_resource(user,'status_import',resource['name'],payload,'private',plan)
            store.audit(user['id'],'excel.status.import_csv',plan)
            return result

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
