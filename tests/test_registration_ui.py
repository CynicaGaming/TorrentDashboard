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
        self.assertIn("const password=$('#registerPass')?.value||'',password2=$('#registerPass2')?.value||'';",app)
        self.assertIn('Passwords do not match',app)
        self.assertIn('password,password2',app)
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
