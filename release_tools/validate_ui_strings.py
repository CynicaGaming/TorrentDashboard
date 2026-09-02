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

    # Torrent interaction contract: row selection opens a qBitTorrent-style
    # information pane while operational commands remain in the context menu.
    assert 'id="torrentDetailPane"' in html
    assert 'id="drawer"' not in html
    assert all(f'data-detailtab="{tab}"' in html for tab in ('general','trackers','peers','webseeds','content'))
    assert 'HTTP Sources' in html and '>Content</button>' in html
    assert "Torrent details" not in app_js
    assert "openDetail(tr.dataset.server,tr.dataset.hash)" in app_js
    assert "torrent-detail-selected" in app_js and "torrent-detail-selected" in app_css
    assert "function closeDetailPane" in app_js and "function refreshDetailData" in app_js
    assert "now-detailRefreshAt<3000" in app_js
    assert "/api/v2/torrents/webseeds" in dashboard_py
    assert "renderWebSeeds" in app_js
    assert "Automatic torrent management" not in app_js
    assert "set_auto_management" not in app_js and "set_auto_management" not in dashboard_py
    assert "menu-separator" in app_css and "@media(max-width:700px)" in app_css
    assert "e.target.closest('button[data-a]')" in app_js
    # Add Torrent metadata is demand-driven and isolated from application startup.
    assert 'id="addMetadataStatus"' in html
    assert 'id="addSaveTorrent"' in html
    assert 'id="addFileRows"' in html
    assert 'id="addStart"' in html and 'id="addStopCondition"' in html
    assert 'Save as .torrent file' in html
    assert 'Torrent management mode' in html
    assert 'def fetch_torrent_metadata(self, source):' in dashboard_py
    assert 'def parse_torrent_metadata(self, filename, content):' in dashboard_py
    assert 'def save_torrent_metadata(self, source):' in dashboard_py
    assert '/api/v2/torrents/fetchMetadata' in dashboard_py
    assert '/api/v2/torrents/parseMetadata' in dashboard_py
    assert '/api/v2/torrents/saveMetadata' in dashboard_py
    assert 'self._request("GET", path)' in dashboard_py
    assert 'self._request("POST", "/api/v2/torrents/saveMetadata"' not in dashboard_py
    assert "addMetadataState.mode==='file'?addMetadataState.source:addSingleSource()" in app_js
    assert '/api/torrent-metadata/fetch' in dashboard_py
    assert '/api/torrent-metadata/parse' in dashboard_py
    assert '/api/torrent-metadata/save' in dashboard_py
    assert 'filePriorities' in dashboard_py
    assert 'addMetadataGeneration' in app_js
    assert 'clearTimeout(addMetadataTimer)' in app_js
    assert 'setTimeout(()=>fetchAddMetadata(generation),1000)' in app_js
    assert 'setInterval' not in app_js[app_js.find('let addMetadataTimer'):app_js.find('async function rawJson')]
    assert "generation!==addMetadataGeneration||!addModalOpen()" in app_js
    assert "function closeAddTorrent(){clearAddMetadataTimer();addMetadataGeneration++" in app_js
    assert "fetchAddMetadata(" not in app_js[app_js.find('async function bootstrap'):app_js.find("document.addEventListener('DOMContentLoaded'") if "document.addEventListener('DOMContentLoaded'" in app_js else len(app_js)]
    assert '.add-torrent-card{' in app_css

    # Updates owns the public GitHub repository directly. GitHub must not be a
    # modular integration and update installation remains a reactive button.
    assert 'DEFAULT_UPDATE_REPOSITORY = "CynicaGaming/TorrentDashboard"' in dashboard_py
    assert 'def update_repository(cfg):' in dashboard_py
    assert 'def save_update_source(cfg, repository):' in dashboard_py
    assert 'github_update_integration' not in dashboard_py
    assert 'Only one GitHub integration can be configured' not in dashboard_py
    assert '/api/update-source-test' not in dashboard_py
    assert 'test_github_update_access' not in dashboard_py
    assert 'def validate_update_repository(repository: str):' in dashboard_py
    assert 'repo = validate_update_repository(update_repository(cfg))' in dashboard_py
    assert '/api/update-source' in dashboard_py
    assert 'id="uRepository"' in html
    assert 'id="updateSourceTest"' not in html
    assert 'id="updateSourceResult"' not in html
    assert 'updateSourceTest' not in settings_js
    assert 'updateSourceResult' not in settings_js
    assert 'id="updateSourceSave"' not in html
    assert 'Save Settings' not in html
    assert '<div class="settings-savebar" id="settingsSavebar"><button class="primary" type="submit">Save</button></div>' in html
    # Settings navigation labels and card titles must use the same canonical names.
    for title in ('General','Access','Clients','Updates','Notifications','Integrations','Users'):
        assert f'<div class="panel-title">{title}</div>' in html
    assert '<div class="panel-title">General Dashboard Settings</div>' not in html
    assert '<div class="panel-title">Dashboard Access</div>' not in html
    assert '<div class="panel-title">qBitTorrent Servers</div>' not in html
    assert '<div class="panel-title">User Management</div>' not in html
    assert '(Optional)' not in settings_js
    assert settings_js.count('class="required-mark"') >= 4
    assert '.required-mark{color:#ff5d6c' in settings_css
    assert 'class="field-label">Username <span class="required-mark"' in settings_js
    assert 'class="user-group-select"' in settings_js
    assert '.user-group-select{display:block;width:100%' in settings_css
    assert 'id="testNotification"' in html
    assert 'settingsNotifyPermission' not in html and 'settingsNotifyPermission' not in settings_js
    assert 'id="notifyPermission"' not in html and '#notifyPermission' not in app_js
    assert 'async function testNotification()' in settings_js
    assert 'Notification.requestPermission()' in settings_js
    assert 'async function showBrowserNotification' in app_js
    assert 'CREATE_NO_WINDOW' in dashboard_py and '**_windows_background_process_kwargs()' in dashboard_py
    assert "const corePages = new Set(['general','access','clients','updates','notifications']);" in settings_js
    assert "if (activePage === 'updates') return saveUpdateSource();" in settings_js
    assert '#updateSourceSave' not in settings_js
    assert 'data-settings-page="updates" type="button">Updates</button>' in html
    assert 'data-settings-page="access" type="button">Access</button>' in html
    assert 'data-settings-page="clients" type="button">Clients</button>' in html
    assert 'data-settings-page="users" type="button">Users</button>' in html
    assert '<option value="access">Access</option>' in html
    assert '<option value="clients">Clients</option>' in html
    assert '<option value="users">Users</option>' in html
    assert 'data-settings-page="access" type="button">Dashboard Access</button>' not in html
    assert 'data-settings-page="clients" type="button">Download Clients</button>' not in html
    assert 'data-settings-page="users" type="button">User Management</button>' not in html
    assert '<option value="updates">Updates</option>' in html
    assert 'Application Updates' not in html
    assert "x.type === 'github'" not in settings_js
    assert "title:'Install update'" not in app_js
    assert "confirmLabel:'Install and restart'" not in app_js
    assert 'UPDATE_STATE_PATH.unlink(missing_ok=True)' in dashboard_py
    assert 'shutil.rmtree(UPDATE_DIR, ignore_errors=True)' in dashboard_py

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
    assert 'id="settingsPageTitle"' not in html
    assert 'Settings are separated by category' not in html
    assert 'Save User' not in settings_js
    assert '<div class="field-help">Standard Users have read-only dashboard access.' not in settings_js
    assert ' · ${esc(group)}' not in settings_js
    assert 'function integrationSubtitle' in settings_js
    assert '0.5.14 readability pass' in app_css
    assert '0.5.14 settings de-duplication' in settings_css
    assert 'id="wRefresh"' not in html and 'id="sRefresh"' not in html
    assert 'id="actionDialogModal"' in html and 'id="actionDialogForm"' in html
    assert 'LIVE_REFRESH_MS=1000' in app_js
    assert 'refreshMs' not in app_js and 'refresh_seconds' not in app_js and 'refresh_seconds' not in settings_js
    assert not re.search(r'(?<!\.)\bprompt\s*\(', app_js)
    assert not re.search(r'\bconfirm\s*\(', app_js)
    assert 'STATUS_REFRESH_SECONDS = 1.0' in dashboard_py
    assert 'stop_event.wait(STATUS_REFRESH_SECONDS)' in dashboard_py
    assert '0.5.16 unified application dialog' in app_css
    assert 'data-view="history"' not in html
    assert 'Transfer History' not in html
    assert 'data-view="notifications"' in html
    assert 'id="view-notifications"' in html
    assert 'id="notificationList"' in html
    assert 'async function loadNotifications' in app_js
    assert 'async function loadHistory' not in app_js
    assert 'id="removeModal"' in html
    assert 'id="removeFiles"' in html
    assert 'Also delete the downloaded files' in html
    assert 'async function removeTorrentTargets' in app_js
    assert "confirm('Also delete downloaded files?" not in app_js
    assert "confirm('Delete downloaded files too?')" not in app_js
    assert 'nav-caret' not in html
    assert 'setSettingsNavExpanded(!expanded)' not in app_js
    assert "$$('.nav-root,.settings-subnav button,.mobile-nav button')" in app_js
    assert '0.5.15 removal dialog and notification center' in app_css
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

    # 0.5.28 local secret icons, secure account changes, and curated client settings.
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

    print("UI string audit passed")


if __name__ == "__main__":
    main()
