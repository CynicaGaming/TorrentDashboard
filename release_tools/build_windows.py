#!/usr/bin/env python3
"""Build the Windows x64 package with Dashboard.exe, Recovery.exe and Updater.exe."""
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
    text = (ROOT / "src" / "torrent_dashboard" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*["\']([^"\']+)', text, re.M)
    if not match:
        raise RuntimeError("Could not determine __version__ from src/torrent_dashboard/__init__.py")
    return match.group(1)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    package = output / f"TorrentDashboard-Windows-{version}-x64"
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

    dashboard_bundle = spec_dist / "TorrentDashboard"
    if not dashboard_bundle.is_dir():
        raise RuntimeError("PyInstaller did not create the expected TorrentDashboard directory")
    shutil.copytree(dashboard_bundle, package)

    # Recovery and Updater are deliberately standalone one-file executables.
    # This keeps local recovery independent of Dashboard's _internal runtime and
    # lets Dashboard launch a detached Updater copy that can replace Updater.exe.
    for name in ("Recovery.exe", "Updater.exe"):
        source = spec_dist / name
        if not source.is_file():
            raise RuntimeError(f"PyInstaller did not create standalone {name}")
        shutil.copy2(source, package / name)

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

    managed_roots = [
        "Dashboard.exe",
        "Recovery.exe",
        "Updater.exe",
        "_internal",
        "static",
        "release_notes",
        "README.md",
        "CHANGELOG.md",
        "package-info.json",
    ]
    package_info = {
        "schema": 1,
        "version": version,
        "repository": args.repo,
        "tag": args.tag,
        "platform": "windows-x64",
        "executables": ["Dashboard.exe", "Recovery.exe", "Updater.exe"],
        "distribution": "windows-x64",
        "layout": "windows-bundle-v1",
        "managed_roots": managed_roots,
        "preview": True,
    }
    (package / "package-info.json").write_text(json.dumps(package_info, indent=2) + "\n", encoding="utf-8")

    archive = output / f"TorrentDashboard-Windows-{version}-x64.zip"
    if archive.exists():
        archive.unlink()
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
        for path in sorted(package.rglob("*")):
            if path.is_file():
                zipped.write(path, arcname=f"{package.name}/{path.relative_to(package)}")

    digest = sha256(archive)
    info_path = output / f"TorrentDashboard-Windows-{version}.release.json"
    info = dict(package_info)
    info.update({"package": archive.name, "sha256": digest})
    info_path.write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    print(archive)
    print(info_path)
    print(f"SHA-256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
