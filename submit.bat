@echo off
REM Build the submission end to end: ask who we are, check the prediction files,
REM then package them into outputs\submission\<team>\.
REM
REM Stops if validation fails. A CSV that does not match the schema is scored
REM as-is by the organisers, so it must never reach predictions.zip. Anything
REM else that is missing, the demo video included, is reported and skipped.
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

echo == 1/2  validating prediction files ==
call scripts\validate.bat || exit /b 1

echo.
echo == 2/2  packaging the submission ==
call scripts\package.bat !TEAM_ARGS! %*
exit /b %errorlevel%
