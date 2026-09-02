#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def write(path, content):
    (ROOT / path).write_text(content, encoding="utf-8")


def replace_once(text, old, new, label):
    if old not in text:
        raise RuntimeError(f"Missing migration anchor: {label}")
    return text.replace(old, new, 1)


# Version/cache boundary.
dashboard = read("dashboard.py")
dashboard = replace_once(dashboard, 'VERSION = "0.5.59"', 'VERSION = "0.5.60"', "dashboard version")
dashboard = replace_once(
    dashboard,
    'UPDATE_STATE_PATH = DATA_DIR / "update-status.json"\n',
    'UPDATE_STATE_PATH = DATA_DIR / "update-status.json"\nRELEASE_INFO_PATH = APP_DIR / "release-info.json"\n',
    "release info path",
)

# Persist/read exact verified package metadata. The file is generated only from
# a verified GitHub asset digest; it is not authored into the ZIP itself.
anchor = '''def fetch_update_release(cfg):\n'''
helper = '''def _release_info_payload(version, package, sha256, repository="", release_url="", published_at="", channel="", commit=""):\n    digest=str(sha256 or "").strip().lower()\n    if not re.fullmatch(r"[0-9a-f]{64}",digest):\n        raise RuntimeError("Release package SHA-256 is invalid")\n    return {\n        "schema":1,\n        "version":str(version or "").strip().lstrip("vV"),\n        "package":str(package or "").strip(),\n        "sha256":digest,\n        "repository":str(repository or "").strip(),\n        "releaseUrl":str(release_url or "").strip(),\n        "publishedAt":str(published_at or "").strip(),\n        "channel":str(channel or "").strip(),\n        "commit":str(commit or "").strip(),\n    }\n\n\ndef write_release_info(path, info):\n    path=Path(path)\n    path.parent.mkdir(parents=True,exist_ok=True)\n    payload=_release_info_payload(\n        info.get("version"),info.get("package"),info.get("sha256"),info.get("repository"),\n        info.get("releaseUrl"),info.get("publishedAt"),info.get("channel"),info.get("commit"),\n    )\n    tmp=path.with_suffix(path.suffix+".tmp")\n    tmp.write_text(json.dumps(payload,indent=2)+"\\n",encoding="utf-8")\n    tmp.replace(path)\n    return payload\n\n\ndef installed_release_info():\n    try:\n        raw=json.loads(RELEASE_INFO_PATH.read_text(encoding="utf-8"))\n        info=_release_info_payload(\n            raw.get("version"),raw.get("package"),raw.get("sha256"),raw.get("repository"),\n            raw.get("releaseUrl"),raw.get("publishedAt"),raw.get("channel"),raw.get("commit"),\n        )\n        if info.get("version") != VERSION:\n            return {}\n        return info\n    except Exception:\n        return {}\n\n\ndef fetch_update_release(cfg):\n'''
dashboard = replace_once(dashboard, anchor, helper, "release info helpers")

# If a manually extracted build checks GitHub while it is still the latest
# release, opportunistically persist its authoritative package digest.
old = '''    data["updateAvailable"]=is_newer_version(version)\n    return data\n'''
new = '''    data["updateAvailable"]=is_newer_version(version)\n    if version == VERSION and not installed_release_info():\n        try:\n            write_release_info(RELEASE_INFO_PATH,_release_info_payload(\n                version,data["asset"]["name"],data["asset"]["sha256"],repo,data.get("releaseUrl",""),\n                data.get("publishedAt",""),data.get("channel",""),str(release.get("target_commitish") or ""),\n            ))\n        except Exception:\n            pass\n    return data\n'''
dashboard = replace_once(dashboard, old, new, "persist current release digest")

