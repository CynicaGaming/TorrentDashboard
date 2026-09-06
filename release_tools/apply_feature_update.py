#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_FROM = "0.5.121"
VERSION_TO = "0.5.122"


def path(name: str) -> Path:
    return ROOT / name


def read(name: str) -> str:
    return path(name).read_text(encoding="utf-8")


def write(name: str, content: str) -> None:
    path(name).write_text(content, encoding="utf-8")


def replace_once(name: str, old: str, new: str) -> None:
    text = read(name)
    if old not in text:
        raise RuntimeError(f"Anchor not found in {name}: {old[:120]!r}")
    if text.count(old) != 1:
        raise RuntimeError(f"Anchor is not unique in {name}: {old[:120]!r}")
    write(name, text.replace(old, new, 1))


def append_once(name: str, marker: str, block: str) -> None:
    text = read(name)
    if marker in text:
        return
    if not text.endswith("\n"):
        text += "\n"
    write(name, text + "\n" + block.rstrip() + "\n")


JELLYFIN_MODULE = r'''"""Jellyfin service-integration runtime for status, libraries, and explicit refresh actions."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

MAX_JELLYFIN_RESPONSE_BYTES = 2_000_000
DEFAULT_JELLYFIN_TIMEOUT = 7


def find_jellyfin_integration(cfg, integration_id):
    """Return one saved Jellyfin integration without exposing any secret fields."""
    integration_id = str(integration_id or "").strip()
    if not integration_id:
        raise RuntimeError("Jellyfin integration ID is required")
    item = next(
        (
            entry
            for entry in cfg.get("integrations", [])
            if str(entry.get("id") or "") == integration_id
        ),
        None,
    )
    if not item:
        raise RuntimeError("Jellyfin integration was not found")
    if str(item.get("type") or "").lower() != "jellyfin":
        raise RuntimeError("Integration is not a Jellyfin connection")
    return item


def _jellyfin_connection(item):
    if str(item.get("type") or "").lower() != "jellyfin":
        raise RuntimeError("Integration is not a Jellyfin connection")
    url = str(item.get("url") or "").strip().rstrip("/")
    api_key = str(item.get("api_key") or "").strip()
    if not url.startswith(("http://", "https://")):
        raise RuntimeError("Jellyfin URL must start with http:// or https://")
    if not api_key:
        raise RuntimeError("Jellyfin API key is required")
    return url, api_key


def _jellyfin_request(item, endpoint, *, method="GET", expect_json=True, opener=None, timeout=DEFAULT_JELLYFIN_TIMEOUT):
    url, api_key = _jellyfin_connection(item)
    opener = opener or urllib.request.urlopen
    request = urllib.request.Request(
        url + endpoint,
        headers={
            "X-Emby-Token": api_key,
            "Accept": "application/json",
        },
        method=method,
    )
    try:
        with opener(request, timeout=timeout) as response:
            body = response.read(MAX_JELLYFIN_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Jellyfin returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not connect to Jellyfin: {exc.reason}") from exc
    except OSError as exc:
        raise RuntimeError(f"Could not connect to Jellyfin: {exc}") from exc
    if len(body) > MAX_JELLYFIN_RESPONSE_BYTES:
        raise RuntimeError("Jellyfin returned an unexpectedly large response")
    if not expect_json:
        return None
    try:
        return json.loads(body.decode("utf-8")) if body else {}
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Jellyfin returned an invalid response") from exc


def jellyfin_server_info(item, *, opener=None):
    """Return a browser-safe summary of the connected Jellyfin server."""
    data = _jellyfin_request(item, "/System/Info", opener=opener)
    if not isinstance(data, dict):
        raise RuntimeError("Jellyfin returned an invalid system response")
    return {
        "name": str(data.get("ServerName") or item.get("name") or "Jellyfin").strip(),
        "version": str(data.get("Version") or data.get("ProductVersion") or "").strip(),
        "operating_system": str(data.get("OperatingSystem") or "").strip(),
        "pending_restart": bool(data.get("HasPendingRestart", False)),
    }


def jellyfin_libraries(item, *, opener=None):
    """Return normalized Jellyfin virtual-folder/library information."""
    data = _jellyfin_request(item, "/Library/VirtualFolders", opener=opener)
    if not isinstance(data, list):
        raise RuntimeError("Jellyfin returned an invalid library response")
    libraries = []
    for source in data:
        if not isinstance(source, dict):
            continue
        raw_progress = source.get("RefreshProgress")
        try:
            progress = float(raw_progress) if raw_progress is not None else None
        except (TypeError, ValueError):
            progress = None
        if progress is not None:
            progress = max(0.0, min(100.0, progress))
        locations = [
            str(value).strip()
            for value in (source.get("Locations") or [])
            if str(value).strip()
        ]
        libraries.append({
            "id": str(source.get("ItemId") or "").strip(),
            "name": str(source.get("Name") or "Library").strip(),
            "collection_type": str(source.get("CollectionType") or "").strip(),
            "locations": locations,
            "refresh_status": str(source.get("RefreshStatus") or "").strip(),
            "refresh_progress": progress,
        })
    libraries.sort(key=lambda item: item["name"].lower())
    return libraries


def jellyfin_overview(item, *, opener=None):
    """Return server health metadata and configured libraries for Settings."""
    return {
        "ok": True,
        "server": jellyfin_server_info(item, opener=opener),
        "libraries": jellyfin_libraries(item, opener=opener),
    }


def refresh_jellyfin_libraries(item, *, opener=None):
    """Request Jellyfin's normal global library scan."""
    _jellyfin_request(item, "/Library/Refresh", method="POST", expect_json=False, opener=opener)
    return {"ok": True, "message": "Jellyfin library refresh requested"}


__all__ = [
    "find_jellyfin_integration",
    "jellyfin_libraries",
    "jellyfin_overview",
    "jellyfin_server_info",
    "refresh_jellyfin_libraries",
]
'''
write("torrent_dashboard/jellyfin.py", JELLYFIN_MODULE)

