from pathlib import Path
import json
import re
import textwrap

ROOT = Path(__file__).resolve().parents[2]
OLD_VERSION = "0.5.162"
NEW_VERSION = "0.5.163"


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def write(path, text):
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text, old, new, label):
    if old not in text:
        raise RuntimeError(f"Expected marker not found in {label}: {old[:100]}")
    return text.replace(old, new, 1)


# Version markers.
init_path = "src/torrent_dashboard/__init__.py"
init = read(init_path)
init = replace_once(init, f'__version__ = "{OLD_VERSION}"', f'__version__ = "{NEW_VERSION}"', init_path)
write(init_path, init)

index_path = "static/index.html"
index = read(index_path).replace(OLD_VERSION, NEW_VERSION)
old_signup = '<input autocomplete="new-password" id="registerPass" minlength="8" placeholder="Password" type="password" required/><button class="primary" type="submit">Create account</button>'
new_signup = '<input autocomplete="new-password" id="registerPass" minlength="8" placeholder="Password" type="password" required/><input autocomplete="new-password" id="registerPass2" minlength="8" placeholder="Confirm password" type="password" required/><button class="primary" type="submit">Create account</button>'
index = replace_once(index, old_signup, new_signup, index_path)
write(index_path, index)

sw_path = "static/sw.js"
sw = read(sw_path).replace("torrent-dashboard-v05162", "torrent-dashboard-v05163").replace(OLD_VERSION, NEW_VERSION)
write(sw_path, sw)

# Public registration: add Confirm password and send it to the server.
app_path = "static/app.js"
app = read(app_path)
app = replace_once(app, "const FRONTEND_BUILD='0.5.162';", "const FRONTEND_BUILD='0.5.163';", app_path)
call_pos = app.find("rawJson('/api/register'")
if call_pos < 0:
    raise RuntimeError("Registration request was not found in static/app.js")
window_start = max(0, call_pos - 1400)
window_end = min(len(app), call_pos + 1000)
block = app[window_start:window_end]
if "registerPass2" not in block:
    match = re.search(r"(const\s+password\s*=\s*[^;]*registerPass[^;]*;)", block)
    if not match:
        raise RuntimeError("Registration password assignment was not found")
    block = block[:match.end()] + "\n  const password2=$('#registerPass2')?.value||'';" + block[match.end():]
call_local = block.find("rawJson('/api/register'")
line_start = block.rfind("\n", 0, call_local) + 1
indent = re.match(r"\s*", block[line_start:]).group(0)
if "Passwords do not match" not in block[:call_local]:
    guard = indent + "if(password!==password2){const el=$('#registerError');if(el)el.textContent='Passwords do not match';return;}\n"
    block = block[:line_start] + guard + block[line_start:]
if "{username,password,password2}" not in block:
    block, count = re.subn(r"\{username\s*,\s*password\}", "{username,password,password2}", block, count=1)
    if count != 1:
        raise RuntimeError("Registration request payload was not found")
app = app[:window_start] + block + app[window_end:]
write(app_path, app)

# Enforce password confirmation on the public registration endpoint.
dashboard_path = "src/torrent_dashboard/dashboard.py"
dashboard = read(dashboard_path)
old_route = '        try: data=parse_json_body(self,20000)\n        except Exception as e: return self.send_json(400,{"error":str(e)})\n        try:\n            updated,user=mutate_config(lambda current: register_user(current,data))'
new_route = '        try: data=parse_json_body(self,20000)\n        except Exception as e: return self.send_json(400,{"error":str(e)})\n        if str(data.get("password") or "") != str(data.get("password2") or ""):\n            return self.send_json(400,{"error":"Passwords do not match"})\n        try:\n            updated,user=mutate_config(lambda current: register_user(current,data))'
dashboard = replace_once(dashboard, old_route, new_route, dashboard_path)
write(dashboard_path, dashboard)

