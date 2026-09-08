"""Portable backup creation, validation, import, listing, export, and restore."""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import shutil
import sqlite3
import stat
import tempfile
import time
import zipfile
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from .persistence import atomic_write_bytes

APPLICATION_ID = "torrent-dashboard"
BACKUP_SCHEMA = 1
BACKUP_EXTENSION = ".tdbackup"
MAX_BACKUP_BYTES = 512 * 1024 * 1024
MAX_BACKUP_MEMBERS = 20000
MAX_MANIFEST_BYTES = 8 * 1024 * 1024
MAX_CONFIG_BYTES = 8 * 1024 * 1024
_PUBLICATION_LOCK = threading.Lock()
BACKUP_DIR_NAME = "backups"
PRESERVED_DATA_NAMES = {BACKUP_DIR_NAME, "recovery-backups"}
EPHEMERAL_DATA_NAMES = {"updates", "update-runner", "update-status.json", "release-integrity.json", "update-restart.log"}
EXCLUDED_DATA_NAMES = PRESERVED_DATA_NAMES | EPHEMERAL_DATA_NAMES
IDENTITY_CONFIG_KEYS = {"users", "recovery"}
LEGACY_AUTH_IDENTITY_KEYS = {"username", "password_hash"}
PORTABLE_SCOPE = ["settings", "integrations", "clients"]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _version_key(value: str) -> tuple[int, ...]:
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?", str(value or ""), re.ASCII)
    if not match:
        raise RuntimeError("Backup contains an invalid application version")
    return tuple(int(part) for part in match.groups())


def backup_directory(app_dir: Path) -> Path:
    return Path(app_dir) / "data" / BACKUP_DIR_NAME


def _backup_filename(kind: str = "manual") -> str:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    prefix = "TorrentDashboard-PreRestore" if kind == "pre-restore" else "TorrentDashboard-Backup"
    return f"{prefix}-{stamp}{BACKUP_EXTENSION}"


def _safe_filename(filename: str) -> str:
    # Browsers may send a Windows basename even when the server runs on Linux.
    safe = str(filename or "").replace("\\", "/").rsplit("/", 1)[-1]
    _safe_member_name(safe)
    if not safe.lower().endswith(BACKUP_EXTENSION):
        raise RuntimeError(f"Backup files must use the {BACKUP_EXTENSION} extension")
    return safe


def _publish_backup(temporary: Path, directory: Path, filename: str) -> Path:
    """Publish only complete, verified archives; serialize same-name imports."""
    safe = _safe_filename(filename)
    stem = safe[:-len(BACKUP_EXTENSION)]
    with _PUBLICATION_LOCK:
        destination = directory / safe
        index = 1
        while destination.exists() or destination.is_symlink():
            destination = directory / f"{stem}-{index}{BACKUP_EXTENSION}"
            index += 1
        temporary.replace(destination)
    return destination


def _state_files(data_dir: Path):
    # Prune before traversal, including junctions on Windows and SQLite sidecars.
    for parent, directories, filenames in os.walk(data_dir, followlinks=False):
        parent = Path(parent)
        directories[:] = sorted(
            name for name in directories
            if not (parent == data_dir and name in EXCLUDED_DATA_NAMES)
            and not (parent / name).is_symlink()
            and not getattr(parent / name, "is_junction", lambda: False)()
        )
        for name in sorted(filenames):
            source = parent / name
            if parent == data_dir and (name in EXCLUDED_DATA_NAMES or name in {
                "torrent_desk.sqlite3-wal", "torrent_desk.sqlite3-shm", "torrent_desk.sqlite3-journal",
            }):
                continue
            if not source.is_symlink() and source.is_file():
                yield source


