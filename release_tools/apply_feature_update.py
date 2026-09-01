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
# Backend: GitHub updates are public/unauthenticated by default.
# ---------------------------------------------------------------------------
dashboard = read('dashboard.py')
dashboard = replace_once(dashboard, 'VERSION = "0.5.16"', 'VERSION = "0.5.17"', 'version')
dashboard = replace_once(
    dashboard,
    '            {"key": "repository", "label": "Repository", "placeholder": "owner/repository", "required": True},\n            {"key": "token", "label": "Access Token", "placeholder": "Fine-grained token with Contents: Read", "secret": True, "required": False},',
    '            {"key": "repository", "label": "Repository", "placeholder": "owner/repository (public)", "required": True},',
    'GitHub integration fields',
)

old_legacy = '''    # 0.5.13 moves GitHub credentials into the modular Integrations system.\n    # Existing installs are migrated in memory so update access is preserved,\n    # while fresh installs continue to start with an empty integrations list.\n    legacy_updates = raw.get("updates", {}) if isinstance(raw.get("updates"), dict) else {}\n    legacy_repo = str(legacy_updates.get("repository") or "").strip()\n    legacy_token = str(legacy_updates.get("github_token") or "").strip()\n    if legacy_repo and not any(item.get("type") == "github" for item in merged.get("integrations", [])):\n        payload = {\n            "id": stable_record_id("integration", "github", legacy_repo),\n            "type": "github",\n            "name": "GitHub",\n            "repository": legacy_repo,\n            "token": legacy_token,\n            "enabled": True,\n        }\n        try:\n            merged.setdefault("integrations", []).append(normalize_integration(payload, payload))\n        except Exception:\n            pass\n    # The old update-settings object is deliberately retired. GitHub integration\n    # is now the single source of truth for repository and token configuration.\n    merged["updates"] = {}\n'''
new_legacy = '''    # GitHub update configuration lives in the modular Integrations system.\n    # 0.5.17 supports public repositories only, so legacy access tokens are\n    # deliberately not migrated into the active configuration.\n    legacy_updates = raw.get("updates", {}) if isinstance(raw.get("updates"), dict) else {}\n    legacy_repo = str(legacy_updates.get("repository") or "").strip()\n    if legacy_repo and not any(item.get("type") == "github" for item in merged.get("integrations", [])):\n        payload = {\n            "id": stable_record_id("integration", "github", legacy_repo),\n            "type": "github",\n            "name": "GitHub",\n            "repository": legacy_repo,\n            "enabled": True,\n        }\n        try:\n            merged.setdefault("integrations", []).append(normalize_integration(payload, payload))\n        except Exception:\n            pass\n    merged["updates"] = {}\n'''
dashboard = replace_once(dashboard, old_legacy, new_legacy, 'legacy GitHub migration')

dashboard = replace_once(
    dashboard,
    '''def github_headers(token="", accept="application/vnd.github+json"):\n    headers = {\n        "User-Agent": f"TorrentDashboard/{VERSION}",\n        "Accept": accept,\n        "X-GitHub-Api-Version": "2022-11-28",\n    }\n    token = str(token or "").strip()\n    if token and token != "<configured>":\n        headers["Authorization"] = f"Bearer {token}"\n    return headers\n''',
    '''def github_headers(accept="application/vnd.github+json"):\n    return {\n        "User-Agent": f"TorrentDashboard/{VERSION}",\n        "Accept": accept,\n        "X-GitHub-Api-Version": "2022-11-28",\n    }\n''',
    'GitHub headers',
)
dashboard = replace_once(
    dashboard,
    '''def github_update_headers(cfg, accept="application/vnd.github+json"):\n    integration = github_update_integration(cfg)\n    return github_headers(integration.get("token", ""), accept)\n''',
    '''def github_update_headers(cfg, accept="application/vnd.github+json"):\n    github_update_integration(cfg)\n    return github_headers(accept)\n''',
    'GitHub update headers',
)
dashboard = replace_once(
    dashboard,
    '''    except urllib.error.HTTPError as exc:\n        token = str(github_update_integration(cfg).get("token") or "").strip()\n        if exc.code in (401,403):\n            raise RuntimeError("GitHub rejected the update token. Verify that it has Contents: Read access to this repository.") from exc\n        if exc.code == 404 and not token:\n            raise RuntimeError("GitHub repository or releases were not found. If this repository is private, add a GitHub Update Token with Contents: Read access.") from exc\n        if exc.code == 404:\n            raise RuntimeError("GitHub repository or releases were not found, or the token cannot access them.") from exc\n        raise\n''',
    '''    except urllib.error.HTTPError as exc:\n        if exc.code in (401, 403):\n            raise RuntimeError("GitHub denied the request or the unauthenticated API rate limit was reached. Try again later.") from exc\n        if exc.code == 404:\n            raise RuntimeError("Public GitHub repository or releases were not found. Verify the repository name and published releases.") from exc\n        raise\n''',
    'GitHub release errors',
)
dashboard = replace_once(
    dashboard,
    '            result = test_github_update_access(item["repository"], item.get("token", ""))',
    '            result = test_github_update_access(item["repository"])',
    'GitHub integration test call',
)