# Pending users use the same editable fields as normal users. Save before approval so
# changes made by the administrator are not lost when Approve is clicked.
settings_path = "static/settings.js"
settings = read(settings_path)
pattern = re.compile(r"\n  function renderUsers\(\) \{.*?\n  async function approvePendingUser", re.S)
new_render = r'''
  function renderUsers() {
    const list = document.querySelector('#userList');
    if (!list) return;
    if (!users.length) {
      list.innerHTML='<div class="settings-empty"><b>No users found</b><span>Add an administrator account to manage Torrent Dashboard.</span></div>';
      return;
    }
    list.innerHTML='';
    users.forEach((user,index) => {
      const pending=user.status==='pending';
      const card=document.createElement('article');
      card.className='settings-accordion user-item';
      card.dataset.id=user.id||'';
      const group=user.group==='administrator'?'Administrator':'Standard user';
      const current=!pending && user.id && user.id===currentUserId;
      const display=userName(user);
      const username=user.username||'New user';
      const showUsername=!!user.username && display!==user.username;
      const badge=pending?'<span class="user-group-badge pending">Pending</span>':`<span class="user-group-badge ${user.group==='administrator'?'admin':'standard'}">${esc(group)}</span>`;
      const passwordAttrs=user._new?'placeholder="Create password"':'class="secret-configured" data-configured-secret="1" value="'+SECRET_MASK+'"';
      const confirmAttrs=user._new?'placeholder="Confirm password"':'class="secret-configured" data-configured-secret="1" value="'+SECRET_MASK+'"';
      const actions=pending
        ? '<button class="primary user-save" type="button">Save</button><button class="primary pending-user-approve" type="button">Approve</button><button class="danger pending-user-reject" type="button">Reject</button>'
        : `<button class="primary user-save" type="button">Save</button><button class="danger user-delete" type="button" ${current?'disabled':''}>Delete</button>`;
      const body=`<div class="accordion-body ${index===0?'':'hidden'}"><div class="settings-form-grid two-col"><label><span class="field-label">Username <span class="required-mark" aria-hidden="true">*</span></span><input data-user-field="username" value="${esc(user.username||'')}" maxlength="128" autocomplete="off" required></label><label><span class="field-label">User group <span class="required-mark" aria-hidden="true">*</span></span><select class="user-group-select" data-user-field="group" required><option value="administrator" ${user.group==='administrator'?'selected':''}>Administrator</option><option value="standard" ${user.group==='standard'?'selected':''}>Standard user</option></select></label><label>First name<input data-user-field="first_name" value="${esc(user.first_name||'')}" maxlength="128"></label><label>Last name<input data-user-field="last_name" value="${esc(user.last_name||'')}" maxlength="128"></label><label class="full-field">Email<input data-user-field="email" type="email" value="${esc(user.email||'')}" maxlength="254"></label><label><span class="field-label">Password <span class="required-mark" aria-hidden="true">*</span></span><input data-user-field="password" type="password" autocomplete="new-password" required ${passwordAttrs}></label><label><span class="field-label">Confirm password <span class="required-mark" aria-hidden="true">*</span></span><input data-user-field="password2" type="password" autocomplete="new-password" required ${confirmAttrs}></label></div><div class="settings-inline-actions">${actions}</div></div>`;
      card.innerHTML=`<button class="accordion-summary" type="button" aria-expanded="${index===0?'true':'false'}"><span><span class="user-name-line"><b>${esc(display)}</b>${current?'<span class="current-user-badge">Current user</span>':''}</span>${showUsername?`<small>${esc(username)}</small>`:''}</span>${badge}<span class="accordion-chevron">⌄</span></button>${body}`;
      const summary=card.querySelector('.accordion-summary');
      summary.addEventListener('click',()=>{const body=card.querySelector('.accordion-body');const open=body.classList.contains('hidden');body.classList.toggle('hidden',!open);summary.setAttribute('aria-expanded',String(open))});
      card.querySelector('.user-save').addEventListener('click',()=>saveUser(card));
      if(pending){
        card.querySelector('.pending-user-approve').addEventListener('click',async()=>{if(await saveUser(card,{reload:false,notify:false}))await approvePendingUser(user)});
        card.querySelector('.pending-user-reject').addEventListener('click',()=>rejectPendingUser(user));
      }else{
        card.querySelector('.user-delete').addEventListener('click',()=>deleteUser(card,user));
      }
      decorateSecretFields(card);
      list.appendChild(card);
      applySentenceCaseUi(card);
    });
  }

  async function approvePendingUser'''
settings, count = pattern.subn(new_render, settings, count=1)
if count != 1:
    raise RuntimeError(f"Expected one renderUsers block; replaced {count}")

