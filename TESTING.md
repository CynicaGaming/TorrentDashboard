# Torrent Dashboard Testing Guide

Automated checks are the release gate; this document records the manual verification that still depends on a browser, qBitTorrent instance, operating system, or update/restart behavior.

## Automated baseline

Run before and after a development increment:

```bash
python release_tools/validate_source.py
python release_tools/validate_ui_strings.py
node --check static/app.js
node --check static/settings.js
```

For a release candidate also verify generated documentation:

```bash
python release_tools/generate_release_notes.py --version X.Y.Z --check
```

The Python suite uses only the standard library and currently covers extracted domain behavior, configuration transactions, release/provenance parsing and persistence, and source/architecture contracts.

## Manual smoke-test matrix

Only run tests that are relevant and safe in your environment. Never commit real credentials or private infrastructure details while documenting results.

### Startup and setup

- Fresh installation opens the first-run wizard.
- Setup completes with a reachable qBitTorrent instance.
- A failed client connection does not save partial setup state.
- Restarting after setup returns to the dashboard rather than the wizard.

### Authentication and roles

- Administrator login succeeds and administrative Settings/actions are available.
- Standard User login can view permitted dashboard/account surfaces and cannot perform administrator-only mutations.
- Logout invalidates the current session.
- Trusted-network behavior matches the configured access mode.

### Dashboard live state

- Dashboard refreshes without visibly reloading the page.
- Download/upload metrics and torrent counts reflect qBitTorrent state.
- Empty-state copy matches the real reason no rows are visible.
- Connection failures use the error banner and recover when connectivity returns.
- Search, category, tag, tracker, and status filters remain stable while polling.

### Torrent actions

- Start/resume, pause/stop, recheck, delete, force start, and location actions behave as expected for an administrator.
- Bulk actions operate only on selected torrents.
- Destructive actions require the expected confirmation.
- Standard Users cannot invoke administrator-only torrent mutations.

### Torrent details

- The docked torrent-details bar is always present on desktop/tablet and starts collapsed with no selection.
- Clicking the disclosure bar expands/collapses the inspector without clearing the selected torrent.
- Selecting a torrent automatically expands the inspector and updates the selected-torrent context.
- Expanding with no torrent selected shows the empty detail state without errors.
- Torrent list and detail body scroll independently when needed.
- General, Trackers, Peers, HTTP Sources, and Content tabs render without errors.
- Mobile keeps the persistent collapsed bar and uses the bottom-sheet presentation when expanded.

### Add Torrent

- Magnet/URL submission follows the normal qBitTorrent add path.
- `.torrent` upload follows the normal upload path.
- Metadata preview remains read-only and does not alter the source submitted to qBitTorrent.
- Metadata timeout/cancel paths leave the dialog usable.
- Save-as-`.torrent` is available only when metadata export is actually available.

### Settings

- General, Access, Clients, Updates, and Notifications use the shared **Settings saved** confirmation.
- User and Integration CRUD use scoped success/error language.
- Secret masks do not expose configured credentials back to the browser.
- Concurrent unrelated configuration changes do not overwrite one another.

### Updates and recovery

Use only a test installation or an environment where restart/rollback is acceptable.

- Check for updates discovers the intended public repository release.
- Patch notes show the current and previous release entries.
- Package SHA-256 values populate from authoritative release metadata.
- Downloaded update ZIP is verified before staging.
- Successful update restarts into the expected version.
- Runtime `config.json` and `data/` survive the update.
- A deliberately invalid test build rolls back rather than leaving the installation unusable.

### Responsive interface

At minimum check one desktop width and one mobile width after meaningful UI changes.

Desktop/tablet:

- Text remains legible at 100% browser zoom.
- Torrent workspace does not consume the entire page when few/no torrents are present.
- Torrent list plus open detail inspector fit in the initial viewport by default.
- No controls overlap at common desktop widths.

Mobile:

- Navigation remains reachable.
- Tables/cards do not introduce unusable horizontal overflow.
- Torrent detail bar remains reachable, expands as a bottom sheet, and collapses again with a full-width touch target.
- Dialogs remain operable with the on-screen keyboard present.

## Recording gaps

If a regression cannot reasonably be automated yet, record the missing coverage in `development/current.json` or the next release metadata and add it to this matrix if it is a recurring verification need.

Do not use this file as a test-results log; it is a stable testing contract for upstream and forks.

