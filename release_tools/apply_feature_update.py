#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def replace_between(text: str, start: str, end: str, replacement: str, label: str) -> str:
    start_count = text.count(start)
    if start_count != 1:
        raise RuntimeError(f"{label}: expected exactly one start marker, found {start_count}")
    start_at = text.index(start)
    end_at = text.find(end, start_at + len(start))
    if end_at < 0:
        raise RuntimeError(f"{label}: end marker was not found")
    return text[:start_at] + replacement + text[end_at:]


# ---------------------------------------------------------------------------
# Backend: notification-rule migration, client health, and transition events.
# ---------------------------------------------------------------------------
dashboard = read("dashboard.py")
dashboard = replace_once(dashboard, 'VERSION = "0.5.33"', 'VERSION = "0.5.34"', "version")

notification_helpers = '''DEFAULT_UPDATE_REPOSITORY = "CynicaGaming/TorrentDashboard"

NOTIFICATION_RULE_KEYS = (
    "torrent_completed",
    "torrent_error",
    "torrent_stalled",
    "client_offline",
    "client_recovered",
    "update_available",
    "security_account",
)


def default_notification_rules(browser=True, sound=False):
    rules = {key: {"browser": False, "sound": False} for key in NOTIFICATION_RULE_KEYS}
    rules["torrent_completed"] = {"browser": bool(browser), "sound": bool(sound)}
    return rules


def normalize_notification_rules(value, legacy_browser=True, legacy_sound=False):
    defaults = default_notification_rules(legacy_browser, legacy_sound)
    if not isinstance(value, dict):
        return defaults
    out = {}
    for key in NOTIFICATION_RULE_KEYS:
        source = value.get(key) if isinstance(value.get(key), dict) else {}
        fallback = defaults[key]
        out[key] = {
            "browser": bool(source.get("browser", fallback["browser"])),
            "sound": bool(source.get("sound", fallback["sound"])),
        }
    return out
'''
dashboard = replace_once(
    dashboard,
    'DEFAULT_UPDATE_REPOSITORY = "CynicaGaming/TorrentDashboard"\n',
    notification_helpers,
    "notification rule constants",
)

dashboard = replace_once(
    dashboard,
'''    "notifications": {
        "browser": True,
        "sound": False,
        "sound_mode": "default",
        "custom_sound_file": "",
        "custom_sound_name": "",
        "custom_sound_mime": ""
    },''',
'''    "notifications": {
        "browser": True,
        "sound": False,
        "sound_mode": "default",
        "custom_sound_file": "",
        "custom_sound_name": "",
        "custom_sound_mime": "",
        "rules": default_notification_rules(True, False),
    },''',
    "default notification rules",
)

dashboard = replace_once(
    dashboard,
'''    merged = deep_merge(DEFAULT_CONFIG, raw)
    # 0.5.16 makes status collection a fixed one-second application behavior.''',
'''    merged = deep_merge(DEFAULT_CONFIG, raw)
    # 0.5.34 introduces fixed notification event rules while preserving the
    # previous global browser/sound behavior for torrent-completion alerts.
    raw_notifications = raw.get("notifications", {}) if isinstance(raw.get("notifications"), dict) else {}
    merged_notifications = merged.setdefault("notifications", {})
    legacy_browser = bool(raw_notifications.get("browser", merged_notifications.get("browser", True)))
    legacy_sound = bool(raw_notifications.get("sound", merged_notifications.get("sound", False)))
    merged_notifications["rules"] = normalize_notification_rules(raw_notifications.get("rules"), legacy_browser, legacy_sound)
    merged_notifications["browser"] = merged_notifications["rules"]["torrent_completed"]["browser"]
    merged_notifications["sound"] = merged_notifications["rules"]["torrent_completed"]["sound"]
    # 0.5.16 makes status collection a fixed one-second application behavior.''',
    "notification migration",
)

public_notification_helper = '''def public_notification_settings(cfg):
    n = cfg.get("notifications", {}) if isinstance(cfg.get("notifications"), dict) else {}
    rules = normalize_notification_rules(n.get("rules"), n.get("browser", True), n.get("sound", False))
    sound_path, _ = configured_notification_sound(cfg)
    return {
        "browser": rules["torrent_completed"]["browser"],
        "sound": rules["torrent_completed"]["sound"],
        "sound_mode": "custom" if n.get("sound_mode") == "custom" else "default",
        "custom_sound_configured": bool(sound_path),
        "rules": rules,
    }


'''
dashboard = replace_once(
    dashboard,
    '\ndef normalize_github_repository(value: str) -> str:\n',
    '\n' + public_notification_helper + 'def normalize_github_repository(value: str) -> str:\n',
    "public notification settings",
)

health_helpers = '''def torrent_runtime_notice_state(torrent):
    state = str((torrent or {}).get("state") or "").lower()
    if "error" in state or "missing" in state:
        return "error"
    try:
        complete = float((torrent or {}).get("progress", 0) or 0) >= 0.999999
    except (TypeError, ValueError):
        complete = False
    if "stall" in state and not complete:
        return "stalled"
    return ""


def client_health_snapshot(cfg):
    now = int(time.time())
    with CACHE_LOCK:
        cache = {key: dict(value) for key, value in CACHE.items()}
    result = []
    for server in cfg.get("servers", []):
        sid = str(server.get("id") or "")
        item = cache.get(sid, {})
        enabled = bool(server.get("enabled", True))
        if not enabled:
            status = "disabled"
            online = None
        elif not item:
            status = "connecting"
            online = None
        elif item.get("ok"):
            status = "online"
            online = True
        else:
            status = "offline"
            online = False
        result.append({
            "id": sid,
            "name": server.get("name", sid),
            "enabled": enabled,
            "status": status,
            "online": online,
            "app_version": str(item.get("app_version") or ""),
            "api_version": str(item.get("api_version") or ""),
            "auth_method": server.get("auth_method", "password"),
            "last_success": int(item.get("last_success") or 0),
            "last_attempt": int(item.get("last_attempt") or item.get("ts") or 0),
            "latency_ms": int(item.get("latency_ms") or 0),
            "error": str(item.get("error") or "") if status == "offline" else "",
            "age_seconds": max(0, now - int(item.get("last_success") or now)) if item.get("last_success") else None,
        })
    return result


'''
dashboard = replace_once(
    dashboard,
    '\ndef disk_free_for(preferences):\n',
    '\n' + health_helpers + 'def disk_free_for(preferences):\n',
    "client health helpers",
)

collector = '''def collector_loop(stop_event):
    while not stop_event.is_set():
        cfg = load_config()
        sample_every = max(5, int(cfg["dashboard"].get("history_sample_seconds", 10)))
        for server in cfg.get("servers", []):
            if not server.get("enabled", True):
                continue
            sid = server.get("id")
            started = time.perf_counter()
            with CACHE_LOCK:
                old_cache = dict(CACHE.get(sid, {}))
                previous = list(old_cache.get("torrents", []))
                previous_ok = old_cache.get("ok") if old_cache else None
            try:
                client = get_client(cfg, sid)
                torrents, transfer, app_version, api_version = client.info()
                preferences = client.preferences()
                meta = client.metadata()
                disk_free = disk_free_for(preferences)
                now = int(time.time())
                latency_ms = max(1, int((time.perf_counter() - started) * 1000))
                prev_completed = {t.get("hash") for t in previous if float(t.get("progress",0) or 0) >= .999999}
                now_completed = {t.get("hash") for t in torrents if float(t.get("progress",0) or 0) >= .999999}
                newly = now_completed - prev_completed if previous else set()
                with CACHE_LOCK:
                    CACHE[sid] = {
                        "ok": True,
                        "ts": now,
                        "last_attempt": now,
                        "last_success": now,
                        "latency_ms": latency_ms,
                        "server": {"id": sid, "name": server.get("name", sid)},
                        "torrents": torrents,
                        "transfer": transfer,
                        "meta": meta,
                        "app_version": app_version,
                        "api_version": api_version,
                        "disk_free": disk_free,
                        "error": "",
                    }
                if previous_ok is False:
                    HISTORY.event(sid, "client_recovered", server.get("name", sid), "", {"latency_ms": latency_ms})
                previous_by_hash = {str(t.get("hash") or ""): t for t in previous if t.get("hash")}
                for torrent in torrents:
                    hash_ = str(torrent.get("hash") or "")
                    prior = previous_by_hash.get(hash_)
                    if not prior:
                        continue
                    current_notice = torrent_runtime_notice_state(torrent)
                    previous_notice = torrent_runtime_notice_state(prior)
                    if current_notice and current_notice != previous_notice:
                        HISTORY.event(sid, f"torrent_{current_notice}", torrent.get("name", "Torrent"), hash_, {})
                HISTORY.sample(sid, torrents, transfer, disk_free, sample_every)
                for h in newly:
                    torrent = next((x for x in torrents if x.get("hash") == h), None)
                    if torrent:
                        send_notification(cfg, "Torrent completed", f"{torrent.get('name','Torrent')} finished on {server.get('name',sid)}")
            except Exception as exc:
                now = int(time.time())
                with CACHE_LOCK:
                    old = dict(CACHE.get(sid, {}))
                    was_ok = old.get("ok") if old else None
                    CACHE[sid] = {
                        **old,
                        "ok": False,
                        "ts": now,
                        "last_attempt": now,
                        "server": {"id": sid, "name": server.get("name", sid)},
                        "error": str(exc),
                    }
                if was_ok is not False:
                    HISTORY.event(sid, "client_offline", server.get("name", sid), "", {"error": str(exc)[:1000]})
        try:
            HISTORY.cleanup(cfg["dashboard"].get("history_retention_days",30))
        except Exception:
            pass
        stop_event.wait(STATUS_REFRESH_SECONDS)


'''
dashboard = replace_between(
    dashboard,
    'def collector_loop(stop_event):\n',
    'def integration_request(',
    collector,
    "collector health transitions",
)

# /api/me gets safe notification preferences for Standard Users as well.
dashboard = replace_once(
    dashboard,
    '"scheme":"https" if cfg["dashboard"].get("https_enabled") else "http"}',
    '"scheme":"https" if cfg["dashboard"].get("https_enabled") else "http","notifications":public_notification_settings(cfg)}',
    "me notification settings",
)

# Add safe health data to status payloads and the Clients endpoint.
dashboard = replace_once(
    dashboard,
'''            payload["tab_counts"]={
                "all":len(payload.get("torrents",[])),
                "downloading":sum(1 for t in payload.get("torrents",[]) if float(t.get("progress",0) or 0)<1 and "paused" not in str(t.get("state","")).lower() and "stopped" not in str(t.get("state","")).lower()),
                "completed":sum(1 for t in payload.get("torrents",[]) if float(t.get("progress",0) or 0)>=.999999),
                "paused":sum(1 for t in payload.get("torrents",[]) if "paused" in str(t.get("state","")).lower() or "stopped" in str(t.get("state","")).lower()),
            }
            return self.send_json(200,payload,new_cookie)

        if path=="/api/servers":
            servers=[{"id":s.get("id"),"name":s.get("name",s.get("id")),"enabled":s.get("enabled",True)} for s in cfg.get("servers",[])]
            return self.send_json(200,{"servers":servers},new_cookie)''',
'''            payload["tab_counts"]={
                "all":len(payload.get("torrents",[])),
                "downloading":sum(1 for t in payload.get("torrents",[]) if float(t.get("progress",0) or 0)<1 and "paused" not in str(t.get("state","")).lower() and "stopped" not in str(t.get("state","")).lower()),
                "completed":sum(1 for t in payload.get("torrents",[]) if float(t.get("progress",0) or 0)>=.999999),
                "paused":sum(1 for t in payload.get("torrents",[]) if "paused" in str(t.get("state","")).lower() or "stopped" in str(t.get("state","")).lower()),
            }
            payload["server_health"] = client_health_snapshot(cfg)
            return self.send_json(200,payload,new_cookie)

        if path=="/api/servers":
            return self.send_json(200,{"servers":client_health_snapshot(cfg)},new_cookie)''',
    "status client health",
)

# Redacted settings always return normalized rules.
dashboard = replace_once(
    dashboard,
'''    n=out.get("notifications",{})
    for secret in ("gotify_token","telegram_bot_token"):
        if n.get(secret): n[secret]="<configured>"''',
'''    n=out.get("notifications",{})
    n["rules"] = normalize_notification_rules(n.get("rules"), n.get("browser", True), n.get("sound", False))
    n["browser"] = n["rules"]["torrent_completed"]["browser"]
    n["sound"] = n["rules"]["torrent_completed"]["sound"]
    for secret in ("gotify_token","telegram_bot_token"):
        if n.get(secret): n[secret]="<configured>"''',
    "redacted notification rules",
)

