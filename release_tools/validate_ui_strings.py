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
    sw = (ROOT / "static" / "sw.js").read_text(encoding="utf-8")

    validate_html_attributes(html)
    validate_javascript("static/app.js", app_js)
    validate_javascript("static/settings.js", settings_js)

    assert 'placeholder="Search torrents…"' in html
    assert 'id="savedView"' not in html
    assert 'id="saveView"' not in html
    assert 'Save Current View' not in html
    assert 'Saved Views' not in html
    assert 'function renderSavedViews' not in app_js
    assert 'savedViews' not in app_js
    assert 'id="kpiRange"' not in html
    assert 'id="chartRange"' not in html
    assert 'id="transferChart"' not in html
    assert 'id="ratioChart"' not in html
    assert 'id="analyticsGrid"' not in html
    assert 'function loadAnalytics' not in app_js
    assert 'function drawTransferChart' not in app_js
    assert 'function drawRatioChart' not in app_js
    assert 'id="historyTable"' not in html
    assert 'id="historyRange"' not in html
    assert 'Transfer History' not in html
    assert 'function loadHistory' not in app_js
    assert 'function renderHistory' not in app_js
    assert 'id="view-history"' not in html
    assert 'data-view="history"' not in html
    assert 'id="settingsNavToggle"' in html
    assert 'id="settingsSubnav"' in html
    assert 'id="settingsMobilePage"' in html
    assert 'data-settings-page="general"' in html
    assert 'data-settings-page="access"' in html
    assert 'data-settings-page="clients"' in html
    assert 'data-settings-page="updates"' in html
    assert 'data-settings-page="notifications"' in html
    assert 'data-settings-page="integrations"' in html
    assert 'data-settings-page="users"' in html
    assert '<option value="general">General</option>' in html
    assert '<option value="access">Access</option>' in html
    assert '<option value="clients">Clients</option>' in html
    assert '<option value="updates">Updates</option>' in html
    assert '<option value="notifications">Notifications</option>' in html
    assert '<option value="integrations">Integrations</option>' in html
    assert '<option value="users">Users</option>' in html
    assert 'id="settingsPageTitle"' not in html
    assert 'Settings are separated by category' not in html
    assert 'class="settings-nav"' not in html
    assert 'id="settingsNavGroup"' in html
    assert 'function setSettingsNavExpanded' in app_js
    assert "$$('.nav-root,.settings-subnav button,.mobile-nav button')" in app_js
    assert '@media(min-width:821px){.settings-nav{margin-top:0}}' in settings_css
    assert 'margin-top:52px' not in settings_css
    assert 'data-bulk-clear="1"' in html
    assert "state.selected.clear();render();return" in app_js
    assert '#settingsMobilePage' in settings_js
    assert 'position:fixed!important' in app_css
    assert '.standard-user .row-actions' not in settings_css
    assert '.standard-user #contextMenu' not in settings_css

    # Self-service account/profile contract. Standard Users must reach these
    # routes before the Administrator-only mutation barrier.
    assert 'id="profileBtn"' in html
    assert 'id="accountMenu"' in html and 'id="accountModal"' in html
    assert 'id="accountProfileForm"' in html and 'id="accountPasswordForm"' in html
    assert 'id="accountAvatarInput"' in html and 'data-avatar-default' in html
    assert 'function syncCurrentUserUi' in app_js
    assert 'function hideAccountMenu' in app_js
    assert 'async function openAccountModal' in app_js
    assert "await post('/api/account/password'" in app_js
    assert "await api('/api/account/avatar',{method:'POST'" in app_js
    assert '0.5.24 self-service account menu' in app_css
    assert 'MAX_AVATAR_BYTES = 4 * 1024 * 1024' in dashboard_py
    assert 'def save_current_user_profile' in dashboard_py
    assert 'def change_current_user_password' in dashboard_py
    assert 'def store_user_avatar' in dashboard_py
    assert 'def remove_user_except(self, user_id, keep_token)' in dashboard_py
    assert 'if path=="/api/account/avatar":' in dashboard_py
    post_section = dashboard_py.split('    def do_POST(self):', 1)[1]
    assert post_section.index('if path=="/api/account":') < post_section.index('if not session_is_admin(sess):')
    assert post_section.index('if path=="/api/account/password":') < post_section.index('if not session_is_admin(sess):')
    assert post_section.index('if path=="/api/account/avatar":') < post_section.index('if not session_is_admin(sess):')

    # Account identity now lives only in the top-right profile control.
    assert 'id="currentUserName"' not in html
    assert 'id="currentUserGroup"' not in html
    assert 'currentUserName' not in app_js and 'currentUserGroup' not in app_js
    assert '<div class="sidebar-foot"><small id="version">—</small></div>' in html

    # Local secret icons, secure account changes, and curated client settings.
    assert 'id="addBtn"' not in html and 'id="moreBtn"' not in html
    assert 'id="addLinkBtn"' in html and 'id="addFileBtn"' in html
    assert 'function secretToggleSvg' in app_js and 'material-symbol-icon' in app_js
    assert 'visibility_lock' in app_js and "visibility'" in app_js
    assert 'material-symbols-outlined' not in app_css
    assert 'fonts.googleapis.com' not in html and 'fonts.gstatic.com' not in dashboard_py
    assert 'id="loginPass"' in html and 'autocomplete="current-password"' in html
    assert 'id="accountAvatarBtn"' not in html and 'accountAvatarBtn' not in app_js
    assert 'id="accountPasswordBtn"' not in html and 'accountPasswordBtn' not in app_js
    assert 'id="accountCurrentPassword"' not in html and 'accountCurrentPassword' not in app_js
    assert 'id="accountGroup"' not in html and 'accountGroup' not in app_js
    profile_update_js = app_js.split('async function saveOwnProfile(e){', 1)[1].split('async function changeOwnPassword(e){', 1)[0]
    assert 'accountGroup' not in profile_update_js
    assert '"group": existing.get("group"),' in dashboard_py
    password_update_js = app_js.split('async function changeOwnPassword(e){', 1)[1].split('async function uploadOwnAvatar(){', 1)[0]
    assert 'requestPasswordConfirmation' in password_update_js and 'current_password:current' in password_update_js
    assert 'id="accountProfilePassword"' not in html and 'accountProfilePassword' not in app_js
    assert 'id="passwordConfirmModal"' in html and 'requestPasswordConfirmation' in app_js
    assert 'password_configured' in dashboard_py
    assert 'Default Torrent Dashboard Sound' not in html and '<option value="default">Default</option>' in html
    assert '<option value="custom">Custom</option>' in html and '<option value="custom">Custom Sound</option>' not in html
    assert '<div class="account-form-grid"><label class="account-full-field">Username<input autocomplete="username" id="accountUsername"' in html
    assert ' · You' not in settings_js and 'Current user' in settings_js
    assert 'id="clientSettingsModal"' in html and 'id="clientSettingsForm"' in html
    for field in ('clientGlobalDl','clientGlobalUl','clientAltDl','clientAltUl','clientListenPort','clientMaxConnections','clientProxyType','clientProxyHost','clientProxyPort','clientProxyPassword'):
        assert f'id="{field}"' in html
    assert 'data-client-settings-tab="speed"' in html and 'data-client-settings-tab="connection"' in html and 'data-client-settings-tab="proxy"' in html
    assert '/api/client-settings' in dashboard_py and '/api/client-settings' in settings_js
    assert 'def client_settings(self):' in dashboard_py and 'def update_client_settings(self, data):' in dashboard_py
    assert '/api/v2/app/setPreferences' in dashboard_py
    assert 'proxy_password' in dashboard_py and 'password_configured' in dashboard_py
    assert 'preferences = client.preferences()' in dashboard_py and 'disk_free = disk_free_for(preferences)' in dashboard_py
    assert '0.5.26 qBitTorrent-style torrent toolbar' in app_css
    assert '0.5.28 advanced per-client qBitTorrent settings' in settings_css

    # 0.5.38 sidebar identity remains in the stable runtime baseline.
    assert 'id="homeBrand"' in html and 'id="brandAddress"' in html
    assert 'qBitTorrent Control' not in html
    assert "state.me.lan_ip||'Local'" in app_js
    assert "$('#homeBrand').addEventListener('click',()=>setView('dashboard'))" in app_js

    # v0.5.41 recovery boundary: never mix a stale app shell with JavaScript
    # from another build, and keep browser/network failures observable.
    assert 'Frontend build mismatch' in dashboard_py
    assert 'requested != VERSION' in dashboard_py
    assert "event.request.mode==='navigate'" in sw
    assert "url.pathname==='/'" in sw
    assert '[Torrent Dashboard]' in settings_js
    assert '__tdFetchDiagnostics' in settings_js
    assert '__tdReportError' in app_js

    print("UI string audit passed")


if __name__ == "__main__":
    main()