### Desktop torrent inspector

- With no torrent selected, verify the compact Torrent details bar remains visible below the torrent list without consuming the expanded workspace height.
- With a torrent selected at normal desktop zoom, verify the inspector expands automatically and the torrent list and inspector both remain visible without scrolling the overall page.
- Collapse the inspector and verify the selected row remains selected; expand it again and verify the same torrent details return.
- Verify the torrent inspector reaches the bottom of the visible dashboard content and is visually separated from the torrent list as its own bordered panel.
- Verify General, Trackers, Peers, HTTP Sources, and Content have a useful vertical viewport and scroll internally when needed.
- Resize the browser and verify the dock recalculates without overlapping the viewport; mobile continues to use the bottom-sheet presentation.


### Bottom-anchored torrent dock

- Verify Dashboard / Live torrent activity is visible on Dashboard while top-right controls remain available.
- With details collapsed, verify the disclosure bar sits at the bottom of the visible dashboard workspace.
- Expand details and verify the inspector grows upward from the same anchor while the torrent list scrolls above it.
- Resize desktop/tablet and verify both states remain bottom-aligned without overlaying torrent rows.
- Verify mobile retains the persistent collapsed bar above mobile navigation and expands into the sheet.


### Update-check intent and empty detail disclosure

- Open Settings → Updates and verify no GitHub update request is initiated solely by entering the page; cached/local release history may render immediately.
- Press Check for updates and verify the normal GitHub update lookup occurs and refreshes update/release-integrity information.
- With no torrent selected, verify the collapsed Torrent details bar contains no “No torrent selected” helper text.
- Select a torrent and verify the selected torrent name may appear in the disclosure context and the inspector expands normally.


### Server-selection defaults

- With exactly one enabled qBitTorrent client, verify that client is selected automatically and All servers is not offered in the server selector.
- With one enabled client, verify Add Torrent and other client-specific actions are immediately available without first changing the server selector.
- With two or more enabled clients, verify All servers is available as an aggregation choice.
- With multiple clients, select a specific client, reload the dashboard, and verify the valid previous selection is restored.
- Disable or remove the remembered client and verify the dashboard falls back to All servers when multiple clients remain, or automatically selects the sole remaining enabled client.


### Product language and capitalization

- Verify setup, sign-in, Dashboard, Settings, Add torrent, account, and client-settings surfaces after a copy-system change.
- Confirm named destinations retain their intended label casing while headings, labels, actions, statuses, errors, and explanatory copy use natural sentence case.
- Confirm qBitTorrent, Torrent Dashboard, GitHub, API, Web API, HTTP, IP, URL, SHA-256, and `.torrent` keep their established capitalization.
- Confirm authored copy does not visibly change after JavaScript initializes or after dynamically generated controls are inserted.
- Verify access controls say **Allowed IP addresses** rather than whitelist language and client-management actions use **client** where that is the user-facing concept.
- Verify validation and toast messages contain no camelCase tokens, internal field names, or mechanically recased technical terms.


### Add Torrent source modes and file selection

- Open Add Torrent and verify **Magnet link** and **.torrent file** are separate source tabs; switching tabs never causes the inactive source to be submitted.
- In Magnet link mode, paste one magnet URI and verify metadata loads without adding the torrent. Once ready, verify the Content panel shows selectable folders/files.
- Select and clear a folder and verify all descendant files follow it. Create a mixed selection and verify the parent folder and Select all controls show an indeterminate state.
- Change an included file between Normal, High, and Maximum priority, add the torrent, and verify qBitTorrent receives the corresponding file priorities. Unchecked files must arrive as Do not download.
- In .torrent file mode, click the drop area and verify the platform file picker opens. Repeat by dragging a `.torrent` file onto the drop area and verify the selected filename is shown and metadata is parsed.
- Add a parsed `.torrent` with at least one excluded file and verify the torrent is added through qBitTorrent's cached metadata with the selected files honored.
- Force metadata parsing to fail or use an older qBitTorrent build and verify a local `.torrent` can still fall back to direct upload, without selectable file priorities.
- After magnet metadata is ready, use **Save .torrent file** and verify a non-empty `.torrent` downloads. Repeat with a source whose torrent already exists in qBitTorrent and verify export fallback succeeds.
- In .torrent file mode, use **Save .torrent file** and verify the originally selected local file is downloaded without requiring qBitTorrent metadata cache availability.

