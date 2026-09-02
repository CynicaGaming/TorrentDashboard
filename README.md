<div align="center">

# Torrent Dashboard

**A clean, self-hosted qBitTorrent dashboard built for desktop and mobile browsers.**

![Python](https://img.shields.io/badge/Python-3.13+-3776AB?logo=python&logoColor=white)
![qBitTorrent](https://img.shields.io/badge/qBitTorrent-Web%20API-2F67BA)
![Release](https://img.shields.io/github/v/release/CynicaGaming/TorrentDashboard?include_prereleases&label=pre-release)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey)

</div>

> [!NOTE]
> Torrent Dashboard is currently in **0.x prerelease development**. Features and configuration may change between builds.

## Overview

Torrent Dashboard provides a modern browser interface for monitoring and managing one or more qBitTorrent clients. It is intended for local or trusted-network use and is designed for phones, tablets, and desktop displays.

### Highlights

- Live torrent status, progress, speed, ETA, ratio, and health information
- Responsive desktop and mobile interface
- qBitTorrent-style torrent context actions and details
- Multiple qBitTorrent client support
- Administrator and Standard User dashboard roles with self-service account profiles
- Trusted network-interface and IP/CIDR access controls
- Modular media-service and notification integrations
- Browser notifications and configurable completion sounds
- Manual in-application prerelease updates from a **public GitHub repository**
- Single-instance protection and update rollback safeguards

## Quick Start

### Requirements

- Python **3.13 or newer**
- qBitTorrent with its **Web UI enabled**
- qBitTorrent 5.2+ is recommended for Web API key authentication

### Windows

1. Download the latest `Torrent-Dashboard-X.Y.Z.zip` from GitHub Releases.
2. Extract it to a permanent folder.
3. Run `Start Dashboard.bat`.
4. Complete the First Run Setup wizard.

### Linux

1. Download and extract the latest release ZIP.
2. Run `python3 dashboard.py` from the extracted directory.
3. Complete the First Run Setup wizard.

Torrent Dashboard listens on `0.0.0.0` so permitted devices on your network can reach it. The wizard detects the local address and lets you choose the dashboard port and trusted interfaces.

## Configuration

Configuration is handled through the First Run Setup wizard and **Settings**. A hand-edited example configuration is intentionally not shipped.

Runtime configuration is stored in `config.json`; databases, uploaded sounds, update state, integrity cache, and backups are stored under `data/`. Both are ignored by Git and excluded from release packages.

Stored passwords, qBitTorrent API keys, integration secrets, and webhook URLs are redacted before settings data is returned to the browser. They are still local application secrets at rest, so access to the Torrent Dashboard installation directory should be restricted to trusted operating-system users.

## Updates

1. Open **Settings → Updates**.
2. Enter the public GitHub repository as `owner/repository`, then select **Save**.
3. Select **Check for updates**. Torrent Dashboard validates that the repository is publicly reachable before comparing releases.

No GitHub access token is required or supported by the default updater. Torrent Dashboard reads public GitHub Release metadata, verifies GitHub's SHA-256 digest for the release ZIP, stages the update, restarts, and rolls back if the new version fails its health check.

Release automation publishes `Torrent-Dashboard-X.Y.Z.zip` plus a generated `Torrent-Dashboard-X.Y.Z.release.json` provenance sidecar. The updater trusts the GitHub asset digest; the sidecar exists for release provenance and external inspection rather than as a second independently authored checksum source.

## Security and Privacy

Keep qBitTorrent itself on localhost or another protected interface whenever possible and expose only Torrent Dashboard to trusted clients.

The repository intentionally excludes live configuration and runtime data. Release packaging also runs a public-repository hygiene check that rejects common credential formats, private-key material, `.env` files, `config.json`, and runtime data if they are accidentally tracked.

If you discover a security issue, do not post credentials or sensitive exploit details in a public issue.

## Development

Architecture and module ownership are documented in [`ARCHITECTURE.md`](ARCHITECTURE.md). Current development handoff state is generated in [`PROJECT_STATE.md`](PROJECT_STATE.md). Backend domain modules isolate users/accounts, configuration lifecycle, configuration transactions, and integrations from the HTTP composition root.

Backend tests use the Python standard library and can be run with:

```bash
python -m unittest discover -s tests -v
```

Reusable source/architecture validation can be run with:

```bash
python release_tools/validate_source.py
```

Development releases use semantic versions in the `0.x.x` range. Structured release metadata in `release_notes/releases.json` generates the changelog, project handoff, and GitHub release body.

Pull requests and forks are welcome. Fork maintainers can point **Settings → Updates** at their own public release repository or change `DEFAULT_UPDATE_REPOSITORY` for their build.
