#!/usr/bin/env python3
"""Build the Torrent Dashboard editable source ZIP for a GitHub prerelease."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import runpy
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "src" / "torrent_dashboard" / "__init__.py"
EXCLUDE_TOP = {"config.json", "data", ".git", ".github", "dist", "dist-windows", "build", "__pycache__", "release-info.json", "package-info.json"}


def app_version():
    text = VERSION_FILE.read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', text, re.M)
    if not match:
        raise SystemExit("Could not determine __version__")
    return match.group(1)


def sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def include(path: Path):
    rel = path.relative_to(ROOT)
    if not rel.parts or rel.parts[0] in EXCLUDE_TOP:
        return False
    if "__pycache__" in rel.parts or path.suffix == ".pyc":
        return False
    return path.is_file()


def package_files(output: Path):
    """Yield package files without traversing excluded or output trees."""
    output = output.resolve()
    for current, directories, filenames in os.walk(ROOT, topdown=True):
        current_path = Path(current)
        relative = current_path.relative_to(ROOT)
        if not relative.parts:
            directories[:] = sorted(
                name
                for name in directories
                if name not in EXCLUDE_TOP and (current_path / name).resolve() != output
            )
        else:
            directories[:] = sorted(
                name
                for name in directories
                if name != "__pycache__" and (current_path / name).resolve() != output
            )
        for filename in sorted(filenames):
            path = current_path / filename
            resolved = path.resolve()
            if resolved == output or output in resolved.parents:
                continue
            if include(path):
                yield path


def compatibility_launchers(version: str) -> dict[str, str]:
    """Return release-only root launchers accepted by pre-src update staging.

    These files are never written into the repository source tree. They exist in
    the 0.5.146 source ZIP so an older dashboard that validates dashboard.py at
    the archive root can stage the package, restart through the legacy path, and
    immediately hand execution to the canonical src/torrent_dashboard package.
    """
    common = (
        "from pathlib import Path\n"
        "import sys\n\n"
        "_SRC = Path(__file__).resolve().parent / \"src\"\n"
        "if str(_SRC) not in sys.path:\n"
        "    sys.path.insert(0, str(_SRC))\n\n"
    )
    return {
        "dashboard.py": (
            "#!/usr/bin/env python3\n"
            "\"\"\"Legacy source-update compatibility launcher; maintained code lives under src/.\"\"\"\n"
            + common
            + f'VERSION = "{version}"\n'
            + "from torrent_dashboard.dashboard import main\n\n"
            + "if __name__ == \"__main__\":\n"
            + "    raise SystemExit(main())\n"
        ),
        "updater.py": (
            "#!/usr/bin/env python3\n"
            "\"\"\"Legacy updater launcher; maintained code lives under src/.\"\"\"\n"
            + common
            + "from torrent_dashboard.updater import main\n\n"
            + "if __name__ == \"__main__\":\n"
            + "    raise SystemExit(main())\n"
        ),
        "recovery_tool.py": (
            "#!/usr/bin/env python3\n"
            "\"\"\"Legacy recovery launcher; maintained code lives under src/.\"\"\"\n"
            + common
            + "from torrent_dashboard.recovery_tool import main\n\n"
            + "if __name__ == \"__main__\":\n"
            + "    raise SystemExit(main())\n"
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--output", default="dist")
    args = parser.parse_args()
    runpy.run_path(str(ROOT / "release_tools" / "validate_source.py"), run_name="__main__")
    runpy.run_path(str(ROOT / "release_tools" / "validate_ui_strings.py"), run_name="__main__")
    runpy.run_path(str(ROOT / "release_tools" / "validate_public_repo.py"), run_name="__main__")
    version = app_version()
    tag_version = args.tag[1:] if args.tag.startswith("v") else args.tag
    if tag_version != version:
        raise SystemExit(f"Tag {args.tag} does not match application version {version}")
    output = (ROOT / args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    asset_name = f"Torrent-Dashboard-{version}.zip"
    asset_path = output / asset_name
    prefix = f"Torrent-Dashboard-{version}"
    launchers = compatibility_launchers(version)
    package_info = {
        "schema": 1, "version": version, "repository": args.repo, "tag": args.tag,
        "distribution": "source", "layout": "src",
        "migration_remove": ["dashboard.py", "updater.py", "recovery_tool.py", "torrent_dashboard"],
        "compatibility_launchers": sorted(launchers),
    }
    with zipfile.ZipFile(asset_path, "w", zipfile.ZIP_DEFLATED) as zipped:
        for path in package_files(output):
            zipped.write(path, arcname=f"{prefix}/{path.relative_to(ROOT)}")
        for name, source in launchers.items():
            zipped.writestr(f"{prefix}/{name}", source)
        zipped.writestr(f"{prefix}/package-info.json", json.dumps(package_info, indent=2) + "\n")
    digest = sha256(asset_path)
    try:
        commit = os.environ.get("GITHUB_SHA") or subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        commit = ""
    info = {
        "schema": 1, "version": version, "package": asset_name, "sha256": digest,
        "repository": args.repo, "tag": args.tag, "commit": commit,
        "distribution": "source", "layout": "src",
    }
    info_path = output / f"Torrent-Dashboard-{version}.release.json"
    info_path.write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    print(asset_path)
    print(info_path)
    print(f"SHA-256: {digest}")


if __name__ == "__main__":
    main()
