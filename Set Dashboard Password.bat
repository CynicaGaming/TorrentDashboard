@echo off
setlocal
cd /d "%~dp0"
set /p TDPASS=New dashboard password: 
py dashboard.py --set-password --password "%TDPASS%"
endlocal
