#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD_VERSION = "0.5.128"
NEW_VERSION = "0.5.129"

APP_CSS = r'''

/* 0.5.129 desktop and mobile legibility pass. */
/* Preserve the compact visual hierarchy while eliminating sub-10px text on core surfaces. */
.topbar p{font-size:12.5px;line-height:1.45}
.brand small,.sidebar-foot{font-size:11px;line-height:1.4}
.metrics span{font-size:10.5px;line-height:1.3}.metrics small{font-size:10.5px;line-height:1.35}
.tabs button{font-size:12px}.filters input,.filters select{font-size:12px}.bulkbar{font-size:12px}.bulkbar button{font-size:11.5px}
th{font-size:10.5px;line-height:1.3}td{font-size:12.5px;line-height:1.35}.torrent-sub,.progress-top{font-size:10.5px;line-height:1.35}.state{font-size:10.5px}
.empty strong{font-size:14px}.empty span{font-size:12px;line-height:1.5}.history-head p{font-size:12px;line-height:1.5}.panel-title{font-size:13.5px}.event{font-size:12px;line-height:1.45}
.settings-card label{font-size:12px;line-height:1.4}.settings-card code,.warning{font-size:11.5px;line-height:1.5}.integration-card{font-size:11.5px}.integration-card span{font-size:10.5px}
.drawer-sheet header p{font-size:12px;line-height:1.45}.detail-actions button,.detail-tabs button{font-size:11.5px}.kv span{font-size:10px}.kv b{font-size:12px;line-height:1.4}.detail-table td{font-size:11px;line-height:1.4}.detail-table th{font-size:10px}
.modal-card label{font-size:12px;line-height:1.4}.or{font-size:10.5px}.menu button,.toast{font-size:12px;line-height:1.4}
.setup-rail small,.setup-rail p{font-size:11px}.setup-rail li{font-size:11.5px}.setup-copy{font-size:12.5px}.setup-page>label,.setup-page .two label,#wizardAccount>label{font-size:12px}.setup-note,.setup-code,.test-result{font-size:11px}.review-grid span,.review-grid small{font-size:10.5px}.review-grid b{font-size:12.5px}.server-setting .server-test-result{font-size:11px}

@media(min-width:1024px){
  td{font-size:13px}.torrent-name{font-size:13.5px}.torrent-sub,.progress-top{font-size:11px}.state{font-size:11px}
  th{font-size:11px}.metrics span,.metrics small{font-size:11px}.tabs button{font-size:12.5px}.filters input,.filters select{font-size:12.5px}
  .drawer-sheet h2,.modal-card h2{font-size:18px}.detail-actions button,.detail-tabs button{font-size:12px}.kv span{font-size:10.5px}.kv b{font-size:12.5px}.detail-table td{font-size:11.5px}
}

@media(max-width:820px){
  .topbar h1{font-size:19px}.topbar p{font-size:11px;line-height:1.4}.top-actions select,.top-actions .primary{font-size:11.5px}
  .metrics span,.metrics small{font-size:10.5px}.metrics strong{font-size:19px}
  .tabs button{font-size:11.5px}.filters input,.filters select{font-size:11.5px}.bulkbar,.bulkbar button{font-size:11.5px}
  td{font-size:12px}.torrent-name{font-size:14px;line-height:1.4}.torrent-sub{font-size:10.5px}.mobile-grid:before{font-size:10px;line-height:1.3}.progress-top,.state{font-size:10.5px}
  .mobile-nav button{font-size:11.5px;line-height:1.25}
  .drawer-sheet header p{font-size:11.5px}.detail-actions button,.detail-tabs button{font-size:11.5px}.kv span{font-size:10px}.kv b{font-size:12px}.detail-table td{font-size:11px}
  .modal-card label{font-size:12px}.menu button,.toast{font-size:12px}
  .setup-rail strong{font-size:15px}.setup-rail small{font-size:10.5px}.setup-rail li{font-size:10.5px}.setup-copy{font-size:12px}.setup-page>label,.setup-page .two label,#wizardAccount>label{font-size:12px}.setup-note,.setup-code,.test-result{font-size:10.5px}.review-grid span,.review-grid small{font-size:10px}.review-grid b{font-size:12px}
}
'''

