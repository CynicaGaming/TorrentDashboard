#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_FROM = "0.5.62"
VERSION_TO = "0.5.63"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


# Keep dashboard.py as the composition root, but remove the stale-snapshot save
# compatibility wrapper now that all application writes use mutate_config().
dashboard = read("dashboard.py")
if f'VERSION = "{VERSION_FROM}"' not in dashboard:
    raise SystemExit(f"dashboard.py is not at v{VERSION_FROM}")
dashboard = replace_once(
    dashboard,
    "\ndef save_config(cfg):\n    return CONFIG_STORE.save(cfg)\n\n",
    "\n",
    "remove save_config compatibility wrapper",
)
dashboard = replace_once(
    dashboard,
    f'VERSION = "{VERSION_FROM}"',
    f'VERSION = "{VERSION_TO}"',
    "dashboard version",
)
write("dashboard.py", dashboard)

# Package modules should explain their responsibility at the module boundary.
config_store = read("torrent_dashboard/config_store.py")
if not config_store.startswith('"""'):
    config_store = (
        '"""Thread-safe coordination for configuration reads and mutations."""\n\n'
        + config_store
    )
write("torrent_dashboard/config_store.py", config_store)

users = read("torrent_dashboard/users.py")
if not users.startswith('"""'):
    users = (
        '"""User, account, password, and profile domain operations."""\n\n'
        + users
    )
write("torrent_dashboard/users.py", users)

# Release packages should run the reusable code-health validator in addition to
# the long-lived UI regression contract and public-repository hygiene check.
build_release = read("release_tools/build_release.py")
needle = '    runpy.run_path(str(ROOT/"release_tools"/"validate_ui_strings.py"),run_name="__main__")\n'
if 'validate_source.py' not in build_release:
    if needle not in build_release:
        raise SystemExit("build_release.py validation hook changed")
    build_release = build_release.replace(
        needle,
        '    runpy.run_path(str(ROOT/"release_tools"/"validate_source.py"),run_name="__main__")\n' + needle,
        1,
    )
write("release_tools/build_release.py", build_release)

# Synchronize frontend generation identifiers even though this maintenance
# release does not intentionally change user-facing behavior.
index_html = read("static/index.html")
if VERSION_FROM not in index_html:
    raise SystemExit("static/index.html build version was not found")
write("static/index.html", index_html.replace(VERSION_FROM, VERSION_TO))

app_js = read("static/app.js")
app_js = replace_once(
    app_js,
    f"const FRONTEND_BUILD='{VERSION_FROM}';",
    f"const FRONTEND_BUILD='{VERSION_TO}';",
    "frontend build",
)
write("static/app.js", app_js)

sw = read("static/sw.js")
if "torrent-dashboard-v0562" not in sw or VERSION_FROM not in sw:
    raise SystemExit("service-worker v0.5.62 identifiers were not found")
sw = sw.replace("torrent-dashboard-v0562", "torrent-dashboard-v0563").replace(VERSION_FROM, VERSION_TO)
write("static/sw.js", sw)

# Add one structured maintenance release. Generated documentation remains a
# deterministic projection of this source data.
notes_path = ROOT / "release_notes" / "releases.json"
notes = json.loads(notes_path.read_text(encoding="utf-8"))
releases = notes.setdefault("releases", [])
if any(str(item.get("version")) == VERSION_TO for item in releases):
    raise SystemExit(f"release metadata already contains v{VERSION_TO}")
previous = next((item for item in releases if str(item.get("version")) == VERSION_FROM), None)
if not previous:
    raise SystemExit(f"release metadata is missing v{VERSION_FROM}")

