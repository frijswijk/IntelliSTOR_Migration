@echo off
REM Quick script to delete future test instances (2026 onwards)

cls

cd /d "%~dp0"

REM Load environment
call Migration_Environment.bat
call venv\Scripts\activate.bat

echo ========================================================================
echo DELETE FUTURE TEST INSTANCES (2026 onwards)
echo ========================================================================
echo Database: %SQL_SG_Database%
echo Server: %SQLServer%
echo ========================================================================
echo.
echo This will delete ALL instances from 2026-01-01 onwards.
echo.
echo WARNING: This is NOT a dry-run - this will ACTUALLY DELETE data!
echo.
set /p CONFIRM="Type exactly 'DELETE' (without quotes) to proceed, or press Enter to cancel: "

if not "%CONFIRM%"=="DELETE" (
    echo.
    echo Operation cancelled (you typed: '%CONFIRM%')
    echo   You must type exactly: DELETE
    echo.
    pause
    exit /b 0
)

echo.
echo ========================================================================
echo Starting deletion process...
echo ========================================================================

REM Run the cleanup script WITHOUT --dry-run flag, with skip-orphan-check for speed
python cleanup_report_instances.py --start-date 2026-01-01 --skip-orphan-check

set EXIT_CODE=%ERRORLEVEL%

echo.
if %EXIT_CODE% EQU 0 (
    echo Deletion completed successfully
) else (
    echo Deletion failed with exit code: %EXIT_CODE%
)

echo.
pause
