@echo off
setlocal
title AeroNet MSFS 2020 Telemetry Bridge
cd /d "%~dp0"

where py >nul 2>&1
if errorlevel 1 (
    echo Python Launcher was not found. Run install-deps.bat first.
    pause
    exit /b 1
)

py -3.11 -u "%~dp0plugin.py"
if errorlevel 1 (
    echo.
    echo AeroNet bridge exited with an error.
    pause
)
