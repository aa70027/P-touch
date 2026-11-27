const {test}=require('node:test');const assert=require('node:assert/strict');const fs=require('node:fs');const vm=require('node:vm');const path=require('node:path');
function setup(){
 const storage=new Map(),events=new Map(),classes=new Map(),panes=new Map();
 const toolbar={innerHTML:''},content={classList:{toggle:(name,on)=>classes.set(name,on)},insertAdjacentHTML:()=>{}};
 let html='';Object.defineProperty(content,'innerHTML',{get:()=>html,set:value=>{html=value;panes.set('.editor-stage',{scrollTop:0,scrollLeft:0});panes.set('.editor-inspector',{scrollTop:0,scrollLeft:0});}});
 const box={console,structuredClone,Map,Set,crypto:require('node:crypto').webcrypto,setTimeout:()=>1,clearTimeout:()=>{},setInterval:()=>{},
 localStorage:{getItem:key=>storage.get(key)||null,setItem:(key,value)=>storage.set(key,value)},
 window:{addEventListener:()=>{}},document:{addEventListener:(name,handler)=>{if(!events.has(name))events.set(name,[]);events.get(name).push(handler);},querySelector:selector=>selector==='#content'?content:selector==='#editor-top-actions'?toolbar:panes.get(selector)||null,querySelectorAll:()=>[]}};
 vm.createContext(box);
 for(const file of ['i18n','app','release','printing','editor','status','standalone'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/'+file+'.js'),'utf8'),box);
 vm.runInContext("S.boot={user:{id:'one'},model:'PT-E550W',profiles:[{id:'PT-E550W',name:'PT-E550W',widths:[24],dpi:180,high_dpi:360}],fonts:['Segoe UI']};S.doc=newDoc();",box);
 return{box,storage,events,classes,panes,toolbar,content,run:code=>vm.runInContext(code,box)};
}
test('toolbar exposes the five original actions as localized accessible icon buttons',()=>{
 const h=setup();for(const lang of ['fa','en','ar']){
  h.run(`language='${lang}'`);const html=h.run('editorToolbar()');
  assert.equal((html.match(/<button /g)||[]).length,5);
  for(const action of ['print-dialog','standalone','save-template','save-file','new'])assert.match(html,new RegExp('data-action="'+action+'"'));
  assert.equal((html.match(/title="[^"]+" aria-label="[^"]+"/g)||[]).length,5);
  assert.doesNotMatch(html,/<\/svg>[^<]+<\/button>/);
 }
});
test('designer moves actions out of the canvas heading and retains data and preview in one pane',()=>{
 const h=setup(),html=h.run('editorView()');assert.doesNotMatch(html,/page-heading|<h1|data-action="print-dialog"|data-action="save-file"/);
 assert.ok(html.indexOf('id="canvas"')<html.indexOf('class="stack editor-inspector"'));
 assert.ok(html.indexOf('class="card bottom-grid"')<html.indexOf('class="stack editor-inspector"'));
 assert.equal((html.match(/<summary /g)||[]).length,3);
});
test('rerendering properties keeps both pane scroll positions and closed panels',()=>{
 const h=setup();h.run('renderView()');h.panes.get('.editor-inspector').scrollTop=640;h.panes.get('.editor-stage').scrollTop=120;h.panes.get('.editor-stage').scrollLeft=35;
 h.storage.set('studio-editor-panels:one',JSON.stringify({label:false}));h.run('page().width=24;renderView()');
 assert.equal(h.panes.get('.editor-inspector').scrollTop,640);assert.equal(h.panes.get('.editor-stage').scrollTop,120);assert.equal(h.panes.get('.editor-stage').scrollLeft,35);
 assert.match(h.content.innerHTML,/data-editor-panel="label" ><summary/);
 assert.match(h.content.innerHTML,/data-editor-panel="elements" open>/);
});
test('toolbar and editor workspace state are cleared when leaving the designer',()=>{
 const h=setup();h.run('renderView()');assert.ok(h.toolbar.innerHTML);assert.equal(h.classes.get('editor-workspace'),true);
 h.run("S.view='help';helpView=()=>'';renderView()");assert.equal(h.toolbar.innerHTML,'');assert.equal(h.classes.get('editor-workspace'),false);
});
test('panel preferences survive toggles and remain isolated by account',()=>{
 const h=setup(),target={matches:()=>true,isConnected:true,dataset:{editorPanel:'element'},open:false};
 for(const listener of h.events.get('toggle'))listener({target});assert.equal(h.run("editorPanelOpen('element')"),'');
 h.run("S.boot.user.id='two'");assert.equal(h.run("editorPanelOpen('element')"),'open');h.run("S.boot.user.id='one'");assert.equal(h.run("editorPanelOpen('element')"),'');
});
test('stale toggle events and corrupt or unavailable storage cannot break editing',()=>{
 const h=setup();h.storage.set('studio-editor-panels:one','invalid');assert.equal(h.run("editorPanelOpen('label')"),'open');
 for(const listener of h.events.get('toggle'))listener({target:{matches:()=>true,isConnected:false,dataset:{editorPanel:'label'},open:false}});
 assert.equal(h.storage.get('studio-editor-panels:one'),'invalid');
 h.box.localStorage.setItem=()=>{throw Error('storage disabled');};assert.doesNotThrow(()=>{for(const listener of h.events.get('toggle'))listener({target:{matches:()=>true,isConnected:true,dataset:{editorPanel:'label'},open:false}});});
});
