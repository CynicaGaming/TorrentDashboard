from pathlib import Path
import json

root = Path(__file__).resolve().parents[1]

ops_source = r"""'use strict';
(() => {
  const pageId='system';
  let backupPasswordConfigured=false;
  let clearBackupPassword=false;
  const COMPONENT_LABELS={
    dashboard:'Torrent Dashboard',
    disk:'Disk space',
    backups:'Backups',
    updates:'Updates',
    clients:'qBittorrent clients',
    integrations:'Integrations'
  };

  function escapeHtml(value='') {
    return String(value??'').replace(/[&<>\"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[ch]));
  }
  function notify(message,tone='') {
    if(typeof toast==='function')return toast(message,tone);
    console[tone==='error'?'error':'log'](message);
  }
  async function getJson(path) {
    if(typeof api==='function')return api(path);
    const response=await fetch(path,{cache:'no-store',credentials:'same-origin'});
    const data=await response.json();
    if(!response.ok)throw new Error(data.error||`HTTP ${response.status}`);
    return data;
  }
  async function postJson(path,payload) {
    if(typeof post==='function')return post(path,payload);
    const me=await getJson('/api/me');
    const response=await fetch(path,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':me.csrf||''},body:JSON.stringify(payload)});
    const data=await response.json();
    if(!response.ok)throw new Error(data.error||`HTTP ${response.status}`);
    return data;
  }
  function value(id,fallback=''){const el=document.querySelector('#'+id);return el?el.value:fallback}
  function checked(id){return !!document.querySelector('#'+id)?.checked}
  function setValue(id,v){const el=document.querySelector('#'+id);if(el)el.value=String(v??'')}
  function setChecked(id,v){const el=document.querySelector('#'+id);if(el)el.checked=!!v}
  function humanizeIdentifier(value='') {
    const raw=String(value??'').trim();
    if(!raw)return'';
    const spaced=raw.replace(/[_-]+/g,' ').replace(/([a-z0-9])([A-Z])/g,'$1 $2').replace(/\s+/g,' ').trim().toLowerCase();
    return spaced.charAt(0).toUpperCase()+spaced.slice(1);
  }
  function stateLabel(value='') {
    const key=String(value??'').trim().toLowerCase();
    const labels={healthy:'Healthy',issue:'Needs attention',warning:'Warning',disconnected:'Disconnected',success:'Success',failure:'Failed',denied:'Denied',info:'Info',unknown:'Unknown'};
    return labels[key]||humanizeIdentifier(value)||'Unknown';
  }
  function componentLabel(value='') {return COMPONENT_LABELS[String(value||'')]||humanizeIdentifier(value)||'Component'}

  function buildNavigation() {
    const subnav=document.querySelector('#settingsSubnav');
    if(subnav&&!subnav.querySelector('[data-settings-page="system"]')){
      const button=document.createElement('button');
      button.type='button';button.dataset.view='settings';button.dataset.settingsPage=pageId;button.textContent='System health';
      button.addEventListener('click',()=>window.TDSettings?.activate?.(pageId));
      subnav.appendChild(button);
    }
    const mobile=document.querySelector('#settingsMobilePage');
    if(mobile&&!mobile.querySelector('option[value="system"]')){
      const option=document.createElement('option');option.value='system';option.textContent='System health';mobile.appendChild(option);
    }
  }

  function addCard(sectionName,id,markup) {
    if(document.querySelector('#'+id))return;
    const section=document.querySelector(`[data-settings-section="${sectionName}"]`);
    if(section)section.insertAdjacentHTML('beforeend',markup);
  }

  function buildSystemPage() {
    if(document.querySelector('[data-settings-section="system"]'))return;
    const content=document.querySelector('.settings-content');
    if(!content)return;
    const section=document.createElement('section');
    section.className='settings-page';section.dataset.settingsSection='system';
    section.innerHTML=`
      <div class="panel settings-card" id="opsSystemHealthCard">
        <div class="panel-title">System health</div>
        <p class="muted">Operational status for Torrent Dashboard, qBittorrent clients, integrations, backups, updates, and disk space.</p>
        <div class="update-status" id="opsHealthSummary"><div><span>Overall</span><strong>Loading…</strong></div></div>
        <div class="notification-list" id="opsHealthComponents"></div>
        <div class="settings-inline-actions"><button class="secondary" id="opsRefreshHealth" type="button">Refresh health</button></div>
      </div>`;
    content.appendChild(section);
    document.querySelector('#opsRefreshHealth')?.addEventListener('click',loadHealth);
  }

  function buildBackupCards() {
    addCard('backups','opsBackupProtectionCard',`
      <div class="panel settings-card" id="opsBackupProtectionCard">
        <div class="panel-title">Backup protection</div>
        <p class="muted">Protect portable backup archives with password-based authenticated encryption before they are stored locally or exported.</p>
        <label class="toggle"><input id="opsBackupEncrypt" type="checkbox"/><span>Encrypt portable backup archives</span></label>
        <label>Backup encryption password<input id="opsBackupPassword" type="password" autocomplete="new-password" placeholder="At least 12 characters"/></label>
        <div class="field-help">The password stays local to this installation and is not written into portable backups.</div>
        <div class="settings-inline-actions"><button class="secondary" id="opsClearBackupPassword" type="button">Clear stored backup password</button></div>
      </div>`);
    addCard('backups','opsBackupScheduleCard',`
      <div class="panel settings-card" id="opsBackupScheduleCard">
        <div class="panel-title">Backup schedule</div>
        <p class="muted">Create local backups automatically on the schedule you choose.</p>
        <label class="toggle"><input id="opsBackupSchedule" type="checkbox"/><span>Automatic backups</span></label>
        <div class="settings-form-grid two-col">
          <label>Frequency<select id="opsBackupFrequency"><option value="hourly">Hourly</option><option value="daily">Daily</option><option value="weekly">Weekly</option></select></label>
          <label>Run hour<input id="opsBackupHour" type="number" min="0" max="23" step="1"/></label>
          <label>Weekly day<select id="opsBackupWeekday"><option value="0">Monday</option><option value="1">Tuesday</option><option value="2">Wednesday</option><option value="3">Thursday</option><option value="4">Friday</option><option value="5">Saturday</option><option value="6">Sunday</option></select></label>
        </div>
      </div>`);
    addCard('backups','opsRetentionCard',`
      <div class="panel settings-card" id="opsRetentionCard">
        <div class="panel-title">Retention</div>
        <p class="muted">Control how many backups are kept and how long local dashboard and staged-update history is retained.</p>
        <div class="settings-form-grid two-col">
          <label>Dashboard history (days)<input id="opsHistoryDays" type="number" min="1" max="3650"/></label>
          <label>Backups to retain<input id="opsBackupCount" type="number" min="1" max="365"/></label>
          <label>Staged updates (days)<input id="opsUpdateDays" type="number" min="1" max="365"/></label>
        </div>
        <div class="settings-inline-actions"><button class="secondary" id="opsRunRetention" type="button">Run retention now</button></div>
        <div class="test-result muted" id="opsRetentionStatus"></div>
      </div>`);
    document.querySelector('#opsClearBackupPassword')?.addEventListener('click',()=>{
      clearBackupPassword=true;backupPasswordConfigured=false;setValue('opsBackupPassword','');setChecked('opsBackupEncrypt',false);
      notify('Stored backup password will be cleared when backup settings are saved');
    });
    document.querySelector('#opsRunRetention')?.addEventListener('click',runRetention);
  }

  function buildUpdateCard() {
    addCard('updates','opsAutomaticUpdatesCard',`
      <div class="panel settings-card" id="opsAutomaticUpdatesCard">
        <div class="panel-title">Automatic updates</div>
        <p class="muted">Install updater-ready releases automatically during a local maintenance window.</p>
        <label class="toggle"><input id="opsAutoUpdate" type="checkbox"/><span>Install updates automatically</span></label>
        <div class="field-help">Incomplete GitHub releases are skipped. The previous complete release remains available until the new source and Windows packages are verified.</div>
        <div class="settings-form-grid two-col">
          <label>Maintenance window start<input id="opsUpdateStart" type="time" step="60"/></label>
          <label>Maintenance window end<input id="opsUpdateEnd" type="time" step="60"/></label>
        </div>
        <label class="toggle"><input id="opsPreUpdateBackup" type="checkbox"/><span>Create a backup before automatic updates</span></label>
      </div>`);
  }

  function buildSurfaces() {
    buildNavigation();buildSystemPage();buildBackupCards();buildUpdateCard();
  }

  function fillPolicy(settings) {
    const backups=settings.backups||{},maintenance=settings.maintenance||{},auto=maintenance.auto_update||{},retention=maintenance.retention||{};
    backupPasswordConfigured=!!backups.password_configured;clearBackupPassword=false;
    setChecked('opsBackupEncrypt',backups.encrypt);setValue('opsBackupPassword','');
    const password=document.querySelector('#opsBackupPassword');if(password)password.placeholder=backupPasswordConfigured?'Stored password configured':'At least 12 characters';
    setChecked('opsBackupSchedule',backups.schedule_enabled);setValue('opsBackupFrequency',backups.schedule_frequency||'daily');setValue('opsBackupHour',backups.schedule_hour??3);setValue('opsBackupWeekday',backups.schedule_weekday??0);
    setChecked('opsAutoUpdate',auto.enabled);setValue('opsUpdateStart',auto.window_start||'03:00');setValue('opsUpdateEnd',auto.window_end||'05:00');setChecked('opsPreUpdateBackup',auto.pre_backup!==false);
    setValue('opsHistoryDays',retention.history_days??30);setValue('opsBackupCount',retention.backup_count??14);setValue('opsUpdateDays',retention.update_days??14);
  }

  async function loadPolicy() {
    buildSurfaces();
    try{fillPolicy(await getJson('/api/settings'))}catch(error){notify(error.message,'error')}
  }

  async function saveBackupSettings({toastOnSuccess=true}={}) {
    buildSurfaces();
    const entered=value('opsBackupPassword','');
    const payload={
      backups:{
        encrypt:checked('opsBackupEncrypt'),password:entered||(backupPasswordConfigured?'<configured>':''),clear_password:clearBackupPassword,
        schedule_enabled:checked('opsBackupSchedule'),schedule_frequency:value('opsBackupFrequency','daily'),schedule_hour:Number(value('opsBackupHour',3)),schedule_weekday:Number(value('opsBackupWeekday',0))
      },
      maintenance:{retention:{history_days:Number(value('opsHistoryDays',30)),backup_count:Number(value('opsBackupCount',14)),update_days:Number(value('opsUpdateDays',14))}}
    };
    try{
      const result=await postJson('/api/settings',payload);
      const backups=result.settings?.backups||{};backupPasswordConfigured=!!backups.password_configured;clearBackupPassword=false;setValue('opsBackupPassword','');
      fillPolicy(result.settings||await getJson('/api/settings'));
      if(toastOnSuccess)notify('Settings saved');
      return result;
    }catch(error){notify(error.message,'error');return false}
  }

  async function saveUpdateSettings({toastOnSuccess=true}={}) {
    buildSurfaces();
    const payload={maintenance:{auto_update:{enabled:checked('opsAutoUpdate'),window_start:value('opsUpdateStart','03:00'),window_end:value('opsUpdateEnd','05:00'),pre_backup:checked('opsPreUpdateBackup')}}};
    try{
      const result=await postJson('/api/settings',payload);
      fillPolicy(result.settings||await getJson('/api/settings'));
      if(toastOnSuccess)notify('Settings saved');
      return result;
    }catch(error){notify(error.message,'error');return false}
  }

  async function loadHealth() {
    buildSurfaces();
    const summary=document.querySelector('#opsHealthSummary'),list=document.querySelector('#opsHealthComponents');
    if(summary)summary.innerHTML='<div><span>Overall</span><strong>Checking…</strong></div>';
    try{
      const health=await getJson('/api/system-health');
      if(summary)summary.innerHTML=`<div><span>Overall</span><strong>${escapeHtml(stateLabel(health.state||'unknown'))}</strong></div><div><span>Version</span><strong>${escapeHtml(health.version||'')}</strong></div><div><span>Uptime</span><strong>${Math.floor(Number(health.uptime_seconds||0)/60)} min</strong></div><div><span>Free disk</span><strong>${formatBytes(health.disk?.free||0)}</strong></div>`;
      if(list)list.innerHTML=(health.components||[]).map(item=>{const state=String(item.state||'unknown').toLowerCase();const tone=state==='healthy'?'good':state==='warning'?'warn':'bad';return `<article class="notification-item ${tone}"><span class="notification-dot" aria-hidden="true"></span><div class="notification-copy"><div class="notification-title"><b>${escapeHtml(componentLabel(item.id))}</b><span>${escapeHtml(stateLabel(item.state))}</span></div><p>${escapeHtml(item.message||'')}</p></div></article>`}).join('')||'<div class="settings-empty"><b>No health data</b></div>';
    }catch(error){if(summary)summary.innerHTML='<div><span>Overall</span><strong>Unavailable</strong></div>';if(list)list.innerHTML=`<div class="settings-empty"><b>Health check failed</b><span>${escapeHtml(error.message)}</span></div>`}
  }
  function formatBytes(value){let n=Number(value||0);if(!n)return'0 B';const units=['B','KB','MB','GB','TB'];let i=0;while(n>=1024&&i<units.length-1){n/=1024;i++}return`${n.toFixed(i?1:0)} ${units[i]}`}

  async function runRetention() {
    const status=document.querySelector('#opsRetentionStatus');if(status)status.textContent='Running retention…';
    try{const data=await postJson('/api/retention/run',{});if(status){status.className='test-result ok';status.textContent=`Retention complete · ${data.result?.backups_removed?.length||0} backup(s) and ${data.result?.updates_removed?.length||0} staged update artifact(s) removed.`}await loadPolicy()}
    catch(error){if(status){status.className='test-result bad';status.textContent=error.message}}
  }

  function activate(page) {
    buildSurfaces();
    if(page==='system')loadHealth();
    if(page==='backups'||page==='updates')loadPolicy();
  }

  window.TDOps={activate,loadPolicy,saveBackupSettings,saveUpdateSettings};

  function initialize() {
    if(!document.querySelector('#view-settings'))return;
    buildSurfaces();
    const current=localStorage.tdSettingsPage||'general';
    if(current==='system')setTimeout(()=>window.TDSettings?.activate?.('system'),0);
    else if(current==='backups'||current==='updates')activate(current);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initialize,{once:true});else initialize();
})();
"""
(root / 'static' / 'ops.js').write_text(ops_source, encoding='utf-8')

