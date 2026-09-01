# Torrent Desk

Torrent Desk is a local, responsive qBittorrent dashboard and management interface with mobile support, setup wizard, LAN-aware authentication, API-key support, history, notifications, integrations, and verified in-app updates.

This repository is managed as the update source for Torrent Desk. The application defaults to `CynicaGaming/TorrentDashboard` for update checks.

## Private Repository Updates

Because this repository is private, Torrent Desk supports a server-side **GitHub Update Token**. Use a fine-grained personal access token restricted to this repository with **Contents: Read** permission. The token is stored only in the local `config.json`, redacted from browser-facing settings responses, and excluded from release archives.

## Releases

Pushing `main` with a new `VERSION` in `dashboard.py` triggers the included GitHub Actions workflow. It builds a clean ZIP, SHA-256 checksum, and `update-manifest.json`, then creates the corresponding GitHub Release. If that version already has a release, the workflow skips republishing it.
