#!/usr/bin/env python3
"""Apply the v0.5.64 configuration and integrations composition switch."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.63"
NEW = "0.5.64"


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def write(path, text):
    (ROOT / path).write_text(text, encoding="utf-8")


def one(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


# dashboard.py becomes a composition root for configuration/integrations.
d = read("dashboard.py")
d = one(
    d,
    "from torrent_dashboard.config_store import ConfigStore\nfrom torrent_dashboard.users import (",
    '''from torrent_dashboard.config import (
    ConfigRepository,
    DEFAULT_CONFIG,
    DEFAULT_UPDATE_REPOSITORY,
    normalize_github_repository,
    public_config,
)
from torrent_dashboard.config_store import ConfigStore
from torrent_dashboard.integrations import (
    INTEGRATION_TYPES,
    delete_integration,
    integration_catalog,
    normalize_integration,
    redacted_integrations,
    save_integration,
    test_integration_connection,
)
from torrent_dashboard.users import (''',
    "dashboard imports",
)
d = one(d, 'VERSION = "0.5.63"', 'VERSION = "0.5.64"', "version")
d = one(d, 'DEFAULT_UPDATE_REPOSITORY = "CynicaGaming/TorrentDashboard"\n', "", "update repo constant")

start = d.index("DEFAULT_CONFIG = {")
end = d.index("class SessionStore:", start)
d = d[:start] + '''CONFIG_REPOSITORY = ConfigRepository(
    CONFIG_PATH,
    detect_lan_network=lambda: detect_lan_network(),
)
CONFIG_STORE = ConfigStore(CONFIG_REPOSITORY.load, CONFIG_REPOSITORY.save)


def load_config():
    return CONFIG_STORE.load()


def mutate_config(transform):
    return CONFIG_STORE.mutate(transform)


''' + d[end:]

start = d.index("INTEGRATION_TYPES = {")
end = d.index("def normalize_qbittorrent_server", start)
d = d[:start] + d[end:]

start = d.index("def normalize_github_repository(value: str) -> str:")
end = d.index("def github_headers", start)
d = d[:start] + d[end:]

start = d.index("def redacted_config(cfg):")
end = d.index("def apply_settings_update", start)
d = d[:start] + '''def redacted_config(cfg):
    out = public_config(cfg)
    out["runtime"] = {
        "detected_lan": detect_lan_network(),
        "local_ip": local_lan_ip(),
        "network_interfaces": detect_network_interfaces(),
        "trusted_interface_networks": interface_networks(cfg.get("auth", {}).get("trusted_interfaces", [])),
        "effective_trusted_cidrs": effective_trusted_cidrs(cfg.get("auth", {})),
        "updateState": update_state(),
        "releaseHistory": local_release_history(),
    }
    return out


''' + d[end:]

for marker in (
    "def _load_config_unlocked",
    "def _save_config_unlocked",
    "def normalize_integration",
    "def redacted_integrations",
    "def normalize_github_repository",
    "INTEGRATION_TYPES = {",
):
    if marker in d:
        raise RuntimeError(f"dashboard.py still owns extracted behavior: {marker}")
write("dashboard.py", d)

# Architecture validation now makes the extraction permanent.
v = read("release_tools/validate_source.py")
v = one(
    v,
    '''    if "from torrent_dashboard.users import" not in source:
        fail("dashboard.py must consume the extracted users module")
    if "from torrent_dashboard.config_store import ConfigStore" not in source:
        fail("dashboard.py must use ConfigStore for configuration coordination")
''',
    '''    if "from torrent_dashboard.users import" not in source:
        fail("dashboard.py must consume the extracted users module")
    if "from torrent_dashboard.config import" not in source:
        fail("dashboard.py must consume the extracted configuration module")
    if "from torrent_dashboard.integrations import" not in source:
        fail("dashboard.py must consume the extracted integrations module")
    if "from torrent_dashboard.config_store import ConfigStore" not in source:
        fail("dashboard.py must use ConfigStore for configuration coordination")

    forbidden_ownership = (
        "def _load_config_unlocked",
        "def _save_config_unlocked",
        "def normalize_integration",
        "def redacted_integrations",
        "def normalize_github_repository",
        "INTEGRATION_TYPES = {",
    )
    leftovers = [marker for marker in forbidden_ownership if marker in source]
    if leftovers:
        fail("dashboard.py still owns extracted configuration/integration behavior: " + ", ".join(leftovers))
    if "CONFIG_STORE = ConfigStore(CONFIG_REPOSITORY.load, CONFIG_REPOSITORY.save)" not in source:
        fail("dashboard.py must coordinate ConfigRepository through ConfigStore")
''',
    "validator ownership",
)
write("release_tools/validate_source.py", v)

u = read("release_tools/validate_ui_strings.py")
u = one(
    u,
    '''    dashboard_py = (ROOT / "dashboard.py").read_text(encoding="utf-8")
    config_store_py = (ROOT / "torrent_dashboard" / "config_store.py").read_text(encoding="utf-8")
    users_py = (ROOT / "torrent_dashboard" / "users.py").read_text(encoding="utf-8")
''',
    '''    dashboard_py = (ROOT / "dashboard.py").read_text(encoding="utf-8")
    config_py = (ROOT / "torrent_dashboard" / "config.py").read_text(encoding="utf-8")
    config_store_py = (ROOT / "torrent_dashboard" / "config_store.py").read_text(encoding="utf-8")
    integrations_py = (ROOT / "torrent_dashboard" / "integrations.py").read_text(encoding="utf-8")
    users_py = (ROOT / "torrent_dashboard" / "users.py").read_text(encoding="utf-8")
''',
    "UI validator sources",
)
u = one(
    u,
    '    assert \'DEFAULT_UPDATE_REPOSITORY = "CynicaGaming/TorrentDashboard"\' in dashboard_py\n',
    '    assert \'DEFAULT_UPDATE_REPOSITORY = "CynicaGaming/TorrentDashboard"\' in config_py\n',
    "UI update repo ownership",
)
u = one(
    u,
    '''    # 0.5.56 serializes all configuration read/modify/write mutations.
    assert 'from torrent_dashboard.config_store import ConfigStore' in dashboard_py
    assert 'CONFIG_STORE = ConfigStore(_load_config_unlocked, _save_config_unlocked)' in dashboard_py
    assert 'def mutate_config(transform):' in dashboard_py
    assert 'class ConfigStore:' in config_store_py and 'with self._lock:' in config_store_py
''',
    '''    # 0.5.56 serializes all configuration read/modify/write mutations; 0.5.64
    # moves schema/migration/persistence ownership behind ConfigRepository.
    assert 'from torrent_dashboard.config import (' in dashboard_py
    assert 'from torrent_dashboard.integrations import (' in dashboard_py
    assert 'from torrent_dashboard.config_store import ConfigStore' in dashboard_py
    assert 'CONFIG_STORE = ConfigStore(CONFIG_REPOSITORY.load, CONFIG_REPOSITORY.save)' in dashboard_py
    assert 'def mutate_config(transform):' in dashboard_py
    assert 'class ConfigRepository:' in config_py and 'def normalize_config(' in config_py
    assert 'INTEGRATION_TYPES = {' in integrations_py and 'def normalize_integration(' in integrations_py
    assert 'def _load_config_unlocked' not in dashboard_py and 'INTEGRATION_TYPES = {' not in dashboard_py
    assert 'class ConfigStore:' in config_store_py and 'with self._lock:' in config_store_py
''',
    "UI config ownership",
)
write("release_tools/validate_ui_strings.py", u)

# Frontend build generation remains synchronized.
html = read("static/index.html")
if OLD not in html:
    raise RuntimeError("index build marker missing")
write("static/index.html", html.replace(OLD, NEW))

app = read("static/app.js")
app = one(app, "const FRONTEND_BUILD='0.5.63';", "const FRONTEND_BUILD='0.5.64';", "app build marker")
write("static/app.js", app)

sw = read("static/sw.js")
sw = one(sw, "torrent-dashboard-v0563", "torrent-dashboard-v0564", "service worker cache")
if OLD not in sw:
    raise RuntimeError("service-worker asset marker missing")
write("static/sw.js", sw.replace(OLD, NEW))

# Durable documentation follows the actual module ownership.
a = read("ARCHITECTURE.md")
a = one(
    a,
    "Owns application composition, process startup, HTTP routing, qBitTorrent orchestration, sessions, network/interface discovery, integrations, notification delivery, history collection, update orchestration, and compatibility adapters that have not yet been extracted.",
    "Owns application composition, process startup, HTTP routing, qBitTorrent orchestration, sessions, network/interface discovery, notification delivery, history collection, update orchestration, and compatibility adapters that have not yet been extracted. Configuration and integration domains are imported from package modules rather than implemented here.",
    "architecture dashboard",
)
a = one(
    a,
    '''### `torrent_dashboard/config_store.py`

Owns in-process configuration transaction coordination. `mutate()` acquires the lock before reading the latest configuration, applies one transformation, persists it, and releases the lock only after the write completes.

Configuration schema normalization and migration are still in `dashboard.py` and are the next backend extraction target.
''',
    '''### `torrent_dashboard/config.py`

Owns configuration defaults, legacy migrations, update-repository normalization, browser-safe configuration redaction, and atomic `config.json` persistence through `ConfigRepository`. LAN detection needed by one legacy migration is injected by the composition root rather than imported from it.

### `torrent_dashboard/config_store.py`

Owns in-process configuration transaction coordination. `mutate()` acquires the lock before reading the latest configuration through `ConfigRepository`, applies one transformation, persists it, and releases the lock only after the write completes.

### `torrent_dashboard/integrations.py`

Owns the integration provider catalog, field validation and normalization, configured-secret redaction, connection tests, and integration CRUD transforms. Provider definitions no longer live in the HTTP adapter.
''',
    "architecture config modules",
)
a = one(
    a,
    '''The next useful boundaries are:

1. **Configuration** — schema defaults, migrations, normalization, sanitization, and persistence.
2. **Release/update metadata** — GitHub release parsing, installed provenance, and integrity-history persistence.
3. **qBitTorrent client/domain operations** — isolate Web API transport and normalization from HTTP routes.
4. **Integrations/notifications** — separate provider normalization and delivery health from request handling.
5. **Frontend feature modules** — reduce the responsibility of `static/app.js` after backend boundaries stabilize.
''',
    '''The next useful boundaries are:

1. **Release/update metadata** — GitHub release parsing, installed provenance, and integrity-history persistence.
2. **qBitTorrent client/domain operations** — isolate Web API transport, server normalization, and preference translation from HTTP routes.
3. **Request/application services** — move setup and settings transformations behind testable service functions so HTTP handlers remain adapters.
4. **Notification delivery** — separate delivery dispatch from provider configuration now that integration definitions are isolated.
5. **Frontend feature modules** — reduce the responsibility of `static/app.js` after backend boundaries stabilize.
''',
    "architecture roadmap",
)
write("ARCHITECTURE.md", a)

r = read("README.md")
r = one(
    r,
    "Architecture and module ownership are documented in [`ARCHITECTURE.md`](ARCHITECTURE.md). Current development handoff state is generated in [`PROJECT_STATE.md`](PROJECT_STATE.md).\n",
    "Architecture and module ownership are documented in [`ARCHITECTURE.md`](ARCHITECTURE.md). Current development handoff state is generated in [`PROJECT_STATE.md`](PROJECT_STATE.md). Backend domain modules isolate users/accounts, configuration lifecycle, configuration transactions, and integrations from the HTTP composition root.\n",
    "README architecture summary",
)
write("README.md", r)

# Structured release metadata remains the source of truth for generated handoff docs.
p = ROOT / "release_notes" / "releases.json"
data = json.loads(p.read_text(encoding="utf-8"))
if any(str(item.get("version")) == NEW for item in data.get("releases", [])):
    raise RuntimeError("v0.5.64 release metadata already exists")
data["releases"].append({
    "version": NEW,
    "date": "2026-09-02",
    "status": "prerelease",
    "title": "Configuration and integrations module extraction",
    "summary": "Moves configuration lifecycle and integration-provider ownership out of dashboard.py into dedicated package modules while preserving existing dashboard behavior.",
    "highlights": [
        "Added torrent_dashboard/config.py for defaults, legacy migrations, update-repository normalization, browser-safe redaction, and atomic config.json persistence.",
        "Added torrent_dashboard/integrations.py for provider definitions, normalization, secret redaction, connection tests, and integration CRUD transforms.",
        "dashboard.py now composes ConfigRepository through ConfigStore instead of implementing configuration lifecycle inline.",
        "Existing route handlers keep their established helper call surface through imports to minimize refactor blast radius."
    ],
    "fixes": [],
    "technical": [
        "LAN detection for the legacy auto-trust migration is injected into ConfigRepository, preserving the no-import-back-to-dashboard dependency rule.",
        "ConfigStore remains the transaction coordinator while ConfigRepository owns parsing, migration, normalization, and atomic persistence.",
        "Browser configuration sanitization now has a package boundary; dashboard.py only adds runtime network and update state."
    ],
    "validation": [
        "Configuration tests cover default creation, legacy network/auth/integration/update migrations, save cleanup, and browser secret redaction.",
        "Integration tests cover secret preservation, URL validation, immutable CRUD transforms, and provider catalog metadata.",
        "Reusable source validation rejects configuration or integration ownership drifting back into dashboard.py.",
        "Existing UI, frontend-generation, release-metadata, user-domain, and configuration-concurrency checks remain active."
    ],
    "known_issues": [
        "dashboard.py and static/app.js remain larger than the intended steady-state architecture; release/update metadata and qBitTorrent transport are the next high-value extraction boundaries.",
        "ConfigStore coordinates only the running process; an external editor writing config.json concurrently is not cross-process locked."
    ],
    "architecture": [
        "dashboard.py is the composition root and HTTP adapter; configuration schema/persistence and integration definitions are no longer implemented there.",
        "User and account logic lives in torrent_dashboard/users.py.",
        "Configuration defaults, migrations, browser sanitization, repository normalization, and atomic persistence live in torrent_dashboard/config.py.",
        "Configuration transaction coordination lives in torrent_dashboard/config_store.py.",
        "Integration provider definitions, normalization, redaction, connection tests, and CRUD transforms live in torrent_dashboard/integrations.py.",
        "Runtime LAN detection is injected into ConfigRepository rather than reversing dependency direction to dashboard.py.",
        "Release/update provenance remains in dashboard.py and is the next planned extraction."
    ],
    "decisions": [
        "Continue behavior-preserving modularization in small prerelease increments.",
        "Package modules must not import dashboard.py.",
        "Keep ConfigStore focused on transaction coordination and ConfigRepository focused on configuration file lifecycle.",
        "Inject runtime-only dependencies into package modules instead of importing the process adapter.",
        "Keep integration provider configuration separate from notification delivery."
    ],
    "next_steps": [
        {"priority": 1, "title": "Extract release and update provenance", "detail": "Move GitHub release parsing, installed release metadata, package-integrity normalization, and historical digest caching out of dashboard.py."},
        {"priority": 2, "title": "Extract qBitTorrent transport and normalization", "detail": "Move QBitClient, server normalization, proxy/preference translation, and Web API transport away from HTTP routing."},
        {"priority": 3, "title": "Expand request-level behavioral tests", "detail": "Add authorization, CSRF, setup, account-route, and settings-mutation coverage around extracted service boundaries."},
        {"priority": 4, "title": "Harden secrets at rest", "detail": "Use the configuration boundary to add restrictive file permissions and separate ordinary configuration from stored credentials."}
    ]
})
p.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
subprocess.run([sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", NEW], cwd=ROOT, check=True)
print("Applied v0.5.64 configuration/integrations composition switch")