dashboard = re.sub(
    r'def test_github_update_access\(repository: str, token: str = ""\):.*?\n\ndef fetch_update_release\(cfg\):',
    '''def test_github_update_access(repository: str):\n    repo = normalize_github_repository(repository)\n    cfg = {"integrations": [{"type": "github", "repository": repo, "enabled": True}]}\n    headers = github_headers()\n    try:\n        info = _urlopen_json(f"https://api.github.com/repos/{repo}", timeout=10, headers=headers)\n    except urllib.error.HTTPError as exc:\n        if exc.code in (401, 403):\n            raise RuntimeError("GitHub denied the connection or the unauthenticated API rate limit was reached. Try again later.") from exc\n        if exc.code == 404:\n            raise RuntimeError("Public GitHub repository not found. Verify the owner/repository value.") from exc\n        raise RuntimeError(f"GitHub connection failed with HTTP {exc.code}") from exc\n    except urllib.error.URLError as exc:\n        raise RuntimeError(f"Could not connect to GitHub: {exc.reason}") from exc\n\n    if bool(info.get("private", False)):\n        raise RuntimeError("Torrent Dashboard updates require a public GitHub repository")\n\n    result = {\n        "ok": True,\n        "repository": str(info.get("full_name") or repo),\n        "private": False,\n        "defaultBranch": str(info.get("default_branch") or ""),\n        "latestRelease": "",\n        "clientZipPresent": False,\n        "sha256Available": False,\n    }\n    try:\n        release = _latest_github_release(cfg, repo)\n        result["latestRelease"] = str(release.get("tag_name") or release.get("name") or "")\n        asset = _find_dashboard_asset(release)\n        result["clientZipPresent"] = bool(asset)\n        if asset:\n            try:\n                _asset_sha256(asset)\n                result["sha256Available"] = True\n            except RuntimeError:\n                result["sha256Available"] = False\n    except RuntimeError as exc:\n        if "No GitHub release" not in str(exc):\n            raise\n    return result\n\n\ndef fetch_update_release(cfg):''',
    dashboard,
    count=1,
    flags=re.S,
)
if 'def test_github_update_access(repository: str):' not in dashboard:
    raise RuntimeError('GitHub test function replacement failed')

# Saving settings must never preserve a retired GitHub token from an older config.
dashboard = replace_once(
    dashboard,
    '''def save_config(cfg):\n    tmp = CONFIG_PATH.with_suffix(".tmp")\n    tmp.write_text(json.dumps(cfg, indent=2) + "\\n", encoding="utf-8")\n    tmp.replace(CONFIG_PATH)\n''',
    '''def save_config(cfg):\n    cfg = json.loads(json.dumps(cfg))\n    for integration in cfg.get("integrations", []):\n        if integration.get("type") == "github":\n            integration.pop("token", None)\n    cfg.setdefault("updates", {}).pop("github_token", None)\n    tmp = CONFIG_PATH.with_suffix(".tmp")\n    tmp.write_text(json.dumps(cfg, indent=2) + "\\n", encoding="utf-8")\n    tmp.replace(CONFIG_PATH)\n''',
    'config secret scrub',
)

write('dashboard.py', dashboard)

