#!/usr/bin/env python3
"""Build Torrent Dashboard GitHub release assets."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_TOP = {"config.json", "data", ".git", ".github", "dist", "__pycache__"}


def app_version():
    text = (ROOT / "dashboard.py").read_text(encoding="utf-8")
    m = re.search(r'^VERSION\s*=\s*["\']([^"\']+)["\']', text, re.M)
    if not m:
        raise SystemExit("Could not determine VERSION from dashboard.py")
    return m.group(1)


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def include(path: Path):
    rel = path.relative_to(ROOT)
    if not rel.parts:
        return False
    if rel.parts[0] in EXCLUDE_TOP:
        return False
    if "__pycache__" in rel.parts or path.suffix == ".pyc":
        return False
    return path.is_file()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="GitHub owner/repo")
    ap.add_argument("--tag", required=True, help="Release tag, normally vX.Y.Z")
    ap.add_argument("--output", default="dist")
    ap.add_argument("--notes", default="")
    args = ap.parse_args()

    version = app_version()
    tag_version = args.tag[1:] if args.tag.startswith("v") else args.tag
    if tag_version != version:
        raise SystemExit(f"Tag {args.tag} does not match dashboard VERSION {version}")

    repo = args.repo.strip().removesuffix(".git")
    if repo.startswith("https://github.com/"):
        repo = repo[len("https://github.com/"):].strip("/")
    if repo.count("/") != 1:
        raise SystemExit("--repo must be owner/repo")

    out = (ROOT / args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    asset_name = f"Torrent-Dashboard-{version}.zip"
    asset_path = out / asset_name

    with zipfile.ZipFile(asset_path, "w", zipfile.ZIP_DEFLATED) as z:
        prefix = f"Torrent-Dashboard-{version}"
        for p in sorted(ROOT.rglob("*")):
            if include(p):
                z.write(p, arcname=f"{prefix}/{p.relative_to(ROOT)}")

    digest = sha256(asset_path)
    manifest = {
        "schema": 1,
        "app": "torrentDesk",
        "version": version,
        "channel": "stable",
        "publishedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "releaseUrl": f"https://github.com/{repo}/releases/tag/{args.tag}",
        "notes": args.notes,
        "asset": {
            "name": asset_name,
            "url": f"https://github.com/{repo}/releases/download/{args.tag}/{asset_name}",
            "sha256": digest,
            "size": asset_path.stat().st_size,
        },
        "preserve": ["config.json", "data/"],
    }
    manifest_path = out / "update-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (out / f"{asset_name}.sha256").write_text(f"{digest}  {asset_name}\n", encoding="utf-8")
    print(asset_path)
    print(manifest_path)


if __name__ == "__main__":
    main()
