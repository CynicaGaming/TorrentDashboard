#!/usr/bin/env python3
from __future__ import annotations

import json,re,subprocess,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VERSION='0.5.58'

def read(p): return (ROOT/p).read_text(encoding='utf-8')
def write(p,s): (ROOT/p).write_text(s,encoding='utf-8')
def once(text,old,new,label):
    n=text.count(old)
    if n!=1: raise RuntimeError(f'Expected one {label} match, found {n}')
    return text.replace(old,new,1)

d=read('dashboard.py')
d,n=re.subn(r'^VERSION\s*=\s*["\']0\.5\.57["\']','VERSION = "0.5.58"',d,count=1,flags=re.M)
if n!=1: raise RuntimeError('Could not advance VERSION')
anchor='''def fetch_update_manifest(cfg):\n    return fetch_update_release(cfg)\n'''
helpers=r'''def fetch_update_manifest(cfg):
    return fetch_update_release(cfg)


def _release_history_markdown(item):
    version=str(item.get("version") or "").strip().lstrip("vV")
    title=str(item.get("title") or f"Torrent Dashboard v{version}").strip()
    summary=str(item.get("summary") or "").strip()
    lines=[f"## v{version} — {title}"]
    if summary: lines.extend(["",summary])
    for heading,values in (("What's changed",item.get("highlights") or []),("Fixes",item.get("fixes") or []),("Technical notes",item.get("technical") or []),("Validation",item.get("validation") or []),("Known issues",item.get("known_issues") or [])):
        clean=[str(x).strip() for x in values if str(x).strip()]
        if clean: lines.extend(["",f"### {heading},"" ])
        if clean:
            lines[-1]=f"### {heading}"
            lines.extend([""]+[f"- {value}" for value in clean])
    return "\n".join(lines).strip()+"\n"


def local_release_history(latest_manifest=None,limit=30):
    entries=[]
    try:
        data=json.loads((APP_DIR/"release_notes"/"releases.json").read_text(encoding="utf-8"))
        for raw in data.get("releases",[]):
            if not isinstance(raw,dict): continue
            version=str(raw.get("version") or "").strip().lstrip("vV")
            if not re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?",version): continue
            entries.append({"version":version,"title":str(raw.get("title") or f"Torrent Dashboard v{version}"),"summary":str(raw.get("summary") or ""),"publishedAt":str(raw.get("date") or ""),"channel":"prerelease" if raw.get("status")=="prerelease" else "stable","notes":_release_history_markdown(raw),"source":"bundled"})
    except Exception: entries=[]
    if isinstance(latest_manifest,dict) and latest_manifest.get("version"):
        version=str(latest_manifest.get("version") or "").strip().lstrip("vV")
        remote={"version":version,"title":str(latest_manifest.get("title") or f"Torrent Dashboard v{version}"),"summary":"","publishedAt":str(latest_manifest.get("publishedAt") or ""),"channel":str(latest_manifest.get("channel") or ""),"notes":str(latest_manifest.get("notes") or ""),"source":"github"}
        idx=next((i for i,x in enumerate(entries) if x.get("version")==version),None)
        if idx is None: entries.append(remote)
        else: entries[idx]={**entries[idx],**{k:v for k,v in remote.items() if v}}
    try: entries.sort(key=lambda x:_version_key(x.get("version") or "0"),reverse=True)
    except Exception: entries.reverse()
    seen=set();out=[]
    for item in entries:
        version=item.get("version")
        if not version or version in seen: continue
        seen.add(version);out.append(item)
        if len(out)>=max(1,int(limit)): break
    return out
'''
d=once(d,anchor,helpers,'manifest alias')
d=once(d,'        "updateState": update_state(),\n','        "updateState": update_state(),\n        "releaseHistory": local_release_history(),\n','runtime history')
d=once(d,'        "notes":str(release.get("body") or ""),\n','        "notes":str(release.get("body") or ""),\n        "title":str(release.get("name") or f"Torrent Dashboard v{version}"),\n','release title')
old='''    def update_check(self,cfg,new_cookie):
        try:
            repo = update_repository(cfg)
        except Exception as e:
            return self.send_json(200,{"configured":False,"currentVersion":VERSION,"error":str(e),"state":update_state()},new_cookie)
        try:
            manifest=fetch_update_manifest(cfg)
            return self.send_json(200,{"configured":True,"repository":repo,"currentVersion":VERSION,"manifest":manifest,"updateAvailable":manifest.get("updateAvailable",False),"state":update_state()},new_cookie)
        except Exception as e:
            return self.send_json(502,{"configured":True,"repository":repo,"currentVersion":VERSION,"error":str(e),"state":update_state()},new_cookie)
'''
new='''    def update_check(self,cfg,new_cookie):
        try:
            repo = update_repository(cfg)
        except Exception as e:
            return self.send_json(200,{"configured":False,"currentVersion":VERSION,"error":str(e),"state":update_state(),"releaseHistory":local_release_history()},new_cookie)
        try:
            manifest=fetch_update_manifest(cfg)
            return self.send_json(200,{"configured":True,"repository":repo,"currentVersion":VERSION,"manifest":manifest,"updateAvailable":manifest.get("updateAvailable",False),"state":update_state(),"releaseHistory":local_release_history(manifest)},new_cookie)
        except Exception as e:
            return self.send_json(502,{"configured":True,"repository":repo,"currentVersion":VERSION,"error":str(e),"state":update_state(),"releaseHistory":local_release_history()},new_cookie)
'''
d=once(d,old,new,'update_check')
write('dashboard.py',d)

