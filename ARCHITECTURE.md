# Torrent Dashboard Architecture

This document describes the intended module boundaries for Torrent Dashboard and the rules used to keep the application maintainable as features are added.

## Design goals

Torrent Dashboard intentionally remains a small, dependency-light Python application. Modularity should come from clear internal boundaries rather than from introducing a framework solely to organize code.

The current rules are:

- `dashboard.py` is the **composition root and HTTP adapter**. It may assemble services and route requests, but new domain logic should normally live under `torrent_dashboard/`.
- Modules under `torrent_dashboard/` **must not import `dashboard`**. Dependencies on runtime-specific behavior are passed in explicitly instead of creating circular imports.
- Domain modules should expose small public interfaces through `__all__` and keep filesystem/network side effects at clear boundaries.
- Configuration changes must use the `ConfigStore.mutate()` transaction path. Request code must never save a stale configuration snapshot directly.
- Release metadata is authored once in `release_notes/releases.json`; generated files and GitHub release notes must not become competing sources of truth.
- Runtime data belongs under `data/` and is excluded from release packages unless a component explicitly documents otherwise.

## Current backend layout

### `dashboard.py`

Owns application composition, process startup, HTTP routing, qBitTorrent orchestration, sessions, network/interface discovery, notification delivery, history collection, update orchestration, and compatibility adapters that have not yet been extracted. Configuration and integration domains are imported from package modules rather than implemented here.

This file is still larger than the desired steady-state architecture. Refactors should reduce its responsibilities incrementally while keeping behavior stable.

### `torrent_dashboard/users.py`

Owns the user/account domain:

- password hashing and verification
- user normalization and lookup
- administrator/standard-user invariants
- self-service profile changes
- avatar validation and storage
- password changes
- legacy authentication-field synchronization

### `torrent_dashboard/config.py`

Owns configuration defaults, legacy migrations, update-repository normalization, browser-safe configuration redaction, and atomic `config.json` persistence through `ConfigRepository`. LAN detection needed by one legacy migration is injected by the composition root rather than imported from it.

### `torrent_dashboard/config_store.py`

Owns in-process configuration transaction coordination. `mutate()` acquires the lock before reading the latest configuration through `ConfigRepository`, applies one transformation, persists it, and releases the lock only after the write completes.

### `torrent_dashboard/integrations.py`

Owns the integration provider catalog, field validation and normalization, configured-secret redaction, connection tests, and integration CRUD transforms. Provider definitions no longer live in the HTTP adapter.

### `updater.py`

Owns out-of-process update replacement, restart verification, and rollback. It should remain independent from dashboard HTTP routing so a failed application update can still be recovered.

## Frontend layout

### `static/app.js`

Owns the main dashboard runtime, torrent interaction, account UI, dialogs, notifications, and shared API helpers. It remains a large module; future feature work should prefer extracting cohesive browser-side domains instead of continuing to grow this file.

### `static/settings.js`

Owns Settings-page behavior, including users, integrations, client settings, notifications, and updates. This separation has worked well and is the model for future frontend extraction.

### Styles

`static/app.css` contains shared/dashboard styles and `static/settings.css` contains Settings-specific styles. New component styles should stay with the narrowest applicable surface.

## Configuration flow

All application-generated `config.json` writes follow this contract:

1. Acquire the shared `ConfigStore` lock.
2. Reload the latest configuration from disk.
3. Apply one validated transformation.
4. Persist the complete transformed configuration atomically.
5. Release the lock.

A caller that already holds a configuration dictionary must not assume that dictionary is current enough to save.

## Release and update flow

1. Structured release information is added to `release_notes/releases.json`.
2. `release_tools/generate_release_notes.py` generates `CHANGELOG.md`, `PROJECT_STATE.md`, `HANDOFF.md`, and the GitHub release body.
3. Source validation and unit tests run before packaging.
4. `release_tools/build_release.py` creates the ZIP and a sidecar release-information JSON file.
5. GitHub publishes both assets.
6. Torrent Dashboard verifies GitHub's SHA-256 for the ZIP before staging an update.
7. The updater preserves runtime data, verifies the restarted version through `/health`, and rolls back on failure.

`PROJECT_STATE.md` is generated released-state context. `HANDOFF.md` combines released state with the authored active-work file. `ARCHITECTURE.md` is the durable design reference and is edited deliberately when module boundaries change.

## Testing strategy

Tests use the Python standard library (`unittest`) so the development and release environments do not need extra packages.

Run the backend tests with:

```bash
python -m unittest discover -s tests -v
```

Release validation also compiles Python modules, syntax-checks JavaScript, checks frontend build-version synchronization, validates generated release metadata, validates development-continuity files, and runs repository hygiene checks.

Manual/environment-dependent verification is documented in `TESTING.md` rather than being left implicit in conversation history.

## Dependency direction

Preferred dependency direction:

```text
HTTP / process adapters (`dashboard.py`, `updater.py`)
                 │
                 ▼
      application/domain modules
          (`torrent_dashboard/`)
                 │
                 ▼
       Python standard library
```

A package module importing `dashboard.py` is considered an architectural violation because it makes the composition root part of the domain dependency graph.

## Development continuity

The repository is designed so development can continue without access to prior chat history.

- `PROJECT_STATE.md` is generated from released metadata and represents the last documented upstream state.
- `development/current.json` is the authored active-work record and may legitimately differ in a fork.
- `HANDOFF.md` combines released state and active work into the first document a new developer or AI should read.
- `DEVELOPMENT.md` defines the contributor, fork, validation, versioning, and release workflow.
- `TESTING.md` records the manual verification contract that cannot be fully represented by unit tests.
- `docs/decisions/` records durable architectural rationale and can be superseded rather than rewritten.

Canonical repository/branch/PR references in generated state are explicitly labeled **upstream**. They provide lineage and context; they are not instructions that a fork must use the same repository identity or workflow.

Continuity files are public engineering artifacts. They must not contain credentials, private infrastructure details, user data, private incident context, or conversation transcripts.

## Near-term extraction plan

The next useful boundaries are:

1. **Release/update metadata** — GitHub release parsing, installed provenance, and integrity-history persistence.
2. **qBitTorrent client/domain operations** — isolate Web API transport, server normalization, and preference translation from HTTP routes.
3. **Request/application services** — move setup and settings transformations behind testable service functions so HTTP handlers remain adapters.
4. **Notification delivery** — separate delivery dispatch from provider configuration now that integration definitions are isolated.
5. **Frontend feature modules** — reduce the responsibility of `static/app.js` after backend boundaries stabilize.

Extraction should remain incremental. A refactor should not simultaneously redesign unrelated user-facing behavior unless the behavior change is independently required and tested.
