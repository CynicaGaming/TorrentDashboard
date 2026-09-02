# ADR 0003: Serialize application configuration mutations

**Status:** Accepted

## Context

A threaded HTTP server can process multiple settings mutations concurrently. Loading a configuration snapshot and later saving it can silently overwrite an unrelated concurrent change even when the final file replacement itself is atomic.

## Decision

All application-generated configuration mutations use `ConfigStore.mutate()`: acquire the shared lock, reload the latest configuration, apply one transformation, atomically persist the result, then release the lock.

## Consequences

- Unrelated concurrent dashboard writes are preserved.
- Request handlers must not save an older configuration snapshot directly.
- This is an in-process guarantee; it does not coordinate an external editor writing `config.json` simultaneously.
