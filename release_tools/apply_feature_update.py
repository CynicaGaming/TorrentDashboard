#!/usr/bin/env python3
from pathlib import Path
import subprocess

# Reuse the complete v0.5.89 staged migration from the parent commit and add
# the one superseded historical validator assertion discovered by the gate.
source = subprocess.check_output(
    ["git", "show", "HEAD^:release_tools/apply_feature_update.py"],
    text=True,
)
needle = 'validator = read("release_tools/validate_ui_strings.py")'
replacement = needle + '''\nold_resize_wording = "    assert 'Drag the narrow right edge' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')"\nnew_resize_wording = "    assert 'Drag the right edge' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')"\nvalidator = replace_once(validator, old_resize_wording, new_resize_wording, "superseded resize wording validator assertion")'''
if source.count(needle) != 1:
    raise RuntimeError("Could not locate validator load in parent staged migration")
source = source.replace(needle, replacement, 1)
namespace = {"__name__": "__main__", "__file__": __file__}
exec(compile(source, __file__, "exec"), namespace)
