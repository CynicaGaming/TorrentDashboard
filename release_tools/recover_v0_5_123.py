#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.122"
NEW = "0.5.123"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def version_bump() -> None:
    replacements = {
        "dashboard.py": [(f'VERSION = "{OLD}"', f'VERSION = "{NEW}"')],
        "static/app.js": [(f"const FRONTEND_BUILD='{OLD}';", f"const FRONTEND_BUILD='{NEW}';")],
        "static/index.html": [(OLD, NEW)],
        "static/sw.js": [("torrent-dashboard-v05122", "torrent-dashboard-v05123"), (OLD, NEW)],
    }
    for path, pairs in replacements.items():
        text = read(path)
        for old, new in pairs:
            if path in ("static/index.html", "static/sw.js") and old == OLD:
                if old not in text:
                    raise RuntimeError(f"{path}: missing {old}")
                text = text.replace(old, new)
            else:
                text = replace_once(text, old, new, path)
        write(path, text)


def patch_integrations_module() -> None:
    path = "torrent_dashboard/integrations.py"
    text = read(path)
    text = replace_once(text, "import json\nimport urllib.error", "import json\nimport socket\nimport time\nfrom concurrent.futures import ThreadPoolExecutor\nimport urllib.error", path)

    marker = "\n\ndef test_integration_connection(item):\n"
    if marker not in text:
        raise RuntimeError(f"{path}: test_integration_connection marker not found")
    block = r'''


def _integration_health(state, message):
    return {"state": state, "message": str(message or ""), "checked_at": int(time.time())}


def _integration_health_http_error(label, code, passive=False):
    code = int(code or 0)
    if passive and code in (405, 501):
        return _integration_health("healthy", f"{label} endpoint is reachable")
    if code == 404:
        return _integration_health("disconnected", f"{label} endpoint was not found")
    if code in (401, 403):
        return _integration_health("issue", f"{label} is reachable but authentication was rejected (HTTP {code})")
    return _integration_health("issue", f"{label} is reachable but returned HTTP {code}")


def _integration_json(url, headers=None):
    request_headers = {"Accept": "application/json", "User-Agent": "TorrentDashboard integration health"}
    request_headers.update(headers or {})
    request = urllib.request.Request(url, headers=request_headers)
    with urllib.request.urlopen(request, timeout=4) as response:
        return json.loads(response.read(200000).decode("utf-8"))


def _integration_passive_endpoint(url, label, headers=None):
    request_headers = {"User-Agent": "TorrentDashboard integration health"}
    request_headers.update(headers or {})
    request = urllib.request.Request(url, headers=request_headers, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=4) as response:
            response.read(1)
        return _integration_health("healthy", f"{label} endpoint is reachable")
    except urllib.error.HTTPError as exc:
        return _integration_health_http_error(label, exc.code, passive=True)
    except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        reason = getattr(exc, "reason", exc)
        return _integration_health("disconnected", f"Could not reach {label}: {reason}")


def probe_integration_health(item):
    item = normalize_integration(item, item)
    provider = item["type"]
    label = INTEGRATION_TYPES[provider]["label"]
    if not item.get("enabled", True):
        return _integration_health("disconnected", f"{label} integration is disabled")
    try:
        if provider in ("sonarr", "radarr", "lidarr", "prowlarr"):
            headers = {"X-Api-Key": item["api_key"]}
            status = _integration_json(item["url"].rstrip("/") + "/api/v3/system/status", headers)
            version = str(status.get("version") or "").strip()
            try:
                health = _integration_json(item["url"].rstrip("/") + "/api/v3/health", headers)
            except urllib.error.HTTPError as exc:
                return _integration_health("issue", f"{label}{(' ' + version) if version else ''} is connected, but its health endpoint returned HTTP {exc.code}")
            except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
                reason = getattr(exc, "reason", exc)
                return _integration_health("issue", f"{label}{(' ' + version) if version else ''} is connected, but its health check failed: {reason}")
            if isinstance(health, list) and health:
                messages = [
                    str(entry.get("message") or entry.get("source") or entry.get("type") or "Health warning").strip()
                    for entry in health if isinstance(entry, dict)
                ]
                detail = next((message for message in messages if message), "Health warning reported")
                extra = f" (+{len(health) - 1} more)" if len(health) > 1 else ""
                return _integration_health("issue", f"{label} connected · {detail}{extra}")
            return _integration_health("healthy", f"{label}{(' ' + version) if version else ''} connected")

        if provider == "jellyfin":
            server = jellyfin_server_info(item)
            version = str(server.get("version") or "").strip()
            if server.get("pending_restart"):
                return _integration_health("issue", f"Jellyfin{(' ' + version) if version else ''} connected · restart pending")
            return _integration_health("healthy", f"Jellyfin{(' ' + version) if version else ''} connected")

        if provider == "plex":
            request = urllib.request.Request(
                item["url"].rstrip("/") + "/identity",
                headers={"X-Plex-Token": item["token"], "User-Agent": "TorrentDashboard integration health"},
            )
            with urllib.request.urlopen(request, timeout=4) as response:
                response.read(200000)
            return _integration_health("healthy", "Plex connected")

        if provider == "discord":
            request = urllib.request.Request(
                item["webhook_url"],
                headers={"Accept": "application/json", "User-Agent": "TorrentDashboard integration health"},
            )
            with urllib.request.urlopen(request, timeout=4) as response:
                response.read(200000)
            return _integration_health("healthy", "Discord webhook connected")

        if provider == "ntfy":
            headers = {}
            if item.get("access_token"):
                headers["Authorization"] = f"Bearer {item['access_token']}"
            return _integration_passive_endpoint(item["topic_url"], "ntfy", headers)

        if provider == "generic_webhook":
            return _integration_passive_endpoint(item["webhook_url"], "Webhook")

        if provider == "home_assistant":
            return _integration_passive_endpoint(item["webhook_url"], "Home Assistant webhook")

        return _integration_health("issue", f"{label} health checking is not supported")
    except urllib.error.HTTPError as exc:
        return _integration_health_http_error(label, exc.code)
    except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        reason = getattr(exc, "reason", exc)
        return _integration_health("disconnected", f"Could not reach {label}: {reason}")
    except json.JSONDecodeError:
        return _integration_health("issue", f"{label} is connected but returned an invalid health response")
    except Exception as exc:
        return _integration_health("issue", f"{label} health check failed: {exc}")


def integration_health_statuses(cfg):
    integrations = list(cfg.get("integrations", []) or [])
    if not integrations:
        return []
    workers = max(1, min(6, len(integrations)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(probe_integration_health, item) for item in integrations]
        output = []
        for item, future in zip(integrations, futures):
            try:
                health = future.result()
            except Exception as exc:
                health = _integration_health("issue", f"Health check failed: {exc}")
            output.append({"id": str(item.get("id") or ""), "health": health})
        return output
'''
    text = text.replace(marker, block + marker, 1)
    text = replace_once(
        text,
        '    "integration_catalog",\n    "normalize_integration",',
        '    "integration_catalog",\n    "integration_health_statuses",\n    "normalize_integration",\n    "probe_integration_health",',
        path,
    )
    write(path, text)


