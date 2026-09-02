#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def write(path, content):
    (ROOT / path).write_text(content, encoding="utf-8")


def replace_once(text, old, new, label):
    if old not in text:
        raise RuntimeError(f"Missing migration anchor: {label}")
    return text.replace(old, new, 1)


# Backend: retain the complete source metadata, but only expose the two most
# recent releases to the Settings -> Updates presentation layer.
dashboard = read("dashboard.py")
dashboard = replace_once(dashboard, 'VERSION = "0.5.58"', 'VERSION = "0.5.59"', "dashboard version")
dashboard = replace_once(
    dashboard,
    "def local_release_history(latest_manifest=None,limit=30):",
    "def local_release_history(latest_manifest=None,limit=2):",
    "release history limit",
)
write("dashboard.py", dashboard)

# Frontend: keep only the latest two releases and present them as compact,
# readable release cards. Preserve structured titles when GitHub metadata is
# merged so the user does not see the generic GitHub release title.
app = read("static/app.js")
app = replace_once(app, "const FRONTEND_BUILD='0.5.58';", "const FRONTEND_BUILD='0.5.59';", "frontend build")
pattern = re.compile(r"function normalizedReleaseHistory\(history=\[\],manifest=\{\}\)\{.*?\}\nfunction renderUpdateInfo", re.S)
replacement = r'''function releaseDisplayDate(value=''){if(!value)return'';const raw=String(value);const date=new Date(/^\d{4}-\d{2}-\d{2}$/.test(raw)?`${raw}T12:00:00Z`:raw);if(Number.isNaN(date.getTime()))return raw.slice(0,10);return new Intl.DateTimeFormat(undefined,{year:'numeric',month:'short',day:'numeric'}).format(date)}
function normalizedReleaseHistory(history=[],manifest={}){
  const entries=Array.isArray(history)?history.filter(x=>x&&x.version).map(x=>({...x,version:String(x.version).replace(/^v/i,'')})):[];
  if(manifest?.version){
    const version=String(manifest.version).replace(/^v/i,'');
    const remote={version,title:manifest.title||`Torrent Dashboard v${version}`,publishedAt:manifest.publishedAt||'',channel:manifest.channel||'',notes:manifest.notes||'',source:'github'};
    const i=entries.findIndex(x=>x.version===version);
    if(i>=0){const existing=entries[i];entries[i]={...existing,publishedAt:remote.publishedAt||existing.publishedAt,channel:remote.channel||existing.channel,notes:remote.notes||existing.notes,source:'github'}}
    else entries.push(remote);
  }
  const seen=new Set();
  return entries.sort((a,b)=>compareUpdateVersions(b.version,a.version)).filter(x=>{if(seen.has(x.version))return false;seen.add(x.version);return true}).slice(0,2)
}
function renderUpdateHistory(history=[],manifest={},currentVersion=''){
  const wrap=$('#updateNotesWrap'),list=$('#updateNotesList');if(!wrap||!list)return;
  const entries=normalizedReleaseHistory(history,manifest);wrap.classList.toggle('hidden',!entries.length);list.replaceChildren();
  const current=String(currentVersion||'').replace(/^v/i,'');
  entries.forEach((entry,index)=>{
    const article=document.createElement('article');article.className=`update-release${index===0?' featured':''}`;
    const summary=document.createElement('button');summary.type='button';summary.className='update-release-summary';
    const open=index===0;summary.setAttribute('aria-expanded',String(open));
    const version=document.createElement('span');version.className='update-release-version';version.textContent=`v${entry.version}`;
    const copy=document.createElement('span');copy.className='update-release-copy';
    const title=document.createElement('strong');title.textContent=entry.title||`Torrent Dashboard ${entry.version}`;copy.appendChild(title);
    const meta=document.createElement('span');meta.className='update-release-meta';
    const badge=(text,kind='')=>{const el=document.createElement('span');el.className=`update-release-badge${kind?` ${kind}`:''}`;el.textContent=text;meta.appendChild(el)};
    if(index===0)badge('Latest release','latest');
    if(entry.version===current)badge('Installed','installed');
    if(entry.channel)badge(entry.channel==='prerelease'?'Pre-release':'Stable',entry.channel==='prerelease'?'prerelease':'stable');
    if(entry.publishedAt){const date=document.createElement('small');date.className='update-release-date';date.textContent=releaseDisplayDate(entry.publishedAt);meta.appendChild(date)}
    copy.appendChild(meta);
    const chevron=document.createElement('span');chevron.className='update-release-chevron';chevron.textContent='⌄';summary.append(version,copy,chevron);
    const body=document.createElement('div');body.className=`update-release-body${open?'':' hidden'}`;
    const noteText=String(entry.notes||entry.summary||'No patch notes were recorded for this revision.').replace(/^##\s+[^\n]+\n*/,'').trim();
    renderPatchMarkdown(body,noteText||entry.summary||'No patch notes were recorded for this revision.');
    summary.addEventListener('click',()=>{const next=body.classList.contains('hidden');body.classList.toggle('hidden',!next);summary.setAttribute('aria-expanded',String(next))});
    article.append(summary,body);list.appendChild(article)
  })
}
function renderUpdateInfo'''
app, count = pattern.subn(replacement, app, count=1)
if count != 1:
    raise RuntimeError("Could not replace release history renderer")
