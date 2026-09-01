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

html = read('static/index.html')
html = html.replace('0.5.27', '0.5.28')
html = regex_once(
    html,
    r'<link href="https://fonts\.googleapis\.com/[^\n]+\n',
    '',
    'remove Google Material Symbols stylesheet',
)
html = replace_once(
    html,
    '<input autocomplete="new-password" data-1p-ignore="" data-lpignore="true" id="loginPass" name="tdPass" placeholder="Password" type="password"/>',
    '<input autocomplete="current-password" data-1p-ignore="" data-lpignore="true" id="loginPass" name="tdPass" placeholder="Password" type="password"/>',
    'login password autocomplete',
)
html = replace_once(html, '<option value="default">Default Torrent Dashboard Sound</option>', '<option value="default">Default</option>', 'notification sound label')
html = replace_once(html, '<button id="accountAvatarBtn" type="button">Change profile picture</button>', '', 'remove redundant avatar menu action')
html = replace_once(
    html,
    '<label>Current password<input autocomplete="current-password" id="accountProfilePassword" placeholder="Required only to change username" type="password"/></label>',
    '',
    'remove inline profile password field',
)
html = replace_once(
    html,
    '<div class="field-help">Changing your username requires your current password. Your role can only be changed by an Administrator.</div>',
    '<div class="field-help">Username and email changes require password confirmation. Your role can only be changed by an Administrator.</div>',
    'account secure-change help',
)
html = replace_once(
    html,
    '<label>Current password<input autocomplete="current-password" id="accountCurrentPassword" type="password" required/></label>',
    '<label>Current password<input autocomplete="current-password" id="accountCurrentPassword" type="password"/></label>',
    'allow first password setup for passwordless account',
)
html = replace_once(
    html,
    '<div class="field-help">Changing your password requires the current password and a new password of at least 8 characters.</div>',
    '<div class="field-help">Changing your password requires the current password when one is already configured, and a new password of at least 8 characters.</div>',
    'password-change help',
)

secure_modal = '''<div class="modal hidden" id="passwordConfirmModal"><div class="modal-backdrop" data-password-confirm-cancel=""></div><form class="modal-card password-confirm-card" id="passwordConfirmForm"><header><div><h2>Confirm your password</h2><p id="passwordConfirmMessage">Enter your current password to continue with this secure account change.</p></div><button class="icon-btn" data-password-confirm-cancel="" type="button" aria-label="Cancel password confirmation">×</button></header><div class="password-confirm-body"><label>Password<input autocomplete="current-password" id="passwordConfirmInput" type="password" required/></label><div class="test-result muted" id="passwordConfirmStatus"></div></div><footer class="password-confirm-actions"><button class="primary" type="submit">Continue</button><button class="secondary" data-password-confirm-cancel="" type="button">Cancel</button></footer></form></div>\n'''
html = replace_once(html, '<div class="modal hidden" id="clientSettingsModal">', secure_modal + '<div class="modal hidden" id="clientSettingsModal">', 'secure password confirmation modal')

