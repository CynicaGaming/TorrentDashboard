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


## Fixed torrent columns

For the current desktop/tablet interaction model, the torrent list uses one fixed visible column set rather than exposing per-browser column customization. This deliberately trades configurability for predictable geometry while the table interaction layer is simplified.

- The visible data-column order is **Name, Size, Status, Progress, Seeds, Peers, Down, Up, ETA, Ratio, Category, Tags**. The selection checkbox remains the only fixed 40 px table rail; torrent commands are contextual rather than occupying a permanent Actions column.
- Desktop/tablet widths are deterministic proportions of the available data area after the fixed selection rail is reserved: Name 29%, Size 5%, Status 7%, Progress 20%, Seeds 4.5%, Peers 4.5%, Down 4.5%, Up 4.5%, ETA 3.5%, Ratio 4.5%, Category 6.5%, Tags 6.5%.
- Those proportions are recalculated from the live torrent viewport when the window changes size. The desktop table remains exactly viewport-width, so this fixed layout must not introduce a horizontal scrollbar.
- Header labels follow their body alignment. Size, Seeds, Peers, Down, Up, ETA, and Ratio are right-aligned; other data columns are left-aligned. Header clicks and keyboard activation continue to sort, with the active direction shown by the locally embedded chevron.
- Column resize handles, drag reorder, header visibility menus, Reset columns, spacer geometry, and browser-local `tdColumns` width/order/visibility persistence are intentionally inactive in this fixed-layout phase. Existing `tdColumns` state is discarded during migration so an old customized layout cannot leak into the fixed table.
- Name and other text cells use only their assigned cell width for ellipsis. There is no historical independent Name maximum-width cap.
- Mobile keeps the existing card presentation; the fixed desktop width calculation is cleared at the mobile breakpoint.
- Mobile metadata rows use a consistent left-label/right-value grid. Desktop numeric-column text alignment must not leak into mobile pseudo-labels or shift labels toward the card center.
- Torrent row commands use one shared context menu: right-click opens it on pointer-based desktop interfaces, while a deliberate long press opens it on touch. Touch movement cancels the pending long press so normal vertical scrolling is not intercepted.
- On mobile, the bulk-selection overlay must clear the current Torrent details pane rather than sharing its bottom stack. Its bottom offset follows the rendered detail pane so selection actions remain fully visible in both collapsed and expanded detail states.
- Sorting remains browser-local in `tdSort`. The default may still be Added descending even though Added is not one of the visible fixed columns.

### Compact mobile torrent cards

At the mobile breakpoint, torrent cards use a compact two-column metadata matrix rather than giving every desktop field a full-width row. Name and Progress remain full-width; Size/Status, Seeds/Peers, Download/Upload, ETA/Ratio, and Category/Tags share paired rows. The selection checkbox is positioned at the card's top-right without consuming layout height. Torrent names may wrap to at most two lines. Every metadata item keeps its label at the left of its local cell and its value at the right. This mobile layout is independent of the fixed desktop column proportions.

### Responsive torrent detail records

Trackers and Peers use purpose-built responsive detail records rather than inheriting the generic mobile table-to-card fallback. Desktop/tablet retains the normal labeled tables. At the mobile breakpoint, Peers presents the peer address as the record heading, client as secondary context, and labeled Progress, Download, and Upload metrics. Trackers presents a cleaned tracker name or URL, a human-readable status badge, labeled Seeds and Peers counts, and the tracker message only when one exists. qBitTorrent tracker status codes must not be exposed as unexplained numbers, and pseudo-trackers such as DHT, PeX, and LSD must not display literal Markdown-style asterisks. The General tab remains an independent presentation and is not altered by this responsive record treatment.

### Stable desktop torrent workspace height

On desktop/tablet, the torrent workspace has one bounded height derived from the viewport and its fixed document position. Ordinary document scrolling must never change that height. The torrent list keeps its own vertical scroller inside the bounded workspace, while expanding/collapsing Torrent details only reallocates space inside that same workspace. Viewport resizing may legitimately recalculate the workspace height; page scroll position must not be an input to that calculation.

### Content-fit desktop Torrent details

The desktop torrent workspace remains a fixed bounded surface. When Torrent details is expanded on the finite General tab, the detail pane should measure its rendered content and claim enough height inside that fixed workspace to show the complete General view without an unnecessary inner scrollbar whenever the viewport can accommodate it. Preserve a usable torrent-list slice and its independent scrollbar. Potentially unbounded tabs such as Trackers, Peers, HTTP sources, and Content remain bounded and independently scrollable rather than expanding the workspace or consuming the entire torrent list.



### Fixed torrent list and natural-height desktop details

This supersedes the earlier shared-height desktop workspace compromise. On desktop/tablet, the torrent list owns a stable bounded height and its own vertical scrollbar; opening Torrent details must not resize that list. The finite General detail view may extend the document below the list and should use its natural content height so routine properties are readable without an inner scrollbar. Potentially unbounded detail tabs such as Trackers, Peers, HTTP sources, and Content remain bounded and internally scrollable. Page scrolling may move the combined list/detail surfaces through the viewport, but must not change the torrent list height. Torrent Dashboard branding and browser/PWA iconography remain local assets with no external runtime dependency.


