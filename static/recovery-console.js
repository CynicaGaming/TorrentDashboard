"use strict";
const RECOVERY_BUILD="0.5.140";
const $=selector=>document.querySelector(selector);
let csrf="";
let sessionKind="";
let commandHistory=[];
let historyIndex=0;

function appendLine(text,tone="muted"){
  const output=$("#consoleOutput");if(!output)return;
  const line=document.createElement("div");line.className=`console-line ${tone}`;line.textContent=String(text??"");output.appendChild(line);output.scrollTop=output.scrollHeight;
}
function setLocked(locked,label="Locked"){
  $("#consoleUnlock").classList.toggle("hidden",!locked);$("#consoleTerminal").classList.toggle("hidden",locked);
  const badge=$("#consoleLockStatus");badge.textContent=label;badge.classList.toggle("locked",locked);badge.classList.toggle("unlocked",!locked);
  if(locked){csrf="";sessionKind="";}else setTimeout(()=>$("#consoleCommand")?.focus(),0);
}

function setPasswordVisibility(show){
  const input=$("#consolePassword"),button=$("#consolePasswordToggle");if(!input||!button)return;
  input.type=show?"text":"password";button.dataset.visible=show?"1":"0";button.setAttribute("aria-label",show?"Hide password":"Show password");button.title=show?"Hide password":"Show password";
  button.innerHTML=show?'<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M2.27 3.27 1 4.54l3.13 3.13A11.8 11.8 0 0 0 1 12c1.73 4.39 6 7.5 11 7.5 1.55 0 3.03-.3 4.38-.84l3.08 3.07L20.73 20 3.54 2.73 2.27 3.27ZM12 17a5 5 0 0 1-5-5c0-.65.13-1.27.35-1.83l1.55 1.55A3.17 3.17 0 0 0 12 15.17c.1 0 .19 0 .28-.02l1.55 1.55A4.9 4.9 0 0 1 12 17Zm9.73-5c-.77 1.94-1.94 3.57-3.39 4.82l-2.12-2.12A5 5 0 0 0 9.3 7.78L7.66 6.14A11.4 11.4 0 0 1 12 5c5 0 9.27 3.11 11 7-.34.86-.77 1.67-1.27 2.4L19.9 12.57c.04-.19.1-.37.1-.57 0-2.76-2.24-5-5-5-.2 0-.38.06-.57.1l-1.66-1.66A7 7 0 0 1 19 12c0 .42-.05.83-.12 1.22L21.73 16.07A11.3 11.3 0 0 0 23 12h-1.27Z"/></svg>':'<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5C21.27 7.61 17 4.5 12 4.5Zm0 12A4.5 4.5 0 1 1 12 7.5a4.5 4.5 0 0 1 0 9Zm0-7.2a2.7 2.7 0 1 0 0 5.4 2.7 2.7 0 0 0 0-5.4Z"/></svg>';
}

