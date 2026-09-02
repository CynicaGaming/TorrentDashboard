#!/usr/bin/env python3
from pathlib import Path

HERE = Path(__file__).resolve().parent
impl = HERE / "apply_feature_update_impl.py"
source = impl.read_text(encoding="utf-8")

replacements = [
    ("join('\\n')", "join('\\\\n')", "trusted-IP newline escape"),
    ('aria-labelledby="clientSettingsTitle"', 'aria-label="Client settings"', "client settings accessible name"),
    ('<h2 id="clientSettingsTitle">Settings</h2>', '<h2>Settings</h2>', "client settings heading contract"),
]
for old, new, label in replacements:
    if source.count(old) != 1:
        raise RuntimeError(f"{label}: expected one match, found {source.count(old)}")
    source = source.replace(old, new, 1)

namespace = {"__file__": str(impl), "__name__": "__main__"}
try:
    exec(compile(source, str(impl), "exec"), namespace)
finally:
    impl.unlink(missing_ok=True)
