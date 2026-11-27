"""Image-based LBX preparation and explicit handoff to official Brother tools.

LBX is a ZIP/XML design file, not a compiled BLF or a printer acknowledgement.
Device database retrieval is deliberately not inferred from exports or launches.
"""
import csv
import io
import json
from pathlib import Path
import re
import subprocess
import uuid
import xml.etree.ElementTree as ET
import zipfile

from fastapi import Depends
from fastapi.responses import FileResponse
from PIL import ImageOps
from pydantic import BaseModel,Field

from .formulas import apply_rules
from .models import Document
from .render import render_label,png_bytes

BASE='http://schemas.brother.info/ptouch/2007/lbx/'
SPACE={'pt':BASE+'main','style':BASE+'style','image':BASE+'image','meta':BASE+'meta','dc':'http://purl.org/dc/elements/1.1/'}
for prefix,uri in SPACE.items():ET.register_namespace(prefix,uri)


def node(parent,prefix,tag_name,**attributes):
    return ET.SubElement(parent,'{'+SPACE[prefix]+'}'+tag_name,{key:str(value) for key,value in attributes.items()})


def pt(mm):return f'{mm*72/25.4:.5f}pt'


def image_lbx(image,metadata,title):
    """Keep all text/shaping in pixels; one static template per record/page."""
    if metadata['model']!='PT-E550W':raise ValueError('STANDALONE_REQUIRES_E550W')
    bounds=ImageOps.invert(image.convert('L')).getbbox()
    if bounds is None:bounds=(image.width//2,image.height//2,image.width//2+1,image.height//2+1)
    picture=image.crop(bounds).convert('RGBA')
    if max(picture.size)>2048:raise ValueError('STANDALONE_IMAGE_MAX_2048')
    along,across=metadata['resolution'];length=metadata['length_mm'];width=metadata['width_mm']
    left,top,right,bottom=bounds
    geometry=dict(x=pt(left/along*25.4),y=pt(top/across*25.4),width=pt((right-left)/along*25.4),height=pt((bottom-top)/across*25.4))
    document=ET.Element('{'+SPACE['pt']+'}document',version='1.1',generator='Cable Label Studio')
    body=node(document,'pt','body',currentSheet='Label');sheet=node(body,'style','sheet',name='Label')
    margin=(width-metadata['printable_mm'])/2
    formats={3.5:'257',6:'258',9:'264',12:'259',18:'260',24:'261'}
    node(sheet,'style','paper',media='0',width=pt(width),height=pt(length),marginLeft=pt(margin),marginRight=pt(margin),
         marginTop=pt(2),marginBottom=pt(2),orientation='landscape',autoLength='false',monochromeDisplay='true',
         paperColor='#FFFFFF',paperInk='#000000',split='1',format=formats[width],backgroundTheme='0',printerName='Brother PT-E550W')
    node(sheet,'style','cutLine',regularCut='0pt',freeCut='')
    node(sheet,'style','backGround',x=pt(2),y=pt(margin),width=pt(max(0,length-4)),height=pt(metadata['printable_mm']),brushStyle='NULL',brushId='0',color='#000000',backColor='#FFFFFF')
    objects=node(sheet,'pt','objects');item=node(objects,'image','image')
    style=node(item,'pt','objectStyle',**geometry,backColor='#FFFFFF',ropMode='COPYPEN',angle='0',anchor='TOPLEFT',flip='NONE')
    node(style,'pt','pen',style='NULL',widthX='0.5pt',widthY='0.5pt',color='#000000')
    node(style,'pt','brush',style='NULL',color='#000000',id='0')
    node(style,'pt','expanded',objectName='LabelImage',ID='0',lock='0',templateMergeTarget='LABELLIST',templateMergeType='NONE',templateMergeID='0',linkStatus='NONE',linkID='0')
    image_style=node(item,'image','imageStyle',originalName='LabelImage.bmp',alignInText='NONE',firstMerge='false',fileName='Object0.bmp')
    node(image_style,'image','transparent',flag='false',color='#FFFFFF')
    node(image_style,'image','trimming',flag='false',shape='RECTANGLE',trimOrgX='0pt',trimOrgY='0pt',trimOrgWidth='0pt',trimOrgHeight='0pt')
    node(image_style,'image','orgPos',**geometry)
    node(image_style,'image','effect',effect='NONE',brightness='50',contrast='50',photoIndex='0')
    node(image_style,'image','mono',operationKind='BINARY',reverse='0',ditherKind='MESH',threshold='128',gamma='100',ditherEdge='0',rgbconvProportionRed='30',rgbconvProportionGreen='59',rgbconvProportionBlue='11',rgbconvProportionReversed='0')
    properties=ET.Element('{'+SPACE['meta']+'}properties')
    node(properties,'meta','appName').text='Cable Label Studio'
    node(properties,'dc','title').text=title
    node(properties,'dc','creator').text='Amir Rahimi'
    node(properties,'dc','description').text='Free MIT software · https://github.com/aa70027/P-touch'
    node(properties,'meta','numPages').text='1'
    bitmap=io.BytesIO();picture.save(bitmap,format='BMP',dpi=(along,across))
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_STORED) as archive:
        archive.writestr('label.xml',ET.tostring(document,encoding='utf-8',xml_declaration=True))
        archive.writestr('prop.xml',ET.tostring(properties,encoding='utf-8',xml_declaration=True))
        archive.writestr('Object0.bmp',bitmap.getvalue())
    return output.getvalue()


