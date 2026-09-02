from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TARGET = "281b6613833a207af47c31381cd45c849c05b14d"
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


def from_target(path: str) -> bytes:
    return subprocess.check_output(["git", "show", f"{TARGET}:{path}"], cwd=ROOT)


for path in FILES:
    destination = ROOT / path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(from_target(path))

# Keep the exact v0.5.32 application behavior while publishing a forward-only
# release that installations on later prereleases can accept normally.
dashboard = ROOT / "dashboard.py"
text = dashboard.read_text(encoding="utf-8")
old = 'VERSION = "0.5.32"'
assert text.count(old) == 1, "Unexpected v0.5.32 version marker"
dashboard.write_text(text.replace(old, 'VERSION = "0.5.37"'), encoding="utf-8")

index = ROOT / "static/index.html"
text = index.read_text(encoding="utf-8")
assert "?v=0.5.32" in text, "Expected v0.5.32 asset markers"
index.write_text(text.replace("?v=0.5.32", "?v=0.5.37"), encoding="utf-8")

sw = ROOT / "static/sw.js"
text = sw.read_text(encoding="utf-8")
assert "torrent-dashboard-v0532" in text and "?v=0.5.32" in text, "Expected v0.5.32 service-worker markers"
text = text.replace("torrent-dashboard-v0532", "torrent-dashboard-v0537").replace("?v=0.5.32", "?v=0.5.37")
sw.write_text(text, encoding="utf-8")

print("Restored v0.5.32 application baseline as v0.5.37")
