#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def write(path, text):
    (ROOT / path).write_text(text, encoding='utf-8')


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'{label}: expected exactly one match, found {count}')
    return text.replace(old, new, 1)


# ---------------------------------------------------------------------------
# Backend: Updates owns its public GitHub repository directly.
# ---------------------------------------------------------------------------
dashboard = read('dashboard.py')
dashboard = replace_once(dashboard, 'VERSION = "0.5.17"\nSTATUS_REFRESH_SECONDS = 1.0', 'VERSION = "0.5.18"\nSTATUS_REFRESH_SECONDS = 1.0\nDEFAULT_UPDATE_REPOSITORY = "CynicaGaming/TorrentDashboard"', 'version/default update repository')
dashboard = replace_once(dashboard, '    "updates": {},', '    "updates": {"repository": DEFAULT_UPDATE_REPOSITORY},', 'default updates config')

github_catalog = '''    "github": {\n        "label": "GitHub",\n        "fields": [\n            {"key": "repository", "label": "Repository", "placeholder": "owner/repository (public)", "required": True},\n        ],\n    },\n'''
dashboard = replace_once(dashboard, github_catalog, '', 'GitHub integration catalog entry')

old_integrations = '''    raw_integrations = raw.get("integrations")\n    if isinstance(raw_integrations, list):\n        migrated = []\n        for item in raw_integrations:\n            if not isinstance(item, dict):\n                continue\n            try:\n                migrated.append(normalize_integration(item, item))\n            except Exception:\n                continue\n        merged["integrations"] = migrated\n'''
new_integrations = '''    raw_integrations = raw.get("integrations")\n    legacy_github_repo = ""\n    if isinstance(raw_integrations, list):\n        migrated = []\n        for item in raw_integrations:\n            if not isinstance(item, dict):\n                continue\n            if str(item.get("type") or "").strip().lower() == "github":\n                if not legacy_github_repo:\n                    legacy_github_repo = str(item.get("repository") or "").strip()\n                continue\n            try:\n                migrated.append(normalize_integration(item, item))\n            except Exception:\n                continue\n        merged["integrations"] = migrated\n'''
dashboard = replace_once(dashboard, old_integrations, new_integrations, 'integration migration')

old_update_migration = '''    # GitHub update configuration lives in Integrations. Since 0.5.17 the\n    # default updater supports public repositories only and does not retain\n    # legacy GitHub access tokens.\n    legacy_updates = raw.get("updates", {}) if isinstance(raw.get("updates"), dict) else {}\n    legacy_repo = str(legacy_updates.get("repository") or "").strip()\n    if legacy_repo and not any(item.get("type") == "github" for item in merged.get("integrations", [])):\n        payload = {"id": stable_record_id("integration", "github", legacy_repo), "type": "github", "name": "GitHub", "repository": legacy_repo, "enabled": True}\n        try:\n            merged.setdefault("integrations", []).append(normalize_integration(payload, payload))\n        except Exception:\n            pass\n    merged["updates"] = {}\n'''
new_update_migration = '''    # Updates owns its public GitHub repository directly. Preserve the saved\n    # repository from either the previous Updates object or the retired GitHub\n    # integration, then remove GitHub from the integration collection.\n    legacy_updates = raw.get("updates", {}) if isinstance(raw.get("updates"), dict) else {}\n    update_repo = str(legacy_updates.get("repository") or legacy_github_repo or DEFAULT_UPDATE_REPOSITORY).strip()\n    try:\n        update_repo = normalize_github_repository(update_repo)\n    except Exception:\n        update_repo = DEFAULT_UPDATE_REPOSITORY\n    merged["updates"] = {"repository": update_repo}\n    merged["integrations"] = [x for x in merged.get("integrations", []) if x.get("type") != "github"]\n'''
dashboard = replace_once(dashboard, old_update_migration, new_update_migration, 'update source migration')

