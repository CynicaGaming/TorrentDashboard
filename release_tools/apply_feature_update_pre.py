#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "static" / "app.js"
text = path.read_text(encoding="utf-8")
old = "if(state.selected.size){state.selected.clear();render();return}closeDetailPane()}});"
new = "if(state.selected.size){state.selected.clear();render();return}if(state.detailExpanded){state.detailExpanded=false;syncDetailDock()}}});"
count = text.count(old)
if count != 1:
    raise SystemExit(f"Escape detail collapse migration: expected one match, found {count}")
path.write_text(text.replace(old, new, 1), encoding="utf-8")
print("Migrated Escape from closing torrent details to collapsing them")
