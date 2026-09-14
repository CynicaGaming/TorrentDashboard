from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.5.160"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"Could not locate {label}")
    return text.replace(old, new, 1)


def sub_once(text: str, pattern: str, replacement: str, label: str) -> str:
    text, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f"Could not locate {label}")
    return text


# User lifecycle: active users plus public pending registrations.
users = read("src/torrent_dashboard/users.py")
users = replace_once(users, "import secrets\nimport uuid", "import secrets\nimport time\nimport uuid", "users time import")
users = replace_once(
    users,
    'USER_GROUPS = {\n    "administrator": "Administrator",\n    "standard": "Standard user",\n}\n',
    'USER_GROUPS = {\n    "administrator": "Administrator",\n    "standard": "Standard user",\n}\nUSER_STATUSES = {\n    "active": "Active",\n    "pending": "Pending approval",\n}\n',
    "user status labels",
)
users = replace_once(
    users,
    '    if require_password and not password_hash:\n        raise RuntimeError("Password is required for a new user")\n    return {',
    '    if require_password and not password_hash:\n        raise RuntimeError("Password is required for a new user")\n    status_raw = str(data.get("status") if data.get("status") is not None else existing.get("status") or "active").strip().lower()\n    status = "pending" if status_raw == "pending" else "active"\n    try:\n        created_at = int(data.get("created_at") if data.get("created_at") is not None else existing.get("created_at") or 0)\n    except (TypeError, ValueError):\n        created_at = 0\n    return {',
    "normalize user status",
)
users = replace_once(
    users,
    '        "group": group,\n    }\n\n\ndef public_user(user):',
    '        "group": group,\n        "status": status,\n        "created_at": created_at,\n    }\n\n\ndef public_user(user):',
    "normalized user lifecycle fields",
)
users = sub_once(
    users,
    r'def public_user\(user\):.*?\n\ndef _profile_avatar_stem',
    '''def public_user(user):\n    avatar_path, _ = configured_user_avatar(user)\n    status = "pending" if user.get("status") == "pending" else "active"\n    return {\n        "id": str(user.get("id") or ""),\n        "username": str(user.get("username") or ""),\n        "first_name": str(user.get("first_name") or ""),\n        "last_name": str(user.get("last_name") or ""),\n        "email": str(user.get("email") or ""),\n        "group": "administrator" if user.get("group") == "administrator" else "standard",\n        "group_label": USER_GROUPS.get(user.get("group"), "Standard user"),\n        "display_name": user_display_name(user),\n        "avatar_configured": bool(avatar_path),\n        "avatar_version": str(user.get("avatar_version") or ""),\n        "password_configured": bool(user.get("password_hash")),\n        "status": status,\n        "status_label": USER_STATUSES[status],\n        "created_at": int(user.get("created_at") or 0),\n    }\n\n\ndef _profile_avatar_stem''',
    "public user lifecycle",
)
users = sub_once(
    users,
    r'def sync_legacy_auth\(cfg\):.*?\n\ndef save_user',
    '''def sync_legacy_auth(cfg):\n    auth = cfg.setdefault("auth", {})\n    active = [u for u in cfg.get("users", []) if u.get("status", "active") != "pending"]\n    admins = [u for u in active if u.get("group") == "administrator"]\n    chosen = admins[0] if admins else (active or [None])[0]\n    if chosen:\n        auth["username"] = chosen.get("username", "admin")\n        auth["password_hash"] = chosen.get("password_hash", "")\n    else:\n        auth["username"] = "admin"\n        auth["password_hash"] = ""\n    return cfg\n\n\ndef save_user''',
    "legacy auth active-user selection",
)
users = replace_once(
    users,
    '    item = normalize_user(data, existing, require_password=existing is None)\n',
    '    payload = dict(data)\n    payload["status"] = str((existing or {}).get("status") or "active") if existing else "active"\n    payload["created_at"] = int((existing or {}).get("created_at") or time.time())\n    item = normalize_user(payload, existing, require_password=existing is None)\n',
    "administrator user save lifecycle",
)
registration_functions = '''\n\ndef register_user(cfg, data):\n    out = json.loads(json.dumps(cfg))\n    users = out.setdefault("users", [])\n    if sum(1 for user in users if user.get("status") == "pending") >= 50:\n        raise RuntimeError("Too many registrations are waiting for administrator review")\n    password = str(data.get("password") or "")\n    if len(password) < 8:\n        raise RuntimeError("Password must be at least 8 characters")\n    item = normalize_user(\n        {\n            "username": data.get("username"),\n            "password": password,\n            "first_name": data.get("first_name"),\n            "last_name": data.get("last_name"),\n            "email": data.get("email"),\n            "group": "standard",\n            "status": "pending",\n            "created_at": int(time.time()),\n        },\n        require_password=True,\n    )\n    duplicate = next(\n        (\n            user for user in users\n            if str(user.get("username") or "").casefold() == item["username"].casefold()\n        ),\n        None,\n    )\n    if duplicate:\n        raise RuntimeError("That username is already in use")\n    users.append(item)\n    sync_legacy_auth(out)\n    return out, item\n\n\ndef approve_user(cfg, user_id):\n    out = json.loads(json.dumps(cfg))\n    user = user_by_id(out, user_id)\n    if not user:\n        raise RuntimeError("Registration was not found")\n    if user.get("status") != "pending":\n        raise RuntimeError("This user is not waiting for approval")\n    user["status"] = "active"\n    user["group"] = "standard"\n    sync_legacy_auth(out)\n    return out, user\n\n\ndef reject_user(cfg, user_id):\n    out = json.loads(json.dumps(cfg))\n    user = user_by_id(out, user_id)\n    if not user:\n        raise RuntimeError("Registration was not found")\n    if user.get("status") != "pending":\n        raise RuntimeError("This user is not waiting for approval")\n    out["users"] = [item for item in out.get("users", []) if str(item.get("id") or "") != str(user_id or "")]\n    sync_legacy_auth(out)\n    return out, user\n'''
users = replace_once(users, "\ndef delete_user(cfg, user_id, current_user_id=\"\"):\n", registration_functions + "\n\ndef delete_user(cfg, user_id, current_user_id=\"\"):\n", "registration domain operations")
users = replace_once(users, '    "USER_GROUPS",\n', '    "USER_GROUPS",\n    "USER_STATUSES",\n    "approve_user",\n', "user exports start")
users = replace_once(users, '    "remove_user_avatar",\n', '    "register_user",\n    "reject_user",\n    "remove_user_avatar",\n', "registration exports")
write("src/torrent_dashboard/users.py", users)

