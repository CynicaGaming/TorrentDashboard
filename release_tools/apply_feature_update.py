from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "release_tools" / "validate_ui_strings.py"
text = path.read_text(encoding="utf-8")
old = "assert '0.5.26 per-client qBitTorrent settings' in settings_css"
new = "assert '0.5.27 client settings facelift' in settings_css"
if text.count(old) != 1:
    raise RuntimeError(f"Expected exactly one stale client-settings validator, found {text.count(old)}")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
print("Updated v0.5.27 UI validator marker.")
