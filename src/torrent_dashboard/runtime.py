"""Torrent Dashboard process adapter with reliability and operations services.

The historical dashboard module remains the HTTP composition root. This adapter
installs narrowly scoped operational extensions before starting it: updater-ready
release selection, encrypted portable backups, maintenance scheduling, retention,
security-audit APIs, and the consolidated system-health surface.
"""
from __future__ import annotations

from datetime import datetime
import logging
import threading
import time
from types import SimpleNamespace
import urllib.parse

from torrent_dashboard import backup_service
from torrent_dashboard import dashboard as core
from torrent_dashboard.ops_config import apply_operations_update, public_operations_config
from torrent_dashboard.operations import (
    MaintenanceStateStore,
    automatic_update_due,
    build_system_health,
    retention_due,
    run_retention,
    scheduled_backup_due,
)
from torrent_dashboard.release_selection import select_updater_ready_release

STARTED_AT = time.time()
MAINTENANCE_STATE = MaintenanceStateStore(core.DATA_DIR / "maintenance-state.json")
_ORIGINAL_APPLY_SETTINGS_UPDATE = core.apply_settings_update
_ORIGINAL_REDACTED_CONFIG = core.redacted_config
_ORIGINAL_HANDLER = core.Handler
_ORIGINAL_SERVER = core.ThreadingHTTPServer


def _backup_password(config: dict) -> str:
    return backup_service.configured_backup_password(config)


def _create_backup(app_dir, version, config, *, kind="manual", history_lock=None):
    return backup_service.create_backup(
        app_dir, version, config, kind=kind, history_lock=history_lock,
        password=_backup_password(config),
    )


def _list_backups(app_dir):
    try:
        password = _backup_password(core.load_config())
    except Exception:
        password = ""
    return backup_service.list_backups(app_dir, password=password)


def _import_backup(app_dir, filename, content, *, current_version=None):
    config = core.load_config()
    password = _backup_password(config)
    return backup_service.import_backup(
        app_dir, filename, content, current_version=current_version or core.VERSION,
        source_password=password, storage_password=password,
    )


def _restore_backup(app_dir, name, *, current_version, current_config, validator=None, history_lock=None):
    return backup_service.restore_backup(
        app_dir, name, current_version=current_version, current_config=current_config,
        validator=validator, history_lock=history_lock, password=_backup_password(current_config),
    )


def _apply_settings_update(config, data):
    updated = _ORIGINAL_APPLY_SETTINGS_UPDATE(config, data)
    return apply_operations_update(updated, data)


def _redacted_config(config):
    return public_operations_config(_ORIGINAL_REDACTED_CONFIG(config))


def _fetch_update_release(config):
    """Return the newest updater-ready release, skipping partially published releases."""
    repo = core.validate_update_repository(core.update_repository(config))
    releases = core._github_releases(config, repo)
    if not releases:
        raise RuntimeError("No GitHub release was found for the configured repository")
    distribution = core.runtime_distribution(core.APP_DIR)
    release = select_updater_ready_release(releases, distribution)
    if not release:
        raise RuntimeError("No updater-ready GitHub release contains the required package and SHA-256 digest")
    tag = str(release.get("tag_name") or "").strip()
    version = tag.lstrip("vV")
    asset = core._find_dashboard_asset(release, distribution)
    api_url = str(asset.get("url") or "")
    if not api_url.startswith("https://api.github.com/"):
        raise RuntimeError("GitHub release asset URL is invalid")
    integrity_history = core._github_release_integrity(releases, 20, distribution)
    data = {
        "version": version,
        "channel": "prerelease" if release.get("prerelease") else "stable",
        "publishedAt": str(release.get("published_at") or release.get("created_at") or ""),
        "releaseUrl": str(release.get("html_url") or ""),
        "notes": str(release.get("body") or ""),
        "title": str(release.get("name") or f"Torrent Dashboard v{version}"),
        "asset": {
            "name": str(asset.get("name") or f"Torrent-Dashboard-{version}.zip"),
            "githubApiUrl": api_url,
            "url": str(asset.get("browser_download_url") or ""),
            "sha256": core._asset_sha256(asset),
            "size": int(asset.get("size") or 0),
        },
        "currentVersion": core.VERSION,
        "releaseHistory": integrity_history[:2],
    }
    try:
        core.write_release_integrity_cache(integrity_history)
    except Exception:
        pass
    data["updateAvailable"] = core.is_newer_version(version)
    if version == core.VERSION and not core.installed_release_info():
        try:
            core.write_release_info(
                core.RELEASE_INFO_PATH,
                core._release_info_payload(
                    version, data["asset"]["name"], data["asset"]["sha256"], repo,
                    data.get("releaseUrl", ""), data.get("publishedAt", ""),
                    data.get("channel", ""), str(release.get("target_commitish") or ""),
                ),
            )
        except Exception:
            pass
    return data


