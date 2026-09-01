#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def write(path, text):
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text, old, new, label):
    if old not in text:
        raise RuntimeError(f"Missing expected source for {label}")
    return text.replace(old, new, 1)


# --- dashboard.py ---------------------------------------------------------
p = read("dashboard.py")
p = replace_once(p, 'VERSION = "0.5.12"', 'VERSION = "0.5.13"', "version")
p = replace_once(
    p,
    '''    "updates": {\n        "enabled": True,\n        "repository": "CynicaGaming/TorrentDashboard",\n        "github_token": "",\n        "auto_check": True,\n        "check_hours": 6\n    },''',
    '''    "updates": {},''',
    "default update configuration",
)
p = re.sub(
    r'''\n    updates_raw = raw\.setdefault\("updates", \{\}\)\n    updates_raw\.setdefault\("github_token", ""\)\n    legacy_manifest = raw\.get\("dashboard", \{\}\)\.get\("update_manifest_url", ""\)\n    if legacy_manifest and not updates_raw\.get\("manifest_url"\):\n        updates_raw\["manifest_url"\] = legacy_manifest\n        updates_raw\["enabled"\] = True\n''',
    "\n",
    p,
    count=1,
)
marker = '''    for legacy_key in ("webhook_url", "discord_webhook", "ntfy_url"):\n        merged.setdefault("notifications", {}).pop(legacy_key, None)\n\n    sync_legacy_auth(merged)'''
replacement = '''    for legacy_key in ("webhook_url", "discord_webhook", "ntfy_url"):\n        merged.setdefault("notifications", {}).pop(legacy_key, None)\n\n    # 0.5.13 moves GitHub credentials into the modular Integrations system.\n    # Existing installs are migrated in memory so update access is preserved,\n    # while fresh installs continue to start with an empty integrations list.\n    legacy_updates = raw.get("updates", {}) if isinstance(raw.get("updates"), dict) else {}\n    legacy_repo = str(legacy_updates.get("repository") or "").strip()\n    legacy_token = str(legacy_updates.get("github_token") or "").strip()\n    if legacy_repo and not any(item.get("type") == "github" for item in merged.get("integrations", [])):\n        payload = {\n            "id": stable_record_id("integration", "github", legacy_repo),\n            "type": "github",\n            "name": "GitHub",\n            "repository": legacy_repo,\n            "token": legacy_token,\n            "enabled": True,\n        }\n        try:\n            merged.setdefault("integrations", []).append(normalize_integration(payload, payload))\n        except Exception:\n            pass\n    # The old update-settings object is deliberately retired. GitHub integration\n    # is now the single source of truth for repository and token configuration.\n    merged["updates"] = {}\n\n    sync_legacy_auth(merged)'''
p = replace_once(p, marker, replacement, "GitHub integration migration")
p = replace_once(
    p,
    'INTEGRATION_TYPES = {\n    "sonarr": {',
    '''INTEGRATION_TYPES = {\n    "github": {\n        "label": "GitHub",\n        "fields": [\n            {"key": "repository", "label": "Repository", "placeholder": "owner/repository", "required": True},\n            {"key": "token", "label": "Access Token", "placeholder": "Fine-grained token with Contents: Read", "secret": True, "required": False},\n        ],\n    },\n    "sonarr": {''',
    "GitHub integration catalog entry",
)
p = replace_once(
    p,
    '''        item[key] = value\n    return item\n\n\ndef redacted_integrations''',
    '''        item[key] = value\n    if provider == "github":\n        item["repository"] = normalize_github_repository(item.get("repository"))\n    return item\n\n\ndef redacted_integrations''',
    "GitHub integration normalization",
)
p = replace_once(
    p,
    '''        if provider in ("sonarr", "radarr", "lidarr", "prowlarr"):\n            req = urllib.request.Request(item["url"].rstrip("/") + "/api/v3/system/status", headers={"X-Api-Key": item["api_key"], "Accept": "application/json"})''',
    '''        if provider == "github":\n            result = test_github_update_access(item["repository"], item.get("token", ""))\n            release = result.get("latestRelease") or "No release published"\n            return {**result, "message": f"Connected · GitHub · {result.get('repository', item['repository'])} · {release}"}\n        if provider in ("sonarr", "radarr", "lidarr", "prowlarr"):\n            req = urllib.request.Request(item["url"].rstrip("/") + "/api/v3/system/status", headers={"X-Api-Key": item["api_key"], "Accept": "application/json"})''',
    "GitHub integration connection test",
)
p = replace_once(
    p,
    '''    item = normalize_integration(data, existing)\n    if existing:\n        integrations[integrations.index(existing)] = item''',
    '''    item = normalize_integration(data, existing)\n    if item.get("type") == "github":\n        duplicate = next((x for x in integrations if x is not existing and str(x.get("id") or "") != item["id"] and x.get("type") == "github"), None)\n        if duplicate:\n            raise RuntimeError("Only one GitHub integration can be configured for application updates")\n    if existing:\n        integrations[integrations.index(existing)] = item''',
    "single GitHub integration rule",
)
old_headers = '''def github_update_headers(cfg, accept="application/vnd.github+json"):\n    headers = {\n        "User-Agent": f"TorrentDashboard/{VERSION}",\n        "Accept": accept,\n        "X-GitHub-Api-Version": "2022-11-28",\n    }\n    token = str(cfg.get("updates", {}).get("github_token") or "").strip()\n    if token and token != "<configured>":\n        headers["Authorization"] = f"Bearer {token}"\n    return headers\n'''
new_headers = '''def github_headers(token="", accept="application/vnd.github+json"):\n    headers = {\n        "User-Agent": f"TorrentDashboard/{VERSION}",\n        "Accept": accept,\n        "X-GitHub-Api-Version": "2022-11-28",\n    }\n    token = str(token or "").strip()\n    if token and token != "<configured>":\n        headers["Authorization"] = f"Bearer {token}"\n    return headers\n\n\ndef github_update_integration(cfg):\n    matches = [x for x in cfg.get("integrations", []) if x.get("type") == "github" and x.get("enabled", True)]\n    if not matches:\n        raise RuntimeError("Add or enable a GitHub integration under Settings → Integrations before checking for updates")\n    if len(matches) > 1:\n        raise RuntimeError("Multiple GitHub integrations are enabled. Keep one enabled as the application update source")\n    return matches[0]\n\n\ndef github_update_headers(cfg, accept="application/vnd.github+json"):\n    integration = github_update_integration(cfg)\n    return github_headers(integration.get("token", ""), accept)\n'''
p = replace_once(p, old_headers, new_headers, "GitHub header source")
p = replace_once(
    p,
    '''        token = str(cfg.get("updates", {}).get("github_token") or "").strip()''',
    '''        token = str(github_update_integration(cfg).get("token") or "").strip()''',
    "GitHub release error token",
)
p = replace_once(
    p,
    '''    cfg = {"updates": {"github_token": token}}\n    headers = github_update_headers(cfg)''',
    '''    cfg = {"integrations": [{"type": "github", "repository": repo, "token": token, "enabled": True}]}\n    headers = github_headers(token)''',
    "GitHub connection test temporary config",
)
p = replace_once(
    p,
    '''def fetch_update_release(cfg):\n    u=cfg.get("updates",{})\n    repo=str(u.get("repository") or "").strip()\n    if not repo:\n        raise RuntimeError("No GitHub update repository is configured")\n    repo=normalize_github_repository(repo)''',
    '''def fetch_update_release(cfg):\n    source = github_update_integration(cfg)\n    repo = normalize_github_repository(source.get("repository"))''',
    "update source integration",
)
p = re.sub(r'\n\s*"updates": \{"enabled": cfg\.get\("updates",\{\}\)\.get\("enabled",True\), "repository": cfg\.get\("updates",\{\}\)\.get\("repository","CynicaGaming/TorrentDashboard"\)\},', '', p, count=1)
p = replace_once(p, '        if path=="/api/setup/test-github": return self.setup_test_github()\n', '', "setup GitHub route")
p = re.sub(
    r'''\n            if path=="/api/update-test":\n                data=parse_json_body\(self,20000\)\n                repo=str\(data\.get\("repository"\) or cfg\.get\("updates",\{\}\)\.get\("repository"\) or ""\)\.strip\(\)\n                supplied=str\(data\.get\("github_token"\) or ""\)\.strip\(\)\n                token_value=supplied or str\(cfg\.get\("updates",\{\}\)\.get\("github_token"\) or ""\)\.strip\(\)\n                result=test_github_update_access\(repo,token_value\)\n                return self\.send_json\(200,result,new_cookie\)''',
    '', p, count=1,
)
p = re.sub(
    r'''\n    def setup_test_github\(self\):\n        try:\n            data=parse_json_body\(self,20000\); self\.setup_authorized\(data\)\n            repo=str\(data\.get\("repository"\) or ""\)\.strip\(\)\n            token=str\(data\.get\("github_token"\) or ""\)\.strip\(\)\n            return self\.send_json\(200,test_github_update_access\(repo,token\)\)\n        except Exception as e:\n            return self\.send_json\(400,\{"error":str\(e\)\}\)\n''',
    '', p, count=1,
)
p = replace_once(
    p,
    '            dashboard=data.get("dashboard") or {}; updates=data.get("updates") or {}; auth=data.get("auth") or {}; servers=data.get("servers") or []',
    '            dashboard=data.get("dashboard") or {}; auth=data.get("auth") or {}; servers=data.get("servers") or []',
    "setup payload parsing",
)
p = re.sub(
    r'''\n            update_enabled=bool\(updates\.get\("enabled",False\)\)\n            update_repo=str\(updates\.get\("repository"\) or ""\)\.strip\(\)\n            if update_enabled and not update_repo:\n                raise RuntimeError\("Set the GitHub repository before enabling updates"\)\n            out\["updates"\]\["enabled"\]=update_enabled\n            out\["updates"\]\["repository"\]=normalize_github_repository\(update_repo\) if update_repo else ""\n            token=str\(updates\.get\("github_token"\) or ""\)\.strip\(\)\n            if token: out\["updates"\]\["github_token"\]=token\n            out\["updates"\]\["auto_check"\]=bool\(updates\.get\("auto_check",True\)\)\n            out\["updates"\]\["check_hours"\]=max\(1,min\(168,int\(updates\.get\("check_hours"\) or 6\)\)\)''',
    '', p, count=1,
)
old_update_check = '''    def update_check(self,cfg,new_cookie):\n        updates=cfg.get("updates",{})\n        if not updates.get("enabled"):\n            return self.send_json(200,{"configured":False,"enabled":False,"currentVersion":VERSION,"state":update_state()},new_cookie)\n        try:\n            manifest=fetch_update_manifest(cfg)\n            return self.send_json(200,{"configured":True,"enabled":True,"currentVersion":VERSION,"manifest":manifest,"updateAvailable":manifest.get("updateAvailable",False),"state":update_state()},new_cookie)\n        except Exception as e:\n            return self.send_json(502,{"configured":True,"enabled":True,"currentVersion":VERSION,"error":str(e),"state":update_state()},new_cookie)\n'''
new_update_check = '''    def update_check(self,cfg,new_cookie):\n        try:\n            github_update_integration(cfg)\n        except Exception as e:\n            return self.send_json(200,{"configured":False,"currentVersion":VERSION,"error":str(e),"state":update_state()},new_cookie)\n        try:\n            manifest=fetch_update_manifest(cfg)\n            return self.send_json(200,{"configured":True,"currentVersion":VERSION,"manifest":manifest,"updateAvailable":manifest.get("updateAvailable",False),"state":update_state()},new_cookie)\n        except Exception as e:\n            return self.send_json(502,{"configured":True,"currentVersion":VERSION,"error":str(e),"state":update_state()},new_cookie)\n'''
p = replace_once(p, old_update_check, new_update_check, "update check behavior")
p = replace_once(p, '    if out.get("updates",{}).get("github_token"): out["updates"]["github_token"]="<configured>"\n', '', "legacy update token redaction")
p = re.sub(
    r'''\n    updates=data\.get\("updates",\{\}\)\n    if "enabled" in updates: out\["updates"\]\["enabled"\]=bool\(updates\.get\("enabled"\)\)\n    if "repository" in updates:\n        repo=str\(updates\.get\("repository"\) or ""\)\.strip\(\)\n        out\["updates"\]\["repository"\]=normalize_github_repository\(repo\) if repo else ""\n    if "github_token" in updates:\n        token=str\(updates\.get\("github_token"\) or ""\)\n        if token and token != "<configured>": out\["updates"\]\["github_token"\]=token\.strip\(\)\n    if "auto_check" in updates: out\["updates"\]\["auto_check"\]=bool\(updates\.get\("auto_check"\)\)\n    if "check_hours" in updates: out\["updates"\]\["check_hours"\]=max\(1,min\(168,int\(updates\.get\("check_hours"\) or 6\)\)\)\n    if out\["updates"\]\.get\("enabled"\) and not out\["updates"\]\.get\("repository"\):\n        raise RuntimeError\("Set a GitHub repository before enabling updates"\)''',
    '', p, count=1,
)
write("dashboard.py", p)

