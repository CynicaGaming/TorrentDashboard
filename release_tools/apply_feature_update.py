#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "release_tools" / "validate_ui_strings.py"
text = path.read_text(encoding="utf-8")

replacements = [
    (
        '    dashboard_py = (ROOT / "dashboard.py").read_text(encoding="utf-8")\n',
        '    dashboard_py = (ROOT / "dashboard.py").read_text(encoding="utf-8")\n'
        '    users_py = (ROOT / "torrent_dashboard" / "users.py").read_text(encoding="utf-8")\n',
        "users module validator input",
    ),
    (
        "    assert 'MAX_AVATAR_BYTES = 4 * 1024 * 1024' in dashboard_py\n",
        "    assert 'MAX_AVATAR_BYTES = 4 * 1024 * 1024' in users_py\n",
        "avatar size contract",
    ),
    (
        "    assert 'def save_current_user_profile' in dashboard_py\n",
        "    assert 'def save_current_user_profile' in users_py\n",
        "profile save contract",
    ),
    (
        "    assert 'def change_current_user_password' in dashboard_py\n",
        "    assert 'def change_current_user_password' in users_py\n",
        "password change contract",
    ),
    (
        "    assert 'def store_user_avatar' in dashboard_py\n",
        "    assert 'def store_user_avatar' in users_py\n",
        "avatar storage contract",
    ),
    (
        "    assert '\"group\": existing.get(\"group\"),' in dashboard_py\n",
        "    assert '\"group\": existing.get(\"group\"),' in users_py\n",
        "self-service group preservation contract",
    ),
    (
        "    assert 'password_configured' in dashboard_py\n",
        "    assert 'password_configured' in users_py\n",
        "account password-configured contract",
    ),
]

for old, new, label in replacements:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one {label} match, found {count}")
    text = text.replace(old, new, 1)

path.write_text(text, encoding="utf-8")

# Confirm the refactor-aware validator and extracted user module both compile.
compile(path.read_text(encoding="utf-8"), str(path), "exec")
users_path = ROOT / "torrent_dashboard" / "users.py"
compile(users_path.read_text(encoding="utf-8"), str(users_path), "exec")
