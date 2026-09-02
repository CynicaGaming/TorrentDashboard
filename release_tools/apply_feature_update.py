#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


# Backend: persist authoritative release integrity so normal Settings loads can
# display the previous release hash without depending on browser-session state.
dashboard = read("dashboard.py")
dashboard = replace_once(dashboard, 'RELEASE_INFO_PATH = APP_DIR / "release-info.json"\n', 'RELEASE_INFO_PATH = APP_DIR / "release-info.json"\nRELEASE_INTEGRITY_CACHE_PATH = DATA_DIR / "release-integrity.json"\n', "release integrity cache path")
dashboard = replace_once(dashboard, 'VERSION = "0.5.61"', 'VERSION = "0.5.62"', "backend version")

anchor = '''    return rows\n\n\ndef validate_update_repository(repository: str):\n'''
cache_helpers = '''    return rows\n\n\ndef _normalized_release_integrity(rows, limit=20):\n    out=[]; seen=set()\n    for raw in rows if isinstance(rows,list) else []:\n        if not isinstance(raw,dict):\n            continue\n        version=str(raw.get("version") or "").strip().lstrip("vV")\n        digest=str(raw.get("sha256") or "").strip().lower()\n        if not re.fullmatch(r"\\d+\\.\\d+\\.\\d+(?:[-+][0-9A-Za-z.-]+)?",version):\n            continue\n        if not re.fullmatch(r"[0-9a-f]{64}",digest) or version in seen:\n            continue\n        seen.add(version)\n        out.append({\n            "version":version,\n            "sha256":digest,\n            "package":str(raw.get("package") or f"Torrent-Dashboard-{version}.zip"),\n            "publishedAt":str(raw.get("publishedAt") or ""),\n            "channel":str(raw.get("channel") or ""),\n            "releaseUrl":str(raw.get("releaseUrl") or ""),\n        })\n        if len(out)>=max(1,int(limit)):\n            break\n    return out\n\n\ndef cached_release_integrity():\n    try:\n        payload=json.loads(RELEASE_INTEGRITY_CACHE_PATH.read_text(encoding="utf-8"))\n        if not isinstance(payload,dict) or int(payload.get("schema") or 0) != 1:\n            return []\n        return _normalized_release_integrity(payload.get("releases") or [],20)\n    except Exception:\n        return []\n\n\ndef write_release_integrity_cache(rows):\n    clean=_normalized_release_integrity(rows,20)\n    if not clean:\n        return []\n    DATA_DIR.mkdir(parents=True,exist_ok=True)\n    payload={"schema":1,"repository":DEFAULT_UPDATE_REPOSITORY,"updatedAt":int(time.time()),"releases":clean}\n    tmp=RELEASE_INTEGRITY_CACHE_PATH.with_suffix(".tmp")\n    tmp.write_text(json.dumps(payload,indent=2)+"\\n",encoding="utf-8")\n    tmp.replace(RELEASE_INTEGRITY_CACHE_PATH)\n    return clean\n\n\ndef validate_update_repository(repository: str):\n'''
dashboard = replace_once(dashboard, anchor, cache_helpers, "release integrity cache helpers")

dashboard = replace_once(
    dashboard,
    '    data={\n        "version":version,\n',
    '    integrity_history=_github_release_integrity(releases,20)\n    data={\n        "version":version,\n',
    "integrity history collection",
)
dashboard = replace_once(dashboard, '        "releaseHistory":_github_release_integrity(releases,2),\n', '        "releaseHistory":integrity_history[:2],\n', "manifest integrity history")
dashboard = replace_once(
    dashboard,
    '    }\n    data["updateAvailable"]=is_newer_version(version)\n',
    '    }\n    try:\n        write_release_integrity_cache(integrity_history)\n    except Exception:\n        pass\n    data["updateAvailable"]=is_newer_version(version)\n',
    "persist release integrity cache",
)

cache_merge = '''    except Exception: entries=[]\n    for integrity in cached_release_integrity():\n        iv=str(integrity.get("version") or "").strip().lstrip("vV")\n        idx=next((i for i,x in enumerate(entries) if x.get("version")==iv),None)\n        if idx is None:\n            continue\n        digest=str(integrity.get("sha256") or "").strip().lower()\n        if re.fullmatch(r"[0-9a-f]{64}",digest):\n            entries[idx]={\n                **entries[idx],\n                "sha256":digest,\n                "package":str(integrity.get("package") or entries[idx].get("package") or ""),\n                "publishedAt":str(integrity.get("publishedAt") or entries[idx].get("publishedAt") or ""),\n                "channel":str(integrity.get("channel") or entries[idx].get("channel") or ""),\n            }\n    if isinstance(latest_manifest,dict) and latest_manifest.get("version"):\n'''
dashboard = replace_once(dashboard, '    except Exception: entries=[]\n    if isinstance(latest_manifest,dict) and latest_manifest.get("version"):\n', cache_merge, "merge cached integrity")
write("dashboard.py", dashboard)

