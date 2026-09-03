'use strict';
const FRONTEND_BUILD='0.5.83';
const HTML_BUILD=document.querySelector('meta[name="torrent-dashboard-build"]')?.content||'';
const RECOVERY_KEY=`td-frontend-recovery-${FRONTEND_BUILD}`;
async function recoverFrontendBuild(reason){
  console.error('[Torrent Dashboard] Frontend build mismatch', {reason,htmlBuild:HTML_BUILD,scriptBuild:FRONTEND_BUILD});
  if(window.__tdFrontendRecoveryStarted)return;
  window.__tdFrontendRecoveryStarted=true;
  const attempts=Number(sessionStorage.getItem(RECOVERY_KEY)||0);
  if(attempts>=2){console.error('[Torrent Dashboard] Frontend recovery stopped after repeated mismatches');return}
  sessionStorage.setItem(RECOVERY_KEY,String(attempts+1));
  try{if('serviceWorker'in navigator){const registrations=await navigator.serviceWorker.getRegistrations();await Promise.all(registrations.map(registration=>registration.unregister()))}}catch(error){console.error('[Torrent Dashboard] Service worker cleanup failed',error)}
  try{if('caches'in window){const keys=await caches.keys();await Promise.all(keys.filter(key=>key.startsWith('torrent-dashboard-')).map(key=>caches.delete(key)))}}catch(error){console.error('[Torrent Dashboard] Cache cleanup failed',error)}
  const url=new URL(location.href);url.searchParams.set('td-recover',FRONTEND_BUILD);location.replace(url.toString())
}
if(HTML_BUILD!==FRONTEND_BUILD){recoverFrontendBuild('HTML and JavaScript builds do not match');throw new Error(`Torrent Dashboard frontend build mismatch: HTML ${HTML_BUILD||'unknown'}, JavaScript ${FRONTEND_BUILD}`)}
sessionStorage.removeItem(RECOVERY_KEY);
window.addEventListener('error',event=>console.error('[Torrent Dashboard] Uncaught error',event.error||event.message));
window.addEventListener('unhandledrejection',event=>console.error('[Torrent Dashboard] Unhandled promise rejection',event.reason));
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];

const UI_SPECIAL={torrentdashboard:'Torrent Dashboard',homeassistant:'Home Assistant',qbittorrent:'qBitTorrent',github:'GitHub',api:'API',ip:'IP',cidr:'CIDR',url:'URL',lan:'LAN',nic:'NIC',https:'HTTPS',http:'HTTP',ui:'UI',pwa:'PWA',exe:'EXE',eta:'ETA',id:'ID',pc:'PC',nas:'NAS',ntfy:'ntfy',sonarr:'Sonarr',radarr:'Radarr',lidarr:'Lidarr',prowlarr:'Prowlarr',jellyfin:'Jellyfin',plex:'Plex',discord:'Discord',windows:'Windows'};
function uiText(value=''){
  let s=String(value||'');if(!s)return s;
  const ell=s.endsWith('…');if(ell)s=s.slice(0,-1);
  s=s.replace(/Torrent Dashboard/gi,'torrentdashboard').replace(/Home Assistant/gi,'homeassistant').replace(/qBitTorrent/gi,'qbittorrent').replace(/GitHub/gi,'github');
  s=s.replace(/([a-z0-9])([A-Z])/g,'$1 $2').replace(/([A-Za-z])([0-9])/g,'$1 $2').replace(/([0-9])([A-Za-z])/g,'$1 $2').replace(/[_-]+/g,' ');
  let started=false;
  s=s.split(/\s+/).filter(Boolean).map(w=>{
    const special=UI_SPECIAL[w.toLowerCase()];
    if(special){if(/[A-Za-z]/.test(special))started=true;return special}
    if(/^\d/.test(w))return w;
    const lower=w.toLowerCase();
    if(!started&&/[A-Za-z]/.test(lower)){started=true;return lower.charAt(0).toUpperCase()+lower.slice(1)}
    return lower;
  }).join(' ');
  return s+(ell?'…':'')
}
function hasCamelCaseUiText(value=''){return /[a-z0-9][A-Z]/.test(String(value||''))}
function isLegacyUiToken(value=''){
  const s=String(value||'').trim();
  return hasCamelCaseUiText(s)||/^[a-z0-9]+(?:_[a-z0-9]+)+$/.test(s)
}
function displayUiText(value=''){const s=String(value??'');return isLegacyUiToken(s)?uiText(s):s}
const UI_MATERIAL_ICON_PATHS={
  chevron_right:'M9.29 6.71a.996.996 0 0 0 0 1.41L13.17 12l-3.88 3.88a.996.996 0 1 0 1.41 1.41l4.59-4.59a.996.996 0 0 0 0-1.41L10.7 6.7a.996.996 0 0 0-1.41.01Z',
  expand_more:'M7.41 8.59 12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41Z',
};
function materialIconSvg(name){const path=UI_MATERIAL_ICON_PATHS[name]||UI_MATERIAL_ICON_PATHS.expand_more;return `<svg class="material-symbol-icon" aria-hidden="true" viewBox="0 0 24 24"><path d="${path}"/></svg>`}
function normalizeUiAttributes(el){
  if(!el?.getAttribute)return;
  for(const attr of ['placeholder','title','aria-label']){
    const raw=el.getAttribute(attr);
    if(raw&&isLegacyUiToken(raw))el.setAttribute(attr,uiText(raw));
  }
}
function applySentenceCaseUi(root=document){
  const selectors='button,label,th,option,h1,h2,h3,h4,.panel-title,.settings-section-title,.eyebrow,.nav,.mobile-nav,.detail-tabs,legend,.metric span,.field-row b,.review-grid span,.update-status span,.brand strong,.brand small,.setup-rail strong,.setup-rail small,#setupSteps button';
  const els=[];
  if(root.matches?.(selectors))els.push(root);
  els.push(...(root.querySelectorAll?.(selectors)||[]));
  els.forEach(el=>{
    normalizeUiAttributes(el);
    for(const n of [...el.childNodes]){
      if(n.nodeType===Node.TEXT_NODE){
        const raw=n.nodeValue,trim=raw.trim();
        if(trim&&isLegacyUiToken(trim))n.nodeValue=raw.replace(trim,uiText(trim));
      }
    }
  });
  const attrEls=[];
  if(root.matches?.('[placeholder],[title],[aria-label]'))attrEls.push(root);
  attrEls.push(...(root.querySelectorAll?.('[placeholder],[title],[aria-label]')||[]));
  attrEls.forEach(normalizeUiAttributes);
}
const CONFIGURED_SECRET_MASK='••••••••••';
function setConfiguredSecretField(input,configured,emptyPlaceholder=''){
  if(!input)return;
  input.placeholder=emptyPlaceholder;
  input.value=configured?CONFIGURED_SECRET_MASK:'';
  input.classList.toggle('secret-configured',!!configured);
  if(configured)input.dataset.configuredSecret='1';else delete input.dataset.configuredSecret;
  input.setCustomValidity('');
  syncSecretToggle(input);
}
function secretFieldValue(input,preserve='<configured>'){
  if(!input)return'';
  const value=input.value.trim();
  if(input.dataset.configuredSecret==='1'){
    if(value===CONFIGURED_SECRET_MASK||value==='')return preserve;
    if(value.includes('•'))throw new Error('Delete the existing mask before entering a new secret');
  }
  return value;
}
function secretToggleSvg(name){
  if(name==='visibility_lock')return '<svg class="material-symbol-icon" aria-hidden="true" viewBox="0 0 24 24"><path d="M11 4.5C6.4 4.5 2.5 7.35 1 11.5c1.5 4.15 5.4 7 10 7 1.05 0 2.06-.15 3-.44V15.8a4.5 4.5 0 1 1 1.36-6.92A5.2 5.2 0 0 1 17 9.1V8.8C15.38 6.17 13.27 4.5 11 4.5Zm0 3A4 4 0 1 0 11 15.5 4 4 0 0 0 11 7.5Zm0 2A2 2 0 1 1 11 13.5 2 2 0 0 1 11 9.5Z"/><path d="M20.5 14h-.5v-1.25a2.5 2.5 0 0 0-5 0V14h-.5a1 1 0 0 0-1 1v4a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1v-4a1 1 0 0 0-1-1Zm-4-1.25a1 1 0 0 1 2 0V14h-2v-1.25Z"/></svg>';
  return '<svg class="material-symbol-icon" aria-hidden="true" viewBox="0 0 24 24"><path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5C21.27 7.61 17 4.5 12 4.5Zm0 12A4.5 4.5 0 1 1 12 7.5a4.5 4.5 0 0 1 0 9Zm0-7.2a2.7 2.7 0 1 0 0 5.4 2.7 2.7 0 0 0 0-5.4Z"/></svg>';
}
function setSecretToggleIcon(btn,name){btn.innerHTML=secretToggleSvg(name);btn.dataset.materialSymbol=name}
function syncSecretToggle(input){
  const wrap=input?.closest?.('.secret-input');
  const btn=wrap?.querySelector('.secret-toggle');
  if(!btn)return;
  const value=input.value||'';
  const stored=input.dataset.configuredSecret==='1'&&(value===CONFIGURED_SECRET_MASK||value===''||value.includes('•'));
  wrap.classList.toggle('stored-secret',stored);
  btn.hidden=stored;
  if(stored){
    input.type='password';
    btn.innerHTML='';
    btn.removeAttribute('aria-label');
    btn.removeAttribute('title');
    return;
  }
  const showing=input.type==='text';
  setSecretToggleIcon(btn,showing?'visibility_lock':'visibility');
  btn.setAttribute('aria-label',showing?'Hide secret':'Show secret');
  btn.title=showing?'Hide secret':'Show secret';
}
function decorateSecretFields(root=document){
  const fields=[];
  if(root.matches?.('input[type="password"]:not(.autofill-decoy):not([aria-hidden="true"])'))fields.push(root);
  fields.push(...(root.querySelectorAll?.('input[type="password"]:not(.autofill-decoy):not([aria-hidden="true"])')||[]));
  fields.forEach(input=>{
    if(input.dataset.secretReady==='1'){syncSecretToggle(input);return;}
    input.dataset.secretReady='1';
    const wrap=document.createElement('div');wrap.className='secret-input';
    input.parentNode.insertBefore(wrap,input);wrap.appendChild(input);
    const btn=document.createElement('button');btn.type='button';btn.className='secret-toggle';setSecretToggleIcon(btn,'visibility');btn.setAttribute('aria-label','Show secret');
    btn.addEventListener('click',()=>{const showing=input.type==='text';input.type=showing?'password':'text';syncSecretToggle(input)});
    input.addEventListener('input',()=>{
      if(input.dataset.configuredSecret==='1'){
        const value=input.value||'';
        if(value===CONFIGURED_SECRET_MASK||value==='')input.setCustomValidity('');
        else if(value.includes('•'))input.setCustomValidity('Delete the existing mask before entering a new secret.');
        else{delete input.dataset.configuredSecret;input.classList.remove('secret-configured');input.setCustomValidity('')}
      }
      syncSecretToggle(input);
    });
    wrap.appendChild(btn);
    syncSecretToggle(input);
  });
}
const caseObserver=new MutationObserver(records=>{for(const r of records){if(r.type==='attributes'){applySentenceCaseUi(r.target);continue}for(const n of r.addedNodes){if(n.nodeType===Node.ELEMENT_NODE){applySentenceCaseUi(n);decorateSecretFields(n)}else if(n.nodeType===Node.TEXT_NODE&&n.parentElement){applySentenceCaseUi(n.parentElement)}}}});

const LIVE_REFRESH_MS=1000;
const state={me:null,csrf:'',setup:null,setupStep:0,setupMaxStep:0,server:localStorage.tdServer||'all',torrents:[],transfer:{},meta:{},filter:localStorage.tdFilter||'all',sort:localStorage.tdSort||'added_desc',search:localStorage.tdSearch||'',category:localStorage.tdCategory||'',tag:localStorage.tdTag||'',tracker:localStorage.tdTracker||'',selected:new Set(),detail:null,detailExpanded:false,detailTab:'general',settings:null,lastComplete:new Set(),deferredPrompt:null,setupInterfaceSelectionInitialized:false,settingsInterfaceSelectionInitialized:false,updateInfo:null,notificationEvents:[]};

function esc(v=''){return String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function bytes(n,d=1){n=Number(n);if(!Number.isFinite(n)||n<0)return'—';if(n===0)return'0 B';const u=['B','KB','MB','GB','TB','PB'];let i=Math.min(Math.floor(Math.log(n)/Math.log(1024)),u.length-1);return`${(n/1024**i).toFixed(i?d:0)} ${u[i]}`}
function speed(n){return`${bytes(n)}/s`}
function eta(s){s=Number(s);if(!Number.isFinite(s)||s<0||s>=8640000)return'∞';let d=Math.floor(s/86400);s%=86400;let h=Math.floor(s/3600);s%=3600;let m=Math.floor(s/60);if(d)return`${d}d ${h}h`;if(h)return`${h}h ${m}m`;if(m)return`${m}m`;return`${Math.floor(s)}s`}
function when(ts){if(!ts)return'—';const d=new Date(Number(ts)*1000);return d.toLocaleString()}
function rel(ts){if(!ts)return'—';let s=Math.max(0,Date.now()/1000-ts);if(s<60)return`${Math.floor(s)}s ago`;if(s<3600)return`${Math.floor(s/60)}m ago`;if(s<86400)return`${Math.floor(s/3600)}h ago`;return`${Math.floor(s/86400)}d ago`}
function toast(msg,type=''){const el=document.createElement('div');el.className='toast '+type;el.textContent=displayUiText(msg);$('#toasts').append(el);setTimeout(()=>el.remove(),3800)}
let notificationAudio=null;
async function playSoundUrl(src){
  if(notificationAudio){try{notificationAudio.pause()}catch{}}
  const audio=new Audio(src);audio.preload='auto';audio.volume=.72;notificationAudio=audio;await audio.play();return audio
}
function configuredCompletionSoundUrl(){const n=state.settings?.notifications||{};return n.sound_mode==='custom'&&n.custom_sound_file?`/api/notification-sound?ts=${Date.now()}`:`/static/default-completion.wav?v=${encodeURIComponent(state.me?.version||'')}`}
async function playCompletionSound(){if(!state.settings?.notifications?.sound)return;const n=state.settings.notifications||{};try{return await playSoundUrl(configuredCompletionSoundUrl())}catch(e){if(n.sound_mode==='custom')return playSoundUrl(`/static/default-completion.wav?v=${encodeURIComponent(state.me?.version||'')}`);throw e}}
async function showBrowserNotification(title,options={}){if(!('Notification'in window))throw new Error('Browser notifications are not supported');if(Notification.permission!=='granted')throw new Error('Browser notification permission is not granted');if('serviceWorker'in navigator){try{const reg=await navigator.serviceWorker.ready;if(reg?.showNotification){await reg.showNotification(title,options);return}}catch{}}new Notification(title,options)}
async function api(url,opt={}){opt.headers={...(opt.headers||{})};if(opt.method&&opt.method!=='GET'&&opt.method!=='HEAD'&&state.csrf)opt.headers['X-CSRF-Token']=state.csrf;const r=await fetch(url,opt);let data;const ct=r.headers.get('content-type')||'';data=ct.includes('json')?await r.json():await r.text();if(r.status===401){showLogin();throw new Error(data.error||'Authentication required')}if(!r.ok)throw new Error(data.error||`HTTP ${r.status}`);return data}
async function post(url,obj){return api(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(obj)})}

