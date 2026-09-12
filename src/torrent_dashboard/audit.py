"""Dedicated local security audit log with bounded, redacted details."""
from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import threading
import time

_SENSITIVE_FRAGMENTS = (
    "password", "passwd", "secret", "token", "api_key", "apikey",
    "recovery_key", "webhook", "authorization", "cookie",
)


def _sensitive_key(key: object) -> bool:
    value = str(key or "").strip().lower().replace("-", "_")
    return any(fragment in value for fragment in _SENSITIVE_FRAGMENTS)


def sanitize_details(value, *, depth: int = 0):
    """Return a JSON-safe audit payload with secret-looking fields redacted."""
    if depth > 6:
        return "<truncated>"
    if isinstance(value, dict):
        out = {}
        for raw_key, raw_value in list(value.items())[:64]:
            key = str(raw_key)[:128]
            out[key] = "<redacted>" if _sensitive_key(key) else sanitize_details(raw_value, depth=depth + 1)
        return out
    if isinstance(value, (list, tuple)):
        return [sanitize_details(item, depth=depth + 1) for item in list(value)[:64]]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)[:2048]


class AuditStore:
    """SQLite-backed audit trail for authentication and administrative actions."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.initialize()

    @contextmanager
    def _db(self):
        with self.lock:
            db = sqlite3.connect(str(self.path), timeout=10)
            try:
                db.row_factory = sqlite3.Row
                with db:
                    yield db
            finally:
                db.close()

    def initialize(self):
        with self._db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS audit_events(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts INTEGER NOT NULL,
                actor TEXT NOT NULL DEFAULT '',
                user_id TEXT NOT NULL DEFAULT '',
                action TEXT NOT NULL,
                outcome TEXT NOT NULL,
                client_ip TEXT NOT NULL DEFAULT '',
                target TEXT NOT NULL DEFAULT '',
                details TEXT NOT NULL DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_audit_events_ts ON audit_events(ts);
            CREATE INDEX IF NOT EXISTS idx_audit_events_action ON audit_events(action, ts);
            """)

    def record(self, action: str, *, actor: str = "", user_id: str = "", outcome: str = "success",
               client_ip: str = "", target: str = "", details=None, ts: int | None = None):
        action = str(action or "").strip()[:128]
        if not action:
            raise RuntimeError("Audit action is required")
        outcome = str(outcome or "success").strip().lower()[:32]
        if outcome not in {"success", "failure", "denied", "info"}:
            outcome = "info"
        payload = json.dumps(sanitize_details(details or {}), separators=(",", ":"), sort_keys=True)
        if len(payload) > 32768:
            payload = json.dumps({"note": "audit details exceeded the storage limit"})
        with self._db() as db:
            db.execute(
                "INSERT INTO audit_events(ts,actor,user_id,action,outcome,client_ip,target,details) VALUES(?,?,?,?,?,?,?,?)",
                (int(ts or time.time()), str(actor or "")[:128], str(user_id or "")[:128], action, outcome,
                 str(client_ip or "")[:128], str(target or "")[:512], payload),
            )

    def entries(self, *, limit: int = 100, action: str = "", outcome: str = "", since: int = 0):
        limit = max(1, min(int(limit or 100), 500))
        clauses = ["ts >= ?"]
        args: list[object] = [max(0, int(since or 0))]
        if action:
            clauses.append("action = ?")
            args.append(str(action)[:128])
        if outcome:
            clauses.append("outcome = ?")
            args.append(str(outcome)[:32])
        args.append(limit)
        with self._db() as db:
            rows = db.execute(
                f"SELECT * FROM audit_events WHERE {' AND '.join(clauses)} ORDER BY id DESC LIMIT ?", args
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            try:
                item["details"] = json.loads(item.get("details") or "{}")
            except Exception:
                item["details"] = {}
            result.append(item)
        return result

    def cleanup(self, days: int) -> int:
        cutoff = int(time.time()) - max(1, int(days or 1)) * 86400
        with self._db() as db:
            cursor = db.execute("DELETE FROM audit_events WHERE ts < ?", (cutoff,))
            return max(0, int(cursor.rowcount or 0))

    def summary(self):
        day = int(time.time()) - 86400
        with self._db() as db:
            total = int(db.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0])
            recent = int(db.execute("SELECT COUNT(*) FROM audit_events WHERE ts >= ?", (day,)).fetchone()[0])
            failures = int(db.execute(
                "SELECT COUNT(*) FROM audit_events WHERE ts >= ? AND outcome IN ('failure','denied')", (day,)
            ).fetchone()[0])
            last = db.execute("SELECT ts,action,outcome FROM audit_events ORDER BY id DESC LIMIT 1").fetchone()
        return {
            "total": total,
            "last_24h": recent,
            "failures_24h": failures,
            "last_event": dict(last) if last else None,
        }


__all__ = ["AuditStore", "sanitize_details"]