def patch_dashboard() -> None:
    path = "dashboard.py"
    text = read(path)
    text = replace_once(
        text,
        "    integration_catalog,\n    normalize_integration,",
        "    integration_catalog,\n    integration_health_statuses,\n    normalize_integration,",
        path,
    )
    text = replace_once(
        text,
        'if path in ("/api/settings","/api/integrations","/api/integrations/jellyfin/status","/api/users","/api/network/interfaces","/api/client-settings","/api/torrent-metadata/save") and not session_is_admin(sess):',
        'if path in ("/api/settings","/api/integrations","/api/integration-health","/api/integrations/jellyfin/status","/api/users","/api/network/interfaces","/api/client-settings","/api/torrent-metadata/save") and not session_is_admin(sess):',
        path,
    )
    text = replace_once(
        text,
        '        if path=="/api/integrations": return self.send_json(200,{"types":integration_catalog(),"integrations":redacted_integrations(cfg)},new_cookie)\n',
        '        if path=="/api/integration-health": return self.send_json(200,{"integrations":integration_health_statuses(cfg)},new_cookie)\n        if path=="/api/integrations": return self.send_json(200,{"types":integration_catalog(),"integrations":redacted_integrations(cfg)},new_cookie)\n',
        path,
    )
    write(path, text)