# Public registration endpoint, pending-login response, and administrator approval actions.
dashboard = read("src/torrent_dashboard/dashboard.py")
dashboard = replace_once(dashboard, "    change_current_user_password,\n", "    approve_user,\n    change_current_user_password,\n", "approve user import")
dashboard = replace_once(dashboard, "    remove_user_avatar,\n", "    register_user,\n    reject_user,\n    remove_user_avatar,\n", "registration user imports")
dashboard = replace_once(
    dashboard,
    "LOGIN_ATTEMPTS = defaultdict(deque)\nLOGIN_LOCK = threading.Lock()\n",
    "LOGIN_ATTEMPTS = defaultdict(deque)\nLOGIN_LOCK = threading.Lock()\nREGISTRATION_ATTEMPTS = defaultdict(deque)\nREGISTRATION_LOCK = threading.Lock()\n",
    "registration rate-limit state",
)
register_method = '''    def register_route(self):\n        cfg=load_config(); ip=self.client_ip(); now=time.time()\n        if not cfg.get("setup",{}).get("complete"):\n            return self.send_json(409,{"error":"Finish dashboard setup before registering an account"})\n        if str((cfg.get("auth") or {}).get("mode") or "required") == "disabled":\n            return self.send_json(409,{"error":"Account registration is unavailable while authentication is disabled"})\n        with REGISTRATION_LOCK:\n            q=REGISTRATION_ATTEMPTS[ip]\n            while q and q[0]<now-3600: q.popleft()\n            if len(q)>=5: return self.send_json(429,{"error":"Too many registration attempts. Try again later."})\n            q.append(now)\n        try: data=parse_json_body(self,20000)\n        except Exception as e: return self.send_json(400,{"error":str(e)})\n        if str(data.get("password") or "") != str(data.get("password2") or ""):\n            return self.send_json(400,{"error":"Passwords do not match"})\n        try:\n            updated,user=mutate_config(lambda current: register_user(current,data))\n            HISTORY.event("dashboard","user_registration_pending",user.get("username",""),"",{"client_ip":ip,"user_id":user.get("id","")})\n            return self.send_json(202,{"ok":True,"status":"pending","message":"Registration submitted. Your account is pending administrator approval."})\n        except Exception as e:\n            return self.send_json(400,{"error":str(e)})\n\n'''
dashboard = replace_once(dashboard, "    def login_route(self):\n", register_method + "    def login_route(self):\n", "public registration route method")
dashboard = replace_once(
    dashboard,
    '        if not user or not encoded or not verify_password(str(data.get("password","")),encoded):\n            HISTORY.event("dashboard", "login_failed", username[:128], "", {"client_ip": ip})\n            return self.send_json(401,{"error":"Invalid username or password"})\n        token,sess=SESSIONS.create',
    '        if not user or not encoded or not verify_password(str(data.get("password","")),encoded):\n            HISTORY.event("dashboard", "login_failed", username[:128], "", {"client_ip": ip})\n            return self.send_json(401,{"error":"Invalid username or password"})\n        if user.get("status") == "pending":\n            HISTORY.event("dashboard", "login_pending_approval", username[:128], "", {"client_ip": ip, "user_id": user.get("id", "")})\n            return self.send_json(403,{"error":"Your account is pending administrator approval."})\n        token,sess=SESSIONS.create',
    "pending login status response",
)
dashboard = replace_once(
    dashboard,
    '        if path=="/api/setup/complete": return self.setup_complete()\n        if path=="/api/login": return self.login_route()\n',
    '        if path=="/api/setup/complete": return self.setup_complete()\n        if path=="/api/register": return self.register_route()\n        if path=="/api/login": return self.login_route()\n',
    "public registration post route",
)
user_actions = '''            if path=="/api/users/approve":\n                data=parse_json_body(self,10000); uid=str(data.get("id") or "")\n                updated,user=mutate_config(lambda current: approve_user(current,uid))\n                HISTORY.event("dashboard","user_registration_approved",user.get("username",""),"",{"client_ip":self.client_ip(),"user_id":uid,"approved_by":sess.get("username","")})\n                return self.send_json(200,{"ok":True,"user":public_user(user)},new_cookie)\n            if path=="/api/users/reject":\n                data=parse_json_body(self,10000); uid=str(data.get("id") or "")\n                updated,user=mutate_config(lambda current: reject_user(current,uid)); delete_user_avatar_files(uid); SESSIONS.remove_user(uid)\n                HISTORY.event("dashboard","user_registration_rejected",user.get("username",""),"",{"client_ip":self.client_ip(),"user_id":uid,"rejected_by":sess.get("username","")})\n                return self.send_json(200,{"ok":True},new_cookie)\n'''
dashboard = replace_once(dashboard, '            if path=="/api/users":\n', user_actions + '            if path=="/api/users":\n', "administrator registration actions")
write("src/torrent_dashboard/dashboard.py", dashboard)