s=read('static/settings.js')
s=once(s,"renderUpdateInfo({configured:!!updateRepository,repository:updateRepository,currentVersion:state.me?.version,state:s.runtime?.updateState||{}});","renderUpdateInfo({configured:!!updateRepository,repository:updateRepository,currentVersion:state.me?.version,state:s.runtime?.updateState||{},releaseHistory:s.runtime?.releaseHistory||[]});",'settings hydration')
write('static/settings.js',s)

h=read('static/index.html')
h=once(h,'''<div class="update-notes hidden" id="updateNotesWrap">
<div class="update-notes-heading"><strong>Patch Notes</strong><span id="updateNotesVersion"></span></div>
<div class="update-notes-content" id="updateNotes"></div>
</div>''','''<div class="update-notes hidden" id="updateNotesWrap">
<div class="update-notes-heading"><div><strong>Patch Notes</strong><span>Release history</span></div></div>
<div class="update-release-list" id="updateNotesList"></div>
</div>''','notes container')
h=h.replace('0.5.57','0.5.58')
write('static/index.html',h)

a=read('static/app.js')
a=once(a,"const FRONTEND_BUILD='0.5.57';","const FRONTEND_BUILD='0.5.58';",'frontend build')
start=a.find('function renderUpdateNotes('); end=a.find('async function checkForUpdates',start)
if start<0 or end<0: raise RuntimeError('Could not locate update renderer')
renderer=r'''function renderPatchMarkdown(box,markdown=''){
  box.replaceChildren();let list=null;
  for(const raw of String(markdown||'').replace(/\r/g,'').split('\n')){
    const line=raw.trim();if(!line){list=null;continue}
    const heading=line.match(/^(#{2,4})\s+(.+)$/);
    if(heading){list=null;const el=document.createElement(heading[1].length===2?'h4':'h5');el.textContent=heading[2];box.appendChild(el);continue}
    if(line.startsWith('- ')){if(!list){list=document.createElement('ul');box.appendChild(list)}const li=document.createElement('li');li.textContent=line.slice(2);list.appendChild(li);continue}
    list=null;const p=document.createElement('p');p.textContent=line;box.appendChild(p)
  }
}
function updateVersionParts(value=''){return String(value||'').replace(/^v/i,'').split(/[+-]/,1)[0].split('.').map(x=>Number(x)||0)}
function compareUpdateVersions(a,b){const aa=updateVersionParts(a),bb=updateVersionParts(b),n=Math.max(aa.length,bb.length);for(let i=0;i<n;i++){const d=(aa[i]||0)-(bb[i]||0);if(d)return d}return 0}
function normalizedReleaseHistory(history=[],manifest={}){
  const entries=Array.isArray(history)?history.filter(x=>x&&x.version).map(x=>({...x,version:String(x.version).replace(/^v/i,'')})):[];
  if(manifest?.version){const version=String(manifest.version).replace(/^v/i,'');const remote={version,title:manifest.title||`Torrent Dashboard v${version}`,publishedAt:manifest.publishedAt||'',channel:manifest.channel||'',notes:manifest.notes||'',source:'github'};const i=entries.findIndex(x=>x.version===version);if(i>=0)entries[i]={...entries[i],...Object.fromEntries(Object.entries(remote).filter(([,v])=>v!==''))};else entries.push(remote)}
  const seen=new Set();return entries.sort((a,b)=>compareUpdateVersions(b.version,a.version)).filter(x=>{if(seen.has(x.version))return false;seen.add(x.version);return true})
}
function renderUpdateHistory(history=[],manifest={},currentVersion=''){
  const wrap=$('#updateNotesWrap'),list=$('#updateNotesList');if(!wrap||!list)return;const entries=normalizedReleaseHistory(history,manifest);wrap.classList.toggle('hidden',!entries.length);list.replaceChildren();
  entries.forEach((entry,index)=>{const article=document.createElement('article');article.className='update-release';const summary=document.createElement('button');summary.type='button';summary.className='update-release-summary';const open=index===0;summary.setAttribute('aria-expanded',String(open));const copy=document.createElement('span');copy.className='update-release-copy';const title=document.createElement('strong');title.textContent=`v${entry.version}${entry.title?` · ${entry.title}`:''}`;copy.appendChild(title);const meta=document.createElement('small');const parts=[];const current=String(currentVersion||'').replace(/^v/i,'');if(entry.version===current)parts.push('Installed');if(manifest?.version&&entry.version===String(manifest.version).replace(/^v/i,'')&&entry.version!==current)parts.push('Latest available');if(entry.channel)parts.push(entry.channel==='prerelease'?'Pre-release':'Stable');if(entry.publishedAt)parts.push(String(entry.publishedAt).slice(0,10));meta.textContent=parts.join(' · ');copy.appendChild(meta);const chevron=document.createElement('span');chevron.className='update-release-chevron';chevron.textContent='⌄';summary.append(copy,chevron);const body=document.createElement('div');body.className=`update-release-body${open?'':' hidden'}`;renderPatchMarkdown(body,entry.notes||entry.summary||'No patch notes were recorded for this revision.');summary.addEventListener('click',()=>{const next=body.classList.contains('hidden');body.classList.toggle('hidden',!next);summary.setAttribute('aria-expanded',String(next))});article.append(summary,body);list.appendChild(article)})
}
function renderUpdateInfo(data){state.updateInfo=data||null;const current=data?.currentVersion||state.me?.version||'—',manifest=data?.manifest||{},st=data?.state||state.settings?.runtime?.updateState||{};$('#updateCurrent').textContent=current;$('#updateLatest').textContent=manifest.version||st.version||uiText('notChecked');$('#updateState').textContent=uiText(st.state||'idle');const msg=$('#updateMessage');msg.className='muted update-message';let text='';if(data?.error){text=data.error;msg.classList.add('bad')}else if(data?.configured===false){text=data?.error||'Enter and save a public GitHub repository under Updates before checking for updates'}else if(st.state==='readyToInstall'){text=`updateReadyToInstall ${st.version||manifest.version||''}`;msg.classList.add('ok')}else if(data?.updateAvailable){text=`updateAvailable ${manifest.version}${manifest.publishedAt?` · ${manifest.publishedAt}`:''}`;msg.classList.add('ok')}else if(manifest.version){text=`upToDate ${current}`;msg.classList.add('ok')}else if(st.state&&st.state!=='idle'){text=st.error||st.state}else{text='checkForUpdatesWhenReady'}msg.textContent=data?.error?text:uiText(text);renderUpdateHistory(data?.releaseHistory||state.settings?.runtime?.releaseHistory||[],manifest,current);updateActionButton(data)}
'''
a=a[:start]+renderer+a[end:]
write('static/app.js',a)

