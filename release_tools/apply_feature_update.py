#!/usr/bin/env python3
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
path=ROOT/'dashboard.py'
text=path.read_text(encoding='utf-8')
old='''def installed_release_info():
    try:
        raw=json.loads(RELEASE_INFO_PATH.read_text(encoding="utf-8"))
        info=_release_info_payload(
            raw.get("version"),raw.get("package"),raw.get("sha256"),raw.get("repository"),
            raw.get("releaseUrl"),raw.get("publishedAt"),raw.get("channel"),raw.get("commit"),
        )
        if info.get("version") != VERSION:
            return {}
        return info
    except Exception:
        return {}
'''
new='''def installed_release_info():
    try:
        raw=json.loads(RELEASE_INFO_PATH.read_text(encoding="utf-8"))
        info=_release_info_payload(
            raw.get("version"),raw.get("package"),raw.get("sha256"),raw.get("repository"),
            raw.get("releaseUrl"),raw.get("publishedAt"),raw.get("channel"),raw.get("commit"),
        )
        if info.get("version") == VERSION:
            return info
    except Exception:
        pass
    # The first update that introduces release-info.json is installed by the
    # previous version's updater. That updater leaves the already verified ZIP
    # under data/updates/<version>/, so recover the exact package digest from
    # those retained bytes and persist it for all subsequent reads.
    try:
        package=UPDATE_DIR/VERSION/f"Torrent-Dashboard-{VERSION}.zip"
        if package.is_file():
            info=_release_info_payload(VERSION,package.name,sha256_file(package))
            return write_release_info(RELEASE_INFO_PATH,info)
    except Exception:
        pass
    return {}
'''
if old not in text:
    raise SystemExit('installed_release_info anchor not found')
text=text.replace(old,new,1)
path.write_text(text,encoding='utf-8')
assert 'package=UPDATE_DIR/VERSION/f"Torrent-Dashboard-{VERSION}.zip"' in text
print('Applied v0.5.60 release-info bootstrap fallback')
