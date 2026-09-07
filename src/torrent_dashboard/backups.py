"""Portable backup creation, validation, import, listing, export, and restore."""
from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import stat
import tempfile
import time
import zipfile
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

APPLICATION_ID = "torrent-dashboard"
BACKUP_SCHEMA = 1
BACKUP_EXTENSION = ".tdbackup"
MAX_BACKUP_BYTES = 512 * 1024 * 1024
MAX_BACKUP_MEMBERS = 20000
BACKUP_DIR_NAME = "backups"
PRESERVED_DATA_NAMES = {BACKUP_DIR_NAME, "recovery-backups"}
EPHEMERAL_DATA_NAMES = {"updates", "update-status.json", "release-integrity.json", "update-restart.log"}
EXCLUDED_DATA_NAMES = PRESERVED_DATA_NAMES | EPHEMERAL_DATA_NAMES


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _version_key(value: str) -> tuple[int, ...]:
    base = str(value or "").strip().lstrip("vV").split("-", 1)[0].split("+", 1)[0]
    try:
        return tuple(int(part) for part in base.split("."))
    except (TypeError, ValueError):
        return ()


def backup_directory(app_dir: Path) -> Path:
    return Path(app_dir) / "data" / BACKUP_DIR_NAME


def _backup_filename(kind: str = "manual") -> str:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    prefix = "TorrentDashboard-PreRestore" if kind == "pre-restore" else "TorrentDashboard-Backup"
    return f"{prefix}-{stamp}{BACKUP_EXTENSION}"


