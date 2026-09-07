#!/usr/bin/env python3
"""Build the Windows x64 preview package with Dashboard.exe, Recovery.exe and Updater.exe."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def app_version() -> str:
    text = (ROOT / "dashboard.py").read_text(encoding="utf-8")
    match = re.search(r'^VERSION\s*=\s*["\']([^"\']+)', text, re.M)
    if not match:
        raise RuntimeError("Could not determine VERSION from dashboard.py")
    return match.group(1)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def copy_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--output", default="dist-windows")
    args = parser.parse_args()

    if sys.platform != "win32":
        raise SystemExit("Windows packages must be built on Windows")

    version = app_version()
    tag_version = args.tag[1:] if args.tag.startswith("v") else args.tag
    if version != tag_version:
        raise SystemExit(f"Tag {args.tag} does not match dashboard VERSION {version}")

    output = (ROOT / args.output).resolve()
    work = output / "pyinstaller-work"
    spec_dist = output / "pyinstaller-dist"
    package = output / f"Torrent-Dashboard-{version}-windows-x64"
    for path in (work, spec_dist, package):
        if path.exists():
            shutil.rmtree(path)
    output.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--clean",
            "--noconfirm",
            str(ROOT / "release_tools" / "windows.spec"),
            "--workpath",
            str(work),
            "--distpath",
            str(spec_dist),
        ],
        cwd=ROOT,
        check=True,
    )

    built = spec_dist / "TorrentDashboard"
    if not built.is_dir():
        raise RuntimeError("PyInstaller did not create the expected TorrentDashboard directory")
    shutil.copytree(built, package)

    copy_tree(ROOT / "static", package / "static")
    copy_tree(ROOT / "release_notes", package / "release_notes")
    for filename in ("README.md", "CHANGELOG.md"):
        source = ROOT / filename
        if source.is_file():
            shutil.copy2(source, package / filename)

    required = [package / "Dashboard.exe", package / "Recovery.exe", package / "Updater.exe"]
    missing = [path.name for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"Compiled package is missing: {', '.join(missing)}")

    package_info = {
        "schema": 1,
        "version": version,
        "repository": args.repo,
        "tag": args.tag,
        "platform": "windows-x64",
        "executables": ["Dashboard.exe", "Recovery.exe", "Updater.exe"],
        "distribution": "preview",
    }
    (package / "package-info.json").write_text(json.dumps(package_info, indent=2) + "\n", encoding="utf-8")

    archive = output / f"Torrent-Dashboard-{version}-windows-x64.zip"
    if archive.exists():
        archive.unlink()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(package.rglob("*")):
            if path.is_file():
                zf.write(path, arcname=f"{package.name}/{path.relative_to(package)}")

    digest = sha256(archive)
    info_path = output / f"Torrent-Dashboard-{version}-windows-x64.release.json"
    info = dict(package_info)
    info.update({"package": archive.name, "sha256": digest})
    info_path.write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    print(archive)
    print(info_path)
    print(f"SHA-256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
