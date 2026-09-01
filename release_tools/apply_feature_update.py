#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.21"
NEW = "0.5.22"


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def write(path, text):
    (ROOT / path).write_text(text, encoding="utf-8")


# Version and asset revisions.
dashboard = read("dashboard.py")
dashboard, count = re.subn(r'^VERSION\s*=\s*["\'][^"\']+["\']', f'VERSION = "{NEW}"', dashboard, count=1, flags=re.M)
assert count == 1
write("dashboard.py", dashboard)

html = read("static/index.html")
# Settings navigation labels are the canonical page names. Keep titles identical.
replacements = {
    '<div class="panel-title">General Dashboard Settings</div>': '<div class="panel-title">General</div>',
    '<div class="panel-title">Dashboard Access</div>': '<div class="panel-title">Access</div>',
    '<div class="panel-title">qBitTorrent Servers</div>': '<div class="panel-title">Clients</div>',
    '<div class="panel-title">User Management</div>': '<div class="panel-title">Users</div>',
}
for old, new in replacements.items():
    assert old in html, old
    html = html.replace(old, new, 1)
html = html.replace(OLD, NEW)
write("static/index.html", html)

settings = read("static/settings.js")
old_user_form = '''<div class="settings-form-grid two-col"><label>Username<input data-user-field="username" value="${esc(user.username||'')}" maxlength="128" autocomplete="off"></label><label>User Group<select data-user-field="group"><option value="administrator" ${user.group==='administrator'?'selected':''}>Administrator</option><option value="standard" ${user.group==='standard'?'selected':''}>Standard User</option></select></label><label>First Name <small>(Optional)</small><input data-user-field="first_name" value="${esc(user.first_name||'')}" maxlength="128"></label><label>Last Name <small>(Optional)</small><input data-user-field="last_name" value="${esc(user.last_name||'')}" maxlength="128"></label><label class="full-field">Email <small>(Optional)</small><input data-user-field="email" type="email" value="${esc(user.email||'')}" maxlength="254"></label><label>Password<input data-user-field="password" type="password" autocomplete="new-password" ${user._new?'placeholder="Create Password"':'class="secret-configured" data-configured-secret="1" value="'+SECRET_MASK+'"'}></label><label>Confirm Password<input data-user-field="password2" type="password" autocomplete="new-password" ${user._new?'placeholder="Confirm Password"':'class="secret-configured" data-configured-secret="1" value="'+SECRET_MASK+'"'}></label></div>'''
new_user_form = '''<div class="settings-form-grid two-col"><label>Username <span class="required-mark" aria-hidden="true">*</span><input data-user-field="username" value="${esc(user.username||'')}" maxlength="128" autocomplete="off" required></label><label>User Group <span class="required-mark" aria-hidden="true">*</span><select data-user-field="group" required><option value="administrator" ${user.group==='administrator'?'selected':''}>Administrator</option><option value="standard" ${user.group==='standard'?'selected':''}>Standard User</option></select></label><label>First Name<input data-user-field="first_name" value="${esc(user.first_name||'')}" maxlength="128"></label><label>Last Name<input data-user-field="last_name" value="${esc(user.last_name||'')}" maxlength="128"></label><label class="full-field">Email<input data-user-field="email" type="email" value="${esc(user.email||'')}" maxlength="254"></label><label>Password <span class="required-mark" aria-hidden="true">*</span><input data-user-field="password" type="password" autocomplete="new-password" required ${user._new?'placeholder="Create Password"':'class="secret-configured" data-configured-secret="1" value="'+SECRET_MASK+'"'}></label><label>Confirm Password <span class="required-mark" aria-hidden="true">*</span><input data-user-field="password2" type="password" autocomplete="new-password" required ${user._new?'placeholder="Confirm Password"':'class="secret-configured" data-configured-secret="1" value="'+SECRET_MASK+'"'}></label></div>'''
assert old_user_form in settings
settings = settings.replace(old_user_form, new_user_form, 1)
assert '(Optional)' not in settings
write("static/settings.js", settings)

css = read("static/settings.css")
marker = "\n/* 0.5.22 required-field markers. */\n.required-mark{color:#ff5d6c;font-weight:800;margin-left:3px}\n"
if marker.strip() not in css:
    css += marker
write("static/settings.css", css)

sw = read("static/sw.js").replace(OLD, NEW).replace("torrent-dashboard-v0521", "torrent-dashboard-v0522")
write("static/sw.js", sw)

validator = read("release_tools/validate_ui_strings.py")
anchor = "    assert '<div class=\"settings-savebar\" id=\"settingsSavebar\"><button class=\"primary\" type=\"submit\">Save</button></div>' in html\n"
extra = """    # Settings navigation labels and card titles must use the same canonical names.\n    for title in ('General','Access','Clients','Updates','Notifications','Integrations','Users'):\n        assert f'<div class=\"panel-title\">{title}</div>' in html\n    assert '<div class=\"panel-title\">General Dashboard Settings</div>' not in html\n    assert '<div class=\"panel-title\">Dashboard Access</div>' not in html\n    assert '<div class=\"panel-title\">qBitTorrent Servers</div>' not in html\n    assert '<div class=\"panel-title\">User Management</div>' not in html\n    assert '(Optional)' not in settings_js\n    assert settings_js.count('class=\"required-mark\"') >= 4\n    assert '.required-mark{color:#ff5d6c' in settings_css\n"""
assert anchor in validator
validator = validator.replace(anchor, anchor + extra, 1)
write("release_tools/validate_ui_strings.py", validator)

# Final contract checks.
final_html = read("static/index.html")
for title in ('General','Access','Clients','Updates','Notifications','Integrations','Users'):
    assert f'<div class="panel-title">{title}</div>' in final_html
assert '(Optional)' not in read("static/settings.js")
assert 'VERSION = "0.5.22"' in read("dashboard.py")
assert '?v=0.5.22' in read("static/sw.js")
print("Staged Torrent Dashboard 0.5.22 settings title and required-field consistency")
