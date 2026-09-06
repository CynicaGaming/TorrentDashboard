# Contributing to Torrent Dashboard

Torrent Dashboard is a prerelease project. Changes should preserve existing behavior unless a pull request explicitly describes a breaking change.

## Development environment

Runtime requirements:

- Python 3.13 or newer
- qBitTorrent with the Web UI enabled for end-to-end testing

Contributor validation also uses Node.js for JavaScript syntax checks. The application itself does not require Node.js at runtime.

## Before making changes

1. Create a topic branch from `main`.
2. Keep runtime configuration, databases, uploaded files, certificates, tokens, API keys, and webhook secrets out of Git.
3. Avoid coupling unrelated feature changes into the same pull request.
4. Preserve compatibility paths unless the pull request includes a migration and release note.

## Validation

Run these checks before opening or updating a pull request:

```bash
python -m py_compile dashboard.py updater.py release_tools/build_release.py release_tools/validate_checkpoint.py
for file in static/*.js; do node --check "$file"; done
python release_tools/validate_public_repo.py
python release_tools/validate_ui_strings.py
python release_tools/validate_checkpoint.py
```

Pull requests also run the repository validation workflow.

## Version coupling

The frontend and backend deliberately fail closed when build versions do not match. When changing the application version, update all coupled references together:

- `VERSION` in `dashboard.py`
- `FRONTEND_BUILD` in `static/app.js`
- the build meta tag and versioned static references in `static/index.html`
- versioned service-worker asset references and cache identity in `static/sw.js`

`release_tools/validate_checkpoint.py` checks these relationships.

## Notifications and integrations

Integration connection tests are not all passive. Discord, ntfy, generic webhook, and Home Assistant tests send a real test message to the configured destination. Do not add automatic page-load probing for those integrations.

Browser/PWA notification permission must be requested from a user interaction. Keep enable/disable operations scoped to notification settings; they must not save unrelated unsaved Settings fields.

The repository currently supports browser/PWA device notifications and external notification integrations. A complete background Web Push sender/subscription backend is a separate capability and should not be implied by UI wording unless it is actually implemented.

## Security

Do not commit credentials, private keys, live webhook URLs, `.env` files, `config.json`, or the `data/` directory. The public-repository validator rejects common secret formats and runtime paths, but it is not a substitute for reviewing a diff before publishing it.

If a change affects authentication, authorization, CSRF handling, update verification, archive extraction, URL handling, or secret redaction, describe the security impact in the pull request.

## Pull requests

A useful pull request should state:

- what behavior changes;
- what behavior is intentionally preserved;
- validation performed;
- any migration or compatibility considerations;
- any known limitation that remains.

`main` publishes the prerelease workflow, so changes should not be merged until validation is green and the diff has been reviewed.
