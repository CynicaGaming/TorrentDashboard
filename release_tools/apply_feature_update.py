#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.5.117"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    if old not in text:
        raise SystemExit(f"{path}: expected transform anchor not found: {old[:120]!r}")
    if text.count(old) != 1:
        raise SystemExit(f"{path}: transform anchor is not unique ({text.count(old)} matches): {old[:120]!r}")
    write(path, text.replace(old, new, 1))


# Version/build synchronization.
replace_once("dashboard.py", 'VERSION = "0.5.116"', f'VERSION = "{VERSION}"')
replace_once("static/app.js", "const FRONTEND_BUILD='0.5.116';", f"const FRONTEND_BUILD='{VERSION}';")
html = read("static/index.html")
if "0.5.116" not in html:
    raise SystemExit("static/index.html: v0.5.116 build references not found")
write("static/index.html", html.replace("0.5.116", VERSION))
sw = read("static/sw.js")
if "torrent-dashboard-v05116" not in sw or "0.5.116" not in sw:
    raise SystemExit("static/sw.js: v0.5.116 cache/build references not found")
sw = sw.replace("torrent-dashboard-v05116", "torrent-dashboard-v05117").replace("0.5.116", VERSION)
write("static/sw.js", sw)

# Add the locally embedded Material-style notifications icon path.
replace_once(
    "static/app.js",
    "  check:'M9 16.17 4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z',\n};",
    "  check:'M9 16.17 4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z',\n"
    "  notifications:'M12 22c1.1 0 1.99-.9 1.99-2h-4A2 2 0 0 0 12 22Zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4a1.5 1.5 0 0 0-3 0v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2Z',\n};",
)

# Insert the notification bell between torrent controls and the profile button.
replace_once(
    "static/index.html",
    "</div>\n<button class=\"profile-button\" id=\"profileBtn\" type=\"button\" aria-label=\"Open account menu\" aria-haspopup=\"menu\" aria-expanded=\"false\">",
    "</div>\n"
    "<div class=\"notification-bell-wrap\">\n"
    "<button class=\"notification-bell-button\" id=\"notificationBellBtn\" type=\"button\" aria-label=\"Open notifications\" aria-haspopup=\"dialog\" aria-expanded=\"false\" aria-controls=\"notificationBellPanel\">\n"
    "<svg class=\"material-symbol-icon\" aria-hidden=\"true\" viewBox=\"0 0 24 24\"><path d=\"M12 22c1.1 0 1.99-.9 1.99-2h-4A2 2 0 0 0 12 22Zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4a1.5 1.5 0 0 0-3 0v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2Z\"/></svg>\n"
    "<span class=\"notification-bell-badge hidden\" id=\"notificationBellBadge\" aria-hidden=\"true\"></span>\n"
    "</button>\n"
    "<section class=\"notification-bell-panel hidden\" id=\"notificationBellPanel\" role=\"dialog\" aria-label=\"Recent torrent completions\">\n"
    "<header class=\"notification-bell-header\"><strong>Notifications</strong><button class=\"notification-bell-clear\" id=\"notificationBellClear\" type=\"button\">Clear</button></header>\n"
    "<div class=\"notification-bell-list\" id=\"notificationBellList\"></div>\n"
    "<button class=\"notification-bell-history\" id=\"notificationBellHistory\" type=\"button\">View all notifications</button>\n"
    "</section>\n"
    "</div>\n"
    "<button class=\"profile-button\" id=\"profileBtn\" type=\"button\" aria-label=\"Open account menu\" aria-haspopup=\"menu\" aria-expanded=\"false\">",
)

