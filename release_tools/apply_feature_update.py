#!/usr/bin/env python3
"""Apply the staged v0.5.96 update with the corrected design-language assertion."""
from __future__ import annotations

import subprocess

source = subprocess.check_output(
    ["git", "show", "HEAD^:release_tools/apply_feature_update.py"],
    text=True,
)
old = "assert 'header labels follow the alignment of their body cells' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')"
new = "assert 'Header labels follow the alignment of their body cells' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')"
if source.count(old) != 1:
    raise RuntimeError(f"Expected one staged design-language assertion, found {source.count(old)}")
source = source.replace(old, new, 1)
exec(compile(source, "apply_feature_update.py", "exec"))
