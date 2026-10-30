@echo off
setlocal
title AeroNet MSFS Bridge - Install dependencies
cd /d "%~dp0"

where py >nul 2>&1
if errorlevel 1 (
    echo Python Launcher was not found.
    echo Install 64-bit Python 3.11 from https://www.python.org/downloads/windows/
    echo Make sure "Python Launcher" and "Add Python to PATH" are enabled.
    pause
    exit /b 1
)

py -3.11 -c "import sys,struct; print('Python:',sys.version); print('Architecture:',struct.calcsize('P')*8,'bit'); sys.exit(0 if struct.calcsize('P')*8==64 else 1)"
if errorlevel 1 (
    echo AeroNet requires 64-bit Python.
    pause
    exit /b 1
)

py -3.11 -m pip install --upgrade pip
if errorlevel 1 goto failed

py -3.11 -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 goto failed

echo.
echo Dependencies installed successfully.
echo You can now start the simulator bridge with start.bat.
pause
exit /b 0

:failed
echo.
echo Dependency installation failed. Check the error above.
pause
exit /b 1