# Login registration form and pending registrations in Users.
html = read("static/index.html")
html = replace_once(
    html,
    '<button class="active" id="loginSignInTab" type="button" aria-selected="true">Sign in</button><button id="loginRecoveryTab" type="button" aria-selected="false">Recovery</button>',
    '<button class="active" id="loginSignInTab" type="button" aria-selected="true">Sign in</button><button id="loginRegisterTab" type="button" aria-selected="false">Register</button><button id="loginRecoveryTab" type="button" aria-selected="false">Recovery</button>',
    "registration login tab",
)
register_pane = '<section class="login-pane hidden" id="loginRegisterPane"><h1>Create account</h1><p>Register for access. An administrator must approve your account before you can sign in.</p><form autocomplete="off" id="registerForm"><input autocapitalize="none" autocomplete="username" id="registerUser" placeholder="Username" spellcheck="false" required/><div class="two"><input autocomplete="given-name" id="registerFirstName" maxlength="128" placeholder="First name"/><input autocomplete="family-name" id="registerLastName" maxlength="128" placeholder="Last name"/></div><input autocomplete="email" id="registerEmail" maxlength="254" placeholder="Email (optional)" type="email"/><input autocomplete="new-password" id="registerPass" placeholder="Password" type="password" required/><input autocomplete="new-password" id="registerPass2" placeholder="Confirm password" type="password" required/><button class="primary" type="submit">Register</button><div class="form-error" id="registerError"></div><div class="test-result muted" id="registerStatus"></div></form></section>'
html = sub_once(
    html,
    r'(<section class="login-pane hidden" id="loginRecoveryPane">.*?</section>)(</div></div>\n<div class="app hidden" id="app">)',
    r'\1' + register_pane + r'\2',
    "registration login pane",
)
old_users = '<section class="settings-page" data-settings-section="users">\n<div class="panel settings-card"><div class="panel-title">Users</div><p class="muted user-management-intro">Administrators can manage the dashboard. Standard users have read-only dashboard access and can manage their own account.</p><div class="settings-inline-actions"><button class="primary" id="addUserSetting" type="button">＋ Add user</button></div><div id="userList"></div></div>\n</section>'
new_users = '<section class="settings-page" data-settings-section="users">\n<div class="panel settings-card" id="pendingUsersCard"><div class="panel-title">Pending registrations</div><p class="muted">New registrations cannot sign in until an administrator approves them.</p><div id="pendingUserList"></div></div>\n<div class="panel settings-card"><div class="panel-title">Users</div><p class="muted user-management-intro">Administrators can manage approved dashboard users. Standard users have read-only dashboard access and can manage their own account.</p><div class="settings-inline-actions"><button class="primary" id="addUserSetting" type="button">＋ Add user</button></div><div id="userList"></div></div>\n</section>'
html = replace_once(html, old_users, new_users, "pending registrations settings card")
write("static/index.html", html)