# Add browser-local bell state and rendering immediately before the existing notification presentation helpers.
notification_anchor = "function notificationCategory(item){const event=String(item?.event||'').toLowerCase();"
notification_code = r'''const NOTIFICATION_BELL_LIMIT=8;
const NOTIFICATION_REFRESH_MS=10000;
const NOTIFICATION_SEEN_KEY='tdNotificationBellSeen';
const NOTIFICATION_CLEARED_KEY='tdNotificationBellCleared';
const NOTIFICATION_TOKEN_LIMIT=400;
let notificationRefreshTimer=null;
function notificationEventToken(item){return`${Number(item?.id)||0}:${Number(item?.ts)||0}`}
function notificationTokenSet(key){try{const raw=JSON.parse(localStorage.getItem(key)||'[]');return new Set(Array.isArray(raw)?raw.map(String):[])}catch{return new Set()}}
function saveNotificationTokenSet(key,set){localStorage.setItem(key,JSON.stringify([...set].slice(-NOTIFICATION_TOKEN_LIMIT)))}
function notificationCompletionEvents(includeCleared=false){
  const cleared=includeCleared?new Set():notificationTokenSet(NOTIFICATION_CLEARED_KEY);
  return(state.notificationEvents||[]).filter(item=>{
    if(String(item?.event||'').toLowerCase()!=='completed')return false;
    if(state.server!=='all'&&item.server_id!==state.server)return false;
    return includeCleared||!cleared.has(notificationEventToken(item));
  })
}
function initializeNotificationBellState(){
  if(localStorage.getItem(NOTIFICATION_SEEN_KEY)!==null||localStorage.getItem(NOTIFICATION_CLEARED_KEY)!==null)return;
  const seen=new Set(notificationCompletionEvents(true).map(notificationEventToken));saveNotificationTokenSet(NOTIFICATION_SEEN_KEY,seen)
}
function renderNotificationBell(){
  const button=$('#notificationBellBtn'),badge=$('#notificationBellBadge'),list=$('#notificationBellList'),clear=$('#notificationBellClear');if(!button||!badge||!list)return;
  const items=notificationCompletionEvents(),seen=notificationTokenSet(NOTIFICATION_SEEN_KEY),unread=items.filter(item=>!seen.has(notificationEventToken(item))).length;
  badge.textContent=unread>99?'99+':String(unread);badge.classList.toggle('hidden',!unread);button.setAttribute('aria-label',unread?`Open notifications, ${unread} unread`:'Open notifications');if(clear)clear.disabled=!items.length;
  if(!items.length){list.innerHTML='<div class="notification-bell-empty">No recent completions</div>';return}
  list.innerHTML=items.slice(0,NOTIFICATION_BELL_LIMIT).map(item=>{const view=notificationPresentation(item);return`<article class="notification-bell-item ${esc(view.tone)}"><span class="notification-dot" aria-hidden="true"></span><div class="notification-bell-copy"><b>${esc(item.name||view.title)}</b><span>${esc(view.title)}</span></div><time title="${esc(when(item.ts))}">${esc(rel(item.ts))}</time></article>`}).join('')
}
function markNotificationBellSeen(){const seen=notificationTokenSet(NOTIFICATION_SEEN_KEY);for(const item of notificationCompletionEvents())seen.add(notificationEventToken(item));saveNotificationTokenSet(NOTIFICATION_SEEN_KEY,seen);renderNotificationBell()}
function clearNotificationBell(){const cleared=notificationTokenSet(NOTIFICATION_CLEARED_KEY),seen=notificationTokenSet(NOTIFICATION_SEEN_KEY);for(const item of notificationCompletionEvents()){const token=notificationEventToken(item);cleared.add(token);seen.add(token)}saveNotificationTokenSet(NOTIFICATION_CLEARED_KEY,cleared);saveNotificationTokenSet(NOTIFICATION_SEEN_KEY,seen);renderNotificationBell()}
function setNotificationBellOpen(open){const panel=$('#notificationBellPanel'),button=$('#notificationBellBtn');if(!panel||!button)return;open=!!open;panel.classList.toggle('hidden',!open);button.setAttribute('aria-expanded',String(open));$('#topbar')?.classList.toggle('notification-open',open);if(open){hideAccountMenu();markNotificationBellSeen()}}
function scheduleNotificationRefresh(){clearInterval(notificationRefreshTimer);notificationRefreshTimer=setInterval(()=>loadNotifications(true),NOTIFICATION_REFRESH_MS)}
'''
app_js = read("static/app.js")
if notification_anchor not in app_js:
    raise SystemExit("static/app.js: notification helper anchor not found")
write("static/app.js", app_js.replace(notification_anchor, notification_code + notification_anchor, 1))

