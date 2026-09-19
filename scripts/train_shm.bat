@echo off
REM Thin wrapper: fit the SHM fatigue curve, creating or refreshing .venv first.
REM See src\shm\train.py.
setlocal
cd /d "%~dp0.."

if not exist ".venv" (
    echo no .venv yet -- running install.bat
    call install.bat || exit /b 1
)

set "VENV_PY=.venv\Scripts\python.exe"
set "STAMP=.venv\.requirements-sha"

REM The path is left unquoted: cmd cannot parse a quoted path inside a for /f
REM command string, and the relative path it holds has no spaces in it.
for /f "delims=" %%H in ('%VENV_PY% -c "import hashlib, pathlib; print(hashlib.sha256(pathlib.Path('requirements.txt').read_bytes()).hexdigest())"') do set "WANT=%%H"
set "HAVE="
if exist "%STAMP%" set /p HAVE=<"%STAMP%"

REM Reinstall when requirements.txt has moved since the last run, so a teammate adding a
REM dependency does not leave everyone else on a stale venv that fails at import time.
"%VENV_PY%" -c "import pandas, numpy" >nul 2>&1
if errorlevel 1 goto install
if not "%WANT%"=="%HAVE%" goto install
echo requirements already satisfied
goto run

:install
echo installing requirements ...
"%VENV_PY%" -m pip install -r requirements.txt --quiet || exit /b 1
REM Parenthesised: a leading redirect binds to echo, not to set /p, and writes
REM "ECHO is on." into the stamp instead of the hash.
(echo|set /p="%WANT%")>"%STAMP%"

:run
echo.
REM Pass --output PATH through to write the checkpoint somewhere other than the default;
REM the module owns that default, not this script.
"%VENV_PY%" -m src.shm.train %*
exit /b %errorlevel%