# Public form behavior.
app = read("static/app.js")
app = sub_once(
    app,
    r"let loginMode='signin';\nfunction setLoginMode\(mode='signin'\)\{.*?\}\nlet setupRecoveryReadyAt=0,setupRecoveryTimer=null;",
    '''let loginMode='signin';\nfunction setLoginMode(mode='signin'){\n  loginMode=['signin','register','recovery'].includes(mode)?mode:'signin';\n  const signin=loginMode==='signin',register=loginMode==='register',recovery=loginMode==='recovery';\n  $('#loginSignInPane')?.classList.toggle('hidden',!signin);$('#loginRegisterPane')?.classList.toggle('hidden',!register);$('#loginRecoveryPane')?.classList.toggle('hidden',!recovery);\n  $('#loginSignInTab')?.classList.toggle('active',signin);$('#loginRegisterTab')?.classList.toggle('active',register);$('#loginRecoveryTab')?.classList.toggle('active',recovery);\n  $('#loginSignInTab')?.setAttribute('aria-selected',String(signin));$('#loginRegisterTab')?.setAttribute('aria-selected',String(register));$('#loginRecoveryTab')?.setAttribute('aria-selected',String(recovery));\n  setTimeout(()=>{if(register)$('#registerUser')?.focus();else if(recovery)$('#recoveryKey')?.focus();else $('#loginUser')?.focus()},0);\n}\nlet setupRecoveryReadyAt=0,setupRecoveryTimer=null;''',
    "three-mode login switcher",
)
register_js = '''async function registerAccount(event){event.preventDefault();const error=$('#registerError'),status=$('#registerStatus'),button=$('#registerForm button[type="submit"]');if(error)error.textContent='';if(status){status.className='test-result muted';status.textContent=''}const password=$('#registerPass')?.value||'',confirmation=$('#registerPass2')?.value||'';if(password.length<8){if(error)error.textContent='Password must be at least 8 characters';return}if(password!==confirmation){if(error)error.textContent='Passwords do not match';return}if(button)button.disabled=true;try{const data=await rawJson('/api/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:$('#registerUser')?.value.trim()||'',first_name:$('#registerFirstName')?.value.trim()||'',last_name:$('#registerLastName')?.value.trim()||'',email:$('#registerEmail')?.value.trim()||'',password,password2:confirmation})});$('#registerForm')?.reset();if(status){status.className='test-result ok';status.textContent=data.message||'Registration submitted. Your account is pending administrator approval.'}}catch(err){if(error)error.textContent=err.message||'Registration could not be submitted'}finally{if(button)button.disabled=false}}\n'''
app = replace_once(app, "async function recoverDashboard(event){", register_js + "async function recoverDashboard(event){", "registration submit handler")
app = replace_once(
    app,
    "$('#recoveryLoginForm')?.addEventListener('submit',recoverDashboard);$('#loginSignInTab')?.addEventListener('click',()=>setLoginMode('signin'));$('#loginRecoveryTab')?.addEventListener('click',()=>setLoginMode('recovery'));",
    "$('#registerForm')?.addEventListener('submit',registerAccount);$('#recoveryLoginForm')?.addEventListener('submit',recoverDashboard);$('#loginSignInTab')?.addEventListener('click',()=>setLoginMode('signin'));$('#loginRegisterTab')?.addEventListener('click',()=>setLoginMode('register'));$('#loginRecoveryTab')?.addEventListener('click',()=>setLoginMode('recovery'));",
    "registration public bindings",
)
write("static/app.js", app)

