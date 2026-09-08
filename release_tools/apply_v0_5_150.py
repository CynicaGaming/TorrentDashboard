from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.5.150"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        if new in text:
            return
        raise SystemExit(f"Expected block not found in {path}: {old[:120]!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def update_version() -> None:
    init = ROOT / "src" / "torrent_dashboard" / "__init__.py"
    text = init.read_text(encoding="utf-8")
    if f'__version__ = "{VERSION}"' not in text:
        text = text.replace('__version__ = "0.5.149"', f'__version__ = "{VERSION}"', 1)
    init.write_text(text, encoding="utf-8")

    app = ROOT / "static" / "app.js"
    text = app.read_text(encoding="utf-8")
    text = text.replace("const FRONTEND_BUILD='0.5.149';", f"const FRONTEND_BUILD='{VERSION}';", 1)
    text = text.replace("$('#accountConsoleBtn')?.addEventListener('click',()=>{hideAccountMenu();setView('console')});", "", 1)
    app.write_text(text, encoding="utf-8")

    index = ROOT / "static" / "index.html"
    text = index.read_text(encoding="utf-8")
    old_glow = '''.login-card{\n  border-color:color-mix(in srgb,var(--accent) 34%,var(--border));\n  animation:login-accent-glow 5.5s ease-in-out infinite;\n}\n@keyframes login-accent-glow{\n  0%,100%{box-shadow:var(--shadow),0 0 0 1px color-mix(in srgb,var(--accent) 14%,transparent),0 0 20px color-mix(in srgb,var(--accent) 12%,transparent)}\n  50%{box-shadow:var(--shadow),0 0 0 1px color-mix(in srgb,var(--accent) 34%,transparent),0 0 36px color-mix(in srgb,var(--accent) 24%,transparent)}\n}\n@media (prefers-reduced-motion:reduce){\n  .login-card{animation:none;box-shadow:var(--shadow),0 0 0 1px color-mix(in srgb,var(--accent) 20%,transparent),0 0 24px color-mix(in srgb,var(--accent) 16%,transparent)}\n}\n'''
    new_glow = '''.login-card{\n  position:relative;\n  isolation:isolate;\n  border-color:color-mix(in srgb,var(--accent) 24%,var(--border));\n  box-shadow:var(--shadow),0 0 0 1px color-mix(in srgb,var(--accent) 8%,transparent);\n}\n.login-card::before{\n  content:"";\n  position:absolute;\n  inset:-18px;\n  z-index:-1;\n  border-radius:30px;\n  background:radial-gradient(ellipse at center,color-mix(in srgb,var(--accent) 28%,transparent) 0%,color-mix(in srgb,var(--accent) 13%,transparent) 44%,transparent 74%);\n  filter:blur(17px);\n  opacity:.46;\n  transform:scale(.985);\n  pointer-events:none;\n  animation:login-radiant-glow 7s ease-in-out infinite;\n}\n@keyframes login-radiant-glow{\n  0%,100%{opacity:.38;transform:scale(.985)}\n  50%{opacity:.68;transform:scale(1.015)}\n}\n@media (prefers-reduced-motion:reduce){\n  .login-card::before{animation:none;opacity:.52;transform:none}\n}\n'''
    if new_glow not in text:
        if old_glow not in text:
            raise SystemExit("Expected login glow block not found in static/index.html")
        text = text.replace(old_glow, new_glow, 1)
    text = text.replace("0.5.146", VERSION).replace("0.5.149", VERSION)
    index.write_text(text, encoding="utf-8")

    sw = ROOT / "static" / "sw.js"
    text = sw.read_text(encoding="utf-8")
    text = text.replace("0.5.149", VERSION).replace("v05149", "v05150")
    sw.write_text(text, encoding="utf-8")


def update_release_notes() -> None:
    path = ROOT / "release_notes" / "releases.json"
    notes = json.loads(path.read_text(encoding="utf-8"))
    if any(str(item.get("version")) == VERSION for item in notes.get("releases", [])):
        return
    notes["releases"].insert(0, {
        "version": VERSION,
        "date": "2026-09-07",
        "status": "prerelease",
        "title": "Login glow and profile menu polish",
        "summary": "Refines the login accent treatment and simplifies the profile menu while restoring frontend build-version synchronization on main.",
        "highlights": [
            "The login card now uses a softer radial accent glow around the card instead of animating the card shadow itself.",
            "The glow pulses more slowly and keeps a static reduced-motion presentation for users who disable animation.",
            "The profile menu keeps account settings, install-app, and sign-out actions without a stale duplicate Console binding."
        ],
        "fixes": [
            "Restores the HTML, JavaScript, and service-worker build identifiers to one release version after the prior branch merge left index.html on an older build marker.",
            "Removes the obsolete accountConsoleBtn event binding now that Console is reached through primary navigation."
        ],
        "technical": [
            "Moves the login glow to a ::before pseudo-element so the card border and primary shadow remain stable during the animation.",
            "Synchronizes the frontend build marker, cache-busted asset URLs, JavaScript build constant, and service-worker cache key to v0.5.150."
        ],
        "validation": [
            "Runs source validation, UI contract validation, the unit-test suite, JavaScript syntax checks, generated-documentation checks, and repository hygiene checks.",
            "Runs the normal pull-request matrix on Linux and Windows with Python 3.13 and 3.14 before merge."
        ],
        "known_issues": [
            "Portable backup archives still contain saved client and integration credentials in plaintext; store exported .tdbackup files securely."
        ],
        "architecture": [],
        "decisions": [
            "Keep Console in primary navigation instead of duplicating it inside the profile menu.",
            "Keep login animation isolated to a decorative pseudo-element with a reduced-motion fallback."
        ],
        "next_steps": [
            {
                "priority": 1,
                "title": "Soak the login treatment",
                "detail": "Exercise the login screen across accent colors, reduced-motion mode, desktop, and mobile while continuing compiled Windows update testing."
            }
        ]
    })
    path.write_text(json.dumps(notes, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    update_version()
    update_release_notes()


if __name__ == "__main__":
    main()
