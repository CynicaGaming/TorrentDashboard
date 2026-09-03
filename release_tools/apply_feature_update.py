#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD, NEW = "0.5.76", "0.5.77"


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def write(path, text):
    (ROOT / path).write_text(text, encoding="utf-8")


def once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


def required(text, old, new, label):
    if old not in text:
        raise SystemExit(f"{label}: expected a match")
    return text.replace(old, new)


# Author static interface copy in its final display form.
html = read("static/index.html").replace(OLD, NEW)
for old, new, label in [
    ("First Run Setup", "First-run setup", "setup label"),
    ("Step 1 Of 4", "Step 1 of 4", "step 1"),
    ("Step 2 Of 4", "Step 2 of 4", "step 2"),
    ("Step 3 Of 4", "Step 3 of 4", "step 3"),
    ("Step 4 Of 4", "Step 4 of 4", "step 4"),
    ("Set Up Your Dashboard", "Set up your dashboard", "setup heading"),
    ("Dashboard Name", "Dashboard name", "dashboard name"),
    ("Local Dashboard Address", "Local dashboard address", "local address"),
    ("Remote Setup Code", "Remote setup code", "setup code"),
    ("Shown In Console", "Shown in console", "setup code placeholder"),
    ("Protect Dashboard Access", "Protect dashboard access", "access heading"),
    ("Authentication Mode", "Authentication mode", "auth mode"),
    ("Bypass Password For Trusted Addresses", "Bypass password for trusted addresses", "setup bypass"),
    ("Require Password Everywhere", "Require password everywhere", "setup required"),
    ("Disable Dashboard Authentication", "Disable dashboard authentication", "setup disabled"),
    ("Dashboard Username", "Dashboard username", "dashboard username"),
    ("Dashboard Password", "Dashboard password", "dashboard password"),
    ("Create Password", "Create password", "create password"),
    ("Confirm Password", "Confirm password", "confirm password"),
    ("Trusted Network Interfaces", "Trusted network interfaces", "trusted interfaces"),
    ("Refresh Interfaces", "Refresh interfaces", "refresh interfaces"),
    ("Detecting Network Interfaces…", "Detecting network interfaces…", "interface status"),
    ("IP Address Whitelist", "Allowed IP addresses", "allowed IPs"),
    ("Add Your Download Client", "Add a download client", "client heading"),
    ("Client Type", "Client type", "client type"),
    ("Display Name", "Display name", "display name"),
    ("qBitTorrent Authentication", "qBitTorrent authentication", "qBitTorrent auth"),
    ("Username And Password", "Username and password", "username password"),
    ("qBitTorrent Username", "qBitTorrent username", "qBitTorrent username"),
    ("qBitTorrent Password", "qBitTorrent password", "qBitTorrent password"),
    ("Test qBitTorrent Connection", "Test connection", "test connection"),
    ("Not Tested Yet", "Not tested yet", "not tested"),
    ("Review And Finish", "Review and finish", "review heading"),
    ("Sign In To Dashboard", "Sign in to Torrent Dashboard", "sign-in subtitle"),
    (">Sign In</button>", ">Sign in</button>", "sign-in button"),
    ("Live Torrent Activity", "Live torrent activity", "dashboard subtitle"),
    ("Disk Free", "Free disk space", "disk metric"),
    ("All Categories", "All categories", "categories filter"),
    ("All Tags", "All tags", "tags filter"),
    ("All Trackers", "All trackers", "trackers filter"),
    ("Download Speed", "Download speed", "download sort"),
    ("Upload Speed", "Upload speed", "upload sort"),
    ("HTTP Sources", "HTTP sources", "HTTP sources"),
    ("Dashboard Title", "Dashboard name", "settings dashboard name"),
    ("Accent Color", "Accent color", "accent color"),
    ("Visible Desktop Columns", "Visible desktop columns", "desktop columns"),
    ("Required Everywhere", "Required everywhere", "settings required"),
    ("Bypass For Trusted Addresses", "Bypass for trusted addresses", "settings bypass"),
    ("Copy Address", "Copy address", "copy address"),
    ("＋ Add Server", "＋ Add client", "add client"),
    ("GitHub Repository", "GitHub repository", "GitHub repository"),
    ("Current Version", "Current version", "current version"),
    ("Latest Version", "Latest version", "latest version"),
    ("Not Checked", "Not checked", "not checked"),
    ("Update State", "Update state", "update state"),
    ("Check For Updates", "Check for updates", "check updates"),
    ("Patch Notes", "Patch notes", "patch notes"),
    ("Browser Notifications", "Browser notifications", "browser notifications"),
    ("Completion Sound", "Completion sound", "completion sound"),
    ("Custom Sound File", "Custom sound file", "custom sound file"),
    ("No Custom Sound Uploaded", "No custom sound uploaded", "sound status"),
    ("Test Notification", "Test notification", "test notification"),
    ("Choose Integration…", "Choose integration…", "choose integration"),
    ("＋ Add Integration", "＋ Add integration", "add integration"),
    ("Standard Users", "Standard users", "standard users"),
    ("＋ Add User", "＋ Add user", "add user"),
    ("Close Add Torrent", "Close add torrent", "close add torrent"),
    ("Save as .torrent", "Save .torrent file", "save torrent file"),
    ("Also delete the downloaded files", "Delete downloaded files too", "delete downloaded files"),
    ("<h2>Remove torrent(s)</h2>", '<h2 id="removeTitle">Remove torrent</h2>', "remove title"),
    ("<h2>Settings</h2><p id=\"clientSettingsClientName\">", "<h2>Client settings</h2><p id=\"clientSettingsClientName\">", "client settings title"),
    ('aria-label="Close settings"', 'aria-label="Close client settings"', "client settings close"),
]:
    html = required(html, old, new, label)
