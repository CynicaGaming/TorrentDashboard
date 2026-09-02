#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"Missing migration anchor: {label}")
    return text.replace(old, new, 1)


# Version/cache boundary.
dashboard = read("dashboard.py")
dashboard = replace_once(dashboard, 'VERSION = "0.5.60"', 'VERSION = "0.5.61"', "dashboard version")

# Build a compact authoritative integrity history from the retained GitHub
# releases. This keeps SHA-256 values out of authored release-note metadata.
asset_anchor = '''def validate_update_repository(repository: str):\n'''
asset_helper = '''def _github_release_integrity(releases, limit=2):\n    rows=[]\n    for release in releases if isinstance(releases,list) else []:\n        if release.get("draft"):\n            continue\n        version=str(release.get("tag_name") or "").strip().lstrip("vV")\n        if not re.fullmatch(r"\\d+\\.\\d+\\.\\d+(?:[-+][0-9A-Za-z.-]+)?",version):\n            continue\n        asset=_find_dashboard_asset(release)\n        if not asset:\n            continue\n        try:\n            digest=_asset_sha256(asset)\n        except Exception:\n            continue\n        rows.append({\n            "version":version,\n            "sha256":digest,\n            "package":str(asset.get("name") or f"Torrent-Dashboard-{version}.zip"),\n            "publishedAt":str(release.get("published_at") or release.get("created_at") or ""),\n            "channel":"prerelease" if release.get("prerelease") else "stable",\n            "releaseUrl":str(release.get("html_url") or ""),\n        })\n        if len(rows)>=max(1,int(limit)):\n            break\n    return rows\n\n\ndef validate_update_repository(repository: str):\n'''
dashboard = replace_once(dashboard, asset_anchor, asset_helper, "GitHub release integrity helper")

old = '''def fetch_update_release(cfg):\n    repo = validate_update_repository(update_repository(cfg))\n    release=_latest_github_release(cfg,repo)\n'''
new = '''def fetch_update_release(cfg):\n    repo = validate_update_repository(update_repository(cfg))\n    releases=_github_releases(cfg,repo)\n    if not releases:\n        raise RuntimeError("No GitHub release was found for the configured repository")\n    release=releases[0]\n'''
dashboard = replace_once(dashboard, old, new, "reuse GitHub release list")

old = '''        "currentVersion":VERSION,\n    }\n    data["updateAvailable"]=is_newer_version(version)\n'''
new = '''        "currentVersion":VERSION,\n        "releaseHistory":_github_release_integrity(releases,2),\n    }\n    data["updateAvailable"]=is_newer_version(version)\n'''
dashboard = replace_once(dashboard, old, new, "manifest integrity history")

old = '''        if idx is None: entries.append(remote)\n        else: entries[idx]={**entries[idx],**{k:v for k,v in remote.items() if v}}\n    installed=installed_release_info()\n'''
new = '''        if idx is None: entries.append(remote)\n        else: entries[idx]={**entries[idx],**{k:v for k,v in remote.items() if v}}\n        for integrity in latest_manifest.get("releaseHistory") or []:\n            if not isinstance(integrity,dict):\n                continue\n            iv=str(integrity.get("version") or "").strip().lstrip("vV")\n            idx=next((i for i,x in enumerate(entries) if x.get("version")==iv),None)\n            if idx is None:\n                continue\n            digest=str(integrity.get("sha256") or "").strip().lower()\n            if re.fullmatch(r"[0-9a-f]{64}",digest):\n                entries[idx]={\n                    **entries[idx],\n                    "sha256":digest,\n                    "package":str(integrity.get("package") or entries[idx].get("package") or ""),\n                    "publishedAt":str(integrity.get("publishedAt") or entries[idx].get("publishedAt") or ""),\n                    "channel":str(integrity.get("channel") or entries[idx].get("channel") or ""),\n                }\n    installed=installed_release_info()\n'''
dashboard = replace_once(dashboard, old, new, "merge previous release integrity")
write("dashboard.py", dashboard)