# Make the full notification loader drive both the durable view and transient bell.
replace_once(
    "static/app.js",
    "async function loadNotifications(){try{const d=await api('/api/events?limit=200');state.notificationEvents=d.events||[];renderNotifications()}catch(err){toast(err.message,'error')}}",
    "async function loadNotifications(quiet=false){try{const d=await api('/api/events?limit=200');state.notificationEvents=d.events||[];initializeNotificationBellState();renderNotifications();renderNotificationBell()}catch(err){if(quiet)console.error('[Torrent Dashboard] Notification refresh failed',err);else toast(err.message,'error')}}",
)

# Promptly sync the durable completion event into the bell after a live completion.
old_completion = "function checkCompletions(){const now=new Set(state.torrents.filter(t=>Number(t.progress)>=.999999).map(keyFor));if(state.lastComplete.size){for(const k of now)if(!state.lastComplete.has(k)){const t=state.torrents.find(x=>keyFor(x)===k);if(t){toast(`completed: ${t.name}`);playCompletionSound().catch(()=>{});if(state.settings?.notifications?.browser&&'Notification' in window&&Notification.permission==='granted')showBrowserNotification(state.settings?.dashboard?.title||'Torrent Dashboard',{body:`Completed: ${t.name}`,tag:`torrent-complete-${k}`}).catch(()=>{})}}}state.lastComplete=now;if('setAppBadge'in navigator){let n=state.torrents.filter(isActive).length;n?navigator.setAppBadge(n):navigator.clearAppBadge()}}"
new_completion = "function checkCompletions(){const now=new Set(state.torrents.filter(t=>Number(t.progress)>=.999999).map(keyFor));let completedNow=false;if(state.lastComplete.size){for(const k of now)if(!state.lastComplete.has(k)){const t=state.torrents.find(x=>keyFor(x)===k);if(t){completedNow=true;toast(`completed: ${t.name}`);playCompletionSound().catch(()=>{});if(state.settings?.notifications?.browser&&'Notification' in window&&Notification.permission==='granted')showBrowserNotification(state.settings?.dashboard?.title||'Torrent Dashboard',{body:`Completed: ${t.name}`,tag:`torrent-complete-${k}`}).catch(()=>{})}}}state.lastComplete=now;if(completedNow)setTimeout(()=>loadNotifications(true),1200);if('setAppBadge'in navigator){let n=state.torrents.filter(isActive).length;n?navigator.setAppBadge(n):navigator.clearAppBadge()}}"
replace_once("static/app.js", old_completion, new_completion)

# Bell interactions, server scoping, Escape handling, and startup polling.
replace_once(
    "static/app.js",
    "$('#serverSelect').addEventListener('change',async e=>{state.server=e.target.value;localStorage.tdServer=state.server;state.selected.clear();resetDetailPane();await refreshStatus();if(state.server!=='all')await loadMeta();if($('#view-notifications')?.classList.contains('active'))renderNotifications()});",
    "$('#serverSelect').addEventListener('change',async e=>{state.server=e.target.value;localStorage.tdServer=state.server;state.selected.clear();resetDetailPane();await refreshStatus();if(state.server!=='all')await loadMeta();renderNotificationBell();if($('#view-notifications')?.classList.contains('active'))renderNotifications()});",
)
replace_once(
    "static/app.js",
    "$('#profileBtn').addEventListener('click',e=>{showMenu($('#accountMenu'),e.currentTarget);e.currentTarget.setAttribute('aria-expanded','true')});document.addEventListener('click',e=>{if(!e.target.closest('.menu')&&!e.target.closest('#profileBtn')){$$('.menu').forEach(m=>m.classList.add('hidden'));$('#profileBtn')?.setAttribute('aria-expanded','false')}});",
    "$('#profileBtn').addEventListener('click',e=>{setNotificationBellOpen(false);showMenu($('#accountMenu'),e.currentTarget);e.currentTarget.setAttribute('aria-expanded','true')});document.addEventListener('click',e=>{if(!e.target.closest('.menu')&&!e.target.closest('#profileBtn')){$$('.menu').forEach(m=>m.classList.add('hidden'));$('#profileBtn')?.setAttribute('aria-expanded','false')}if(!e.target.closest('.notification-bell-wrap'))setNotificationBellOpen(false)});",
)
replace_once(
    "static/app.js",
    "$('#notificationFilter')?.addEventListener('change',renderNotifications);$('#refreshNotifications')?.addEventListener('click',loadNotifications);",
    "$('#notificationFilter')?.addEventListener('change',renderNotifications);$('#refreshNotifications')?.addEventListener('click',()=>loadNotifications());$('#notificationBellBtn')?.addEventListener('click',()=>setNotificationBellOpen($('#notificationBellPanel')?.classList.contains('hidden')));$('#notificationBellClear')?.addEventListener('click',e=>{e.stopPropagation();clearNotificationBell()});$('#notificationBellHistory')?.addEventListener('click',()=>{setNotificationBellOpen(false);setView('notifications')});",
)
replace_once(
    "static/app.js",
    "window.addEventListener('keydown',e=>{if(e.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){e.preventDefault();$('#search').focus()}if(e.key==='Escape'){if(!$('#passwordConfirmModal')?.classList.contains('hidden'))",
    "window.addEventListener('keydown',e=>{if(e.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){e.preventDefault();$('#search').focus()}if(e.key==='Escape'){if(!$('#notificationBellPanel')?.classList.contains('hidden')){setNotificationBellOpen(false);return}if(!$('#passwordConfirmModal')?.classList.contains('hidden'))",
)
replace_once(
    "static/app.js",
    "await loadServers();bindUI();applyPrefs();if(state.server!=='all')await loadMeta();await refreshStatus();scheduleRefresh();registerPwa();",
    "await loadServers();bindUI();applyPrefs();if(state.server!=='all')await loadMeta();await refreshStatus();await loadNotifications(true);scheduleRefresh();scheduleNotificationRefresh();registerPwa();",
)

