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
dashboard = replace_once(dashboard, 'VERSION = "0.5.31"', 'VERSION = "0.5.32"', "version")
write("dashboard.py", dashboard)

html = read("static/index.html")
html = replace_once(
    html,
    '<label>Role<input aria-readonly="true" id="accountGroup" readonly tabindex="-1"/></label>',
    '',
    "account role field",
)
html = replace_once(
    html,
    'Username and email changes require password confirmation. Your role can only be changed by an Administrator.',
    'Username and email changes require password confirmation.',
    "account profile help",
)
html = html.replace("?v=0.5.31", "?v=0.5.32")
write("static/index.html", html)

app_js = read("static/app.js")
app_js = replace_once(
    app_js,
    "  $('#accountGroup').value=d.user?.group_label||uiText(d.user?.group||'standardUser');\n",
    "",
    "account role population",
)
write("static/app.js", app_js)

sw = read("static/sw.js")
sw = replace_once(sw, "torrent-dashboard-v0531", "torrent-dashboard-v0532", "service worker cache")
sw = sw.replace("?v=0.5.31", "?v=0.5.32")
write("static/sw.js", sw)

validator = read("release_tools/validate_ui_strings.py")
validator = replace_once(
    validator,
    "    assert '<label>Role<input aria-readonly=\"true\" id=\"accountGroup\" readonly tabindex=\"-1\"/></label>' in html\n",
    "    assert 'id=\"accountGroup\"' not in html and 'accountGroup' not in app_js\n",
    "role visibility validator",
)
write("release_tools/validate_ui_strings.py", validator)

final_html = read("static/index.html")
final_js = read("static/app.js")
final_dashboard = read("dashboard.py")
assert 'id="accountGroup"' not in final_html
assert 'accountGroup' not in final_js
assert '"group": existing.get("group"),' in final_dashboard
assert 'Username and email changes require password confirmation.' in final_html
assert 'Your role can only be changed by an Administrator.' not in final_html

print("Applied 0.5.32 account role cleanup.")