html = html.replace("IP Address", "IP address").replace("API Key", "API key")
html = required(html,
    "API key authentication is preferred on qBitTorrent 5.2+; Username and password remain available for older versions.",
    "API key authentication is preferred on qBitTorrent 5.2+. Username and password are available for older versions.",
    "setup auth description")
html = required(html,
    "Loopback access on the host is always trusted. Interface selections follow the actual subnet assigned to each NIC, so DHCP address changes do not require editing the whitelist. The manual list accepts a single IP or a CIDR on each line.",
    "Loopback access on the host is always trusted. Trusted interfaces follow their current subnet, so DHCP address changes do not require manual updates. You can also add one IP address or CIDR per line.",
    "trusted network help")
html = required(html,
    "Usernames, passwords, profile information, and access roles are managed under User Management.",
    "Usernames, passwords, profile information, and access roles are managed under Users.",
    "users help")
html = required(html,
    "Manage each download client connection here. Use Settings on a saved client for its live qBitTorrent transfer preferences.",
    "Manage your qBitTorrent connections. Open Settings on a saved client to change its transfer preferences.",
    "clients intro")
html = required(html,
    "Public GitHub repository used as this dashboard's update source. Save changes before checking for updates; Check for updates validates the repository before comparing releases.",
    "Choose the public GitHub repository used for updates. Save changes before checking for updates.",
    "updates help")
html = required(html,
    "Check the configured public repository for a newer Torrent Dashboard release.",
    "Check for a newer Torrent Dashboard release when you're ready.",
    "updates message")
html = required(html,
    "Configure notifications generated by this browser. External delivery services such as Discord, ntfy, and webhooks are managed under Integrations.",
    "Choose how this browser notifies you. Discord, ntfy, webhooks, and other external destinations are managed under Integrations.",
    "notifications intro")
html = required(html,
    "No integrations are populated by default. Add media services or notification destinations only when you use them, test each connection, and save it independently.",
    "Connect Torrent Dashboard to media services and notification destinations. Test each connection before saving it.",
    "integrations intro")
html = required(html,
    "Administrators can manage torrents, settings, integrations, and users. Standard users can manage their own account and profile while dashboard management remains read-only.",
    "Administrators can manage the dashboard. Standard users have read-only dashboard access and can manage their own account.",
    "users intro")
html = required(html,
    "<strong>Save at</strong><span>Use manual paths or let qBitTorrent manage the location automatically.</span>",
    "<strong>Location</strong><span>Choose where qBitTorrent saves this torrent.</span>",
    "add torrent location")
html = required(html, "Save files to location", "Save path", "add torrent save path")
html = required(html, "Manage your personal Torrent Dashboard account.", "Manage your profile, password, and picture.", "account intro")
html = required(html,
    "Changing your password requires confirmation in a separate prompt and a new password of at least 8 characters.",
    "Use at least 8 characters. You'll confirm your current password before the change is saved.",
    "password help")
write("static/index.html", html)


