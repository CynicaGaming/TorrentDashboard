#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.19"
NEW = "0.5.20"


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def write(path, text):
    (ROOT / path).write_text(text, encoding="utf-8")


# Version and browser asset revisions.
dashboard = read("dashboard.py")
dashboard, count = re.subn(r'^VERSION\s*=\s*["\'][^"\']+["\']', f'VERSION = "{NEW}"', dashboard, count=1, flags=re.M)
assert count == 1
write("dashboard.py", dashboard)

html = read("static/index.html")
assert 'id="updateSourceSave"' in html
html = html.replace('<div class="settings-inline-actions"><button class="primary" id="updateSourceSave" type="button">Save</button></div>\n', '')
assert 'id="updateSourceSave"' not in html
old_save = '<div class="settings-savebar" id="settingsSavebar"><button class="primary" type="submit">Save Settings</button></div>'
new_save = '<div class="settings-savebar" id="settingsSavebar"><button class="primary" type="submit">Save</button></div>'
assert old_save in html
html = html.replace(old_save, new_save)
html = html.replace(OLD, NEW)
write("static/index.html", html)

settings = read("static/settings.js")
old_pages = "const corePages = new Set(['general','access','clients','notifications']);"
new_pages = "const corePages = new Set(['general','access','clients','updates','notifications']);"
assert old_pages in settings
settings = settings.replace(old_pages, new_pages)
settings = settings.replace("    document.querySelector('#updateSourceSave')?.addEventListener('click', saveUpdateSource);\n", "")
needle = "  async function saveCore(e) {\n    if (e?.preventDefault) e.preventDefault();\n"
replacement = "  async function saveCore(e) {\n    if (e?.preventDefault) e.preventDefault();\n    const activePage = document.querySelector('.settings-page.active')?.dataset.settingsSection || 'general';\n    if (activePage === 'updates') return saveUpdateSource();\n"
assert needle in settings
settings = settings.replace(needle, replacement, 1)
assert "#updateSourceSave" not in settings
write("static/settings.js", settings)

sw = read("static/sw.js").replace(OLD, NEW).replace("torrent-dashboard-v0519", "torrent-dashboard-v0520")
write("static/sw.js", sw)

validator = read("release_tools/validate_ui_strings.py")
validator = validator.replace("    assert 'id=\"updateSourceSave\"' in html\n", "    assert 'id=\"updateSourceSave\"' not in html\n    assert 'Save Settings' not in html\n    assert '<div class=\"settings-savebar\" id=\"settingsSavebar\"><button class=\"primary\" type=\"submit\">Save</button></div>' in html\n    assert \"const corePages = new Set(['general','access','clients','updates','notifications']);\" in settings_js\n    assert \"if (activePage === 'updates') return saveUpdateSource();\" in settings_js\n    assert '#updateSourceSave' not in settings_js\n")
write("release_tools/validate_ui_strings.py", validator)

# Final targeted contract checks.
assert 'Save Settings' not in read("static/index.html")
assert 'id="updateSourceSave"' not in read("static/index.html")
assert 'VERSION = "0.5.20"' in read("dashboard.py")
assert '?v=0.5.20' in read("static/sw.js")
print("Staged Torrent Dashboard 0.5.20 standardized settings save action")
