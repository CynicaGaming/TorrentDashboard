#!/usr/bin/env python3
"""Stage v0.5.70 fork-safe development continuity documentation."""
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
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def replace_once(rel: str, old: str, new: str) -> None:
    text = read(rel)
    if text.count(old) != 1:
        raise RuntimeError(f"Expected exactly one occurrence in {rel}: {old!r}")
    write(rel, text.replace(old, new, 1))


# Synchronized application/frontend version.
replace_once("dashboard.py", f'VERSION = "{PREVIOUS}"', f'VERSION = "{VERSION}"')
index = read("static/index.html")
if index.count(PREVIOUS) < 5:
    raise RuntimeError("static/index.html did not contain the expected build references")
write("static/index.html", index.replace(PREVIOUS, VERSION))
replace_once("static/app.js", f"const FRONTEND_BUILD='{PREVIOUS}';", f"const FRONTEND_BUILD='{VERSION}';")
sw = read("static/sw.js")
sw = sw.replace("torrent-dashboard-v0569", "torrent-dashboard-v0570").replace(PREVIOUS, VERSION)
write("static/sw.js", sw)


GENERATOR = r'''#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "release_notes" / "releases.json"
ACTIVE_WORK = ROOT / "development" / "current.json"


def version_key(value: str):
    raw = str(value or "").strip().lstrip("vV")
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?", raw):
        raise RuntimeError(f"Invalid semantic version in release metadata: {value}")
    main, sep, suffix = raw.partition("-")
    nums = tuple(int(part) for part in main.split("."))
    return (*nums, 1 if not sep else 0, suffix.lower())


def clean_string_list(value, label: str):
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(x, str) and x.strip() for x in value):
        raise RuntimeError(f"{label} must be a list of non-empty strings")
    return [x.strip() for x in value]


def load_source():
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("releases"), list):
        raise RuntimeError("release_notes/releases.json must contain a releases array")
    seen = set()
    releases = []
    for raw in data["releases"]:
        if not isinstance(raw, dict):
            raise RuntimeError("Every release entry must be an object")
        version = str(raw.get("version") or "").strip().lstrip("vV")
        version_key(version)
        if version in seen:
            raise RuntimeError(f"Duplicate release metadata for v{version}")
        seen.add(version)
        summary = str(raw.get("summary") or "").strip()
        title = str(raw.get("title") or "").strip()
        if not summary or not title:
            raise RuntimeError(f"v{version} requires title and summary")
        item = dict(raw)
        item["version"] = version
        for field in ("highlights", "fixes", "technical", "validation", "known_issues", "architecture", "decisions"):
            item[field] = clean_string_list(item.get(field, []), f"v{version} field {field}")
        next_steps = item.get("next_steps", []) or []
        if not isinstance(next_steps, list):
            raise RuntimeError(f"v{version} next_steps must be a list")
        normalized_steps = []
        for step in next_steps:
            if not isinstance(step, dict):
                raise RuntimeError(f"v{version} next_steps entries must be objects")
            priority = int(step.get("priority") or 0)
            title_text = str(step.get("title") or "").strip()
            detail = str(step.get("detail") or "").strip()
            if priority < 1 or not title_text or not detail:
                raise RuntimeError(f"v{version} next_steps entries require priority, title, and detail")
            normalized_steps.append({"priority": priority, "title": title_text, "detail": detail})
        item["next_steps"] = sorted(normalized_steps, key=lambda x: x["priority"])
        releases.append(item)
    releases.sort(key=lambda x: version_key(x["version"]), reverse=True)
    project = data.get("project") if isinstance(data.get("project"), dict) else {}
    return project, releases


def load_active_work():
    if not ACTIVE_WORK.is_file():
        raise RuntimeError("development/current.json is required for development continuity")
    data = json.loads(ACTIVE_WORK.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or int(data.get("schema") or 0) != 1:
        raise RuntimeError("development/current.json must use schema 1")
    for field in ("status", "objective", "why", "next_action"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            raise RuntimeError(f"development/current.json requires non-empty {field}")
        data[field] = data[field].strip()
    for field in ("acceptance_criteria", "decisions", "files", "blockers", "out_of_scope"):
        data[field] = clean_string_list(data.get(field, []), f"development/current.json field {field}")
    return data


def canonical_repository(project):
    return str(project.get("canonical_repository") or project.get("repository") or "CynicaGaming/TorrentDashboard").strip()


def upstream_value(project, new_key, old_key):
    return str(project.get(new_key) or project.get(old_key) or "").strip()


def bullets(items):
    return "\n".join(f"- {item}" for item in items)


def render_release_body(item):
    lines = [f"## v{item['version']} — {item['title']}", "", item["summary"].strip()]
    sections = [
        ("What's changed", item["highlights"]),
        ("Fixes", item["fixes"]),
        ("Technical notes", item["technical"]),
        ("Validation", item["validation"]),
        ("Known issues", item["known_issues"]),
    ]
    for heading, values in sections:
        if values:
            lines.extend(["", f"### {heading}", "", bullets(values)])
    lines.append("")
    return "\n".join(lines)


def render_changelog(releases):
    lines = [
        "# Torrent Dashboard Changelog",
        "",
        "> Generated from `release_notes/releases.json`. Do not edit this file manually.",
        "",
    ]
    for item in releases:
        lines.extend([render_release_body(item).rstrip(), ""])
    return "\n".join(lines).rstrip() + "\n"


def render_project_state(project, releases):
    latest = releases[0]
    canonical = canonical_repository(project)
    dev_branch = upstream_value(project, "upstream_development_branch", "development_branch")
    prerelease_branch = upstream_value(project, "upstream_prerelease_branch", "prerelease_branch")
    upstream_pr = project.get("upstream_pull_request", project.get("pull_request"))
    lines = [
        "# Torrent Dashboard Project State",
        "",
        "> Generated from `release_notes/releases.json`. Do not edit this file manually.",
        "",
        "> **Fork note:** repository and branch references below describe the canonical upstream development line. Forks should verify their own origin, branch, and pull-request state before continuing work.",
        "",
        "## Current baseline",
        "",
        f"- Latest documented build: **v{latest['version']}** ({latest.get('status', 'unknown')})",
        f"- Canonical upstream: `{canonical}`",
    ]
    if dev_branch:
        lines.append(f"- Upstream development branch: `{dev_branch}`")
    if prerelease_branch:
        lines.append(f"- Upstream prerelease branch: `{prerelease_branch}`")
    if upstream_pr:
        lines.append(f"- Upstream active refactor PR: **#{upstream_pr}**")
    lines.extend(["", "### Latest release summary", "", latest["summary"]])

    if latest.get("architecture"):
        lines.extend(["", "## Architecture state", "", bullets(latest["architecture"])])
    if latest.get("decisions"):
        lines.extend(["", "## Current engineering decisions", "", bullets(latest["decisions"])])
    if project.get("principles"):
        lines.extend(["", "## Development principles", "", bullets([str(x).strip() for x in project["principles"] if str(x).strip()])])

    lines.extend(["", "## Recent work", ""])
    for item in releases[:5]:
        lines.extend([f"### v{item['version']} — {item['title']}", "", item["summary"], ""])
        if item["highlights"]:
            lines.extend([bullets(item["highlights"]), ""])

    lines.extend(["## What to do next", ""])
    if latest.get("next_steps"):
        for step in latest["next_steps"]:
            lines.append(f"{step['priority']}. **{step['title']}** — {step['detail']}")
    else:
        lines.append("No next steps are recorded in the latest release metadata.")

    if latest.get("known_issues"):
        lines.extend(["", "## Known issues", "", bullets(latest["known_issues"])])

    lines.extend([
        "",
        "## Handoff instructions for a new development session",
        "",
        "1. Read `HANDOFF.md` first for the combined released-state and active-work view.",
        "2. Verify the repository origin and current branch; do not assume the canonical upstream branch names exist in a fork.",
        "3. Review `development/current.json` for active engineering intent and `release_notes/releases.json` for released history.",
        "4. Read `DEVELOPMENT.md`, `ARCHITECTURE.md`, and `TESTING.md` before changing unfamiliar subsystems.",
        "5. Continue from the active work item unless the repository maintainer changes priorities.",
        "6. Keep public handoff files free of credentials, private infrastructure details, and conversation transcripts.",
        "",
    ])
    return "\n".join(lines)


def render_handoff(project, releases, active):
    latest = releases[0]
    canonical = canonical_repository(project)
    dev_branch = upstream_value(project, "upstream_development_branch", "development_branch")
    prerelease_branch = upstream_value(project, "upstream_prerelease_branch", "prerelease_branch")
    upstream_pr = project.get("upstream_pull_request", project.get("pull_request"))
    lines = [
        "# Torrent Dashboard Development Handoff",
        "",
        "> Generated from `release_notes/releases.json` and `development/current.json`. Do not edit this file manually.",
        "",
        "## Repository context",
        "",
        "This handoff is intentionally portable across public forks. Verify the current checkout's Git remote, branch, and open work before using upstream references as instructions.",
        "",
        f"- Canonical upstream: `{canonical}`",
        f"- Last documented upstream build: **v{latest['version']}** ({latest.get('status', 'unknown')})",
    ]
    if dev_branch:
        lines.append(f"- Upstream development branch: `{dev_branch}`")
    if prerelease_branch:
        lines.append(f"- Upstream prerelease branch: `{prerelease_branch}`")
    if upstream_pr:
        lines.append(f"- Upstream active PR: **#{upstream_pr}**")

    lines.extend([
        "",
        "## Last known-good state",
        "",
        latest["summary"],
        "",
        "The released-state details and recent history are in `PROJECT_STATE.md`; architectural constraints are in `ARCHITECTURE.md`.",
        "",
        "## Active development intent",
        "",
        f"- Status: **{active['status']}**",
        f"- Objective: **{active['objective']}**",
        f"- Why: {active['why']}",
    ])
    if active["acceptance_criteria"]:
        lines.extend(["", "### Acceptance criteria", "", bullets(active["acceptance_criteria"])])
    if active["decisions"]:
        lines.extend(["", "### Decisions already made", "", bullets(active["decisions"])])
    if active["files"]:
        lines.extend(["", "### Expected areas of change", "", bullets([f"`{item}`" for item in active["files"]])])
    if active["blockers"]:
        lines.extend(["", "### Blockers", "", bullets(active["blockers"])])
    else:
        lines.extend(["", "### Blockers", "", "None currently recorded."])
    if active["out_of_scope"]:
        lines.extend(["", "### Explicitly out of scope", "", bullets(active["out_of_scope"])])

    lines.extend([
        "",
        "## Exact next action",
        "",
        active["next_action"],
        "",
        "## Resume checklist",
        "",
        "1. Inspect `git remote -v`, `git status`, and the current branch/ref. In a fork, treat upstream branch/PR names only as historical context.",
        "2. Read `DEVELOPMENT.md`, `ARCHITECTURE.md`, `TESTING.md`, and any relevant records under `docs/decisions/`.",
        "3. Run `python release_tools/validate_source.py` before making changes so the inherited baseline is known-good.",
        "4. Compare the checkout against the last documented release and inspect any uncommitted or branch-only changes before continuing.",
        "5. Work from `development/current.json`; update it when scope, decisions, blockers, or the exact next action changes.",
        "6. Regenerate this file with `python release_tools/generate_release_notes.py --version <current-version>` whenever active work state changes.",
        "",
        "## Fork guidance",
        "",
        "- Forks may keep the canonical upstream reference for lineage while replacing `development/current.json` with their own active roadmap.",
        "- Forks are not required to use the upstream branch names, PR number, prerelease channel, or release cadence.",
        "- If a fork publishes its own updater releases, review its workflow branch triggers and configure Torrent Dashboard to use that fork's public release repository.",
        "- Do not place credentials, private network addresses, private incident details, or chat transcripts in public continuity files.",
        "",
    ])
    return "\n".join(lines)


def write_or_check(path: Path, content: str, check: bool):
    if check:
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current != content:
            raise RuntimeError(f"Generated file is stale: {path.relative_to(ROOT)}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Generate Torrent Dashboard release and handoff notes")
    parser.add_argument("--version", required=True)
    parser.add_argument("--release-body")
    parser.add_argument("--project-state", default="PROJECT_STATE.md")
    parser.add_argument("--handoff", default="HANDOFF.md")
    parser.add_argument("--changelog", default="CHANGELOG.md")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    project, releases = load_source()
    active = load_active_work()
    wanted = str(args.version).strip().lstrip("vV")
    release = next((item for item in releases if item["version"] == wanted), None)
    if not release:
        raise RuntimeError(f"No release metadata exists for v{wanted}")

    project_state = render_project_state(project, releases)
    handoff = render_handoff(project, releases, active)
    changelog = render_changelog(releases)
    write_or_check(ROOT / args.project_state, project_state, args.check)
    write_or_check(ROOT / args.handoff, handoff, args.check)
    write_or_check(ROOT / args.changelog, changelog, args.check)

    if args.release_body:
        path = ROOT / args.release_body
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_release_body(release), encoding="utf-8")

    print(f"Release metadata and handoff OK for v{wanted}")


if __name__ == "__main__":
    main()
'''
write("release_tools/generate_release_notes.py", GENERATOR)


