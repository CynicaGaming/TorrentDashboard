# ADR 0006: Record the current responsive detail workspace

**Status:** Accepted; supersedes ADR 0005

## Context

Later UI iterations replaced closable details, fixed six-row lists, and forced document scrolling. Keeping these historical instructions in the current design/test contract made future changes ambiguous.

## Decision

Preserve the implemented proportional desktop workspace: prefer 44% of available space for whole torrent rows, retain at least three rows, and prioritize finite General content. Desktop starts with an expanded no-selection detail shell; mobile starts collapsed. The disclosure preserves selection, while selecting the same row again clears it. Opening details does not force document scrolling.

## Consequences

This record documents existing behavior, not a UI redesign. `DESIGN_LANGUAGE.md` and `TESTING.md` describe the current contract; release history preserves earlier iterations. Detail docking and torrent cards currently have different responsive breakpoints, so both boundaries need manual coverage.