# Frontend: merge the manifest digest even when the version already exists in
# bundled history, and place the integrity block after the patch-note content.
app = read("static/app.js")
app = replace_once(app, "const FRONTEND_BUILD='0.5.60';", "const FRONTEND_BUILD='0.5.61';", "frontend version")
old = '''    if(i>=0){const existing=entries[i];entries[i]={...existing,publishedAt:remote.publishedAt||existing.publishedAt,channel:remote.channel||existing.channel,notes:remote.notes||existing.notes,source:'github'}}\n'''
new = '''    if(i>=0){const existing=entries[i];entries[i]={...existing,publishedAt:remote.publishedAt||existing.publishedAt,channel:remote.channel||existing.channel,notes:remote.notes||existing.notes,sha256:remote.sha256||existing.sha256,package:remote.package||existing.package,source:'github'}}\n'''
app = replace_once(app, old, new, "frontend manifest integrity merge")
old = '''    const body=document.createElement('div');body.className=`update-release-body${open?'':' hidden'}`;\n    if(/^[0-9a-f]{64}$/i.test(String(entry.sha256||''))){\n      const integrity=document.createElement('div');integrity.className='update-release-integrity';\n      const integrityCopy=document.createElement('div');integrityCopy.className='update-release-integrity-copy';\n      const integrityLabel=document.createElement('span');integrityLabel.textContent='Package SHA-256';\n      const integrityHash=document.createElement('code');integrityHash.textContent=String(entry.sha256).toLowerCase();\n      integrityCopy.append(integrityLabel,integrityHash);\n      const copyButton=document.createElement('button');copyButton.type='button';copyButton.className='secondary small-btn update-hash-copy';copyButton.textContent='Copy';copyButton.title='Copy package SHA-256';\n      copyButton.addEventListener('click',async event=>{event.stopPropagation();try{await navigator.clipboard.writeText(integrityHash.textContent);toast('Package SHA-256 copied')}catch{toast('Could not copy SHA-256','error')}});\n      integrity.append(integrityCopy,copyButton);body.appendChild(integrity);\n    }\n    const notes=document.createElement('div');notes.className='update-release-notes';\n    const noteText=String(entry.notes||entry.summary||'No patch notes were recorded for this revision.').replace(/^##\\s+[^\\n]+\\n*/,'').trim();\n    renderPatchMarkdown(notes,noteText||entry.summary||'No patch notes were recorded for this revision.');body.appendChild(notes);\n'''
new = '''    const body=document.createElement('div');body.className=`update-release-body${open?'':' hidden'}`;\n    const notes=document.createElement('div');notes.className='update-release-notes';\n    const noteText=String(entry.notes||entry.summary||'No patch notes were recorded for this revision.').replace(/^##\\s+[^\\n]+\\n*/,'').trim();\n    renderPatchMarkdown(notes,noteText||entry.summary||'No patch notes were recorded for this revision.');body.appendChild(notes);\n    if(/^[0-9a-f]{64}$/i.test(String(entry.sha256||''))){\n      const integrity=document.createElement('div');integrity.className='update-release-integrity';\n      const integrityCopy=document.createElement('div');integrityCopy.className='update-release-integrity-copy';\n      const integrityLabel=document.createElement('span');integrityLabel.textContent='Package SHA-256';\n      const integrityHash=document.createElement('code');integrityHash.textContent=String(entry.sha256).toLowerCase();\n      integrityCopy.append(integrityLabel,integrityHash);\n      const copyButton=document.createElement('button');copyButton.type='button';copyButton.className='secondary small-btn update-hash-copy';copyButton.textContent='Copy';copyButton.title='Copy package SHA-256';\n      copyButton.addEventListener('click',async event=>{event.stopPropagation();try{await navigator.clipboard.writeText(integrityHash.textContent);toast('Package SHA-256 copied')}catch{toast('Could not copy SHA-256','error')}});\n      integrity.append(integrityCopy,copyButton);body.appendChild(integrity);\n    }\n'''
app = replace_once(app, old, new, "move integrity below notes")
write("static/app.js", app)

index = read("static/index.html").replace("0.5.60", "0.5.61")
write("static/index.html", index)
sw = read("static/sw.js").replace("torrent-dashboard-v0560", "torrent-dashboard-v0561").replace("0.5.60", "0.5.61")
write("static/sw.js", sw)

