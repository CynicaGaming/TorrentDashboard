from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "src" / "torrent_dashboard" / "backups.py"
text = path.read_text(encoding="utf-8")
old = '''    auth = merged.get("auth")
    if not isinstance(auth, dict):
        auth = {}
    current_auth = current_copy.get("auth") if isinstance(current_copy.get("auth"), dict) else {}
    for key in LEGACY_AUTH_IDENTITY_KEYS:
        if key in current_auth:
            auth[key] = current_auth[key]
        else:
            auth.pop(key, None)
    merged["auth"] = auth
'''
new = '''    had_auth = isinstance(merged.get("auth"), dict) or isinstance(current_copy.get("auth"), dict)
    auth = merged.get("auth") if isinstance(merged.get("auth"), dict) else {}
    current_auth = current_copy.get("auth") if isinstance(current_copy.get("auth"), dict) else {}
    for key in LEGACY_AUTH_IDENTITY_KEYS:
        if key in current_auth:
            auth[key] = current_auth[key]
        else:
            auth.pop(key, None)
    if had_auth:
        merged["auth"] = auth
    else:
        merged.pop("auth", None)
'''
if old not in text:
    raise SystemExit("Expected identity merge block was not found")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
