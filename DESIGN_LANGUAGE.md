# Torrent Dashboard Design Language

Torrent Dashboard uses a single content language across desktop and responsive surfaces. These rules apply to static HTML, dynamically generated controls, dialogs, status messages, notifications, and toasts.

## Core rules

- Use **deliberate, context-aware capitalization**. Compact named destinations may read like product labels; headings, field labels, actions, status text, validation, and explanatory copy generally use sentence case. Preserve product names and established acronyms such as Torrent Dashboard, qBitTorrent, GitHub, API, IP, URL, HTTPS, and SHA-256.
- Use the **same words for the same action and outcome**. A Save action in the core Settings save bar confirms with **“Settings saved”** regardless of which Settings page is active.
- Use feature-specific success copy only when the saved object is materially different from dashboard settings, such as **“User saved”** or **“Integration saved”**.
- Use **one success channel per interaction**. Page-level saves use a toast. Scoped dialogs that already keep a visible inline status do not also emit a duplicate success toast.
- Loading and in-progress states use an active verb plus an ellipsis, for example **“Saving client settings…”** or **“Checking for updates…”**.
- Toasts are short outcome statements without terminal punctuation. Persistent inline status and explanatory copy use complete sentences with punctuation.
- Validation and errors state what the user needs to do in plain language. Avoid internal field names, implementation terminology, camelCase tokens, and title-case error sentences.
- Destructive controls use a direct verb and object, and confirmations identify what will be deleted or removed.


## Capitalization and product voice

Torrent Dashboard follows a Firefox-inspired desktop-application pattern rather than forcing one casing rule onto every surface.

- **Named destinations and compact product labels** may use title-style capitalization when they behave like stable names, for example **Access Control** and **Download Client** in setup navigation. One-word destinations such as **Dashboard**, **Settings**, and **Notifications** are naturally capitalized.
- **Page and dialog headings, field labels, buttons, menu commands, tabs, and status labels** use sentence case: **Set up your dashboard**, **Authentication mode**, **Check for updates**, **HTTP sources**, **Client settings**.
- **Explanatory copy, validation, errors, empty states, and status messages** use natural sentence case and should read as concise human language rather than implementation output.
- **Proper names, protocols, acronyms, and file or format names** retain their established form: Torrent Dashboard, qBitTorrent, GitHub, API, Web API, HTTP, IP, URL, SHA-256, `.torrent`.
- Prefer direct product concepts over legacy implementation terminology. Use **client** on client-management surfaces and **allowed IP addresses** in user-facing access controls; internal configuration keys and historical documentation do not need to be renamed solely for copy consistency.
- Prefer verb phrases for actions: **Add client**, **Test connection**, **Copy address**, **Remove torrent**. Avoid noun-heavy implementation phrases and parenthetical constructions such as **Remove torrent(s)**.
- Do not capitalize words merely because they appear in a control. Capitalization should communicate hierarchy or a proper name, not decoration.



## Iconography

Common interface symbols should use locally embedded Material-style SVG paths rather than text glyphs when an established icon exists. Disclosure chevrons, expansion controls, and file-source affordances should share this treatment so their stroke/shape quality is consistent across browsers and operating systems. Do not introduce a Google Fonts, Material Symbols font, or other remote icon dependency solely for interface chrome; Torrent Dashboard must keep these controls available offline and in self-hosted/forked deployments.

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

New user-facing copy must be authored in its final display form. Runtime normalization must not recase deliberate authored text; `uiText()` remains only as a compatibility layer for legacy camelCase or underscore tokens and may be retired incrementally.

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

- Torrent details dock below the torrent list as a distinct sibling panel rather than visually merging into the table surface.
- The list and inspector should each have their own border, radius, background, and clear spacing so their roles are immediately distinguishable.
- The primary torrent list remains independently scrollable while details are open.
- Torrent details are persistent and collapsible rather than closable. The collapsed state is a compact disclosure bar; it never clears the selected torrent.
- Selecting a torrent expands the inspector automatically and updates its content. With no selection, the dock remains available and may be expanded to an empty state.
- The full disclosure bar is the interaction target and must remain keyboard- and touch-accessible; small icon-only collapse/close controls are not required.
- Mobile may use a bottom-sheet treatment when expanded, but the collapsed disclosure bar remains persistently reachable.

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

## Viewport-docked desktop inspectors

On non-mobile layouts, a docked list/detail workspace should use the actual remaining viewport rather than a fixed viewport-height guess. When torrent details are expanded, the workspace should extend to the bottom of the visible dashboard content, keep the torrent list scrollable above a visually separate detail panel, and allocate enough height to the inspector for its primary content to remain legible. When collapsed, the inspector remains as a compact dock bar without forcing the expanded workspace height. The separation between list and inspector is part of the hierarchy, not unused space. Mobile keeps the sheet model.



## Client-style dashboard workspace

The Dashboard retains its page title and short activity subtitle for visual hierarchy and orientation. Navigation also establishes location, but removing the heading does not materially increase usable torrent space and weakens the page hierarchy. On desktop/tablet, the torrent workspace fills the actual remaining viewport so the persistent Torrent details disclosure stays anchored to the bottom. Collapsed it reads as a compact client-style bar; expanded it grows upward while the torrent list scrolls above it.


## Explicit update checks

