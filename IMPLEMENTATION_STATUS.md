# Torrent Desk implementation status

This file tracks the implementation status of the larger Torrent Desk roadmap.

## Implemented

- Responsive desktop and mobile dashboard
- qBittorrent Web API integration
- qBittorrent API-key support (5.2.0+)
- Username/password fallback for older qBittorrent versions
- Read-only mode
- Multi-server configuration
- Per-torrent detail drawer
- Files, peers, trackers, and pieces detail tabs
- Per-torrent actions
- Bulk actions
- Add magnet and `.torrent` support
- Category/tag/tracker filtering
- Sorting
- Saved views
- Column visibility preferences
- Theme/density/accent preferences
- SQLite history
- Transfer analytics
- Browser notifications
- Webhook, Discord, ntfy notification support
- Sonarr/Radarr/Lidarr/Prowlarr/Jellyfin/Plex configuration and health/status integrations
- PWA support
- QR-code LAN access (optional dependency)
- Optional dependency installer
- Setup wizard
- Setup-time qBittorrent credential/API-key validation
- Dashboard authentication modes: required, LAN bypass, disabled
- Multi-NIC trusted network selection
- General IP/CIDR whitelist
- Audit logging
- HTTPS settings
- Dockerfile/docker-compose helper
- systemd service helper
- Windows startup helper
- Windows tray/service helper scripts (optional dependencies)
- GitHub Releases update checks
- Update manifest + SHA-256 verification
- Safe ZIP extraction
- Staged update downloader
- Detached update installer
- Pre-update application-file backup
- Health-checked restart
- Automatic rollback on failed update
- GitHub Actions release workflow
- Title Case UI naming convention

## Environment-dependent / partial

- Windows tray requires `pystray` + Pillow.
- Windows Service requires `pywin32` and should be validated on the target Windows installation.
- EXE creation requires PyInstaller and is provided as a helper rather than a prebuilt binary.
- QR codes require `qrcode` + Pillow; setup/settings can install these dependencies.
- Direct HTTPS serving requires the user to provide a certificate/key. Reverse-proxy deployment is generally preferable for Internet-facing access.
- Plex/Jellyfin integration currently verifies connectivity rather than providing exact media-import correlation for every torrent.
- Auto-updates rely on correctly published GitHub Release assets and a trusted SHA-256 manifest. The updater does not implement cryptographic manifest signing yet.

## Security notes

- qBittorrent credentials/API keys remain server-side.
- Dashboard passwords are PBKDF2-SHA256 hashed.
- Authenticated write operations use CSRF tokens.
- Audit entries are recorded for dashboard actions.
- LAN bypass trusts only selected NIC subnets plus explicitly configured IP/CIDR whitelist entries.
- qBittorrent login attempts back off after credential rejection / HTTP 403 to avoid lockout loops.
- API-key clients never call qBittorrent `/auth/login`.
- Update ZIPs are SHA-256 verified and protected against path traversal before installation.
- Updates preserve `config.json` and `data/` and create a rollback backup before replacing application files.

- 3.4.0: Defaulted updates to CynicaGaming/TorrentDashboard, added authenticated private-release downloads, and converted visible UI copy to Title Case.
