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



def validate_design_language(app_js: str, settings_js: str):
    if settings_js.count("toast('Settings saved');") != 2:
        raise SystemExit("Core Settings pages must share the exact 'Settings saved' confirmation")

    forbidden_settings = (
        "updateSourceSaved",
        "settingsSaved",
        "clientSettingsSaved",
        "Save The Client Before Opening Client Settings",
        "Enter A GitHub Repository",
        "Choose An Integration Type",
        "Enter A Username",
        "Passwords Do Not Match",
        "No Integrations Added",
        "No Users Found",
        "Testing Connection…",
        "Not Tested Yet",
    )
    leaked = [value for value in forbidden_settings if value in settings_js]
    if leaked:
        raise SystemExit("Legacy Settings language remains: " + ", ".join(leaked))

    redundant_modal_toasts = (
        "toast('profileSaved')",
        "toast('passwordChanged')",
        "toast('profilePictureUpdated')",
        "toast('profilePictureRemoved')",
    )
    leaked = [value for value in redundant_modal_toasts if value in app_js]
    if leaked:
        raise SystemExit("Duplicate modal success toasts remain: " + ", ".join(leaked))

    required = (
        "toast('Address copied')",
        "toast('Integration saved')",
        "toast('Integration deleted')",
        "toast('User saved')",
        "toast('User deleted')",
        "toast('Administrator access is required','error')",
        "toast('Select a specific client first','error')",
    )
    missing = [value for value in required if value not in app_js and value not in settings_js]
    if missing:
        raise SystemExit("Required canonical interface language is missing: " + ", ".join(missing))

