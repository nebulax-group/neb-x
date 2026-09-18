@echo off
REM Bootstrap the one virtualenv for neb-x. Safe to re-run.
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if %errorlevel%==0 (set "PY=py -3") else (set "PY=python")

%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)" 2>nul
if errorlevel 1 (
    echo error: Python 3.12+ required, and none was found on PATH.
    echo        Install it from https://www.python.org/downloads/ and re-run.
    goto :fail
)

if not exist ".venv\" (
    echo creating .venv ...
    %PY% -m venv .venv
    if errorlevel 1 goto :fail
) else (
    echo .venv already exists, reusing it
)

REM Call the venv interpreter directly: activating here would not survive back to the caller.
set "VENV_PY=.venv\Scripts\python.exe"

"%VENV_PY%" -m pip install --upgrade pip --quiet
if errorlevel 1 goto :fail

"%VENV_PY%" -m pip install -r requirements.txt
if errorlevel 1 goto :fail

"%VENV_PY%" -c "import importlib; [print('  ok   ', n, getattr(importlib.import_module(n), '__version__', '?')) for n in ('numpy','scipy','pandas','openpyxl','sklearn','streamlit')]"
if errorlevel 1 (
    echo error: packages installed but at least one will not import.
    goto :fail
)

echo.
echo Done. Activate it in your shell with:
echo     .venv\Scripts\activate
goto :eof

:fail
echo.
echo INSTALL FAILED
exit /b 1