dashboard = replace_once(
    dashboard,
'''    if "notifications" in data:
        for k,v in data["notifications"].items():
            if k in out["notifications"] and v!="<configured>": out["notifications"][k]=v
    sync_legacy_auth(out)''',
'''    if "notifications" in data:
        incoming = data["notifications"] if isinstance(data["notifications"], dict) else {}
        if "sound_mode" in incoming:
            mode = str(incoming.get("sound_mode") or "default")
            if mode not in ("default", "custom"):
                raise RuntimeError("Invalid notification sound mode")
            out["notifications"]["sound_mode"] = mode
        if "rules" in incoming:
            current_rules = normalize_notification_rules(
                out["notifications"].get("rules"),
                out["notifications"].get("browser", True),
                out["notifications"].get("sound", False),
            )
            supplied = incoming.get("rules") if isinstance(incoming.get("rules"), dict) else {}
            merged_rules = {key: dict(value) for key, value in current_rules.items()}
            for key in NOTIFICATION_RULE_KEYS:
                if key not in supplied or not isinstance(supplied[key], dict):
                    continue
                merged_rules[key] = {
                    "browser": bool(supplied[key].get("browser", current_rules[key]["browser"])),
                    "sound": bool(supplied[key].get("sound", current_rules[key]["sound"])),
                }
            out["notifications"]["rules"] = merged_rules
            out["notifications"]["browser"] = merged_rules["torrent_completed"]["browser"]
            out["notifications"]["sound"] = merged_rules["torrent_completed"]["sound"]
        else:
            # Keep compatibility with clients that still submit the 0.5.33
            # global browser/sound fields.
            legacy_browser = bool(incoming.get("browser", out["notifications"].get("browser", True)))
            legacy_sound = bool(incoming.get("sound", out["notifications"].get("sound", False)))
            rules = normalize_notification_rules(out["notifications"].get("rules"), legacy_browser, legacy_sound)
            if "browser" in incoming:
                rules["torrent_completed"]["browser"] = legacy_browser
            if "sound" in incoming:
                rules["torrent_completed"]["sound"] = legacy_sound
            out["notifications"]["rules"] = rules
            out["notifications"]["browser"] = rules["torrent_completed"]["browser"]
            out["notifications"]["sound"] = rules["torrent_completed"]["sound"]
    sync_legacy_auth(out)''',
    "notification settings update",
)
write("dashboard.py", dashboard)


# ---------------------------------------------------------------------------
# HTML: notification rule matrix, save-state affordances, and dialog ARIA.
# ---------------------------------------------------------------------------
html = read("static/index.html").replace("?v=0.5.33", "?v=0.5.34")

notification_section = '''<section class="settings-page" data-settings-section="notifications">
<div class="panel settings-card notification-settings-card"><div class="panel-title">Notifications</div>
<p class="muted notification-intro">Choose which events can use browser notifications or sound. Discord, ntfy, and webhooks remain under Integrations.</p>
<div class="notification-options">
<div class="notification-rule-table" role="group" aria-labelledby="notificationRulesTitle">
<div class="notification-rule-heading" id="notificationRulesTitle"><strong>Event rules</strong><span>Browser</span><span>Sound</span></div>
<div class="notification-rule-row"><span><strong>Torrent completed</strong><small>A torrent finishes downloading.</small></span><label><input data-notification-rule="torrent_completed" data-notification-channel="browser" type="checkbox"/><span class="sr-only">Browser notification for torrent completed</span></label><label><input data-notification-rule="torrent_completed" data-notification-channel="sound" type="checkbox"/><span class="sr-only">Sound for torrent completed</span></label></div>
<div class="notification-rule-row"><span><strong>Torrent error</strong><small>A torrent enters an error or missing-files state.</small></span><label><input data-notification-rule="torrent_error" data-notification-channel="browser" type="checkbox"/><span class="sr-only">Browser notification for torrent error</span></label><label><input data-notification-rule="torrent_error" data-notification-channel="sound" type="checkbox"/><span class="sr-only">Sound for torrent error</span></label></div>
<div class="notification-rule-row"><span><strong>Torrent stalled</strong><small>A downloading torrent becomes stalled.</small></span><label><input data-notification-rule="torrent_stalled" data-notification-channel="browser" type="checkbox"/><span class="sr-only">Browser notification for stalled torrent</span></label><label><input data-notification-rule="torrent_stalled" data-notification-channel="sound" type="checkbox"/><span class="sr-only">Sound for stalled torrent</span></label></div>
<div class="notification-rule-row"><span><strong>Client offline</strong><small>A configured qBitTorrent client becomes unreachable.</small></span><label><input data-notification-rule="client_offline" data-notification-channel="browser" type="checkbox"/><span class="sr-only">Browser notification for client offline</span></label><label><input data-notification-rule="client_offline" data-notification-channel="sound" type="checkbox"/><span class="sr-only">Sound for client offline</span></label></div>
<div class="notification-rule-row"><span><strong>Client recovered</strong><small>A previously offline client reconnects.</small></span><label><input data-notification-rule="client_recovered" data-notification-channel="browser" type="checkbox"/><span class="sr-only">Browser notification for client recovered</span></label><label><input data-notification-rule="client_recovered" data-notification-channel="sound" type="checkbox"/><span class="sr-only">Sound for client recovered</span></label></div>
<div class="notification-rule-row"><span><strong>Update available</strong><small>A newer Torrent Dashboard release is found.</small></span><label><input data-notification-rule="update_available" data-notification-channel="browser" type="checkbox"/><span class="sr-only">Browser notification for update available</span></label><label><input data-notification-rule="update_available" data-notification-channel="sound" type="checkbox"/><span class="sr-only">Sound for update available</span></label></div>
<div class="notification-rule-row"><span><strong>Security and account</strong><small>Sign-ins and account or user changes.</small></span><label><input data-notification-rule="security_account" data-notification-channel="browser" type="checkbox"/><span class="sr-only">Browser notification for security and account events</span></label><label><input data-notification-rule="security_account" data-notification-channel="sound" type="checkbox"/><span class="sr-only">Sound for security and account events</span></label></div>
</div>
<div class="notification-sound-config" id="notificationSoundConfig">
<label>Sound<select id="nSoundMode"><option value="default">Default</option><option value="custom">Custom</option></select></label>
<div class="custom-sound-wrap hidden" id="nCustomSoundWrap">
<label>Custom Sound File<input accept="audio/wav,audio/mpeg,audio/ogg,.wav,.mp3,.ogg" id="nSoundFile" type="file"/></label>
<div class="configured-sound" id="nCustomSoundName">None uploaded</div>
<div class="field-help">WAV, MP3, or OGG · 2 MB max · Preserved during updates.</div>
</div>
<div class="settings-inline-actions notification-actions"><button class="secondary" id="testNotification" type="button">Test browser</button><button class="secondary" id="testNotificationSound" type="button">Test sound</button></div>
<div class="test-result muted" id="soundStatus" role="status" aria-live="polite"></div>
</div>
</div>
</div>
</section>
'''
html = replace_between(
    html,
    '<section class="settings-page" data-settings-section="notifications">\n',
    '<div class="settings-savebar" id="settingsSavebar">',
    notification_section,
    "notification settings section",
)

html = replace_once(
    html,
    '<div class="settings-savebar" id="settingsSavebar"><button class="primary" type="submit">Save</button></div>',
    '<div class="settings-savebar" id="settingsSavebar"><span class="settings-save-state" id="settingsSaveState" role="status" aria-live="polite"></span><button class="primary" id="settingsSaveButton" type="submit" disabled>Save</button></div>',
    "settings save state",
)

html = replace_once(
    html,
    '<div class="account-form-actions"><button class="primary" type="submit">Save profile</button></div>',
    '<div class="account-form-actions"><span class="form-save-state" id="accountProfileSaveState" role="status" aria-live="polite"></span><button class="primary" id="accountProfileSave" type="submit" disabled>Save profile</button></div>',
    "account profile save state",
)
html = replace_once(
    html,
    '<div class="account-form-actions"><button class="primary" type="submit">Change password</button></div>',
    '<div class="account-form-actions"><span class="form-save-state" id="accountPasswordSaveState" role="status" aria-live="polite"></span><button class="primary" id="accountPasswordSave" type="submit" disabled>Change password</button></div>',
    "account password save state",
)
html = replace_once(
    html,
    '<div class="test-result muted" id="accountStatus"></div>',
    '<div class="test-result muted" id="accountStatus" role="status" aria-live="polite"></div>',
    "account live status",
)
html = replace_once(
    html,
    '<div class="test-result muted" id="passwordConfirmStatus"></div>',
    '<div class="test-result muted" id="passwordConfirmStatus" role="status" aria-live="polite"></div>',
    "password confirm live status",
)
html = replace_once(
    html,
    '<div class="client-settings-status muted" id="clientSettingsStatus"></div></div><footer class="client-settings-actions"><button class="primary" id="saveClientSettings" type="submit">Save</button><button class="secondary" data-client-settings-close="" type="button">Cancel</button></footer>',
    '<div class="client-settings-status muted" id="clientSettingsStatus" role="status" aria-live="polite"></div></div><footer class="client-settings-actions"><span class="form-save-state" id="clientSettingsSaveState" role="status" aria-live="polite"></span><button class="primary" id="saveClientSettings" type="submit" disabled>Save</button><button class="secondary" data-client-settings-close="" type="button">Cancel</button></footer>',
    "client settings save state",
)

# Dialog semantics and tab semantics. Keep the existing structures/styles.
for old, new, label in [
    ('<form class="modal-card" id="addForm">', '<form class="modal-card" id="addForm" role="dialog" aria-modal="true" aria-labelledby="addModalTitle">', 'add dialog role'),
    ('<header><h2>Add Torrent</h2>', '<header><h2 id="addModalTitle">Add Torrent</h2>', 'add dialog title'),
    ('<form class="modal-card action-dialog-card" id="actionDialogForm">', '<form class="modal-card action-dialog-card" id="actionDialogForm" role="dialog" aria-modal="true" aria-labelledby="actionDialogTitle">', 'action dialog role'),
    ('<form class="modal-card remove-modal-card" id="removeForm">', '<form class="modal-card remove-modal-card" id="removeForm" role="dialog" aria-modal="true" aria-labelledby="removeModalTitle">', 'remove dialog role'),
    ('<form class="modal-card password-confirm-card" id="passwordConfirmForm">', '<form class="modal-card password-confirm-card" id="passwordConfirmForm" role="dialog" aria-modal="true" aria-labelledby="passwordConfirmTitle">', 'password dialog role'),
    ('<h2>Confirm your password</h2>', '<h2 id="passwordConfirmTitle">Confirm your password</h2>', 'password dialog title'),
    ('<form class="modal-card client-settings-card" id="clientSettingsForm">', '<form class="modal-card client-settings-card" id="clientSettingsForm" role="dialog" aria-modal="true" aria-labelledby="clientSettingsTitle">', 'client dialog role'),
    ('<header><div><h2>Settings</h2><p id="clientSettingsClientName">qBitTorrent</p>', '<header><div><h2 id="clientSettingsTitle">Settings</h2><p id="clientSettingsClientName">qBitTorrent</p>', 'client dialog title'),
    ('<section class="drawer-sheet">', '<section class="drawer-sheet" role="dialog" aria-modal="true" aria-labelledby="detailName">', 'drawer dialog role'),
]:
    html = replace_once(html, old, new, label)

html = replace_once(
    html,
    '<div class="client-settings-tabs" role="tablist" aria-label="Client settings sections"><button class="active" data-client-settings-tab="speed" type="button">Speed</button><button data-client-settings-tab="connection" type="button">Connection</button><button data-client-settings-tab="proxy" type="button">Proxy</button></div>',
    '<div class="client-settings-tabs" role="tablist" aria-label="Client settings sections"><button class="active" id="clientSettingsTabSpeed" data-client-settings-tab="speed" role="tab" aria-selected="true" aria-controls="clientSettingsPaneSpeed" tabindex="0" type="button">Speed</button><button id="clientSettingsTabConnection" data-client-settings-tab="connection" role="tab" aria-selected="false" aria-controls="clientSettingsPaneConnection" tabindex="-1" type="button">Connection</button><button id="clientSettingsTabProxy" data-client-settings-tab="proxy" role="tab" aria-selected="false" aria-controls="clientSettingsPaneProxy" tabindex="-1" type="button">Proxy</button></div>',
    "client tab aria",
)
html = replace_once(html, '<section class="client-settings-pane active" data-client-settings-pane="speed">', '<section class="client-settings-pane active" id="clientSettingsPaneSpeed" data-client-settings-pane="speed" role="tabpanel" aria-labelledby="clientSettingsTabSpeed">', "speed tabpanel")
html = replace_once(html, '<section class="client-settings-pane" data-client-settings-pane="connection">', '<section class="client-settings-pane" id="clientSettingsPaneConnection" data-client-settings-pane="connection" role="tabpanel" aria-labelledby="clientSettingsTabConnection" hidden>', "connection tabpanel")
html = replace_once(html, '<section class="client-settings-pane" data-client-settings-pane="proxy">', '<section class="client-settings-pane" id="clientSettingsPaneProxy" data-client-settings-pane="proxy" role="tabpanel" aria-labelledby="clientSettingsTabProxy" hidden>', "proxy tabpanel")
html = replace_once(html, '<div class="banner error hidden" id="errorBanner"></div>', '<div class="banner error hidden" id="errorBanner" role="alert" aria-live="assertive"></div>', "error banner aria")
write("static/index.html", html)