def _client_health_rows(config: dict):
    rows = []
    with core.CACHE_LOCK:
        cache = {key: dict(value) for key, value in core.CACHE.items()}
    for server in config.get("servers", []):
        if not server.get("enabled", True):
            continue
        sid = str(server.get("id") or "")
        item = cache.get(sid) or {}
        rows.append({
            "id": sid,
            "name": str(server.get("name") or sid),
            "healthy": bool(item.get("ok")),
            "error": str(item.get("error") or ""),
            "checked_at": int(item.get("ts") or 0),
        })
    return rows


def _health_payload(config: dict):
    password = _backup_password(config)
    try:
        integrations = core.integration_health_statuses(config)
    except Exception as exc:
        integrations = [{"id": "integration-health", "health": {"state": "issue", "message": str(exc)}}]
    return build_system_health(
        app_dir=core.APP_DIR,
        version=core.VERSION,
        started_at=STARTED_AT,
        config=config,
        update_state=core.update_state(),
        maintenance_state=MAINTENANCE_STATE.load(),
        backups=backup_service.list_backups(core.APP_DIR, password=password),
        audit_summary=core.HISTORY.audit.summary(),
        client_rows=_client_health_rows(config),
        integration_rows=integrations,
    )


def _retention(config: dict):
    update = core.update_state()
    protected = {core.VERSION, str(update.get("version") or "")}
    result = run_retention(
        app_dir=core.APP_DIR,
        update_dir=core.UPDATE_DIR,
        history=core.HISTORY,
        audit=core.HISTORY.audit,
        policy=(config.get("maintenance") or {}).get("retention") or {},
        protected_update_versions=protected,
    )
    MAINTENANCE_STATE.update(last_retention_ts=int(time.time()), last_retention=result)
    return result


def _scheduled_backup(config: dict):
    with core.CONFIG_STORE.exclusive() as current:
        item = _create_backup(core.APP_DIR, core.VERSION, current, kind="scheduled", history_lock=core.HISTORY.lock)
    now = int(time.time())
    MAINTENANCE_STATE.update(last_backup_ts=now, last_backup_attempt_ts=now, last_backup_name=item.get("name", ""), last_backup_error="")
    core.HISTORY.event("dashboard", "backup_scheduled", item.get("name", ""), "", {"encrypted": bool(item.get("encrypted"))})
    return item


def _automatic_update(server, config: dict):
    auto = (config.get("maintenance") or {}).get("auto_update") or {}
    today = datetime.now().date().isoformat()
    MAINTENANCE_STATE.update(last_auto_update_day=today, last_auto_update_ts=int(time.time()), last_auto_update_error="")
    current_state = str(core.update_state().get("state") or "idle")
    if current_state in {"downloading", "readyToInstall", "installing", "installingRecovery", "waitingForShutdown", "restarting"}:
        return None
    manifest = core.fetch_update_manifest(config)
    if not manifest.get("updateAvailable"):
        core.HISTORY.event("dashboard", "update_auto_checked", core.VERSION, "", {"result": "up_to_date"})
        return None
    if auto.get("pre_backup", True):
        with core.CONFIG_STORE.exclusive() as current:
            backup = _create_backup(core.APP_DIR, core.VERSION, current, kind="pre-update", history_lock=core.HISTORY.lock)
        core.HISTORY.event("dashboard", "backup_pre_update_created", backup.get("name", ""), "", {"encrypted": bool(backup.get("encrypted"))})
    staged = core.stage_update(config)
    core.HISTORY.event("dashboard", "update_auto_downloaded", str(staged.get("version") or ""))
    if staged.get("state") == "readyToInstall":
        core.HISTORY.event("dashboard", "update_auto_install_started", str(staged.get("version") or ""))
        return core.launch_update_installer(SimpleNamespace(server=server), config, staged.get("version"))
    return staged