# Preserve authored display strings; normalize only legacy generated tokens.
app_js = read("static/app.js")
app_js = once(app_js, f"const FRONTEND_BUILD='{OLD}';", f"const FRONTEND_BUILD='{NEW}';", "frontend build")
app_js = once(app_js,
"""function hasCamelCaseUiText(value=''){return /[a-z0-9][A-Z]/.test(String(value||''))}
function normalizeUiAttributes(el){
  if(!el?.getAttribute)return;
  for(const attr of ['placeholder','title','aria-label']){
    const raw=el.getAttribute(attr);
    if(raw&&hasCamelCaseUiText(raw))el.setAttribute(attr,uiText(raw));
  }
}""",
"""function hasCamelCaseUiText(value=''){return /[a-z0-9][A-Z]/.test(String(value||''))}
function isLegacyUiToken(value=''){
  const s=String(value||'').trim();
  return hasCamelCaseUiText(s)||/^[a-z0-9]+(?:_[a-z0-9]+)+$/.test(s)
}
function displayUiText(value=''){const s=String(value??'');return isLegacyUiToken(s)?uiText(s):s}
function normalizeUiAttributes(el){
  if(!el?.getAttribute)return;
  for(const attr of ['placeholder','title','aria-label']){
    const raw=el.getAttribute(attr);
    if(raw&&isLegacyUiToken(raw))el.setAttribute(attr,uiText(raw));
  }
}""", "legacy token helper")
app_js = once(app_js,
    "if(trim&&trim.length<80&&/[A-Za-z]/.test(trim))n.nodeValue=raw.replace(trim,uiText(trim));",
    "if(trim&&isLegacyUiToken(trim))n.nodeValue=raw.replace(trim,uiText(trim));",
    "authored copy preservation")
app_js = once(app_js,
    "function toast(msg,type=''){const el=document.createElement('div');el.className='toast '+type;el.textContent=/^[A-Za-z0-9_ -]+$/.test(String(msg))?uiText(msg):msg;$('#toasts').append(el);setTimeout(()=>el.remove(),3800)}",
    "function toast(msg,type=''){const el=document.createElement('div');el.className='toast '+type;el.textContent=displayUiText(msg);$('#toasts').append(el);setTimeout(()=>el.remove(),3800)}",
    "toast copy")
for old, new, label in [
    ("'Network Interface'", "'Network interface'", "network interface"),
    ("Default Route", "Default route", "default route"),
    ("No Network Interfaces Detected", "No network interfaces detected", "interface empty"),
    ("You can still use the IP address whitelist below.", "You can still add allowed IP addresses below.", "allowed IP help"),
    ("Required Everywhere", "Required everywhere", "review required"),
    ("Trusted Address Bypass", "Bypass for trusted addresses", "review bypass"),
    ("'API Key':'Username And Password'", "'API key':'Username and password'", "review client auth"),
    ("Dashboard Access", "Dashboard access", "review dashboard access"),
    ("The first setup account is an Administrator.", "The first setup account is an administrator.", "review admin"),
    ("Download Client", "Download client", "review client"),
    ("qBitTorrent Authentication", "qBitTorrent authentication", "review qBitTorrent auth"),
    ("Bearer API Key · No Login Cookie", "Bearer API key · no login cookie", "review bearer auth"),
    ("Not Tested Yet", "Not tested yet", "wizard status"),
    ("Testing And Saving…", "Testing and saving…", "wizard saving"),
    ("Setup Could Not Be Completed", "Setup could not be completed.", "wizard failure"),
    ("${Number(t.num_seeds||0)} Seeds", "${Number(t.num_seeds||0)} seeds", "seed count"),
    ("Display Name", "Display name", "client display name"),
    (">API Key</option>", ">API key</option>", "client API option"),
    (">Username And Password</option>", ">Username and password</option>", "client password option"),
    (">API Key<input", ">API key<input", "client API label"),
    ("'API Key Configured'", "'API key configured'", "configured API key"),
    ("Bearer Authentication", "Bearer authentication", "bearer auth"),
    ("'Password Configured'", "'Password configured'", "configured password"),
    ("?'API Key':'Password'", "?'API key':'Password'", "client test auth"),
    ("pasteMagnetUrlOrChooseTorrentFile", "Enter a magnet link, torrent URL, or choose a .torrent file", "add validation"),
]:
    app_js = required(app_js, old, new, label)
