#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / 'release_tools' / 'validate_ui_strings.py'
text = path.read_text(encoding='utf-8')
old = '''    assert "resetDirtyScope('settingsCore',true);\n      return d;" not in settings_js.split('async function saveUpdateSource()',1)[1].split('async function loadExtras()',1)[0]
'''
# The previous generated validator contains an actual newline inside the quoted
# expression, so match that exact malformed source rather than weakening the check.
malformed = '''    assert "resetDirtyScope('settingsCore',true);
      return d;" not in settings_js.split('async function saveUpdateSource()',1)[1].split('async function loadExtras()',1)[0]
'''
new = '''    update_source_section = settings_js.split('async function saveUpdateSource()',1)[1].split('async function loadExtras()',1)[0]
    assert "resetDirtyScope('settingsCore',true);" not in update_source_section
'''
if malformed in text:
    text = text.replace(malformed, new, 1)
elif old in text:
    text = text.replace(old, new, 1)
else:
    raise RuntimeError('malformed update-source dirty-state assertion was not found')
path.write_text(text, encoding='utf-8')
print('Fixed v0.5.34 packaging validator syntax.')
