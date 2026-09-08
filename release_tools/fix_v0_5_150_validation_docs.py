from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def ensure_section(path: Path, marker: str, section: str) -> None:
    text = path.read_text(encoding="utf-8")
    if marker in text:
        return
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text + "\n" + section.strip() + "\n", encoding="utf-8")


def main() -> None:
    ensure_section(
        ROOT / "DESIGN_LANGUAGE.md",
        "Content-fit desktop Torrent details",
        """
## Content-fit desktop Torrent details

Desktop Torrent details should size to the finite content of the active detail tab instead of reserving a fixed-height region that creates unnecessary dead space. General may use its natural content height within the existing clamp, while long tracker, peer, HTTP-source, and content views keep their bounded internal scrolling behavior. The torrent list remains independently scrollable and yields space to the detail pane when necessary.
""",
    )
    ensure_section(
        ROOT / "DESIGN_LANGUAGE.md",
        "Stable desktop torrent workspace height",
        """
## Stable desktop torrent workspace height

The desktop torrent workspace derives list height from viewport size, the workspace's stable document position, rendered row height, and the active detail pane's measured need. Normal document scrolling must not change the computed list height; only meaningful layout inputs such as viewport height, density, row geometry, or active detail content should trigger recomputation.
""",
    )
    ensure_section(
        ROOT / "DESIGN_LANGUAGE.md",
        "## Client-style dashboard workspace",
        """
## Client-style dashboard workspace

The Dashboard keeps normal page hierarchy in the top bar while the torrent list and persistent Torrent details inspector form one client-style workspace beneath it. The list remains the primary independently scrollable surface; Torrent details is bottom-anchored within that workspace and expands without replacing the page header or automatically scrolling the document.
""",
    )
    ensure_section(
        ROOT / "DESIGN_LANGUAGE.md",
        "Fixed torrent list and natural-height desktop details",
        """
## Fixed torrent list and natural-height desktop details

On desktop, the torrent list uses the computed viewport allocation while a finite General detail view may take its natural content height. The list and details retain independent sizing responsibilities so finite content does not create dead space and long detail views can continue using bounded internal scrolling.
""",
    )
    ensure_section(
        ROOT / "DESIGN_LANGUAGE.md",
        "### Torrent sort chevrons",
        """
### Torrent sort chevrons

Torrent sort chevrons remain inline with their owning label, preserve the text/numeric alignment of the column, and do not float against a column edge or alter header geometry when sort direction changes.
""",
    )

    ensure_section(
        ROOT / "TESTING.md",
        "Desktop Torrent details content-fit sizing",
        """
### Desktop Torrent details content-fit sizing

- Open General on desktop with a selected torrent and verify the detail pane fits its finite content without a large empty region.
- Switch to Trackers, Peers, HTTP sources, and Content and verify long content remains internally scrollable without forcing the entire page to grow unexpectedly.
- Resize through common desktop heights and confirm the torrent list yields enough space for the active detail pane while retaining the three-row minimum.
""",
    )
    ensure_section(
        ROOT / "TESTING.md",
        "Desktop torrent workspace scroll stability",
        """
### Desktop torrent workspace scroll stability

- Record the torrent-list height, scroll the document without resizing, and allow several polling cycles; the list height must remain stable.
- Change viewport height or density and verify the list height recomputes from the new geometry.
- Confirm opening or switching detail tabs does not cause an automatic document scroll and that list/detail scrolling remain independent.
""",
    )
    ensure_section(
        ROOT / "TESTING.md",
        "### Bottom-anchored torrent dock",
        """
### Bottom-anchored torrent dock

- On desktop, confirm the normal Dashboard top-bar heading remains visible while the torrent list and Torrent details stay grouped below it.
- Expand and collapse Torrent details and verify the list remains independently scrollable and the document does not jump automatically.
- With no selection, verify the disclosure remains quiet; with a selection, verify the disclosure identifies the selected torrent without duplicating its identity in a second detail header.
""",
    )
    ensure_section(
        ROOT / "TESTING.md",
        "Fixed desktop torrent list with natural General details",
        """
### Fixed desktop torrent list with natural General details

- Open General on desktop and verify finite detail content uses natural height while the torrent list retains its computed viewport allocation.
- Switch to a long detail tab and confirm its body becomes internally scrollable instead of growing the whole page without bound.
- Recheck list/detail sizing after viewport and density changes.
""",
    )
    ensure_section(
        ROOT / "TESTING.md",
        "### Torrent sort chevrons",
        """
### Torrent sort chevrons

- Sort text and numeric columns in both directions and verify each chevron stays immediately beside its label.
- Confirm numeric headings remain right-aligned, text headings remain left-aligned, and the chevron does not move to the column boundary.
""",
    )


if __name__ == "__main__":
    main()