# ---------------------------------------------------------------------------
# Public repository README and ignore rules.
# ---------------------------------------------------------------------------
readme = r'''<div align="center">

# Torrent Dashboard

**A clean, self-hosted qBitTorrent dashboard built for desktop and mobile browsers.**

![Python](https://img.shields.io/badge/Python-3.13+-3776AB?logo=python&logoColor=white)
![qBitTorrent](https://img.shields.io/badge/qBitTorrent-Web%20API-2F67BA)
![Release](https://img.shields.io/github/v/release/CynicaGaming/TorrentDashboard?include_prereleases&label=pre-release)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey)

</div>

> [!NOTE]
> Torrent Dashboard is currently in **0.x prerelease development**. Features and configuration may change between builds.

## Overview

Torrent Dashboard provides a modern browser interface for monitoring and managing one or more qBitTorrent clients. It is designed to run locally or on a trusted network and remain usable on phones, tablets, and desktop displays.

### Highlights

- Live torrent status, progress, speed, ETA, ratio, and health information
- Responsive desktop and mobile interface
- qBitTorrent-style torrent context actions and details
- Multiple qBitTorrent client support
- Dashboard authentication with Administrator and Standard User roles
- Trusted network-interface and IP/CIDR access controls
- Modular integrations for media services and notification destinations
- Browser notifications and configurable completion sounds
- In-application prerelease updates from a **public GitHub repository**
- Single-instance protection and update rollback safeguards

## Quick Start

### Requirements

- Python **3.13 or newer**
- qBitTorrent with its **Web UI enabled**
- qBitTorrent 5.2+ is recommended when using Web API key authentication

### Windows

1. Download the latest `Torrent-Dashboard-X.Y.Z.zip` from GitHub Releases.
2. Extract the archive to a permanent folder.
3. Run `Start Dashboard.bat`.
4. Complete the First Run Setup wizard in your browser.

Torrent Dashboard listens on `0.0.0.0` so it can be reached from permitted devices on your network. The wizard detects the local address and lets you choose the dashboard port and trusted network interfaces.

## Configuration

Torrent Dashboard is configured through the First Run Setup wizard and **Settings** interface. A hand-edited example configuration is intentionally not shipped.

Runtime configuration is stored in `config.json`, while databases, uploaded sounds, update state, and backups are stored under `data/`. Both are ignored by Git and excluded from release packages.

Stored passwords, qBitTorrent API keys, integration API keys, tokens, and webhook URLs are redacted before settings data is returned to the browser. Existing secrets appear as a persistent mask and are preserved until explicitly replaced.

## Application Updates

Application updates are intentionally manual during prerelease development:

1. Add a **GitHub** integration under **Settings → Integrations**.
2. Enter the public repository as `owner/repository`.
3. Use **Test connection**.
4. Open **Application updates** and select **Check for updates**.

No GitHub access token is required or supported by the default updater. The updater reads public GitHub Release metadata, verifies the SHA-256 digest supplied by GitHub for the release asset, stages the update, restarts Torrent Dashboard, and rolls back if the new version fails its health check.

A release only needs the `Torrent-Dashboard-X.Y.Z.zip` asset. Separate checksum or update-manifest assets are not required.

## Security and Privacy

Torrent Dashboard is intended for self-hosted use. Keep qBitTorrent itself bound to localhost or an otherwise protected interface whenever possible and expose only Torrent Dashboard to trusted clients.

The repository intentionally excludes runtime configuration and data. The release process also runs a public-repository hygiene check that rejects common credential formats, private-key material, `.env` files, `config.json`, and runtime data if they are accidentally tracked.

If you discover a security issue, avoid posting credentials or sensitive exploit details in a public issue.

## Development

Development releases use semantic versions in the `0.x.x` range. GitHub prereleases are titled **Torrent Dashboard Pre-Release**; the version is carried by the Git tag and client ZIP so the updater can order releases correctly.

Pull requests and forks are welcome. Fork maintainers can adapt the updater or integration model for their own deployment requirements.
'''
write('README.md', readme)

write('.gitignore', '''# Runtime configuration and application data\nconfig.json\ndata/\n*.sqlite\n*.sqlite3\n*.db\n*.log\n\n# Local secrets and certificates\n.env\n.env.*\n*.pem\n*.key\n*.p12\n*.pfx\n\n# Python / build output\n__pycache__/\n*.pyc\n.venv/\nvenv/\nbuild/\ndist/\n*.spec\n\n# Editor / OS noise\n.vscode/\n.idea/\n.DS_Store\nThumbs.db\n''')

for obsolete in ('config.example.json', 'IMPLEMENTATION_STATUS.md'):
    path = ROOT / obsolete
    if path.exists():
        path.unlink()

