# ADR 0007: Quiesce live work during state restoration

**Status:** Accepted

## Context

A database lock alone cannot protect a restore from an already authenticated request, a settings mutation, or a collector holding old configuration. SQLite connection context managers also do not close connections, which can prevent file replacement on Windows.

## Decision

Use a standard-library `StateGate` at HTTP/collector entry points. Normal work may overlap; restore drains active work and blocks new work until replacement and session/cache invalidation finish. Authenticate requests after gate entry. Acquire locks in the order state gate, configuration, history, cache. Every history operation closes its SQLite connection before releasing the history lock.

Publish backups only after validation. Use portable path validation and streamed digests, and retain a verified safety backup before destructive restore work. Serialize backup publication within the single application process.

## Consequences

Restore may wait for ongoing requests or client polling. Socket inactivity timeouts limit stalled HTTP reads. This is in-process coordination, not coordination with external editors or standalone recovery tools. Ordinary exceptions trigger rollback; process termination/power loss can still require manual safety-backup recovery. A launched updater must finish before restore is allowed.

## References

- [Python SQLite connection context managers](https://docs.python.org/3/library/sqlite3.html#how-to-use-the-connection-context-manager)
- [Windows file naming rules](https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file)
