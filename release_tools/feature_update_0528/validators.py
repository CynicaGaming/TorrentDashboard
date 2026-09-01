#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")

def regex_once(text: str, pattern: str, replacement: str, label: str, flags: int = 0) -> str:
    out, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one regex match, found {count}")
    return out

validator = read('release_tools/validate_ui_strings.py')
validator = regex_once(
    validator,
    r'    # 0\.5\.26 qBitTorrent-style toolbar and per-client settings\..*?    assert \'0\.5\.27 client settings facelift\' in settings_css\n',
    '''    # 0.5.28 local secret icons, secure account changes, and curated client settings.
    assert 'id="addBtn"' not in html and 'id="moreBtn"' not in html
    assert 'id="addLinkBtn"' in html and 'id="addFileBtn"' in html
    assert 'function secretToggleSvg' in app_js and 'material-symbol-icon' in app_js
    assert 'visibility_lock' in app_js and "visibility'" in app_js
    assert 'material-symbols-outlined' not in app_css
    assert 'fonts.googleapis.com' not in html and 'fonts.gstatic.com' not in dashboard_py
    assert 'id="loginPass"' in html and 'autocomplete="current-password"' in html
    assert 'id="accountAvatarBtn"' not in html and 'accountAvatarBtn' not in app_js
    assert 'id="accountProfilePassword"' not in html and 'accountProfilePassword' not in app_js
    assert 'id="passwordConfirmModal"' in html and 'requestPasswordConfirmation' in app_js
    assert 'password_configured' in dashboard_py
    assert 'Default Torrent Dashboard Sound' not in html and '<option value="default">Default</option>' in html
    assert ' · You' not in settings_js and 'Current user' in settings_js
    assert 'id="clientSettingsModal"' in html and 'id="clientSettingsForm"' in html
    for field in ('clientGlobalDl','clientGlobalUl','clientAltDl','clientAltUl','clientListenPort','clientMaxConnections','clientProxyType','clientProxyHost','clientProxyPort','clientProxyPassword'):
        assert f'id="{field}"' in html
    assert 'data-client-settings-tab="speed"' in html and 'data-client-settings-tab="connection"' in html and 'data-client-settings-tab="proxy"' in html
    assert '/api/client-settings' in dashboard_py and '/api/client-settings' in settings_js
    assert 'def client_settings(self):' in dashboard_py and 'def update_client_settings(self, data):' in dashboard_py
    assert '/api/v2/app/setPreferences' in dashboard_py
    assert 'proxy_password' in dashboard_py and 'password_configured' in dashboard_py
    assert 'preferences = client.preferences()' in dashboard_py and 'disk_free = disk_free_for(preferences)' in dashboard_py
    assert '0.5.26 qBitTorrent-style torrent toolbar' in app_css
    assert '0.5.28 advanced per-client qBitTorrent settings' in settings_css
''',
    'validator 0.5.28 contract',
    re.S,
)
write('release_tools/validate_ui_strings.py', validator)

# The Actions workflow is loaded before this staged updater executes. Its 0.5.28
# source contract therefore lives directly in .github/workflows/release.yml.
# Keep this helper focused on files that can be safely materialized during the run.
sw = read('static/sw.js').replace('0.5.27', '0.5.28')
write('static/sw.js', sw)