def main():
    html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    app_js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
    settings_js = (ROOT / "static" / "settings.js").read_text(encoding="utf-8")
    app_css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
    settings_css = (ROOT / "static" / "settings.css").read_text(encoding="utf-8")
    dashboard_py = (ROOT / "dashboard.py").read_text(encoding="utf-8")
    config_py = (ROOT / "torrent_dashboard" / "config.py").read_text(encoding="utf-8")
    config_store_py = (ROOT / "torrent_dashboard" / "config_store.py").read_text(encoding="utf-8")
    integrations_py = (ROOT / "torrent_dashboard" / "integrations.py").read_text(encoding="utf-8")
    users_py = (ROOT / "torrent_dashboard" / "users.py").read_text(encoding="utf-8")

    validate_html_attributes(html)
    validate_javascript("static/app.js", app_js)
    validate_javascript("static/settings.js", settings_js)
    validate_design_language(app_js, settings_js)

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
    assert 'HTTP sources' in html and '>Content</button>' in html
    assert "Torrent details" not in app_js
    assert "openDetail(server,hash)" in app_js
    assert "torrent-detail-selected" in app_js and "torrent-detail-selected" in app_css
    assert "function toggleDetailPane" in app_js and "function resetDetailPane" in app_js and "function refreshDetailData" in app_js
    assert "now-detailRefreshAt<3000" in app_js
    assert "detailExpanded:false" in app_js
    assert "workspace?.classList.toggle('detail-expanded',expanded)" in app_js
    assert 'class="torrent-workspace"' in html and 'class="torrent-panel torrent-list-panel"' in html
    assert 'class="torrent-detail-pane collapsed"' in html and 'id="detailHandle"' in html
    assert 'aria-expanded="false"' in html and 'aria-controls="detailPanelContent"' in html
    assert 'id="detailClose"' not in html and "closeDetailPane" not in app_js
    assert "detailCollapsed" not in app_js and "tdDetailCollapsed" not in app_js
    assert "state.detailExpanded=!state.detailExpanded" in app_js
    assert "state.detailExpanded=true" in app_js
    assert "(!state.detailExpanded&&!force)" in app_js
    assert ".torrent-workspace{display:flex;flex-direction:column;gap:12px;overflow:visible;height:var(--torrent-workspace-height,min(720px,calc(100dvh - 220px)))}" in app_css
    assert ".topbar.dashboard-mode .topbar-heading{display:none}" not in app_css
    assert ".torrent-list-panel{display:flex;flex:1 1 auto;min-height:0;overflow:hidden}" in app_css
    assert ".torrent-detail-pane:not(.collapsed){min-height:240px;flex:0 1 clamp(260px,46%,420px)}" in app_css
    assert ".torrent-detail-pane.collapsed{min-height:48px!important;max-height:48px!important;flex-basis:48px!important}" in app_css
    assert ".torrent-detail-pane:not(.has-selection) .torrent-detail-tabs{display:none}" in app_css
    assert ".torrent-detail-handle{appearance:none;width:100%;min-height:48px" in app_css
    assert ".detail-pane-close" not in app_css and ".torrent-detail-header" not in app_css
    assert "function syncTorrentWorkspaceLayout()" in app_js
    assert "window.innerHeight-top-16" in app_js
    assert "--torrent-workspace-height" in app_js
    assert "height:calc(100dvh - 320px);min-height:480px" not in app_css
    assert 'id="mTotal"' in html and 'id="mTorrentSummary"' in html
    assert 'id="mUpdated"' not in html and 'id="mHealth"' not in html
    assert 'id="emptyTitle"' in html and 'id="emptyText"' in html
    assert "function emptyStateCopy()" in app_js
    assert "['No active torrents','Nothing is downloading right now.']" in app_js
    assert "['No torrents match these filters','Adjust your search or filters.']" in app_js
    assert ".torrent-list-region>.empty{position:absolute;inset:44px 0 0;display:grid;place-content:center" in app_css
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
    assert "function openAddTorrent(){" in app_js
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
    assert 'setTimeout(()=>fetchAddMetadataPreview(source,generation),ADD_METADATA_POLL_MS)' in app_js
    assert 'setInterval(fetchAddMetadataPreview' not in app_js
    assert '0.5.51 Add Torrent magnet metadata preview' in app_css

    # 0.5.52 introduced .torrent metadata parsing; v0.5.78 now uses parsed metadata for selectable cached adds.
    assert '/api/torrent-metadata/parse' in app_js
    assert '/api/torrent-metadata/save' in app_js
    assert 'function parseAddTorrentFileMetadata' in app_js
    assert 'function parsedTorrentMetadata' in app_js
    assert "form.append('torrents',file,file.name)" in app_js
    assert "api('/api/torrent-metadata/parse',{method:'POST',body:form})" in app_js
    assert "Array.isArray(raw)" in app_js
    assert "action:'add_torrent'" in app_js and "api('/api/upload'" in app_js
    assert 'function addMetadataSources()' in app_js and "sources.length!==1" in app_js
    assert 'Choose the files and folders to download' in app_js
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

    # 0.5.54 introduced metadata export; v0.5.78 adds canonical-hash and existing-torrent fallback.
    assert 'id="addSaveTorrent"' in html
    assert 'Save .torrent file' in html
    assert 'async function saveAddTorrentMetadata()' in app_js
    assert "params.set('hash',hash)" in app_js
    assert 'triggerTorrentFileDownload(localFile' in app_js
    assert '"/api/v2/torrents/export?"' in dashboard_py
    assert 'form["filePriorities"] = ",".join(clean_priorities)' in dashboard_py

    # 0.5.78 separates Add Torrent sources, adds folder/file selection, and
    # makes .torrent export resilient across metadata-cache and existing-transfer cases.
    for control in ("addSourceMagnetTab","addSourceFileTab","addTorrentDrop","addTorrentFileName","addSelectAllFiles"):
        assert f'id="{control}"' in html
    assert 'Drop a .torrent file here' in html and 'or click to browse' in html
    assert 'data-add-source="magnet"' in html and 'data-add-source="file"' in html
    assert "drop.addEventListener('drop'" in app_js and "$('#torrentFile').click()" in app_js
    assert 'function buildAddFileTree(files)' in app_js
    assert 'data-add-folder-files' in app_js and 'data-add-file-check' in app_js
    assert 'input.indeterminate=selected>0&&selected<files.length' in app_js
    assert 'function addFilePriorities()' in app_js
    assert "payload.file_priorities=priorities" in app_js
    assert "action:'add_torrent'" in app_js
    assert 'if action in ("add_magnet", "add_torrent"):' in dashboard_py
    assert '"filePriorities"' in dashboard_py
    assert 'def save_torrent_metadata(self, source, torrent_id=""):' in dashboard_py
    assert '"/api/v2/torrents/export?"' in dashboard_py
    assert 'qs.get("hash",[""])[0]' in dashboard_py
    assert '0.5.78 Add Torrent source separation and content selection' in app_css
    assert '## Add Torrent source and content workflow' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')
    assert '### Add Torrent source modes and file selection' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')


    # 0.5.79 fixes a startup-blocking EventTarget arity error in Add Torrent drag/drop binding.
    assert "for(const eventName of ['dragenter','dragover'])drop.addEventListener(eventName,event=>" in app_js
    assert "for(const eventName of ['dragleave','drop'])drop.addEventListener(eventName,event=>" in app_js
    assert "drop.addEventListener(event=>" not in app_js

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
    assert 'DEFAULT_UPDATE_REPOSITORY = "CynicaGaming/TorrentDashboard"' in config_py
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
    assert 'Delete downloaded files too' in html
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

    # 0.5.56 serializes all configuration read/modify/write mutations; 0.5.64
    # moves schema/migration/persistence ownership behind ConfigRepository.
    assert 'from torrent_dashboard.config import (' in dashboard_py
    assert 'from torrent_dashboard.integrations import (' in dashboard_py
    assert 'from torrent_dashboard.config_store import ConfigStore' in dashboard_py
    assert 'CONFIG_STORE = ConfigStore(CONFIG_REPOSITORY.load, CONFIG_REPOSITORY.save)' in dashboard_py
    assert 'def mutate_config(transform):' in dashboard_py
    assert 'class ConfigRepository:' in config_py and 'def normalize_config(' in config_py
    assert 'INTEGRATION_TYPES = {' in integrations_py and 'def normalize_integration(' in integrations_py
    assert 'def _load_config_unlocked' not in dashboard_py and 'INTEGRATION_TYPES = {' not in dashboard_py
    assert 'class ConfigStore:' in config_store_py and 'with self._lock:' in config_store_py
    mutation_section = dashboard_py.split('class Handler(BaseHTTPRequestHandler):', 1)[1]
    assert 'save_config(' not in mutation_section
    assert mutation_section.count('mutate_config(') >= 12

    # 0.5.66 desktop readability contract. Desktop uses available space instead
    # of falling back to the historical 8-11px interface baseline.
    assert '0.5.66 desktop legibility baseline' in app_css
    assert '0.5.66 desktop settings legibility' in settings_css
    assert '@media(min-width:1024px)' in app_css and '@media(min-width:1024px)' in settings_css
    assert ':root{--muted:#a7b3bf;--row:70px}' in app_css
    assert ':root[data-density="compact"]{--row:56px}' in app_css
    assert '.torrent-name{max-width:620px;font-size:15px}' in app_css
    assert '.update-release-body{padding:16px 17px 18px;font-size:12.5px' in app_css
    assert '.settings-subnav button{min-height:40px;padding:10px 11px;font-size:13px' in settings_css
    assert '.accordion-summary b{font-size:14px}' in settings_css
    assert '.client-setting-copy>span{font-size:11.5px' in settings_css
    assert '## Desktop legibility' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')

    # 0.5.75 retains bottom anchoring, restores Dashboard hierarchy, quiets the empty disclosure, and makes update checks explicit.
    assert 'id="topbar"' in html and 'class="topbar" id="topbar"' in html and 'class="topbar-heading"' in html
    assert "classList.toggle('dashboard-mode'" not in app_js
    assert "if(dashboardView)requestAnimationFrame(syncTorrentWorkspaceLayout)" in app_js
    assert "--torrent-workspace-height" in app_js and "--torrent-workspace-open-height" not in app_js
    assert "const available=Math.max(360,Math.floor(window.innerHeight-top-16))" in app_js
    assert '.topbar.dashboard-mode' not in app_css
    assert '.topbar.dashboard-mode .topbar-heading{display:none}' not in app_css
    assert '## Client-style dashboard workspace' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')
    assert '### Bottom-anchored torrent dock' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')
    assert 'class="topbar dashboard-mode"' not in html
    assert 'id="detailHandleSelection"></span>' in html
    assert 'No torrent selected' not in html and 'No torrent selected' not in app_js
    assert '.torrent-detail-handle-selection:empty{display:none}' in app_css
    assert 'updateIntegrityRefreshAt' not in settings_js and 'updateIntegrityRefreshPromise' not in settings_js
    assert 'checkForUpdates(true)' not in settings_js
    assert '## Explicit update checks' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')
    assert '### Update-check intent and empty detail disclosure' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')

    # 0.5.76 treats All servers as aggregation rather than the default pseudo-client.
    assert "server:localStorage.tdServer||'all'" in app_js
    assert 'function preferredServer(enabled=[])' in app_js
    assert 'if(enabled.length===1)return String(enabled[0].id)' in app_js
    assert "const includeAll=enabled.length!==1" in app_js
    assert "localStorage.tdServer=state.server" in app_js
    assert "if(state.server!=='all')await loadMeta()" in app_js
    assert '## Server-selection defaults' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')
    assert '### Server-selection defaults' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')


    # 0.5.77 preserves intentionally authored display copy and confines runtime
    # normalization to legacy generated tokens.
    assert 'function isLegacyUiToken' in app_js and 'function displayUiText' in app_js
    assert 'if(trim&&isLegacyUiToken(trim))' in app_js
    assert 'el.textContent=displayUiText(msg)' in app_js
    assert 'trim.length<80&&/[A-Za-z]/.test(trim)' not in app_js
    for copy in (
        'First-run setup','Step 1 of 4','Set up your dashboard','Dashboard name',
        'Local dashboard address','Authentication mode','Allowed IP addresses',
        'Username and password','Test connection','Not tested yet','Review and finish',
        'Sign in to Torrent Dashboard','Live torrent activity','Free disk space',
        'All categories','Download speed','HTTP sources','Accent color',
        'Torrent columns','Copy address','Add client','GitHub repository',
        'Current version','Not checked','Check for updates','Patch notes',
        'Browser notifications','Completion sound','Add integration','Add user',
        'Save .torrent file','Delete downloaded files too','Client settings',
    ):
        assert copy in html, f'missing polished interface copy: {copy}'
    for legacy in (
        'First Run Setup','Step 1 Of 4','Set Up Your Dashboard','Authentication Mode',
        'IP Address Whitelist','Username And Password','Not Tested Yet','Review And Finish',
        'Sign In To Dashboard','Live Torrent Activity','Disk Free','All Categories',
        'Download Speed','HTTP Sources','Dashboard Title','Accent Color',
        'Visible Desktop Columns','Copy Address','＋ Add Server','GitHub Repository',
        'Current Version','Latest Version','Not Checked','Update State','Check For Updates',
        'Patch Notes','Browser Notifications','Completion Sound','Custom Sound File',
        'No Custom Sound Uploaded','Test Notification','Choose Integration…',
        '＋ Add Integration','Standard Users','＋ Add User','Remove torrent(s)',
    ):
        assert legacy not in html, f'legacy capitalization remains: {legacy}'
    assert 'No Network Interfaces Detected' not in app_js
    assert 'Testing And Saving…' not in app_js and 'Setup Could Not Be Completed' not in app_js
    assert 'Standard User' not in settings_js
    assert '"standard": "Standard user"' in users_py
    assert '"API key"' in integrations_py and '"Access token"' in integrations_py
    assert '## Capitalization and product voice' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')
    assert '### Product language and capitalization' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')
    assert 'whitelist' not in html.lower()
    assert '<b id="selectedCount">0</b> selected' in html

    # 0.5.73 supersedes v0.5.72's open/close-only inspector. The dock is
    # persistent, selection and disclosure are independent, and the full bar is
    # the accessible collapse/expand target on desktop and mobile.
    assert 'class="torrent-workspace"' in html
    assert 'class="torrent-panel torrent-list-panel"' in html
    assert 'class="torrent-list-region"' in html
    assert 'class="torrent-detail-pane collapsed"' in html
    assert 'id="detailHandle"' in html and 'id="detailHandleSelection"' in html
    assert 'id="detailClose"' not in html and 'Close torrent details' not in html
    assert 'detailExpanded:false' in app_js and 'detailCollapsed' not in app_js
    assert 'function syncDetailDock()' in app_js and 'async function toggleDetailPane()' in app_js
    assert 'function resetDetailPane(' in app_js and 'closeDetailPane' not in app_js
    assert '0.5.74 bottom-anchored client workspace' in app_css
    assert '.torrent-list-region .table-wrap{flex:1 1 auto;min-height:0;overflow:auto' in app_css
    assert '.torrent-detail-pane{position:static;inset:auto' in app_css
    assert '.torrent-detail-pane.collapsed{min-height:48px!important' in app_css
    assert '.torrent-detail-handle[aria-expanded="true"] svg{transform:rotate(180deg)}' in app_css
    assert '@media(max-width:700px)' in app_css and 'bottom:58px;top:auto;height:min(68dvh,640px)' in app_css

    # 0.5.81 keeps Add Torrent checkboxes aligned while hierarchy is expressed
    # by the content label, and clears stale detail context when a torrent disappears.
    assert app_js.count('data-add-depth="${depth}" style="--add-depth:${depth}"') == 2
    assert '0.5.81 aligned Add Torrent selection column and indented hierarchy labels' in app_css
    assert '.add-content-row{grid-template-columns:34px minmax(0,1fr) 90px 112px}' in app_css
    assert '.add-content-select{place-items:center!important;padding-right:0}' in app_css
    assert '.add-content-name{padding-left:calc(var(--add-depth,0) * 16px)}' in app_css
    assert 'grid-template-columns:calc(34px + var(--add-depth,0) * 16px)' not in app_css
    assert "if(state.detail?.server===server&&state.detail?.hash===hash){resetDetailPane();return}" in app_js
    assert 'function reconcileDetailSelection()' in app_js
    assert "const exists=state.torrents.some(t=>(t._server_id||state.server)===state.detail.server&&t.hash===state.detail.hash)" in app_js
    assert 'if(!exists)resetDetailPane(false)' in app_js
    assert 'reconcileDetailSelection();renderMetrics(d)' in app_js
    assert 'function resetDetailPane(renderList=true)' in app_js
    assert '## Hierarchical torrent content selection' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')
    assert '### Add Torrent hierarchy and detail-selection reconciliation' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')

    # 0.5.82 reserves the same disclosure slot for folders and files so
    # hierarchy is expressed after the expander column, and removes the
    # redundant selected-torrent identity block from the expanded inspector.
    assert 'class="add-tree-spacer" aria-hidden="true"' in app_js
    assert '.add-tree-spacer{display:block;width:22px;min-width:22px;height:22px;flex:0 0 22px}' in app_css
    assert '0.5.82 tree disclosure alignment and streamlined Torrent details' in app_css
    assert 'class="torrent-detail-context"' not in html
    assert 'id="detailName"' not in html and 'id="detailMeta"' not in html
    assert 'torrent-detail-context' not in app_css
    assert "$('#detailName')" not in app_js and "$('#detailMeta')" not in app_js
    assert "selected?(detailCurrentTorrent()?.name||'Selected torrent'):''" in app_js
    assert 'The disclosure bar is the single selection-identity surface' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')

    # 0.5.83 replaces text-glyph disclosure/file affordances with locally
    # embedded Material SVGs and simplifies the Add Torrent content table.
    assert 'const UI_MATERIAL_ICON_PATHS={' in app_js and 'function materialIconSvg(name)' in app_js
    assert "materialIconSvg(collapsed?'chevron_right':'expand_more')" in app_js
    assert "chevron.innerHTML=materialIconSvg('expand_more')" in app_js
    assert "${collapsed?'›':'⌄'}" not in app_js and "chevron.textContent='⌄'" not in app_js
    assert 'class="material-symbol-icon detail-disclosure-icon"' in html
    assert 'class="material-symbol-icon add-drop-icon"' in html and '>⇧<' not in html
    assert '.material-symbol-icon{display:block;width:18px;height:18px;fill:currentColor' in app_css
    assert '0.5.83 locally embedded Material disclosure icons and Add Torrent table polish' in app_css
    assert '<strong>Content</strong><span id="addContentSummary"' not in html
    assert 'class="add-preview-heading add-content-summary-heading"' in html
    assert '.add-content-columns>span:nth-child(2){text-align:left}' in app_css
    assert 'class="add-folder-items"' not in app_js
    assert '## Iconography' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')
    assert 'folder rows do not show descendant file counts' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')

    # 0.5.84-v0.5.87 keeps torrent columns browser-local and directly
    # configurable from the header; v0.5.87 adds persisted edge resizing.
    assert 'id="columnPrefList"' not in html and 'id="resetColumns"' not in html
    assert 'class="menu column-menu hidden" id="columnMenu"' in html and 'aria-label="Torrent columns"' in html
    assert html.count('draggable="true" data-col=') == 14
    assert "{key:'seeds',label:'Seeds',defaultVisible:true}" in app_js
    assert "{key:'peers',label:'Peers',defaultVisible:true}" in app_js
    assert "{key:'category',label:'Category',defaultVisible:true}" in app_js
    assert "{key:'tags',label:'Tags',defaultVisible:true}" in app_js
    assert "{key:'size',label:'Size',defaultVisible:false}" in app_js
    assert "savedPreviousDefault&&column.key==='category'?true" in app_js
    assert 'widths:{}' in app_js and 'TORRENT_COLUMN_MIN_WIDTHS' in app_js and 'TORRENT_COLUMN_MAX_WIDTH=720' in app_js
    assert 'function torrentColumnPreferences()' in app_js and 'function saveTorrentColumnPreferences(prefs)' in app_js
    assert 'function applyTorrentColumnWidths' in app_js and 'function saveTorrentColumnWidth' in app_js
    assert 'function bindTorrentColumnHeaderUI()' in app_js and "head.addEventListener('contextmenu'" in app_js
    assert "head.addEventListener('dragstart'" in app_js and "head.addEventListener('dragover'" in app_js and "head.addEventListener('drop'" in app_js
    assert "head.addEventListener('pointerdown'" in app_js and "head.addEventListener('pointermove'" in app_js and "head.addEventListener('pointerup'" in app_js
    assert 'function startTorrentColumnResize' in app_js and 'function finishTorrentColumnResize' in app_js
    assert "handle.className='column-resize-handle'" in app_js and "event.target.closest('.column-resize-handle')" in app_js
    assert 'function reorderTorrentColumns(sourceKey,targetKey,after=false)' in app_js
    assert 'function renderTorrentColumnMenu()' in app_js and 'function showTorrentColumnMenu(x,y)' in app_js
    assert "materialIconSvg('check')" in app_js
    assert "row.querySelector('.row-actions-head,.row-actions')" in app_js and 'applyColumnPrefs();applyTorrentColumnWidths();const empty=' in app_js
    assert 'data-col="seeds" data-label="Seeds"' in app_js and 'data-col="peers" data-label="Peers"' in app_js and 'data-col="tags" data-label="Tags"' in app_js
    assert 'swarmColumnValue(t.num_seeds,t.num_complete)' in app_js and 'swarmColumnValue(t.num_leechs,t.num_incomplete)' in app_js
    assert 'renderTorrentColumnPreferences' not in app_js and 'saveTorrentColumnPreferencesFromSettings' not in app_js
    assert "document.querySelector('#columnPrefList')" not in settings_js and 'saveTorrentColumnPreferencesFromSettings' not in settings_js
    assert '.torrent-column-hidden{display:none!important}' in app_css
    assert '0.5.86 direct torrent-column manipulation' in app_css and '0.5.87 resizable torrent columns' in app_css
    assert '.column-resize-handle{' in app_css and 'body.torrent-column-resizing' in app_css
    assert "cell.classList.toggle('torrent-column-sized',valid)" in app_js and '.torrent-column-sized .torrent-column-text{max-width:none}' in app_css
    assert '0.5.84 torrent column organizer' not in settings_css
    assert '## Configurable torrent columns' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')
    assert 'Drag the narrow right edge' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')
    assert '### Configurable torrent columns' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')
    print("UI string audit passed")


if __name__ == "__main__":
    main()