DEVELOPMENT = r'''# Torrent Dashboard Development Guide

This document describes how to continue development safely in the canonical repository or in a public fork.

## Repository portability

Torrent Dashboard is a public project and may be forked. Documentation distinguishes **canonical upstream context** from the identity of the checkout you are currently working in.

Before making changes, verify your repository and branch with `git remote -v`, `git status`, and `git branch --show-current`. A fork is not required to use the canonical upstream branch names, pull requests, updater repository, or release cadence.

`PROJECT_STATE.md` records the last documented upstream release state. `development/current.json` records active engineering intent and is expected to diverge in forks. `HANDOFF.md` combines both into a portable resume document.

Never place credentials, private network addresses, private incident details, customer/user data, or conversation transcripts in these public files.

## Requirements

- Python 3.13 or newer
- Node.js for JavaScript syntax validation
- qBitTorrent with Web UI enabled for integration and manual smoke testing
- Git for normal contribution workflows

No Python framework or third-party runtime dependency is required for the dashboard itself.

## Development workflow

1. Verify the repository origin and current branch.
2. Read `HANDOFF.md` and `development/current.json` before starting unfamiliar work.
3. Read `ARCHITECTURE.md` and any relevant records under `docs/decisions/` before changing module boundaries.
4. Run the existing validation suite before editing so you know the inherited baseline is healthy.
5. Keep one development increment narrow enough to describe with explicit acceptance criteria.
6. Update `development/current.json` whenever the objective, decisions, blockers, affected areas, or exact next action changes.
7. Add structured release metadata only when an increment is ready to become a documented release.
8. Regenerate generated documentation and run the complete validation suite before publishing.

## Validation commands

Backend, architecture, documentation, and unit tests:

```bash
python release_tools/validate_source.py
```

User-interface contract audit:

```bash
python release_tools/validate_ui_strings.py
```

JavaScript syntax:

```bash
node --check static/app.js
node --check static/settings.js
```

Generated release/handoff consistency, where `X.Y.Z` is the current `dashboard.VERSION`:

```bash
python release_tools/generate_release_notes.py --version X.Y.Z --check
```

See `TESTING.md` for the manual smoke-test matrix that complements automation.

## Generated and authored project state

### Authored sources

- `release_notes/releases.json` — released history, engineering decisions, and prioritized post-release work.
- `development/current.json` — current/unfinished engineering intent. Keep it public-safe and concise.
- `ARCHITECTURE.md` — durable module ownership and dependency rules.
- `DESIGN_LANGUAGE.md` — durable interface/content rules.
- `TESTING.md` — automated and manual verification contract.
- `docs/decisions/` — short architectural decision records explaining why important choices were made.

### Generated files

- `CHANGELOG.md`
- `PROJECT_STATE.md`
- `HANDOFF.md`
- GitHub release bodies during publication

Do not manually edit generated files. Change their source data and regenerate them instead.

## Starting or changing active work

`development/current.json` uses schema 1 and contains:

- `status`
- `objective`
- `why`
- `acceptance_criteria`
- `decisions`
- `files`
- `blockers`
- `out_of_scope`
- `next_action`

A fork should replace this file with its own active intent once it diverges from upstream. Keeping the upstream version is fine when the fork is simply tracking upstream.

After changing active work state, regenerate `HANDOFF.md` using the current application version:

```bash
python release_tools/generate_release_notes.py --version X.Y.Z
```

## Versioning and release metadata

Torrent Dashboard currently uses semantic `0.x.x` prerelease versions. The version must remain synchronized across `dashboard.py`, frontend build metadata, asset query strings, and the service-worker cache. `release_tools/validate_source.py` enforces that contract.

Each published increment gets one entry in `release_notes/releases.json`. That entry is the source for the GitHub release body, changelog, and released-state handoff material.

## Canonical upstream branch model

The canonical upstream currently develops increments on `refactor/backend-modularization-users` and promotes validated commits to `prerelease/backend-modularization` for updater-visible prereleases. This is an upstream implementation detail, not a requirement for forks.

The workflows under `.github/workflows/` contain branch triggers. Fork maintainers who use different branch names or publication rules should review those triggers before enabling release automation.

## Fork release behavior

Forks can point **Settings → Updates** at their own public GitHub release repository. A fork that wants its build to default to its own repository can change `DEFAULT_UPDATE_REPOSITORY` in the configuration module.

A fork publishing updates should retain the same integrity guarantees unless it deliberately replaces the update architecture:

- validate source before packaging
- publish the finalized ZIP and provenance sidecar
- verify the ZIP SHA-256 before installation
- preserve runtime data during replacement
- retain rollback behavior

## Definition of done for an increment

An increment is ready to publish when:

- its acceptance criteria are satisfied
- relevant automated tests exist or have been updated
- `python release_tools/validate_source.py` passes
- UI and JavaScript validation passes when frontend code changed
- manual checks from `TESTING.md` appropriate to the change have been performed
- release metadata accurately describes user-facing and engineering impact
- generated documentation is current
- `development/current.json` points at the next unfinished objective rather than the just-completed work
- no private or environment-specific data has entered the public repository
'''
write("DEVELOPMENT.md", DEVELOPMENT)


