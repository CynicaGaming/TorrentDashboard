"""Select the newest GitHub release that is actually usable by this installation."""
from __future__ import annotations

import re

from .release_provenance import asset_sha256, find_dashboard_asset, version_key

_SEMVER_RE = re.compile(r"\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?")


def select_updater_ready_release(releases, distribution: str, *, current_version: str = ""):
    """Return the newest non-draft release with a compatible ZIP and SHA-256 digest.

    GitHub returns releases newest-first. Incomplete releases are deliberately
    skipped instead of becoming a temporary auto-update outage while another
    distribution is still being uploaded.
    """
    current = str(current_version or "").strip().lstrip("vV")
    for release in releases if isinstance(releases, list) else []:
        if not isinstance(release, dict) or release.get("draft"):
            continue
        version = str(release.get("tag_name") or "").strip().lstrip("vV")
        if not _SEMVER_RE.fullmatch(version):
            continue
        if current and version_key(version) <= version_key(current):
            continue
        asset = find_dashboard_asset(release, distribution)
        if not asset:
            continue
        try:
            asset_sha256(asset)
        except Exception:
            continue
        return release
    return None


__all__ = ["select_updater_ready_release"]