SETTINGS_CSS = r'''

/* 0.5.129 settings and integration legibility pass. */
.settings-mobile-picker{font-size:12px}.settings-empty b{font-size:13.5px}.settings-empty span{font-size:11.5px;line-height:1.55}
.accordion-summary b{font-size:13px}.accordion-summary small{font-size:10.5px;line-height:1.4}.accordion-body label{font-size:12px;line-height:1.45}.user-group-badge{font-size:10px}
.user-management-intro,.client-settings-intro{font-size:12px;line-height:1.6}.configured-sound{font-size:11px;line-height:1.45}.notification-sound-mode-field,.notification-volume-row>label,.notification-volume-control output{font-size:11.5px}.notification-sound-drop strong{font-size:13px}.notification-sound-drop>span,.notification-sound-drop .configured-sound{font-size:11px;line-height:1.45}.notification-sound-option,.notification-sound-select-button{font-size:12px}
.client-settings-card header p{font-size:11.5px}.client-settings-tabs button{font-size:11.5px}.client-settings-section-heading span{font-size:11px}.client-setting-copy strong{font-size:12.5px}.client-setting-copy>span{font-size:11px}.client-limit-grid label,.client-field-grid label{font-size:11.5px!important}.client-limit-input>span{font-size:10px}.client-limit-grid small,.client-field-grid small,.client-settings-status{font-size:10.5px}.current-user-badge{font-size:9.5px}
.integration-service-heading .eyebrow{font-size:10.5px}.jellyfin-server-line strong{font-size:14px}.integration-service-heading small,.jellyfin-library-head small{font-size:10.5px;line-height:1.4}.service-status-badge{font-size:10px}.jellyfin-library-head strong{font-size:13px}.jellyfin-library-copy strong{font-size:12px}.jellyfin-library-copy span,.jellyfin-library-paths span,.jellyfin-library-paths code{font-size:10px;line-height:1.4}.jellyfin-library-scan span{font-size:9.5px}.jellyfin-library-scan strong{font-size:11px}.integration-service-empty{font-size:10.5px;line-height:1.45}
.jellyfin-task-copy strong{font-size:12px}.jellyfin-task-copy span{font-size:10.5px;line-height:1.4}

@media(min-width:1024px){
  .accordion-summary b{font-size:14.5px}.accordion-summary small{font-size:12px}.accordion-body label{font-size:13px}.user-group-badge{font-size:11px}
  .notification-sound-mode-field,.notification-volume-row>label,.notification-volume-control output{font-size:12px}.notification-sound-drop strong{font-size:13.5px}.notification-sound-drop>span,.notification-sound-drop .configured-sound{font-size:11.5px}.notification-sound-option,.notification-sound-select-button{font-size:12.5px}
  .jellyfin-task-copy strong{font-size:12.5px}.jellyfin-task-copy span{font-size:11px}.jellyfin-library-copy strong{font-size:12.5px}.jellyfin-library-copy span,.jellyfin-library-paths span,.jellyfin-library-paths code{font-size:10.5px}
}

@media(max-width:820px){
  .settings-mobile-picker{font-size:11.5px}.accordion-summary b{font-size:13px}.accordion-summary small{font-size:10.5px}.accordion-body label{font-size:12px}.user-group-badge{font-size:9.5px}.user-management-intro{font-size:11.5px}
  .client-settings-intro{font-size:11.5px}.client-settings-card header p{font-size:11px}.client-settings-tabs button{font-size:11.5px}.client-settings-section-heading span{font-size:10.5px}.client-setting-copy strong{font-size:12.5px}.client-setting-copy>span{font-size:10.5px}.client-limit-grid label,.client-field-grid label{font-size:11.5px!important}.client-limit-grid small,.client-field-grid small,.client-settings-status{font-size:10.5px}
  .integration-service-heading .eyebrow{font-size:10px}.integration-service-heading small,.jellyfin-library-head small{font-size:10.5px}.service-status-badge{font-size:9.5px}.jellyfin-library-copy strong{font-size:12px}.jellyfin-library-copy span,.jellyfin-library-paths span,.jellyfin-library-paths code{font-size:10px}.jellyfin-library-scan span{font-size:9.5px}.jellyfin-library-scan strong{font-size:11px}.integration-service-empty{font-size:10.5px}.jellyfin-task-copy strong{font-size:12px}.jellyfin-task-copy span{font-size:10.5px}
  .notification-sound-mode-field,.notification-volume-row>label,.notification-volume-control output{font-size:11.5px}.notification-sound-drop strong{font-size:13px}.notification-sound-drop>span,.notification-sound-drop .configured-sound{font-size:11px}.notification-sound-option,.notification-sound-select-button{font-size:12px}
}
'''


