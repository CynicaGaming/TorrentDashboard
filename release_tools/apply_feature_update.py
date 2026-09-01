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
dashboard = replace_once(dashboard, 'VERSION = "0.5.29"', 'VERSION = "0.5.30"', "version")
write("dashboard.py", dashboard)

html = read("static/index.html")
html = replace_once(
    html,
    '<option value="custom">Custom Sound</option>',
    '<option value="custom">Custom</option>',
    "custom sound label",
)
html = replace_once(
    html,
    '<div class="account-form-grid"><label>Username<input autocomplete="username" id="accountUsername" maxlength="128" required/></label><label>First name<input id="accountFirstName" maxlength="128"/></label><label>Last name<input id="accountLastName" maxlength="128"/></label>',
    '<div class="account-form-grid"><label class="account-full-field">Username<input autocomplete="username" id="accountUsername" maxlength="128" required/></label><label>First name<input id="accountFirstName" maxlength="128"/></label><label>Last name<input id="accountLastName" maxlength="128"/></label>',
    "profile username full row",
)
html = html.replace("?v=0.5.29", "?v=0.5.30")
write("static/index.html", html)

sw = read("static/sw.js")
sw = sw.replace("torrent-dashboard-v0529", "torrent-dashboard-v0530")
sw = sw.replace("?v=0.5.29", "?v=0.5.30")
write("static/sw.js", sw)

validator = read("release_tools/validate_ui_strings.py")
validator = replace_once(
    validator,
    "    assert 'Default Torrent Dashboard Sound' not in html and '<option value=\"default\">Default</option>' in html\n",
    "    assert 'Default Torrent Dashboard Sound' not in html and '<option value=\"default\">Default</option>' in html\n    assert '<option value=\"custom\">Custom</option>' in html and '<option value=\"custom\">Custom Sound</option>' not in html\n    assert '<div class=\"account-form-grid\"><label class=\"account-full-field\">Username<input autocomplete=\"username\" id=\"accountUsername\"' in html\n",
    "0.5.30 profile and sound contract",
)
write("release_tools/validate_ui_strings.py", validator)

final_html = read("static/index.html")
assert 'id="accountPasswordBtn"' not in final_html
assert '<option value="custom">Custom</option>' in final_html
assert '<label class="account-full-field">Username<input autocomplete="username" id="accountUsername"' in final_html
assert '<label>First name<input id="accountFirstName"' in final_html
assert '<label>Last name<input id="accountLastName"' in final_html

print("Applied 0.5.30 profile layout and notification label polish.")