# --- index.html -----------------------------------------------------------
h = read("static/index.html").replace("0.5.12", "0.5.13")
h = replace_once(
    h,
    '<ol id="setupSteps"><li class="active"><button data-setup-step="0" type="button">Dashboard</button></li><li><button data-setup-step="1" type="button">Access Control</button></li><li><button data-setup-step="2" type="button">Download Client</button></li><li><button data-setup-step="3" type="button">Application Updates</button></li><li><button data-setup-step="4" type="button">Review</button></li></ol>',
    '<ol id="setupSteps"><li class="active"><button data-setup-step="0" type="button">Dashboard</button></li><li><button data-setup-step="1" type="button">Access Control</button></li><li><button data-setup-step="2" type="button">Download Client</button></li><li><button data-setup-step="3" type="button">Review</button></li></ol>',
    "four-step setup navigation",
)
h = h.replace("Step 1 Of 5", "Step 1 Of 4").replace("Step 2 Of 5", "Step 2 Of 4").replace("Step 3 Of 5", "Step 3 Of 4")
h = re.sub(
    r'''\n<section class="setup-page" data-step="3">\n<span class="eyebrow">Step 4 Of 5</span><h1>Configure Application Updates</h1>.*?</section>\n<section class="setup-page" data-step="4">\n<span class="eyebrow">Step 5 Of 5</span>''',
    '\n<section class="setup-page" data-step="3">\n<span class="eyebrow">Step 4 Of 4</span>',
    h,
    count=1,
    flags=re.S,
)
old_updates_html = '''<section class="settings-page" data-settings-section="updates">\n<div class="panel settings-card" id="updateSettingsCard">\n<div class="panel-title">Application Updates</div>\n<div class="update-config">\n<label class="toggle"><input id="sUpdatesEnabled" type="checkbox"/><span>Enable GitHub Updates</span></label>\n<label class="full-field">GitHub Repository<input autocomplete="off" id="sUpdateRepo" placeholder="owner/repository or https://github.com/owner/repository"/></label><label class="full-field">GitHub Update Token <small>(Required For Private Repositories)</small><input autocomplete="off" id="sUpdateToken" placeholder="Leave Blank To Keep Current Token" type="password"/></label>\n<label class="toggle"><input id="sUpdateAutoCheck" type="checkbox"/><span>Check Automatically</span></label>\n<label>Check Interval Hours<input id="sUpdateHours" max="168" min="1" type="number" value="6"/></label>\n</div>\n<div class="update-status" id="updateStatus"><div><span>Current Version</span><strong id="updateCurrent">—</strong></div><div><span>Latest Version</span><strong id="updateLatest">Not Checked</strong></div><div><span>Update State</span><strong id="updateState">Idle</strong></div></div>\n<div class="update-actions"><button class="secondary" id="testUpdateAccess" type="button">Test GitHub Connection</button><button class="secondary update-action" id="updateAction" type="button">Check For Updates</button></div>\n<div class="test-result muted update-access-result" id="updateAccessResult">Not Tested Yet</div>\n<div class="muted update-message" id="updateMessage">Configure the GitHub repository and, for a private repository, a token with <code>Contents: Read</code>. Releases are checked directly through GitHub and verified against the ZIP digest before installation.</div>\n</div>\n</section>'''
new_updates_html = '''<section class="settings-page" data-settings-section="updates">\n<div class="panel settings-card" id="updateSettingsCard">\n<div class="panel-title">Application Updates</div>\n<div class="update-status" id="updateStatus"><div><span>Current Version</span><strong id="updateCurrent">—</strong></div><div><span>Latest Version</span><strong id="updateLatest">Not Checked</strong></div><div><span>Update State</span><strong id="updateState">Idle</strong></div></div>\n<div class="update-actions"><button class="secondary update-action" id="updateAction" type="button">Check For Updates</button></div>\n<div class="muted update-message" id="updateMessage">Application updates use the GitHub connection configured under Integrations. Add and test a GitHub integration there before checking for updates.</div>\n</div>\n</section>'''
h = replace_once(h, old_updates_html, new_updates_html, "application updates settings UI")
h = h.replace(
    'No integrations are populated by default. Add media services or notification destinations only when you use them, test each connection, and save it independently.',
    'No integrations are populated by default. Add GitHub, media services, or notification destinations only when you use them, test each connection, and save it independently.',
)
write("static/index.html", h)

