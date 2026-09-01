# Torrent Desk

Torrent Desk is a local qBittorrent dashboard and management UI for desktop and mobile browsers.

## Quick Start

1. Install Python 3.11+.
2. Extract the client.
3. Double-click **Start Dashboard.bat**.
4. Complete the first-run setup wizard.
5. Test the qBittorrent connection and GitHub update access before selecting **Finish**.

Torrent Desk listens on `0.0.0.0:8765` by default and opens `127.0.0.1:8765` on the host PC.

## Dashboard Access

Dashboard access can be required everywhere, bypassed for selected trusted network interfaces / explicit IP or CIDR whitelist entries, or disabled. The Settings page shows the current **LAN URL** directly inside **Dashboard Access**, where it can be copied for use on another allowed device.

All password, API Key, and token fields in the browser UI include Show/Hide controls. Credentials remain server-side.

## qBittorrent Authentication

qBittorrent 5.2+ can use an API Key. Older versions can use username/password. Torrent Desk tests the selected authentication method before setup is completed.

## Application Updates

The default update repository is `CynicaGaming/TorrentDashboard`. The setup wizard and Settings page both provide **Test GitHub Connection**, which verifies repository/token access without saving the entered values. For private repositories, use a fine-grained token restricted to the repository with **Contents: Read** permission.

The updater verifies the release manifest and SHA-256 package hash, preserves `config.json` and `data/`, creates a pre-update backup, health-checks the restarted application, and rolls back if the new build does not start correctly.

During prerelease stabilization, `v3.4.0` is intentionally replaced in place on each completed `main` build.

## Client Contents

The standard client contains the dashboard application, browser UI, updater, release tooling, configuration example, and the single Windows launcher. QR-code support, Docker files, service/tray helpers, startup helpers, EXE-builder helpers, and password-reset BAT files are intentionally omitted.
