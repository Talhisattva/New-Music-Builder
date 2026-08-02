@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_CMD="
where python >nul 2>nul && set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
  where py >nul 2>nul && set "PYTHON_CMD=py -3"
)

if not defined PYTHON_CMD (
  echo Python 3 was not found on PATH.
  echo Install Python, then try again.
  pause
  exit /b 1
)

%PYTHON_CMD% "%~dp0main.py"
if errorlevel 1 (
  echo.
  echo New Music Builder failed to start.
  echo Check logs\startup_fatal.log for details.
  pause
)
