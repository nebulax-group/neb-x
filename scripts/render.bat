@echo off
REM Thin wrapper: render the pitch video, creating or refreshing .venv first.
REM See src\video\render.py.
setlocal
cd /d "%~dp0.."

if not exist ".venv" (
    echo no .venv yet -- running install.bat
    call install.bat || exit /b 1
)

set "VENV_PY=.venv\Scripts\python.exe"
set "STAMP=.venv\.requirements-sha"
set "VIDEO_STAMP=.venv\.video-requirements-sha"

for /f %%H in ('"%VENV_PY%" -c "import hashlib, pathlib; print(hashlib.sha256(pathlib.Path('requirements.txt').read_bytes()).hexdigest())"') do set "WANT=%%H"
set "HAVE="
if exist "%STAMP%" set /p HAVE=<"%STAMP%"

REM Reinstall when requirements.txt has moved since the last run, so a teammate adding a
REM dependency does not leave everyone else on a stale venv that fails at import time.
"%VENV_PY%" -c "import pandas, numpy" >nul 2>&1
if errorlevel 1 goto install
if not "%WANT%"=="%HAVE%" goto install
echo requirements already satisfied
goto render_requirements

:install
echo installing requirements ...
"%VENV_PY%" -m pip install -r requirements.txt --quiet || exit /b 1
>"%STAMP%" echo|set /p="%WANT%"

:render_requirements
REM manim is kept out of requirements.txt on purpose: it needs cairo, pango and ffmpeg,
REM and everyone installs that file, the deployed app included. Only this script installs
REM video\requirements.txt, and only on the machine that renders.
for /f %%H in ('"%VENV_PY%" -c "import hashlib, pathlib; print(hashlib.sha256(pathlib.Path('video/requirements.txt').read_bytes()).hexdigest())"') do set "VIDEO_WANT=%%H"
set "VIDEO_HAVE="
if exist "%VIDEO_STAMP%" set /p VIDEO_HAVE=<"%VIDEO_STAMP%"

"%VENV_PY%" -c "import manim" >nul 2>&1
if errorlevel 1 goto install_render
if not "%VIDEO_WANT%"=="%VIDEO_HAVE%" goto install_render
echo render requirements already satisfied
goto ask

:install_render
echo installing the render requirements ...
"%VENV_PY%" -m pip install -r video\requirements.txt --quiet || exit /b 1
>"%VIDEO_STAMP%" echo|set /p="%VIDEO_WANT%"

:ask
echo.
REM Arguments mean the caller has already chosen, and --help must not sit behind a prompt.
if not "%~1"=="" goto run_given

for /f "tokens=1,2" %%A in ('"%VENV_PY%" -m src.video.render --defaults') do (
    set "QUALITY=%%A"
    set "FPS=%%B"
)

set "ANSWER="
set /p "ANSWER=manim quality [%QUALITY%]: "
if defined ANSWER set "QUALITY=%ANSWER%"

set "ANSWER="
set /p "ANSWER=frames per second [%FPS%]: "
if defined ANSWER set "FPS=%ANSWER%"

echo.
REM The module decides what is rendered, in what order and how it is stitched.
"%VENV_PY%" -m src.video.render --quality "%QUALITY%" --fps "%FPS%"
exit /b %errorlevel%

:run_given
"%VENV_PY%" -m src.video.render %*
exit /b %errorlevel%
