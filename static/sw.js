'use strict';

const CACHE='torrent-dashboard-v0554-stabilization1';
const FEATURE_STYLE='/static/integration-notifications.css?v=0.5.54';
const FEATURE_SCRIPT='/static/integration-notifications.js?v=0.5.54';
const SOUND_PATCH='/static/default-notification-sound.js?v=0.5.54';
const SOUND_PATH='/static/notification-default.mp3';
const SOUND_PARTS=[1,2,3,4,5,6,7].map(n=>`/static/notification-default.b64.${String(n).padStart(2,'0')}?v=0.5.54`);
const ASSETS=[
  '/static/app.css?v=0.5.54',
  '/static/settings.css?v=0.5.54',
  '/static/settings.js?v=0.5.54',
  '/static/app.js?v=0.5.54',
  FEATURE_STYLE,
  FEATURE_SCRIPT,
  SOUND_PATCH,
  ...SOUND_PARTS,
  '/manifest.webmanifest'
];

async function soundPartText(cache,part){
  let response=await cache.match(part);
  if(!response){
    response=await fetch(part,{cache:'no-store'});
    if(response.ok)await cache.put(part,response.clone());
  }
  if(!response||!response.ok)throw new Error('Notification sound asset is unavailable');
  return (await response.text()).trim();
}

async function notificationSoundResponse(){
  const cache=await caches.open(CACHE);
  const cached=await cache.match(SOUND_PATH);
  if(cached)return cached;

  const texts=await Promise.all(SOUND_PARTS.map(part=>soundPartText(cache,part)));
  const binary=atob(texts.join(''));
  const bytes=new Uint8Array(binary.length);
  for(let i=0;i<binary.length;i++)bytes[i]=binary.charCodeAt(i);

  const response=new Response(bytes,{status:200,headers:{
    'Content-Type':'audio/mpeg',
    'Cache-Control':'public, max-age=31536000, immutable'
  }});
  await cache.put(SOUND_PATH,response.clone());
  return response;
}

self.addEventListener('install',event=>{
  self.skipWaiting();
  event.waitUntil((async()=>{
    const cache=await caches.open(CACHE);
    await cache.addAll(ASSETS);
    await notificationSoundResponse();
  })());
});

self.addEventListener('activate',event=>event.waitUntil(Promise.all([
  caches.keys().then(keys=>Promise.all(keys.filter(key=>key!==CACHE).map(key=>caches.delete(key)))),
  self.clients.claim()
])));

async function injectFeatureAssets(response){
  if(!response||!response.ok)return response;
  const contentType=response.headers.get('content-type')||'';
  if(!contentType.includes('text/html'))return response;
  let html=await response.text();
  if(!html.includes('/static/integration-notifications.css')){
    html=html.replace('</head>',`<link href="${FEATURE_STYLE}" rel="stylesheet"/>\n</head>`);
  }
  if(!html.includes('/static/integration-notifications.js')){
    const scripts=`<script src="${SOUND_PATCH}"></script>\n<script src="${FEATURE_SCRIPT}"></script>\n`;
    const settingsAnchor='<script src="/static/settings.js';
    html=html.includes(settingsAnchor)
      ? html.replace(settingsAnchor,scripts+settingsAnchor)
      : html.replace('</body>',scripts+'</body>');
  }
  const headers=new Headers(response.headers);
  headers.delete('content-length');
  headers.delete('content-encoding');
  return new Response(html,{status:response.status,statusText:response.statusText,headers});
}

self.addEventListener('fetch',event=>{
  if(event.request.method!=='GET')return;
  const url=new URL(event.request.url);
  if(url.origin!==self.location.origin||url.pathname.startsWith('/api/'))return;
  if(url.pathname===SOUND_PATH){
    event.respondWith(notificationSoundResponse());
    return;
  }
  if(event.request.mode==='navigate'||url.pathname==='/'||url.pathname==='/index.html'){
    event.respondWith(fetch(event.request,{cache:'no-store'}).then(injectFeatureAssets));
    return;
  }
  event.respondWith(
    fetch(event.request,{cache:'no-store'}).then(response=>{
      if(response.ok){
        const copy=response.clone();
        caches.open(CACHE).then(cache=>cache.put(event.request,copy));
      }
      return response;
    }).catch(()=>caches.match(event.request))
  );
});

function safeNotificationUrl(value='/'){
  try{
    const url=new URL(value||'/',self.location.origin);
    if(url.origin===self.location.origin)return url.href;
  }catch{}
  return new URL('/',self.location.origin).href;
}

self.addEventListener('push',event=>{
  let payload={};
  try{payload=event.data?.json()||{}}
  catch{payload={body:event.data?.text()||''}}
  const title=String(payload.title||'Torrent Dashboard').slice(0,160);
  const body=String(payload.body||'Torrent Dashboard has a new notification.').slice(0,1000);
  event.waitUntil(self.registration.showNotification(title,{
    body,
    tag:String(payload.tag||'torrent-dashboard-push').slice(0,160),
    data:{url:safeNotificationUrl(payload.url||'/')}
  }));
});

self.addEventListener('notificationclick',event=>{
  event.notification.close();
  const target=safeNotificationUrl(event.notification.data?.url||'/');
  event.waitUntil(clients.matchAll({type:'window',includeUncontrolled:true}).then(items=>{
    for(const client of items){
      if(client.url.startsWith(self.location.origin)&&'focus'in client){
        if('navigate'in client)client.navigate(target);
        return client.focus();
      }
    }
    return clients.openWindow?clients.openWindow(target):undefined;
  }));
});
