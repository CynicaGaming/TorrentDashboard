# Torrent Desk 3.4.0 Prerelease

## Current Cleanup

- Title Case is the UI naming convention.
- All password/API Key/token fields have Show/Hide controls.
- Setup uses Next on intermediate stages and Finish only on Review.
- qBittorrent setup verification is retained.
- QR-code support and optional dependency installation have been removed.
- LAN URL is part of Dashboard Access; the separate Remote Access card has been removed.
- Setup and Settings include Test GitHub Connection for repository/token validation.
- The service worker cache is versioned and deletes older Torrent Desk caches on activation.
- Non-core BAT, Docker, service, tray, startup, and EXE-builder helpers are removed.
- GitHub private-repository updates, checksum verification, rollback, and config/data preservation remain enabled.
- `v3.4.0` is temporarily replaced in place as a prerelease while the application is being stabilized.