# Administrator pending-registration queue.
settings = read("static/settings.js")
render_block = '''  function renderPendingUsers() {\n    const list=document.querySelector('#pendingUserList');\n    if(!list)return;\n    const pending=users.filter(user=>user.status==='pending');\n    if(!pending.length){list.innerHTML='<div class="settings-empty"><b>No pending registrations</b><span>New registration requests will appear here for approval.</span></div>';return}\n    list.innerHTML='';\n    pending.forEach((user,index)=>{\n      const card=document.createElement('article');card.className='settings-accordion user-item';card.dataset.id=user.id||'';\n      const display=userName(user),username=user.username||'User',showUsername=display!==username;\n      card.innerHTML=`<button class="accordion-summary" type="button" aria-expanded="${index===0?'true':'false'}"><span><span class="user-name-line"><b>${esc(display)}</b></span>${showUsername?`<small>${esc(username)}</small>`:''}</span><span class="user-group-badge pending">Pending approval</span><span class="accordion-chevron">⌄</span></button><div class="accordion-body ${index===0?'':'hidden'}"><div class="settings-form-grid two-col"><label>Username<input value="${esc(user.username||'')}" readonly></label><label>Email<input value="${esc(user.email||'')}" readonly></label><label>First name<input value="${esc(user.first_name||'')}" readonly></label><label>Last name<input value="${esc(user.last_name||'')}" readonly></label></div><div class="settings-inline-actions"><button class="primary pending-user-approve" type="button">Approve</button><button class="danger pending-user-reject" type="button">Reject</button></div></div>`;\n      const summary=card.querySelector('.accordion-summary');summary.addEventListener('click',()=>{const body=card.querySelector('.accordion-body');const open=body.classList.contains('hidden');body.classList.toggle('hidden',!open);summary.setAttribute('aria-expanded',String(open))});\n      card.querySelector('.pending-user-approve').addEventListener('click',()=>approvePendingUser(user));\n      card.querySelector('.pending-user-reject').addEventListener('click',()=>rejectPendingUser(user));\n      list.appendChild(card);applySentenceCaseUi(card);\n    });\n  }\n\n  function renderUsers() {\n    const list = document.querySelector('#userList');\n    if (!list) return;\n    const approvedUsers=users.filter(user=>user.status!=='pending');\n    if (!approvedUsers.length) {\n      list.innerHTML='<div class="settings-empty"><b>No users found</b><span>Add an administrator account to manage Torrent Dashboard.</span></div>';\n      return;\n    }\n    list.innerHTML='';\n    approvedUsers.forEach((user,index) => {\n      const card=document.createElement('article');\n      card.className='settings-accordion user-item';\n      card.dataset.id=user.id||'';\n      const group=user.group==='administrator'?'Administrator':'Standard user';\n      const current=user.id && user.id===currentUserId;\n      const display=userName(user);\n      const username=user.username||'New user';\n      const showUsername=!!user.username && display!==user.username;\n      card.innerHTML=`<button class="accordion-summary" type="button" aria-expanded="${index===0?'true':'false'}"><span><span class="user-name-line"><b>${esc(display)}</b>${current?'<span class="current-user-badge">Current user</span>':''}</span>${showUsername?`<small>${esc(username)}</small>`:''}</span><span class="user-group-badge ${user.group==='administrator'?'admin':'standard'}">${esc(group)}</span><span class="accordion-chevron">⌄</span></button><div class="accordion-body ${index===0?'':'hidden'}"><div class="settings-form-grid two-col"><label><span class="field-label">Username <span class="required-mark" aria-hidden="true">*</span></span><input data-user-field="username" value="${esc(user.username||'')}" maxlength="128" autocomplete="off" required></label><label><span class="field-label">User group <span class="required-mark" aria-hidden="true">*</span></span><select class="user-group-select" data-user-field="group" required><option value="administrator" ${user.group==='administrator'?'selected':''}>Administrator</option><option value="standard" ${user.group==='standard'?'selected':''}>Standard user</option></select></label><label>First name<input data-user-field="first_name" value="${esc(user.first_name||'')}" maxlength="128"></label><label>Last name<input data-user-field="last_name" value="${esc(user.last_name||'')}" maxlength="128"></label><label class="full-field">Email<input data-user-field="email" type="email" value="${esc(user.email||'')}" maxlength="254"></label><label><span class="field-label">Password <span class="required-mark" aria-hidden="true">*</span></span><input data-user-field="password" type="password" autocomplete="new-password" required ${user._new?'placeholder="Create password"':'class="secret-configured" data-configured-secret="1" value="'+SECRET_MASK+'"'}></label><label><span class="field-label">Confirm password <span class="required-mark" aria-hidden="true">*</span></span><input data-user-field="password2" type="password" autocomplete="new-password" required ${user._new?'placeholder="Confirm password"':'class="secret-configured" data-configured-secret="1" value="'+SECRET_MASK+'"'}></label></div><div class="settings-inline-actions"><button class="primary user-save" type="button">Save</button><button class="danger user-delete" type="button" ${current?'disabled':''}>Delete</button></div></div>`;\n      const summary=card.querySelector('.accordion-summary');\n      summary.addEventListener('click',()=>{const body=card.querySelector('.accordion-body');const open=body.classList.contains('hidden');body.classList.toggle('hidden',!open);summary.setAttribute('aria-expanded',String(open))});\n      card.querySelector('.user-save').addEventListener('click',()=>saveUser(card));\n      card.querySelector('.user-delete').addEventListener('click',()=>deleteUser(card,user));\n      list.appendChild(card);\n      decorateSecretFields(card);\n      applySentenceCaseUi(card);\n    });\n  }\n\n  async function approvePendingUser(user){try{await post('/api/users/approve',{id:user.id});toast('Registration approved');await loadUsers()}catch(e){toast(e.message,'error')}}\n  async function rejectPendingUser(user){try{await post('/api/users/reject',{id:user.id});toast('Registration rejected');await loadUsers()}catch(e){toast(e.message,'error')}}\n\n  async function loadUsers()'''
settings = sub_once(settings, r'  function renderUsers\(\) \{.*?\n  async function loadUsers\(\)', render_block, "pending registration user rendering")
settings = replace_once(settings, "      renderUsers();\n", "      renderPendingUsers();\n      renderUsers();\n", "pending user list refresh")
write("static/settings.js", settings)

