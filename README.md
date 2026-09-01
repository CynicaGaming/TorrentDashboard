# Torrent Desk

Torrent Desk is a local qBittorrent management dashboard. It is intended to run on the same PC/server as qBittorrent while being usable from desktop and mobile browsers on your LAN.

## Highlights

- Responsive desktop table and portrait mobile cards
- First-run setup wizard
- qBittorrent API-key authentication on qBittorrent 5.2+ / Web API 2.14.1+
- Username/password compatibility for older qBittorrent versions
- Multiple qBittorrent instances
- Search, filters, saved views, categories, tags, trackers, and sorting
- Torrent details, files, peers, trackers, pieces, and common management actions
- SQLite transfer history and analytics
- Optional browser/webhook notifications and media automation integrations
- Dashboard login with required, trusted-LAN-bypass, or disabled authentication modes
- Trusted network-interface selection and explicit IP/CIDR whitelist entries
- PWA support and optional QR-code LAN access
- Verified in-app updates from GitHub Releases

## Quick Start

1. Install Python 3.11+.
2. Extract Torrent Desk.
3. Double-click **Start Dashboard.bat**.
4. Your browser opens the first-run setup wizard.
5. Configure dashboard access and qBittorrent.
6. Test the qBittorrent connection before finishing setup.

Torrent Desk binds to `0.0.0.0:8765` by default. Its local browser opens `http://127.0.0.1:8765`.

## qBittorrent API Key

On qBittorrent 5.2.0+ you can use an API key instead of a qBittorrent username/password. Generate it in qBittorrent under **Preferences → Web UI → API Key**.

Torrent Desk sends it as:

```text
Authorization: Bearer qbt_...
```

This method avoids the Web UI login-cookie flow and therefore avoids qBittorrent login-ban behavior caused by repeated bad passwords.

Older qBittorrent installations can use username/password mode.

## Dashboard Authentication

Torrent Desk supports three modes:

- **Required Everywhere** — every browser must sign in.
- **Bypass For Trusted Addresses** — selected local NIC subnets and explicitly whitelisted IP/CIDRs bypass the login screen; other clients must sign in.
- **Disabled** — no dashboard login is required.

The default bind address is `0.0.0.0`.

### Trusted Network Interfaces

Torrent Desk detects active IPv4 network interfaces and displays:

- interface name
- interface address
- CIDR/subnet
- netmask
- default gateway
- usable address range
- default-route indicator

You can select multiple NICs. Their current subnets are included in the effective trusted network list.

### IP Address Whitelist

The manual list accepts one address or CIDR per line, for example:

```text
10.0.0.25
10.20.0.0/24
100.64.20.5
```

A single IP is treated as `/32` (or `/128` for IPv6).

Loopback is always trusted.

## Optional Dependencies

The setup wizard and Settings page can install supported optional dependencies using an internal allowlist.

QR support requires:

```text
qrcode
Pillow
```

Other helper features may require:

```text
pystray
pywin32
pyinstaller
```

If package installation fails, Torrent Desk shows pip's error output so you can resolve the Python environment manually.

## Configuration

Most configuration should be done through the setup wizard and Settings page. `config.example.json` is retained as an advanced/manual reference.

Important files/directories:

```text
config.json                 local settings and credentials
static/                     browser UI
data/torrent_desk.sqlite3   local history database
data/updates/               staged updates and backups
```

`config.json` and `data/` are intentionally excluded from Git release packages.

## Update System

Torrent Desk can update itself from GitHub Releases.

In **Settings → Application Updates**:

1. Enable GitHub updates.
2. Enter a repository such as `CynicaGaming/TorrentDashboard`.
3. Choose whether to check automatically.
4. Set the automatic check interval.

Normal public-repository update checks use:

```text
https://github.com/OWNER/REPO/releases/latest/download/update-manifest.json
```

A release contains:

```text
Torrent-Desk-X.Y.Z.zip
Torrent-Desk-X.Y.Z.zip.sha256
update-manifest.json
```

The updater:

1. downloads the release manifest,
2. validates its schema and application ID,
3. compares the release version with the running version,
4. downloads the exact versioned ZIP,
5. verifies its SHA-256,
6. verifies the expected package size when provided,
7. rejects unsafe ZIP paths,
8. stages the verified files under `data/updates/`,
9. launches a separate updater process,
10. creates a backup of application files that will be replaced,
11. preserves `config.json` and `data/`,
12. overlays the new application files,
13. restarts Torrent Desk,
14. checks `/health` for the expected new version,
15. automatically restores the backup if the new version does not start successfully.

Because the running server cannot reliably replace itself—particularly on Windows—the installation step is handled by `updater.py` after the dashboard process shuts down.

### Release Workflow

The repository contains `.github/workflows/release.yml` plus `release_tools/build_release.py`.

The included GitHub Actions workflow publishes releases from version changes on `main`. Before publishing a new version, update the `VERSION` constant in `dashboard.py` and push the completed source.

The release builder creates the versioned ZIP, its SHA-256 file, and `update-manifest.json`. It validates that the requested release version matches Torrent Desk's `VERSION` constant.

## Updating Existing Installs

For an initial installation of an updater-enabled build, install the provided ZIP normally. After a GitHub repository is configured and it has compatible release assets, use:

**Settings → Application Updates → Check For Updates → Download Update → Install And Restart**

Future application releases preserve local configuration and history.

## Optional Windows Helpers

- **Start Dashboard.bat** — launches the app with `py` or `python`.
- **Start at Login.bat** — creates a shortcut in the current user's Startup folder.
- **Set Dashboard Password.bat** — changes the dashboard password from the console.
- **Build EXE.bat** — optional PyInstaller helper.
- `tray.py` — optional Windows tray launcher (`pystray`, Pillow).
- `windows_service.py` — optional Windows service wrapper (`pywin32`).

## Docker

A `Dockerfile` and `docker-compose.yml` are included. Persist `/app/config.json` and `/app/data` when using containers.

## Linux / systemd

`torrent-desk.service` is included as a starting point. Adjust paths and the service user before installing it.

## Security Guidance

Binding to `0.0.0.0` means the service is reachable from interfaces allowed through the host firewall.

For a LAN-only deployment:

- keep qBittorrent on `127.0.0.1` where possible,
- expose only Torrent Desk to the LAN,
- use dashboard authentication unless you deliberately trust the LAN,
- keep read-only mode available if you only need monitoring.

Do not expose the plain HTTP server directly to the public Internet. Prefer a VPN or a properly configured HTTPS reverse proxy.

## Title Case UI

- Primary UI labels and navigation use Title Case as the visual naming convention.
- Authentication can trust one or more selected network interfaces; their current subnets are derived automatically.
- `trusted_ips` is a general exact-IP / CIDR whitelist independent of interface trust.
- The first-run wizard and Settings page expose optional dependency installation, including QR support.
- The login form deliberately opens with blank credentials and includes autofill-suppression hints for browsers/password managers.


## Private Repository Updates

The default update repository is `CynicaGaming/TorrentDashboard`. Because the repository is currently private, Torrent Desk supports a server-side **GitHub Update Token**. Use a fine-grained personal access token restricted to this repository with **Contents: Read** permission. The token is stored only in local `config.json`, redacted from browser-facing settings responses, and excluded from release archives. If the repository becomes public later, the token can be removed.

The included GitHub Actions workflow creates a release automatically when `main` is pushed with a new `VERSION`. If a release for that version already exists, the workflow exits without republishing it.
