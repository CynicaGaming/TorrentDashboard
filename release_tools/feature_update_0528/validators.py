#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)

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

workflow = read('.github/workflows/release.yml')
workflow = replace_once(
    workflow,
    '''          assert "btn.hidden=stored" in app_js
          assert "visibility_lock" in app_js and "visibility'" in app_js
          assert 'material-symbols-outlined' in app_css
          assert '.secret-input.stored-secret' in app_css
          assert '.secret-toggle:disabled' not in css
          assert 'fonts.googleapis.com' in html
          assert 'fonts.gstatic.com' in dashboard_source
          assert '<h2>Settings</h2><p id="clientSettingsClientName">qBitTorrent</p>' in html
          assert 'class="client-switch"' in html
          assert '>Save</button><button class="secondary" data-client-settings-close' in html
          assert '>Client Settings</button>' not in app_js
          assert '>Settings</button>' in app_js
''',
    '''          assert "btn.hidden=stored" in app_js
          assert 'function secretToggleSvg' in app_js and 'material-symbol-icon' in app_js
          assert "visibility_lock" in app_js and "visibility'" in app_js
          assert 'material-symbols-outlined' not in app_css
          assert '.secret-input.stored-secret' in app_css
          assert '.secret-toggle:disabled' not in css
          assert 'fonts.googleapis.com' not in html
          assert 'fonts.gstatic.com' not in dashboard_source
          assert 'id="passwordConfirmModal"' in html
          assert 'accountProfilePassword' not in html and 'accountProfilePassword' not in app_js
          assert 'accountAvatarBtn' not in html and 'accountAvatarBtn' not in app_js
          assert '/api/client-settings' in dashboard_source and '/api/client-settings' in js
          assert 'clientAltDl' in html and 'clientAltUl' in html
          assert 'clientListenPort' in html and 'clientProxyType' in html
          assert 'def update_client_settings(self, data):' in dashboard_source
          assert '>Client Settings</button>' not in app_js
          assert '>Settings</button>' in app_js
''',
    'workflow source assertions',
)
workflow = replace_once(
    workflow,
    "          assert sample['name'] == 'Desktop'\n",
    "          assert sample['name'] == 'Desktop'\n          assert dashboard.normalize_qbittorrent_proxy_type(4) == 'socks5'\n          assert dashboard.normalize_qbittorrent_proxy_type('SOCKS4') == 'socks4'\n          assert dashboard.encode_qbittorrent_proxy_type('http', True, 1) == 3\n          assert dashboard.encode_qbittorrent_proxy_type('socks5', False, 'SOCKS5') == 'SOCKS5'\n",
    'workflow proxy compatibility tests',
)
write('.github/workflows/release.yml', workflow)

sw = read('static/sw.js').replace('0.5.27', '0.5.28')
write('static/sw.js', sw)
