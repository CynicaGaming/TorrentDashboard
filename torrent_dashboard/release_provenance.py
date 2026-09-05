"""Release metadata parsing and installed-package provenance persistence."""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

_SEMVER_RE = re.compile(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_DASHBOARD_ASSET_RE = re.compile(r"Torrent-Dashboard-[0-9A-Za-z.+-]+\.zip")


def version_key(value: str):
    """Return the legacy sortable key used by the dashboard update flow."""
    raw = str(value or "0").strip().lstrip("vV")
    main, sep, pre = raw.partition("-")
    nums = []
    for part in main.split("."):
        match = re.match(r"^(\d+)", part)
        nums.append(int(match.group(1)) if match else 0)
    nums = (nums + [0, 0, 0, 0])[:4]
    pre_key = (1, "") if not sep else (0, pre.lower())
    return (*nums, *pre_key)


def find_dashboard_asset(release):
    """Select the Torrent Dashboard ZIP from one GitHub release payload."""
    assets = release.get("assets") or []
    candidates = [
        asset
        for asset in assets
        if _DASHBOARD_ASSET_RE.fullmatch(str(asset.get("name") or ""))
    ]
    if not candidates:
        candidates = [
            asset
            for asset in assets
            if str(asset.get("name") or "").lower().endswith(".zip")
        ]
    return candidates[0] if candidates else None


def asset_sha256(asset):
    """Normalize GitHub's finalized SHA-256 asset digest."""
    digest = str((asset or {}).get("digest") or "").strip().lower()
    if digest.startswith("sha256:"):
        digest = digest.split(":", 1)[1]
    if not _SHA256_RE.fullmatch(digest):
        raise RuntimeError("GitHub did not provide a SHA-256 digest for the release ZIP")
    return digest


def github_release_integrity(releases, limit=2):
    """Extract normalized package provenance rows from GitHub releases."""
    rows = []
    for release in releases if isinstance(releases, list) else []:
        if release.get("draft"):
            continue
        version = str(release.get("tag_name") or "").strip().lstrip("vV")
        if not _SEMVER_RE.fullmatch(version):
            continue
        asset = find_dashboard_asset(release)
        if not asset:
            continue
        try:
            digest = asset_sha256(asset)
        except Exception:
            continue
        rows.append(
            {
                "version": version,
                "sha256": digest,
                "package": str(asset.get("name") or f"Torrent-Dashboard-{version}.zip"),
                "publishedAt": str(release.get("published_at") or release.get("created_at") or ""),
                "channel": "prerelease" if release.get("prerelease") else "stable",
                "releaseUrl": str(release.get("html_url") or ""),
            }
        )
        if len(rows) >= max(1, int(limit)):
            break
    return rows


def normalize_release_integrity(rows, limit=20):
    """Validate, deduplicate, and bound persisted release-integrity rows."""
    out = []
    seen = set()
    for raw in rows if isinstance(rows, list) else []:
        if not isinstance(raw, dict):
            continue
        version = str(raw.get("version") or "").strip().lstrip("vV")
        digest = str(raw.get("sha256") or "").strip().lower()
        if not _SEMVER_RE.fullmatch(version):
            continue
        if not _SHA256_RE.fullmatch(digest) or version in seen:
            continue
        seen.add(version)
        out.append(
            {
                "version": version,
                "sha256": digest,
                "package": str(raw.get("package") or f"Torrent-Dashboard-{version}.zip"),
                "publishedAt": str(raw.get("publishedAt") or ""),
                "channel": str(raw.get("channel") or ""),
                "releaseUrl": str(raw.get("releaseUrl") or ""),
            }
        )
        if len(out) >= max(1, int(limit)):
            break
    return out


def release_info_payload(
    version,
    package,
    sha256,
    repository="",
    release_url="",
    published_at="",
    channel="",
    commit="",
):
    """Build the normalized installed release-info payload."""
    digest = str(sha256 or "").strip().lower()
    if not _SHA256_RE.fullmatch(digest):
        raise RuntimeError("Release package SHA-256 is invalid")
    return {
        "schema": 1,
        "version": str(version or "").strip().lstrip("vV"),
        "package": str(package or "").strip(),
        "sha256": digest,
        "repository": str(repository or "").strip(),
        "releaseUrl": str(release_url or "").strip(),
        "publishedAt": str(published_at or "").strip(),
        "channel": str(channel or "").strip(),
        "commit": str(commit or "").strip(),
    }


def sha256_file(path: Path):
    """Hash one file without loading it entirely into memory."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _release_history_markdown(item):
    version = str(item.get("version") or "").strip().lstrip("vV")
    title = str(item.get("title") or f"Torrent Dashboard v{version}").strip()
    summary = str(item.get("summary") or "").strip()
    lines = [f"## v{version} — {title}"]
    if summary:
        lines.extend(["", summary])
    for heading, values in (
        ("What's changed", item.get("highlights") or []),
        ("Fixes", item.get("fixes") or []),
        ("Technical notes", item.get("technical") or []),
        ("Validation", item.get("validation") or []),
        ("Known issues", item.get("known_issues") or []),
    ):
        clean = [str(value).strip() for value in values if str(value).strip()]
        if clean:
            lines.extend(["", f"### {heading}", ""])
            lines.extend([""] + [f"- {value}" for value in clean])
    return "\n".join(lines).strip() + "\n"


class ReleaseProvenance:
    """Own installed package provenance and release-integrity persistence."""

    def __init__(
        self,
        *,
        release_info_path: Path,
        integrity_cache_path: Path,
        updates_dir: Path,
        release_notes_path: Path,
        version: str,
        default_repository: str,
    ):
        self.release_info_path = Path(release_info_path)
        self.integrity_cache_path = Path(integrity_cache_path)
        self.updates_dir = Path(updates_dir)
        self.release_notes_path = Path(release_notes_path)
        self.version = str(version)
        self.default_repository = str(default_repository)

    def write_release_info(self, path, info):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = release_info_payload(
            info.get("version"),
            info.get("package"),
            info.get("sha256"),
            info.get("repository"),
            info.get("releaseUrl"),
            info.get("publishedAt"),
            info.get("channel"),
            info.get("commit"),
        )
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        tmp.replace(path)
        return payload

    def installed_release_info(self):
        try:
            raw = json.loads(self.release_info_path.read_text(encoding="utf-8"))
            info = release_info_payload(
                raw.get("version"),
                raw.get("package"),
                raw.get("sha256"),
                raw.get("repository"),
                raw.get("releaseUrl"),
                raw.get("publishedAt"),
                raw.get("channel"),
                raw.get("commit"),
            )
            if info.get("version") == self.version:
                return info
        except Exception:
            pass

        # The first build with release-info.json may have been installed by an
        # older updater. Recover provenance from the retained, already verified
        # package and persist it for subsequent reads.
        try:
            package = self.updates_dir / self.version / f"Torrent-Dashboard-{self.version}.zip"
            if package.is_file():
                info = release_info_payload(self.version, package.name, sha256_file(package))
                return self.write_release_info(self.release_info_path, info)
        except Exception:
            pass
        return {}

    def cached_release_integrity(self):
        try:
            payload = json.loads(self.integrity_cache_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or int(payload.get("schema") or 0) != 1:
                return []
            return normalize_release_integrity(payload.get("releases") or [], 20)
        except Exception:
            return []

    def write_release_integrity_cache(self, rows):
        clean = normalize_release_integrity(rows, 20)
        if not clean:
            return []
        self.integrity_cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema": 1,
            "repository": self.default_repository,
            "updatedAt": int(time.time()),
            "releases": clean,
        }
        tmp = self.integrity_cache_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        tmp.replace(self.integrity_cache_path)
        return clean

    def local_release_history(self, latest_manifest=None, limit=2):
        entries = []
        try:
            data = json.loads(self.release_notes_path.read_text(encoding="utf-8"))
            for raw in data.get("releases", []):
                if not isinstance(raw, dict):
                    continue
                version = str(raw.get("version") or "").strip().lstrip("vV")
                if not _SEMVER_RE.fullmatch(version):
                    continue
                entries.append(
                    {
                        "version": version,
                        "title": str(raw.get("title") or f"Torrent Dashboard v{version}"),
                        "summary": str(raw.get("summary") or ""),
                        "publishedAt": str(raw.get("date") or ""),
                        "channel": "prerelease" if raw.get("status") == "prerelease" else "stable",
                        "notes": _release_history_markdown(raw),
                        "source": "bundled",
                    }
                )
        except Exception:
            entries = []

        for integrity in self.cached_release_integrity():
            version = str(integrity.get("version") or "").strip().lstrip("vV")
            idx = next((i for i, item in enumerate(entries) if item.get("version") == version), None)
            if idx is None:
                continue
            digest = str(integrity.get("sha256") or "").strip().lower()
            if _SHA256_RE.fullmatch(digest):
                entries[idx] = {
                    **entries[idx],
                    "sha256": digest,
                    "package": str(integrity.get("package") or entries[idx].get("package") or ""),
                    "publishedAt": str(integrity.get("publishedAt") or entries[idx].get("publishedAt") or ""),
                    "channel": str(integrity.get("channel") or entries[idx].get("channel") or ""),
                }

        if isinstance(latest_manifest, dict) and latest_manifest.get("version"):
            version = str(latest_manifest.get("version") or "").strip().lstrip("vV")
            remote = {
                "version": version,
                "title": str(latest_manifest.get("title") or f"Torrent Dashboard v{version}"),
                "summary": "",
                "publishedAt": str(latest_manifest.get("publishedAt") or ""),
                "channel": str(latest_manifest.get("channel") or ""),
                "notes": str(latest_manifest.get("notes") or ""),
                "sha256": str((latest_manifest.get("asset") or {}).get("sha256") or ""),
                "package": str((latest_manifest.get("asset") or {}).get("name") or ""),
                "source": "github",
            }
            idx = next((i for i, item in enumerate(entries) if item.get("version") == version), None)
            if idx is None:
                entries.append(remote)
            else:
                entries[idx] = {**entries[idx], **{key: value for key, value in remote.items() if value}}
            for integrity in latest_manifest.get("releaseHistory") or []:
                if not isinstance(integrity, dict):
                    continue
                integrity_version = str(integrity.get("version") or "").strip().lstrip("vV")
                idx = next(
                    (i for i, item in enumerate(entries) if item.get("version") == integrity_version),
                    None,
                )
                if idx is None:
                    continue
                digest = str(integrity.get("sha256") or "").strip().lower()
                if _SHA256_RE.fullmatch(digest):
                    entries[idx] = {
                        **entries[idx],
                        "sha256": digest,
                        "package": str(integrity.get("package") or entries[idx].get("package") or ""),
                        "publishedAt": str(integrity.get("publishedAt") or entries[idx].get("publishedAt") or ""),
                        "channel": str(integrity.get("channel") or entries[idx].get("channel") or ""),
                    }

        installed = self.installed_release_info()
        if installed.get("version"):
            idx = next(
                (i for i, item in enumerate(entries) if item.get("version") == installed.get("version")),
                None,
            )
            if idx is not None:
                entries[idx] = {
                    **entries[idx],
                    "sha256": installed.get("sha256", ""),
                    "package": installed.get("package", ""),
                }

        try:
            entries.sort(key=lambda item: version_key(item.get("version") or "0"), reverse=True)
        except Exception:
            entries.reverse()

        seen = set()
        out = []
        for item in entries:
            version = item.get("version")
            if not version or version in seen:
                continue
            seen.add(version)
            out.append(item)
            if len(out) >= max(1, int(limit)):
                break
        return out


__all__ = [
    "ReleaseProvenance",
    "asset_sha256",
    "find_dashboard_asset",
    "github_release_integrity",
    "normalize_release_integrity",
    "release_info_payload",
    "sha256_file",
    "version_key",
]