JELLYFIN_TESTS = r'''from __future__ import annotations

import json
import unittest

from torrent_dashboard.jellyfin import (
    find_jellyfin_integration,
    jellyfin_overview,
    refresh_jellyfin_libraries,
)


class FakeResponse:
    def __init__(self, payload=None):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, _limit=-1):
        if self.payload is None:
            return b""
        return json.dumps(self.payload).encode("utf-8")


class JellyfinIntegrationTests(unittest.TestCase):
    def item(self):
        return {
            "id": "jellyfin-1",
            "type": "jellyfin",
            "name": "Media server",
            "enabled": True,
            "url": "http://jellyfin:8096",
            "api_key": "secret-key",
        }

    def test_overview_fetches_server_and_virtual_folders(self):
        calls = []

        def opener(request, timeout=0):
            calls.append((request.full_url, request.get_method(), request.headers.get("X-emby-token"), timeout))
            if request.full_url.endswith("/System/Info"):
                return FakeResponse({
                    "ServerName": "Living Room Jellyfin",
                    "Version": "10.10.7",
                    "OperatingSystem": "Linux",
                    "HasPendingRestart": True,
                })
            if request.full_url.endswith("/Library/VirtualFolders"):
                return FakeResponse([
                    {
                        "Name": "Movies",
                        "CollectionType": "movies",
                        "Locations": ["/media/movies"],
                        "ItemId": "library-movies",
                        "RefreshStatus": "Running",
                        "RefreshProgress": 37.5,
                    },
                    {
                        "Name": "Shows",
                        "CollectionType": "tvshows",
                        "Locations": ["/media/tv", " /media/anime "],
                        "ItemId": "library-shows",
                    },
                ])
            raise AssertionError(request.full_url)

        overview = jellyfin_overview(self.item(), opener=opener)
        self.assertTrue(overview["ok"])
        self.assertEqual(overview["server"]["name"], "Living Room Jellyfin")
        self.assertEqual(overview["server"]["version"], "10.10.7")
        self.assertTrue(overview["server"]["pending_restart"])
        self.assertEqual([item["name"] for item in overview["libraries"]], ["Movies", "Shows"])
        self.assertEqual(overview["libraries"][0]["refresh_progress"], 37.5)
        self.assertEqual(overview["libraries"][1]["locations"], ["/media/tv", "/media/anime"])
        self.assertEqual([call[0].rsplit("/", 2)[-2:] for call in calls], [["System", "Info"], ["Library", "VirtualFolders"]])
        self.assertTrue(all(call[2] == "secret-key" for call in calls))

    def test_refresh_uses_global_library_scan_endpoint(self):
        calls = []

        def opener(request, timeout=0):
            calls.append((request.full_url, request.get_method(), request.headers.get("X-emby-token"), timeout))
            return FakeResponse()

        result = refresh_jellyfin_libraries(self.item(), opener=opener)
        self.assertTrue(result["ok"])
        self.assertEqual(calls[0][0], "http://jellyfin:8096/Library/Refresh")
        self.assertEqual(calls[0][1], "POST")
        self.assertEqual(calls[0][2], "secret-key")

    def test_saved_jellyfin_lookup_rejects_other_provider(self):
        cfg = {"integrations": [{"id": "sonarr-1", "type": "sonarr"}]}
        with self.assertRaisesRegex(RuntimeError, "not a Jellyfin"):
            find_jellyfin_integration(cfg, "sonarr-1")

    def test_saved_jellyfin_lookup_returns_full_server_side_configuration(self):
        item = self.item()
        found = find_jellyfin_integration({"integrations": [item]}, item["id"])
        self.assertIs(found, item)
        self.assertEqual(found["api_key"], "secret-key")


if __name__ == "__main__":
    unittest.main()
'''
write("tests/test_jellyfin.py", JELLYFIN_TESTS)

