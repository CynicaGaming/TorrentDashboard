@echo off
setlocal
cd /d "%~dp0"
py -m pip install pyinstaller
py -m PyInstaller --onefile --name TorrentDesk dashboard.py
pause
