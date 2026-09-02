#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET_VERSION = "0.5.50"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one {label} match, found {count}")
    return text.replace(old, new, 1)


def update_versions():
    dashboard = ROOT / "dashboard.py"
    text = dashboard.read_text(encoding="utf-8")
    text = replace_once(text, 'VERSION = "0.5.49"', f'VERSION = "{TARGET_VERSION}"', "dashboard version")
    dashboard.write_text(text, encoding="utf-8")

    index = ROOT / "static" / "index.html"
    text = index.read_text(encoding="utf-8")
    if text.count("0.5.49") < 4:
        raise RuntimeError("Expected v0.5.49 frontend references")
    text = text.replace("0.5.49", TARGET_VERSION)
    index.write_text(text, encoding="utf-8")

    app = ROOT / "static" / "app.js"
    text = app.read_text(encoding="utf-8")
    text = replace_once(text, "const FRONTEND_BUILD='0.5.49';", f"const FRONTEND_BUILD='{TARGET_VERSION}';", "frontend build")
    app.write_text(text, encoding="utf-8")

    sw = ROOT / "static" / "sw.js"
    text = sw.read_text(encoding="utf-8")
    text = replace_once(text, "torrent-dashboard-v0549", "torrent-dashboard-v0550", "service worker cache")
    if "v=0.5.49" not in text:
        raise RuntimeError("Expected v0.5.49 service worker assets")
    text = text.replace("v=0.5.49", f"v={TARGET_VERSION}")
    sw.write_text(text, encoding="utf-8")


def update_backend():
    path = ROOT / "dashboard.py"
    text = path.read_text(encoding="utf-8")

    post_marker = '''    def post(self, path, form=None):\n        return self._request("POST", path, form=form or {})\n\n'''
    metadata_methods = post_marker + '''    @staticmethod\n    def _torrent_metadata_json(body):\n        if not body:\n            return {}\n        try:\n            return json.loads(body.decode("utf-8"))\n        except (UnicodeDecodeError, json.JSONDecodeError) as exc:\n            raise RuntimeError("qBittorrent returned invalid torrent metadata") from exc\n\n    @staticmethod\n    def _metadata_api_error(exc):\n        message = str(exc)\n        if "qBittorrent HTTP 404" in message:\n            return RuntimeError("Torrent metadata preview requires qBittorrent Web API 2.11.9 or newer")\n        return RuntimeError(message)\n\n    def fetch_torrent_metadata(self, source, downloader=""):\n        source = str(source or "").strip()[:16000]\n        if not source:\n            raise RuntimeError("A magnet link or torrent URL is required")\n        form = {"source": source}\n        downloader = str(downloader or "").strip()[:256]\n        if downloader:\n            form["downloader"] = downloader\n        try:\n            status, body = self.post("/api/v2/torrents/fetchMetadata", form)\n        except RuntimeError as exc:\n            raise self._metadata_api_error(exc) from exc\n        return {\n            "qbit_status": int(status),\n            "complete": int(status) == 200,\n            "metadata": self._torrent_metadata_json(body),\n        }\n\n    def parse_torrent_metadata(self, filename, content):\n        if not content:\n            raise RuntimeError("No .torrent file supplied")\n        boundary = "----TorrentDashboardMetadata" + secrets.token_hex(12)\n        safe_name = Path(str(filename or "torrent.torrent")).name.replace('"', "")[:255] or "torrent.torrent"\n        raw = (\n            f"--{boundary}\\r\\nContent-Disposition: form-data; name=\\"torrents\\"; filename=\\"{safe_name}\\"\\r\\n"\n            "Content-Type: application/x-bittorrent\\r\\n\\r\\n"\n        ).encode() + content + f"\\r\\n--{boundary}--\\r\\n".encode()\n        try:\n            status, body = self._request(\n                "POST", "/api/v2/torrents/parseMetadata", raw=raw,\n                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}\n            )\n        except RuntimeError as exc:\n            raise self._metadata_api_error(exc) from exc\n        return {\n            "qbit_status": int(status),\n            "metadata": self._torrent_metadata_json(body),\n        }\n\n    def save_torrent_metadata(self, source):\n        source = str(source or "").strip()[:16000]\n        if not source:\n            raise RuntimeError("Torrent metadata source is required")\n        route = "/api/v2/torrents/saveMetadata?" + urllib.parse.urlencode({"source": source})\n        try:\n            status, body = self._request("GET", route, expect_json=False)\n        except RuntimeError as exc:\n            raise self._metadata_api_error(exc) from exc\n        if not body:\n            raise RuntimeError("qBittorrent returned an empty torrent metadata file")\n        return int(status), body\n\n'''
    text = replace_once(text, post_marker, metadata_methods, "qBitTorrent metadata methods")

    admin_get_marker = '''        if path in ("/api/settings","/api/integrations","/api/users","/api/network/interfaces","/api/client-settings") and not session_is_admin(sess):\n            return self.send_json(403,{"error":"Administrator access is required"},new_cookie)\n\n'''
    admin_get_new = '''        if path in ("/api/settings","/api/integrations","/api/users","/api/network/interfaces","/api/client-settings","/api/torrent-metadata/save") and not session_is_admin(sess):\n            return self.send_json(403,{"error":"Administrator access is required"},new_cookie)\n\n        if path=="/api/torrent-metadata/save":\n            sid=qs.get("server",["local"])[0]; source=qs.get("source",[""])[0]\n            try:\n                _,body=get_client(cfg,sid).save_torrent_metadata(source)\n                return self.send_bytes(200,body,"application/x-bittorrent",new_cookie,{"Content-Disposition":'attachment; filename="torrent.torrent"'})\n            except Exception as e:\n                return self.send_json(502,{"error":str(e)},new_cookie)\n\n'''
    text = replace_once(text, admin_get_marker, admin_get_new, "metadata export GET route")

    admin_post_marker = '''            if not session_is_admin(sess):\n                return self.send_json(403,{"error":"Administrator access is required"},new_cookie)\n            if path=="/api/client-settings":\n'''
    admin_post_new = '''            if not session_is_admin(sess):\n                return self.send_json(403,{"error":"Administrator access is required"},new_cookie)\n            if path=="/api/torrent-metadata/fetch":\n                data=parse_json_body(self,50000); sid=str(data.get("server") or "local")\n                result=get_client(cfg,sid).fetch_torrent_metadata(data.get("source"),data.get("downloader"))\n                return self.send_json(200,result,new_cookie)\n            if path=="/api/torrent-metadata/parse":\n                fields,files=parse_multipart(self)\n                sid=str(fields.get("server") or "local")\n                if not files:\n                    raise RuntimeError("No .torrent file supplied")\n                _,filename,content=files[0]\n                result=get_client(cfg,sid).parse_torrent_metadata(filename,content)\n                return self.send_json(200,result,new_cookie)\n            if path=="/api/client-settings":\n'''
    text = replace_once(text, admin_post_marker, admin_post_new, "metadata POST routes")
    path.write_text(text, encoding="utf-8")