# Reuse the Jellyfin runtime transport for the existing connection test.
replace_once(
    "torrent_dashboard/integrations.py",
    "import uuid\n\n\nINTEGRATION_TYPES = {",
    "import uuid\n\nfrom .jellyfin import jellyfin_server_info\n\n\nINTEGRATION_TYPES = {",
)
replace_once(
    "torrent_dashboard/integrations.py",
    '''        elif provider == "jellyfin":\n            req = urllib.request.Request(\n                item["url"].rstrip("/") + "/System/Info",\n                headers={"X-Emby-Token": item["api_key"], "Accept": "application/json"},\n            )\n            with urllib.request.urlopen(req, timeout=7) as resp:\n                data = json.loads(resp.read(200000).decode("utf-8"))\n            version = str(data.get("Version") or data.get("ProductVersion") or "").strip()\n''',
    '''        elif provider == "jellyfin":\n            data = jellyfin_server_info(item)\n            version = str(data.get("version") or "").strip()\n''',
)

# Compose Jellyfin runtime operations in the HTTP adapter without moving provider logic into dashboard.py.
replace_once(
    "dashboard.py",
    '''    test_integration_connection,\n)\nfrom torrent_dashboard.users import (''',
    '''    test_integration_connection,\n)\nfrom torrent_dashboard.jellyfin import (\n    find_jellyfin_integration,\n    jellyfin_overview,\n    refresh_jellyfin_libraries,\n)\nfrom torrent_dashboard.users import (''',
)
replace_once(
    "dashboard.py",
    '''        if path in ("/api/settings","/api/integrations","/api/users","/api/network/interfaces","/api/client-settings","/api/torrent-metadata/save") and not session_is_admin(sess):''',
    '''        if path in ("/api/settings","/api/integrations","/api/integrations/jellyfin/status","/api/users","/api/network/interfaces","/api/client-settings","/api/torrent-metadata/save") and not session_is_admin(sess):''',
)
replace_once(
    "dashboard.py",
    '''        if path=="/api/integrations": return self.send_json(200,{"types":integration_catalog(),"integrations":redacted_integrations(cfg)},new_cookie)\n        if path=="/api/users":''',
    '''        if path=="/api/integrations": return self.send_json(200,{"types":integration_catalog(),"integrations":redacted_integrations(cfg)},new_cookie)\n        if path=="/api/integrations/jellyfin/status":\n            try:\n                item=find_jellyfin_integration(cfg,qs.get("id",[""])[0])\n                return self.send_json(200,jellyfin_overview(item),new_cookie)\n            except Exception as e:\n                return self.send_json(502,{"error":str(e)},new_cookie)\n        if path=="/api/users":''',
)
replace_once(
    "dashboard.py",
    '''            if path=="/api/integrations/delete":\n                data=parse_json_body(self,10000); iid=str(data.get("id") or ""); updated,_=mutate_config(lambda current: (delete_integration(current,iid),None))\n                HISTORY.event("dashboard","integration_deleted",iid,"",{"client_ip":self.client_ip()})\n                return self.send_json(200,{"ok":True},new_cookie)\n            if path=="/api/users":''',
    '''            if path=="/api/integrations/delete":\n                data=parse_json_body(self,10000); iid=str(data.get("id") or ""); updated,_=mutate_config(lambda current: (delete_integration(current,iid),None))\n                HISTORY.event("dashboard","integration_deleted",iid,"",{"client_ip":self.client_ip()})\n                return self.send_json(200,{"ok":True},new_cookie)\n            if path=="/api/integrations/jellyfin/refresh":\n                data=parse_json_body(self,10000); item=find_jellyfin_integration(cfg,data.get("id"))\n                try:\n                    result=refresh_jellyfin_libraries(item)\n                except Exception as exc:\n                    HISTORY.event("dashboard","jellyfin_library_refresh_failed",item.get("name","Jellyfin"),"",{"client_ip":self.client_ip(),"integration_id":item.get("id","")})\n                    return self.send_json(502,{"error":str(exc)},new_cookie)\n                HISTORY.event("dashboard","jellyfin_library_refresh_requested",item.get("name","Jellyfin"),"",{"client_ip":self.client_ip(),"integration_id":item.get("id","")})\n                return self.send_json(200,result,new_cookie)\n            if path=="/api/users":''',
)

