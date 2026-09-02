#!/usr/bin/env python3
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "93b9b1dc978b44a7b3eea89c496a03af6c6bd14c"
TARGET_VERSION = "0.5.43"
RESTORE = (
    "dashboard.py",
    "static/app.js",
    "static/app.css",
    "static/index.html",
    "static/settings.js",
    "static/settings.css",
    "static/sw.js",
    "release_tools/validate_ui_strings.py",
)


def git_show(path: str) -> str:
    return subprocess.check_output(
        ["git", "show", f"{BASELINE}:{path}"], cwd=ROOT, text=True, encoding="utf-8"
    )


def main():
    for rel in RESTORE:
        dest = ROOT / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(git_show(rel), encoding="utf-8")

    dashboard = ROOT / "dashboard.py"
    text = dashboard.read_text(encoding="utf-8")
    if text.count('VERSION = "0.5.38"') != 1:
        raise RuntimeError("Expected v0.5.38 dashboard version in stable baseline")
    dashboard.write_text(text.replace('VERSION = "0.5.38"', f'VERSION = "{TARGET_VERSION}"', 1), encoding="utf-8")

    index = ROOT / "static" / "index.html"
    text = index.read_text(encoding="utf-8")
    if "v=0.5.38" not in text:
        raise RuntimeError("Expected v0.5.38 asset references in stable index")
    index.write_text(text.replace("v=0.5.38", f"v={TARGET_VERSION}"), encoding="utf-8")

    sw = ROOT / "static" / "sw.js"
    text = sw.read_text(encoding="utf-8")
    if "torrent-dashboard-v0538" not in text or "v=0.5.38" not in text:
        raise RuntimeError("Expected v0.5.38 service-worker identifiers")
    text = text.replace("torrent-dashboard-v0538", "torrent-dashboard-v0543").replace("v=0.5.38", f"v={TARGET_VERSION}")
    sw.write_text(text, encoding="utf-8")

    html = index.read_text(encoding="utf-8")
    app_js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
    dashboard_text = dashboard.read_text(encoding="utf-8")
    assert f'VERSION = "{TARGET_VERSION}"' in dashboard_text
    assert 'id="homeBrand"' in html and 'id="brandAddress"' in html
    assert 'qBitTorrent Control' not in html
    assert "state.me.lan_ip||'Local'" in app_js
    assert "$('#homeBrand').addEventListener('click',()=>setView('dashboard'))" in app_js
    assert "fetch_torrent_metadata" not in dashboard_text
    assert "/api/torrent-metadata/fetch" not in dashboard_text
    assert "Metadata retrieval complete" not in app_js
    assert "__tdMarkStartupStage" not in app_js
    assert "__tdFetchDiagnostics" not in (ROOT / "static" / "settings.js").read_text(encoding="utf-8")

    # Retain the out-of-band recovery updater introduced after the stable release.
    assert "--github-update" in (ROOT / "updater.py").read_text(encoding="utf-8")
    print(f"Restored true v0.5.38 application baseline as v{TARGET_VERSION}")


if __name__ == "__main__":
    main()
