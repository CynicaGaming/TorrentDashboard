#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
workflow = ROOT / ".github" / "workflows" / "release.yml"
text = workflow.read_text(encoding="utf-8")
old = "          assert 'User Management' in html\n"
new = "          assert ('User Management' in html) or ('managed under Users.' in html)\n"
if text.count(old) != 1:
    raise RuntimeError(f"expected one legacy User Management assertion, found {text.count(old)}")
workflow.write_text(text.replace(old, new, 1), encoding="utf-8")
print("Prepared release workflow for terminology cleanup.")
