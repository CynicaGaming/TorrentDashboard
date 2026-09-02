# Torrent Dashboard Design Language

Torrent Dashboard uses a single content language across desktop and responsive surfaces. These rules apply to static HTML, dynamically generated controls, dialogs, status messages, notifications, and toasts.

## Core rules

- Use **sentence case** for headings, labels, buttons, empty states, validation, and status text. Preserve product names and established acronyms such as Torrent Dashboard, qBitTorrent, GitHub, API, IP, URL, HTTPS, and SHA-256.
- Use the **same words for the same action and outcome**. A Save action in the core Settings save bar confirms with **“Settings saved”** regardless of which Settings page is active.
- Use feature-specific success copy only when the saved object is materially different from dashboard settings, such as **“User saved”** or **“Integration saved”**.
- Use **one success channel per interaction**. Page-level saves use a toast. Scoped dialogs that already keep a visible inline status do not also emit a duplicate success toast.
- Loading and in-progress states use an active verb plus an ellipsis, for example **“Saving client settings…”** or **“Checking for updates…”**.
- Toasts are short outcome statements without terminal punctuation. Persistent inline status and explanatory copy use complete sentences with punctuation.
- Validation and errors state what the user needs to do in plain language. Avoid internal field names, implementation terminology, camelCase tokens, and title-case error sentences.
- Destructive controls use a direct verb and object, and confirmations identify what will be deleted or removed.

## Settings feedback contract

The core Settings pages are General, Access, Clients, Updates, and Notifications. They share the same form save bar and the same successful outcome language:

> Settings saved

Updates may use a different backend endpoint, but that implementation detail must not change the user-facing confirmation.

Integrations and Users are record-management surfaces rather than core form pages. Their successful record operations remain scoped:

- Integration saved
- Integration deleted
- User saved
- User deleted

qBitTorrent client settings and account dialogs keep their result visible inside the dialog, so they do not duplicate successful completion with a toast.

## Source and validation

New user-facing copy should be authored in its final display form rather than relying on token-to-text conversion. The existing `uiText()` normalizer remains a compatibility layer for older surfaces and may be retired incrementally.

`release_tools/validate_ui_strings.py` enforces the high-value copy contracts that have caused drift before, including the core Settings save confirmation and known title-case legacy strings.


## Desktop legibility

Desktop layouts should use available space before shrinking text. At viewport widths of 1024 px and above:

- Primary application and table content should generally render in the **13–15 px** range.
- Supporting copy, help text, timestamps, and secondary metadata should generally stay at **11.5 px or larger**. Small badges and compact metadata labels may use approximately **10–11 px** when contrast and spacing remain strong.
- Muted text must remain visibly subordinate without becoming low-contrast. Dark and light themes both need a clear contrast step between `--text`, `--muted`, surfaces, and borders.
- Forms and navigation should gain spacing and hit area before their text is reduced. The desktop canvas should be used rather than preserving large unused margins.
- Compact density may reduce row height and spacing, but it should not restore the former undersized text baseline.
- Tablet and mobile breakpoints remain independently tuned; desktop typography rules must not simply scale responsive layouts upward.


## Docked inspectors

On desktop and tablet layouts, secondary inspection surfaces that describe a selected item should preserve access to the primary list instead of covering it.

- Torrent details dock to the bottom edge of the torrent workspace and share the same outer surface.
- The primary torrent list remains independently scrollable while details are expanded.
- Collapse preserves the current torrent selection and only reduces the inspector to its header; Close clears the inspector entirely.
- Collapse state may be remembered as a user preference, but selecting a torrent must continue to update the docked header even while collapsed.
- Mobile may use a bottom-sheet treatment when the available viewport cannot support a useful split workspace.

## Bounded list and inspector workspaces

On desktop and tablet layouts, list/detail workspaces should fit within the initial viewport under normal browser chrome rather than forcing the page to grow around a large list surface.

- A list-only torrent workspace should remain deliberately bounded; unused vertical space is preferable to an oversized empty table.
- Opening the torrent inspector may enlarge the shared workspace, but the torrent list and detail inspector should remain visible together in the initial viewport at standard desktop/tablet sizes.
- The primary list becomes the flexible internal scroll region. Long lists should scroll inside the workspace before the overall dashboard page scrolls.
- The detail body may scroll independently when its content exceeds the inspector allocation.
- Mobile remains an exception: the existing bottom-sheet interaction may consume most of the viewport because simultaneous list/detail visibility is not practical at phone widths.

## Empty states and live dashboard metrics

Empty-state language must describe why the current surface is empty rather than using one generic message for every zero-row condition.

- A client with no torrents should say that there are no torrents yet/available; it should not imply that filters are hiding results.
- Filtered views should name the relevant condition, such as no active, completed, or paused torrents, or explain that search/filter criteria exclude all rows.
- Empty states inside bounded list workspaces should remain visually centered in the available list body and should not be pushed below a flexing scroll region.
- Primary dashboard metric cards should represent meaningful operational state. Values that refresh every polling interval, such as a per-second "Last update" timestamp, should not occupy a permanent summary card unless staleness itself requires attention.
- Connection failures and stale data should be surfaced as health/error states rather than requiring users to infer problems from a timestamp.

