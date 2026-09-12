#!/usr/bin/env python3
"""One-shot preparation of the v0.5.155 operations milestone."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.5.155"

RELEASE = {
    "version": VERSION,
    "date": "2026-09-11",
    "status": "prerelease",
    "title": "Operations reliability, encrypted backups, and system health",
    "summary": "Adds updater-ready release fallback, authenticated portable-backup encryption, scheduled maintenance, security auditing, system health, and centralized retention while keeping automation opt-in.",
    "highlights": [
        "Keeps auto-update usable while a new release is still assembling by skipping incomplete distribution assets and retaining the previous complete prerelease until both source and Windows packages are verified.",
        "Adds AES-256-GCM portable-backup encryption with password-derived keys, encrypted import/restore support, scheduled backups, and local-only handling of the backup encryption password.",
        "Adds opt-in automatic updates with local maintenance windows, pre-update backups, and the existing verified staging/rollback path.",
        "Adds a dedicated redacted security audit database plus an administrator-only System settings page for health, audit review, backup scheduling, update policy, and retention.",
        "Centralizes retention for history, stale torrent records, security-audit events, backup count, and staged update artifacts."
    ],
    "fixes": [
        "Prevents a partially published newest GitHub release from temporarily making updates unavailable to installations whose distribution asset has not finished uploading.",
        "Moves superseded-prerelease cleanup until after the Windows workflow verifies both updater ZIPs and their GitHub SHA-256 digests.",
        "Keeps backup-encryption credentials out of portable backup payloads and preserves the destination installation's local encryption secret across restores."
    ],
    "technical": [
        "Uses cryptography 50.0.1 for streaming AES-256-GCM with PBKDF2-HMAC-SHA256 password derivation; cryptography is lazy-loaded so an existing source install can still start before dependencies are refreshed.",
        "Adds runtime.py as a narrow operations adapter around the existing dashboard composition root; source launchers, source update restarts, the console entry point, and Dashboard.exe all route through this adapter.",
        "Adds audit.py, backup_crypto.py, backup_service.py, operations.py, ops_config.py, release_selection.py, and static/ops.js as focused operational boundaries.",
        "The Windows preview workflow now runs on pull requests without publishing release assets, providing a pre-merge PyInstaller build and Dashboard.exe/Recovery.exe/Updater.exe smoke test."
    ],
    "validation": [
        "Runs source validation on Ubuntu and Windows with Python 3.13 and 3.14 after installing declared project dependencies.",
        "Builds a real source updater ZIP during pull-request validation and validates generated documentation, browser contracts, JavaScript syntax, and public-repository hygiene.",
        "Adds unit coverage for AES-GCM round trips, tamper and wrong-password rejection, encryption-password portability boundaries, security-audit redaction/mirroring, backup scheduling, maintenance windows, retention, and incomplete-release fallback.",
        "Builds the compiled Windows package on the pull request and smoke-tests Dashboard.exe, Recovery.exe, and Updater.exe before merge."
    ],
    "known_issues": [
        "Backup encryption is opt-in; unencrypted portable backups can contain saved client and integration credentials and should be stored securely.",
        "Windows executables are not code-signed yet."
    ],
    "architecture": [
        "Operational maintenance remains layered around dashboard.py rather than expanding the existing HTTP composition root.",
        "Security audit data is stored separately from general history and redacts secret-looking detail fields before persistence.",
        "Automatic update and scheduled backup policies default to disabled so upgrades do not silently change automation behavior."
    ],
    "decisions": [
        "Prefer a standard maintained AEAD implementation over application-defined backup cryptography.",
        "Treat a release as updater-ready only when the distribution-specific ZIP has a finalized SHA-256 digest.",
        "Keep the previous complete prerelease available until the new source and Windows packages are both verified.",
        "Keep the backup encryption password local to each installation and exclude it from portable state."
    ],
    "next_steps": [
        {
            "priority": 1,
            "title": "Verify updater-visible v0.5.155 release",
            "detail": "After merge, confirm both source and Windows v0.5.155 ZIPs are attached with SHA-256 digests before the previous prerelease is retired, then verify an existing installation detects the new release."
        },
        {
            "priority": 2,
            "title": "Exercise scheduled operations on a long-running install",
            "detail": "Confirm scheduled encrypted backups, maintenance-window automatic updates, retention, audit entries, and System health behave correctly across normal service restarts."
        }
    ]
}

ACTIVE = {
    "schema": 1,
    "status": "release-candidate",
    "objective": "Merge and publish the v0.5.155 operations reliability milestone",
    "why": "TD-R001, TD-R002, TD-R003, TD-R004, TD-R008, TD-R016, and TD-R023 are implemented and need final versioned validation plus updater-visible release verification.",
    "acceptance_criteria": [
        "Ubuntu/Windows Python 3.13/3.14 source validation passes with declared dependencies installed.",
        "The pull-request source updater ZIP builds successfully.",
        "The pull-request Windows package builds and Dashboard.exe, Recovery.exe, and Updater.exe pass smoke tests.",
        "v0.5.155 frontend/service-worker build markers and generated documentation are synchronized.",
        "After merge, both source and Windows updater ZIPs are published with GitHub SHA-256 digests before the previous complete prerelease is removed."
    ],
    "decisions": [
        "Use AES-256-GCM from cryptography for portable-backup encryption.",
        "Keep automatic updates and scheduled backups disabled by default.",
        "Keep the previous complete prerelease available during new-release assembly.",
        "Use runtime.py as the operations adapter while dashboard.py remains the HTTP composition root."
    ],
    "files": [
        "src/torrent_dashboard/runtime.py",
        "src/torrent_dashboard/backup_crypto.py",
        "src/torrent_dashboard/backup_service.py",
        "src/torrent_dashboard/audit.py",
        "src/torrent_dashboard/operations.py",
        "src/torrent_dashboard/ops_config.py",
        "src/torrent_dashboard/release_selection.py",
        "static/ops.js",
        ".github/workflows/release.yml",
        ".github/workflows/windows-preview.yml",
        "release_notes/releases.json"
    ],
    "blockers": [],
    "out_of_scope": [
        "Multi-factor authentication, granular permissions, API tokens, SSO, cross-client migration, and unrelated torrent-management enhancements."
    ],
    "next_action": "Run the final v0.5.155 pull-request source matrix and compiled Windows smoke build; if green, mark PR #41 ready and merge, then verify both updater assets and digests are public."
}


def replace(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"Expected marker not found in {path}: {old}")
    target.write_text(text.replace(old, new), encoding="utf-8")


def main() -> None:
    source_path = ROOT / "release_notes" / "releases.json"
    source = json.loads(source_path.read_text(encoding="utf-8"))
    releases = [item for item in source.get("releases", []) if str(item.get("version")) != VERSION]
    source["releases"] = [RELEASE, *releases]
    source_path.write_text(json.dumps(source, indent=2) + "\n", encoding="utf-8")

    (ROOT / "development" / "current.json").write_text(json.dumps(ACTIVE, indent=2) + "\n", encoding="utf-8")
    replace("src/torrent_dashboard/__init__.py", '__version__ = "0.5.154"', '__version__ = "0.5.155"')
    replace("static/index.html", "0.5.154", "0.5.155")
    replace("static/app.js", "const FRONTEND_BUILD='0.5.154';", "const FRONTEND_BUILD='0.5.155';")
    replace("static/sw.js", "torrent-dashboard-v05154", "torrent-dashboard-v05155")
    replace("static/sw.js", "0.5.154", "0.5.155")

    subprocess.run(
        [sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", VERSION],
        cwd=ROOT,
        check=True,
    )


if __name__ == "__main__":
    main()