# --- settings.js ----------------------------------------------------------
s = read("static/settings.js")
s = replace_once(s, "const corePages = new Set(['general','access','clients','updates','notifications']);", "const corePages = new Set(['general','access','clients','notifications']);", "settings savebar pages")
s = re.sub(
    r'''\n    document\.querySelector\('#testUpdateAccess'\)\?\.addEventListener\('click', \(\) => testGitHubAccess\(\)\.catch\(\(\) => \{\}\)\);\n    \['sUpdateRepo','sUpdateToken'\]\.forEach\(id => document\.querySelector\('#'\+id\)\?\.addEventListener\('input', \(\) => \{\n      const out = document\.querySelector\('#updateAccessResult'\);\n      if \(out\) \{ out\.className='test-result muted update-access-result'; out\.textContent='Not Tested Yet'; \}\n    \}\)\);''',
    '', s, count=1,
)
s = re.sub(
    r'''\n    setChecked\('sUpdatesEnabled', s\.updates\?\.enabled\);\n    setValue\('sUpdateRepo', s\.updates\?\.repository \|\| 'CynicaGaming/TorrentDashboard'\);\n    setValue\('sUpdateToken', ''\);\n    const token = document\.querySelector\('#sUpdateToken'\);\n    configuredSecret\(token, s\.updates\?\.github_token === '<configured>', 'Fine-grained token with Contents: Read'\);\n    setChecked\('sUpdateAutoCheck', s\.updates\?\.auto_check !== false\);\n    setValue\('sUpdateHours', s\.updates\?\.check_hours \|\| 6\);\n    renderUpdateInfo\(\{configured:!!s\.updates\?\.repository,currentVersion:state\.me\?\.version,state:s\.runtime\?\.updateState\|\|\{\}\}\);''',
    '''\n    const githubConfigured = (s.integrations || []).some(x => x.type === 'github' && x.enabled !== false);\n    renderUpdateInfo({configured:githubConfigured,currentVersion:state.me?.version,state:s.runtime?.updateState||{}});''',
    s,
    count=1,
)
s = re.sub(
    r'''\n      updates: \{\n        enabled: !!document\.querySelector\('#sUpdatesEnabled'\)\?\.checked,\n        repository: document\.querySelector\('#sUpdateRepo'\)\?\.value\.trim\(\) \|\| '',\n        github_token: secretFieldValue\(document\.querySelector\('#sUpdateToken'\), '<configured>'\),\n        auto_check: document\.querySelector\('#sUpdateAutoCheck'\)\?\.checked !== false,\n        check_hours: Number\(document\.querySelector\('#sUpdateHours'\)\?\.value \|\| 6\)\n      \},''',
    '', s, count=1,
)
s = replace_once(
    s,
    '''      renderIntegrations();\n    } catch (e) {''',
    '''      renderIntegrations();\n      renderUpdateInfo({configured:integrations.some(x => x.type === 'github' && x.enabled !== false),currentVersion:state.me?.version,state:state.settings?.runtime?.updateState||{}});\n    } catch (e) {''',
    "integration-driven update status",
)
write("static/settings.js", s)

