@echo off
rem Start the Train Condition Monitoring app. Creates .venv on the first run.
rem The Windows twin of run.sh; see that file for what ships beside it.
setlocal
cd /d "%~dp0"

if not exist .venv (
    echo creating .venv ^(first run only^) ...
    python -m venv .venv || exit /b 1
    .venv\Scripts\python.exe -m pip install --upgrade pip --quiet || exit /b 1
    echo installing requirements ...
    .venv\Scripts\python.exe -m pip install -r requirements.txt --quiet || exit /b 1
)

echo starting the app -- press Ctrl+C to stop
.venv\Scripts\python.exe -m streamlit run src\app\main.py %*
