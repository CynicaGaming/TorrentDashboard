#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.124"
NEW = "0.5.125"

def read(path): return (ROOT/path).read_text(encoding="utf-8")
def write(path, text): (ROOT/path).write_text(text, encoding="utf-8")
def once(text, old, new, label):
    count=text.count(old)
    if count != 1: raise RuntimeError(f"{label}: expected one match, found {count}")
    return text.replace(old,new,1)
def first(text, old, new, label):
    if old not in text: raise RuntimeError(f"{label}: target not found")
    return text.replace(old,new,1)

path="static/settings.js"; text=read(path)
old='<span class="accordion-chevron">⌄</span></button><div class="accordion-body ${index===0?\'\':\'hidden\'}">'
new='<span class="accordion-chevron">${jellyfinTaskIcon(\'chevron\')}</span></button><div class="accordion-body ${index===0?\'\':\'hidden\'}">'
text=first(text,old,new,"integration accordion chevron")
write(path,text)

path="static/settings.css"; text=read(path)
css='''\n\n/* 0.5.125 integration accordion chevron state */\n.integration-item>.accordion-summary>.accordion-chevron{display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;transition:transform .16s ease;transform:rotate(0deg);transform-origin:center}\n.integration-item>.accordion-summary>.accordion-chevron .material-symbol-icon{width:18px;height:18px;fill:currentColor}\n.integration-item>.accordion-summary[aria-expanded="true"]>.accordion-chevron{transform:rotate(90deg)}\n@media(prefers-reduced-motion:reduce){.integration-item>.accordion-summary>.accordion-chevron{transition:none}}\n'''
if "0.5.125 integration accordion chevron state" not in text: text += css
write(path,text)

path="dashboard.py"; text=read(path); text=once(text,f'VERSION = "{OLD}"',f'VERSION = "{NEW}"',"dashboard version"); write(path,text)
path="static/app.js"; text=read(path); text=once(text,f"const FRONTEND_BUILD='{OLD}';",f"const FRONTEND_BUILD='{NEW}';","frontend version"); write(path,text)
path="static/index.html"; text=read(path); text=text.replace(OLD,NEW); write(path,text)
path="static/sw.js"; text=read(path); text=text.replace(OLD,NEW).replace("torrent-dashboard-v05124","torrent-dashboard-v05125"); write(path,text)

path="release_notes/releases.json"; data=json.loads(read(path))
if not any(str(x.get("version"))==NEW for x in data.get("releases",[])):
    data.setdefault("releases",[]).append({
      "version":NEW,"date":"2026-09-06","status":"prerelease","title":"Integration accordion chevron fix",
      "summary":"Fixes the Integrations accordion disclosure indicator so its Material-style chevron visibly follows the expanded and collapsed state.",
      "highlights":["Replaces the static integration dropdown glyph with the same locally embedded Material-style chevron used by Jellyfin scheduled tasks.","Rotates the integration chevron from right when collapsed to down when expanded, including the initially open integration."],
      "fixes":["The Jellyfin integration header no longer appears to have a non-working chevron while its accordion body opens and closes."],
      "technical":["Chevron orientation is driven directly by the parent summary button's aria-expanded state, keeping visual and accessibility state synchronized."],
      "validation":["Full source validation, unit tests, UI-string validation, and JavaScript syntax checks are required before publication."],
      "known_issues":[],"architecture":[],"decisions":[],"next_steps":[]
    })
write(path,json.dumps(data,indent=2)+"\n")

path="development/current.json"; active=json.loads(read(path))
active["objective"]="Validate Jellyfin scheduled tasks and integration disclosure behavior"
active["why"]="v0.5.125 corrects the parent integration chevron while preserving the v0.5.124 dynamic Jellyfin scheduled-task controls."
active["acceptance_criteria"]=["Integration chevrons point right when collapsed and down when expanded.","Jellyfin Scheduled tasks continues to enumerate dynamic categories and tasks and can start/stop tasks.","No accordion interaction regresses on desktop or mobile."]
active["next_action"]="Smoke-test the Jellyfin integration accordion and Scheduled tasks controls against the maintainer's live Jellyfin server."
write(path,json.dumps(active,indent=2)+"\n")
