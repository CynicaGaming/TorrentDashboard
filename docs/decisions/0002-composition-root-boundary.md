# ADR 0002: Treat dashboard.py as the composition root

**Status:** Accepted

## Context

Historically `dashboard.py` accumulated HTTP routing and many unrelated domains. Modularization needs a dependency direction that prevents extracted modules from depending back on the monolith.

## Decision

`dashboard.py` is the HTTP/process composition root. Domain and application modules live under `torrent_dashboard/` and must not import `dashboard`. Runtime-specific dependencies are injected into package modules when necessary.

## Consequences

- Extracted modules can be tested independently.
- Circular dependencies are treated as architectural violations.
- `dashboard.py` can remain temporarily large while responsibilities are moved out incrementally.
