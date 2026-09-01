#!/usr/bin/env python3
"""Optional Windows tray launcher. Requires pystray + Pillow."""
import subprocess, sys, threading, time, webbrowser
from pathlib import Path
try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    raise SystemExit("Install pystray and pillow: py -m pip install pystray pillow")
ROOT=Path(__file__).resolve().parent
proc=None
def start():
    global proc
    if proc is None or proc.poll() is not None: proc=subprocess.Popen([sys.executable,str(ROOT/'dashboard.py'),'--no-browser'],cwd=ROOT)
def stop():
    global proc
    if proc and proc.poll() is None: proc.terminate();proc=None
def quit_app(icon,item):stop();icon.stop()
def icon_img():
    im=Image.new('RGB',(64,64),(16,22,28));d=ImageDraw.Draw(im);d.text((20,15),'T',fill='white');return im
start()
icon=pystray.Icon('TorrentDesk',icon_img(),'Torrent Desk',pystray.Menu(pystray.MenuItem('Open',lambda: webbrowser.open('http://127.0.0.1:8765')),pystray.MenuItem('Restart',lambda:(stop(),start())),pystray.MenuItem('Quit',quit_app)))
icon.run()