settings = root / 'static' / 'settings.js'
text = settings.read_text(encoding='utf-8')
old = "const corePages = new Set(['general','access','clients','updates','notifications']);"
new = "const corePages = new Set(['general','access','clients','backups','updates','notifications']);"
if old not in text:
    raise SystemExit('Could not locate core settings page set')
text = text.replace(old, new, 1)
old = "    if (page === 'backups') loadBackups();\n"
new = "    if (page === 'backups') loadBackups();\n    window.TDOps?.activate?.(page);\n"
if old not in text:
    raise SystemExit('Could not locate settings activation hook')
text = text.replace(old, new, 1)
old = "    if (activePage === 'updates') return saveUpdateSource();\n"
new = """    if (activePage === 'backups') {
      if (!window.TDOps?.saveBackupSettings) return toast('Backup settings are unavailable','error');
      const saved = await window.TDOps.saveBackupSettings({toastOnSuccess:false});
      if (saved !== false) toast('Settings saved');
      return;
    }
    if (activePage === 'updates') {
      const source = await saveUpdateSource({toastOnSuccess:false});
      if (!source) return;
      const saved = window.TDOps?.saveUpdateSettings ? await window.TDOps.saveUpdateSettings({toastOnSuccess:false}) : true;
      if (saved !== false) toast('Settings saved');
      return;
    }
"""
if old not in text:
    raise SystemExit('Could not locate settings save dispatch')