# Pending badge styling.
settings_css = read("static/settings.css")
if ".user-group-badge.pending{" not in settings_css:
    settings_css += "\n/* v0.5.160 pending registration state */\n.user-group-badge.pending{border-color:color-mix(in srgb,#f5c451 45%,var(--border));background:color-mix(in srgb,#f5c451 10%,transparent);color:#f5c451}\n"
write("static/settings.css", settings_css)

# Regression coverage.
registration_tests = '''import time\nimport unittest\n\nfrom torrent_dashboard.users import (\n    approve_user, hash_password, public_user, register_user, reject_user, user_by_username,\n)\n\n\nclass UserRegistrationTests(unittest.TestCase):\n    def config(self):\n        return {\n            "auth": {},\n            "users": [{\n                "id": "admin", "username": "admin", "password_hash": hash_password("admin-pass"),\n                "first_name": "", "last_name": "", "email": "", "avatar_file": "",\n                "avatar_version": "", "group": "administrator", "status": "active", "created_at": int(time.time()),\n            }],\n        }\n\n    def test_registration_creates_pending_standard_user(self):\n        cfg,user=register_user(self.config(),{"username":"newuser","password":"password1","first_name":"New","email":"new@example.com"})\n        self.assertEqual(user["status"],"pending")\n        self.assertEqual(user["group"],"standard")\n        self.assertTrue(user["password_hash"])\n        self.assertEqual(public_user(user)["status_label"],"Pending approval")\n        self.assertEqual(user_by_username(cfg,"NEWUSER")["id"],user["id"])\n\n    def test_duplicate_username_is_rejected_case_insensitively(self):\n        cfg,_=register_user(self.config(),{"username":"newuser","password":"password1"})\n        with self.assertRaisesRegex(RuntimeError,"already in use"):\n            register_user(cfg,{"username":"NEWUSER","password":"password2"})\n\n    def test_approval_activates_pending_account(self):\n        cfg,user=register_user(self.config(),{"username":"newuser","password":"password1"})\n        cfg,approved=approve_user(cfg,user["id"])\n        self.assertEqual(approved["status"],"active")\n        self.assertEqual(user_by_username(cfg,"newuser")["status"],"active")\n\n    def test_rejection_removes_pending_registration(self):\n        cfg,user=register_user(self.config(),{"username":"newuser","password":"password1"})\n        cfg,rejected=reject_user(cfg,user["id"])\n        self.assertEqual(rejected["username"],"newuser")\n        self.assertIsNone(user_by_username(cfg,"newuser"))\n\n    def test_short_registration_password_is_rejected(self):\n        with self.assertRaisesRegex(RuntimeError,"at least 8"):\n            register_user(self.config(),{"username":"newuser","password":"short"})\n\n\nif __name__ == "__main__":\n    unittest.main()\n'''
write("tests/test_user_registration.py", registration_tests)
contract_tests = '''from pathlib import Path\nimport unittest\n\nROOT=Path(__file__).resolve().parents[1]\n\nclass RegistrationUiContractTests(unittest.TestCase):\n    def test_public_registration_form_and_pending_admin_queue_exist(self):\n        html=(ROOT/"static"/"index.html").read_text(encoding="utf-8")\n        app=(ROOT/"static"/"app.js").read_text(encoding="utf-8")\n        settings=(ROOT/"static"/"settings.js").read_text(encoding="utf-8")\n        self.assertIn('id="loginRegisterTab"',html)\n        self.assertIn('id="registerForm"',html)\n        self.assertIn('id="pendingUserList"',html)\n        self.assertIn("rawJson('/api/register'",app)\n        self.assertIn("setLoginMode('register')",app)\n        self.assertIn("post('/api/users/approve'",settings)\n        self.assertIn("post('/api/users/reject'",settings)\n        self.assertIn('Pending approval',settings)\n\n    def test_backend_marks_pending_login_and_exposes_approval_routes(self):\n        source=(ROOT/"src"/"torrent_dashboard"/"dashboard.py").read_text(encoding="utf-8")\n        self.assertIn('path=="/api/register"',source)\n        self.assertIn('user.get("status") == "pending"',source)\n        self.assertIn('Your account is pending administrator approval.',source)\n        self.assertIn('path=="/api/users/approve"',source)\n        self.assertIn('path=="/api/users/reject"',source)\n\nif __name__ == "__main__":\n    unittest.main()\n'''
write("tests/test_registration_ui.py", contract_tests)

