# ADR 0004: Derive installed package provenance from verified release assets

**Status:** Accepted

## Context

Users need a trustworthy SHA-256 for the package that produced an installed build. A ZIP cannot contain its own final digest because embedding the digest changes the archive bytes.

## Decision

Trust GitHub's finalized release-asset digest, verify the downloaded ZIP before staging, and persist that verified provenance as installed `release-info.json`. Publish a separate release sidecar for external inspection, and retain historical verified digests under runtime data.

## Consequences

- Package SHA-256 has an unambiguous meaning: the finalized release ZIP.
- Installed provenance is created after verification rather than embedded into the package.
- Manual extraction cannot know its package digest until authoritative release metadata is obtained.