# Add package SHA-256 to local release cards when known from either the
# installed release record or the latest GitHub manifest.
old = '''        remote={"version":version,"title":str(latest_manifest.get("title") or f"Torrent Dashboard v{version}"),"summary":"","publishedAt":str(latest_manifest.get("publishedAt") or ""),"channel":str(latest_manifest.get("channel") or ""),"notes":str(latest_manifest.get("notes") or ""),"source":"github"}\n'''
new = '''        remote={"version":version,"title":str(latest_manifest.get("title") or f"Torrent Dashboard v{version}"),"summary":"","publishedAt":str(latest_manifest.get("publishedAt") or ""),"channel":str(latest_manifest.get("channel") or ""),"notes":str(latest_manifest.get("notes") or ""),"sha256":str((latest_manifest.get("asset") or {}).get("sha256") or ""),"package":str((latest_manifest.get("asset") or {}).get("name") or ""),"source":"github"}\n'''
dashboard = replace_once(dashboard, old, new, "remote release sha")
old = '''    try: entries.sort(key=lambda x:_version_key(x.get("version") or "0"),reverse=True)\n'''
new = '''    installed=installed_release_info()\n    if installed.get("version"):\n        idx=next((i for i,x in enumerate(entries) if x.get("version")==installed.get("version")),None)\n        if idx is not None:\n            entries[idx]={**entries[idx],"sha256":installed.get("sha256",""),"package":installed.get("package","")}\n    try: entries.sort(key=lambda x:_version_key(x.get("version") or "0"),reverse=True)\n'''
dashboard = replace_once(dashboard, old, new, "installed release sha")

# Once the ZIP has been verified, write release-info.json into the staged
# source so updater.py backs it up/restores it atomically with the application.
old = '''        source=safe_extract_zip(package,stage/"extracted")\n        payload={"state":"readyToInstall","version":version,"package":str(package),"source":str(source),"manifest":manifest,"sha256":got,"bytes":total}\n'''
new = '''        source=safe_extract_zip(package,stage/"extracted")\n        write_release_info(source/"release-info.json",_release_info_payload(\n            version,manifest["asset"]["name"],got,update_repository(cfg),manifest.get("releaseUrl",""),\n            manifest.get("publishedAt",""),manifest.get("channel",""),\n        ))\n        payload={"state":"readyToInstall","version":version,"package":str(package),"source":str(source),"manifest":manifest,"sha256":got,"bytes":total}\n'''
dashboard = replace_once(dashboard, old, new, "stage release info")
write("dashboard.py", dashboard)

# Recovery updater also creates the installed release record from the digest it
# independently verifies against GitHub before applying files.
updater = read("updater.py")
insert_anchor = '''def validate_staged_source(source: Path, expected_version: str):\n'''
insert = '''def write_staged_release_info(source: Path, version: str, asset: dict, sha256: str, repository: str, release: dict):\n    digest=str(sha256 or "").strip().lower()\n    if not re.fullmatch(r"[0-9a-f]{64}",digest):\n        raise RuntimeError("Release package SHA-256 is invalid")\n    payload={\n        "schema":1,\n        "version":str(version),\n        "package":str(asset.get("name") or f"Torrent-Dashboard-{version}.zip"),\n        "sha256":digest,\n        "repository":str(repository or ""),\n        "releaseUrl":str(release.get("html_url") or ""),\n        "publishedAt":str(release.get("published_at") or release.get("created_at") or ""),\n        "channel":"prerelease" if release.get("prerelease") else "stable",\n        "commit":str(release.get("target_commitish") or ""),\n    }\n    (source/"release-info.json").write_text(json.dumps(payload,indent=2)+"\\n",encoding="utf-8")\n    return payload\n\n\ndef validate_staged_source(source: Path, expected_version: str):\n'''
updater = replace_once(updater, insert_anchor, insert, "recovery release helper")
old = '''        source = extract_release(archive, tmp / "release")\n        validate_staged_source(source, version)\n\n        backup_root = data_dir / "update-backups" / f"pre-{version}-{int(time.time())}"\n'''
new = '''        source = extract_release(archive, tmp / "release")\n        validate_staged_source(source, version)\n        write_staged_release_info(source,version,asset,actual_digest,repository,release)\n\n        backup_root = data_dir / "update-backups" / f"pre-{version}-{int(time.time())}"\n'''
updater = replace_once(updater, old, new, "recovery verified info")
write("updater.py", updater)

# Release builder emits a sidecar manifest after the ZIP bytes are final. It
# explicitly excludes any release-info.json left by an installed working tree.
build = read("release_tools/build_release.py")
build = replace_once(build, "import hashlib\n", "import hashlib\nimport json\nimport os\nimport subprocess\n", "build imports")
build = replace_once(build, 'EXCLUDE_TOP = {"config.json", "data", ".git", ".github", "dist", "__pycache__"}', 'EXCLUDE_TOP = {"config.json", "data", ".git", ".github", "dist", "__pycache__", "release-info.json"}', "exclude installed release info")
old = '''    print(asset_path)\n    print(f"SHA-256: {sha256(asset_path)}")\n'''
new = '''    digest=sha256(asset_path)\n    try:\n        commit=os.environ.get("GITHUB_SHA") or subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()\n    except Exception:\n        commit=""\n    release_info={\n        "schema":1,\n        "version":version,\n        "package":asset_name,\n        "sha256":digest,\n        "repository":args.repo,\n        "tag":args.tag,\n        "commit":commit,\n    }\n    info_path=out/f"Torrent-Dashboard-{version}.release.json"\n    info_path.write_text(json.dumps(release_info,indent=2)+"\\n",encoding="utf-8")\n    print(asset_path)\n    print(info_path)\n    print(f"SHA-256: {digest}")\n'''
build = replace_once(build, old, new, "build release sidecar")
write("release_tools/build_release.py", build)