async function request(url,options={}){
  options.headers={...(options.headers||{})};
  if(options.method&&options.method!=="GET"&&options.method!=="HEAD"&&csrf)options.headers["X-CSRF-Token"]=csrf;
  const response=await fetch(url,{cache:"no-store",...options});const type=response.headers.get("content-type")||"";const data=type.includes("json")?await response.json():await response.text();
  if(!response.ok)throw new Error(data?.error||data||`HTTP ${response.status}`);return data;
}
async function detectSession(){
  try{const data=await request("/api/recovery/session");if(!data.authenticated)return;applyRecoverySession(data);}catch{}
}
function applyRecoverySession(data){csrf=data.csrf||"";sessionKind=data.kind||"recovery";$("#consolePassword").value="";$("#consoleRecoveryKey").value="";$("#consoleRecoveryCode").value="";const who=data.display_name||data.username||"Recovery user",role=data.group_label||data.group||"Standard user";$("#consoleSessionLabel").textContent=`${who} · ${role}`;setLocked(false,"Unlocked");appendLine(`Torrent Dashboard Recovery Console v${data.version||RECOVERY_BUILD}`,"good");appendLine(`Authorized as ${who} · ${role}. Type help to list commands available to your role.`,"muted");}
async function unlockConsole(event){event?.preventDefault();return unlockConsoleWith("key");}
async function unlockConsoleWith(method){
  const error=$("#consoleUnlockError");error.textContent="";const username=$("#consoleUser").value.trim();
  const payload={};
  if(method==="key"){if(!username)return error.textContent="Enter your username";payload.username=username;payload.recovery_key=$("#consoleRecoveryKey").value.trim();if(!payload.recovery_key)return error.textContent="Enter your recovery key";}
  else if(method==="password"){if(!username)return error.textContent="Enter the administrator username";payload.username=username;payload.password=$("#consolePassword").value;if(!payload.password)return error.textContent="Enter the administrator password";}
  else{payload.recovery_code=$("#consoleRecoveryCode").value.trim();if(!payload.recovery_code)return error.textContent="Enter the startup recovery code";}
  try{const data=await request("/api/recovery/unlock",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});applyRecoverySession(data);}catch(err){error.textContent=err.message||"Could not unlock recovery console";}
}
async function clearFrontendCache(){
  appendLine("td> frontend clear-cache","command");
  try{if("serviceWorker" in navigator){const registrations=await navigator.serviceWorker.getRegistrations();await Promise.all(registrations.map(reg=>reg.unregister()));}if("caches" in window){const keys=await caches.keys();await Promise.all(keys.filter(key=>key.startsWith("torrent-dashboard-")).map(key=>caches.delete(key)));}appendLine("Frontend service workers and Torrent Dashboard caches cleared.","good");}catch(err){appendLine(err.message||String(err),"bad");}
}
async function runCommand(raw){
  const command=String(raw||"").trim();if(!command)return;
  commandHistory.push(command);if(commandHistory.length>100)commandHistory=commandHistory.slice(-100);historyIndex=commandHistory.length;
  if(command==="clear"){$("#consoleOutput").textContent="";return;}
  if(command==="reload"){appendLine("td> reload","command");location.reload();return;}
  if(command==="frontend clear-cache"){await clearFrontendCache();return;}
  appendLine(`td> ${command}`,"command");
  try{const data=await request("/api/recovery/command",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({command})});if(data.output)appendLine(data.output,data.state==="installing"?"good":"muted");if(data.state==="installing")appendLine("The dashboard may disconnect while the verified update is installed.","good");}catch(err){appendLine(err.message||String(err),"bad");if(/authentication|session/i.test(err.message||""))setLocked(true,"Locked");}
}
async function lockConsole(){
  try{await request("/api/recovery/logout",{method:"POST",headers:{"Content-Type":"application/json"},body:"{}"});}catch{}setLocked(true,"Locked");$("#consoleOutput").textContent="";$("#consoleUnlockError").textContent="";
}

$("#consoleUnlockForm").addEventListener("submit",unlockConsole);
$("#consolePasswordToggle").addEventListener("click",()=>setPasswordVisibility($("#consolePassword").type==="password"));
$("#consolePasswordUnlock").addEventListener("click",()=>unlockConsoleWith("password"));
$("#consoleStartupUnlock").addEventListener("click",()=>unlockConsoleWith("startup"));
$("#consoleCommandForm").addEventListener("submit",event=>{event.preventDefault();const input=$("#consoleCommand"),command=input.value;input.value="";runCommand(command);});
$("#consoleHelp").addEventListener("click",()=>runCommand("help"));
$("#consoleClear").addEventListener("click",()=>{$("#consoleOutput").textContent="";$("#consoleCommand").focus();});
$("#consoleLock").addEventListener("click",lockConsole);
$("#consoleCommand").addEventListener("keydown",event=>{if(event.key==="ArrowUp"){event.preventDefault();if(commandHistory.length){historyIndex=Math.max(0,historyIndex-1);event.currentTarget.value=commandHistory[historyIndex]||"";}}else if(event.key==="ArrowDown"){event.preventDefault();historyIndex=Math.min(commandHistory.length,historyIndex+1);event.currentTarget.value=historyIndex<commandHistory.length?commandHistory[historyIndex]:"";}else if(event.key.toLowerCase()==="l"&&event.ctrlKey){event.preventDefault();$("#consoleOutput").textContent="";}});
setPasswordVisibility(false);setLocked(true,"Locked");detectSession();
