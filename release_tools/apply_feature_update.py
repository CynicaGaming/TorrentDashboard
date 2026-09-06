#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD_VERSION = "0.5.54"
NEW_VERSION = "0.5.55"


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def write(path, text):
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text, old, new, label):
    if old not in text:
        raise RuntimeError(f"Could not find {label}")
    return text.replace(old, new, 1)


# Backend: expose passive, side-effect-free integration health probes.
dashboard = read("dashboard.py")
dashboard = replace_once(
    dashboard,
    "from collections import defaultdict, deque\n",
    "from collections import defaultdict, deque\nfrom concurrent.futures import ThreadPoolExecutor\n",
    "dashboard concurrent futures import",
)

health_code = r'''

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
    if 500 <= code <= 599:
        return _integration_health("issue", f"{label} is reachable but returned HTTP {code}")
    return _integration_health("issue", f"{label} is reachable but returned HTTP {code}")


def _integration_json(url, headers=None):
    request_headers = {"Accept": "application/json", "User-Agent": f"TorrentDashboard/{VERSION}"}
    request_headers.update(headers or {})
    req = urllib.request.Request(url, headers=request_headers)
    with urllib.request.urlopen(req, timeout=4) as resp:
        return json.loads(resp.read(200000).decode("utf-8"))


def _integration_passive_endpoint(url, label, headers=None):
    request_headers = {"User-Agent": f"TorrentDashboard/{VERSION}"}
    request_headers.update(headers or {})
    req = urllib.request.Request(url, headers=request_headers, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            resp.read(1)
        return _integration_health("healthy", f"{label} endpoint is reachable")
    except urllib.error.HTTPError as exc:
        return _integration_health_http_error(label, exc.code, passive=True)
    except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        reason = getattr(exc, "reason", exc)
        return _integration_health("disconnected", f"Could not reach {label}: {reason}")


def probe_integration_health(item):
    item = normalize_integration(item, item)
    provider = item["type"]
    spec = INTEGRATION_TYPES[provider]
    label = spec["label"]
    if not item.get("enabled", True):
        return _integration_health("disconnected", f"{label} integration is disabled")
    try:
        if provider in ("sonarr", "radarr", "lidarr", "prowlarr"):
            headers = {"X-Api-Key": item["api_key"]}
            data = _integration_json(item["url"].rstrip("/") + "/api/v3/system/status", headers)
            version = str(data.get("version") or "").strip()
            try:
                health = _integration_json(item["url"].rstrip("/") + "/api/v3/health", headers)
            except urllib.error.HTTPError as exc:
                return _integration_health("issue", f"{label}{(' ' + version) if version else ''} is connected, but its health endpoint returned HTTP {exc.code}")
            except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
                reason = getattr(exc, "reason", exc)
                return _integration_health("issue", f"{label}{(' ' + version) if version else ''} is connected, but its health check failed: {reason}")
            if isinstance(health, list) and health:
                messages = [str(entry.get("message") or entry.get("source") or entry.get("type") or "Health warning").strip() for entry in health if isinstance(entry, dict)]
                detail = next((message for message in messages if message), "Health warning reported")
                extra = f" (+{len(health)-1} more)" if len(health) > 1 else ""
                return _integration_health("issue", f"{label} connected · {detail}{extra}")
            return _integration_health("healthy", f"{label}{(' ' + version) if version else ''} connected")

        if provider == "jellyfin":
            data = _integration_json(item["url"].rstrip("/") + "/System/Info", {"X-Emby-Token": item["api_key"]})
            version = str(data.get("Version") or data.get("ProductVersion") or "").strip()
            if bool(data.get("HasPendingRestart")):
                return _integration_health("issue", f"Jellyfin{(' ' + version) if version else ''} connected · restart pending")
            return _integration_health("healthy", f"Jellyfin{(' ' + version) if version else ''} connected")

        if provider == "plex":
            req = urllib.request.Request(
                item["url"].rstrip("/") + "/identity",
                headers={"X-Plex-Token": item["token"], "User-Agent": f"TorrentDashboard/{VERSION}"},
            )
            with urllib.request.urlopen(req, timeout=4) as resp:
                resp.read(200000)
            return _integration_health("healthy", "Plex connected")

        if provider == "discord":
            req = urllib.request.Request(item["webhook_url"], headers={"Accept": "application/json", "User-Agent": f"TorrentDashboard/{VERSION}"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                resp.read(200000)
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

dashboard = replace_once(
    dashboard,
    "\n\ndef test_integration_connection(item):",
    health_code + "\n\ndef test_integration_connection(item):",
    "integration test function marker",
)
dashboard = replace_once(
    dashboard,
    '"/api/integrations","/api/users"',
    '"/api/integrations","/api/integration-health","/api/users"',
    "integration health admin route",
)
dashboard = replace_once(
    dashboard,
    '        if path=="/api/integrations": return self.send_json(200,{"types":integration_catalog(),"integrations":redacted_integrations(cfg)},new_cookie)\n',
    '        if path=="/api/integration-health": return self.send_json(200,{"integrations":integration_health_statuses(cfg)},new_cookie)\n        if path=="/api/integrations": return self.send_json(200,{"types":integration_catalog(),"integrations":redacted_integrations(cfg)},new_cookie)\n',
    "integration GET route",
)
dashboard = replace_once(dashboard, f'VERSION = "{OLD_VERSION}"', f'VERSION = "{NEW_VERSION}"', "dashboard version")
write("dashboard.py", dashboard)


# Frontend: add the status dot immediately to the left of the integration name,
# refresh it passively while the Integrations page is open, and keep editing
# state intact by updating only the dot rather than re-rendering the forms.
settings = read("static/settings.js")
settings = replace_once(
    settings,
    "  let clientSettingsServerId = '';\n",
    "  let clientSettingsServerId = '';\n  let integrationHealthRefreshing = false;\n",
    "integration health refresh state",
)
settings = replace_once(
    settings,
    "    if (savebar) savebar.classList.toggle('hidden', !corePages.has(page));\n",
    "    if (savebar) savebar.classList.toggle('hidden', !corePages.has(page));\n    if (page === 'integrations' && integrations.some(item => item.id && !item._new)) refreshIntegrationHealth();\n",
    "integration activation refresh",
)
settings = replace_once(
    settings,
    "    document.querySelector('#addUserSetting')?.addEventListener('click', addUser);\n    activate(localStorage.tdSettingsPage || 'general');\n",
    "    document.querySelector('#addUserSetting')?.addEventListener('click', addUser);\n    window.setInterval(() => {\n      const page = document.querySelector('.settings-page.active')?.dataset.settingsSection || '';\n      if (page === 'integrations' && integrations.some(item => item.id && !item._new)) refreshIntegrationHealth();\n    }, 30000);\n    activate(localStorage.tdSettingsPage || 'general');\n",
    "integration health interval",
)

frontend_health = r'''

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
settings = replace_once(
    settings,
    "\n  function renderIntegrations() {",
    frontend_health + "\n  function renderIntegrations() {",
    "integration renderer marker",
)
settings = replace_once(
    settings,
    "      const subtitle = integrationSubtitle(item, type);\n",
    "      const subtitle = integrationSubtitle(item, type);\n      const health = integrationHealthView(item);\n",
    "integration health view",
)
settings = replace_once(
    settings,
    '<span><b>${esc(integrationLabel(item))}</b>',
    '<span class="integration-summary-main"><span class="integration-status ${health.state}" role="img" aria-label="${esc(health.label)}" title="${esc(health.message)}"></span><span class="integration-summary-copy"><b>${esc(integrationLabel(item))}</b>',
    "integration summary status start",
)
settings = replace_once(
    settings,
    '</span><span class="accordion-chevron">⌄</span></button><div class="accordion-body ${index===0?\'\':\'hidden\'}">',
    '</span></span><span class="accordion-chevron">⌄</span></button><div class="accordion-body ${index===0?\'\':\'hidden\'}">',
    "integration summary status end",
)
settings = replace_once(
    settings,
    "      renderIntegrations();\n    } catch (e) {\n      toast(e.message,'error');\n    }\n  }\n\n  function addIntegration()",
    "      renderIntegrations();\n      refreshIntegrationHealth();\n    } catch (e) {\n      toast(e.message,'error');\n    }\n  }\n\n  function addIntegration()",
    "integration initial health refresh",
)
settings = replace_once(
    settings,
    "    } catch (e) {\n      out.className='test-result bad integration-result';\n      out.textContent=e.message;\n    }\n  }\n\n  async function saveIntegration(card)",
    "    } catch (e) {\n      out.className='test-result bad integration-result';\n      out.textContent=e.message;\n    } finally {\n      if (card.dataset.id) refreshIntegrationHealth();\n    }\n  }\n\n  async function saveIntegration(card)",
    "integration test health refresh",
)
write("static/settings.js", settings)


