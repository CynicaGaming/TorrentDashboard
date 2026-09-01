#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
OLD = "0.5.5"
NEW = "0.5.6"


def replace_once(text, old, new, label):
    if old not in text:
        raise RuntimeError(f"Could not find {label}")
    return text.replace(old, new, 1)


def patch_dashboard():
    path = ROOT / "dashboard.py"
    text = path.read_text(encoding="utf-8")
    text = replace_once(text, "import argparse\n", "import argparse\nimport atexit\n", "atexit import")
    text = replace_once(text, "import threading\n", "import threading\nimport tempfile\n", "tempfile import")
    text = replace_once(text, f'VERSION = "{OLD}"\n\nDEFAULT_CONFIG = {{', f'''VERSION = "{NEW}"


class SingleInstanceLock:
    """Machine-level guard that prevents two dashboard processes from running."""

    def __init__(self):
        self._handle = None
        self._file = None

    def acquire(self):
        if os.name == "nt":
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.CreateMutexW(None, False, "Local\\\\TorrentDashboard.SingleInstance")
            if not handle:
                raise OSError("Could not create the Torrent Dashboard instance mutex")
            if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
                kernel32.CloseHandle(handle)
                return False
            self._handle = handle
            return True

        import fcntl
        lock_path = Path(tempfile.gettempdir()) / "torrent-dashboard.lock"
        lock_file = open(lock_path, "a+", encoding="utf-8")
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lock_file.close()
            return False
        lock_file.seek(0)
        lock_file.truncate()
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        self._file = lock_file
        return True

    def release(self):
        if self._handle is not None:
            try:
                import ctypes
                ctypes.windll.kernel32.CloseHandle(self._handle)
            except Exception:
                pass
            self._handle = None
        if self._file is not None:
            try:
                import fcntl
                fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
            try:
                self._file.close()
            except Exception:
                pass
            self._file = None


DEFAULT_CONFIG = {{''', "version and single-instance guard")

    text = replace_once(
        text,
        '    args=parser.parse_args()\n    if args.set_password:',
        '''    args=parser.parse_args()
    instance_lock=SingleInstanceLock()
    if not instance_lock.acquire():
        print("Torrent Dashboard is already running on this computer.")
        print("Close the existing dashboard process before starting another instance.")
        raise SystemExit(3)
    atexit.register(instance_lock.release)
    if args.set_password:''',
        "main instance acquisition",
    )
    text = replace_once(
        text,
        '        if path=="/health": return self.send_json(200,{"ok":True,"version":VERSION})',
        '        if path=="/health": return self.send_json(200,{"ok":True,"version":VERSION,"pid":os.getpid(),"application":str(APP_DIR),"python":sys.executable})',
        "health diagnostics",
    )
    text = replace_once(
        text,
        '    print(f"Torrent Dashboard {VERSION}")\n    print(f"Listening on {scheme}://{host}:{port}")',
        '    print(f"Torrent Dashboard {VERSION}")\n    print(f"Process ID: {os.getpid()}")\n    print(f"Application: {APP_DIR}")\n    print(f"Python: {sys.executable}")\n    print(f"Listening on {scheme}://{host}:{port}")',
        "startup diagnostics",
    )
    path.write_text(text, encoding="utf-8")