# Frontend release cards show full package SHA-256 with a copy control.
app = read("static/app.js")
app = replace_once(app, "const FRONTEND_BUILD='0.5.59';", "const FRONTEND_BUILD='0.5.60';", "frontend build")
old = '''    const remote={version,title:manifest.title||`Torrent Dashboard v${version}`,publishedAt:manifest.publishedAt||'',channel:manifest.channel||'',notes:manifest.notes||'',source:'github'};\n'''
new = '''    const remote={version,title:manifest.title||`Torrent Dashboard v${version}`,publishedAt:manifest.publishedAt||'',channel:manifest.channel||'',notes:manifest.notes||'',sha256:manifest.asset?.sha256||'',package:manifest.asset?.name||'',source:'github'};\n'''
app = replace_once(app, old, new, "frontend remote sha")
old = '''    const body=document.createElement('div');body.className=`update-release-body${open?'':' hidden'}`;\n    const noteText=String(entry.notes||entry.summary||'No patch notes were recorded for this revision.').replace(/^##\\s+[^\\n]+\\n*/,'').trim();\n    renderPatchMarkdown(body,noteText||entry.summary||'No patch notes were recorded for this revision.');\n'''
new = '''    const body=document.createElement('div');body.className=`update-release-body${open?'':' hidden'}`;\n    if(/^[0-9a-f]{64}$/i.test(String(entry.sha256||''))){\n      const integrity=document.createElement('div');integrity.className='update-release-integrity';\n      const integrityCopy=document.createElement('div');integrityCopy.className='update-release-integrity-copy';\n      const integrityLabel=document.createElement('span');integrityLabel.textContent='Package SHA-256';\n      const integrityHash=document.createElement('code');integrityHash.textContent=String(entry.sha256).toLowerCase();\n      integrityCopy.append(integrityLabel,integrityHash);\n      const copyButton=document.createElement('button');copyButton.type='button';copyButton.className='secondary small-btn update-hash-copy';copyButton.textContent='Copy';copyButton.title='Copy package SHA-256';\n      copyButton.addEventListener('click',async event=>{event.stopPropagation();try{await navigator.clipboard.writeText(integrityHash.textContent);toast('Package SHA-256 copied')}catch{toast('Could not copy SHA-256','error')}});\n      integrity.append(integrityCopy,copyButton);body.appendChild(integrity);\n    }\n    const notes=document.createElement('div');notes.className='update-release-notes';\n    const noteText=String(entry.notes||entry.summary||'No patch notes were recorded for this revision.').replace(/^##\\s+[^\\n]+\\n*/,'').trim();\n    renderPatchMarkdown(notes,noteText||entry.summary||'No patch notes were recorded for this revision.');body.appendChild(notes);\n'''
app = replace_once(app, old, new, "release hash renderer")
write("static/app.js", app)

index = read("static/index.html").replace("0.5.59", "0.5.60")
write("static/index.html", index)
sw = read("static/sw.js").replace("torrent-dashboard-v0559", "torrent-dashboard-v0560").replace("0.5.59", "0.5.60")
write("static/sw.js", sw)

