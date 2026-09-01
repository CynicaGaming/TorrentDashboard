#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

def read(path): return (ROOT/path).read_text(encoding='utf-8')
def write(path,text): (ROOT/path).write_text(text,encoding='utf-8')
def sub1(text,pattern,repl,label,flags=0):
    out,n=re.subn(pattern,lambda _m: repl,text,count=1,flags=flags)
    if n!=1: raise RuntimeError(f'{label}: expected 1 match, found {n}')
    return out

# Backend: public GitHub repositories only; no update token support.
d=read('dashboard.py')
d=d.replace('VERSION = "0.5.16"','VERSION = "0.5.17"',1)
d=sub1(d,r'\s*\{"key": "token", "label": "Access Token", "placeholder": "Fine-grained token with Contents: Read", "secret": True, "required": False\},\n','\n','remove GitHub token field')
d=sub1(d,r'    # 0\.5\.13 moves GitHub credentials into the modular Integrations system\..*?    merged\["updates"\] = \{\}\n', '''    # GitHub update configuration lives in Integrations. Since 0.5.17 the\n    # default updater supports public repositories only and does not retain\n    # legacy GitHub access tokens.\n    legacy_updates = raw.get("updates", {}) if isinstance(raw.get("updates"), dict) else {}\n    legacy_repo = str(legacy_updates.get("repository") or "").strip()\n    if legacy_repo and not any(item.get("type") == "github" for item in merged.get("integrations", [])):\n        payload = {"id": stable_record_id("integration", "github", legacy_repo), "type": "github", "name": "GitHub", "repository": legacy_repo, "enabled": True}\n        try:\n            merged.setdefault("integrations", []).append(normalize_integration(payload, payload))\n        except Exception:\n            pass\n    merged["updates"] = {}\n''','legacy GitHub block',re.S)
d=sub1(d,r'def github_headers\(token="", accept="application/vnd\.github\+json"\):.*?    return headers\n', '''def github_headers(accept="application/vnd.github+json"):\n    return {\n        "User-Agent": f"TorrentDashboard/{VERSION}",\n        "Accept": accept,\n        "X-GitHub-Api-Version": "2022-11-28",\n    }\n''','GitHub headers',re.S)
d=sub1(d,r'def github_update_headers\(cfg, accept="application/vnd\.github\+json"\):\n    integration = github_update_integration\(cfg\)\n    return github_headers\(integration\.get\("token", ""\), accept\)\n', '''def github_update_headers(cfg, accept="application/vnd.github+json"):\n    github_update_integration(cfg)\n    return github_headers(accept)\n''','GitHub update headers')
d=sub1(d,r'    except urllib\.error\.HTTPError as exc:\n        token = str\(github_update_integration\(cfg\)\.get\("token"\) or ""\)\.strip\(\)\n        if exc\.code in \(401,403\):.*?        raise\n    return \[r for r in \(releases or \[\]\) if not r\.get\("draft"\)\]', '''    except urllib.error.HTTPError as exc:\n        if exc.code in (401, 403):\n            raise RuntimeError("GitHub denied the request or the unauthenticated API rate limit was reached. Try again later.") from exc\n        if exc.code == 404:\n            raise RuntimeError("Public GitHub repository or releases were not found. Verify the repository name and published releases.") from exc\n        raise\n    return [r for r in (releases or []) if not r.get("draft")]''','GitHub release errors',re.S)
d=d.replace('result = test_github_update_access(item["repository"], item.get("token", ""))','result = test_github_update_access(item["repository"])',1)
d=sub1(d,r'def test_github_update_access\(repository: str, token: str = ""\):.*?\n\ndef fetch_update_release\(cfg\):', '''def test_github_update_access(repository: str):\n    repo = normalize_github_repository(repository)\n    cfg = {"integrations": [{"type": "github", "repository": repo, "enabled": True}]}\n    try:\n        info = _urlopen_json(f"https://api.github.com/repos/{repo}", timeout=10, headers=github_headers())\n    except urllib.error.HTTPError as exc:\n        if exc.code in (401, 403):\n            raise RuntimeError("GitHub denied the connection or the unauthenticated API rate limit was reached. Try again later.") from exc\n        if exc.code == 404:\n            raise RuntimeError("Public GitHub repository not found. Verify the owner/repository value.") from exc\n        raise RuntimeError(f"GitHub connection failed with HTTP {exc.code}") from exc\n    except urllib.error.URLError as exc:\n        raise RuntimeError(f"Could not connect to GitHub: {exc.reason}") from exc\n    if bool(info.get("private", False)):\n        raise RuntimeError("Torrent Dashboard updates require a public GitHub repository")\n    result={"ok":True,"repository":str(info.get("full_name") or repo),"private":False,"defaultBranch":str(info.get("default_branch") or ""),"latestRelease":"","clientZipPresent":False,"sha256Available":False}\n    try:\n        release=_latest_github_release(cfg,repo)\n        result["latestRelease"]=str(release.get("tag_name") or release.get("name") or "")\n        asset=_find_dashboard_asset(release)\n        result["clientZipPresent"]=bool(asset)\n        if asset:\n            try:\n                _asset_sha256(asset); result["sha256Available"]=True\n            except RuntimeError:\n                pass\n    except RuntimeError as exc:\n        if "No GitHub release" not in str(exc): raise\n    return result\n\n\ndef fetch_update_release(cfg):''','GitHub test function',re.S)
d=sub1(d,r'def save_config\(cfg\):\n    tmp = CONFIG_PATH\.with_suffix\("\.tmp"\)\n    tmp\.write_text\(json\.dumps\(cfg, indent=2\) \+ "\\n", encoding="utf-8"\)\n    tmp\.replace\(CONFIG_PATH\)\n', '''def save_config(cfg):\n    cfg = json.loads(json.dumps(cfg))\n    for integration in cfg.get("integrations", []):\n        if integration.get("type") == "github": integration.pop("token", None)\n    cfg.setdefault("updates", {}).pop("github_token", None)\n    tmp = CONFIG_PATH.with_suffix(".tmp")\n    tmp.write_text(json.dumps(cfg, indent=2) + "\\n", encoding="utf-8")\n    tmp.replace(CONFIG_PATH)\n''','save config scrub')
d=d.replace('{"key": "repository", "label": "Repository", "placeholder": "owner/repository", "required": True}', '{"key": "repository", "label": "Repository", "placeholder": "owner/repository (public)", "required": True}',1)
write('dashboard.py',d)