app_js = once(app_js,
    "whitelist=p.auth.trusted_ips.length?`${p.auth.trusted_ips.length} Whitelist ${p.auth.trusted_ips.length===1?'Entry':'Entries'}`:'No Whitelist Entries';",
    "allowedIps=p.auth.trusted_ips.length?`${p.auth.trusted_ips.length} allowed IP ${p.auth.trusted_ips.length===1?'address':'addresses'}`:'No allowed IP addresses';",
    "review IP summary")
app_js = required(app_js, "${esc(whitelist)}", "${esc(allowedIps)}", "review IP variable")
app_js = once(app_js,
    "function validateSetupStep(step=state.setupStep){if(step===0){if(!$('#wTitle').value.trim())throw new Error('enterDashboardName');const port=Number($('#wPort').value);if(!Number.isInteger(port)||port<1||port>65535)throw new Error('enterValidDashboardPort')}if(step===1){const mode=$('#wAuthMode').value;if(mode!=='disabled'){if(!$('#wDashUser').value.trim())throw new Error('enterDashboardUsername');if(!$('#wDashPass').value)throw new Error('createDashboardPassword');if($('#wDashPass').value!==$('#wDashPass2').value)throw new Error('dashboardPasswordsDoNotMatch')}if(mode==='lan_bypass'&&!selectedInterfaceIds('#wInterfaceList').length&&!parseWhitelist('#wTrustedIps').length)throw new Error('selectTrustedInterfaceOrWhitelistIp')}if(step===2){if(!$('#wClientUrl').value.trim())throw new Error('enterQbittorrentWebUiUrl');if($('#wClientAuth').value==='api_key'){const key=$('#wClientApiKey').value.trim();if(!key)throw new Error('enterQbittorrentApiKey');if(!/^qbt_[A-Za-z0-9]{28}$/.test(key))throw new Error('invalidQbittorrentApiKeyFormat')}else{if(!$('#wClientUser').value.trim())throw new Error('enterQbittorrentUsername');if(!$('#wClientPass').value)throw new Error('enterQbittorrentPassword')}}}",
    "function validateSetupStep(step=state.setupStep){if(step===0){if(!$('#wTitle').value.trim())throw new Error('Enter a dashboard name');const port=Number($('#wPort').value);if(!Number.isInteger(port)||port<1||port>65535)throw new Error('Enter a valid dashboard port')}if(step===1){const mode=$('#wAuthMode').value;if(mode!=='disabled'){if(!$('#wDashUser').value.trim())throw new Error('Enter an administrator username');if(!$('#wDashPass').value)throw new Error('Create an administrator password');if($('#wDashPass').value!==$('#wDashPass2').value)throw new Error('Passwords do not match')}if(mode==='lan_bypass'&&!selectedInterfaceIds('#wInterfaceList').length&&!parseWhitelist('#wTrustedIps').length)throw new Error('Select a trusted network interface or add an allowed IP address')}if(step===2){if(!$('#wClientUrl').value.trim())throw new Error('Enter the qBitTorrent Web UI URL');if($('#wClientAuth').value==='api_key'){const key=$('#wClientApiKey').value.trim();if(!key)throw new Error('Enter a qBitTorrent API key');if(!/^qbt_[A-Za-z0-9]{28}$/.test(key))throw new Error('The qBitTorrent API key format is invalid')}else{if(!$('#wClientUser').value.trim())throw new Error('Enter the qBitTorrent username');if(!$('#wClientPass').value)throw new Error('Enter the qBitTorrent password')}}}",
    "setup validation")
app_js = once(app_js,
    "out.textContent=`connected · qBitTorrent ${d.version||'unknown'} · webApi ${d.api_version||'unknown'}`",
    "out.textContent=`Connected · qBitTorrent ${d.version||'unknown'} · Web API ${d.api_version||'unknown'}`",
    "setup connection result")
app_js = once(app_js,
    "sel.innerHTML=(includeAll?'<option value=\"all\">allServers</option>':'')",
    "sel.innerHTML=(includeAll?'<option value=\"all\">All servers</option>':'')",
    "All servers label")