save_pattern = re.compile(r"  async function saveUser\(card\) \{.*?\n  \}\n\n  async function deleteUser", re.S)
new_save = r'''  async function saveUser(card,options={}) {
    const data=userData(card);
    if (!data.username) { toast('Enter a username','error'); return false; }
    if (data.password !== data.password2) { toast('Passwords do not match','error'); return false; }
    delete data.password2;
    try {
      await post('/api/users',data);
      if(options.notify!==false)toast('User saved');
      if(options.reload!==false)await loadUsers();
      return true;
    } catch(e) {
      toast(e.message,'error');
      return false;
    }
  }

  async function deleteUser'''
settings, count = save_pattern.subn(new_save, settings, count=1)
if count != 1:
    raise RuntimeError(f"Expected one saveUser block; replaced {count}")
write(settings_path, settings)

# Focused registration/admin-user contract tests.
test_path = "tests/test_registration_ui.py"
test_content = '''
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class RegistrationUiContractTests(unittest.TestCase):
    def test_public_registration_requires_password_confirmation(self):
        html=(ROOT/"static"/"index.html").read_text(encoding="utf-8")
        app=(ROOT/"static"/"app.js").read_text(encoding="utf-8")
        source=(ROOT/"src"/"torrent_dashboard"/"dashboard.py").read_text(encoding="utf-8")
        self.assertIn('id="loginRegisterLink"',html)
        self.assertIn('>Create an account</button>',html)
        self.assertNotIn('id="loginRegisterTab"',html)
        self.assertIn('id="loginBackToSignIn"',html)
        self.assertIn('id="registerForm"',html)
        self.assertIn('id="registerUser"',html)
        self.assertIn('id="registerPass"',html)
        self.assertIn('id="registerPass2"',html)
        for removed in ('registerFirstName','registerLastName','registerEmail'):
            self.assertNotIn(f'id="{removed}"',html)
        self.assertIn("$('#registerPass2')",app)
        self.assertIn('Passwords do not match',app)
        self.assertIn('{username,password,password2}',app)
        self.assertIn('data.get("password2")',source)
        self.assertIn('Passwords do not match',source)
        self.assertIn("signInTab.textContent=register?'Sign up':'Sign in'",app)

    def test_pending_users_share_full_admin_edit_form(self):
        html=(ROOT/"static"/"index.html").read_text(encoding="utf-8")
        settings=(ROOT/"static"/"settings.js").read_text(encoding="utf-8")
        self.assertNotIn('id="pendingUsersCard"',html)
        self.assertNotIn('id="pendingUserList"',html)
        self.assertIn('id="userList"',html)
        self.assertIn("const pending=user.status==='pending'",settings)
        self.assertIn('user-group-badge pending',settings)
        for field in ('username','group','first_name','last_name','email','password','password2'):
            self.assertIn(f'data-user-field="{field}"',settings)
        self.assertIn('pending-user-approve',settings)
        self.assertIn('pending-user-reject',settings)
        self.assertIn("saveUser(card,{reload:false,notify:false})",settings)
        self.assertIn("post('/api/users/approve'",settings)
        self.assertIn("post('/api/users/reject'",settings)

    def test_backend_keeps_pending_login_and_approval_routes(self):
        source=(ROOT/"src"/"torrent_dashboard"/"dashboard.py").read_text(encoding="utf-8")
        self.assertIn('path=="/api/register"',source)
        self.assertIn('user.get("status") == "pending"',source)
        self.assertIn('Your account is Pending. An administrator must approve it before you can sign in.',source)
        self.assertIn('path=="/api/users/approve"',source)
        self.assertIn('path=="/api/users/reject"',source)

if __name__ == "__main__":
    unittest.main()
'''
write(test_path, textwrap.dedent(test_content).lstrip())

# Update the UI validator to reflect the intentional Confirm password field and
# editable Pending user details.
validator_path = "release_tools/validate_ui_strings.py"
validator = read(validator_path)
old_contract = '    assert all(f\'id="{control}"\' not in html for control in (\'registerFirstName\',\'registerLastName\',\'registerEmail\',\'registerPass2\'))'
new_contract = '    assert all(f\'id="{control}"\' not in html for control in (\'registerFirstName\',\'registerLastName\',\'registerEmail\'))\n    assert \'id="registerPass2"\' in html and "$(\'#registerPass2\')" in app_js\n    assert \'data.get("password2")\' in dashboard_py and \'Passwords do not match\' in dashboard_py'
validator = replace_once(validator, old_contract, new_contract, validator_path)
marker = '    assert "post(\'/api/users/approve\'" in settings_js and "post(\'/api/users/reject\'" in settings_js'
if marker not in validator:
    raise RuntimeError("Pending approval validator marker was not found")
