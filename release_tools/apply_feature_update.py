#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
app_path = ROOT / 'static' / 'app.js'
css_path = ROOT / 'static' / 'app.css'
index_path = ROOT / 'static' / 'index.html'
sw_path = ROOT / 'static' / 'sw.js'
dash_path = ROOT / 'dashboard.py'
validator_path = ROOT / 'release_tools' / 'validate_ui_strings.py'

app = app_path.read_text(encoding='utf-8')
css = css_path.read_text(encoding='utf-8')
index = index_path.read_text(encoding='utf-8')
sw = sw_path.read_text(encoding='utf-8')
dash = dash_path.read_text(encoding='utf-8')
validator = validator_path.read_text(encoding='utf-8')

# Version and browser-asset cache revision.
if 'VERSION = "0.5.9"' not in dash:
    raise SystemExit('Expected Torrent Dashboard 0.5.9 source')
dash = dash.replace('VERSION = "0.5.9"', 'VERSION = "0.5.10"', 1)
index = index.replace('?v=0.5.9', '?v=0.5.10')
sw = sw.replace('torrent-dashboard-v059', 'torrent-dashboard-v0510').replace('?v=0.5.9', '?v=0.5.10')

# qBitTorrent exposes automatic torrent management directly. Add it to the
# existing action bridge so the familiar menu item has real backend behavior.
if 'if action == "set_auto_management":' not in dash:
    marker = '        if action == "set_location":\n'
    if marker not in dash:
        raise SystemExit('Could not locate qBitTorrent set_location action')
    addition = (
        '        if action == "set_auto_management":\n'
        '            return self.post("/api/v2/torrents/setAutoManagement", {"hashes": hashes, "enable": str(bool(payload.get("value"))).lower()})\n'
    )
    dash = dash.replace(marker, addition + marker, 1)

# Replace the torrent menu with a qBitTorrent-inspired hierarchy while keeping
# Torrent Dashboard styling and permission semantics. Unsupported desktop-only
# actions such as opening the server file explorer are intentionally omitted.
start = app.find('function showTorrentMenu(')
end = app.find('\nfunction showMenu(', start)
if start < 0 or end < 0:
    raise SystemExit('Could not locate showTorrentMenu block')
new_menu = r'''function showTorrentMenu(tr,anchor,context=false){
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
    items.push(item('set_auto_management','Automatic torrent management',t.auto_tmm?'✓':'□'));
    items.push(sep);
  }

  items.push(item('details','Torrent options…','ⓘ'));

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
    if(a==='delete'){
      const files=confirm('Also delete downloaded files?\nCancel = keep files.');
      if(!confirm(`Remove ${t.name} from Torrent Dashboard?`))return;
      return doAction('delete',{server:sid,hashes:[h],delete_files:files});
    }
    if(a==='force_start')return doAction('force_start',{server:sid,hashes:[h],value:!t.force_start});
    if(a==='set_auto_management')return doAction('set_auto_management',{server:sid,hashes:[h],value:!t.auto_tmm});
    if(a==='set_location'){
      const v=prompt('New save location:',t.save_path||'');
      if(v!==null&&v.trim())return doAction('set_location',{server:sid,hashes:[h],location:v.trim()});
      return;
    }
    if(a==='rename'){
      const v=prompt('New torrent name:',t.name||'');
      if(v!==null&&v.trim())return doAction('rename',{server:sid,hash:h,hashes:[h],name:v.trim()});
      return;
    }
    if(a==='set_category'){
      const v=prompt('Category:',t.category||'');
      if(v!==null)return doAction('set_category',{server:sid,hashes:[h],category:v.trim()});
      return;
    }
    if(a==='tags'){
      const current=String(t.tags||'').split(',').map(x=>x.trim()).filter(Boolean);
      const v=prompt('Tags (comma-separated):',current.join(', '));
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
}'''
app = app[:start] + new_menu + app[end:]

# Make the generic popup positioning aware of the rendered menu dimensions.
menu_start = app.find('function showMenu(')
menu_end = app.find('\n\nasync function doAction', menu_start)
if menu_start < 0 or menu_end < 0:
    raise SystemExit('Could not locate showMenu block')
new_show = r'''function showMenu(m,anchor){
  $$('.menu').forEach(x=>{if(x!==m)x.classList.add('hidden')});
  m.classList.remove('hidden');
  const r=anchor.getBoundingClientRect(),rect=m.getBoundingClientRect();
  const left=Math.max(8,Math.min(innerWidth-rect.width-8,r.right-rect.width));
  let top=r.bottom+5;
  if(top+rect.height>innerHeight-8)top=Math.max(8,r.top-rect.height-5);
  m.style.left=left+'px';m.style.top=top+'px';
}'''
app = app[:menu_start] + new_show + app[menu_end:]

