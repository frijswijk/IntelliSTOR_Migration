@echo off
REM Cleanup Orphaned MAP/RPT Files
REM Windows batch wrapper for cleanup_orphaned_files.py

cls

REM Change to script directory
cd /d "%~dp0"

REM Load environment variables
call Migration_Environment.bat

REM Activate virtual environment
call venv\Scripts\activate.bat

REM --- Display Header ---
echo ========================================================================
echo IntelliSTOR Orphaned Files Cleanup Tool
echo ========================================================================
echo Database: %SQL_SG_Database%
echo Server: %SQLServer%
echo ========================================================================
echo.

REM --- Explain what will happen ---
echo This script will DELETE orphaned MAP and RPT files.
echo.
echo Orphaned files are:
echo   - MAP files not referenced by any SST_STORAGE record
echo   - RPT files not referenced by any RPTFILE_INSTANCE record
echo.
echo These files are typically left behind when using --skip-orphan-check
echo during bulk instance deletions.
echo.
echo They don't cause problems but waste database space.
echo.

REM --- Ask for dry run or actual deletion ---
echo Choose an option:
echo   1) Dry run (show what would be deleted, no actual deletion)
echo   2) Actually delete orphaned files (PERMANENT)
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
    echo WARNING: This will PERMANENTLY delete orphaned files!
) else (
    echo.
    echo Invalid choice. Operation cancelled.
    echo.
    pause
    exit /b 0
)

REM --- Capture Start Time ---
set START_TIME=%date% %time%
set LOG_FILE=Cleanup_Orphaned_Files_LOG.txt

echo.
echo ========================================================================
echo Cleanup started at: %START_TIME%
echo ========================================================================
echo.

REM Run the cleanup script
python cleanup_orphaned_files.py %DRY_RUN%

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

if %SCRIPT_EXIT_CODE% EQU 0 (
    echo [%START_TIME%] DB: %SQL_SG_Database% ^| Mode: %MODE% ^| Status: SUCCESS >> %LOG_FILE%
    echo.
    echo Log updated in %LOG_FILE%
) else (
    echo [%START_TIME%] DB: %SQL_SG_Database% ^| Status: FAILED >> %LOG_FILE%
    echo.
    echo ERROR: Script failed. Check log in %LOG_FILE%
)

echo.
pause
