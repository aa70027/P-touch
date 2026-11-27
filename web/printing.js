'use strict';
Object.assign(translations,{
 persianDigits:['Persian digits in text','نمایش و چاپ اعداد فارسی در متن','عرض الأرقام الفارسية وطباعتها في النص'],
 digitsHint:['Applies after data/formulas; QR and barcode payloads keep their original data.','پس از جای‌گذاری داده و فرمول اعمال می‌شود؛ دادهٔ QR و بارکد تغییر نمی‌کند.','يُطبّق بعد البيانات والصيغ؛ تبقى بيانات QR والباركود الأصلية.'],
 centerWidth:['Center across tape width','وسط عرض نوار','توسيط عبر عرض الشريط'],centerPage:['Center on page / cell','وسط صفحه / خانه','توسيط في الصفحة / الخانة'],
 centerAllWidth:['Move content to the center of tape width','انتقال محتوا به مرکز عرض نوار','نقل المحتوى إلى وسط عرض الشريط'],
 centerAutoHint:['Centering on the page fixes the current automatic length so the position stays centered.','وسط صفحه، طول خودکار فعلی را ثابت می‌کند تا جای محتوا واقعاً در مرکز بماند.','يثبّت توسيط الصفحة الطول التلقائي الحالي للحفاظ على الموضع في الوسط.'],
 centered:['Content centered.','محتوا به مرکز منتقل شد.','تم توسيط المحتوى.'],centeredFixed:['Content centered; current length is now fixed.','محتوا وسط‌چین شد؛ طول فعلی ثابت شد.','تم التوسيط وتثبيت الطول الحالي.'],
 fileCuts:['Cut settings for each file','تنظیمات برش هر فایل','إعدادات القطع لكل ملف'],generalCut:['Using current general settings','از تنظیمات عمومی فعلی','من الإعدادات العامة الحالية'],customCut:['Saved settings for this file','تنظیم اختصاصی این فایل','إعدادات خاصة بهذا الملف'],
 resetFileCuts:['Use general settings','استفاده از تنظیمات عمومی','استخدام الإعدادات العامة'],
 cutSaveHint:['Starting print saves changed cuts for each file. Unsaved designs/shared files are saved as a private copy when needed. Other layout edits to an existing file are not overwritten.','با شروع چاپ، تغییرات برش برای همان فایل ذخیره می‌شوند. طرح ذخیره‌نشده یا فایل مشترک، در صورت نیاز به‌صورت یک کپی خصوصی ذخیره می‌شود. سایر تغییرات طرحِ یک فایل موجود بازنویسی نمی‌شوند.','يحفظ بدء الطباعة تغييرات القطع لكل ملف. يُحفظ التصميم غير المحفوظ أو الملف المشترك كنسخة خاصة عند الحاجة، دون استبدال تعديلات التخطيط الأخرى لملف موجود.'],
 personalCopy:['My copy','نسخهٔ من','نسختي'],afterPrint:['After sending print, go to:','بعد از چاپ برو به:','بعد إرسال الطباعة انتقل إلى:'],
 goToQueue:['Print queue page','به صفحه صف چاپ','صفحة قائمة الطباعة'],stayOnPage:['Stay on this page','در همین صفحه بمان','البقاء في هذه الصفحة'],
 printSubmittedToast:['Print data sent successfully. Physical completion is unconfirmed.','ارسال چاپ به چاپگر موفق بود؛ تکمیل فیزیکی تأیید نشده است.','أُرسلت بيانات الطباعة بنجاح؛ الاكتمال الفعلي غير مؤكّد.'],
 printFailedToast:['Print failed','چاپ ناموفق بود','فشلت الطباعة'],simulationDoneToast:['Print simulation completed.','چاپ آزمایشی تکمیل شد.','اكتملت محاكاة الطباعة.'],printCancelledToast:['Print job cancelled.','کار چاپ لغو شد.','أُلغيت مهمة الطباعة.'],
 inlineJobs:['Print status','وضعیت چاپ','حالة الطباعة'],statusConnectionLost:['Status connection lost; reconnecting without resending.','ارتباط دریافت وضعیت قطع شد؛ اتصال مجدد بدون ارسال دوبارهٔ چاپ.','انقطع اتصال الحالة؛ تجري إعادة المحاولة دون إعادة إرسال الطباعة.'],
 inlineNextHint:['Confirm the next record here, or press Ctrl+Enter.','رکورد بعد را همین‌جا تأیید کنید یا Ctrl+Enter بزنید.','أكّد السجل التالي هنا أو اضغط Ctrl+Enter.'],
 CONTENT_TOO_TALL_TO_CENTER:['The content is taller than the printable width. Reduce its size or spacing first.','ارتفاع محتوا از عرض قابل چاپ بیشتر است؛ ابتدا اندازه یا فاصلهٔ اجزا را کاهش دهید.','المحتوى أطول من العرض القابل للطباعة؛ قلّل الحجم أو المسافات أولاً.'],
 ELEMENT_FRAME_TOO_TALL_TO_CENTER:['The element frame cannot fit across this tape. Reduce its height/width or rotation first.','کادر جزء در عرض این نوار جا نمی‌شود؛ ابتدا ارتفاع، عرض یا چرخش را اصلاح کنید.','لا يتسع إطار العنصر عبر الشريط؛ عدّل أبعاده أو دورانه أولاً.'],
 CONTENT_TOO_WIDE_TO_CENTER:['The content is wider than this page/cell. Increase the length or reduce the content size.','محتوا از طول صفحه یا خانه بزرگ‌تر است؛ طول را افزایش یا اندازهٔ محتوا را کاهش دهید.','المحتوى أعرض من الصفحة أو الخانة؛ زد الطول أو قلّل حجم المحتوى.']
});
Object.assign(translations,{CENTER_CONFLICTS_WITH_MARGINS:['Centering conflicts with the saved margins. Reduce the margins or increase the fixed length.','وسط صفحه با فاصله‌های قبل و بعد سازگار نیست؛ فاصله‌ها را کم یا طول ثابت را بیشتر کنید.','يتعارض التوسيط مع الهوامش؛ قلّلها أو زد الطول الثابت.']});
const CUT_KEYS=['cut_between_pages','cut_end_record','cut_between_files','cut_end_file'];
const CUT_LABELS=['betweenPages','endRecord','betweenFiles','endFile'];
S.pendingPrints=new Map();
function cutPolicyChanged(entry){const initial=entry.initialPolicy,next=entry.custom?entry.cutDraft:null;return initial===null?next!==null:next===null||CUT_KEYS.some(k=>initial[k]!==next[k]);}
function printEntry(key,doc,resourceId=null,current=false){const copy=clone(doc);return {key,doc:copy,resourceId,current,initialPolicy:clone(copy.cut_settings??null),custom:!!copy.cut_settings,cutDraft:clone(copy.cut_settings||S.printDefaults.cut_settings)};}
function selectedPrintEntries(){return S.printSelected.map(key=>S.printEntries.get(key));}
function cutEditorsHtml(){return selectedPrintEntries().map(entry=>`<fieldset class="print-cut-file" data-cut-entry="${h(entry.key)}"><legend>${h(entry.doc.name)}</legend><div class="split"><span class="badge">${h(t(entry.custom?'customCut':'generalCut'))}</span>${button('reset-print-cuts','resetFileCuts','small',`data-key="${h(entry.key)}"`)}</div><div class="fieldgrid">${CUT_KEYS.map((key,i)=>select(key,CUT_LABELS[i],['full','half','none'],entry.cutDraft[key],'print-cut')).join('')}</div>${modelProfile(entry.doc.pages[0]?.model).driver_controls?`<p class="notice">${h(t('driverModeHint'))}</p>`:''}</fieldset>`).join('');}
function renderPrintCutEditors(){const box=$('#print-cut-editors');if(box)box.innerHTML=cutEditorsHtml();}
function afterPrintButtons(){return `<div class="after-print-switch"><strong>${h(t('afterPrint'))}</strong><input type="hidden" data-dialog="after_print" value="${S.afterPrint}"><div role="radiogroup" aria-label="${h(t('afterPrint'))}" class="segmented">${[['queue','goToQueue'],['stay','stayOnPage']].map(([value,label])=>`<button type="button" role="radio" aria-checked="${S.afterPrint===value}" class="${S.afterPrint===value?'active':''}" data-action="after-print-choice" data-value="${value}">${h(t(label))}</button>`).join('')}</div></div>`;}
async function openPrintDialog(existing=null){
 S.printDefaults=await api('/printing/defaults');S.printExisting=existing;S.printOrigin=S.view;
 const preferred=localStorage.getItem('studio-after-print:'+S.boot.user.id);S.afterPrint=preferred==='stay'?'stay':'queue';
 S.printEntries=new Map();S.printSelected=[];
 if(existing){existing.documents.forEach((doc,i)=>{const key='history:'+i;S.printEntries.set(key,printEntry(key,doc,existing.document_ids?.[i]||null));S.printSelected.push(key);});}
 else{S.printEntries.set('current',printEntry('current',S.doc,S.resourceId,true));S.printSelected=['current'];}
 const count=existing?.records.length||S.records.length;
 modal(`<h2>${h(t('print'))}</h2><div class="fieldgrid">${field('copies','copies',existing?.copies||1,'number','min="1" max="10000"','dialog')}${field('file_copies','fileCopies',existing?.file_copies||1,'number','min="1" max="10000"','dialog')}${select('mode','mode',['continuous','confirm'],existing?.mode||'continuous','dialog')}${select('recordMode','records',[['all','allRecords'],['range','selectedRecords']],'all','dialog')}${field('fromRecord','fromRecord',1,'number',`min="1" max="${count}"`,'dialog')}${field('toRecord','toRecord',count,'number',`min="1" max="${count}"`,'dialog')}<div class="span">${check('simulation','simulation',existing?.simulation??false,'dialog')}</div></div><p class="hint">${h(t('simulationHint'))}</p>${!existing?`<h3>${h(t('selectFiles'))}</h3><p class="hint">${h(t('printFilesHint'))}</p><div class="print-file-list">${resourceList('document').filter(d=>d.id!==S.resourceId).map(d=>`<label class="check"><input type="checkbox" data-print-document="${d.id}">${h(d.name)}</label>`).join('')||`<p class="hint">${h(t('noItems'))}</p>`}</div>`:''}<h3>${h(t('fileCuts'))}</h3><p class="hint">${h(t('cutSaveHint'))}</p><div id="print-cut-editors">${cutEditorsHtml()}</div><div id="after-print-options">${afterPrintButtons()}</div><p class="notice">${h(t('physicalHint'))}</p><div class="actions">${button('submit-print','submitPrint','primary')}</div>`);
}
async function persistPrintCuts(entry){
 const policy=entry.custom?clone(entry.cutDraft):null;
 entry.doc.cut_settings=policy;
 if(!cutPolicyChanged(entry))return;
 const resource=S.resources.find(r=>r.id===entry.resourceId);
 let saved;
 if(resource&&resource.owner===S.boot.user.id&&['document','template'].includes(resource.kind)){
  saved=await api('/resources/'+resource.id+'/cut-settings','PATCH',{cut_settings:policy});
 }else{
  const copied=!!resource&&resource.owner!==S.boot.user.id;
  const name=copied?entry.doc.name.slice(0,165)+' · '+t('personalCopy'):entry.doc.name;
  saved=await api('/resources','POST',{name,kind:'document',scope:'private',payload:{...entry.doc,name}});
  entry.doc.name=saved.name;
  entry.resourceId=saved.id;
 }
 const index=S.resources.findIndex(r=>r.id===saved.id);if(index>=0)S.resources[index]=saved;else S.resources.unshift(saved);
 if(entry.current){S.doc.cut_settings=clone(policy);if(!resource||resource.owner!==S.boot.user.id){S.resourceId=saved.id;S.resourceKind='document';S.doc.name=saved.name;S.dirty=false;}}
 entry.initialPolicy=clone(policy);
}
async function submitPrint(node){
 const values=dialogValues(),entries=selectedPrintEntries();
 let records=clone(S.printExisting?.records||S.records);
 if(values.recordMode==='range'){
  if(values.fromRecord<1||values.toRecord<values.fromRecord||values.toRecord>records.length)throw Error('INVALID_RECORD_RANGE');
  records=records.slice(values.fromRecord-1,values.toRecord);
 }
 if(!records.length)throw Error('NO_RECORDS');
 node.disabled=true;
 try{
  for(const entry of entries)await persistPrintCuts(entry);
  const request={...(S.printExisting||{}),source:null,documents:entries.map(entry=>({...clone(entry.doc),cut_settings:clone(entry.cutDraft)})),document_ids:entries.map(entry=>entry.resourceId),records,copies:values.copies,file_copies:values.file_copies,mode:values.mode,simulation:values.simulation};
  if(!S.printExisting&&S.sourceId&&S.sourceActive!==false)Object.assign(request,sourceBinding(),{record_from:values.recordMode==='range'?values.fromRecord-1:0,record_to:values.recordMode==='range'?values.toRecord:null});
  const result=await api('/jobs','POST',request);
  localStorage.setItem('studio-after-print:'+S.boot.user.id,values.after_print);
  closeModal();
  if(values.after_print==='stay'){
   S.pendingPrints.set(result.id,{id:result.id,owner:S.boot.user.id,state:'queued',total:0,sent:0,simulated:0});
   renderInlinePrintStatus();toast(t('jobQueued'));pollInlinePrints();
  }else{await navigate('queue');toast(t('jobQueued'));}
 }finally{node.disabled=false;}
}
function inlinePrintHtml(){return [...S.pendingPrints.values()].filter(job=>job.owner===S.boot?.user?.id).map(job=>`<div class="notice info split"><span><strong>${h(t('inlineJobs'))}</strong> · ${h(t(job.state))} · <span class="mono">${job.sent+job.simulated} / ${job.total||'…'}</span>${job.disconnected?` · ${h(t('statusConnectionLost'))}`:''}</span><div class="actions">${job.state==='waiting'?button('inline-next-record','next','small primary',`data-id="${job.id}"`):''}${button('inline-cancel-print','cancel','small',`data-id="${job.id}"`)}${button('inline-open-queue','queue','small')}</div></div>`).join('');}
function renderInlinePrintStatus(){const box=$('#inline-print-status'),html=inlinePrintHtml();if(box&&box.innerHTML!==html)box.innerHTML=html;}
function printOutcome(job){if(job.state==='submitted')return [t('printSubmittedToast'),false];if(job.state==='simulated')return [t('simulationDoneToast'),false];if(job.state==='cancelled')return [t('printCancelledToast'),true];return [t('printFailedToast')+(job.error?' · '+errorText(job.error):''),true];}
let inlinePollBusy=false;
async function pollInlinePrints(){
 if(inlinePollBusy||!S.boot?.user)return;inlinePollBusy=true;
 try{for(const [id,old] of [...S.pendingPrints]){
  if(old.owner!==S.boot.user.id){S.pendingPrints.delete(id);continue;}
  let job;try{job=await api('/jobs/'+id+'/status');}catch{S.pendingPrints.set(id,{...old,disconnected:true});continue;}
  if(['submitted','simulated','failed','cancelled','interrupted'].includes(job.state)){
   S.pendingPrints.delete(id);const [message,error]=printOutcome(job);toast(message,error,5000);
  }else{S.pendingPrints.set(id,{...job,owner:old.owner});if(job.state==='waiting'&&old.state!=='waiting')toast(t('inlineNextHint'),false,5000);}
 }renderInlinePrintStatus();}finally{inlinePollBusy=false;}
}
async function centerDesign(axis,all=false){
 if(!all&&!element())throw Error('ELEMENT_NOT_FOUND');
 const result=await api('/design/center','POST',{document:S.doc,page:S.page,row:S.records[S.row]||{},...sourceBinding(),element_id:all?null:element().id,axis});
 S.doc=result.document;S.dirty=true;renderView();toast(t(result.fixed_length?'centeredFixed':'centered'));
}
const precedingPrintAct=act;
act=async function(action,node){switch(action){
 case'submit-print':return submitPrint(node);
 case'reset-print-cuts':{const entry=S.printEntries.get(node.dataset.key);entry.custom=false;entry.cutDraft=clone(S.printDefaults.cut_settings);renderPrintCutEditors();return;}
 case'after-print-choice':S.afterPrint=node.dataset.value;$('#after-print-options').innerHTML=afterPrintButtons();return;
 case'center-width':return centerDesign('width');
 case'center-page':return centerDesign('page');
 case'center-content-width':return centerDesign('width',true);
 case'inline-next-record':await api('/jobs/'+node.dataset.id+'/next','POST',{});return pollInlinePrints();
 case'inline-cancel-print':await api('/jobs/'+node.dataset.id+'/cancel','POST',{});return pollInlinePrints();
 case'inline-open-queue':return navigate('queue');
 default:return precedingPrintAct(action,node);
}};
document.addEventListener('change',event=>{const node=event.target;if(node.dataset.printCut){const entry=S.printEntries.get(node.closest('[data-cut-entry]').dataset.cutEntry);entry.cutDraft[node.dataset.printCut]=node.value;entry.custom=true;const badge=node.closest('fieldset').querySelector('.badge');if(badge)badge.textContent=t('customCut');}if(node.dataset.printDocument){const key='saved:'+node.dataset.printDocument;if(node.checked){if(!S.printEntries.has(key)){const resource=S.resources.find(r=>r.id===node.dataset.printDocument);S.printEntries.set(key,printEntry(key,resource.payload,resource.id));}S.printSelected.push(key);}else S.printSelected=S.printSelected.filter(k=>k!==key);renderPrintCutEditors();}});
document.addEventListener('keydown',event=>{if(event.ctrlKey&&event.key==='Enter'&&S.view==='editor'&&!$('#dialog').open){const waiting=[...S.pendingPrints.values()].find(j=>j.owner===S.boot?.user?.id&&j.state==='waiting');if(waiting){event.preventDefault();safely(()=>act('inline-next-record',{dataset:{id:waiting.id}}));}}});
setInterval(()=>{if(S.pendingPrints.size)pollInlinePrints();},1200);
