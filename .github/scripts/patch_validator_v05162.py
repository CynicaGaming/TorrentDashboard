from pathlib import Path

root = Path(__file__).resolve().parents[2]
path = root / "release_tools" / "validate_ui_strings.py"
text = path.read_text(encoding="utf-8")
old = "    assert 'id=\"pendingUserList\"' in html"
new = (
    "    assert 'id=\"pendingUsersCard\"' not in html and 'id=\"pendingUserList\"' not in html\n"
    "    assert 'id=\"userList\"' in html"
)
if old not in text:
    raise RuntimeError("Legacy pending-user-list browser contract was not found")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
