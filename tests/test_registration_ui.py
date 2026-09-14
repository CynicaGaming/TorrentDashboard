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
