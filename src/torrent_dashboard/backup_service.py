"""Managed portable-backup policy including authenticated encryption."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import time
import uuid

from . import backups as plain
from .backup_crypto import decrypt_file, encrypt_file, is_encrypted_backup
from .persistence import atomic_write_json

BACKUP_EXTENSION = plain.BACKUP_EXTENSION
MAX_BACKUP_BYTES = plain.MAX_BACKUP_BYTES
MAX_ENCRYPTED_BACKUP_BYTES = MAX_BACKUP_BYTES + 4096


def configured_backup_password(config: dict) -> str:
    backups = config.get("backups") if isinstance(config.get("backups"), dict) else {}
    if not backups.get("encrypt"):
        return ""
    return str(backups.get("password") or "")


def _portable_config(config: dict) -> dict:
    """Exclude the local encryption credential from the portable payload."""
    clean = json.loads(json.dumps(config))
    clean.setdefault("backups", {})["password"] = ""
    return clean


def _backup_directory(app_dir: Path | str) -> Path:
    directory = Path(app_dir) / "data" / "backups"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _safe_name(filename: str) -> str:
    name = Path(str(filename or "backup.tdbackup").replace("\\", "/")).name
    if not name.lower().endswith(BACKUP_EXTENSION):
        raise RuntimeError(f"Backup files must use the {BACKUP_EXTENSION} extension")
    if name in ("", ".", "..") or any(ch in name for ch in '<>:"|?*'):
        raise RuntimeError("Backup file name is invalid")
    return name


def _unique_destination(directory: Path, filename: str) -> Path:
    safe = _safe_name(filename)
    stem = safe[:-len(BACKUP_EXTENSION)]
    destination = directory / safe
    index = 1
    while destination.exists() or destination.is_symlink():
        destination = directory / f"{stem}-{index}{BACKUP_EXTENSION}"
        index += 1
    return destination


def _plain_temp(path: Path, password: str):
    """Context helper yielding a validated plaintext archive path."""
    class _Context:
        def __enter__(self):
            if not is_encrypted_backup(path):
                self.tempdir = None
                return path
            if not password:
                raise RuntimeError("This backup is encrypted. Configure its backup password first")
            self.tempdir = tempfile.TemporaryDirectory(prefix="torrent-dashboard-decrypt-")
            target = Path(self.tempdir.name) / "backup.tdbackup"
            decrypt_file(path, target, password)
            return target

        def __exit__(self, exc_type, exc, tb):
            if self.tempdir is not None:
                self.tempdir.cleanup()
    return _Context()


def backup_metadata(path: Path, *, password: str = "", validate: bool = False) -> dict:
    path = Path(path)
    encrypted = is_encrypted_backup(path)
    if not encrypted:
        item = plain.backup_metadata(path, validate=validate)
        item["encrypted"] = False
        return item
    fallback = {
        "name": path.name,
        "size": path.stat().st_size,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(path.stat().st_mtime)),
        "source_version": "",
        "kind": "encrypted",
        "valid": None,
        "encrypted": True,
    }
    if not password:
        fallback["locked"] = True
        return fallback
    try:
        with _plain_temp(path, password) as decrypted:
            item = plain.backup_metadata(decrypted, validate=validate)
        item.update({"name": path.name, "size": path.stat().st_size, "encrypted": True, "locked": False})
        return item
    except Exception as exc:
        fallback.update({"valid": False, "locked": True, "error": str(exc)})
        return fallback


def list_backups(app_dir: Path | str, *, password: str = "") -> list[dict]:
    directory = _backup_directory(app_dir)
    items = [backup_metadata(path, password=password) for path in directory.glob(f"*{BACKUP_EXTENSION}") if path.is_file()]
    return sorted(items, key=lambda item: (item.get("created_at") or "", item.get("name") or ""), reverse=True)


def _encrypt_in_place(path: Path, password: str, version: str) -> dict:
    temporary = path.with_name(f".encrypting-{uuid.uuid4().hex}.tmp")
    with tempfile.TemporaryDirectory(prefix="torrent-dashboard-encryption-verify-") as temp_name:
        verify = Path(temp_name) / "verified.tdbackup"
        try:
            encrypt_file(path, temporary, password)
            decrypt_file(temporary, verify, password)
            plain.validate_backup(verify, current_version=version)
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
    return backup_metadata(path, password=password, validate=True)


def create_backup(app_dir: Path | str, version: str, config: dict, *, kind: str = "manual", history_lock=None,
                  password: str = "") -> dict:
    """Create a portable backup, encrypting before publication when a password is supplied."""
    app_dir = Path(app_dir).resolve()
    directory = _backup_directory(app_dir)
    with tempfile.TemporaryDirectory(prefix="torrent-dashboard-managed-backup-") as temp_name:
        staging_root = Path(temp_name) / "app"
        item = plain.create_backup(staging_root, version, _portable_config(config), kind=kind, history_lock=history_lock)
        source = plain.backup_path(staging_root, item["name"])
        destination = _unique_destination(directory, source.name)
        temporary = directory / f".creating-{uuid.uuid4().hex}.tmp"
        try:
            if password:
                encrypt_file(source, temporary, password)
                verify_path = Path(temp_name) / "verified.tdbackup"
                decrypt_file(temporary, verify_path, password)
                plain.validate_backup(verify_path, current_version=version)
            else:
                shutil.copyfile(source, temporary)
                plain.validate_backup(temporary, current_version=version)
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
    return backup_metadata(destination, password=password, validate=True)


def import_backup(app_dir: Path | str, filename: str, content: bytes, *, current_version: str | None = None,
                  source_password: str = "", storage_password: str = "") -> dict:
    """Validate an imported backup and normalize it to the local encryption policy."""
    if not content:
        raise RuntimeError("Choose a Torrent Dashboard backup file")
    if len(content) > MAX_ENCRYPTED_BACKUP_BYTES:
        raise RuntimeError("Backup exceeds the 512 MB safety limit")
    directory = _backup_directory(app_dir)
    supplied = _safe_name(filename)
    with tempfile.TemporaryDirectory(prefix="torrent-dashboard-import-") as temp_name:
        temp_dir = Path(temp_name)
        incoming = temp_dir / "incoming.tdbackup"
        incoming.write_bytes(content)
        encrypted = is_encrypted_backup(incoming)
        if encrypted:
            if not source_password:
                raise RuntimeError("This backup is encrypted. Configure the matching backup password before importing it")
            plain_path = temp_dir / "decrypted.tdbackup"
            decrypt_file(incoming, plain_path, source_password)
        else:
            plain_path = incoming
        plain.validate_backup(plain_path, current_version=current_version)
        destination = _unique_destination(directory, supplied)
        temporary = directory / f".importing-{uuid.uuid4().hex}.tmp"
        try:
            if storage_password:
                encrypt_file(plain_path, temporary, storage_password)
                verify_path = temp_dir / "verified.tdbackup"
                decrypt_file(temporary, verify_path, storage_password)
                plain.validate_backup(verify_path, current_version=current_version)
            else:
                shutil.copyfile(plain_path, temporary)
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
    return backup_metadata(destination, password=storage_password, validate=True)


def _restore_local_backup_policy(app_dir: Path, current_config: dict) -> None:
    """Keep the destination installation's encryption secret and enablement state."""
    config_path = app_dir / "config.json"
    try:
        restored = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return
    current_backups = current_config.get("backups") if isinstance(current_config.get("backups"), dict) else {}
    restored_backups = restored.setdefault("backups", {})
    restored_backups["password"] = str(current_backups.get("password") or "")
    restored_backups["encrypt"] = bool(current_backups.get("encrypt", False) and restored_backups["password"])
    atomic_write_json(config_path, restored)