# ---------------------------------------------------------------------------
# Frontend core: dirty tracking, focus management, notifications, health,
# adaptive large-library rendering, and navigation protection.
# ---------------------------------------------------------------------------
app = read("static/app.js")

app = replace_once(
    app,
    "const LIVE_REFRESH_MS=1000;\nconst state={me:null,csrf:'',setup:null,setupStep:0,setupMaxStep:0,server:'all',torrents:[],transfer:{},meta:{},filter:localStorage.tdFilter||'all',sort:localStorage.tdSort||'added_desc',search:localStorage.tdSearch||'',category:localStorage.tdCategory||'',tag:localStorage.tdTag||'',tracker:localStorage.tdTracker||'',selected:new Set(),detail:null,detailTab:'overview',settings:null,lastComplete:new Set(),deferredPrompt:null,setupInterfaceSelectionInitialized:false,settingsInterfaceSelectionInitialized:false,updateInfo:null,notificationEvents:[]};",
    "const LIVE_REFRESH_MS=1000;\nconst LARGE_LIBRARY_THRESHOLD=300;\nconst state={me:null,csrf:'',setup:null,setupStep:0,setupMaxStep:0,server:'all',torrents:[],transfer:{},meta:{},filter:localStorage.tdFilter||'all',sort:localStorage.tdSort||'added_desc',search:localStorage.tdSearch||'',category:localStorage.tdCategory||'',tag:localStorage.tdTag||'',tracker:localStorage.tdTracker||'',selected:new Set(),detail:null,detailTab:'overview',settings:null,lastComplete:new Set(),completionBaselineReady:false,torrentNoticeStates:new Map(),torrentNoticeReady:false,clientHealth:{},clientNoticeStates:new Map(),clientNoticeReady:false,notificationEventCursor:null,lastSecurityPoll:0,notifiedUpdateVersion:'',rowRenderCache:new Map(),rowRenderOrder:[],renderPending:false,deferredPrompt:null,setupInterfaceSelectionInitialized:false,settingsInterfaceSelectionInitialized:false,updateInfo:null,notificationEvents:[]};",
    "state expansion",
)

utility_block = '''async function post(url,obj){return api(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(obj)})}

const dirtyScopes=new Map();
function formFingerprint(root){
  if(!root)return'';
  return JSON.stringify([...root.querySelectorAll('input,select,textarea')].filter(el=>!['button','submit','reset'].includes(el.type)).map((el,index)=>{
    const key=el.id||el.name||el.dataset.field||el.dataset.k||el.dataset.userField||`${el.tagName}:${index}`;
    let value;
    if(el.type==='checkbox'||el.type==='radio')value=!!el.checked;
    else if(el.type==='file'){const file=el.files?.[0];value=file?`${file.name}:${file.size}:${file.lastModified}`:'';}
    else value=el.value;
    return[key,el.type||el.tagName,value];
  }));
}
function dirtyElement(ref){return typeof ref==='string'?$(ref):ref}
function syncDirtyScope(name){
  const scope=dirtyScopes.get(name);if(!scope)return false;
  const dirty=scope.forceDirty||formFingerprint(scope.root)!==scope.baseline;
  scope.dirty=dirty;
  const button=dirtyElement(scope.saveButton),status=dirtyElement(scope.statusEl);
  if(button)button.disabled=!dirty;
  if(status){status.classList.toggle('dirty',dirty);status.classList.toggle('saved',false);status.textContent=dirty?'Unsaved changes':'';}
  return dirty;
}
function registerDirtyScope(name,root,options={}){
  root=dirtyElement(root);if(!root)return;
  let scope=dirtyScopes.get(name);
  if(scope?.root!==root){
    scope={name,root,baseline:formFingerprint(root),dirty:false,forceDirty:false,saveButton:options.saveButton,statusEl:options.statusEl,timer:null};
    dirtyScopes.set(name,scope);
    const listener=()=>syncDirtyScope(name);root.addEventListener('input',listener);root.addEventListener('change',listener);
  }else{
    scope.saveButton=options.saveButton??scope.saveButton;scope.statusEl=options.statusEl??scope.statusEl;
  }
  if(options.forceDirty)scope.forceDirty=true;
  syncDirtyScope(name);
}
function forceDirtyScope(name){const scope=dirtyScopes.get(name);if(!scope)return;scope.forceDirty=true;syncDirtyScope(name)}
function resetDirtyScope(name,saved=false){
  const scope=dirtyScopes.get(name);if(!scope)return;
  clearTimeout(scope.timer);scope.forceDirty=false;scope.baseline=formFingerprint(scope.root);scope.dirty=false;
  const button=dirtyElement(scope.saveButton),status=dirtyElement(scope.statusEl);if(button)button.disabled=true;
  if(status){status.classList.remove('dirty');status.classList.toggle('saved',!!saved);status.textContent=saved?'Saved':'';if(saved)scope.timer=setTimeout(()=>{if(!syncDirtyScope(name)){status.classList.remove('saved');status.textContent=''}},1800)}
}
function unregisterDirtyScope(name){const scope=dirtyScopes.get(name);if(scope)clearTimeout(scope.timer);dirtyScopes.delete(name)}
function dirtyScopeNames(filter=null){return[...dirtyScopes.entries()].filter(([name,scope])=>scope.dirty&&(!filter||filter(name))).map(([name])=>name)}
function anyDirtyScopes(){return dirtyScopeNames().length>0}
function clearDirtyScopes(names){for(const name of names)resetDirtyScope(name,false)}
async function confirmDiscardScopes(names,message='Unsaved changes will be lost.'){
  names=(names||[]).filter(name=>dirtyScopes.get(name)?.dirty);if(!names.length)return true;
  const confirmed=await showActionDialog({input:false,title:'Discard changes?',message,confirmLabel:'Discard',danger:true});
  if(confirmed)clearDirtyScopes(names);
  return!!confirmed;
}
window.addEventListener('beforeunload',e=>{if(!anyDirtyScopes())return;e.preventDefault();e.returnValue='';});

const surfaceOrigins=new WeakMap();
function surfaceFocusable(root){return[...root.querySelectorAll('button:not([disabled]),input:not([disabled]):not([type="hidden"]),select:not([disabled]),textarea:not([disabled]),[href],[tabindex]:not([tabindex="-1"])')].filter(el=>!el.hidden&&el.getClientRects().length)}
function showSurface(surface,focusTarget=null){surface=dirtyElement(surface);if(!surface)return;surfaceOrigins.set(surface,document.activeElement);surface.classList.remove('hidden');surface.setAttribute('aria-hidden','false');setTimeout(()=>{const target=dirtyElement(focusTarget)||surfaceFocusable(surface)[0];target?.focus()},0)}
function hideSurface(surface,restore=true){surface=dirtyElement(surface);if(!surface)return;surface.classList.add('hidden');surface.setAttribute('aria-hidden','true');const origin=surfaceOrigins.get(surface);surfaceOrigins.delete(surface);if(restore&&origin?.isConnected)setTimeout(()=>origin.focus(),0)}
function activeFocusSurface(){const visible=$$('.modal:not(.hidden),.drawer:not(.hidden)');return visible[visible.length-1]||null}
function trapSurfaceFocus(e){if(e.key!=='Tab')return false;const surface=activeFocusSurface();if(!surface)return false;const items=surfaceFocusable(surface);if(!items.length){e.preventDefault();return true}const first=items[0],last=items[items.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();return true}if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();return true}if(!surface.contains(document.activeElement)){e.preventDefault();first.focus();return true}return false}
'''
app = replace_once(app, "async function post(url,obj){return api(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(obj)})}\n", utility_block, "dirty and focus utilities")

notification_runtime = '''function configuredCompletionSoundUrl(){const n=state.settings?.notifications||state.me?.notifications||{};return n.sound_mode==='custom'&&(n.custom_sound_file||n.custom_sound_configured)?`/api/notification-sound?ts=${Date.now()}`:`/static/default-completion.wav?v=${encodeURIComponent(state.me?.version||'')}`}
function notificationRule(key){const n=state.settings?.notifications||state.me?.notifications||{},rule=n.rules?.[key];if(rule)return{browser:!!rule.browser,sound:!!rule.sound};if(key==='torrent_completed')return{browser:n.browser!==false,sound:!!n.sound};return{browser:false,sound:false}}
async function playNotificationRuleSound(key){if(!notificationRule(key).sound)return;const n=state.settings?.notifications||state.me?.notifications||{};try{return await playSoundUrl(configuredCompletionSoundUrl())}catch(e){if(n.sound_mode==='custom')return playSoundUrl(`/static/default-completion.wav?v=${encodeURIComponent(state.me?.version||'')}`);throw e}}
async function playCompletionSound(){return playNotificationRuleSound('torrent_completed')}
async function dispatchNotificationRule(key,title,body,tag=''){const rule=notificationRule(key),jobs=[];if(rule.sound)jobs.push(playNotificationRuleSound(key));if(rule.browser&&'Notification'in window&&Notification.permission==='granted')jobs.push(showBrowserNotification(state.settings?.dashboard?.title||state.me?.title||'Torrent Dashboard',{body,tag:tag||`torrent-dashboard-${key}`}));if(jobs.length)await Promise.allSettled(jobs)}
'''
app = replace_between(app, 'function configuredCompletionSoundUrl()', 'async function showBrowserNotification', notification_runtime, "notification runtime helpers")

app = replace_once(
    app,
    "function openAddTorrent(mode='link'){if(state.server==='all')return toast('chooseSpecificServerFirst','error');$('#addModal').classList.remove('hidden');if(mode==='file')$('#torrentFile').click();else $('#addUrls').focus()}",
    "function openAddTorrent(mode='link'){if(state.server==='all')return toast('chooseSpecificServerFirst','error');showSurface('#addModal',mode==='file'?'#torrentFile':'#addUrls');if(mode==='file')setTimeout(()=>$('#torrentFile').click(),0)}",
    "add modal focus",
)

refresh_block = '''let refreshTimer;
function scheduleRefresh(){clearInterval(refreshTimer);refreshTimer=setInterval(refreshStatus,LIVE_REFRESH_MS)}
async function refreshStatus(){try{const d=await api(`/api/status?server=${encodeURIComponent(state.server)}`);state.torrents=d.torrents||[];state.transfer=d.transfer||{};renderMetrics(d);checkCompletions();checkTorrentRuntimeNotifications();if(Array.isArray(d.server_health)){updateClientHealth(d.server_health);checkClientHealthNotifications(d.server_health)}if(Date.now()-state.lastSecurityPoll>15000){state.lastSecurityPoll=Date.now();pollSecurityNotifications().catch(()=>{})}if(document.hidden)state.renderPending=true;else render();$('#errorBanner').classList.toggle('hidden',d.ok!==false);if(d.ok===false){$('#errorBanner').textContent=d.error||(d.errors||[]).map(x=>x.error).join(' · ')||uiText('connectionProblem')}}catch(e){$('#errorBanner').textContent=e.message;$('#errorBanner').classList.remove('hidden')}}
function checkCompletions(){const now=new Set(state.torrents.filter(t=>Number(t.progress)>=.999999).map(keyFor));if(state.completionBaselineReady){for(const k of now)if(!state.lastComplete.has(k)){const t=state.torrents.find(x=>keyFor(x)===k);if(t){toast(`completed: ${t.name}`);dispatchNotificationRule('torrent_completed','Torrent completed',`${t.name||'Torrent'} finished downloading${t._server_name?` on ${t._server_name}`:''}.`,`torrent-complete-${k}`).catch(()=>{})}}}state.lastComplete=now;state.completionBaselineReady=true;if('setAppBadge'in navigator){let n=state.torrents.filter(isActive).length;n?navigator.setAppBadge(n):navigator.clearAppBadge()}}
function torrentNoticeState(t){const value=stateInfo(t)[0];return value==='error'||value==='stalled'?value:''}
function checkTorrentRuntimeNotifications(){const next=new Map();for(const t of state.torrents){const key=keyFor(t),value=torrentNoticeState(t);next.set(key,value);if(!state.torrentNoticeReady||!value||state.torrentNoticeStates.get(key)===value)continue;const server=t._server_name?` on ${t._server_name}`:'';if(value==='error')dispatchNotificationRule('torrent_error','Torrent error',`${t.name||'Torrent'} entered an error state${server}.`,`torrent-error-${key}`).catch(()=>{});else dispatchNotificationRule('torrent_stalled','Torrent stalled',`${t.name||'Torrent'} is stalled${server}.`,`torrent-stalled-${key}`).catch(()=>{})}state.torrentNoticeStates=next;state.torrentNoticeReady=true}
function updateClientHealth(items){state.clientHealth=Object.fromEntries((items||[]).map(item=>[String(item.id||''),item]));updateServerHealthCards(items||[])}
function checkClientHealthNotifications(items){const next=new Map();for(const item of items||[]){const id=String(item.id||''),status=String(item.status||'connecting');next.set(id,status);if(!state.clientNoticeReady)continue;const prev=state.clientNoticeStates.get(id);if(prev==='online'&&status==='offline')dispatchNotificationRule('client_offline','Client offline',`${item.name||'qBitTorrent'} is unreachable.`,`client-offline-${id}`).catch(()=>{});else if(prev==='offline'&&status==='online')dispatchNotificationRule('client_recovered','Client recovered',`${item.name||'qBitTorrent'} is online again.`,`client-recovered-${id}`).catch(()=>{})}state.clientNoticeStates=next;state.clientNoticeReady=true}
async function pollSecurityNotifications(){const rule=notificationRule('security_account');if(!rule.browser&&!rule.sound)return;const data=await api('/api/events?limit=50'),events=data.events||[],latest=Math.max(0,...events.map(item=>Number(item.id)||0));if(state.notificationEventCursor===null){state.notificationEventCursor=latest;return}const fresh=events.filter(item=>(Number(item.id)||0)>state.notificationEventCursor&&notificationCategory(item)==='security').sort((a,b)=>(Number(a.id)||0)-(Number(b.id)||0));state.notificationEventCursor=Math.max(state.notificationEventCursor,latest);for(const item of fresh){const view=notificationPresentation(item);await dispatchNotificationRule('security_account',view.title,view.message,`security-${item.id}`)}}
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&state.renderPending){state.renderPending=false;render()}});

'''
app = replace_between(app, 'let refreshTimer;\n', 'function renderMetrics', refresh_block, "refresh and runtime notifications")