def _unique_path(directory: Path, filename: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    safe = Path(str(filename or "")).name
    if not safe.lower().endswith(BACKUP_EXTENSION):
        safe += BACKUP_EXTENSION
    stem = safe[: -len(BACKUP_EXTENSION)]
    candidate = directory / safe
    index = 1
    while candidate.exists():
        candidate = directory / f"{stem}-{index}{BACKUP_EXTENSION}"
        index += 1
    return candidate


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


def create_backup(app_dir: Path, version: str, config: dict, *, kind: str = "manual", history_lock=None) -> dict:
    """Create a state-only portable backup and return its public metadata."""
    app_dir = Path(app_dir).resolve()
    data_dir = app_dir / "data"
    directory = backup_directory(app_dir)
    lock = history_lock if history_lock is not None else nullcontext()
    with lock:
        with tempfile.TemporaryDirectory(prefix="torrent-dashboard-backup-") as tmp_name:
            staging = Path(tmp_name)
            payload = staging / "payload"
            payload.mkdir(parents=True, exist_ok=True)
            (payload / "config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

            if data_dir.exists():
                for source in sorted(data_dir.rglob("*")):
                    rel = source.relative_to(data_dir)
                    if not rel.parts or rel.parts[0] in EXCLUDED_DATA_NAMES:
                        continue
                    if source.is_symlink():
                        continue
                    if not source.is_file():
                        continue
                    destination = payload / "data" / rel
                    if source.resolve() == (data_dir / "torrent_desk.sqlite3").resolve():
                        _copy_sqlite_snapshot(source, destination)
                    else:
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source, destination)

            files = _payload_files(staging)
            manifest = {
                "schema": BACKUP_SCHEMA,
                "application": APPLICATION_ID,
                "created_at": _utc_now(),
                "source_version": str(version or "unknown"),
                "kind": str(kind or "manual"),
                "portable": True,
                "contains_secrets": True,
                "files": files,
            }
            (staging / "backup-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

            destination = _unique_path(directory, _backup_filename(kind))
            with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
                archive.write(staging / "backup-manifest.json", "backup-manifest.json")
                for item in files:
                    archive.write(staging / item["path"], item["path"])

    return backup_metadata(destination, validate=True)


def _safe_member_name(name: str) -> str:
    value = str(name or "")
    if not value or "\\" in value or value.startswith("/"):
        raise RuntimeError("Backup contains an unsafe path")
    path = PurePosixPath(value)
    if any(part in ("", ".", "..") for part in path.parts):
        raise RuntimeError("Backup contains an unsafe path")
    return path.as_posix()


def _read_manifest(archive: zipfile.ZipFile) -> dict:
    try:
        raw = archive.read("backup-manifest.json")
        manifest = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise RuntimeError("Backup manifest is missing or invalid") from exc
    if not isinstance(manifest, dict):
        raise RuntimeError("Backup manifest must be a JSON object")
    if manifest.get("application") != APPLICATION_ID:
        raise RuntimeError("This is not a Torrent Dashboard backup")
    if int(manifest.get("schema") or 0) != BACKUP_SCHEMA:
        raise RuntimeError("Unsupported Torrent Dashboard backup schema")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
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
            total = 0
            for info in infos:
                name = _safe_member_name(info.filename.rstrip("/")) if info.filename.endswith("/") else _safe_member_name(info.filename)
                if name in seen:
                    raise RuntimeError("Backup contains duplicate file names")
                seen.add(name)
                if info.flag_bits & 0x1:
                    raise RuntimeError("Encrypted ZIP members are not supported")
                mode = (info.external_attr >> 16) & 0xFFFF
                if mode and stat.S_ISLNK(mode):
                    raise RuntimeError("Backup contains symbolic links")
                total += max(0, int(info.file_size))
                if total > MAX_BACKUP_BYTES:
                    raise RuntimeError("Backup expands beyond the 512 MB safety limit")

            manifest = _read_manifest(archive)
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
                expected[name] = (int(item.get("size") or 0), digest)

            if "payload/config.json" not in expected:
                raise RuntimeError("Backup does not contain config.json")
            payload_members = {name for name in seen if name.startswith("payload/") and not name.endswith("/")}
            if payload_members != set(expected):
                raise RuntimeError("Backup payload does not match its manifest")

            for name, (size, digest) in expected.items():
                data = archive.read(name)
                if len(data) != size:
                    raise RuntimeError(f"Backup file size mismatch: {name}")
                if hashlib.sha256(data).hexdigest() != digest:
                    raise RuntimeError(f"Backup integrity check failed: {name}")

            try:
                config = json.loads(archive.read("payload/config.json").decode("utf-8"))
            except Exception as exc:
                raise RuntimeError("Backup config.json is invalid") from exc
            if not isinstance(config, dict):
                raise RuntimeError("Backup config.json must contain a JSON object")
            if not bool(config.get("setup", {}).get("complete")):
                raise RuntimeError("Backup does not contain a completed Torrent Dashboard configuration")
            recovery = config.get("recovery") if isinstance(config.get("recovery"), dict) else {}
            if not str(recovery.get("key_hash") or ""):
                raise RuntimeError("Backup is missing the dashboard recovery key hash")

            if current_version:
                source_key = _version_key(manifest.get("source_version"))
                current_key = _version_key(current_version)
                if source_key and current_key and source_key > current_key:
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


def import_backup(app_dir: Path, filename: str, content: bytes, *, current_version: str | None = None) -> dict:
    if not content:
        raise RuntimeError("Choose a Torrent Dashboard backup file")
    if len(content) > MAX_BACKUP_BYTES:
        raise RuntimeError("Backup exceeds the 512 MB safety limit")
    supplied = Path(str(filename or "backup.tdbackup")).name
    if not supplied.lower().endswith(BACKUP_EXTENSION):
        raise RuntimeError(f"Backup files must use the {BACKUP_EXTENSION} extension")
    directory = backup_directory(Path(app_dir))
    directory.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix="torrent-dashboard-import-", suffix=BACKUP_EXTENSION, delete=False) as handle:
        temp_path = Path(handle.name)
        handle.write(content)
    try:
        validate_backup(temp_path, current_version=current_version)
        destination = _unique_path(directory, supplied)
        shutil.move(str(temp_path), destination)
        return backup_metadata(destination, validate=True)
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


def _apply_payload(app_dir: Path, payload: Path) -> None:
    config_source = payload / "config.json"
    if not config_source.is_file():
        raise RuntimeError("Backup payload is missing config.json")
    data_dir = app_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    for child in list(data_dir.iterdir()):
        if child.name in PRESERVED_DATA_NAMES:
            continue
        if child.is_dir() and not child.is_symlink():
            shutil.rmtree(child)
        else:
            child.unlink(missing_ok=True)

    restored_data = payload / "data"
    if restored_data.exists():
        for source in sorted(restored_data.rglob("*")):
            rel = source.relative_to(restored_data)
            if not rel.parts or rel.parts[0] in EXCLUDED_DATA_NAMES:
                continue
            destination = data_dir / rel
            if source.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
            elif source.is_file():
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)

    config_tmp = app_dir / "config.json.restore.tmp"
    shutil.copy2(config_source, config_tmp)
    config_tmp.replace(app_dir / "config.json")


def restore_backup(
    app_dir: Path,
    name: str,
    *,
    current_version: str,
    current_config: dict,
    history_lock=None,
) -> dict:
    """Restore a validated backup transactionally, retaining a pre-restore safety backup."""
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
                _apply_payload(app_dir, extracted / "payload")
            except Exception as exc:
                rollback_dir = Path(temp_name) / "rollback"
                rollback_dir.mkdir(parents=True, exist_ok=True)
                _extract_validated_backup(safety_path, rollback_dir, current_version=current_version)
                _apply_payload(app_dir, rollback_dir / "payload")
                raise RuntimeError(f"Backup restore failed and the previous state was restored: {exc}") from exc
    return {
        "backup": backup_metadata(source),
        "safety_backup": safety,
        "manifest": manifest,
    }
