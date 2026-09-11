import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from torrent_dashboard import recovery_tool as rt
from torrent_dashboard.recovery import generate_dashboard_recovery_key, recovery_key_record


class LocalRecoveryToolTests(unittest.TestCase):
    def test_authenticates_only_setup_recovery_key(self):
        key = generate_dashboard_recovery_key()
        cfg = {"recovery": recovery_key_record(key)}
        self.assertTrue(rt.authenticate_key(cfg, key))
        wrong = key[:-1] + ("A" if key[-1] != "A" else "B")
        self.assertFalse(rt.authenticate_key(cfg, wrong))

    def test_missing_recovery_key_is_not_regenerated(self):
        with self.assertRaisesRegex(RuntimeError, "no setup-generated recovery key"):
            rt.authenticate_key({"recovery": {}}, "TDRK-TEST")

    def test_repository_change_is_backed_up_and_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.json"
            backups = root / "backups"
            config.write_text(json.dumps({
                "recovery": {"key_hash": "x"},
                "updates": {"repository": "CynicaGaming/TorrentDashboard"},
            }), encoding="utf-8")
            with mock.patch.object(rt, "CONFIG_PATH", config), mock.patch.object(rt, "BACKUP_DIR", backups):
                cfg = rt.load_config(config)
                rt.set_repository(cfg, "example/project")
                self.assertEqual(json.loads(config.read_text())["updates"]["repository"], "example/project")
                self.assertEqual(len(list(backups.glob("config-*.json"))), 1)

    def test_restore_refuses_backup_without_recovery_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = root / "config.json"
            backups = root / "backups"
            backups.mkdir()
            config.write_text(json.dumps({"recovery": {"key_hash": "current"}}), encoding="utf-8")
            (backups / "config-old.json").write_text(json.dumps({"recovery": {}}), encoding="utf-8")
            with mock.patch.object(rt, "CONFIG_PATH", config), mock.patch.object(rt, "BACKUP_DIR", backups):
                with self.assertRaisesRegex(RuntimeError, "without a recovery key"):
                    rt.restore_config("config-old.json")

    def test_local_tool_contains_no_listening_server_implementation(self):
        text = Path(rt.__file__).read_text(encoding="utf-8")
        for forbidden in ("BaseHTTPRequestHandler", "ThreadingHTTPServer", "socketserver", "http.server"):
            self.assertNotIn(forbidden, text)

    def test_recovery_command_parser_supports_quoted_identifiers(self):
        self.assertEqual(rt.parse_command('client test "desktop one"'), ["client", "test", "desktop one"])
        with self.assertRaisesRegex(RuntimeError, "one recovery command"):
            rt.parse_command("status\nhelp")

    def test_local_help_contains_migrated_console_operations(self):
        with mock.patch("builtins.print") as output:
            rt.print_help()
        rendered = "\n".join(str(call.args[0]) for call in output.call_args_list if call.args)
        for command in ("client list", "integration list", "torrent list", "jellyfin list", "users", "events"):
            self.assertIn(command, rendered)
        self.assertIn("does not expose", rendered)


if __name__ == "__main__":
    unittest.main()