def update_validator():
    path = ROOT / "release_tools" / "validate_ui_strings.py"
    text = path.read_text(encoding="utf-8")

    old_legacy = '''    # Add Torrent metadata is intentionally not part of 0.5.44.\n    assert "fetch_torrent_metadata" not in dashboard_py\n    assert "/api/torrent-metadata/fetch" not in dashboard_py\n    assert "Metadata retrieval complete" not in app_js\n'''
    new_legacy = '''    # Add Torrent metadata is implemented server-side in 0.5.50 but remains\n    # disconnected from the browser until the next controlled phase.\n    assert "Metadata retrieval complete" not in app_js\n'''
    text = replace_once(text, old_legacy, new_legacy, "retired metadata-absence validator")

    old_048 = '''    assert 'fetch_torrent_metadata' not in dashboard_py\n    assert '/api/torrent-metadata/fetch' not in dashboard_py\n    assert 'addMetadataState' not in app_js\n    assert 'Metadata retrieval complete' not in app_js\n'''
    new_048 = '''    assert 'addMetadataState' not in app_js\n    assert 'Metadata retrieval complete' not in app_js\n'''
    text = replace_once(text, old_048, new_048, "v0.5.48 metadata-absence validator")

    old_049 = '''    assert '0.5.49 Add Torrent advanced options' in app_css\n    assert 'fetch_torrent_metadata' not in dashboard_py\n    assert '/api/torrent-metadata/fetch' not in dashboard_py\n    assert 'addMetadataState' not in app_js\n'''
    new_049 = '''    assert '0.5.49 Add Torrent advanced options' in app_css\n    assert 'addMetadataState' not in app_js\n    # 0.5.50 metadata backend: explicit admin-only proxy routes exist, but no\n    # browser code is allowed to call them yet. This keeps polling out of runtime.\n    for method in ('fetch_torrent_metadata','parse_torrent_metadata','save_torrent_metadata'):\n        assert f'def {method}' in dashboard_py\n    for route in ('/api/torrent-metadata/fetch','/api/torrent-metadata/parse','/api/torrent-metadata/save'):\n        assert route in dashboard_py\n        assert route not in app_js\n    assert '/api/v2/torrents/fetchMetadata' in dashboard_py\n    assert '/api/v2/torrents/parseMetadata' in dashboard_py\n    assert '/api/v2/torrents/saveMetadata' in dashboard_py\n    assert 'qbit_status' in dashboard_py and 'complete' in dashboard_py\n    assert 'Torrent metadata preview requires qBittorrent Web API 2.11.9 or newer' in dashboard_py\n    assert 'Metadata retrieval complete' not in app_js\n'''
    text = replace_once(text, old_049, new_049, "v0.5.50 metadata backend validator")
    path.write_text(text, encoding="utf-8")


def main():
    update_versions()
    update_backend()
    update_validator()

    dashboard = (ROOT / "dashboard.py").read_text(encoding="utf-8")
    app = (ROOT / "static" / "app.js").read_text(encoding="utf-8")
    html = (ROOT / "static" / "index.html").read_text(encoding="utf-8")
    sw = (ROOT / "static" / "sw.js").read_text(encoding="utf-8")
    assert f'VERSION = "{TARGET_VERSION}"' in dashboard
    assert f'<meta content="{TARGET_VERSION}" name="torrent-dashboard-build"/>' in html
    assert f"const FRONTEND_BUILD='{TARGET_VERSION}';" in app
    assert all(route in dashboard and route not in app for route in ('/api/torrent-metadata/fetch','/api/torrent-metadata/parse','/api/torrent-metadata/save'))
    assert "event.request.mode==='navigate'" in sw
    print("Applied v0.5.50 backend-only qBitTorrent metadata support")


if __name__ == "__main__":
    main()
