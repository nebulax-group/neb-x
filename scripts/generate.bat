@echo off
REM Thin wrapper: write every prediction CSV, creating or refreshing .venv first.
REM See src\submission\generate.py.
setlocal
cd /d "%~dp0.."

if not exist ".venv" (
    echo no .venv yet -- running install.bat
    call install.bat || exit /b 1
)

set "VENV_PY=.venv\Scripts\python.exe"
set "STAMP=.venv\.requirements-sha"

REM %VENV_PY% is unquoted deliberately: cmd cannot parse a quoted path inside a
REM for /f command string, and the relative path it holds has no spaces in it.
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
REM Parenthesised so the redirect lands on set /p rather than on echo, which
REM otherwise writes "ECHO is on." to the stamp and the hash to the screen.
(echo|set /p="%WANT%")>"%STAMP%"

:run
echo.
REM Takes no arguments: a partial run would leave one subsystem's CSV older than the
REM rest, which is the state this step exists to make impossible. The module decides.
"%VENV_PY%" -m src.submission.generate
exit /b %errorlevel%