TESTING = r'''# Torrent Dashboard Testing Guide

Automated checks are the release gate; this document records the manual verification that still depends on a browser, qBitTorrent instance, operating system, or update/restart behavior.

## Automated baseline

Run before and after a development increment:

```bash
python release_tools/validate_source.py
python release_tools/validate_ui_strings.py
node --check static/app.js
node --check static/settings.js
```

For a release candidate also verify generated documentation:

```bash
python release_tools/generate_release_notes.py --version X.Y.Z --check
```

The Python suite uses only the standard library and currently covers extracted domain behavior, configuration transactions, and source/architecture contracts.

## Manual smoke-test matrix

Only run tests that are relevant and safe in your environment. Never commit real credentials or private infrastructure details while documenting results.

### Startup and setup

- Fresh installation opens the first-run wizard.
- Setup completes with a reachable qBitTorrent instance.
- A failed client connection does not save partial setup state.
- Restarting after setup returns to the dashboard rather than the wizard.

### Authentication and roles

- Administrator login succeeds and administrative Settings/actions are available.
- Standard User login can view permitted dashboard/account surfaces and cannot perform administrator-only mutations.
- Logout invalidates the current session.
- Trusted-network behavior matches the configured access mode.

### Dashboard live state

- Dashboard refreshes without visibly reloading the page.
- Download/upload metrics and torrent counts reflect qBitTorrent state.
- Empty-state copy matches the real reason no rows are visible.
- Connection failures use the error banner and recover when connectivity returns.
- Search, category, tag, tracker, and status filters remain stable while polling.

### Torrent actions

- Start/resume, pause/stop, recheck, delete, force start, and location actions behave as expected for an administrator.
- Bulk actions operate only on selected torrents.
- Destructive actions require the expected confirmation.
- Standard Users cannot invoke administrator-only torrent mutations.

### Torrent details

- Selecting a torrent opens the docked inspector on desktop/tablet.
- Torrent list and detail body scroll independently when needed.
- Collapse preserves the selected torrent; Close clears the detail context.
- General, Trackers, Peers, HTTP Sources, and Content tabs render without errors.
- Mobile retains the bottom-sheet detail presentation.

### Add Torrent

- Magnet/URL submission follows the normal qBitTorrent add path.
- `.torrent` upload follows the normal upload path.
- Metadata preview remains read-only and does not alter the source submitted to qBitTorrent.
- Metadata timeout/cancel paths leave the dialog usable.
- Save-as-`.torrent` is available only when metadata export is actually available.

### Settings

- General, Access, Clients, Updates, and Notifications use the shared **Settings saved** confirmation.
- User and Integration CRUD use scoped success/error language.
- Secret masks do not expose configured credentials back to the browser.
- Concurrent unrelated configuration changes do not overwrite one another.

### Updates and recovery

Use only a test installation or an environment where restart/rollback is acceptable.

- Check for updates discovers the intended public repository release.
- Patch notes show the current and previous release entries.
- Package SHA-256 values populate from authoritative release metadata.
- Downloaded update ZIP is verified before staging.
- Successful update restarts into the expected version.
- Runtime `config.json` and `data/` survive the update.
- A deliberately invalid test build rolls back rather than leaving the installation unusable.

### Responsive interface

At minimum check one desktop width and one mobile width after meaningful UI changes.

Desktop/tablet:

- Text remains legible at 100% browser zoom.
- Torrent workspace does not consume the entire page when few/no torrents are present.
- Torrent list plus open detail inspector fit in the initial viewport by default.
- No controls overlap at common desktop widths.

Mobile:

- Navigation remains reachable.
- Tables/cards do not introduce unusable horizontal overflow.
- Torrent detail sheet can be opened, collapsed, and closed.
- Dialogs remain operable with the on-screen keyboard present.

## Recording gaps

If a regression cannot reasonably be automated yet, record the missing coverage in `development/current.json` or the next release metadata and add it to this matrix if it is a recurring verification need.

Do not use this file as a test-results log; it is a stable testing contract for upstream and forks.
'''
write("TESTING.md", TESTING)


