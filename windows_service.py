#!/usr/bin/env python3
"""Optional Windows Service wrapper. Requires pywin32."""
import subprocess, sys
from pathlib import Path
try:
    import win32event, win32service, win32serviceutil
except ImportError:
    raise SystemExit("Install pywin32: py -m pip install pywin32")
ROOT=Path(__file__).resolve().parent
class TorrentDeskService(win32serviceutil.ServiceFramework):
    _svc_name_='TorrentDesk';_svc_display_name_='Torrent Desk'
    def __init__(self,args):super().__init__(args);self.stop_event=win32event.CreateEvent(None,0,0,None);self.proc=None
    def SvcStop(self):self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING);win32event.SetEvent(self.stop_event);self.proc and self.proc.terminate()
    def SvcDoRun(self):
        self.proc=subprocess.Popen([sys.executable,str(ROOT/'dashboard.py'),'--no-browser'],cwd=ROOT)
        win32event.WaitForSingleObject(self.stop_event,win32event.INFINITE)
if __name__=='__main__':win32serviceutil.HandleCommandLine(TorrentDeskService)