# ---------------------------------------------------------------------------
# Permanent public-repository hygiene validation.
# ---------------------------------------------------------------------------
validator = r'''#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DISALLOWED_PATHS = {
    'config.json',
    'config.example.json',
    'IMPLEMENTATION_STATUS.md',
    '.env',
}
DISALLOWED_PREFIXES = ('data/', '.venv/', 'venv/', 'dist/', 'build/')
TEXT_SUFFIXES = {'.py','.js','.css','.html','.md','.json','.yml','.yaml','.toml','.ini','.cfg','.txt','.bat','.ps1','.sh','.webmanifest','.gitignore'}
PATTERNS = {
    'GitHub token': re.compile(r'\b(?:github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{30,})\b'),
    'AWS access key': re.compile(r'\bAKIA[0-9A-Z]{16}\b'),
    'private key material': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'Discord webhook credential': re.compile(r'https://(?:canary\.|ptb\.)?discord(?:app)?\.com/api/webhooks/\d{5,}/[A-Za-z0-9._-]{20,}'),
    'Slack webhook credential': re.compile(r'https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]+'),
    'qBitTorrent API key': re.compile(r'\bqbt_[A-Za-z0-9]{28}\b'),
}


def tracked_files():
    try:
        out = subprocess.check_output(['git','ls-files','-z'], cwd=ROOT)
        return [p.decode('utf-8') for p in out.split(b'\0') if p]
    except Exception:
        return [str(p.relative_to(ROOT)).replace('\\','/') for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.parts]


def is_text_path(path: Path):
    return path.name == '.gitignore' or path.suffix.lower() in TEXT_SUFFIXES


def main():
    failures=[]
    files=tracked_files()
    for rel in files:
        norm=rel.replace('\\','/')
        if norm in DISALLOWED_PATHS or any(norm.startswith(prefix) for prefix in DISALLOWED_PREFIXES):
            failures.append(f'disallowed tracked path: {norm}')
            continue
        path=ROOT/norm
        if not path.exists() or not is_text_path(path):
            continue
        try:
            text=path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            continue
        for label,pattern in PATTERNS.items():
            if pattern.search(text):
                failures.append(f'{label} pattern found in {norm}')
    if failures:
        raise SystemExit('Public repository hygiene check failed:\n- ' + '\n- '.join(sorted(set(failures))))
    print(f'Public repository hygiene check passed ({len(files)} tracked files scanned)')


if __name__=='__main__':
    main()
'''
write('release_tools/validate_public_repo.py', validator)

# Build packages only after both UI and public-repository validation.
builder = read('release_tools/build_release.py')
builder = replace_once(
    builder,
    '    runpy.run_path(str(ROOT/"release_tools"/"validate_ui_strings.py"),run_name="__main__")\n',
    '    runpy.run_path(str(ROOT/"release_tools"/"validate_ui_strings.py"),run_name="__main__")\n    runpy.run_path(str(ROOT/"release_tools"/"validate_public_repo.py"),run_name="__main__")\n',
    'release public validation',
)
write('release_tools/build_release.py', builder)

# Static cache/version revision.
html = read('static/index.html').replace('?v=0.5.16', '?v=0.5.17')
write('static/index.html', html)
sw = read('static/sw.js').replace('torrent-dashboard-v0516', 'torrent-dashboard-v0517').replace('?v=0.5.16', '?v=0.5.17')
write('static/sw.js', sw)

# CI validates the public-repository contract explicitly.
workflow = read('.github/workflows/release.yml')
workflow = replace_once(
    workflow,
    '          node --check static/settings.js\n',
    '          node --check static/settings.js\n          python release_tools/validate_public_repo.py\n',
    'CI public validator',
)
workflow = replace_once(
    workflow,
    "          assert {'discord','ntfy','generic_webhook'} <= set(dashboard.INTEGRATION_TYPES)\n",
    "          assert {'discord','ntfy','generic_webhook'} <= set(dashboard.INTEGRATION_TYPES)\n          assert [f['key'] for f in dashboard.INTEGRATION_TYPES['github']['fields']] == ['repository']\n",
    'CI GitHub field assertion',
)
workflow = replace_once(
    workflow,
    "          assert 'update-manifest.json' not in html\n",
    "          assert 'update-manifest.json' not in html\n          assert not pathlib.Path('config.example.json').exists()\n          assert not pathlib.Path('IMPLEMENTATION_STATUS.md').exists()\n          readme = pathlib.Path('README.md').read_text(encoding='utf-8')\n          assert 'No GitHub access token is required or supported' in readme\n          assert 'Private repositories require' not in readme\n",
    'CI public README assertions',
)
write('.github/workflows/release.yml', workflow)

# Final staging assertions.
assert 'VERSION = "0.5.17"' in read('dashboard.py')
assert 'Fine-grained token with Contents: Read' not in read('dashboard.py')
assert 'GitHub rejected the update token' not in read('dashboard.py')
assert not (ROOT/'config.example.json').exists()
assert not (ROOT/'IMPLEMENTATION_STATUS.md').exists()
assert (ROOT/'release_tools/validate_public_repo.py').exists()
print('Staged Torrent Dashboard 0.5.17 public repository cleanup')