### Desktop Torrent details viewport reveal

The fixed desktop torrent-list height and natural-height General detail model remain unchanged. The dashboard header, metrics, and filter controls are ordinary document content above the torrent workspace and must not be folded into a new detail-height calculation. When a user explicitly expands Torrent details from a collapsed state on desktop/tablet, the document should reveal the torrent workspace at the top of the viewport so those preceding panels scroll out naturally. This reproduces the useful manual-scroll state without shrinking the torrent list or reintroducing an inner General scrollbar. Respect reduced-motion preferences and do not force this reveal repeatedly while the detail pane is already expanded.


### Six-row desktop torrent viewport

The desktop torrent list is a deterministic data viewport rather than a remainder of the browser viewport. Its height is the rendered torrent-table header plus exactly six normal torrent rows, including the current density's row height and the panel border allowance. Header, metric, filter, login/profile, and Torrent details geometry must not change that list height. If fewer than six rows are visible, leaving unused whitespace in the list is acceptable. If more than six rows are visible, the list scrolls internally. Torrent details remains a separate surface below the list; General may use natural document height while long-data tabs retain bounded internal scrolling.


### Adaptive desktop torrent viewport fit

The desktop torrent list uses six rows as a preferred maximum, not an unconditional fixed height. The dashboard computes a stable viewport budget from the torrent workspace's document position and the browser height, then subtracts the currently rendered Torrent details pane and the workspace gap. The remaining space is snapped down to a whole number of rendered torrent rows, with three rows as the minimum useful desktop list. This keeps the expanded General pane and the torrent list inside the original top-of-page viewport whenever the available geometry permits, without making the list react to document scrolling. General remains natural-height; long-data detail tabs retain their bounded internal scrolling. Opening Torrent details must not force the document to scroll because the layout itself is responsible for fitting the workspace.


### Viewport-proportional desktop torrent workspace

The expanded desktop torrent workspace should preserve the visual balance established by the v0.5.112 layout across different monitor heights. The torrent list prefers roughly 44% of the usable viewport remaining below the workspace's stable document position, while Torrent details receives the rest. The split is not a hard percentage: the rendered detail pane has priority, and the list shrinks when necessary so finite General content remains fully readable. The list height is always snapped to complete rendered torrent rows with a three-row minimum, and taller viewports may expose more than six rows instead of leaving unnecessary dead space. Document scrolling must not change the calculation; browser height and density changes may recompute it.


### Torrent sort chevrons

Torrent-table header labels continue to align with their body data: text-oriented headers remain left-aligned and numeric headers remain right-aligned. The sort affordance itself is independent of that text alignment. Every sortable torrent header uses the same trailing/right-edge chevron position so the indicator is visually associated with its owning column and never appears to belong to the neighboring column.


### Torrent sort indicator grouping

- Sortable torrent headers treat the label and chevron as one inline visual group.
- Text-oriented header groups align left; numeric header groups align right to match their body values.
- The chevron always follows the owning label with a small fixed gap rather than floating at an unrelated column edge.
- Hover, focus, and active-sort emphasis must not change the indicator's geometry.


### Persistent Torrent Details shell

- On desktop, Torrent Details remains a stable structural part of the dashboard even when no torrent is selected.
- The no-selection state renders the normal General structure and keeps Trackers, Peers, HTTP sources, and Content tabs available without explanatory empty-state copy.
- Static em-dash placeholders communicate unavailable values; animated skeletons are reserved for the brief interval after a real torrent is selected and detail data is loading.
- Mobile keeps Torrent Details collapsed by default so the persistent shell does not obscure the dashboard, but opening it exposes the same no-selection templates.
- The desktop no-selection General template participates in the existing viewport/detail fitting contract rather than introducing a second sizing model.


### Header completion notification inbox

- The application header includes a locally embedded Material-style notification bell beside the client controls and account control.
- The bell is a compact transient inbox for completed torrents, not a duplicate of the full Notifications destination. Its unread badge and recent list follow the currently selected client scope.
- Opening the bell marks the currently visible completion entries as seen while leaving them in the bell. **Clear** dismisses the bell's current completion entries only in that browser.
- Bell seen/cleared state is browser-local presentation state. Clearing the bell must never delete or mutate the durable server-side event history.
- **View all notifications** opens the main Notifications view, which remains the detailed history for torrent, security, account, update, integration, and system events.
- The popover must remain above mobile Torrent Details and bulk-action layers and must not introduce header overflow on narrow screens.


## Add Torrent folder disclosure actions

The Add Torrent content preview keeps per-folder chevrons as the primary local disclosure control and adds **Expand all** / **Collapse all** as compact secondary actions beside the file summary. The actions operate only on the currently loaded metadata tree; they do not change file selection, priority, or torrent add options.

The controls remain disabled until the metadata contains at least one folder. **Expand all** is disabled when every folder is already open, and **Collapse all** is disabled when every known folder path is already collapsed. Bulk disclosure must preserve the same folder ordering, indentation, checkbox state, and file-priority state used by individual folder toggles.

On narrow layouts the summary stays above the two disclosure actions and the actions share the available row width rather than forcing the content preview wider than the modal.
