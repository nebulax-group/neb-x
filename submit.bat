@echo off
REM Build the submission end to end: ask who we are, run every subsystem over its
REM held-out test inputs, check what comes out, then package it into
REM submission\<team>\.
REM
REM The prediction CSVs are always regenerated here and never reused. A file left in
REM outputs\predictions\ by an earlier run or a browser download is stale by
REM definition, so it is overwritten, and one whose subsystem could not run at all is
REM discarded rather than submitted.
REM
REM The demo video comes from video\out\, where scripts\render.bat leaves it, and
REM falls back to any recording dropped in video\.
REM
REM Stops if validation fails. A CSV that does not match the schema is scored
REM as-is by the organisers, so it must never reach predictions.zip. Anything
REM else that is missing, an unfinished subsystem and the demo video included, is
REM reported and skipped.
REM
REM Pass --team "Your Name" to skip the prompt.
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "TEAM_ARGS="
echo %* | find "--team" >nul
if errorlevel 1 (
    REM The folder must carry the registered name exactly; it is how the
    REM organisers identify the submission, so it is asked for rather than guessed.
    set /p "TEAM=Team name, exactly as registered: "
    if defined TEAM (
        set "TEAM_ARGS=--team "!TEAM!""
    ) else (
        echo no name given, falling back to the placeholder
    )
    echo.
)

echo == 1/3  generating prediction files ==
call scripts\generate.bat || exit /b 1

echo.
echo == 2/3  validating prediction files ==
call scripts\validate.bat || exit /b 1

echo.
echo == 3/3  packaging the submission ==
call scripts\package.bat !TEAM_ARGS! %*
exit /b %errorlevel%
