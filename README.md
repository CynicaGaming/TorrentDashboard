# Torrent Dashboard

Torrent Dashboard is a local qBitTorrent dashboard and management UI for desktop and mobile browsers.

## Prerelease Versioning

Development builds use semantic versions in the `0.x.x` range. GitHub Releases are titled **Torrent Dashboard Pre-Release**; the version remains in the Git tag and client ZIP name so the updater can order releases safely.

## Updates

The updater reads GitHub Release metadata directly. A release only needs the `Torrent-Dashboard-X.Y.Z.zip` client asset. GitHub supplies the ZIP SHA-256 digest through the Releases API, so separate `.sha256` and `update-manifest.json` assets are not required.

Private repositories require a fine-grained token with **Contents: Read**. Test access during setup or in Settings before saving.

## Configured Secrets

Stored passwords, API keys, and tokens are never returned to the browser. Settings display a persistent masked value to show that a secret is configured. The stored secret is preserved until the mask is replaced with a newly entered value.
