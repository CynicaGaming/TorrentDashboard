"""Normalization and update helpers for backup, maintenance, and retention policy."""
from __future__ import annotations

import json
import re

BACKUP_FREQUENCIES = {"hourly", "daily", "weekly"}

DEFAULT_BACKUPS = {
    "encrypt": False,
    "password": "",
    "schedule_enabled": False,
    "schedule_frequency": "daily",
    "schedule_hour": 3,
    "schedule_weekday": 0,
}

DEFAULT_MAINTENANCE = {
    "auto_update": {
        "enabled": False,
        "window_start": "03:00",
        "window_end": "05:00",
        "pre_backup": True,
    },
    "retention": {
        "history_days": 30,
        "audit_days": 90,
        "backup_count": 14,
        "update_days": 14,
    },
}


def _bounded_int(value, default, minimum, maximum):
    try:
        result = int(value)
    except (TypeError, ValueError):
        result = int(default)
    return max(minimum, min(maximum, result))


def normalize_hhmm(value: str, default: str) -> str:
    value = str(value or "").strip()
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value):
        return default
    return value


def normalize_operations_config(config: dict) -> dict:
    """Normalize operations policy in-place and return the config object."""
    backups = config.setdefault("backups", {})
    if not isinstance(backups, dict):
        backups = config["backups"] = {}
    for key, value in DEFAULT_BACKUPS.items():
        backups.setdefault(key, value)
    backups["encrypt"] = bool(backups.get("encrypt", False))
    backups["password"] = str(backups.get("password") or "")[:4096]
    backups["schedule_enabled"] = bool(backups.get("schedule_enabled", False))
    frequency = str(backups.get("schedule_frequency") or "daily").strip().lower()
    backups["schedule_frequency"] = frequency if frequency in BACKUP_FREQUENCIES else "daily"
    backups["schedule_hour"] = _bounded_int(backups.get("schedule_hour"), 3, 0, 23)
    backups["schedule_weekday"] = _bounded_int(backups.get("schedule_weekday"), 0, 0, 6)
    if backups["encrypt"] and backups["password"] and len(backups["password"]) < 12:
        # Existing invalid secrets should never make the application unbootable.
        backups["encrypt"] = False

    maintenance = config.setdefault("maintenance", {})
    if not isinstance(maintenance, dict):
        maintenance = config["maintenance"] = {}
    auto = maintenance.setdefault("auto_update", {})
    if not isinstance(auto, dict):
        auto = maintenance["auto_update"] = {}
    defaults = DEFAULT_MAINTENANCE["auto_update"]
    auto["enabled"] = bool(auto.get("enabled", defaults["enabled"]))
    auto["window_start"] = normalize_hhmm(auto.get("window_start"), defaults["window_start"])
    auto["window_end"] = normalize_hhmm(auto.get("window_end"), defaults["window_end"])
    auto["pre_backup"] = bool(auto.get("pre_backup", defaults["pre_backup"]))

    retention = maintenance.setdefault("retention", {})
    if not isinstance(retention, dict):
        retention = maintenance["retention"] = {}
    retention_defaults = DEFAULT_MAINTENANCE["retention"]
    legacy_history = (config.get("dashboard") or {}).get("history_retention_days", retention_defaults["history_days"])
    retention["history_days"] = _bounded_int(retention.get("history_days", legacy_history), legacy_history, 1, 3650)
    retention["audit_days"] = _bounded_int(retention.get("audit_days"), retention_defaults["audit_days"], 7, 3650)
    retention["backup_count"] = _bounded_int(retention.get("backup_count"), retention_defaults["backup_count"], 1, 365)
    retention["update_days"] = _bounded_int(retention.get("update_days"), retention_defaults["update_days"], 1, 365)
    config.setdefault("dashboard", {})["history_retention_days"] = retention["history_days"]
    return config


def public_operations_config(config: dict) -> dict:
    """Return browser-safe backup/maintenance settings."""
    clean = json.loads(json.dumps(config))
    normalize_operations_config(clean)
    backups = clean.setdefault("backups", {})
    configured = bool(backups.get("password"))
    backups["password_configured"] = configured
    backups["password"] = "<configured>" if configured else ""
    return clean


def apply_operations_update(config: dict, data: dict) -> dict:
    """Apply browser-submitted backup/maintenance settings while preserving masked secrets."""
    out = json.loads(json.dumps(config))
    normalize_operations_config(out)

    supplied_backups = data.get("backups") if isinstance(data.get("backups"), dict) else None
    if supplied_backups is not None:
        backups = out["backups"]
        for key in ("encrypt", "schedule_enabled"):
            if key in supplied_backups:
                backups[key] = bool(supplied_backups[key])
        if "schedule_frequency" in supplied_backups:
            value = str(supplied_backups.get("schedule_frequency") or "").strip().lower()
            if value not in BACKUP_FREQUENCIES:
                raise RuntimeError("Invalid backup schedule frequency")
            backups["schedule_frequency"] = value
        if "schedule_hour" in supplied_backups:
            backups["schedule_hour"] = _bounded_int(supplied_backups.get("schedule_hour"), 3, 0, 23)
        if "schedule_weekday" in supplied_backups:
            backups["schedule_weekday"] = _bounded_int(supplied_backups.get("schedule_weekday"), 0, 0, 6)
        if "password" in supplied_backups:
            password = str(supplied_backups.get("password") or "")
            if password not in ("", "<configured>"):
                if len(password) < 12:
                    raise RuntimeError("Backup encryption password must contain at least 12 characters")
                backups["password"] = password[:4096]
        if supplied_backups.get("clear_password"):
            backups["password"] = ""
            backups["encrypt"] = False
        if backups.get("encrypt") and not backups.get("password"):
            raise RuntimeError("Set a backup encryption password before enabling backup encryption")

    supplied_maintenance = data.get("maintenance") if isinstance(data.get("maintenance"), dict) else None
    if supplied_maintenance is not None:
        auto_data = supplied_maintenance.get("auto_update")
        if isinstance(auto_data, dict):
            auto = out["maintenance"]["auto_update"]
            if "enabled" in auto_data:
                auto["enabled"] = bool(auto_data["enabled"])
            if "window_start" in auto_data:
                value = str(auto_data.get("window_start") or "").strip()
                if normalize_hhmm(value, "") != value:
                    raise RuntimeError("Automatic update window start must use HH:MM")
                auto["window_start"] = value
            if "window_end" in auto_data:
                value = str(auto_data.get("window_end") or "").strip()
                if normalize_hhmm(value, "") != value:
                    raise RuntimeError("Automatic update window end must use HH:MM")
                auto["window_end"] = value
            if "pre_backup" in auto_data:
                auto["pre_backup"] = bool(auto_data["pre_backup"])

        retention_data = supplied_maintenance.get("retention")
        if isinstance(retention_data, dict):
            retention = out["maintenance"]["retention"]
            bounds = {
                "history_days": (1, 3650),
                "audit_days": (7, 3650),
                "backup_count": (1, 365),
                "update_days": (1, 365),
            }
            for key, (minimum, maximum) in bounds.items():
                if key in retention_data:
                    retention[key] = _bounded_int(retention_data[key], retention[key], minimum, maximum)
            out.setdefault("dashboard", {})["history_retention_days"] = retention["history_days"]

    return normalize_operations_config(out)


__all__ = [
    "BACKUP_FREQUENCIES",
    "DEFAULT_BACKUPS",
    "DEFAULT_MAINTENANCE",
    "apply_operations_update",
    "normalize_hhmm",
    "normalize_operations_config",
    "public_operations_config",
]