client_modal = '''<div class="modal hidden" id="clientSettingsModal"><div class="modal-backdrop" data-client-settings-close=""></div><form class="modal-card client-settings-card" id="clientSettingsForm"><header><div><h2>Settings</h2><p id="clientSettingsClientName">qBitTorrent</p></div><button class="icon-btn" data-client-settings-close="" type="button" aria-label="Close settings">×</button></header><div class="client-settings-tabs" role="tablist" aria-label="Client settings sections"><button class="active" data-client-settings-tab="speed" type="button">Speed</button><button data-client-settings-tab="connection" type="button">Connection</button><button data-client-settings-tab="proxy" type="button">Proxy</button></div><div class="client-settings-body"><section class="client-settings-pane active" data-client-settings-pane="speed"><div class="client-settings-section-heading"><strong>Transfer limits</strong><span>Set the normal and alternative global speed limits for this qBitTorrent client.</span></div><div class="client-limit-grid"><label><span>Download limit</span><span class="client-limit-input"><input id="clientGlobalDl" min="0" step="1" type="number" value="0"/><span>KB/s</span></span><small>0 means unlimited</small></label><label><span>Upload limit</span><span class="client-limit-input"><input id="clientGlobalUl" min="0" step="1" type="number" value="0"/><span>KB/s</span></span><small>0 means unlimited</small></label></div><div class="client-settings-divider" aria-hidden="true"></div><label class="client-setting-row"><span class="client-setting-copy"><strong>Alternative speed limits</strong><span>Use qBitTorrent's alternative rate profile for this client.</span></span><span class="client-switch"><input id="clientAltSpeed" type="checkbox"/><span aria-hidden="true"></span></span></label><div class="client-limit-grid compact-top"><label><span>Alternative download limit</span><span class="client-limit-input"><input id="clientAltDl" min="0" step="1" type="number" value="0"/><span>KB/s</span></span><small>0 means unlimited</small></label><label><span>Alternative upload limit</span><span class="client-limit-input"><input id="clientAltUl" min="0" step="1" type="number" value="0"/><span>KB/s</span></span><small>0 means unlimited</small></label></div></section><section class="client-settings-pane" data-client-settings-pane="connection"><div class="client-settings-section-heading"><strong>Incoming connections</strong><span>Control the listening port, automatic port mapping, and connection limits.</span></div><div class="client-field-grid two-col"><label><span>Listening port</span><input id="clientListenPort" max="65535" min="1" step="1" type="number"/></label><label class="client-toggle-field"><span class="client-setting-copy"><strong>Random port on startup</strong><span>Let qBitTorrent choose the listening port.</span></span><span class="client-switch"><input id="clientRandomPort" type="checkbox"/><span aria-hidden="true"></span></span></label></div><label class="client-setting-row"><span class="client-setting-copy"><strong>UPnP / NAT-PMP port forwarding</strong><span>Automatically request a router port mapping when supported.</span></span><span class="client-switch"><input id="clientUpnp" type="checkbox"/><span aria-hidden="true"></span></span></label><div class="client-settings-divider" aria-hidden="true"></div><div class="client-field-grid two-col connection-limits"><label><span>Global connection limit</span><input id="clientMaxConnections" min="-1" step="1" type="number"/><small>-1 means unlimited</small></label><label><span>Connections per torrent</span><input id="clientMaxConnectionsTorrent" min="-1" step="1" type="number"/><small>-1 means unlimited</small></label><label><span>Global upload slots</span><input id="clientMaxUploads" min="-1" step="1" type="number"/><small>-1 means unlimited</small></label><label><span>Upload slots per torrent</span><input id="clientMaxUploadsTorrent" min="-1" step="1" type="number"/><small>-1 means unlimited</small></label></div></section><section class="client-settings-pane" data-client-settings-pane="proxy"><div class="client-settings-section-heading"><strong>Proxy</strong><span>Configure qBitTorrent's outbound proxy without exposing stored proxy passwords to Torrent Dashboard clients.</span></div><div class="client-field-grid proxy-grid"><label><span>Type</span><select id="clientProxyType"><option value="none">None</option><option value="http">HTTP</option><option value="socks5">SOCKS5</option><option value="socks4">SOCKS4</option></select></label><label><span>Host</span><input id="clientProxyHost" autocomplete="off" placeholder="proxy.example.com"/></label><label><span>Port</span><input id="clientProxyPort" max="65535" min="1" step="1" type="number"/></label></div><label class="client-setting-row" id="clientProxyAuthRow"><span class="client-setting-copy"><strong>Authentication</strong><span>Use a username and password for the proxy.</span></span><span class="client-switch"><input id="clientProxyAuth" type="checkbox"/><span aria-hidden="true"></span></span></label><div class="client-field-grid two-col" id="clientProxyCredentials"><label><span>Username</span><input id="clientProxyUsername" autocomplete="off"/></label><label><span>Password</span><input id="clientProxyPassword" autocomplete="off" type="password" placeholder="Password"/></label></div><div class="client-settings-divider" aria-hidden="true"></div><label class="client-setting-row" id="clientProxyLookupRow"><span class="client-setting-copy"><strong>Resolve hostnames through proxy</strong><span>Send hostname lookups through the configured proxy when supported.</span></span><span class="client-switch"><input id="clientProxyLookup" type="checkbox"/><span aria-hidden="true"></span></span></label><label class="client-setting-row" id="clientProxyBittorrentRow"><span class="client-setting-copy"><strong>Use proxy for BitTorrent</strong><span>Route BitTorrent traffic through the configured proxy when supported.</span></span><span class="client-switch"><input id="clientProxyBittorrent" type="checkbox"/><span aria-hidden="true"></span></span></label><label class="client-setting-row" id="clientProxyPeersRow"><span class="client-setting-copy"><strong>Proxy peer connections</strong><span>Proxy peer and web-seed connections when qBitTorrent supports it.</span></span><span class="client-switch"><input id="clientProxyPeers" type="checkbox"/><span aria-hidden="true"></span></span></label></section><div class="client-settings-status muted" id="clientSettingsStatus"></div></div><footer class="client-settings-actions"><button class="primary" id="saveClientSettings" type="submit">Save</button><button class="secondary" data-client-settings-close="" type="button">Cancel</button></footer></form></div>'''
html = regex_once(
    html,
    r'<div class="modal hidden" id="clientSettingsModal">.*?</form></div>',
    client_modal,
    'advanced client settings modal',
    re.S,
)
write('static/index.html', html)