text = text.replace(old, new, 1)
start = text.index('  async function saveUpdateSource() {')
end = text.index('\n  async function loadExtras()', start)
replacement = """  async function saveUpdateSource({toastOnSuccess=true}={}) {
    const repository = updateSourceRepository();
    if (!repository) { toast('Enter a GitHub repository','error'); return null; }
    try {
      const d = await post('/api/update-source', {repository});
      state.settings = d.settings;
      const input = document.querySelector('#uRepository');
      if (input) input.value = d.repository || repository;
      renderUpdateInfo({configured:true,repository:d.repository || repository,currentVersion:state.me?.version,state:d.settings?.runtime?.updateState||{}});
      if (toastOnSuccess) toast('Settings saved');
      return d;
    } catch (e) {
      toast(e.message,'error');
      return null;
    }
  }
"""
text = text[:start] + replacement + text[end:]
settings.write_text(text, encoding='utf-8')

css = root / 'static' / 'settings.css'
css_text = css.read_text(encoding='utf-8')
marker = '0.5.158 consistent spacing for settings pages with multiple cards'
if marker not in css_text:
    css_text = css_text.rstrip() + f"\n\n/* {marker}. */\n.settings-page>.settings-card+.settings-card{{margin-top:12px}}\n"
    css.write_text(css_text, encoding='utf-8')

