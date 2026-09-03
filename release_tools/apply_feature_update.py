#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def write(path, text):
    (ROOT / path).write_text(text, encoding='utf-8')


def replace(path, old, new):
    text = read(path)
    if old not in text:
        raise RuntimeError(f'Expected source fragment not found in {path}: {old[:180]!r}')
    write(path, text.replace(old, new, 1))


replace(
    'static/app.js',
    'function applyTorrentColumnWidth(key,width=null){const valid=Number.isFinite(Number(width)),value=valid?`${Math.round(Number(width))}px`:\'\';document.querySelectorAll(`#torrentTable [data-col="${key}"]`).forEach(cell=>{cell.style.width=value;cell.style.minWidth=value;cell.style.maxWidth=value})}',
    'function applyTorrentColumnWidth(key,width=null){const valid=width!==null&&width!==undefined&&Number.isFinite(Number(width)),value=valid?`${Math.round(Number(width))}px`:\'\';document.querySelectorAll(`#torrentTable [data-col="${key}"]`).forEach(cell=>{cell.style.width=value;cell.style.minWidth=value;cell.style.maxWidth=value;cell.classList.toggle(\'torrent-column-sized\',valid)})}',
)

css = read('static/app.css')
css += '''\n#torrentTable td.torrent-column-sized[data-col="name"] .torrent-name{max-width:none}\n#torrentTable td.torrent-column-sized .torrent-column-text{max-width:none}\n'''
write('static/app.css', css)

replace(
    'release_tools/validate_ui_strings.py',
    "    assert '.column-resize-handle{' in app_css and 'body.torrent-column-resizing' in app_css\n",
    "    assert '.column-resize-handle{' in app_css and 'body.torrent-column-resizing' in app_css\n    assert \"cell.classList.toggle('torrent-column-sized',valid)\" in app_js and '.torrent-column-sized .torrent-column-text{max-width:none}' in app_css\n",
)

print('Polished v0.5.87 resized column content')
