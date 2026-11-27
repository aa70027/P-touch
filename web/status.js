'use strict';
Object.assign(translations,{
 excelStatus:['Excel print status','وضعیت چاپ Excel','حالة الطباعة في Excel'],
 excelStatusDesc:['Manage an existing status column in the original linked workbook.','مدیریت ستون وضعیت در فایل Excel اصلیِ متصل‌شده.','إدارة عمود الحالة في ملف Excel الأصلي المرتبط.'],
 statusSource:['Original Excel source','منبع Excel اصلی','مصدر Excel الأصلي'],statusKey:['Unique row ID column','ستون شناسهٔ یکتای ردیف','عمود معرّف السجل الفريد'],statusColumn:['Print status column','ستون وضعیت چاپ','عمود حالة الطباعة'],
 statusRequirements:['Choose a linked XLSX/XLSM file you own. Add a unique ID and a plain-text status column in Excel first.','فایل XLSX یا XLSM متصل‌شده و متعلق به خودتان را انتخاب کنید. ابتدا در Excel، ستون شناسهٔ یکتا و ستون متنی وضعیت را ایجاد کنید.','اختر ملف XLSX أو XLSM مرتبطاً تملكه. أنشئ أولاً في Excel عمود معرّف فريد وعمود حالة نصياً.'],
 statusDevicePending:['Printer status: not synchronized. Device database readback has not been verified. Saving Excel does not update the printer.','وضعیت دستگاه: همگام نشده. بازخوانی پایگاه دادهٔ دستگاه هنوز تأیید نشده است. ذخیرهٔ Excel دستگاه را به‌روز نمی‌کند.','حالة الجهاز: غير متزامنة. لم يتم التحقق من استرجاع قاعدة بيانات الجهاز. لا يحدّث حفظ Excel الطابعة.'],
 statusInspect:['Read status rows','خواندن ردیف‌های وضعیت','قراءة سجلات الحالة'],statusSave:['Save changes in original Excel','ذخیرهٔ تغییرات در Excel اصلی','حفظ التغييرات في Excel الأصلي'],
 statusMarkOK:['Set selected rows to OK','ثبت OK برای ردیف‌های انتخاب‌شده','تعيين OK للسجلات المحددة'],statusSearch:['Find row ID','جست‌وجوی شناسهٔ ردیف','البحث عن معرّف السجل'],statusCurrent:['Current value','مقدار فعلی','القيمة الحالية'],statusNew:['New value','مقدار جدید','القيمة الجديدة'],
 statusSaved:['Status saved in original Excel; printer remains unsynchronized.','وضعیت در Excel اصلی ذخیره شد؛ دستگاه هنوز همگام نشده است.','حُفظت الحالة في Excel الأصلي؛ الجهاز غير متزامن بعد.'],
 statusSafeWrite:['Only status cells change. A backup is made first. Close Excel before saving. Changes are manual acknowledgements, not printer-confirmed completion.','فقط سلول‌های وضعیت تغییر می‌کنند و پیش از ذخیره پشتیبان تهیه می‌شود. پیش از ذخیره، فایل را در Excel ببندید. این ثبت، تأیید دستی کاربر است و تأیید خودکار چاپگر محسوب نمی‌شود.','تتغير خلايا الحالة فقط وتُنشأ نسخة احتياطية أولاً. أغلق الملف في Excel قبل الحفظ. هذه تأكيدات يدوية وليست تأكيداً آلياً من الطابعة.'],
 statusEdits:['Changed rows','ردیف‌های تغییریافته','السجلات المعدّلة'],statusHistory:['Status change backups','پشتیبان تغییرات وضعیت','نسخ تغييرات الحالة الاحتياطية'],
 statusSelect:['Select rows on this page','انتخاب ردیف‌های این صفحه','تحديد سجلات هذه الصفحة'],previous:['Previous','قبلی','السابق'],sheets:['Worksheets','شیت‌ها','أوراق العمل'],
 STATUS_REQUIRES_ORIGINAL_LINKED_EXCEL:['Link the original Excel file from Windows first. Uploaded copies cannot update the original.','ابتدا فایل Excel اصلی را از Windows متصل کنید؛ نسخهٔ آپلودشده فایل اصلی را تغییر نمی‌دهد.','اربط ملف Excel الأصلي من Windows أولاً؛ لا تعدّل النسخة المرفوعة الملف الأصلي.'],
 STATUS_WRITE_REQUIRES_XLSX_OR_XLSM:['Status writeback supports XLSX/XLSM. Convert legacy XLS in Excel first.','ثبت وضعیت در XLSX و XLSM پشتیبانی می‌شود؛ XLS قدیمی را ابتدا در Excel تبدیل کنید.','يدعم حفظ الحالة XLSX وXLSM؛ حوّل ملف XLS القديم في Excel أولاً.'],
 STATUS_KEY_COLUMN_MISSING:['The selected ID column is missing on a selected sheet.','ستون شناسه در یکی از شیت‌های انتخاب‌شده وجود ندارد.','عمود المعرّف مفقود في ورقة محددة.'],STATUS_COLUMN_MISSING:['The status column is missing on a selected sheet.','ستون وضعیت در یکی از شیت‌های انتخاب‌شده وجود ندارد.','عمود الحالة مفقود في ورقة محددة.'],
 STATUS_ROW_KEY_NOT_UNIQUE:['Row IDs must be unique within each sheet.','شناسهٔ ردیف باید در هر شیت یکتا باشد.','يجب أن يكون المعرّف فريداً داخل كل ورقة.'],STATUS_ROW_KEY_MISSING:['A nonempty row has no ID.','یک ردیف دارای داده، شناسه ندارد.','يوجد سجل بيانات دون معرّف.'],STATUS_ROW_KEY_MUST_NOT_BE_FORMULA:['Row IDs must be fixed values, not formulas.','شناسهٔ ردیف باید مقدار ثابت باشد و فرمول نباشد.','يجب أن تكون المعرّفات قيماً ثابتة وليست صيغاً.'],
 STATUS_COLUMN_CONTAINS_FORMULA:['Choose a status column without formulas.','ستون وضعیت نباید شامل فرمول باشد.','اختر عمود حالة دون صيغ.'],STATUS_KEY_AND_VALUE_COLUMNS_MUST_DIFFER:['ID and status columns must differ.','ستون شناسه و وضعیت باید متفاوت باشند.','يجب أن يختلف عمود المعرّف عن الحالة.'],STATUS_DUPLICATE_HEADERS:['Column headers must be unique.','نام ستون‌ها باید یکتا باشد.','يجب أن تكون عناوين الأعمدة فريدة.'],
 SOURCE_CHANGED_REFRESH_STATUS:['Excel changed after reading. Refresh the status rows and review again.','Excel پس از خواندن تغییر کرده است؛ ردیف‌ها را دوباره بخوانید و بازبینی کنید.','تغيّر Excel بعد القراءة؛ أعد قراءة السجلات ومراجعتها.'],STATUS_ROW_CHANGED:['A status value changed. Refresh before saving.','مقدار وضعیت تغییر کرده است؛ پیش از ذخیره دوباره بخوانید.','تغيّرت قيمة الحالة؛ أعد القراءة قبل الحفظ.'],
 STATUS_SHEET_PROTECTED:['The sheet is protected; it was not modified.','شیت محافظت شده و تغییر نکرده است.','الورقة محمية ولم تُعدّل.'],SIGNED_WORKBOOK_NOT_WRITABLE:['Digitally signed workbooks are not modified.','فایل دارای امضای دیجیتال تغییر داده نمی‌شود.','لا تُعدّل الملفات الموقعة رقمياً.'],STATUS_SELECT_1_TO_10000_ROWS:['Select 1 to 10,000 changed rows.','از ۱ تا ۱۰٬۰۰۰ ردیف تغییریافته انتخاب کنید.','اختر من سجل إلى ١٠٬٠٠٠ سجل معدّل.']
});
function ownedStatusSources(){return resourceList('source').filter(r=>r.owner===S.boot.user.id&&r.payload.linked_path&&/\.xls[xm]$/i.test(r.payload.linked_path));}
async function openExcelStatus(ident=null){
 const sources=ownedStatusSources();ident=ident||sources.find(r=>r.id===S.sourceId)?.id||sources[0]?.id;
 if(!ident){modal(`<h2>${h(t('excelStatus'))}</h2><p class="notice">${h(t('statusRequirements'))}</p>`);return;}
 const options=await api('/sources/'+ident+'/status/options'),config=options.config||{};
 S.excelStatus={owner:S.boot.user.id,source:ident,options,sheets:config.sheets?.filter(s=>options.sheets.includes(s))||options.sheets.slice(0,1),key:config.key_column||'',column:config.status_column||'',snapshot:null,selected:new Set(),edits:new Map(),page:0,search:'',history:await api('/sources/'+ident+'/status/history')};
 modal(excelStatusHtml());
}
function statusOwner(){if(!S.excelStatus||S.excelStatus.owner!==S.boot.user.id)throw Error('LOGIN_REQUIRED');return S.excelStatus;}
function statusCommonColumns(){const v=statusOwner();return v.sheets.reduce((cols,sheet,i)=>i?cols.filter(c=>v.options.columns_by_sheet[sheet].includes(c)):v.options.columns_by_sheet[sheet]||[],[]).filter(Boolean);}
function excelStatusHtml(){
 const v=statusOwner(),columns=statusCommonColumns();
 v.key=columns.includes(v.key)?v.key:columns.find(c=>['ID','id','RecordID','شناسه'].includes(c))||columns[0]||'';
 v.column=columns.includes(v.column)?v.column:columns.find(c=>['وضعیت چاپ','PrintStatus','Status','status'].includes(c))||columns.find(c=>c!==v.key)||'';
 return `<h2>${h(t('excelStatus'))}</h2><p>${h(t('excelStatusDesc'))}</p><div class="notice">${h(t('statusDevicePending'))}</div><p class="hint">${h(t('statusRequirements'))}</p><div class="fieldgrid"><div class="span">${select('source','statusSource',ownedStatusSources().map(r=>[r.id,r.name]),v.source,'status-config')}</div><div class="span"><strong>${h(t('sheets'))}</strong><div class="actions">${v.options.sheets.map(sheet=>`<label class="check"><input type="checkbox" data-status-sheet="${h(sheet)}" ${v.sheets.includes(sheet)?'checked':''}>${h(sheet)}</label>`).join('')}</div></div>${select('key','statusKey',columns,v.key,'status-config')}${select('column','statusColumn',columns,v.column,'status-config')}</div><div class="actions">${button('status-inspect','statusInspect','primary',!v.sheets.length||!v.key||!v.column?'disabled':'')}${button('status-export','statusExport','',!v.snapshot?'disabled':'')}${button('status-import','statusImport')}</div><p class="hint">${h(t('statusSafeWrite'))}</p><div id="status-rows">${statusRowsHtml()}</div>${v.history.length?`<h3>${h(t('statusHistory'))}</h3><div class="stack">${v.history.slice(0,10).map(event=>`<div class="split"><span>${h(formatDate(event.created))} · ${event.changed}</span>${event.backup_url?`<a href="${h(event.backup_url)}" download>${h(t('download'))}</a>`:''}</div>`).join('')}</div>`:''}`;
}
function statusRowsHtml(){
 const v=statusOwner();if(!v.snapshot)return '';
 const filtered=v.snapshot.records.map((row,index)=>({row,index})).filter(({row})=>!v.search||row.key.toLocaleLowerCase().includes(v.search.toLocaleLowerCase()));
 v.page=Math.min(v.page,Math.max(0,Math.ceil(filtered.length/100)-1));const visible=filtered.slice(v.page*100,v.page*100+100);v.visible=visible.map(r=>r.index);
 return `<div class="stack"><input class="search" data-status-search placeholder="${h(t('statusSearch'))}" value="${h(v.search)}"><div class="split"><span>${h(t('statusEdits'))}: <strong id="status-edit-count">${v.edits.size}</strong> / ${v.snapshot.records.length}</span><div class="actions">${button('status-mark-ok','statusMarkOK','',!v.selected.size?'disabled':'')}${button('status-apply','statusSave','primary',!v.edits.size?'disabled':'')}</div></div><div class="table-wrap"><table><thead><tr><th><input type="checkbox" data-status-all aria-label="${h(t('statusSelect'))}" ${visible.length&&visible.every(r=>v.selected.has(r.index))?'checked':''}></th><th>${h(t('sheets'))}</th><th>${h(v.snapshot.key_column)}</th><th>${h(t('statusCurrent'))}</th><th>${h(t('statusNew'))}</th></tr></thead><tbody>${visible.map(({row,index})=>`<tr><td><input type="checkbox" data-status-selected="${index}" aria-label="${h(row.key)}" ${v.selected.has(index)?'checked':''}></td><td>${h(row.sheet)}</td><td>${h(row.key)}</td><td>${h(row.status)}</td><td><input data-status-edit="${index}" maxlength="100" aria-label="${h(t('statusNew')+' '+row.key)}" value="${h(v.edits.has(index)?v.edits.get(index):row.status)}"></td></tr>`).join('')}</tbody></table></div><div class="split"><span>${v.page+1} / ${Math.max(1,Math.ceil(filtered.length/100))}</span><div class="actions">${button('status-prev','previous','small',v.page===0?'disabled':'')}${button('status-next','nativeNextPage','small',(v.page+1)*100>=filtered.length?'disabled':'')}</div></div></div>`;
}
function statusRenderRows(){const box=$('#status-rows');if(box)box.innerHTML=statusRowsHtml();}
async function statusInspect(){const v=statusOwner();v.snapshot=await api('/sources/'+v.source+'/status/inspect','POST',{sheets:v.sheets,key_column:v.key,status_column:v.column});v.selected.clear();v.edits.clear();v.page=0;v.search='';statusRenderRows();}
async function statusApply(node){
 const v=statusOwner();if(!v.snapshot||!v.edits.size)throw Error('STATUS_SELECT_1_TO_10000_ROWS');
 const updates=[...v.edits].map(([index,status])=>{const row=v.snapshot.records[index];return {sheet:row.sheet,key:row.key,expected_status:row.status,status};});
 node.disabled=true;
 try{await api('/sources/'+v.source+'/status/apply','POST',{sheets:v.snapshot.sheets,key_column:v.snapshot.key_column,status_column:v.snapshot.status_column,fingerprint:v.snapshot.fingerprint,updates});await statusInspect();v.history=await api('/sources/'+v.source+'/status/history');$('#dialog-content').innerHTML=excelStatusHtml();toast(t('statusSaved'),false,6000);}finally{node.disabled=false;}
}
const beforeStatusDataView=dataView;
dataView=function(){return beforeStatusDataView()+`<section class="card"><div class="card-title"><h3>${h(t('excelStatus'))}</h3>${button('excel-status','excelStatus')}</div><p class="card-body">${h(t('excelStatusDesc'))}</p></section>`;};
const beforeStatusAct=act;
act=async function(action,node){switch(action){
 case'excel-status':return openExcelStatus();
 case'status-inspect':return statusInspect();
 case'status-apply':return statusApply(node);
 case'status-mark-ok':{const v=statusOwner();for(const index of v.selected){const row=v.snapshot.records[index];if(row.status==='OK')v.edits.delete(index);else v.edits.set(index,'OK');}statusRenderRows();return;}
 case'status-prev':statusOwner().page--;statusRenderRows();return;
 case'status-next':statusOwner().page++;statusRenderRows();return;
 case'logout':S.excelStatus=null;break;
 }return beforeStatusAct(action,node);
};
document.addEventListener('change',event=>safely(async()=>{
 const node=event.target;
 if(node.dataset.statusConfig){const v=statusOwner(),key=node.dataset.statusConfig;if(key==='source')return openExcelStatus(node.value);v[key]=node.value;v.snapshot=null;v.edits.clear();v.selected.clear();$('#dialog-content').innerHTML=excelStatusHtml();}
 if(node.dataset.statusSheet!==undefined){const v=statusOwner();v.sheets=$$('[data-status-sheet]:checked').map(n=>n.dataset.statusSheet);v.snapshot=null;v.edits.clear();v.selected.clear();$('#dialog-content').innerHTML=excelStatusHtml();}
 if(node.dataset.statusSelected!==undefined){const v=statusOwner(),index=Number(node.dataset.statusSelected);node.checked?v.selected.add(index):v.selected.delete(index);statusRenderRows();}
 if(node.dataset.statusAll!==undefined){const v=statusOwner();for(const index of v.visible)node.checked?v.selected.add(index):v.selected.delete(index);statusRenderRows();}
 if(node.dataset.statusEdit!==undefined){const v=statusOwner(),index=Number(node.dataset.statusEdit);if(node.value===v.snapshot.records[index].status)v.edits.delete(index);else v.edits.set(index,node.value);const apply=$('[data-action="status-apply"]');if(apply)apply.disabled=!v.edits.size;const count=$('#status-edit-count');if(count)count.textContent=v.edits.size;}
}));
document.addEventListener('input',event=>{const node=event.target;if(node.dataset.statusSearch!==undefined){const v=statusOwner();v.search=node.value;v.page=0;const start=node.selectionStart;statusRenderRows();const input=$('[data-status-search]');if(input){input.focus();input.setSelectionRange(start,start);}}});