# Add the service runtime UI to saved Jellyfin integration cards.
replace_once(
    "static/settings.js",
    '''  function integrationSubtitle(item, type) {\n    const label = type?.label || item.type || '';\n    const display = integrationLabel(item);\n    const parts = [];\n    if (label && display !== label) parts.push(label);\n    if (item._new) parts.push('Not saved');\n    return parts.join(' · ');\n  }\n\n  function renderIntegrations() {''',
    r'''  function integrationSubtitle(item, type) {
    const label = type?.label || item.type || '';
    const display = integrationLabel(item);
    const parts = [];
    if (label && display !== label) parts.push(label);
    if (item._new) parts.push('Not saved');
    return parts.join(' · ');
  }

  function jellyfinServiceMarkup(item) {
    if (item.type !== 'jellyfin' || !item.id || item._new) return '';
    return `<section class="integration-service jellyfin-service" data-jellyfin-service><div class="integration-service-head"><div class="integration-service-heading"><span class="eyebrow">Jellyfin server</span><div class="jellyfin-server-line"><span class="service-status-badge checking" data-jellyfin-status>Checking…</span><strong data-jellyfin-name>Jellyfin</strong></div><small data-jellyfin-meta>Loading server status…</small></div><button class="secondary jellyfin-reload" type="button">Reload status</button></div><div class="jellyfin-library-head"><div><strong>Libraries</strong><small data-jellyfin-library-count>Loading…</small></div><button class="secondary jellyfin-refresh-libraries" type="button">Refresh libraries</button></div><div class="jellyfin-library-list" data-jellyfin-libraries><div class="integration-service-empty">Loading libraries…</div></div></section>`;
  }

  function jellyfinLibraryType(value='') {
    const raw=String(value||'').toLowerCase();
    const labels={movies:'Movies',tvshows:'TV shows',music:'Music',books:'Books',photos:'Photos',musicvideos:'Music videos',homevideos:'Home videos',boxsets:'Collections',mixed:'Mixed content'};
    return labels[raw] || (raw ? uiText(raw) : 'Library');
  }

  function renderJellyfinOverview(card, data) {
    const server=data?.server||{}, libraries=Array.isArray(data?.libraries)?data.libraries:[];
    const status=card.querySelector('[data-jellyfin-status]');
    if(status){status.className='service-status-badge online';status.textContent=server.pending_restart?'Online · Restart pending':'Online'}
    const name=card.querySelector('[data-jellyfin-name]');if(name)name.textContent=server.name||'Jellyfin';
    const meta=card.querySelector('[data-jellyfin-meta]');
    if(meta){const parts=[];if(server.version)parts.push(`Jellyfin ${server.version}`);if(server.operating_system)parts.push(server.operating_system);meta.textContent=parts.join(' · ')||'Connected'}
    const count=card.querySelector('[data-jellyfin-library-count]');if(count)count.textContent=`${libraries.length} ${libraries.length===1?'library':'libraries'}`;
    const list=card.querySelector('[data-jellyfin-libraries]');if(!list)return;
    if(!libraries.length){list.innerHTML='<div class="integration-service-empty">No libraries reported</div>';return}
    list.innerHTML=libraries.map(library=>{
      const locations=(library.locations||[]).map(value=>String(value||'').trim()).filter(Boolean);
      const statusText=String(library.refresh_status||'').trim();
      const progress=Number(library.refresh_progress);
      const scan=Number.isFinite(progress)?`${Math.max(0,Math.min(100,progress)).toFixed(progress%1?1:0)}%${statusText?` · ${esc(uiText(statusText))}`:''}`:(statusText?esc(uiText(statusText)):'Idle');
      return `<article class="jellyfin-library-row"><div class="jellyfin-library-copy"><strong>${esc(library.name||'Library')}</strong><span>${esc(jellyfinLibraryType(library.collection_type))}</span></div><div class="jellyfin-library-paths">${locations.length?locations.map(value=>`<code>${esc(value)}</code>`).join(''):'<span>Location not reported</span>'}</div><div class="jellyfin-library-scan"><span>Scan</span><strong>${scan}</strong></div></article>`;
    }).join('');
  }

  async function loadJellyfinOverview(card) {
    if(!card?.dataset.id||card.dataset.type!=='jellyfin')return;
    const runtime=card.querySelector('[data-jellyfin-service]');if(!runtime||runtime.dataset.loading==='1')return;
    runtime.dataset.loading='1';
    const status=card.querySelector('[data-jellyfin-status]');if(status){status.className='service-status-badge checking';status.textContent='Checking…'}
    try{
      const data=await api(`/api/integrations/jellyfin/status?id=${encodeURIComponent(card.dataset.id)}`);
      runtime.dataset.loaded='1';renderJellyfinOverview(card,data);
    }catch(error){
      if(status){status.className='service-status-badge offline';status.textContent='Offline'}
      const meta=card.querySelector('[data-jellyfin-meta]');if(meta)meta.textContent=error.message||'Could not load Jellyfin status';
      const count=card.querySelector('[data-jellyfin-library-count]');if(count)count.textContent='Unavailable';
      const list=card.querySelector('[data-jellyfin-libraries]');if(list)list.innerHTML='<div class="integration-service-empty">Libraries unavailable</div>';
    }finally{delete runtime.dataset.loading}
  }

  async function refreshJellyfinLibraries(card) {
    if(!card?.dataset.id)return;
    const button=card.querySelector('.jellyfin-refresh-libraries');if(button)button.disabled=true;
    try{
      const result=await post('/api/integrations/jellyfin/refresh',{id:card.dataset.id});
      toast(result.message||'Jellyfin library refresh requested');
      await new Promise(resolve=>setTimeout(resolve,700));
      await loadJellyfinOverview(card);
    }catch(error){toast(error.message||'Could not refresh Jellyfin libraries','error')}
    finally{if(button)button.disabled=false}
  }

  function renderIntegrations() {''',
)
replace_once(
    "static/settings.js",
    '''      card.innerHTML = `<button class="accordion-summary" type="button" aria-expanded="${index===0?'true':'false'}"><span><b>${esc(integrationLabel(item))}</b>${subtitle?`<small>${esc(subtitle)}</small>`:''}</span><span class="accordion-chevron">⌄</span></button><div class="accordion-body ${index===0?'':'hidden'}"><div class="settings-form-grid"><label>Display name<input data-field="name" value="${esc(item.name||type.label)}" maxlength="128"></label>${fields}<label class="toggle"><input data-field="enabled" type="checkbox" ${item.enabled!==false?'checked':''}><span>Enabled</span></label></div><div class="settings-inline-actions"><button class="secondary integration-test" type="button">Test connection</button><button class="primary integration-save" type="button">Save</button><button class="danger integration-delete" type="button">Delete</button></div><div class="test-result muted integration-result">Not tested yet</div></div>`;''',
    '''      card.innerHTML = `<button class="accordion-summary" type="button" aria-expanded="${index===0?'true':'false'}"><span><b>${esc(integrationLabel(item))}</b>${subtitle?`<small>${esc(subtitle)}</small>`:''}</span><span class="accordion-chevron">⌄</span></button><div class="accordion-body ${index===0?'':'hidden'}"><div class="settings-form-grid"><label>Display name<input data-field="name" value="${esc(item.name||type.label)}" maxlength="128"></label>${fields}<label class="toggle"><input data-field="enabled" type="checkbox" ${item.enabled!==false?'checked':''}><span>Enabled</span></label></div><div class="settings-inline-actions"><button class="secondary integration-test" type="button">Test connection</button><button class="primary integration-save" type="button">Save</button><button class="danger integration-delete" type="button">Delete</button></div><div class="test-result muted integration-result">Not tested yet</div>${jellyfinServiceMarkup(item)}</div>`;''',
)
replace_once(
    "static/settings.js",
    '''      summary.addEventListener('click', () => {\n        const body = card.querySelector('.accordion-body');\n        const open = body.classList.contains('hidden');\n        body.classList.toggle('hidden', !open);\n        summary.setAttribute('aria-expanded', String(open));\n      });\n      card.querySelector('.integration-test').addEventListener('click', () => testIntegration(card));\n      card.querySelector('.integration-save').addEventListener('click', () => saveIntegration(card));\n      card.querySelector('.integration-delete').addEventListener('click', () => deleteIntegration(card, item));\n      list.appendChild(card);\n      decorateSecretFields(card);\n      applySentenceCaseUi(card);''',
    '''      summary.addEventListener('click', () => {\n        const body = card.querySelector('.accordion-body');\n        const open = body.classList.contains('hidden');\n        body.classList.toggle('hidden', !open);\n        summary.setAttribute('aria-expanded', String(open));\n        if(open&&card.dataset.type==='jellyfin'&&card.dataset.id)loadJellyfinOverview(card);\n      });\n      card.querySelector('.integration-test').addEventListener('click', () => testIntegration(card));\n      card.querySelector('.integration-save').addEventListener('click', () => saveIntegration(card));\n      card.querySelector('.integration-delete').addEventListener('click', () => deleteIntegration(card, item));\n      card.querySelector('.jellyfin-reload')?.addEventListener('click', () => loadJellyfinOverview(card));\n      card.querySelector('.jellyfin-refresh-libraries')?.addEventListener('click', () => refreshJellyfinLibraries(card));\n      list.appendChild(card);\n      decorateSecretFields(card);\n      applySentenceCaseUi(card);\n      if(index===0&&card.dataset.type==='jellyfin'&&card.dataset.id)setTimeout(()=>loadJellyfinOverview(card),0);''',
)