c=read('static/app.css')+'''\n\n/* Collapsible revision history in Settings > Updates. */\n.update-release-list{display:grid;gap:10px;margin-top:10px}\n.update-release{border:1px solid var(--border);border-radius:10px;overflow:hidden;background:var(--panel-2,rgba(255,255,255,.025))}\n.update-release-summary{width:100%;display:flex;align-items:center;justify-content:space-between;gap:16px;padding:13px 14px;border:0;background:transparent;color:inherit;text-align:left;cursor:pointer}\n.update-release-summary:hover{background:rgba(127,127,127,.06)}\n.update-release-copy{display:grid;gap:3px;min-width:0}.update-release-copy strong{font-size:.94rem;line-height:1.3;overflow-wrap:anywhere}.update-release-copy small{color:var(--muted);font-size:.77rem}\n.update-release-chevron{font-size:1.1rem;transition:transform .16s ease;color:var(--muted)}.update-release-summary[aria-expanded="true"] .update-release-chevron{transform:rotate(180deg)}\n.update-release-body{padding:4px 14px 14px;border-top:1px solid var(--border);line-height:1.55}.update-release-body h4,.update-release-body h5{margin:14px 0 7px}.update-release-body p{margin:8px 0;color:var(--muted)}.update-release-body ul{margin:7px 0 7px 20px;padding:0;color:var(--muted)}.update-release-body li+li{margin-top:5px}\n'''
write('static/app.css',c)
write('static/sw.js',read('static/sw.js').replace('torrent-dashboard-v0557','torrent-dashboard-v0558').replace('0.5.57','0.5.58'))

