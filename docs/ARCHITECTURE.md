# Torrent Dashboard Architecture

## Overview

Torrent Dashboard is intentionally compact: a Python standard-library HTTP application serves a static browser UI, talks to qBitTorrent and configured integrations, stores local history in SQLite, and manages its own prerelease update flow.

The main runtime components are:

- `dashboard.py` — HTTP server, authentication and sessions, qBitTorrent client, integrations, notifications, history, configuration, and update orchestration.
- `updater.py` — detached update installation and rollback support.
- `static/` — application shell, settings UI, PWA service worker, styles, and notification assets.
- `data/` — runtime-only databases, uploaded assets, update state, and backups. This directory is not tracked.
- `release_tools/` — repository hygiene, UI, checkpoint, and release-package validation.

## HTTP and security model

The server uses `ThreadingHTTPServer` and serves both the static application and JSON APIs. Mutating authenticated APIs require the session CSRF token. Administrator-only endpoints enforce the Administrator role independently of whether the session came from password authentication or trusted-network bypass.

Sessions are in-memory and use an `HttpOnly`, `SameSite=Lax` cookie. The server emits restrictive security headers, including `X-Content-Type-Options`, `X-Frame-Options`, a same-origin referrer policy, and a Content Security Policy.

Trusted access can be derived from selected network interfaces plus explicit IP/CIDR entries. Loopback is always trusted.

## Configuration and runtime data

`config.json` stores application configuration. It is intentionally excluded from Git and release source control. Runtime data lives under `data/`.

Secrets are retained server-side and redacted before settings are returned to the browser. Existing configured secrets are represented by a placeholder so saving an unchanged form does not replace them.

Configuration migrations are handled during `load_config()` so older installations can upgrade without requiring a hand-edited migration file.

## qBitTorrent integration

Each configured qBitTorrent server has a cached `QBitClient`. The client supports API-key authentication for qBitTorrent 5.2+ and username/password authentication for older versions.

The collector refreshes live state on the application's fixed one-second cadence. It stores current state in memory and writes lower-frequency historical samples to SQLite. Failed username/password logins are deliberately not retried continuously because qBitTorrent can temporarily ban an IP after repeated Web UI failures.

## History and events

SQLite stores:

- time-series transfer snapshots;
- per-torrent history;
- dashboard and torrent events.

History retention and sample frequency are configurable. Live torrent state remains in memory and is not sourced from the historical tables.

## Integrations

The integration catalog is data-driven in `dashboard.py`. Media integrations use read-style connection tests, while delivery integrations such as Discord, ntfy, generic webhooks, and Home Assistant send a real test message.

The integration status indicator is a browser-side health hint. It records the most recent explicit test result in local storage:

- green — the last explicit test succeeded;
- yellow — configured but untested, changed since testing, or returned a non-connectivity problem;
- red — disabled or the last test showed an unreachable/network-level failure.

Delivery integrations are not automatically probed on page load because doing so would generate real messages.

## Notifications

There are two notification paths:

1. Browser/PWA notifications shown on the user's device. These require browser permission and are controlled by the browser-notification setting.
2. Server-side external notification integrations, which send completion messages to configured destinations.

The service worker supports notification display/click behavior and contains a `push` event handler, but the application does not currently implement the subscription storage and server-side Web Push sender required for independent background delivery to a closed browser/PWA.

The requested default MP3 is stored as seven Base64 text parts in `static/`. During service-worker installation the parts are decoded once, verified indirectly by release validation, and cached as `/static/notification-default.mp3`. A small compatibility shim redirects the previous default WAV path to this MP3 without changing custom-sound behavior.

Custom WAV, MP3, and OGG files are uploaded to `data/` and served through the authenticated notification-sound API.

## PWA and caching

`static/sw.js` owns the PWA cache. It keeps versioned frontend assets available and injects the stabilization feature assets into navigation responses. Frontend build mismatch recovery unregisters stale service workers and clears Torrent Dashboard caches before reloading the correct build.

Service-worker changes should be treated as release-coupled code because an incorrect cache key or versioned asset reference can leave clients on incompatible frontend files.

## Updates

The updater reads public GitHub Release metadata, validates semantic versioning, identifies the release ZIP, verifies GitHub's SHA-256 digest and reported size, rejects unsafe ZIP traversal paths, stages the package, and launches `updater.py` in a detached process.

The installed application is health-checked after replacement and can roll back if the new version does not start correctly.

## Release validation

The repository runs several complementary checks:

- Python compilation;
- JavaScript syntax checking;
- public-repository secret/runtime-file hygiene;
- UI regression checks;
- cross-file checkpoint invariants, including version coupling and the exact default-notification MP3 digest.

`release_tools/build_release.py` runs the repository validators before producing a release ZIP.
