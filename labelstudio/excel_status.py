"""Status writeback to the original workbook, independent of printer acknowledgements.

Only explicit status-cell edits are made. Opaque workbook parts (including VBA,
drawings and external links) are retained, rather than round-tripped through a
spreadsheet renderer. Device database retrieval is a separate capability.
"""
import contextlib
from functools import wraps
import hashlib
import io
import os
from pathlib import Path
import posixpath
import tempfile
import uuid
import zipfile
from xml.dom import minidom
from xml.parsers.expat import ExpatError

NS='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
REL='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
MAX_FILE=100*1024*1024


def workbook_errors(function):
    @wraps(function)
    def run(*args,**kwargs):
        try:return function(*args,**kwargs)
        except FileNotFoundError as exc:raise ValueError('SOURCE_FILE_NOT_FOUND') from exc
        except PermissionError as exc:
            if str(exc)=='SOURCE_FILE_LOCKED_OR_DENIED':raise
            raise PermissionError('SOURCE_FILE_LOCKED_OR_DENIED') from exc
        except (zipfile.BadZipFile,ExpatError,KeyError) as exc:raise ValueError('WORKBOOK_INVALID') from exc
    return run


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def nodes(parent,name):
    return [child for child in parent.childNodes if child.nodeType==child.ELEMENT_NODE and child.localName==name]


def text(parent):
    return ''.join(child.data for child in parent.childNodes if child.nodeType in (child.TEXT_NODE,child.CDATA_SECTION_NODE))


def xml(raw):
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():raise ValueError('WORKBOOK_XML_UNSUPPORTED')
    return minidom.parseString(raw)


def load(raw):
    archive=zipfile.ZipFile(io.BytesIO(raw))
    entries=archive.infolist()
    if len(entries)>10000 or sum(item.file_size for item in entries)>500*1024*1024:
        archive.close();raise ValueError('WORKBOOK_TOO_LARGE')
    if len({item.filename for item in entries})!=len(entries):
        archive.close();raise ValueError('WORKBOOK_DUPLICATE_PARTS')
    if any(item.filename.startswith('_xmlsignatures/') for item in entries):
        archive.close();raise ValueError('SIGNED_WORKBOOK_NOT_WRITABLE')
    workbook=xml(archive.read('xl/workbook.xml'))
    relationships=xml(archive.read('xl/_rels/workbook.xml.rels'))
    targets={n.getAttribute('Id'):n.getAttribute('Target') for n in relationships.documentElement.childNodes
             if n.nodeType==n.ELEMENT_NODE and n.localName=='Relationship' and n.getAttribute('TargetMode')!='External'}
    sheets={}
    for sheet in workbook.getElementsByTagNameNS(NS,'sheet'):
        target=targets.get(sheet.getAttributeNS(REL,'id'),'')
        if not target:raise ValueError('WORKBOOK_SHEET_RELATIONSHIP_MISSING')
        target=posixpath.normpath(target.lstrip('/') if target.startswith('/') else 'xl/'+target)
        if not target.startswith('xl/') or target not in archive.namelist():raise ValueError('WORKBOOK_SHEET_RELATIONSHIP_INVALID')
        sheets[sheet.getAttribute('name')]=target
    strings=[]
    if 'xl/sharedStrings.xml' in archive.namelist():
        shared=xml(archive.read('xl/sharedStrings.xml'))
        strings=[''.join(text(n) for n in si.getElementsByTagNameNS(NS,'t')) for si in shared.getElementsByTagNameNS(NS,'si')]
    return archive,workbook,sheets,strings


def value(cell,strings):
    kind=cell.getAttribute('t')
    if kind=='inlineStr':return ''.join(text(n) for n in cell.getElementsByTagNameNS(NS,'t'))
    values=nodes(cell,'v');result=text(values[0]) if values else ''
    if kind=='s':
        try:return strings[int(result)]
        except (ValueError,IndexError):raise ValueError('WORKBOOK_SHARED_STRING_INVALID')
    return result


def column(reference):
    name=''.join(c for c in reference if c.isalpha())
    if not name or len(name)>3:raise ValueError('WORKBOOK_CELL_REFERENCE_INVALID')
    return name