ACTIVE = {
    "schema": 1,
    "status": "ready",
    "objective": "Extract release and update provenance from dashboard.py",
    "why": "Release parsing, installed package provenance, SHA-256 normalization, and integrity-history persistence form one cohesive domain that is still mixed into the HTTP composition root.",
    "acceptance_criteria": [
        "GitHub release parsing and asset-digest normalization live in a focused torrent_dashboard module rather than dashboard.py.",
        "Installed release-info.json and data/release-integrity.json read/write behavior is owned behind a small tested interface.",
        "dashboard.py composes the release/provenance service and retains routing/orchestration rather than domain parsing logic.",
        "The existing public GitHub update protocol, two-release patch-note history, package SHA-256 display, and updater behavior remain unchanged.",
        "Behavioral tests cover normalization, cache merge/persistence, malformed metadata, and installed-release precedence."
    ],
    "decisions": [
        "Keep the extraction behavior-preserving; do not redesign the updater UI in the same increment.",
        "Keep updater.py independent so failed application updates can still recover out of process.",
        "Treat GitHub's finalized asset digest or a previously verified local package digest as authoritative package provenance."
    ],
    "files": [
        "dashboard.py",
        "torrent_dashboard/",
        "tests/",
        "ARCHITECTURE.md"
    ],
    "blockers": [],
    "out_of_scope": [
        "Secret-at-rest changes.",
        "Authorization-role changes.",
        "Changing the public GitHub release/update protocol.",
        "Frontend redesign unrelated to release provenance."
    ],
    "next_action": "Inventory the release/provenance helpers still defined in dashboard.py, define the public interface for a torrent_dashboard release/provenance module, and add characterization tests before moving implementations."
}
write("development/current.json", json.dumps(ACTIVE, indent=2) + "\n")


