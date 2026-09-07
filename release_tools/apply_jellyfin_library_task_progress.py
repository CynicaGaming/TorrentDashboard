#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one match in {path}: found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    jellyfin = ROOT / "torrent_dashboard" / "jellyfin.py"
    tests = ROOT / "tests" / "test_jellyfin.py"
    settings = ROOT / "static" / "settings.js"
    dashboard = ROOT / "dashboard.py"
    index = ROOT / "static" / "index.html"
    appjs = ROOT / "static" / "app.js"
    sw = ROOT / "static" / "sw.js"
    releases = ROOT / "release_notes" / "releases.json"
    ui_validator = ROOT / "release_tools" / "validate_ui_strings.py"

    replace_once(
        jellyfin,
        '''def refresh_jellyfin_libraries(item, *, opener=None):\n    """Request Jellyfin's normal global library scan."""\n    _jellyfin_request(item, "/Library/Refresh", method="POST", expect_json=False, opener=opener)\n    return {"ok": True, "message": "Jellyfin library refresh requested"}\n''',
        '''def _is_library_scan_task(task):\n    key = str(task.get("key") or "").strip().lower()\n    name = str(task.get("name") or "").strip().lower()\n    return key == "refreshmedialibrarytask" or "refreshmedialibrary" in key or name in {"scan media library", "scan library"}\n\n\ndef jellyfin_library_scan_task(item, *, opener=None):\n    """Return Jellyfin's real Scan Media Library scheduled task."""\n    task = next((task for task in jellyfin_scheduled_tasks(item, opener=opener) if _is_library_scan_task(task)), None)\n    if not task:\n        raise RuntimeError("Jellyfin did not report a Scan Media Library scheduled task")\n    return task\n\n\ndef refresh_jellyfin_libraries(item, *, opener=None):\n    """Start Jellyfin's real Scan Media Library scheduled task."""\n    task = jellyfin_library_scan_task(item, opener=opener)\n    start_jellyfin_scheduled_task(item, task["id"], opener=opener)\n    return {"ok": True, "message": "Jellyfin library scan started", "task": task}\n''',
    )
    replace_once(
        jellyfin,
        '    "jellyfin_libraries",\n    "jellyfin_overview",',
        '    "jellyfin_libraries",\n    "jellyfin_library_scan_task",\n    "jellyfin_overview",',
    )

    replace_once(
        tests,
        '''    def test_refresh_uses_global_library_scan_endpoint(self):\n        calls = []\n\n        def opener(request, timeout=0):\n            calls.append((request.full_url, request.get_method(), request.headers.get("X-emby-token"), timeout))\n            return FakeResponse()\n\n        result = refresh_jellyfin_libraries(self.item(), opener=opener)\n        self.assertTrue(result["ok"])\n        self.assertEqual(calls[0][0], "http://jellyfin:8096/Library/Refresh")\n        self.assertEqual(calls[0][1], "POST")\n        self.assertEqual(calls[0][2], "secret-key")\n''',
        '''    def test_refresh_starts_real_scan_media_library_scheduled_task(self):\n        calls = []\n\n        def opener(request, timeout=0):\n            calls.append((request.full_url, request.get_method(), request.headers.get("X-emby-token"), timeout))\n            if request.full_url.endswith("/ScheduledTasks?isHidden=false"):\n                return FakeResponse([\n                    {\n                        "Id": "scan-task",\n                        "Key": "RefreshMediaLibraryTask",\n                        "Name": "Scan Media Library",\n                        "Category": "Library",\n                        "State": "Idle",\n                        "CurrentProgressPercentage": None,\n                    },\n                    {\n                        "Id": "other-task",\n                        "Key": "Plugin.Task",\n                        "Name": "Other task",\n                        "Category": "Plugin",\n                        "State": "Idle",\n                    },\n                ])\n            return FakeResponse()\n\n        result = refresh_jellyfin_libraries(self.item(), opener=opener)\n        self.assertTrue(result["ok"])\n        self.assertEqual(result["task"]["id"], "scan-task")\n        self.assertEqual(calls[0][0], "http://jellyfin:8096/ScheduledTasks?isHidden=false")\n        self.assertEqual(calls[0][1], "GET")\n        self.assertEqual(calls[1][0], "http://jellyfin:8096/ScheduledTasks/Running/scan-task")\n        self.assertEqual(calls[1][1], "POST")\n        self.assertTrue(all(call[2] == "secret-key" for call in calls))\n''',
    )

    text = settings.read_text(encoding="utf-8")
    start = text.index("  function jellyfinLibraryScanState(libraries) {")
    end = text.index("  function renderJellyfinOverview(card, data) {", start)
    replacement = '''  function isJellyfinLibraryScanTask(task) {\n    const key=String(task?.key||'').trim().toLowerCase();\n    const name=String(task?.name||'').trim().toLowerCase();\n    return key==='refreshmedialibrarytask'||key.includes('refreshmedialibrary')||name==='scan media library'||name==='scan library';\n  }\n\n  function renderJellyfinLibraryProgress(card,task) {\n    const host=card.querySelector('[data-jellyfin-library-progress]');if(!host)return;\n    if(!task?.running){host.classList.add('hidden');host.innerHTML='';return}\n    const progress=task.progress==null?null:Number(task.progress);\n    const percentage=Number.isFinite(progress)?`${Math.round(Math.max(0,Math.min(100,progress)))}%`:'';\n    host.classList.remove('hidden');\n    host.innerHTML=`<article class="jellyfin-task-row running"><span class="jellyfin-task-clock">${jellyfinTaskIcon('cycle')}</span><div class="jellyfin-task-copy"><strong>${esc(task.name||'Scan Media Library')}</strong><span>${esc(jellyfinTaskSubtitle(task))}</span></div><strong class="jellyfin-library-progress-value">${esc(percentage||'…')}</strong></article>`;\n  }\n\n'''
    settings.write_text(text[:start] + replacement + text[end:], encoding="utf-8")

    replace_once(settings, "    renderJellyfinLibraryProgress(card,libraries);\n", "")
    replace_once(
        settings,
        "    const runtime=card.querySelector('[data-jellyfin-service]');if(runtime)runtime.dataset.taskRunning=tasks.some(task=>task.running)?'1':'0';\n    if(!tasks.length){list.innerHTML='<div class=\"integration-service-empty\">No scheduled tasks reported</div>';return}",
        "    const runtime=card.querySelector('[data-jellyfin-service]');\n    const scanTask=tasks.find(isJellyfinLibraryScanTask)||null;\n    const wasLibraryScanRunning=runtime?.dataset.libraryScanRunning==='1';\n    const libraryScanRunning=!!scanTask?.running;\n    if(runtime){runtime.dataset.taskRunning=tasks.some(task=>task.running)?'1':'0';runtime.dataset.libraryScanRunning=libraryScanRunning?'1':'0'}\n    renderJellyfinLibraryProgress(card,scanTask);\n    if(wasLibraryScanRunning&&!libraryScanRunning)setTimeout(()=>loadJellyfinOverview(card),0);\n    if(!tasks.length){list.innerHTML='<div class=\"integration-service-empty\">No scheduled tasks reported</div>';return}",
    )
    replace_once(
        settings,
        "try{const data=await api(`/api/integrations/jellyfin/status?id=${encodeURIComponent(card.dataset.id)}`);runtime.dataset.loaded='1';renderJellyfinOverview(card,data);if(runtime.dataset.libraryScanning==='1')scheduleJellyfinLibraryPoll(card)}catch(error)",
        "try{const data=await api(`/api/integrations/jellyfin/status?id=${encodeURIComponent(card.dataset.id)}`);runtime.dataset.loaded='1';renderJellyfinOverview(card,data)}catch(error)",
    )
    replace_once(
        settings,
        "try{const result=await post('/api/integrations/jellyfin/refresh',{id:card.dataset.id});toast(result.message||'Jellyfin library refresh requested');scheduleJellyfinLibraryPoll(card,true);await new Promise(resolve=>setTimeout(resolve,500));await loadJellyfinOverview(card)}catch(error)",
        "try{const result=await post('/api/integrations/jellyfin/refresh',{id:card.dataset.id});toast(result.message||'Jellyfin library scan started');await new Promise(resolve=>setTimeout(resolve,350));await loadJellyfinTasks(card,{quiet:true})}catch(error)",
    )

    replace_once(
        ui_validator,
        "    assert '/System/Info' in jellyfin_py and '/Library/VirtualFolders' in jellyfin_py and '/Library/Refresh' in jellyfin_py\n",
        "    assert '/System/Info' in jellyfin_py and '/Library/VirtualFolders' in jellyfin_py and '/ScheduledTasks?isHidden=false' in jellyfin_py\n",
    )

    replace_once(dashboard, 'VERSION = "0.5.132"', 'VERSION = "0.5.133"')
    index_text = index.read_text(encoding="utf-8")
    if index_text.count("0.5.132") != 5:
        raise RuntimeError(f"Unexpected index version count: {index_text.count('0.5.132')}")
    index.write_text(index_text.replace("0.5.132", "0.5.133"), encoding="utf-8")
    replace_once(appjs, "const FRONTEND_BUILD='0.5.132';", "const FRONTEND_BUILD='0.5.133';")
    replace_once(sw, "torrent-dashboard-v05132", "torrent-dashboard-v05133")
    sw_text = sw.read_text(encoding="utf-8")
    if sw_text.count("v=0.5.132") != 4:
        raise RuntimeError("Unexpected service-worker asset version count")
    sw.write_text(sw_text.replace("v=0.5.132", "v=0.5.133"), encoding="utf-8")

    data = json.loads(releases.read_text(encoding="utf-8"))
    if any(str(item.get("version")) == "0.5.133" for item in data.get("releases", [])):
        raise RuntimeError("v0.5.133 metadata already exists")
    data["releases"].insert(0, {
        "version": "0.5.133",
        "date": "2026-09-07",
        "status": "prerelease",
        "title": "Jellyfin scan task progress",
        "summary": "Drives the Libraries scan indicator from Jellyfin's real Scan Media Library scheduled task rather than virtual-folder refresh polling.",
        "highlights": [
            "Starts Jellyfin's actual Scan Media Library scheduled task when the Libraries cycle control is pressed.",
            "Uses that task's CurrentProgressPercentage and running state for the compact Libraries progress row.",
            "Reuses the existing Scheduled tasks refresh loop instead of running a separate library-overview polling loop."
        ],
        "fixes": [
            "Removes the v0.5.132 virtual-folder progress inference and dedicated library-status polling loop."
        ],
        "technical": [
            "Identifies the built-in scan task by RefreshMediaLibraryTask key with a name fallback for compatibility.",
            "Refreshes the library overview once when the real scheduled scan transitions from running to idle."
        ],
        "validation": [
            "Source validation, unit tests, UI-string validation, JavaScript syntax checks, and release-note checks run before publication."
        ],
        "known_issues": [], "architecture": [], "decisions": [], "next_steps": []
    })
    releases.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    subprocess.run(["python", str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", "0.5.133"], cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
