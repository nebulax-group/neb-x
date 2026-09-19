@echo off
REM Thin wrapper: fit every subsystem that has a trainer, in one pass.
REM
REM One run leaves outputs\models\ complete, which is what submit.bat assumes and
REM does not do for itself. Each subsystem runs as its own process, so one whose
REM data is absent on this machine costs only itself and the rest still fit.
REM
REM Takes no arguments on purpose: --refresh means something to rail and is an error
REM everywhere else. The per-subsystem wrappers are where their own flags go.
REM Expect rail to dominate the wall clock: ~60 s against a warm feature cache under
REM outputs\models\rail\, ~390 s the first time on a machine, when it extracts one.
setlocal enabledelayedexpansion
cd /d "%~dp0.."

if not exist ".venv" (
    echo no .venv yet -- running scripts\install.bat
    call scripts\install.bat || exit /b 1
)

set "VENV_PY=.venv\Scripts\python.exe"
set "STAMP=.venv\.requirements-sha"

for /f "delims=" %%H in ('%VENV_PY% -c "import hashlib, pathlib; print(hashlib.sha256(pathlib.Path('scripts/requirements.txt').read_bytes()).hexdigest())"') do set "WANT=%%H"
set "HAVE="
if exist "%STAMP%" set /p HAVE=<"%STAMP%"

REM Reinstall when requirements.txt has moved since the last run, so a teammate adding a
REM dependency does not leave everyone else on a stale venv that fails at import time.
"%VENV_PY%" -c "import sklearn, joblib, pandas, numpy" >nul 2>&1
if errorlevel 1 goto install
if not "%WANT%"=="%HAVE%" goto install
echo requirements already satisfied
goto run

:install
echo installing requirements ...
"%VENV_PY%" -m pip install -r scripts\requirements.txt --quiet || exit /b 1
>"%STAMP%" echo|set /p="%WANT%"

:run
REM Asked for rather than restated here: config owns which subsystems exist, and one
REM is trainable exactly when it ships a train.py -- the same way the app decides what
REM it can predict. A new subsystem joins this run by existing.
for /f "delims=" %%S in ('%VENV_PY% -c "from src.common.config import SUBSYSTEMS; print(*SUBSYSTEMS)"') do set "SUBSYSTEMS=%%S"
REM An empty list would train nothing and say so in a summary that reads like success,
REM which is the one outcome this script must never produce quietly.
if not defined SUBSYSTEMS (
    echo error: no subsystems to train; src\common\config.py listed none
    exit /b 1
)

set "TRAINED="
set "UNTRAINED="
set "FAILED="

for %%S in (%SUBSYSTEMS%) do (
    if not exist "src\%%S\train.py" (
        set "UNTRAINED=!UNTRAINED! %%S"
    ) else (
        echo.
        echo == %%S ==
        "%VENV_PY%" -m src.%%S.train
        if errorlevel 1 (set "FAILED=!FAILED! %%S") else (set "TRAINED=!TRAINED! %%S")
    )
)

echo.
if defined TRAINED echo trained:!TRAINED!
REM ACV is the one that lands here: its ranking fits no parameters, so it has nothing
REM to train and is ready to predict without this step.
if defined UNTRAINED echo no trainer, nothing to fit:!UNTRAINED!
if defined FAILED (
    echo failed:!FAILED!
    exit /b 1
)
exit /b 0