write('README.md', '''<div align="center">\n\n# Torrent Dashboard\n\n**A clean, self-hosted qBitTorrent dashboard built for desktop and mobile browsers.**\n\n![Python](https://img.shields.io/badge/Python-3.13+-3776AB?logo=python&logoColor=white)\n![qBitTorrent](https://img.shields.io/badge/qBitTorrent-Web%20API-2F67BA)\n![Release](https://img.shields.io/github/v/release/CynicaGaming/TorrentDashboard?include_prereleases&label=pre-release)\n![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey)\n\n</div>\n\n> [!NOTE]\n> Torrent Dashboard is currently in **0.x prerelease development**. Features and configuration may change between builds.\n\n## Overview\n\nTorrent Dashboard provides a modern browser interface for monitoring and managing one or more qBitTorrent clients. It is intended for local or trusted-network use and is designed for phones, tablets, and desktop displays.\n\n### Highlights\n\n- Live torrent status, progress, speed, ETA, ratio, and health information\n- Responsive desktop and mobile interface\n- qBitTorrent-style torrent context actions and details\n- Multiple qBitTorrent client support\n- Administrator and Standard User dashboard roles\n- Trusted network-interface and IP/CIDR access controls\n- Modular media-service and notification integrations\n- Browser notifications and configurable completion sounds\n- Manual in-application prerelease updates from a **public GitHub repository**\n- Single-instance protection and update rollback safeguards\n\n## Quick Start\n\n### Requirements\n\n- Python **3.13 or newer**\n- qBitTorrent with its **Web UI enabled**\n- qBitTorrent 5.2+ is recommended for Web API key authentication\n\n### Windows\n\n1. Download the latest `Torrent-Dashboard-X.Y.Z.zip` from GitHub Releases.\n2. Extract it to a permanent folder.\n3. Run `Start Dashboard.bat`.\n4. Complete the First Run Setup wizard.\n\nTorrent Dashboard listens on `0.0.0.0` so permitted devices on your network can reach it. The wizard detects the local address and lets you choose the dashboard port and trusted interfaces.\n\n## Configuration\n\nConfiguration is handled through the First Run Setup wizard and **Settings**. A hand-edited example configuration is intentionally not shipped.\n\nRuntime configuration is stored in `config.json`; databases, uploaded sounds, update state, and backups are stored under `data/`. Both are ignored by Git and excluded from release packages.\n\nStored passwords, qBitTorrent API keys, integration secrets, and webhook URLs are redacted before settings data is returned to the browser.\n\n## Application Updates\n\n1. Add a **GitHub** integration under **Settings → Integrations**.\n2. Enter the public repository as `owner/repository`.\n3. Select **Test connection**.\n4. Open **Application updates** and select **Check for updates**.\n\nNo GitHub access token is required or supported by the default updater. Torrent Dashboard reads public GitHub Release metadata, verifies GitHub's SHA-256 digest for the release asset, stages the update, restarts, and rolls back if the new version fails its health check.\n\nA release only needs `Torrent-Dashboard-X.Y.Z.zip`; separate checksum and update-manifest assets are not required.\n\n## Security and Privacy\n\nKeep qBitTorrent itself on localhost or another protected interface whenever possible and expose only Torrent Dashboard to trusted clients.\n\nThe repository intentionally excludes live configuration and runtime data. Release packaging also runs a public-repository hygiene check that rejects common credential formats, private-key material, `.env` files, `config.json`, and runtime data if they are accidentally tracked.\n\nIf you discover a security issue, do not post credentials or sensitive exploit details in a public issue.\n\n## Development\n\nDevelopment releases use semantic versions in the `0.x.x` range. GitHub prereleases are titled **Torrent Dashboard Pre-Release**; the version remains in the Git tag and ZIP name so the updater can order releases safely.\n\nPull requests and forks are welcome. Fork maintainers can adapt the updater or integration model for their own deployment requirements.\n''')