# Frontend: opening Updates performs a silent, throttled GitHub refresh. The
# result immediately fills both displayed hashes and persists them server-side.
settings = read("static/settings.js")
settings = replace_once(
    settings,
    "  let clientSettingsServerId = '';\n",
    "  let clientSettingsServerId = '';\n  let updateIntegrityRefreshAt = 0;\n  let updateIntegrityRefreshPromise = null;\n",
    "settings refresh state",
)
settings = replace_once(
    settings,
    "    if (savebar) savebar.classList.toggle('hidden', !corePages.has(page));\n  }\n",
    "    if (savebar) savebar.classList.toggle('hidden', !corePages.has(page));\n    if (page === 'updates' && state.settings && typeof checkForUpdates === 'function') {\n      const now = Date.now();\n      if (!updateIntegrityRefreshPromise && now - updateIntegrityRefreshAt > 60000) {\n        updateIntegrityRefreshAt = now;\n        updateIntegrityRefreshPromise = Promise.resolve()\n          .then(() => checkForUpdates(true))\n          .catch(() => null)\n          .finally(() => { updateIntegrityRefreshPromise = null; });\n      }\n    }\n  }\n",
    "automatic update integrity refresh",
)
write("static/settings.js", settings)

# Synchronized build identifiers.
app = read("static/app.js")
app = replace_once(app, "const FRONTEND_BUILD='0.5.61';", "const FRONTEND_BUILD='0.5.62';", "frontend build")
write("static/app.js", app)

index = read("static/index.html")
if index.count("0.5.61") < 3:
    raise RuntimeError("index build identifiers were not found")
index = index.replace("0.5.61", "0.5.62")
write("static/index.html", index)

sw = read("static/sw.js")
if "torrent-dashboard-v0561" not in sw or sw.count("0.5.61") < 4:
    raise RuntimeError("service worker build identifiers were not found")
sw = sw.replace("torrent-dashboard-v0561", "torrent-dashboard-v0562").replace("0.5.61", "0.5.62")
write("static/sw.js", sw)

# Structured release metadata remains the source for user-facing notes and the
# durable project handoff. Package hashes remain runtime provenance data.
meta_path = ROOT / "release_notes" / "releases.json"
meta = json.loads(meta_path.read_text(encoding="utf-8"))
if any(str(item.get("version")) == "0.5.62" for item in meta.get("releases", [])):
    raise RuntimeError("v0.5.62 metadata already exists")
previous = next(item for item in reversed(meta["releases"]) if item.get("next_steps"))
meta["releases"].append({
    "version": "0.5.62",
    "date": "2026-09-02",
    "status": "prerelease",
    "title": "Persistent historical package integrity",
    "summary": "Makes the previous release's Package SHA-256 populate reliably by caching authoritative GitHub release digests and refreshing them automatically when the Updates page opens.",
    "highlights": [
        "Successful GitHub release lookups persist authoritative package digests to data/release-integrity.json.",
        "Normal Settings loads merge the persisted integrity cache into the two displayed patch-note revisions.",
        "Opening Settings → Updates silently refreshes release metadata at most once per minute, so historical SHA-256 values self-populate without requiring a manual Check for updates click."
    ],
    "fixes": [
        "The previous patch-note card no longer loses its SHA-256 when Settings is reloaded or opened in a new browser session after the remote metadata was fetched."
    ],
    "technical": [
        "The cache stores validated semantic versions and 64-character SHA-256 values only; invalid or incomplete rows are discarded on read and write.",
        "The existing installed release-info.json remains authoritative for the running build and overrides cached metadata for that version.",
        "The cache lives under data/ so it survives application updates without becoming authored release-note content."
    ],
    "validation": [
        "CI verifies release-integrity cache read/write normalization and confirms cached metadata populates the previous bundled release entry.",
        "JavaScript syntax validation covers the throttled automatic refresh path.",
        "Generated CHANGELOG.md and PROJECT_STATE.md must match the v0.5.62 structured metadata before publication."
    ],
    "known_issues": [
        "The first time an installation opens Updates with no prior integrity cache, GitHub must be reachable before a historical digest can be populated. Once fetched, the digest remains available from the local cache."
    ],
    "architecture": list(previous.get("architecture") or []) + [
        "Authoritative historical release digests are cached under data/release-integrity.json and merged into the locally bundled patch-note history."
    ],
    "decisions": list(previous.get("decisions") or []) + [
        "Persist remote release-integrity metadata under data/ so historical hashes remain available across browser sessions and application updates without treating hashes as authored patch-note fields."
    ],
    "next_steps": list(previous.get("next_steps") or []),
})
meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

subprocess.run([sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", "0.5.62"], cwd=ROOT, check=True)
subprocess.run([sys.executable, "-m", "py_compile", "dashboard.py", "updater.py"], cwd=ROOT, check=True)
subprocess.run(["node", "--check", "static/app.js"], cwd=ROOT, check=True)
subprocess.run(["node", "--check", "static/settings.js"], cwd=ROOT, check=True)

# Regression test the durable path without network access.
subprocess.run([sys.executable, "-c", r'''
import json, tempfile
from pathlib import Path
import dashboard

with tempfile.TemporaryDirectory() as td:
    dashboard.RELEASE_INTEGRITY_CACHE_PATH = Path(td) / "release-integrity.json"
    sha61 = "a" * 64
    rows = dashboard.write_release_integrity_cache([
        {"version":"0.5.61","sha256":sha61,"package":"Torrent-Dashboard-0.5.61.zip","channel":"prerelease"},
        {"version":"bad","sha256":"nope"},
    ])
    assert len(rows) == 1 and rows[0]["sha256"] == sha61
    assert dashboard.cached_release_integrity()[0]["version"] == "0.5.61"
    history = dashboard.local_release_history()
    prev = next(item for item in history if item["version"] == "0.5.61")
    assert prev["sha256"] == sha61

settings = Path("static/settings.js").read_text(encoding="utf-8")
assert "page === 'updates'" in settings
assert "checkForUpdates(true)" in settings
print("v0.5.62 integrity cache regression checks passed")
'''], cwd=ROOT, check=True)

print("Staged v0.5.62 persistent historical integrity metadata")
