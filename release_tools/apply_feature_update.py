#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def write(path, text):
    (ROOT / path).write_text(text, encoding="utf-8")


def replace_once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one {label} marker, found {count}")
    return text.replace(old, new, 1)


def main():
    dashboard = read("dashboard.py")
    dashboard = replace_once(dashboard, 'VERSION = "0.5.56"', 'VERSION = "0.5.57"', "dashboard version")
    write("dashboard.py", dashboard)

    app = read("static/app.js")
    app = replace_once(app, "const FRONTEND_BUILD='0.5.56';", "const FRONTEND_BUILD='0.5.57';", "frontend build")
    update_anchor = "function renderUpdateInfo(data){state.updateInfo=data||null;const current=data?.currentVersion||state.me?.version||'—',manifest=data?.manifest||{},st=data?.state||state.settings?.runtime?.updateState||{};"
    update_replacement = """function renderUpdateNotes(markdown='',version=''){
  const wrap=$('#updateNotesWrap'),box=$('#updateNotes'),versionEl=$('#updateNotesVersion');
  if(!wrap||!box)return;
  const text=String(markdown||'').trim();
  wrap.classList.toggle('hidden',!text);
  box.replaceChildren();
  if(versionEl)versionEl.textContent=version?`v${version}`:'';
  if(!text)return;
  let list=null;
  for(const raw of text.split(/\\r?\\n/)){
    const line=raw.trim();
    if(!line){list=null;continue}
    const heading=line.match(/^#{2,3}\\s+(.+)$/);
    if(heading){const h=document.createElement('h4');h.textContent=heading[1];box.appendChild(h);list=null;continue}
    const bullet=line.match(/^[-*]\\s+(.+)$/);
    if(bullet){if(!list){list=document.createElement('ul');box.appendChild(list)}const li=document.createElement('li');li.textContent=bullet[1];list.appendChild(li);continue}
    const p=document.createElement('p');p.textContent=line;box.appendChild(p);list=null;
  }
}
function renderUpdateInfo(data){state.updateInfo=data||null;const current=data?.currentVersion||state.me?.version||'—',manifest=data?.manifest||{},st=data?.state||state.settings?.runtime?.updateState||{};renderUpdateNotes(manifest.notes||st.manifest?.notes||'',manifest.version||st.version||'');"""
    app = replace_once(app, update_anchor, update_replacement, "update renderer")
    write("static/app.js", app)

    index = read("static/index.html")
    index = index.replace("0.5.56", "0.5.57")
    notes_anchor = '<div class="muted update-message" id="updateMessage">Check the configured public repository for a newer Torrent Dashboard release.</div>\n</div>'
    notes_replacement = '''<div class="muted update-message" id="updateMessage">Check the configured public repository for a newer Torrent Dashboard release.</div>
<div class="update-notes hidden" id="updateNotesWrap">
<div class="update-notes-heading"><strong>Patch Notes</strong><span id="updateNotesVersion"></span></div>
<div class="update-notes-content" id="updateNotes"></div>
</div>
</div>'''
    index = replace_once(index, notes_anchor, notes_replacement, "updates patch notes panel")
    write("static/index.html", index)

    sw = read("static/sw.js")
    sw = replace_once(sw, "torrent-dashboard-v0556", "torrent-dashboard-v0557", "service worker cache")
    sw = sw.replace("0.5.56", "0.5.57")
    write("static/sw.js", sw)

    css = read("static/settings.css")
    marker = "/* release-notes-pipeline */"
    if marker not in css:
        css += '''\n\n/* release-notes-pipeline */
.update-notes{margin-top:16px;padding-top:16px;border-top:1px solid var(--line,#2b3038)}
.update-notes-heading{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:10px}
.update-notes-heading span{font-size:12px;opacity:.68}
.update-notes-content{display:grid;gap:8px;font-size:13px;line-height:1.55}
.update-notes-content h4{margin:6px 0 0;font-size:13px}
.update-notes-content p{margin:0;color:var(--muted,#9aa3af)}
.update-notes-content ul{margin:0;padding-left:20px;color:var(--muted,#9aa3af)}
.update-notes-content li+li{margin-top:5px}
'''
    write("static/settings.css", css)

    subprocess.run([
        sys.executable,
        str(ROOT / "release_tools" / "generate_release_notes.py"),
        "--version", "0.5.57",
    ], cwd=ROOT, check=True)

    for path in (
        "dashboard.py",
        "release_tools/generate_release_notes.py",
        "torrent_dashboard/users.py",
        "torrent_dashboard/config_store.py",
    ):
        compile(read(path), path, "exec")

    expected = {
        "dashboard.py": 'VERSION = "0.5.57"',
        "static/app.js": "const FRONTEND_BUILD='0.5.57';",
        "static/index.html": 'content="0.5.57" name="torrent-dashboard-build"',
        "static/sw.js": "torrent-dashboard-v0557",
        "PROJECT_STATE.md": "Latest documented build: **v0.5.57**",
        "CHANGELOG.md": "## v0.5.57 — Release notes and project handoff pipeline",
    }
    for path, needle in expected.items():
        if needle not in read(path):
            raise RuntimeError(f"Validation failed for {path}: missing {needle}")

    if "renderUpdateNotes(manifest.notes" not in read("static/app.js"):
        raise RuntimeError("Updates UI is not wired to GitHub release notes")

    print("Applied v0.5.57 release notes and project handoff pipeline")


if __name__ == "__main__":
    main()
