#!/usr/bin/env python3
from __future__ import annotations
import runpy
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTS = ROOT / "release_tools" / "feature_update_0528"
for name in ("backend.py","html.py","appjs.py","settingsjs.py","css.py","validators.py"):
    part = PARTS / name
    text = part.read_text(encoding="utf-8")
    text = text.replace('ROOT = Path(__file__).resolve().parents[1]', 'ROOT = Path(__file__).resolve().parents[2]', 1)
    part.write_text(text, encoding="utf-8")
    runpy.run_path(str(part), run_name="__main__")
shutil.rmtree(PARTS, ignore_errors=True)
print("Applied 0.5.28 account, icon, and advanced client-settings update.")
