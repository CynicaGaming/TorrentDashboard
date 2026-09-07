"""Atomic replacement of private application state files."""

import json
import os
from pathlib import Path
import tempfile


def atomic_write_bytes(path: Path, content: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        # mkstemp uses an exclusive, unpredictable name and owner-only POSIX mode.
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}-", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def atomic_write_json(path: Path, value) -> None:
    atomic_write_bytes(path, (json.dumps(value, indent=2) + "\n").encode("utf-8"))


__all__ = ["atomic_write_bytes", "atomic_write_json"]
