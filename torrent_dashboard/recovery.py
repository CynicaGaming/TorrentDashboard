"""Dashboard-wide recovery-key generation and verification."""
from __future__ import annotations

import base64
import secrets
import time

from .users import hash_password, verify_password

RECOVERY_ACCOUNT_ID = "__recovery_administrator__"
RECOVERY_ACCOUNT_USERNAME = "Administrator"
RECOVERY_KEY_PREFIX = "TDRK"
RECOVERY_KEY_BYTES = 32

def normalize_dashboard_recovery_key(value: str) -> str:
    raw = str(value or "").strip().upper()
    return "".join(ch for ch in raw if ch not in "- \t\r\n")

def generate_dashboard_recovery_key() -> str:
    secret = base64.b32encode(secrets.token_bytes(RECOVERY_KEY_BYTES)).decode("ascii").rstrip("=")
    grouped = "-".join(secret[index:index + 4] for index in range(0, len(secret), 4))
    return f"{RECOVERY_KEY_PREFIX}-{grouped}"

def recovery_key_record(value: str) -> dict:
    normalized = normalize_dashboard_recovery_key(value)
    if not normalized.startswith(RECOVERY_KEY_PREFIX) or len(normalized) < 40:
        raise RuntimeError("Invalid dashboard recovery key")
    return {"key_hash": hash_password(normalized), "created_at": int(time.time()), "last4": normalized[-4:]}

def verify_dashboard_recovery_key(value: str, encoded: str) -> bool:
    normalized = normalize_dashboard_recovery_key(value)
    if not normalized.startswith(RECOVERY_KEY_PREFIX) or len(normalized) < 40:
        return False
    return verify_password(normalized, str(encoded or ""))

__all__ = [
    "RECOVERY_ACCOUNT_ID", "RECOVERY_ACCOUNT_USERNAME", "RECOVERY_KEY_BYTES", "RECOVERY_KEY_PREFIX",
    "generate_dashboard_recovery_key", "normalize_dashboard_recovery_key", "recovery_key_record",
    "verify_dashboard_recovery_key",
]
