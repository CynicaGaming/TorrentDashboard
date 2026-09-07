# Hardening scope and follow-up

The v0.5.148 change addresses reproducible defects in the v0.5.147 baseline. It is an engineering hardening increment, not a claim of a completed security certification or comprehensive penetration test.

## Addressed

- Close SQLite connections deterministically and serialize all history access with restoration.
- Drain requests and collectors before restore, reload configuration under its lock, and invalidate sessions/caches before admitting new work.
- Reject restore during an active application update.
- Recheck existing LAN/disabled bypass sessions after access policy changes, including recovery-console requests; invalidate other sessions on administrator password resets.
- Bound HTTP framing, require JSON objects, reject truncated uploads, and preserve multipart binary data.
- Exclude detached updater runners and SQLite sidecars; verify archives before publication; prevent concurrent imports from overwriting one another.
- Reject unsafe or ambiguous Windows/Linux archive paths and malformed versions; bound manifest/configuration reads and stream per-file verification.
- Use private, exclusive temporary files for atomic configuration replacement; report rollback failure accurately while retaining the safety archive.
- Run validation on pull requests across Linux/Windows and Python 3.13/3.14. Pin workflow actions to verified upstream commits and disable persisted checkout credentials.
- Consolidate superseded UI documentation without changing the layout contract.

## Operational checks still required

1. Exercise the compiled Windows cross-install backup/import/restore and safety-backup round trip with active browsers and a live qBitTorrent client.
2. Exercise compiled update/rollback and interrupted-restore recovery in disposable installations. An interrupted multi-file restore is not power-loss atomic.
3. Check the current desktop/mobile UI at the documented breakpoints after deployment.

## Further engineering work

- Source-package pruning PR #28 is included in the main baseline for this branch. Preserve its custom-output pruning and regression coverage in future packaging changes.
- Continue extracting qBitTorrent transport, request services, and notification dispatch from the composition root in behavior-preserving increments.
- Expand HTTP integration coverage for setup, session expiry, and update/recovery flows; review unauthenticated diagnostic exposure and deployment defaults against a defined deployment threat model.
- Evaluate frontend module boundaries and browser automation before making large UI changes.
- Retain the documented trusted-network deployment scope. Backup encryption, code signing, and comprehensive crash-recovery journaling require separate product/design decisions.

Read `TESTING.md` for the manual contract and `development/current.json` for the active next action. Do not interpret source-level cross-install tests or successful executable `--help` checks as proof that live Windows migration was exercised.
