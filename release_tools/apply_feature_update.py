#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_VERSION = "0.5.54"
TARGET_VERSION = "0.5.55"

USER_FUNCTIONS = {
    "hash_password",
    "verify_password",
    "user_display_name",
    "normalize_user",
    "public_user",
    "_profile_avatar_stem",
    "configured_user_avatar",
    "_validate_profile_avatar",
    "delete_user_avatar_files",
    "store_user_avatar",
    "remove_user_avatar",
    "save_current_user_profile",
    "change_current_user_password",
    "user_by_username",
    "user_by_id",
    "session_is_admin",
    "sync_legacy_auth",
    "save_user",
    "delete_user",
}

USER_ASSIGNMENTS = {
    "AVATAR_DIR",
    "MAX_AVATAR_BYTES",
    "PROFILE_AVATAR_TYPES",
    "USER_GROUPS",
}

USER_IMPORT = '''from torrent_dashboard.users import (
    AVATAR_DIR,
    MAX_AVATAR_BYTES,
    PROFILE_AVATAR_TYPES,
    USER_GROUPS,
    change_current_user_password,
    configured_user_avatar,
    delete_user,
    delete_user_avatar_files,
    hash_password,
    normalize_user,
    public_user,
    remove_user_avatar,
    save_current_user_profile,
    save_user,
    session_is_admin,
    store_user_avatar,
    sync_legacy_auth,
    user_by_id,
    user_by_username,
    user_display_name,
    verify_password,
)
'''


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one {label} match, found {count}")
    return text.replace(old, new, 1)


def assignment_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    targets = []
    if isinstance(node, ast.Assign):
        targets = node.targets
    elif isinstance(node, ast.AnnAssign):
        targets = [node.target]
    for target in targets:
        if isinstance(target, ast.Name):
            names.add(target.id)
    return names


def extract_user_domain_from_dashboard(text: str) -> str:
    if "from torrent_dashboard.users import (" in text:
        raise RuntimeError("User domain import already exists in dashboard.py")

    tree = ast.parse(text)
    ranges: list[tuple[int, int, str]] = []
    found_functions: set[str] = set()
    found_assignments: set[str] = set()

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in USER_FUNCTIONS:
            if node.end_lineno is None:
                raise RuntimeError(f"Could not determine source range for {node.name}")
            found_functions.add(node.name)
            ranges.append((node.lineno, node.end_lineno, node.name))
            continue
        names = assignment_names(node)
        matched = names & USER_ASSIGNMENTS
        if matched:
            if node.end_lineno is None:
                raise RuntimeError(f"Could not determine source range for {sorted(matched)}")
            found_assignments.update(matched)
            ranges.append((node.lineno, node.end_lineno, ", ".join(sorted(matched))))

    missing_functions = USER_FUNCTIONS - found_functions
    missing_assignments = USER_ASSIGNMENTS - found_assignments
    if missing_functions or missing_assignments:
        details = []
        if missing_functions:
            details.append("functions: " + ", ".join(sorted(missing_functions)))
        if missing_assignments:
            details.append("assignments: " + ", ".join(sorted(missing_assignments)))
        raise RuntimeError("Could not locate user-domain definitions in dashboard.py (" + "; ".join(details) + ")")

    lines = text.splitlines(keepends=True)
    for start, end, _ in sorted(ranges, reverse=True):
        del lines[start - 1 : end]
    text = "".join(lines)

    import_anchor = "from pathlib import Path\n"
    text = replace_once(text, import_anchor, import_anchor + "\n" + USER_IMPORT, "pathlib import anchor")

    # Keep the public dashboard module API stable while moving implementation
    # details into the package. Existing callers and release checks continue to
    # reference dashboard.normalize_user, dashboard.save_user, etc.
    tree = ast.parse(text)
    remaining_defs = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    duplicates = USER_FUNCTIONS & remaining_defs
    if duplicates:
        raise RuntimeError("User-domain definitions remain in dashboard.py: " + ", ".join(sorted(duplicates)))
    return text


def update_versions():
    dashboard = ROOT / "dashboard.py"
    text = dashboard.read_text(encoding="utf-8")
    text = replace_once(
        text,
        f'VERSION = "{EXPECTED_VERSION}"',
        f'VERSION = "{TARGET_VERSION}"',
        "dashboard version",
    )
    dashboard.write_text(text, encoding="utf-8")

    index = ROOT / "static" / "index.html"
    text = index.read_text(encoding="utf-8")
    if text.count(EXPECTED_VERSION) < 4:
        raise RuntimeError(f"Expected frontend references for {EXPECTED_VERSION}")
    index.write_text(text.replace(EXPECTED_VERSION, TARGET_VERSION), encoding="utf-8")

    app = ROOT / "static" / "app.js"
    text = app.read_text(encoding="utf-8")
    text = replace_once(
        text,
        f"const FRONTEND_BUILD='{EXPECTED_VERSION}';",
        f"const FRONTEND_BUILD='{TARGET_VERSION}';",
        "frontend build",
    )
    app.write_text(text, encoding="utf-8")

    sw = ROOT / "static" / "sw.js"
    text = sw.read_text(encoding="utf-8")
    expected_cache = "torrent-dashboard-v" + EXPECTED_VERSION.replace(".", "")
    target_cache = "torrent-dashboard-v" + TARGET_VERSION.replace(".", "")
    text = replace_once(text, expected_cache, target_cache, "service worker cache")
    if f"v={EXPECTED_VERSION}" not in text:
        raise RuntimeError(f"Expected service worker asset references for {EXPECTED_VERSION}")
    sw.write_text(text.replace(f"v={EXPECTED_VERSION}", f"v={TARGET_VERSION}"), encoding="utf-8")


def update_dashboard():
    users_module = ROOT / "torrent_dashboard" / "users.py"
    if not users_module.exists():
        raise RuntimeError("torrent_dashboard/users.py is missing")
    compile(users_module.read_text(encoding="utf-8"), str(users_module), "exec")

    dashboard = ROOT / "dashboard.py"
    text = dashboard.read_text(encoding="utf-8")
    text = extract_user_domain_from_dashboard(text)
    compile(text, str(dashboard), "exec")
    dashboard.write_text(text, encoding="utf-8")


def main():
    update_dashboard()
    update_versions()

    dashboard = (ROOT / "dashboard.py").read_text(encoding="utf-8")
    assert "from torrent_dashboard.users import (" in dashboard
    assert "def normalize_user(" not in dashboard
    assert "def save_current_user_profile(" not in dashboard
    assert "def change_current_user_password(" not in dashboard
    assert f'VERSION = "{TARGET_VERSION}"' in dashboard


if __name__ == "__main__":
    main()