def patch_settings_js() -> None:
    path = "static/settings.js"
    text = read(path)
    text = replace_once(text, "  let clientSettingsServerId = '';\n", "  let clientSettingsServerId = '';\n  let integrationHealthRefreshing = false;\n", path)
    text = replace_once(
        text,
        "    document.querySelector('#addUserSetting')?.addEventListener('click', addUser);\n    activate(localStorage.tdSettingsPage || 'general');",
        "    document.querySelector('#addUserSetting')?.addEventListener('click', addUser);\n    setInterval(() => {\n      const page = document.querySelector('[data-settings-section=\"integrations\"]');\n      if (page?.classList.contains('active')) refreshIntegrationHealth();\n    }, 30000);\n    activate(localStorage.tdSettingsPage || 'general');",
        path,
    )
    marker = "\n\n  function jellyfinServiceMarkup(item) {"
    if marker not in text:
        raise RuntimeError(f"{path}: Jellyfin marker not found")
    block = r'''

  function integrationHealthView(item) {
    if (item?._new) return {state:'disconnected',label:'Disconnected',message:'Save this integration before checking its connection.'};
    if (item?.enabled === false) return {state:'disconnected',label:'Disconnected',message:'Integration is disabled.'};
    const health = item?.health || {};
    const stateName = ['healthy','issue','disconnected'].includes(health.state) ? health.state : 'checking';
    const label = stateName === 'healthy' ? 'Connected and healthy' : stateName === 'issue' ? 'Connected with an issue' : stateName === 'disconnected' ? 'Disconnected' : 'Checking connection';
    return {state:stateName,label,message:health.message || label};
  }

  function applyIntegrationHealth() {
    document.querySelectorAll('.integration-item').forEach(card => {
      const item = integrations.find(entry => String(entry.id || '') === String(card.dataset.id || ''));
      const dot = card.querySelector('.integration-status');
      if (!item || !dot) return;
      const health = integrationHealthView(item);
      dot.className = `integration-status ${health.state}`;
      dot.setAttribute('aria-label', health.label);
      dot.title = health.message;
    });
  }

  async function refreshIntegrationHealth() {
    if (integrationHealthRefreshing || !state.me?.can_manage) return;
    const saved = integrations.filter(item => item.id && !item._new);
    if (!saved.length) return;
    integrationHealthRefreshing = true;
    try {
      const data = await api('/api/integration-health');
      const healthById = new Map((data.integrations || []).map(entry => [String(entry.id || ''), entry.health || {}]));
      integrations.forEach(item => {
        const health = healthById.get(String(item.id || ''));
        if (health) item.health = health;
      });
      applyIntegrationHealth();
    } catch (error) {
      integrations.forEach(item => {
        if (item.id && !item._new) item.health = {state:'disconnected',message:error.message || 'Could not refresh integration health.'};
      });
      applyIntegrationHealth();
    } finally {
      integrationHealthRefreshing = false;
    }
  }
'''
    text = text.replace(marker, block + marker, 1)
    old_summary = "card.innerHTML = `<button class=\"accordion-summary\" type=\"button\" aria-expanded=\"${index===0?'true':'false'}\"><span><b>${esc(integrationLabel(item))}</b>${subtitle?`<small>${esc(subtitle)}</small>`:''}</span><span class=\"accordion-chevron\">⌄</span></button>"
    new_summary = "const health = integrationHealthView(item);\n      card.innerHTML = `<button class=\"accordion-summary\" type=\"button\" aria-expanded=\"${index===0?'true':'false'}\"><span class=\"integration-summary-main\"><span class=\"integration-status ${health.state}\" role=\"img\" aria-label=\"${esc(health.label)}\" title=\"${esc(health.message)}\"></span><span class=\"integration-summary-copy\"><b>${esc(integrationLabel(item))}</b>${subtitle?`<small>${esc(subtitle)}</small>`:''}</span></span><span class=\"accordion-chevron\">⌄</span></button>"
    text = replace_once(text, old_summary, new_summary, path)
    text = replace_once(
        text,
        "      renderIntegrations();\n    } catch (e) {",
        "      renderIntegrations();\n      refreshIntegrationHealth();\n    } catch (e) {",
        path,
    )
    text = replace_once(
        text,
        "    } catch (e) {\n      out.className='test-result bad integration-result';\n      out.textContent=e.message;\n    }\n  }\n\n  async function saveIntegration(card)",
        "    } catch (e) {\n      out.className='test-result bad integration-result';\n      out.textContent=e.message;\n    } finally {\n      if (card.dataset.id) refreshIntegrationHealth();\n    }\n  }\n\n  async function saveIntegration(card)",
        path,
    )
    write(path, text)