append_once(
    "static/settings.css",
    "/* 0.5.122 Jellyfin service integration runtime */",
    r'''/* 0.5.122 Jellyfin service integration runtime */
.integration-service{display:grid;gap:12px;margin-top:16px;padding-top:16px;border-top:1px solid var(--border)}
.integration-service-head,.jellyfin-library-head{display:flex;align-items:center;justify-content:space-between;gap:12px}
.integration-service-heading,.jellyfin-library-head>div{display:grid;gap:4px;min-width:0}
.integration-service-heading .eyebrow{font-size:9px;color:var(--muted);text-transform:none;letter-spacing:.02em}
.jellyfin-server-line{display:flex;align-items:center;gap:8px;min-width:0}.jellyfin-server-line strong{font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.integration-service-heading small,.jellyfin-library-head small{font-size:9px;color:var(--muted)}
.service-status-badge{display:inline-flex;align-items:center;min-height:22px;padding:3px 7px;border:1px solid var(--border);border-radius:999px;font-size:8.5px;white-space:nowrap}.service-status-badge.online{color:#72d6ad;border-color:color-mix(in srgb,#72d6ad 38%,var(--border));background:color-mix(in srgb,#72d6ad 8%,transparent)}.service-status-badge.offline{color:#ff7887;border-color:color-mix(in srgb,#ff7887 38%,var(--border));background:color-mix(in srgb,#ff7887 8%,transparent)}.service-status-badge.checking{color:var(--muted)}
.integration-service-head>button,.jellyfin-library-head>button{flex:0 0 auto;min-width:120px}.jellyfin-library-head{padding-top:2px}.jellyfin-library-head strong{font-size:12px}
.jellyfin-library-list{display:grid;gap:7px}.jellyfin-library-row{display:grid;grid-template-columns:minmax(150px,.8fr) minmax(220px,1.7fr) minmax(90px,.45fr);gap:12px;align-items:center;padding:10px 11px;border:1px solid var(--border);border-radius:11px;background:color-mix(in srgb,var(--panel2) 48%,transparent)}
.jellyfin-library-copy{display:grid;gap:3px;min-width:0}.jellyfin-library-copy strong{font-size:10.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.jellyfin-library-copy span,.jellyfin-library-paths span{font-size:8.5px;color:var(--muted)}.jellyfin-library-paths{display:grid;gap:3px;min-width:0}.jellyfin-library-paths code{display:block;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:var(--muted);font-size:8.5px;background:transparent;padding:0}.jellyfin-library-scan{display:grid;gap:3px;text-align:right}.jellyfin-library-scan span{font-size:8px;color:var(--muted)}.jellyfin-library-scan strong{font-size:9.5px;color:var(--text)}
.integration-service-empty{padding:14px;border:1px dashed var(--border);border-radius:10px;color:var(--muted);font-size:9px;text-align:center}
@media(max-width:700px){.integration-service-head,.jellyfin-library-head{align-items:flex-start;flex-wrap:wrap}.integration-service-head>button,.jellyfin-library-head>button{min-width:0}.jellyfin-library-row{grid-template-columns:1fr;gap:8px}.jellyfin-library-scan{text-align:left;grid-template-columns:auto 1fr;align-items:baseline;gap:6px}.jellyfin-library-paths code{white-space:normal;overflow-wrap:anywhere}}
''',
)