# Validation contracts for the new public/admin flow.
validator = read("release_tools/validate_ui_strings.py")
anchor = "    assert 'Recovery.exe' in html\n"
validator = replace_once(
    validator,
    anchor,
    anchor + "    assert 'id=\"loginRegisterTab\"' in html and 'id=\"registerForm\"' in html\n    assert 'id=\"pendingUserList\"' in html\n    assert \"rawJson('/api/register'\" in app_js\n    assert \"post('/api/users/approve'\" in settings_js and \"post('/api/users/reject'\" in settings_js\n    assert 'path==\"/api/register\"' in dashboard_py and 'pending administrator approval' in dashboard_py\n",
    "registration UI validation contract",
)
write("release_tools/validate_ui_strings.py", validator)

# Version/frontend cache markers.
init = read("src/torrent_dashboard/__init__.py").replace('__version__ = "0.5.159"', f'__version__ = "{VERSION}"', 1)
if VERSION not in init:
    raise SystemExit("Version bump failed")
write("src/torrent_dashboard/__init__.py", init)
app = read("static/app.js").replace("const FRONTEND_BUILD='0.5.159';", f"const FRONTEND_BUILD='{VERSION}';", 1)
write("static/app.js", app)
html = read("static/index.html").replace("0.5.159", VERSION)
write("static/index.html", html)
sw = read("static/sw.js").replace("torrent-dashboard-v05159", "torrent-dashboard-v05160").replace("0.5.159", VERSION)
write("static/sw.js", sw)