write("static/app.js", app)

# HTML/cache version and concise heading copy.
index = read("static/index.html")
index = index.replace('0.5.58', '0.5.59')
index = replace_once(index, '<div class="update-notes-heading"><div><strong>Patch Notes</strong><span>Release history</span></div></div>', '<div class="update-notes-heading"><div><strong>Patch Notes</strong><span>Latest two releases</span></div></div>', "patch notes heading")
write("static/index.html", index)

sw = read("static/sw.js").replace("torrent-dashboard-v0558", "torrent-dashboard-v0559").replace("0.5.58", "0.5.59")
write("static/sw.js", sw)

# Replace the initial accordion styling with a cleaner release-card treatment.
css = read("static/app.css")
marker = "/* Collapsible revision history in Settings > Updates. */"
if marker not in css:
    raise RuntimeError("Missing release history CSS marker")
css = css.split(marker, 1)[0].rstrip() + r'''

/* 0.5.59 compact release notes in Settings > Updates. */
.update-notes{margin-top:18px;padding-top:17px;border-top:1px solid color-mix(in srgb,var(--border) 72%,transparent)}
.update-notes-heading{display:flex;align-items:end;justify-content:space-between;gap:12px;margin-bottom:10px}.update-notes-heading>div{display:grid;gap:3px}.update-notes-heading strong{font-size:12px;color:var(--text)}.update-notes-heading span{font-size:9px;color:var(--muted)}
.update-release-list{display:grid;gap:10px}
.update-release{overflow:hidden;border:1px solid var(--border);border-radius:14px;background:linear-gradient(180deg,color-mix(in srgb,var(--panel2) 72%,var(--panel)),var(--panel));box-shadow:0 8px 24px rgba(0,0,0,.08)}
.update-release.featured{border-color:color-mix(in srgb,var(--accent) 30%,var(--border));box-shadow:inset 0 1px 0 color-mix(in srgb,var(--accent) 8%,transparent),0 8px 24px rgba(0,0,0,.08)}
.update-release-summary{width:100%;display:grid;grid-template-columns:auto minmax(0,1fr) auto;align-items:center;gap:12px;padding:14px 15px;border:0;border-radius:0;background:transparent;color:inherit;text-align:left;cursor:pointer}.update-release-summary:hover{background:color-mix(in srgb,var(--panel2) 56%,transparent)}
.update-release-version{display:inline-flex;align-items:center;justify-content:center;min-width:64px;padding:6px 8px;border:1px solid color-mix(in srgb,var(--accent) 25%,var(--border));border-radius:9px;background:color-mix(in srgb,var(--accent) 8%,var(--panel3));color:var(--accent);font:700 10px/1 ui-monospace,SFMono-Regular,Consolas,"Liberation Mono",monospace;letter-spacing:-.02em}
.update-release-copy{display:grid;gap:7px;min-width:0}.update-release-copy>strong{font-size:11.5px;line-height:1.35;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.update-release-meta{display:flex;align-items:center;gap:5px;flex-wrap:wrap}
.update-release-badge{display:inline-flex;align-items:center;min-height:20px;padding:3px 7px;border:1px solid var(--border);border-radius:999px;background:var(--panel3);color:var(--muted);font-size:8px;line-height:1}.update-release-badge.latest{border-color:color-mix(in srgb,var(--accent) 30%,var(--border));color:var(--accent)}.update-release-badge.installed{border-color:color-mix(in srgb,var(--good) 34%,var(--border));color:var(--good)}.update-release-badge.stable{color:var(--good)}.update-release-date{margin-left:2px;color:var(--muted);font-size:8.5px}
.update-release-chevron{display:grid;place-items:center;width:28px;height:28px;border-radius:8px;color:var(--muted);font-size:15px;transition:transform .16s ease,background .16s ease}.update-release-summary:hover .update-release-chevron{background:var(--panel3)}.update-release-summary[aria-expanded="true"] .update-release-chevron{transform:rotate(180deg)}
.update-release-body{padding:14px 15px 16px;border-top:1px solid color-mix(in srgb,var(--border) 78%,transparent);font-size:10px;line-height:1.6}.update-release-body>p:first-child{margin:0 0 14px;padding:11px 12px;border:1px solid color-mix(in srgb,var(--border) 72%,transparent);border-radius:10px;background:var(--panel3);color:var(--text);font-size:10.5px}.update-release-body h4,.update-release-body h5{margin:15px 0 7px;color:var(--text);font-size:9px;text-transform:uppercase;letter-spacing:.07em}.update-release-body p{margin:7px 0;color:var(--muted)}.update-release-body ul{display:grid;gap:6px;margin:7px 0;padding:0;list-style:none}.update-release-body li{position:relative;padding-left:14px;color:var(--muted)}.update-release-body li::before{content:"";position:absolute;left:1px;top:.7em;width:5px;height:5px;border-radius:50%;background:color-mix(in srgb,var(--accent) 72%,var(--muted))}
@media(max-width:620px){.update-release-summary{grid-template-columns:auto minmax(0,1fr) auto;gap:9px;padding:12px}.update-release-version{min-width:58px;font-size:9px}.update-release-copy>strong{font-size:10.5px}.update-release-badge{font-size:7.5px}.update-release-body{padding:12px}.update-release-date{flex-basis:100%;margin-left:0}}
'''
write("static/app.css", css)