old_save_config = '''def save_config(cfg):\n    cfg = json.loads(json.dumps(cfg))\n    for integration in cfg.get("integrations", []):\n        if integration.get("type") == "github": integration.pop("token", None)\n    cfg.setdefault("updates", {}).pop("github_token", None)\n    tmp = CONFIG_PATH.with_suffix(".tmp")\n    tmp.write_text(json.dumps(cfg, indent=2) + "\\n", encoding="utf-8")\n    tmp.replace(CONFIG_PATH)\n'''
new_save_config = '''def save_config(cfg):\n    cfg = json.loads(json.dumps(cfg))\n    cfg["integrations"] = [x for x in cfg.get("integrations", []) if x.get("type") != "github"]\n    updates = cfg.setdefault("updates", {})\n    updates["repository"] = normalize_github_repository(updates.get("repository") or DEFAULT_UPDATE_REPOSITORY)\n    updates.pop("github_token", None)\n    tmp = CONFIG_PATH.with_suffix(".tmp")\n    tmp.write_text(json.dumps(cfg, indent=2) + "\\n", encoding="utf-8")\n    tmp.replace(CONFIG_PATH)\n'''
dashboard = replace_once(dashboard, old_save_config, new_save_config, 'save config update source')

dashboard = replace_once(dashboard, '''    if provider == "github":\n        item["repository"] = normalize_github_repository(item.get("repository"))\n''', '', 'GitHub normalize integration special case')

github_test_branch = '''        if provider == "github":\n            result = test_github_update_access(item["repository"])\n            release = result.get("latestRelease") or "No release published"\n            return {**result, "message": f"Connected · GitHub · {result.get('repository', item['repository'])} · {release}"}\n'''
dashboard = replace_once(dashboard, github_test_branch, '', 'GitHub integration test branch')

github_duplicate = '''    if item.get("type") == "github":\n        duplicate = next((x for x in integrations if x is not existing and str(x.get("id") or "") != item["id"] and x.get("type") == "github"), None)\n        if duplicate:\n            raise RuntimeError("Only one GitHub integration can be configured for application updates")\n'''
dashboard = replace_once(dashboard, github_duplicate, '', 'GitHub duplicate integration guard')

old_update_source_helpers = '''def github_update_integration(cfg):\n    matches = [x for x in cfg.get("integrations", []) if x.get("type") == "github" and x.get("enabled", True)]\n    if not matches:\n        raise RuntimeError("Add or enable a GitHub integration under Settings → Integrations before checking for updates")\n    if len(matches) > 1:\n        raise RuntimeError("Multiple GitHub integrations are enabled. Keep one enabled as the application update source")\n    return matches[0]\n\n\ndef github_update_headers(cfg, accept="application/vnd.github+json"):\n    github_update_integration(cfg)\n    return github_headers(accept)\n'''
new_update_source_helpers = '''def update_repository(cfg):\n    updates = cfg.get("updates", {}) if isinstance(cfg.get("updates"), dict) else {}\n    return normalize_github_repository(updates.get("repository") or DEFAULT_UPDATE_REPOSITORY)\n\n\ndef github_update_headers(cfg, accept="application/vnd.github+json"):\n    update_repository(cfg)\n    return github_headers(accept)\n\n\ndef save_update_source(cfg, repository):\n    out = json.loads(json.dumps(cfg))\n    repo = normalize_github_repository(repository)\n    out["updates"] = {"repository": repo}\n    out["integrations"] = [x for x in out.get("integrations", []) if x.get("type") != "github"]\n    return out, repo\n'''
dashboard = replace_once(dashboard, old_update_source_helpers, new_update_source_helpers, 'update source helpers')

dashboard = replace_once(dashboard, '    cfg = {"integrations": [{"type": "github", "repository": repo, "enabled": True}]}', '    cfg = {"updates": {"repository": repo}}', 'GitHub connection test cfg')
dashboard = replace_once(dashboard, '''def fetch_update_release(cfg):\n    source = github_update_integration(cfg)\n    repo = normalize_github_repository(source.get("repository"))\n''', '''def fetch_update_release(cfg):\n    repo = update_repository(cfg)\n''', 'fetch update repository')