def patch_app_js():
    path = ROOT / "static" / "app.js"
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(r"const UI_SPECIAL=.*?\nconst CONFIGURED_SECRET_MASK=", re.S)
    replacement = r'''const UI_SPECIAL={torrentdashboard:'Torrent Dashboard',homeassistant:'Home Assistant',qbittorrent:'qBitTorrent',github:'GitHub',api:'API',ip:'IP',cidr:'CIDR',url:'URL',lan:'LAN',nic:'NIC',https:'HTTPS',http:'HTTP',ui:'UI',pwa:'PWA',exe:'EXE',eta:'ETA',id:'ID',pc:'PC',nas:'NAS',ntfy:'ntfy',sonarr:'Sonarr',radarr:'Radarr',lidarr:'Lidarr',prowlarr:'Prowlarr',jellyfin:'Jellyfin',plex:'Plex',discord:'Discord',windows:'Windows'};
function uiText(value=''){
  let s=String(value||'');if(!s)return s;
  const ell=s.endsWith('…');if(ell)s=s.slice(0,-1);
  s=s.replace(/Torrent Dashboard/gi,'torrentdashboard').replace(/Home Assistant/gi,'homeassistant').replace(/qBitTorrent/gi,'qbittorrent').replace(/GitHub/gi,'github');
  s=s.replace(/([a-z0-9])([A-Z])/g,'$1 $2').replace(/([A-Za-z])([0-9])/g,'$1 $2').replace(/([0-9])([A-Za-z])/g,'$1 $2').replace(/[_-]+/g,' ');
  let started=false;
  s=s.split(/\s+/).filter(Boolean).map(w=>{
    const special=UI_SPECIAL[w.toLowerCase()];
    if(special){if(/[A-Za-z]/.test(special))started=true;return special}
    if(/^\d/.test(w))return w;
    const lower=w.toLowerCase();
    if(!started&&/[A-Za-z]/.test(lower)){started=true;return lower.charAt(0).toUpperCase()+lower.slice(1)}
    return lower;
  }).join(' ');
  return s+(ell?'…':'')
}
function applySentenceCaseUi(root=document){
  const selectors='button,label,th,option,h1,h2,h3,h4,.panel-title,.settings-section-title,.eyebrow,.nav,.mobile-nav,.detail-tabs,legend,.metric span,.field-row b,.review-grid span,.update-status span,.brand strong,.brand small,.setup-rail strong,.setup-rail small,#setupSteps button';
  const els=[];
  if(root.matches?.(selectors))els.push(root);
  els.push(...(root.querySelectorAll?.(selectors)||[]));
  els.forEach(el=>{for(const n of [...el.childNodes]){if(n.nodeType===Node.TEXT_NODE){const raw=n.nodeValue,trim=raw.trim();if(trim&&trim.length<80&&/[A-Za-z]/.test(trim)){n.nodeValue=raw.replace(trim,uiText(trim))}}}})
}
const CONFIGURED_SECRET_MASK='''
    text, count = pattern.subn(lambda _m: replacement, text, count=1)
    if count != 1:
        raise RuntimeError(f"Expected one UI casing block, replaced {count}")
    text = text.replace("applyTitleCaseUi", "applySentenceCaseUi")
    text = text.replace("titleObserver", "caseObserver")
    text = text.replace("'Delete The Existing Mask Before Entering A New Secret'", "'Delete the existing mask before entering a new secret'")
    text = text.replace("'Stored Secret Cannot Be Revealed'", "'Stored secret cannot be revealed'")
    text = text.replace("showing?'Hide Secret':'Show Secret'", "showing?'Hide secret':'Show secret'")
    text = text.replace("btn.setAttribute('aria-label','Show Secret')", "btn.setAttribute('aria-label','Show secret')")
    text = replace_once(
        text,
        "if(!confirm(`installAndRestart ${version}?`))return;",
        "if(!confirm(`${uiText('installAndRestart')} ${version}?`))return;",
        "update confirmation casing",
    )
    path.write_text(text, encoding="utf-8")


def patch_versions():
    index = ROOT / "static" / "index.html"
    text = index.read_text(encoding="utf-8").replace(f"?v={OLD}", f"?v={NEW}")
    index.write_text(text, encoding="utf-8")

    sw = ROOT / "static" / "sw.js"
    text = sw.read_text(encoding="utf-8").replace("torrent-dashboard-v055", "torrent-dashboard-v056").replace(f"?v={OLD}", f"?v={NEW}")
    sw.write_text(text, encoding="utf-8")


patch_dashboard()
patch_app_js()
patch_versions()
print("Applied Torrent Dashboard 0.5.6 single-instance and sentence-case update")