# Responsive bell/popover styling. Clear is a browser-local dismissal only.
css = read("static/app.css")
marker = "/* 0.5.117 header completion notification inbox */"
if marker in css:
    raise SystemExit("static/app.css: v0.5.117 marker already exists")
css += r'''

/* 0.5.117 header completion notification inbox */
.notification-bell-wrap{position:relative;flex:0 0 auto}
.notification-bell-button{position:relative;width:38px;height:38px;display:grid;place-items:center;padding:0;border:1px solid var(--border);background:var(--panel3);color:var(--muted);border-radius:10px}
.notification-bell-button:hover,.notification-bell-button[aria-expanded="true"]{background:var(--panel2);color:var(--text)}
.notification-bell-button:focus-visible{box-shadow:0 0 0 2px color-mix(in srgb,var(--accent) 48%,transparent)}
.notification-bell-button .material-symbol-icon{width:19px;height:19px}
.notification-bell-badge{position:absolute;right:1px;top:1px;min-width:16px;height:16px;padding:0 4px;border-radius:999px;display:grid;place-items:center;background:var(--accent);color:#08111e;font-size:8px;font-weight:800;line-height:1;border:2px solid var(--panel3);pointer-events:none}
.notification-bell-panel{position:absolute;right:0;top:calc(100% + 8px);z-index:110;width:min(380px,calc(100vw - 24px));max-height:min(520px,70vh);display:flex;flex-direction:column;background:var(--panel2);border:1px solid var(--border);border-radius:14px;box-shadow:var(--shadow);overflow:hidden}
.notification-bell-header{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:10px 12px;border-bottom:1px solid var(--border)}
.notification-bell-header strong{font-size:11px}.notification-bell-clear{border:0;background:transparent;color:var(--muted);font-size:9.5px;padding:5px 7px}.notification-bell-clear:hover:not(:disabled){color:var(--text);background:var(--panel3)}.notification-bell-clear:disabled{opacity:.45;cursor:default}
.notification-bell-list{display:grid;overflow:auto;max-height:min(380px,55vh)}
.notification-bell-item{display:grid;grid-template-columns:8px minmax(0,1fr) auto;gap:9px;align-items:start;padding:11px 12px;border-bottom:1px solid color-mix(in srgb,var(--border) 68%,transparent)}
.notification-bell-item:last-child{border-bottom:0}.notification-bell-item.good .notification-dot{background:var(--good)}.notification-bell-item.warn .notification-dot{background:var(--warn)}.notification-bell-item.bad .notification-dot{background:var(--bad)}
.notification-bell-copy{display:grid;gap:3px;min-width:0}.notification-bell-copy b{font-size:10.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.notification-bell-copy span{color:var(--muted);font-size:9px}.notification-bell-item time{color:var(--muted);font-size:8.5px;white-space:nowrap;padding-top:1px}
.notification-bell-empty{padding:26px 14px;text-align:center;color:var(--muted);font-size:10px}
.notification-bell-history{border:0;border-top:1px solid var(--border);border-radius:0;background:color-mix(in srgb,var(--panel3) 55%,transparent);color:var(--text);padding:10px 12px;font-size:10px;text-align:center}
.notification-bell-history:hover{background:var(--panel3)}
.topbar.notification-open{z-index:85}
@media(max-width:760px){.notification-bell-button{width:32px;height:32px}.notification-bell-button .material-symbol-icon{width:17px;height:17px}}
@media(max-width:520px){.notification-bell-button{width:34px;height:34px}.notification-bell-panel{position:fixed;right:8px;top:58px;width:min(360px,calc(100vw - 16px));max-height:calc(100dvh - 142px)}.notification-bell-list{max-height:calc(100dvh - 240px)}}
'''
write("static/app.css", css)

