# ADR 0001: Keep the runtime dependency-light

**Status:** Accepted

## Context

Torrent Dashboard is designed to be extracted and run directly on Windows or Linux with minimal setup. Introducing a framework solely to organize code would add deployment and upgrade complexity without solving a user-facing requirement.

## Decision

Keep the application runtime on the Python standard library unless a concrete product requirement justifies an additional dependency. Achieve maintainability through internal modules, explicit service boundaries, tests, and adapters.

## Consequences

- Releases remain simple ZIP deployments.
- Internal architecture must be disciplined because a framework will not impose boundaries for us.
- A future dependency is allowed when its benefit is specific and documented rather than organizational convenience alone.
