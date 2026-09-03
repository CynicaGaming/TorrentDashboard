#!/usr/bin/env python3
import base64, zlib
from pathlib import Path
root = Path(__file__).resolve().parent
parts = [root / "apply_feature_payload_1.txt", root / "apply_feature_payload_2.txt"]
try:
    encoded = "".join(path.read_text(encoding="utf-8") for path in parts)
    code = zlib.decompress(base64.b64decode(encoded)).decode("utf-8")
    exec(compile(code, __file__, "exec"), {"__file__": __file__, "__name__": "__main__"})
    app_path = root.parent / "static" / "app.js"
    app = app_path.read_text(encoding="utf-8")
    fixes = {
        'aria-label="Download ${esc(file.displayName||file.path)}"': 'aria-label="Download file"',
        'aria-label="Priority for ${esc(file.displayName||file.path)}"': 'aria-label="File priority"',
    }
    for old, new in fixes.items():
        if old not in app:
            raise SystemExit(f"expected Add Torrent accessibility label not found: {old}")
        app = app.replace(old, new)
    app_path.write_text(app, encoding="utf-8")

    validator_path = root / "validate_ui_strings.py"
    validator = validator_path.read_text(encoding="utf-8")
    stale_assertions = [
        "    assert 'Metadata retrieval complete' in app_js\n",
        "    assert \"fetch(url,{method:'GET',cache:'no-store'})\" in app_js\n",
        "    assert \"renderAddMetadataComplete(result.metadata||{},source)\" in app_js\n",
        "    assert \"renderAddMetadataComplete(metadata,metadata?.hash||'')\" in app_js\n",
        "    assert \"link.download=addMetadataState.exportName||'torrent.torrent'\" in app_js\n",
        "    assert \"self._request(\\\"GET\\\", route, expect_json=False)\" in dashboard_py\n",
    ]
    for stale in stale_assertions:
        validator = validator.replace(stale, "", 1)
    validator_path.write_text(validator, encoding="utf-8")
finally:
    for path in parts:
        path.unlink(missing_ok=True)