GUIDES={
 'fa':'''چاپ مستقل PT-E550W
این بسته آمادهٔ بررسی در P-touch Editor است؛ تهیهٔ بسته به معنی انتقال به دستگاه نیست.
هر LBX یک تصویر ثابت از یک رکورد/صفحه است. متن فارسی و قلم‌ها در تصویر حفظ شده‌اند؛ متن قالب روی دستگاه قابل ویرایش نیست. records.csv دادهٔ جداگانه است و به تصاویر LBX اتصال پویا ندارد. manifest.json ارتباط رکورد و فایل را نشان می‌دهد.
۱. فایل LBX موردنظر را در P-touch Editor باز کنید؛ مدل PT-E550W، عرض نوار، طول و پیش‌نمایش را بررسی کنید. قالب‌های تصویری باید روی دستگاه واقعی پذیرش شوند؛ آن‌ها را تأییدشدهٔ سخت‌افزاری محسوب نکنید.
۲. File → Transfer Template را بزنید تا قالب در P-touch Transfer Manager ثبت شود. CSV را نیز در صورت نیاز جدا اضافه کنید. در شماره‌های خالی منتقل کنید؛ فایل‌های قبلی را بازنویسی نکنید.
۳. USB: چاپگر را در Transfer Manager انتخاب و Transfer را بزنید.
۴. Wi-Fi: در Transfer Manager فایل BLF را ذخیره کنید؛ در BRAdmin Professional دستگاه را انتخاب کنید و Control → Load Firmware (Manual) → TFTP PUT را برای همان BLF قالب اجرا کنید. رمز مدیریت چاپگر را فقط در ابزار رسمی وارد کنید. برنامه فرمان ارتقای Firmware ارسال نمی‌کند.
۵. پس از انتقال، طبق راهنمای Brother به حالت عادی برگردید؛ روی دستگاه File → Transferred Templates را باز و قالب را انتخاب کنید. تعداد نسخه و برش را روی دستگاه تعیین و Print را بزنید.
وضعیت CSV را می‌توان دستی ویرایش کرد؛ خود دستگاه OK را پس از چاپ ثبت نمی‌کند. برای برگشت وضعیت به Excel، فقط CSV واقعی و قابل خواندن را در پنجرهٔ وضعیت وارد و تغییرات/تعارض‌ها را بازبینی کنید. Backup اختصاصی Brother قابل ورود به‌عنوان CSV نیست؛ بازخوانی خودکار سلول‌های دستگاه پشتیبانی نشده است.
سازنده: Amir Rahimi · رایگان، مجوز MIT · https://github.com/aa70027/P-touch
''',
 'en':'''PT-E550W standalone printing
This package is prepared for review in P-touch Editor; preparation is not a device transfer.
Each LBX is a static image of one record/page, preserving text shaping and fonts. Its text is not editable on the printer. records.csv is separate data, not dynamically bound to the LBX images. manifest.json maps records to files.
1. Open an LBX in P-touch Editor. Verify PT-E550W, tape width, length and preview. Image templates require real-device acceptance; no hardware certification is implied.
2. Use File → Transfer Template to register it in P-touch Transfer Manager. Add CSV separately if needed; select free key numbers without overwriting existing files.
3. USB: select the printer in Transfer Manager and choose Transfer.
4. Wi-Fi: save a template BLF from Transfer Manager. In BRAdmin Professional select the printer, then Control → Load Firmware (Manual) → TFTP PUT for that template BLF. Enter the printer admin password only in the official tool. This application sends no firmware-upgrade commands.
5. Return to normal mode as described by Brother, then choose File → Transferred Templates on the device. Select the template, copies and cutting, and press Print.
Status data can be edited manually; the device does not automatically mark OK after printing. To write back into Excel, import only a genuine readable CSV in the status window and review differences/conflicts. Proprietary Brother backups are not CSV; automatic device-cell retrieval is unsupported.
Amir Rahimi · Free MIT software · https://github.com/aa70027/P-touch
''',
 'ar':'''الطباعة المستقلة PT-E550W
هذه حزمة للمراجعة في P-touch Editor؛ إعدادها لا يعني نقلها إلى الجهاز.
كل LBX صورة ثابتة لسجل وصفحة تحفظ شكل النص والخطوط؛ النص غير قابل للتحرير على الطابعة. records.csv بيانات منفصلة دون ربط ديناميكي بصور LBX. يربط manifest.json السجلات بالملفات.
١. افتح LBX في P-touch Editor وتحقق من PT-E550W وعرض الشريط والطول والمعاينة. يلزم اختبار القوالب المصورة على الجهاز الفعلي ولا يُدّعى اعتمادها عتادياً.
٢. اختر File → Transfer Template لفتح P-touch Transfer Manager. أضف CSV منفصلاً عند الحاجة واختر أرقاماً خالية دون استبدال الملفات الموجودة.
٣. USB: اختر الطابعة في Transfer Manager واضغط Transfer.
٤. Wi-Fi: احفظ قالب BLF من Transfer Manager ثم اختر الجهاز في BRAdmin Professional واتبع Control → Load Firmware (Manual) → TFTP PUT لقالب BLF. أدخل كلمة مرور إدارة الجهاز في الأداة الرسمية فقط. لا يرسل التطبيق أوامر تحديث Firmware.
٥. أعد الجهاز إلى الوضع العادي وفق دليل Brother ثم اختر File → Transferred Templates على الجهاز، وحدد القالب والنسخ والقطع واضغط Print.
يمكن تحرير الحالة يدوياً؛ لا يسجل الجهاز OK تلقائياً بعد الطباعة. لإرجاع الحالة إلى Excel استورد CSV حقيقياً قابلاً للقراءة وراجع الاختلافات والتعارضات. نسخ Brother الخاصة ليست CSV؛ استرجاع خلايا الجهاز آلياً غير مدعوم.
Amir Rahimi · مجاني بترخيص MIT · https://github.com/aa70027/P-touch
'''
}