css = read("static/app.css")
css += '''\n\n/* 0.5.60 release package integrity metadata. */\n.update-release-integrity{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:0 0 14px;padding:11px 12px;border:1px solid color-mix(in srgb,var(--accent) 22%,var(--border));border-radius:10px;background:color-mix(in srgb,var(--accent) 5%,var(--panel3))}.update-release-integrity-copy{display:grid;gap:5px;min-width:0}.update-release-integrity-copy>span{font-size:8px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted)}.update-release-integrity-copy code{display:block!important;padding:0!important;border:0!important;background:transparent!important;color:var(--text);font-size:9px;line-height:1.45;overflow-wrap:anywhere;word-break:break-all}.update-hash-copy{flex:0 0 auto;min-width:62px}.update-release-notes>p:first-child{margin:0 0 14px;padding:11px 12px;border:1px solid color-mix(in srgb,var(--border) 72%,transparent);border-radius:10px;background:var(--panel3);color:var(--text);font-size:10.5px}.update-release-notes h4,.update-release-notes h5{margin:15px 0 7px;color:var(--text);font-size:9px;text-transform:uppercase;letter-spacing:.07em}.update-release-notes p{margin:7px 0;color:var(--muted)}.update-release-notes ul{display:grid;gap:6px;margin:7px 0;padding:0;list-style:none}.update-release-notes li{position:relative;padding-left:14px;color:var(--muted)}.update-release-notes li::before{content:"";position:absolute;left:1px;top:.7em;width:5px;height:5px;border-radius:50%;background:color-mix(in srgb,var(--accent) 72%,var(--muted))}@media(max-width:620px){.update-release-integrity{align-items:flex-start;flex-direction:column}.update-hash-copy{width:100%}}\n'''
write("static/app.css", css)

# Add structured v0.5.60 release notes and regenerate durable handoff files.
meta_path = ROOT / "release_notes" / "releases.json"
meta = json.loads(meta_path.read_text(encoding="utf-8"))
if any(str(x.get("version")) == "0.5.60" for x in meta.get("releases", [])):
    raise RuntimeError("v0.5.60 release metadata already exists")
previous = next(x for x in meta["releases"] if str(x.get("version")) == "0.5.59")
entry = {
    "version": "0.5.60",
    "date": "2026-09-02",
    "status": "prerelease",
    "title": "Installed package integrity metadata",
    "summary": "Persists the verified release-package SHA-256 with installed builds and surfaces the exact package digest alongside patch notes.",
    "highlights": [
        "Settings → Updates shows Package SHA-256 for a release whenever authoritative package metadata is available, with a one-click Copy control.",
        "The normal updater writes release-info.json into the staged application only after the downloaded ZIP matches GitHub's published SHA-256.",
        "Recovery updates persist the same release metadata after independently verifying the GitHub asset digest.",
        "The release build emits a Torrent-Dashboard-<version>.release.json sidecar containing the final ZIP digest, version, repository, tag, and commit."
    ],
    "fixes": [],
    "technical": [
        "release-info.json is intentionally created after package verification rather than embedded in the ZIP, because embedding a ZIP's own final digest would change the ZIP and invalidate that digest.",
        "release_tools/build_release.py excludes any locally installed release-info.json so stale package metadata cannot leak into a future release.",
        "If a manually extracted build checks GitHub while it is still the latest release, the dashboard can opportunistically persist its authoritative GitHub package digest."
    ],
    "validation": [
        "CI validates that the generated sidecar SHA-256 exactly matches the final release ZIP.",
        "Python compilation covers normal and recovery update persistence paths.",
        "JavaScript syntax validation covers package-integrity rendering and copy behavior."
    ],
    "known_issues": [
        "A build installed by manually extracting a ZIP cannot know the ZIP's own digest until it obtains authoritative release metadata, because the archive cannot contain its own final hash."
    ],
    "architecture": list(previous.get("architecture", [])) + [
        "Installed release provenance is stored in root release-info.json and is replaced/rolled back with application files; release build provenance is also published as a sidecar JSON asset."
    ],
    "decisions": list(previous.get("decisions", [])) + [
        "Treat Package SHA-256 as release provenance metadata sourced only from the finalized GitHub asset or a verified local download, never as manually authored patch-note content."
    ],
    "next_steps": list(previous.get("next_steps", [])),
}
meta["releases"].append(entry)
meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
subprocess.run([sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", "0.5.60"], cwd=ROOT, check=True)

# Local acceptance checks before the workflow performs independent validation.
assert 'VERSION = "0.5.60"' in read("dashboard.py")
assert 'RELEASE_INFO_PATH = APP_DIR / "release-info.json"' in read("dashboard.py")
assert "def installed_release_info():" in read("dashboard.py")
assert "write_staged_release_info" in read("updater.py")
assert '"release-info.json"' in read("release_tools/build_release.py")
assert "Torrent-Dashboard-{version}.release.json" in read("release_tools/build_release.py")
assert "Package SHA-256" in read("static/app.js")
assert "torrent-dashboard-v0560" in read("static/sw.js")
assert "Installed package integrity metadata" in read("PROJECT_STATE.md")

print("Applied v0.5.60 package integrity metadata")
