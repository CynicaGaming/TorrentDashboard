#!/usr/bin/env python3
from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'release_tools' / 'validate_ui_strings.py'
text = path.read_text(encoding='utf-8')
old = "    assert 'const savedRepository = String(state.settings?.updates?.repository || '');' in settings_js\n"
new = "    assert \"const savedRepository = String(state.settings?.updates?.repository || '');\" in settings_js\n"
if text.count(old) != 1:
    raise RuntimeError(f'expected one savedRepository validator line, found {text.count(old)}')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
print('Corrected v0.5.34 validator quote matching.')
