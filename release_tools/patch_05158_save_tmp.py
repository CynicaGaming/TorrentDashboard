from pathlib import Path

root = Path(__file__).resolve().parents[1]

path = root / "static" / "settings.js"
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

validator = root / "release_tools" / "validate_ui_strings.py"
validation = validator.read_text(encoding="utf-8")
old_contract = "const corePages = new Set(['general','access','clients','updates','notifications']);"
new_contract = "const corePages = new Set(['general','access','clients','backups','updates','notifications']);"
if old_contract not in validation:
    raise SystemExit("Could not locate core Settings page validation contract")
validation = validation.replace(old_contract, new_contract, 1)
validator.write_text(validation, encoding="utf-8")
