#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def write(path, text):
    (ROOT / path).write_text(text, encoding='utf-8')


def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit(f'Expected source not found for {label}')
    return text.replace(old, new, 1)


# --- dashboard.py: version, lower allocation transition tracking, crash diagnostics ---
path = 'dashboard.py'
text = read(path)
text = replace_once(text, 'import urllib.error\n', 'import urllib.error\nimport faulthandler\nimport traceback\n', 'diagnostic imports')
text = replace_once(text, 'VERSION = "0.5.34"', 'VERSION = "0.5.35"', 'version bump')
text = replace_once(
    text,
    'CUSTOM_SOUND_BASENAME = "custom-notification-sound"\n',
    'CUSTOM_SOUND_BASENAME = "custom-notification-sound"\nCRASH_LOG_PATH = DATA_DIR / "crash.log"\n_CRASH_LOG_HANDLE = None\n',
    'crash log constants',
)
text = replace_once(
    text,
    'LAST_COMPLETION_EVENT = set()\n',
    'LAST_COMPLETION_EVENT = set()\nTORRENT_NOTICE_CACHE = {}\n',
    'torrent notice cache',
)
text = replace_once(
    text,
    '                previous = list(old_cache.get("torrents", []))\n',
    '                previous = old_cache.get("torrents", [])\n',
    'avoid torrent list copy',
)
old_notice = '''                previous_by_hash = {str(t.get("hash") or ""): t for t in previous if t.get("hash")}\n                for torrent in torrents:\n                    hash_ = str(torrent.get("hash") or "")\n                    prior = previous_by_hash.get(hash_)\n                    if not prior:\n                        continue\n                    current_notice = torrent_runtime_notice_state(torrent)\n                    previous_notice = torrent_runtime_notice_state(prior)\n                    if current_notice and current_notice != previous_notice:\n                        HISTORY.event(sid, f"torrent_{current_notice}", torrent.get("name", "Torrent"), hash_, {})\n'''
new_notice = '''                # Keep only abnormal states between polls instead of building a full\n                # hash->torrent map for the entire library every second. This preserves\n                # transition events while keeping the added 0.5.34 work proportional to\n                # the number of abnormal torrents rather than the total library size.\n                current_notices = {}\n                for torrent in torrents:\n                    hash_ = str(torrent.get("hash") or "")\n                    if not hash_:\n                        continue\n                    notice = torrent_runtime_notice_state(torrent)\n                    if notice:\n                        current_notices[hash_] = (notice, torrent.get("name", "Torrent"))\n                previous_notices = TORRENT_NOTICE_CACHE.get(sid, {})\n                for hash_, (notice, name) in current_notices.items():\n                    if previous_notices.get(hash_) != notice:\n                        HISTORY.event(sid, f"torrent_{notice}", name, hash_, {})\n                TORRENT_NOTICE_CACHE[sid] = {hash_: notice for hash_, (notice, _name) in current_notices.items()}\n'''
text = replace_once(text, old_notice, new_notice, 'collector transition tracking')

main_marker = '''def main():\n    parser=argparse.ArgumentParser(description="Torrent Dashboard")\n'''
diag = '''def enable_crash_logging():\n    global _CRASH_LOG_HANDLE\n    try:\n        DATA_DIR.mkdir(exist_ok=True)\n        _CRASH_LOG_HANDLE = open(CRASH_LOG_PATH, "a", encoding="utf-8", buffering=1)\n        _CRASH_LOG_HANDLE.write(f"\\n--- Torrent Dashboard {VERSION} start {time.strftime('%Y-%m-%d %H:%M:%S')} ---\\n")\n        faulthandler.enable(_CRASH_LOG_HANDLE, all_threads=True)\n\n        def log_thread_exception(args):\n            try:\n                _CRASH_LOG_HANDLE.write(f"\\nUnhandled thread exception in {getattr(args.thread, 'name', 'thread')}:\\n")\n                traceback.print_exception(args.exc_type, args.exc_value, args.exc_traceback, file=_CRASH_LOG_HANDLE)\n            except Exception:\n                pass\n\n        threading.excepthook = log_thread_exception\n    except Exception:\n        _CRASH_LOG_HANDLE = None\n\n\ndef log_unhandled_exception():\n    try:\n        handle = _CRASH_LOG_HANDLE\n        if handle is None:\n            DATA_DIR.mkdir(exist_ok=True)\n            handle = open(CRASH_LOG_PATH, "a", encoding="utf-8")\n        handle.write(f"\\nUnhandled main-thread exception {time.strftime('%Y-%m-%d %H:%M:%S')}:\\n")\n        traceback.print_exc(file=handle)\n        handle.flush()\n        if handle is not _CRASH_LOG_HANDLE:\n            handle.close()\n    except Exception:\n        pass\n\n\ndef main():\n    parser=argparse.ArgumentParser(description="Torrent Dashboard")\n'''
text = replace_once(text, main_marker, diag, 'crash diagnostics functions')
text = replace_once(
    text,
    'if __name__=="__main__": main()\n',
    '''if __name__=="__main__":\n    enable_crash_logging()\n    try:\n        main()\n    except (KeyboardInterrupt, SystemExit):\n        raise\n    except BaseException:\n        log_unhandled_exception()\n        raise\n''',
    'main crash logging wrapper',
)
write(path, text)


