'use strict';
function editorToolbar(){
 const paths={print:'M6 8V3h12v5 M6 17H3V8h18v9h-3 M6 13h12v8H6z',standalone:'M5 3h14v18H5z M8 7h8 M8 11h8 M9 17h6',template:'M5 3h14v18l-7-4-7 4z',save:'M4 3h13l4 4v14H3V3z M7 3v6h9V3 M7 21v-8h10v8',new:'M12 4v16 M4 12h16'};
 return [['print-dialog','print','print'],['standalone','standalone','standalone'],['save-template','saveTemplate','template'],['save-file','saveFile','save'],['new','new','new']].map(([action,label,icon])=>`<button type="button" class="editor-icon ${action==='print-dialog'?'primary':''}" data-action="${action}" title="${h(t(label))}" aria-label="${h(t(label))}"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="${paths[icon]}"/></svg></button>`).join('');
}
function editorPanelKey(){return 'studio-editor-panels:'+S.boot.user.id;}
function editorPanelPreferences(){try{const value=JSON.parse(localStorage.getItem(editorPanelKey())||'{}');return value&&typeof value==='object'&&!Array.isArray(value)?value:{};}catch{return {};}}
function editorPanelOpen(name){return editorPanelPreferences()[name]===false?'':'open';}
document.addEventListener('toggle',event=>{
 const panel=event.target;
 if(!S.boot?.user||S.view!=='editor'||!panel.matches?.('details[data-editor-panel]'))return;
 if(!panel.isConnected)return;
 const name=panel.dataset.editorPanel;if(!['label','elements','element'].includes(name))return;
 const preferences=editorPanelPreferences();preferences[name]=panel.open;
 try{localStorage.setItem(editorPanelKey(),JSON.stringify(preferences));}catch{}
},true);
