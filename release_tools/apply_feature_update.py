#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"Could not find expected {label}")
    return text.replace(old, new, 1)


def patch_dashboard() -> None:
    path = ROOT / "dashboard.py"
    text = path.read_text(encoding="utf-8")
    text = replace_once(text, 'VERSION = "0.5.0"', 'VERSION = "0.5.1"', 'dashboard version')
    path.write_text(text, encoding="utf-8")


def patch_index() -> None:
    path = ROOT / "static" / "index.html"
    text = path.read_text(encoding="utf-8")
    text = text.replace('v=0.5.0', 'v=0.5.1')
    path.write_text(text, encoding="utf-8")


def patch_app() -> None:
    path = ROOT / "static" / "app.js"
    text = path.read_text(encoding="utf-8")
    text = text.replace("navigator.serviceWorker.register('/sw.js?v=0.5.0')", "navigator.serviceWorker.register('/sw.js?v=0.5.1')")
    path.write_text(text, encoding="utf-8")


def patch_settings_js() -> None:
    path = ROOT / "static" / "settings.js"
    text = path.read_text(encoding="utf-8")

    text = replace_once(
        text,
        "  const corePages = new Set(['general','access','clients','updates','notifications']);\n",
        "  const corePages = new Set(['general','access','clients','updates','notifications']);\n  const SECRET_MASK = '••••••••••';\n\n  function configuredSecret(input, configured, emptyPlaceholder='') {\n    if (!input) return;\n    input.value = '';\n    input.placeholder = configured ? SECRET_MASK : emptyPlaceholder;\n    input.classList.toggle('secret-configured', !!configured);\n    if (configured) input.dataset.configuredSecret = '1';\n    else delete input.dataset.configuredSecret;\n  }\n",
        'secret display helper',
    )

    text = replace_once(
        text,
        "    if (token) token.placeholder = s.updates?.github_token === '<configured>' ? 'Token Configured — Leave Blank To Keep' : 'Fine-grained token with Contents: Read';",
        "    configuredSecret(token, s.updates?.github_token === '<configured>', 'Fine-grained token with Contents: Read');",
        'GitHub token placeholder',
    )

    text = replace_once(
        text,
        "    renderServerSettings(s.servers || []);\n    const n = s.notifications || {};",
        "    renderServerSettings(s.servers || []);\n    [...document.querySelectorAll('.server-setting')].forEach((row, index) => {\n      const server = (s.servers || [])[index] || {};\n      configuredSecret(row.querySelector('[data-k=\"api_key\"]'), server.api_key === '<configured>', 'qbt_…');\n      configuredSecret(row.querySelector('[data-k=\"password\"]'), server.password === '<configured>', 'Password');\n    });\n    const n = s.notifications || {};",
        'download client secret masking',
    )

    text = replace_once(
        text,
        "    const placeholder = secret && configured ? 'Configured — Leave Blank To Keep' : (field.placeholder || '');\n    return `<label>${esc(field.label)}<input data-field=\"${esc(field.key)}\" ${secret?'data-secret=\"1\"':''} type=\"${esc(type)}\" autocomplete=\"off\" value=\"${secret?'':esc(value||'')}\" placeholder=\"${esc(placeholder)}\"></label>`;",
        "    const placeholder = secret && configured ? SECRET_MASK : (field.placeholder || '');\n    const secretClass = secret && configured ? ' class=\"secret-configured\" data-configured-secret=\"1\"' : '';\n    return `<label>${esc(field.label)}<input data-field=\"${esc(field.key)}\" ${secret?'data-secret=\"1\"':''}${secretClass} type=\"${esc(type)}\" autocomplete=\"off\" value=\"${secret?'':esc(value||'')}\" placeholder=\"${esc(placeholder)}\"></label>`;",
        'integration secret placeholder',
    )

    text = replace_once(
        text,
        "<label>Password${user._new?'':' <small>(Leave Blank To Keep)</small>'}<input data-user-field=\"password\" type=\"password\" autocomplete=\"new-password\"></label><label>Confirm Password<input data-user-field=\"password2\" type=\"password\" autocomplete=\"new-password\"></label>",
        "<label>Password<input data-user-field=\"password\" type=\"password\" autocomplete=\"new-password\" ${user._new?'placeholder=\"Create Password\"':'class=\"secret-configured\" data-configured-secret=\"1\" placeholder=\"'+SECRET_MASK+'\"'}></label><label>Confirm Password<input data-user-field=\"password2\" type=\"password\" autocomplete=\"new-password\" ${user._new?'placeholder=\"Confirm Password\"':'class=\"secret-configured\" data-configured-secret=\"1\" placeholder=\"'+SECRET_MASK+'\"'}></label>",
        'user password masking',
    )

    path.write_text(text, encoding="utf-8")


def patch_settings_css() -> None:
    path = ROOT / "static" / "settings.css"
    text = path.read_text(encoding="utf-8")
    text = replace_once(text, '.settings-page .settings-card{max-width:980px}', '.settings-page .settings-card{max-width:none;width:100%}', 'settings card width')

    polish = r'''

/* 0.5.1 settings polish: align page surfaces and keep configured secrets visually masked. */
.settings-layout{grid-template-columns:200px minmax(0,1fr);gap:18px}
.settings-content{min-width:0;width:100%}
.settings-page-head{padding:2px 2px 4px;margin-bottom:10px}
.settings-page-head h2{font-size:19px;letter-spacing:-.025em}
.settings-page-head p{max-width:760px}
.settings-nav{padding:8px;box-shadow:0 12px 32px rgba(0,0,0,.12)}
.settings-nav button{min-height:40px;padding:9px 11px}
.settings-nav button.active{background:linear-gradient(180deg,var(--panel2),color-mix(in srgb,var(--panel2) 84%,var(--panel3)));box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--accent) 12%,transparent)}
.settings-page .settings-card,.settings-savebar{width:100%}
.settings-card{overflow:hidden}
.settings-card>.panel-title{background:color-mix(in srgb,var(--panel2) 62%,transparent)}
.settings-savebar{padding:9px 10px}
.secret-configured::placeholder{color:var(--text);opacity:.62;letter-spacing:.12em}
.secret-configured:focus::placeholder{opacity:.35}
.secret-input .secret-configured{font-family:ui-monospace,SFMono-Regular,Consolas,"Liberation Mono",monospace}
@media(max-width:900px){.settings-layout{grid-template-columns:170px minmax(0,1fr);gap:12px}}
@media(max-width:820px){.settings-layout{display:block}.settings-page-head{padding-left:2px;padding-right:2px}.settings-nav{gap:5px}.settings-nav button{min-height:38px}}
@media(max-width:560px){.settings-page-head p{font-size:9px}.settings-nav{margin-left:-2px;margin-right:-2px}.settings-card{border-radius:13px}.settings-savebar{padding:8px}}
'''
    if '/* 0.5.1 settings polish:' not in text:
        text += polish
    path.write_text(text, encoding="utf-8")


def patch_sw() -> None:
    path = ROOT / "static" / "sw.js"
    text = path.read_text(encoding="utf-8")
    text = text.replace("torrent-dashboard-v050", "torrent-dashboard-v051")
    text = text.replace('v=0.5.0', 'v=0.5.1')
    path.write_text(text, encoding="utf-8")


def main() -> None:
    patch_dashboard()
    patch_index()
    patch_app()
    patch_settings_js()
    patch_settings_css()
    patch_sw()
    print('Applied Torrent Dashboard 0.5.1 settings polish and secret masking update')


if __name__ == '__main__':
    main()