render_block = '''function rowSignature(t){const key=keyFor(t);return JSON.stringify([t.name,t.size,t.category,t.num_seeds,t.progress,t.amount_left,t.state,t.dlspeed,t.upspeed,t.eta,t.ratio,t._server_name,state.selected.has(key)])}
function rowNode(html){const template=document.createElement('template');template.innerHTML=html.trim();return template.content.firstElementChild}
function renderTorrentRows(list){const tbody=$('#torrentRows'),keys=list.map(keyFor);if(list.length<LARGE_LIBRARY_THRESHOLD){tbody.innerHTML=list.map(rowHtml).join('');state.rowRenderCache=new Map(list.map(t=>[keyFor(t),rowSignature(t)]));state.rowRenderOrder=keys;return}const sameOrder=keys.length===state.rowRenderOrder.length&&keys.every((key,index)=>key===state.rowRenderOrder[index]);if(sameOrder){const rows=[...tbody.children];list.forEach((t,index)=>{const key=keys[index],signature=rowSignature(t);if(state.rowRenderCache.get(key)===signature)return;const node=rowNode(rowHtml(t));rows[index]?.replaceWith(node);state.rowRenderCache.set(key,signature)});return}const existing=new Map([...tbody.children].map(row=>[row.dataset.key,row])),fragment=document.createDocumentFragment(),nextCache=new Map();for(const t of list){const key=keyFor(t),signature=rowSignature(t);let row=existing.get(key);if(!row||state.rowRenderCache.get(key)!==signature)row=rowNode(rowHtml(t));fragment.appendChild(row);nextCache.set(key,signature)}tbody.replaceChildren(fragment);state.rowRenderCache=nextCache;state.rowRenderOrder=keys}
function render(){const list=visibleTorrents();renderTorrentRows(list);$('#empty').classList.toggle('hidden',list.length>0);$('#selectedCount').textContent=state.selected.size;$('#bulkbar').classList.toggle('hidden',!state.selected.size);$('#selectAll').checked=!!list.length&&list.every(t=>state.selected.has(keyFor(t)));updateFilters()}
'''
app = replace_between(app, 'function render(){', 'function rowHtml(t)', render_block, "adaptive row rendering")

# Dialog focus handling.
app = replace_once(app, "function closeActionDialog(result=null){const modal=$('#actionDialogModal');if(modal)modal.classList.add('hidden');const resolve=actionDialogResolve;actionDialogResolve=null;if(resolve)resolve(result)}", "function closeActionDialog(result=null){const modal=$('#actionDialogModal');hideSurface(modal);const resolve=actionDialogResolve;actionDialogResolve=null;if(resolve)resolve(result)}", "action close focus")
app = replace_once(app, "confirm.className=`${options.danger?'danger':'primary'} action-dialog-confirm`;modal.classList.remove('hidden');return new Promise(resolve=>{actionDialogResolve=resolve;setTimeout(()=>{if(actionDialogHasInput){input.focus();input.select()}else confirm.focus()},0)})", "confirm.className=`${options.danger?'danger':'primary'} action-dialog-confirm`;showSurface(modal,actionDialogHasInput?input:confirm);return new Promise(resolve=>{actionDialogResolve=resolve;setTimeout(()=>{if(actionDialogHasInput)input.select()},0)})", "action open focus")
app = replace_once(app, "function closeRemoveDialog(result=null){const modal=$('#removeModal');if(modal)modal.classList.add('hidden');const resolve=removeDialogResolve;removeDialogResolve=null;if(resolve)resolve(result)}", "function closeRemoveDialog(result=null){const modal=$('#removeModal');hideSurface(modal);const resolve=removeDialogResolve;removeDialogResolve=null;if(resolve)resolve(result)}", "remove close focus")
app = replace_once(app, "$('#removeModal').classList.remove('hidden');return new Promise(resolve=>{removeDialogResolve=resolve;setTimeout(()=>$('#removeForm .remove-confirm')?.focus(),0)})", "showSurface('#removeModal','#removeForm .remove-confirm');return new Promise(resolve=>{removeDialogResolve=resolve})", "remove open focus")
app = replace_once(app, "async function openDetail(server,hash){state.detail={server,hash,data:null};state.detailTab='overview';$$('[data-detailtab]').forEach(b=>b.classList.toggle('active',b.dataset.detailtab==='overview'));$('#drawer').classList.remove('hidden');", "async function openDetail(server,hash){state.detail={server,hash,data:null};state.detailTab='overview';$$('[data-detailtab]').forEach(b=>b.classList.toggle('active',b.dataset.detailtab==='overview'));showSurface('#drawer','[data-close]');", "detail open focus")
app = replace_once(app, "function closeDrawer(){$('#drawer').classList.add('hidden');state.detail=null}", "function closeDrawer(){hideSurface('#drawer');state.detail=null}", "detail close focus")

# Event-center presentation for new health/runtime events.
notification_presentation = '''function notificationCategory(item){const event=String(item?.event||'').toLowerCase();if(event==='completed'||event==='torrent_upload'||event.startsWith('torrent_')||event.startsWith('action:'))return'torrents';if(event.startsWith('login_')||event.startsWith('user_')||event.startsWith('account_')||event==='setup_completed')return'security';if(event.startsWith('update_'))return'updates';return'system'}
function notificationPresentation(item){const event=String(item?.event||'').toLowerCase(),category=notificationCategory(item);let title='',message='',tone='neutral';if(event==='completed'){title='Torrent completed';message=`${item.name||'Torrent'} finished downloading${item.server_id&&item.server_id!=='dashboard'?` on ${item.server_id}`:''}.`;tone='good'}else if(event==='torrent_error'){title='Torrent error';message=`${item.name||'Torrent'} entered an error state${item.server_id?` on ${item.server_id}`:''}.`;tone='bad'}else if(event==='torrent_stalled'){title='Torrent stalled';message=`${item.name||'Torrent'} became stalled${item.server_id?` on ${item.server_id}`:''}.`;tone='warn'}else if(event==='client_offline'){title='Client offline';message=`${item.name||item.server_id||'qBitTorrent'} became unreachable.`;tone='bad'}else if(event==='client_recovered'){title='Client recovered';message=`${item.name||item.server_id||'qBitTorrent'} reconnected.`;tone='good'}else if(event==='torrent_upload'){title='Torrent added';message=item.name?`${item.name} was added to ${item.server_id||'qBitTorrent'}.`:'A torrent was added.';tone='good'}else if(event.startsWith('action:')){const action=event.split(':',2)[1]||'action';const labels={delete:'Torrent removed',start:'Torrent resumed',stop:'Torrent paused',recheck:'Torrent rechecked',reannounce:'Torrent reannounced',rename:'Torrent renamed',set_location:'Torrent location changed',set_category:'Torrent category changed'};title=labels[action]||uiText(`torrent ${action}`);message=`Action sent${item.server_id&&item.server_id!=='dashboard'?` to ${item.server_id}`:''}${item.name?` by ${item.name}`:''}.`;tone=action==='delete'?'warn':'neutral'}else if(event==='login_failed'){title='Failed sign-in';message=`A sign-in attempt failed${item.name?` for ${item.name}`:''}.`;tone='bad'}else if(event==='login_success'){title='Signed in';message=`${item.name||'A user'} signed in to Torrent Dashboard.`;tone='good'}else if(event==='account_profile_changed'){title='Account updated';message=`${item.name||'A user'} updated their profile.`;tone='good'}else if(event==='account_password_changed'){title='Password changed';message=`${item.name||'A user'} changed their password.`;tone='good'}else if(event==='account_avatar_changed'){title='Profile picture changed';message=`${item.name||'A user'} updated their profile picture.`;tone='good'}else if(event==='account_avatar_removed'){title='Profile picture removed';message=`${item.name||'A user'} removed their profile picture.`}else if(event==='setup_completed'){title='Setup completed';message='Torrent Dashboard first-run setup was completed.';tone='good'}else if(event==='user_saved'){title='User saved';message=`${item.name||'A user account'} was updated.`}else if(event==='user_deleted'){title='User deleted';message='A dashboard user was removed.';tone='warn'}else if(event==='integration_saved'){title='Integration saved';message=`${item.name||'An integration'} was updated.`}else if(event==='integration_deleted'){title='Integration deleted';message='An integration was removed.';tone='warn'}else if(event==='settings_changed'){title='Settings changed';message=`Dashboard settings were updated${item.name?` by ${item.name}`:''}.`}else if(event==='update_downloaded'){title='Update downloaded';message=item.name?`Version ${item.name} is ready to install.`:'An application update was downloaded.';tone='good'}else if(event==='update_install_started'){title='Update installation started';message=item.name?`Torrent Dashboard is installing version ${item.name}.`:'Torrent Dashboard is installing an update.';tone='good'}else if(event==='notification_sound_changed'){title='Notification sound changed';message=item.name?`${item.name} is now configured.`:'The custom notification sound was changed.'}else{title=uiText(event||'dashboardEvent');message=[item.server_id&&item.server_id!=='dashboard'?item.server_id:'',item.name||''].filter(Boolean).join(' · ')||'Torrent Dashboard recorded an event.'}return{category,title,message,tone}}
'''
app = replace_between(app, 'function notificationCategory(item)', 'function renderNotifications()', notification_presentation, "notification presentation")