validator = validator.replace(marker, marker + '\n    assert all(f\'data-user-field="{field}"\' in settings_js for field in (\'username\',\'group\',\'first_name\',\'last_name\',\'email\',\'password\',\'password2\'))\n    assert "saveUser(card,{reload:false,notify:false})" in settings_js', 1)
write(validator_path, validator)

# Release metadata.
release_path = ROOT / "release_notes" / "releases.json"
release_data = json.loads(release_path.read_text(encoding="utf-8"))
release_data["releases"] = [r for r in release_data.get("releases", []) if r.get("version") != NEW_VERSION]
release_data["releases"].insert(0, {
    "version": NEW_VERSION,
    "date": "2026-09-14",
    "status": "prerelease",
    "title": "Confirm sign-up passwords and complete Pending users",
    "summary": "Restores password confirmation during sign-up and gives administrators the full editable user form for Pending registrations before approval.",
    "highlights": [
        "Adds Confirm password back to the public Sign up form and rejects mismatched passwords in both the browser and registration endpoint.",
        "Gives Pending users the same Username, User group, First name, Last name, Email, Password, and Confirm password fields as active users.",
        "Saves administrator edits automatically before approving a Pending user, while keeping approval and rejection explicit."
    ],
    "fixes": [],
    "technical": [
        "The /api/users save path continues to preserve Pending status until the explicit approve route is called.",
        "Pending-account password fields retain the configured-secret mask and only replace the stored password when the administrator enters a new one."
    ],
    "validation": [
        "Adds browser contracts for public password confirmation and editable Pending user fields.",
        "Runs the standard Ubuntu/Windows Python 3.13/3.14 matrix, source updater build, and Windows executable smoke tests."
    ],
    "known_issues": [
        "Backup encryption remains opt-in; unencrypted portable backups can contain saved client and integration credentials and should be stored securely.",
        "Windows executables are not code-signed yet."
    ],
    "architecture": [
        "Pending and active accounts share the same user-editing form; lifecycle state is controlled independently through explicit Approve and Reject actions."
    ],
    "decisions": [
        "Public registration remains limited to Username, Password, and Confirm password.",
        "Administrators may complete profile fields, change group, or replace a Pending user's password before approval.",
        "Clicking Approve first persists any edits currently entered in the Pending user's form."
    ],
    "next_steps": [
        {"priority": 1, "title": "Verify pending-user completion flow", "detail": "Register a test account, edit its profile/group/password from Users, approve it, and confirm the edited credentials and profile are active."}
    ]
})
release_path.write_text(json.dumps(release_data, indent=2) + "\n", encoding="utf-8")

current_path = ROOT / "development" / "current.json"
current = json.loads(current_path.read_text(encoding="utf-8"))
current.update({
    "status": "release-candidate",
    "objective": "Publish v0.5.163 with password confirmation and complete Pending-user administration",
    "why": "Sign-up should protect against password typos, and administrators should be able to complete or correct a Pending account before approving it.",
    "acceptance_criteria": [
        "Sign up requires Password and Confirm password and rejects mismatches server-side.",
        "Pending accounts remain in the normal Users list with a Pending badge.",
        "Pending users expose Username, User group, First name, Last name, Email, Password, and Confirm password fields.",
        "Save preserves Pending status, while Approve persists edits and then activates the user.",
        "Reject remains available for Pending users.",
        "The full source matrix, source updater build, and compiled Windows smoke tests pass.",
        "v0.5.163 publishes source and Windows updater packages with SHA-256 digests."
    ],
    "decisions": [
        "Public registration asks only for Username, Password, and Confirm password.",
        "Pending users use the same editable administration form as active users.",
        "Approve saves form edits before changing lifecycle state to Active."
    ],
    "files": [
        "static/index.html", "static/app.js", "static/settings.js", "static/sw.js",
        "src/torrent_dashboard/dashboard.py", "src/torrent_dashboard/__init__.py",
        "tests/test_registration_ui.py", "release_tools/validate_ui_strings.py",
        "release_notes/releases.json", "development/current.json"
    ],
    "blockers": [],
    "out_of_scope": [
        "No changes to registration rate limits, approval authorization, session policy, or recovery behavior in this release."
    ],
    "next_action": "Run full pull-request validation and Windows packaging; if green, merge and verify the complete updater-visible v0.5.163 release."
})
current_path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
