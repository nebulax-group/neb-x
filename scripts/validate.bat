@echo off
REM Thin wrapper: check the prediction CSVs, creating or refreshing .venv first.
REM See src\submission\validate.py.
setlocal
cd /d "%~dp0.."

if not exist ".venv" (
    echo no .venv yet -- running install.bat
    call install.bat || exit /b 1
)

set "VENV_PY=.venv\Scripts\python.exe"
set "STAMP=.venv\.requirements-sha"

for /f %%H in ('"%VENV_PY%" -c "import hashlib, pathlib; print(hashlib.sha256(pathlib.Path('requirements.txt').read_bytes()).hexdigest())"') do set "WANT=%%H"
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
>"%STAMP%" echo|set /p="%WANT%"

:run
echo.
REM No arguments sweeps every subsystem and skips the ones nobody has produced yet;
REM a path checks that one file. The module decides, not this script.
"%VENV_PY%" -m src.submission.validate %*
exit /b %errorlevel%
