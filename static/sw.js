'use strict';

const CACHE='torrent-dashboard-v0554-mobile-notifications';
const FEATURE_STYLE='/static/integration-notifications.css?v=0.5.55';
const FEATURE_SCRIPT='/static/integration-notifications.js?v=0.5.55';
const SOUND_PATCH='/static/default-notification-sound.js?v=0.5.55';
const SOUND_PATH='/static/notification-default.mp3';
const SOUND_PARTS=[1,2,3,4,5,6,7].map(n=>`/static/notification-default.b64.${String(n).padStart(2,'0')}?v=0.5.55`);
const ASSETS=[
  '/static/app.css?v=0.5.55',
  '/static/settings.css?v=0.5.55',
  '/static/settings.js?v=0.5.55',
  '/static/app.js?v=0.5.55',
  FEATURE_STYLE,
  FEATURE_SCRIPT,
  SOUND_PATCH,
  ...SOUND_PARTS,
  '/manifest.webmanifest'
];

self.addEventListener('install',event=>{
  self.skipWaiting();
  event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(ASSETS)));
});

self.addEventListener('activate',event=>event.waitUntil(Promise.all([
  caches.keys().then(keys=>Promise.all(keys.filter(key=>key!==CACHE).map(key=>caches.delete(key)))),
  self.clients.claim()
])));

async function notificationSoundResponse(){
  const cache=await caches.open(CACHE);
  const texts=[];
  for(const part of SOUND_PARTS){
    let response=await cache.match(part);
    if(!response){
      response=await fetch(part,{cache:'no-store'});
      if(response.ok) await cache.put(part,response.clone());
    }
    if(!response||!response.ok) throw new Error('Notification sound asset is unavailable');
    texts.push((await response.text()).trim());
  }
  const binary=atob(texts.join(''));
  const bytes=new Uint8Array(binary.length);
  for(let i=0;i<binary.length;i++) bytes[i]=binary.charCodeAt(i);
  return new Response(bytes,{status:200,headers:{'Content-Type':'audio/mpeg','Content-Length':String(bytes.length),'Cache-Control':'public, max-age=31536000, immutable','Accept-Ranges':'bytes'}});
}

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

self.addEventListener('push',event=>{
  let payload={};
  try{payload=event.data?.json()||{}}
  catch{payload={body:event.data?.text()||''}}
  const title=payload.title||'Torrent Dashboard';
  event.waitUntil(self.registration.showNotification(title,{
    body:payload.body||'Torrent Dashboard has a new notification.',
    tag:payload.tag||'torrent-dashboard-push',
    data:{url:payload.url||'/'}
  }));
});

self.addEventListener('notificationclick',event=>{
  event.notification.close();
  const target=new URL(event.notification.data?.url||'/',self.location.origin).href;
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
