:: SPDX-License-Identifier: GPL-3.0-or-later
@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
title ZeroScript App Launcher
cd /d "%~dp0"

if not exist "%~dp0app.py" (
    echo   ERROR: app.py not found next to start_app.bat.
    pause
    exit /b 1
)

set "PY="
where py >nul 2>nul && set "PY=py -3"
call :validate_py && goto :found
set "PY=python"
call :validate_py && goto :found

for %%R in ("%LOCALAPPDATA%\Programs\Python" "%ProgramFiles%" "%ProgramFiles(x86)%") do (
    if exist "%%~R" (
        for /f "delims=" %%D in ('dir /b /ad /o-n "%%~R\Python3*" 2^>nul') do (
            if exist "%%~R\%%D\python.exe" (
                set PY="%%~R\%%D\python.exe"
                call :validate_py && goto :found
            )
        )
    )
)

echo   Python 3.9+ not found. Launching start.bat setup...
call "%~dp0start.bat"
exit /b %errorlevel%

:found
%PY% -c "import websockets" >nul 2>nul
if errorlevel 1 (
    echo   Installing websockets...
    %PY% -m pip install --user websockets
)

for /f "delims=" %%W in ('call %PY% -c "import os, sys; w=os.path.join(os.path.dirname(sys.executable), 'pythonw.exe'); print(w if os.path.isfile(w) else sys.executable)"') do set "PYW=%%W"

start "" "%PYW%" "%~dp0app.py"
exit /b 0

:validate_py
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >nul 2>nul
exit /b %errorlevel%

