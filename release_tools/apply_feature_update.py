#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

html_path = ROOT / 'static' / 'index.html'
html = html_path.read_text(encoding='utf-8')
replacements = [
    (
        'Choose which network adapters are trusted. Every selected adapter contributes its current subnet, and you can add individual IP addresses or CIDRs to the whitelist.',
        'Choose which network adapters are trusted. Every selected adapter contributes its current subnet, and you can also allow individual IP addresses or CIDRs.'
    ),
    (
        'You can add additional qBitTorrent instances, notifications, integrations, themes, trusted interfaces, and whitelist entries later under Settings.',
        'You can add additional qBitTorrent instances, notifications, integrations, themes, trusted interfaces, and allowed IP addresses later under Settings.'
    ),
    ('<b id="selectedCount">0</b> Selected', '<b id="selectedCount">0</b> selected'),
]
for old, new in replacements:
    if old not in html:
        raise SystemExit(f'missing copy cleanup source: {old}')
    html = html.replace(old, new)
html_path.write_text(html, encoding='utf-8')

validator_path = ROOT / 'release_tools' / 'validate_ui_strings.py'
validator = validator_path.read_text(encoding='utf-8')
anchor = "    assert '### Product language and capitalization' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')\n"
extra = "    assert 'whitelist' not in html.lower()\n    assert '<b id=\"selectedCount\">0</b> selected' in html\n"
if anchor not in validator:
    raise SystemExit('missing v0.5.77 validator anchor')
if extra not in validator:
    validator = validator.replace(anchor, anchor + extra, 1)
validator_path.write_text(validator, encoding='utf-8')
print('Finished v0.5.77 copy polish')
