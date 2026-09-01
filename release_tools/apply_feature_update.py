#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
app_path = ROOT / 'static' / 'app.js'
index_path = ROOT / 'static' / 'index.html'
sw_path = ROOT / 'static' / 'sw.js'
dash_path = ROOT / 'dashboard.py'

app = app_path.read_text(encoding='utf-8')
index = index_path.read_text(encoding='utf-8')
sw = sw_path.read_text(encoding='utf-8')
dash = dash_path.read_text(encoding='utf-8')

# Version bump.
dash = re.sub(r'^VERSION\s*=\s*["\']0\.5\.8["\']', 'VERSION = "0.5.9"', dash, count=1, flags=re.M)
index = index.replace('?v=0.5.8', '?v=0.5.9')
sw = sw.replace('torrent-dashboard-v058', 'torrent-dashboard-v059').replace('?v=0.5.8', '?v=0.5.9')

# The delegated row click opened the context menu and then allowed the same click
# to bubble to the document-level outside-click handler, which immediately hid it.
old_row = "function rowClick(e){const tr=e.target.closest('tr');if(!tr)return;if(e.target.closest('.rowcheck'))return;if(e.target.closest('.more-row')){showTorrentMenu(tr,e.target);return}openDetail(tr.dataset.server,tr.dataset.hash)}"
new_row = "function rowClick(e){const tr=e.target.closest('tr');if(!tr)return;if(e.target.closest('.rowcheck'))return;if(e.target.closest('.more-row')){e.stopPropagation();showTorrentMenu(tr,e.target.closest('.more-row'));return}openDetail(tr.dataset.server,tr.dataset.hash)}"
if old_row not in app:
    raise SystemExit('Could not locate rowClick implementation')
app = app.replace(old_row, new_row, 1)

old_outside = "document.addEventListener('click',e=>{if(!e.target.closest('.menu')&&!e.target.closest('#moreBtn'))$$('.menu').forEach(m=>m.classList.add('hidden'))});"
new_outside = "document.addEventListener('click',e=>{if(!e.target.closest('.menu')&&!e.target.closest('#moreBtn')&&!e.target.closest('.more-row'))$$('.menu').forEach(m=>m.classList.add('hidden'))});"
if old_outside not in app:
    raise SystemExit('Could not locate outside-click handler')
app = app.replace(old_outside, new_outside, 1)

# Replace the torrent action menu with a permission-aware menu. Details and Copy
# hash remain available to Standard Users; mutation controls are Administrator-only.
start = app.find('function showTorrentMenu(')
end = app.find('\nfunction showMenu(', start)
if start < 0 or end < 0:
    raise SystemExit('Could not locate showTorrentMenu block')
new_menu = r'''function showTorrentMenu(tr,anchor,context=false){
  const m=$('#contextMenu'),sid=tr.dataset.server,h=tr.dataset.hash;
  const t=state.torrents.find(x=>(x._server_id||state.server)===sid&&x.hash===h);
  if(!t)return;
  const admin=!!state.me?.can_manage;
  const items=[
    '<button data-a="details">Details</button>',
    admin?`<button data-a="${isPaused(t)?'start':'stop'}">${isPaused(t)?'Resume':'Pause'}</button>`:'',
    admin?'<button data-a="recheck">Recheck</button>':'',
    admin?'<button data-a="reannounce">Reannounce</button>':'',
    admin?`<button data-a="force_start">${t.force_start?'Disable force start':'Enable force start'}</button>`:'',
    admin?'<button data-a="toggle_sequential">Toggle sequential download</button>':'',
    admin?'<button data-a="toggle_first_last">Toggle first/last priority</button>':'',
    admin?'<button data-a="top_priority">Move to top</button>':'',
    admin?'<button data-a="increase_priority">Move up</button>':'',
    admin?'<button data-a="decrease_priority">Move down</button>':'',
    admin?'<button data-a="bottom_priority">Move to bottom</button>':'',
    admin?'<button data-a="set_category">Set category…</button>':'',
    admin?'<button data-a="add_tags">Add tags…</button>':'',
    '<button data-a="copy_hash">Copy hash</button>',
    admin?'<button data-a="delete" class="danger">Delete…</button>':''
  ].filter(Boolean);
  m.innerHTML=items.join('');
  applySentenceCaseUi(m);
  m.onclick=async e=>{
    const button=e.target.closest('button[data-a]'),a=button?.dataset.a;
    if(!a)return;
    m.classList.add('hidden');
    if(a==='details')return openDetail(sid,h);
    if(a==='copy_hash')return navigator.clipboard.writeText(h).then(()=>toast('Hash copied'));
    if(!state.me?.can_manage)return toast('Administrator access is required','error');
    if(a==='delete'){
      const files=confirm('Also delete downloaded files?\nCancel = keep files.');
      if(!confirm(`Delete ${t.name}?`))return;
      return doAction('delete',{server:sid,hashes:[h],delete_files:files});
    }
    if(a==='force_start')return doAction('force_start',{server:sid,hashes:[h],value:!t.force_start});
    if(a==='set_category'){const v=prompt('Category name:');if(v!==null)return doAction(a,{server:sid,hashes:[h],category:v})}
    if(a==='add_tags'){const v=prompt('Comma-separated tags:');if(v)return doAction(a,{server:sid,hashes:[h],tags:v})}
    return doAction(a,{server:sid,hashes:[h]});
  };
  if(context){
    const r=anchor.getBoundingClientRect();
    m.style.left=Math.max(8,Math.min(innerWidth-205,r.left))+'px';
    m.style.top=Math.max(8,Math.min(innerHeight-360,r.top))+'px';
    m.classList.remove('hidden');
  }else showMenu(m,anchor);
}'''
app = app[:start] + new_menu + app[end:]

# Use the current role model rather than the removed legacy read_only flag.
old_action = "async function doAction(action,payload={}){if(state.me.read_only)return toast('dashboardIsReadOnly','error');"
new_action = "async function doAction(action,payload={}){if(!state.me?.can_manage)return toast('Administrator access is required','error');"
if old_action in app:
    app = app.replace(old_action, new_action, 1)

app_path.write_text(app, encoding='utf-8')
index_path.write_text(index, encoding='utf-8')
sw_path.write_text(sw, encoding='utf-8')
dash_path.write_text(dash, encoding='utf-8')

# Release-time sanity checks for this regression.
assert 'VERSION = "0.5.9"' in dash
assert '?v=0.5.9' in index
assert 'torrent-dashboard-v059' in sw
assert 'e.stopPropagation();showTorrentMenu' in app
assert "!e.target.closest('.more-row')" in app
assert '<button data-a="details">Details</button>' in app
assert "if(a==='details')return openDetail(sid,h);" in app
assert "const admin=!!state.me?.can_manage;" in app
print('Torrent action menu update applied')