server_functions = '''function renderServerSettings(servers){$('#serverSettings').innerHTML='';servers.forEach(s=>addServerRow(s,false));updateServerHealthCards(Object.values(state.clientHealth||{}))}
function addServerRow(s={id:'',name:'',base_url:'http://127.0.0.1:8080',auth_method:'api_key',api_key:'',username:'',password:'',enabled:true},trackDirty=true){
  const d=document.createElement('div');d.className='server-setting';const method=s.auth_method||((s.api_key&&s.api_key!=='')?'api_key':'password');
  d.innerHTML=`<div class="client-health" data-client-health></div><label>Display Name<input data-k="name" placeholder="Desktop" value="${esc(s.name||'')}"></label><label class="server-url">Web UI URL<input data-k="base_url" placeholder="http://127.0.0.1:8080" value="${esc(s.base_url||'')}"></label><label>Authentication<select data-k="auth_method"><option value="api_key" ${method==='api_key'?'selected':''}>API Key</option><option value="password" ${method==='password'?'selected':''}>Username And Password</option></select></label><div class="server-auth-api"><label>API Key<input data-k="api_key" type="password" autocomplete="off" placeholder="${s.api_key==='<configured>'?'API Key Configured':'qbt_…'}"></label><small>qBitTorrent 5.2+ · Bearer Authentication</small></div><div class="server-auth-password two"><label>Username<input data-k="username" autocomplete="off" value="${esc(s.username||'')}"></label><label>Password<input data-k="password" type="password" autocomplete="off" placeholder="${s.password==='<configured>'?'Password Configured':'Password'}"></label></div><div class="server-setting-actions"><button type="button" class="test-server">Test</button><button type="button" class="secondary client-settings" ${s.id?'':'disabled'}>Settings</button><button type="button" class="danger">Remove</button></div><input type="hidden" data-k="id" value="${esc(s.id||'')}"><small class="server-test-result" role="status" aria-live="polite"></small>`;
  const sync=()=>{const useApi=d.querySelector('[data-k="auth_method"]').value==='api_key';d.querySelector('.server-auth-api').classList.toggle('hidden',!useApi);d.querySelector('.server-auth-password').classList.toggle('hidden',useApi)};
  d.querySelector('[data-k="auth_method"]').addEventListener('change',sync);sync();d.querySelector('.danger').onclick=()=>{d.remove();forceDirtyScope('settingsCore')};d.querySelector('.test-server').onclick=()=>testServerRow(d);d.querySelector('.client-settings').onclick=()=>TDSettings.openClientSettings(d.querySelector('[data-k="id"]').value);$('#serverSettings').append(d);applySentenceCaseUi(d);decorateSecretFields(d);renderServerHealth(d,state.clientHealth?.[String(s.id||'')]);if(trackDirty)forceDirtyScope('settingsCore')
}
function renderServerHealth(row,health){const target=row?.querySelector?.('[data-client-health]');if(!target)return;const id=row.querySelector('[data-k="id"]')?.value||'';if(!id){target.className='client-health unsaved';target.innerHTML='<span class="client-health-dot" aria-hidden="true"></span><div><strong>Not saved</strong><small>Save this client to begin health monitoring.</small></div>';return}const status=health?.status||'connecting',online=status==='online';target.className=`client-health ${status}`;let detail='Connecting…';if(online){const auth=health.auth_method==='api_key'?'API Key':'Password',parts=[health.app_version?`qBitTorrent ${health.app_version}`:'qBitTorrent',health.api_version?`Web API ${health.api_version}`:'',auth,health.latency_ms?`${health.latency_ms} ms`:''].filter(Boolean);detail=parts.join(' · ')}else if(status==='offline'){detail=health.error||'Client is unreachable.'}else if(status==='disabled'){detail='Client is disabled.'}const last=health?.last_success?(Date.now()/1000-health.last_success<5?'Last seen now':`Last seen ${rel(health.last_success)}`):(status==='connecting'?'Waiting for first response':'No successful connection recorded');target.innerHTML=`<span class="client-health-dot" aria-hidden="true"></span><div><strong>${esc(uiText(status))}</strong><small title="${esc(detail)}">${esc(detail)}</small><small>${esc(last)}</small></div>`}
function updateServerHealthCards(items){const map=Object.fromEntries((items||[]).map(item=>[String(item.id||''),item]));$$('.server-setting').forEach(row=>{const id=String(row.querySelector('[data-k="id"]')?.value||'');renderServerHealth(row,map[id]||state.clientHealth?.[id])})}
function serverRowData(r){let o={enabled:true};r.querySelectorAll('[data-k]').forEach(i=>o[i.dataset.k]=i.type==='password'?secretFieldValue(i,'<configured>'):i.value);return o}
async function testServerRow(r){const out=r.querySelector('.server-test-result');out.textContent='Testing…';out.className='server-test-result';try{const d=await post('/api/client-test',serverRowData(r));out.textContent=`Connected · qBitTorrent ${d.version||'Unknown'} · Web API ${d.api_version||'Unknown'} · ${serverRowData(r).auth_method==='api_key'?'API Key':'Password'}`;out.className='server-test-result ok'}catch(e){out.textContent=e.message;out.className='server-test-result bad'}}
async function saveSettings(e){return TDSettings.saveCore(e)}

async function loadIntegrations(){return TDSettings.loadIntegrations()}
'''
app = replace_between(app, 'function renderServerSettings(servers)', 'function applyColumnPrefs()', server_functions, "client health cards")

# Account modal dirty-state lifecycle.
account_block = '''async function openAccountModal(target='profile'){
  if(!state.me?.user_id)return toast('This session is not linked to a user account','error');
  showSurface('#accountModal',target==='password'?'#accountNewPassword':'#accountFirstName');
  const status=$('#accountStatus');status.className='test-result muted';status.textContent='Loading account…';
  try{
    await loadAccount();status.textContent='';
    registerDirtyScope('accountProfile','#accountProfileForm',{saveButton:'#accountProfileSave',statusEl:'#accountProfileSaveState'});
    registerDirtyScope('accountPassword','#accountPasswordForm',{saveButton:'#accountPasswordSave',statusEl:'#accountPasswordSaveState'});
    resetDirtyScope('accountProfile');resetDirtyScope('accountPassword');
  }catch(e){status.className='test-result bad';status.textContent=e.message}
}
async function closeAccountModal(force=false){const names=['accountProfile','accountPassword'];if(!force&&!await confirmDiscardScopes(names))return false;clearDirtyScopes(names);hideSurface('#accountModal');$('#accountProfileForm')?.reset();$('#accountPasswordForm')?.reset();$('#accountStatus').textContent='';accountProfileSnapshot=null;return true}
async function saveOwnProfile(e){
  e.preventDefault();
  const status=$('#accountStatus');
  if(!dirtyScopes.get('accountProfile')?.dirty)return;
  const payload={username:$('#accountUsername').value.trim(),first_name:$('#accountFirstName').value.trim(),last_name:$('#accountLastName').value.trim(),email:$('#accountEmail').value.trim()};
  const secureChange=!!accountProfileSnapshot&&(payload.username!==String(accountProfileSnapshot.username||'')||payload.email!==String(accountProfileSnapshot.email||''));
  try{
    if(secureChange&&accountProfileSnapshot?.password_configured){
      const password=await requestPasswordConfirmation('Confirm your password to change your username or email.');
      if(password===null)return;
      payload.current_password=password;
    }
    status.className='test-result muted';status.textContent='Saving profile…';
    const d=await post('/api/account',payload);
    applyAccountUser(d.user);accountProfileSnapshot={...d.user};status.className='test-result ok';status.textContent='Profile saved.';resetDirtyScope('accountProfile',true);
  }catch(e){status.className='test-result bad';status.textContent=e.message}
}
async function changeOwnPassword(e){
  e.preventDefault();
  const next=$('#accountNewPassword').value,confirmPassword=$('#accountConfirmPassword').value,status=$('#accountStatus');
  if(!dirtyScopes.get('accountPassword')?.dirty)return;
  if(next!==confirmPassword){status.className='test-result bad';status.textContent='New passwords do not match.';return}
  try{
    let current='';
    if(accountProfileSnapshot?.password_configured){
      const confirmed=await requestPasswordConfirmation('Confirm your password to change it.');
      if(confirmed===null)return;
      current=confirmed;
    }
    status.className='test-result muted';status.textContent='Changing password…';
    await post('/api/account/password',{current_password:current,new_password:next});
    $('#accountPasswordForm').reset();status.className='test-result ok';status.textContent='Password changed.';resetDirtyScope('accountPassword',true);
  }catch(e){status.className='test-result bad';status.textContent=e.message}
}
'''
app = replace_between(app, "async function openAccountModal(target='profile')", 'async function uploadOwnAvatar()', account_block, "account dirty lifecycle")

app = replace_once(app, "function closePasswordConfirmation(result=null){const modal=$('#passwordConfirmModal');modal?.classList.add('hidden');", "function closePasswordConfirmation(result=null){const modal=$('#passwordConfirmModal');hideSurface(modal);", "password confirmation close focus")
app = replace_once(app, "modal?.classList.remove('hidden');return new Promise(resolve=>{passwordConfirmationResolve=resolve;setTimeout(()=>input?.focus(),0)})", "showSurface(modal,input);return new Promise(resolve=>{passwordConfirmationResolve=resolve})", "password confirmation open focus")

# Load health into the selector and settings cards.
app = replace_once(
    app,
    "async function loadServers(){const d=await api('/api/servers');const sel=$('#serverSelect');sel.innerHTML='<option value=\"all\">allServers</option>'+d.servers.filter(s=>s.enabled).map(s=>`<option value=\"${esc(s.id)}\">${esc(s.name)}</option>`).join('');sel.value=state.server}",
    "async function loadServers(){const d=await api('/api/servers');updateClientHealth(d.servers||[]);const sel=$('#serverSelect');sel.innerHTML='<option value=\"all\">allServers</option>'+d.servers.filter(s=>s.enabled).map(s=>`<option value=\"${esc(s.id)}\">${esc(s.name)}</option>`).join('');if(![...sel.options].some(o=>o.value===state.server))state.server='all';sel.value=state.server}",
    "load servers health",
)

# Update available is a notification rule event, deduplicated by version.
app = replace_once(
    app,
    "async function checkForUpdates(silent=false){try{const d=await api('/api/update-check');renderUpdateInfo(d);if(!silent&&d.updateAvailable)toast(`updateAvailable ${d.manifest.version}`);else if(!silent&&!d.error)toast(d.configured===false?'updatesNotConfigured':'updateCheckComplete');return d}catch(e){renderUpdateInfo({currentVersion:state.me?.version,error:e.message,state:state.settings?.runtime?.updateState||{}});if(!silent)toast(e.message,'error');throw e}}",
    "async function checkForUpdates(silent=false){try{const d=await api('/api/update-check');renderUpdateInfo(d);if(d.updateAvailable&&d.manifest?.version&&state.notifiedUpdateVersion!==d.manifest.version){state.notifiedUpdateVersion=d.manifest.version;dispatchNotificationRule('update_available','Update available',`Torrent Dashboard ${d.manifest.version} is available.`,`update-${d.manifest.version}`).catch(()=>{})}if(!silent&&d.updateAvailable)toast(`updateAvailable ${d.manifest.version}`);else if(!silent&&!d.error)toast(d.configured===false?'updatesNotConfigured':'updateCheckComplete');return d}catch(e){renderUpdateInfo({currentVersion:state.me?.version,error:e.message,state:state.settings?.runtime?.updateState||{}});if(!silent)toast(e.message,'error');throw e}}",
    "update available notification",
)

# Rebind navigation/modals with async discard protection and focus trapping.
bind_ui = '''function bindUI(){if(bound)return;bound=true;
  $$('.nav-root,.settings-subnav button,.mobile-nav button').forEach(b=>b.addEventListener('click',()=>{setView(b.dataset.view)}));
  $$('#tabs button').forEach(b=>b.classList.toggle('active',b.dataset.filter===state.filter));$$('#tabs button').forEach(b=>b.addEventListener('click',()=>{state.filter=b.dataset.filter;localStorage.tdFilter=state.filter;$$('#tabs button').forEach(x=>x.classList.toggle('active',x===b));render()}));
  $('#search').value=state.search;$('#search').addEventListener('input',e=>{state.search=e.target.value.trim().toLowerCase();localStorage.tdSearch=state.search;render()});
  $('#categoryFilter').addEventListener('change',e=>{state.category=e.target.value;localStorage.tdCategory=state.category;render()});
  $('#tagFilter').addEventListener('change',e=>{state.tag=e.target.value;localStorage.tdTag=state.tag;render()});
  $('#trackerFilter').addEventListener('change',e=>{state.tracker=e.target.value;localStorage.tdTracker=state.tracker;render()});
  $('#sort').value=state.sort;$('#sort').addEventListener('change',e=>{state.sort=e.target.value;localStorage.tdSort=state.sort;render()});
  $('#serverSelect').addEventListener('change',async e=>{state.server=e.target.value;state.selected.clear();await refreshStatus();if(!['all'].includes(state.server))await loadMeta();if($('#view-notifications')?.classList.contains('active'))renderNotifications()});
  $('#selectAll').addEventListener('change',e=>{visibleTorrents().forEach(t=>e.target.checked?state.selected.add(keyFor(t)):state.selected.delete(keyFor(t)));render()});
  $('#torrentRows').addEventListener('click',rowClick);$('#torrentRows').addEventListener('change',rowChange);$('#torrentRows').addEventListener('contextmenu',rowContext);
  $('#bulkbar').addEventListener('click',e=>{if(e.target.closest('[data-bulk-clear]')){state.selected.clear();render();return}const a=e.target.closest('[data-bulk]')?.dataset.bulk;if(a)bulkAction(a)});
  $('#addLinkBtn').addEventListener('click',()=>openAddTorrent('link'));$('#addFileBtn').addEventListener('click',()=>openAddTorrent('file'));$$('[data-modalclose]').forEach(x=>x.addEventListener('click',()=>{hideSurface('#addModal');$('#addForm')?.reset()}));$('#addForm').addEventListener('submit',addTorrent);$('#removeForm')?.addEventListener('submit',e=>{e.preventDefault();closeRemoveDialog({deleteFiles:!!$('#removeFiles')?.checked})});$$('[data-remove-cancel]').forEach(x=>x.addEventListener('click',()=>closeRemoveDialog(null)));
  $$('[data-close]').forEach(x=>x.addEventListener('click',closeDrawer));$$('[data-detailtab]').forEach(x=>x.addEventListener('click',()=>{state.detailTab=x.dataset.detailtab;$$('[data-detailtab]').forEach(b=>b.classList.toggle('active',b===x));renderDetail()}));
  $('#profileBtn').addEventListener('click',e=>{showMenu($('#accountMenu'),e.currentTarget);e.currentTarget.setAttribute('aria-expanded','true')});document.addEventListener('click',e=>{if(!e.target.closest('.menu')&&!e.target.closest('#profileBtn')&&!e.target.closest('.more-row')){$$('.menu').forEach(m=>m.classList.add('hidden'));$('#profileBtn')?.setAttribute('aria-expanded','false')}});
  $('#accountSettingsBtn').addEventListener('click',()=>{hideAccountMenu();openAccountModal('profile')});$('#logoutBtn').addEventListener('click',()=>{hideAccountMenu();signOut()});$$('[data-account-close]').forEach(x=>x.addEventListener('click',()=>closeAccountModal()));$('#accountProfileForm').addEventListener('submit',saveOwnProfile);$('#accountPasswordForm').addEventListener('submit',changeOwnPassword);$('#accountChooseAvatar').addEventListener('click',()=>$('#accountAvatarInput').click());$('#accountAvatarInput').addEventListener('change',uploadOwnAvatar);$('#accountRemoveAvatar').addEventListener('click',removeOwnAvatar);bindPasswordConfirmation();
  $('#pauseAllBtn').addEventListener('click',()=>globalAction('stop'));$('#resumeAllBtn').addEventListener('click',()=>globalAction('start'));
  $('#notificationFilter')?.addEventListener('change',renderNotifications);$('#refreshNotifications')?.addEventListener('click',loadNotifications);
  if(state.me?.can_manage)TDSettings.bind();
  window.addEventListener('keydown',async e=>{if(e.key==='Tab'&&trapSurfaceFocus(e))return;if(e.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){e.preventDefault();$('#search').focus()}if(e.key==='Escape'){if(!$('#passwordConfirmModal')?.classList.contains('hidden')){closePasswordConfirmation(null);return}if(!$('#clientSettingsModal')?.classList.contains('hidden')){await TDSettings.closeClientSettings();return}if(!$('#accountModal')?.classList.contains('hidden')){await closeAccountModal();return}if(!$('#accountMenu')?.classList.contains('hidden')){hideAccountMenu();return}if(!$('#actionDialogModal')?.classList.contains('hidden')){closeActionDialog(null);return}if(!$('#removeModal')?.classList.contains('hidden')){closeRemoveDialog(null);return}if(state.selected.size){state.selected.clear();render();return}closeDrawer();hideSurface('#addModal')}});
}

'''
app = replace_between(app, 'function bindUI(){', 'function setSettingsNavExpanded', bind_ui, "bind UI accessibility")