# Durable design/testing contract.
design_path = "DESIGN_LANGUAGE.md"
design = read(design_path)
section = "### Header completion notification inbox"
if section in design:
    raise SystemExit("DESIGN_LANGUAGE.md: v0.5.117 section already exists")
design += """

### Header completion notification inbox

- The application header includes a locally embedded Material-style notification bell beside the client controls and account control.
- The bell is a compact transient inbox for completed torrents, not a duplicate of the full Notifications destination. Its unread badge and recent list follow the currently selected client scope.
- Opening the bell marks the currently visible completion entries as seen while leaving them in the bell. **Clear** dismisses the bell's current completion entries only in that browser.
- Bell seen/cleared state is browser-local presentation state. Clearing the bell must never delete or mutate the durable server-side event history.
- **View all notifications** opens the main Notifications view, which remains the detailed history for torrent, security, account, update, integration, and system events.
- The popover must remain above mobile Torrent Details and bulk-action layers and must not introduce header overflow on narrow screens.
"""
write(design_path, design)

testing_path = "TESTING.md"
testing = read(testing_path)
if section in testing:
    raise SystemExit("TESTING.md: v0.5.117 section already exists")
testing += """

### Header completion notification inbox

1. On a browser with no prior bell state, load existing event history and confirm old completion events may appear in the list but do not generate a historical unread-count flood.
2. Complete a torrent and confirm the header bell badge increments after the durable completion event is recorded; open the bell and confirm the torrent name, completion label, and relative timestamp appear.
3. Opening the bell marks currently listed completion events seen: the badge clears while the entries remain visible.
4. Press **Clear** and confirm the current completion entries disappear from the bell. Open **View all notifications** and verify the same completion events remain in the durable Notifications history.
5. Complete another torrent after clearing and confirm it appears as a new unread bell entry.
6. Switch between individual clients and **All servers** and verify the bell list/badge follow the selected scope. Clearing one scope must not silently erase durable history or another browser's presentation state.
7. Reload the same browser and verify seen/cleared bell state persists; a separate browser profile should maintain independent bell presentation state.
8. Verify **View all notifications** navigates to the existing Notifications destination with detailed torrent, security, system, account, integration, and update events intact.
9. On mobile, confirm the bell popover remains above Torrent Details/bulk actions, fits the viewport without horizontal overflow, closes on outside tap/Escape, and does not displace the existing top controls.
"""
write(testing_path, testing)

