from __future__ import annotations
import unittest
from torrent_dashboard.recovery import RECOVERY_ACCOUNT_ID, RECOVERY_ACCOUNT_USERNAME, generate_dashboard_recovery_key, normalize_dashboard_recovery_key, recovery_key_record, verify_dashboard_recovery_key

class DashboardRecoveryTests(unittest.TestCase):
    def test_dashboard_recovery_key_round_trip(self):
        key=generate_dashboard_recovery_key(); record=recovery_key_record(key)
        self.assertTrue(key.startswith("TDRK-")); self.assertTrue(verify_dashboard_recovery_key(key,record["key_hash"]))
        self.assertFalse(verify_dashboard_recovery_key(key+"X",record["key_hash"]))
        self.assertNotEqual(record["key_hash"],normalize_dashboard_recovery_key(key))
        self.assertEqual(record["last4"],normalize_dashboard_recovery_key(key)[-4:])
    def test_key_is_opaque_and_random(self):
        first=generate_dashboard_recovery_key(); second=generate_dashboard_recovery_key(); self.assertNotEqual(first,second)
        normalized=normalize_dashboard_recovery_key(first); self.assertNotIn("ADMINISTRATOR",normalized); self.assertNotIn(RECOVERY_ACCOUNT_ID.upper(),normalized)
    def test_builtin_recovery_principal(self):
        self.assertEqual(RECOVERY_ACCOUNT_USERNAME,"Administrator"); self.assertTrue(RECOVERY_ACCOUNT_ID.startswith("__recovery_"))
if __name__ == "__main__": unittest.main()