set_view = '''function setSettingsNavExpanded(expanded){const group=$('#settingsNavGroup'),submenu=$('#settingsSubnav');if(!group||!submenu)return;group.classList.toggle('expanded',!!expanded);submenu.classList.toggle('hidden',!expanded)}
async function setView(view){if(view==='settings'&&!state.me?.can_manage){view='dashboard';toast('Administrator Access Is Required','error')}const current=$('.view.active')?.id?.replace('view-','')||'dashboard',settingsView=view==='settings';if(current==='settings'&&!settingsView&&TDSettings.dirtyScopeNames){const names=TDSettings.dirtyScopeNames();if(names.length&&!await confirmDiscardScopes(names))return false}$$('.view').forEach(v=>v.classList.toggle('active',v.id===`view-${view}`));$$('.nav-root,.mobile-nav button').forEach(b=>b.classList.toggle('active',b.dataset.view===view));setSettingsNavExpanded(settingsView);$('#pageTitle').textContent=uiText(view);$('#subtitle').textContent=uiText(view==='dashboard'?'liveTorrentActivity':view==='notifications'?'recentDashboardActivity':'dashboardConfiguration');if(view==='notifications')loadNotifications();if(settingsView){TDSettings.activate(localStorage.tdSettingsPage||'general');if(current!=='settings'){await loadSettings();await TDSettings.loadExtras()}}return true}

'''
app = replace_between(app, 'function setSettingsNavExpanded', 'async function loadServers()', set_view, "settings navigation guard")

app = replace_once(app, "async function signOut(){try{await post('/api/logout',{})}catch{}location.reload()}", "async function signOut(){const names=dirtyScopeNames();if(names.length&&!await confirmDiscardScopes(names))return;try{await post('/api/logout',{})}catch{}location.reload()}", "sign out dirty guard")

# Standard Users receive the same safe notification-rule configuration.
app = replace_once(app, "if(state.me.can_manage){await loadSettings()}else{state.settings={dashboard:{low_disk_gb:20},notifications:{browser:false,sound:false}}}", "if(state.me.can_manage){await loadSettings()}else{state.settings={dashboard:{low_disk_gb:20},notifications:state.me.notifications||{browser:false,sound:false,rules:{}}}}", "standard user notifications")
write("static/app.js", app)


# ---------------------------------------------------------------------------
# Settings module: dirty/save state, client tabs/focus, rule editor, and
# per-card dirty state without reloading other unsaved cards.
# ---------------------------------------------------------------------------
settings = read("static/settings.js")
settings = replace_once(settings, "  let clientSettingsServerId = '';\n", "  let clientSettingsServerId = '';\n  let localDirtySerial = 0;\n", "settings dirty serial")

bind_function = '''  function bind() {
    if (bound) return;
    bound = true;
    document.querySelectorAll('[data-settings-page]').forEach(btn => btn.addEventListener('click', () => activate(btn.dataset.settingsPage)));
    document.querySelector('#settingsMobilePage')?.addEventListener('change', e => activate(e.target.value));
    document.querySelector('#settingsForm')?.addEventListener('submit', saveCore);
    document.querySelector('#copyLocalAddress')?.addEventListener('click', () => navigator.clipboard.writeText(document.querySelector('#localDashboardUrl')?.textContent || '').then(() => toast('addressCopied')));
    document.querySelector('#sPort')?.addEventListener('input', updateLocalAddress);
    document.querySelector('#sRefreshInterfaces')?.addEventListener('click', () => refreshSettingsInterfaces(true).catch(e => toast(e.message,'error')));
    document.querySelector('#addServerSetting')?.addEventListener('click', () => addServerRow());
    document.querySelector('#clientSettingsForm')?.addEventListener('submit', saveClientSettings);
    document.querySelectorAll('[data-client-settings-close]').forEach(el => el.addEventListener('click', () => closeClientSettings()));
    document.querySelectorAll('[data-client-settings-tab]').forEach(el => {
      el.addEventListener('click', () => activateClientSettingsTab(el.dataset.clientSettingsTab));
      el.addEventListener('keydown', event => {
        if (!['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) return;
        event.preventDefault();
        const tabs=[...document.querySelectorAll('[data-client-settings-tab]')],index=tabs.indexOf(el);
        const next=event.key==='Home'?0:event.key==='End'?tabs.length-1:(index+(event.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;
        activateClientSettingsTab(tabs[next].dataset.clientSettingsTab);tabs[next].focus();
      });
    });
    document.querySelector('#clientRandomPort')?.addEventListener('change', syncClientSettingsControls);
    document.querySelector('#clientProxyType')?.addEventListener('change', syncClientSettingsControls);
    document.querySelector('#clientProxyAuth')?.addEventListener('change', syncClientSettingsControls);
    document.querySelector('#updateAction')?.addEventListener('click', handleUpdateAction);
    document.querySelector('#nSoundMode')?.addEventListener('change', updateNotificationSoundUi);
    document.querySelector('#nSoundFile')?.addEventListener('change', updateNotificationSoundUi);
    document.querySelector('#testNotification')?.addEventListener('click', testNotification);
    document.querySelector('#testNotificationSound')?.addEventListener('click', testNotificationSound);
    document.querySelector('#addIntegrationSetting')?.addEventListener('click', addIntegration);
    document.querySelector('#addUserSetting')?.addEventListener('click', addUser);
    registerDirtyScope('settingsCore','#settingsForm',{saveButton:'#settingsSaveButton',statusEl:'#settingsSaveState'});
    resetDirtyScope('settingsCore');
    activate(localStorage.tdSettingsPage || 'general');
  }

'''
settings = replace_between(settings, '  function bind() {\n', '  function setClientSettingsStatus', bind_function, "settings bind")

settings = replace_between(
    settings,
    "  function activateClientSettingsTab(tab='speed') {\n",
    '  function syncClientSettingsControls()',
'''  function activateClientSettingsTab(tab='speed') {
    const allowed = new Set(['speed','connection','proxy']);
    if (!allowed.has(tab)) tab = 'speed';
    document.querySelectorAll('[data-client-settings-tab]').forEach(el => {const active=el.dataset.clientSettingsTab===tab;el.classList.toggle('active',active);el.setAttribute('aria-selected',String(active));el.tabIndex=active?0:-1;});
    document.querySelectorAll('[data-client-settings-pane]').forEach(el => {const active=el.dataset.clientSettingsPane===tab;el.classList.toggle('active',active);el.hidden=!active;});
  }

''',
    "client tab behavior",
)

client_lifecycle = '''  async function closeClientSettings(force=false) {
    if (!force && !await confirmDiscardScopes(['clientSettings'])) return false;
    resetDirtyScope('clientSettings');
    hideSurface('#clientSettingsModal');
    clientSettingsServerId = '';
    setClientSettingsStatus('');
    return true;
  }

  async function openClientSettings(serverId) {
    serverId = String(serverId || '').trim();
    if (!serverId) return toast('Save the client before opening Settings.','error');
    const server = (state.settings?.servers || []).find(item => String(item.id || '') === serverId);
    clientSettingsServerId = serverId;
    const name = document.querySelector('#clientSettingsClientName');
    if (name) name.textContent = `${server?.name || serverId} · qBitTorrent`;
    activateClientSettingsTab('speed');
    showSurface('#clientSettingsModal','[data-client-settings-tab="speed"]');
    setClientSettingsStatus('Loading…');
    const button=document.querySelector('#saveClientSettings');if(button)button.disabled=true;
    try {
      const data = await api(`/api/client-settings?server=${encodeURIComponent(serverId)}`);
      fillClientSettings(data.settings || {});
      registerDirtyScope('clientSettings','#clientSettingsForm',{saveButton:'#saveClientSettings',statusEl:'#clientSettingsSaveState'});
      resetDirtyScope('clientSettings');
      setClientSettingsStatus('');
    } catch (e) {
      setClientSettingsStatus(e.message || 'Could not load settings.', 'bad');
    }
  }

  function clientNumber(id, fallback=0) {
    const value = Number(document.querySelector('#'+id)?.value ?? fallback);
    return Number.isFinite(value) ? Math.trunc(value) : NaN;
  }

  async function saveClientSettings(e) {
    if (e?.preventDefault) e.preventDefault();
    if (!clientSettingsServerId || !dirtyScopes.get('clientSettings')?.dirty) return;
    const passwordInput=document.querySelector('#clientProxyPassword');
    let proxyPassword='';
    try { proxyPassword=secretFieldValue(passwordInput,'<configured>'); } catch(err) { return setClientSettingsStatus(err.message,'bad'); }
    const payload={
      server:clientSettingsServerId,
      speed:{alternative_enabled:!!document.querySelector('#clientAltSpeed')?.checked,download_limit_kb:clientNumber('clientGlobalDl'),upload_limit_kb:clientNumber('clientGlobalUl'),alternative_download_limit_kb:clientNumber('clientAltDl'),alternative_upload_limit_kb:clientNumber('clientAltUl')},
      connection:{listen_port:clientNumber('clientListenPort'),random_port:!!document.querySelector('#clientRandomPort')?.checked,upnp:!!document.querySelector('#clientUpnp')?.checked,max_connections:clientNumber('clientMaxConnections'),max_connections_per_torrent:clientNumber('clientMaxConnectionsTorrent'),max_upload_slots:clientNumber('clientMaxUploads'),max_upload_slots_per_torrent:clientNumber('clientMaxUploadsTorrent')},
      proxy:{type:document.querySelector('#clientProxyType')?.value||'none',host:document.querySelector('#clientProxyHost')?.value.trim()||'',port:clientNumber('clientProxyPort'),authentication:!!document.querySelector('#clientProxyAuth')?.checked,username:document.querySelector('#clientProxyUsername')?.value.trim()||'',password:proxyPassword,hostname_lookup:!!document.querySelector('#clientProxyLookup')?.checked,bittorrent:!!document.querySelector('#clientProxyBittorrent')?.checked,peer_connections:!!document.querySelector('#clientProxyPeers')?.checked}
    };
    const numeric=[payload.speed.download_limit_kb,payload.speed.upload_limit_kb,payload.speed.alternative_download_limit_kb,payload.speed.alternative_upload_limit_kb,payload.connection.max_connections,payload.connection.max_connections_per_torrent,payload.connection.max_upload_slots,payload.connection.max_upload_slots_per_torrent];
    if (!payload.connection.random_port) numeric.push(payload.connection.listen_port);
    if (payload.proxy.type !== 'none') numeric.push(payload.proxy.port);
    if (numeric.some(x => Number.isNaN(x))) return setClientSettingsStatus('Enter whole numbers for limits and ports.', 'bad');
    const button = document.querySelector('#saveClientSettings');
    if (button) button.disabled = true;
    setClientSettingsStatus('Saving…');
    try {
      const data=await post('/api/client-settings',payload);
      fillClientSettings(data.settings || {});
      resetDirtyScope('clientSettings',true);
      setClientSettingsStatus('');
      if (state.server === clientSettingsServerId) await loadMeta();
    } catch (err) {
      setClientSettingsStatus(err.message || 'Could not save settings.', 'bad');
      syncDirtyScope('clientSettings');
    }
  }

'''
settings = replace_between(settings, '  function closeClientSettings() {\n', '  function updateLocalAddress()', client_lifecycle, "client settings lifecycle")

