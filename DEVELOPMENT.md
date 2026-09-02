# Torrent Dashboard Development Guide

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