write('.gitignore','''# Runtime configuration and application data\nconfig.json\ndata/\n*.sqlite\n*.sqlite3\n*.db\n*.log\n\n# Local secrets and certificates\n.env\n.env.*\n*.pem\n*.key\n*.p12\n*.pfx\n\n# Python / build output\n__pycache__/\n*.pyc\n.venv/\nvenv/\nbuild/\ndist/\n*.spec\n\n# Editor / OS noise\n.vscode/\n.idea/\n.DS_Store\nThumbs.db\n''')
for name in ('config.example.json','IMPLEMENTATION_STATUS.md'):
    p=ROOT/name
    if p.exists(): p.unlink()

write('release_tools/validate_public_repo.py', r'''#!/usr/bin/env python3
import re, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BAD={'config.json','config.example.json','IMPLEMENTATION_STATUS.md','.env'}
PREFIX=('data/','.venv/','venv/','dist/','build/')
PATTERNS={
 'GitHub token':re.compile(r'\b(?:github_pat_[A-Za-z0-9_]{20,}|gh[pousr]_[A-Za-z0-9]{30,})\b'),
 'AWS access key':re.compile(r'\bAKIA[0-9A-Z]{16}\b'),
 'private key':re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
 'Discord webhook':re.compile(r'https://(?:canary\.|ptb\.)?discord(?:app)?\.com/api/webhooks/\d{5,}/[A-Za-z0-9._-]{20,}'),
 'Slack webhook':re.compile(r'https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]+'),
 'qBitTorrent API key':re.compile(r'\bqbt_[A-Za-z0-9]{28}\b'),
}
TEXT={'.py','.js','.css','.html','.md','.json','.yml','.yaml','.toml','.ini','.cfg','.txt','.bat','.ps1','.sh','.webmanifest'}
files=[x.decode() for x in subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).split(b'\0') if x]
fail=[]
for rel in files:
    rel=rel.replace('\\','/')
    if rel in BAD or any(rel.startswith(p) for p in PREFIX): fail.append('disallowed tracked path: '+rel); continue
    p=ROOT/rel
    if p.name!='.gitignore' and p.suffix.lower() not in TEXT: continue
    try: text=p.read_text(encoding='utf-8')
    except UnicodeDecodeError: continue
    for label,rx in PATTERNS.items():
        if rx.search(text): fail.append(f'{label} pattern found in {rel}')
if fail: raise SystemExit('Public repository hygiene check failed:\n- '+'\n- '.join(sorted(set(fail))))
print(f'Public repository hygiene check passed ({len(files)} tracked files scanned)')
''')

b=read('release_tools/build_release.py')
if 'validate_public_repo.py' not in b:
    b=b.replace('    runpy.run_path(str(ROOT/"release_tools"/"validate_ui_strings.py"),run_name="__main__")\n','    runpy.run_path(str(ROOT/"release_tools"/"validate_ui_strings.py"),run_name="__main__")\n    runpy.run_path(str(ROOT/"release_tools"/"validate_public_repo.py"),run_name="__main__")\n',1)
write('release_tools/build_release.py',b)
write('static/index.html',read('static/index.html').replace('?v=0.5.16','?v=0.5.17'))
write('static/sw.js',read('static/sw.js').replace('torrent-dashboard-v0516','torrent-dashboard-v0517').replace('?v=0.5.16','?v=0.5.17'))

assert 'VERSION = "0.5.17"' in read('dashboard.py')
assert 'Fine-grained token with Contents: Read' not in read('dashboard.py')
assert not (ROOT/'config.example.json').exists()
assert not (ROOT/'IMPLEMENTATION_STATUS.md').exists()
print('Staged Torrent Dashboard 0.5.17 public repository cleanup')