dashboard = replace_once(dashboard, '''    def update_check(self,cfg,new_cookie):\n        try:\n            github_update_integration(cfg)\n        except Exception as e:\n            return self.send_json(200,{"configured":False,"currentVersion":VERSION,"error":str(e),"state":update_state()},new_cookie)\n        try:\n            manifest=fetch_update_manifest(cfg)\n            return self.send_json(200,{"configured":True,"currentVersion":VERSION,"manifest":manifest,"updateAvailable":manifest.get("updateAvailable",False),"state":update_state()},new_cookie)\n        except Exception as e:\n            return self.send_json(502,{"configured":True,"currentVersion":VERSION,"error":str(e),"state":update_state()},new_cookie)\n''', '''    def update_check(self,cfg,new_cookie):\n        try:\n            repo = update_repository(cfg)\n        except Exception as e:\n            return self.send_json(200,{"configured":False,"currentVersion":VERSION,"error":str(e),"state":update_state()},new_cookie)\n        try:\n            manifest=fetch_update_manifest(cfg)\n            return self.send_json(200,{"configured":True,"repository":repo,"currentVersion":VERSION,"manifest":manifest,"updateAvailable":manifest.get("updateAvailable",False),"state":update_state()},new_cookie)\n        except Exception as e:\n            return self.send_json(502,{"configured":True,"repository":repo,"currentVersion":VERSION,"error":str(e),"state":update_state()},new_cookie)\n''', 'update check handler')

post_anchor = '''            if path=="/api/settings":\n                data=parse_json_body(self); updated=apply_settings_update(cfg,data); save_config(updated)\n                HISTORY.event("dashboard", "settings_changed", sess.get("username",""), "", {"client_ip": self.client_ip()})\n                return self.send_json(200,{"ok":True,"settings":redacted_config(updated)},new_cookie)\n'''
post_replacement = post_anchor + '''            if path=="/api/update-source-test":\n                data=parse_json_body(self,10000); repo=normalize_github_repository(data.get("repository") or "")\n                result=test_github_update_access(repo)\n                return self.send_json(200,result,new_cookie)\n            if path=="/api/update-source":\n                data=parse_json_body(self,10000); updated,repo=save_update_source(cfg,data.get("repository") or ""); save_config(updated)\n                HISTORY.event("dashboard","update_source_changed",repo,"",{"client_ip":self.client_ip()})\n                return self.send_json(200,{"ok":True,"repository":repo,"settings":redacted_config(updated)},new_cookie)\n'''
dashboard = replace_once(dashboard, post_anchor, post_replacement, 'update source endpoints')

# Explicit cleanup assertions for the retired integration model.
if '"github": {' in dashboard.split('INTEGRATION_TYPES = {', 1)[1].split('\n}\n', 1)[0]:
    raise RuntimeError('GitHub still exists in INTEGRATION_TYPES')
if 'github_update_integration' in dashboard:
    raise RuntimeError('github_update_integration still exists')
if 'Add or enable a GitHub integration' in dashboard:
    raise RuntimeError('legacy GitHub integration update guidance remains')
write('dashboard.py', dashboard)

# ---------------------------------------------------------------------------
# Settings UI: rename to Updates and own repository/test/save there.
# ---------------------------------------------------------------------------
html = read('static/index.html')
html = html.replace('0.5.17', '0.5.18')
html = replace_once(html, '<button data-view="settings" data-settings-page="updates" type="button">Application Updates</button>', '<button data-view="settings" data-settings-page="updates" type="button">Updates</button>', 'desktop Updates label')
html = replace_once(html, '<option value="updates">Application Updates</option>', '<option value="updates">Updates</option>', 'mobile Updates label')
old_updates_panel = '''<section class="settings-page" data-settings-section="updates">\n<div class="panel settings-card" id="updateSettingsCard">\n<div class="panel-title">Application Updates</div>\n<div class="update-status" id="updateStatus"><div><span>Current Version</span><strong id="updateCurrent">—</strong></div><div><span>Latest Version</span><strong id="updateLatest">Not Checked</strong></div><div><span>Update State</span><strong id="updateState">Idle</strong></div></div>\n<div class="update-actions"><button class="secondary update-action" id="updateAction" type="button">Check For Updates</button></div>\n<div class="muted update-message" id="updateMessage">Application updates use the GitHub connection configured under Integrations. Add and test a GitHub integration there before checking for updates.</div>\n</div>\n</section>'''
new_updates_panel = '''<section class="settings-page" data-settings-section="updates">\n<div class="panel settings-card" id="updateSettingsCard">\n<div class="panel-title">Updates</div>\n<div class="settings-form-grid"><label>GitHub Repository<input id="uRepository" maxlength="255" placeholder="owner/repository"/></label></div>\n<div class="settings-inline-actions"><button class="secondary" id="updateSourceTest" type="button">Test Connection</button><button class="primary" id="updateSourceSave" type="button">Save</button></div>\n<div class="test-result muted" id="updateSourceResult">Public GitHub repository used as this dashboard's update source.</div>\n<div class="update-status" id="updateStatus"><div><span>Current Version</span><strong id="updateCurrent">—</strong></div><div><span>Latest Version</span><strong id="updateLatest">Not Checked</strong></div><div><span>Update State</span><strong id="updateState">Idle</strong></div></div>\n<div class="update-actions"><button class="secondary update-action" id="updateAction" type="button">Check For Updates</button></div>\n<div class="muted update-message" id="updateMessage">Check the configured public repository for a newer Torrent Dashboard release.</div>\n</div>\n</section>'''
html = replace_once(html, old_updates_panel, new_updates_panel, 'Updates panel')
html = replace_once(html, '<div class="panel settings-card"><div class="panel-title">Integrations</div><p class="muted">No integrations are populated by default. Add GitHub, media services, or notification destinations only when you use them, test each connection, and save it independently.</p>', '<div class="panel settings-card"><div class="panel-title">Integrations</div><p class="muted">No integrations are populated by default. Add media services or notification destinations only when you use them, test each connection, and save it independently.</p>', 'Integrations intro')
write('static/index.html', html)

