@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%~dp0src;%PYTHONPATH%"

if /i "%~1"=="update" goto :update

goto :start

:runpython
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 %*
  exit /b %errorlevel%
)
where python >nul 2>nul
if %errorlevel%==0 (
  python %*
  exit /b %errorlevel%
)
echo Python 3 was not found. Install Python 3 and try again.
exit /b 9009

:ensuredeps
call :runpython -c "import cryptography" >nul 2>nul
if %errorlevel%==0 exit /b 0
echo Installing Torrent Dashboard runtime dependency cryptography 50.0.1...
call :runpython -m pip install --disable-pip-version-check "cryptography==50.0.1"
exit /b %errorlevel%

:start
call :ensuredeps
if not %errorlevel%==0 (
  echo Required Python dependencies could not be installed.
  pause
  goto :end
)
call :runpython -m torrent_dashboard.runtime
if not %errorlevel%==0 pause
goto :end

:update
echo Torrent Dashboard Recovery Update
echo.
echo The dashboard must be stopped before recovery updating.
echo This does not require the web interface.
echo.
call :runpython -m torrent_dashboard.updater --github-update --target "%~dp0"
pause
goto :end

:end
endlocal
