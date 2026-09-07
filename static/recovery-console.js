"use strict";
const RECOVERY_BUILD="0.5.138";
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
async function request(url,options={}){
  options.headers={...(options.headers||{})};
  if(options.method&&options.method!=="GET"&&options.method!=="HEAD"&&csrf)options.headers["X-CSRF-Token"]=csrf;
  const response=await fetch(url,{cache:"no-store",...options});const type=response.headers.get("content-type")||"";const data=type.includes("json")?await response.json():await response.text();
  if(!response.ok)throw new Error(data?.error||data||`HTTP ${response.status}`);return data;
}
async function detectSession(){
  try{const data=await request("/api/recovery/session");if(!data.authenticated)return;csrf=data.csrf||"";sessionKind=data.kind||"administrator";$("#consoleSessionLabel").textContent=`Authorized via ${sessionKind}`;setLocked(false,"Unlocked");appendLine(`Torrent Dashboard Recovery Console v${data.version||RECOVERY_BUILD}`,"good");appendLine("No command has been run. Type help to list available commands.","muted");}catch{}
}
async function unlockConsole(event){
  event.preventDefault();const error=$("#consoleUnlockError");error.textContent="";
  const payload={username:$("#consoleUser").value.trim(),password:$("#consolePassword").value,recovery_code:$("#consoleRecoveryCode").value.trim()};
  try{const data=await request("/api/recovery/unlock",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});csrf=data.csrf||"";sessionKind=data.kind||"recovery";$("#consolePassword").value="";$("#consoleRecoveryCode").value="";$("#consoleSessionLabel").textContent=`Authorized via ${sessionKind}`;setLocked(false,"Unlocked");appendLine(`Torrent Dashboard Recovery Console v${data.version||RECOVERY_BUILD}`,"good");appendLine("No command has been run. Type help to list available commands.","muted");}catch(err){error.textContent=err.message||"Could not unlock recovery console";}
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
$("#consoleCommandForm").addEventListener("submit",event=>{event.preventDefault();const input=$("#consoleCommand"),command=input.value;input.value="";runCommand(command);});
$("#consoleHelp").addEventListener("click",()=>runCommand("help"));
$("#consoleClear").addEventListener("click",()=>{$("#consoleOutput").textContent="";$("#consoleCommand").focus();});
$("#consoleLock").addEventListener("click",lockConsole);
$("#consoleCommand").addEventListener("keydown",event=>{if(event.key==="ArrowUp"){event.preventDefault();if(commandHistory.length){historyIndex=Math.max(0,historyIndex-1);event.currentTarget.value=commandHistory[historyIndex]||"";}}else if(event.key==="ArrowDown"){event.preventDefault();historyIndex=Math.min(commandHistory.length,historyIndex+1);event.currentTarget.value=historyIndex<commandHistory.length?commandHistory[historyIndex]:"";}else if(event.key.toLowerCase()==="l"&&event.ctrlKey){event.preventDefault();$("#consoleOutput").textContent="";}});
setLocked(true,"Locked");detectSession();
