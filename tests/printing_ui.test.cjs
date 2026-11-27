const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const policy={cut_between_pages:'half',cut_end_record:'half',cut_between_files:'full',cut_end_file:'full'};
const documentFixture=()=>({name:'Cable',pages:[{model:'PT-E550W',elements:[{id:'text1',text:'UNSAVED',x:2,y:22,h:6}]}],rules:[],variables:{},cut_settings:null});
const plain=v=>JSON.parse(JSON.stringify(v));
function setup(){
 const calls=[],toasts=[],boxes=new Map(),storage=new Map(),listeners=new Map();let jobState='running';
 const state={boot:{user:{id:'local'},profiles:[]},doc:documentFixture(),resources:[],records:[{N:'123'}],row:0,page:0,element:0,view:'editor',dirty:true,resourceId:null,resourceKind:null,sourceId:null};
 const context={S:state,translations:{},structuredClone,Map,Set,console,localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},document:{addEventListener:(event,handler)=>listeners.set(event,handler)},setInterval:()=>{},clone:structuredClone,safely:async work=>work(),
  $:selector=>{if(!boxes.has(selector))boxes.set(selector,{innerHTML:''});return boxes.get(selector);},$$:()=>[],
  t:key=>context.translations[key]?.[0]||key,h:v=>String(v??''),modelProfile:()=>({driver_controls:false}),
  field:(k,l,v)=>`<input data-dialog="${k}" value="${v}">`,check:(k,l,v)=>`<input type="checkbox" data-dialog="${k}">`,select:(k,l,values,v,group)=>`<select data-${group}="${k}">${v}</select>`,
  button:(a,label,c='',extra='')=>`<button data-action="${a}" ${extra}>${context.t(label)}</button>`,resourceList:kind=>state.resources.filter(r=>r.kind===kind),
  modal:html=>{context.modalHtml=html;},closeModal:()=>calls.push(['close']),dialogValues:()=>context.values,
  toast:(...args)=>toasts.push(args),navigate:async view=>{state.view=view;calls.push(['navigate',view]);},sourceBinding:()=>({}),errorText:v=>v,
  renderView:()=>calls.push(['render']),page:()=>state.doc.pages[state.page],element:()=>state.doc.pages[state.page].elements[state.element],act:async()=>{},
  api:async(url,method='GET',body)=>{
   calls.push([url,method,plain(body??null)]);
   if(url==='/printing/defaults')return {cut_settings:structuredClone(policy)};
   if(url==='/resources'&&method==='POST')return {id:'copy-id',owner:'local',kind:body.kind,name:body.name,payload:body.payload,scope:body.scope};
   if(url.endsWith('/cut-settings')){const old=state.resources.find(r=>url.includes('/'+r.id+'/'));return {...old,payload:{...old.payload,cut_settings:body.cut_settings}};}
   if(url==='/jobs')return {id:'job-id'};
   if(url.endsWith('/status'))return {id:'job-id',state:jobState,total:1,sent:jobState==='submitted'?1:0,simulated:jobState==='simulated'?1:0,error:jobState==='failed'?'printer offline':null};
   if(url.endsWith('/cancel'))jobState='cancelled';
   if(url==='/design/center')return {document:{...body.document,pages:[{...body.document.pages[0],elements:[{id:'text1',text:'UNSAVED',x:2,y:9,h:6}]}]},fixed_length:false};
   return {ok:true};
  }
 };
 context.values={copies:1,file_copies:1,mode:'continuous',recordMode:'all',fromRecord:1,toRecord:1,simulation:true,after_print:'stay'};
 vm.createContext(context);
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/printing.js'),'utf8')+'\nthis.featureApi={openPrintDialog,selectedPrintEntries,cutPolicyChanged,persistPrintCuts,submitPrint,pollInlinePrints,printOutcome,centerDesign,inlinePrintHtml};',context);
 return {context,state,calls,toasts,storage,boxes,listeners,api:context.featureApi,setJobState:value=>jobState=value};
}
const flush=()=>new Promise(resolve=>setImmediate(resolve));

test('print dialog loads fresh general cuts and provides two accessible destination choices',async()=>{
 const x=setup();await x.api.openPrintDialog();
 assert.equal(x.calls[0][0],'/printing/defaults');
 assert.deepEqual(plain(x.api.selectedPrintEntries()[0].cutDraft),policy);
 assert.equal(x.api.selectedPrintEntries()[0].custom,false);
 assert.match(x.context.modalHtml,/role="radiogroup"/);
 assert.equal((x.context.modalHtml.match(/role="radio"/g)||[]).length,2);
 for(const key of Object.keys(policy))assert.match(x.context.modalHtml,new RegExp(key));
});

test('file-specific saved cuts override the general defaults when reopening',async()=>{
 const x=setup();x.state.doc.cut_settings={...policy,cut_end_file:'none'};
 await x.api.openPrintDialog();assert.equal(x.api.selectedPrintEntries()[0].cutDraft.cut_end_file,'none');
 assert.equal(x.api.selectedPrintEntries()[0].custom,true);
});

test('owner cut updates preserve unsaved design edits and send only cut settings to persistence',async()=>{
 const x=setup();x.state.resourceId='owned';x.state.resourceKind='document';
 x.state.resources=[{id:'owned',owner:'local',kind:'document',payload:{...documentFixture(),pages:[{elements:[{text:'OLD SAVED'}]}]}}];
 await x.api.openPrintDialog();const entry=x.api.selectedPrintEntries()[0];entry.custom=true;entry.cutDraft.cut_end_file='none';
 await x.api.persistPrintCuts(entry);
 const patch=x.calls.find(c=>c[1]==='PATCH');assert.deepEqual(Object.keys(patch[2]),['cut_settings']);
 assert.equal(x.state.doc.pages[0].elements[0].text,'UNSAVED');assert.equal(x.state.dirty,true);
 assert.equal(x.state.resources[0].payload.pages[0].elements[0].text,'OLD SAVED');
});

