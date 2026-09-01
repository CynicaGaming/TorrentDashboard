#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one exact match, found {count}: {old[:100]!r}")
    write(path, text.replace(old, new, 1))


def sub_once(path: str, pattern: str, replacement: str, flags: int = 0) -> None:
    text = read(path)
    updated, count = re.subn(pattern, lambda _m: replacement, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"{path}: expected one regex match, found {count}: {pattern[:100]!r}")
    write(path, updated)


# Version and browser asset revisions.
replace_once("dashboard.py", 'VERSION = "0.5.18"', 'VERSION = "0.5.19"')
for path in ("static/index.html", "static/sw.js"):
    text = read(path)
    if "0.5.18" not in text:
        raise RuntimeError(f"{path}: previous asset version not found")
    write(path, text.replace("0.5.18", "0.5.19").replace("v0518", "v0519"))

# The Updates page no longer needs a separate connection-test control/status.
replace_once(
    "static/index.html",
    '''<div class="settings-form-grid"><label>GitHub Repository<input id="uRepository" maxlength="255" placeholder="owner/repository"/></label></div>\n<div class="settings-inline-actions"><button class="secondary" id="updateSourceTest" type="button">Test Connection</button><button class="primary" id="updateSourceSave" type="button">Save</button></div>\n<div class="test-result muted" id="updateSourceResult">Public GitHub repository used as this dashboard's update source.</div>''',
    '''<div class="settings-form-grid"><label>GitHub Repository<input id="uRepository" maxlength="255" placeholder="owner/repository"/></label></div>\n<div class="settings-inline-actions"><button class="primary" id="updateSourceSave" type="button">Save</button></div>\n<div class="field-help">Public GitHub repository used as this dashboard's update source. Save changes before checking for updates; Check for updates validates the repository before comparing releases.</div>''',
)

# Remove the redundant test button binding and status-driven test routine.
replace_once(
    "static/settings.js",
    "    document.querySelector('#updateSourceTest')?.addEventListener('click', testUpdateSource);\n",
    "",
)
sub_once(
    "static/settings.js",
    r"  async function testUpdateSource\(\) \{.*?\n  \}\n\n  async function saveUpdateSource\(\) \{.*?\n  \}\n\n  async function loadExtras",
    '''  async function saveUpdateSource() {\n    const repository = updateSourceRepository();\n    if (!repository) return toast('Enter A GitHub Repository','error');\n    try {\n      const d = await post('/api/update-source', {repository});\n      state.settings = d.settings;\n      const input = document.querySelector('#uRepository');\n      if (input) input.value = d.repository || repository;\n      renderUpdateInfo({configured:true,repository:d.repository || repository,currentVersion:state.me?.version,state:d.settings?.runtime?.updateState||{}});\n      toast('updateSourceSaved');\n      return d;\n    } catch (e) {\n      toast(e.message,'error');\n    }\n  }\n\n  async function loadExtras''',
    flags=re.S,
)

# Validate the public repository as the first phase of every update check. With
# tokenless public access GitHub intentionally does not distinguish a missing
# repository from a private one, so the error text must be accurate for both.
sub_once(
    "dashboard.py",
    r"def test_github_update_access\(repository: str\):.*?\n\ndef fetch_update_release\(cfg\):\n    repo = update_repository\(cfg\)\n",
    '''def validate_update_repository(repository: str):\n    repo = normalize_github_repository(repository)\n    try:\n        info = _urlopen_json(f"https://api.github.com/repos/{repo}", timeout=10, headers=github_headers())\n    except urllib.error.HTTPError as exc:\n        if exc.code == 403:\n            raise RuntimeError("GitHub denied the request or the unauthenticated API rate limit was reached. Try again later.") from exc\n        if exc.code == 404:\n            raise RuntimeError("Public GitHub repository not found. Verify owner/repository and make sure the repository is public.") from exc\n        raise RuntimeError(f"GitHub repository check failed with HTTP {exc.code}") from exc\n    except urllib.error.URLError as exc:\n        raise RuntimeError(f"Could not connect to GitHub: {exc.reason}") from exc\n    if bool(info.get("private", False)):\n        raise RuntimeError("Torrent Dashboard updates require a public GitHub repository")\n    return str(info.get("full_name") or repo)\n\n\ndef fetch_update_release(cfg):\n    repo = validate_update_repository(update_repository(cfg))\n''',
    flags=re.S,
)