fill_and_save = '''  function fill(s) {
    if (!s) return;
    const setValue = (id, value) => { const el=document.querySelector('#'+id); if(el) el.value=value ?? ''; };
    const setChecked = (id, value) => { const el=document.querySelector('#'+id); if(el) el.checked=!!value; };
    setValue('sTitle', s.dashboard?.title || 'Torrent Dashboard');
    setValue('sLocalIp', s.runtime?.local_ip || state.me?.lan_ip || '127.0.0.1');
    setValue('sPort', s.dashboard?.port || state.me?.port || 8765);
    updateLocalAddress();
    setValue('sAuth', s.auth?.mode || 'required');
    setValue('sTrustedIps', (s.auth?.trusted_ips || []).join('\n'));
    renderInterfaceList('#sInterfaceList', s.runtime?.network_interfaces || [], s.auth?.trusted_interfaces || [], false);
    state.settingsInterfaceSelectionInitialized = true;

    setValue('sTheme', localStorage.tdTheme || 'dark');
    setValue('sDensity', localStorage.tdDensity || 'comfortable');
    setValue('sAccent', localStorage.tdAccent || '#72a9ff');
    let cols = JSON.parse(localStorage.tdColumns || '{}');
    document.querySelectorAll('[data-column]').forEach(x => x.checked = cols[x.dataset.column] !== false);

    const updateRepository = s.updates?.repository || '';
    setValue('uRepository', updateRepository);
    renderUpdateInfo({configured:!!updateRepository,repository:updateRepository,currentVersion:state.me?.version,state:s.runtime?.updateState||{}});

    renderServerSettings(s.servers || []);
    [...document.querySelectorAll('.server-setting')].forEach((row, index) => {
      const server = (s.servers || [])[index] || {};
      configuredSecret(row.querySelector('[data-k="api_key"]'), server.api_key === '<configured>', 'qbt_…');
      configuredSecret(row.querySelector('[data-k="password"]'), server.password === '<configured>', 'Password');
    });
    const n = s.notifications || {};
    const rules=n.rules||{};
    document.querySelectorAll('[data-notification-rule]').forEach(input=>{const rule=rules[input.dataset.notificationRule]||{};input.checked=!!rule[input.dataset.notificationChannel]});
    setValue('nSoundMode', n.sound_mode || 'default');
    const soundFile = document.querySelector('#nSoundFile');
    if (soundFile) soundFile.value = '';
    const soundName = document.querySelector('#nCustomSoundName');
    if (soundName) soundName.textContent = n.custom_sound_name || 'None uploaded';
    updateNotificationSoundUi();
    activate(localStorage.tdSettingsPage || 'general');
    if(dirtyScopes.has('settingsCore'))resetDirtyScope('settingsCore');
  }

  function notificationRulesData(){const rules={};document.querySelectorAll('[data-notification-rule]').forEach(input=>{const key=input.dataset.notificationRule,channel=input.dataset.notificationChannel;(rules[key]??={browser:false,sound:false})[channel]=!!input.checked});return rules}

  async function saveCore(e) {
    if (e?.preventDefault) e.preventDefault();
    if (!dirtyScopes.get('settingsCore')?.dirty) return;
    const activePage = document.querySelector('.settings-page.active')?.dataset.settingsSection || 'general';
    if (activePage === 'updates') return saveUpdateSource();
    const servers = [...document.querySelectorAll('.server-setting')].map(serverRowData);
    const payload = {
      dashboard: {title: document.querySelector('#sTitle')?.value || 'Torrent Dashboard',port: Number(document.querySelector('#sPort')?.value || 8765)},
      auth: {mode: document.querySelector('#sAuth')?.value || 'required',trusted_interfaces: selectedInterfaceIds('#sInterfaceList'),trusted_ips: parseWhitelist('#sTrustedIps')},
      servers,
      notifications: {sound_mode: document.querySelector('#nSoundMode')?.value || 'default',rules:notificationRulesData()}
    };
    try {
      await uploadNotificationSoundIfNeeded();
      const d = await post('/api/settings', payload);
      state.settings = d.settings;
      localStorage.tdTheme = document.querySelector('#sTheme')?.value || 'dark';
      localStorage.tdDensity = document.querySelector('#sDensity')?.value || 'comfortable';
      localStorage.tdAccent = document.querySelector('#sAccent')?.value || '#72a9ff';
      const cols = {};document.querySelectorAll('[data-column]').forEach(x => cols[x.dataset.column] = x.checked);localStorage.tdColumns = JSON.stringify(cols);
      applyPrefs();fill(state.settings);resetDirtyScope('settingsCore',true);await loadServers();await refreshStatus();
    } catch (err) {toast(err.message,'error');syncDirtyScope('settingsCore')}
  }

'''
settings = replace_between(settings, '  function fill(s) {\n', '  function updateNotificationSoundUi()', fill_and_save, "settings fill and save")

notification_tests = '''  async function testNotification() {
    const status = document.querySelector('#soundStatus');
    try {
      if (status) { status.className='test-result muted'; status.textContent='Testing…'; }
      if (!('Notification' in window)) throw new Error('Browser notifications are not supported by this browser.');
      let permission=Notification.permission;
      if (permission==='default') permission=await Notification.requestPermission();
      if (permission!=='granted') throw new Error(permission==='denied' ? "Browser notification permission is blocked. Enable it in this site's browser permissions." : 'Browser notification permission was not granted.');
      await showBrowserNotification(state.settings?.dashboard?.title || 'Torrent Dashboard',{body:'Test notification from Torrent Dashboard.',tag:'torrent-dashboard-test'});
      if (status) { status.className='test-result ok'; status.textContent='Test successful.'; }
    } catch(e) {if (status) { status.className='test-result bad'; status.textContent=e.message || 'Notification test failed.'; }}
  }

  async function testNotificationSound() {
    const status=document.querySelector('#soundStatus'),mode=document.querySelector('#nSoundMode')?.value||'default',file=document.querySelector('#nSoundFile')?.files?.[0];let url='',revoke=false;
    try{
      if(status){status.className='test-result muted';status.textContent='Testing…'}
      if(mode==='custom'&&file){url=URL.createObjectURL(file);revoke=true}else if(mode==='custom')url=`/api/notification-sound?ts=${Date.now()}`;else url=`/static/default-completion.wav?v=${encodeURIComponent(state.me?.version||'')}`;
      await playSoundUrl(url);if(status){status.className='test-result ok';status.textContent='Test successful.'}
    }catch(e){if(status){status.className='test-result bad';status.textContent=e.message||'Sound test failed.'}}finally{if(revoke)URL.revokeObjectURL(url)}
  }

'''
settings = replace_between(settings, '  async function testNotification() {\n', '  function updateSourceRepository()', notification_tests, "notification tests")

settings = replace_once(
    settings,
    "      toast('updateSourceSaved');\n      return d;",
    "      resetDirtyScope('settingsCore',true);\n      return d;",
    "update source dirty reset",
)

