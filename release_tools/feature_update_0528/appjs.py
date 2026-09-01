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

app_js = read('static/app.js')
old_icon = 'function setSecretToggleIcon(btn,name){btn.innerHTML=`<span class="material-symbols-outlined" aria-hidden="true">${name}</span>`;btn.dataset.materialSymbol=name}'
new_icon = '''function secretToggleSvg(name){
  if(name==='visibility_lock')return '<svg class="material-symbol-icon" aria-hidden="true" viewBox="0 0 24 24"><path d="M11 4.5C6.4 4.5 2.5 7.35 1 11.5c1.5 4.15 5.4 7 10 7 1.05 0 2.06-.15 3-.44V15.8a4.5 4.5 0 1 1 1.36-6.92A5.2 5.2 0 0 1 17 9.1V8.8C15.38 6.17 13.27 4.5 11 4.5Zm0 3A4 4 0 1 0 11 15.5 4 4 0 0 0 11 7.5Zm0 2A2 2 0 1 1 11 13.5 2 2 0 0 1 11 9.5Z"/><path d="M20.5 14h-.5v-1.25a2.5 2.5 0 0 0-5 0V14h-.5a1 1 0 0 0-1 1v4a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1v-4a1 1 0 0 0-1-1Zm-4-1.25a1 1 0 0 1 2 0V14h-2v-1.25Z"/></svg>';
  return '<svg class="material-symbol-icon" aria-hidden="true" viewBox="0 0 24 24"><path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5C21.27 7.61 17 4.5 12 4.5Zm0 12A4.5 4.5 0 1 1 12 7.5a4.5 4.5 0 0 1 0 9Zm0-7.2a2.7 2.7 0 1 0 0 5.4 2.7 2.7 0 0 0 0-5.4Z"/></svg>';
}
function setSecretToggleIcon(btn,name){btn.innerHTML=secretToggleSvg(name);btn.dataset.materialSymbol=name}'''
app_js = replace_once(app_js, old_icon, new_icon, 'local visibility SVG implementation')
app_js = replace_once(
    app_js,
    "  $('#accountSettingsBtn').addEventListener('click',()=>{hideAccountMenu();openAccountModal('profile')});$('#accountPasswordBtn').addEventListener('click',()=>{hideAccountMenu();openAccountModal('password')});$('#accountAvatarBtn').addEventListener('click',()=>{hideAccountMenu();openAccountModal('avatar')});$('#logoutBtn').addEventListener('click',()=>{hideAccountMenu();signOut()});$$('[data-account-close]').forEach(x=>x.addEventListener('click',closeAccountModal));$('#accountProfileForm').addEventListener('submit',saveOwnProfile);$('#accountPasswordForm').addEventListener('submit',changeOwnPassword);$('#accountChooseAvatar').addEventListener('click',()=>$('#accountAvatarInput').click());$('#accountAvatarInput').addEventListener('change',uploadOwnAvatar);$('#accountRemoveAvatar').addEventListener('click',removeOwnAvatar);",
    "  $('#accountSettingsBtn').addEventListener('click',()=>{hideAccountMenu();openAccountModal('profile')});$('#accountPasswordBtn').addEventListener('click',()=>{hideAccountMenu();openAccountModal('password')});$('#logoutBtn').addEventListener('click',()=>{hideAccountMenu();signOut()});$$('[data-account-close]').forEach(x=>x.addEventListener('click',closeAccountModal));$('#accountProfileForm').addEventListener('submit',saveOwnProfile);$('#accountPasswordForm').addEventListener('submit',changeOwnPassword);$('#accountChooseAvatar').addEventListener('click',()=>$('#accountAvatarInput').click());$('#accountAvatarInput').addEventListener('change',uploadOwnAvatar);$('#accountRemoveAvatar').addEventListener('click',removeOwnAvatar);bindPasswordConfirmation();",
    'account menu bindings',
)
app_js = replace_once(
    app_js,
    "if(e.key==='Escape'){if(!$('#clientSettingsModal')?.classList.contains('hidden')){TDSettings.closeClientSettings();return}if(!$('#accountModal')?.classList.contains('hidden')){closeAccountModal();return}",
    "if(e.key==='Escape'){if(!$('#passwordConfirmModal')?.classList.contains('hidden')){closePasswordConfirmation(null);return}if(!$('#clientSettingsModal')?.classList.contains('hidden')){TDSettings.closeClientSettings();return}if(!$('#accountModal')?.classList.contains('hidden')){closeAccountModal();return}",
    'escape closes secure confirmation first',
)
app_js = replace_once(
    app_js,
    "  for(const id of ['accountSettingsBtn','accountPasswordBtn','accountAvatarBtn']){const el=$('#'+id);if(el)el.disabled=!editable}",
    "  for(const id of ['accountSettingsBtn','accountPasswordBtn']){const el=$('#'+id);if(el)el.disabled=!editable}",
    'account menu editable controls',
)

