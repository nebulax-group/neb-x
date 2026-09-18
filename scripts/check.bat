@echo off
REM Thin wrapper: verify this machine's environment. See scripts\check_env.py.
setlocal
cd /d "%~dp0.."
".venv\Scripts\python.exe" scripts\check_env.py %*
exit /b %errorlevel%