ADR_README = r'''# Architectural Decision Records

This directory records important decisions whose rationale should survive individual chats, maintainers, and forks.

Records are intentionally short. They describe **why** a durable choice was made, not every implementation detail or conversation that led to it.

## Forks

These records describe decisions inherited from the canonical Torrent Dashboard upstream. A fork may keep them as historical context, supersede them with a later record, or add fork-specific records. Do not rewrite upstream history merely because a fork chooses a different direction.

## Format

Use sequential filenames such as `0006-example-decision.md` and include:

- Status
- Context
- Decision
- Consequences

Use **Superseded** rather than deleting a decision that was once intentionally adopted.
'''
write("docs/decisions/README.md", ADR_README)

ADRS = {
"0001-standard-library-architecture.md": r'''# ADR 0001: Keep the runtime dependency-light

**Status:** Accepted

## Context

Torrent Dashboard is designed to be extracted and run directly on Windows or Linux with minimal setup. Introducing a framework solely to organize code would add deployment and upgrade complexity without solving a user-facing requirement.

## Decision

Keep the application runtime on the Python standard library unless a concrete product requirement justifies an additional dependency. Achieve maintainability through internal modules, explicit service boundaries, tests, and adapters.

## Consequences

- Releases remain simple ZIP deployments.
- Internal architecture must be disciplined because a framework will not impose boundaries for us.
- A future dependency is allowed when its benefit is specific and documented rather than organizational convenience alone.
''',
"0002-composition-root-boundary.md": r'''# ADR 0002: Treat dashboard.py as the composition root

**Status:** Accepted

## Context

Historically `dashboard.py` accumulated HTTP routing and many unrelated domains. Modularization needs a dependency direction that prevents extracted modules from depending back on the monolith.

## Decision

`dashboard.py` is the HTTP/process composition root. Domain and application modules live under `torrent_dashboard/` and must not import `dashboard`. Runtime-specific dependencies are injected into package modules when necessary.

## Consequences

- Extracted modules can be tested independently.
- Circular dependencies are treated as architectural violations.
- `dashboard.py` can remain temporarily large while responsibilities are moved out incrementally.
''',
"0003-serialized-config-transactions.md": r'''# ADR 0003: Serialize application configuration mutations

**Status:** Accepted

## Context

A threaded HTTP server can process multiple settings mutations concurrently. Loading a configuration snapshot and later saving it can silently overwrite an unrelated concurrent change even when the final file replacement itself is atomic.

## Decision

All application-generated configuration mutations use `ConfigStore.mutate()`: acquire the shared lock, reload the latest configuration, apply one transformation, atomically persist the result, then release the lock.

## Consequences

- Unrelated concurrent dashboard writes are preserved.
- Request handlers must not save an older configuration snapshot directly.
- This is an in-process guarantee; it does not coordinate an external editor writing `config.json` simultaneously.
''',
"0004-release-provenance.md": r'''# ADR 0004: Derive installed package provenance from verified release assets

**Status:** Accepted

## Context

Users need a trustworthy SHA-256 for the package that produced an installed build. A ZIP cannot contain its own final digest because embedding the digest changes the archive bytes.

## Decision

Trust GitHub's finalized release-asset digest, verify the downloaded ZIP before staging, and persist that verified provenance as installed `release-info.json`. Publish a separate release sidecar for external inspection, and retain historical verified digests under runtime data.

## Consequences

- Package SHA-256 has an unambiguous meaning: the finalized release ZIP.
- Installed provenance is created after verification rather than embedded into the package.
- Manual extraction cannot know its package digest until authoritative release metadata is obtained.
''',
"0005-responsive-detail-inspector.md": r'''# ADR 0005: Dock torrent details on larger screens and use a sheet on mobile

**Status:** Accepted

## Context

Torrent details are useful while the torrent list remains visible. A floating desktop panel obscured primary content, while permanently splitting a narrow mobile screen would make both surfaces harder to use.

## Decision

Desktop and tablet use a docked, collapsible inspector attached to the torrent workspace. The torrent list remains independently scrollable. Mobile retains a bottom-sheet presentation. Collapse preserves selection; Close clears detail context.

## Consequences

- Selection and detail comparison remain visible together on larger screens.
- The shared desktop workspace must be bounded to fit in the initial viewport by default.
- Responsive behavior intentionally differs by viewport because the available interaction space differs.
'''
}
for name, content in ADRS.items():
    write(f"docs/decisions/{name}", content)


