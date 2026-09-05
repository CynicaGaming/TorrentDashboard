#!/usr/bin/env python3
"""Build the Torrent Dashboard client ZIP for a GitHub prerelease."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import re
import runpy
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_TOP = {"config.json", "data", ".git", ".github", "dist", "__pycache__", "release-info.json"}

def app_version():
    text=(ROOT/"dashboard.py").read_text(encoding="utf-8")
    m=re.search(r'^VERSION\s*=\s*["\']([^"\']+)["\']',text,re.M)
    if not m: raise SystemExit("Could not determine VERSION from dashboard.py")
    return m.group(1)

def sha256(path: Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def include(path: Path):
    rel=path.relative_to(ROOT)
    if not rel.parts or rel.parts[0] in EXCLUDE_TOP: return False
    if "__pycache__" in rel.parts or path.suffix==".pyc": return False
    return path.is_file()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo",required=True)
    ap.add_argument("--tag",required=True)
    ap.add_argument("--output",default="dist")
    args=ap.parse_args()
    runpy.run_path(str(ROOT/"release_tools"/"validate_source.py"),run_name="__main__")
    runpy.run_path(str(ROOT/"release_tools"/"validate_ui_strings.py"),run_name="__main__")
    runpy.run_path(str(ROOT/"release_tools"/"validate_public_repo.py"),run_name="__main__")
    version=app_version(); tag_version=args.tag[1:] if args.tag.startswith("v") else args.tag
    if tag_version!=version: raise SystemExit(f"Tag {args.tag} does not match dashboard VERSION {version}")
    out=(ROOT/args.output).resolve();out.mkdir(parents=True,exist_ok=True)
    asset_name=f"Torrent-Dashboard-{version}.zip";asset_path=out/asset_name
    with zipfile.ZipFile(asset_path,"w",zipfile.ZIP_DEFLATED) as z:
        prefix=f"Torrent-Dashboard-{version}"
        for path in sorted(ROOT.rglob("*")):
            if include(path): z.write(path,arcname=f"{prefix}/{path.relative_to(ROOT)}")
    digest=sha256(asset_path)
    try:
        commit=os.environ.get("GITHUB_SHA") or subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    except Exception:
        commit=""
    release_info={
        "schema":1,
        "version":version,
        "package":asset_name,
        "sha256":digest,
        "repository":args.repo,
        "tag":args.tag,
        "commit":commit,
    }
    info_path=out/f"Torrent-Dashboard-{version}.release.json"
    info_path.write_text(json.dumps(release_info,indent=2)+"\n",encoding="utf-8")
    print(asset_path)
    print(info_path)
    print(f"SHA-256: {digest}")

if __name__=="__main__": main()