# Keep outside-click handling from treating a torrent row ellipsis as outside.
old_outside = "document.addEventListener('click',e=>{if(!e.target.closest('.menu')&&!e.target.closest('#moreBtn')&&!e.target.closest('.more-row'))$$('.menu').forEach(m=>m.classList.add('hidden'))});"
if old_outside not in app:
    raise SystemExit('Could not locate torrent-menu outside-click handler')

menu_css = r'''

/* 0.5.10 qBitTorrent-inspired torrent action menu. */
#contextMenu{min-width:250px;max-width:min(292px,calc(100vw - 16px));max-height:calc(100vh - 16px);overflow-y:auto;overscroll-behavior:contain;padding:6px;scrollbar-width:thin}
#contextMenu button{display:flex;align-items:center;gap:9px;min-height:34px;padding:7px 10px;border-radius:8px;white-space:nowrap}
#contextMenu button:hover{background:var(--panel3)}
#contextMenu .menu-icon{display:inline-grid;place-items:center;flex:0 0 17px;width:17px;color:var(--muted);font-size:12px;font-weight:700}
#contextMenu button:hover .menu-icon{color:var(--accent)}
#contextMenu .menu-separator{height:1px;background:color-mix(in srgb,var(--border) 78%,transparent);margin:5px 2px}
#contextMenu .menu-caption{padding:5px 10px 3px;color:var(--muted);font-size:8px;text-transform:uppercase;letter-spacing:.08em}
#contextMenu button.danger{color:var(--bad)!important;background:transparent!important;border:0!important}
#contextMenu button.danger:hover{background:color-mix(in srgb,var(--bad) 9%,transparent)!important}
@media(max-width:700px){
  #contextMenu{left:8px!important;right:8px!important;top:auto!important;bottom:calc(68px + env(safe-area-inset-bottom));min-width:0;max-width:none;max-height:min(68vh,560px);padding:8px;border-radius:16px}
  #contextMenu button{min-height:44px;padding:10px 12px;font-size:12px;border-radius:10px}
  #contextMenu .menu-icon{flex-basis:20px;width:20px;font-size:14px}
  #contextMenu .menu-caption{padding:7px 12px 4px;font-size:9px}
  #contextMenu .menu-separator{margin:6px 3px}
}
'''
if '/* 0.5.10 qBitTorrent-inspired torrent action menu. */' not in css:
    css += menu_css

# Extend release-time UI checks to cover the menu structure and mobile treatment.
if 'qBitTorrent-inspired torrent menu' not in validator:
    validator = validator.replace(
        '    settings_js = (ROOT / "static" / "settings.js").read_text(encoding="utf-8")\n',
        '    settings_js = (ROOT / "static" / "settings.js").read_text(encoding="utf-8")\n    app_css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")\n',
        1,
    )
    validator = validator.replace(
        '    assert "applySentenceCaseUi(card)" in settings_js\n',
        '    assert "applySentenceCaseUi(card)" in settings_js\n'
        '    # qBitTorrent-inspired torrent menu must remain functional and mobile friendly.\n'
        '    assert "Torrent options…" in app_js\n'
        '    assert "Automatic torrent management" in app_js\n'
        '    assert "set_auto_management" in (ROOT / "dashboard.py").read_text(encoding="utf-8")\n'
        '    assert "menu-separator" in app_css and "@media(max-width:700px)" in app_css\n'
        '    assert "e.target.closest(\'button[data-a]\')" in app_js\n',
        1,
    )

app_path.write_text(app, encoding='utf-8')
css_path.write_text(css, encoding='utf-8')
index_path.write_text(index, encoding='utf-8')
sw_path.write_text(sw, encoding='utf-8')
dash_path.write_text(dash, encoding='utf-8')
validator_path.write_text(validator, encoding='utf-8')

assert 'VERSION = "0.5.10"' in dash
assert '?v=0.5.10' in index
assert 'torrent-dashboard-v0510' in sw
assert 'Automatic torrent management' in app
assert 'Set location…' in app and 'Rename…' in app
assert 'Torrent options…' in app and 'Force recheck' in app and 'Force reannounce' in app
assert 'setAutoManagement' in dash
assert '0.5.10 qBitTorrent-inspired torrent action menu' in css
print('qBitTorrent-style torrent menu update applied')
