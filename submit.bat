@echo off
REM Build the submission end to end: check the prediction files, then package them.
REM
REM Stops at the first failure on purpose. A CSV that does not match the schema is
REM scored as-is by the organisers, so it must never reach predictions.zip.
REM
REM Pass --team "Your Name" to set the top-level folder name.
setlocal
cd /d "%~dp0"

echo == 1/2  validating prediction files ==
call scripts\validate.bat || exit /b 1

echo.
echo == 2/2  packaging the submission ==
call scripts\package.bat %*
exit /b %errorlevel%
