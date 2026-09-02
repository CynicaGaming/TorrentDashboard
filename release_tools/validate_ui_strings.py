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
    config_store_py = (ROOT / "torrent_dashboard" / "config_store.py").read_text(encoding="utf-8")
    users_py = (ROOT / "torrent_dashboard" / "users.py").read_text(encoding="utf-8")

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
    # Add Torrent shell and native qBitTorrent add options remain present.
    assert 'class="modal-card add-torrent-card"' in html
    assert 'class="add-torrent-body"' in html
    assert 'class="add-torrent-options"' in html
    assert 'class="add-torrent-preview"' in html
    assert 'id="addUrls"' in html and 'id="torrentFile"' in html and 'id="addPath"' in html
    assert 'id="addCategory"' in html and 'id="addTags"' in html
    assert 'id="addStartTorrent"' in html and 'id="addSequential"' in html and 'id="addFirstLast"' in html
    assert 'id="addTorrentBtn"' in html
    assert "function openAddTorrent(){" in app_js and "torrentFile').click()" not in app_js
    for control in ('addAutoTmm','addUseDownloadPath','addDownloadPath','addRename','addStartTorrent','addStopCondition','addToTop','addSeedMode','addContentLayout','addDlLimit','addUlLimit'):
        assert f'id="{control}"' in html
    assert 'function addTorrentOptions()' in app_js and 'function appendAddTorrentFields' in app_js
    assert "fd.append('autoTMM'" in app_js and "fd.append('contentLayout'" in app_js
    assert '"autoTMM"' in dashboard_py and '"addToTopOfQueue"' in dashboard_py and '"seedMode"' in dashboard_py
    assert '"stopCondition"' in dashboard_py and '"contentLayout"' in dashboard_py
    assert '0.5.48 Add Torrent visual shell' in app_css
    assert '0.5.49 Add Torrent advanced options' in app_css

    # 0.5.50 metadata backend remains available.
    for method in ('fetch_torrent_metadata','parse_torrent_metadata','save_torrent_metadata'):
        assert f'def {method}' in dashboard_py
    for route in ('/api/torrent-metadata/fetch','/api/torrent-metadata/parse','/api/torrent-metadata/save'):
        assert route in dashboard_py
    assert '/api/v2/torrents/fetchMetadata' in dashboard_py
    assert '/api/v2/torrents/parseMetadata' in dashboard_py
    assert '/api/v2/torrents/saveMetadata' in dashboard_py
    assert 'qbit_status' in dashboard_py and 'complete' in dashboard_py
    assert 'Torrent metadata preview requires qBittorrent Web API 2.11.9 or newer' in dashboard_py

    # 0.5.51 magnet/URL metadata preview remains bounded and read-only.
    for control in ('addContentBody','addContentSummary','addMetadataStatus','addMetadataStatusTitle','addMetadataStatusText','addMetadataProgress','addInfoSize','addInfoDate','addInfoHashV1','addInfoHashV2','addInfoCreatedBy','addInfoComment'):
        assert f'id="{control}"' in html
    assert '/api/torrent-metadata/fetch' in app_js
    assert 'const ADD_METADATA_POLL_MS=1000;' in app_js
    assert 'const ADD_METADATA_TIMEOUT_MS=120000;' in app_js
    assert 'const addMetadataState=' in app_js
    assert 'function scheduleAddMetadataPreview' in app_js
    assert 'function fetchAddMetadataPreview' in app_js
    assert 'function cancelAddMetadata' in app_js
    assert 'function closeAddTorrent()' in app_js
    assert 'Metadata retrieval complete' in app_js
    assert 'setTimeout(()=>fetchAddMetadataPreview(source,generation),ADD_METADATA_POLL_MS)' in app_js
    assert 'setInterval(fetchAddMetadataPreview' not in app_js
    assert '0.5.51 Add Torrent magnet metadata preview' in app_css

    # 0.5.52 adds read-only .torrent parsing without changing either stable add path.
    assert '/api/torrent-metadata/parse' in app_js
    assert '/api/torrent-metadata/save' in app_js
    assert 'function parseAddTorrentFileMetadata' in app_js
    assert 'function parsedTorrentMetadata' in app_js
    assert "form.append('torrents',file,file.name)" in app_js
    assert "api('/api/torrent-metadata/parse',{method:'POST',body:form})" in app_js
    assert "Array.isArray(raw)" in app_js
    assert "action:'add_magnet'" in app_js and "api('/api/upload'" in app_js
    assert "urls:$('#addUrls').value.trim()" in app_js
    assert 'Preview only · Add torrent still submits the original source.' in app_js
    assert 'Preview only · Add torrent still uploads the original .torrent file.' in app_js
    assert '.torrent metadata preview will be enabled in the next controlled phase.' not in app_js
    # 0.5.53 keeps completed/stopped torrents classified as complete while
    # exposing qBitTorrent download-location defaults in Client Settings and Add Torrent.
    assert "function isStopped(t)" in app_js
    assert "function isPaused(t){return !isComplete(t)&&isStopped(t)}" in app_js
    assert "if(isComplete(t)&&isStopped(t))return['complete','seed']" in app_js
    assert "item(isStopped(t)?'start':'stop'" in app_js
    assert 'float(t.get("progress",0) or 0)<.999999 and ("paused"' in dashboard_py
    for control in ('clientSavePath','clientTempPathEnabled','clientTempPath'):
        assert f'id="{control}"' in html
    assert 'data-client-settings-tab="downloads"' in html
    assert 'data-client-settings-pane="downloads"' in html
    assert '"downloads": {' in dashboard_py and '"save_path": str(prefs.get("save_path")' in dashboard_py
    assert '"temp_path_enabled": bool(prefs.get("temp_path_enabled"' in dashboard_py
    assert '"temp_path": str(prefs.get("temp_path")' in dashboard_py
    assert "downloads:{save_path:document.querySelector('#clientSavePath')" in settings_js
    assert "function loadAddTorrentClientDefaults" in app_js
    assert "downloads.save_path||''" in app_js and "downloads.temp_path||''" in app_js
    assert "downloads.temp_path_enabled" in app_js
    assert 'Use another path for incomplete torrents' in html
    assert '.client-path-grid{grid-template-columns:1fr}' in settings_css

    # 0.5.54 enables export only after metadata is complete. It must use
    # qBitTorrent's native saveMetadata cache without changing torrent addition.
    assert 'id="addSaveTorrent"' in html
    assert 'Save as .torrent' in html
    assert 'async function saveAddTorrentMetadata()' in app_js
    assert "fetch(url,{method:'GET',cache:'no-store'})" in app_js
    assert "renderAddMetadataComplete(result.metadata||{},source)" in app_js
    assert "renderAddMetadataComplete(metadata,metadata?.hash||'')" in app_js
    assert "link.download=addMetadataState.exportName||'torrent.torrent'" in app_js
    assert "self._request(\"GET\", route, expect_json=False)" in dashboard_py
    assert "fd.append('filePriorities'" not in app_js
    assert 'add_cached_metadata' not in app_js

    # 0.5.47 frontend generation contract. Navigation HTML is never cached,
    # stale versioned scripts trigger recovery, and optional Add Torrent bindings
    # cannot abort critical dashboard startup.
    sw = (ROOT / "static" / "sw.js").read_text(encoding="utf-8")
    version = re.search(r'^VERSION\s*=\s*["\']([^"\']+)', dashboard_py, re.M).group(1)
    assert f'<meta content="{version}" name="torrent-dashboard-build"/>' in html
    assert f"const FRONTEND_BUILD='{version}';" in app_js
    assert "HTML_BUILD!==FRONTEND_BUILD" in app_js and "recoverFrontendBuild" in app_js
    assert "showStartupFailure(e,'bootstrap')" in app_js
    assert "function bindAddTorrentUI()" in app_js
    assert "missing elements" in app_js
    assert "function bindUI(){if(bound)return;" in app_js
    assert "function bindUI(){if(bound)return;bound=true;" not in app_js
    assert "bound=true;\n}" in app_js
    assert 'id="startupFailure"' in html and '.startup-failure{' in app_css
    assert "frontend_recovery_script" in dashboard_py
    assert 'requested and requested != VERSION' in dashboard_py
    assert "event.request.mode==='navigate'" in sw
    assets = sw.split('const ASSETS=',1)[1].split(';',1)[0]
    assert "'/'" not in assets and "'/index.html'" not in assets

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
    assert 'MAX_AVATAR_BYTES = 4 * 1024 * 1024' in users_py
    assert 'def save_current_user_profile' in users_py
    assert 'def change_current_user_password' in users_py
    assert 'def store_user_avatar' in users_py
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
    assert 'id="addTorrentBtn"' in html and 'id="addLinkBtn"' not in html and 'id="addFileBtn"' not in html
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
    assert '"group": existing.get("group"),' in users_py
    password_update_js = app_js.split('async function changeOwnPassword(e){', 1)[1].split('async function uploadOwnAvatar(){', 1)[0]
    assert 'requestPasswordConfirmation' in password_update_js and 'current_password:current' in password_update_js
    assert 'id="accountProfilePassword"' not in html and 'accountProfilePassword' not in app_js
    assert 'id="passwordConfirmModal"' in html and 'requestPasswordConfirmation' in app_js
    assert 'password_configured' in users_py
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

    # 0.5.56 serializes all configuration read/modify/write mutations.
    assert 'from torrent_dashboard.config_store import ConfigStore' in dashboard_py
    assert 'CONFIG_STORE = ConfigStore(_load_config_unlocked, _save_config_unlocked)' in dashboard_py
    assert 'def mutate_config(transform):' in dashboard_py
    assert 'class ConfigStore:' in config_store_py and 'with self._lock:' in config_store_py
    mutation_section = dashboard_py.split('class Handler(BaseHTTPRequestHandler):', 1)[1]
    assert 'save_config(' not in mutation_section
    assert mutation_section.count('mutate_config(') >= 12

    print("UI string audit passed")


if __name__ == "__main__":
    main()