architecture = list(previous.get("architecture") or [])
architecture.extend([
    "ARCHITECTURE.md now documents module ownership, dependency direction, configuration transactions, testing, and the extraction roadmap.",
    "Reusable source validation lives in release_tools/validate_source.py and is intended to be shared by development and release workflows.",
])
decisions = list(previous.get("decisions") or [])
decisions.extend([
    "Run periodic maintenance checkpoints that improve tests, documentation, module boundaries, and release tooling without bundling unrelated product changes.",
    "Treat dashboard.py as the composition root; modules under torrent_dashboard must not import dashboard.py.",
    "Run standard-library unit tests and reusable architecture validation as part of release packaging, not only ad-hoc source-string assertions.",
])

releases.append({
    "version": VERSION_TO,
    "date": "2026-09-02",
    "status": "prerelease",
    "title": "Code health and release guardrails",
    "summary": "Adds a maintenance checkpoint for architecture documentation, reusable source validation, user-domain tests, and release-workflow consistency without intentionally changing dashboard behavior.",
    "highlights": [
        "Added ARCHITECTURE.md with explicit module ownership, dependency direction, configuration-transaction rules, testing guidance, and the next extraction boundaries.",
        "Added release_tools/validate_source.py so development and release automation can share architecture, version-synchronization, compilation, and unit-test checks.",
        "Added behavioral unit tests for password verification, username validation, duplicate users, last-administrator protection, self-service profile security, and password changes.",
        "Refreshed README development, Linux startup, update provenance, and local-secret guidance.",
    ],
    "fixes": [
        "Removed the unused dashboard save_config compatibility wrapper so stale-snapshot saves cannot quietly re-enter request code.",
        "Release packaging now runs the reusable source validator before building an artifact.",
    ],
    "technical": [
        "Package modules are required to have module docstrings and are prevented by validation from importing the dashboard composition root.",
        "Source validation rejects duplicate top-level dashboard definitions and any direct save_config() calls.",
        "Code-health metrics for dashboard.py, app.js, settings.js, and package modules are printed in validation logs to make growth visible during maintenance checkpoints.",
    ],
    "validation": [
        "Python package compilation and unittest discovery run through release_tools/validate_source.py.",
        "Existing UI regression contracts continue to run alongside the new architecture-focused checks.",
        "Frontend build metadata, static asset query versions, app.js build identity, and service-worker cache generation must remain synchronized.",
    ],
    "known_issues": [
        "dashboard.py and static/app.js remain larger than the intended steady-state architecture; this checkpoint adds guardrails before the next extraction rather than attempting multiple large refactors at once.",
    ],
    "architecture": architecture,
    "decisions": decisions,
    "next_steps": [
        {
            "priority": 1,
            "title": "Extract configuration normalization and persistence",
            "detail": "Move config defaults, migration, normalization, sanitization, and atomic persistence into a dedicated torrent_dashboard module while preserving ConfigStore as the transaction coordinator."
        },
        {
            "priority": 2,
            "title": "Split release/update provenance from dashboard.py",
            "detail": "Move GitHub release parsing, installed release metadata, and historical digest caching behind a cohesive backend module after configuration extraction is stable."
        },
        {
            "priority": 3,
            "title": "Expand request-level behavioral tests",
            "detail": "Add authorization, CSRF, setup, account-route, and configuration-mutation coverage around the extracted domain boundaries."
        },
        {
            "priority": 4,
            "title": "Harden secrets at rest",
            "detail": "After configuration ownership is isolated, add restrictive filesystem permissions and a cleaner separation between ordinary configuration and stored credentials."
        }
    ],
})
notes_path.write_text(json.dumps(notes, indent=2) + "\n", encoding="utf-8")

subprocess.run(
    [sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", VERSION_TO],
    cwd=ROOT,
    check=True,
)

# Validate the applied source, not only the transformation itself.
subprocess.run([sys.executable, str(ROOT / "release_tools" / "validate_source.py")], cwd=ROOT, check=True)
subprocess.run([sys.executable, str(ROOT / "release_tools" / "validate_ui_strings.py")], cwd=ROOT, check=True)
subprocess.run(
    [sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", VERSION_TO, "--check"],
    cwd=ROOT,
    check=True,
)
print(f"Applied Torrent Dashboard v{VERSION_TO} code-health checkpoint")
