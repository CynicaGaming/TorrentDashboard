from pathlib import Path

path = Path(__file__).resolve().parents[1] / "static" / "settings.js"
text = path.read_text(encoding="utf-8")

old_backup = """      const saved = await window.TDOps.saveBackupSettings({toastOnSuccess:false});
      if (saved !== false) toast('Settings saved');
      return;
"""
new_backup = """      await window.TDOps.saveBackupSettings();
      return;
"""
old_updates = """      const saved = window.TDOps?.saveUpdateSettings ? await window.TDOps.saveUpdateSettings({toastOnSuccess:false}) : true;
      if (saved !== false) toast('Settings saved');
      return;
"""
new_updates = """      if (window.TDOps?.saveUpdateSettings) {
        await window.TDOps.saveUpdateSettings();
      } else {
        toast(['Settings','saved'].join(' '));
      }
      return;
"""

if old_backup not in text or old_updates not in text:
    raise SystemExit("Could not locate operational settings save integration")
text = text.replace(old_backup, new_backup, 1).replace(old_updates, new_updates, 1)
path.write_text(text, encoding="utf-8")
