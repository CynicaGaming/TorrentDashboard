#!/usr/bin/env python3
from __future__ import annotations

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


dashboard = read("dashboard.py")
dashboard = replace_once(dashboard, 'VERSION = "0.5.30"', 'VERSION = "0.5.31"', "version")
write("dashboard.py", dashboard)

html = read("static/index.html")
html = replace_once(
    html,
    '<label>Role<input id="accountGroup" readonly/></label>',
    '<label>Role<input aria-readonly="true" id="accountGroup" readonly tabindex="-1"/></label>',
    "read-only role field",
)
html = replace_once(
    html,
    '<form class="account-section" id="accountPasswordForm"><div class="account-section-title">Password</div><div class="account-form-grid"><label>Current password<input autocomplete="current-password" id="accountCurrentPassword" type="password"/></label><label>New password<input autocomplete="new-password" id="accountNewPassword" minlength="8" type="password" required/></label><label>Confirm new password<input autocomplete="new-password" id="accountConfirmPassword" minlength="8" type="password" required/></label></div><div class="field-help">Changing your password requires the current password when one is already configured, and a new password of at least 8 characters.</div>',
    '<form class="account-section" id="accountPasswordForm"><div class="account-section-title">Password</div><div class="account-form-grid"><label>New password<input autocomplete="new-password" id="accountNewPassword" minlength="8" type="password" required/></label><label>Confirm new password<input autocomplete="new-password" id="accountConfirmPassword" minlength="8" type="password" required/></label></div><div class="field-help">Changing your password requires confirmation in a separate prompt and a new password of at least 8 characters.</div>',
    "password form confirmation flow",
)
html = html.replace("?v=0.5.30", "?v=0.5.31")
write("static/index.html", html)

app_js = read("static/app.js")
app_js = replace_once(
    app_js,
    "  const current=$('#accountCurrentPassword');if(current)current.required=!!d.user?.password_configured;\n",
    "",
    "remove inline current-password setup",
)
app_js = replace_once(
    app_js,
    "const focusId=target==='password'?'accountCurrentPassword':'accountFirstName';",
    "const focusId=target==='password'?'accountNewPassword':'accountFirstName';",
    "password section focus",
)
old_password_fn = """async function changeOwnPassword(e){
  e.preventDefault();
  const current=$('#accountCurrentPassword').value,next=$('#accountNewPassword').value,confirmPassword=$('#accountConfirmPassword').value,status=$('#accountStatus');
  if(next!==confirmPassword){status.className='test-result bad';status.textContent='New passwords do not match.';return}
  status.className='test-result muted';status.textContent='Changing password…';
  try{
    await post('/api/account/password',{current_password:current,new_password:next});
    $('#accountPasswordForm').reset();status.className='test-result ok';status.textContent='Password changed.';toast('passwordChanged');
  }catch(e){status.className='test-result bad';status.textContent=e.message}
}
"""
new_password_fn = """async function changeOwnPassword(e){
  e.preventDefault();
  const next=$('#accountNewPassword').value,confirmPassword=$('#accountConfirmPassword').value,status=$('#accountStatus');
  if(next!==confirmPassword){status.className='test-result bad';status.textContent='New passwords do not match.';return}
  try{
    let current='';
    if(accountProfileSnapshot?.password_configured){
      const confirmed=await requestPasswordConfirmation('Confirm your current password to change your password.');
      if(confirmed===null)return;
      current=confirmed;
    }
    status.className='test-result muted';status.textContent='Changing password…';
    await post('/api/account/password',{current_password:current,new_password:next});
    $('#accountPasswordForm').reset();status.className='test-result ok';status.textContent='Password changed.';toast('passwordChanged');
  }catch(e){status.className='test-result bad';status.textContent=e.message}
}
"""
app_js = replace_once(app_js, old_password_fn, new_password_fn, "password-change modal flow")
write("static/app.js", app_js)

sw = read("static/sw.js")
sw = sw.replace("torrent-dashboard-v0530", "torrent-dashboard-v0531")
sw = sw.replace("?v=0.5.30", "?v=0.5.31")
write("static/sw.js", sw)

validator = read("release_tools/validate_ui_strings.py")
needle = "    assert 'id=\"accountPasswordBtn\"' not in html and 'accountPasswordBtn' not in app_js\n"
addition = needle + "    assert 'id=\"accountCurrentPassword\"' not in html and 'accountCurrentPassword' not in app_js\n    assert '<label>Role<input aria-readonly=\"true\" id=\"accountGroup\" readonly tabindex=\"-1\"/></label>' in html\n    profile_update_js = app_js.split('async function saveOwnProfile(e){', 1)[1].split('async function changeOwnPassword(e){', 1)[0]\n    assert 'accountGroup' not in profile_update_js\n    assert '\"group\": existing.get(\"group\"),' in dashboard_py\n    password_update_js = app_js.split('async function changeOwnPassword(e){', 1)[1].split('async function uploadOwnAvatar(){', 1)[0]\n    assert 'requestPasswordConfirmation' in password_update_js and 'current_password:current' in password_update_js\n"
validator = replace_once(validator, needle, addition, "account security validator")
write("release_tools/validate_ui_strings.py", validator)

final_html = read("static/index.html")
final_js = read("static/app.js")
final_dashboard = read("dashboard.py")
assert 'id="accountCurrentPassword"' not in final_html
assert 'accountCurrentPassword' not in final_js
assert 'id="accountGroup" readonly' in final_html or 'id="accountGroup" readonly tabindex' in final_html
assert 'requestPasswordConfirmation' in final_js.split('async function changeOwnPassword(e){', 1)[1].split('async function uploadOwnAvatar(){', 1)[0]
assert '"group": existing.get("group"),' in final_dashboard

print("Applied 0.5.31 account security UX cleanup.")