class StandaloneRequest(BaseModel):
    document:Document
    records:list[dict]=Field(default_factory=lambda:[{}],min_length=1,max_length=99)
    source:str|None=None
    sheets:list[str]|None=None
    record_from:int=Field(0,ge=0)
    record_to:int|None=Field(None,ge=1)


def register_standalone_routes(app,store,current_user,assets_for,source_data):
    def owned(ident,user):
        resource=store.resource(ident,user)
        if resource['kind']!='standalone' or resource['owner']!=user['id']:raise PermissionError('OWNER_ONLY')
        return resource,store.root/'standalone'/ident

    @app.get('/api/standalone/tools')
    def tools(user=Depends(current_user)):
        from .native import brother_tools
        return {key:bool(value) for key,value in brother_tools().items()}

    @app.get('/api/standalone')
    def list_bundles(user=Depends(current_user)):
        return [resource for resource in store.resources(user,'standalone') if resource['owner']==user['id']]

    @app.post('/api/standalone/prepare')
    def prepare(value:StandaloneRequest,user=Depends(current_user)):
        records=value.records
        if value.source:records=source_data(value.source,user,sheets=value.sheets)['records'][value.record_from:value.record_to]
        if not records:raise ValueError('NO_RECORDS')
        if len(records)*len(value.document.pages)>99:raise ValueError('STANDALONE_MAX_99_TEMPLATES')
        if any(page.model!='PT-E550W' for page in value.document.pages):raise ValueError('STANDALONE_REQUIRES_E550W')
        output=io.BytesIO();mapping=[];total=0;columns=list(dict.fromkeys(key for row in records for key in row))
        with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as archive:
            text=io.StringIO(newline='');writer=csv.DictWriter(text,fieldnames=columns);writer.writeheader();writer.writerows(records)
            archive.writestr('records.csv','\ufeff'+text.getvalue())
            for record_index,row in enumerate(records):
                resolved=apply_rules(row,value.document.rules,value.document.variables)
                for page_index,page in enumerate(value.document.pages):
                    image,metadata=render_label(page,resolved,assets_for(user))
                    filename=f'label-{len(mapping)+1:03}.lbx'
                    title=f'L{len(mapping)+1:03}-R{record_index+1:03}-P{page_index+1:02}'
                    raw=image_lbx(image,metadata,title)
                    total+=len(raw)
                    if total>64*1024*1024:raise ValueError('STANDALONE_PACKAGE_TOO_LARGE')
                    archive.writestr(filename,raw);archive.writestr(filename[:-4]+'.png',png_bytes(image))
                    mapping.append(dict(file=filename,title=title,record=record_index+1,page=page_index+1,sheet=row.get('_sheet',''),row=row))
            index=io.StringIO(newline='');table=csv.writer(index);table.writerow(['TemplateFile','DeviceTitle','RecordNumber','Page','Sheet'])
            for entry in mapping:table.writerow([entry['file'],entry['title'],entry['record'],entry['page'],entry['sheet']])
            archive.writestr('labels.csv','\ufeff'+index.getvalue())
            manifest=dict(name=value.document.name,model='PT-E550W',kind='static-image-templates',device_state='not_transferred',
                          hardware_tested=False,templates=mapping,project='https://github.com/aa70027/P-touch',creator='Amir Rahimi',license='MIT')
            archive.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
            archive.writestr('source.label.json',value.document.model_dump_json(indent=2))
            for language,guide in GUIDES.items():archive.writestr('README.'+language+'.txt',guide)
        resource=store.save_resource(user,'standalone',value.document.name,{'templates':[row['file'] for row in mapping],
                                     'records':len(records),'device_state':'not_transferred'},'private')
        ident=resource['id'];directory=store.root/'standalone'/ident;directory.mkdir(parents=True)
        (directory/'package.zip').write_bytes(output.getvalue())
        store.audit(user['id'],'standalone.prepare',ident)
        return resource|{'download_url':f'/api/standalone/{ident}/download'}

    @app.get('/api/standalone/{ident}/download')
    def download(ident:str,user=Depends(current_user)):
        resource,directory=owned(ident,user)
        return FileResponse(directory/'package.zip',filename='PT-E550W-standalone.zip')

    @app.post('/api/standalone/{ident}/open')
    def open_editor(ident:str,value:dict,user=Depends(current_user)):
        from .native import open_brother_tool
        resource,directory=owned(ident,user);filename=str(value.get('file',''))
        if not re.fullmatch(r'label-\d{3}\.lbx',filename) or filename not in resource['payload']['templates']:raise ValueError('STANDALONE_FILE_NOT_FOUND')
        with zipfile.ZipFile(directory/'package.zip') as archive:(directory/filename).write_bytes(archive.read(filename))
        open_brother_tool('editor',directory/filename)
        store.audit(user['id'],'standalone.editor.open',ident)
        return {'state':'editor_opened','device_state':'not_transferred'}

    @app.post('/api/standalone/tool/{tool}')
    def open_tool(tool:str,user=Depends(current_user)):
        from .native import open_brother_tool
        open_brother_tool(tool)
        return {'state':'tool_opened','device_state':'not_transferred'}
