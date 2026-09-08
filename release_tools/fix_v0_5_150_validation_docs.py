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


if __name__ == "__main__":
    main()