# Structured release metadata remains complete. Add the UI refinement as the
# newest record, then regenerate the changelog and project handoff from it.
meta_path = ROOT / "release_notes" / "releases.json"
meta = json.loads(meta_path.read_text(encoding="utf-8"))
if any(str(x.get("version")) == "0.5.59" for x in meta.get("releases", [])):
    raise RuntimeError("v0.5.59 release metadata already exists")
previous = next(x for x in meta["releases"] if str(x.get("version")) == "0.5.58")
entry = {
    "version": "0.5.59",
    "date": "2026-09-02",
    "status": "prerelease",
    "title": "Patch notes presentation cleanup",
    "summary": "Simplified Settings → Updates to focus on the latest two releases while retaining the complete release history for changelog and project handoff purposes, with a cleaner release-card presentation.",
    "highlights": [
        "Settings → Updates now shows only the latest release and the immediately previous release instead of the complete historical list.",
        "Release cards now use a dedicated version badge, release-status badges, publication date, clearer typography, and improved spacing.",
        "The expanded release no longer repeats the version/title heading inside the patch-note body.",
        "The full structured release history remains preserved in release_notes/releases.json, CHANGELOG.md, and PROJECT_STATE.md."
    ],
    "fixes": [
        "Reduced unnecessary scrolling and visual noise on the Updates page without discarding historical release records."
    ],
    "technical": [
        "The backend releaseHistory response now defaults to two entries and the frontend independently caps the normalized list at two entries.",
        "Structured local titles are preserved when the matching GitHub release manifest is merged, avoiding generic GitHub release titles in the UI."
    ],
    "validation": [
        "Python compilation validates the two-entry release-history backend path.",
        "JavaScript syntax validation covers the revised release-card renderer and two-entry cap.",
        "Generated CHANGELOG.md and PROJECT_STATE.md must match the v0.5.59 metadata before publication."
    ],
    "known_issues": [],
    "architecture": list(previous.get("architecture", [])),
    "decisions": list(previous.get("decisions", [])) + [
        "Keep complete release history in repository metadata while limiting the in-app Updates view to the two most recent releases."
    ],
    "next_steps": list(previous.get("next_steps", [])),
}
meta["releases"].append(entry)
meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

subprocess.run([sys.executable, str(ROOT / "release_tools" / "generate_release_notes.py"), "--version", "0.5.59"], cwd=ROOT, check=True)

# Guard the intended user-visible contract before CI validates the applied tree.
assert 'VERSION = "0.5.59"' in read("dashboard.py")
assert "def local_release_history(latest_manifest=None,limit=2):" in read("dashboard.py")
assert "slice(0,2)" in read("static/app.js")
assert "Latest two releases" in read("static/index.html")
assert "torrent-dashboard-v0559" in read("static/sw.js")
assert "Patch notes presentation cleanup" in read("PROJECT_STATE.md")

print("Applied v0.5.59 patch notes presentation cleanup")