p=ROOT/'release_notes'/'releases.json';data=json.loads(p.read_text(encoding='utf-8'))
if any(str(x.get('version'))==VERSION for x in data.get('releases',[])): raise RuntimeError('v0.5.58 metadata already exists')
prev=data['releases'][-1]
data['releases'].append({
 'version':VERSION,'date':'2026-09-02','status':'prerelease','title':'Collapsible revision patch notes',
 'summary':'Expanded Settings → Updates from a single latest-release note block into a collapsible patch-note history for every documented Torrent Dashboard revision.',
 'highlights':['Settings → Updates now shows one collapsible patch-note entry per documented revision, ordered newest first.','Bundled release metadata is available immediately when the Updates page opens; a newly discovered GitHub release is merged into the history before it is installed.','The newest revision opens by default and each older revision can be expanded independently.','Future prerelease publication preserves older prereleases instead of deleting the complete prerelease history.'],
 'fixes':['Patch notes are no longer limited to only the latest GitHub release body.'],
 'technical':['The backend exposes sanitized releaseHistory metadata from release_notes/releases.json and merges the current GitHub manifest into it.','The accordion renderer continues to build DOM nodes with textContent rather than injecting release HTML.'],
 'validation':['Python compilation validates the release-history helper and existing update path.','JavaScript syntax validation covers the accordion, version ordering, and safe Markdown-to-DOM renderer.','Generated CHANGELOG.md and PROJECT_STATE.md must match the v0.5.58 structured metadata before publication.'],
 'known_issues':['Structured historical notes begin at v0.5.55 because earlier releases predate the release metadata pipeline.'],
 'architecture':prev.get('architecture',[])+['Update history is sourced from bundled structured release metadata and supplemented with the latest GitHub release manifest during update checks.'],
 'decisions':prev.get('decisions',[])+['Preserve future GitHub prereleases instead of deleting all older prereleases during publication.'],
 'next_steps':prev.get('next_steps',[])
})
p.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
subprocess.run([sys.executable,str(ROOT/'release_tools'/'generate_release_notes.py'),'--version',VERSION],check=True)
print('Applied v0.5.58 collapsible revision patch notes update')