# Expand the README development entry point with fork-safe guidance.
readme = read("README.md")
marker = "## Development\n"
if marker not in readme:
    raise RuntimeError("README Development section missing")
prefix = readme.split(marker, 1)[0]
readme_dev = r'''## Development

Start with [`DEVELOPMENT.md`](DEVELOPMENT.md) for the contributor/fork workflow and [`HANDOFF.md`](HANDOFF.md) for the current portable development handoff. Architecture and module ownership are documented in [`ARCHITECTURE.md`](ARCHITECTURE.md), interface/content conventions in [`DESIGN_LANGUAGE.md`](DESIGN_LANGUAGE.md), and the automated/manual verification contract in [`TESTING.md`](TESTING.md).

Important architectural choices and their rationale are kept under [`docs/decisions/`](docs/decisions/). Current unfinished engineering intent lives in [`development/current.json`](development/current.json); generated released-state context remains in [`PROJECT_STATE.md`](PROJECT_STATE.md).

Torrent Dashboard is a public project and these continuity files are intentionally fork-safe. Canonical upstream branch and PR references are labeled as upstream context rather than assumptions about a fork. Fork maintainers should update `development/current.json` when their roadmap diverges and should never place credentials, private infrastructure details, or conversation transcripts in public handoff material.

Backend tests and reusable source validation can be run with:

```bash
python release_tools/validate_source.py
```

UI contract validation can be run with:

```bash
python release_tools/validate_ui_strings.py
```

Structured release metadata in `release_notes/releases.json` generates the changelog, project state, portable handoff, and GitHub release body. Pull requests and forks are welcome. Fork maintainers can point **Settings → Updates** at their own public release repository or change `DEFAULT_UPDATE_REPOSITORY` for their build.
'''
write("README.md", prefix + readme_dev)