### Add Torrent hierarchy and detail-selection reconciliation

- Load a multi-folder torrent in Add Torrent and verify every folder/file checkbox remains vertically aligned in the same selection column.
- Verify folder rows use the locally embedded Material disclosure icon and file rows reserve an equal-width spacer. A child file label must begin to the right of its parent folder label; deeper descendants should continue stepping right by hierarchy depth.
- Verify the Name header is left-aligned at the beginning of the name column, Size and Priority remain aligned, folder rows do not show descendant file counts, and the preview summary appears without a redundant Content heading.
- Select a torrent row and verify Torrent details expands for it. The disclosure bar should identify the selected torrent, and the expanded panel should proceed directly to the detail tabs without repeating the torrent title/hash in a second header.
- Click the same torrent row again and verify the selected-row treatment clears and Torrent details returns to the empty collapsed disclosure.
- Select one torrent and then a different torrent; verify details switch directly to the second torrent rather than clearing first.
- With a torrent selected in Torrent details, remove that torrent (or remove it directly in qBitTorrent) and verify the next status refresh clears the stale detail context and collapses the dock. Removing another torrent must not clear the current detail selection.


### Fixed torrent columns

- On desktop/tablet, verify the visible data columns appear exactly in this order: Name, Size, Status, Progress, Seeds, Peers, Down, Up, ETA, Ratio, Category, Tags. Selection must remain on the far left and there must be no dedicated Actions column.
- Verify there are no resize cursors/handles, drag-reorder gestures, Columns context menu, Reset columns action, Tracker/Added visible columns, or other column-visibility controls.
- Right-click several torrent rows and verify the shared torrent context menu opens at the pointer location with the same actions previously exposed through the ellipsis button.
- Seed browser-local `tdColumns` with an old customized order/visibility/width payload before loading and verify it is discarded and cannot affect the rendered table.
- Resize the browser through several desktop/tablet widths above the mobile breakpoint. The table must continue fitting its torrent viewport without a horizontal scrollbar; the reclaimed former Actions width should remain available to the fixed data columns.
- Verify the fixed desktop width proportions keep Name and Progress visually dominant while Size, Seeds, Peers, Down, Up, ETA, and Ratio remain compact; Category and Tags should retain enough room to be recognizable before ellipsis.
- Verify header labels match body alignment: compact numeric columns are right-aligned and the remaining columns are left-aligned. The sort chevron must not shift the visible column boundary.
- Click and keyboard-activate every visible data header and verify sorting still works and `aria-sort` follows the active direction.
- Verify an unresized Name cell reveals as much text as its assigned fixed share permits and ellipsizes only when that actual cell width is insufficient.
- Hold the dashboard open across several one-second polling intervals and browser resizes; row content and fixed widths must remain stable without column jumps.
- At the mobile breakpoint, verify the existing torrent card layout returns and no desktop inline fixed widths interfere with card sizing. Long-press a non-control area of a torrent card for roughly half a second and verify the same torrent context menu opens; move/scroll before the threshold and verify no menu opens. A normal tap must still open Torrent details, while the tap following a completed long press must not.
- On mobile cards, verify Size, Status, Seeds, Peers, Download, Upload, ETA, Ratio, Category, and Tags all keep their field label at the left edge and their value at the right edge; desktop right-alignment rules must not move numeric labels toward the center divider.
- On mobile, check a torrent while Torrent details is collapsed and verify the bulk action bar is fully visible above the disclosure bar and mobile navigation. Expand Torrent details while the torrent remains checked and verify the bulk action bar moves above the expanded sheet instead of being covered by it.

### Compact mobile torrent cards

- At 820 px and below, verify each torrent card uses two metadata columns: Size/Status, Seeds/Peers, Download/Upload, ETA/Ratio, and Category/Tags. Name and Progress must span the full card width.
- Verify the selection checkbox is overlaid at the card's top-right and no longer consumes its own full-width row.
- Verify long torrent names wrap to no more than two lines and do not force horizontal overflow.
- Verify each compact metadata item keeps its label left and its value right, including the Status pill and long Category/Tags values.
- Compare several cards with v0.5.104-sized content and verify substantially more than one torrent can fit in a typical phone viewport while preserving all displayed metadata.
- Recheck long-press row actions, normal tap-to-open Torrent details, checkbox selection, and the mobile bulk-action/detail-pane stacking behavior after the grid compaction.