old_account_block = '''async function loadAccount(){
  const d=await api('/api/account');
  applyAccountUser(d.user);
  $('#accountUsername').value=d.user?.username||'';
  $('#accountFirstName').value=d.user?.first_name||'';
  $('#accountLastName').value=d.user?.last_name||'';
  $('#accountEmail').value=d.user?.email||'';
  $('#accountGroup').value=d.user?.group_label||uiText(d.user?.group||'standardUser');
  $('#accountProfilePassword').value='';
  return d.user;
}
async function openAccountModal(target='profile'){
  if(!state.me?.user_id)return toast('This session is not linked to a user account','error');
  $('#accountModal').classList.remove('hidden');
  const status=$('#accountStatus');status.className='test-result muted';status.textContent='Loading account…';
  try{
    await loadAccount();status.textContent='';
    const focusId=target==='password'?'accountCurrentPassword':target==='avatar'?'accountChooseAvatar':'accountFirstName';
    setTimeout(()=>$('#'+focusId)?.focus(),0);
  }catch(e){status.className='test-result bad';status.textContent=e.message}
}
function closeAccountModal(){$('#accountModal').classList.add('hidden');$('#accountProfileForm')?.reset();$('#accountPasswordForm')?.reset();$('#accountStatus').textContent=''}
async function saveOwnProfile(e){
  e.preventDefault();
  const status=$('#accountStatus');status.className='test-result muted';status.textContent='Saving profile…';
  try{
    const d=await post('/api/account',{username:$('#accountUsername').value.trim(),first_name:$('#accountFirstName').value.trim(),last_name:$('#accountLastName').value.trim(),email:$('#accountEmail').value.trim(),current_password:$('#accountProfilePassword').value});
    applyAccountUser(d.user);$('#accountProfilePassword').value='';status.className='test-result ok';status.textContent='Profile saved.';toast('profileSaved');
  }catch(e){status.className='test-result bad';status.textContent=e.message}
}
'''
new_account_block = '''let accountProfileSnapshot=null,passwordConfirmationResolve=null,passwordConfirmationBound=false;
function closePasswordConfirmation(result=null){const modal=$('#passwordConfirmModal');modal?.classList.add('hidden');const input=$('#passwordConfirmInput');if(input){input.value='';input.type='password';syncSecretToggle(input)}const status=$('#passwordConfirmStatus');if(status)status.textContent='';const resolve=passwordConfirmationResolve;passwordConfirmationResolve=null;if(resolve)resolve(result)}
function bindPasswordConfirmation(){if(passwordConfirmationBound)return;passwordConfirmationBound=true;$('#passwordConfirmForm')?.addEventListener('submit',e=>{e.preventDefault();const input=$('#passwordConfirmInput');if(!input?.reportValidity())return;closePasswordConfirmation(input.value)});$$('[data-password-confirm-cancel]').forEach(x=>x.addEventListener('click',()=>closePasswordConfirmation(null)))}
function requestPasswordConfirmation(message){bindPasswordConfirmation();if(passwordConfirmationResolve)closePasswordConfirmation(null);const modal=$('#passwordConfirmModal'),input=$('#passwordConfirmInput'),copy=$('#passwordConfirmMessage');if(copy)copy.textContent=message||'Enter your current password to continue with this secure account change.';if(input){input.value='';input.type='password';syncSecretToggle(input)}modal?.classList.remove('hidden');return new Promise(resolve=>{passwordConfirmationResolve=resolve;setTimeout(()=>input?.focus(),0)})}
async function loadAccount(){
  const d=await api('/api/account');
  applyAccountUser(d.user);accountProfileSnapshot={...d.user};
  $('#accountUsername').value=d.user?.username||'';
  $('#accountFirstName').value=d.user?.first_name||'';
  $('#accountLastName').value=d.user?.last_name||'';
  $('#accountEmail').value=d.user?.email||'';
  $('#accountGroup').value=d.user?.group_label||uiText(d.user?.group||'standardUser');
  const current=$('#accountCurrentPassword');if(current)current.required=!!d.user?.password_configured;
  return d.user;
}
async function openAccountModal(target='profile'){
  if(!state.me?.user_id)return toast('This session is not linked to a user account','error');
  $('#accountModal').classList.remove('hidden');
  const status=$('#accountStatus');status.className='test-result muted';status.textContent='Loading account…';
  try{
    await loadAccount();status.textContent='';
    const focusId=target==='password'?'accountCurrentPassword':'accountFirstName';
    setTimeout(()=>$('#'+focusId)?.focus(),0);
  }catch(e){status.className='test-result bad';status.textContent=e.message}
}
function closeAccountModal(){$('#accountModal').classList.add('hidden');$('#accountProfileForm')?.reset();$('#accountPasswordForm')?.reset();$('#accountStatus').textContent='';accountProfileSnapshot=null}
async function saveOwnProfile(e){
  e.preventDefault();
  const status=$('#accountStatus');
  const payload={username:$('#accountUsername').value.trim(),first_name:$('#accountFirstName').value.trim(),last_name:$('#accountLastName').value.trim(),email:$('#accountEmail').value.trim()};
  const secureChange=!!accountProfileSnapshot&&(payload.username!==String(accountProfileSnapshot.username||'')||payload.email!==String(accountProfileSnapshot.email||''));
  try{
    if(secureChange&&accountProfileSnapshot?.password_configured){
      const password=await requestPasswordConfirmation('Confirm your current password to change your username or email address.');
      if(password===null)return;
      payload.current_password=password;
    }
    status.className='test-result muted';status.textContent='Saving profile…';
    const d=await post('/api/account',payload);
    applyAccountUser(d.user);accountProfileSnapshot={...d.user};status.className='test-result ok';status.textContent='Profile saved.';toast('profileSaved');
  }catch(e){status.className='test-result bad';status.textContent=e.message}
}
'''
app_js = replace_once(app_js, old_account_block, new_account_block, 'secure account profile workflow')
write('static/app.js', app_js)