Settings → Updates must not initiate a GitHub network check merely because the page is opened. Cached/local release information may render immediately, but freshness is user-directed through the Check for updates action. This keeps network activity predictable and preserves a clear distinction between viewing update settings and requesting an update check.

When the Torrent details disclosure has no selected torrent, the compact handle should remain visually quiet: show only the stable Torrent details label and disclosure affordance. Selection-specific copy appears only when a torrent is actually selected.


## Server-selection defaults

All servers is an aggregation mode, not a pseudo-client. It should be offered only when aggregation has meaning.

- With exactly one enabled download client, select that client automatically and omit All servers from the selector so client-specific commands are immediately available.
- With multiple enabled clients, expose All servers and restore the user's last valid server selection when possible.
- If a remembered client is disabled or removed, recover predictably: use All servers when multiple enabled clients remain, or the sole enabled client when only one remains.
- Server selection is a local interface preference; changing it does not modify dashboard configuration.


## Add Torrent source and content workflow

Add Torrent treats a magnet/URL and a local `.torrent` file as distinct source modes rather than presenting them as interchangeable controls in one field group.

- **Magnet link** accepts one magnet URI or HTTP(S) torrent URL and may begin metadata retrieval while the user continues configuring the torrent.
- **.torrent file** provides a dedicated drag-and-drop target that also opens the platform file picker when clicked.
- Once metadata is available, Content becomes an interactive file tree. Files can be included or excluded individually, and folder selection applies to every descendant file with mixed selections represented by an indeterminate state.
- Included files may retain qBitTorrent's Normal, High, or Maximum priority; excluded files are submitted as Do not download.
- Local `.torrent` files are parsed through qBitTorrent before add so selected file priorities can be applied through qBitTorrent's cached-metadata add path. Direct file upload remains a fallback when metadata parsing is unavailable.
- Save `.torrent` file is available for a selected local file without a network round trip. For magnet/URL metadata, Torrent Dashboard first uses qBitTorrent's metadata cache and may fall back to exporting an already-existing torrent by its canonical torrent ID.

## Hierarchical torrent content selection

Add Torrent keeps selection controls in one stable checkbox column so scanning and bulk selection remain predictable. The content column reserves one fixed disclosure slot on every row: folders use a Material disclosure icon and files use an equal-width spacer. Hierarchy indentation is applied after that shared slot, so child files visibly sit beneath their parent folder labels while Size and Priority remain aligned. Column labels describe the table directly: Name is left-aligned at the start of its column, folder rows do not repeat descendant file counts in the Priority column, and the live file/size summary makes a separate Content heading unnecessary.

For the persistent Torrent details dock, clicking the torrent whose details are already selected clears that detail context and returns the dock to its empty collapsed state. Selecting a different torrent replaces the context and expands the dock normally. The detail context must also be reconciled against each refreshed torrent list: if the selected server/hash no longer exists, clear the stale detail selection automatically. The disclosure bar is the single selection-identity surface; do not repeat the torrent title/hash in a second header immediately above the detail tabs.


## Configurable torrent columns

The torrent table is a user-configurable local workspace, and column management lives where the columns are used.

- **Name** is visible by default but is otherwise a normal configurable data column. The selection checkbox and row-actions control are the only fixed outer-edge columns.
- On desktop/tablet, drag a visible torrent data header horizontally to change its position. Drag the right edge of a visible data header to resize that column; resizing takes exclusive control of the pointer. During an active resize, defer torrent-row DOM rendering until the gesture ends so live polling cannot move the target.
- Torrent names and other text columns should consume the width actually assigned to their cell. Use ellipsis only when the rendered cell is actually narrower than its content; it is an overflow treatment, not a fixed historical width cap.
- Right-click anywhere on the torrent header bar to open the **Columns** menu. Every data column, including Name, can be shown or hidden there; **Reset columns** restores the documented default order/visibility and clears custom widths.
- Click a data-column header to sort by that field. Clicking the active sort header toggles ascending/descending; the active direction is shown with the local Material-style chevron and exposed through `aria-sort`.
- Header sorting, header reordering, and edge resizing are separate gestures. Completing a resize or reorder must not accidentally trigger a sort click.
- Torrent header labels follow the table's normal content flow rather than being centered as a resize aid. Resize discovery belongs to the internal edge gutter and divider, so label placement should not distort the relationship between headers and row content.
- The sort choice is a browser-local preference and remains compatible with existing `tdSort` values from the retired sort dropdown.
- The available column catalog includes Name, Size, Progress, Status, Seeds, Peers, Download, Upload, ETA, Ratio, Category, Tags, Tracker, and Added. Seeds, Peers, Category, and Tags are part of the default visible layout.
- The Dashboard keeps the status tabs (All, Downloading, Completed, Paused) plus one text search. Search matches torrent name, category, tags, and tracker; separate Category/Tags/Tracker dropdown filters are intentionally omitted because they duplicate searchable metadata.
- Retired metadata-filter preferences must be cleared during migration so an old hidden Category/Tag/Tracker selection can never continue filtering the table after its control is removed.
- Column order, visibility, width, and sort are browser-local presentation preferences. They must not mutate shared dashboard configuration or affect another user's browser.
- When Size or Category is promoted to its own visible column, the Name cell should avoid repeating the same value in its secondary summary line.