test('shared-file cut edits create a private copy without patching the original',async()=>{
 const x=setup();x.state.resourceId='shared';x.state.resources=[{id:'shared',owner:'another-user',kind:'document',payload:documentFixture()}];
 await x.api.openPrintDialog();const entry=x.api.selectedPrintEntries()[0];entry.custom=true;entry.cutDraft.cut_end_file='half';
 await x.api.persistPrintCuts(entry);
 assert.equal(x.calls.some(c=>c[1]==='PATCH'),false);
 assert.equal(x.calls.find(c=>c[0]==='/resources'&&c[1]==='POST')[2].scope,'private');
 assert.equal(x.state.resourceId,'copy-id');assert.equal(x.state.resources.find(r=>r.id==='shared').payload.cut_settings,null);
 assert.equal(x.state.resources.find(r=>r.id==='copy-id').payload.name,x.state.doc.name);
});

test('unchanged inherited defaults are snapshotted for this job without saving a file override',async()=>{
 const x=setup();await x.api.openPrintDialog();
 x.state.printDefaults.cut_settings.cut_end_file='none';
 await x.api.submitPrint({disabled:false});await flush();
 const request=x.calls.find(c=>c[0]==='/jobs'&&c[1]==='POST')[2];
 assert.equal(request.documents[0].cut_settings.cut_end_file,'full');
 assert.equal(x.calls.some(c=>c[0]==='/resources'||c[1]==='PATCH'),false);
 assert.equal(x.state.doc.cut_settings,null);
});

test('stay option preserves the editor and reports a delayed printer failure as a short toast',async()=>{
 const x=setup();await x.api.openPrintDialog();await x.api.submitPrint({disabled:false});await flush();
 assert.equal(x.state.view,'editor');assert.equal(x.state.doc.pages[0].elements[0].text,'UNSAVED');assert.equal(x.state.dirty,true);
 assert.equal(x.calls.some(c=>c[0]==='navigate'),false);
 x.setJobState('failed');await x.api.pollInlinePrints();
 assert.match(x.toasts.at(-1)[0],/Print failed.*printer offline/);assert.equal(x.toasts.at(-1)[1],true);assert.equal(x.toasts.at(-1)[2],5000);
 assert.equal(x.state.pendingPrints.size,0);
});

test('queue destination navigates only after a job has been accepted',async()=>{
 const x=setup();await x.api.openPrintDialog();x.context.values.after_print='queue';await x.api.submitPrint({disabled:false});
 assert.equal(x.state.view,'queue');assert.equal(x.state.pendingPrints.size,0);
 assert.ok(x.calls.findIndex(c=>c[0]==='/jobs')<x.calls.findIndex(c=>c[0]==='navigate'));
});

test('stay success reports submission, not physical confirmation',async()=>{
 const x=setup();await x.api.openPrintDialog();await x.api.submitPrint({disabled:false});await flush();
 x.setJobState('submitted');await x.api.pollInlinePrints();
 assert.match(x.toasts.at(-1)[0],/sent successfully.*unconfirmed/);
 assert.equal(x.toasts.at(-1)[1],false);assert.equal(x.state.view,'editor');
});

test('confirm-each-record mode stays operable in the editor',async()=>{
 const x=setup();await x.api.openPrintDialog();x.context.values.mode='confirm';x.setJobState('waiting');
 await x.api.submitPrint({disabled:false});await flush();
 assert.match(x.api.inlinePrintHtml(),/inline-next-record/);assert.match(x.api.inlinePrintHtml(),/inline-cancel-print/);
 assert.equal(x.state.view,'editor');
});

test('pending notifications never cross application user accounts',async()=>{
 const x=setup();await x.api.openPrintDialog();await x.api.submitPrint({disabled:false});await flush();
 x.state.boot.user.id='someone-else';x.calls.length=0;await x.api.pollInlinePrints();
 assert.equal(x.state.pendingPrints.size,0);assert.equal(x.calls.some(c=>String(c[0]).endsWith('/status')),false);
});

test('Ctrl+Enter confirms a waiting inline record without interpreting ordinary Enter as a print command',async()=>{
 const x=setup();await x.api.openPrintDialog();x.context.values.mode='confirm';x.setJobState('waiting');
 await x.api.submitPrint({disabled:false});await flush();x.calls.length=0;
 x.listeners.get('keydown')({key:'Enter',ctrlKey:false,preventDefault:()=>{}});await flush();
 assert.equal(x.calls.some(c=>String(c[0]).endsWith('/next')),false);
 let prevented=false;x.listeners.get('keydown')({key:'Enter',ctrlKey:true,preventDefault:()=>{prevented=true;}});await flush();
 assert.equal(prevented,true);assert.equal(x.calls.some(c=>String(c[0]).endsWith('/next')),true);assert.equal(x.state.view,'editor');
});

test('center action preserves the selected design and applies returned coordinates',async()=>{
 const x=setup();await x.api.centerDesign('width');
 const request=x.calls.find(c=>c[0]==='/design/center')[2];assert.equal(request.element_id,'text1');assert.equal(request.axis,'width');
 assert.equal(x.state.doc.pages[0].elements[0].y,9);assert.equal(x.state.dirty,true);assert.equal(x.state.view,'editor');
});