# Add continuity architecture without conflating upstream identity with a fork.
architecture = read("ARCHITECTURE.md")
insert_before = "## Near-term extraction plan\n"
if insert_before not in architecture:
    raise RuntimeError("ARCHITECTURE.md extraction-plan marker missing")
continuity = r'''## Development continuity

The repository is designed so development can continue without access to prior chat history.

- `PROJECT_STATE.md` is generated from released metadata and represents the last documented upstream state.
- `development/current.json` is the authored active-work record and may legitimately differ in a fork.
- `HANDOFF.md` combines released state and active work into the first document a new developer or AI should read.
- `DEVELOPMENT.md` defines the contributor, fork, validation, versioning, and release workflow.
- `TESTING.md` records the manual verification contract that cannot be fully represented by unit tests.
- `docs/decisions/` records durable architectural rationale and can be superseded rather than rewritten.

Canonical repository/branch/PR references in generated state are explicitly labeled **upstream**. They provide lineage and context; they are not instructions that a fork must use the same repository identity or workflow.

Continuity files are public engineering artifacts. They must not contain credentials, private infrastructure details, user data, private incident context, or conversation transcripts.

'''
write("ARCHITECTURE.md", architecture.replace(insert_before, continuity + insert_before, 1))


# Release metadata migration: label canonical/upstream identifiers explicitly.
release_path = ROOT / "release_notes" / "releases.json"
data = json.loads(release_path.read_text(encoding="utf-8"))
project = data.setdefault("project", {})
project["canonical_repository"] = project.pop("repository", "CynicaGaming/TorrentDashboard")
project["upstream_development_branch"] = project.pop("development_branch", "refactor/backend-modularization-users")
project["upstream_prerelease_branch"] = project.pop("prerelease_branch", "prerelease/backend-modularization")
project["upstream_pull_request"] = project.pop("pull_request", 25)
principles = project.setdefault("principles", [])
fork_principle = "Keep public development continuity portable across forks; label canonical repository/branch/PR references as upstream context rather than local identity."
if fork_principle not in principles:
    principles.append(fork_principle)

