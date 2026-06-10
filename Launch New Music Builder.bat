@echo off
setlocal
cd /d "%~dp0"
pythonw.exe "%~dp0main.py"
if errorlevel 1 (
  echo New Music Builder failed to start.
  echo Check logs\startup_fatal.log
  pause
)