# Rewrite integration/user card lifecycle so saving one card never discards
# edits in another card.
card_lifecycle = '''  function cardDirtyKey(kind,item){if(!item._dirtyKey)item._dirtyKey=`${kind}:${item.id||`new-${++localDirtySerial}`}`;return item._dirtyKey}
  function renderIntegrations() {
    const list = document.querySelector('#integrationList');
    if (!list) return;
    for(const name of dirtyScopeNames(name=>name.startsWith('integration:')))unregisterDirtyScope(name);
    if (!integrations.length) {list.innerHTML = '<div class="settings-empty"><b>No integrations</b><span>Choose a type above to add one.</span></div>';return;}
    list.innerHTML = '';
    integrations.forEach((item, index) => {
      const type = catalog.find(x => x.type === item.type);if (!type) return;
      const key=cardDirtyKey('integration',item),card = document.createElement('article');card.className = 'settings-accordion integration-item';card.dataset.id = item.id || '';card.dataset.type = item.type;card.dataset.dirtyScope=key;
      const fields = (type.fields || []).map(f => fieldHtml(f, item[f.key], item.configured_secrets?.includes(f.key))).join(''),subtitle = integrationSubtitle(item, type);
      card.innerHTML = `<button class="accordion-summary" type="button" aria-expanded="${index===0?'true':'false'}"><span><b>${esc(integrationLabel(item))}</b>${subtitle?`<small>${esc(subtitle)}</small>`:''}</span><span class="accordion-chevron">⌄</span></button><div class="accordion-body ${index===0?'':'hidden'}"><div class="settings-form-grid"><label>Display Name<input data-field="name" value="${esc(item.name||type.label)}" maxlength="128"></label>${fields}<label class="toggle"><input data-field="enabled" type="checkbox" ${item.enabled!==false?'checked':''}><span>Enabled</span></label></div><div class="settings-inline-actions"><span class="form-save-state integration-save-state" role="status" aria-live="polite"></span><button class="secondary integration-test" type="button">Test</button><button class="primary integration-save" type="button" disabled>Save</button><button class="danger integration-delete" type="button">Delete</button></div><div class="test-result muted integration-result" role="status" aria-live="polite"></div></div>`;
      const summary = card.querySelector('.accordion-summary');summary.addEventListener('click', () => {const body = card.querySelector('.accordion-body'),open = body.classList.contains('hidden');body.classList.toggle('hidden', !open);summary.setAttribute('aria-expanded', String(open));});
      card.querySelector('.integration-test').addEventListener('click', () => testIntegration(card));card.querySelector('.integration-save').addEventListener('click', () => saveIntegration(card,item));card.querySelector('.integration-delete').addEventListener('click', () => deleteIntegration(card, item));list.appendChild(card);decorateSecretFields(card);applySentenceCaseUi(card);registerDirtyScope(key,card,{saveButton:card.querySelector('.integration-save'),statusEl:card.querySelector('.integration-save-state'),forceDirty:!!item._new});
    });
  }

  function integrationData(card) {const data = {id: card.dataset.id || '', type: card.dataset.type};card.querySelectorAll('[data-field]').forEach(input => {data[input.dataset.field] = input.type === 'checkbox' ? input.checked : (input.dataset.secret==='1' ? secretFieldValue(input,'<configured>') : input.value.trim());});return data;}

  async function loadIntegrations() {try {const d = await api('/api/integrations');catalog = d.types || [];integrations = d.integrations || [];const select = document.querySelector('#integrationTypeSelect');if (select) select.innerHTML = '<option value="">Choose integration…</option>' + catalog.map(x => `<option value="${esc(x.type)}">${esc(x.label)}</option>`).join('');renderIntegrations();} catch (e) {toast(e.message,'error')}}

  function addIntegration() {const select = document.querySelector('#integrationTypeSelect'),type = catalog.find(x => x.type === select?.value);if (!type) return toast('Choose an integration type.','error');integrations.unshift({id:'',type:type.type,name:type.label,enabled:true,_new:true,configured_secrets:[]});renderIntegrations();if (select) select.value='';}

  async function testIntegration(card) {const out = card.querySelector('.integration-result');out.className='test-result muted integration-result';out.textContent='Testing…';try {const d = await post('/api/integration-test', integrationData(card));out.className='test-result ok integration-result';out.textContent=d.message || 'Connected';} catch (e) {out.className='test-result bad integration-result';out.textContent=e.message;}}

  async function saveIntegration(card,item) {
    const key=card.dataset.dirtyScope;if(!dirtyScopes.get(key)?.dirty)return;
    try {const d = await post('/api/integrations', integrationData(card));Object.assign(item,d.integration||{}, {_new:false,_dirtyKey:key});card.dataset.id=item.id||'';const type=catalog.find(x=>x.type===item.type);card.querySelector('.accordion-summary b').textContent=integrationLabel(item);const small=card.querySelector('.accordion-summary small');const subtitle=integrationSubtitle(item,type);if(small){small.textContent=subtitle;small.classList.toggle('hidden',!subtitle)}for(const field of type?.fields||[]){if(field.secret)configuredSecret(card.querySelector(`[data-field="${field.key}"]`),item.configured_secrets?.includes(field.key),field.placeholder||'')}resetDirtyScope(key,true);return d;} catch (e) {toast(e.message,'error');syncDirtyScope(key)}
  }

  async function deleteIntegration(card, item) {const confirmed = await showActionDialog({input:false,title:'Delete integration',message:`Delete “${integrationLabel(item)}”?`,confirmLabel:'Delete',danger:true});if (!confirmed) return;const key=card.dataset.dirtyScope;if (!card.dataset.id) {integrations = integrations.filter(x => x !== item);unregisterDirtyScope(key);card.remove();if(!integrations.length)renderIntegrations();return;}try {await post('/api/integrations/delete',{id:card.dataset.id});integrations=integrations.filter(x=>x!==item);unregisterDirtyScope(key);card.remove();toast('integrationDeleted');if(!integrations.length)renderIntegrations();} catch (e) {toast(e.message,'error')}}

  function userName(user) {const full = [user.first_name,user.last_name].filter(Boolean).join(' ').trim();return full || user.username || 'User';}

  function renderUsers() {
    const list = document.querySelector('#userList');if (!list) return;for(const name of dirtyScopeNames(name=>name.startsWith('user:')))unregisterDirtyScope(name);
    if (!users.length) {list.innerHTML='<div class="settings-empty"><b>No users</b><span>Add an administrator to manage Torrent Dashboard.</span></div>';return;}
    list.innerHTML='';users.forEach((user,index) => {const key=cardDirtyKey('user',user),card=document.createElement('article');card.className='settings-accordion user-item';card.dataset.id=user.id||'';card.dataset.dirtyScope=key;const group=user.group==='administrator'?'Administrator':'Standard User',current=user.id && user.id===currentUserId,display=userName(user),username=user.username||'New User',showUsername=!!user.username && display!==user.username;
      card.innerHTML=`<button class="accordion-summary" type="button" aria-expanded="${index===0?'true':'false'}"><span><span class="user-name-line"><b>${esc(display)}</b>${current?'<span class="current-user-badge">Current user</span>':''}</span>${showUsername?`<small>${esc(username)}</small>`:''}</span><span class="user-group-badge ${user.group==='administrator'?'admin':'standard'}">${esc(group)}</span><span class="accordion-chevron">⌄</span></button><div class="accordion-body ${index===0?'':'hidden'}"><div class="settings-form-grid two-col"><label><span class="field-label">Username <span class="required-mark" aria-hidden="true">*</span></span><input data-user-field="username" value="${esc(user.username||'')}" maxlength="128" autocomplete="off" required></label><label><span class="field-label">Role <span class="required-mark" aria-hidden="true">*</span></span><select class="user-group-select" data-user-field="group" required><option value="administrator" ${user.group==='administrator'?'selected':''}>Administrator</option><option value="standard" ${user.group==='standard'?'selected':''}>Standard User</option></select></label><label>First Name<input data-user-field="first_name" value="${esc(user.first_name||'')}" maxlength="128"></label><label>Last Name<input data-user-field="last_name" value="${esc(user.last_name||'')}" maxlength="128"></label><label class="full-field">Email<input data-user-field="email" type="email" value="${esc(user.email||'')}" maxlength="254"></label><label><span class="field-label">Password <span class="required-mark" aria-hidden="true">*</span></span><input data-user-field="password" type="password" autocomplete="new-password" required ${user._new?'placeholder="Create Password"':'class="secret-configured" data-configured-secret="1" value="'+SECRET_MASK+'"'}></label><label><span class="field-label">Confirm Password <span class="required-mark" aria-hidden="true">*</span></span><input data-user-field="password2" type="password" autocomplete="new-password" required ${user._new?'placeholder="Confirm Password"':'class="secret-configured" data-configured-secret="1" value="'+SECRET_MASK+'"'}></label></div><div class="settings-inline-actions"><span class="form-save-state user-save-state" role="status" aria-live="polite"></span><button class="primary user-save" type="button" disabled>Save</button><button class="danger user-delete" type="button" ${current?'disabled':''}>Delete</button></div></div>`;
      const summary=card.querySelector('.accordion-summary');summary.addEventListener('click',()=>{const body=card.querySelector('.accordion-body'),open=body.classList.contains('hidden');body.classList.toggle('hidden',!open);summary.setAttribute('aria-expanded',String(open))});card.querySelector('.user-save').addEventListener('click',()=>saveUser(card,user));card.querySelector('.user-delete').addEventListener('click',()=>deleteUser(card,user));list.appendChild(card);decorateSecretFields(card);applySentenceCaseUi(card);registerDirtyScope(key,card,{saveButton:card.querySelector('.user-save'),statusEl:card.querySelector('.user-save-state'),forceDirty:!!user._new});
    });
  }

  async function loadUsers() {try {const d = await api('/api/users');users = d.users || [];currentUserId = d.current_user_id || state.me?.user_id || '';renderUsers();} catch(e) {toast(e.message,'error')}}
  function addUser() {users.unshift({id:'',username:'',first_name:'',last_name:'',email:'',group:'standard',_new:true});renderUsers();}
  function userData(card) {const data={id:card.dataset.id||''};card.querySelectorAll('[data-user-field]').forEach(input=>data[input.dataset.userField]=input.type==='password'?secretFieldValue(input,''):input.value.trim());return data;}

  async function saveUser(card,user) {const key=card.dataset.dirtyScope;if(!dirtyScopes.get(key)?.dirty)return;const data=userData(card);if (!data.username) return toast('Enter a username.','error');if (data.password !== data.password2) return toast('Passwords do not match.','error');delete data.password2;try {const d=await post('/api/users',data);Object.assign(user,d.user||{}, {_new:false,_dirtyKey:key});card.dataset.id=user.id||'';configuredSecret(card.querySelector('[data-user-field="password"]'),true,'Password');configuredSecret(card.querySelector('[data-user-field="password2"]'),true,'Confirm Password');const summary=card.querySelector('.accordion-summary'),display=userName(user);summary.querySelector('.user-name-line b').textContent=display;const badge=summary.querySelector('.user-group-badge');badge.textContent=user.group==='administrator'?'Administrator':'Standard User';badge.className=`user-group-badge ${user.group==='administrator'?'admin':'standard'}`;resetDirtyScope(key,true);} catch(e) {toast(e.message,'error');syncDirtyScope(key)}}

  async function deleteUser(card,user) {if (!card.dataset.id) {const key=card.dataset.dirtyScope;users=users.filter(x=>x!==user);unregisterDirtyScope(key);card.remove();if(!users.length)renderUsers();return;}const confirmed=await showActionDialog({input:false,title:'Delete user',message:`Delete “${user.username}”?`,confirmLabel:'Delete',danger:true});if (!confirmed) return;try {await post('/api/users/delete',{id:card.dataset.id});const key=card.dataset.dirtyScope;users=users.filter(x=>x!==user);unregisterDirtyScope(key);card.remove();toast('userDeleted');if(!users.length)renderUsers();} catch(e) {toast(e.message,'error')}}

  function dirtyScopeNamesForSettings(){return dirtyScopeNames(name=>name==='settingsCore'||name.startsWith('integration:')||name.startsWith('user:'))}

'''
settings = replace_between(settings, '  function renderIntegrations() {\n', '  return {bind,activate,fill,saveCore,loadExtras,loadIntegrations,loadUsers,openClientSettings,closeClientSettings};', card_lifecycle, "integration and user dirty lifecycle")
settings = replace_once(settings, '  return {bind,activate,fill,saveCore,loadExtras,loadIntegrations,loadUsers,openClientSettings,closeClientSettings};', '  return {bind,activate,fill,saveCore,loadExtras,loadIntegrations,loadUsers,openClientSettings,closeClientSettings,dirtyScopeNames:dirtyScopeNamesForSettings};', "settings dirty export")
write("static/settings.js", settings)


# ---------------------------------------------------------------------------
# Styling: notification matrix, health cards, dirty state, focus visibility.
# ---------------------------------------------------------------------------
app_css = read("static/app.css")
app_css += '''

/* 0.5.34 accessibility and adaptive-rendering interaction polish */
.sr-only{position:absolute!important;width:1px!important;height:1px!important;padding:0!important;margin:-1px!important;overflow:hidden!important;clip:rect(0,0,0,0)!important;white-space:nowrap!important;border:0!important}
:where(button,input,select,textarea,a,[tabindex]):focus-visible{outline:2px solid color-mix(in srgb,var(--accent) 78%,white);outline-offset:2px}
.modal[aria-hidden="true"],.drawer[aria-hidden="true"]{pointer-events:none}
.form-save-state,.settings-save-state{font-size:9.5px;color:var(--muted);min-height:16px;display:inline-flex;align-items:center}.form-save-state.dirty,.settings-save-state.dirty{color:var(--warn)}.form-save-state.saved,.settings-save-state.saved{color:var(--good)}
.account-form-actions{align-items:center;justify-content:space-between;gap:12px}
'''
write("static/app.css", app_css)

settings_css = read("static/settings.css")
settings_css += '''

/* 0.5.34 dirty state, client health, notification rules, and a11y */
.settings-savebar{justify-content:space-between;align-items:center;gap:12px}.settings-savebar button:disabled,.settings-inline-actions button:disabled,.client-settings-actions button:disabled{opacity:.5;cursor:not-allowed}
.client-health{grid-column:1/-1;display:grid;grid-template-columns:auto minmax(0,1fr);gap:9px;align-items:start;padding:9px 10px;border:1px solid var(--border);border-radius:10px;background:color-mix(in srgb,var(--panel2) 48%,transparent)}.client-health-dot{width:8px;height:8px;border-radius:50%;margin-top:4px;background:var(--muted)}.client-health.online .client-health-dot{background:var(--good)}.client-health.offline .client-health-dot{background:var(--bad)}.client-health.connecting .client-health-dot{background:var(--warn)}.client-health>div{display:grid;gap:2px;min-width:0}.client-health strong{font-size:10px}.client-health small{font-size:8.5px;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.client-health.offline small:first-of-type{color:color-mix(in srgb,var(--bad) 75%,var(--muted))}
.notification-rule-table{border:1px solid var(--border);border-radius:12px;overflow:hidden;background:var(--panel3)}.notification-rule-heading,.notification-rule-row{display:grid;grid-template-columns:minmax(0,1fr) 72px 72px;align-items:center;gap:6px;padding:10px 12px}.notification-rule-heading{background:color-mix(in srgb,var(--panel2) 72%,transparent);border-bottom:1px solid var(--border)}.notification-rule-heading strong{font-size:10.5px}.notification-rule-heading>span{text-align:center;font-size:8.5px;color:var(--muted)}.notification-rule-row+.notification-rule-row{border-top:1px solid color-mix(in srgb,var(--border) 80%,transparent)}.notification-rule-row>span{display:grid;gap:2px}.notification-rule-row>span strong{font-size:10.5px}.notification-rule-row>span small{font-size:8.5px;color:var(--muted);line-height:1.4}.notification-rule-row>label{display:grid;place-items:center;margin:0!important}.notification-rule-row input{width:17px;height:17px;margin:0}.notification-actions{display:flex!important;grid-template-columns:none!important}.notification-actions button{min-width:130px!important}.client-settings-actions{align-items:center}.client-settings-actions .form-save-state{margin-right:auto}.integration-save-state,.user-save-state{margin-right:auto}
.client-settings-pane[hidden]{display:none!important}.client-settings-status:empty{display:none}
@media(max-width:620px){.notification-rule-heading,.notification-rule-row{grid-template-columns:minmax(0,1fr) 58px 58px;padding:10px 9px}.notification-rule-heading>span{font-size:7.5px}.notification-rule-row>span small{font-size:8px}.notification-actions{display:grid!important;grid-template-columns:1fr 1fr!important}.notification-actions button{width:100%;min-width:0!important}.settings-savebar{align-items:center}.client-health small{white-space:normal}.client-settings-actions{grid-template-columns:minmax(0,1fr) 1fr 1fr}.client-settings-actions .form-save-state{grid-column:1/-1}}
'''
write("static/settings.css", settings_css)

# Service worker cache busting.
sw = read("static/sw.js")
sw = sw.replace("0.5.33", "0.5.34")
write("static/sw.js", sw)

# Add explicit release-tool validation without changing the workflow file.
validator = read("release_tools/validate_ui_strings.py")
checks = '''    # 0.5.34 usability, health, notification rules, accessibility, and scale.
    assert 'LARGE_LIBRARY_THRESHOLD=300' in app_js and 'renderTorrentRows' in app_js and 'rowRenderCache' in app_js
    assert 'registerDirtyScope' in app_js and 'Unsaved changes' in app_js and "beforeunload" in app_js
    assert 'id="settingsSaveState"' in html and 'id="settingsSaveButton"' in html
    assert 'accountProfileSaveState' in html and 'clientSettingsSaveState' in html
    assert 'Discard changes?' in app_js and 'dirtyScopeNames:dirtyScopeNamesForSettings' in settings_js
    assert 'client_health' in app_js or 'client-health' in app_js
    assert 'client_health_snapshot' in dashboard_py and 'server_health' in dashboard_py and 'last_success' in dashboard_py
    assert 'client_offline' in dashboard_py and 'client_recovered' in dashboard_py
    for event_key in ('torrent_completed','torrent_error','torrent_stalled','client_offline','client_recovered','update_available','security_account'):
        assert event_key in dashboard_py and f'data-notification-rule="{event_key}"' in html
    assert 'default_notification_rules' in dashboard_py and 'normalize_notification_rules' in dashboard_py
    assert 'id="testNotificationSound"' in html and 'async function testNotificationSound()' in settings_js
    assert 'role="tab"' in html and 'role="tabpanel"' in html and 'aria-selected="true"' in html
    assert 'trapSurfaceFocus' in app_js and 'showSurface' in app_js and ':focus-visible' in app_css
    assert 'role="status" aria-live="polite"' in html

'''
validator = replace_once(validator, '    print("UI string audit passed")\n', checks + '    print("UI string audit passed")\n', "0.5.34 validation checks")
write("release_tools/validate_ui_strings.py", validator)

print("Applied v0.5.34 usability, health, notification rules, accessibility, and performance update.")
