#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one match in {path}: found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    settings = ROOT / "static" / "settings.js"
    css = ROOT / "static" / "settings.css"
    dashboard = ROOT / "dashboard.py"
    sw = ROOT / "static" / "sw.js"
    index = ROOT / "static" / "index.html"
    app = ROOT / "static" / "app.js"
    releases = ROOT / "release_notes" / "releases.json"

    replace_once(
        settings,
        '<div class="jellyfin-library-list" data-jellyfin-libraries><div class="integration-service-empty">Loading libraries…</div></div>',
        '<div class="jellyfin-library-progress hidden" data-jellyfin-library-progress></div><div class="jellyfin-library-list" data-jellyfin-libraries><div class="integration-service-empty">Loading libraries…</div></div>',
    )

    marker = "  function renderJellyfinOverview(card, data) {"
    helper = '''  function jellyfinLibraryScanState(libraries) {
    const active=[];
    for(const library of (Array.isArray(libraries)?libraries:[])){
      const raw=library?.refresh_progress;
      const progress=(raw===null||raw===undefined||raw==='')?null:Number(raw);
      const bounded=Number.isFinite(progress)?Math.max(0,Math.min(100,progress)):null;
      const status=String(library?.refresh_status||'').trim();
      const normalized=status.toLowerCase();
      const statusActive=!!normalized&&!['idle','completed','complete','success','succeeded'].includes(normalized);
      if(statusActive||(bounded!==null&&bounded>0&&bounded<100))active.push({progress:bounded,status});
    }
    if(!active.length)return null;
    const values=active.map(item=>item.progress).filter(Number.isFinite);
    const progress=values.length?values.reduce((sum,value)=>sum+value,0)/values.length:null;
    const status=active.map(item=>item.status).find(Boolean)||'Scanning';
    return {progress,status};
  }

  function renderJellyfinLibraryProgress(card,libraries) {
    const host=card.querySelector('[data-jellyfin-library-progress]');
    const runtime=card.querySelector('[data-jellyfin-service]');
    const scan=jellyfinLibraryScanState(libraries);
    if(runtime)runtime.dataset.libraryScanning=scan?'1':'0';
    if(!host)return;
    if(!scan){host.classList.add('hidden');host.innerHTML='';return}
    const progress=Number.isFinite(scan.progress)?Math.max(0,Math.min(100,scan.progress)):null;
    const percentage=progress===null?'':`${progress.toFixed(progress%1?1:0)}%`;
    const detail=[uiText(scan.status||'Scanning'),percentage].filter(Boolean).join(' · ');
    host.classList.remove('hidden');
    host.innerHTML=`<article class="jellyfin-task-row running"><span class="jellyfin-task-clock">${jellyfinTaskIcon('cycle')}</span><div class="jellyfin-task-copy"><strong>Scan media library</strong><span>${esc(detail||'Running')}</span></div><strong class="jellyfin-library-progress-value">${esc(percentage||'…')}</strong></article>`;
  }

  function scheduleJellyfinLibraryPoll(card,force=false) {
    if(card._jellyfinLibraryTimer)clearTimeout(card._jellyfinLibraryTimer);
    const runtime=card.querySelector('[data-jellyfin-service]');
    if(!force&&runtime?.dataset.libraryScanning!=='1')return;
    card._jellyfinLibraryTimer=setTimeout(()=>{
      if(!card.isConnected||card.querySelector('.accordion-body')?.classList.contains('hidden'))return;
      loadJellyfinOverview(card);
    },2000);
  }

'''
    text = settings.read_text(encoding="utf-8")
    if marker not in text:
        raise RuntimeError("renderJellyfinOverview marker not found")
    settings.write_text(text.replace(marker, helper + marker, 1), encoding="utf-8")

    replace_once(
        settings,
        "    const count=card.querySelector('[data-jellyfin-library-count]');if(count)count.textContent=`${libraries.length} ${libraries.length===1?'library':'libraries'}`;\n    const list=card.querySelector('[data-jellyfin-libraries]');if(!list)return;",
        "    const count=card.querySelector('[data-jellyfin-library-count]');if(count)count.textContent=`${libraries.length} ${libraries.length===1?'library':'libraries'}`;\n    renderJellyfinLibraryProgress(card,libraries);\n    const list=card.querySelector('[data-jellyfin-libraries]');if(!list)return;",
    )

    replace_once(
        settings,
        "const statusText=String(library.refresh_status||'').trim();const progress=Number(library.refresh_progress);const scan=Number.isFinite(progress)?`${Math.max(0,Math.min(100,progress)).toFixed(progress%1?1:0)}%${statusText?` · ${esc(uiText(statusText))}`:''}`:(statusText?esc(uiText(statusText)):'Idle');",
        "const statusText=String(library.refresh_status||'').trim();const rawProgress=library.refresh_progress;const progress=(rawProgress===null||rawProgress===undefined||rawProgress==='')?null:Number(rawProgress);const scan=Number.isFinite(progress)?`${Math.max(0,Math.min(100,progress)).toFixed(progress%1?1:0)}%${statusText?` · ${esc(uiText(statusText))}`:''}`:(statusText?esc(uiText(statusText)):'Idle');",
    )

    replace_once(
        settings,
        "try{const data=await api(`/api/integrations/jellyfin/status?id=${encodeURIComponent(card.dataset.id)}`);runtime.dataset.loaded='1';renderJellyfinOverview(card,data)}catch(error)",
        "try{const data=await api(`/api/integrations/jellyfin/status?id=${encodeURIComponent(card.dataset.id)}`);runtime.dataset.loaded='1';renderJellyfinOverview(card,data);if(runtime.dataset.libraryScanning==='1')scheduleJellyfinLibraryPoll(card)}catch(error)",
    )

    replace_once(
        settings,
        "try{const result=await post('/api/integrations/jellyfin/refresh',{id:card.dataset.id});toast(result.message||'Jellyfin library refresh requested');await new Promise(resolve=>setTimeout(resolve,700));await loadJellyfinOverview(card)}catch(error)",
        "try{const result=await post('/api/integrations/jellyfin/refresh',{id:card.dataset.id});toast(result.message||'Jellyfin library refresh requested');scheduleJellyfinLibraryPoll(card,true);await new Promise(resolve=>setTimeout(resolve,500));await loadJellyfinOverview(card)}catch(error)",
    )

    css_text = css.read_text(encoding="utf-8")
    css_append = '''\n/* 0.5.132 Jellyfin library scan progress */\n.jellyfin-library-progress{margin:0 0 8px}.jellyfin-library-progress .jellyfin-task-row{grid-template-columns:28px minmax(0,1fr) auto}.jellyfin-library-progress-value{min-width:42px;text-align:right;font-size:10px;color:var(--accent);font-variant-numeric:tabular-nums}.jellyfin-library-progress .jellyfin-task-clock .material-symbol-icon{animation:jellyfinRefreshSpin 1s linear infinite}\n@media(max-width:700px){.jellyfin-library-progress .jellyfin-task-row{grid-template-columns:26px minmax(0,1fr) auto}.jellyfin-library-progress-value{font-size:10px}}\n@media(prefers-reduced-motion:reduce){.jellyfin-library-progress .jellyfin-task-clock .material-symbol-icon{animation:none}}\n'''
    if "0.5.132 Jellyfin library scan progress" not in css_text:
        css.write_text(css_text.rstrip() + css_append, encoding="utf-8")

    replace_once(dashboard, 'VERSION = "0.5.131"', 'VERSION = "0.5.132"')
    replace_once(app, "const FRONTEND_BUILD='0.5.131';", "const FRONTEND_BUILD='0.5.132';")

    index_text = index.read_text(encoding="utf-8")
    if index_text.count("0.5.131") < 5:
        raise RuntimeError("Unexpected index frontend version count")
    index.write_text(index_text.replace("0.5.131", "0.5.132"), encoding="utf-8")

    replace_once(sw, "torrent-dashboard-v05131", "torrent-dashboard-v05132")
    sw_text = sw.read_text(encoding="utf-8")
    if sw_text.count("v=0.5.131") != 4:
        raise RuntimeError("Unexpected service-worker asset version count")
    sw.write_text(sw_text.replace("v=0.5.131", "v=0.5.132"), encoding="utf-8")

    data=json.loads(releases.read_text(encoding="utf-8"))
    if any(str(item.get('version'))=='0.5.132' for item in data.get('releases',[])):
        raise RuntimeError('v0.5.132 metadata already exists')
    data['releases'].insert(0,{
        'version':'0.5.132','date':'2026-09-07','status':'prerelease','title':'Jellyfin library scan progress',
        'summary':'Shows active Jellyfin library rescans using the same compact running-task presentation as Scheduled tasks.',
        'highlights':['Shows an inline Scan media library task row while a Jellyfin library refresh is running.','Displays Jellyfin-reported scan status and percentage using the existing scheduled-task visual language.','Polls the Jellyfin overview every two seconds only while a library scan is active.'],
        'fixes':['Treats a missing Jellyfin RefreshProgress value as idle instead of coercing it to 0%.'],
        'technical':['Uses existing /Library/VirtualFolders RefreshStatus and RefreshProgress data; no new Jellyfin API surface is required.','Keeps polling scoped to an expanded, connected Jellyfin integration and stops automatically when the scan completes.'],
        'validation':['Source validation, unit tests, UI-string validation, JavaScript syntax checks, and release-note checks run before publication.'],
        'known_issues':[],'architecture':[],'decisions':[],'next_steps':[]
    })
    releases.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

    subprocess.run(["python", str(ROOT/"release_tools"/"generate_release_notes.py"), "--version", "0.5.132"], cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
