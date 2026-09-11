"""Verified update staging used by the local recovery command surface."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path


READY_STATE = "readyToInstall"


def _version_key(updater, value: str):
    key = updater.version_key(str(value or ""))
    if key is None:
        raise RuntimeError(f"Invalid Torrent Dashboard version: {value}")
    return key


def _asset_digest(asset: dict) -> str:
    digest = str(asset.get("digest") or "").strip().lower()
    if not digest.startswith("sha256:") or not re.fullmatch(r"sha256:[0-9a-f]{64}", digest):
        raise RuntimeError("GitHub did not provide a valid SHA-256 digest for the release asset")
    return digest.partition(":")[2]


def _download_url(asset: dict) -> str:
    url = str(asset.get("browser_download_url") or "").strip()
    if not url.startswith("https://github.com/"):
        raise RuntimeError("Release asset has an invalid download URL")
    return url


def _status_path(target: Path) -> Path:
    return Path(target) / "data" / "update-status.json"


def _updates_dir(target: Path) -> Path:
    return Path(target) / "data" / "updates"


def _write_status(target: Path, payload: dict) -> dict:
    path = _status_path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def stage_latest_update(target: Path, repository: str, updater, *, force: bool = False) -> dict:
    """Download, verify, extract, and retain the newest matching release without installing it."""
    target = Path(target).resolve()
    repository = str(repository or "").strip()
    distribution = updater.installation_distribution(target)
    installed = updater.current_version(target)
    version, release, asset = updater.newest_release(repository, distribution)

    installed_key = updater.version_key(installed)
    latest_key = _version_key(updater, version)
    if not force and installed_key is not None and latest_key <= installed_key:
        return _write_status(
            target,
            {
                "state": "upToDate",
                "currentVersion": installed,
                "version": version,
                "distribution": distribution,
                "repository": repository,
            },
        )

    expected_digest = _asset_digest(asset)
    download_url = _download_url(asset)
    stage = _updates_dir(target) / version
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True, exist_ok=True)

    package_name = str(asset.get("name") or updater.release_asset_name(version, distribution))
    package = stage / Path(package_name).name
    try:
        actual_digest = updater.download_file(download_url, package).lower()
        if actual_digest != expected_digest:
            raise RuntimeError(
                f"Release SHA-256 verification failed (expected {expected_digest}, got {actual_digest})"
            )
        source = updater.extract_release(package, stage / "extracted")
        updater.validate_staged_source(source, version, distribution)
        updater.write_staged_release_info(source, version, asset, actual_digest, repository, release)
        payload = {
            "state": READY_STATE,
            "version": version,
            "distribution": distribution,
            "repository": repository,
            "package": str(package),
            "source": str(source),
            "sha256": actual_digest,
            "bytes": package.stat().st_size,
            "releaseUrl": str(release.get("html_url") or ""),
            "publishedAt": str(release.get("published_at") or release.get("created_at") or ""),
            "channel": "prerelease" if release.get("prerelease") else "stable",
        }
        return _write_status(target, payload)
    except Exception as exc:
        _write_status(
            target,
            {
                "state": "failed",
                "version": version,
                "distribution": distribution,
                "repository": repository,
                "error": str(exc),
            },
        )
        raise


def read_staged_update(target: Path, updater, requested_version: str | None = None) -> dict:
    """Load and revalidate the retained staged release before handing it to the updater."""
    target = Path(target).resolve()
    path = _status_path(target)
    if not path.is_file():
        raise RuntimeError("No verified update is ready to install")
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Update status is unreadable: {exc}") from exc
    if not isinstance(state, dict) or state.get("state") != READY_STATE:
        raise RuntimeError("No verified update is ready to install")

    version = str(state.get("version") or "").strip()
    _version_key(updater, version)
    if requested_version and str(requested_version).strip() != version:
        raise RuntimeError("The staged update version changed; run update status or download again")

    installed = updater.current_version(target)
    installed_key = updater.version_key(installed)
    if installed_key is not None and _version_key(updater, version) <= installed_key:
        raise RuntimeError("The staged update is not newer than the installed version")

    source = Path(str(state.get("source") or "")).resolve()
    updates_root = _updates_dir(target).resolve()
    if source == updates_root or updates_root not in source.parents or not source.is_dir():
        raise RuntimeError("The staged update source is missing or outside the managed update directory")
    distribution = updater.installation_distribution(target)
    updater.validate_staged_source(source, version, distribution)

    digest = str(state.get("sha256") or "").lower()
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise RuntimeError("The staged update does not have a valid verified SHA-256")
    package = Path(str(state.get("package") or "")).resolve()
    if package == updates_root or updates_root not in package.parents or not package.is_file():
        raise RuntimeError("The staged update package is missing")

    actual = hashlib.sha256()
    with package.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            actual.update(chunk)
    if actual.hexdigest() != digest:
        raise RuntimeError("The retained staged update package failed its SHA-256 recheck")

    return {**state, "source": str(source), "package": str(package), "distribution": distribution}


__all__ = ["READY_STATE", "read_staged_update", "stage_latest_update"]
