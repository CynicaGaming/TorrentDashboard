#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "release_tools" / "validate_ui_strings.py"
text = path.read_text(encoding="utf-8")
old = '''    # 0.5.67 docks torrent details into the torrent workspace. The list must
    # remain the flexible scroll region and collapse must preserve selection.
    assert 'class="torrent-panel torrent-workspace"' in html
    assert 'class="torrent-list-region"' in html
    assert 'id="detailToggle"' in html and 'aria-label="Collapse torrent details"' in html
    assert "detailCollapsed:localStorage.tdDetailCollapsed==='1'" in app_js
    assert 'function syncDetailPaneState()' in app_js and 'async function toggleDetailPane()' in app_js
    assert "localStorage.tdDetailCollapsed=state.detailCollapsed?'1':'0'" in app_js
    assert "if(!state.detailCollapsed)await refreshDetailData(true)" in app_js
    assert "state.detailCollapsed&&!force" in app_js
    assert '0.5.67 docked collapsible torrent details' in app_css
    assert '.torrent-list-region .table-wrap{flex:1 1 auto;min-height:0;overflow:auto' in app_css
    assert '.torrent-detail-pane{position:static;inset:auto' in app_css
    assert '.torrent-detail-pane.collapsed{flex:0 0 58px!important' in app_css
    assert '@media(max-width:700px)' in app_css and 'top:auto!important;height:58px!important' in app_css
'''
new = '''    # 0.5.72 supersedes the original collapsible inspector contract. Torrent
    # list and details are distinct sibling surfaces; details are open or closed.
    assert 'class="torrent-workspace"' in html
    assert 'class="torrent-panel torrent-list-panel"' in html
    assert 'class="torrent-list-region"' in html
    assert 'id="detailToggle"' not in html and 'Collapse torrent details' not in html
    assert 'detailCollapsed' not in app_js and 'tdDetailCollapsed' not in app_js
    assert 'function syncDetailPaneState()' not in app_js and 'toggleDetailPane' not in app_js
    assert '0.5.72 separated viewport-docked torrent details' in app_css
    assert '.torrent-list-region .table-wrap{flex:1 1 auto;min-height:0;overflow:auto' in app_css
    assert '.torrent-detail-pane{position:static;inset:auto' in app_css
    assert 'border:1px solid var(--border);border-radius:var(--radius);box-shadow:var(--shadow)' in app_css
    assert '.torrent-detail-pane.collapsed' not in app_css and '.detail-pane-toggle' not in app_css
    assert '@media(max-width:700px)' in app_css
'''
count = text.count(old)
if count != 1:
    raise SystemExit(f"expected one legacy torrent-detail validator block, found {count}")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
print("Updated torrent-detail UI contract for v0.5.72")
