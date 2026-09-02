"""Thread-safe coordination for configuration reads and mutations."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any


class ConfigStore:
    """Serialize configuration reads and transactional mutations within the process.

    The important operation is ``mutate``: it acquires the lock before loading the
    current configuration, applies the caller's transformation to that fresh
    snapshot, saves the transformed configuration, and only then releases the lock.
    This prevents two request threads from independently loading the same snapshot
    and later overwriting each other's changes.
    """

    def __init__(self, loader: Callable[[], dict], saver: Callable[[dict], None]):
        self._loader = loader
        self._saver = saver
        self._lock = threading.RLock()

    def load(self) -> dict:
        with self._lock:
            return self._loader()

    def save(self, cfg: dict) -> dict:
        """Serialize a direct save for compatibility with non-request call sites.

        Request handlers should prefer ``mutate`` because a direct save cannot
        reconstruct changes made from a stale snapshot.
        """
        with self._lock:
            self._saver(cfg)
            return cfg

    def mutate(self, transform: Callable[[dict], tuple[dict, Any]]) -> tuple[dict, Any]:
        """Apply one read/modify/write transaction to the latest configuration."""
        with self._lock:
            current = self._loader()
            outcome = transform(current)
            if not isinstance(outcome, tuple) or len(outcome) != 2:
                raise TypeError("Configuration transform must return (updated_config, result)")
            updated, result = outcome
            if not isinstance(updated, dict):
                raise TypeError("Configuration transform must return a dict configuration")
            self._saver(updated)
            return updated, result


__all__ = ["ConfigStore"]