app_js = required(app_js, "return toast('Choose a specific server first','error')", "return toast('Select a specific client first','error')", "specific client error")
app_js = required(app_js, "throw new Error('Choose a specific server for this action')", "throw new Error('Select a specific client for this action')", "specific action client error")
app_js = once(app_js,
    "function showRemoveDialog(targets){targets=(targets||[]).filter(x=>x&&x.hash);if(!targets.length)return Promise.resolve(null);if(removeDialogResolve)closeRemoveDialog(null);const one=targets.length===1;const name=targets[0]?.name||targets[0]?.hash||'this torrent';$('#removePrompt').textContent=one?`Are you sure you want to remove “${name}” from the transfer list?`:`Are you sure you want to remove ${targets.length} torrents from the transfer list?`;",
    "function showRemoveDialog(targets){targets=(targets||[]).filter(x=>x&&x.hash);if(!targets.length)return Promise.resolve(null);if(removeDialogResolve)closeRemoveDialog(null);const one=targets.length===1;const name=targets[0]?.name||targets[0]?.hash||'this torrent';const title=$('#removeTitle');if(title)title.textContent=one?'Remove torrent':'Remove torrents';$('#removePrompt').textContent=one?`Remove “${name}” from qBitTorrent?`:`Remove ${targets.length} torrents from qBitTorrent?`;",
    "remove dialog")
write("static/app.js", app_js)


settings_js = read("static/settings.js")
for old, new, label in [
    ("Save the client before opening client settings", "Save this client before opening its settings", "unsaved client"),
    ("Live settings loaded from qBitTorrent.", "Settings loaded from qBitTorrent.", "settings loaded"),
    ("Enter valid whole numbers for the client limits and ports.", "Enter whole numbers for client limits and ports.", "numeric validation"),
    ("Standard User", "Standard user", "standard user"),
]:
    settings_js = required(settings_js, old, new, label)
write("static/settings.js", settings_js)

integrations = read("torrent_dashboard/integrations.py")
integrations = required(integrations, '"API Key"', '"API key"', "integration API key")
integrations = required(integrations, '"Access Token"', '"Access token"', "integration access token")
integrations = required(integrations, '"Generic Webhook"', '"Generic webhook"', "generic webhook")
write("torrent_dashboard/integrations.py", integrations)

users = read("torrent_dashboard/users.py")
users = required(users, '"standard": "Standard User"', '"standard": "Standard user"', "standard group label")
users = required(users, '"User group must be Administrator or Standard User"', '"Choose Administrator or Standard user for the user group"', "group validation")
users = required(users, '"Standard User"),', '"Standard user"),', "group fallback")
write("torrent_dashboard/users.py", users)


design = read("DESIGN_LANGUAGE.md")
design = once(design,
    '- Use **sentence case** for headings, labels, buttons, empty states, validation, and status text. Preserve product names and established acronyms such as Torrent Dashboard, qBitTorrent, GitHub, API, IP, URL, HTTPS, and SHA-256.',
    '- Use **deliberate, context-aware capitalization**. Compact named destinations may read like product labels; headings, field labels, actions, status text, validation, and explanatory copy generally use sentence case. Preserve product names and established acronyms such as Torrent Dashboard, qBitTorrent, GitHub, API, IP, URL, HTTPS, and SHA-256.',
    "design casing rule")
design = once(design,
    'New user-facing copy should be authored in its final display form rather than relying on token-to-text conversion. The existing `uiText()` normalizer remains a compatibility layer for older surfaces and may be retired incrementally.',
    'New user-facing copy must be authored in its final display form. Runtime normalization must not recase deliberate authored text; `uiText()` remains only as a compatibility layer for legacy camelCase or underscore tokens and may be retired incrementally.',
    "authored copy rule")
section = """

## Capitalization and product voice

Torrent Dashboard follows a Firefox-inspired desktop-application pattern rather than forcing one casing rule onto every surface.

- **Named destinations and compact product labels** may use title-style capitalization when they behave like stable names, for example **Access Control** and **Download Client** in setup navigation. One-word destinations such as **Dashboard**, **Settings**, and **Notifications** are naturally capitalized.
- **Page and dialog headings, field labels, buttons, menu commands, tabs, and status labels** use sentence case: **Set up your dashboard**, **Authentication mode**, **Check for updates**, **HTTP sources**, **Client settings**.
- **Explanatory copy, validation, errors, empty states, and status messages** use natural sentence case and should read as concise human language rather than implementation output.
- **Proper names, protocols, acronyms, and file or format names** retain their established form: Torrent Dashboard, qBitTorrent, GitHub, API, Web API, HTTP, IP, URL, SHA-256, `.torrent`.
- Prefer direct product concepts over legacy implementation terminology. Use **client** on client-management surfaces and **allowed IP addresses** in user-facing access controls; internal configuration keys and historical documentation do not need to be renamed solely for copy consistency.
- Prefer verb phrases for actions: **Add client**, **Test connection**, **Copy address**, **Remove torrent**. Avoid noun-heavy implementation phrases and parenthetical constructions such as **Remove torrent(s)**.
- Do not capitalize words merely because they appear in a control. Capitalization should communicate hierarchy or a proper name, not decoration.
"""
if "## Capitalization and product voice" not in design:
    design = design.replace("\n## Settings feedback contract", section + "\n## Settings feedback contract", 1)