operations = root / 'src' / 'torrent_dashboard' / 'operations.py'
op_text = operations.read_text(encoding='utf-8')
if 'import re\n' not in op_text:
    op_text = op_text.replace('import json\n', 'import json\nimport re\n', 1)
helper_marker = '\ndef build_system_health(*, app_dir: Path | str, version: str, started_at: float, config: dict,\n'
helper = '''
def _display_state(value: str) -> str:
    raw = str(value or "unknown").strip()
    if not raw:
        return "Unknown"
    text = re.sub(r"([a-z0-9])([A-Z])", r"\\1 \\2", raw)
    text = re.sub(r"[_-]+", " ", text)
    text = re.sub(r"\\s+", " ", text).strip().lower()
    return text[:1].upper() + text[1:]


def _count_label(count: int, singular: str, plural: str | None = None) -> str:
    count = int(count or 0)
    return f"{count} {singular if count == 1 else (plural or singular + 's')}"

'''
if '_display_state(value: str)' not in op_text:
    if helper_marker not in op_text:
        raise SystemExit('Could not locate system health helper insertion point')
    op_text = op_text.replace(helper_marker, helper + helper_marker, 1)
block_start = op_text.index('    components = [', op_text.index('def build_system_health'))
block_end = op_text.index('    overall = ', block_start)
new_block = '''    client_count = len(clients)
    integration_count = len(integrations)
    update_label = _display_state(update_status)

    components = [
        {"id": "dashboard", "state": "healthy", "message": f"Torrent Dashboard {version} is running"},
        {
            "id": "disk",
            "state": "issue" if disk["free"] and disk["free"] < low_disk_bytes else "healthy",
            "message": "Free disk space is below the configured threshold" if disk["free"] and disk["free"] < low_disk_bytes else "Disk space is within the configured threshold",
        },
        {
            "id": "backups",
            "state": "issue" if backup_issue else "healthy",
            "message": "Scheduled backups are enabled but no backup is available" if backup_issue else ("Backup library is available" if latest_backup else "Backup scheduling is disabled or no manual backup has been created"),
        },
        {
            "id": "updates",
            "state": "issue" if update_issue else "healthy",
            "message": str((update_state or {}).get("error") or f"Update status: {update_label}"),
        },
        {
            "id": "clients",
            "state": "issue" if disconnected_clients else "healthy",
            "message": f"{_count_label(disconnected_clients, 'qBittorrent client')} unavailable" if disconnected_clients else f"{_count_label(client_count, 'qBittorrent client')} monitored",
        },
        {
            "id": "integrations",
            "state": "issue" if integration_issues else "healthy",
            "message": f"{_count_label(integration_issues, 'integration')} need attention" if integration_issues else f"{_count_label(integration_count, 'integration')} monitored",
        },
    ]
'''
op_text = op_text[:block_start] + new_block + op_text[block_end:]
operations.write_text(op_text, encoding='utf-8')