### Responsive tracker and peer details

- At 820 px and below, open Peers and verify each connected peer is a compact labeled record: address heading, client beneath it, then Progress, Download, and Upload metrics. No anonymous vertical value stacks should remain.
- Open Trackers and verify each record shows a cleaned tracker name/URL, a human-readable status badge, labeled Seeds and Peers counts, and a Message section only when the tracker reports one.
- Verify qBitTorrent tracker statuses 0 through 4 render as Disabled, Not contacted, Working, Updating, and Not working rather than raw numeric codes.
- Verify pseudo-trackers such as DHT, PeX, and LSD do not display literal surrounding `**` markers.
- Test a long IPv6 peer address, long client name, long tracker URL, and long tracker message; records must wrap or ellipsize without horizontal overflow.
- Above 820 px, verify Peers and Trackers remain conventional tables with visible column headers.
- Recheck General before and after switching through Trackers and Peers; its layout and content must remain unchanged.

### Desktop torrent workspace scroll stability

- On a desktop-width viewport, note the rendered torrent workspace/list height, then scroll the document above and below the workspace while live one-second polling continues. Verify the torrent workspace and torrent-list panel do not grow or shrink as a consequence of document scroll position.
- Scroll a long torrent list using the table's own vertical scrollbar and verify the list remains bounded while the page position stays independent.
- Resize the browser vertically and verify the workspace recalculates to the new viewport height, then remains stable again during document scrolling.
- Expand and collapse Torrent details and verify space is reallocated inside the fixed workspace rather than increasing the overall workspace height.
- Repeat at mobile width and verify the existing mobile bottom-sheet/list behavior is unchanged.

### Desktop Torrent details content-fit sizing

- On a normal desktop viewport, open Torrent details → General and verify the full General content is visible without scrolling the detail body when there is sufficient workspace height.
- Verify expanding General takes space from the torrent list inside the existing fixed workspace; the overall workspace height must remain unchanged and the torrent list must retain its own scrollbar.
- Collapse and re-expand Torrent details and verify the content-fit height is restored without layout growth or page-scroll coupling.
- Switch from General to Peers, Trackers, HTTP sources, and Content with long datasets and verify those tabs use the normal bounded detail height and their own internal scrolling rather than expanding to their full dataset height.
- Resize the browser vertically and verify General recalculates its fitted height while retaining a usable torrent-list region. On unusually short desktop viewports, detail-body scrolling is acceptable once the reserved list region prevents the full General content from fitting.
- Repeat at mobile width and verify the existing bottom-sheet behavior is unchanged.



### Fixed desktop torrent list with natural General details

- On desktop, record the torrent list height, scroll the page, open/collapse Torrent details, and switch tabs; the torrent list height must remain unchanged and the list must retain its own scrollbar.
- Open Torrent details → General and verify the full General content is readable without scrolling the detail body. The page may become taller and use normal document scrolling below the fixed torrent list.
- Switch to Trackers, Peers, HTTP sources, and Content with long datasets and verify those tabs remain bounded and use their own detail-body scrolling rather than expanding to their entire dataset height.
- Resize the desktop viewport and verify the torrent list recalculates only within the 360–560 px bounded range; ordinary page scrolling must not alter the chosen height.
- Verify `/static/favicon.svg` is used as the browser favicon, web-manifest icon, service-worker shell asset, and setup/login/sidebar brand mark.
- Repeat at mobile width and verify the existing mobile torrent cards and bottom-sheet Torrent details behavior are unchanged.


### Desktop Torrent details viewport reveal

- Start at the top of Dashboard with the page heading, metrics, and filters visible. Open Torrent details from its collapsed disclosure and verify the document scrolls the torrent workspace to the top of the viewport while preserving the existing torrent-list height.
- Repeat by opening a torrent row while Torrent details is collapsed; the same workspace reveal should occur.
- With Torrent details already expanded, switch torrents and detail tabs and verify the page is not repeatedly forced back to the workspace top.
- Verify General retains its natural document height and no inner scrollbar is reintroduced; Trackers, Peers, HTTP sources, and Content retain their existing bounded scrolling.
- Enable reduced-motion preference and verify the reveal is immediate rather than animated.
- Repeat at mobile width and verify the mobile bottom-sheet behavior does not invoke desktop document scrolling.