# Architecture and manual validation contract.
replace_once(
    "ARCHITECTURE.md",
    "### `torrent_dashboard/release_provenance.py`\n",
    "### `torrent_dashboard/jellyfin.py`\n\nOwns the Jellyfin service-integration runtime: authenticated server status, virtual-folder/library inventory normalization, and explicit global library refresh requests. Jellyfin API keys remain server-side; browser responses contain only normalized server/library metadata. `dashboard.py` only resolves authenticated HTTP routes and composes these operations.\n\n### `torrent_dashboard/release_provenance.py`\n",
)
append_once(
    "DESIGN_LANGUAGE.md",
    "## Jellyfin service integrations",
    '''## Jellyfin service integrations

A configured service integration should expose useful operational state in the same Settings accordion where it is configured instead of requiring a separate management destination. Jellyfin shows a compact server-health summary followed by its reported libraries. Library paths may wrap on narrow layouts, while server state, library names, collection types, and scan state remain visually distinct.

Connection testing and runtime service state are separate concepts: **Test connection** validates credentials/configuration, while the Jellyfin runtime panel shows current server/library state. Destructive or metadata-editing Jellyfin actions are outside this baseline; **Refresh libraries** is an explicit administrator action and must never be triggered merely by opening Settings or by torrent completion.
''',
)
append_once(
    "TESTING.md",
    "### Jellyfin service integration",
    '''### Jellyfin service integration

- Configure a Jellyfin integration with a valid URL/API key and verify Test connection reports the server version.
- Expand the saved Jellyfin integration and verify the runtime panel reports Online, the server name/version/operating system, and every configured library returned by Jellyfin.
- Verify each library shows its collection type, configured locations, and refresh status/progress when Jellyfin reports those fields. Long paths must wrap or ellipsize without horizontal overflow.
- Stop Jellyfin or use an unreachable URL and verify the runtime panel reports Offline/Libraries unavailable without exposing the API key or breaking the rest of Settings.
- Press Refresh libraries and verify Jellyfin starts a normal library scan; Torrent Dashboard must not alter library configuration or metadata options.
- Verify a successful refresh records a `jellyfin_library_refresh_requested` history event and a failed refresh records `jellyfin_library_refresh_failed`.
- Repeat at mobile width and verify the library records collapse to a single-column layout without obscuring Save/Delete/Test connection controls.
''',
)