# Add focused UI regression assertions without weakening prior contracts.
validator_path = "release_tools/validate_ui_strings.py"
validator = read(validator_path)
validator_anchor = "    assert '### Torrent sort chevrons' in testing\n\n    print(\"UI string audit passed\")"
validator_block = r'''    assert '### Torrent sort chevrons' in testing

    # 0.5.117 adds a browser-local completion inbox over durable event history.
    for control in ('notificationBellBtn','notificationBellBadge','notificationBellPanel','notificationBellList','notificationBellClear','notificationBellHistory'):
        assert f'id="{control}"' in html
    assert 'aria-label="Open notifications"' in html and 'View all notifications' in html
    assert "notifications:'M12 22" in app_js
    assert 'const NOTIFICATION_BELL_LIMIT=8;' in app_js
    assert 'const NOTIFICATION_REFRESH_MS=10000;' in app_js
    assert "const NOTIFICATION_SEEN_KEY='tdNotificationBellSeen';" in app_js
    assert "const NOTIFICATION_CLEARED_KEY='tdNotificationBellCleared';" in app_js
    assert 'function initializeNotificationBellState()' in app_js
    assert "String(item?.event||'').toLowerCase()!=='completed'" in app_js
    assert 'localStorage.setItem(key,JSON.stringify' in app_js
    assert 'function clearNotificationBell()' in app_js and 'function markNotificationBellSeen()' in app_js
    assert "setView('notifications')" in app_js and 'scheduleNotificationRefresh()' in app_js
    assert 'await loadNotifications(true);scheduleRefresh();scheduleNotificationRefresh();registerPwa();' in app_js
    assert "if(completedNow)setTimeout(()=>loadNotifications(true),1200)" in app_js
    assert '/api/events/clear' not in dashboard_py and '/api/events/clear' not in app_js
    assert '0.5.117 header completion notification inbox' in app_css
    assert '.topbar.notification-open{z-index:85}' in app_css
    assert '### Header completion notification inbox' in design_language
    assert '### Header completion notification inbox' in testing_md

    print("UI string audit passed")'''
if validator_anchor not in validator:
    raise SystemExit("release_tools/validate_ui_strings.py: insertion anchor not found")
write(validator_path, validator.replace(validator_anchor, validator_block, 1))

# Append structured release metadata, inheriting the latest durable engineering decisions.
metadata_path = ROOT / "release_notes" / "releases.json"
metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
if any(str(item.get("version")) == VERSION for item in metadata.get("releases", [])):
    raise SystemExit(f"release_notes/releases.json: {VERSION} already exists")
latest = metadata["releases"][-1]
decisions = list(latest.get("decisions", []))
for decision in (
    "Treat the header notification bell as a browser-local transient completion inbox; clearing it must not delete durable Notifications history.",
    "Keep detailed security, account, system, integration, and update activity in the full Notifications view while the header bell initially surfaces completed torrents only.",
):
    if decision not in decisions:
        decisions.append(decision)
metadata["releases"].append({
    "version": VERSION,
    "date": "2026-09-04",
    "status": "prerelease",
    "title": "Header completion notification inbox",
    "summary": "Adds a compact Material-style notification bell for recent completed torrents while preserving the full Notifications view as durable activity history.",
    "highlights": [
        "Adds a locally embedded Material-style bell to the application header with an unread completion count and a compact recent-completions popover.",
        "Opening the bell marks the currently scoped completion entries seen; Clear dismisses those bell entries only in the current browser.",
        "View all notifications opens the existing Notifications destination for complete torrent, security, account, update, integration, and system history.",
        "The bell follows the selected client scope and is responsive on both desktop and mobile without replacing existing browser/sound completion notifications."
    ],
    "fixes": [],
    "technical": [
        "The bell derives from the existing /api/events HistoryStore feed; no backend event-deletion route or alternate notification store is introduced.",
        "Seen and cleared completion-event tokens are stored browser-locally with bounded localStorage sets, so dismissal cannot mutate shared application history.",
        "The event feed refreshes quietly every ten seconds and requests an additional refresh shortly after a live completion transition so the bell updates promptly."
    ],
    "validation": [
        "The UI audit requires the bell controls, local Material icon, browser-local seen/cleared state, quiet refresh path, completion-triggered synchronization, and absence of a server-side clear endpoint.",
        "Manual coverage verifies unread/seen/clear behavior, durable full-history preservation, client-scope isolation, new completions after clear, desktop/mobile layering, and View all navigation.",
        "Existing backend tests, JavaScript syntax checks, generated continuity files, frontend/service-worker synchronization, and prerelease package-integrity gates remain required."
    ],
    "known_issues": [],
    "decisions": decisions,
})
metadata_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

# Regenerate all derived release/handoff state from the structured metadata.
subprocess.run(["python", str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", VERSION], cwd=ROOT, check=True)

print(f"Staged Torrent Dashboard {VERSION} header completion notification inbox")
