#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch(path, replacements):
    file = ROOT / path
    text = file.read_text(encoding='utf-8')
    for old, new, label in replacements:
        count = text.count(old)
        if count != 1:
            raise RuntimeError(f'{path}: {label}: expected one match, found {count}')
        text = text.replace(old, new, 1)
    file.write_text(text, encoding='utf-8')


patch('static/app.js', [
    ('''function formFingerprint(root){
  if(!root)return'';
  return JSON.stringify([...root.querySelectorAll('input,select,textarea')].filter(el=>!['button','submit','reset'].includes(el.type)).map((el,index)=>{
    const key=el.id||el.name||el.dataset.field||el.dataset.k||el.dataset.userField||`${el.tagName}:${index}`;
    let value;
    if(el.type==='checkbox'||el.type==='radio')value=!!el.checked;
    else if(el.type==='file'){const file=el.files?.[0];value=file?`${file.name}:${file.size}:${file.lastModified}`:'';}
    else value=el.value;
    return[key,el.type||el.tagName,value];
  }));
}''', '''function formFingerprint(root){
  if(!root)return'';
  const fields=[...root.querySelectorAll('input,select,textarea')].filter(el=>!['button','submit','reset'].includes(el.type)).map((el,index)=>{
    const key=el.id||el.name||el.dataset.field||el.dataset.k||el.dataset.userField||el.dataset.interfaceId||`${el.tagName}:${index}`;
    if(el.type==='checkbox'&&el.dataset.interfaceId&&!el.checked)return null;
    let value;
    if(el.type==='checkbox'||el.type==='radio')value=!!el.checked;
    else if(el.type==='file'){const file=el.files?.[0];value=file?`${file.name}:${file.size}:${file.lastModified}`:'';}
    else value=el.value;
    return[key,value];
  }).filter(Boolean).sort((a,b)=>String(a[0]).localeCompare(String(b[0])));
  return JSON.stringify(fields);
}''', 'stable form fingerprint'),
])

patch('static/settings.js', [
    ('''    const activePage = document.querySelector('.settings-page.active')?.dataset.settingsSection || 'general';
    if (activePage === 'updates') return saveUpdateSource();
    const servers = [...document.querySelectorAll('.server-setting')].map(serverRowData);''', '''    const repository = updateSourceRepository();
    const savedRepository = String(state.settings?.updates?.repository || '');
    const servers = [...document.querySelectorAll('.server-setting')].map(serverRowData);''', 'remove Updates-only save shortcut'),
    ('''    try {
      await uploadNotificationSoundIfNeeded();
      const d = await post('/api/settings', payload);''', '''    try {
      if (repository !== savedRepository) {
        const source = await saveUpdateSource();
        if (!source) { syncDirtyScope('settingsCore'); return; }
      }
      await uploadNotificationSoundIfNeeded();
      const d = await post('/api/settings', payload);''', 'save update source without losing other core settings'),
    ('''      renderUpdateInfo({configured:true,repository:d.repository || repository,currentVersion:state.me?.version,state:d.settings?.runtime?.updateState||{}});
      resetDirtyScope('settingsCore',true);
      return d;''', '''      renderUpdateInfo({configured:true,repository:d.repository || repository,currentVersion:state.me?.version,state:d.settings?.runtime?.updateState||{}});
      return d;''', 'do not clear global dirty state after update-source-only save'),
    ('''  function addIntegration() {const select = document.querySelector('#integrationTypeSelect'),type = catalog.find(x => x.type === select?.value);if (!type) return toast('Choose an integration type.','error');integrations.unshift({id:'',type:type.type,name:type.label,enabled:true,_new:true,configured_secrets:[]});renderIntegrations();if (select) select.value='';}''', '''  function addIntegration() {const select = document.querySelector('#integrationTypeSelect'),type = catalog.find(x => x.type === select?.value);if (!type) return toast('Choose an integration type.','error');if(dirtyScopeNames(name=>name.startsWith('integration:')).length)return toast('Save or remove current integration changes before adding another.','error');integrations.unshift({id:'',type:type.type,name:type.label,enabled:true,_new:true,configured_secrets:[]});renderIntegrations();if (select) select.value='';}''', 'protect dirty integration cards while adding'),
    ('''  function addUser() {users.unshift({id:'',username:'',first_name:'',last_name:'',email:'',group:'standard',_new:true});renderUsers();}''', '''  function addUser() {if(dirtyScopeNames(name=>name.startsWith('user:')).length)return toast('Save or remove current user changes before adding another.','error');users.unshift({id:'',username:'',first_name:'',last_name:'',email:'',group:'standard',_new:true});renderUsers();}''', 'protect dirty user cards while adding'),
])

patch('release_tools/validate_ui_strings.py', [
    ('''    assert '<div class="settings-savebar" id="settingsSavebar"><button class="primary" type="submit">Save</button></div>' in html''', '''    assert 'id="settingsSaveState"' in html and 'id="settingsSaveButton"' in html and 'id="settingsSaveButton" type="submit" disabled' in html''', 'updated settings savebar contract'),
    ('''    assert "if (activePage === 'updates') return saveUpdateSource();" in settings_js''', '''    assert "if (activePage === 'updates') return saveUpdateSource();" not in settings_js
    assert 'const savedRepository = String(state.settings?.updates?.repository || \'\');' in settings_js
    assert 'const source = await saveUpdateSource();' in settings_js''', 'unified settings save contract'),
    ('''    assert 'role="status" aria-live="polite"' in html
''', '''    assert 'role="status" aria-live="polite"' in html
    assert "return[key,el.type||el.tagName,value]" not in app_js
    assert "el.dataset.interfaceId&&!el.checked" in app_js
    assert 'Save or remove current integration changes before adding another.' in settings_js
    assert 'Save or remove current user changes before adding another.' in settings_js
    assert "resetDirtyScope('settingsCore',true);\n      return d;" not in settings_js.split('async function saveUpdateSource()',1)[1].split('async function loadExtras()',1)[0]
''', 'dirty-state regression checks'),
])

print('Hardened v0.5.34 dirty-state behavior and packaging validation.')