# UI/source regression assertions for the new runtime surface.
replace_once(
    "release_tools/validate_ui_strings.py",
    '''    integrations_py = (ROOT / "torrent_dashboard" / "integrations.py").read_text(encoding="utf-8")\n    users_py = (ROOT / "torrent_dashboard" / "users.py").read_text(encoding="utf-8")''',
    '''    integrations_py = (ROOT / "torrent_dashboard" / "integrations.py").read_text(encoding="utf-8")\n    jellyfin_py = (ROOT / "torrent_dashboard" / "jellyfin.py").read_text(encoding="utf-8")\n    users_py = (ROOT / "torrent_dashboard" / "users.py").read_text(encoding="utf-8")''',
)
replace_once(
    "release_tools/validate_ui_strings.py",
    '''    print("UI string audit passed")''',
    '''    # 0.5.122 turns Jellyfin from connection-test scaffolding into a service integration.\n    assert '/api/integrations/jellyfin/status' in dashboard_py\n    assert '/api/integrations/jellyfin/refresh' in dashboard_py\n    assert 'find_jellyfin_integration' in dashboard_py and 'jellyfin_overview' in dashboard_py\n    assert 'def jellyfin_overview' in jellyfin_py and 'def refresh_jellyfin_libraries' in jellyfin_py\n    assert '/System/Info' in jellyfin_py and '/Library/VirtualFolders' in jellyfin_py and '/Library/Refresh' in jellyfin_py\n    assert 'function jellyfinServiceMarkup' in settings_js\n    assert 'function renderJellyfinOverview' in settings_js and 'function loadJellyfinOverview' in settings_js\n    assert 'function refreshJellyfinLibraries' in settings_js and 'Refresh libraries' in settings_js\n    assert '0.5.122 Jellyfin service integration runtime' in settings_css\n    assert '## Jellyfin service integrations' in design_language\n    assert '### Jellyfin service integration' in testing_md\n\n    print("UI string audit passed")''',
)

# Move the durable active objective to the service-integration track selected by the maintainer.
current = {
    "schema": 1,
    "status": "ready",
    "objective": "Validate and extend the Jellyfin service-integration runtime",
    "why": "Jellyfin is the first configured service integration to become operational rather than connection-test-only, providing a concrete provider pattern for future Sonarr, Radarr, Lidarr, and Prowlarr runtime features.",
    "acceptance_criteria": [
        "A saved Jellyfin integration can report server identity/health and configured libraries without exposing its API key to the browser.",
        "Administrators can explicitly request a normal Jellyfin library refresh from Settings and receive a clear success/failure result.",
        "Jellyfin network/API behavior lives under torrent_dashboard rather than growing dashboard.py with provider-specific transport logic.",
        "Automated tests characterize Jellyfin authentication, server/library normalization, and refresh request behavior.",
        "The next integration increment reuses the service-provider boundary instead of adding unrelated one-off HTTP logic."
    ],
    "decisions": [
        "Keep the first Jellyfin runtime read-mostly: server status and library inventory are read operations; library refresh is the only mutation.",
        "Do not trigger Jellyfin refresh automatically when a torrent completes because media managers may still need to import or move completed downloads.",
        "Keep Jellyfin credentials server-side and return only normalized, browser-safe service metadata.",
        "Use the existing Integrations Settings accordion as the operational surface rather than creating a second Jellyfin management destination."
    ],
    "files": [
        "torrent_dashboard/jellyfin.py",
        "torrent_dashboard/integrations.py",
        "dashboard.py",
        "static/settings.js",
        "static/settings.css",
        "tests/",
        "ARCHITECTURE.md",
        "TESTING.md"
    ],
    "blockers": [],
    "out_of_scope": [
        "Jellyfin library creation, deletion, path editing, or metadata-provider configuration.",
        "Automatic refresh on torrent completion.",
        "Jellyfin media-item browsing/playback management.",
        "Sonarr, Radarr, Lidarr, and Prowlarr runtime behavior in the same increment.",
        "Secret-at-rest changes."
    ],
    "next_action": "Validate v0.5.122 against a real Jellyfin server, then use the resulting service-integration pattern for the next selected provider rather than adding provider transport to dashboard.py."
}
write("development/current.json", json.dumps(current, indent=2) + "\n")

