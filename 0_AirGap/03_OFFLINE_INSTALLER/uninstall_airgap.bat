@echo off
REM ============================================================================
REM IntelliSTOR Air-Gap Python Uninstaller
REM ============================================================================
REM
REM This script removes the air-gap Python installation and optionally
REM restores original batch files from backups.
REM
REM Usage:
REM   uninstall_airgap.bat [python_dir]
REM
REM Example:
REM   uninstall_airgap.bat
REM   uninstall_airgap.bat C:\IntelliSTOR_Python
REM
REM ============================================================================

setlocal enabledelayedexpansion

echo ============================================================================
echo IntelliSTOR Air-Gap Python Uninstaller
echo ============================================================================
echo.

REM Get script directory
set "SCRIPT_DIR=%~dp0"
set "PACKAGE_ROOT=%SCRIPT_DIR%.."
set "SOURCE_DIR=%PACKAGE_ROOT%\08_SOURCE_CODE\IntelliSTOR_Migration"

REM Python installation path
set "INSTALL_PATH=%~1"
if "%INSTALL_PATH%"=="" (
    set "INSTALL_PATH=%PACKAGE_ROOT%\IntelliSTOR_Python"
)

echo Configuration:
echo   Python Installation: %INSTALL_PATH%
echo   Source Directory: %SOURCE_DIR%
echo.

REM ============================================================================
REM Warning
REM ============================================================================

echo WARNING: This will remove the air-gap Python installation.
echo.
echo The following will be deleted:
echo   - Python installation directory: %INSTALL_PATH%
echo.
echo The following will be optionally restored:
echo   - Batch files from .backup copies (if available)
echo   - Migration_Environment.bat from backup
echo.

choice /C YN /M "Do you want to proceed with uninstallation"
if errorlevel 2 goto :cancel
if errorlevel 1 goto :uninstall

:cancel
echo.
echo Uninstallation cancelled by user.
pause
exit /b 0

:uninstall
echo.

REM ============================================================================
REM Step 1: Remove Python Installation
REM ============================================================================

echo ============================================================================
echo Step 1: Removing Python installation
echo ============================================================================
echo.

if exist "%INSTALL_PATH%" (
    echo Removing: %INSTALL_PATH%
    echo.

    REM Remove the directory
    rmdir /S /Q "%INSTALL_PATH%"

    if errorlevel 1 (
        echo ERROR: Failed to remove Python installation directory
        echo.
        echo Possible causes:
        echo   - Directory is in use by running Python processes
        echo   - Insufficient permissions
        echo.
        echo Please close all Python processes and try again.
        pause
        exit /b 1
    )

    echo Python installation removed successfully
) else (
    echo Python installation not found at: %INSTALL_PATH%
    echo Skipping removal.
)
echo.

REM ============================================================================
REM Step 2: Restore Batch Files (Optional)
REM ============================================================================

echo ============================================================================
echo Step 2: Restore batch files from backups
echo ============================================================================
echo.

REM Count backup files
set "BACKUP_COUNT=0"
if exist "%SOURCE_DIR%" (
    for /r "%SOURCE_DIR%" %%F in (*.bat.backup) do set /a BACKUP_COUNT+=1
)

if %BACKUP_COUNT% GTR 0 (
    echo Found %BACKUP_COUNT% backup files
    echo.
    choice /C YN /M "Do you want to restore batch files from backups"

    if not errorlevel 2 (
        REM User chose Yes
        echo.
        echo Restoring batch files...
        echo.

        set "RESTORED=0"
        set "FAILED=0"

        for /r "%SOURCE_DIR%" %%F in (*.bat.backup) do (
            set "BACKUP_FILE=%%F"
            set "ORIGINAL_FILE=%%~dpnF"

            copy /Y "!BACKUP_FILE!" "!ORIGINAL_FILE!" >nul 2>&1
            if errorlevel 1 (
                echo   Failed: !ORIGINAL_FILE!
                set /a FAILED+=1
            ) else (
                echo   Restored: !ORIGINAL_FILE!
                set /a RESTORED+=1
            )
        )

        echo.
        echo Restored !RESTORED! files
        if !FAILED! GTR 0 (
            echo Failed to restore !FAILED! files
        )
    ) else (
        echo Skipping batch file restoration
    )
) else (
    echo No backup files found
    echo Skipping batch file restoration
)
echo.

REM ============================================================================
REM Step 3: Restore Migration_Environment.bat (Optional)
REM ============================================================================

echo ============================================================================
echo Step 3: Restore Migration_Environment.bat
echo ============================================================================
echo.

if exist "%SOURCE_DIR%\Migration_Environment.bat.backup" (
    echo Found Migration_Environment.bat backup
    echo.
    choice /C YN /M "Do you want to restore Migration_Environment.bat from backup"

    if not errorlevel 2 (
        REM User chose Yes
        copy /Y "%SOURCE_DIR%\Migration_Environment.bat.backup" "%SOURCE_DIR%\Migration_Environment.bat" >nul

        if errorlevel 1 (
            echo Failed to restore Migration_Environment.bat
        ) else (
            echo Migration_Environment.bat restored successfully
        )
    ) else (
        echo Skipping Migration_Environment.bat restoration
    )
) else (
    echo No backup found for Migration_Environment.bat
    echo.
    echo To manually remove air-gap configuration, edit Migration_Environment.bat
    echo and delete the AIRGAP_PYTHON line:
    echo   SET "AIRGAP_PYTHON=..."
)
echo.

REM ============================================================================
REM Step 4: Clean Up Backup Files (Optional)
REM ============================================================================

echo ============================================================================
echo Step 4: Clean up backup files
echo ============================================================================
echo.

if %BACKUP_COUNT% GTR 0 (
    choice /C YN /M "Do you want to delete backup files (.bat.backup)"

    if not errorlevel 2 (
        REM User chose Yes
        echo.
        echo Deleting backup files...

        set "DELETED=0"
        for /r "%SOURCE_DIR%" %%F in (*.bat.backup) do (
            del "%%F" >nul 2>&1
            if not errorlevel 1 (
                set /a DELETED+=1
            )
        )

        echo Deleted !DELETED! backup files
    ) else (
        echo Backup files preserved
    )
) else (
    echo No backup files to clean up
)
echo.

REM ============================================================================
REM Completion
REM ============================================================================

echo ============================================================================
echo UNINSTALLATION COMPLETE
echo ============================================================================
echo.
echo The air-gap Python installation has been removed.
echo.

if %BACKUP_COUNT% GTR 0 (
    echo Batch files have been restored from backups (if selected).
)

echo.
echo To reinstall, run:
echo   03_OFFLINE_INSTALLER\install_airgap_python.bat
echo.
pause
exit /b 0