def _copy_sqlite_snapshot(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_db = sqlite3.connect(str(source), timeout=10)
    try:
        destination_db = sqlite3.connect(str(destination), timeout=10)
        try:
            source_db.backup(destination_db)
        finally:
            destination_db.close()
    finally:
        source_db.close()


def _payload_files(staging: Path) -> list[dict]:
    files = []
    for path in sorted((staging / "payload").rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(staging).as_posix()
        files.append({"path": rel, "size": path.stat().st_size, "sha256": _sha256(path)})
    return files


def _portable_config(config: dict) -> dict:
    """Return portable settings while excluding user and recovery identity."""
    if not isinstance(config, dict):
        raise RuntimeError("Backup configuration must be a JSON object")
    portable = json.loads(json.dumps(config))
    for key in IDENTITY_CONFIG_KEYS:
        portable.pop(key, None)
    auth = portable.get("auth")
    if isinstance(auth, dict):
        for key in LEGACY_AUTH_IDENTITY_KEYS:
            auth.pop(key, None)
    return portable


def _merge_restored_config(restored: dict, current: dict) -> dict:
    """Apply portable settings while retaining destination identity and recovery state."""
    if not isinstance(restored, dict) or not isinstance(current, dict):
        raise RuntimeError("Backup restore configuration is invalid")
    merged = json.loads(json.dumps(restored))
    current_copy = json.loads(json.dumps(current))
    for key in IDENTITY_CONFIG_KEYS:
        if key in current_copy:
            merged[key] = current_copy[key]
        else:
            merged.pop(key, None)
    had_auth = isinstance(merged.get("auth"), dict) or isinstance(current_copy.get("auth"), dict)
    auth = merged.get("auth") if isinstance(merged.get("auth"), dict) else {}
    current_auth = current_copy.get("auth") if isinstance(current_copy.get("auth"), dict) else {}
    for key in LEGACY_AUTH_IDENTITY_KEYS:
        if key in current_auth:
            auth[key] = current_auth[key]
        else:
            auth.pop(key, None)
    if had_auth:
        merged["auth"] = auth
    else:
        merged.pop("auth", None)
    return merged


def create_backup(app_dir: Path, version: str, config: dict, *, kind: str = "manual", history_lock=None) -> dict:
    """Create a portable configuration backup without users, recovery keys, or runtime data."""
    app_dir = Path(app_dir).resolve()
    directory = backup_directory(app_dir)
    lock = history_lock if history_lock is not None else nullcontext()
    with lock:
        with tempfile.TemporaryDirectory(prefix="torrent-dashboard-backup-") as tmp_name:
            staging = Path(tmp_name)
            payload = staging / "payload"
            payload.mkdir(parents=True, exist_ok=True)
            portable = _portable_config(config)
            (payload / "config.json").write_text(json.dumps(portable, indent=2) + "\n", encoding="utf-8")
            files = _payload_files(staging)
            if sum(int(item.get("size") or 0) for item in files) > MAX_BACKUP_BYTES:
                raise RuntimeError("Backup payload exceeds the 512 MB safety limit")
            manifest = {
                "schema": BACKUP_SCHEMA,
                "application": APPLICATION_ID,
                "created_at": _utc_now(),
                "source_version": str(version or "unknown"),
                "kind": str(kind or "manual"),
                "portable": True,
                "scope": PORTABLE_SCOPE,
                "contains_secrets": True,
                "files": files,
            }
            (staging / "backup-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            directory.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=directory, prefix=".creating-", suffix=".tmp", delete=False) as handle:
                temporary = Path(handle.name)
            try:
                with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
                    archive.write(staging / "backup-manifest.json", "backup-manifest.json")
                    for item in files:
                        archive.write(staging / item["path"], item["path"])
                validate_backup(temporary)
                destination = _publish_backup(temporary, directory, _backup_filename(kind))
            finally:
                temporary.unlink(missing_ok=True)
    return backup_metadata(destination)
def _safe_member_name(name: str) -> str:
    if not isinstance(name, str) or not name:
        raise RuntimeError("Backup contains an unsafe path")
    parts = name.split("/")
    for part in parts:
        if (part in ("", ".", "..") or part.endswith((".", " "))
                or any(ord(ch) < 32 or ord(ch) == 127 or ch in '\\:<>"|?*' for ch in part)
                or re.fullmatch(r"(?:CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?", part, re.I)):
            raise RuntimeError("Backup contains an unsafe or non-portable path")
    return name


def _read_manifest(archive: zipfile.ZipFile) -> dict:
    try:
        if archive.getinfo("backup-manifest.json").file_size > MAX_MANIFEST_BYTES:
            raise RuntimeError("Backup manifest is too large")
        raw = archive.read("backup-manifest.json")
        manifest = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise RuntimeError("Backup manifest is missing or invalid") from exc
    if not isinstance(manifest, dict):
        raise RuntimeError("Backup manifest must be a JSON object")
    if manifest.get("application") != APPLICATION_ID:
        raise RuntimeError("This is not a Torrent Dashboard backup")
    if type(manifest.get("schema")) is not int or manifest["schema"] != BACKUP_SCHEMA:
        raise RuntimeError("Unsupported Torrent Dashboard backup schema")
    files = manifest.get("files")
    if not isinstance(files, list) or not files or len(files) >= MAX_BACKUP_MEMBERS:
        raise RuntimeError("Backup manifest does not contain a file list")
    return manifest


def validate_backup(path: Path, *, current_version: str | None = None) -> dict:
    """Fully validate an archive, including member safety, size, and SHA-256 digests."""
    path = Path(path)
    if not path.is_file():
        raise RuntimeError("Backup file was not found")
    if path.stat().st_size > MAX_BACKUP_BYTES:
        raise RuntimeError("Backup exceeds the 512 MB safety limit")
    try:
        with zipfile.ZipFile(path) as archive:
            infos = archive.infolist()
            if len(infos) > MAX_BACKUP_MEMBERS:
                raise RuntimeError("Backup contains too many files")
            seen = set()
            folded = set()
            members = {}
            total = 0
            for info in infos:
                name = _safe_member_name(info.filename[:-1] if info.is_dir() else info.filename)
                if name.casefold() in folded:
                    raise RuntimeError("Backup contains duplicate or case-colliding file names")
                folded.add(name.casefold())
                if not info.is_dir():
                    seen.add(name)
                    members[name] = info
                if info.flag_bits & 0x1:
                    raise RuntimeError("Encrypted ZIP members are not supported")
                mode = (info.external_attr >> 16) & 0xFFFF
                if mode and stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR):
                    raise RuntimeError("Backup contains a link or special file")
                total += max(0, int(info.file_size))
                if total > MAX_BACKUP_BYTES:
                    raise RuntimeError("Backup expands beyond the 512 MB safety limit")

            folded_files = {name.casefold() for name in seen}
            for name in folded:
                for ancestor in PurePosixPath(name).parents:
                    if ancestor.as_posix() in folded_files:
                        raise RuntimeError("Backup contains conflicting file and directory paths")
            manifest = _read_manifest(archive)
            source_key = _version_key(manifest.get("source_version"))
            expected = {}
            for item in manifest["files"]:
                if not isinstance(item, dict):
                    raise RuntimeError("Backup manifest contains an invalid file entry")
                name = _safe_member_name(item.get("path"))
                if not (name == "payload/config.json" or name.startswith("payload/data/")):
                    raise RuntimeError("Backup payload contains an unsupported path")
                if name in expected:
                    raise RuntimeError("Backup manifest contains duplicate file entries")
                digest = str(item.get("sha256") or "").lower()
                if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
                    raise RuntimeError("Backup manifest contains an invalid SHA-256 digest")
                size = item.get("size")
                if type(size) is not int or size < 0:
                    raise RuntimeError("Backup manifest contains an invalid file size")
                expected[name] = (size, digest)

            if "payload/config.json" not in expected:
                raise RuntimeError("Backup does not contain config.json")
            if seen != set(expected) | {"backup-manifest.json"}:
                raise RuntimeError("Backup payload does not match its manifest")

            for name, (size, digest) in expected.items():
                if members[name].file_size != size:
                    raise RuntimeError(f"Backup file size mismatch: {name}")
                actual = hashlib.sha256()
                count = 0
                with archive.open(name) as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        count += len(chunk)
                        if count > size:
                            raise RuntimeError(f"Backup file size mismatch: {name}")
                        actual.update(chunk)
                if count != size or actual.hexdigest() != digest:
                    raise RuntimeError(f"Backup integrity check failed: {name}")

            if expected["payload/config.json"][0] > MAX_CONFIG_BYTES:
                raise RuntimeError("Backup configuration is too large")
            try:
                config = json.loads(archive.read("payload/config.json").decode("utf-8"))
            except Exception as exc:
                raise RuntimeError("Backup config.json is invalid") from exc
            if not isinstance(config, dict):
                raise RuntimeError("Backup config.json must contain a JSON object")
            if not isinstance(config.get("setup"), dict) or config["setup"].get("complete") is not True:
                raise RuntimeError("Backup does not contain a completed Torrent Dashboard configuration")
            scope = manifest.get("scope")
            if scope is not None:
                if scope != PORTABLE_SCOPE:
                    raise RuntimeError("Backup contains an unsupported portability scope")
                if any(key in config for key in IDENTITY_CONFIG_KEYS):
                    raise RuntimeError("Portable backup must not contain users or recovery keys")
                auth = config.get("auth") if isinstance(config.get("auth"), dict) else {}
                if any(key in auth for key in LEGACY_AUTH_IDENTITY_KEYS):
                    raise RuntimeError("Portable backup must not contain user credential material")

            if current_version:
                current_key = _version_key(current_version)
                if source_key > current_key:
                    raise RuntimeError(
                        f"Backup was created by Torrent Dashboard {manifest.get('source_version')}; "
                        f"update this installation to at least that version before restoring it"
                    )
            return manifest
    except zipfile.BadZipFile as exc:
        raise RuntimeError("Backup archive is not a valid ZIP file") from exc


def backup_metadata(path: Path, *, validate: bool = False) -> dict:
    path = Path(path)
    try:
        if validate:
            manifest = validate_backup(path)
        else:
            with zipfile.ZipFile(path) as archive:
                manifest = _read_manifest(archive)
        return {
            "name": path.name,
            "created_at": str(manifest.get("created_at") or ""),
            "source_version": str(manifest.get("source_version") or "unknown"),
            "kind": str(manifest.get("kind") or "manual"),
            "size": path.stat().st_size,
            "files": len(manifest.get("files") or []),
            "valid": True,
            "error": "",
        }
    except Exception as exc:
        return {
            "name": path.name,
            "created_at": "",
            "source_version": "unknown",
            "kind": "unknown",
            "size": path.stat().st_size if path.exists() else 0,
            "files": 0,
            "valid": False,
            "error": str(exc),
        }


def list_backups(app_dir: Path) -> list[dict]:
    directory = backup_directory(Path(app_dir))
    if not directory.exists():
        return []
    items = [backup_metadata(path) for path in directory.glob(f"*{BACKUP_EXTENSION}") if path.is_file()]
    return sorted(items, key=lambda item: (item.get("created_at") or "", item.get("name") or ""), reverse=True)


def backup_path(app_dir: Path, name: str) -> Path:
    directory = backup_directory(Path(app_dir)).resolve()
    candidate = (directory / Path(str(name or "")).name).resolve()
    if directory != candidate.parent or not candidate.is_file() or candidate.suffix.lower() != BACKUP_EXTENSION:
        raise RuntimeError("Backup file was not found")
    return candidate


def delete_backup(app_dir: Path, name: str) -> str:
    """Delete one local portable backup archive and return its file name."""
    supplied = str(name or "")
    safe = _safe_filename(supplied)
    if supplied != safe:
        raise RuntimeError("Backup file was not found")
    path = backup_path(app_dir, safe)
    path.unlink()
    return path.name


def import_backup(app_dir: Path, filename: str, content: bytes, *, current_version: str | None = None) -> dict:
    if not content:
        raise RuntimeError("Choose a Torrent Dashboard backup file")
    if len(content) > MAX_BACKUP_BYTES:
        raise RuntimeError("Backup exceeds the 512 MB safety limit")
    supplied = _safe_filename(filename or "backup.tdbackup")
    directory = backup_directory(Path(app_dir))
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=directory, prefix=".importing-", suffix=".tmp", delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(content)
    try:
        validate_backup(temp_path, current_version=current_version)
        destination = _publish_backup(temp_path, directory, supplied)
        return backup_metadata(destination)
    finally:
        temp_path.unlink(missing_ok=True)


def _extract_validated_backup(path: Path, destination: Path, *, current_version: str) -> dict:
    manifest = validate_backup(path, current_version=current_version)
    with zipfile.ZipFile(path) as archive:
        for item in manifest["files"]:
            name = _safe_member_name(item["path"])
            target = destination / PurePosixPath(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(name) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
    return manifest


def _apply_payload(app_dir: Path, payload: Path, current_config: dict) -> None:
    config_source = payload / "config.json"
    if not config_source.is_file():
        raise RuntimeError("Backup payload is missing config.json")
    try:
        restored = json.loads(config_source.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError("Backup payload config.json is invalid") from exc
    merged = _merge_restored_config(restored, current_config)
    atomic_write_bytes(app_dir / "config.json", (json.dumps(merged, indent=2) + "\n").encode("utf-8"))
def restore_backup(
    app_dir: Path,
    name: str,
    *,
    current_version: str,
    current_config: dict,
    history_lock=None,
    validator=None,
) -> dict:
    """Restore validated state with a safety snapshot and rollback on exceptions."""
    app_dir = Path(app_dir).resolve()
    source = backup_path(app_dir, name)
    validate_backup(source, current_version=current_version)
    lock = history_lock if history_lock is not None else nullcontext()
    with lock:
        safety = create_backup(app_dir, current_version, current_config, kind="pre-restore", history_lock=None)
        safety_path = backup_path(app_dir, safety["name"])
        with tempfile.TemporaryDirectory(prefix="torrent-dashboard-restore-") as temp_name:
            extracted = Path(temp_name)
            manifest = _extract_validated_backup(source, extracted, current_version=current_version)
            try:
                _apply_payload(app_dir, extracted / "payload", current_config)
                if validator is not None:
                    validator()
            except Exception as exc:
                rollback_dir = Path(temp_name) / "rollback"
                rollback_dir.mkdir(parents=True, exist_ok=True)
                try:
                    _extract_validated_backup(safety_path, rollback_dir, current_version=current_version)
                    _apply_payload(app_dir, rollback_dir / "payload", current_config)
                except Exception as rollback_exc:
                    raise RuntimeError(
                        f"Backup restore failed and automatic rollback also failed. "
                        f"Retain safety backup {safety_path.name} for recovery: {rollback_exc}"
                    ) from exc
                raise RuntimeError(f"Backup restore failed and the previous state was restored: {exc}") from exc
    return {
        "backup": backup_metadata(source),
        "safety_backup": safety,
        "manifest": manifest,
    }


__all__ = ["BACKUP_EXTENSION", "MAX_BACKUP_BYTES", "backup_path", "create_backup", "import_backup", "list_backups", "restore_backup", "validate_backup"]