def restore_backup(app_dir: Path | str, name: str, *, current_version: str, current_config: dict,
                   validator=None, history_lock=None, password: str = "") -> dict:
    """Restore a local backup while keeping the destination encryption credential local."""
    app_dir = Path(app_dir).resolve()
    source = plain.backup_path(app_dir, name)
    directory = _backup_directory(app_dir)
    before = {path.resolve() for path in directory.glob(f"*{BACKUP_EXTENSION}") if path.is_file()}
    local_config = _portable_config(current_config)
    temporary_name = ""
    temporary_path = None
    restore_name = source.name
    if is_encrypted_backup(source):
        if not password:
            raise RuntimeError("This backup is encrypted. Configure the matching backup password before restoring it")
        temporary_name = f"restore-{uuid.uuid4().hex}{BACKUP_EXTENSION}"
        temporary_path = directory / temporary_name
        decrypt_file(source, temporary_path, password)
        plain.validate_backup(temporary_path, current_version=current_version)
        restore_name = temporary_name
    try:
        result = plain.restore_backup(
            app_dir, restore_name, current_version=current_version, current_config=local_config,
            validator=validator, history_lock=history_lock,
        )
        _restore_local_backup_policy(app_dir, current_config)
        if isinstance(result.get("backup"), dict):
            result["backup"]["name"] = source.name
            result["backup"]["encrypted"] = is_encrypted_backup(source)
        return result
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        if password:
            # plain.restore_backup needs its safety ZIP during rollback. Encrypt
            # any new pre-restore safety archive only after that transaction is finished.
            for candidate in directory.glob(f"*{BACKUP_EXTENSION}"):
                try:
                    resolved = candidate.resolve()
                    if resolved in before or not candidate.is_file() or is_encrypted_backup(candidate):
                        continue
                    metadata = plain.backup_metadata(candidate, validate=False)
                    if metadata.get("kind") == "pre-restore":
                        _encrypt_in_place(candidate, password, current_version)
                except Exception:
                    # Never destroy the only safety copy if post-restore encryption fails.
                    continue


def delete_backup(app_dir: Path | str, name: str):
    return plain.delete_backup(Path(app_dir), name)


def backup_path(app_dir: Path | str, name: str):
    return plain.backup_path(Path(app_dir), name)


__all__ = [
    "BACKUP_EXTENSION",
    "MAX_BACKUP_BYTES",
    "MAX_ENCRYPTED_BACKUP_BYTES",
    "backup_metadata",
    "backup_path",
    "configured_backup_password",
    "create_backup",
    "delete_backup",
    "import_backup",
    "list_backups",
    "restore_backup",
]
