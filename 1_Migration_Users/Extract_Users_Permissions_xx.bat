@echo off
setlocal enabledelayedexpansion
cls

:GET_COUNTRY
set "COUNTRY_CODE=%1"
if "%COUNTRY_CODE%"=="" (
    set /p "COUNTRY_CODE=Please enter the Country Code (e.g., MY, SG): "
)

:: Terminate if still empty
if "%COUNTRY_CODE%"=="" (
    echo Error: No Country Code provided. Terminating script.
    pause
    exit /b
)

:: --- TESTDATA LOGIC ---
set "EXTRA_FLAGS="
set "TEST_PARAM=%2"

if /I "%TEST_PARAM%"=="TESTDATA" (
    set "EXTRA_FLAGS=--TESTDATA"
) else (
    echo.
    echo Would you like to include TESTDATA for %COUNTRY_CODE%?
    choice /M "Select Yes to include --TESTDATA or No to skip"
    if errorlevel 2 (
        echo Skipping Test Data...
    ) else (
        set "EXTRA_FLAGS=--TESTDATA"
    )
)
:: ----------------------

Call ..\Migration_Environment.bat

Set "DB_KEY=SQL-%COUNTRY_CODE%-Database"
Set "DB_ACTUAL_VALUE=!%DB_KEY%!"

if "!DB_ACTUAL_VALUE!"=="" (
    echo Error: Could not find a database setting for "!DB_KEY!" in Migration_Environment.bat
    pause
    exit /b
)

echo.
echo Database: !DB_ACTUAL_VALUE!
echo Flags:    --windows-auth --quiet !EXTRA_FLAGS!
echo.

python Extract_Users_Permissions.py --server %SQLServer% --database !DB_ACTUAL_VALUE! --output Users-%COUNTRY_CODE% --windows-auth --quiet !EXTRA_FLAGS!