previous = next((item for item in data["releases"] if item.get("version") == PREVIOUS), {})
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
data["releases"] = [item for item in data["releases"] if item.get("version") != VERSION] + [release]
release_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


# Extend reusable documentation validation to the new continuity contract.
validator = read("release_tools/validate_source.py")
validator = validator.replace("import ast\nimport compileall\n", "import ast\nimport compileall\nimport json\n", 1)
old_docs = '''def validate_documentation() -> None:\n    for name in ("README.md", "ARCHITECTURE.md", "DESIGN_LANGUAGE.md", "PROJECT_STATE.md", "CHANGELOG.md"):\n        if not (ROOT / name).is_file():\n            fail(f"Required project documentation is missing: {name}")\n'''
new_docs = '''def validate_documentation() -> None:\n    required = (\n        "README.md", "DEVELOPMENT.md", "ARCHITECTURE.md", "DESIGN_LANGUAGE.md",\n        "TESTING.md", "PROJECT_STATE.md", "HANDOFF.md", "CHANGELOG.md",\n        "development/current.json", "docs/decisions/README.md",\n    )\n    for name in required:\n        if not (ROOT / name).is_file():\n            fail(f"Required project documentation is missing: {name}")\n\n    decisions = sorted((ROOT / "docs" / "decisions").glob("[0-9][0-9][0-9][0-9]-*.md"))\n    if len(decisions) < 5:\n        fail("Expected the baseline architectural decision records under docs/decisions")\n\n    active = json.loads((ROOT / "development" / "current.json").read_text(encoding="utf-8"))\n    if int(active.get("schema") or 0) != 1:\n        fail("development/current.json must use schema 1")\n    for field in ("status", "objective", "why", "next_action"):\n        if not isinstance(active.get(field), str) or not active[field].strip():\n            fail(f"development/current.json requires non-empty {field}")\n    for field in ("acceptance_criteria", "decisions", "files", "blockers", "out_of_scope"):\n        value = active.get(field)\n        if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):\n            fail(f"development/current.json field {field} must be a list of non-empty strings")\n'''
if old_docs not in validator:
    raise RuntimeError("validate_source.py documentation function did not match expected source")
validator = validator.replace(old_docs, new_docs, 1)
write("release_tools/validate_source.py", validator)


# Generate the derived handoff/state/changelog from the two authored sources.
subprocess.run(
    [sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", VERSION],
    cwd=ROOT,
    check=True,
)

print(f"Staged Torrent Dashboard v{VERSION} fork-safe development continuity")