# --- app.js: remove special large-library renderer and avoid disabled-rule scans ---
path = 'static/app.js'
text = read(path)
text = replace_once(text, 'const LARGE_LIBRARY_THRESHOLD=300;\n', '', 'large library threshold')
text = replace_once(text, ',rowRenderCache:new Map(),rowRenderOrder:[]', '', 'large library state cache')
start = text.find('function rowSignature(t)')
end = text.find('function rowHtml(t)', start)
if start < 0 or end < 0:
    raise SystemExit('Expected large-library renderer block not found')
simple_render = "function render(){const list=visibleTorrents();$('#torrentRows').innerHTML=list.map(rowHtml).join('');$('#empty').classList.toggle('hidden',list.length>0);$('#selectedCount').textContent=state.selected.size;$('#bulkbar').classList.toggle('hidden',!state.selected.size);$('#selectAll').checked=!!list.length&&list.every(t=>state.selected.has(keyFor(t)));updateFilters()}\n"
text = text[:start] + simple_render + text[end:]
old_runtime = "function checkTorrentRuntimeNotifications(){const next=new Map();for(const t of state.torrents){const key=keyFor(t),value=torrentNoticeState(t);next.set(key,value);if(!state.torrentNoticeReady||!value||state.torrentNoticeStates.get(key)===value)continue;const server=t._server_name?` on ${t._server_name}`:'';if(value==='error')dispatchNotificationRule('torrent_error','Torrent error',`${t.name||'Torrent'} entered an error state${server}.`,`torrent-error-${key}`).catch(()=>{});else dispatchNotificationRule('torrent_stalled','Torrent stalled',`${t.name||'Torrent'} is stalled${server}.`,`torrent-stalled-${key}`).catch(()=>{})}state.torrentNoticeStates=next;state.torrentNoticeReady=true}"
new_runtime = "function checkTorrentRuntimeNotifications(){const errorRule=notificationRule('torrent_error'),stalledRule=notificationRule('torrent_stalled'),errorEnabled=errorRule.browser||errorRule.sound,stalledEnabled=stalledRule.browser||stalledRule.sound;if(!errorEnabled&&!stalledEnabled){state.torrentNoticeStates.clear();state.torrentNoticeReady=false;return}const next=new Map();for(const t of state.torrents){const key=keyFor(t),value=torrentNoticeState(t);next.set(key,value);if(!state.torrentNoticeReady||!value||state.torrentNoticeStates.get(key)===value)continue;const server=t._server_name?` on ${t._server_name}`:'';if(value==='error'&&errorEnabled)dispatchNotificationRule('torrent_error','Torrent error',`${t.name||'Torrent'} entered an error state${server}.`,`torrent-error-${key}`).catch(()=>{});else if(value==='stalled'&&stalledEnabled)dispatchNotificationRule('torrent_stalled','Torrent stalled',`${t.name||'Torrent'} is stalled${server}.`,`torrent-stalled-${key}`).catch(()=>{})}state.torrentNoticeStates=next;state.torrentNoticeReady=true}"
text = replace_once(text, old_runtime, new_runtime, 'notification scan guard')
write(path, text)


# --- cache-bust browser assets for the hotfix ---
path = 'static/index.html'
text = read(path).replace('0.5.34', '0.5.35')
write(path, text)

path = 'static/sw.js'
text = read(path).replace("const CACHE='torrent-dashboard-v0533';", "const CACHE='torrent-dashboard-v0535';").replace('0.5.34', '0.5.35')
write(path, text)


# --- update release validation contract ---
path = 'release_tools/validate_ui_strings.py'
text = read(path)
text = replace_once(
    text,
    "    assert 'LARGE_LIBRARY_THRESHOLD=300' in app_js and 'renderTorrentRows' in app_js and 'rowRenderCache' in app_js\n",
    "    assert 'LARGE_LIBRARY_THRESHOLD' not in app_js and 'renderTorrentRows' not in app_js and 'rowRenderCache' not in app_js\n",
    'large renderer validator',
)
anchor = "    assert 'role=\"status\" aria-live=\"polite\"' in html\n"
extra = anchor + "    assert 'if(!errorEnabled&&!stalledEnabled)' in app_js\n    assert 'CRASH_LOG_PATH' in dashboard_py and 'faulthandler.enable' in dashboard_py and 'threading.excepthook' in dashboard_py\n    assert 'previous = list(old_cache.get(\"torrents\", []))' not in dashboard_py\n"
text = replace_once(text, anchor, extra, 'hotfix validators')
write(path, text)

print('Applied v0.5.35 crash stabilization hotfix.')
