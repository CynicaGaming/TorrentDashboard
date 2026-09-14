from pathlib import Path
import json
import re
import textwrap

ROOT = Path(__file__).resolve().parents[2]
OLD_VERSION = "0.5.161"
NEW_VERSION = "0.5.162"


def replace_once(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"Expected marker not found in {path}: {old[:100]}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


# Keep frontend/package versions synchronized.
replace_once(
    "src/torrent_dashboard/__init__.py",
    '__version__ = "0.5.161"',
    '__version__ = "0.5.162"',
)

index_path = ROOT / "static/index.html"
index = index_path.read_text(encoding="utf-8").replace(OLD_VERSION, NEW_VERSION)
old_users = (
    '<section class="settings-page" data-settings-section="users">\n'
    '<div class="panel settings-card" id="pendingUsersCard"><div class="panel-title">Pending registrations</div><p class="muted">New registrations cannot sign in until an administrator approves them.</p><div id="pendingUserList"></div></div>\n'
    '<div class="panel settings-card"><div class="panel-title">Users</div><p class="muted user-management-intro">Administrators can manage approved dashboard users. Standard users have read-only dashboard access and can manage their own account.</p><div class="settings-inline-actions"><button class="primary" id="addUserSetting" type="button">＋ Add user</button></div><div id="userList"></div></div>\n'
    '</section>'
)
new_users = (
    '<section class="settings-page" data-settings-section="users">\n'
    '<div class="panel settings-card"><div class="panel-title">Users</div><p class="muted user-management-intro">Administrators can manage dashboard users from one list. Pending registrations are marked Pending until approved or rejected. Standard users have read-only dashboard access and can manage their own account.</p><div class="settings-inline-actions"><button class="primary" id="addUserSetting" type="button">＋ Add user</button></div><div id="userList"></div></div>\n'
    '</section>'
)
if old_users not in index:
    raise RuntimeError("Expected separate Pending registrations card was not found")
index_path.write_text(index.replace(old_users, new_users, 1), encoding="utf-8")

app_path = ROOT / "static/app.js"
app = app_path.read_text(encoding="utf-8")
app = app.replace("const FRONTEND_BUILD='0.5.161';", "const FRONTEND_BUILD='0.5.162';", 1)
old_mode = (
    "  $('#loginSignInTab')?.classList.toggle('active',signin);$('#loginRecoveryTab')?.classList.toggle('active',recovery);\n"
    "  $('#loginSignInTab')?.setAttribute('aria-selected',String(signin));$('#loginRecoveryTab')?.setAttribute('aria-selected',String(recovery));"
)
new_mode = (
    "  const signInTab=$('#loginSignInTab');if(signInTab){signInTab.textContent=register?'Sign up':'Sign in';signInTab.classList.toggle('active',signin||register);signInTab.setAttribute('aria-selected',String(signin||register))}\n"
    "  $('#loginRecoveryTab')?.classList.toggle('active',recovery);$('#loginRecoveryTab')?.setAttribute('aria-selected',String(recovery));"
)
if old_mode not in app:
    raise RuntimeError("Expected login tab state block was not found")
app = app.replace(old_mode, new_mode, 1)
old_binding = "$('#loginSignInTab')?.addEventListener('click',()=>setLoginMode('signin'));"
new_binding = "$('#loginSignInTab')?.addEventListener('click',()=>setLoginMode(loginMode==='register'?'register':'signin'));"
if old_binding not in app:
    raise RuntimeError("Expected Sign in tab binding was not found")
app_path.write_text(app.replace(old_binding, new_binding, 1), encoding="utf-8")

sw_path = ROOT / "static/sw.js"
sw = sw_path.read_text(encoding="utf-8")
sw = sw.replace("torrent-dashboard-v05161", "torrent-dashboard-v05162").replace(OLD_VERSION, NEW_VERSION)
sw_path.write_text(sw, encoding="utf-8")

settings_path = ROOT / "static/settings.js"
settings = settings_path.read_text(encoding="utf-8")
pattern = re.compile(r"\n  function renderPendingUsers\(\) \{.*?\n  async function approvePendingUser", re.S)
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
      const body=pending
        ? `<div class="accordion-body ${index===0?'':'hidden'}"><div class="settings-form-grid two-col"><label>Username<input value="${esc(user.username||'')}" readonly></label><label>Status<input value="Pending" readonly></label></div><div class="settings-inline-actions"><button class="primary pending-user-approve" type="button">Approve</button><button class="danger pending-user-reject" type="button">Reject</button></div></div>`
        : `<div class="accordion-body ${index===0?'':'hidden'}"><div class="settings-form-grid two-col"><label><span class="field-label">Username <span class="required-mark" aria-hidden="true">*</span></span><input data-user-field="username" value="${esc(user.username||'')}" maxlength="128" autocomplete="off" required></label><label><span class="field-label">User group <span class="required-mark" aria-hidden="true">*</span></span><select class="user-group-select" data-user-field="group" required><option value="administrator" ${user.group==='administrator'?'selected':''}>Administrator</option><option value="standard" ${user.group==='standard'?'selected':''}>Standard user</option></select></label><label>First name<input data-user-field="first_name" value="${esc(user.first_name||'')}" maxlength="128"></label><label>Last name<input data-user-field="last_name" value="${esc(user.last_name||'')}" maxlength="128"></label><label class="full-field">Email<input data-user-field="email" type="email" value="${esc(user.email||'')}" maxlength="254"></label><label><span class="field-label">Password <span class="required-mark" aria-hidden="true">*</span></span><input data-user-field="password" type="password" autocomplete="new-password" required ${user._new?'placeholder="Create password"':'class="secret-configured" data-configured-secret="1" value="'+SECRET_MASK+'"'}></label><label><span class="field-label">Confirm password <span class="required-mark" aria-hidden="true">*</span></span><input data-user-field="password2" type="password" autocomplete="new-password" required ${user._new?'placeholder="Confirm password"':'class="secret-configured" data-configured-secret="1" value="'+SECRET_MASK+'"'}></label></div><div class="settings-inline-actions"><button class="primary user-save" type="button">Save</button><button class="danger user-delete" type="button" ${current?'disabled':''}>Delete</button></div></div>`;
      card.innerHTML=`<button class="accordion-summary" type="button" aria-expanded="${index===0?'true':'false'}"><span><span class="user-name-line"><b>${esc(display)}</b>${current?'<span class="current-user-badge">Current user</span>':''}</span>${showUsername?`<small>${esc(username)}</small>`:''}</span>${badge}<span class="accordion-chevron">⌄</span></button>${body}`;
      const summary=card.querySelector('.accordion-summary');
      summary.addEventListener('click',()=>{const body=card.querySelector('.accordion-body');const open=body.classList.contains('hidden');body.classList.toggle('hidden',!open);summary.setAttribute('aria-expanded',String(open))});
      if(pending){
        card.querySelector('.pending-user-approve').addEventListener('click',()=>approvePendingUser(user));
        card.querySelector('.pending-user-reject').addEventListener('click',()=>rejectPendingUser(user));
      }else{
        card.querySelector('.user-save').addEventListener('click',()=>saveUser(card));
        card.querySelector('.user-delete').addEventListener('click',()=>deleteUser(card,user));
        decorateSecretFields(card);
      }
      list.appendChild(card);
      applySentenceCaseUi(card);
    });
  }

  async function approvePendingUser'''
settings, count = pattern.subn(new_render, settings, count=1)
if count != 1:
    raise RuntimeError(f"Expected one pending/users rendering block; replaced {count}")
old_load = "      renderPendingUsers();\n      renderUsers();"
if old_load not in settings:
    raise RuntimeError("Expected renderPendingUsers/loadUsers sequence was not found")
settings_path.write_text(settings.replace(old_load, "      renderUsers();", 1), encoding="utf-8")

# Update focused UI contracts.
test_content = '''
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class RegistrationUiContractTests(unittest.TestCase):
    def test_public_registration_and_pending_users_share_existing_surfaces(self):
        html=(ROOT/"static"/"index.html").read_text(encoding="utf-8")
        app=(ROOT/"static"/"app.js").read_text(encoding="utf-8")
        settings=(ROOT/"static"/"settings.js").read_text(encoding="utf-8")
        self.assertIn('id="loginRegisterLink"',html)
        self.assertIn('>Create an account</button>',html)
        self.assertNotIn('id="loginRegisterTab"',html)
        self.assertIn('id="loginBackToSignIn"',html)
        self.assertIn('id="registerForm"',html)
        self.assertIn('id="registerUser"',html)
        self.assertIn('id="registerPass"',html)
        for removed in ('registerFirstName','registerLastName','registerEmail','registerPass2'):
            self.assertNotIn(f'id="{removed}"',html)
            self.assertNotIn(f"$('#{removed}')",app)
        self.assertIn("signInTab.textContent=register?'Sign up':'Sign in'",app)
        self.assertIn("signInTab.classList.toggle('active',signin||register)",app)
        self.assertNotIn('id="pendingUsersCard"',html)
        self.assertNotIn('id="pendingUserList"',html)
        self.assertIn('id="userList"',html)
        self.assertIn("const pending=user.status==='pending'",settings)
        self.assertIn('user-group-badge pending',settings)
        self.assertIn("post('/api/users/approve'",settings)
        self.assertIn("post('/api/users/reject'",settings)
        self.assertIn('>Pending</span>',settings)
        self.assertNotIn('Pending approval',settings)
        self.assertIn("rawJson('/api/register'",app)
        self.assertIn("setLoginMode('register')",app)

    def test_backend_marks_pending_login_and_exposes_approval_routes(self):
        source=(ROOT/"src"/"torrent_dashboard"/"dashboard.py").read_text(encoding="utf-8")
        self.assertIn('path=="/api/register"',source)
        self.assertIn('user.get("status") == "pending"',source)
        self.assertIn('Your account is Pending. An administrator must approve it before you can sign in.',source)
        self.assertNotIn('data.get("password2")',source)
        self.assertIn('path=="/api/users/approve"',source)
        self.assertIn('path=="/api/users/reject"',source)

