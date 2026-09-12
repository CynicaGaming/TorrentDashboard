#!/usr/bin/env python3
"""Run reusable source, architecture, documentation, and unit-test validation."""
from __future__ import annotations

import ast
import compileall
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
PACKAGE_DIR = SRC_DIR / "torrent_dashboard"
TESTS_DIR = ROOT / "tests"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def fail(message: str) -> None:
    raise SystemExit(message)


def python_modules() -> list[Path]:
    modules = sorted(PACKAGE_DIR.glob("*.py"))
    if not modules:
        fail("src/torrent_dashboard contains no Python modules")
    return modules


def validate_package_boundaries() -> None:
    for path in python_modules():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if ast.get_docstring(tree) is None:
            fail(f"{path.relative_to(ROOT)} requires a module docstring")
        if path.name in {"dashboard.py"}:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                if any(alias.name in {"dashboard", "torrent_dashboard.dashboard"} for alias in node.names):
                    fail(f"{path.relative_to(ROOT)} must not import the dashboard composition root")
            elif isinstance(node, ast.ImportFrom) and node.module in {"dashboard", "torrent_dashboard.dashboard"}:
                fail(f"{path.relative_to(ROOT)} must not import the dashboard composition root")


def validate_dashboard_contract() -> None:
    path = PACKAGE_DIR / "dashboard.py"
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
    required = (
        "from torrent_dashboard.config import",
        "from torrent_dashboard.users import",
        "from torrent_dashboard.integrations import",
        "from torrent_dashboard.release_provenance import",
        "from torrent_dashboard.config_store import ConfigStore",
        "CONFIG_STORE = ConfigStore(CONFIG_REPOSITORY.load, CONFIG_REPOSITORY.save)",
        "RELEASE_PROVENANCE = ReleaseProvenance(",
        "VERSION = __version__",
    )
    missing = [marker for marker in required if marker not in source]
    if missing:
        fail("dashboard composition contract is incomplete: " + ", ".join(missing))
    forbidden = (
        "def _load_config_unlocked", "def _save_config_unlocked", "def normalize_integration",
        "def redacted_integrations", "def normalize_github_repository", "INTEGRATION_TYPES = {",
        "def _version_key", "def _find_dashboard_asset", "def _asset_sha256",
        "def _github_release_integrity", "def _normalized_release_integrity",
        "def cached_release_integrity", "def write_release_integrity_cache",
        "def _release_info_payload", "def write_release_info", "def installed_release_info",
        "def _release_history_markdown", "def local_release_history",
    )
    leftovers = [marker for marker in forbidden if marker in source]
    if leftovers:
        fail("dashboard.py still owns extracted behavior: " + ", ".join(leftovers))


def app_version() -> str:
    source = (PACKAGE_DIR / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', source, re.M)
    if not match:
        fail("Could not determine __version__ from src/torrent_dashboard/__init__.py")
    return match.group(1)


def validate_frontend_version() -> None:
    version = app_version()
    html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    app_js = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
    sw = (ROOT / "static" / "sw.js").read_text(encoding="utf-8")
    required = {
        "index build meta": f'<meta content="{version}" name="torrent-dashboard-build"/>',
        "index app.js": f'/static/app.js?v={version}',
        "index settings.js": f'/static/settings.js?v={version}',
        "index app.css": f'/static/app.css?v={version}',
        "index settings.css": f'/static/settings.css?v={version}',
        "app.js build": f"const FRONTEND_BUILD='{version}';",
        "sw asset version": f"?v={version}",
    }
    sources = {label: html for label in required}
    sources["app.js build"] = app_js
    sources["sw asset version"] = sw
    missing = [label for label, needle in required.items() if needle not in sources[label]]
    if missing:
        fail("Frontend version synchronization failed: " + ", ".join(missing))
    cache_version = "v" + version.replace(".", "")
    if f"torrent-dashboard-{cache_version}" not in sw:
        fail("Service-worker cache version is not synchronized with application version")


def validate_layout() -> None:
    required = (
        "pyproject.toml",
        "src/torrent_dashboard/__init__.py",
        "src/torrent_dashboard/dashboard.py",
        "src/torrent_dashboard/runtime.py",
        "src/torrent_dashboard/updater.py",
        "src/torrent_dashboard/recovery_tool.py",
    )
    for name in required:
        if not (ROOT / name).is_file():
            fail(f"Required src-layout file is missing: {name}")
    for retired in ("dashboard.py", "updater.py", "recovery_tool.py", "torrent_dashboard"):
        if (ROOT / retired).exists():
            fail(f"Legacy application path must be removed: {retired}")
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for entry in (
        'torrent-dashboard = "torrent_dashboard.runtime:main"',
        'torrent-dashboard-recovery = "torrent_dashboard.recovery_tool:main"',
        'torrent-dashboard-updater = "torrent_dashboard.updater:main"',
    ):
        if entry not in pyproject:
            fail(f"pyproject.toml is missing entry point: {entry}")


def validate_documentation() -> None:
    required = (
        "README.md", "DEVELOPMENT.md", "ARCHITECTURE.md", "DESIGN_LANGUAGE.md",
        "TESTING.md", "PROJECT_STATE.md", "HANDOFF.md", "CHANGELOG.md",
        "development/current.json", "docs/decisions/README.md",
    )
    for name in required:
        if not (ROOT / name).is_file():
            fail(f"Required project documentation is missing: {name}")
    decisions = sorted((ROOT / "docs" / "decisions").glob("[0-9][0-9][0-9][0-9]-*.md"))
    if len(decisions) < 5:
        fail("Expected baseline architectural decision records under docs/decisions")
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
    suite = unittest.defaultTestLoader.discover(str(TESTS_DIR), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        fail("Unit tests failed")


def print_metrics() -> None:
    paths = [PACKAGE_DIR / "dashboard.py", PACKAGE_DIR / "runtime.py", ROOT / "static" / "app.js", ROOT / "static" / "settings.js", *python_modules()]
    seen = set()
    print("\nCode-health metrics")
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        text = path.read_text(encoding="utf-8")
        lines = text.count("\n") + (0 if text.endswith("\n") else 1)
        print(f"  {path.relative_to(ROOT)}: {lines} lines, {len(text)} bytes")


def main() -> None:
    if not compileall.compile_dir(str(PACKAGE_DIR), quiet=1):
        fail("Python package compilation failed")
    for path in (
        PACKAGE_DIR / "dashboard.py", PACKAGE_DIR / "runtime.py", PACKAGE_DIR / "updater.py", PACKAGE_DIR / "recovery_tool.py",
        ROOT / "release_tools" / "build_release.py", ROOT / "release_tools" / "build_windows.py",
        ROOT / "release_tools" / "generate_release_notes.py",
    ):
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
    validate_layout()
    validate_package_boundaries()
    validate_dashboard_contract()
    validate_frontend_version()
    validate_documentation()
    run_unit_tests()
    print_metrics()
    print("Source validation OK")


if __name__ == "__main__":
    main()