def patch_settings_css() -> None:
    path = "static/settings.css"
    text = read(path)
    css = r'''

/* 0.5.123 integration health indicators. */
.integration-summary-main{display:flex!important;align-items:center;gap:10px;min-width:0;flex:1}
.integration-summary-copy{display:block;min-width:0;flex:1}
.integration-status{display:inline-block;flex:0 0 10px;width:10px;height:10px;border-radius:999px;background:var(--muted);box-shadow:0 0 0 3px color-mix(in srgb,currentColor 16%,transparent)}
.integration-status.healthy{color:var(--good);background:var(--good)}
.integration-status.issue{color:var(--warn);background:var(--warn)}
.integration-status.disconnected{color:var(--bad);background:var(--bad)}
.integration-status.checking{color:var(--muted);background:var(--muted);animation:integration-status-pulse 1.15s ease-in-out infinite alternate}
@keyframes integration-status-pulse{from{opacity:.42}to{opacity:1}}
@media(prefers-reduced-motion:reduce){.integration-status.checking{animation:none}}
'''
    if "0.5.123 integration health indicators" not in text:
        text = text.rstrip() + css + "\n"
    write(path, text)


def patch_tests() -> None:
    path = "tests/test_integrations.py"
    text = read(path)
    text = replace_once(text, "import unittest\n", "import unittest\nfrom unittest import mock\nimport urllib.error\n", path)
    text = replace_once(
        text,
        "    normalize_integration,\n    save_integration,",
        "    normalize_integration,\n    probe_integration_health,\n    save_integration,",
        path,
    )
    marker = "\n\nif __name__ == \"__main__\":\n"
    if marker not in text:
        raise RuntimeError(f"{path}: unittest marker missing")
    tests = r'''

    def test_health_marks_disabled_integration_disconnected(self):
        health = probe_integration_health({
            "type": "sonarr",
            "name": "Sonarr",
            "enabled": False,
            "url": "http://sonarr:8989",
            "api_key": "abc",
        })
        self.assertEqual(health["state"], "disconnected")

    def test_health_marks_reachable_auth_failure_as_issue(self):
        error = urllib.error.HTTPError("http://sonarr:8989", 401, "Unauthorized", {}, None)
        with mock.patch("torrent_dashboard.integrations.urllib.request.urlopen", side_effect=error):
            health = probe_integration_health({
                "type": "sonarr",
                "name": "Sonarr",
                "enabled": True,
                "url": "http://sonarr:8989",
                "api_key": "bad",
            })
        self.assertEqual(health["state"], "issue")
'''
    text = text.replace(marker, tests + marker, 1)
    write(path, text)