def sheet_rows(document,strings,key_column,status_column,sheet):
    sections=document.getElementsByTagNameNS(NS,'sheetData')
    if len(sections)!=1:raise ValueError('WORKBOOK_SHEET_DATA_INVALID')
    rows=nodes(sections[0],'row');header=next((r for r in rows if r.getAttribute('r')=='1'),None)
    if header is None:raise ValueError('STATUS_HEADER_ROW_MISSING')
    names={}
    for cell in nodes(header,'c'):
        name=value(cell,strings).strip()
        if not name:continue
        if name in names:raise ValueError('STATUS_DUPLICATE_HEADERS')
        names[name]=column(cell.getAttribute('r'))
    if key_column not in names:raise ValueError('STATUS_KEY_COLUMN_MISSING')
    if status_column not in names:raise ValueError('STATUS_COLUMN_MISSING')
    if key_column==status_column:raise ValueError('STATUS_KEY_AND_VALUE_COLUMNS_MUST_DIFFER')
    keys=set();records=[]
    for row in rows:
        if row is header:continue
        cells={column(c.getAttribute('r')):c for c in nodes(row,'c')}
        if not any(value(c,strings)!='' or nodes(c,'f') for c in cells.values()):continue
        key_cell=cells.get(names[key_column]);status_cell=cells.get(names[status_column])
        if key_cell is not None and nodes(key_cell,'f'):raise ValueError('STATUS_ROW_KEY_MUST_NOT_BE_FORMULA')
        if key_cell is None or not value(key_cell,strings).strip():raise ValueError('STATUS_ROW_KEY_MISSING')
        if key_cell.getAttribute('t')=='e':raise ValueError('STATUS_ROW_KEY_INVALID')
        key=value(key_cell,strings)
        if key in keys:raise ValueError('STATUS_ROW_KEY_NOT_UNIQUE')
        keys.add(key)
        if status_cell is not None and nodes(status_cell,'f'):raise ValueError('STATUS_COLUMN_CONTAINS_FORMULA')
        records.append(dict(sheet=sheet,key=key,status=value(status_cell,strings) if status_cell is not None else '',
                            row=int(row.getAttribute('r')),reference=names[status_column]+row.getAttribute('r')))
        if len(records)>100000:raise ValueError('TOO_MANY_ROWS')
    return records


def check_path(path):
    path=Path(path).resolve()
    if path.suffix.lower() not in ('.xlsx','.xlsm'):raise ValueError('STATUS_WRITE_REQUIRES_XLSX_OR_XLSM')
    if path.stat().st_size>MAX_FILE:raise ValueError('WORKBOOK_TOO_LARGE')
    return path


@workbook_errors
def inspect_status(path,sheets,key_column,status_column):
    path=check_path(path);raw=path.read_bytes()
    archive,workbook,targets,strings=load(raw)
    try:
        selected=list(dict.fromkeys(sheets))
        if not selected:raise ValueError('SELECT_AT_LEAST_ONE_SHEET')
        records=[]
        for sheet in selected:
            if sheet not in targets:raise ValueError('SHEET_NOT_FOUND')
            records.extend(sheet_rows(xml(archive.read(targets[sheet])),strings,key_column,status_column,sheet))
        if len(records)>100000:raise ValueError('TOO_MANY_ROWS')
        return dict(fingerprint=digest(raw),file=path.name,sheets=selected,key_column=key_column,status_column=status_column,records=records)
    finally:archive.close()


@workbook_errors
def status_options(path):
    path=check_path(path);archive,workbook,targets,strings=load(path.read_bytes())
    try:
        columns={}
        for sheet,target in targets.items():
            doc=xml(archive.read(target))
            header=next((r for r in doc.getElementsByTagNameNS(NS,'row') if r.getAttribute('r')=='1'),None)
            columns[sheet]=[value(c,strings).strip() for c in nodes(header,'c')] if header is not None else []
        return dict(file=path.name,sheets=list(targets),columns_by_sheet=columns)
    finally:archive.close()


@contextlib.contextmanager
def locked_original(path):
    """Deny existing/new writers, but permit the final atomic file replacement."""
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes
        import msvcrt
        api=ctypes.WinDLL('kernel32',use_last_error=True)
        api.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
        api.CreateFileW.restype=wintypes.HANDLE
        handle=api.CreateFileW(str(path),0x80000000,1|4,None,3,0x80,None)
        if handle==ctypes.c_void_p(-1).value:raise PermissionError('SOURCE_FILE_LOCKED_OR_DENIED')
        fd=msvcrt.open_osfhandle(int(handle),os.O_RDONLY|os.O_BINARY)
        with os.fdopen(fd,'rb') as file:yield file
    else:
        import fcntl
        with path.open('rb') as file:
            fcntl.flock(file,fcntl.LOCK_EX|fcntl.LOCK_NB)
            try:yield file
            finally:fcntl.flock(file,fcntl.LOCK_UN)


def set_literal(document,cell,new_value):
    for child in list(cell.childNodes):
        if child.nodeType==child.ELEMENT_NODE and child.localName in ('v','is','f'):
            cell.removeChild(child)
    prefix=cell.prefix+':' if cell.prefix else ''
    cell.setAttribute('t','inlineStr')
    inline=document.createElementNS(NS,prefix+'is');item=document.createElementNS(NS,prefix+'t')
    item.setAttribute('xml:space','preserve');item.appendChild(document.createTextNode(new_value));inline.appendChild(item)
    extension=next((n for n in nodes(cell,'extLst')),None)
    cell.insertBefore(inline,extension) if extension else cell.appendChild(inline)


def replace_original(temporary,path):
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes
        api=ctypes.WinDLL('kernel32',use_last_error=True)
        api.ReplaceFileW.argtypes=[wintypes.LPCWSTR,wintypes.LPCWSTR,wintypes.LPCWSTR,wintypes.DWORD,ctypes.c_void_p,ctypes.c_void_p]
        api.ReplaceFileW.restype=wintypes.BOOL
        if not api.ReplaceFileW(str(path),str(temporary),None,0,None,None):
            raise ctypes.WinError(ctypes.get_last_error())
    else:os.replace(temporary,path)


