#!/usr/bin/env python3
"""Apply the v0.5.64 configuration and integrations composition switch."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD_VERSION = "0.5.63"
NEW_VERSION = "0.5.64"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old, new, 1)


# Switch the composition root to package-owned configuration and integrations.
dashboard = read("dashboard.py")
dashboard = replace_once(
    dashboard,
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
dashboard = replace_once(
    dashboard,
    f'VERSION = "{OLD_VERSION}"',
    f'VERSION = "{NEW_VERSION}"',
    "dashboard version",
)
dashboard = replace_once(
    dashboard,
    'DEFAULT_UPDATE_REPOSITORY = "CynicaGaming/TorrentDashboard"\n',
    "",
    "dashboard update repository constant",
)

config_start = dashboard.index("DEFAULT_CONFIG = {")
config_end = dashboard.index("class SessionStore:", config_start)
dashboard = dashboard[:config_start] + '''CONFIG_REPOSITORY = ConfigRepository(
    CONFIG_PATH,
    detect_lan_network=lambda: detect_lan_network(),
)
CONFIG_STORE = ConfigStore(CONFIG_REPOSITORY.load, CONFIG_REPOSITORY.save)


def load_config():
    return CONFIG_STORE.load()


def mutate_config(transform):
    return CONFIG_STORE.mutate(transform)


''' + dashboard[config_end:]

integration_start = dashboard.index("INTEGRATION_TYPES = {")
integration_end = dashboard.index("def normalize_qbittorrent_server", integration_start)
dashboard = dashboard[:integration_start] + dashboard[integration_end:]

github_start = dashboard.index("def normalize_github_repository(value: str) -> str:")
github_end = dashboard.index("def github_headers", github_start)
dashboard = dashboard[:github_start] + dashboard[github_end:]

redact_start = dashboard.index("def redacted_config(cfg):")
redact_end = dashboard.index("def apply_settings_update", redact_start)
dashboard = dashboard[:redact_start] + '''def redacted_config(cfg):
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


''' + dashboard[redact_end:]

for marker in (
    "def _load_config_unlocked",
    "def _save_config_unlocked",
    "def normalize_integration",
    "def redacted_integrations",
    "def normalize_github_repository",
    "INTEGRATION_TYPES = {",
):
    if marker in dashboard:
        raise RuntimeError(f"dashboard.py still owns extracted behavior: {marker}")
write("dashboard.py", dashboard)

# Strengthen reusable architecture validation around the new ownership boundary.
validator = read("release_tools/validate_source.py")
validator = replace_once(
    validator,
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
    "source validator module boundary",
)
write("release_tools/validate_source.py", validator)

# Move UI-regression source ownership checks to the extracted modules.
ui = read("release_tools/validate_ui_strings.py")
ui = replace_once(
    ui,
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
    "UI validator source map",
)
ui = replace_once(
    ui,
    '    assert \'DEFAULT_UPDATE_REPOSITORY = "CynicaGaming/TorrentDashboard"\' in dashboard_py\n',
    '    assert \'DEFAULT_UPDATE_REPOSITORY = "CynicaGaming/TorrentDashboard"\' in config_py\n',
    "UI validator update source owner",
)
ui = replace_once(
    ui,
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
    "UI validator config contract",
)
write("release_tools/validate_ui_strings.py", ui)

# Synchronize frontend generation markers.
index_html = read("static/index.html")
if OLD_VERSION not in index_html:
    raise RuntimeError("index.html has no old build marker")
write("static/index.html", index_html.replace(OLD_VERSION, NEW_VERSION))

app_js = read("static/app.js")
app_js = replace_once(
    app_js,
    f"const FRONTEND_BUILD='{OLD_VERSION}';",
    f"const FRONTEND_BUILD='{NEW_VERSION}';",
    "app.js frontend build",
)
write("static/app.js", app_js)

sw = read("static/sw.js")
sw = replace_once(sw, "torrent-dashboard-v0563", "torrent-dashboard-v0564", "service worker cache")
if OLD_VERSION not in sw:
    raise RuntimeError("sw.js has no old asset build marker")
write("static/sw.js", sw.replace(OLD_VERSION, NEW_VERSION))

# Update durable architecture documentation.
architecture = read("ARCHITECTURE.md")
architecture = replace_once(
    architecture,
    "Owns application composition, process startup, HTTP routing, qBitTorrent orchestration, sessions, network/interface discovery, integrations, notification delivery, history collection, update orchestration, and compatibility adapters that have not yet been extracted.",
    "Owns application composition, process startup, HTTP routing, qBitTorrent orchestration, sessions, network/interface discovery, notification delivery, history collection, update orchestration, and compatibility adapters that have not yet been extracted. Configuration and integration domains are imported from package modules rather than implemented here.",
    "architecture dashboard ownership",
)
architecture = replace_once(
    architecture,
    '''### `torrent_dashboard/config_store.py`

Owns in-process configuration transaction coordination. `mutate()` acquires the lock before reading the latest configuration, applies one transformation, persists it, and releases the lock only after the write completes.

Configuration schema normalization and migration are still in `dashboard.py` and are the next backend extraction target.
''',
    '''### `torrent_dashboard/config.py`

Owns configuration defaults, legacy migrations, update-repository normalization, browser-safe configuration redaction, and atomic `config.json` persistence through `ConfigRepository`. The only runtime-specific migration dependency is LAN detection, which is injected by the composition root as a callback.

### `torrent_dashboard/config_store.py`

Owns in-process configuration transaction coordination. `mutate()` acquires the lock before reading the latest configuration through `ConfigRepository`, applies one transformation, persists it, and releases the lock only after the write completes.

### `torrent_dashboard/integrations.py`

Owns the integration provider catalog, field validation and normalization, configured-secret redaction, connection tests, and integration CRUD transforms. Provider definitions no longer live in the HTTP adapter.
''',
    "architecture config ownership",
)
architecture = replace_once(
    architecture,
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
write("ARCHITECTURE.md", architecture)

readme = read("README.md")
readme = replace_once(
    readme,
    "Architecture and module ownership are documented in [`ARCHITECTURE.md`](ARCHITECTURE.md). Current development handoff state is generated in [`PROJECT_STATE.md`](PROJECT_STATE.md).\n",
    "Architecture and module ownership are documented in [`ARCHITECTURE.md`](ARCHITECTURE.md). Current development handoff state is generated in [`PROJECT_STATE.md`](PROJECT_STATE.md). Backend domain modules currently isolate users/accounts, configuration lifecycle, configuration transactions, and integrations from the HTTP composition root.\n",
    "README module summary",
)
write("README.md", readme)

# Require extracted modules in both published package contracts.
for path in (".github/workflows/publish-refactor-prerelease.yml", ".github/workflows/release.yml"):
    workflow = read(path)
    marker = "              '/torrent_dashboard/config_store.py',\n"
    if marker not in workflow:
        raise RuntimeError(f"{path}: required tuple marker missing")
    workflow = workflow.replace(
        marker,
        marker
        + "              '/torrent_dashboard/config.py',\n"
        + "              '/torrent_dashboard/integrations.py',\n",
        1,
    )
    write(path, workflow)

# Record v0.5.64 in the structured release source, then regenerate derived docs.
release_path = ROOT / "release_notes" / "releases.json"
data = json.loads(release_path.read_text(encoding="utf-8"))
if any(str(item.get("version")) == NEW_VERSION for item in data.get("releases", [])):
    raise RuntimeError(f"release metadata for {NEW_VERSION} already exists")
data["releases"].append({
    "version": NEW_VERSION,
    "date": "2026-09-02",
    "status": "prerelease",
    "title": "Configuration and integrations module extraction",
    "summary": "Moves configuration lifecycle and integration-provider ownership out of dashboard.py into dedicated package modules while preserving the existing HTTP and updater behavior.",
    "highlights": [
        "Added torrent_dashboard/config.py for configuration defaults, legacy migrations, update-repository normalization, browser-safe redaction, and atomic config.json persistence.",
        "Added torrent_dashboard/integrations.py for provider definitions, normalization, secret redaction, connection tests, and integration CRUD transforms.",
        "dashboard.py now composes ConfigRepository through ConfigStore and imports both extracted domains instead of implementing them inline.",
        "Existing route handlers keep their established helper call surface through imports, minimizing the behavioral blast radius of the extraction."
    ],
    "fixes": [],
    "technical": [
        "ConfigRepository receives LAN detection as an injected callback for the legacy auto-trust migration, preserving the rule that package modules never import dashboard.py.",
        "ConfigStore remains the serialized read/modify/write transaction coordinator; ConfigRepository owns file parsing, migrations, normalization, and atomic persistence.",
        "Browser-facing configuration sanitization now has a pure package boundary, while dashboard.py only adds runtime network and update state.",
        "Release package assertions require the configuration and integrations modules in both development and main publication workflows."
    ],
    "validation": [
        "Added configuration tests covering default-file creation, legacy setup/network migration, legacy users/integrations/update-source migration, save-time retired-field cleanup, and browser secret redaction.",
        "Added integration tests covering configured-secret preservation, URL validation, immutable CRUD transforms, and provider catalog metadata.",
        "Reusable source validation rejects configuration or integration ownership drifting back into dashboard.py and continues enforcing package dependency direction.",
        "Existing UI regression, frontend build-generation, release metadata, and configuration concurrency checks remain in the publication pipeline."
    ],
    "known_issues": [
        "dashboard.py and static/app.js remain larger than the intended steady-state architecture; release/update metadata and qBitTorrent transport are the next high-value backend extraction boundaries.",
        "ConfigStore still coordinates only the running process; simultaneous edits by an external config.json editor are not cross-process locked."
    ],
    "architecture": [
        "dashboard.py is the composition root and HTTP adapter; configuration schema/persistence and integration definitions are no longer implemented there.",
        "User and account domain logic lives in torrent_dashboard/users.py.",
        "Configuration defaults, migrations, browser sanitization, repository normalization, and atomic file persistence live in torrent_dashboard/config.py.",
        "Configuration transaction coordination remains in torrent_dashboard/config_store.py.",
        "Integration provider definitions, normalization, redaction, connection tests, and CRUD transforms live in torrent_dashboard/integrations.py.",
        "Runtime LAN detection is injected into ConfigRepository instead of reversing dependency direction back to dashboard.py.",
        "Release/update provenance is still implemented in dashboard.py and is the next planned backend extraction.",
        "Reusable source validation lives in release_tools/validate_source.py and enforces the package-to-composition-root dependency boundary."
    ],
    "decisions": [
        "Continue modularization in behavior-preserving increments rather than combining refactors with unrelated feature changes.",
        "Treat dashboard.py as the composition root; modules under torrent_dashboard must not import dashboard.py.",
        "Keep ConfigStore focused on transaction coordination and ConfigRepository focused on configuration file lifecycle.",
        "Inject runtime-only dependencies such as LAN detection into package modules rather than importing the HTTP/process adapter.",
        "Keep integration provider configuration separate from notification delivery so those responsibilities can evolve independently.",
        "Preserve the existing route-level helper call surface during extraction to minimize refactor blast radius."
    ],
    "next_steps": [
        {
            "priority": 1,
            "title": "Extract release and update provenance",
            "detail": "Move GitHub release parsing, installed release metadata, package-integrity normalization, and historical digest caching out of dashboard.py behind a cohesive package module."
        },
        {
            "priority": 2,
            "title": "Extract qBitTorrent transport and normalization",
            "detail": "Move QBitClient, qBitTorrent server normalization, proxy/preference translation, and Web API transport away from HTTP routing while keeping the route contract unchanged."
        },
        {
            "priority": 3,
            "title": "Expand request-level behavioral tests",
            "detail": "Add authorization, CSRF, setup, account-route, and settings-mutation coverage around the extracted service boundaries."
        },
        {
            "priority": 4,
            "title": "Harden secrets at rest",
            "detail": "Use the new configuration ownership boundary to add restrictive filesystem permissions and a cleaner separation between ordinary configuration and stored credentials."
        }
    ]
})
release_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

subprocess.run(
    [sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", NEW_VERSION],
    cwd=ROOT,
    check=True,
)

print("Applied v0.5.64 configuration/integrations composition switch")