def patch_release_metadata() -> None:
    path = ROOT / "release_notes" / "releases.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    project = data.setdefault("project", {})
    project.pop("upstream_development_branch", None)
    project.pop("upstream_prerelease_branch", None)
    project.pop("upstream_pull_request", None)
    if any(str(item.get("version")) == NEW for item in data.get("releases", [])):
        raise RuntimeError(f"release metadata already contains {NEW}")
    release = {
        "version": NEW,
        "date": "2026-09-06",
        "status": "prerelease",
        "title": "Recovered release line and integration health indicators",
        "summary": "Restores the validated v0.5.122 development baseline as the canonical release line and adds at-a-glance integration health indicators without downgrading existing installations.",
        "highlights": [
            "Restores the complete modular v0.5.122 application baseline, including the operational Jellyfin service integration, as the source for subsequent releases.",
            "Adds a status indicator to the left of every saved integration name: green for healthy, yellow for reachable but degraded, and red for disconnected or disabled.",
            "Integration health refreshes automatically while the Integrations settings page is open and after manual connection tests."
        ],
        "fixes": [
            "Restores monotonic prerelease versioning so v0.5.122 installations correctly discover v0.5.123 instead of treating an older published build as current.",
            "Passive health checks do not send Discord, ntfy, Home Assistant, or generic webhook test notifications merely to determine status."
        ],
        "technical": [
            "Adds a browser-safe administrator-only /api/integration-health endpoint backed by concurrent provider probes in torrent_dashboard/integrations.py.",
            "Arr providers use their system and health endpoints; Jellyfin surfaces pending restart as degraded; reachable HTTP/auth/service errors are degraded while network failures and missing endpoints are disconnected.",
            "Removes stale refactor branch metadata from generated public handoff documents and keeps main as the canonical active branch."
        ],
        "validation": [
            "Existing source, UI-string, backend unit, JavaScript syntax, generated-state, and release package validation remain required.",
            "Integration tests cover disabled/disconnected classification and reachable authentication failures as degraded status.",
            "The updater-visible prerelease is verified after publication with the expected ZIP asset and GitHub SHA-256 digest."
        ],
        "known_issues": [
            "Webhook-style integrations can prove endpoint reachability passively, but some providers cannot expose deeper service health without sending a real event."
        ],
        "architecture": [
            "Integration configuration/normalization and passive provider health probing remain in torrent_dashboard/integrations.py; dashboard.py only exposes the authenticated HTTP route.",
            "Jellyfin operational status and library behavior remain owned by torrent_dashboard/jellyfin.py."
        ],
        "decisions": [
            "Keep prerelease versions monotonically increasing; rollback behavior must still advance the version rather than publishing an older semantic version.",
            "Keep main as the canonical active branch after recovery and avoid persistent development/prerelease branch clutter.",
            "Use passive health checks for notification/webhook providers so opening Settings never generates external test traffic."
        ],
        "next_steps": [
            {"priority": 1, "title": "Validate integration health against live services", "detail": "Confirm green/yellow/red classification against the maintainer's configured Arr, Jellyfin, Plex, and notification integrations."},
            {"priority": 2, "title": "Continue service integration work", "detail": "Reuse the modular provider boundary for the next selected Sonarr, Radarr, Lidarr, or Prowlarr operational integration."}
        ]
    }
    data["releases"].append(release)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    current_path = ROOT / "development" / "current.json"
    current = json.loads(current_path.read_text(encoding="utf-8"))
    current["status"] = "ready"
    current["objective"] = "Validate integration health and continue service-integration runtime work"
    current["why"] = "v0.5.123 restores the v0.5.122 modular baseline and adds passive integration health indicators; the next work should validate those states against real services before extending another provider runtime."
    current["acceptance_criteria"] = [
        "Green, yellow, and red integration states match live provider behavior without sending passive-test notifications.",
        "Jellyfin operational status and library refresh continue to work after the release-line recovery.",
        "The next provider runtime increment reuses torrent_dashboard provider boundaries rather than growing dashboard.py transport logic."
    ]
    current["next_action"] = "Smoke-test v0.5.123 against the maintainer's configured integrations, then select the next service provider for an operational runtime increment."
    current_path.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def replace_release_workflow() -> None:
    path = ROOT / ".github" / "workflows" / "release.yml"
    workflow = r'''name: Torrent Dashboard Pre-Release

on:
  push:
    branches:
      - main
  workflow_dispatch:

permissions:
  contents: write

concurrency:
  group: torrent-dashboard-prerelease
  cancel-in-progress: true

jobs:
  build-release:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v7
        with:
          fetch-depth: 0

      - name: Set Up Python
        uses: actions/setup-python@v7
        with:
          python-version: '3.13'

      - name: Validate Source
        shell: bash
        run: |
          python release_tools/validate_source.py
          python release_tools/validate_ui_strings.py
          python -m unittest discover -s tests -p 'test_*.py'
          node --check static/app.js
          node --check static/settings.js
          node - <<'JS'
          global.window = {};
          const fs = require('fs');
          eval(fs.readFileSync('static/settings.js','utf8'));
          if (!window.TDSettings || typeof window.TDSettings.bind !== 'function' || typeof window.TDSettings.fill !== 'function') {
            throw new Error('settings.js did not initialize window.TDSettings');
          }
          JS

      - name: Determine Version
        id: version
        shell: bash
        run: |
          VERSION=$(python - <<'PY'
          import re
          text=open('dashboard.py', encoding='utf-8').read()
          print(re.search(r'^VERSION\s*=\s*["\']([^"\']+)', text, re.M).group(1))
          PY
          )
          echo "version=$VERSION" >> "$GITHUB_OUTPUT"
          echo "tag=v$VERSION" >> "$GITHUB_OUTPUT"

      - name: Generate Release Notes
        shell: bash
        run: |
          python release_tools/generate_release_notes.py \
            --version "${{ steps.version.outputs.version }}" \
            --release-body dist/release-notes.md \
            --check

      - name: Build Release Package
        env:
          REPO: ${{ github.repository }}
          TAG: ${{ steps.version.outputs.tag }}
        shell: bash
        run: |
          python release_tools/build_release.py --repo "$REPO" --tag "$TAG" --output dist
          ZIP="dist/Torrent-Dashboard-${{ steps.version.outputs.version }}.zip"
          INFO="dist/Torrent-Dashboard-${{ steps.version.outputs.version }}.release.json"
          test -f "$ZIP"
          test -f "$INFO"
          python - <<'PY'
          import hashlib
          import json
          import zipfile
          from pathlib import Path
          version='${{ steps.version.outputs.version }}'
          path=Path('dist') / f'Torrent-Dashboard-{version}.zip'
          info_path=Path('dist') / f'Torrent-Dashboard-{version}.release.json'
          with zipfile.ZipFile(path) as z:
              names=[n for n in z.namelist() if not n.endswith('/')]
          required=(
              '/dashboard.py','/updater.py','/torrent_dashboard/__init__.py','/torrent_dashboard/users.py',
              '/torrent_dashboard/config_store.py','/torrent_dashboard/config.py','/torrent_dashboard/integrations.py',
              '/torrent_dashboard/jellyfin.py','/torrent_dashboard/release_provenance.py','/ARCHITECTURE.md',
              '/PROJECT_STATE.md','/CHANGELOG.md','/release_notes/releases.json','/static/index.html',
              '/static/app.js','/static/settings.js','/static/settings.css',
          )
          for suffix in required:
              assert any(n.endswith(suffix) for n in names), suffix
          assert not any(n.endswith('recover_v0_5_123.py') for n in names)
          info=json.loads(info_path.read_text(encoding='utf-8'))
          digest=hashlib.sha256(path.read_bytes()).hexdigest()
          assert info['version'] == version
          assert info['package'] == path.name
          assert info['sha256'] == digest
          PY

      - name: Publish Or Refresh GitHub Pre-Release
        env:
          GH_TOKEN: ${{ github.token }}
          TAG: ${{ steps.version.outputs.tag }}
        shell: bash
        run: |
          set -euo pipefail
          ZIP="dist/Torrent-Dashboard-${{ steps.version.outputs.version }}.zip"
          INFO="dist/Torrent-Dashboard-${{ steps.version.outputs.version }}.release.json"
          if gh release view "$TAG" >/dev/null 2>&1; then
            gh release upload "$TAG" "$ZIP" "$INFO" --clobber
            gh release edit "$TAG" \
              --target "$GITHUB_SHA" \
              --title "Torrent Dashboard $TAG Pre-Release" \
              --notes-file dist/release-notes.md \
              --prerelease
          else
            gh release create "$TAG" \
              "$ZIP" "$INFO" \
              --target "$GITHUB_SHA" \
              --title "Torrent Dashboard $TAG Pre-Release" \
              --notes-file dist/release-notes.md \
              --prerelease
          fi

      - name: Remove Superseded Pre-Releases
        env:
          GH_TOKEN: ${{ github.token }}
          TAG: ${{ steps.version.outputs.tag }}
        shell: bash
        run: |
          set -euo pipefail
          for old_tag in $(gh api "repos/${{ github.repository }}/releases?per_page=100" --jq '.[] | select(.prerelease == true) | .tag_name'); do
            if [ "$old_tag" != "$TAG" ]; then
              gh release delete "$old_tag" --cleanup-tag --yes
            fi
          done

      - name: Verify Updater-Visible Pre-Release
        env:
          GH_TOKEN: ${{ github.token }}
          TAG: ${{ steps.version.outputs.tag }}
        shell: bash
        run: |
          set -euo pipefail
          gh api "repos/${{ github.repository }}/releases/tags/$TAG" --jq '
            select(.draft == false)
            | select(.prerelease == true)
            | select(.tag_name == env.TAG)
            | .assets[]
            | select(.name == "Torrent-Dashboard-${{ steps.version.outputs.version }}.zip")
            | select(.digest | startswith("sha256:"))
            | .id
          ' | grep -Eq '^[0-9]+$'
'''
    path.write_text(workflow, encoding="utf-8")


def cleanup_stale_refactor_files() -> None:
    for relative in (
        ".github/refactor-prerelease-trigger",
        ".github/workflows/apply-refactor-branch.yml",
        ".github/workflows/publish-refactor-prerelease.yml",
    ):
        path = ROOT / relative
        if path.exists():
            path.unlink()


def main() -> None:
    version_bump()
    patch_integrations_module()
    patch_dashboard()
    patch_settings_js()
    patch_settings_css()
    patch_tests()
    patch_release_metadata()
    replace_release_workflow()
    cleanup_stale_refactor_files()
    import subprocess
    subprocess.run(["python", "release_tools/generate_release_notes.py", "--version", NEW], cwd=ROOT, check=True)
    for relative in ("release_tools/recover_v0_5_123.py", ".github/workflows/recover-v0.5.123.yml"):
        path = ROOT / relative
        if path.exists():
            path.unlink()
    print(f"Recovered validated release line as v{NEW}")


if __name__ == "__main__":
    main()
