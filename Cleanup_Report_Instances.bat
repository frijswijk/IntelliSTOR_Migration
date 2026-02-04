@echo off
REM Cleanup Report Instances
REM Windows batch wrapper for cleanup_report_instances.py

cls

REM Change to script directory
cd /d "%~dp0"

REM Load environment variables
call Migration_Environment.bat

REM Activate virtual environment
call venv\Scripts\activate.bat

REM --- Display Header ---
echo ========================================================================
echo IntelliSTOR Database Cleanup Tool
echo ========================================================================
echo Database: %SQL_SG_Database%
echo Server: %SQLServer%
echo ========================================================================
echo.

REM --- Get date range from user ---
echo This script will DELETE report instances and associated data.
echo You can specify a date range to delete instances.
echo.
echo Options:
echo   1) Delete up to a specific date (from beginning)
echo   2) Delete from a specific date onwards (e.g., future test data)
echo   3) Delete within a specific date range
echo.
set /p DATE_CHOICE="Enter choice [1, 2, or 3]: "

set START_DATE=
set END_DATE=

if "%DATE_CHOICE%"=="1" (
    echo.
    echo Delete all instances from the beginning up to (and including) a date.
    set /p END_DATE="Enter the end date (YYYY-MM-DD) or press Enter to cancel: "

    if "%END_DATE%"=="" (
        echo.
        echo Operation cancelled.
        echo.
        pause
        exit /b 0
    )
) else if "%DATE_CHOICE%"=="2" (
    echo.
    echo Delete all instances from a start date onwards (useful for test data).
    set /p START_DATE="Enter the start date (YYYY-MM-DD) or press Enter to cancel: "

    if "%START_DATE%"=="" (
        echo.
        echo Operation cancelled.
        echo.
        pause
        exit /b 0
    )
) else if "%DATE_CHOICE%"=="3" (
    echo.
    echo Delete all instances within a specific date range.
    set /p START_DATE="Enter the start date (YYYY-MM-DD) or press Enter to cancel: "

    if "%START_DATE%"=="" (
        echo.
        echo Operation cancelled.
        echo.
        pause
        exit /b 0
    )

    set /p END_DATE="Enter the end date (YYYY-MM-DD) or press Enter to cancel: "

    if "%END_DATE%"=="" (
        echo.
        echo Operation cancelled.
        echo.
        pause
        exit /b 0
    )
) else (
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
    echo WARNING: This will PERMANENTLY delete data!
) else (
    echo.
    echo Invalid choice. Operation cancelled.
    echo.
    pause
    exit /b 0
)

REM --- Capture Start Time ---
set START_TIME=%date% %time%
set LOG_FILE=Cleanup_Report_Instances_LOG.txt

echo.
echo ========================================================================
echo Cleanup started at: %START_TIME%
echo ========================================================================
echo.

REM Build the command with appropriate arguments
set CMD_ARGS=%DRY_RUN%
if not "%START_DATE%"=="" set CMD_ARGS=%CMD_ARGS% --start-date %START_DATE%
if not "%END_DATE%"=="" set CMD_ARGS=%CMD_ARGS% --end-date %END_DATE%

REM Run the cleanup script
python cleanup_report_instances.py %CMD_ARGS%

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

set DATE_RANGE=
if not "%START_DATE%"=="" if not "%END_DATE%"=="" (
    set DATE_RANGE=Range: %START_DATE% to %END_DATE%
) else if not "%START_DATE%"=="" (
    set DATE_RANGE=From: %START_DATE%
) else if not "%END_DATE%"=="" (
    set DATE_RANGE=Up to: %END_DATE%
)

if %SCRIPT_EXIT_CODE% EQU 0 (
    echo [%START_TIME%] DB: %SQL_SG_Database% ^| %DATE_RANGE% ^| Mode: %MODE% ^| Status: SUCCESS >> %LOG_FILE%
    echo.
    echo Log updated in %LOG_FILE%
) else (
    echo [%START_TIME%] DB: %SQL_SG_Database% ^| %DATE_RANGE% ^| Status: FAILED >> %LOG_FILE%
    echo.
    echo ERROR: Script failed. Check log in %LOG_FILE%
)

echo.
pause
