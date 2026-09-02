#!/usr/bin/env python3
"""Apply the v0.5.66 desktop legibility pass."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.65"
NEW = "0.5.66"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    if old not in text:
        raise SystemExit(f"{path}: expected text not found: {old!r}")
    write(path, text.replace(old, new, 1))


replace_once("dashboard.py", f'VERSION = "{OLD}"', f'VERSION = "{NEW}"')
index = read("static/index.html")
if OLD not in index:
    raise SystemExit("static/index.html: old build version not found")
write("static/index.html", index.replace(OLD, NEW))
replace_once("static/app.js", f"const FRONTEND_BUILD='{OLD}';", f"const FRONTEND_BUILD='{NEW}';")
sw = read("static/sw.js")
if OLD not in sw or "v0565" not in sw:
    raise SystemExit("static/sw.js: expected v0.5.65 cache generation not found")
write("static/sw.js", sw.replace(OLD, NEW).replace("v0565", "v0566"))

app_marker = "/* 0.5.66 desktop legibility baseline. */"
app_css = read("static/app.css")
if app_marker in app_css:
    raise SystemExit("static/app.css: v0.5.66 marker already present")
app_css += r'''

/* 0.5.66 desktop legibility baseline. */
@media(min-width:1024px){
  :root{--muted:#a7b3bf;--row:70px}
  :root[data-theme="light"]{--muted:#596878}
  :root[data-density="compact"]{--row:56px}
  html,body{font-size:15px;line-height:1.45}
  .app{grid-template-columns:272px minmax(0,1fr)}
  .sidebar{padding:26px 20px}
  .main{max-width:none;margin:0;padding:36px 44px 84px}
  .brand{gap:12px}.brand strong{font-size:16px}.brand small{font-size:12px}
  .nav{min-height:46px;padding:12px 14px;font-size:14px}
  .sidebar-foot{font-size:12px}
  .topbar{margin-bottom:26px}.topbar h1{font-size:29px}.topbar p{font-size:14px;line-height:1.45}
  .top-actions{gap:10px}.top-actions select{min-width:170px}
  button,select,input,textarea{font-size:13.5px}
  .metrics{gap:12px;margin-bottom:14px}.metrics article{padding:18px 19px}
  .metrics span{font-size:11.5px}.metrics strong{font-size:24px;margin-top:7px}.metrics small{font-size:12px;margin-top:5px}
  .controls-panel{padding:12px;margin-bottom:12px}.tabs{gap:6px}.tabs button{font-size:12.5px;padding:10px 12px}
  .filters{gap:9px}.filters input{width:280px}.filters input,.filters select{font-size:12.5px;padding:10px 11px}
  .bulkbar{font-size:12.5px}.bulkbar button{font-size:11.5px}
  table{min-width:1120px}th{font-size:11.5px;padding:13px 14px}td{font-size:14px;padding:11px 14px}
  .torrent-name{max-width:620px;font-size:15px}.torrent-sub{font-size:12px;margin-top:5px}
  .progress-top{font-size:11.5px;margin-bottom:7px}.track{height:7px}.state{font-size:11.5px;padding:6px 9px}
  .row-actions button{min-width:36px;min-height:36px}
  .banner{font-size:13.5px;line-height:1.5}
  .panel-title{font-size:15px;padding:17px 18px}.settings-card{padding:0 18px 18px}.settings-card .panel-title{margin:0 -18px 17px}
  .settings-card label{font-size:13px;line-height:1.4}.settings-card code{font-size:12px}.field-help,.warning{font-size:12px;line-height:1.55}
  .empty{padding:72px 24px}.empty strong{font-size:15px}.empty span{font-size:12px;line-height:1.5}
  .history-head h2{font-size:23px}.history-head p{font-size:12.5px}.event{font-size:12.5px}.event small{font-size:11.5px}
  .menu{min-width:230px}.menu button{font-size:12.5px;padding:10px 11px}.toast{font-size:13px}
  #contextMenu{min-width:270px}#contextMenu button{font-size:12.5px;min-height:38px}#contextMenu .menu-caption{font-size:10px}
  .profile-button-copy{max-width:180px}.profile-button-copy strong{font-size:12.5px}.profile-button-copy small{font-size:10.5px}
  .account-menu-head strong{font-size:13px}.account-menu-head small{font-size:11px}
  .modal-card h2,.drawer-sheet h2{font-size:19px}.modal-card label{font-size:12.5px}.drawer-sheet header p{font-size:12px}
  .account-modal-card{width:min(760px,calc(100% - 32px))}.account-modal-card header p{font-size:12px}
  .account-avatar-editor strong{font-size:14px}.account-avatar-editor p{font-size:11.5px;line-height:1.5}.account-avatar-actions button{font-size:12px}
  .account-section-title{font-size:14px}.account-form-grid label{font-size:12.5px}.account-section .field-help{font-size:11.5px}
  .password-confirm-card header p,.password-confirm-body label{font-size:12px}
  .torrent-detail-pane{min-height:320px;max-height:48vh}.torrent-detail-header{padding:12px 15px}.torrent-detail-header strong{font-size:13.5px}.torrent-detail-header span{font-size:11.5px}
  .torrent-detail-tabs button{font-size:12px;padding:9px 12px}.torrent-detail-body{padding:15px}
  .detail-progress-row{grid-template-columns:90px 1fr 88px;font-size:11.5px}.detail-general-section{padding:13px 14px}.detail-general-section>strong{font-size:13px}
  .detail-stat{font-size:11.5px;padding:4px 0}.detail-table.compact td,.detail-table.compact th{font-size:11px;padding:8px 9px}.detail-table select{font-size:11px}
  .notification-toolbar{padding:18px 20px}.notification-toolbar strong{font-size:15.5px}.notification-toolbar span{font-size:12.5px}
  .notification-item{padding:16px 20px}.notification-title b{font-size:13.5px}.notification-title span{font-size:10.5px}.notification-copy p{font-size:12px;line-height:1.55}.notification-item time{font-size:11px}
  .remove-modal-card header p,.action-dialog-card header p{font-size:12.5px}.remove-warning-copy strong{font-size:15px}.remove-warning-copy p{font-size:12.5px}.remove-target-list,.remove-files-option{font-size:12px!important}.action-dialog-content label{font-size:12.5px}
  .interface-title b{font-size:12.5px}.interface-default{font-size:9.5px}.interface-card span:not(.interface-default){font-size:11.5px}.interface-card small{font-size:10.5px}.interface-empty b{font-size:12.5px}.interface-empty span{font-size:11.5px}
  .lan-access-block b{font-size:12.5px}.lan-access-block small{font-size:11px}
  .update-status span{font-size:11px}.update-status strong{font-size:13.5px}.update-message{font-size:12px}
  .update-notes-heading strong{font-size:14px}.update-notes-heading span{font-size:12px}
  .update-release-summary{padding:16px 17px}.update-release-version{min-width:72px;font-size:11.5px;padding:7px 9px}.update-release-copy>strong{font-size:13.5px}.update-release-badge{font-size:10px;min-height:23px}.update-release-date{font-size:10.5px}
  .update-release-body{padding:16px 17px 18px;font-size:12.5px;line-height:1.65}.update-release-notes>p:first-child{font-size:12.5px;line-height:1.6}.update-release-notes h4,.update-release-notes h5{font-size:11px}.update-release-integrity-copy>span{font-size:10.5px}.update-release-integrity-copy code{font-size:11px}
  .startup-failure strong{font-size:13px}.startup-failure span{font-size:11.5px}
  .add-torrent-card{width:min(1220px,calc(100% - 48px));height:min(820px,90vh)}.add-torrent-body{grid-template-columns:minmax(360px,420px) minmax(0,1fr)}
  .add-torrent-options{padding:18px 20px 22px}.add-torrent-preview{padding:18px;gap:14px}.add-torrent-section-title strong{font-size:12.5px}.add-torrent-section-title span{font-size:11px}.add-torrent-options label{font-size:12px}
  .add-source-or{font-size:10px}.add-preview-heading strong{font-size:12.5px}.add-preview-heading span{font-size:10.5px}.add-content-columns{font-size:10px}.add-content-row{font-size:11.5px;padding:10px 12px}.add-preview-empty strong{font-size:13.5px}.add-preview-empty span{font-size:11.5px}.add-info-grid span,.add-info-grid b{font-size:11.5px}.add-torrent-status strong{font-size:11.5px}.add-torrent-status span{font-size:10.5px}.add-torrent-actions button{font-size:12px}
  .add-rate-input>span,.add-rate-grid small{font-size:10.5px}
}
'''.replace(r'\"', '"')
write("static/app.css", app_css)

settings_marker = "/* 0.5.66 desktop settings legibility. */"
settings_css = read("static/settings.css")
if settings_marker in settings_css:
    raise SystemExit("static/settings.css: v0.5.66 marker already present")
settings_css += r'''

/* 0.5.66 desktop settings legibility. */
@media(min-width:1024px){
  .settings-subnav{gap:4px;margin:4px 0 8px 15px;padding:5px 0 5px 13px}.settings-subnav button{min-height:40px;padding:10px 11px;font-size:13px;line-height:1.35}
  .settings-savebar{padding:11px 12px}.settings-savebar button{min-width:170px;min-height:40px}
  .settings-empty{padding:32px}.settings-empty b{font-size:14px}.settings-empty span{font-size:12px;line-height:1.55}
  .accordion-summary{min-height:64px;padding:16px 17px}.accordion-summary b{font-size:14px}.accordion-summary small{font-size:11.5px;margin-top:5px}.accordion-chevron{font-size:18px}
  .accordion-body{padding:18px}.accordion-body label{font-size:13px;line-height:1.4}.user-group-badge{font-size:11px;padding:6px 10px;min-width:122px}
  .settings-inline-actions{gap:10px;margin:15px 0}.settings-inline-actions button{min-width:144px;min-height:40px}
  .user-management-intro,.client-settings-intro{font-size:12.5px;line-height:1.6}
  .notification-settings-card .notification-intro{font-size:12.5px;line-height:1.6}.notification-options{gap:12px}.notification-sound-config{padding:14px}.configured-sound{font-size:11.5px}
  .client-settings-card{width:min(820px,calc(100% - 32px))}.client-settings-card header{padding:21px 22px 19px}.client-settings-card header h2{font-size:20px}.client-settings-card header p{font-size:12px;line-height:1.5}
  .client-settings-tabs{padding:10px 22px}.client-settings-tabs button{font-size:12.5px;padding:9px 13px}.client-settings-body{gap:18px;padding:22px;min-height:360px}
  .client-settings-section-heading strong{font-size:15px}.client-settings-section-heading span{font-size:11.5px;line-height:1.55}.client-setting-row{gap:22px;padding:16px 0!important}.client-setting-copy strong{font-size:13.5px}.client-setting-copy>span{font-size:11.5px;line-height:1.55}
  .integration-add-row{grid-template-columns:minmax(0,320px) auto;gap:10px}.integration-result,.test-result{font-size:12px;line-height:1.5}
  .sidebar-user strong{font-size:13px}.sidebar-user small{font-size:11px}
}
'''
write("static/settings.css", settings_css)

design = read("DESIGN_LANGUAGE.md")
if "## Desktop legibility" not in design:
    design += """

