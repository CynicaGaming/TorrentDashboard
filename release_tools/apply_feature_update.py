#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(text, old, new, label):
    if old not in text:
        raise RuntimeError(f"Could not find {label}")
    return text.replace(old, new, 1)


def main():
    dashboard = ROOT / "dashboard.py"
    text = dashboard.read_text(encoding="utf-8")
    text = replace_once(text, 'VERSION = "0.5.3"', 'VERSION = "0.5.4"', 'dashboard version')
    dashboard.write_text(text, encoding="utf-8")

    index = ROOT / "static" / "index.html"
    text = index.read_text(encoding="utf-8")
    text = text.replace('?v=0.5.3', '?v=0.5.4')
    index.write_text(text, encoding="utf-8")

    app = ROOT / "static" / "app.js"
    text = app.read_text(encoding="utf-8")
    old = "function registerPwa(){if('serviceWorker'in navigator)navigator.serviceWorker.register('/sw.js?v=0.5.1').catch(()=>{});window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();state.deferredPrompt=e;$('#installPwa').classList.remove('hidden')});$('#installPwa').onclick=async()=>{if(state.deferredPrompt){state.deferredPrompt.prompt();await state.deferredPrompt.userChoice;state.deferredPrompt=null;$('#installPwa').classList.add('hidden')}}}"
    new = "function registerPwa(){if('serviceWorker'in navigator){navigator.serviceWorker.register('/sw.js',{updateViaCache:'none'}).then(reg=>reg.update()).catch(()=>{});navigator.serviceWorker.addEventListener('controllerchange',()=>{if(sessionStorage.getItem('tdSwReloaded')!=='1'){sessionStorage.setItem('tdSwReloaded','1');location.reload()}})}window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();state.deferredPrompt=e;$('#installPwa').classList.remove('hidden')});$('#installPwa').onclick=async()=>{if(state.deferredPrompt){state.deferredPrompt.prompt();await state.deferredPrompt.userChoice;state.deferredPrompt=null;$('#installPwa').classList.add('hidden')}}}"
    text = replace_once(text, old, new, 'service worker registration')
    app.write_text(text, encoding="utf-8")

    sw = ROOT / "static" / "sw.js"
    text = sw.read_text(encoding="utf-8")
    text = text.replace("torrent-dashboard-v053", "torrent-dashboard-v054").replace("0.5.3", "0.5.4")
    old_fetch = "self.addEventListener('fetch',event=>{if(event.request.method!=='GET'||new URL(event.request.url).pathname.startsWith('/api/'))return;event.respondWith(fetch(event.request,{cache:'no-store'}).then(response=>{const copy=response.clone();caches.open(CACHE).then(cache=>cache.put(event.request,copy));return response}).catch(()=>caches.match(event.request)))})"
    new_fetch = "self.addEventListener('fetch',event=>{if(event.request.method!=='GET'||new URL(event.request.url).pathname.startsWith('/api/'))return;event.respondWith(fetch(event.request,{cache:'no-store'}).then(response=>{if(response.ok){const copy=response.clone();caches.open(CACHE).then(cache=>cache.put(event.request,copy))}return response}).catch(()=>caches.match(event.request)))})"
    text = replace_once(text, old_fetch, new_fetch, 'service worker fetch handler')
    sw.write_text(text, encoding="utf-8")

    print('Applied Torrent Dashboard 0.5.4 service-worker recovery update')


if __name__ == '__main__':
    main()