@workbook_errors
def apply_status(path,sheets,key_column,status_column,fingerprint,updates,backup_dir):
    """Apply explicit user-approved rows; never infer OK from a print submission.

    updates contain sheet/key/expected_status/status. A stale workbook, ambiguous
    keys, protected sheet or formula status column rejects the whole batch.
    """
    path=check_path(path)
    if not updates or len(updates)>10000:raise ValueError('STATUS_SELECT_1_TO_10000_ROWS')
    selected=list(dict.fromkeys(sheets))
    if not selected:raise ValueError('SELECT_AT_LEAST_ONE_SHEET')
    temporary=None
    with locked_original(path) as original:
        raw=original.read()
        if len(raw)>MAX_FILE:raise ValueError('WORKBOOK_TOO_LARGE')
        if digest(raw)!=fingerprint:raise ValueError('SOURCE_CHANGED_REFRESH_STATUS')
        original_identity=os.fstat(original.fileno())
        archive,workbook,targets,strings=load(raw)
        try:
            documents={};records={}
            for sheet in selected:
                if sheet not in targets:raise ValueError('SHEET_NOT_FOUND')
                doc=xml(archive.read(targets[sheet]));documents[sheet]=doc
                if doc.getElementsByTagNameNS(NS,'sheetProtection'):raise ValueError('STATUS_SHEET_PROTECTED')
                for row in sheet_rows(doc,strings,key_column,status_column,sheet):records[(sheet,row['key'])]=row
            changes=[];seen=set()
            for update in updates:
                identity=(update['sheet'],str(update['key']))
                if identity in seen:raise ValueError('STATUS_DUPLICATE_UPDATE')
                seen.add(identity)
                if identity not in records:raise ValueError('STATUS_ROW_NOT_FOUND')
                current=records[identity]
                if update['expected_status']!=current['status']:raise ValueError('STATUS_ROW_CHANGED')
                new_value=update['status']
                if not isinstance(new_value,str) or len(new_value)>100 or any(ord(c)<32 and c not in '\n\t\r' for c in new_value):
                    raise ValueError('STATUS_VALUE_INVALID')
                if new_value==current['status']:continue
                doc=documents[identity[0]]
                row=next(r for r in doc.getElementsByTagNameNS(NS,'row') if r.getAttribute('r')==str(current['row']))
                target=next((c for c in nodes(row,'c') if c.getAttribute('r')==current['reference']),None)
                if target is None:
                    prefix=row.prefix+':' if row.prefix else '';target=doc.createElementNS(NS,prefix+'c');target.setAttribute('r',current['reference'])
                    # Preserve ascending cell order (Excel column names compare by length, then letters).
                    desired=column(current['reference']);later=next((c for c in nodes(row,'c') if (len(column(c.getAttribute('r'))),column(c.getAttribute('r')))>(len(desired),desired)),None)
                    row.insertBefore(target,later) if later else row.appendChild(target)
                set_literal(doc,target,new_value)
                changes.append(dict(sheet=identity[0],key=identity[1],before=current['status'],after=new_value))
            if not changes:return dict(changed=0,fingerprint=fingerprint,changes=[],backup=None)
            modified={targets[sheet]:doc.toxml(encoding='utf-8') for sheet,doc in documents.items() if any(c['sheet']==sheet for c in changes)}
            # Ask Excel to recalculate dependent formulas when the file is next opened.
            calculation=workbook.getElementsByTagNameNS(NS,'calcPr')
            if calculation:
                calculation[0].setAttribute('fullCalcOnLoad','1');modified['xl/workbook.xml']=workbook.toxml(encoding='utf-8')
            output=io.BytesIO()
            with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as result:
                for item in archive.infolist():result.writestr(item,modified.get(item.filename,archive.read(item.filename)))
            new_raw=output.getvalue()
            backup_dir=Path(backup_dir);backup_dir.mkdir(parents=True,exist_ok=True)
            backup=backup_dir/('excel-status-'+uuid.uuid4().hex+path.suffix.lower())
            with backup.open('xb') as file:file.write(raw);file.flush();os.fsync(file.fileno())
            fd,temporary=tempfile.mkstemp(prefix='.'+path.name+'.studio-status-',suffix='.tmp',dir=path.parent)
            with os.fdopen(fd,'wb') as file:file.write(new_raw);file.flush();os.fsync(file.fileno())
            current_identity=path.stat()
            if (current_identity.st_dev,current_identity.st_ino)!=(original_identity.st_dev,original_identity.st_ino):
                raise ValueError('SOURCE_CHANGED_REFRESH_STATUS')
            try:replace_original(temporary,path)
            except PermissionError:raise PermissionError('SOURCE_FILE_LOCKED_OR_DENIED')
            temporary=None
            return dict(changed=len(changes),fingerprint=digest(new_raw),changes=changes,backup=backup.name)
        finally:
            archive.close()
            if temporary is not None:Path(temporary).unlink(missing_ok=True)