(root / 'tests' / 'test_system_ops_ui.py').write_text('''from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SystemOperationsUiTests(unittest.TestCase):
    def test_ops_script_exposes_reorganized_surfaces(self):
        source = (ROOT / "static" / "ops.js").read_text(encoding="utf-8")
        for marker in (
            "System health", "Backup protection", "Backup schedule", "Automatic updates",
            "Retention", "/api/system-health", "/api/retention/run", "schedule_frequency",
            "window_start", "backup_count",
        ):
            self.assertIn(marker, source)
        self.assertNotIn("Security audit", source)
        self.assertNotIn("opsAuditList", source)
        self.assertNotIn("/api/audit?", source)

    def test_operational_settings_use_existing_settings_pages(self):
        source = (ROOT / "static" / "ops.js").read_text(encoding="utf-8")
        settings = (ROOT / "static" / "settings.js").read_text(encoding="utf-8")
        self.assertIn("addCard('backups','opsBackupProtectionCard'", source)
        self.assertIn("addCard('backups','opsBackupScheduleCard'", source)
        self.assertIn("addCard('backups','opsRetentionCard'", source)
        self.assertIn("addCard('updates','opsAutomaticUpdatesCard'", source)
        self.assertIn("'clients','backups','updates','notifications'", settings)
        self.assertIn("window.TDOps.saveBackupSettings", settings)
        self.assertIn("window.TDOps.saveUpdateSettings", settings)

    def test_system_health_uses_human_readable_labels(self):
        source = (ROOT / "static" / "ops.js").read_text(encoding="utf-8")
        self.assertIn("dashboard:'Torrent Dashboard'", source)
        self.assertIn("disk:'Disk space'", source)
        self.assertIn("clients:'qBittorrent clients'", source)
        self.assertIn("stateLabel(health.state", source)
        self.assertIn('class="notification-dot"', source)
        self.assertIn('class="notification-copy"', source)

    def test_multi_card_settings_pages_have_spacing(self):
        source = (ROOT / "static" / "settings.css").read_text(encoding="utf-8")
        self.assertIn('.settings-page>.settings-card+.settings-card{margin-top:12px}', source)

    def test_runtime_keeps_durable_audit_api_without_duplicate_ui(self):
        source = (ROOT / "src" / "torrent_dashboard" / "runtime.py").read_text(encoding="utf-8")
        self.assertIn('/static/ops.js?v=', source)
        self.assertIn('path == "/api/system-health"', source)
        self.assertIn('path == "/api/audit"', source)
        self.assertIn('path == "/api/retention/run"', source)


if __name__ == "__main__":
    unittest.main()
''', encoding='utf-8')

