#!/usr/bin/env python3
"""Run reusable source, architecture, documentation, and unit-test validation.

This intentionally uses only the Python standard library so the same command can
run locally, in the development branch workflow, and in release packaging.
"""
from __future__ import annotations

import ast
import compileall
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / "torrent_dashboard"
TESTS_DIR = ROOT / "tests"


def fail(message: str) -> None:
    raise SystemExit(message)


def python_modules() -> list[Path]:
    modules = sorted(PACKAGE_DIR.glob("*.py"))
    if not modules:
        fail("torrent_dashboard package contains no Python modules")
    return modules


def validate_package_boundaries() -> None:
    for path in python_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if ast.get_docstring(tree) is None:
            fail(f"{path.relative_to(ROOT)} requires a module docstring")
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                if any(alias.name == "dashboard" for alias in node.names):
                    fail(f"{path.relative_to(ROOT)} must not import dashboard")
            elif isinstance(node, ast.ImportFrom) and node.module == "dashboard":
                fail(f"{path.relative_to(ROOT)} must not import dashboard")


def validate_dashboard_contract() -> None:
    path = ROOT / "dashboard.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))

    definitions: dict[str, int] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            definitions[node.name] = definitions.get(node.name, 0) + 1
    duplicates = sorted(name for name, count in definitions.items() if count > 1)
    if duplicates:
        fail("dashboard.py has duplicate top-level definitions: " + ", ".join(duplicates))

    direct_saves = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "save_config":
            direct_saves.append(getattr(node, "lineno", 0))
    if direct_saves:
        fail("dashboard.py must use mutate_config() instead of save_config(); calls at lines " + ", ".join(map(str, direct_saves)))

    if "from torrent_dashboard.users import" not in source:
        fail("dashboard.py must consume the extracted users module")
    if "from torrent_dashboard.config import" not in source:
        fail("dashboard.py must consume the extracted configuration module")
    if "from torrent_dashboard.integrations import" not in source:
        fail("dashboard.py must consume the extracted integrations module")
    if "from torrent_dashboard.release_provenance import" not in source:
        fail("dashboard.py must consume the extracted release provenance module")
    if "from torrent_dashboard.config_store import ConfigStore" not in source:
        fail("dashboard.py must use ConfigStore for configuration coordination")

    forbidden_ownership = (
        "def _load_config_unlocked",
        "def _save_config_unlocked",
        "def normalize_integration",
        "def redacted_integrations",
        "def normalize_github_repository",
        "INTEGRATION_TYPES = {",
        "def _version_key",
        "def _find_dashboard_asset",
        "def _asset_sha256",
        "def _github_release_integrity",
        "def _normalized_release_integrity",
        "def cached_release_integrity",
        "def write_release_integrity_cache",
        "def _release_info_payload",
        "def write_release_info",
        "def installed_release_info",
        "def _release_history_markdown",
        "def local_release_history",
    )
    leftovers = [marker for marker in forbidden_ownership if marker in source]
    if leftovers:
        fail("dashboard.py still owns extracted configuration/integration behavior: " + ", ".join(leftovers))
    if "CONFIG_STORE = ConfigStore(CONFIG_REPOSITORY.load, CONFIG_REPOSITORY.save)" not in source:
        fail("dashboard.py must coordinate ConfigRepository through ConfigStore")
    if "RELEASE_PROVENANCE = ReleaseProvenance(" not in source:
        fail("dashboard.py must compose ReleaseProvenance with runtime paths")


def app_version() -> str:
    source = (ROOT / "dashboard.py").read_text(encoding="utf-8")
    match = re.search(r'^VERSION\s*=\s*["\']([^"\']+)["\']', source, re.M)
    if not match:
        fail("Could not determine dashboard VERSION")
    return match.group(1)


def validate_frontend_version() -> None:
    version = app_version()
    html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    app_js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
    sw = (ROOT / "static" / "sw.js").read_text(encoding="utf-8")
    required = {
        "static/index.html build meta": f'<meta content="{version}" name="torrent-dashboard-build"/>',
        "static/index.html app.js": f'/static/app.js?v={version}',
        "static/index.html settings.js": f'/static/settings.js?v={version}',
        "static/index.html app.css": f'/static/app.css?v={version}',
        "static/index.html settings.css": f'/static/settings.css?v={version}',
        "static/app.js frontend build": f"const FRONTEND_BUILD='{version}';",
        "static/sw.js asset version": f"?v={version}",
    }
    sources = {
        "static/index.html build meta": html,
        "static/index.html app.js": html,
        "static/index.html settings.js": html,
        "static/index.html app.css": html,
        "static/index.html settings.css": html,
        "static/app.js frontend build": app_js,
        "static/sw.js asset version": sw,
    }
    missing = [label for label, needle in required.items() if needle not in sources[label]]
    if missing:
        fail("Frontend version synchronization failed: " + ", ".join(missing))
    cache_version = "v" + version.replace(".", "")
    if f"torrent-dashboard-{cache_version}" not in sw:
        fail("Service-worker cache version is not synchronized with VERSION")


def validate_documentation() -> None:
    required = (
        "README.md",
        "DEVELOPMENT.md",
        "ARCHITECTURE.md",
        "DESIGN_LANGUAGE.md",
        "TESTING.md",
        "PROJECT_STATE.md",
        "HANDOFF.md",
        "CHANGELOG.md",
        "development/current.json",
        "docs/decisions/README.md",
    )
    for name in required:
        if not (ROOT / name).is_file():
            fail(f"Required project documentation is missing: {name}")

    decisions = sorted((ROOT / "docs" / "decisions").glob("[0-9][0-9][0-9][0-9]-*.md"))
    if len(decisions) < 5:
        fail("Expected the baseline architectural decision records under docs/decisions")

    active = json.loads((ROOT / "development" / "current.json").read_text(encoding="utf-8"))
    if int(active.get("schema") or 0) != 1:
        fail("development/current.json must use schema 1")
    for field in ("status", "objective", "why", "next_action"):
        if not isinstance(active.get(field), str) or not active[field].strip():
            fail(f"development/current.json requires non-empty {field}")
    for field in ("acceptance_criteria", "decisions", "files", "blockers", "out_of_scope"):
        value = active.get(field)
        if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
            fail(f"development/current.json field {field} must be a list of non-empty strings")


def run_unit_tests() -> None:
    if not TESTS_DIR.is_dir():
        fail("tests directory is missing")
    root_text = str(ROOT)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    suite = unittest.defaultTestLoader.discover(str(TESTS_DIR), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        fail("Unit tests failed")


def print_metrics() -> None:
    paths = [ROOT / "dashboard.py", ROOT / "static" / "app.js", ROOT / "static" / "settings.js", *python_modules()]
    print("\nCode-health metrics")
    for path in paths:
        text = path.read_text(encoding="utf-8")
        lines = text.count("\n") + (0 if text.endswith("\n") else 1)
        print(f"  {path.relative_to(ROOT)}: {lines} lines, {len(text)} bytes")


def main() -> None:
    if not compileall.compile_dir(str(PACKAGE_DIR), quiet=1):
        fail("Python package compilation failed")
    for path in (ROOT / "dashboard.py", ROOT / "updater.py", ROOT / "release_tools" / "build_release.py", ROOT / "release_tools" / "generate_release_notes.py"):
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
    validate_package_boundaries()
    validate_dashboard_contract()
    validate_frontend_version()
    validate_documentation()
    run_unit_tests()
    print_metrics()
    print("Source validation OK")


if __name__ == "__main__":
    main()
