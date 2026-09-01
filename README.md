# Torrent Desk

Torrent Desk is a local qBittorrent dashboard and management UI for desktop and mobile browsers.

## Quick Start

1. Install Python 3.11+.
2. Extract the client.
3. Double-click **Start Dashboard.bat**.
4. Complete the first-run setup wizard.
5. Test the qBittorrent connection before selecting **Finish**.

Torrent Desk listens on `0.0.0.0:8765` by default and opens `127.0.0.1:8765` on the host PC.

## Authentication

Dashboard access can be required everywhere, bypassed for selected trusted network interfaces / explicit IP or CIDR whitelist entries, or disabled. qBittorrent 5.2+ can use an API Key; older versions can use username/password.

All password, API Key, and token fields in the browser UI include Show/Hide controls. Credentials remain server-side.

## Optional Dependency

QR Code support requires `qrcode` and Pillow. It can be installed during setup or later in Settings. The standard client intentionally omits Docker, service/tray, EXE-builder, startup, and password-reset helper files.

## Updates

The default update source is `CynicaGaming/TorrentDashboard`. Because the repository is private, use a fine-grained GitHub token restricted to this repository with **Contents: Read** permission. The token is stored only in local `config.json` and is redacted from browser-facing settings.

During the current prerelease cycle, `v3.4.0` is replaced in place on each completed `main` build. Once the application is declared stable, releases should return to immutable versioned tags.

Updates download a manifest and versioned ZIP, verify SHA-256, stage safely, preserve `config.json` and `data/`, restart through `updater.py`, health-check the new version, and roll back application files if startup fails.

## Standard Client Files

- `Start Dashboard.bat`
- `dashboard.py`
- `updater.py`
- `static/`
- `release_tools/`
- `requirements-optional.txt`
- `config.example.json`
- `.gitignore`
- documentation

Do not share `config.json`; it contains local credentials and secrets.
