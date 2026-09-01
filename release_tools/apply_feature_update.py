#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.6"
NEW = "0.5.7"
CAMEL = re.compile(r"[a-z0-9][A-Z]")


def replace_once(text, old, new, label):
    if old not in text:
        raise RuntimeError(f"Could not find {label}")
    return text.replace(old, new, 1)


def patch_dashboard():
    path = ROOT / "dashboard.py"
    text = path.read_text(encoding="utf-8")
    text = replace_once(text, f'VERSION = "{OLD}"', f'VERSION = "{NEW}"', "dashboard version")
    path.write_text(text, encoding="utf-8")


def patch_app_js():
    path = ROOT / "static" / "app.js"
    text = path.read_text(encoding="utf-8")
    start = text.index("function applySentenceCaseUi(root=document){")
    end = text.index("const CONFIGURED_SECRET_MASK=", start)
    replacement = '''function hasCamelCaseUiText(value=''){return /[a-z0-9][A-Z]/.test(String(value||''))}\nfunction normalizeUiAttributes(el){\n  if(!el?.getAttribute)return;\n  for(const attr of ['placeholder','title','aria-label']){\n    const raw=el.getAttribute(attr);\n    if(raw&&hasCamelCaseUiText(raw))el.setAttribute(attr,uiText(raw));\n  }\n}\nfunction applySentenceCaseUi(root=document){\n  const selectors='button,label,th,option,h1,h2,h3,h4,.panel-title,.settings-section-title,.eyebrow,.nav,.mobile-nav,.detail-tabs,legend,.metric span,.field-row b,.review-grid span,.update-status span,.brand strong,.brand small,.setup-rail strong,.setup-rail small,#setupSteps button';\n  const els=[];\n  if(root.matches?.(selectors))els.push(root);\n  els.push(...(root.querySelectorAll?.(selectors)||[]));\n  els.forEach(el=>{\n    normalizeUiAttributes(el);\n    for(const n of [...el.childNodes]){\n      if(n.nodeType===Node.TEXT_NODE){\n        const raw=n.nodeValue,trim=raw.trim();\n        if(trim&&trim.length<80&&/[A-Za-z]/.test(trim))n.nodeValue=raw.replace(trim,uiText(trim));\n      }\n    }\n  });\n  const attrEls=[];\n  if(root.matches?.('[placeholder],[title],[aria-label]'))attrEls.push(root);\n  attrEls.push(...(root.querySelectorAll?.('[placeholder],[title],[aria-label]')||[]));\n  attrEls.forEach(normalizeUiAttributes);\n}\n'''
    text = text[:start] + replacement + text[end:]

    old_observer = "const caseObserver=new MutationObserver(records=>{for(const r of records){for(const n of r.addedNodes){if(n.nodeType===Node.ELEMENT_NODE){applySentenceCaseUi(n);decorateSecretFields(n)}}}});"
    new_observer = "const caseObserver=new MutationObserver(records=>{for(const r of records){if(r.type==='attributes'){applySentenceCaseUi(r.target);continue}for(const n of r.addedNodes){if(n.nodeType===Node.ELEMENT_NODE){applySentenceCaseUi(n);decorateSecretFields(n)}else if(n.nodeType===Node.TEXT_NODE&&n.parentElement){applySentenceCaseUi(n.parentElement)}}}});"
    text = replace_once(text, old_observer, new_observer, "sentence-case observer")

    old_watch = "caseObserver.observe(document.body,{childList:true,subtree:true});"
    new_watch = "caseObserver.observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['placeholder','title','aria-label']});"
    text = replace_once(text, old_watch, new_watch, "sentence-case observer options")
    path.write_text(text, encoding="utf-8")


def patch_settings_js():
    path = ROOT / "static" / "settings.js"
    text = path.read_text(encoding="utf-8")
    text = text.replace("applyTitleCaseUi", "applySentenceCaseUi")
    path.write_text(text, encoding="utf-8")


def patch_index():
    path = ROOT / "static" / "index.html"
    text = path.read_text(encoding="utf-8")
    text = text.replace(f"?v={OLD}", f"?v={NEW}")
    text = text.replace('placeholder="searchTorrents…"', 'placeholder="Search torrents…"')
    text = text.replace('title="saveCurrentFilters"', 'title="Save current filters"')

    # Catch any other camelCase values in explicitly user-facing HTML attributes.
    attr_re = re.compile(r'(?P<prefix>\b(?:placeholder|title|aria-label)=")(?P<value>[^"]*)(?P<suffix>")')
    offenders = []
    for match in attr_re.finditer(text):
        value = match.group('value')
        if CAMEL.search(value):
            offenders.append(value)
    if offenders:
        raise RuntimeError(f"Unconverted camelCase UI attributes remain: {offenders}")
    path.write_text(text, encoding="utf-8")


def patch_sw():
    path = ROOT / "static" / "sw.js"
    text = path.read_text(encoding="utf-8")
    text = text.replace("torrent-dashboard-v056", "torrent-dashboard-v057")
    text = text.replace(f"?v={OLD}", f"?v={NEW}")
    path.write_text(text, encoding="utf-8")


patch_dashboard()
patch_app_js()
patch_settings_js()
patch_index()
patch_sw()
print("Applied Torrent Dashboard 0.5.7 UI casing audit")