(root / 'tests' / 'test_operations.py').write_text('''from datetime import datetime
import os
import tempfile
import time
from pathlib import Path
import unittest

from torrent_dashboard.operations import (
    automatic_update_due,
    build_system_health,
    prune_backups,
    prune_update_artifacts,
    scheduled_backup_due,
    within_maintenance_window,
)


class OperationsTests(unittest.TestCase):
    def test_maintenance_window_supports_overnight_ranges(self):
        self.assertTrue(within_maintenance_window(datetime(2026, 1, 1, 23, 30), "23:00", "02:00"))
        self.assertTrue(within_maintenance_window(datetime(2026, 1, 2, 1, 30), "23:00", "02:00"))
        self.assertFalse(within_maintenance_window(datetime(2026, 1, 2, 12, 0), "23:00", "02:00"))

    def test_daily_backup_runs_once_per_day_at_configured_hour(self):
        policy = {"schedule_enabled": True, "schedule_frequency": "daily", "schedule_hour": 3, "schedule_weekday": 0}
        now = datetime(2026, 9, 11, 3, 5)
        self.assertTrue(scheduled_backup_due(policy, {}, now))
        state = {"last_backup_ts": int(datetime(2026, 9, 11, 3, 1).timestamp())}
        self.assertFalse(scheduled_backup_due(policy, state, now))

    def test_auto_update_runs_once_per_window_day(self):
        policy = {"enabled": True, "window_start": "03:00", "window_end": "05:00"}
        now = datetime(2026, 9, 11, 4, 0)
        self.assertTrue(automatic_update_due(policy, {}, now))
        self.assertFalse(automatic_update_due(policy, {"last_auto_update_day": "2026-09-11"}, now))

    def test_prune_backups_keeps_newest_count(self):
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            directory = root / "data" / "backups"
            directory.mkdir(parents=True)
            for index in range(5):
                path = directory / f"backup-{index}.tdbackup"
                path.write_bytes(b"x")
                os.utime(path, (100 + index, 100 + index))
            removed = prune_backups(root, 2)
            self.assertEqual(len(removed), 3)
            self.assertEqual(len(list(directory.glob("*.tdbackup"))), 2)

    def test_prune_update_artifacts_preserves_active_version(self):
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            old = root / "0.5.100"
            keep = root / "0.5.155"
            old.mkdir(); keep.mkdir()
            stale = time.time() - 40 * 86400
            os.utime(old, (stale, stale)); os.utime(keep, (stale, stale))
            removed = prune_update_artifacts(root, 14, protected_versions={"0.5.155"})
            self.assertIn("0.5.100", removed)
            self.assertFalse(old.exists())
            self.assertTrue(keep.exists())

    def test_security_events_do_not_make_service_health_unhealthy(self):
        with tempfile.TemporaryDirectory() as temp_name:
            health = build_system_health(
                app_dir=Path(temp_name), version="0.5.158", started_at=time.time()-60,
                config={"dashboard":{"low_disk_gb":0},"backups":{}},
                update_state={"state":"installed"}, maintenance_state={}, backups=[],
                audit_summary={"failures_24h":2}, client_rows=[], integration_rows=[],
            )
        self.assertEqual(health["state"], "healthy")
        self.assertNotIn("audit", [item["id"] for item in health["components"]])
        updates = next(item for item in health["components"] if item["id"] == "updates")
        self.assertEqual(updates["message"], "Update status: Installed")


if __name__ == "__main__":
    unittest.main()
''', encoding='utf-8')

