#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8")

def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)

def regex_once(text: str, pattern: str, replacement: str, label: str, flags: int = 0) -> str:
    out, count = re.subn(pattern, replacement, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one regex match, found {count}")
    return out

app_css = read('static/app.css')
app_css = regex_once(
    app_css,
    r'\.material-symbols-outlined\{.*?\.secret-toggle:focus-visible\{[^}]*\}',
    '''/* 0.5.28 locally embedded visibility icons */
.secret-input{position:relative;display:flex;align-items:center;width:100%}.secret-input input{width:100%;padding-right:44px!important}.secret-input.stored-secret input{padding-right:11px!important}.secret-toggle{position:absolute;right:5px;top:50%;transform:translateY(-50%);display:grid;place-items:center;width:32px;min-width:32px;height:32px;padding:0;border:0;border-radius:8px;background:transparent;color:var(--muted);line-height:1;z-index:2}.secret-toggle .material-symbol-icon{display:block;width:19px;height:19px;fill:currentColor}.secret-toggle:hover{color:var(--text);background:var(--panel2)}.secret-toggle:focus-visible{outline:none;box-shadow:0 0 0 2px color-mix(in srgb,var(--accent) 24%,transparent)}.login-card .secret-input{width:100%}.login-card .secret-input input{min-width:0}input::-ms-reveal,input::-ms-clear{display:none}''',
    'local visibility icon CSS',
    re.S,
)
app_css += '''\n\n/* 0.5.28 secure account confirmation */\n.password-confirm-card{width:min(440px,calc(100% - 24px));padding-bottom:0}.password-confirm-card header p{margin:5px 0 0;color:var(--muted);font-size:10px;line-height:1.45}.password-confirm-body{display:grid;gap:8px;padding:18px}.password-confirm-body label{display:grid;gap:6px;margin:0;color:var(--muted);font-size:10px}.password-confirm-body input{width:100%;min-height:42px}.password-confirm-actions{display:flex;justify-content:flex-end;gap:8px;padding:13px 18px 18px;border-top:1px solid var(--border)}.password-confirm-actions button{min-width:104px}\n@media(max-width:560px){#passwordConfirmModal{place-items:end center;padding:0}.password-confirm-card{width:100%;border-radius:18px 18px 0 0;border-bottom:0}.password-confirm-actions{display:grid;grid-template-columns:1fr 1fr;padding:12px 16px calc(16px + env(safe-area-inset-bottom))}.password-confirm-actions button{width:100%;min-width:0}}\n'''
write('static/app.css', app_css)

settings_css = read('static/settings.css')
settings_css = regex_once(
    settings_css,
    r'/\* 0\.5\.27 client settings facelift \*/.*\Z',
    '''/* 0.5.28 advanced per-client qBitTorrent settings */
.client-settings-intro{margin:0 0 14px;line-height:1.5;font-size:10.5px}.server-setting-actions{display:flex;align-items:center;gap:7px;flex-wrap:wrap}.server-setting-actions .client-settings:disabled{opacity:.45;cursor:not-allowed}
.client-settings-card{width:min(690px,calc(100% - 24px));padding-bottom:0;overflow:hidden}.client-settings-card header{align-items:center;padding:19px 20px 17px}.client-settings-card header h2{font-size:18px}.client-settings-card header p{margin:5px 0 0;color:var(--muted);font-size:10px}
.client-settings-tabs{display:flex;gap:4px;padding:9px 20px;border-bottom:1px solid var(--border);background:color-mix(in srgb,var(--panel2) 38%,transparent)}.client-settings-tabs button{border:0;background:transparent;color:var(--muted);padding:8px 11px;font-size:10px}.client-settings-tabs button.active{color:var(--text);background:var(--panel2);box-shadow:inset 0 -2px 0 var(--accent)}
.client-settings-body{display:grid;gap:15px;padding:20px;min-height:330px}.client-settings-pane{display:none;min-width:0}.client-settings-pane.active{display:grid;align-content:start}.client-settings-section-heading{display:grid;gap:4px;margin-bottom:6px}.client-settings-section-heading strong{font-size:13px;color:var(--text)}.client-settings-section-heading span{font-size:9.5px;line-height:1.45;color:var(--muted)}
.client-setting-row{display:flex!important;align-items:center!important;justify-content:space-between;gap:18px;margin:0!important;padding:14px 0!important;color:var(--text)!important}.client-setting-copy{display:grid;gap:4px;min-width:0}.client-setting-copy strong{font-size:11.5px}.client-setting-copy>span{font-size:9.5px;line-height:1.45;color:var(--muted)}
.client-switch{position:relative;display:block;flex:0 0 auto;width:40px;height:23px}.client-switch input{position:absolute!important;width:1px!important;height:1px!important;opacity:0;pointer-events:none}.client-switch>span{display:block;width:40px;height:23px;border:1px solid var(--border);border-radius:999px;background:var(--panel3);transition:background .15s,border-color .15s,box-shadow .15s}.client-switch>span:after{content:"";position:absolute;left:4px;top:4px;width:15px;height:15px;border-radius:50%;background:var(--muted);transition:transform .15s,background .15s}.client-switch input:checked+span{background:color-mix(in srgb,var(--accent) 18%,var(--panel3));border-color:color-mix(in srgb,var(--accent) 55%,var(--border))}.client-switch input:checked+span:after{transform:translateX(17px);background:var(--accent)}.client-switch input:focus-visible+span{box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 13%,transparent)}
.client-settings-divider{height:1px;margin:5px 0;background:color-mix(in srgb,var(--border) 78%,transparent)}.client-limit-grid,.client-field-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:12px}.client-limit-grid.compact-top{margin-top:10px}.client-limit-grid label,.client-field-grid label{display:grid!important;gap:7px!important;margin:0!important;color:var(--text)!important;font-size:10.5px!important}.client-limit-grid label>span:first-child,.client-field-grid label>span:first-child{font-weight:600}.client-limit-input{position:relative;display:block}.client-limit-input input{width:100%;min-height:42px;padding-right:58px!important}.client-limit-input>span{position:absolute;right:12px;top:50%;transform:translateY(-50%);font-size:8.5px;color:var(--muted);pointer-events:none}.client-limit-grid small,.client-field-grid small{font-size:9px;color:var(--muted)}
.client-field-grid input,.client-field-grid select{width:100%;min-height:42px}.client-field-grid.two-col{grid-template-columns:1fr 1fr}.client-toggle-field{display:flex!important;align-items:center!important;justify-content:space-between;gap:12px;padding:0 2px}.connection-limits{margin-top:14px}.proxy-grid{grid-template-columns:140px minmax(0,1fr) 130px}.disabled-fields{opacity:.5}.disabled-fields input{cursor:not-allowed}
.client-settings-status{display:flex;align-items:center;gap:8px;min-height:18px;color:var(--muted);font-size:9.5px;line-height:1.4}.client-settings-status:before{content:"";width:7px;height:7px;flex:0 0 auto;border-radius:50%;background:var(--muted)}.client-settings-status.ok{color:var(--good)}.client-settings-status.ok:before{background:var(--good)}.client-settings-status.bad{color:var(--bad)}.client-settings-status.bad:before{background:var(--bad)}
.client-settings-actions{display:flex;justify-content:flex-end;gap:8px;padding:14px 20px 18px;border-top:1px solid var(--border);background:color-mix(in srgb,var(--panel2) 45%,transparent)}.client-settings-actions button{min-width:96px}.user-name-line{display:flex;align-items:center;gap:7px;min-width:0}.current-user-badge{display:inline-flex;align-items:center;flex:0 0 auto;border:1px solid color-mix(in srgb,var(--accent) 32%,var(--border));border-radius:999px;padding:2px 6px;color:var(--accent);font-size:8px;font-weight:650;line-height:1.25;white-space:nowrap}
@media(max-width:700px){#clientSettingsModal{place-items:end center;padding:0}.client-settings-card{width:100%;max-height:min(91vh,780px);border-radius:18px 18px 0 0;border-bottom:0}.client-settings-tabs{padding:8px 14px;overflow:auto}.client-settings-body{padding:17px;min-height:0}.client-settings-actions{padding:13px 17px calc(18px + env(safe-area-inset-bottom))}.proxy-grid{grid-template-columns:1fr 120px}.proxy-grid label:nth-child(2){grid-column:1/-1;grid-row:2}.client-field-grid.two-col,.client-limit-grid{grid-template-columns:1fr 1fr}}
@media(max-width:500px){.client-field-grid.two-col,.client-limit-grid,.proxy-grid{grid-template-columns:1fr}.proxy-grid label:nth-child(2){grid-column:auto;grid-row:auto}.client-settings-actions{display:grid;grid-template-columns:1fr 1fr}.client-settings-actions button{width:100%;min-width:0}.client-settings-intro{font-size:9.5px}.current-user-badge{font-size:7.5px}}\n''',
    'advanced client settings CSS',
    re.S,
)
write('static/settings.css', settings_css)