settings = read('static/settings.js')
settings = replace_once(settings, "    document.querySelector('#updateAction')?.addEventListener('click', handleUpdateAction);", "    document.querySelector('#updateAction')?.addEventListener('click', handleUpdateAction);\n    document.querySelector('#updateSourceTest')?.addEventListener('click', testUpdateSource);\n    document.querySelector('#updateSourceSave')?.addEventListener('click', saveUpdateSource);", 'bind update source actions')
settings = replace_once(settings, '''    const githubConfigured = (s.integrations || []).some(x => x.type === 'github' && x.enabled !== false);\n    renderUpdateInfo({configured:githubConfigured,currentVersion:state.me?.version,state:s.runtime?.updateState||{}});\n''', '''    const updateRepository = s.updates?.repository || '';\n    setValue('uRepository', updateRepository);\n    renderUpdateInfo({configured:!!updateRepository,repository:updateRepository,currentVersion:state.me?.version,state:s.runtime?.updateState||{}});\n''', 'fill update repository')

insert_before_extras = '''  async function loadExtras() {\n'''
update_source_functions = '''  function updateSourceRepository() {\n    return document.querySelector('#uRepository')?.value.trim() || '';\n  }\n\n  async function testUpdateSource() {\n    const result = document.querySelector('#updateSourceResult');\n    const repository = updateSourceRepository();\n    if (!repository) return toast('Enter A GitHub Repository','error');\n    if (result) { result.className='test-result muted'; result.textContent='Testing Connection…'; }\n    try {\n      const d = await post('/api/update-source-test', {repository});\n      if (result) {\n        result.className='test-result ok';\n        result.textContent=`Connected · ${d.repository || repository}${d.latestRelease ? ` · ${d.latestRelease}` : ''}`;\n      }\n      return d;\n    } catch (e) {\n      if (result) { result.className='test-result bad'; result.textContent=e.message; }\n      toast(e.message,'error');\n    }\n  }\n\n  async function saveUpdateSource() {\n    const result = document.querySelector('#updateSourceResult');\n    const repository = updateSourceRepository();\n    if (!repository) return toast('Enter A GitHub Repository','error');\n    try {\n      const d = await post('/api/update-source', {repository});\n      state.settings = d.settings;\n      const input = document.querySelector('#uRepository');\n      if (input) input.value = d.repository || repository;\n      renderUpdateInfo({configured:true,repository:d.repository || repository,currentVersion:state.me?.version,state:d.settings?.runtime?.updateState||{}});\n      if (result) { result.className='test-result ok'; result.textContent=`Update source saved · ${d.repository || repository}`; }\n      toast('updateSourceSaved');\n      return d;\n    } catch (e) {\n      if (result) { result.className='test-result bad'; result.textContent=e.message; }\n      toast(e.message,'error');\n    }\n  }\n\n'''
settings = replace_once(settings, insert_before_extras, update_source_functions + insert_before_extras, 'update source settings functions')
settings = replace_once(settings, '''      renderIntegrations();\n      renderUpdateInfo({configured:integrations.some(x => x.type === 'github' && x.enabled !== false),currentVersion:state.me?.version,state:state.settings?.runtime?.updateState||{}});\n''', '''      renderIntegrations();\n''', 'remove GitHub integration updater coupling')
if "x.type === 'github'" in settings:
    raise RuntimeError('settings.js still couples updates to GitHub integration')
