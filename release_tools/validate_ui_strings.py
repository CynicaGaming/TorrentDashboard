#!/usr/bin/env python3
"""Fail a release build if internal-style UI strings leak into user-facing surfaces."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAMEL = re.compile(r"[a-z0-9][A-Z]")
PROPER_NAMES = ("Torrent Dashboard", "qBitTorrent", "GitHub", "Home Assistant")


def has_camel_leak(value: str) -> bool:
    cleaned = str(value or "")
    for name in PROPER_NAMES:
        cleaned = cleaned.replace(name, "")
    return bool(CAMEL.search(cleaned))


def validate_html_attributes(html: str):
    offenders = []
    for attr, value in re.findall(r'\b(placeholder|title|aria-label)="([^"]*)"', html):
        if has_camel_leak(value):
            offenders.append(f'{attr}="{value}"')
    if offenders:
        raise SystemExit("camelCase found in user-facing HTML attributes: " + ", ".join(offenders))


def validate_javascript(name: str, text: str):
    if "applyTitleCaseUi" in text:
        raise SystemExit(f"{name}: obsolete applyTitleCaseUi reference remains")

    offenders = []
    for value in re.findall(r"textContent\s*=\s*['\"]([^'\"]+)['\"]", text):
        if has_camel_leak(value):
            offenders.append(f"textContent={value!r}")

    for value in re.findall(r'(?:placeholder|title|aria-label)=\\?["\']([^"\']*)', text):
        if has_camel_leak(value):
            offenders.append(f"attribute={value!r}")

    if offenders:
        raise SystemExit(f"{name}: camelCase UI strings remain: " + ", ".join(offenders))


def main():
    html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    app_js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
    settings_js = (ROOT / "static" / "settings.js").read_text(encoding="utf-8")
    app_css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
    settings_css = (ROOT / "static" / "settings.css").read_text(encoding="utf-8")
    dashboard_py = (ROOT / "dashboard.py").read_text(encoding="utf-8")

    validate_html_attributes(html)
    validate_javascript("static/app.js", app_js)
    validate_javascript("static/settings.js", settings_js)

    assert 'placeholder="Search torrents…"' in html
    assert 'id="savedView"' not in html
    assert 'id="saveView"' not in html
    assert 'tdSavedViews' not in app_js
    assert 'function syncFilterSelect' in app_js
    assert 'document.activeElement===select' in app_js
    assert 'optionsSignature' in app_js
    assert "function normalizeUiAttributes" in app_js
    assert "attributeFilter:['placeholder','title','aria-label']" in app_js
    assert "applySentenceCaseUi(card)" in settings_js

    # Torrent interaction contract: explicit context menu rather than row-click
    # navigation, with qBitTorrent-inspired grouping and no automatic management.
    assert "Torrent details" in app_js
    assert "Torrent options…" not in app_js
    assert "Automatic torrent management" not in app_js
    assert "set_auto_management" not in app_js
    assert "set_auto_management" not in dashboard_py
    assert "openDetail(tr.dataset.server,tr.dataset.hash)" not in app_js
    assert "menu-separator" in app_css and "@media(max-width:700px)" in app_css
    assert "e.target.closest('button[data-a]')" in app_js
    assert 'github' in dashboard_py
    assert 'id="sUpdateRepo"' not in html
    assert 'id="sUpdateToken"' not in html
    assert 'id="sUpdateAutoCheck"' not in html
    assert 'id="sUpdateHours"' not in html
    assert 'id="testUpdateAccess"' not in html
    assert 'id="wUpdateRepo"' not in html
    assert 'id="wUpdateToken"' not in html
    assert 'id="wUpdatesEnabled"' not in html
    assert 'id="wUpdateAutoCheck"' not in html
    assert 'Test GitHub Connection' not in html
    assert 'maybeAutoCheckUpdates' not in app_js
    assert 'setup_test_github' not in dashboard_py
    assert '/api/update-test' not in dashboard_py
    assert 'github_update_integration' in dashboard_py
    assert 'Only one GitHub integration can be configured' in dashboard_py
    assert 'id="settingsNavGroup"' in html
    assert 'id="settingsSubnav"' in html
    assert 'id="settingsMobilePage"' in html
    assert 'class="settings-nav"' not in html
    assert 'data-bulk-clear="1"' in html
    assert "function setSettingsNavExpanded" in app_js
    assert "state.selected.clear();render();return" in app_js
    assert "#settingsMobilePage" in settings_js
    assert "position:fixed!important" in app_css
    assert '.standard-user .row-actions' not in settings_css
    assert '.standard-user #contextMenu' not in settings_css

    print("UI string audit passed")


if __name__ == "__main__":
    main()