init = root / 'src' / 'torrent_dashboard' / '__init__.py'
init_text = init.read_text(encoding='utf-8').replace('__version__ = "0.5.157"', '__version__ = "0.5.158"')
if '__version__ = "0.5.158"' not in init_text:
    raise SystemExit('Version bump failed')
init.write_text(init_text, encoding='utf-8')
for path in [root / 'static' / 'index.html', root / 'static' / 'app.js']:
    path.write_text(path.read_text(encoding='utf-8').replace('0.5.157', '0.5.158'), encoding='utf-8')
sw = root / 'static' / 'sw.js'
sw.write_text(sw.read_text(encoding='utf-8').replace('torrent-dashboard-v05157', 'torrent-dashboard-v05158').replace('0.5.157', '0.5.158'), encoding='utf-8')

catalog_path = root / 'release_notes' / 'releases.json'
catalog = json.loads(catalog_path.read_text(encoding='utf-8'))
if not any(str(item.get('version')) == '0.5.158' for item in catalog['releases']):
    catalog['releases'].insert(0, {
        'version': '0.5.158',
        'date': '2026-09-11',
        'status': 'prerelease',
        'title': 'Operational settings organization and health copy cleanup',
        'summary': 'Moves backup and update policy controls into their existing settings areas, leaves System health as a diagnostics-only page, and replaces machine-oriented health labels with readable UI copy.',
        'highlights': [
            'Backup protection and Backup schedule are now separate cards under Settings → Backups, with Retention alongside them.',
            'Automatic updates now lives under Settings → Updates and saves with the existing update settings action.',
            'System health is diagnostics-only and uses human-readable component names and status labels.',
            'Security-audit storage remains available to the backend, but the duplicate audit UI is removed because security activity is already surfaced through Notifications.'
        ],
        'fixes': [
            'Adds consistent spacing between adjacent settings cards.',
            'Stops recent denied or failed security events from making overall service health report an Issue.',
            'Removes raw machine identifiers and awkward singular/plural text from the System health presentation.'
        ],
        'technical': [
            'Backups joins the shared settings save-bar pages; the operations adapter exposes scoped backup and automatic-update save hooks to the existing settings controller.',
            'The durable audit database and /api/audit endpoint remain intact for logging and programmatic diagnostics even though the duplicate browser audit card is removed.',
            'System health keeps stable internal component IDs while the frontend maps them to presentation labels.'
        ],
        'validation': [
            'Runs source/unit validation, browser contract checks, JavaScript syntax checks, generated documentation validation, the source updater package build, and the Windows PyInstaller smoke build.'
        ],
        'known_issues': [
            'Backup encryption remains opt-in; unencrypted portable backups can contain saved client and integration credentials and should be stored securely.',
            'Windows executables are not code-signed yet.'
        ],
        'architecture': [
            'Operational policy is presented with the domain it configures instead of accumulating on a generic System settings page.'
        ],
        'decisions': [
            'Keep System health as a diagnostics-only view while retaining durable audit storage behind Notifications and operational APIs.',
            'Use the shared settings save bar for Backup and Update policy changes.'
        ],
        'next_steps': [
            {'priority': 1, 'title': 'Verify reorganized settings after auto-update', 'detail': 'Confirm v0.5.158 shows separate Backup protection, Backup schedule, and Retention cards under Backups; Automatic updates under Updates; and a diagnostics-only System health page with readable labels.'}
        ]
    })
