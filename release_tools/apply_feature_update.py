#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def replace_once(text, old, new, label):
    if old not in text:
        raise RuntimeError(f"Could not find {label}")
    return text.replace(old, new, 1)


def sub_once(text, pattern, repl, label, flags=0):
    out, count = re.subn(pattern, repl, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"Expected one {label}, replaced {count}")
    return out


def patch_versions():
    path = ROOT / "dashboard.py"
    text = path.read_text(encoding="utf-8")
    text = replace_once(text, 'VERSION = "0.5.1"', 'VERSION = "0.5.2"', 'dashboard version')
    path.write_text(text, encoding="utf-8")

    path = ROOT / "static" / "index.html"
    text = path.read_text(encoding="utf-8").replace('?v=0.5.1', '?v=0.5.2')
    path.write_text(text, encoding="utf-8")

    path = ROOT / "static" / "sw.js"
    text = path.read_text(encoding="utf-8")
    text = text.replace('0.5.1', '0.5.2').replace('torrent-dashboard-v051', 'torrent-dashboard-v052')
    path.write_text(text, encoding="utf-8")


def patch_app_js():
    path = ROOT / "static" / "app.js"
    text = path.read_text(encoding="utf-8")

    secret_block = r'''const CONFIGURED_SECRET_MASK='••••••••••';
function setConfiguredSecretField(input,configured,emptyPlaceholder=''){
  if(!input)return;
  input.placeholder=emptyPlaceholder;
  input.value=configured?CONFIGURED_SECRET_MASK:'';
  input.classList.toggle('secret-configured',!!configured);
  if(configured)input.dataset.configuredSecret='1';else delete input.dataset.configuredSecret;
  input.setCustomValidity('');
  syncSecretToggle(input);
}
function secretFieldValue(input,preserve='<configured>'){
  if(!input)return'';
  const value=input.value.trim();
  if(input.dataset.configuredSecret==='1'){
    if(value===CONFIGURED_SECRET_MASK||value==='')return preserve;
    if(value.includes('•'))throw new Error('Delete The Existing Mask Before Entering A New Secret');
  }
  return value;
}
function syncSecretToggle(input){
  const btn=input?.parentElement?.querySelector('.secret-toggle');
  if(!btn)return;
  const value=input.value||'';
  const stored=input.dataset.configuredSecret==='1'&&(value===CONFIGURED_SECRET_MASK||value===''||value.includes('•'));
  if(stored){
    input.type='password';
    btn.disabled=true;
    btn.textContent='Stored';
    btn.setAttribute('aria-label','Stored Secret Cannot Be Revealed');
    btn.title='Stored secrets are not sent back to the browser. Delete the mask and enter a new value to replace it.';
    return;
  }
  btn.disabled=false;
  btn.removeAttribute('title');
  const showing=input.type==='text';
  btn.textContent=showing?'Hide':'Show';
  btn.setAttribute('aria-label',showing?'Hide Secret':'Show Secret');
}
function decorateSecretFields(root=document){
  const fields=[];
  if(root.matches?.('input[type="password"]:not(.autofill-decoy):not([aria-hidden="true"])'))fields.push(root);
  fields.push(...(root.querySelectorAll?.('input[type="password"]:not(.autofill-decoy):not([aria-hidden="true"])')||[]));
  fields.forEach(input=>{
    if(input.dataset.secretReady==='1'){syncSecretToggle(input);return;}
    input.dataset.secretReady='1';
    const wrap=document.createElement('div');wrap.className='secret-input';
    input.parentNode.insertBefore(wrap,input);wrap.appendChild(input);
    const btn=document.createElement('button');btn.type='button';btn.className='secret-toggle';btn.textContent='Show';btn.setAttribute('aria-label','Show Secret');
    btn.addEventListener('click',()=>{if(btn.disabled)return;const showing=input.type==='text';input.type=showing?'password':'text';syncSecretToggle(input)});
    input.addEventListener('input',()=>{
      if(input.dataset.configuredSecret==='1'){
        const value=input.value||'';
        if(value===CONFIGURED_SECRET_MASK||value==='')input.setCustomValidity('');
        else if(value.includes('•'))input.setCustomValidity('Delete the existing mask before entering a new secret.');
        else{delete input.dataset.configuredSecret;input.classList.remove('secret-configured');input.setCustomValidity('')}
      }
      syncSecretToggle(input);
    });
    wrap.appendChild(btn);
    syncSecretToggle(input);
  });
}
const titleObserver='''
    text = sub_once(
        text,
        r'function decorateSecretFields\(root=document\)\{.*?\n\}\nconst titleObserver=',
        secret_block,
        'secret field helpers',
        re.S,
    )

    text = replace_once(
        text,
        "github_token:$('#sUpdateToken').value.trim()",
        "github_token:secretFieldValue($('#sUpdateToken'),'')",
        'GitHub test token value',
    )
    text = replace_once(
        text,
        "function serverRowData(r){let o={enabled:true};r.querySelectorAll('[data-k]').forEach(i=>o[i.dataset.k]=i.value);return o}",
        "function serverRowData(r){let o={enabled:true};r.querySelectorAll('[data-k]').forEach(i=>o[i.dataset.k]=i.type==='password'?secretFieldValue(i,'<configured>'):i.value);return o}",
        'server row secret preservation',
    )
    path.write_text(text, encoding="utf-8")


