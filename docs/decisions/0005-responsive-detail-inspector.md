# ADR 0005: Dock torrent details on larger screens and use a sheet on mobile

**Status:** Accepted

## Context

Torrent details are useful while the torrent list remains visible. A floating desktop panel obscured primary content, while permanently splitting a narrow mobile screen would make both surfaces harder to use.

## Decision

Desktop and tablet use a docked, collapsible inspector attached to the torrent workspace. The torrent list remains independently scrollable. Mobile retains a bottom-sheet presentation. Collapse preserves selection; Close clears detail context.

## Consequences

- Selection and detail comparison remain visible together on larger screens.
- The shared desktop workspace must be bounded to fit in the initial viewport by default.
- Responsive behavior intentionally differs by viewport because the available interaction space differs.
