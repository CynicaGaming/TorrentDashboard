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
- Administrator and Standard User dashboard roles
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

Torrent Dashboard listens on `0.0.0.0` so permitted devices on your network can reach it. The wizard detects the local address and lets you choose the dashboard port and trusted interfaces.

## Configuration

Configuration is handled through the First Run Setup wizard and **Settings**. A hand-edited example configuration is intentionally not shipped.

Runtime configuration is stored in `config.json`; databases, uploaded sounds, update state, and backups are stored under `data/`. Both are ignored by Git and excluded from release packages.

Stored passwords, qBitTorrent API keys, integration secrets, and webhook URLs are redacted before settings data is returned to the browser.

## Updates

1. Open **Settings → Updates**.
2. Enter the public GitHub repository as `owner/repository`.
3. Select **Test connection**, then **Save**.
4. Select **Check for updates**.

No GitHub access token is required or supported by the default updater. Torrent Dashboard reads public GitHub Release metadata, verifies GitHub's SHA-256 digest for the release asset, stages the update, restarts, and rolls back if the new version fails its health check.

A release only needs `Torrent-Dashboard-X.Y.Z.zip`; separate checksum and update-manifest assets are not required.

## Security and Privacy

Keep qBitTorrent itself on localhost or another protected interface whenever possible and expose only Torrent Dashboard to trusted clients.

The repository intentionally excludes live configuration and runtime data. Release packaging also runs a public-repository hygiene check that rejects common credential formats, private-key material, `.env` files, `config.json`, and runtime data if they are accidentally tracked.

If you discover a security issue, do not post credentials or sensitive exploit details in a public issue.

## Development

Development releases use semantic versions in the `0.x.x` range. GitHub prereleases are titled **Torrent Dashboard Pre-Release**; the version remains in the Git tag and ZIP name so the updater can order releases safely.

Pull requests and forks are welcome. Fork maintainers can point **Settings → Updates** at their own public release repository or change `DEFAULT_UPDATE_REPOSITORY` for their build.
