const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const code=fs.readFileSync(path.join(__dirname,'../web/status.js'),'utf8');
function harness(){
 const calls=[],events={},elements={'#dialog-content':{},'#status-rows':{},'[data-action="status-apply"]':{}};
 const rows=[{sheet:'One',key:'A01',status:''},{sheet:'Two',key:'A01',status:'printed before'}];
 const options={file:'source.xlsx',sheets:['One','Two'],columns_by_sheet:{One:['ID','وضعیت چاپ'],Two:['ID','وضعیت چاپ']},config:{sheets:['One','Two'],key_column:'ID',status_column:'وضعیت چاپ'}};
 const state={boot:{user:{id:'owner'}},resources:[{id:'source',owner:'owner',name:'Renamed source',kind:'source',payload:{linked_path:'original.xlsx'}}],sourceId:'source'};
 const escape=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const box={S:state,translations:{},document:{addEventListener:(event,fn)=>events[event]=fn},h:escape,
  t:key=>box.translations[key]?.[0]||key,resourceList:kind=>state.resources.filter(r=>r.kind===kind),
  $:selector=>elements[selector],$$:()=>[],dataView:()=>'<base>',act:async()=>{},safely:fn=>fn(),formatDate:String,toast:(...args)=>calls.push(['toast',...args]),
  modal:html=>elements['#dialog-content'].innerHTML=html,
  button:(action,label,cls='',extra='')=>`<button data-action="${action}" ${extra}>${label}</button>`,
  select:(key,label,items,value,group)=>`<select data-${group}="${key}" value="${escape(value)}">${items.map(item=>escape(Array.isArray(item)?item[1]:item)).join('|')}</select>`,
  api:async(url,method,body)=>{calls.push([url,method,body]);if(url.endsWith('/options'))return structuredClone(options);if(url.endsWith('/history'))return [];if(url.endsWith('/inspect'))return {file:'source.xlsx',fingerprint:'a'.repeat(64),records:structuredClone(rows),...body};if(url.endsWith('/apply'))return {changed:1,device:{state:'pending_transfer'}};throw Error(url);}
 };
 vm.createContext(box);vm.runInContext(code,box);
 return {box,calls,state,elements,events,rows};
}
test('opening status reads preferences without modifying Excel',async()=>{
 const h=harness();await h.box.openExcelStatus();
 assert.equal(h.calls.filter(c=>c[1]==='POST').length,0);
 assert.match(h.elements['#dialog-content'].innerHTML,/not synchronized/);
 assert.equal(h.state.excelStatus.source,'source');
});
test('same ID on different sheets stays distinct when saving explicit status edits',async()=>{
 const h=harness();await h.box.openExcelStatus();await h.box.statusInspect();
 h.state.excelStatus.selected.add(1);await h.box.act('status-mark-ok',{});await h.box.statusApply({disabled:false});
 const request=h.calls.find(c=>c[0].endsWith('/apply'))[2];
 assert.equal(request.fingerprint,'a'.repeat(64));assert.equal(request.updates.length,1);
 assert.equal(request.updates[0].sheet,'Two');assert.equal(request.updates[0].key,'A01');
 assert.equal(request.updates[0].expected_status,'printed before');assert.equal(request.updates[0].status,'OK');
});
test('reading status does not automatically mark any row OK',async()=>{
 const h=harness();await h.box.openExcelStatus();await h.box.statusInspect();
 assert.equal(h.state.excelStatus.edits.size,0);
 assert.equal(h.calls.filter(c=>c[0].endsWith('/apply')).length,0);
});
test('stale workbook rejection retains edits and never retries writes',async()=>{
 const h=harness();await h.box.openExcelStatus();await h.box.statusInspect();h.state.excelStatus.edits.set(0,'OK');
 const before=h.box.api;h.box.api=async(url,...args)=>{if(url.endsWith('/apply')){h.calls.push([url]);throw Error('SOURCE_CHANGED_REFRESH_STATUS');}return before(url,...args);};
 const node={disabled:false};await assert.rejects(h.box.statusApply(node),/SOURCE_CHANGED/);
 assert.equal(node.disabled,false);assert.equal(h.state.excelStatus.edits.get(0),'OK');
 assert.equal(h.calls.filter(c=>c[0].endsWith('/apply')).length,1);
});
test('account switch cannot reuse the previous user status session',async()=>{
 const h=harness();await h.box.openExcelStatus();await h.box.statusInspect();h.state.excelStatus.edits.set(0,'OK');h.state.boot.user.id='other';
 await assert.rejects(h.box.statusApply({disabled:false}),/LOGIN_REQUIRED/);
 assert.equal(h.calls.filter(c=>c[0].endsWith('/apply')).length,0);
});
test('status row content is escaped before inserting into the page',async()=>{
 const h=harness();h.rows[0].key='<script>bad()</script>';h.rows[0].status='" onfocus="bad';
 await h.box.openExcelStatus();await h.box.statusInspect();
 const html=h.box.statusRowsHtml();assert.doesNotMatch(html,/<script>/);assert.match(html,/&lt;script&gt;/);
});
test('uploaded copies and other users sources are excluded',async()=>{
 const h=harness();h.state.resources.push({id:'upload',owner:'owner',kind:'source',name:'upload.xlsx',payload:{file:'upload.xlsx'}},
  {id:'foreign',owner:'other',kind:'source',name:'foreign.xlsx',payload:{linked_path:'foreign.xlsx'}});
 assert.deepEqual(Array.from(h.box.ownedStatusSources(),s=>s.id),['source']);
});
