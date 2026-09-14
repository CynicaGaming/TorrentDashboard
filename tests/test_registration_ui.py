from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class RegistrationUiContractTests(unittest.TestCase):
    def test_public_registration_form_and_pending_admin_queue_exist(self):
        html=(ROOT/"static"/"index.html").read_text(encoding="utf-8")
        app=(ROOT/"static"/"app.js").read_text(encoding="utf-8")
        settings=(ROOT/"static"/"settings.js").read_text(encoding="utf-8")
        self.assertIn('id="loginRegisterTab"',html)
        self.assertIn('id="registerForm"',html)
        self.assertIn('id="pendingUserList"',html)
        self.assertIn("rawJson('/api/register'",app)
        self.assertIn("setLoginMode('register')",app)
        self.assertIn("post('/api/users/approve'",settings)
        self.assertIn("post('/api/users/reject'",settings)
        self.assertIn('Pending approval',settings)

    def test_backend_marks_pending_login_and_exposes_approval_routes(self):
        source=(ROOT/"src"/"torrent_dashboard"/"dashboard.py").read_text(encoding="utf-8")
        self.assertIn('path=="/api/register"',source)
        self.assertIn('user.get("status") == "pending"',source)
        self.assertIn('Your account is pending administrator approval.',source)
        self.assertIn('path=="/api/users/approve"',source)
        self.assertIn('path=="/api/users/reject"',source)

if __name__ == "__main__":
    unittest.main()
