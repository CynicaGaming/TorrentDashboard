#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "release_notes" / "releases.json"

data = json.loads(META.read_text(encoding="utf-8"))
releases = data.get("releases")
if not isinstance(releases, list):
    raise RuntimeError("release_notes/releases.json has no releases list")

previous = next((item for item in releases if isinstance(item, dict) and str(item.get("version")) == "0.5.106"), None)
current = next((item for item in releases if isinstance(item, dict) and str(item.get("version")) == "0.5.107"), None)
if previous is None or current is None:
    raise RuntimeError("Expected both v0.5.106 and v0.5.107 release metadata")

decisions = list(previous.get("decisions") or [])
new_decision = "Calculate desktop torrent workspace height from its stable document position rather than its scroll-relative viewport position; document scrolling must not resize the workspace."
if new_decision not in decisions:
    decisions.append(new_decision)
current["decisions"] = decisions

META.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
subprocess.run(
    [sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", "0.5.107"],
    cwd=ROOT,
    check=True,
)
print("Preserved v0.5.107 engineering decisions")
