#!/usr/bin/env python3
from __future__ import annotations
import runpy
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTS = ROOT / "release_tools" / "feature_update_0528"
for name in ("backend.py","html.py","appjs.py","settingsjs.py","css.py","validators.py"):
    runpy.run_path(str(PARTS / name), run_name="__main__")
shutil.rmtree(PARTS, ignore_errors=True)
print("Applied 0.5.28 account, icon, and advanced client-settings update.")