def _maintenance_loop(server):
    stop = server._ops_stop
    if stop.wait(30):
        return
    while not stop.is_set():
        try:
            with core.STATE_GATE.activity():
                config = core.load_config()
                state = MAINTENANCE_STATE.load()
                backup_policy = config.get("backups") or {}
                last_attempt = int(state.get("last_backup_attempt_ts") or 0)
                if scheduled_backup_due(backup_policy, state) and time.time() - last_attempt >= 3600:
                    MAINTENANCE_STATE.update(last_backup_attempt_ts=int(time.time()))
                    try:
                        _scheduled_backup(config)
                    except Exception as exc:
                        MAINTENANCE_STATE.update(last_backup_error=str(exc)[:1000])
                        core.HISTORY.audit.record("backup_scheduled_failed", outcome="failure", details={"error": str(exc)})
                state = MAINTENANCE_STATE.load()
                if retention_due(state):
                    try:
                        result = _retention(config)
                        core.HISTORY.event("dashboard", "retention_completed", "runtime", "", result)
                    except Exception as exc:
                        MAINTENANCE_STATE.update(last_retention_error=str(exc)[:1000], last_retention_ts=int(time.time()))
                        core.HISTORY.audit.record("retention_failed", outcome="failure", details={"error": str(exc)})
                state = MAINTENANCE_STATE.load()
                auto = (config.get("maintenance") or {}).get("auto_update") or {}
                if automatic_update_due(auto, state):
                    try:
                        _automatic_update(server, config)
                    except Exception as exc:
                        MAINTENANCE_STATE.update(last_auto_update_error=str(exc)[:1000])
                        core.HISTORY.audit.record("update_auto_failed", outcome="failure", details={"error": str(exc)})
        except Exception:
            logging.getLogger(__name__).exception("Operations maintenance cycle failed")
        stop.wait(60)


class OperationsHandler(_ORIGINAL_HANDLER):
    def serve_static(self, name, content_type=None):
        if name == "index.html":
            path = core.STATIC_DIR / "index.html"
            if path.is_file():
                html = path.read_text(encoding="utf-8")
                marker = f'<script src="/static/ops.js?v={core.VERSION}"></script>'
                if marker not in html:
                    html = html.replace("</body>", marker + "\n</body>")
                return self.send_bytes(200, html.encode("utf-8"), "text/html; charset=utf-8")
        return super().serve_static(name, content_type)

    def _ops_context(self, mutation=False):
        context = self.require_auth(mutation)
        if not context:
            return None
        config, token, session, new_cookie = context
        if not core.session_is_admin(session):
            self.send_json(403, {"error": "Administrator access is required"}, new_cookie)
            return None
        return config, token, session, new_cookie

    def _do_GET(self):
        path, _, query = self.path.partition("?")
        if path == "/api/system-health":
            context = self._ops_context(False)
            if not context:
                return
            config, _, _, new_cookie = context
            try:
                return self.send_json(200, _health_payload(config), new_cookie)
            except Exception as exc:
                return self.send_json(500, {"error": str(exc)}, new_cookie)
        if path == "/api/audit":
            context = self._ops_context(False)
            if not context:
                return
            _, _, _, new_cookie = context
            values = urllib.parse.parse_qs(query)
            try:
                rows = core.HISTORY.audit.entries(
                    limit=values.get("limit", ["100"])[0],
                    action=values.get("action", [""])[0],
                    outcome=values.get("outcome", [""])[0],
                    since=values.get("since", ["0"])[0],
                )
                return self.send_json(200, {"events": rows, "summary": core.HISTORY.audit.summary()}, new_cookie)
            except Exception as exc:
                return self.send_json(500, {"error": str(exc)}, new_cookie)
        return super()._do_GET()

    def _do_POST(self):
        path = self.path.partition("?")[0]
        if path == "/api/retention/run":
            context = self._ops_context(True)
            if not context:
                return
            config, _, session, new_cookie = context
            try:
                result = _retention(config)
                core.HISTORY.event("dashboard", "retention_manual", session.get("username", ""), "", {"client_ip": self.client_ip(), **result})
                return self.send_json(200, {"ok": True, "result": result}, new_cookie)
            except Exception as exc:
                return self.send_json(400, {"error": str(exc)}, new_cookie)
        return super()._do_POST()


class OperationsHTTPServer(_ORIGINAL_SERVER):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._ops_stop = threading.Event()
        self._ops_thread = threading.Thread(target=_maintenance_loop, args=(self,), daemon=True, name="torrent-dashboard-maintenance")
        self._ops_thread.start()

    def server_close(self):
        self._ops_stop.set()
        return super().server_close()


def install_runtime_extensions():
    core.fetch_update_release = _fetch_update_release
    core.fetch_update_manifest = _fetch_update_release
    core.apply_settings_update = _apply_settings_update
    core.redacted_config = _redacted_config
    core.create_backup = _create_backup
    core.list_backups = _list_backups
    core.import_backup = _import_backup
    core.restore_backup = _restore_backup
    core.delete_backup = backup_service.delete_backup
    core.backup_path = backup_service.backup_path
    core.Handler = OperationsHandler
    core.ThreadingHTTPServer = OperationsHTTPServer


def main():
    install_runtime_extensions()
    return core.main()


if __name__ == "__main__":
    raise SystemExit(main())
