'use strict';
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
function normalizeUiAttributes(el){
  if(!el?.getAttribute)return;
  for(const attr of ['placeholder','title','aria-label']){
    const raw=el.getAttribute(attr);
    if(raw&&hasCamelCaseUiText(raw))el.setAttribute(attr,uiText(raw));
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
        if(trim&&trim.length<80&&/[A-Za-z]/.test(trim))n.nodeValue=raw.replace(trim,uiText(trim));
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
function setSecretToggleIcon(btn,name){btn.innerHTML=`<span class="material-symbols-outlined" aria-hidden="true">${name}</span>`;btn.dataset.materialSymbol=name}
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
const state={me:null,csrf:'',setup:null,setupStep:0,setupMaxStep:0,server:'all',torrents:[],transfer:{},meta:{},filter:localStorage.tdFilter||'all',sort:localStorage.tdSort||'added_desc',search:localStorage.tdSearch||'',category:localStorage.tdCategory||'',tag:localStorage.tdTag||'',tracker:localStorage.tdTracker||'',selected:new Set(),detail:null,detailTab:'overview',settings:null,lastComplete:new Set(),deferredPrompt:null,setupInterfaceSelectionInitialized:false,settingsInterfaceSelectionInitialized:false,updateInfo:null,notificationEvents:[]};

function esc(v=''){return String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function bytes(n,d=1){n=Number(n);if(!Number.isFinite(n)||n<0)return'—';if(n===0)return'0 B';const u=['B','KB','MB','GB','TB','PB'];let i=Math.min(Math.floor(Math.log(n)/Math.log(1024)),u.length-1);return`${(n/1024**i).toFixed(i?d:0)} ${u[i]}`}
function speed(n){return`${bytes(n)}/s`}
function eta(s){s=Number(s);if(!Number.isFinite(s)||s<0||s>=8640000)return'∞';let d=Math.floor(s/86400);s%=86400;let h=Math.floor(s/3600);s%=3600;let m=Math.floor(s/60);if(d)return`${d}d ${h}h`;if(h)return`${h}h ${m}m`;if(m)return`${m}m`;return`${Math.floor(s)}s`}
function when(ts){if(!ts)return'—';const d=new Date(Number(ts)*1000);return d.toLocaleString()}
function rel(ts){if(!ts)return'—';let s=Math.max(0,Date.now()/1000-ts);if(s<60)return`${Math.floor(s)}s ago`;if(s<3600)return`${Math.floor(s/60)}m ago`;if(s<86400)return`${Math.floor(s/3600)}h ago`;return`${Math.floor(s/86400)}d ago`}
function toast(msg,type=''){const el=document.createElement('div');el.className='toast '+type;el.textContent=/^[A-Za-z0-9_ -]+$/.test(String(msg))?uiText(msg):msg;$('#toasts').append(el);setTimeout(()=>el.remove(),3800)}
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
function openAddTorrent(mode='link'){if(state.server==='all')return toast('chooseSpecificServerFirst','error');$('#addModal').classList.remove('hidden');if(mode==='file')$('#torrentFile').click();else $('#addUrls').focus()}

async function rawJson(url,opt={}){const r=await fetch(url,opt);const data=await r.json().catch(()=>({}));if(!r.ok)throw new Error(data.error||`HTTP ${r.status}`);return data}
function parseWhitelist(selector){return $(selector).value.split(/\n|,/).map(x=>x.trim()).filter(Boolean)}
function selectedInterfaceIds(target){return $$(`${target} input[data-interface-id]:checked`).map(x=>x.dataset.interfaceId)}
function setupServer(){return{type:'qbittorrent',name:$('#wClientName').value.trim()||'qBitTorrent',base_url:$('#wClientUrl').value.trim(),auth_method:$('#wClientAuth').value,api_key:$('#wClientApiKey').value.trim(),username:$('#wClientUser').value.trim(),password:$('#wClientPass').value,enabled:true}}
function setupPayload(){return{setup_code:$('#wSetupCode').value.trim(),dashboard:{title:$('#wTitle').value.trim()||'Torrent Dashboard',port:Number($('#wPort').value||state.setup?.port||8765)},auth:{mode:$('#wAuthMode').value,username:$('#wDashUser').value.trim()||'admin',password:$('#wDashPass').value,trusted_interfaces:selectedInterfaceIds('#wInterfaceList'),trusted_ips:parseWhitelist('#wTrustedIps')},servers:[setupServer()]}}

function interfaceCard(item,checked){const label=item.interface||item.interface_id||'Network Interface',gateway=item.gateway?` · Gateway ${esc(item.gateway)}`:'',def=item.default?'<span class="interface-default">Default Route</span>':'';return`<label class="interface-card"><input type="checkbox" data-interface-id="${esc(item.interface_id||item.interface||'')}" ${checked?'checked':''}><div><div class="interface-title"><b>${esc(label)}</b>${def}</div><span>${esc(item.address||'—')} · ${esc(item.cidr||uiText('unknownSubnet'))}${gateway}</span><small>${esc(item.netmask||'')} ${item.range_start?`· ${esc(item.range_start)}–${esc(item.range_end)}`:''}</small></div></label>`}
function renderInterfaceList(target,interfaces,selected=[],autoSelectDefault=false){const el=$(target);if(!el)return;interfaces=interfaces||[];const selectedSet=new Set(selected||[]);if(autoSelectDefault&&!selectedSet.size&&interfaces.length){const d=interfaces.find(x=>x.default)||interfaces[0];if(d)selectedSet.add(d.interface_id||d.interface)}if(!interfaces.length){el.innerHTML='<div class="interface-empty"><b>No Network Interfaces Detected</b><span>You can still use the IP address whitelist below.</span></div>';return}el.innerHTML=interfaces.map(x=>interfaceCard(x,selectedSet.has(x.interface_id||x.interface))).join('')}
async function refreshSetupInterfaces(force=false){const current=selectedInterfaceIds('#wInterfaceList');const d=await rawJson(`/api/setup/network-interfaces?refresh=${force?'1':'0'}`);state.setup.network_interfaces=d.interfaces||[];renderInterfaceList('#wInterfaceList',state.setup.network_interfaces,current,current.length===0&&!state.setupInterfaceSelectionInitialized);state.setupInterfaceSelectionInitialized=true}
async function refreshSettingsInterfaces(force=false){const current=selectedInterfaceIds('#sInterfaceList');const d=await api(`/api/network/interfaces?refresh=${force?'1':'0'}`);if(state.settings?.runtime)state.settings.runtime.network_interfaces=d.interfaces||[];renderInterfaceList('#sInterfaceList',d.interfaces||[],current,false)}


function updateSetupStep(){const pages=$$('.setup-page'),items=$$('#setupSteps li'),last=pages.length-1;state.setupMaxStep=Math.max(state.setupMaxStep,state.setupStep);pages.forEach((p,i)=>p.classList.toggle('active',i===state.setupStep));items.forEach((x,i)=>{x.classList.toggle('active',i===state.setupStep);x.classList.toggle('done',i<state.setupMaxStep);const b=x.querySelector('[data-setup-step]');if(b){b.setAttribute('aria-current',i===state.setupStep?'step':'false');b.title=uiText(i===state.setupStep?'currentStep':'goToSetupStep')}});$('#wBack').classList.toggle('hidden',state.setupStep===0);$('#wNext').textContent=state.setupStep===last?'Finish':'Next';if(state.setupStep===last)renderSetupReview();$('#setupError').textContent=''}
function validateSetupStep(step=state.setupStep){if(step===0){if(!$('#wTitle').value.trim())throw new Error('enterDashboardName');const port=Number($('#wPort').value);if(!Number.isInteger(port)||port<1||port>65535)throw new Error('enterValidDashboardPort')}if(step===1){const mode=$('#wAuthMode').value;if(mode!=='disabled'){if(!$('#wDashUser').value.trim())throw new Error('enterDashboardUsername');if(!$('#wDashPass').value)throw new Error('createDashboardPassword');if($('#wDashPass').value!==$('#wDashPass2').value)throw new Error('dashboardPasswordsDoNotMatch')}if(mode==='lan_bypass'&&!selectedInterfaceIds('#wInterfaceList').length&&!parseWhitelist('#wTrustedIps').length)throw new Error('selectTrustedInterfaceOrWhitelistIp')}if(step===2){if(!$('#wClientUrl').value.trim())throw new Error('enterQbittorrentWebUiUrl');if($('#wClientAuth').value==='api_key'){const key=$('#wClientApiKey').value.trim();if(!key)throw new Error('enterQbittorrentApiKey');if(!/^qbt_[A-Za-z0-9]{28}$/.test(key))throw new Error('invalidQbittorrentApiKeyFormat')}else{if(!$('#wClientUser').value.trim())throw new Error('enterQbittorrentUsername');if(!$('#wClientPass').value)throw new Error('enterQbittorrentPassword')}}}
function validateSetupThrough(step){for(let i=0;i<=step;i++)validateSetupStep(i)}
function goToSetupStep(target){const last=$$('.setup-page').length-1;target=Math.max(0,Math.min(last,Number(target)));$('#setupError').textContent='';try{if(target>state.setupStep){for(let i=state.setupStep;i<target;i++)validateSetupStep(i)}state.setupStep=target;state.setupMaxStep=Math.max(state.setupMaxStep,target);updateSetupStep()}catch(e){$('#setupError').textContent=e.message}}
function renderSetupReview(){
  const p=setupPayload(),mode={required:'Required Everywhere',lan_bypass:'Trusted Address Bypass',disabled:'Disabled'}[p.auth.mode]||uiText(p.auth.mode),client=p.servers[0],clientAuth=client.auth_method==='api_key'?'API Key':'Username And Password',interfaceNames=p.auth.trusted_interfaces.length?p.auth.trusted_interfaces.join(', '):'None',whitelist=p.auth.trusted_ips.length?`${p.auth.trusted_ips.length} Whitelist ${p.auth.trusted_ips.length===1?'Entry':'Entries'}`:'No Whitelist Entries';
  $('#wReview').innerHTML=`<div><span>Dashboard</span><b>${esc(p.dashboard.title)}</b><small>${esc($('#wLocalIp').value)}:${p.dashboard.port}</small></div><div><span>Dashboard Access</span><b>${esc(mode)}</b><small>${esc(interfaceNames)} · ${esc(whitelist)}</small></div><div><span>Administrator</span><b>${esc(p.auth.username)}</b><small>The first setup account is an Administrator.</small></div><div><span>Download Client</span><b>${esc(client.name)}</b><small>${esc(client.base_url)}</small></div><div><span>qBitTorrent Authentication</span><b>${esc(clientAuth)}</b><small>${client.auth_method==='api_key'?'Bearer API Key · No Login Cookie':esc(client.username)}</small></div>`;
  applySentenceCaseUi($('#wReview'));
}
function updateWizardClientAuth(){const useApi=$('#wClientAuth').value==='api_key';$('#wClientApiWrap').classList.toggle('hidden',!useApi);$('#wClientPasswordWrap').classList.toggle('hidden',useApi);$('#wClientResult').className='test-result muted';$('#wClientResult').textContent='Not Tested Yet'}
function updateWizardLanVisibility(){const enabled=$('#wAuthMode').value==='lan_bypass';$('#wLanTrust').classList.toggle('hidden',!enabled)}
async function testSetupClient(){const out=$('#wClientResult');out.className='test-result muted';out.textContent=uiText('testing…');try{const d=await rawJson('/api/setup/test-client',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({setup_code:$('#wSetupCode').value.trim(),server:setupServer()})});out.className='test-result ok';out.textContent=`connected · qBitTorrent ${d.version||'unknown'} · webApi ${d.api_version||'unknown'}`}catch(e){out.className='test-result bad';out.textContent=e.message;throw e}}
async function finishSetup(e){if(e?.preventDefault)e.preventDefault();$('#setupError').textContent='';const btn=$('#wNext');try{validateSetupThrough(2);btn.disabled=true;btn.textContent='Testing And Saving…';await rawJson('/api/setup/complete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(setupPayload())});location.reload()}catch(err){$('#setupError').textContent=err.message||'Setup Could Not Be Completed';btn.disabled=false;btn.textContent='Finish';$('#setupError').scrollIntoView({behavior:'smooth',block:'nearest'})}}
function bindPublicUI(){if(window.__tdPublicBound)return;window.__tdPublicBound=true;$('#loginForm').addEventListener('submit',async e=>{e.preventDefault();$('#loginError').textContent='';try{await post('/api/login',{username:$('#loginUser').value,password:$('#loginPass').value});location.reload()}catch(err){$('#loginError').textContent=err.message}});$('#setupForm').addEventListener('submit',e=>e.preventDefault());$('#wBack').addEventListener('click',()=>goToSetupStep(state.setupStep-1));$('#wNext').addEventListener('click',()=>{const last=$$('.setup-page').length-1;if(state.setupStep===last){finishSetup();return}goToSetupStep(state.setupStep+1)});$('#setupSteps').addEventListener('click',e=>{const b=e.target.closest('[data-setup-step]');if(b)goToSetupStep(Number(b.dataset.setupStep))});$('#wTestClient').addEventListener('click',()=>testSetupClient().catch(()=>{}));$('#wClientAuth').addEventListener('change',updateWizardClientAuth);$('#wAuthMode').addEventListener('change',()=>{$('#wizardAccount').classList.toggle('hidden',$('#wAuthMode').value==='disabled');updateWizardLanVisibility()});$('#wRefreshInterfaces').addEventListener('click',()=>refreshSetupInterfaces(true).catch(e=>$('#setupError').textContent=e.message));}

async function bootstrap(){
  bindPublicUI();
  try{
    state.setup=await rawJson('/api/setup/status');
    if(state.setup.required){showSetup();$('#wLocalIp').value=state.setup?.lan_ip||'127.0.0.1';$('#wPort').value=state.setup?.port||8765;$('#wTrustedIps').value=(state.setup.trusted_ips||[]).join('\n');renderInterfaceList('#wInterfaceList',state.setup.network_interfaces||[],state.setup.trusted_interfaces||[],!(state.setup.trusted_interfaces||[]).length);state.setupInterfaceSelectionInitialized=true;$('#setupCodeWrap').classList.toggle('hidden',!state.setup.code_required);updateWizardClientAuth();updateWizardLanVisibility();updateSetupStep();return}
    state.me=await api('/api/me');state.csrf=state.me.csrf;showApp();
    document.body.classList.toggle('standard-user',!state.me.can_manage);
    $('#brandTitle').textContent=state.me.title;document.title=state.me.title;$('#version').textContent=`v${state.me.version}`;
    if(state.me.user_id){try{const account=await api('/api/account');applyAccountUser(account.user)}catch{}}
    syncCurrentUserUi();
    if(state.me.can_manage){await loadSettings()}else{state.settings={dashboard:{low_disk_gb:20},notifications:{browser:false,sound:false}}}
    await loadServers();bindUI();applyPrefs();await refreshStatus();scheduleRefresh();registerPwa();
  }
  catch(e){if(!$('#login').classList.contains('hidden'))return;toast(e.message,'error')}
}

let bound=false;
function bindUI(){if(bound)return;bound=true;
  $$('.nav-root,.settings-subnav button,.mobile-nav button').forEach(b=>b.addEventListener('click',()=>setView(b.dataset.view)));
  $$('#tabs button').forEach(b=>b.classList.toggle('active',b.dataset.filter===state.filter));$$('#tabs button').forEach(b=>b.addEventListener('click',()=>{state.filter=b.dataset.filter;localStorage.tdFilter=state.filter;$$('#tabs button').forEach(x=>x.classList.toggle('active',x===b));render()}));
  $('#search').value=state.search;$('#search').addEventListener('input',e=>{state.search=e.target.value.trim().toLowerCase();localStorage.tdSearch=state.search;render()});
  $('#categoryFilter').addEventListener('change',e=>{state.category=e.target.value;localStorage.tdCategory=state.category;render()});
  $('#tagFilter').addEventListener('change',e=>{state.tag=e.target.value;localStorage.tdTag=state.tag;render()});
  $('#trackerFilter').addEventListener('change',e=>{state.tracker=e.target.value;localStorage.tdTracker=state.tracker;render()});
  $('#sort').value=state.sort;$('#sort').addEventListener('change',e=>{state.sort=e.target.value;localStorage.tdSort=state.sort;render()});
  $('#serverSelect').addEventListener('change',async e=>{state.server=e.target.value;state.selected.clear();await refreshStatus();if(!['all'].includes(state.server))await loadMeta();if($('#view-notifications')?.classList.contains('active'))renderNotifications()});
  $('#selectAll').addEventListener('change',e=>{visibleTorrents().forEach(t=>e.target.checked?state.selected.add(keyFor(t)):state.selected.delete(keyFor(t)));render()});
  $('#torrentRows').addEventListener('click',rowClick);$('#torrentRows').addEventListener('change',rowChange);$('#torrentRows').addEventListener('contextmenu',rowContext);
  $('#bulkbar').addEventListener('click',e=>{if(e.target.closest('[data-bulk-clear]')){state.selected.clear();render();return}const a=e.target.closest('[data-bulk]')?.dataset.bulk;if(a)bulkAction(a)});
  $('#addLinkBtn').addEventListener('click',()=>openAddTorrent('link'));$('#addFileBtn').addEventListener('click',()=>openAddTorrent('file'));$$('[data-modalclose]').forEach(x=>x.addEventListener('click',()=>$('#addModal').classList.add('hidden')));$('#addForm').addEventListener('submit',addTorrent);$('#removeForm')?.addEventListener('submit',e=>{e.preventDefault();closeRemoveDialog({deleteFiles:!!$('#removeFiles')?.checked})});$$('[data-remove-cancel]').forEach(x=>x.addEventListener('click',()=>closeRemoveDialog(null)));
  $$('[data-close]').forEach(x=>x.addEventListener('click',closeDrawer));$$('[data-detailtab]').forEach(x=>x.addEventListener('click',()=>{state.detailTab=x.dataset.detailtab;$$('[data-detailtab]').forEach(b=>b.classList.toggle('active',b===x));renderDetail()}));
  $('#profileBtn').addEventListener('click',e=>{showMenu($('#accountMenu'),e.currentTarget);e.currentTarget.setAttribute('aria-expanded','true')});document.addEventListener('click',e=>{if(!e.target.closest('.menu')&&!e.target.closest('#profileBtn')&&!e.target.closest('.more-row')){$$('.menu').forEach(m=>m.classList.add('hidden'));$('#profileBtn')?.setAttribute('aria-expanded','false')}});
  $('#accountSettingsBtn').addEventListener('click',()=>{hideAccountMenu();openAccountModal('profile')});$('#accountPasswordBtn').addEventListener('click',()=>{hideAccountMenu();openAccountModal('password')});$('#accountAvatarBtn').addEventListener('click',()=>{hideAccountMenu();openAccountModal('avatar')});$('#logoutBtn').addEventListener('click',()=>{hideAccountMenu();signOut()});$$('[data-account-close]').forEach(x=>x.addEventListener('click',closeAccountModal));$('#accountProfileForm').addEventListener('submit',saveOwnProfile);$('#accountPasswordForm').addEventListener('submit',changeOwnPassword);$('#accountChooseAvatar').addEventListener('click',()=>$('#accountAvatarInput').click());$('#accountAvatarInput').addEventListener('change',uploadOwnAvatar);$('#accountRemoveAvatar').addEventListener('click',removeOwnAvatar);
  $('#pauseAllBtn').addEventListener('click',()=>globalAction('stop'));$('#resumeAllBtn').addEventListener('click',()=>globalAction('start'));
  $('#notificationFilter')?.addEventListener('change',renderNotifications);$('#refreshNotifications')?.addEventListener('click',loadNotifications);
  if(state.me?.can_manage)TDSettings.bind();
  window.addEventListener('keydown',e=>{if(e.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){e.preventDefault();$('#search').focus()}if(e.key==='Escape'){if(!$('#clientSettingsModal')?.classList.contains('hidden')){TDSettings.closeClientSettings();return}if(!$('#accountModal')?.classList.contains('hidden')){closeAccountModal();return}if(!$('#accountMenu')?.classList.contains('hidden')){hideAccountMenu();return}if(!$('#actionDialogModal')?.classList.contains('hidden')){closeActionDialog(null);return}if(!$('#removeModal')?.classList.contains('hidden')){closeRemoveDialog(null);return}if(state.selected.size){state.selected.clear();render();return}closeDrawer();$('#addModal').classList.add('hidden')}});
}

function setSettingsNavExpanded(expanded){const group=$('#settingsNavGroup'),submenu=$('#settingsSubnav');if(!group||!submenu)return;group.classList.toggle('expanded',!!expanded);submenu.classList.toggle('hidden',!expanded)}
function setView(view){if(view==='settings'&&!state.me?.can_manage){view='dashboard';toast('Administrator Access Is Required','error')}const settingsView=view==='settings';$$('.view').forEach(v=>v.classList.toggle('active',v.id===`view-${view}`));$$('.nav-root,.mobile-nav button').forEach(b=>b.classList.toggle('active',b.dataset.view===view));setSettingsNavExpanded(settingsView);$('#pageTitle').textContent=uiText(view);$('#subtitle').textContent=uiText(view==='dashboard'?'liveTorrentActivity':view==='notifications'?'recentDashboardActivity':'dashboardConfiguration');if(view==='notifications')loadNotifications();if(settingsView){TDSettings.activate(localStorage.tdSettingsPage||'general');loadSettings().then(()=>TDSettings.loadExtras())}}

async function loadServers(){const d=await api('/api/servers');const sel=$('#serverSelect');sel.innerHTML='<option value="all">allServers</option>'+d.servers.filter(s=>s.enabled).map(s=>`<option value="${esc(s.id)}">${esc(s.name)}</option>`).join('');sel.value=state.server}
async function loadSettings(){try{state.settings=await api('/api/settings');fillSettings()}catch(e){toast(e.message,'error')}}
function fillSettings(){if(!state.settings)return;TDSettings.fill(state.settings)}
function updateActionButton(data=state.updateInfo){const b=$('#updateAction');if(!b)return;const st=data?.state||state.settings?.runtime?.updateState||{};b.classList.remove('primary','secondary');if(st.state==='readyToInstall'){b.disabled=false;b.classList.add('primary');b.textContent=uiText('installUpdate');return}if(st.state==='downloading'){b.disabled=true;b.classList.add('secondary');b.textContent=uiText('downloading…');return}if(st.state==='installing'){b.disabled=true;b.classList.add('primary');b.textContent=uiText('installing…');return}b.disabled=false;b.classList.add('secondary');b.textContent=uiText('checkForUpdates')}
function renderUpdateInfo(data){state.updateInfo=data||null;const current=data?.currentVersion||state.me?.version||'—',manifest=data?.manifest||{},st=data?.state||state.settings?.runtime?.updateState||{};$('#updateCurrent').textContent=current;$('#updateLatest').textContent=manifest.version||st.version||uiText('notChecked');$('#updateState').textContent=uiText(st.state||'idle');const msg=$('#updateMessage');msg.className='muted update-message';let text='';if(data?.error){text=data.error;msg.classList.add('bad')}else if(data?.configured===false){text=data?.error||'Enter and save a public GitHub repository under Updates before checking for updates'}else if(st.state==='readyToInstall'){text=`updateReadyToInstall ${st.version||manifest.version||''}`;msg.classList.add('ok')}else if(data?.updateAvailable){text=`updateAvailable ${manifest.version}${manifest.publishedAt?` · ${manifest.publishedAt}`:''}`;msg.classList.add('ok')}else if(manifest.version){text=`upToDate ${current}`;msg.classList.add('ok')}else if(st.state&&st.state!=='idle'){text=st.error||st.state}else{text='checkForUpdatesWhenReady'}msg.textContent=data?.error?text:uiText(text);updateActionButton(data)}
async function checkForUpdates(silent=false){try{const d=await api('/api/update-check');renderUpdateInfo(d);if(!silent&&d.updateAvailable)toast(`updateAvailable ${d.manifest.version}`);else if(!silent&&!d.error)toast(d.configured===false?'updatesNotConfigured':'updateCheckComplete');return d}catch(e){renderUpdateInfo({currentVersion:state.me?.version,error:e.message,state:state.settings?.runtime?.updateState||{}});if(!silent)toast(e.message,'error');throw e}}
async function downloadUpdate(){const b=$('#updateAction');if(b){b.disabled=true;b.textContent=uiText('downloading…')}try{const d=await post('/api/update-download',{});renderUpdateInfo({configured:true,currentVersion:state.me?.version,manifest:d.manifest,updateAvailable:true,state:d});toast('updateReadyToInstall');return d}catch(e){toast(e.message,'error');throw e}finally{if(state.updateInfo)renderUpdateInfo(state.updateInfo)}}
async function handleUpdateAction(){const st=state.updateInfo?.state||state.settings?.runtime?.updateState||{};if(st.state==='readyToInstall')return installUpdate();const b=$('#updateAction');if(b){b.disabled=true;b.textContent=uiText('checkingForUpdates…')}try{const d=await checkForUpdates(true);if(d?.updateAvailable){toast(`updateAvailable ${d.manifest.version}`);await downloadUpdate()}else if(!d?.error){toast(d.configured===false?'updatesNotConfigured':'upToDate')}}catch(e){if(!state.updateInfo?.error)toast(e.message,'error')}finally{if(state.updateInfo)renderUpdateInfo(state.updateInfo)}}
async function installUpdate(){const version=state.updateInfo?.state?.version||state.settings?.runtime?.updateState?.version||$('#updateLatest').textContent;const b=$('#updateAction');if(b){b.disabled=true;b.textContent=uiText('restarting…')}try{await post('/api/update-install',{version});$('#updateMessage').textContent=`${uiText('installing')} ${version} · ${uiText('torrentDashboardWillRestart')}`;$('#updateState').textContent=uiText('installing');toast('installingUpdate');waitForUpdatedServer(version)}catch(e){if(b){b.disabled=false;b.textContent=uiText('installUpdate')}toast(e.message,'error')}}
function waitForUpdatedServer(version){const started=Date.now();const timer=setInterval(async()=>{if(Date.now()-started>60000){clearInterval(timer);$('#updateMessage').textContent=uiText('updateRestartTakingLongerThanExpected');return}try{const r=await fetch('/health',{cache:'no-store'});if(!r.ok)return;const d=await r.json();if(String(d.version)===String(version)){clearInterval(timer);location.reload()}}catch{}},1200)}

function applyPrefs(){let theme=localStorage.tdTheme||'dark';if(theme==='system')theme=matchMedia('(prefers-color-scheme:light)').matches?'light':'dark';document.documentElement.dataset.theme=theme;document.documentElement.dataset.density=localStorage.tdDensity||'comfortable';document.documentElement.style.setProperty('--accent',localStorage.tdAccent||'#72a9ff');applyColumnPrefs()}

let refreshTimer;
function scheduleRefresh(){clearInterval(refreshTimer);refreshTimer=setInterval(refreshStatus,LIVE_REFRESH_MS)}
async function refreshStatus(){try{const d=await api(`/api/status?server=${encodeURIComponent(state.server)}`);state.torrents=d.torrents||[];state.transfer=d.transfer||{};renderMetrics(d);checkCompletions();render();$('#errorBanner').classList.toggle('hidden',d.ok!==false);if(d.ok===false){$('#errorBanner').textContent=d.error||(d.errors||[]).map(x=>x.error).join(' · ')||uiText('connectionProblem')}}catch(e){$('#errorBanner').textContent=e.message;$('#errorBanner').classList.remove('hidden')}}
function checkCompletions(){const now=new Set(state.torrents.filter(t=>Number(t.progress)>=.999999).map(keyFor));if(state.lastComplete.size){for(const k of now)if(!state.lastComplete.has(k)){const t=state.torrents.find(x=>keyFor(x)===k);if(t){toast(`completed: ${t.name}`);playCompletionSound().catch(()=>{});if(state.settings?.notifications?.browser&&'Notification' in window&&Notification.permission==='granted')showBrowserNotification(state.settings?.dashboard?.title||'Torrent Dashboard',{body:`Completed: ${t.name}`,tag:`torrent-complete-${k}`}).catch(()=>{})}}}state.lastComplete=now;if('setAppBadge'in navigator){let n=state.torrents.filter(isActive).length;n?navigator.setAppBadge(n):navigator.clearAppBadge()}}

function renderMetrics(d){const t=state.torrents,x=state.transfer,active=t.filter(isActive),queued=active.filter(a=>!Number(a.dlspeed)).length,remain=active.reduce((a,b)=>a+Number(b.amount_left||0),0),etas=active.map(a=>Number(a.eta)).filter(v=>Number.isFinite(v)&&v<8640000),avg=etas.length?etas.reduce((a,b)=>a+b,0)/etas.length:Infinity;$('#mDown').textContent=speed(x.dl_info_speed||0);$('#mDownTotal').textContent=`Session ${bytes(x.dl_info_data||0)}`;$('#mUp').textContent=speed(x.up_info_speed||0);$('#mUpTotal').textContent=`Session ${bytes(x.up_info_data||0)}`;$('#mActive').textContent=active.length;$('#mQueue').textContent=queued?`${queued} ${uiText('queuedOrStalled')}`:uiText('allActive');$('#mRemain').textContent=bytes(remain);$('#mEta').textContent=`${uiText('avgEta')} ${eta(avg)}`;$('#mUpdated').textContent=new Date((d.ts||Date.now()/1000)*1000).toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',second:'2-digit'});$('#mHealth').textContent=uiText(d.ok===false?'connectionIssue':'healthy');let disk=d.disk_free;if(state.server==='all')disk=null;$('#mDisk').textContent=disk==null?'—':bytes(disk);let low=Number(state.settings?.dashboard?.low_disk_gb||20)*1024**3;$('#mDiskWarn').textContent=uiText(disk!=null&&disk<low?'lowDiskSpace':'downloadVolume');const c=d.tab_counts||{};$('#countAll').textContent=c.all??t.length;$('#countActive').textContent=c.downloading??t.filter(isActive).length;$('#countCompleted').textContent=c.completed??t.filter(isComplete).length;$('#countPaused').textContent=c.paused??t.filter(isPaused).length}
function isComplete(t){return Number(t.progress||0)>=.999999}function isPaused(t){let s=String(t.state||'').toLowerCase();return s.includes('paused')||s.includes('stopped')}function isActive(t){return !isComplete(t)&&!isPaused(t)}
function stateInfo(t){const s=String(t.state||'').toLowerCase();if(s.includes('error')||s.includes('missing'))return['error','error'];if(isPaused(t))return['paused','pause'];if(s.includes('upload')||s.includes('seed'))return[Number(t.upspeed)>0?'seeding':'seedIdle','seed'];if(s.includes('stall')&&!isComplete(t))return['stalled','pause'];if(s.includes('check'))return['checking','pause'];if(s.includes('meta'))return['metadata','down'];if(!isComplete(t)&&Number(t.dlspeed)>0)return['downloading','down'];if(!isComplete(t))return['queued',''];return['complete','seed']}
function trackerHost(v){try{return new URL(v).hostname||v}catch{return v||''}}
function keyFor(t){return`${t._server_id||state.server}:${t.hash}`}
function visibleTorrents(){let arr=state.torrents.filter(t=>{if(state.filter==='active'&&!isActive(t))return false;if(state.filter==='completed'&&!isComplete(t))return false;if(state.filter==='paused'&&!isPaused(t))return false;if(state.category&&t.category!==state.category)return false;if(state.tag&&!String(t.tags||'').split(',').map(x=>x.trim()).includes(state.tag))return false;if(state.tracker&&trackerHost(t.tracker)!==state.tracker)return false;if(state.search&&!`${t.name||''} ${t.category||''} ${t.tags||''} ${t.tracker||''}`.toLowerCase().includes(state.search))return false;return true});const [field,dir]=state.sort.split('_');const val=(t)=>({name:String(t.name||'').toLowerCase(),progress:Number(t.progress||0),down:Number(t.dlspeed||0),up:Number(t.upspeed||0),eta:Number(t.eta||9e15),size:Number(t.size||0),ratio:Number(t.ratio||0),added:Number(t.added_on||0)})[field];arr.sort((a,b)=>{let A=val(a),B=val(b);return(A<B?-1:A>B?1:0)*(dir==='desc'?-1:1)});return arr}
function render(){const list=visibleTorrents();$('#torrentRows').innerHTML=list.map(rowHtml).join('');$('#empty').classList.toggle('hidden',list.length>0);$('#selectedCount').textContent=state.selected.size;$('#bulkbar').classList.toggle('hidden',!state.selected.size);$('#selectAll').checked=!!list.length&&list.every(t=>state.selected.has(keyFor(t)));updateFilters()}
function rowHtml(t){const pct=Math.max(0,Math.min(100,Number(t.progress||0)*100)),[label,cls]=stateInfo(t),server=t._server_name?`${t._server_name} · `:'';return`<tr data-key="${esc(keyFor(t))}" data-hash="${esc(t.hash)}" data-server="${esc(t._server_id||state.server)}"><td class="check"><input class="rowcheck" type="checkbox" ${state.selected.has(keyFor(t))?'checked':''}></td><td><div class="torrent-name" title="${esc(t.name)}">${esc(t.name)}</div><div class="torrent-sub">${esc(server)}${bytes(t.size)} · ${esc(t.category||'Uncategorized')} · ${Number(t.num_seeds||0)} Seeds</div></td><td class="progress-cell" data-col="progress"><div class="progress-top"><span>${pct.toFixed(1)}%</span><span>${bytes(t.amount_left)} Left</span></div><div class="track"><div class="fill" style="width:${pct}%"></div></div></td><td class="mobile-grid" data-col="state" data-label="Status"><span class="state ${cls}">${esc(uiText(label))}</span></td><td class="mobile-grid" data-col="down" data-label="Download"><span class="mono">${speed(t.dlspeed||0)}</span></td><td class="mobile-grid" data-col="up" data-label="Upload"><span class="mono">${speed(t.upspeed||0)}</span></td><td class="mobile-grid" data-col="eta" data-label="ETA"><span class="mono">${eta(t.eta)}</span></td><td class="mobile-grid" data-col="ratio" data-label="Ratio"><span class="mono">${Number(t.ratio||0).toFixed(2)}</span></td><td class="row-actions"><button class="more-row" aria-label="Actions">•••</button></td></tr>`}
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
function rowClick(e){const tr=e.target.closest('tr');if(!tr)return;if(e.target.closest('.rowcheck'))return;if(e.target.closest('.more-row')){e.stopPropagation();showTorrentMenu(tr,e.target.closest('.more-row'));return}}
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
    items.push(item(isPaused(t)?'start':'stop',isPaused(t)?'Resume':'Pause',isPaused(t)?'▶':'Ⅱ'));
    items.push(item('force_start',t.force_start?'Disable force start':'Force start','»'));
    items.push(item('delete','Remove…','×','danger'));
    items.push(sep);
    items.push(item('set_location','Set location…','⌖'));
    items.push(item('rename','Rename…','✎'));
    items.push(item('set_category','Category…','≡'));
    items.push(item('tags','Tags…','#'));
    items.push(sep);
  }

  items.push(item('details','Torrent details','ⓘ'));

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
    if(a==='details')return openDetail(sid,h);
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
function showRemoveDialog(targets){targets=(targets||[]).filter(x=>x&&x.hash);if(!targets.length)return Promise.resolve(null);if(removeDialogResolve)closeRemoveDialog(null);const one=targets.length===1;const name=targets[0]?.name||targets[0]?.hash||'this torrent';$('#removePrompt').textContent=one?`Are you sure you want to remove “${name}” from the transfer list?`:`Are you sure you want to remove ${targets.length} torrents from the transfer list?`;const list=$('#removeTargets');if(list){if(one){list.classList.add('hidden');list.innerHTML=''}else{const shown=targets.slice(0,6);list.innerHTML=shown.map(x=>`<div>${esc(x.name||x.hash)}</div>`).join('')+(targets.length>shown.length?`<small>+${targets.length-shown.length} more</small>`:'');list.classList.remove('hidden')}}const files=$('#removeFiles');if(files)files.checked=false;$('#removeModal').classList.remove('hidden');return new Promise(resolve=>{removeDialogResolve=resolve;setTimeout(()=>$('#removeForm .remove-confirm')?.focus(),0)})}
async function removeTorrentTargets(targets){const choice=await showRemoveDialog(targets);if(!choice)return false;const grouped={};for(const item of targets){(grouped[item.server]??=[]).push(item.hash)}for(const [server,hashes] of Object.entries(grouped))await doAction('delete',{server,hashes,delete_files:!!choice.deleteFiles});return true}

async function doAction(action,payload={}){if(!state.me?.can_manage)return toast('Administrator access is required','error');try{let server=payload.server||state.server;if(server==='all')throw new Error('chooseSpecificServerForAction');await post('/api/action',{server,action,...payload});toast('actionSent');setTimeout(refreshStatus,300)}catch(e){toast(e.message,'error')}}
async function globalAction(a){if(state.server==='all'){for(const s of [...new Set(state.torrents.map(t=>t._server_id).filter(Boolean))])await doAction(a,{server:s,hashes:['all']})}else await doAction(a,{hashes:['all']})}
async function bulkAction(a){if(a==='delete'){const targets=[...state.selected].map(k=>{let [sid,...rest]=k.split(':');const hash=rest.join(':');const t=state.torrents.find(x=>(x._server_id||state.server)===sid&&x.hash===hash);return{server:sid,hash,name:t?.name||hash}});const removed=await removeTorrentTargets(targets);if(removed){state.selected.clear();render()}return}let grouped={};for(const k of state.selected){let [sid,...rest]=k.split(':');(grouped[sid]??=[]).push(rest.join(':'))}for(const [sid,hashes]of Object.entries(grouped))await doAction(a,{server:sid,hashes});state.selected.clear();render()}

async function loadMeta(){if(state.server==='all')return;try{state.meta=await api(`/api/meta?server=${encodeURIComponent(state.server)}`)}catch(e){toast(e.message,'error')}}
async function openDetail(server,hash){state.detail={server,hash,data:null};state.detailTab='overview';$$('[data-detailtab]').forEach(b=>b.classList.toggle('active',b.dataset.detailtab==='overview'));$('#drawer').classList.remove('hidden');$('#detailBody').innerHTML='<div class="empty">Loading…</div>';const t=state.torrents.find(x=>(x._server_id||state.server)===server&&x.hash===hash);$('#detailName').textContent=t?.name||hash;$('#detailMeta').textContent=`${server} · ${hash}`;try{state.detail.data=await api(`/api/detail?server=${encodeURIComponent(server)}&hash=${encodeURIComponent(hash)}`);renderDetailActions(t);renderDetail()}catch(e){$('#detailBody').innerHTML=`<div class="banner error">${esc(e.message)}</div>`}}
function closeDrawer(){$('#drawer').classList.add('hidden');state.detail=null}
function renderDetailActions(t){$('#detailActions').innerHTML=`<button data-da="${isPaused(t)?'start':'stop'}">${isPaused(t)?'resume':'pause'}</button><button data-da="recheck">recheck</button><button data-da="reannounce">reannounce</button><button data-da="set_location">moveLocation</button><button data-da="rename">rename</button><button data-da="set_download_limit">downloadLimit</button><button data-da="set_upload_limit">uploadLimit</button><button data-da="set_category">category</button><button data-da="add_tags">tags</button><button data-da="toggle_sequential">sequential</button><button data-da="toggle_first_last">firstLast</button><button data-da="delete" class="danger">delete</button>`;applySentenceCaseUi($('#detailActions'));$('#detailActions').onclick=e=>detailAction(e.target.dataset.da)}
async function detailAction(a){if(!a||!state.detail)return;const {server,hash}=state.detail,t=state.torrents.find(x=>(x._server_id||state.server)===server&&x.hash===hash);if(a==='set_location'){const location=await showActionDialog({title:'Set location',label:'Save location',value:t?.save_path||'',confirmLabel:'Save'});if(location!==null&&location.trim())await doAction(a,{server,hashes:[hash],location:location.trim()});return}if(a==='rename'){const name=await showActionDialog({title:'Rename torrent',label:'Torrent name',value:t?.name||'',confirmLabel:'Save'});if(name!==null&&name.trim())await doAction(a,{server,hash,name:name.trim()});return}if(a==='set_category'){const category=await showActionDialog({title:'Set category',label:'Category',value:t?.category||'',allowEmpty:true,confirmLabel:'Save',help:'Leave blank to clear the category.'});if(category!==null)await doAction(a,{server,hashes:[hash],category:category.trim()});return}if(a==='add_tags'){const current=String(t?.tags||'').split(',').map(x=>x.trim()).filter(Boolean);const tags=await showActionDialog({title:'Edit tags',label:'Tags',value:current.join(', '),allowEmpty:true,confirmLabel:'Save',help:'Separate multiple tags with commas. Leave blank to remove all tags.'});if(tags===null)return;const next=tags.split(',').map(x=>x.trim()).filter(Boolean),remove=current.filter(x=>!next.includes(x)),add=next.filter(x=>!current.includes(x));if(remove.length)await doAction('remove_tags',{server,hashes:[hash],tags:remove.join(',')});if(add.length)await doAction('add_tags',{server,hashes:[hash],tags:add.join(',')});return}if(a==='set_download_limit'||a==='set_upload_limit'){const kb=await showActionDialog({title:a==='set_download_limit'?'Set download limit':'Set upload limit',label:'Limit (KB/s)',value:'0',type:'number',min:0,step:1,confirmLabel:'Apply',help:'Use 0 for unlimited.'});if(kb!==null)await doAction(a,{server,hashes:[hash],limit:Number(kb)*1024});return}if(a==='delete'){if(await removeTorrentTargets([{server,hash,name:t?.name||hash}]))closeDrawer();return}await doAction(a,{server,hashes:[hash]})}
function renderDetail(){if(!state.detail?.data)return;const d=state.detail.data,p=d.properties||{};if(state.detailTab==='overview'){let vals=[['savePath',p.save_path],['totalSize',bytes(p.total_size)],['downloaded',bytes(p.total_downloaded)],['uploaded',bytes(p.total_uploaded)],['ratio',Number(p.share_ratio||0).toFixed(2)],['connections',p.nb_connections],['seeds',`${p.seeds||0} / ${p.seeds_total||0}`],['peers',`${p.peers||0} / ${p.peers_total||0}`],['timeActive',eta(p.time_elapsed)],['seedingTime',eta(p.seeding_time)],['created',when(p.creation_date)],['pieces',`${p.pieces_have||0} / ${p.pieces_num||0}`]];let integ=(d.integrations||[]).map(x=>`<div class="kv"><span>${esc(x.integration)}</span><b>${esc(x.title||'matched')} · ${esc(x.status||x.trackedDownloadStatus||'')}</b></div>`).join('');$('#detailBody').innerHTML=`<div class="kv-grid">${vals.map(v=>`<div class="kv"><span>${esc(uiText(v[0]))}</span><b>${esc(v[1]??'—')}</b></div>`).join('')}${integ}</div>`}else if(state.detailTab==='files')renderFiles(d.files||[]);else if(state.detailTab==='peers')renderPeers(d.peers||{});else if(state.detailTab==='trackers')renderTrackers(d.trackers||[]);else renderPieces(d.pieces||[])}
function renderFiles(files){$('#detailBody').innerHTML=`<table class="detail-table"><thead><tr><th>file</th><th>progress</th><th>size</th><th>priority</th></tr></thead><tbody>${files.map((f,i)=>`<tr><td>${esc(f.name)}</td><td>${(Number(f.progress||0)*100).toFixed(1)}%</td><td>${bytes(f.size)}</td><td><select class="fileprio" data-id="${f.index??i}"><option value="0" ${f.priority===0?'selected':''}>skip</option><option value="1" ${f.priority===1?'selected':''}>normal</option><option value="6" ${f.priority===6?'selected':''}>high</option><option value="7" ${f.priority===7?'selected':''}>max</option></select></td></tr>`).join('')}</tbody></table>`;applySentenceCaseUi($('#detailBody'));$$('.fileprio').forEach(s=>s.onchange=()=>doAction('file_priority',{server:state.detail.server,hash:state.detail.hash,ids:[s.dataset.id],priority:Number(s.value)}))}
function renderPeers(peers){let arr=Object.values(peers.peers||{});$('#detailBody').innerHTML=`<table class="detail-table"><thead><tr><th>address</th><th>client</th><th>progress</th><th>down</th><th>up</th></tr></thead><tbody>${arr.map(p=>`<tr><td>${esc(p.ip)}:${esc(p.port)}</td><td>${esc(p.client||'')}</td><td>${(Number(p.progress||0)*100).toFixed(1)}%</td><td>${speed(p.dl_speed||0)}</td><td>${speed(p.up_speed||0)}</td></tr>`).join('')}</tbody></table>`;applySentenceCaseUi($('#detailBody'))}
function renderTrackers(a){$('#detailBody').innerHTML=`<table class="detail-table"><thead><tr><th>tracker</th><th>status</th><th>seeds</th><th>peers</th><th>message</th></tr></thead><tbody>${a.map(x=>`<tr><td>${esc(x.url)}</td><td>${esc(x.status)}</td><td>${esc(x.num_seeds)}</td><td>${esc(x.num_leeches)}</td><td>${esc(x.msg||'')}</td></tr>`).join('')}</tbody></table>`;applySentenceCaseUi($('#detailBody'))}
function renderPieces(a){$('#detailBody').innerHTML=`<p class="muted">${a.length} pieces</p><div class="pieces">${a.map(x=>`<span class="piece ${x===2?'done':x===1?'partial':''}"></span>`).join('')}</div>`}

async function addTorrent(e){e.preventDefault();if(state.server==='all')return toast('chooseSpecificServerFirst','error');try{const f=$('#torrentFile').files[0];if(f){let fd=new FormData();fd.append('server',state.server);fd.append('savepath',$('#addPath').value);fd.append('category',$('#addCategory').value);fd.append('tags',$('#addTags').value);fd.append('stopped',String($('#addStopped').checked));fd.append('sequentialDownload',String($('#addSequential').checked));fd.append('firstLastPiecePrio',String($('#addFirstLast').checked));fd.append('torrents',f);await api('/api/upload',{method:'POST',headers:{'X-CSRF-Token':state.csrf},body:fd})}else{if(!$('#addUrls').value.trim())throw new Error('pasteMagnetUrlOrChooseTorrentFile');await post('/api/action',{server:state.server,action:'add_magnet',urls:$('#addUrls').value.trim(),savepath:$('#addPath').value,category:$('#addCategory').value,tags:$('#addTags').value,stopped:$('#addStopped').checked,sequential:$('#addSequential').checked,first_last:$('#addFirstLast').checked})}$('#addModal').classList.add('hidden');$('#addForm').reset();toast('torrentAdded');setTimeout(refreshStatus,500)}catch(err){toast(err.message,'error')}}

function notificationCategory(item){const event=String(item?.event||'').toLowerCase();if(event==='completed'||event==='torrent_upload'||event.startsWith('action:'))return'torrents';if(event.startsWith('login_')||event.startsWith('user_')||event.startsWith('account_')||event==='setup_completed')return'security';if(event.startsWith('update_'))return'updates';return'system'}
function notificationPresentation(item){const event=String(item?.event||'').toLowerCase(),category=notificationCategory(item);let title='',message='',tone='neutral';if(event==='completed'){title='Torrent completed';message=`${item.name||'Torrent'} finished downloading${item.server_id&&item.server_id!=='dashboard'?` on ${item.server_id}`:''}.`;tone='good'}else if(event==='torrent_upload'){title='Torrent added';message=item.name?`${item.name} was added to ${item.server_id||'qBitTorrent'}.`:'A torrent was added.';tone='good'}else if(event.startsWith('action:')){const action=event.split(':',2)[1]||'action';const labels={delete:'Torrent removed',start:'Torrent resumed',stop:'Torrent paused',recheck:'Torrent rechecked',reannounce:'Torrent reannounced',rename:'Torrent renamed',set_location:'Torrent location changed',set_category:'Torrent category changed'};title=labels[action]||uiText(`torrent ${action}`);message=`Action sent${item.server_id&&item.server_id!=='dashboard'?` to ${item.server_id}`:''}${item.name?` by ${item.name}`:''}.`;tone=action==='delete'?'warn':'neutral'}else if(event==='login_failed'){title='Failed sign-in';message=`A sign-in attempt failed${item.name?` for ${item.name}`:''}.`;tone='bad'}else if(event==='login_success'){title='Signed in';message=`${item.name||'A user'} signed in to Torrent Dashboard.`;tone='good'}else if(event==='account_profile_changed'){title='Account updated';message=`${item.name||'A user'} updated their profile.`;tone='good'}else if(event==='account_password_changed'){title='Password changed';message=`${item.name||'A user'} changed their password.`;tone='good'}else if(event==='account_avatar_changed'){title='Profile picture changed';message=`${item.name||'A user'} updated their profile picture.`;tone='good'}else if(event==='account_avatar_removed'){title='Profile picture removed';message=`${item.name||'A user'} removed their profile picture.`}else if(event==='setup_completed'){title='Setup completed';message='Torrent Dashboard first-run setup was completed.';tone='good'}else if(event==='user_saved'){title='User saved';message=`${item.name||'A user account'} was updated.`}else if(event==='user_deleted'){title='User deleted';message='A dashboard user was removed.';tone='warn'}else if(event==='integration_saved'){title='Integration saved';message=`${item.name||'An integration'} was updated.`}else if(event==='integration_deleted'){title='Integration deleted';message='An integration was removed.';tone='warn'}else if(event==='settings_changed'){title='Settings changed';message=`Dashboard settings were updated${item.name?` by ${item.name}`:''}.`}else if(event==='update_downloaded'){title='Update downloaded';message=item.name?`Version ${item.name} is ready to install.`:'An application update was downloaded.';tone='good'}else if(event==='update_install_started'){title='Update installation started';message=item.name?`Torrent Dashboard is installing version ${item.name}.`:'Torrent Dashboard is installing an update.';tone='good'}else if(event==='notification_sound_changed'){title='Notification sound changed';message=item.name?`${item.name} is now configured.`:'The custom notification sound was changed.'}else{title=uiText(event||'dashboardEvent');message=[item.server_id&&item.server_id!=='dashboard'?item.server_id:'',item.name||''].filter(Boolean).join(' · ')||'Torrent Dashboard recorded an event.'}return{category,title,message,tone}}
function renderNotifications(){const list=$('#notificationList');if(!list)return;const filter=$('#notificationFilter')?.value||'all';let items=(state.notificationEvents||[]).filter(x=>state.server==='all'||x.server_id===state.server||x.server_id==='dashboard');if(filter!=='all')items=items.filter(x=>notificationCategory(x)===filter);if(!items.length){list.innerHTML=`<div class="empty"><strong>${uiText('noNotificationsYet')}</strong><span>${uiText('dashboardActivityWillAppearHere')}</span></div>`;return}list.innerHTML=items.map(item=>{const view=notificationPresentation(item);return`<article class="notification-item ${esc(view.tone)}"><span class="notification-dot" aria-hidden="true"></span><div class="notification-copy"><div class="notification-title"><b>${esc(view.title)}</b><span>${esc(uiText(view.category))}</span></div><p>${esc(view.message)}</p></div><time title="${esc(when(item.ts))}">${esc(rel(item.ts))}</time></article>`}).join('')}
async function loadNotifications(){try{const d=await api('/api/events?limit=200');state.notificationEvents=d.events||[];renderNotifications()}catch(err){toast(err.message,'error')}}

function renderServerSettings(servers){$('#serverSettings').innerHTML='';servers.forEach(s=>addServerRow(s))}
function addServerRow(s={id:'',name:'',base_url:'http://127.0.0.1:8080',auth_method:'api_key',api_key:'',username:'',password:'',enabled:true}){
  const d=document.createElement('div');d.className='server-setting';const method=s.auth_method||((s.api_key&&s.api_key!=='')?'api_key':'password');
  d.innerHTML=`<label>Display Name<input data-k="name" placeholder="Desktop" value="${esc(s.name||'')}"></label><label class="server-url">Web UI URL<input data-k="base_url" placeholder="http://127.0.0.1:8080" value="${esc(s.base_url||'')}"></label><label>Authentication<select data-k="auth_method"><option value="api_key" ${method==='api_key'?'selected':''}>API Key</option><option value="password" ${method==='password'?'selected':''}>Username And Password</option></select></label><div class="server-auth-api"><label>API Key<input data-k="api_key" type="password" autocomplete="off" placeholder="${s.api_key==='<configured>'?'API Key Configured':'qbt_…'}"></label><small>qBitTorrent 5.2+ · Bearer Authentication</small></div><div class="server-auth-password two"><label>Username<input data-k="username" autocomplete="off" value="${esc(s.username||'')}"></label><label>Password<input data-k="password" type="password" autocomplete="off" placeholder="${s.password==='<configured>'?'Password Configured':'Password'}"></label></div><div class="server-setting-actions"><button type="button" class="test-server">Test</button><button type="button" class="secondary client-settings" ${s.id?'':'disabled'}>Settings</button><button type="button" class="danger">Remove</button></div><input type="hidden" data-k="id" value="${esc(s.id||'')}"><small class="server-test-result"></small>`;
  const sync=()=>{const useApi=d.querySelector('[data-k="auth_method"]').value==='api_key';d.querySelector('.server-auth-api').classList.toggle('hidden',!useApi);d.querySelector('.server-auth-password').classList.toggle('hidden',useApi)};
  d.querySelector('[data-k="auth_method"]').addEventListener('change',sync);sync();d.querySelector('.danger').onclick=()=>d.remove();d.querySelector('.test-server').onclick=()=>testServerRow(d);d.querySelector('.client-settings').onclick=()=>TDSettings.openClientSettings(d.querySelector('[data-k="id"]').value);$('#serverSettings').append(d);applySentenceCaseUi(d);decorateSecretFields(d)
}
function serverRowData(r){let o={enabled:true};r.querySelectorAll('[data-k]').forEach(i=>o[i.dataset.k]=i.type==='password'?secretFieldValue(i,'<configured>'):i.value);return o}
async function testServerRow(r){const out=r.querySelector('.server-test-result');out.textContent=uiText('testing…');out.className='server-test-result';try{const d=await post('/api/client-test',serverRowData(r));out.textContent=`Connected · qBitTorrent ${d.version||'Unknown'} · Web API ${d.api_version||'Unknown'} · ${serverRowData(r).auth_method==='api_key'?'API Key':'Password'}`;out.className='server-test-result ok'}catch(e){out.textContent=e.message;out.className='server-test-result bad'}}
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
  for(const id of ['accountSettingsBtn','accountPasswordBtn','accountAvatarBtn']){const el=$('#'+id);if(el)el.disabled=!editable}
  if($('#accountRemoveAvatar'))$('#accountRemoveAvatar').disabled=!editable||!state.me?.avatar_configured;
  syncAvatarUi();
}
function applyAccountUser(user){
  if(!user||!state.me)return;
  Object.assign(state.me,{username:user.username,display_name:user.display_name,group:user.group,group_label:user.group_label,avatar_configured:!!user.avatar_configured,avatar_version:user.avatar_version||''});
  syncCurrentUserUi();
}
async function loadAccount(){
  const d=await api('/api/account');
  applyAccountUser(d.user);
  $('#accountUsername').value=d.user?.username||'';
  $('#accountFirstName').value=d.user?.first_name||'';
  $('#accountLastName').value=d.user?.last_name||'';
  $('#accountEmail').value=d.user?.email||'';
  $('#accountGroup').value=d.user?.group_label||uiText(d.user?.group||'standardUser');
  $('#accountProfilePassword').value='';
  return d.user;
}
async function openAccountModal(target='profile'){
  if(!state.me?.user_id)return toast('This session is not linked to a user account','error');
  $('#accountModal').classList.remove('hidden');
  const status=$('#accountStatus');status.className='test-result muted';status.textContent='Loading account…';
  try{
    await loadAccount();status.textContent='';
    const focusId=target==='password'?'accountCurrentPassword':target==='avatar'?'accountChooseAvatar':'accountFirstName';
    setTimeout(()=>$('#'+focusId)?.focus(),0);
  }catch(e){status.className='test-result bad';status.textContent=e.message}
}
function closeAccountModal(){$('#accountModal').classList.add('hidden');$('#accountProfileForm')?.reset();$('#accountPasswordForm')?.reset();$('#accountStatus').textContent=''}
async function saveOwnProfile(e){
  e.preventDefault();
  const status=$('#accountStatus');status.className='test-result muted';status.textContent='Saving profile…';
  try{
    const d=await post('/api/account',{username:$('#accountUsername').value.trim(),first_name:$('#accountFirstName').value.trim(),last_name:$('#accountLastName').value.trim(),email:$('#accountEmail').value.trim(),current_password:$('#accountProfilePassword').value});
    applyAccountUser(d.user);$('#accountProfilePassword').value='';status.className='test-result ok';status.textContent='Profile saved.';toast('profileSaved');
  }catch(e){status.className='test-result bad';status.textContent=e.message}
}
async function changeOwnPassword(e){
  e.preventDefault();
  const current=$('#accountCurrentPassword').value,next=$('#accountNewPassword').value,confirmPassword=$('#accountConfirmPassword').value,status=$('#accountStatus');
  if(next!==confirmPassword){status.className='test-result bad';status.textContent='New passwords do not match.';return}
  status.className='test-result muted';status.textContent='Changing password…';
  try{
    await post('/api/account/password',{current_password:current,new_password:next});
    $('#accountPasswordForm').reset();status.className='test-result ok';status.textContent='Password changed.';toast('passwordChanged');
  }catch(e){status.className='test-result bad';status.textContent=e.message}
}
async function uploadOwnAvatar(){
  const input=$('#accountAvatarInput'),file=input?.files?.[0],status=$('#accountStatus');
  if(!file)return;
  if(file.size>4*1024*1024){status.className='test-result bad';status.textContent='Profile picture must be 4 MB or smaller.';input.value='';return}
  const form=new FormData();form.append('avatar',file,file.name);
  status.className='test-result muted';status.textContent='Uploading profile picture…';
  try{
    const d=await api('/api/account/avatar',{method:'POST',body:form});applyAccountUser(d.user);status.className='test-result ok';status.textContent='Profile picture updated.';toast('profilePictureUpdated');
  }catch(e){status.className='test-result bad';status.textContent=e.message}
  finally{input.value=''}
}
async function removeOwnAvatar(){
  const status=$('#accountStatus');status.className='test-result muted';status.textContent='Removing profile picture…';
  try{const d=await post('/api/account/avatar/delete',{});applyAccountUser(d.user);status.className='test-result ok';status.textContent='Profile picture removed.';toast('profilePictureRemoved')}catch(e){status.className='test-result bad';status.textContent=e.message}
}
async function signOut(){try{await post('/api/logout',{})}catch{}location.reload()}

function registerPwa(){if('serviceWorker'in navigator){navigator.serviceWorker.register('/sw.js',{updateViaCache:'none'}).then(reg=>reg.update()).catch(()=>{});navigator.serviceWorker.addEventListener('controllerchange',()=>{if(sessionStorage.getItem('tdSwReloaded')!=='1'){sessionStorage.setItem('tdSwReloaded','1');location.reload()}})}window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();state.deferredPrompt=e;$('#installPwa').classList.remove('hidden')});$('#installPwa').onclick=async()=>{if(state.deferredPrompt){state.deferredPrompt.prompt();await state.deferredPrompt.userChoice;state.deferredPrompt=null;$('#installPwa').classList.add('hidden')}}}

applySentenceCaseUi(document);decorateSecretFields(document);caseObserver.observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['placeholder','title','aria-label']});bootstrap();
