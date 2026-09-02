#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET_VERSION = "0.5.46"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected exactly one {label} match, found {count}")
    return text.replace(old, new, 1)


def main():
    dashboard = ROOT / "dashboard.py"
    text = dashboard.read_text(encoding="utf-8")
    text = replace_once(text, 'VERSION = "0.5.44"', f'VERSION = "{TARGET_VERSION}"', "dashboard version")
    dashboard.write_text(text, encoding="utf-8")

    index = ROOT / "static" / "index.html"
    text = index.read_text(encoding="utf-8")
    if "v=0.5.44" not in text:
        raise RuntimeError("Expected v0.5.44 static asset references")
    index.write_text(text.replace("v=0.5.44", f"v={TARGET_VERSION}"), encoding="utf-8")

    sw = ROOT / "static" / "sw.js"
    text = sw.read_text(encoding="utf-8")
    if "torrent-dashboard-v0544" not in text or "v=0.5.44" not in text:
        raise RuntimeError("Expected v0.5.44 service worker identifiers")
    text = text.replace("torrent-dashboard-v0544", "torrent-dashboard-v0546")
    text = text.replace("v=0.5.44", f"v={TARGET_VERSION}")
    sw.write_text(text, encoding="utf-8")

    print("Restored confirmed-stable v0.5.44 runtime as v0.5.46")


if __name__ == "__main__":
    main()
