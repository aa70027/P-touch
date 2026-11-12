"""Regenerate the small, non-sensitive sample dataset and reusable templates."""
import csv
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from openpyxl import Workbook
from labelstudio.models import Document,Label,Element

root=Path(__file__).parent
records=[{'Rack':'A01','Port':str(i).zfill(2),'Type':'Fiber' if i%2 else 'Copper','X':'ready' if i%2 else '', 'توضیح':'رک اصلی' if i<5 else 'رک پشتیبان'} for i in range(1,9)]
with (root/'cables.csv').open('w',newline='',encoding='utf-8-sig') as output:
    writer=csv.DictWriter(output,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
book=Workbook();sheet=book.active;sheet.title='Cables';sheet.append(list(records[0]));
for row in records:sheet.append(list(row.values()))
sheet.freeze_panes='A2';sheet.auto_filter.ref=sheet.dimensions
for col in sheet.columns:sheet.column_dimensions[col[0].column_letter].width=20
book.save(root/'cables.xlsx')
rules=[{'target':'B','when':'not EMPTY(COL("X"))','value':"'فیبر نوری'",'otherwise':"'کابل مسی'"}]
document=Document(name='نمونه کابل دیتاسنتر',pages=[Label(name='Cable flag',kind='cable-flag',auto_length=False,length=40,
              elements=[Element(text='{Rack}-{Port}',size=12,h=6,y=4),Element(id='type',text='{B}',size=8,h=4,y=12)])],rules=rules,
              variables={'Rack':'A01','Port':'01','X':'ready'})
(root/'datacenter-flag.label.json').write_text(document.model_dump_json(indent=2),encoding='utf-8')
(root/'records.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
print('Generated CSV, XLSX, JSON and Persian flag template')
