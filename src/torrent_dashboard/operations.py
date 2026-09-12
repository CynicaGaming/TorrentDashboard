"""Operational scheduling and retention helpers."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import time
from datetime import datetime

from .persistence import atomic_write_json

MAINTENANCE_STATE_SCHEMA = 1


class MaintenanceStateStore:
    def __init__(self, path: Path | str):
        self.path = Path(path)

    def load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or int(data.get("schema") or 0) != MAINTENANCE_STATE_SCHEMA:
                return {"schema": MAINTENANCE_STATE_SCHEMA}
            return data
        except Exception:
            return {"schema": MAINTENANCE_STATE_SCHEMA}

    def save(self, data: dict):
        payload = {"schema": MAINTENANCE_STATE_SCHEMA, **dict(data or {})}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_json(self.path, payload)
        return payload

    def update(self, **changes):
        payload = self.load()
        payload.update(changes)
        return self.save(payload)


def _minutes(hhmm: str) -> int:
    hour, minute = (int(part) for part in str(hhmm).split(":", 1))
    return hour * 60 + minute


def within_maintenance_window(now: datetime, start: str, end: str) -> bool:
    current = now.hour * 60 + now.minute
    begin = _minutes(start)
    finish = _minutes(end)
    if begin == finish:
        return True
    if begin < finish:
        return begin <= current < finish
    return current >= begin or current < finish


def scheduled_backup_due(policy: dict, state: dict, now: datetime | None = None) -> bool:
    if not bool((policy or {}).get("schedule_enabled")):
        return False
    now = now or datetime.now()
    frequency = str(policy.get("schedule_frequency") or "daily")
    hour = int(policy.get("schedule_hour") or 0)
    last = int((state or {}).get("last_backup_ts") or 0)
    previous = datetime.fromtimestamp(last) if last else None
    if frequency == "hourly":
        return not previous or (now - previous).total_seconds() >= 3600
    if now.hour != hour:
        return False
    if frequency == "weekly" and now.weekday() != int(policy.get("schedule_weekday") or 0):
        return False
    if not previous:
        return True
    if frequency == "weekly":
        return (now - previous).total_seconds() >= 6 * 86400
    return previous.date() != now.date()


def automatic_update_due(policy: dict, state: dict, now: datetime | None = None) -> bool:
    if not bool((policy or {}).get("enabled")):
        return False
    now = now or datetime.now()
    if not within_maintenance_window(now, str(policy.get("window_start") or "03:00"), str(policy.get("window_end") or "05:00")):
        return False
    return str((state or {}).get("last_auto_update_day") or "") != now.date().isoformat()


def retention_due(state: dict, now_ts: int | None = None) -> bool:
    now_ts = int(now_ts or time.time())
    return now_ts - int((state or {}).get("last_retention_ts") or 0) >= 12 * 3600


def prune_backups(app_dir: Path | str, keep: int) -> list[str]:
    directory = Path(app_dir) / "data" / "backups"
    if not directory.exists():
        return []
    keep = max(1, int(keep or 1))
    files = sorted(
        (path for path in directory.glob("*.tdbackup") if path.is_file()),
        key=lambda path: (path.stat().st_mtime, path.name),
        reverse=True,
    )
    removed = []
    for path in files[keep:]:
        path.unlink(missing_ok=True)
        removed.append(path.name)
    return removed


def prune_update_artifacts(update_dir: Path | str, max_age_days: int, *, protected_versions=()) -> list[str]:
    directory = Path(update_dir)
    if not directory.exists():
        return []
    cutoff = time.time() - max(1, int(max_age_days or 1)) * 86400
    protected = {str(item) for item in protected_versions if str(item)}
    removed = []
    for child in directory.iterdir():
        if child.name in protected:
            continue
        try:
            modified = child.stat().st_mtime
        except OSError:
            continue
        if modified >= cutoff:
            continue
        try:
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink(missing_ok=True)
            removed.append(child.name)
        except OSError:
            continue
    return sorted(removed)


def run_retention(*, app_dir: Path | str, update_dir: Path | str, history, audit, policy: dict,
                  protected_update_versions=()):
    policy = policy or {}
    history_days = max(1, int(policy.get("history_days") or 30))
    audit_days = max(7, int(policy.get("audit_days") or 90))
    backup_count = max(1, int(policy.get("backup_count") or 14))
    update_days = max(1, int(policy.get("update_days") or 14))
    history.cleanup(history_days)
    audit_removed = audit.cleanup(audit_days)
    backups_removed = prune_backups(app_dir, backup_count)
    updates_removed = prune_update_artifacts(update_dir, update_days, protected_versions=protected_update_versions)
    return {
        "history_days": history_days,
        "audit_days": audit_days,
        "backup_count": backup_count,
        "update_days": update_days,
        "audit_removed": audit_removed,
        "backups_removed": backups_removed,
        "updates_removed": updates_removed,
    }



__all__ = [
    "MaintenanceStateStore",
    "automatic_update_due",
    "prune_backups",
    "prune_update_artifacts",
    "retention_due",
    "run_retention",
    "scheduled_backup_due",
    "within_maintenance_window",
]
