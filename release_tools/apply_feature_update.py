#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: str, old: str, new: str):
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"Expected text not found in {path}: {old[:120]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


def replace_all(path: str, old: str, new: str):
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"Expected text not found in {path}: {old!r}")
    target.write_text(text.replace(old, new), encoding="utf-8")


replace_once(
    "static/index.html",
    '<div class="sidebar-foot"><div class="sidebar-user"><strong id="currentUserName">—</strong><small id="currentUserGroup">—</small></div><small id="version">—</small></div>',
    '<div class="sidebar-foot"><small id="version">—</small></div>',
)
replace_once(
    "static/app.js",
    "  if($('#currentUserName'))$('#currentUserName').textContent=display;\n  if($('#currentUserGroup'))$('#currentUserGroup').textContent=group;\n",
    "",
)

replace_once("dashboard.py", 'VERSION = "0.5.24"', 'VERSION = "0.5.25"')
replace_all("static/index.html", "v=0.5.24", "v=0.5.25")
replace_once("static/sw.js", "torrent-dashboard-v0524", "torrent-dashboard-v0525")
replace_all("static/sw.js", "v=0.5.24", "v=0.5.25")

validator = ROOT / "release_tools" / "validate_ui_strings.py"
text = validator.read_text(encoding="utf-8")
needle = "    assert post_section.index('if path==\"/api/account/avatar\":') < post_section.index('if not session_is_admin(sess):')\n\n    print(\"UI string audit passed\")"
replacement = "    assert post_section.index('if path==\"/api/account/avatar\":') < post_section.index('if not session_is_admin(sess):')\n\n    # Account identity now lives only in the top-right profile control.\n    assert 'id=\"currentUserName\"' not in html\n    assert 'id=\"currentUserGroup\"' not in html\n    assert 'currentUserName' not in app_js and 'currentUserGroup' not in app_js\n    assert '<div class=\"sidebar-foot\"><small id=\"version\">—</small></div>' in html\n\n    print(\"UI string audit passed\")"
if needle not in text:
    raise RuntimeError("Validator insertion point was not found")
validator.write_text(text.replace(needle, replacement, 1), encoding="utf-8")

print("Applied 0.5.25 sidebar account cleanup")