# --- app.js ---------------------------------------------------------------
a = read("static/app.js").replace("0.5.12", "0.5.13")
a = re.sub(
    r''',updates:\{enabled:\$\('#wUpdatesEnabled'\)\.checked,repository:\$\('#wUpdateRepo'\)\.value\.trim\(\),github_token:\$\('#wUpdateToken'\)\.value\.trim\(\),auto_check:\$\('#wUpdateAutoCheck'\)\.checked,check_hours:6\}''',
    '', a, count=1,
)
a = re.sub(r'''\nfunction githubAccessSummary\(d\).*?\n\nfunction updateSetupStep\(\)''', '\n\nfunction updateSetupStep()', a, count=1, flags=re.S)
a = a.replace("if(step===3&&$('#wUpdatesEnabled').checked&&!$('#wUpdateRepo').value.trim())throw new Error('enterGitHubRepositoryForUpdates')", "")
a = replace_once(
    a,
    "if(state.setupStep===last)renderSetupReview();$('#setupError').textContent=''",
    "if(state.setupStep===last)renderSetupReview();$('#setupError').textContent=''",
    "setup review trigger",
)
a = re.sub(
    r'''function renderSetupReview\(\)\{\n  const p=setupPayload\(\),mode=(.*?)\n  \$\('#wReview'\)\.innerHTML=`(.*?)<div><span>Application Updates</span><b>\$\{p\.updates\.enabled\?'GitHub Updates Enabled':'Manual Updates'\}</b><small>\$\{p\.updates\.enabled\?esc\(p\.updates\.repository\):'Can Be Enabled Later Under Settings\.'\}</small></div>`;''',
    lambda m: "function renderSetupReview(){\n  const p=setupPayload(),mode=" + m.group(1) + "\n  $('#wReview').innerHTML=`" + m.group(2) + "`;",
    a,
    count=1,
    flags=re.S,
)
a = a.replace("validateSetupThrough(3);", "validateSetupThrough(2);")
a = re.sub(
    r'''\$\('#wTestUpdate'\)\.addEventListener\('click',\(\)=>testSetupGitHubAccess\(\)\.catch\(\(\)=>\{\}\)\);\['wUpdateRepo','wUpdateToken'\]\.forEach\(id=>\$\('#'\+id\)\.addEventListener\('input',\(\)=>\{const out=\$\('#wUpdateResult'\);out\.className='test-result muted';out\.textContent='Not Tested Yet'\}\)\)''',
    '', a, count=1,
)
a = re.sub(
    r'''\$\('#wUpdateRepo'\)\.value=state\.setup\?\.updates\?\.repository\|\|\$\('#wUpdateRepo'\)\.value\|\|'CynicaGaming/TorrentDashboard';\$\('#wUpdatesEnabled'\)\.checked=state\.setup\?\.updates\?\.enabled!==false;''',
    '', a, count=1,
)
a = a.replace(";if(state.me.can_manage)setTimeout(maybeAutoCheckUpdates,1200);", ";")
a = re.sub(r'''\nfunction maybeAutoCheckUpdates\(\).*?\n\nfunction applyPrefs\(\)''', '\n\nfunction applyPrefs()', a, count=1, flags=re.S)
a = a.replace("else if(data?.configured===false){text='updatesNotConfigured'}", "else if(data?.configured===false){text=data?.error||'Add or enable a GitHub integration under Integrations to check for updates'}")
write("static/app.js", a)