## Desktop legibility

Desktop layouts should use available space before shrinking text. At viewport widths of 1024 px and above:

- Primary application and table content should generally render in the **13–15 px** range.
- Supporting copy, help text, timestamps, and secondary metadata should generally stay at **11.5 px or larger**. Small badges and compact metadata labels may use approximately **10–11 px** when contrast and spacing remain strong.
- Muted text must remain visibly subordinate without becoming low-contrast. Dark and light themes both need a clear contrast step between `--text`, `--muted`, surfaces, and borders.
- Forms and navigation should gain spacing and hit area before their text is reduced. The desktop canvas should be used rather than preserving large unused margins.
- Compact density may reduce row height and spacing, but it should not restore the former undersized text baseline.
- Tablet and mobile breakpoints remain independently tuned; desktop typography rules must not simply scale responsive layouts upward.
"""
write("DESIGN_LANGUAGE.md", design)

validator = read("release_tools/validate_ui_strings.py")
needle = '    print("UI string audit passed")\n'
if needle not in validator:
    raise SystemExit("validate_ui_strings.py: print anchor not found")
checks = '''    # 0.5.66 desktop readability contract. Desktop uses available space instead\n    # of falling back to the historical 8-11px interface baseline.\n    assert '0.5.66 desktop legibility baseline' in app_css\n    assert '0.5.66 desktop settings legibility' in settings_css\n    assert '@media(min-width:1024px)' in app_css and '@media(min-width:1024px)' in settings_css\n    assert ':root{--muted:#a7b3bf;--row:70px}' in app_css\n    assert ':root[data-density="compact"]{--row:56px}' in app_css\n    assert '.torrent-name{max-width:620px;font-size:15px}' in app_css\n    assert '.update-release-body{padding:16px 17px 18px;font-size:12.5px' in app_css\n    assert '.settings-subnav button{min-height:40px;padding:10px 11px;font-size:13px' in settings_css\n    assert '.accordion-summary b{font-size:14px}' in settings_css\n    assert '.client-setting-copy>span{font-size:11.5px' in settings_css\n    assert '## Desktop legibility' in (ROOT / 'DESIGN_LANGUAGE.md').read_text(encoding='utf-8')\n\n'''
validator = validator.replace(needle, checks + needle, 1)
write("release_tools/validate_ui_strings.py", validator)

notes_path = ROOT / "release_notes" / "releases.json"
data = json.loads(notes_path.read_text(encoding="utf-8"))
releases = data.get("releases", [])
if any(str(item.get("version")) == NEW for item in releases):
    raise SystemExit(f"release metadata already contains {NEW}")
releases.append({
    "version": NEW,
    "date": "2026-09-02",
    "status": "prerelease",
    "title": "Desktop legibility and workspace use",
    "summary": "Raises the desktop readability baseline across Torrent Dashboard and uses the available canvas more effectively without changing mobile behavior or removing compact density.",
    "highlights": [
        "Desktop primary content, forms, tables, navigation, dialogs, patch notes, torrent details, Add Torrent, and notifications use larger type and more deliberate spacing at 1024 px and above.",
        "The desktop sidebar and main content area use more of the available viewport instead of preserving undersized text beside unused space.",
        "Muted text contrast is stronger in both dark and light themes while remaining visually subordinate to primary content.",
        "Compact density remains available with a reduced row height, but no longer implies the former undersized desktop typography baseline."
    ],
    "fixes": [
        "Improves readability at 100% browser zoom on desktop, especially for torrent rows, supporting metadata, Settings forms, update notes, and account/client dialogs."
    ],
    "technical": [
        "Desktop-specific legibility overrides begin at 1024 px so the existing tablet and mobile breakpoints retain their independent tuning.",
        "DESIGN_LANGUAGE.md now defines minimum desktop readability expectations so future feature work uses space before shrinking type.",
        "The UI regression audit verifies the desktop typography floor, muted contrast token, compact-density row override, and key Settings/readability selectors."
    ],
    "validation": [
        "Existing backend behavioral tests and architecture checks remain unchanged by the presentation-only pass.",
        "JavaScript syntax, frontend build synchronization, service-worker cache generation, generated release metadata, and the expanded UI string/readability audit remain release gates."
    ],
    "known_issues": [
        "The pass improves CSS typography and spacing but does not replace browser/device visual regression testing; unusually low-DPI displays may still benefit from OS-level text scaling."
    ],
    "architecture": [
        "dashboard.py remains the composition root and HTTP adapter.",
        "Configuration lifecycle, configuration transactions, integrations, and users/accounts remain isolated in torrent_dashboard package modules.",
        "Desktop presentation now has an explicit design-language readability contract separate from responsive/mobile tuning.",
        "Release/update provenance remains the next planned backend extraction."
    ],
    "decisions": [
        "Use available desktop space before reducing type size.",
        "Treat 1024 px and above as the desktop legibility breakpoint while preserving existing responsive rules below it.",
        "Keep compact density as a spacing preference rather than a license to use hard-to-read text.",
        "Continue behavior-preserving modularization independently from presentation-quality passes."
    ],
    "next_steps": [
        {"priority": 1, "title": "Extract release and update provenance", "detail": "Move GitHub release parsing, installed release metadata, package-integrity normalization, and historical digest caching out of dashboard.py."},
        {"priority": 2, "title": "Extract qBitTorrent transport and normalization", "detail": "Move QBitClient, server normalization, proxy/preference translation, and Web API transport away from HTTP routing."},
        {"priority": 3, "title": "Expand request-level behavioral tests", "detail": "Add authorization, CSRF, setup, account-route, and settings-mutation coverage around extracted service boundaries."},
        {"priority": 4, "title": "Harden secrets at rest", "detail": "Use the configuration boundary to add restrictive file permissions and separate ordinary configuration from stored credentials."}
    ]
})
data["releases"] = releases
notes_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

subprocess.run([sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", NEW], cwd=ROOT, check=True)
print(f"Applied v{NEW} desktop legibility pass")