write("DESIGN_LANGUAGE.md", design)

testing = read("TESTING.md")
if "### Product language and capitalization" not in testing:
    testing += """

### Product language and capitalization

- Verify setup, sign-in, Dashboard, Settings, Add torrent, account, and client-settings surfaces after a copy-system change.
- Confirm named destinations retain their intended label casing while headings, labels, actions, statuses, errors, and explanatory copy use natural sentence case.
- Confirm qBitTorrent, Torrent Dashboard, GitHub, API, Web API, HTTP, IP, URL, SHA-256, and `.torrent` keep their established capitalization.
- Confirm authored copy does not visibly change after JavaScript initializes or after dynamically generated controls are inserted.
- Verify access controls say **Allowed IP addresses** rather than whitelist language and client-management actions use **client** where that is the user-facing concept.
- Verify validation and toast messages contain no camelCase tokens, internal field names, or mechanically recased technical terms.
"""
write("TESTING.md", testing)


validator = read("release_tools/validate_ui_strings.py")
validator = required(validator, '"toast(\'Choose a specific server first\',\'error\')",', '"toast(\'Select a specific client first\',\'error\')",', "canonical client error")
validator = required(validator, "assert 'HTTP Sources' in html", "assert 'HTTP sources' in html", "HTTP sources assertion")
validator = required(validator, "assert 'Save as .torrent' in html", "assert 'Save .torrent file' in html", "save torrent assertion")
validator = required(validator, "assert 'Also delete the downloaded files' in html", "assert 'Delete downloaded files too' in html", "delete files assertion")
anchor = "    assert '### Server-selection defaults' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')\n"
contract = """

    # 0.5.77 preserves intentionally authored display copy and confines runtime
    # normalization to legacy generated tokens.
    assert 'function isLegacyUiToken' in app_js and 'function displayUiText' in app_js
    assert 'if(trim&&isLegacyUiToken(trim))' in app_js
    assert 'el.textContent=displayUiText(msg)' in app_js
    assert 'trim.length<80&&/[A-Za-z]/.test(trim)' not in app_js
    for copy in (
        'First-run setup','Step 1 of 4','Set up your dashboard','Dashboard name',
        'Local dashboard address','Authentication mode','Allowed IP addresses',
        'Username and password','Test connection','Not tested yet','Review and finish',
        'Sign in to Torrent Dashboard','Live torrent activity','Free disk space',
        'All categories','Download speed','HTTP sources','Accent color',
        'Visible desktop columns','Copy address','Add client','GitHub repository',
        'Current version','Not checked','Check for updates','Patch notes',
        'Browser notifications','Completion sound','Add integration','Add user',
        'Save .torrent file','Delete downloaded files too','Client settings',
    ):
        assert copy in html, f'missing polished interface copy: {copy}'
    for legacy in (
        'First Run Setup','Step 1 Of 4','Set Up Your Dashboard','Authentication Mode',
        'IP Address Whitelist','Username And Password','Not Tested Yet','Review And Finish',
        'Sign In To Dashboard','Live Torrent Activity','Disk Free','All Categories',
        'Download Speed','HTTP Sources','Dashboard Title','Accent Color',
        'Visible Desktop Columns','Copy Address','＋ Add Server','GitHub Repository',
        'Current Version','Latest Version','Not Checked','Update State','Check For Updates',
        'Patch Notes','Browser Notifications','Completion Sound','Custom Sound File',
        'No Custom Sound Uploaded','Test Notification','Choose Integration…',
        '＋ Add Integration','Standard Users','＋ Add User','Remove torrent(s)',
    ):
        assert legacy not in html, f'legacy capitalization remains: {legacy}'
    assert 'No Network Interfaces Detected' not in app_js
    assert 'Testing And Saving…' not in app_js and 'Setup Could Not Be Completed' not in app_js
    assert 'Standard User' not in settings_js
    assert '"standard": "Standard user"' in users_py
    assert '"API key"' in integrations_py and '"Access token"' in integrations_py
    assert '## Capitalization and product voice' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')
    assert '### Product language and capitalization' in (ROOT / 'TESTING.md').read_text(encoding='utf-8')
"""
if validator.count(anchor) != 1:
    raise SystemExit(f"validator anchor: expected one match, found {validator.count(anchor)}")
