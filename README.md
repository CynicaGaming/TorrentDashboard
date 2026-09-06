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
- At-a-glance integration health indicators
- Browser/PWA device notifications with enable, disable, and test controls
- Default MP3 completion sound plus configurable custom sounds
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
2. From the extracted Torrent Dashboard directory, run `python3 dashboard.py`.
3. Complete the First Run Setup wizard in the browser.

Torrent Dashboard listens on `0.0.0.0` so permitted devices on your network can reach it. The wizard detects the local address and lets you choose the dashboard port and trusted interfaces.

## Configuration

Configuration is handled through the First Run Setup wizard and **Settings**. A hand-edited example configuration is intentionally not shipped.

Runtime configuration is stored in `config.json`; databases, uploaded sounds, update state, and backups are stored under `data/`. Both are ignored by Git and excluded from release packages.

Stored passwords, qBitTorrent API keys, integration secrets, and webhook URLs are redacted before settings data is returned to the browser.

## Integration Health

The Integrations page displays a status indicator to the left of each integration name:

- **Green:** the most recent explicit connection test succeeded.
- **Yellow:** the integration is untested, changed since the last test, or needs attention without being a network-level disconnect.
- **Red:** the integration is disabled or its last test showed a network-level connection failure.

Health results are stored locally in the browser as an at-a-glance status hint. They are not a continuous server-side monitoring system.

Some delivery integration tests send a real message. Discord, ntfy, generic webhook, and Home Assistant connections are therefore tested only when you explicitly select **Test Connection**; Torrent Dashboard does not automatically probe them on page load.

## Notifications and Sounds

Under **Settings → Notifications**, browser/PWA notifications can be enabled, disabled, and tested. The setting uses the browser and operating-system notification permission available to the current dashboard origin.

On supported Apple mobile devices, notification permission requires Torrent Dashboard to be installed to the Home Screen and opened as a PWA.

The current notification controls do **not** constitute a complete server-side background Web Push system. The service worker can display and handle notifications, but subscription storage and a server-side push sender are not currently configured. Browser/PWA alerts are generated through the dashboard's existing notification path.

The default completion sound is `notification-default.mp3`. Custom WAV, MP3, and OGG completion sounds remain supported and are stored in runtime data rather than in the repository.

See [Notifications and Integration Health](docs/NOTIFICATIONS.md) for the detailed behavior and troubleshooting notes.

## Updates

1. Open **Settings → Updates**.
2. Enter the public GitHub repository as `owner/repository`, then select **Save**.
3. Select **Check for updates**. Torrent Dashboard validates that the repository is publicly reachable before comparing releases.

No GitHub access token is required or supported by the default updater. Torrent Dashboard reads public GitHub Release metadata, verifies GitHub's SHA-256 digest for the release asset, stages the update, restarts, and rolls back if the new version fails its health check.

A release only needs `Torrent-Dashboard-X.Y.Z.zip`; separate checksum and update-manifest assets are not required.

## Security and Privacy

Keep qBitTorrent itself on localhost or another protected interface whenever possible and expose only Torrent Dashboard to trusted clients.

The repository intentionally excludes live configuration and runtime data. Release packaging also runs a public-repository hygiene check that rejects common credential formats, private-key material, `.env` files, `config.json`, and runtime data if they are accidentally tracked.

If you discover a security issue, do not post credentials or sensitive exploit details in a public issue.

## Repository Layout

- `dashboard.py` — application server, qBitTorrent access, authentication, integrations, history, and update orchestration
- `updater.py` — update installation and rollback support
- `static/` — browser UI, settings, PWA service worker, and bundled notification assets
- `release_tools/` — source, UI, checkpoint, and release validation
- `docs/` — architecture and behavior documentation
- `.github/workflows/` — pull-request validation and prerelease publishing

See [Architecture](docs/ARCHITECTURE.md) for the component and data-flow overview.

## Development

Development releases use semantic versions in the `0.x.x` range. GitHub prereleases are titled **Torrent Dashboard Pre-Release**; the version remains in the Git tag and ZIP name so the updater can order releases safely.

Runtime only requires Python. Contributor validation also uses Node.js to syntax-check the browser JavaScript.

Before opening a pull request, run:

```bash
python -m py_compile dashboard.py updater.py release_tools/build_release.py release_tools/validate_checkpoint.py
for file in static/*.js; do node --check "$file"; done
python release_tools/validate_public_repo.py
python release_tools/validate_ui_strings.py
python release_tools/validate_checkpoint.py
```

Pull requests run the validation workflow automatically. The release builder also runs the checkpoint validator before producing the ZIP.

See [CONTRIBUTING.md](CONTRIBUTING.md) before changing version-coupled frontend assets, notification behavior, integrations, authentication, or update code.

Pull requests and forks are welcome. Fork maintainers can point **Settings → Updates** at their own public release repository or change `DEFAULT_UPDATE_REPOSITORY` for their build.