catalog_path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

current = {
    'schema': 1,
    'status': 'release-candidate',
    'objective': 'Publish the v0.5.158 operational settings organization and System health copy cleanup',
    'why': 'The initial System operations page grouped unrelated backup, update, retention, audit, and health concerns together, duplicated security activity already visible in Notifications, exposed machine-oriented labels, and lacked the normal spacing used across other settings pages.',
    'acceptance_criteria': [
        'Backup protection and Backup schedule are separate cards under Backups.',
        'Retention is under Backups and Automatic updates is under Updates.',
        'System health contains diagnostics only, with readable component and status labels.',
        'Security audit is removed from the browser System page and audit failures do not mark overall service health unhealthy.',
        'Adjacent settings cards have consistent spacing and Backups uses the shared Save action.',
        'Ubuntu/Windows Python 3.13/3.14 validation passes.',
        'The source updater ZIP and compiled Windows package build successfully, and all three Windows executables pass smoke tests.',
        'v0.5.158 is published with both source and Windows updater ZIPs and SHA-256 digests.'
    ],
    'decisions': [
        'Organize settings by domain instead of collecting operational policy under a generic System page.',
        'Keep the durable security audit backend but use Notifications as the user-facing security activity surface.',
        'Keep System health focused on service/runtime health rather than historical security events.'
    ],
    'files': [
        'static/ops.js', 'static/settings.js', 'static/settings.css',
        'src/torrent_dashboard/operations.py', 'tests/test_system_ops_ui.py', 'tests/test_operations.py',
        'src/torrent_dashboard/__init__.py', 'static/index.html', 'static/app.js', 'static/sw.js',
        'release_notes/releases.json'
    ],
    'blockers': [],
    'out_of_scope': ['No changes to audit persistence, security-event generation, notification delivery semantics, backup archive format, updater verification, or retention execution semantics.'],
    'next_action': 'Run the full pull-request validation and Windows smoke build; if green, merge and verify the updater-visible v0.5.158 release.'
}
(root / 'development' / 'current.json').write_text(json.dumps(current, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
