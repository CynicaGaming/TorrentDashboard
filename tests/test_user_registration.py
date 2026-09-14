import time
import unittest

from torrent_dashboard.users import (
    approve_user, hash_password, public_user, register_user, reject_user, user_by_username,
)


class UserRegistrationTests(unittest.TestCase):
    def config(self):
        return {
            "auth": {},
            "users": [{
                "id": "admin", "username": "admin", "password_hash": hash_password("admin-pass"),
                "first_name": "", "last_name": "", "email": "", "avatar_file": "",
                "avatar_version": "", "group": "administrator", "status": "active", "created_at": int(time.time()),
            }],
        }

    def test_registration_creates_pending_standard_user(self):
        cfg,user=register_user(self.config(),{"username":"newuser","password":"password1","first_name":"New","email":"new@example.com"})
        self.assertEqual(user["status"],"pending")
        self.assertEqual(user["group"],"standard")
        self.assertTrue(user["password_hash"])
        self.assertEqual(public_user(user)["status_label"],"Pending")
        self.assertEqual(user_by_username(cfg,"NEWUSER")["id"],user["id"])

    def test_duplicate_username_is_rejected_case_insensitively(self):
        cfg,_=register_user(self.config(),{"username":"newuser","password":"password1"})
        with self.assertRaisesRegex(RuntimeError,"already in use"):
            register_user(cfg,{"username":"NEWUSER","password":"password2"})

    def test_approval_activates_pending_account(self):
        cfg,user=register_user(self.config(),{"username":"newuser","password":"password1"})
        cfg,approved=approve_user(cfg,user["id"])
        self.assertEqual(approved["status"],"active")
        self.assertEqual(user_by_username(cfg,"newuser")["status"],"active")

    def test_rejection_removes_pending_registration(self):
        cfg,user=register_user(self.config(),{"username":"newuser","password":"password1"})
        cfg,rejected=reject_user(cfg,user["id"])
        self.assertEqual(rejected["username"],"newuser")
        self.assertIsNone(user_by_username(cfg,"newuser"))

    def test_short_registration_password_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError,"at least 8"):
            register_user(self.config(),{"username":"newuser","password":"short"})


if __name__ == "__main__":
    unittest.main()