def append_once(path: Path, marker: str, content: str) -> None:
    text = path.read_text(encoding="utf-8")
    if marker in text:
        raise RuntimeError(f"Legibility block already exists in {path}")
    path.write_text(text.rstrip() + content + "\n", encoding="utf-8")


append_once(ROOT / "static" / "app.css", "0.5.129 desktop and mobile legibility pass", APP_CSS)
append_once(ROOT / "static" / "settings.css", "0.5.129 settings and integration legibility pass", SETTINGS_CSS)

# Keep the release/version contract synchronized.
dashboard = ROOT / "dashboard.py"
text = dashboard.read_text(encoding="utf-8")
text, count = re.subn(r'^(VERSION\s*=\s*["\'])0\.5\.128(["\'])', rf'\g<1>{NEW_VERSION}\2', text, count=1, flags=re.M)
if count != 1:
    raise RuntimeError("Could not update dashboard VERSION")
dashboard.write_text(text, encoding="utf-8")

app = ROOT / "static" / "app.js"
text = app.read_text(encoding="utf-8")
old = f"const FRONTEND_BUILD='{OLD_VERSION}';"
new = f"const FRONTEND_BUILD='{NEW_VERSION}';"
if old not in text:
    raise RuntimeError("Could not find app.js frontend build version")
app.write_text(text.replace(old, new, 1), encoding="utf-8")

index = ROOT / "static" / "index.html"
text = index.read_text(encoding="utf-8")
if OLD_VERSION not in text:
    raise RuntimeError("Could not find old version in static/index.html")
index.write_text(text.replace(OLD_VERSION, NEW_VERSION), encoding="utf-8")

sw = ROOT / "static" / "sw.js"
text = sw.read_text(encoding="utf-8")
if OLD_VERSION not in text or "torrent-dashboard-v05128" not in text:
    raise RuntimeError("Could not find expected service-worker version markers")
text = text.replace(OLD_VERSION, NEW_VERSION).replace("torrent-dashboard-v05128", "torrent-dashboard-v05129")
sw.write_text(text, encoding="utf-8")

source = ROOT / "release_notes" / "releases.json"
data = json.loads(source.read_text(encoding="utf-8"))
if any(str(item.get("version")) == NEW_VERSION for item in data.get("releases", [])):
    raise RuntimeError(f"Release metadata for {NEW_VERSION} already exists")
data["releases"].insert(0, {
    "version": NEW_VERSION,
    "date": "2026-09-07",
    "status": "prerelease",
    "title": "Desktop and mobile legibility pass",
    "summary": "Raises undersized secondary and compact text across the dashboard and settings UI while preserving the existing information density and responsive layout.",
    "highlights": [
        "Improves torrent table, metric, filter, drawer, modal, notification, and setup text sizing on desktop.",
        "Raises mobile torrent metadata, navigation, settings labels, and helper text to more readable sizes.",
        "Improves Jellyfin integration, scheduled-task, notification-sound, and advanced qBitTorrent settings typography."
    ],
    "fixes": [
        "Removes most remaining 8–10 px text from frequently read interface surfaces.",
        "Improves line height for secondary copy so larger text remains readable without crowding controls."
    ],
    "technical": [
        "Uses targeted responsive CSS overrides rather than a blanket browser zoom or global font-size increase.",
        "Keeps desktop information density higher than mobile while maintaining a larger readable floor on both."
    ],
    "validation": [
        "Source validation, unit tests, UI-string validation, JavaScript syntax checks, and release-note checks run before publication."
    ],
    "known_issues": [],
    "architecture": [],
    "decisions": [],
    "next_steps": []
})
source.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

subprocess.run([
    "python", "release_tools/generate_release_notes.py", "--version", NEW_VERSION
], cwd=ROOT, check=True)
print(f"Applied legibility pass for v{NEW_VERSION}")
