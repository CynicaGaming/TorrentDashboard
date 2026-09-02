#!/usr/bin/env python3
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "153966b6a1591401bc7c7372f8ec7c58286d9a47"  # materialized v0.5.33 release source
TARGET_VERSION = "0.5.42"

# Restore the complete application/runtime surface to the last stable release.
# Keep only the newer out-of-band updater/launcher and release workflow so an
# installed 0.5.41 copy can move forward to this rollback release normally.
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
        ["git", "show", f"{BASELINE}:{path}"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
    )


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one {label} match, found {count}")
    return text.replace(old, new, 1)


# Materialize the known-good release files directly from Git history.
for rel in RESTORE:
    dest = ROOT / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(git_show(rel), encoding="utf-8")

# Forward-version only the minimum identifiers required for the updater and
# browser cache keys. Functional application code remains the v0.5.33 source.
dashboard = ROOT / "dashboard.py"
text = dashboard.read_text(encoding="utf-8")
text = replace_once(text, 'VERSION = "0.5.33"', f'VERSION = "{TARGET_VERSION}"', "dashboard version")
dashboard.write_text(text, encoding="utf-8")

index = ROOT / "static" / "index.html"
text = index.read_text(encoding="utf-8")
if "v=0.5.33" not in text:
    raise RuntimeError("Stable index.html does not contain v0.5.33 asset references")
index.write_text(text.replace("v=0.5.33", f"v={TARGET_VERSION}"), encoding="utf-8")

sw = ROOT / "static" / "sw.js"
text = sw.read_text(encoding="utf-8")
if "torrent-dashboard-v0533" not in text or "v=0.5.33" not in text:
    raise RuntimeError("Stable service worker does not contain the expected v0.5.33 cache identifiers")
text = text.replace("torrent-dashboard-v0533", "torrent-dashboard-v0542")
text = text.replace("v=0.5.33", f"v={TARGET_VERSION}")
sw.write_text(text, encoding="utf-8")

# Rollback integrity checks. These distinguish the stable UI/runtime from the
# later loading-regression work while allowing the version identifiers above.
app_js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
settings_js = (ROOT / "static" / "settings.js").read_text(encoding="utf-8")
html = index.read_text(encoding="utf-8")
dashboard_text = dashboard.read_text(encoding="utf-8")

assert f'VERSION = "{TARGET_VERSION}"' in dashboard_text
assert f'/static/app.js?v={TARGET_VERSION}' in html
assert f'/static/settings.js?v={TARGET_VERSION}' in html
assert f'/static/app.css?v={TARGET_VERSION}' in html
assert f'/static/settings.css?v={TARGET_VERSION}' in html
assert f'v={TARGET_VERSION}' in sw.read_text(encoding="utf-8")

# Later experimental workspace/recovery code must not survive in the app.
assert "fetch_torrent_metadata" not in dashboard_text
assert "/api/torrent-metadata/fetch" not in dashboard_text
assert "Metadata retrieval complete" not in app_js
assert "__tdMarkStartupStage" not in app_js
assert "__tdFetchDiagnostics" not in settings_js
assert "Frontend build mismatch" not in dashboard_text

# Recovery tooling is intentionally retained outside the stable app runtime.
assert (ROOT / "Update Dashboard.bat").exists()
assert "--github-update" in (ROOT / "updater.py").read_text(encoding="utf-8")

print(f"Applied v{TARGET_VERSION} forward rollback from stable v0.5.33 baseline {BASELINE}")
