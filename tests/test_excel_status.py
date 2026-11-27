import io
from pathlib import Path
import zipfile

from openpyxl import Workbook,load_workbook
import pytest

from labelstudio.excel_status import apply_status,inspect_status


def workbook(path):
    book=Workbook();sheet=book.active;sheet.title='کابل‌ها'
    sheet.append(['ID','وضعیت چاپ','Formula']);sheet.append(['A01','', '=1+2']);sheet.append(['A02','OK','=2+2'])
    sheet['B2'].number_format='@'
    second=book.create_sheet('Other');second.append(['ID','وضعیت چاپ']);second.append(['A01',''])
    book.save(path);book.close()
    return path


def edit(path,snapshot,updates):
    return apply_status(path,snapshot['sheets'],'ID','وضعیت چاپ',snapshot['fingerprint'],updates,path.parent/'backups')


def snapshot(path):
    return inspect_status(path,['کابل‌ها','Other'],'ID','وضعیت چاپ')


def test_original_workbook_status_changes_by_sheet_and_key_with_exact_backup(tmp_path):
    path=workbook(tmp_path/'original.xlsx');before=path.read_bytes();state=snapshot(path)
    result=edit(path,state,[dict(sheet='Other',key='A01',expected_status='',status='OK')])
    assert result['changed']==1
    assert (tmp_path/'backups'/result['backup']).read_bytes()==before
    book=load_workbook(path)
    assert book['Other']['B2'].value=='OK' and book['کابل‌ها']['B2'].value is None
    assert book['کابل‌ها']['C2'].value=='=1+2'
    book.close()
    assert snapshot(path)['fingerprint']==result['fingerprint']


def test_status_values_are_literal_and_style_is_preserved(tmp_path):
    path=workbook(tmp_path/'file.xlsx');state=snapshot(path)
    edit(path,state,[dict(sheet='کابل‌ها',key='A01',expected_status='',status='=DDE("x")')])
    book=load_workbook(path)
    assert book['کابل‌ها']['B2'].value=='=DDE("x")'
    assert book['کابل‌ها']['B2'].data_type=='s' and book['کابل‌ها']['B2'].number_format=='@'
    book.close()


def test_opaque_vba_and_external_parts_are_preserved_byte_for_byte(tmp_path):
    path=workbook(tmp_path/'file.xlsm')
    opaque={'xl/vbaProject.bin':b'opaque-VBA-\0\xff','customXml/item1.xml':b'<anything untouched="yes"/>',
            'xl/externalLinks/externalLink1.xml':b'<opaque/>'}
    with zipfile.ZipFile(path,'a') as archive:
        for name,raw in opaque.items():archive.writestr(name,raw)
    with zipfile.ZipFile(path) as archive:before={n:archive.read(n) for n in archive.namelist()}
    state=snapshot(path)
    edit(path,state,[dict(sheet='کابل‌ها',key='A01',expected_status='',status='OK')])
    with zipfile.ZipFile(path) as archive:
        assert set(archive.namelist())==set(before)
        for name,raw in before.items():
            if name not in ('xl/worksheets/sheet1.xml','xl/workbook.xml'):assert archive.read(name)==raw


def test_stale_snapshot_never_overwrites_new_excel_changes(tmp_path):
    path=workbook(tmp_path/'file.xlsx');state=snapshot(path)
    book=load_workbook(path);book['کابل‌ها']['A2']='EXTERNAL';book.save(path);book.close();before=path.read_bytes()
    with pytest.raises(ValueError,match='SOURCE_CHANGED'):
        edit(path,state,[dict(sheet='کابل‌ها',key='A01',expected_status='',status='OK')])
    assert path.read_bytes()==before and not (tmp_path/'backups').exists()


@pytest.mark.parametrize('mutator,error',[
    (lambda s:setattr(s['A3'],'value','A01'),'STATUS_ROW_KEY_NOT_UNIQUE'),
    (lambda s:setattr(s['A2'],'value',None),'STATUS_ROW_KEY_MISSING'),
    (lambda s:setattr(s['A2'],'value','=1+1'),'STATUS_ROW_KEY_MUST_NOT_BE_FORMULA'),
    (lambda s:setattr(s['B2'],'value','=1+1'),'STATUS_COLUMN_CONTAINS_FORMULA'),
])
def test_ambiguous_or_formula_keys_and_statuses_are_rejected(tmp_path,mutator,error):
    path=workbook(tmp_path/'file.xlsx');book=load_workbook(path);mutator(book['کابل‌ها']);book.save(path);book.close();before=path.read_bytes()
    with pytest.raises(ValueError,match=error):snapshot(path)
    assert path.read_bytes()==before


def test_entire_batch_rejected_if_one_expected_value_changed(tmp_path):
    path=workbook(tmp_path/'file.xlsx');state=snapshot(path);before=path.read_bytes()
    updates=[dict(sheet='کابل‌ها',key='A01',expected_status='',status='OK'),
             dict(sheet='کابل‌ها',key='A02',expected_status='not-current',status='')]
    with pytest.raises(ValueError,match='STATUS_ROW_CHANGED'):edit(path,state,updates)
    assert path.read_bytes()==before and not (tmp_path/'backups').exists()


def test_protected_sheet_rejected_without_modification(tmp_path):
    path=workbook(tmp_path/'file.xlsx');book=load_workbook(path);book['کابل‌ها'].protection.sheet=True;book.save(path);book.close()
    state=snapshot(path);before=path.read_bytes()
    with pytest.raises(ValueError,match='STATUS_SHEET_PROTECTED'):edit(path,state,[dict(sheet='کابل‌ها',key='A01',expected_status='',status='OK')])
    assert path.read_bytes()==before


def test_excel_write_lock_prevents_status_replacement(tmp_path):
    if __import__('os').name!='nt':pytest.skip('Windows sharing semantics')
    import ctypes
    from ctypes import wintypes
    path=workbook(tmp_path/'file.xlsx');state=snapshot(path);before=path.read_bytes()
    api=ctypes.WinDLL('kernel32',use_last_error=True)
    api.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
    api.CreateFileW.restype=wintypes.HANDLE
    api.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=api.CreateFileW(str(path),0x80000000|0x40000000,1|2,None,3,0x80,None)
    assert handle!=ctypes.c_void_p(-1).value
    try:
        with pytest.raises(PermissionError,match='SOURCE_FILE_LOCKED'):
            edit(path,state,[dict(sheet='کابل‌ها',key='A01',expected_status='',status='OK')])
    finally:api.CloseHandle(handle)
    assert path.read_bytes()==before


def test_identical_status_is_noop_without_rewrite_or_backup(tmp_path):
    path=workbook(tmp_path/'file.xlsx');state=snapshot(path);before=path.read_bytes()
    result=edit(path,state,[dict(sheet='کابل‌ها',key='A02',expected_status='OK',status='OK')])
    assert result['changed']==0 and result['backup'] is None
    assert path.read_bytes()==before and not (tmp_path/'backups').exists()


def test_missing_or_invalid_workbook_has_actionable_error(tmp_path):
    missing=tmp_path/'missing.xlsx'
    with pytest.raises(ValueError,match='SOURCE_FILE_NOT_FOUND'):snapshot(missing)
    missing.write_bytes(b'not-a-workbook')
    with pytest.raises(ValueError,match='WORKBOOK_INVALID'):snapshot(missing)
