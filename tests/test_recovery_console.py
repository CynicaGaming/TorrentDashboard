from __future__ import annotations

import unittest

from torrent_dashboard.recovery_console import (
    RECOVERY_COMMAND_MAX_CHARS,
    SAFE_TORRENT_ACTIONS,
    parse_recovery_command,
    recovery_help_text,
)


class RecoveryConsoleTests(unittest.TestCase):
    def test_command_parser_supports_quoted_arguments(self):
        self.assertEqual(parse_recovery_command('client test "desktop one"'), ["client", "test", "desktop one"])

    def test_command_parser_rejects_multiline_and_oversized_commands(self):
        with self.assertRaisesRegex(RuntimeError, "one console command"):
            parse_recovery_command("status\nhelp")
        with self.assertRaisesRegex(RuntimeError, "too long"):
            parse_recovery_command("x" * (RECOVERY_COMMAND_MAX_CHARS + 1))

    def test_torrent_console_action_allowlist_excludes_destructive_actions(self):
        self.assertEqual(SAFE_TORRENT_ACTIONS, {"start", "stop", "recheck", "reannounce"})
        self.assertNotIn("delete", SAFE_TORRENT_ACTIONS)

    def test_help_explicitly_states_console_is_not_an_os_shell(self):
        self.assertIn("not an operating-system shell", recovery_help_text())

    def test_standard_help_is_read_only_and_admin_help_includes_actions(self):
        standard = recovery_help_text(False)
        admin = recovery_help_text(True)
        self.assertIn("read-only", standard)
        self.assertIn("client list", standard)
        self.assertIn("integration list", standard)
        self.assertIn("torrent list [client-id]", standard)
        self.assertIn("jellyfin list <integration-id>", standard)
        self.assertNotIn("update apply --confirm", standard)
        self.assertIn("update apply --confirm", admin)
        self.assertIn("torrent action", admin)


if __name__ == "__main__":
    unittest.main()
