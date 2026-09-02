from __future__ import annotations

import unittest

from torrent_dashboard.users import (
    change_current_user_password,
    delete_user,
    hash_password,
    normalize_user,
    save_current_user_profile,
    save_user,
    verify_password,
)


class UserDomainTests(unittest.TestCase):
    def test_password_hash_round_trip(self):
        encoded = hash_password("correct horse battery staple")
        self.assertTrue(verify_password("correct horse battery staple", encoded))
        self.assertFalse(verify_password("wrong password", encoded))

    def test_normalize_user_rejects_invalid_username(self):
        with self.assertRaisesRegex(RuntimeError, "Username may contain"):
            normalize_user({"username": "bad user", "password": "password123"}, require_password=True)

    def test_save_user_rejects_duplicate_username_case_insensitively(self):
        first = normalize_user({"id": "u1", "username": "Admin", "password": "password123", "group": "administrator"}, require_password=True)
        cfg = {"users": [first], "auth": {}}
        with self.assertRaisesRegex(RuntimeError, "already in use"):
            save_user(cfg, {"id": "u2", "username": "admin", "password": "password456", "group": "standard"})

    def test_delete_user_preserves_last_administrator_invariant(self):
        admin = normalize_user({"id": "admin", "username": "admin", "password": "password123", "group": "administrator"}, require_password=True)
        standard = normalize_user({"id": "user", "username": "user", "password": "password123", "group": "standard"}, require_password=True)
        cfg = {"users": [admin, standard], "auth": {}}
        with self.assertRaisesRegex(RuntimeError, "At least one Administrator"):
            delete_user(cfg, "admin")

    def test_self_service_profile_preserves_role_and_requires_password_for_email(self):
        admin = normalize_user({
            "id": "admin",
            "username": "admin",
            "password": "password123",
            "group": "administrator",
            "email": "old@example.test",
        }, require_password=True)
        cfg = {"users": [admin], "auth": {}}

        with self.assertRaisesRegex(RuntimeError, "Current password is required"):
            save_current_user_profile(cfg, "admin", {"email": "new@example.test"})

        updated_cfg, updated = save_current_user_profile(cfg, "admin", {
            "email": "new@example.test",
            "current_password": "password123",
            "first_name": "Torrent",
        })
        self.assertEqual(updated["group"], "administrator")
        self.assertEqual(updated["email"], "new@example.test")
        self.assertEqual(updated_cfg["users"][0]["group"], "administrator")

    def test_password_change_requires_existing_password_and_minimum_length(self):
        user = normalize_user({"id": "u1", "username": "user", "password": "password123", "group": "standard"}, require_password=True)
        cfg = {"users": [user], "auth": {}}
        with self.assertRaisesRegex(RuntimeError, "incorrect"):
            change_current_user_password(cfg, "u1", "wrong", "new-password")
        with self.assertRaisesRegex(RuntimeError, "at least 8"):
            change_current_user_password(cfg, "u1", "password123", "short")

        updated_cfg, updated = change_current_user_password(cfg, "u1", "password123", "new-password")
        self.assertTrue(verify_password("new-password", updated["password_hash"]))
        self.assertEqual(updated_cfg["users"][0]["group"], "standard")


if __name__ == "__main__":
    unittest.main()
