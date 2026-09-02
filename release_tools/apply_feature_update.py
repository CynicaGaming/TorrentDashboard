from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = "84c015e0ee53533e13e0b4b38da688b16b4b9742"
FILES = [
    "dashboard.py",
    "release_tools/validate_ui_strings.py",
    "static/app.css",
    "static/app.js",
    "static/index.html",
    "static/settings.css",
    "static/settings.js",
    "static/sw.js",
]

subprocess.run(["git", "restore", f"--source={BASE}", "--", *FILES], cwd=ROOT, check=True)

# Preserve the exact v0.5.33 application behavior, but publish it as a newer
# release so installations on v0.5.34/v0.5.35 can update back to the known-good code.
dashboard = ROOT / "dashboard.py"
text = dashboard.read_text(encoding="utf-8")
text, count = re.subn(r'^VERSION\s*=\s*["\']0\.5\.33["\']', 'VERSION = "0.5.36"', text, count=1, flags=re.M)
if count != 1:
    raise RuntimeError("Could not update dashboard version from 0.5.33 to 0.5.36")
dashboard.write_text(text, encoding="utf-8")

index = ROOT / "static/index.html"
text = index.read_text(encoding="utf-8").replace("?v=0.5.33", "?v=0.5.36")
index.write_text(text, encoding="utf-8")

sw = ROOT / "static/sw.js"
text = sw.read_text(encoding="utf-8")
text = text.replace("torrent-dashboard-v0533", "torrent-dashboard-v0536")
text = text.replace("?v=0.5.33", "?v=0.5.36")
sw.write_text(text, encoding="utf-8")

print("Restored v0.5.33 application behavior and prepared v0.5.36 rollback release.")