css = read("static/app.css")
css = replace_once(
    css,
    ".update-release-integrity{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:0 0 14px;",
    ".update-release-integrity{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:16px 0 0;",
    "integrity block bottom spacing",
)
write("static/app.css", css)

# Structured release metadata remains the source for notes/handoff, but hashes
# remain dynamic provenance data from GitHub or verified local packages.
notes_path = ROOT / "release_notes" / "releases.json"
metadata = json.loads(notes_path.read_text(encoding="utf-8"))
if any(str(x.get("version")) == "0.5.61" for x in metadata.get("releases", [])):
    raise RuntimeError("v0.5.61 release metadata already exists")
previous = metadata["releases"][-1]
entry = {
    "version": "0.5.61",
    "date": "2026-09-02",
    "status": "prerelease",
    "title": "Patch note integrity history fix",
    "summary": "Moves package integrity metadata below each patch-note body and backfills SHA-256 values for both displayed revisions from retained GitHub releases.",
    "highlights": [
        "Package SHA-256 now appears at the bottom of an expanded patch-note card, after the release notes.",
        "Update checks enrich both displayed revisions with authoritative GitHub ZIP digests instead of enriching only the newest release.",
        "The frontend also preserves SHA-256 and package fields when merging a matching GitHub manifest into bundled release history."
    ],
    "fixes": [
        "The immediately previous patch-note revision now receives its Package SHA-256 after an update check when the corresponding GitHub release is retained."
    ],
    "technical": [
        "fetch_update_release reuses one GitHub release-list response for latest-release selection and a two-entry integrity history, avoiding a second GitHub API request.",
        "SHA-256 values remain provenance metadata and are not copied into release_notes/releases.json."
    ],
    "validation": [
        "A pure release-integrity helper test verifies two retained GitHub releases produce two exact ZIP digests.",
        "local_release_history regression coverage verifies both latest and previous displayed revisions receive SHA-256 metadata.",
        "JavaScript syntax validation covers the reordered integrity block and corrected manifest merge."
    ],
    "known_issues": previous.get("known_issues", []),
    "architecture": previous.get("architecture", []),
    "decisions": list(previous.get("decisions", [])) + [
        "Populate historical package digests from retained GitHub release assets at update-check time rather than storing mutable package hashes in authored patch-note metadata."
    ],
    "next_steps": previous.get("next_steps", []),
}
metadata["releases"].append(entry)
notes_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

# Validate the actual transformed behavior without contacting GitHub.
subprocess.run([sys.executable, "-m", "py_compile", "dashboard.py"], cwd=ROOT, check=True)
subprocess.run(["node", "--check", "static/app.js"], cwd=ROOT, check=True)
code = r'''
import dashboard
sample = [
    {"tag_name":"v0.5.61","prerelease":True,"draft":False,"published_at":"2026-09-02T14:00:00Z","assets":[{"name":"Torrent-Dashboard-0.5.61.zip","digest":"sha256:" + "a"*64}]},
    {"tag_name":"v0.5.60","prerelease":True,"draft":False,"published_at":"2026-09-02T13:00:00Z","assets":[{"name":"Torrent-Dashboard-0.5.60.zip","digest":"sha256:" + "b"*64}]},
]
rows = dashboard._github_release_integrity(sample, 2)
assert [x["version"] for x in rows] == ["0.5.61", "0.5.60"]
assert rows[0]["sha256"] == "a"*64 and rows[1]["sha256"] == "b"*64
manifest = {
    "version":"0.5.61","title":"v0.5.61","publishedAt":"2026-09-02T14:00:00Z","channel":"prerelease","notes":"notes",
    "asset":{"name":"Torrent-Dashboard-0.5.61.zip","sha256":"a"*64},"releaseHistory":rows,
}
history = dashboard.local_release_history(manifest)
assert [x["version"] for x in history] == ["0.5.61", "0.5.60"]
assert history[0]["sha256"] == "a"*64
assert history[1]["sha256"] == "b"*64
'''
subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=True)
subprocess.run([sys.executable, "release_tools/generate_release_notes.py", "--version", "0.5.61"], cwd=ROOT, check=True)
print("Applied v0.5.61 patch-note integrity fixes")