write('static/settings.js', settings)

app = read('static/app.js')
app = replace_once(app, "else if(data?.configured===false){text=data?.error||'Add or enable a GitHub integration under Integrations to check for updates'}", "else if(data?.configured===false){text=data?.error||'Enter and save a public GitHub repository under Updates before checking for updates'}", 'update configuration guidance')
old_install = "async function installUpdate(){const version=state.updateInfo?.state?.version||state.settings?.runtime?.updateState?.version||$('#updateLatest').textContent;const proceed=await showActionDialog({title:'Install update',message:`Torrent Dashboard ${version} is ready to install. The dashboard will restart to finish the update.`,input:false,confirmLabel:'Install and restart'});if(!proceed)return;const b=$('#updateAction');if(b){b.disabled=true;b.textContent=uiText('restarting…')}try{await post('/api/update-install',{version});$('#updateMessage').textContent=`${uiText('installing')} ${version} · ${uiText('torrentDashboardWillRestart')}`;$('#updateState').textContent=uiText('installing');toast('installingUpdate');waitForUpdatedServer(version)}catch(e){if(b){b.disabled=false;b.textContent=uiText('installUpdate')}toast(e.message,'error')}}"
new_install = "async function installUpdate(){const version=state.updateInfo?.state?.version||state.settings?.runtime?.updateState?.version||$('#updateLatest').textContent;const b=$('#updateAction');if(b){b.disabled=true;b.textContent=uiText('restarting…')}try{await post('/api/update-install',{version});$('#updateMessage').textContent=`${uiText('installing')} ${version} · ${uiText('torrentDashboardWillRestart')}`;$('#updateState').textContent=uiText('installing');toast('installingUpdate');waitForUpdatedServer(version)}catch(e){if(b){b.disabled=false;b.textContent=uiText('installUpdate')}toast(e.message,'error')}}"
app = replace_once(app, old_install, new_install, 'reactive install button without confirmation modal')
if "title:'Install update'" in app or "confirmLabel:'Install and restart'" in app:
    raise RuntimeError('install confirmation modal still referenced')
write('static/app.js', app)

sw = read('static/sw.js').replace('0.5.17', '0.5.18').replace('v0517', 'v0518')
write('static/sw.js', sw)

# ---------------------------------------------------------------------------
# README: Updates now owns the public repository directly.
# ---------------------------------------------------------------------------
readme = read('README.md')
readme = replace_once(readme, '## Application Updates', '## Updates', 'README Updates heading')
old_steps = '''1. Add a **GitHub** integration under **Settings → Integrations**.\n2. Enter the public repository as `owner/repository`.\n3. Select **Test connection**.\n4. Open **Application updates** and select **Check for updates**.\n'''
new_steps = '''1. Open **Settings → Updates**.\n2. Enter the public GitHub repository as `owner/repository`.\n3. Select **Test connection**, then **Save**.\n4. Select **Check for updates**.\n'''
readme = replace_once(readme, old_steps, new_steps, 'README update steps')
readme = readme.replace('Fork maintainers can adapt the updater or integration model for their own deployment requirements.', 'Fork maintainers can point **Settings → Updates** at their own public release repository or change `DEFAULT_UPDATE_REPOSITORY` for their build.')
write('README.md', readme)

# Release-time sanity assertions.
for path in ('static/index.html','static/app.js','static/settings.js','static/sw.js'):
    text = read(path)
    if '0.5.17' in text:
        raise RuntimeError(f'old asset version remains in {path}')
if 'Application Updates' in read('static/index.html'):
    raise RuntimeError('Application Updates label remains in UI')
if 'GitHub, media services' in read('static/index.html'):
    raise RuntimeError('GitHub remains described as an integration')
if 'id="uRepository"' not in read('static/index.html') or 'id="updateSourceTest"' not in read('static/index.html'):
    raise RuntimeError('Updates source controls missing')

print('Staged Torrent Dashboard 0.5.18 Updates source redesign')
