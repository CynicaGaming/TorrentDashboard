@echo off
setlocal
cd /d "%~dp0"

if /i "%~1"=="update" goto :update

goto :start

:runpython
where py >nul 2>nul
if %errorlevel%==0 (
  py %*
  exit /b %errorlevel%
)
where python >nul 2>nul
if %errorlevel%==0 (
  python %*
  exit /b %errorlevel%
)
echo Python 3 was not found. Install Python 3 and try again.
exit /b 9009

:start
call :runpython dashboard.py
if not %errorlevel%==0 pause
goto :end

:update
echo Torrent Dashboard Recovery Update
echo.
echo The dashboard must be stopped before recovery updating.
echo This does not require the web interface.
echo.
call :runpython updater.py --github-update
pause
goto :end

:end
endlocal