validator = validator.replace(anchor, anchor + contract, 1)
write("release_tools/validate_ui_strings.py", validator)


dashboard = read("dashboard.py")
dashboard = once(dashboard, f'VERSION = "{OLD}"', f'VERSION = "{NEW}"', "dashboard version")
write("dashboard.py", dashboard)
sw = read("static/sw.js")
sw = once(sw, "torrent-dashboard-v0576", "torrent-dashboard-v0577", "service worker cache").replace(OLD, NEW)
write("static/sw.js", sw)

meta_path = ROOT / "release_notes" / "releases.json"
meta = json.loads(meta_path.read_text(encoding="utf-8"))
releases = meta["releases"]
if any(r.get("version") == NEW for r in releases):
    raise SystemExit(f"release {NEW} already exists")
previous = releases[-1]
entry = {
    "version": NEW,
    "date": "2026-09-02",
    "status": "prerelease",
    "title": "Product language polish",
    "summary": "Refines capitalization and wording across setup, Dashboard, Settings, dialogs, roles, and integrations while preserving intentionally authored copy instead of mechanically recasing it at runtime.",
    "highlights": [
        "Introduces a deliberate mixed capitalization model: compact named destinations may read as product labels while headings, fields, actions, statuses, errors, and explanatory text use natural sentence case.",
        "Polishes setup and sign-in language, including clearer authentication choices, natural validation messages, and consistent API key and Web API terminology.",
        "Refines Dashboard and Settings labels such as Free disk space, HTTP sources, Dashboard name, Check for updates, Patch notes, Browser notifications, and Completion sound.",
        "Uses Allowed IP addresses instead of whitelist language on user-facing access controls, and uses client terminology for client-management actions such as Add client.",
        "Simplifies dialog and account copy, including Remove torrent/Remove torrents, Save .torrent file, Client settings, and more concise profile/password guidance."
    ],
    "fixes": [
        "Stops the runtime sentence-case normalizer from rewriting intentionally authored UI strings and technical forms such as SHA-256.",
        "Removes inconsistent title-cased actions and awkward phrases such as Remove torrent(s), Check For Updates, Sign In To Dashboard, and Not Tested Yet.",
        "Normalizes Standard user, API key, and Access token labels where those values appear directly in browser forms or validation."
    ],
    "technical": [
        "uiText remains available for legacy camelCase/underscore tokens, but authored HTML and JavaScript copy is now preserved verbatim.",
        "DESIGN_LANGUAGE.md now defines a Firefox-inspired capitalization and product-voice model with explicit guidance for destinations, headings, actions, technical names, and terminology.",
        "The UI validator enforces high-value polished strings, rejects known legacy capitalization, and verifies that runtime normalization is limited to legacy tokens."
    ],
    "validation": [
        "The UI audit verifies polished setup, Dashboard, Settings, dialog, integration, and account terminology plus authored-text preservation.",
        "Existing backend behavioral tests, JavaScript syntax checks, generated handoff/release-note validation, frontend/service-worker synchronization, and package-integrity gates remain required."
    ],
    "known_issues": [],
}
entry["architecture"] = copy.deepcopy(previous.get("architecture", []))
entry["next_steps"] = copy.deepcopy(previous.get("next_steps", []))
entry["decisions"] = copy.deepcopy(previous.get("decisions", []))
entry["decisions"].extend([
    "Author user-facing copy in its final display form; runtime token normalization is compatibility behavior for legacy generated tokens, not a presentation system.",
    "Use deliberate mixed capitalization: stable named destinations may read as product labels, while headings, field labels, actions, statuses, errors, and explanatory text generally use sentence case.",
    "Prefer user-facing product concepts over legacy implementation terminology, including allowed IP addresses for access controls and client for client-management actions."
])
releases.append(entry)
meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
subprocess.run(["python", "release_tools/generate_release_notes.py", "--version", NEW], cwd=ROOT, check=True)
print(f"Applied Torrent Dashboard v{NEW} product language polish")