# Add structured release metadata while inheriting durable architecture/decision state.
release_path = path("release_notes/releases.json")
release_data = json.loads(release_path.read_text(encoding="utf-8"))
releases = release_data.get("releases") or []
if any(str(item.get("version")) == VERSION_TO for item in releases):
    raise RuntimeError(f"Release v{VERSION_TO} already exists")
latest = max(releases, key=lambda item: tuple(int(part) for part in str(item.get("version", "0.0.0")).split(".")[:3]))
new_decisions = list(latest.get("decisions") or [])
for decision in (
    "Treat Jellyfin as a service integration rather than connection-test-only scaffolding: expose server/library state and explicit administrator refresh actions in Settings.",
    "Keep Jellyfin API keys server-side; browser-visible service snapshots contain only normalized status and library metadata.",
    "Do not automatically refresh Jellyfin on torrent completion; explicit refresh remains the only Jellyfin mutation in the baseline runtime.",
):
    if decision not in new_decisions:
        new_decisions.append(decision)
new_architecture = list(latest.get("architecture") or [])
architecture_note = "`torrent_dashboard/jellyfin.py` owns Jellyfin HTTP/authentication, server/library normalization, and library refresh behavior; `dashboard.py` remains the HTTP composition adapter."
if architecture_note not in new_architecture:
    new_architecture.append(architecture_note)
new_release = {
    "version": VERSION_TO,
    "status": "prerelease",
    "title": "Jellyfin service integration",
    "summary": "Turns the Jellyfin integration into an operational service surface with live server status, configured library inventory, scan state, and an explicit library refresh action.",
    "highlights": [
        "Saved Jellyfin integrations now show whether the server is reachable plus its reported server name, version, operating system, and restart-pending state.",
        "The Integrations page lists Jellyfin virtual-folder libraries with collection type, media locations, and refresh status/progress when Jellyfin reports them.",
        "Administrators can request Jellyfin's normal global library scan with Refresh libraries without leaving Torrent Dashboard."
    ],
    "fixes": [
        "Jellyfin is no longer limited to save/delete/test-connection scaffolding; the configured service now provides useful runtime behavior."
    ],
    "technical": [
        "Adds `torrent_dashboard/jellyfin.py` as a standard-library-only provider boundary for authenticated Jellyfin requests and browser-safe normalization.",
        "Uses Jellyfin System/Info, Library/VirtualFolders, and Library/Refresh while retaining the existing X-Emby-Token API-key authentication model.",
        "Library refresh success/failure is recorded in durable Torrent Dashboard event history; credentials remain server-side."
    ],
    "validation": [
        "Unit tests cover authenticated server/library requests, normalized virtual-folder data, explicit POST library refresh behavior, and saved-integration lookup rules.",
        "The UI audit requires the Jellyfin status/refresh routes, runtime Settings renderer, responsive service styles, and provider module boundary.",
        "Existing backend tests, source/architecture validation, JavaScript syntax checks, generated-state consistency, and prerelease package-integrity gates remain required."
    ],
    "known_issues": [
        "CI uses a mocked Jellyfin transport; live server/version/library compatibility still requires smoke testing against the maintainer's Jellyfin installation."
    ],
    "architecture": new_architecture,
    "decisions": new_decisions,
    "next_steps": [
        {
            "priority": 1,
            "title": "Validate live Jellyfin behavior",
            "detail": "Confirm status, library inventory, responsive rendering, and explicit library refresh against a real Jellyfin server before expanding service integrations further."
        },
        {
            "priority": 2,
            "title": "Select the next service provider",
            "detail": "Reuse the Jellyfin provider boundary for the next Sonarr, Radarr, Lidarr, or Prowlarr runtime increment rather than growing provider transport in dashboard.py."
        }
    ]
}
releases.append(new_release)
release_data["releases"] = releases
release_path.write_text(json.dumps(release_data, indent=2) + "\n", encoding="utf-8")

# Synchronize application/frontend/service-worker versions.
for name in ("dashboard.py", "static/index.html", "static/app.js", "static/sw.js"):
    text = read(name)
    if VERSION_FROM not in text:
        raise RuntimeError(f"Expected {VERSION_FROM} in {name}")
    write(name, text.replace(VERSION_FROM, VERSION_TO))
sw = read("static/sw.js")
sw = sw.replace("torrent-dashboard-v05121", "torrent-dashboard-v05122")
write("static/sw.js", sw)

# Generate the authored release/handoff derivatives from their canonical sources.
subprocess.run(
    [sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", VERSION_TO],
    cwd=ROOT,
    check=True,
)
