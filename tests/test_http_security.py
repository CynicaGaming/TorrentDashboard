"""Authentication and maintenance checks at the real HTTP dispatch boundary."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from email.message import Message
import io
import json
import threading
import unittest
from unittest.mock import Mock, patch

from torrent_dashboard import dashboard
from torrent_dashboard.state_gate import StateGate


class HttpSecurityTests(unittest.TestCase):
    def setUp(self):
        self.sessions = dashboard.SessionStore()
        self.config = {"auth": {"mode": "required", "session_hours": 24}, "users": []}
        self.gate = StateGate()
        for name, value in (("SESSIONS", self.sessions), ("STATE_GATE", self.gate),
                            ("load_config", Mock(side_effect=lambda: self.config))):
            patcher = patch.object(dashboard, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def request(self, path, token=None, csrf=None, body=b"{}"):
        request = object.__new__(dashboard.Handler)
        request.path = path
        request.client_address = ("192.0.2.1", 1234)
        request.headers = Message()
        request.headers["Content-Length"] = str(len(body))
        if token:
            request.headers["Cookie"] = f"td_session={token}"
        if csrf:
            request.headers["X-CSRF-Token"] = csrf
        request.rfile = io.BytesIO(body)
        request.send_json = Mock()
        return request

    def test_old_bypass_sessions_cannot_survive_enabling_password_auth(self):
        for kind in ("disabled", "lan_bypass"):
            with self.subTest(kind=kind):
                token, _ = self.sessions.create("Guest", 24, kind)
                request = self.request("/api/me", token)
                request.do_GET()
                self.assertEqual(request.send_json.call_args.args[0], 401)
                self.assertIsNone(self.sessions.get(token))

    def test_bypass_session_is_revoked_when_its_network_is_no_longer_trusted(self):
        self.config["auth"]["mode"] = "lan_bypass"
        token, _ = self.sessions.create("LAN", 24, "lan_bypass")
        with patch.object(dashboard, "effective_trusted_cidrs", return_value=["198.51.100.0/24"]):
            request = self.request("/api/me", token)
            request.do_GET()
        self.assertEqual(request.send_json.call_args.args[0], 401)

    def test_restore_requires_authentication_admin_role_and_csrf(self):
        for group, include_token, include_csrf, expected in (
            ("administrator", False, False, 401),
            ("standard", True, True, 403),
            ("administrator", True, False, 403),
        ):
            with self.subTest(group=group, token=include_token, csrf=include_csrf):
                token, session = self.sessions.create("user", 24, "password", group=group)
                request = self.request("/api/backups/restore", token if include_token else None,
                                       session["csrf"] if include_csrf else None)
                with patch.object(dashboard, "restore_backup") as restore:
                    request.do_POST()
                    restore.assert_not_called()
                self.assertEqual(request.send_json.call_args.args[0], expected)

    def test_queued_request_authenticates_after_restore_invalidates_sessions(self):
        token, session = self.sessions.create("admin", 24, "password")
        request = self.request("/api/settings", token, session["csrf"])
        started = threading.Event()
        def send():
            started.set()
            request.do_POST()
        with ThreadPoolExecutor(max_workers=1) as pool:
            with self.gate.maintenance():
                future = pool.submit(send)
                self.assertTrue(started.wait(2))
                self.sessions.clear()
                request.send_json.assert_not_called()
            future.result(timeout=2)
        self.assertEqual(request.send_json.call_args.args[0], 401)

    def test_recovery_console_endpoint_is_removed(self):
        token, session = self.sessions.create("admin", 24, "password", group="administrator")
        request = self.request("/api/recovery/command", token, session["csrf"])
        request.do_POST()
        self.assertEqual(request.send_json.call_args.args[0], 404)
        self.assertFalse(hasattr(dashboard, "recovery_console_execute"))


    def test_restore_cannot_overlap_a_launched_updater(self):
        token, session = self.sessions.create("admin", 24, "password")
        request = self.request("/api/backups/restore", token, session["csrf"])
        with patch.object(dashboard, "update_state", return_value={"state": "installing"}), \
                patch.object(dashboard, "restore_backup") as restore:
            request.do_POST()
            restore.assert_not_called()
        self.assertEqual(request.send_json.call_args.args[0], 400)
        self.assertIn("update", request.send_json.call_args.args[1]["error"])

    def test_restore_clears_sessions_even_if_its_audit_event_fails(self):
        token, session = self.sessions.create("admin", 24, "password")
        request = self.request("/api/backups/restore", token, session["csrf"])
        fresh = {"fresh": "snapshot"}
        config_store = Mock()
        config_store.exclusive.side_effect = lambda: nullcontext(fresh)
        history = Mock()
        history.event.side_effect = OSError("audit storage unavailable")
        result = {"backup": {"name": "backup.tdbackup"}, "safety_backup": {"name": "safety.tdbackup"}}
        with patch.object(dashboard, "CONFIG_STORE", config_store), \
                patch.object(dashboard, "HISTORY", history), \
                patch.object(dashboard, "update_state", return_value={"state": "idle"}), \
                patch.object(dashboard, "restore_backup", return_value=result) as restore, \
                self.assertLogs("torrent_dashboard.dashboard", level="ERROR"):
            request.do_POST()
        self.assertIs(restore.call_args.kwargs["current_config"], fresh)
        self.assertIsNone(self.sessions.get(token))
        self.assertEqual(request.send_json.call_args.args[0], 200)
        self.assertTrue(request.send_json.call_args.args[1]["reauthenticate"])
        history.reset_tracking.assert_called_once()

    def test_admin_password_reset_revokes_other_user_sessions(self):
        self.config["users"] = [
            {"id": "admin", "username": "admin", "group": "administrator", "password_hash": "fixture"},
            {"id": "target", "username": "target", "group": "standard", "password_hash": "fixture"},
        ]
        token, session = self.sessions.create("admin", 24, "password", user_id="admin")
        other, _ = self.sessions.create("target", 24, "password", user_id="target", group="standard")
        body = json.dumps({"id": "target", "username": "target", "password": "test-only-new-password"}).encode()
        request = self.request("/api/users", token, session["csrf"], body)
        with patch.object(dashboard, "mutate_config", side_effect=lambda transform: transform(self.config)), \
                patch.object(dashboard, "HISTORY", Mock()):
            request.do_POST()
        self.assertEqual(request.send_json.call_args.args[0], 200)
        self.assertIsNone(self.sessions.get(other))
        self.assertIsNotNone(self.sessions.get(token))
