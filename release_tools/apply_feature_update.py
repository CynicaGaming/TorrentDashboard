#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


dashboard = read("dashboard.py")
dashboard = replace_once(dashboard, 'VERSION = "0.5.28"', 'VERSION = "0.5.29"', "version")
write("dashboard.py", dashboard)

html = read("static/index.html")
html = replace_once(
    html,
    '<button id="accountSettingsBtn" type="button">Account settings</button><button id="accountPasswordBtn" type="button">Change password</button>',
    '<button id="accountSettingsBtn" type="button">Account settings</button>',
    "profile menu password shortcut",
)
html = html.replace("?v=0.5.28", "?v=0.5.29")
write("static/index.html", html)

app_js = read("static/app.js")
app_js = replace_once(
    app_js,
    "$('#accountPasswordBtn').addEventListener('click',()=>{hideAccountMenu();openAccountModal('password')});",
    "",
    "profile menu password binding",
)
write("static/app.js", app_js)

sw = read("static/sw.js")
sw = sw.replace("torrent-dashboard-v0527", "torrent-dashboard-v0529")
sw = sw.replace("?v=0.5.28", "?v=0.5.29")
write("static/sw.js", sw)

validator = read("release_tools/validate_ui_strings.py")
validator = replace_once(
    validator,
    "    assert 'id=\"accountAvatarBtn\"' not in html and 'accountAvatarBtn' not in app_js\n",
    "    assert 'id=\"accountAvatarBtn\"' not in html and 'accountAvatarBtn' not in app_js\n    assert 'id=\"accountPasswordBtn\"' not in html and 'accountPasswordBtn' not in app_js\n",
    "profile menu validator",
)
write("release_tools/validate_ui_strings.py", validator)

final_html = read("static/index.html")
final_js = read("static/app.js")
assert 'id="accountPasswordForm"' in final_html
assert "await post('/api/account/password'" in final_js
assert 'id="accountPasswordBtn"' not in final_html
assert 'accountPasswordBtn' not in final_js

print("Applied 0.5.29 profile-menu password shortcut cleanup.")
