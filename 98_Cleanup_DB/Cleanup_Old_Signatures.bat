@echo off
REM Cleanup Old Signature Versions
REM Windows batch wrapper for cleanup_old_signatures.py

cls

REM Change to project root (scripts live in 98_Cleanup_DB subfolder)
cd /d "%~dp0\.."

REM Load environment variables
call Migration_Environment.bat

REM Activate virtual environment
call venv\Scripts\activate.bat

REM --- Display Header ---
echo ========================================================================
echo IntelliSTOR Signature Cleanup Tool
echo ========================================================================
echo Database: %SQL_SG_Database%
echo Server: %SQLServer%
echo ========================================================================
echo.

REM --- Explain what will happen ---
echo This script will DELETE old signature versions, keeping only the latest
echo version of each signature.
echo.
echo What will be cleaned:
echo   - Old SIGNATURE versions (keeps latest per species/sign)
echo   - Related SENSITIVE_FIELD records
echo   - Related LINES_IN_SIGN records
echo.
echo What will NOT be affected:
echo   - Latest signature versions (preserved)
echo   - SIGN_GEN_INFO (not version-specific)
echo   - Report instances (don't link to signatures)
echo.

REM --- Ask for scope ---
echo Choose scope:
echo   1) Clean all domains (recommended)
echo   2) Clean specific domain only
echo.
set /p SCOPE_CHOICE="Enter choice [1 or 2]: "

set DOMAIN_ARG=

if "%SCOPE_CHOICE%"=="2" (
    echo.
    set /p DOMAIN_ID="Enter domain ID (usually 1): "

    if "%DOMAIN_ID%"=="" (
        echo.
        echo Invalid domain ID. Operation cancelled.
        echo.
        pause
        exit /b 0
    )

    set DOMAIN_ARG=--domain-id %DOMAIN_ID%
) else if not "%SCOPE_CHOICE%"=="1" (
    echo.
    echo Invalid choice. Operation cancelled.
    echo.
    pause
    exit /b 0
)

REM --- Ask for dry run or actual deletion ---
echo.
echo Choose an option:
echo   1) Dry run (show what would be deleted, no actual deletion)
echo   2) Actually delete data (PERMANENT)
echo.
set /p CHOICE="Enter choice [1 or 2]: "

set DRY_RUN=
if "%CHOICE%"=="1" (
    set DRY_RUN=--dry-run
    echo.
    echo Running in DRY RUN mode...
) else if "%CHOICE%"=="2" (
    set DRY_RUN=
    echo.
    echo WARNING: This will PERMANENTLY delete old signature versions!
) else (
    echo.
    echo Invalid choice. Operation cancelled.
    echo.
    pause
    exit /b 0
)

REM --- Capture Start Time ---
set START_TIME=%date% %time%
set LOG_FILE=Cleanup_Old_Signatures_LOG.txt

echo.
echo ========================================================================
echo Cleanup started at: %START_TIME%
echo ========================================================================
echo.

REM Run the cleanup script
python cleanup_old_signatures.py %DOMAIN_ARG% %DRY_RUN%

set SCRIPT_EXIT_CODE=%ERRORLEVEL%

REM --- Capture End Time ---
echo.
echo ========================================================================
set END_TIME=%date% %time%
echo Script finished at: %END_TIME%
echo ========================================================================

REM --- Logging Section ---
set MODE=DRY_RUN
if "%DRY_RUN%"=="" set MODE=DELETED

set SCOPE=All domains
if not "%DOMAIN_ID%"=="" set SCOPE=Domain %DOMAIN_ID%

if %SCRIPT_EXIT_CODE% EQU 0 (
    echo [%START_TIME%] DB: %SQL_SG_Database% ^| %SCOPE% ^| Mode: %MODE% ^| Status: SUCCESS >> %LOG_FILE%
    echo.
    echo Log updated in %LOG_FILE%
) else (
    echo [%START_TIME%] DB: %SQL_SG_Database% ^| %SCOPE% ^| Status: FAILED >> %LOG_FILE%
    echo.
    echo ERROR: Script failed. Check log in %LOG_FILE%
)

echo.
pause