css = read("static/settings.css")
css += r'''

/* 0.5.55 integration connection health indicators. */
.integration-summary-main{display:flex!important;align-items:center;gap:10px;min-width:0;flex:1}
.integration-summary-copy{display:block;min-width:0;flex:1}
.integration-status{display:block;flex:0 0 auto;width:10px;height:10px;border-radius:999px;background:var(--muted);box-shadow:0 0 0 4px color-mix(in srgb,var(--muted) 12%,transparent);transition:background .16s ease,box-shadow .16s ease,opacity .16s ease}
.integration-status.healthy{background:var(--good);box-shadow:0 0 0 4px color-mix(in srgb,var(--good) 14%,transparent)}
.integration-status.issue{background:var(--warn);box-shadow:0 0 0 4px color-mix(in srgb,var(--warn) 15%,transparent)}
.integration-status.disconnected{background:var(--bad);box-shadow:0 0 0 4px color-mix(in srgb,var(--bad) 14%,transparent)}
.integration-status.checking{background:var(--muted);animation:integration-status-pulse 1.2s ease-in-out infinite}
@keyframes integration-status-pulse{50%{opacity:.42}}
@media(max-width:560px){.integration-summary-main{gap:9px}.integration-status{width:9px;height:9px}}
'''
write("static/settings.css", css)


# Keep the browser/service-worker cache contract synchronized with the release.
for path in ("static/app.js", "static/index.html", "static/sw.js"):
    text = read(path)
    if OLD_VERSION not in text:
        raise RuntimeError(f"Could not find {OLD_VERSION} in {path}")
    write(path, text.replace(OLD_VERSION, NEW_VERSION))

print(f"Applied integration health indicators for {NEW_VERSION}")
