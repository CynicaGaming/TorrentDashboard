#!/usr/bin/env python3
"""Detached Torrent Desk updater with backup, health verification and rollback."""
from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys, time, urllib.request
from pathlib import Path

PRESERVE_TOP={"config.json","data",".git","dist","__pycache__"}

def wait_pid(pid,timeout=45):
    until=time.time()+timeout
    while time.time()<until:
        try:
            if os.name=="nt":
                cp=subprocess.run(["tasklist","/FI",f"PID eq {pid}"],capture_output=True,text=True,timeout=3)
                alive=str(pid) in cp.stdout
            else:
                os.kill(pid,0);alive=True
        except Exception: alive=False
        if not alive:return
        time.sleep(.4)
    raise RuntimeError("Torrent Desk did not stop in time")

def app_files(root):
    for p in root.rglob("*"):
        if not p.is_file():continue
        rel=p.relative_to(root)
        if rel.parts[0] in PRESERVE_TOP or "__pycache__" in rel.parts or p.suffix==".pyc":continue
        yield p,rel

def copy_overlay(source,target,backup):
    backup.mkdir(parents=True,exist_ok=True)
    for p,rel in app_files(source):
        dst=target/rel
        if dst.exists():
            b=backup/rel;b.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dst,b)
        dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst)

def restore_backup(backup,target):
    for p in backup.rglob("*"):
        if p.is_file():
            rel=p.relative_to(backup);dst=target/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst)

def start_app(target):
    kwargs={"cwd":str(target),"stdin":subprocess.DEVNULL,"stdout":subprocess.DEVNULL,"stderr":subprocess.DEVNULL}
    if os.name=="nt":kwargs["creationflags"]=getattr(subprocess,"CREATE_NEW_PROCESS_GROUP",0)|getattr(subprocess,"DETACHED_PROCESS",0)
    else:kwargs["start_new_session"]=True
    return subprocess.Popen([sys.executable,str(target/"dashboard.py"),"--no-browser"],**kwargs)

def health(version,timeout=30):
    end=time.time()+timeout
    while time.time()<end:
        try:
            with urllib.request.urlopen("http://127.0.0.1:8765/health",timeout=2) as r:
                d=json.loads(r.read().decode())
                if str(d.get("version"))==str(version):return True
        except Exception:pass
        time.sleep(1)
    return False

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--pid",type=int,required=True);ap.add_argument("--source",required=True);ap.add_argument("--target",required=True);ap.add_argument("--version",required=True);a=ap.parse_args()
    source=Path(a.source).resolve();target=Path(a.target).resolve();data=target/"data";backup=data/"updates"/"backups"/(time.strftime("%Y%m%d-%H%M%S")+"-"+a.version);status=data/"update-status.json"
    def write(state,**extra):status.parent.mkdir(parents=True,exist_ok=True);status.write_text(json.dumps({"state":state,"version":a.version,"ts":int(time.time()),**extra},indent=2)+"\n")
    try:
        wait_pid(a.pid);write("installing",backup=str(backup));copy_overlay(source,target,backup);start_app(target)
        if health(a.version):write("installed",backup=str(backup));return
        write("rollback",error="New version failed its health check",backup=str(backup));restore_backup(backup,target);start_app(target);write("rolledBack",error="New version failed its health check; previous application files were restored",backup=str(backup))
    except Exception as e:
        try:
            if backup.exists():restore_backup(backup,target);start_app(target)
        except Exception:pass
        write("failed",error=str(e),backup=str(backup));raise
if __name__=="__main__":main()