# --- service worker -------------------------------------------------------
sw = read("static/sw.js").replace("v0512", "v0513").replace("0.5.12", "0.5.13")
write("static/sw.js", sw)

# --- release UI validator ------------------------------------------------
v = read("release_tools/validate_ui_strings.py")
insert = '''    assert 'github' in dashboard_py\n    assert 'id="sUpdateRepo"' not in html\n    assert 'id="sUpdateToken"' not in html\n    assert 'id="sUpdateAutoCheck"' not in html\n    assert 'id="sUpdateHours"' not in html\n    assert 'id="testUpdateAccess"' not in html\n    assert 'id="wUpdateRepo"' not in html\n    assert 'id="wUpdateToken"' not in html\n    assert 'id="wUpdatesEnabled"' not in html\n    assert 'id="wUpdateAutoCheck"' not in html\n    assert 'Test GitHub Connection' not in html\n    assert 'maybeAutoCheckUpdates' not in app_js\n    assert 'setup_test_github' not in dashboard_py\n    assert '/api/update-test' not in dashboard_py\n    assert 'github_update_integration' in dashboard_py\n    assert 'Only one GitHub integration can be configured' in dashboard_py\n'''
v = replace_once(v, '    assert \'id="settingsNavGroup"\' in html\n', insert + '    assert \'id="settingsNavGroup"\' in html\n', "0.5.13 validator assertions")
write("release_tools/validate_ui_strings.py", v)