# Release metadata and handoff state.
release_path=ROOT/"release_notes"/"releases.json"
release_data=json.loads(release_path.read_text(encoding="utf-8"))
if any(str(item.get("version"))==VERSION for item in release_data.get("releases",[])):
    raise SystemExit(f"Release {VERSION} already exists")
release_data["releases"].insert(0,{
    "version":VERSION,
    "date":"2026-09-14",
    "status":"prerelease",
    "title":"Self-registration with administrator approval",
    "summary":"Adds public account registration while keeping access administrator-controlled: new accounts remain pending until approved from Settings → Users.",
    "highlights":[
        "Adds a Register tab beside Sign in and Recovery with username, optional profile details, and password fields.",
        "New registrations are stored as Standard users in Pending approval state and cannot create sessions.",
        "Settings → Users now shows a Pending registrations queue with Approve and Reject actions.",
        "A pending user who enters the correct credentials is told that the account is waiting for administrator approval."
    ],
    "fixes":[],
    "technical":[
        "Registration is rate-limited to five submissions per client IP per hour and capped at 50 simultaneously pending accounts.",
        "Pending accounts are excluded from legacy authentication fallback and are never promoted to Administrator by approval.",
        "Reject removes the pending registration so the username can be registered again later.",
        "Approval and rejection are recorded in dashboard history for administrator auditing."
    ],
    "validation":[
        "Adds domain tests for pending creation, duplicate prevention, approval, rejection, and password validation.",
        "Adds browser/backend contract tests for the registration form, pending login response, and administrator approval routes.",
        "Runs the standard Ubuntu/Windows Python 3.13/3.14 matrix, source updater build, and Windows executable smoke tests."
    ],
    "known_issues":[
        "Backup encryption remains opt-in; unencrypted portable backups can contain saved client and integration credentials and should be stored securely.",
        "Windows executables are not code-signed yet."
    ],
    "architecture":[
        "User lifecycle now distinguishes approved active accounts from public pending registrations while preserving the existing Administrator/Standard authorization model."
    ],
    "decisions":[
        "Self-registration never grants Administrator access; approval always activates the account as a Standard user.",
        "Pending status is revealed only after valid credentials are supplied, avoiding account-status disclosure to unauthenticated guesses.",
        "Rejected registrations are removed rather than retained as long-lived rejected identities."
    ],
    "next_steps":[{"priority":1,"title":"Verify registration and approval","detail":"Register a test account from the login page, confirm pending login messaging, approve it from Users, and verify Standard-user access."}]
})
release_path.write_text(json.dumps(release_data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
active={
    "schema":1,
    "status":"release-candidate",
    "objective":"Publish v0.5.160 with self-registration and administrator approval",
    "why":"Users need a way to request dashboard access without administrators manually creating every account, while administrators must retain final control over who can sign in.",
    "acceptance_criteria":[
        "The public login card offers Register, Sign in, and Recovery modes.",
        "A registration creates a pending Standard user and never creates a session.",
        "Valid credentials for a pending account return a clear pending-approval message.",
        "Administrators can approve or reject requests under Settings → Users.",
        "Approved users can sign in as Standard users; rejected usernames can register again.",
        "Registration is rate-limited and duplicate usernames are rejected case-insensitively.",
        "The full source matrix, source updater build, and compiled Windows smoke tests pass.",
        "v0.5.160 publishes source and Windows updater packages with SHA-256 digests."
    ],
    "decisions":[
        "Approval always activates registrations as Standard users.",
        "Pending status is returned only after correct credentials are verified.",
        "Reject deletes the pending registration rather than preserving a rejected account record."
    ],
    "files":[
        "src/torrent_dashboard/users.py","src/torrent_dashboard/dashboard.py","static/index.html","static/app.js","static/settings.js","static/settings.css","tests/test_user_registration.py","tests/test_registration_ui.py","release_tools/validate_ui_strings.py","release_notes/releases.json","development/current.json"
    ],
    "blockers":[],
    "out_of_scope":["No email verification, invitation codes, CAPTCHA, MFA, or automatic approval in this release."],
    "next_action":"Run full pull-request validation and Windows packaging; if green, merge and verify the complete updater-visible v0.5.160 release."
}
(ROOT/"development"/"current.json").write_text(json.dumps(active,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
