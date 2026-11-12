import csv
import datetime
import io
from pathlib import Path

MAX_ROWS = 100000


def cell(value):
    if value is None:
        return ''
    if isinstance(value, (datetime.datetime, datetime.date, datetime.time)):
        return value.isoformat()
    return value if isinstance(value, (str, int, float, bool)) else str(value)


def tabulate(rows):
    iterator = iter(rows)
    try:
        first = next(iterator)
    except StopIteration:
        return {'columns': [], 'records': []}
    headers, seen = [], set()
    for i, value in enumerate(first):
        name = str(cell(value)).strip() or f'Column{i+1}'
        original, suffix = name, 2
        while name in seen:
            name = f'{original}_{suffix}'
            suffix += 1
        seen.add(name)
        headers.append(name)
    records = []
    for row in iterator:
        if any(v is not None and str(v) != '' for v in row):
            if len(records) >= MAX_ROWS:
                raise ValueError('TOO_MANY_ROWS')
            records.append({name: cell(row[i]) if i < len(row) else '' for i, name in enumerate(headers)})
    return {'columns': headers, 'records': records}


def access_drivers():
    try:
        import pyodbc
        return [d for d in pyodbc.drivers() if 'Access' in d and '*.accdb' in d]
    except ImportError:
        return []


def read_data(path, sheet=None, encoding='utf-8-sig', delimiter=None):
    path = Path(path)
    ext = path.suffix.lower()
    if ext in ('.csv', '.tsv'):
        raw = path.read_text(encoding=encoding)
        try:
            dialect = csv.Sniffer().sniff(raw[:8192], delimiters=',;\t|')
        except csv.Error:
            dialect = csv.excel_tab if ext == '.tsv' else csv.excel
        return tabulate(csv.reader(io.StringIO(raw), dialect=dialect, **({'delimiter': delimiter} if delimiter else {}))) | {'sheets': []}
    if ext in ('.xlsx', '.xlsm'):
        import openpyxl
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True, keep_links=False)
        try:
            names = workbook.sheetnames
            selected = sheet or names[0]
            if selected not in names:
                raise ValueError('SHEET_NOT_FOUND')
            return tabulate(workbook[selected].iter_rows(values_only=True)) | {'sheets': names, 'sheet': selected}
        finally:
            workbook.close()
    if ext == '.xls':
        import xlrd
        book = xlrd.open_workbook(str(path), on_demand=True)
        try:
            names = book.sheet_names()
            selected = sheet or names[0]
            tab = book.sheet_by_name(selected)
            rows = ([xlrd.xldate_as_datetime(c.value, book.datemode) if c.ctype == xlrd.XL_CELL_DATE else c.value for c in tab.row(i)] for i in range(tab.nrows))
            return tabulate(rows) | {'sheets': names, 'sheet': selected}
        finally:
            book.release_resources()
    if ext in ('.mdb', '.accdb'):
        import pyodbc
        drivers = access_drivers()
        if not drivers:
            raise ValueError('ACCESS_DRIVER_MISSING')
        # All database paths originate in the upload store, never interpolated user SQL.
        with pyodbc.connect(f'DRIVER={{{drivers[0]}}};DBQ={path};READONLY=1;', timeout=10) as conn:
            cursor = conn.cursor()
            tables = sorted({r.table_name for r in cursor.tables(tableType='TABLE') if not r.table_name.startswith('MSys')})
            if not tables:
                raise ValueError('NO_TABLES')
            selected = sheet or tables[0]
            if selected not in tables:
                raise ValueError('TABLE_NOT_FOUND')
            cursor.execute('SELECT * FROM [' + selected.replace(']', ']]') + ']')
            headers = [c[0] for c in cursor.description]
            records = []
            while batch := cursor.fetchmany(1000):
                for row in batch:
                    if len(records) >= MAX_ROWS:
                        raise ValueError('TOO_MANY_ROWS')
                    records.append(dict(zip(headers, map(cell, row))))
            return {'columns': headers, 'records': records, 'sheets': tables, 'sheet': selected}
    raise ValueError('UNSUPPORTED_DATA_FORMAT')
