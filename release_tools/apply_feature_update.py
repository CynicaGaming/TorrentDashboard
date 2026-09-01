#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
app_path = ROOT / 'static' / 'app.js'
settings_css_path = ROOT / 'static' / 'settings.css'
index_path = ROOT / 'static' / 'index.html'
sw_path = ROOT / 'static' / 'sw.js'
dash_path = ROOT / 'dashboard.py'
validator_path = ROOT / 'release_tools' / 'validate_ui_strings.py'

app = app_path.read_text(encoding='utf-8')
settings_css = settings_css_path.read_text(encoding='utf-8')
index = index_path.read_text(encoding='utf-8')
sw = sw_path.read_text(encoding='utf-8')
dash = dash_path.read_text(encoding='utf-8')
validator = validator_path.read_text(encoding='utf-8')

# Version and browser asset revisions.
if 'VERSION = "0.5.10"' not in dash:
    raise SystemExit('Expected Torrent Dashboard 0.5.10 source')
dash = dash.replace('VERSION = "0.5.10"', 'VERSION = "0.5.11"', 1)
index = index.replace('?v=0.5.10', '?v=0.5.11')
sw = sw.replace('torrent-dashboard-v0510', 'torrent-dashboard-v0511').replace('?v=0.5.10', '?v=0.5.11')

# Automatic torrent management was intentionally removed from the Dashboard UI.
# Remove the dedicated backend bridge as well so unsupported/dead actions do not linger.
auto_backend = '''        if action == "set_auto_management":\n            return self.post("/api/v2/torrents/setAutoManagement", {"hashes": hashes, "enable": str(bool(payload.get("value"))).lower()})\n'''
if auto_backend not in dash:
    raise SystemExit('Could not locate automatic torrent management backend action')
dash = dash.replace(auto_backend, '', 1)

# Match qBitTorrent's explicit interaction model: clicking a row itself performs no
# navigation. The row ellipsis and right-click context menu are the deliberate entry
# points for torrent actions/details.
old_row = "function rowClick(e){const tr=e.target.closest('tr');if(!tr)return;if(e.target.closest('.rowcheck'))return;if(e.target.closest('.more-row')){e.stopPropagation();showTorrentMenu(tr,e.target.closest('.more-row'));return}openDetail(tr.dataset.server,tr.dataset.hash)}"
new_row = "function rowClick(e){const tr=e.target.closest('tr');if(!tr)return;if(e.target.closest('.rowcheck'))return;if(e.target.closest('.more-row')){e.stopPropagation();showTorrentMenu(tr,e.target.closest('.more-row'));return}}"
if old_row not in app:
    raise SystemExit('Could not locate current rowClick implementation')
app = app.replace(old_row, new_row, 1)

# Remove Automatic torrent management from the menu and rename the details entry.
auto_menu = "    items.push(item('set_auto_management','Automatic torrent management',t.auto_tmm?'✓':'□'));\n"
if auto_menu not in app:
    raise SystemExit('Could not locate automatic torrent management menu item')
app = app.replace(auto_menu, '', 1)

old_details = "  items.push(item('details','Torrent options…','ⓘ'));"
new_details = "  items.push(item('details','Torrent details','ⓘ'));"
if old_details not in app:
    raise SystemExit('Could not locate Torrent options menu item')
app = app.replace(old_details, new_details, 1)

auto_handler = "    if(a==='set_auto_management')return doAction('set_auto_management',{server:sid,hashes:[h],value:!t.auto_tmm});\n"
if auto_handler not in app:
    raise SystemExit('Could not locate automatic torrent management click handler')
app = app.replace(auto_handler, '', 1)

# Standard Users need the explicit context menu once row-click navigation is gone.
# They still receive only the non-mutating menu items produced by showTorrentMenu().
old_standard = '.standard-user .admin-only,.standard-user .row-actions,.standard-user #bulkbar,.standard-user .detail-actions,.standard-user #contextMenu{display:none!important}'
new_standard = '.standard-user .admin-only,.standard-user #bulkbar,.standard-user .detail-actions{display:none!important}'
if old_standard not in settings_css:
    raise SystemExit('Could not locate Standard User visibility rule')
settings_css = settings_css.replace(old_standard, new_standard, 1)

# Strengthen release validation for the interaction contract.
needle = '    assert "applySentenceCaseUi(card)" in settings_js\n'
addition = '''    assert "applySentenceCaseUi(card)" in settings_js\n    assert "Torrent details" in app_js\n    assert "Torrent options…" not in app_js\n    assert "Automatic torrent management" not in app_js\n    assert "set_auto_management" not in app_js\n    assert "openDetail(tr.dataset.server,tr.dataset.hash)" not in app_js\n'''
if needle not in validator:
    raise SystemExit('Could not locate UI validator insertion point')
validator = validator.replace(needle, addition, 1)

app_path.write_text(app, encoding='utf-8')
settings_css_path.write_text(settings_css, encoding='utf-8')
index_path.write_text(index, encoding='utf-8')
sw_path.write_text(sw, encoding='utf-8')
dash_path.write_text(dash, encoding='utf-8')
validator_path.write_text(validator, encoding='utf-8')

assert 'VERSION = "0.5.11"' in dash
assert 'set_auto_management' not in dash
assert '?v=0.5.11' in index
assert 'torrent-dashboard-v0511' in sw
assert "Torrent details" in app
assert "Automatic torrent management" not in app
assert "openDetail(tr.dataset.server,tr.dataset.hash)" not in app
assert '.standard-user .row-actions' not in settings_css
print('Torrent context interaction cleanup applied')
