#!/usr/bin/env python3
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = "93b9b1dc978b44a7b3eea89c496a03af6c6bd14c"
PATH = "release_tools/validate_ui_strings.py"

text = subprocess.check_output(
    ["git", "show", f"{BASELINE}:{PATH}"],
    cwd=ROOT,
    text=True,
    encoding="utf-8",
)

load_marker = '    dashboard_py = (ROOT / "dashboard.py").read_text(encoding="utf-8")\n'
if text.count(load_marker) != 1:
    raise SystemExit("Could not locate validator source-load section")
text = text.replace(
    load_marker,
    load_marker + '    sw = (ROOT / "static" / "sw.js").read_text(encoding="utf-8")\n',
    1,
)

print_marker = '    print("UI string audit passed")\n'
if text.count(print_marker) != 1:
    raise SystemExit("Could not locate validator completion marker")
recovery_checks = '''    # v0.5.41 recovery boundary: never mix a stale app shell with JavaScript\n    # from another build, and keep browser/network failures observable.\n    assert 'Frontend build mismatch' in dashboard_py\n    assert 'requested != VERSION' in dashboard_py\n    assert "event.request.mode==='navigate'" in sw\n    assert "url.pathname==='/'" in sw\n    assert '[Torrent Dashboard]' in settings_js\n    assert '__tdFetchDiagnostics' in settings_js\n    assert '__tdReportError' in app_js\n\n'''
text = text.replace(print_marker, recovery_checks + print_marker, 1)
(ROOT / PATH).write_text(text, encoding="utf-8")

print("Restored full v0.5.38 validator with v0.5.41 recovery checks")
