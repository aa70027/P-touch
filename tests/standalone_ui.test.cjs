const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const vm=require('node:vm');const path=require('node:path');
function harness(){
 const calls=[],elements={'#dialog-content':{},'[data-native="from"]':{value:'1'},'[data-native="to"]':{value:'2'},'[data-native="template"]':{value:'label-001.lbx'}};
 const S={boot:{user:{id:'owner'}},doc:{name:'Draft',pages:[{}]},records:[{ID:'A01'},{ID:'A02'}],sourceId:'source',sourceActive:true,selectedSheets:['Records'],excelStatus:{owner:'owner',source:'source',sheets:['Records'],key:'ID',column:'Status',edits:new Map()}};
 const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const bundle={id:'bundle',name:'Prepared',payload:{templates:['label-001.lbx'],device_state:'not_transferred'}};
 const box={S,translations:{},h:escape,t:key=>box.translations[key]?.[0]||key,$:key=>elements[key],modal:html=>elements['#dialog-content'].innerHTML=html,
  dataView:()=>'',act:async()=>{},field:()=>'',select:()=>'',button:(action,label,cls='',extra='')=>`<button data-action="${action}" ${extra}>${label}</button>`,
  toast:(...args)=>calls.push(['toast',...args]),statusOwner:()=>{if(S.excelStatus.owner!==S.boot.user.id)throw Error('LOGIN_REQUIRED');return S.excelStatus;},
  statusInspect:async()=>calls.push(['inspect']),excelStatusHtml:()=>'<status>',download:(...args)=>calls.push(['download',...args]),
  chooseFile:async()=>{},api:async(url,method,body)=>{calls.push([url,method,body]);if(url==='/standalone/tools')return {editor:false,transfer:false,network:false};if(url==='/standalone')return [bundle];if(url==='/standalone/prepare')return bundle;if(url.endsWith('/status/export'))return {download_url:'/api/status/exchanges/export/download'};if(url.endsWith('/download'))return 'csv-blob';if(url.endsWith('/history'))return [];return {device_state:'not_transferred',changed:1};}
 };vm.createContext(box);vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/standalone.js'),'utf8'),box);return {box,calls,S,elements,bundle};
}
test('standalone preparation is distinct from device transfer and missing tools are disabled',async()=>{
 const h=harness();await h.box.openStandalone();h.S.standalone.bundle=h.bundle;const html=h.box.standaloneHtml();
 assert.match(html,/not transferred to printer/);assert.match(html,/data-action="native-open" disabled/);
 assert.equal(h.calls.some(c=>c[0]==='/jobs'),false);
});
test('preparation rereads the active source and retains the selected range and sheets',async()=>{
 const h=harness();await h.box.openStandalone();await h.box.prepareStandalone({disabled:false});
 const request=h.calls.find(c=>c[0]==='/standalone/prepare')[2];assert.equal(request.source,'source');assert.equal(request.record_from,0);assert.equal(request.record_to,2);assert.equal(request.sheets[0],'Records');assert.equal(request.records.length,1);
 assert.equal(h.S.standalone.bundle.payload.device_state,'not_transferred');
});
test('opening an official tool does not mark the bundle or Excel synchronized',async()=>{
 const h=harness();await h.box.openStandalone();h.S.standalone.bundle=h.bundle;await h.box.act('native-open',{});
 assert.equal(h.bundle.payload.device_state,'not_transferred');assert.equal(h.calls.some(c=>c[0].includes('/status/apply')),false);
});
test('conflicted CSV previews escape cell content and disable applying',()=>{
 const h=harness();const html=h.box.statusImportHtml({updates:[],conflicts:[{sheet:'S',key:'<script>',current:'old',incoming:'new',reason:'both_changed'}],unchanged:0});
 assert.doesNotMatch(html,/<script>/);assert.match(html,/&lt;script&gt;/);assert.match(html,/data-action="status-import-apply" disabled/);
});
test('CSV export refuses unsaved manual edits and exports only after they are cleared',async()=>{
 const h=harness();h.S.excelStatus.edits.set(0,'OK');await assert.rejects(h.box.exportStatusCSV(),/STATUS_SAVE_OR_DISCARD_FIRST/);
 h.S.excelStatus.edits.clear();await h.box.exportStatusCSV();assert.equal(h.calls.find(c=>c[0]==='download')[2],'print-status.csv');
 assert.equal(h.calls.some(c=>c[0].includes('/status/apply')),false);
});
test('reviewed import is applied only explicitly and uses its recorded selection',async()=>{
 const h=harness();h.S.excelStatus.importPlan={id:'plan',conflicts:[],selection:{sheets:['Other'],key_column:'RecordID',status_column:'PrintStatus'}};
 await h.box.act('status-import-apply',{disabled:false});assert.equal(h.calls.filter(c=>c[0]==='/status/imports/plan/apply').length,1);
 assert.equal(h.S.excelStatus.key,'RecordID');assert.equal(h.S.excelStatus.sheets[0],'Other');
});
test('a different account cannot reuse standalone state from the previous user',async()=>{
 const h=harness();await h.box.openStandalone();h.S.boot.user.id='other';await assert.rejects(h.box.prepareStandalone({disabled:false}),/LOGIN_REQUIRED/);
 assert.equal(h.calls.some(c=>c[0]==='/standalone/prepare'),false);
});
