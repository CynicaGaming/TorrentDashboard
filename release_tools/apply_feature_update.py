#!/usr/bin/env python3
"""Finalize the v0.5.70 fork-safe development continuity increment."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.5.70"
PREVIOUS = "0.5.69"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def write(rel: str, content: str) -> None:
    (ROOT / rel).write_text(content, encoding="utf-8")


def replace_once(rel: str, old: str, new: str) -> None:
    text = read(rel)
    if text.count(old) != 1:
        raise RuntimeError(f"Expected exactly one occurrence in {rel}: {old!r}")
    write(rel, text.replace(old, new, 1))


replace_once("dashboard.py", f'VERSION = "{PREVIOUS}"', f'VERSION = "{VERSION}"')
index = read("static/index.html")
if index.count(PREVIOUS) < 5:
    raise RuntimeError("static/index.html did not contain the expected build references")
write("static/index.html", index.replace(PREVIOUS, VERSION))
replace_once("static/app.js", f"const FRONTEND_BUILD='{PREVIOUS}';", f"const FRONTEND_BUILD='{VERSION}';")
sw = read("static/sw.js").replace("torrent-dashboard-v0569", "torrent-dashboard-v0570").replace(PREVIOUS, VERSION)
write("static/sw.js", sw)

path = ROOT / "release_notes" / "releases.json"
data = json.loads(path.read_text(encoding="utf-8"))
project = data.setdefault("project", {})
project["canonical_repository"] = project.pop("repository", project.get("canonical_repository", "CynicaGaming/TorrentDashboard"))
project["upstream_development_branch"] = project.pop("development_branch", project.get("upstream_development_branch", "refactor/backend-modularization-users"))
project["upstream_prerelease_branch"] = project.pop("prerelease_branch", project.get("upstream_prerelease_branch", "prerelease/backend-modularization"))
project["upstream_pull_request"] = project.pop("pull_request", project.get("upstream_pull_request", 25))
principles = project.setdefault("principles", [])
fork_principle = "Keep public development continuity portable across forks; label canonical repository/branch/PR references as upstream context rather than local identity."
if fork_principle not in principles:
    principles.append(fork_principle)

previous = next((item for item in data.get("releases", []) if item.get("version") == PREVIOUS), None)
if not previous:
    raise RuntimeError(f"Missing previous release metadata for v{PREVIOUS}")

release = {
    "version": VERSION,
    "date": "2026-09-02",
    "status": "prerelease",
    "title": "Fork-safe development continuity",
    "summary": "Adds a public, fork-safe development continuity layer so a new developer or AI can recover both the last known-good release state and unfinished engineering intent without relying on prior chat history.",
    "highlights": [
        "Added DEVELOPMENT.md as the durable contributor and fork workflow, including validation, versioning, publication, generated-file, and definition-of-done guidance.",
        "Added TESTING.md with the automated baseline and a manual smoke-test matrix for setup, roles, torrent operations, details, Add Torrent, Settings, updates, recovery, and responsive behavior.",
        "Added development/current.json as a public-safe active-work record for objectives, acceptance criteria, decisions, blockers, scope, affected areas, and the exact next action.",
        "Added generated HANDOFF.md, combining the last documented release state with active development intent into one portable resume document.",
        "Added lightweight architectural decision records under docs/decisions/ so important rationale survives chats, maintainers, and forks.",
        "Canonical repository, branch, and PR references are now labeled as upstream context instead of being presented as the identity of every checkout."
    ],
    "fixes": [],
    "technical": [
        "release_tools/generate_release_notes.py now validates development/current.json and generates HANDOFF.md alongside PROJECT_STATE.md and CHANGELOG.md.",
        "Generated handoff files explicitly instruct forks to verify their own origin/branch before following upstream references.",
        "Forks can replace development/current.json with their own roadmap while retaining upstream release history and architectural decisions as lineage."
    ],
    "validation": [
        "Source validation requires the development, testing, handoff, active-work, and decision-record continuity files.",
        "Release-note validation fails when HANDOFF.md, PROJECT_STATE.md, or CHANGELOG.md is stale relative to their authored sources.",
        "Existing backend tests, UI contract validation, JavaScript syntax checks, and frontend/service-worker version synchronization remain release gates."
    ],
    "known_issues": [],
    "architecture": list(previous.get("architecture", [])) + [
        "Development continuity is split between released state (release_notes/releases.json), authored active work (development/current.json), generated HANDOFF.md, durable architecture/testing guides, and short architectural decision records."
    ],
    "decisions": list(previous.get("decisions", [])) + [
        "Treat canonical repository, branch, and pull-request references as upstream lineage rather than assumptions about a fork's local identity.",
        "Keep active work state public-safe and repository-focused; do not archive chat transcripts as development state.",
        "Use the same developer-oriented documentation for humans and AI rather than maintaining vendor-specific AI instructions."
    ],
    "next_steps": list(previous.get("next_steps", []))
}
data["releases"] = [item for item in data.get("releases", []) if item.get("version") != VERSION] + [release]
path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

subprocess.run(
    [sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", VERSION],
    cwd=ROOT,
    check=True,
)

print(f"Staged Torrent Dashboard v{VERSION} development continuity release")