# Final source-level contract checks before CI performs syntax/runtime validation.
checks = {
    "dashboard.py": [
        'VERSION = "0.5.13"', '"github": {', 'github_update_integration',
        'merged["updates"] = {}', 'Only one GitHub integration can be configured',
    ],
    "static/index.html": [
        'Step 4 Of 4', 'data-settings-section="updates"', 'id="updateAction"',
        'Application updates use the GitHub connection configured under Integrations.',
    ],
    "static/settings.js": ["const corePages = new Set(['general','access','clients','notifications']);", "type === 'github'"],
    "static/app.js": ["validateSetupThrough(2)", "Add or enable a GitHub integration under Integrations to check for updates"],
    "static/sw.js": ["torrent-dashboard-v0513", "0.5.13"],
}
for path, needles in checks.items():
    text = read(path)
    for needle in needles:
        if needle not in text:
            raise RuntimeError(f"{path}: expected {needle!r}")

for forbidden in [
    'id="sUpdateRepo"', 'id="sUpdateToken"', 'id="sUpdateAutoCheck"', 'id="sUpdateHours"',
    'id="testUpdateAccess"', 'id="wUpdateRepo"', 'id="wUpdateToken"', 'id="wUpdatesEnabled"',
    'id="wUpdateAutoCheck"', 'Test GitHub Connection',
]:
    if forbidden in read("static/index.html"):
        raise RuntimeError(f"index.html still contains retired update UI: {forbidden}")
if "maybeAutoCheckUpdates" in read("static/app.js"):
    raise RuntimeError("Automatic update checking code remains")

print("GitHub integration update flow applied")
