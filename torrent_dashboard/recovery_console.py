"""Restricted command grammar for the Torrent Dashboard recovery console."""
from __future__ import annotations

import re
import shlex

RECOVERY_COMMAND_MAX_CHARS = 4096
SAFE_TORRENT_ACTIONS = frozenset({"start", "stop", "recheck", "reannounce"})


def normalize_recovery_code(value):
    return re.sub(r"[-\s]", "", str(value or "")).upper()


def parse_recovery_command(value):
    raw = str(value or "").strip()
    if not raw:
        raise RuntimeError("Enter a console command")
    if len(raw) > RECOVERY_COMMAND_MAX_CHARS:
        raise RuntimeError("Console command is too long")
    if "\n" in raw or "\r" in raw:
        raise RuntimeError("Run one console command at a time")
    try:
        tokens = shlex.split(raw, posix=True)
    except ValueError as exc:
        raise RuntimeError(f"Invalid console command: {exc}") from exc
    if not tokens:
        raise RuntimeError("Enter a console command")
    return tokens


def recovery_help_text():
    return """Torrent Dashboard Recovery Console

Read-only / diagnostic:
  help
  status
  config show
  clients
  client test <client-id>
  integrations
  integration test <integration-id>
  jellyfin tasks <integration-id>
  users
  events [limit]
  update status
  update check
  update repo

Controlled actions:
  torrent action <client-id> <start|stop|recheck|reannounce> <hash|all>
  jellyfin start <integration-id> <task-id>
  jellyfin stop <integration-id> <task-id>
  update repo <owner/repository|default>
  update download
  update install [version] --confirm
  update apply --confirm

Browser-local recovery:
  frontend clear-cache
  clear
  reload

This is not an operating-system shell. Only the commands above are accepted."""
