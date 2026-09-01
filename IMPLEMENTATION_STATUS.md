# Torrent Desk 3.4.0 Prerelease

## Current Cleanup

- Title Case is the UI naming convention.
- All password/API Key/token fields have Show/Hide controls.
- Hidden login autofill decoys are excluded from reveal controls.
- Setup uses Next on intermediate stages and Finish only on Review.
- Setup/Review qBittorrent verification is retained and passes the API-key smoke test.
- The service worker cache is versioned and deletes older Torrent Desk caches on activation.
- QR Code support is the only optional runtime dependency in the standard client.
- Non-core BAT, Docker, service, tray, startup, and EXE-builder helpers are removed.
- GitHub private-repository updates, checksum verification, rollback, and config/data preservation remain enabled.
- `v3.4.0` is temporarily replaced in place as a prerelease while the application is being stabilized.

## Remaining Environment-Dependent Items

- Plex/Jellyfin exact import correlation depends on deployment path/rename rules.
- Direct HTTPS requires a certificate trusted by the client device.
- Disk-free reporting for remote qBittorrent hosts requires the download path to be accessible to Torrent Desk.
- Cryptographic signing of the update manifest remains a future hardening step beyond SHA-256 release verification.
