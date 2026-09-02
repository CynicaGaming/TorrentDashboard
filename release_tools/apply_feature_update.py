#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]
IMPL = Path(__file__).with_name("apply_feature_update_impl.py")

if not IMPL.exists():
    raise RuntimeError("Missing v0.5.45 feature implementation")

# Materialize the reviewed v0.5.45 feature first.
runpy.run_path(str(IMPL), run_name="__main__")

# qBitTorrent exposes torrents/saveMetadata as GET. Keep Torrent Dashboard's
# browser-facing endpoint POST+CSRF, but proxy the request to qBitTorrent using
# its actual method contract.
dashboard_path = ROOT / "dashboard.py"
dashboard = dashboard_path.read_text(encoding="utf-8")
old_save = '            status, body = self._request("POST", "/api/v2/torrents/saveMetadata", form={"source": source})\n'
new_save = '            path = "/api/v2/torrents/saveMetadata?" + urllib.parse.urlencode({"source": source})\n            status, body = self._request("GET", path)\n'
if dashboard.count(old_save) != 1:
    raise RuntimeError("Expected one qBitTorrent saveMetadata POST proxy")
dashboard = dashboard.replace(old_save, new_save, 1)
dashboard_path.write_text(dashboard, encoding="utf-8")

# qBitTorrent's own Add Torrent dialog exports fetched magnets by their original
# source URI. Parsed .torrent files use the cached torrent identifier instead.
app_path = ROOT / "static" / "app.js"
app = app_path.read_text(encoding="utf-8")
old_source = "async function saveAddTorrentMetadata(){const source=addMetadataState.source||addSingleSource();"
new_source = "async function saveAddTorrentMetadata(){const source=addMetadataState.mode==='file'?addMetadataState.source:addSingleSource();"
if app.count(old_source) != 1:
    raise RuntimeError("Expected one Add Torrent metadata export source expression")
app = app.replace(old_source, new_source, 1)
app_path.write_text(app, encoding="utf-8")

# Tighten the permanent release contract around both fixes.
validator_path = ROOT / "release_tools" / "validate_ui_strings.py"
validator = validator_path.read_text(encoding="utf-8")
marker = "    assert '/api/v2/torrents/saveMetadata' in dashboard_py\n"
addition = marker + "    assert 'self._request(\"GET\", path)' in dashboard_py\n    assert 'self._request(\"POST\", \"/api/v2/torrents/saveMetadata\"' not in dashboard_py\n    assert \"addMetadataState.mode==='file'?addMetadataState.source:addSingleSource()\" in app_js\n"
if validator.count(marker) != 1:
    raise RuntimeError("Expected one saveMetadata validator marker")
validator = validator.replace(marker, addition, 1)
validator_path.write_text(validator, encoding="utf-8")

# Do not ship the staging implementation helper.
IMPL.unlink()

# Final local contracts before the workflow's normal compile/Node/UI checks.
dashboard = dashboard_path.read_text(encoding="utf-8")
app = app_path.read_text(encoding="utf-8")
assert 'self._request("GET", path)' in dashboard
assert 'self._request("POST", "/api/v2/torrents/saveMetadata"' not in dashboard
assert "addMetadataState.mode==='file'?addMetadataState.source:addSingleSource()" in app
print("Corrected v0.5.45 saveMetadata method and export source lifecycle")