function showLogin(reset=false){
  const login=$('#login'), entering=login.classList.contains('hidden');
  $('#setup').classList.add('hidden');$('#app').classList.add('hidden');login.classList.remove('hidden');
  if(reset||entering){$('#loginUser').value='';$('#loginPass').value='';}
}
function showApp(){ $('#setup').classList.add('hidden');$('#login').classList.add('hidden');$('#app').classList.remove('hidden') }
function showSetup(){ $('#login').classList.add('hidden');$('#app').classList.add('hidden');$('#setup').classList.remove('hidden') }
function showStartupFailure(error,stage='startup'){
  console.error(`[Torrent Dashboard] ${stage} failed`,error);
  const box=$('#startupFailure');if(!box)return;
  const message=$('#startupFailureMessage');if(message)message.textContent=`${error?.message||error||'Unknown error'} · Open the browser console for details.`;
  box.classList.remove('hidden');
}
const ADD_METADATA_POLL_MS=1000;
const ADD_METADATA_TIMEOUT_MS=120000;
const addMetadataState={generation:0,timer:null,source:'',startedAt:0,inFlight:false,mode:'magnet',file:null,metadata:null,files:[],collapsedFolders:new Set(),exportSource:'',exportHash:'',exportName:''};

function clearAddMetadataTimer(){if(addMetadataState.timer!==null){clearTimeout(addMetadataState.timer);addMetadataState.timer=null}}
function currentAddTorrentFile(){return addMetadataState.file||$('#torrentFile')?.files?.[0]||null}
function syncAddTorrentExport(){
  const button=$('#addSaveTorrent');if(!button)return;
  const localFile=addMetadataState.mode==='file'&&!!currentAddTorrentFile();
  button.disabled=!(localFile||addMetadataState.exportSource||addMetadataState.exportHash);
}
function syncAddSelectAll(){
  const selectAll=$('#addSelectAllFiles');if(!selectAll)return;
  const files=addMetadataState.files||[],selected=files.filter(file=>file.selected).length;
  selectAll.disabled=!files.length;
  selectAll.checked=!!files.length&&selected===files.length;
  selectAll.indeterminate=selected>0&&selected<files.length;
}
function cancelAddMetadata(){
  addMetadataState.generation+=1;clearAddMetadataTimer();addMetadataState.source='';addMetadataState.startedAt=0;addMetadataState.inFlight=false;
  addMetadataState.metadata=null;addMetadataState.files=[];addMetadataState.collapsedFolders.clear();addMetadataState.exportSource='';addMetadataState.exportHash='';addMetadataState.exportName='';
  syncAddTorrentExport();syncAddSelectAll()
}
function setAddMetadataStatus(title,text,stateName='idle'){
  const status=$('#addMetadataStatus'),progress=$('#addMetadataProgress');
  if($('#addMetadataStatusTitle'))$('#addMetadataStatusTitle').textContent=title;
  if($('#addMetadataStatusText'))$('#addMetadataStatusText').textContent=text;
  if(status)status.dataset.state=stateName;
  if(progress)progress.classList.toggle('hidden',stateName!=='loading');
}
function torrentExportFilename(metadata={}){
  const raw=metadata?.info?.name||metadata?.name||'torrent';
  let clean=String(raw).replace(/[\\/:*?"<>|]/g,'_').trim().replace(/[. ]+$/,'');
  if(!clean)clean='torrent';
  clean=clean.slice(0,220);
  return clean.toLowerCase().endsWith('.torrent')?clean:`${clean}.torrent`;
}
function setAddTorrentExport(source='',metadata={}){
  addMetadataState.exportSource=String(source||'');
  addMetadataState.exportHash=String(metadata?.hash||metadata?.infohash_v2||metadata?.infohash_v1||'');
  const file=currentAddTorrentFile();
  addMetadataState.exportName=addMetadataState.mode==='file'&&file?.name?file.name:(addMetadataState.exportSource||addMetadataState.exportHash?torrentExportFilename(metadata):'');
  syncAddTorrentExport();
}
function triggerTorrentFileDownload(blob,name){
  const href=URL.createObjectURL(blob),link=document.createElement('a');
  link.href=href;link.download=name||'torrent.torrent';document.body.appendChild(link);link.click();link.remove();
  setTimeout(()=>URL.revokeObjectURL(href),1000);
}
async function saveAddTorrentMetadata(){
  const button=$('#addSaveTorrent');if(!button)return;
  const localFile=addMetadataState.mode==='file'?currentAddTorrentFile():null;
  const source=addMetadataState.exportSource,hash=addMetadataState.exportHash;
  if(!localFile&&!source&&!hash)return;
  const generation=addMetadataState.generation,server=state.server,previous=button.textContent;
  button.disabled=true;button.textContent='Saving…';
  try{
    if(localFile){
      triggerTorrentFileDownload(localFile,localFile.name||addMetadataState.exportName||'torrent.torrent');
    }else{
      const params=new URLSearchParams({server});
      if(source)params.set('source',source);
      if(hash)params.set('hash',hash);
      const response=await fetch(`/api/torrent-metadata/save?${params}`,{method:'GET',cache:'no-store'});
      if(!response.ok){
        const type=response.headers.get('content-type')||'';
        const error=type.includes('json')?await response.json():await response.text();
        throw new Error(error?.error||error||`HTTP ${response.status}`);
      }
      const blob=await response.blob();
      if(!blob.size)throw new Error('qBitTorrent returned an empty torrent file');
      if(generation!==addMetadataState.generation||$('#addModal').classList.contains('hidden'))return;
      triggerTorrentFileDownload(blob,addMetadataState.exportName||'torrent.torrent');
    }
    toast('Torrent file saved');
  }catch(error){
    console.error('[Torrent Dashboard] Torrent metadata export failed',error);
    toast(error?.message||'Torrent file could not be saved','error');
  }finally{
    button.textContent=previous;
    syncAddTorrentExport();
  }
}
function resetAddMetadataInfo(){
  for(const id of ['addInfoSize','addInfoDate','addInfoHashV1','addInfoHashV2','addInfoCreatedBy','addInfoComment']){const el=$('#'+id);if(el)el.textContent='—'}
}
function renderAddMetadataInfo(metadata={}){
  const info=metadata?.info||{};
  $('#addInfoSize').textContent=Number.isFinite(Number(info.length))?bytes(Number(info.length)):'—';
  $('#addInfoDate').textContent=metadata?.creation_date?when(metadata.creation_date):'—';
  $('#addInfoHashV1').textContent=metadata?.infohash_v1||'—';
  $('#addInfoHashV2').textContent=metadata?.infohash_v2||'—';
  $('#addInfoCreatedBy').textContent=metadata?.created_by||'—';
  $('#addInfoComment').textContent=metadata?.comment||'—';
}
function addMetadataPriorityLabel(value){value=Number(value);if(value===0)return'Do not download';if(value===6)return'High';if(value===7)return'Maximum';return'Normal'}
function addPriorityOptions(value){
  return [[1,'Normal'],[6,'High'],[7,'Maximum']].map(([priority,label])=>`<option value="${priority}" ${Number(value)===priority?'selected':''}>${label}</option>`).join('');
}
function setAddMetadataFiles(metadata={}){
  const raw=Array.isArray(metadata?.info?.files)?metadata.info.files:[];
  addMetadataState.files=raw.map((file,index)=>{
    const rawPriority=Number(file?.priority),selected=rawPriority!==0,priority=[1,6,7].includes(rawPriority)?rawPriority:1;
    return{index,path:String(file?.path||`File ${index+1}`),length:Math.max(0,Number(file?.length)||0),selected,priority};
  });
  addMetadataState.collapsedFolders.clear();
}
function buildAddFileTree(files){
  const root={name:'',path:'',folders:new Map(),files:[]};
  for(const file of files){
    const parts=String(file.path||'').split('/').filter(Boolean),name=parts.pop()||file.path||`File ${file.index+1}`;
    let node=root,path=[];
    for(const part of parts){
      path.push(part);const key=path.join('/');
      if(!node.folders.has(part))node.folders.set(part,{name:part,path:key,folders:new Map(),files:[]});
      node=node.folders.get(part);
    }
    node.files.push({...file,displayName:name});
  }
  return root;
}
function addTreeNodeIndexes(node){
  const indexes=node.files.map(file=>file.index);
  for(const child of node.folders.values())indexes.push(...addTreeNodeIndexes(child));
  return indexes;
}
function addTreeNodeSize(node){
  let total=node.files.reduce((sum,file)=>sum+file.length,0);
  for(const child of node.folders.values())total+=addTreeNodeSize(child);
  return total;
}
function addContentFolderRow(node,depth){
  const indexes=addTreeNodeIndexes(node),files=indexes.map(index=>addMetadataState.files.find(file=>file.index===index)).filter(Boolean),selected=files.filter(file=>file.selected).length;
  const checked=!!files.length&&selected===files.length,collapsed=addMetadataState.collapsedFolders.has(node.path);
  return `<div class="add-content-row add-content-folder" data-add-depth="${depth}" style="--add-depth:${depth}"><span class="add-content-select"><input type="checkbox" data-add-folder-files="${indexes.join(',')}" ${checked?'checked':''} aria-label="Download folder ${esc(node.name)}"></span><span class="add-content-name"><button class="add-folder-toggle" data-add-folder-toggle="${esc(node.path)}" type="button" aria-label="${collapsed?'Expand':'Collapse'} folder ${esc(node.name)}" aria-expanded="${String(!collapsed)}">${materialIconSvg(collapsed?'chevron_right':'expand_more')}</button><span class="add-folder-name">${esc(node.name)}</span></span><span>${bytes(addTreeNodeSize(node))}</span><span aria-hidden="true"></span></div>`;
}
function addContentFileRow(file,depth){
  return `<div class="add-content-row add-content-file" data-add-depth="${depth}" style="--add-depth:${depth}"><span class="add-content-select"><input type="checkbox" data-add-file-check="${file.index}" ${file.selected?'checked':''} aria-label="Download file"></span><span class="add-content-name"><span class="add-tree-spacer" aria-hidden="true"></span>${esc(file.displayName||file.path)}</span><span>${bytes(file.length)}</span><span><select class="add-file-priority" data-add-file-priority="${file.index}" aria-label="File priority" ${file.selected?'':'disabled'}>${addPriorityOptions(file.priority)}</select></span></div>`;
}
function addContentTreeRows(node,depth=0){
  const rows=[],folders=[...node.folders.values()].sort((a,b)=>a.name.localeCompare(b.name,undefined,{numeric:true,sensitivity:'base'}));
  for(const folder of folders){
    rows.push(addContentFolderRow(folder,depth));
    if(!addMetadataState.collapsedFolders.has(folder.path))rows.push(...addContentTreeRows(folder,depth+1));
  }
  const files=[...node.files].sort((a,b)=>(a.displayName||a.path).localeCompare(b.displayName||b.path,undefined,{numeric:true,sensitivity:'base'}));
  for(const file of files)rows.push(addContentFileRow(file,depth));
  return rows;
}
function syncAddFolderCheckboxes(){
  const body=$('#addContentBody');if(!body)return;
  body.querySelectorAll('[data-add-folder-files]').forEach(input=>{
    const indexes=String(input.dataset.addFolderFiles||'').split(',').filter(Boolean).map(Number);
    const files=indexes.map(index=>addMetadataState.files.find(file=>file.index===index)).filter(Boolean),selected=files.filter(file=>file.selected).length;
    input.checked=!!files.length&&selected===files.length;input.indeterminate=selected>0&&selected<files.length;
  });
  syncAddSelectAll();
}
function renderAddTorrentContent(){
  const body=$('#addContentBody');if(!body)return;
  if(!addMetadataState.files.length){
    body.innerHTML='<div class="add-preview-empty"><strong>No files were reported</strong><span>qBitTorrent returned torrent metadata without a selectable file list.</span></div>';
    syncAddSelectAll();return;
  }
  const scrollTop=body.scrollTop,tree=buildAddFileTree(addMetadataState.files);
  body.innerHTML=addContentTreeRows(tree).join('');
  syncAddFolderCheckboxes();body.scrollTop=scrollTop;
}
function renderAddMetadataEmpty(title,text){
  const body=$('#addContentBody');if(body)body.innerHTML=`<div class="add-preview-empty"><strong>${esc(title)}</strong><span>${esc(text)}</span></div>`;
  syncAddSelectAll();
}
function renderAddMetadataIdle(){
  setAddTorrentExport();resetAddMetadataInfo();addMetadataState.metadata=null;addMetadataState.files=[];
  const fileMode=addMetadataState.mode==='file',summary=$('#addContentSummary');
  if(summary)summary.textContent=fileMode?'Choose a .torrent file to inspect its contents.':'Enter one magnet link or torrent URL to retrieve its metadata.';
  renderAddMetadataEmpty(fileMode?'Choose a .torrent file':'Waiting for a magnet link',fileMode?'Drop a .torrent file above or click the file area to browse.':'Paste a magnet link or torrent URL above to inspect its files.');
  setAddMetadataStatus('Metadata preview',fileMode?'Choose a .torrent file to begin.':'Enter a magnet link or torrent URL to begin.','idle');
}
function renderAddMetadataLoading(metadata={}){
  setAddTorrentExport();addMetadataState.metadata=null;addMetadataState.files=[];renderAddMetadataInfo(metadata);
  const summary=$('#addContentSummary');if(summary)summary.textContent='qBitTorrent is retrieving torrent metadata.';
  renderAddMetadataEmpty('Retrieving metadata…','File and folder selection will appear when qBitTorrent finishes retrieving the metadata.');
  setAddMetadataStatus('Retrieving metadata…','You can add the magnet now, or wait to choose individual files.','loading');
}
function renderAddMetadataComplete(metadata={},exportSource=''){
  addMetadataState.metadata=metadata||{};setAddTorrentExport(exportSource,metadata);renderAddMetadataInfo(metadata);setAddMetadataFiles(metadata);
  const info=metadata?.info||{},files=addMetadataState.files,summary=$('#addContentSummary');
  if(summary)summary.textContent=files.length?`${files.length} ${files.length===1?'file':'files'} · ${bytes(Number(info.length)||files.reduce((sum,file)=>sum+file.length,0))}`:(info.name||'Metadata retrieved');
  renderAddTorrentContent();
  setAddMetadataStatus('Metadata ready','Choose the files and folders to download, then add the torrent.','complete');
}
function renderAddMetadataError(message,title='Metadata preview unavailable'){
  setAddTorrentExport();addMetadataState.metadata=null;addMetadataState.files=[];
  const summary=$('#addContentSummary');if(summary)summary.textContent='The torrent can still be added without file selection.';
  renderAddMetadataEmpty(title,message);
  setAddMetadataStatus(title,message,'error');
}
function addMetadataSources(){
  if(addMetadataState.mode!=='magnet')return[];
  return $('#addUrls').value.split(/\r?\n/).map(value=>value.trim()).filter(Boolean);
}
function currentAddMetadataSource(){
  const sources=addMetadataSources();
  return sources.length===1?sources[0]:'';
}
function addTorrentFileKey(file){return file?`${file.name}\u0000${file.size}\u0000${file.lastModified}`:''}
function currentAddTorrentFileKey(){return addTorrentFileKey(currentAddTorrentFile())}
function parsedTorrentMetadata(result){
  const raw=result?.metadata;
  if(Array.isArray(raw))return raw[0]||{};
  return raw&&typeof raw==='object'?raw:{};
}
function syncAddSourceModeUi(){
  $$('[data-add-source]').forEach(button=>{const active=button.dataset.addSource===addMetadataState.mode;button.classList.toggle('active',active);button.setAttribute('aria-selected',String(active))});
  $$('[data-add-source-pane]').forEach(pane=>pane.classList.toggle('hidden',pane.dataset.addSourcePane!==addMetadataState.mode));
  const file=currentAddTorrentFile(),name=$('#addTorrentFileName');if(name)name.textContent=file?`${file.name} · ${bytes(file.size)}`:'No file selected';
}
function setAddSourceMode(mode,focus=true){
  mode=mode==='file'?'file':'magnet';
  if(addMetadataState.mode!==mode){cancelAddMetadata();addMetadataState.mode=mode}
  syncAddSourceModeUi();scheduleAddMetadataPreview(0);
  if(focus)setTimeout(()=>mode==='file'?$('#addTorrentDrop')?.focus():$('#addUrls')?.focus(),0);
}
function setAddTorrentFile(file){
  if(file&&!(String(file.name||'').toLowerCase().endsWith('.torrent')||file.type==='application/x-bittorrent'))return toast('Choose a .torrent file','error');
  addMetadataState.file=file||null;addMetadataState.mode='file';cancelAddMetadata();syncAddSourceModeUi();scheduleAddMetadataPreview(0);
}
function renderAddTorrentFileMetadataLoading(file){
  setAddTorrentExport();addMetadataState.metadata=null;addMetadataState.files=[];resetAddMetadataInfo();
  const summary=$('#addContentSummary');if(summary)summary.textContent=`Reading ${file?.name||'.torrent file'} with qBitTorrent.`;
  renderAddMetadataEmpty('Reading torrent metadata…','File and folder selection will appear as soon as the .torrent file is parsed.');
  setAddMetadataStatus('Reading torrent metadata…','The selected file remains available even if metadata preview fails.','loading');
}
async function parseAddTorrentFileMetadata(file,generation,fileKey){
  if(generation!==addMetadataState.generation||$('#addModal').classList.contains('hidden')||fileKey!==currentAddTorrentFileKey())return;
  addMetadataState.inFlight=true;
  try{
    const form=new FormData();form.append('server',state.server);form.append('torrents',file,file.name);
    const result=await api('/api/torrent-metadata/parse',{method:'POST',body:form});
    if(generation!==addMetadataState.generation||$('#addModal').classList.contains('hidden')||fileKey!==currentAddTorrentFileKey())return;
    const metadata=parsedTorrentMetadata(result);
    if(!metadata||!Object.keys(metadata).length)throw new Error('qBitTorrent returned no torrent metadata');
    renderAddMetadataComplete(metadata,metadata?.hash||'');
  }catch(error){
    if(generation!==addMetadataState.generation)return;
    console.error('[Torrent Dashboard] Add Torrent file metadata preview failed',error);
    renderAddMetadataError(error?.message||'The selected .torrent file could not be parsed.');
  }finally{
    if(generation===addMetadataState.generation)addMetadataState.inFlight=false;
  }
}
function scheduleAddMetadataPreview(delay=450){
  cancelAddMetadata();
  if($('#addModal').classList.contains('hidden'))return;
  if(addMetadataState.mode==='file'){
    const torrentFile=currentAddTorrentFile();
    if(!torrentFile){renderAddMetadataIdle();return}
    const fileKey=addTorrentFileKey(torrentFile);addMetadataState.source=fileKey;addMetadataState.startedAt=Date.now();
    const generation=addMetadataState.generation;renderAddTorrentFileMetadataLoading(torrentFile);
    addMetadataState.timer=setTimeout(()=>parseAddTorrentFileMetadata(torrentFile,generation,fileKey),Math.max(0,delay));return;
  }
  const sources=addMetadataSources();
  if(!sources.length){renderAddMetadataIdle();return}
  if(sources.length!==1){
    renderAddMetadataError('Add one magnet link or torrent URL at a time.','Multiple sources entered');return;
  }
  const source=sources[0];
  if(!/^(magnet:\?|https?:\/\/)/i.test(source)){
    renderAddMetadataError('Enter a magnet link or HTTP(S) torrent URL.','Unsupported torrent source');return;
  }
  addMetadataState.source=source;addMetadataState.startedAt=Date.now();
  const generation=addMetadataState.generation;renderAddMetadataLoading();
  addMetadataState.timer=setTimeout(()=>fetchAddMetadataPreview(source,generation),Math.max(0,delay));
}
async function fetchAddMetadataPreview(source,generation){
  if(generation!==addMetadataState.generation||$('#addModal').classList.contains('hidden')||source!==currentAddMetadataSource())return;
  if(Date.now()-addMetadataState.startedAt>ADD_METADATA_TIMEOUT_MS){
    renderAddMetadataError('Metadata retrieval exceeded two minutes. You can still add the torrent without file selection.','Metadata retrieval timed out');return;
  }
  addMetadataState.inFlight=true;
  try{
    const result=await post('/api/torrent-metadata/fetch',{server:state.server,source});
    if(generation!==addMetadataState.generation||$('#addModal').classList.contains('hidden')||source!==currentAddMetadataSource())return;
    if(result?.complete){renderAddMetadataComplete(result.metadata||{},source);return}
    renderAddMetadataLoading(result?.metadata||{});
    addMetadataState.timer=setTimeout(()=>fetchAddMetadataPreview(source,generation),ADD_METADATA_POLL_MS);
  }catch(error){
    if(generation!==addMetadataState.generation)return;
    console.error('[Torrent Dashboard] Add Torrent metadata preview failed',error);
    renderAddMetadataError(error?.message||'Metadata could not be retrieved.');
  }finally{
    if(generation===addMetadataState.generation)addMetadataState.inFlight=false;
  }
}
function closeAddTorrent(){cancelAddMetadata();$('#addModal').classList.add('hidden')}
function resetAddTorrentState(){
  cancelAddMetadata();addMetadataState.mode='magnet';addMetadataState.file=null;
  const input=$('#torrentFile');if(input)input.value='';
  syncAddSourceModeUi();renderAddMetadataIdle();
}
function syncAddTorrentOptions(){
  const automatic=$('#addAutoTmm')?.value==='true';
  const useDownloadPath=!!$('#addUseDownloadPath')?.checked;
  if($('#addPath'))$('#addPath').disabled=automatic;
  if($('#addUseDownloadPath'))$('#addUseDownloadPath').disabled=automatic;
  if($('#addDownloadPath'))$('#addDownloadPath').disabled=automatic||!useDownloadPath;
}
function bindAddTorrentUI(){
  const required=['addTorrentBtn','addModal','addForm','addUrls','torrentFile','addTorrentDrop','addTorrentFileName','addSourceMagnetTab','addSourceFileTab','addSelectAllFiles','addAutoTmm','addUseDownloadPath','addDownloadPath','addRename','addStartTorrent','addStopCondition','addToTop','addSeedMode','addSequential','addFirstLast','addContentLayout','addDlLimit','addUlLimit','addContentBody','addContentSummary','addMetadataStatus','addMetadataStatusTitle','addMetadataStatusText','addMetadataProgress','addInfoSize','addInfoDate','addInfoHashV1','addInfoHashV2','addInfoCreatedBy','addInfoComment','addSaveTorrent'];
  const missing=required.filter(id=>!document.getElementById(id));
  if(missing.length){console.error('[Torrent Dashboard] Add Torrent UI unavailable; missing elements',missing);return false}
  $('#addTorrentBtn').addEventListener('click',openAddTorrent);
  $('#addAutoTmm').addEventListener('change',syncAddTorrentOptions);$('#addUseDownloadPath').addEventListener('change',syncAddTorrentOptions);
  $$('[data-add-source]').forEach(button=>button.addEventListener('click',()=>setAddSourceMode(button.dataset.addSource)));
  $('#addUrls').addEventListener('input',()=>{if(addMetadataState.mode==='magnet')scheduleAddMetadataPreview()});
  $('#torrentFile').addEventListener('change',event=>setAddTorrentFile(event.target.files?.[0]||null));
  const drop=$('#addTorrentDrop');
  drop.addEventListener('click',()=>$('#torrentFile').click());
  for(const eventName of ['dragenter','dragover'])drop.addEventListener(eventName,event=>{event.preventDefault();event.stopPropagation();drop.classList.add('dragover')});
  for(const eventName of ['dragleave','drop'])drop.addEventListener(eventName,event=>{event.preventDefault();event.stopPropagation();drop.classList.remove('dragover')});
  drop.addEventListener('drop',event=>{const file=[...(event.dataTransfer?.files||[])].find(item=>String(item.name||'').toLowerCase().endsWith('.torrent'));if(file)setAddTorrentFile(file);else toast('Drop a .torrent file','error')});
  $('#addSelectAllFiles').addEventListener('change',event=>{for(const file of addMetadataState.files)file.selected=event.target.checked;renderAddTorrentContent()});
  $('#addContentBody').addEventListener('click',event=>{const toggle=event.target.closest('[data-add-folder-toggle]');if(!toggle)return;const path=toggle.dataset.addFolderToggle;if(addMetadataState.collapsedFolders.has(path))addMetadataState.collapsedFolders.delete(path);else addMetadataState.collapsedFolders.add(path);renderAddTorrentContent()});
  $('#addContentBody').addEventListener('change',event=>{
    const fileCheck=event.target.closest('[data-add-file-check]');
    if(fileCheck){const file=addMetadataState.files.find(item=>item.index===Number(fileCheck.dataset.addFileCheck));if(file)file.selected=fileCheck.checked;renderAddTorrentContent();return}
    const folderCheck=event.target.closest('[data-add-folder-files]');
    if(folderCheck){const indexes=String(folderCheck.dataset.addFolderFiles||'').split(',').filter(Boolean).map(Number),selected=folderCheck.checked;for(const file of addMetadataState.files)if(indexes.includes(file.index))file.selected=selected;renderAddTorrentContent();return}
    const priority=event.target.closest('[data-add-file-priority]');
    if(priority){const file=addMetadataState.files.find(item=>item.index===Number(priority.dataset.addFilePriority)),value=Number(priority.value);if(file&&[1,6,7].includes(value)){file.priority=value;file.selected=true}syncAddFolderCheckboxes()}
  });
  $('#addSaveTorrent').addEventListener('click',saveAddTorrentMetadata);
  $$('#addModal [data-modalclose]').forEach(element=>element.addEventListener('click',closeAddTorrent));
  $('#addForm').addEventListener('submit',addTorrent);
  syncAddTorrentOptions();syncAddSourceModeUi();renderAddMetadataIdle();return true;
}
let addTorrentDefaultsRequest=0;
async function loadAddTorrentClientDefaults(){
  const server=state.server,request=++addTorrentDefaultsRequest;
  const initial={save:$('#addPath').value,temp:$('#addDownloadPath').value,use:!!$('#addUseDownloadPath').checked};
  try{
    const data=await api(`/api/client-settings?server=${encodeURIComponent(server)}`);
    if(request!==addTorrentDefaultsRequest||state.server!==server||$('#addModal').classList.contains('hidden'))return;
    const downloads=data?.settings?.downloads||{};
    if($('#addPath').value===initial.save)$('#addPath').value=downloads.save_path||'';
    if($('#addDownloadPath').value===initial.temp)$('#addDownloadPath').value=downloads.temp_path||'';
    if(!!$('#addUseDownloadPath').checked===initial.use)$('#addUseDownloadPath').checked=!!downloads.temp_path_enabled;
    syncAddTorrentOptions();
  }catch(error){console.error('[Torrent Dashboard] Could not load Add Torrent client defaults',error)}
}
function openAddTorrent(){
  if(state.server==='all')return toast('Select a specific client first','error');
  $('#addModal').classList.remove('hidden');syncAddTorrentOptions();syncAddSourceModeUi();loadAddTorrentClientDefaults();scheduleAddMetadataPreview(0);
  setTimeout(()=>addMetadataState.mode==='file'?$('#addTorrentDrop')?.focus():$('#addUrls')?.focus(),0);
}

async function rawJson(url,opt={}){const r=await fetch(url,opt);const data=await r.json().catch(()=>({}));if(!r.ok)throw new Error(data.error||`HTTP ${r.status}`);return data}
function parseWhitelist(selector){return $(selector).value.split(/\n|,/).map(x=>x.trim()).filter(Boolean)}
function selectedInterfaceIds(target){return $$(`${target} input[data-interface-id]:checked`).map(x=>x.dataset.interfaceId)}
function setupServer(){return{type:'qbittorrent',name:$('#wClientName').value.trim()||'qBitTorrent',base_url:$('#wClientUrl').value.trim(),auth_method:$('#wClientAuth').value,api_key:$('#wClientApiKey').value.trim(),username:$('#wClientUser').value.trim(),password:$('#wClientPass').value,enabled:true}}
function setupPayload(){return{setup_code:$('#wSetupCode').value.trim(),dashboard:{title:$('#wTitle').value.trim()||'Torrent Dashboard',port:Number($('#wPort').value||state.setup?.port||8765)},auth:{mode:$('#wAuthMode').value,username:$('#wDashUser').value.trim()||'admin',password:$('#wDashPass').value,trusted_interfaces:selectedInterfaceIds('#wInterfaceList'),trusted_ips:parseWhitelist('#wTrustedIps')},servers:[setupServer()]}}

function interfaceCard(item,checked){const label=item.interface||item.interface_id||'Network interface',gateway=item.gateway?` · Gateway ${esc(item.gateway)}`:'',def=item.default?'<span class="interface-default">Default route</span>':'';return`<label class="interface-card"><input type="checkbox" data-interface-id="${esc(item.interface_id||item.interface||'')}" ${checked?'checked':''}><div><div class="interface-title"><b>${esc(label)}</b>${def}</div><span>${esc(item.address||'—')} · ${esc(item.cidr||uiText('unknownSubnet'))}${gateway}</span><small>${esc(item.netmask||'')} ${item.range_start?`· ${esc(item.range_start)}–${esc(item.range_end)}`:''}</small></div></label>`}
function renderInterfaceList(target,interfaces,selected=[],autoSelectDefault=false){const el=$(target);if(!el)return;interfaces=interfaces||[];const selectedSet=new Set(selected||[]);if(autoSelectDefault&&!selectedSet.size&&interfaces.length){const d=interfaces.find(x=>x.default)||interfaces[0];if(d)selectedSet.add(d.interface_id||d.interface)}if(!interfaces.length){el.innerHTML='<div class="interface-empty"><b>No network interfaces detected</b><span>You can still add allowed IP addresses below.</span></div>';return}el.innerHTML=interfaces.map(x=>interfaceCard(x,selectedSet.has(x.interface_id||x.interface))).join('')}
async function refreshSetupInterfaces(force=false){const current=selectedInterfaceIds('#wInterfaceList');const d=await rawJson(`/api/setup/network-interfaces?refresh=${force?'1':'0'}`);state.setup.network_interfaces=d.interfaces||[];renderInterfaceList('#wInterfaceList',state.setup.network_interfaces,current,current.length===0&&!state.setupInterfaceSelectionInitialized);state.setupInterfaceSelectionInitialized=true}
async function refreshSettingsInterfaces(force=false){const current=selectedInterfaceIds('#sInterfaceList');const d=await api(`/api/network/interfaces?refresh=${force?'1':'0'}`);if(state.settings?.runtime)state.settings.runtime.network_interfaces=d.interfaces||[];renderInterfaceList('#sInterfaceList',d.interfaces||[],current,false)}


function updateSetupStep(){const pages=$$('.setup-page'),items=$$('#setupSteps li'),last=pages.length-1;state.setupMaxStep=Math.max(state.setupMaxStep,state.setupStep);pages.forEach((p,i)=>p.classList.toggle('active',i===state.setupStep));items.forEach((x,i)=>{x.classList.toggle('active',i===state.setupStep);x.classList.toggle('done',i<state.setupMaxStep);const b=x.querySelector('[data-setup-step]');if(b){b.setAttribute('aria-current',i===state.setupStep?'step':'false');b.title=uiText(i===state.setupStep?'currentStep':'goToSetupStep')}});$('#wBack').classList.toggle('hidden',state.setupStep===0);$('#wNext').textContent=state.setupStep===last?'Finish':'Next';if(state.setupStep===last)renderSetupReview();$('#setupError').textContent=''}
function validateSetupStep(step=state.setupStep){if(step===0){if(!$('#wTitle').value.trim())throw new Error('Enter a dashboard name');const port=Number($('#wPort').value);if(!Number.isInteger(port)||port<1||port>65535)throw new Error('Enter a valid dashboard port')}if(step===1){const mode=$('#wAuthMode').value;if(mode!=='disabled'){if(!$('#wDashUser').value.trim())throw new Error('Enter an administrator username');if(!$('#wDashPass').value)throw new Error('Create an administrator password');if($('#wDashPass').value!==$('#wDashPass2').value)throw new Error('Passwords do not match')}if(mode==='lan_bypass'&&!selectedInterfaceIds('#wInterfaceList').length&&!parseWhitelist('#wTrustedIps').length)throw new Error('Select a trusted network interface or add an allowed IP address')}if(step===2){if(!$('#wClientUrl').value.trim())throw new Error('Enter the qBitTorrent Web UI URL');if($('#wClientAuth').value==='api_key'){const key=$('#wClientApiKey').value.trim();if(!key)throw new Error('Enter a qBitTorrent API key');if(!/^qbt_[A-Za-z0-9]{28}$/.test(key))throw new Error('The qBitTorrent API key format is invalid')}else{if(!$('#wClientUser').value.trim())throw new Error('Enter the qBitTorrent username');if(!$('#wClientPass').value)throw new Error('Enter the qBitTorrent password')}}}
function validateSetupThrough(step){for(let i=0;i<=step;i++)validateSetupStep(i)}
function goToSetupStep(target){const last=$$('.setup-page').length-1;target=Math.max(0,Math.min(last,Number(target)));$('#setupError').textContent='';try{if(target>state.setupStep){for(let i=state.setupStep;i<target;i++)validateSetupStep(i)}state.setupStep=target;state.setupMaxStep=Math.max(state.setupMaxStep,target);updateSetupStep()}catch(e){$('#setupError').textContent=e.message}}
function renderSetupReview(){
  const p=setupPayload(),mode={required:'Required everywhere',lan_bypass:'Bypass for trusted addresses',disabled:'Disabled'}[p.auth.mode]||uiText(p.auth.mode),client=p.servers[0],clientAuth=client.auth_method==='api_key'?'API key':'Username and password',interfaceNames=p.auth.trusted_interfaces.length?p.auth.trusted_interfaces.join(', '):'None',allowedIps=p.auth.trusted_ips.length?`${p.auth.trusted_ips.length} allowed IP ${p.auth.trusted_ips.length===1?'address':'addresses'}`:'No allowed IP addresses';
  $('#wReview').innerHTML=`<div><span>Dashboard</span><b>${esc(p.dashboard.title)}</b><small>${esc($('#wLocalIp').value)}:${p.dashboard.port}</small></div><div><span>Dashboard access</span><b>${esc(mode)}</b><small>${esc(interfaceNames)} · ${esc(allowedIps)}</small></div><div><span>Administrator</span><b>${esc(p.auth.username)}</b><small>The first setup account is an administrator.</small></div><div><span>Download client</span><b>${esc(client.name)}</b><small>${esc(client.base_url)}</small></div><div><span>qBitTorrent authentication</span><b>${esc(clientAuth)}</b><small>${client.auth_method==='api_key'?'Bearer API key · no login cookie':esc(client.username)}</small></div>`;
  applySentenceCaseUi($('#wReview'));
}
function updateWizardClientAuth(){const useApi=$('#wClientAuth').value==='api_key';$('#wClientApiWrap').classList.toggle('hidden',!useApi);$('#wClientPasswordWrap').classList.toggle('hidden',useApi);$('#wClientResult').className='test-result muted';$('#wClientResult').textContent='Not tested yet'}
function updateWizardLanVisibility(){const enabled=$('#wAuthMode').value==='lan_bypass';$('#wLanTrust').classList.toggle('hidden',!enabled)}
async function testSetupClient(){const out=$('#wClientResult');out.className='test-result muted';out.textContent=uiText('testing…');try{const d=await rawJson('/api/setup/test-client',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({setup_code:$('#wSetupCode').value.trim(),server:setupServer()})});out.className='test-result ok';out.textContent=`Connected · qBitTorrent ${d.version||'unknown'} · Web API ${d.api_version||'unknown'}`}catch(e){out.className='test-result bad';out.textContent=e.message;throw e}}
async function finishSetup(e){if(e?.preventDefault)e.preventDefault();$('#setupError').textContent='';const btn=$('#wNext');try{validateSetupThrough(2);btn.disabled=true;btn.textContent='Testing and saving…';await rawJson('/api/setup/complete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(setupPayload())});location.reload()}catch(err){$('#setupError').textContent=err.message||'Setup could not be completed.';btn.disabled=false;btn.textContent='Finish';$('#setupError').scrollIntoView({behavior:'smooth',block:'nearest'})}}
function bindPublicUI(){if(window.__tdPublicBound)return;window.__tdPublicBound=true;$('#loginForm').addEventListener('submit',async e=>{e.preventDefault();$('#loginError').textContent='';try{await post('/api/login',{username:$('#loginUser').value,password:$('#loginPass').value});location.reload()}catch(err){$('#loginError').textContent=err.message}});$('#setupForm').addEventListener('submit',e=>e.preventDefault());$('#wBack').addEventListener('click',()=>goToSetupStep(state.setupStep-1));$('#wNext').addEventListener('click',()=>{const last=$$('.setup-page').length-1;if(state.setupStep===last){finishSetup();return}goToSetupStep(state.setupStep+1)});$('#setupSteps').addEventListener('click',e=>{const b=e.target.closest('[data-setup-step]');if(b)goToSetupStep(Number(b.dataset.setupStep))});$('#wTestClient').addEventListener('click',()=>testSetupClient().catch(()=>{}));$('#wClientAuth').addEventListener('change',updateWizardClientAuth);$('#wAuthMode').addEventListener('change',()=>{$('#wizardAccount').classList.toggle('hidden',$('#wAuthMode').value==='disabled');updateWizardLanVisibility()});$('#wRefreshInterfaces').addEventListener('click',()=>refreshSetupInterfaces(true).catch(e=>$('#setupError').textContent=e.message));}

async function bootstrap(){
  bindPublicUI();
  try{
    state.setup=await rawJson('/api/setup/status');
    if(state.setup.required){showSetup();$('#wLocalIp').value=state.setup?.lan_ip||'127.0.0.1';$('#wPort').value=state.setup?.port||8765;$('#wTrustedIps').value=(state.setup.trusted_ips||[]).join('\n');renderInterfaceList('#wInterfaceList',state.setup.network_interfaces||[],state.setup.trusted_interfaces||[],!(state.setup.trusted_interfaces||[]).length);state.setupInterfaceSelectionInitialized=true;$('#setupCodeWrap').classList.toggle('hidden',!state.setup.code_required);updateWizardClientAuth();updateWizardLanVisibility();updateSetupStep();return}
    state.me=await api('/api/me');state.csrf=state.me.csrf;showApp();
    document.body.classList.toggle('standard-user',!state.me.can_manage);
    $('#brandTitle').textContent=state.me.title;$('#brandAddress').textContent=state.me.lan_ip||'Local';document.title=state.me.title;$('#version').textContent=`v${state.me.version}`;
    if(state.me.user_id){try{const account=await api('/api/account');applyAccountUser(account.user)}catch{}}
    syncCurrentUserUi();
    if(state.me.can_manage){await loadSettings()}else{state.settings={dashboard:{low_disk_gb:20},notifications:{browser:false,sound:false}}}
    await loadServers();bindUI();applyPrefs();if(state.server!=='all')await loadMeta();await refreshStatus();scheduleRefresh();registerPwa();
  }
  catch(e){if(!$('#login').classList.contains('hidden'))return;showStartupFailure(e,'bootstrap')}
}

let bound=false;
function bindUI(){if(bound)return;
  $('#homeBrand').addEventListener('click',()=>setView('dashboard'));
  $$('.nav-root,.settings-subnav button,.mobile-nav button').forEach(b=>b.addEventListener('click',()=>setView(b.dataset.view)));
  $$('#tabs button').forEach(b=>b.classList.toggle('active',b.dataset.filter===state.filter));$$('#tabs button').forEach(b=>b.addEventListener('click',()=>{state.filter=b.dataset.filter;localStorage.tdFilter=state.filter;$$('#tabs button').forEach(x=>x.classList.toggle('active',x===b));render()}));
  $('#search').value=state.search;$('#search').addEventListener('input',e=>{state.search=e.target.value.trim().toLowerCase();localStorage.tdSearch=state.search;render()});
  $('#categoryFilter').addEventListener('change',e=>{state.category=e.target.value;localStorage.tdCategory=state.category;render()});
  $('#tagFilter').addEventListener('change',e=>{state.tag=e.target.value;localStorage.tdTag=state.tag;render()});
  $('#trackerFilter').addEventListener('change',e=>{state.tracker=e.target.value;localStorage.tdTracker=state.tracker;render()});
  $('#sort').value=state.sort;$('#sort').addEventListener('change',e=>{state.sort=e.target.value;localStorage.tdSort=state.sort;render()});
  $('#serverSelect').addEventListener('change',async e=>{state.server=e.target.value;localStorage.tdServer=state.server;state.selected.clear();resetDetailPane();await refreshStatus();if(state.server!=='all')await loadMeta();if($('#view-notifications')?.classList.contains('active'))renderNotifications()});
  $('#selectAll').addEventListener('change',e=>{visibleTorrents().forEach(t=>e.target.checked?state.selected.add(keyFor(t)):state.selected.delete(keyFor(t)));render()});
  $('#torrentRows').addEventListener('click',rowClick);$('#torrentRows').addEventListener('change',rowChange);$('#torrentRows').addEventListener('contextmenu',rowContext);
  $('#bulkbar').addEventListener('click',e=>{if(e.target.closest('[data-bulk-clear]')){state.selected.clear();render();return}const a=e.target.closest('[data-bulk]')?.dataset.bulk;if(a)bulkAction(a)});
  bindAddTorrentUI();$('#removeForm')?.addEventListener('submit',e=>{e.preventDefault();closeRemoveDialog({deleteFiles:!!$('#removeFiles')?.checked})});$$('[data-remove-cancel]').forEach(x=>x.addEventListener('click',()=>closeRemoveDialog(null)));
  $('#detailHandle').addEventListener('click',toggleDetailPane);$$('[data-detailtab]').forEach(x=>x.addEventListener('click',()=>{state.detailTab=x.dataset.detailtab;$$('[data-detailtab]').forEach(b=>b.classList.toggle('active',b===x));renderDetail()}));
  $('#profileBtn').addEventListener('click',e=>{showMenu($('#accountMenu'),e.currentTarget);e.currentTarget.setAttribute('aria-expanded','true')});document.addEventListener('click',e=>{if(!e.target.closest('.menu')&&!e.target.closest('#profileBtn')&&!e.target.closest('.more-row')){$$('.menu').forEach(m=>m.classList.add('hidden'));$('#profileBtn')?.setAttribute('aria-expanded','false')}});
  $('#accountSettingsBtn').addEventListener('click',()=>{hideAccountMenu();openAccountModal('profile')});$('#logoutBtn').addEventListener('click',()=>{hideAccountMenu();signOut()});$$('[data-account-close]').forEach(x=>x.addEventListener('click',closeAccountModal));$('#accountProfileForm').addEventListener('submit',saveOwnProfile);$('#accountPasswordForm').addEventListener('submit',changeOwnPassword);$('#accountChooseAvatar').addEventListener('click',()=>$('#accountAvatarInput').click());$('#accountAvatarInput').addEventListener('change',uploadOwnAvatar);$('#accountRemoveAvatar').addEventListener('click',removeOwnAvatar);bindPasswordConfirmation();
  $('#pauseAllBtn').addEventListener('click',()=>globalAction('stop'));$('#resumeAllBtn').addEventListener('click',()=>globalAction('start'));
  $('#notificationFilter')?.addEventListener('change',renderNotifications);$('#refreshNotifications')?.addEventListener('click',loadNotifications);
  if(state.me?.can_manage)TDSettings.bind();
  window.addEventListener('keydown',e=>{if(e.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){e.preventDefault();$('#search').focus()}if(e.key==='Escape'){if(!$('#passwordConfirmModal')?.classList.contains('hidden')){closePasswordConfirmation(null);return}if(!$('#clientSettingsModal')?.classList.contains('hidden')){TDSettings.closeClientSettings();return}if(!$('#accountModal')?.classList.contains('hidden')){closeAccountModal();return}if(!$('#accountMenu')?.classList.contains('hidden')){hideAccountMenu();return}if(!$('#actionDialogModal')?.classList.contains('hidden')){closeActionDialog(null);return}if(!$('#removeModal')?.classList.contains('hidden')){closeRemoveDialog(null);return}if(!$('#addModal')?.classList.contains('hidden')){closeAddTorrent();return}if(state.selected.size){state.selected.clear();render();return}if(state.detailExpanded){state.detailExpanded=false;syncDetailDock()}}});
  bound=true;
}

function setSettingsNavExpanded(expanded){const group=$('#settingsNavGroup'),submenu=$('#settingsSubnav');if(!group||!submenu)return;group.classList.toggle('expanded',!!expanded);submenu.classList.toggle('hidden',!expanded)}
function setView(view){if(view==='settings'&&!state.me?.can_manage){view='dashboard';toast('Administrator access is required','error')}const settingsView=view==='settings',dashboardView=view==='dashboard';$$('.view').forEach(v=>v.classList.toggle('active',v.id===`view-${view}`));$$('.nav-root,.mobile-nav button').forEach(b=>b.classList.toggle('active',b.dataset.view===view));setSettingsNavExpanded(settingsView);$('#pageTitle').textContent=uiText(view);$('#subtitle').textContent=uiText(view==='dashboard'?'liveTorrentActivity':view==='notifications'?'recentDashboardActivity':'dashboardConfiguration');if(dashboardView)requestAnimationFrame(syncTorrentWorkspaceLayout);if(view==='notifications')loadNotifications();if(settingsView){TDSettings.activate(localStorage.tdSettingsPage||'general');loadSettings().then(()=>TDSettings.loadExtras())}}

function preferredServer(enabled=[]){
  if(enabled.length===1)return String(enabled[0].id);
  const saved=String(localStorage.tdServer||state.server||'all');
  return saved==='all'||enabled.some(server=>String(server.id)===saved)?saved:'all'
}
async function loadServers(){
  const d=await api('/api/servers'),enabled=(d.servers||[]).filter(server=>server.enabled),sel=$('#serverSelect');
  const includeAll=enabled.length!==1;
  sel.innerHTML=(includeAll?'<option value="all">All servers</option>':'')+enabled.map(server=>`<option value="${esc(server.id)}">${esc(server.name)}</option>`).join('');
  state.server=preferredServer(enabled);sel.value=state.server;localStorage.tdServer=state.server
}
async function loadSettings(){try{state.settings=await api('/api/settings');fillSettings()}catch(e){toast(e.message,'error')}}
function fillSettings(){if(!state.settings)return;TDSettings.fill(state.settings)}
function updateActionButton(data=state.updateInfo){const b=$('#updateAction');if(!b)return;const st=data?.state||state.settings?.runtime?.updateState||{};b.classList.remove('primary','secondary');if(st.state==='readyToInstall'){b.disabled=false;b.classList.add('primary');b.textContent=uiText('installUpdate');return}if(st.state==='downloading'){b.disabled=true;b.classList.add('secondary');b.textContent=uiText('downloading…');return}if(st.state==='installing'){b.disabled=true;b.classList.add('primary');b.textContent=uiText('installing…');return}b.disabled=false;b.classList.add('secondary');b.textContent=uiText('checkForUpdates')}
function renderPatchMarkdown(box,markdown=''){
  box.replaceChildren();let list=null;
  for(const raw of String(markdown||'').replace(/\r/g,'').split('\n')){const line=raw.trim();if(!line){list=null;continue}const heading=line.match(/^(#{2,4})\s+(.+)$/);if(heading){list=null;const el=document.createElement(heading[1].length===2?'h4':'h5');el.textContent=heading[2];box.appendChild(el);continue}if(line.startsWith('- ')){if(!list){list=document.createElement('ul');box.appendChild(list)}const li=document.createElement('li');li.textContent=line.slice(2);list.appendChild(li);continue}list=null;const p=document.createElement('p');p.textContent=line;box.appendChild(p)}
}
function updateVersionParts(value=''){return String(value||'').replace(/^v/i,'').split(/[+-]/,1)[0].split('.').map(x=>Number(x)||0)}
function compareUpdateVersions(a,b){const aa=updateVersionParts(a),bb=updateVersionParts(b),n=Math.max(aa.length,bb.length);for(let i=0;i<n;i++){const d=(aa[i]||0)-(bb[i]||0);if(d)return d}return 0}
function releaseDisplayDate(value=''){if(!value)return'';const raw=String(value);const date=new Date(/^\d{4}-\d{2}-\d{2}$/.test(raw)?`${raw}T12:00:00Z`:raw);if(Number.isNaN(date.getTime()))return raw.slice(0,10);return new Intl.DateTimeFormat(undefined,{year:'numeric',month:'short',day:'numeric'}).format(date)}
function normalizedReleaseHistory(history=[],manifest={}){
  const entries=Array.isArray(history)?history.filter(x=>x&&x.version).map(x=>({...x,version:String(x.version).replace(/^v/i,'')})):[];
  if(manifest?.version){
    const version=String(manifest.version).replace(/^v/i,'');
    const remote={version,title:manifest.title||`Torrent Dashboard v${version}`,publishedAt:manifest.publishedAt||'',channel:manifest.channel||'',notes:manifest.notes||'',sha256:manifest.asset?.sha256||'',package:manifest.asset?.name||'',source:'github'};
    const i=entries.findIndex(x=>x.version===version);
    if(i>=0){const existing=entries[i];entries[i]={...existing,publishedAt:remote.publishedAt||existing.publishedAt,channel:remote.channel||existing.channel,notes:remote.notes||existing.notes,sha256:remote.sha256||existing.sha256,package:remote.package||existing.package,source:'github'}}
    else entries.push(remote);
  }
  const seen=new Set();
  return entries.sort((a,b)=>compareUpdateVersions(b.version,a.version)).filter(x=>{if(seen.has(x.version))return false;seen.add(x.version);return true}).slice(0,2)
}
function renderUpdateHistory(history=[],manifest={},currentVersion=''){
  const wrap=$('#updateNotesWrap'),list=$('#updateNotesList');if(!wrap||!list)return;
  const entries=normalizedReleaseHistory(history,manifest);wrap.classList.toggle('hidden',!entries.length);list.replaceChildren();
  const current=String(currentVersion||'').replace(/^v/i,'');
  entries.forEach((entry,index)=>{
    const article=document.createElement('article');article.className=`update-release${index===0?' featured':''}`;
    const summary=document.createElement('button');summary.type='button';summary.className='update-release-summary';
    const open=index===0;summary.setAttribute('aria-expanded',String(open));
    const version=document.createElement('span');version.className='update-release-version';version.textContent=`v${entry.version}`;
    const copy=document.createElement('span');copy.className='update-release-copy';
    const title=document.createElement('strong');title.textContent=entry.title||`Torrent Dashboard ${entry.version}`;copy.appendChild(title);
    const meta=document.createElement('span');meta.className='update-release-meta';
    const badge=(text,kind='')=>{const el=document.createElement('span');el.className=`update-release-badge${kind?` ${kind}`:''}`;el.textContent=text;meta.appendChild(el)};
    if(index===0)badge('Latest release','latest');
    if(entry.version===current)badge('Installed','installed');
    if(entry.channel)badge(entry.channel==='prerelease'?'Pre-release':'Stable',entry.channel==='prerelease'?'prerelease':'stable');
    if(entry.publishedAt){const date=document.createElement('small');date.className='update-release-date';date.textContent=releaseDisplayDate(entry.publishedAt);meta.appendChild(date)}
    copy.appendChild(meta);
    const chevron=document.createElement('span');chevron.className='update-release-chevron';chevron.innerHTML=materialIconSvg('expand_more');summary.append(version,copy,chevron);
    const body=document.createElement('div');body.className=`update-release-body${open?'':' hidden'}`;
    const notes=document.createElement('div');notes.className='update-release-notes';
    const noteText=String(entry.notes||entry.summary||'No patch notes were recorded for this revision.').replace(/^##\s+[^\n]+\n*/,'').trim();
    renderPatchMarkdown(notes,noteText||entry.summary||'No patch notes were recorded for this revision.');body.appendChild(notes);
    if(/^[0-9a-f]{64}$/i.test(String(entry.sha256||''))){
      const integrity=document.createElement('div');integrity.className='update-release-integrity';
      const integrityCopy=document.createElement('div');integrityCopy.className='update-release-integrity-copy';
      const integrityLabel=document.createElement('span');integrityLabel.textContent='Package SHA-256';
      const integrityHash=document.createElement('code');integrityHash.textContent=String(entry.sha256).toLowerCase();
      integrityCopy.append(integrityLabel,integrityHash);
      const copyButton=document.createElement('button');copyButton.type='button';copyButton.className='secondary small-btn update-hash-copy';copyButton.textContent='Copy';copyButton.title='Copy package SHA-256';
      copyButton.addEventListener('click',async event=>{event.stopPropagation();try{await navigator.clipboard.writeText(integrityHash.textContent);toast('Package SHA-256 copied')}catch{toast('Could not copy SHA-256','error')}});
      integrity.append(integrityCopy,copyButton);body.appendChild(integrity);
    }
    summary.addEventListener('click',()=>{const next=body.classList.contains('hidden');body.classList.toggle('hidden',!next);summary.setAttribute('aria-expanded',String(next))});
    article.append(summary,body);list.appendChild(article)
  })
}
function renderUpdateInfo(data){state.updateInfo=data||null;const current=data?.currentVersion||state.me?.version||'—',manifest=data?.manifest||{},st=data?.state||state.settings?.runtime?.updateState||{};$('#updateCurrent').textContent=current;$('#updateLatest').textContent=manifest.version||st.version||uiText('notChecked');$('#updateState').textContent=uiText(st.state||'idle');const msg=$('#updateMessage');msg.className='muted update-message';let text='';if(data?.error){text=data.error;msg.classList.add('bad')}else if(data?.configured===false){text=data?.error||'Enter and save a public GitHub repository under Updates before checking for updates'}else if(st.state==='readyToInstall'){text=`updateReadyToInstall ${st.version||manifest.version||''}`;msg.classList.add('ok')}else if(data?.updateAvailable){text=`updateAvailable ${manifest.version}${manifest.publishedAt?` · ${manifest.publishedAt}`:''}`;msg.classList.add('ok')}else if(manifest.version){text=`upToDate ${current}`;msg.classList.add('ok')}else if(st.state&&st.state!=='idle'){text=st.error||st.state}else{text='checkForUpdatesWhenReady'}msg.textContent=data?.error?text:uiText(text);renderUpdateHistory(data?.releaseHistory||state.settings?.runtime?.releaseHistory||[],manifest,current);updateActionButton(data)}
async function checkForUpdates(silent=false){try{const d=await api('/api/update-check');renderUpdateInfo(d);if(!silent&&d.updateAvailable)toast(`updateAvailable ${d.manifest.version}`);else if(!silent&&!d.error)toast(d.configured===false?'updatesNotConfigured':'updateCheckComplete');return d}catch(e){renderUpdateInfo({currentVersion:state.me?.version,error:e.message,state:state.settings?.runtime?.updateState||{}});if(!silent)toast(e.message,'error');throw e}}
async function downloadUpdate(){const b=$('#updateAction');if(b){b.disabled=true;b.textContent=uiText('downloading…')}try{const d=await post('/api/update-download',{});renderUpdateInfo({configured:true,currentVersion:state.me?.version,manifest:d.manifest,updateAvailable:true,state:d});toast('updateReadyToInstall');return d}catch(e){toast(e.message,'error');throw e}finally{if(state.updateInfo)renderUpdateInfo(state.updateInfo)}}
async function handleUpdateAction(){const st=state.updateInfo?.state||state.settings?.runtime?.updateState||{};if(st.state==='readyToInstall')return installUpdate();const b=$('#updateAction');if(b){b.disabled=true;b.textContent=uiText('checkingForUpdates…')}try{const d=await checkForUpdates(true);if(d?.updateAvailable){toast(`updateAvailable ${d.manifest.version}`);await downloadUpdate()}else if(!d?.error){toast(d.configured===false?'updatesNotConfigured':'upToDate')}}catch(e){if(!state.updateInfo?.error)toast(e.message,'error')}finally{if(state.updateInfo)renderUpdateInfo(state.updateInfo)}}
async function installUpdate(){const version=state.updateInfo?.state?.version||state.settings?.runtime?.updateState?.version||$('#updateLatest').textContent;const b=$('#updateAction');if(b){b.disabled=true;b.textContent=uiText('restarting…')}try{await post('/api/update-install',{version});$('#updateMessage').textContent=`${uiText('installing')} ${version} · ${uiText('torrentDashboardWillRestart')}`;$('#updateState').textContent=uiText('installing');toast('installingUpdate');waitForUpdatedServer(version)}catch(e){if(b){b.disabled=false;b.textContent=uiText('installUpdate')}toast(e.message,'error')}}
function waitForUpdatedServer(version){const started=Date.now();const timer=setInterval(async()=>{if(Date.now()-started>60000){clearInterval(timer);$('#updateMessage').textContent=uiText('updateRestartTakingLongerThanExpected');return}try{const r=await fetch('/health',{cache:'no-store'});if(!r.ok)return;const d=await r.json();if(String(d.version)===String(version)){clearInterval(timer);location.reload()}}catch{}},1200)}

function applyPrefs(){let theme=localStorage.tdTheme||'dark';if(theme==='system')theme=matchMedia('(prefers-color-scheme:light)').matches?'light':'dark';document.documentElement.dataset.theme=theme;document.documentElement.dataset.density=localStorage.tdDensity||'comfortable';document.documentElement.style.setProperty('--accent',localStorage.tdAccent||'#72a9ff');applyColumnPrefs()}

let refreshTimer;
function scheduleRefresh(){clearInterval(refreshTimer);refreshTimer=setInterval(refreshStatus,LIVE_REFRESH_MS)}
async function refreshStatus(){try{const d=await api(`/api/status?server=${encodeURIComponent(state.server)}`);state.torrents=d.torrents||[];state.transfer=d.transfer||{};reconcileDetailSelection();renderMetrics(d);checkCompletions();render();if(state.detail&&$('#view-dashboard').classList.contains('active'))refreshDetailData(false);$('#errorBanner').classList.toggle('hidden',d.ok!==false);if(d.ok===false){$('#errorBanner').textContent=d.error||(d.errors||[]).map(x=>x.error).join(' · ')||uiText('connectionProblem')}}catch(e){$('#errorBanner').textContent=e.message;$('#errorBanner').classList.remove('hidden')}}
function checkCompletions(){const now=new Set(state.torrents.filter(t=>Number(t.progress)>=.999999).map(keyFor));if(state.lastComplete.size){for(const k of now)if(!state.lastComplete.has(k)){const t=state.torrents.find(x=>keyFor(x)===k);if(t){toast(`completed: ${t.name}`);playCompletionSound().catch(()=>{});if(state.settings?.notifications?.browser&&'Notification' in window&&Notification.permission==='granted')showBrowserNotification(state.settings?.dashboard?.title||'Torrent Dashboard',{body:`Completed: ${t.name}`,tag:`torrent-complete-${k}`}).catch(()=>{})}}}state.lastComplete=now;if('setAppBadge'in navigator){let n=state.torrents.filter(isActive).length;n?navigator.setAppBadge(n):navigator.clearAppBadge()}}

function renderMetrics(d){const t=state.torrents,x=state.transfer,active=t.filter(isActive),queued=active.filter(a=>!Number(a.dlspeed)).length,remain=active.reduce((a,b)=>a+Number(b.amount_left||0),0),etas=active.map(a=>Number(a.eta)).filter(v=>Number.isFinite(v)&&v<8640000),avg=etas.length?etas.reduce((a,b)=>a+b,0)/etas.length:Infinity;$('#mDown').textContent=speed(x.dl_info_speed||0);$('#mDownTotal').textContent=`Session ${bytes(x.dl_info_data||0)}`;$('#mUp').textContent=speed(x.up_info_speed||0);$('#mUpTotal').textContent=`Session ${bytes(x.up_info_data||0)}`;$('#mActive').textContent=active.length;$('#mQueue').textContent=queued?`${queued} ${uiText('queuedOrStalled')}`:uiText('allActive');$('#mRemain').textContent=bytes(remain);$('#mEta').textContent=`${uiText('avgEta')} ${eta(avg)}`;const completed=t.filter(isComplete).length,paused=t.filter(isPaused).length;$('#mTotal').textContent=t.length;$('#mTorrentSummary').textContent=t.length?`${completed} completed · ${paused} paused`:'No torrents';let disk=d.disk_free;if(state.server==='all')disk=null;$('#mDisk').textContent=disk==null?'—':bytes(disk);let low=Number(state.settings?.dashboard?.low_disk_gb||20)*1024**3;$('#mDiskWarn').textContent=uiText(disk!=null&&disk<low?'lowDiskSpace':'downloadVolume');const c=d.tab_counts||{};$('#countAll').textContent=c.all??t.length;$('#countActive').textContent=c.downloading??t.filter(isActive).length;$('#countCompleted').textContent=c.completed??t.filter(isComplete).length;$('#countPaused').textContent=c.paused??t.filter(isPaused).length}
function isComplete(t){return Number(t.progress||0)>=.999999}function isStopped(t){let s=String(t.state||'').toLowerCase();return s.includes('paused')||s.includes('stopped')}function isPaused(t){return !isComplete(t)&&isStopped(t)}function isActive(t){return !isComplete(t)&&!isStopped(t)}
function stateInfo(t){const s=String(t.state||'').toLowerCase();if(s.includes('error')||s.includes('missing'))return['error','error'];if(isComplete(t)&&isStopped(t))return['complete','seed'];if(isPaused(t))return['paused','pause'];if(s.includes('upload')||s.includes('seed'))return[Number(t.upspeed)>0?'seeding':'seedIdle','seed'];if(s.includes('stall')&&!isComplete(t))return['stalled','pause'];if(s.includes('check'))return['checking','pause'];if(s.includes('meta'))return['metadata','down'];if(!isComplete(t)&&Number(t.dlspeed)>0)return['downloading','down'];if(!isComplete(t))return['queued',''];return['complete','seed']}
function trackerHost(v){try{return new URL(v).hostname||v}catch{return v||''}}
function keyFor(t){return`${t._server_id||state.server}:${t.hash}`}
function visibleTorrents(){let arr=state.torrents.filter(t=>{if(state.filter==='active'&&!isActive(t))return false;if(state.filter==='completed'&&!isComplete(t))return false;if(state.filter==='paused'&&!isPaused(t))return false;if(state.category&&t.category!==state.category)return false;if(state.tag&&!String(t.tags||'').split(',').map(x=>x.trim()).includes(state.tag))return false;if(state.tracker&&trackerHost(t.tracker)!==state.tracker)return false;if(state.search&&!`${t.name||''} ${t.category||''} ${t.tags||''} ${t.tracker||''}`.toLowerCase().includes(state.search))return false;return true});const [field,dir]=state.sort.split('_');const val=(t)=>({name:String(t.name||'').toLowerCase(),progress:Number(t.progress||0),down:Number(t.dlspeed||0),up:Number(t.upspeed||0),eta:Number(t.eta||9e15),size:Number(t.size||0),ratio:Number(t.ratio||0),added:Number(t.added_on||0)})[field];arr.sort((a,b)=>{let A=val(a),B=val(b);return(A<B?-1:A>B?1:0)*(dir==='desc'?-1:1)});return arr}
function syncTorrentWorkspaceLayout(){
  const workspace=$('.torrent-workspace');if(!workspace)return;
  const mobile=window.matchMedia('(max-width:700px)').matches;
  if(mobile||!$('#view-dashboard')?.classList.contains('active')){workspace.style.removeProperty('--torrent-workspace-height');return}
  const top=Math.max(0,workspace.getBoundingClientRect().top);
  const available=Math.max(360,Math.floor(window.innerHeight-top-16));
  const value=`${available}px`;
  if(workspace.style.getPropertyValue('--torrent-workspace-height')!==value)workspace.style.setProperty('--torrent-workspace-height',value);
}
window.addEventListener('resize',()=>requestAnimationFrame(syncTorrentWorkspaceLayout));

function emptyStateCopy(){
  const hasFacet=!!(state.search||state.category||state.tag||state.tracker);
  if(!state.torrents.length)return state.me?.can_manage?['No torrents yet','Add a torrent to get started.']:['No torrents available','There are no torrents on this server.'];
  if(hasFacet)return['No torrents match these filters','Adjust your search or filters.'];
  if(state.filter==='active')return['No active torrents','Nothing is downloading right now.'];
  if(state.filter==='completed')return['No completed torrents','Completed torrents will appear here.'];
  if(state.filter==='paused')return['No paused torrents','Paused torrents will appear here.'];
  return['No torrents in this view','Try another filter.'];
}
function render(){const list=visibleTorrents();$('#torrentRows').innerHTML=list.map(rowHtml).join('');const empty=$('#empty');empty.classList.toggle('hidden',list.length>0);if(!list.length){const [title,text]=emptyStateCopy();$('#emptyTitle').textContent=title;$('#emptyText').textContent=text}$('#selectedCount').textContent=state.selected.size;$('#bulkbar').classList.toggle('hidden',!state.selected.size);$('#selectAll').checked=!!list.length&&list.every(t=>state.selected.has(keyFor(t)));updateFilters();syncTorrentWorkspaceLayout()}
function rowHtml(t){const pct=Math.max(0,Math.min(100,Number(t.progress||0)*100)),[label,cls]=stateInfo(t),server=t._server_name?`${t._server_name} · `:'';return`<tr class="${state.detail&&state.detail.server===(t._server_id||state.server)&&state.detail.hash===t.hash?'torrent-detail-selected':''}" data-key="${esc(keyFor(t))}" data-hash="${esc(t.hash)}" data-server="${esc(t._server_id||state.server)}"><td class="check"><input class="rowcheck" type="checkbox" ${state.selected.has(keyFor(t))?'checked':''}></td><td><div class="torrent-name" title="${esc(t.name)}">${esc(t.name)}</div><div class="torrent-sub">${esc(server)}${bytes(t.size)} · ${esc(t.category||'Uncategorized')} · ${Number(t.num_seeds||0)} seeds</div></td><td class="progress-cell" data-col="progress"><div class="progress-top"><span>${pct.toFixed(1)}%</span><span>${bytes(t.amount_left)} Left</span></div><div class="track"><div class="fill" style="width:${pct}%"></div></div></td><td class="mobile-grid" data-col="state" data-label="Status"><span class="state ${cls}">${esc(uiText(label))}</span></td><td class="mobile-grid" data-col="down" data-label="Download"><span class="mono">${speed(t.dlspeed||0)}</span></td><td class="mobile-grid" data-col="up" data-label="Upload"><span class="mono">${speed(t.upspeed||0)}</span></td><td class="mobile-grid" data-col="eta" data-label="ETA"><span class="mono">${eta(t.eta)}</span></td><td class="mobile-grid" data-col="ratio" data-label="Ratio"><span class="mono">${Number(t.ratio||0).toFixed(2)}</span></td><td class="row-actions"><button class="more-row" aria-label="Actions">•••</button></td></tr>`}
function syncFilterSelect(select,values,selected,emptyLabel){
  if(!select)return;
  const signature=JSON.stringify([emptyLabel,...values]);
  // Native select menus can jump back to the first item if their option DOM is
  // modified while the menu is open. Leave a focused select completely alone;
  // the next dashboard refresh will reconcile it after the user closes it.
  if(document.activeElement===select)return;
  if(select.dataset.optionsSignature!==signature){
    select.innerHTML=`<option value="">${esc(emptyLabel)}</option>`+values.map(x=>`<option>${esc(x)}</option>`).join('');
    select.dataset.optionsSignature=signature;
  }
  if(select.value!==selected)select.value=selected;
}
function updateFilters(){
  const cats=[...new Set(state.torrents.map(t=>t.category).filter(Boolean))].sort();
  const tags=[...new Set(state.torrents.flatMap(t=>String(t.tags||'').split(',').map(x=>x.trim()).filter(Boolean)))].sort();
  const trackers=[...new Set(state.torrents.map(t=>trackerHost(t.tracker)).filter(Boolean))].sort();
  syncFilterSelect($('#categoryFilter'),cats,state.category,'All categories');
  syncFilterSelect($('#tagFilter'),tags,state.tag,'All tags');
  syncFilterSelect($('#trackerFilter'),trackers,state.tracker,'All trackers');
}
function rowChange(e){if(!e.target.classList.contains('rowcheck'))return;const tr=e.target.closest('tr'),k=tr.dataset.key;e.target.checked?state.selected.add(k):state.selected.delete(k);render()}
function rowClick(e){const tr=e.target.closest('tr');if(!tr)return;if(e.target.closest('.rowcheck'))return;if(e.target.closest('.more-row')){e.stopPropagation();showTorrentMenu(tr,e.target.closest('.more-row'));return}const server=tr.dataset.server,hash=tr.dataset.hash;if(state.detail?.server===server&&state.detail?.hash===hash){resetDetailPane();return}openDetail(server,hash)}
function rowContext(e){const tr=e.target.closest('tr');if(!tr)return;e.preventDefault();showTorrentMenu(tr,{getBoundingClientRect:()=>({left:e.clientX,top:e.clientY,bottom:e.clientY,right:e.clientX})},true)}
function showTorrentMenu(tr,anchor,context=false){
  const m=$('#contextMenu'),sid=tr.dataset.server,h=tr.dataset.hash;
  const t=state.torrents.find(x=>(x._server_id||state.server)===sid&&x.hash===h);
  if(!t)return;
  const admin=!!state.me?.can_manage;
  const icon=(glyph)=>`<span class="menu-icon" aria-hidden="true">${glyph}</span>`;
  const item=(action,label,glyph='',cls='')=>`<button type="button" data-a="${action}"${cls?` class="${cls}"`:''}>${icon(glyph)}<span>${label}</span></button>`;
  const sep='<div class="menu-separator" role="separator"></div>';
  const items=[];

  if(admin){
    items.push(item(isStopped(t)?'start':'stop',isStopped(t)?'Resume':'Pause',isStopped(t)?'▶':'Ⅱ'));
    items.push(item('force_start',t.force_start?'Disable force start':'Force start','»'));
    items.push(item('delete','Remove…','×','danger'));
    items.push(sep);
    items.push(item('set_location','Set location…','⌖'));
    items.push(item('rename','Rename…','✎'));
    items.push(item('set_category','Category…','≡'));
    items.push(item('tags','Tags…','#'));
    items.push(sep);
  }


  if(admin){
    items.push(sep);
    items.push(item('toggle_sequential','Download in sequential order',t.seq_dl?'✓':'□'));
    items.push(item('toggle_first_last','Download first and last pieces first',t.f_l_piece_prio?'✓':'□'));
    items.push(sep);
    items.push(item('recheck','Force recheck','↻'));
    items.push(item('reannounce','Force reannounce','⟳'));
    items.push(sep);
    items.push('<div class="menu-caption">Queue position</div>');
    items.push(item('top_priority','Move to top','⇈'));
    items.push(item('increase_priority','Move up','↑'));
    items.push(item('decrease_priority','Move down','↓'));
    items.push(item('bottom_priority','Move to bottom','⇊'));
  }

  items.push(sep);
  if(t.magnet_uri)items.push(item('copy_magnet','Copy magnet link','⧉'));
  items.push(item('copy_hash','Copy hash','⧉'));

  m.innerHTML=items.join('');
  $$('.menu').forEach(x=>{if(x!==m)x.classList.add('hidden')});
  m.onclick=async e=>{
    const button=e.target.closest('button[data-a]'),a=button?.dataset.a;
    if(!a)return;
    m.classList.add('hidden');
    if(a==='copy_hash')return navigator.clipboard.writeText(h).then(()=>toast('Hash copied'));
    if(a==='copy_magnet')return navigator.clipboard.writeText(t.magnet_uri||'').then(()=>toast('Magnet link copied'));
    if(!state.me?.can_manage)return toast('Administrator access is required','error');
    if(a==='delete')return removeTorrentTargets([{server:sid,hash:h,name:t.name||h}]);
    if(a==='force_start')return doAction('force_start',{server:sid,hashes:[h],value:!t.force_start});
    if(a==='set_location'){
      const v=await showActionDialog({title:'Set location',label:'Save location',value:t.save_path||'',confirmLabel:'Save'});
      if(v!==null&&v.trim())return doAction('set_location',{server:sid,hashes:[h],location:v.trim()});
      return;
    }
    if(a==='rename'){
      const v=await showActionDialog({title:'Rename torrent',label:'Torrent name',value:t.name||'',confirmLabel:'Save'});
      if(v!==null&&v.trim())return doAction('rename',{server:sid,hash:h,hashes:[h],name:v.trim()});
      return;
    }
    if(a==='set_category'){
      const v=await showActionDialog({title:'Set category',label:'Category',value:t.category||'',allowEmpty:true,confirmLabel:'Save',help:'Leave blank to clear the category.'});
      if(v!==null)return doAction('set_category',{server:sid,hashes:[h],category:v.trim()});
      return;
    }
    if(a==='tags'){
      const current=String(t.tags||'').split(',').map(x=>x.trim()).filter(Boolean);
      const v=await showActionDialog({title:'Edit tags',label:'Tags',value:current.join(', '),allowEmpty:true,confirmLabel:'Save',help:'Separate multiple tags with commas. Leave blank to remove all tags.'});
      if(v===null)return;
      const next=v.split(',').map(x=>x.trim()).filter(Boolean);
      const remove=current.filter(x=>!next.includes(x));
      const add=next.filter(x=>!current.includes(x));
      if(remove.length)await doAction('remove_tags',{server:sid,hashes:[h],tags:remove.join(',')});
      if(add.length)await doAction('add_tags',{server:sid,hashes:[h],tags:add.join(',')});
      return;
    }
    return doAction(a,{server:sid,hashes:[h]});
  };

  if(context){
    m.classList.remove('hidden');
    const r=anchor.getBoundingClientRect(),rect=m.getBoundingClientRect();
    m.style.left=Math.max(8,Math.min(innerWidth-rect.width-8,r.left))+'px';
    m.style.top=Math.max(8,Math.min(innerHeight-rect.height-8,r.top))+'px';
  }else showMenu(m,anchor);
}
function showMenu(m,anchor){
  $$('.menu').forEach(x=>{if(x!==m)x.classList.add('hidden')});
  m.classList.remove('hidden');
  const r=anchor.getBoundingClientRect(),rect=m.getBoundingClientRect();
  const left=Math.max(8,Math.min(innerWidth-rect.width-8,r.right-rect.width));
  let top=r.bottom+5;
  if(top+rect.height>innerHeight-8)top=Math.max(8,r.top-rect.height-5);
  m.style.left=left+'px';m.style.top=top+'px';
}



let actionDialogResolve=null,actionDialogHasInput=false,actionDialogBound=false;
function closeActionDialog(result=null){const modal=$('#actionDialogModal');if(modal)modal.classList.add('hidden');const resolve=actionDialogResolve;actionDialogResolve=null;if(resolve)resolve(result)}
function bindActionDialog(){if(actionDialogBound)return;actionDialogBound=true;$('#actionDialogForm')?.addEventListener('submit',e=>{e.preventDefault();const input=$('#actionDialogInput');if(actionDialogHasInput){if(!input.reportValidity())return;closeActionDialog(input.value)}else closeActionDialog(true)});$$('[data-action-dialog-cancel]').forEach(x=>x.addEventListener('click',()=>closeActionDialog(null)))}
function showActionDialog(options={}){bindActionDialog();if(actionDialogResolve)closeActionDialog(null);const modal=$('#actionDialogModal'),title=$('#actionDialogTitle'),message=$('#actionDialogMessage'),field=$('#actionDialogField'),label=$('#actionDialogLabel'),input=$('#actionDialogInput'),help=$('#actionDialogHelp'),confirm=$('#actionDialogConfirm');actionDialogHasInput=options.input!==false;title.textContent=options.title||'Action';message.textContent=options.message||'';message.classList.toggle('hidden',!options.message);field.classList.toggle('hidden',!actionDialogHasInput);label.textContent=options.label||'Value';help.textContent=options.help||'';help.classList.toggle('hidden',!options.help);input.type=options.type||'text';input.value=String(options.value??'');input.placeholder=options.placeholder||'';input.required=actionDialogHasInput&&!options.allowEmpty;for(const attr of ['min','max','step']){if(options[attr]!==undefined&&options[attr]!==null)input.setAttribute(attr,String(options[attr]));else input.removeAttribute(attr)}confirm.textContent=options.confirmLabel||'Save';confirm.className=`${options.danger?'danger':'primary'} action-dialog-confirm`;modal.classList.remove('hidden');return new Promise(resolve=>{actionDialogResolve=resolve;setTimeout(()=>{if(actionDialogHasInput){input.focus();input.select()}else confirm.focus()},0)})}

let removeDialogResolve=null;
function closeRemoveDialog(result=null){const modal=$('#removeModal');if(modal)modal.classList.add('hidden');const resolve=removeDialogResolve;removeDialogResolve=null;if(resolve)resolve(result)}
function showRemoveDialog(targets){targets=(targets||[]).filter(x=>x&&x.hash);if(!targets.length)return Promise.resolve(null);if(removeDialogResolve)closeRemoveDialog(null);const one=targets.length===1;const name=targets[0]?.name||targets[0]?.hash||'this torrent';const title=$('#removeTitle');if(title)title.textContent=one?'Remove torrent':'Remove torrents';$('#removePrompt').textContent=one?`Remove “${name}” from qBitTorrent?`:`Remove ${targets.length} torrents from qBitTorrent?`;const list=$('#removeTargets');if(list){if(one){list.classList.add('hidden');list.innerHTML=''}else{const shown=targets.slice(0,6);list.innerHTML=shown.map(x=>`<div>${esc(x.name||x.hash)}</div>`).join('')+(targets.length>shown.length?`<small>+${targets.length-shown.length} more</small>`:'');list.classList.remove('hidden')}}const files=$('#removeFiles');if(files)files.checked=false;$('#removeModal').classList.remove('hidden');return new Promise(resolve=>{removeDialogResolve=resolve;setTimeout(()=>$('#removeForm .remove-confirm')?.focus(),0)})}
async function removeTorrentTargets(targets){const choice=await showRemoveDialog(targets);if(!choice)return false;const grouped={};for(const item of targets){(grouped[item.server]??=[]).push(item.hash)}for(const [server,hashes] of Object.entries(grouped))await doAction('delete',{server,hashes,delete_files:!!choice.deleteFiles});return true}

async function doAction(action,payload={}){if(!state.me?.can_manage)return toast('Administrator access is required','error');try{let server=payload.server||state.server;if(server==='all')throw new Error('Select a specific client for this action');await post('/api/action',{server,action,...payload});toast('Action sent');setTimeout(refreshStatus,300)}catch(e){toast(e.message,'error')}}
async function globalAction(a){if(state.server==='all'){for(const s of [...new Set(state.torrents.map(t=>t._server_id).filter(Boolean))])await doAction(a,{server:s,hashes:['all']})}else await doAction(a,{hashes:['all']})}
async function bulkAction(a){if(a==='delete'){const targets=[...state.selected].map(k=>{let [sid,...rest]=k.split(':');const hash=rest.join(':');const t=state.torrents.find(x=>(x._server_id||state.server)===sid&&x.hash===hash);return{server:sid,hash,name:t?.name||hash}});const removed=await removeTorrentTargets(targets);if(removed){state.selected.clear();render()}return}let grouped={};for(const k of state.selected){let [sid,...rest]=k.split(':');(grouped[sid]??=[]).push(rest.join(':'))}for(const [sid,hashes]of Object.entries(grouped))await doAction(a,{server:sid,hashes});state.selected.clear();render()}

async function loadMeta(){if(state.server==='all')return;try{state.meta=await api(`/api/meta?server=${encodeURIComponent(state.server)}`)}catch(e){toast(e.message,'error')}}
let detailRefreshAt=0;
function detailEmptyMarkup(){return '<div class="empty detail-empty"><span>Select a torrent to view details.</span></div>'}
function syncDetailDock(){
  const pane=$('#torrentDetailPane'),handle=$('#detailHandle'),workspace=pane?.closest('.torrent-workspace');if(!pane||!handle)return;
  const expanded=!!state.detailExpanded,selected=!!state.detail;
  pane.classList.toggle('collapsed',!expanded);pane.classList.toggle('has-selection',selected);workspace?.classList.toggle('detail-expanded',expanded);
  handle.setAttribute('aria-expanded',String(expanded));const selection=$('#detailHandleSelection');if(selection)selection.textContent=selected?(detailCurrentTorrent()?.name||'Selected torrent'):'';
  syncTorrentWorkspaceLayout();
}
async function toggleDetailPane(){
  state.detailExpanded=!state.detailExpanded;syncDetailDock();
  if(state.detailExpanded&&state.detail){if(state.detail.data)renderDetail();await refreshDetailData(true)}
}
function resetDetailPane(renderList=true){
  state.detail=null;state.detailExpanded=false;detailRefreshAt=0;$('#detailHandleSelection').textContent='';$('#detailBody').innerHTML=detailEmptyMarkup();syncDetailDock();if(renderList)render();
}
function reconcileDetailSelection(){
  if(!state.detail)return;
  const exists=state.torrents.some(t=>(t._server_id||state.server)===state.detail.server&&t.hash===state.detail.hash);
  if(!exists)resetDetailPane(false);
}
async function openDetail(server,hash){
  const same=state.detail?.server===server&&state.detail?.hash===hash;state.detail={server,hash,data:same?state.detail?.data:null};state.detailExpanded=true;state.detailTab=state.detailTab||'general';
  syncDetailDock();$$('[data-detailtab]').forEach(b=>b.classList.toggle('active',b.dataset.detailtab===state.detailTab));render();
  await refreshDetailData(true);
}
async function refreshDetailData(force=false){
  if(!state.detail||(!state.detailExpanded&&!force))return;const now=Date.now();if(!force&&now-detailRefreshAt<3000)return;detailRefreshAt=now;const {server,hash}=state.detail;
  if(!state.detail.data)$('#detailBody').innerHTML='<div class="empty">Loading…</div>';
  try{const data=await api(`/api/detail?server=${encodeURIComponent(server)}&hash=${encodeURIComponent(hash)}`);if(!state.detail||state.detail.server!==server||state.detail.hash!==hash)return;state.detail.data=data;renderDetail()}catch(e){if(state.detail)$('#detailBody').innerHTML=`<div class="banner error">${esc(e.message)}</div>`}
}
function detailCurrentTorrent(){if(!state.detail)return null;return state.torrents.find(x=>(x._server_id||state.server)===state.detail.server&&x.hash===state.detail.hash)||null}
function detailStat(label,value){return`<div class="detail-stat"><span>${esc(label)}</span><b>${esc(value??'—')}</b></div>`}
function renderDetail(){if(!state.detail?.data)return;const d=state.detail.data,p=d.properties||{},t=detailCurrentTorrent()||{};if(state.detailTab==='general')renderDetailGeneral(t,p);else if(state.detailTab==='trackers')renderTrackers(d.trackers||[]);else if(state.detailTab==='peers')renderPeers(d.peers||{});else if(state.detailTab==='webseeds')renderWebSeeds(d.webseeds||[]);else renderFiles(d.files||[])}
function renderDetailGeneral(t,p){const progress=Math.max(0,Math.min(1,Number(t.progress||p.progress||0))),availabilityRaw=Number(t.availability),availability=Number.isFinite(availabilityRaw)&&availabilityRaw>=0?Math.min(1,availabilityRaw):null;const transfer=[['Time active',eta(p.time_elapsed)],['Downloaded',bytes(p.total_downloaded)],['Download speed',speed(p.dl_speed||t.dlspeed||0)],['Download limit',Number(p.dl_limit)>0?speed(p.dl_limit):'∞'],['Share ratio',Number(p.share_ratio||t.ratio||0).toFixed(2)],['Popularity',Number(p.popularity||0).toFixed(2)],['ETA',eta(p.eta??t.eta)],['Uploaded',bytes(p.total_uploaded)],['Upload speed',speed(p.up_speed||t.upspeed||0)],['Upload limit',Number(p.up_limit)>0?speed(p.up_limit):'∞'],['Reannounce in',eta(p.reannounce)]];const swarm=[['Connections',`${p.nb_connections??0} (${p.nb_connections_limit??'—'} max)`],['Seeds',`${p.seeds??t.num_seeds??0} (${p.seeds_total??t.num_complete??0} total)`],['Peers',`${p.peers??t.num_leechs??0} (${p.peers_total??t.num_incomplete??0} total)`],['Wasted',bytes(p.total_wasted||0)],['Last seen complete',when(p.last_seen)]];const info=[['Total size',bytes(p.total_size||t.total_size||t.size||0)],['Added on',when(p.addition_date||t.added_on)],['Completed on',when(p.completion_date||t.completion_on)],['Private',p.private===true||p.is_private===true?'Yes':p.private===false||p.is_private===false?'No':'—'],['Pieces',`${p.pieces_num??'—'} × ${bytes(p.piece_size||0)}`],['Created by',p.created_by||'—'],['Created on',when(p.creation_date)],['Save path',p.save_path||t.save_path||'—'],['Comment',p.comment||'—']];$('#detailBody').innerHTML=`<div class="detail-progress-grid"><div class="detail-progress-row"><span>Progress</span><div class="detail-progress-bar"><span style="width:${(progress*100).toFixed(1)}%"></span></div><b>${(progress*100).toFixed(1)}%</b></div><div class="detail-progress-row"><span>Availability</span><div class="detail-progress-bar availability"><span style="width:${availability===null?0:(availability*100).toFixed(1)}%"></span></div><b>${availability===null?'—':availabilityRaw.toFixed(3)}</b></div></div><div class="detail-general-grid"><section class="detail-general-section"><strong>Transfer</strong>${transfer.map(x=>detailStat(x[0],x[1])).join('')}</section><section class="detail-general-section"><strong>Swarm</strong>${swarm.map(x=>detailStat(x[0],x[1])).join('')}</section><section class="detail-general-section"><strong>Information</strong>${info.map(x=>detailStat(x[0],x[1])).join('')}</section></div>`}
function renderFiles(files){const admin=!!state.me?.can_manage;$('#detailBody').innerHTML=`<div class="detail-table-wrap"><table class="detail-table compact"><thead><tr><th>Name</th><th>Progress</th><th>Size</th><th>Priority</th></tr></thead><tbody>${files.map((f,i)=>`<tr><td>${esc(f.name)}</td><td>${(Number(f.progress||0)*100).toFixed(1)}%</td><td>${bytes(f.size)}</td><td><select class="fileprio" data-id="${f.index??i}" ${admin?'':'disabled'}><option value="0" ${f.priority===0?'selected':''}>Do not download</option><option value="1" ${f.priority===1?'selected':''}>Normal</option><option value="6" ${f.priority===6?'selected':''}>High</option><option value="7" ${f.priority===7?'selected':''}>Maximum</option></select></td></tr>`).join('')}</tbody></table></div>`;if(admin)$$('.fileprio').forEach(s=>s.onchange=()=>doAction('file_priority',{server:state.detail.server,hash:state.detail.hash,ids:[s.dataset.id],priority:Number(s.value)}))}
function renderPeers(peers){let arr=Object.values(peers.peers||{});$('#detailBody').innerHTML=`<div class="detail-table-wrap"><table class="detail-table compact"><thead><tr><th>Address</th><th>Client</th><th>Progress</th><th>Down</th><th>Up</th></tr></thead><tbody>${arr.map(p=>`<tr><td>${esc(p.ip)}:${esc(p.port)}</td><td>${esc(p.client||'')}</td><td>${(Number(p.progress||0)*100).toFixed(1)}%</td><td>${speed(p.dl_speed||0)}</td><td>${speed(p.up_speed||0)}</td></tr>`).join('')}</tbody></table></div>`}
function renderTrackers(a){$('#detailBody').innerHTML=`<div class="detail-table-wrap"><table class="detail-table compact"><thead><tr><th>Tracker</th><th>Status</th><th>Seeds</th><th>Peers</th><th>Message</th></tr></thead><tbody>${a.map(x=>`<tr><td>${esc(x.url)}</td><td>${esc(x.status)}</td><td>${esc(x.num_seeds)}</td><td>${esc(x.num_leeches)}</td><td>${esc(x.msg||'')}</td></tr>`).join('')}</tbody></table></div>`}
function renderWebSeeds(a){$('#detailBody').innerHTML=a.length?`<div class="detail-table-wrap"><table class="detail-table compact"><thead><tr><th>URL</th></tr></thead><tbody>${a.map(x=>`<tr><td>${esc(x.url||x)}</td></tr>`).join('')}</tbody></table></div>`:'<div class="empty"><strong>No HTTP sources</strong><span>This torrent does not advertise any web seeds.</span></div>'}

function addRateBytes(selector,label){const value=Number($(selector)?.value||0);if(!Number.isFinite(value)||value<0)throw new Error(`${label} must be zero or greater`);return Math.round(value*1024)}
function addTorrentOptions(){return{auto_tmm:$('#addAutoTmm').value==='true',savepath:$('#addPath').value.trim(),use_download_path:$('#addUseDownloadPath').checked,download_path:$('#addDownloadPath').value.trim(),rename:$('#addRename').value.trim(),category:$('#addCategory').value.trim(),tags:$('#addTags').value.trim(),stopped:!$('#addStartTorrent').checked,stop_condition:$('#addStopCondition').value,add_to_top:$('#addToTop').checked,seed_mode:$('#addSeedMode').checked,sequential:$('#addSequential').checked,first_last:$('#addFirstLast').checked,content_layout:$('#addContentLayout').value,dl_limit:addRateBytes('#addDlLimit','Download limit'),ul_limit:addRateBytes('#addUlLimit','Upload limit')}}
function appendAddTorrentFields(fd,o){fd.append('autoTMM',String(o.auto_tmm));fd.append('savepath',o.savepath);fd.append('useDownloadPath',String(o.use_download_path));fd.append('downloadPath',o.download_path);fd.append('rename',o.rename);fd.append('category',o.category);fd.append('tags',o.tags);fd.append('stopped',String(o.stopped));fd.append('stopCondition',o.stop_condition);fd.append('addToTopOfQueue',String(o.add_to_top));fd.append('seedMode',String(o.seed_mode));fd.append('sequentialDownload',String(o.sequential));fd.append('firstLastPiecePrio',String(o.first_last));fd.append('contentLayout',o.content_layout);fd.append('dlLimit',String(o.dl_limit));fd.append('upLimit',String(o.ul_limit))}
function addFilePriorities(){
  if(!addMetadataState.metadata||!addMetadataState.files.length)return null;
  return [...addMetadataState.files].sort((a,b)=>a.index-b.index).map(file=>file.selected?file.priority:0);
}
async function addTorrent(e){
  e.preventDefault();
  if(state.server==='all')return toast('Select a specific client first','error');
  try{
    const options=addTorrentOptions(),priorities=addFilePriorities();
    if(addMetadataState.mode==='file'){
      const file=currentAddTorrentFile();if(!file)throw new Error('Choose a .torrent file');
      const cachedSource=String(addMetadataState.metadata?.hash||'');
      if(cachedSource){
        await post('/api/action',{server:state.server,action:'add_torrent',source:cachedSource,file_priorities:priorities,...options});
      }else{
        const fd=new FormData();fd.append('server',state.server);appendAddTorrentFields(fd,options);fd.append('torrents',file,file.name);
        await api('/api/upload',{method:'POST',headers:{'X-CSRF-Token':state.csrf},body:fd});
      }
    }else{
      const sources=addMetadataSources();if(sources.length!==1)throw new Error('Enter one magnet link or torrent URL');
      const payload={server:state.server,action:'add_torrent',source:sources[0],...options};
      if(priorities)payload.file_priorities=priorities;
      await post('/api/action',payload);
    }
    closeAddTorrent();$('#addForm').reset();resetAddTorrentState();syncAddTorrentOptions();toast('Torrent added');setTimeout(refreshStatus,500);
  }catch(err){toast(err.message,'error')}
}

function notificationCategory(item){const event=String(item?.event||'').toLowerCase();if(event==='completed'||event==='torrent_upload'||event.startsWith('action:'))return'torrents';if(event.startsWith('login_')||event.startsWith('user_')||event.startsWith('account_')||event==='setup_completed')return'security';if(event.startsWith('update_'))return'updates';return'system'}
function notificationPresentation(item){const event=String(item?.event||'').toLowerCase(),category=notificationCategory(item);let title='',message='',tone='neutral';if(event==='completed'){title='Torrent completed';message=`${item.name||'Torrent'} finished downloading${item.server_id&&item.server_id!=='dashboard'?` on ${item.server_id}`:''}.`;tone='good'}else if(event==='torrent_upload'){title='Torrent added';message=item.name?`${item.name} was added to ${item.server_id||'qBitTorrent'}.`:'A torrent was added.';tone='good'}else if(event.startsWith('action:')){const action=event.split(':',2)[1]||'action';const labels={delete:'Torrent removed',start:'Torrent resumed',stop:'Torrent paused',recheck:'Torrent rechecked',reannounce:'Torrent reannounced',rename:'Torrent renamed',set_location:'Torrent location changed',set_category:'Torrent category changed'};title=labels[action]||uiText(`torrent ${action}`);message=`Action sent${item.server_id&&item.server_id!=='dashboard'?` to ${item.server_id}`:''}${item.name?` by ${item.name}`:''}.`;tone=action==='delete'?'warn':'neutral'}else if(event==='login_failed'){title='Failed sign-in';message=`A sign-in attempt failed${item.name?` for ${item.name}`:''}.`;tone='bad'}else if(event==='login_success'){title='Signed in';message=`${item.name||'A user'} signed in to Torrent Dashboard.`;tone='good'}else if(event==='account_profile_changed'){title='Account updated';message=`${item.name||'A user'} updated their profile.`;tone='good'}else if(event==='account_password_changed'){title='Password changed';message=`${item.name||'A user'} changed their password.`;tone='good'}else if(event==='account_avatar_changed'){title='Profile picture changed';message=`${item.name||'A user'} updated their profile picture.`;tone='good'}else if(event==='account_avatar_removed'){title='Profile picture removed';message=`${item.name||'A user'} removed their profile picture.`}else if(event==='setup_completed'){title='Setup completed';message='Torrent Dashboard first-run setup was completed.';tone='good'}else if(event==='user_saved'){title='User saved';message=`${item.name||'A user account'} was updated.`}else if(event==='user_deleted'){title='User deleted';message='A dashboard user was removed.';tone='warn'}else if(event==='integration_saved'){title='Integration saved';message=`${item.name||'An integration'} was updated.`}else if(event==='integration_deleted'){title='Integration deleted';message='An integration was removed.';tone='warn'}else if(event==='settings_changed'){title='Settings changed';message=`Dashboard settings were updated${item.name?` by ${item.name}`:''}.`}else if(event==='update_downloaded'){title='Update downloaded';message=item.name?`Version ${item.name} is ready to install.`:'An application update was downloaded.';tone='good'}else if(event==='update_install_started'){title='Update installation started';message=item.name?`Torrent Dashboard is installing version ${item.name}.`:'Torrent Dashboard is installing an update.';tone='good'}else if(event==='notification_sound_changed'){title='Notification sound changed';message=item.name?`${item.name} is now configured.`:'The custom notification sound was changed.'}else{title=uiText(event||'dashboardEvent');message=[item.server_id&&item.server_id!=='dashboard'?item.server_id:'',item.name||''].filter(Boolean).join(' · ')||'Torrent Dashboard recorded an event.'}return{category,title,message,tone}}
function renderNotifications(){const list=$('#notificationList');if(!list)return;const filter=$('#notificationFilter')?.value||'all';let items=(state.notificationEvents||[]).filter(x=>state.server==='all'||x.server_id===state.server||x.server_id==='dashboard');if(filter!=='all')items=items.filter(x=>notificationCategory(x)===filter);if(!items.length){list.innerHTML=`<div class="empty"><strong>${uiText('noNotificationsYet')}</strong><span>${uiText('dashboardActivityWillAppearHere')}</span></div>`;return}list.innerHTML=items.map(item=>{const view=notificationPresentation(item);return`<article class="notification-item ${esc(view.tone)}"><span class="notification-dot" aria-hidden="true"></span><div class="notification-copy"><div class="notification-title"><b>${esc(view.title)}</b><span>${esc(uiText(view.category))}</span></div><p>${esc(view.message)}</p></div><time title="${esc(when(item.ts))}">${esc(rel(item.ts))}</time></article>`}).join('')}
async function loadNotifications(){try{const d=await api('/api/events?limit=200');state.notificationEvents=d.events||[];renderNotifications()}catch(err){toast(err.message,'error')}}

function renderServerSettings(servers){$('#serverSettings').innerHTML='';servers.forEach(s=>addServerRow(s))}
function addServerRow(s={id:'',name:'',base_url:'http://127.0.0.1:8080',auth_method:'api_key',api_key:'',username:'',password:'',enabled:true}){
  const d=document.createElement('div');d.className='server-setting';const method=s.auth_method||((s.api_key&&s.api_key!=='')?'api_key':'password');
  d.innerHTML=`<label>Display name<input data-k="name" placeholder="Desktop" value="${esc(s.name||'')}"></label><label class="server-url">Web UI URL<input data-k="base_url" placeholder="http://127.0.0.1:8080" value="${esc(s.base_url||'')}"></label><label>Authentication<select data-k="auth_method"><option value="api_key" ${method==='api_key'?'selected':''}>API key</option><option value="password" ${method==='password'?'selected':''}>Username and password</option></select></label><div class="server-auth-api"><label>API key<input data-k="api_key" type="password" autocomplete="off" placeholder="${s.api_key==='<configured>'?'API key configured':'qbt_…'}"></label><small>qBitTorrent 5.2+ · Bearer authentication</small></div><div class="server-auth-password two"><label>Username<input data-k="username" autocomplete="off" value="${esc(s.username||'')}"></label><label>Password<input data-k="password" type="password" autocomplete="off" placeholder="${s.password==='<configured>'?'Password configured':'Password'}"></label></div><div class="server-setting-actions"><button type="button" class="test-server">Test</button><button type="button" class="secondary client-settings" ${s.id?'':'disabled'}>Settings</button><button type="button" class="danger">Remove</button></div><input type="hidden" data-k="id" value="${esc(s.id||'')}"><small class="server-test-result"></small>`;
  const sync=()=>{const useApi=d.querySelector('[data-k="auth_method"]').value==='api_key';d.querySelector('.server-auth-api').classList.toggle('hidden',!useApi);d.querySelector('.server-auth-password').classList.toggle('hidden',useApi)};
  d.querySelector('[data-k="auth_method"]').addEventListener('change',sync);sync();d.querySelector('.danger').onclick=()=>d.remove();d.querySelector('.test-server').onclick=()=>testServerRow(d);d.querySelector('.client-settings').onclick=()=>TDSettings.openClientSettings(d.querySelector('[data-k="id"]').value);$('#serverSettings').append(d);applySentenceCaseUi(d);decorateSecretFields(d)
}
function serverRowData(r){let o={enabled:true};r.querySelectorAll('[data-k]').forEach(i=>o[i.dataset.k]=i.type==='password'?secretFieldValue(i,'<configured>'):i.value);return o}
async function testServerRow(r){const out=r.querySelector('.server-test-result');out.textContent=uiText('testing…');out.className='server-test-result';try{const d=await post('/api/client-test',serverRowData(r));out.textContent=`Connected · qBitTorrent ${d.version||'Unknown'} · Web API ${d.api_version||'Unknown'} · ${serverRowData(r).auth_method==='api_key'?'API key':'Password'}`;out.className='server-test-result ok'}catch(e){out.textContent=e.message;out.className='server-test-result bad'}}
async function saveSettings(e){return TDSettings.saveCore(e)}

async function loadIntegrations(){return TDSettings.loadIntegrations()}

function applyColumnPrefs(){let cols=JSON.parse(localStorage.tdColumns||'{}');for(const k of ['progress','state','down','up','eta','ratio'])$('#torrentTable')?.classList.toggle('hide-col-'+k,cols[k]===false)}

function hideAccountMenu(){const menu=$('#accountMenu');if(menu)menu.classList.add('hidden');$('#profileBtn')?.setAttribute('aria-expanded','false')}
function syncAvatarUi(){
  const configured=!!state.me?.avatar_configured&&!!state.me?.user_id;
  const src=configured?`/api/account/avatar?v=${encodeURIComponent(state.me.avatar_version||'1')}`:'';
  $$('[data-avatar-image]').forEach(img=>{
    const fallback=img.parentElement?.querySelector('[data-avatar-default]');
    if(configured){
      img.onerror=()=>{img.classList.add('hidden');fallback?.classList.remove('hidden')};
      img.src=src;img.classList.remove('hidden');fallback?.classList.add('hidden');
    }else{
      img.removeAttribute('src');img.classList.add('hidden');fallback?.classList.remove('hidden');
    }
  });
}
function syncCurrentUserUi(){
  const display=state.me?.display_name||state.me?.username||'User',group=state.me?.group_label||uiText(state.me?.group||'standardUser');
  if($('#mobileAccount'))$('#mobileAccount').textContent=group;
  if($('#profileButtonName'))$('#profileButtonName').textContent=display;
  if($('#profileButtonGroup'))$('#profileButtonGroup').textContent=group;
  if($('#accountMenuName'))$('#accountMenuName').textContent=display;
  if($('#accountMenuGroup'))$('#accountMenuGroup').textContent=group;
  const editable=!!state.me?.user_id;
  for(const id of ['accountSettingsBtn']){const el=$('#'+id);if(el)el.disabled=!editable}
  if($('#accountRemoveAvatar'))$('#accountRemoveAvatar').disabled=!editable||!state.me?.avatar_configured;
  syncAvatarUi();
}
function applyAccountUser(user){
  if(!user||!state.me)return;
  Object.assign(state.me,{username:user.username,display_name:user.display_name,group:user.group,group_label:user.group_label,avatar_configured:!!user.avatar_configured,avatar_version:user.avatar_version||''});
  syncCurrentUserUi();
}
let accountProfileSnapshot=null,passwordConfirmationResolve=null,passwordConfirmationBound=false;
function closePasswordConfirmation(result=null){const modal=$('#passwordConfirmModal');modal?.classList.add('hidden');const input=$('#passwordConfirmInput');if(input){input.value='';input.type='password';syncSecretToggle(input)}const status=$('#passwordConfirmStatus');if(status)status.textContent='';const resolve=passwordConfirmationResolve;passwordConfirmationResolve=null;if(resolve)resolve(result)}
function bindPasswordConfirmation(){if(passwordConfirmationBound)return;passwordConfirmationBound=true;$('#passwordConfirmForm')?.addEventListener('submit',e=>{e.preventDefault();const input=$('#passwordConfirmInput');if(!input?.reportValidity())return;closePasswordConfirmation(input.value)});$$('[data-password-confirm-cancel]').forEach(x=>x.addEventListener('click',()=>closePasswordConfirmation(null)))}
function requestPasswordConfirmation(message){bindPasswordConfirmation();if(passwordConfirmationResolve)closePasswordConfirmation(null);const modal=$('#passwordConfirmModal'),input=$('#passwordConfirmInput'),copy=$('#passwordConfirmMessage');if(copy)copy.textContent=message||'Enter your current password to continue with this secure account change.';if(input){input.value='';input.type='password';syncSecretToggle(input)}modal?.classList.remove('hidden');return new Promise(resolve=>{passwordConfirmationResolve=resolve;setTimeout(()=>input?.focus(),0)})}
async function loadAccount(){
  const d=await api('/api/account');
  applyAccountUser(d.user);accountProfileSnapshot={...d.user};
  $('#accountUsername').value=d.user?.username||'';
  $('#accountFirstName').value=d.user?.first_name||'';
  $('#accountLastName').value=d.user?.last_name||'';
  $('#accountEmail').value=d.user?.email||'';
  return d.user;
}
async function openAccountModal(target='profile'){
  if(!state.me?.user_id)return toast('This session is not linked to a user account','error');
  $('#accountModal').classList.remove('hidden');
  const status=$('#accountStatus');status.className='test-result muted';status.textContent='Loading account…';
  try{
    await loadAccount();status.textContent='';
    const focusId=target==='password'?'accountNewPassword':'accountFirstName';
    setTimeout(()=>$('#'+focusId)?.focus(),0);
  }catch(e){status.className='test-result bad';status.textContent=e.message}
}
function closeAccountModal(){$('#accountModal').classList.add('hidden');$('#accountProfileForm')?.reset();$('#accountPasswordForm')?.reset();$('#accountStatus').textContent='';accountProfileSnapshot=null}
async function saveOwnProfile(e){
  e.preventDefault();
  const status=$('#accountStatus');
  const payload={username:$('#accountUsername').value.trim(),first_name:$('#accountFirstName').value.trim(),last_name:$('#accountLastName').value.trim(),email:$('#accountEmail').value.trim()};
  const secureChange=!!accountProfileSnapshot&&(payload.username!==String(accountProfileSnapshot.username||'')||payload.email!==String(accountProfileSnapshot.email||''));
  try{
    if(secureChange&&accountProfileSnapshot?.password_configured){
      const password=await requestPasswordConfirmation('Confirm your current password to change your username or email address.');
      if(password===null)return;
      payload.current_password=password;
    }
    status.className='test-result muted';status.textContent='Saving profile…';
    const d=await post('/api/account',payload);
    applyAccountUser(d.user);accountProfileSnapshot={...d.user};status.className='test-result ok';status.textContent='Profile saved.';
  }catch(e){status.className='test-result bad';status.textContent=e.message}
}
async function changeOwnPassword(e){
  e.preventDefault();
  const next=$('#accountNewPassword').value,confirmPassword=$('#accountConfirmPassword').value,status=$('#accountStatus');
  if(next!==confirmPassword){status.className='test-result bad';status.textContent='New passwords do not match.';return}
  try{
    let current='';
    if(accountProfileSnapshot?.password_configured){
      const confirmed=await requestPasswordConfirmation('Confirm your current password to change your password.');
      if(confirmed===null)return;
      current=confirmed;
    }
    status.className='test-result muted';status.textContent='Changing password…';
    await post('/api/account/password',{current_password:current,new_password:next});
    $('#accountPasswordForm').reset();status.className='test-result ok';status.textContent='Password changed.';
  }catch(e){status.className='test-result bad';status.textContent=e.message}
}
async function uploadOwnAvatar(){
  const input=$('#accountAvatarInput'),file=input?.files?.[0],status=$('#accountStatus');
  if(!file)return;
  if(file.size>4*1024*1024){status.className='test-result bad';status.textContent='Profile picture must be 4 MB or smaller.';input.value='';return}
  const form=new FormData();form.append('avatar',file,file.name);
  status.className='test-result muted';status.textContent='Uploading profile picture…';
  try{
    const d=await api('/api/account/avatar',{method:'POST',body:form});applyAccountUser(d.user);status.className='test-result ok';status.textContent='Profile picture updated.';
  }catch(e){status.className='test-result bad';status.textContent=e.message}
  finally{input.value=''}
}
async function removeOwnAvatar(){
  const status=$('#accountStatus');status.className='test-result muted';status.textContent='Removing profile picture…';
  try{const d=await post('/api/account/avatar/delete',{});applyAccountUser(d.user);status.className='test-result ok';status.textContent='Profile picture removed.'}catch(e){status.className='test-result bad';status.textContent=e.message}
}
async function signOut(){try{await post('/api/logout',{})}catch{}location.reload()}

function registerPwa(){if('serviceWorker'in navigator){navigator.serviceWorker.register('/sw.js',{updateViaCache:'none'}).then(reg=>reg.update()).catch(()=>{});navigator.serviceWorker.addEventListener('controllerchange',()=>{if(sessionStorage.getItem('tdSwReloaded')!=='1'){sessionStorage.setItem('tdSwReloaded','1');location.reload()}})}window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();state.deferredPrompt=e;$('#installPwa').classList.remove('hidden')});$('#installPwa').onclick=async()=>{if(state.deferredPrompt){state.deferredPrompt.prompt();await state.deferredPrompt.userChoice;state.deferredPrompt=null;$('#installPwa').classList.add('hidden')}}}

applySentenceCaseUi(document);decorateSecretFields(document);caseObserver.observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['placeholder','title','aria-label']});bootstrap();