if __name__ == "__main__":
    unittest.main()
'''
(ROOT / "tests/test_registration_ui.py").write_text(textwrap.dedent(test_content).lstrip(), encoding="utf-8")

validator_path = ROOT / "release_tools/validate_ui_strings.py"
validator = validator_path.read_text(encoding="utf-8")
marker = '    print("UI string audit passed")'
contract = '''    # 0.5.162 keeps registration mode visually distinct and folds Pending accounts into the Users list.
    assert "signInTab.textContent=register?'Sign up':'Sign in'" in app_js
    assert "signInTab.classList.toggle('active',signin||register)" in app_js
    assert 'id="pendingUsersCard"' not in html and 'id="pendingUserList"' not in html
    assert 'id="userList"' in html
    assert "const pending=user.status==='pending'" in settings_js
    assert 'user-group-badge pending' in settings_js
    assert "post('/api/users/approve'" in settings_js and "post('/api/users/reject'" in settings_js

    print("UI string audit passed")'''
if marker not in validator:
    raise RuntimeError("UI validator completion marker was not found")
validator_path.write_text(validator.replace(marker, contract, 1), encoding="utf-8")

# Release metadata drives generated changelog/project/handoff documents.
release_path = ROOT / "release_notes/releases.json"
release_data = json.loads(release_path.read_text(encoding="utf-8"))
release_data["releases"] = [r for r in release_data.get("releases", []) if r.get("version") != NEW_VERSION]
release_data["releases"].insert(0, {
    "version": NEW_VERSION,
    "date": "2026-09-14",
    "status": "prerelease",
    "title": "Unify Pending users and distinguish Sign up",
    "summary": "Makes account creation visibly distinct from sign-in and manages Pending registrations in the normal Users list instead of a separate queue.",
    "highlights": [
        "Shows Sign up in the access tab while the Create account pane is active, then restores Sign in when returning to login or Recovery.",
        "Removes the separate Pending registrations settings card and shows Pending accounts directly in the normal Users accordion list.",
        "Marks unapproved accounts with a Pending badge and keeps Approve and Reject actions inside that user entry."
    ],
    "fixes": [],
    "technical": [
        "Pending-account approval, rejection, Standard-user assignment, rate limits, and session blocking are unchanged.",
        "The existing Users list now renders both active and Pending account states from the same /api/users response."
    ],
    "validation": [
        "Adds registration UI contracts for the dynamic Sign up label and unified Pending-user list.",
        "Runs the standard Ubuntu/Windows Python 3.13/3.14 matrix, source updater build, and Windows executable smoke tests."
    ],
    "known_issues": [
        "Backup encryption remains opt-in; unencrypted portable backups can contain saved client and integration credentials and should be stored securely.",
        "Windows executables are not code-signed yet."
    ],
    "architecture": [
        "Account lifecycle state is presented inside one Users management surface instead of splitting Pending registrations into a separate administrative queue."
    ],
    "decisions": [
        "The primary access tab reads Sign up whenever the public registration pane is active.",
        "Pending registrations belong in the normal Users list and are distinguished with a Pending badge.",
        "Approval and rejection remain explicit administrator actions on the Pending user entry."
    ],
    "next_steps": [
        {"priority": 1, "title": "Verify unified account flow", "detail": "Open Create an account, confirm the access tab reads Sign up, register a test user, then approve it from the normal Users list."}
    ]
})
release_path.write_text(json.dumps(release_data, indent=2) + "\n", encoding="utf-8")

current_path = ROOT / "development/current.json"
current = json.loads(current_path.read_text(encoding="utf-8"))
current.update({
    "status": "release-candidate",
    "objective": "Publish v0.5.162 with a clearer Sign up state and unified user management",
    "why": "Account creation should be visibly distinct from sign-in, while administrators should manage active and Pending accounts from one consistent Users list.",
    "acceptance_criteria": [
        "The access tab reads Sign up while Create an account is active and returns to Sign in for normal login.",
        "Pending registrations appear in the normal Users list rather than a separate Pending registrations card.",
        "Pending accounts display a Pending badge and expose Approve and Reject from their accordion entry.",
        "Approved users retain the existing editable user fields and group controls.",
        "Registration approval, rejection, rate limiting, Standard-user assignment, and pending-session blocking remain unchanged.",
        "The full source matrix, source updater build, and compiled Windows smoke tests pass.",
        "v0.5.162 publishes source and Windows updater packages with SHA-256 digests."
    ],
    "decisions": [
        "Sign up is the visible access-tab label only while the registration pane is active.",
        "Pending registrations share the normal Users list and are distinguished with a Pending badge.",
        "Pending user details remain read-only until an administrator approves the account."
    ],
    "files": [
        "static/index.html",
        "static/app.js",
        "static/settings.js",
        "static/sw.js",
        "src/torrent_dashboard/__init__.py",
        "tests/test_registration_ui.py",
        "release_tools/validate_ui_strings.py",
        "release_notes/releases.json",
        "development/current.json"
    ],
    "blockers": [],
    "out_of_scope": [
        "No changes to registration rate limits, approval authorization, account roles, or authentication/session policy in this release."
    ],
    "next_action": "Run full pull-request validation and Windows packaging; if green, merge and verify the complete updater-visible v0.5.162 release."
})
current_path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