# Remove the standalone update-source test API. Saving validates syntax only;
# Check for updates performs the network/repository validation.
replace_once(
    "dashboard.py",
    '''            if path=="/api/update-source-test":\n                data=parse_json_body(self,10000); repo=normalize_github_repository(data.get("repository") or "")\n                result=test_github_update_access(repo)\n                return self.send_json(200,result,new_cookie)\n''',
    "",
)

# Changing source invalidates any staged package from the previous repository.
replace_once(
    "dashboard.py",
    '''            if path=="/api/update-source":\n                data=parse_json_body(self,10000); updated,repo=save_update_source(cfg,data.get("repository") or ""); save_config(updated)\n                HISTORY.event("dashboard","update_source_changed",repo,"",{"client_ip":self.client_ip()})\n                return self.send_json(200,{"ok":True,"repository":repo,"settings":redacted_config(updated)},new_cookie)\n''',
    '''            if path=="/api/update-source":\n                data=parse_json_body(self,10000); previous_repo=update_repository(cfg); updated,repo=save_update_source(cfg,data.get("repository") or ""); save_config(updated)\n                if repo != previous_repo:\n                    UPDATE_STATE_PATH.unlink(missing_ok=True)\n                    if UPDATE_DIR.exists(): shutil.rmtree(UPDATE_DIR, ignore_errors=True)\n                HISTORY.event("dashboard","update_source_changed",repo,"",{"client_ip":self.client_ip()})\n                return self.send_json(200,{"ok":True,"repository":repo,"settings":redacted_config(updated)},new_cookie)\n''',
)

# Public documentation follows the streamlined flow.
replace_once(
    "README.md",
    '''1. Open **Settings → Updates**.\n2. Enter the public GitHub repository as `owner/repository`.\n3. Select **Test connection**, then **Save**.\n4. Select **Check for updates**.\n''',
    '''1. Open **Settings → Updates**.\n2. Enter the public GitHub repository as `owner/repository`, then select **Save**.\n3. Select **Check for updates**. Torrent Dashboard validates that the repository is publicly reachable before comparing releases.\n''',
)

# Release-time regression contract for the simplified Updates page.
replace_once(
    "release_tools/validate_ui_strings.py",
    '''    assert '/api/update-source-test' in dashboard_py\n    assert '/api/update-source' in dashboard_py\n    assert 'id="uRepository"' in html\n    assert 'id="updateSourceTest"' in html\n    assert 'id="updateSourceSave"' in html\n''',
    '''    assert '/api/update-source-test' not in dashboard_py\n    assert 'test_github_update_access' not in dashboard_py\n    assert 'def validate_update_repository(repository: str):' in dashboard_py\n    assert 'repo = validate_update_repository(update_repository(cfg))' in dashboard_py\n    assert '/api/update-source' in dashboard_py\n    assert 'id="uRepository"' in html\n    assert 'id="updateSourceTest"' not in html\n    assert 'id="updateSourceResult"' not in html\n    assert 'updateSourceTest' not in settings_js\n    assert 'updateSourceResult' not in settings_js\n    assert 'id="updateSourceSave"' in html\n''',
)

# Make the stale-package invalidation and reactive install flow part of release validation.
replace_once(
    "release_tools/validate_ui_strings.py",
    '''    assert "title:'Install update'" not in app_js\n    assert "confirmLabel:'Install and restart'" not in app_js\n''',
    '''    assert "title:'Install update'" not in app_js\n    assert "confirmLabel:'Install and restart'" not in app_js\n    assert 'UPDATE_STATE_PATH.unlink(missing_ok=True)' in dashboard_py\n    assert 'shutil.rmtree(UPDATE_DIR, ignore_errors=True)' in dashboard_py\n''',
)

print("Staged Torrent Dashboard 0.5.19 streamlined update-source validation")