def patch_settings_js():
    path = ROOT / "static" / "settings.js"
    text = path.read_text(encoding="utf-8")
    text = replace_once(text, "const SECRET_MASK = '••••••••••';", "const SECRET_MASK = CONFIGURED_SECRET_MASK;", 'settings secret mask constant')

    text = sub_once(
        text,
        r"  function configuredSecret\(input, configured, emptyPlaceholder=''\) \{.*?\n  \}",
        "  function configuredSecret(input, configured, emptyPlaceholder='') {\n    setConfiguredSecretField(input, configured, emptyPlaceholder);\n  }",
        'configured secret helper',
        re.S,
    )

    text = replace_once(
        text,
        "github_token: document.querySelector('#sUpdateToken')?.value.trim() || '<configured>',",
        "github_token: secretFieldValue(document.querySelector('#sUpdateToken'), '<configured>'),",
        'GitHub token save behavior',
    )

    old_field = '''  function fieldHtml(field, value, configured) {
    const secret = !!field.secret;
    const type = secret ? 'password' : (field.input_type || 'text');
    const placeholder = secret && configured ? SECRET_MASK : (field.placeholder || '');
    const secretClass = secret && configured ? ' class="secret-configured" data-configured-secret="1"' : '';
    return `<label>${esc(field.label)}<input data-field="${esc(field.key)}" ${secret?'data-secret="1"':''}${secretClass} type="${esc(type)}" autocomplete="off" value="${secret?'':esc(value||'')}" placeholder="${esc(placeholder)}"></label>`;
  }'''
    new_field = '''  function fieldHtml(field, value, configured) {
    const secret = !!field.secret;
    const type = secret ? 'password' : (field.input_type || 'text');
    const secretClass = secret && configured ? ' class="secret-configured" data-configured-secret="1"' : '';
    const displayValue = secret ? (configured ? SECRET_MASK : '') : (value || '');
    return `<label>${esc(field.label)}<input data-field="${esc(field.key)}" ${secret?'data-secret="1"':''}${secretClass} type="${esc(type)}" autocomplete="off" value="${esc(displayValue)}" placeholder="${esc(field.placeholder||'')}"></label>`;
  }'''
    text = replace_once(text, old_field, new_field, 'integration secret field rendering')

    text = replace_once(
        text,
        "data[input.dataset.field] = input.type === 'checkbox' ? input.checked : input.value.trim();",
        "data[input.dataset.field] = input.type === 'checkbox' ? input.checked : (input.dataset.secret==='1' ? secretFieldValue(input,'<configured>') : input.value.trim());",
        'integration secret payload',
    )

    text = text.replace(
        "${user._new?'placeholder=\"Create Password\"':'class=\"secret-configured\" data-configured-secret=\"1\" placeholder=\"'+SECRET_MASK+'\"'}",
        "${user._new?'placeholder=\"Create Password\"':'class=\"secret-configured\" data-configured-secret=\"1\" value=\"'+SECRET_MASK+'\"'}",
    )
    text = text.replace(
        "${user._new?'placeholder=\"Confirm Password\"':'class=\"secret-configured\" data-configured-secret=\"1\" placeholder=\"'+SECRET_MASK+'\"'}",
        "${user._new?'placeholder=\"Confirm Password\"':'class=\"secret-configured\" data-configured-secret=\"1\" value=\"'+SECRET_MASK+'\"'}",
    )

    text = replace_once(
        text,
        "card.querySelectorAll('[data-user-field]').forEach(input=>data[input.dataset.userField]=input.value.trim());",
        "card.querySelectorAll('[data-user-field]').forEach(input=>data[input.dataset.userField]=input.type==='password'?secretFieldValue(input,''):input.value.trim());",
        'user password payload',
    )
    path.write_text(text, encoding="utf-8")


def patch_settings_css():
    path = ROOT / "static" / "settings.css"
    text = path.read_text(encoding="utf-8")
    addition = "\n.secret-input .secret-toggle:disabled{cursor:default;opacity:.62;color:var(--muted);background:var(--panel2);border-color:var(--border)}.secret-configured{letter-spacing:.08em}\n"
    if '.secret-toggle:disabled' not in text:
        text += addition
    path.write_text(text, encoding="utf-8")


def main():
    patch_versions()
    patch_app_js()
    patch_settings_js()
    patch_settings_css()
    print('Applied Torrent Dashboard 0.5.2 persistent configured-secret mask update')


if __name__ == '__main__':
    main()
