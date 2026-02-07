@echo off
REM ============================================================================
REM IntelliSTOR Air-Gap Python Installer
REM ============================================================================
REM
REM This script installs Python and all dependencies in an air-gapped
REM environment without requiring internet access.
REM
REM Prerequisites:
REM   - Complete air-gap package transferred to this machine
REM   - No Python installation required beforehand
REM   - No admin privileges required (installs to user directory)
REM
REM What this script does:
REM   1. Extracts Python embeddable distribution
REM   2. Configures Python to use pip and site-packages
REM   3. Installs pip offline
REM   4. Installs all required packages (pymssql, ldap3, flask, etc.)
REM   5. Optionally copies Visual C++ Runtime DLLs
REM   6. Updates Migration_Environment.bat configuration
REM   7. Verifies installation
REM
REM Usage:
REM   install_airgap_python.bat [install_path]
REM
REM Example:
REM   install_airgap_python.bat
REM   install_airgap_python.bat C:\IntelliSTOR_Python
REM
REM ============================================================================

setlocal enabledelayedexpansion

echo ============================================================================
echo IntelliSTOR Air-Gap Python Installer
echo ============================================================================
echo.

REM ============================================================================
REM Configuration
REM ============================================================================

REM Get script directory (03_OFFLINE_INSTALLER)
set "SCRIPT_DIR=%~dp0"
set "PACKAGE_ROOT=%SCRIPT_DIR%.."

REM Installation path
set "INSTALL_PATH=%~1"
if "%INSTALL_PATH%"=="" (
    set "INSTALL_PATH=%PACKAGE_ROOT%\IntelliSTOR_Python"
)

REM Package directories
set "PYTHON_EMBEDDED_DIR=%PACKAGE_ROOT%\04_PYTHON_EMBEDDED"
set "WHEELS_DIR=%PACKAGE_ROOT%\05_WHEELS"
set "DLLS_DIR=%PACKAGE_ROOT%\06_DLLS"
set "SOURCE_DIR=%PACKAGE_ROOT%\08_SOURCE_CODE\IntelliSTOR_Migration"

REM Installation directories
set "PYTHON_DIR=%INSTALL_PATH%\python"
set "SCRIPTS_DIR=%PYTHON_DIR%\Scripts"

echo Configuration:
echo   Package Root: %PACKAGE_ROOT%
echo   Installation Path: %INSTALL_PATH%
echo   Python Directory: %PYTHON_DIR%
echo.

REM ============================================================================
REM Validation
REM ============================================================================

echo ============================================================================
echo Step 1: Validating package contents
echo ============================================================================
echo.

REM Check if Python embeddable exists
set "PYTHON_ZIP="
for %%F in ("%PYTHON_EMBEDDED_DIR%\python-*-embed-*.zip") do (
    set "PYTHON_ZIP=%%F"
    goto :found_python_zip
)

:found_python_zip
if "%PYTHON_ZIP%"=="" (
    echo ERROR: Python embeddable distribution not found in:
    echo   %PYTHON_EMBEDDED_DIR%
    echo.
    echo Please ensure the air-gap package is complete.
    pause
    exit /b 1
)

echo Found Python: %PYTHON_ZIP%

REM Check if get-pip.py exists
if not exist "%PYTHON_EMBEDDED_DIR%\get-pip.py" (
    echo ERROR: get-pip.py not found in:
    echo   %PYTHON_EMBEDDED_DIR%
    echo.
    echo Please ensure the air-gap package is complete.
    pause
    exit /b 1
)

echo Found get-pip.py

REM Check if wheels directory exists and has content
if not exist "%WHEELS_DIR%" (
    echo ERROR: Wheels directory not found:
    echo   %WHEELS_DIR%
    echo.
    echo Please ensure the air-gap package is complete.
    pause
    exit /b 1
)

set "WHEEL_COUNT=0"
for %%F in ("%WHEELS_DIR%\*.whl") do set /a WHEEL_COUNT+=1

if %WHEEL_COUNT%==0 (
    echo ERROR: No wheel files found in:
    echo   %WHEELS_DIR%
    echo.
    echo Please ensure the air-gap package is complete.
    pause
    exit /b 1
)

echo Found %WHEEL_COUNT% wheel files

echo.
echo Validation complete - all required files present
echo.

REM ============================================================================
REM Confirmation
REM ============================================================================

echo ============================================================================
echo Ready to Install
echo ============================================================================
echo.
echo This will install Python and dependencies to:
echo   %PYTHON_DIR%
echo.
echo Disk space required: ~150 MB
echo.
choice /C YN /M "Do you want to proceed with installation"
if errorlevel 2 goto :cancel
if errorlevel 1 goto :install

:cancel
echo.
echo Installation cancelled by user.
pause
exit /b 0

:install
echo.

REM ============================================================================
REM Step 2: Extract Python Embeddable
REM ============================================================================

echo ============================================================================
echo Step 2: Extracting Python embeddable distribution
echo ============================================================================
echo.

REM Create installation directory
if not exist "%PYTHON_DIR%" (
    mkdir "%PYTHON_DIR%"
    if errorlevel 1 (
        echo ERROR: Failed to create directory: %PYTHON_DIR%
        pause
        exit /b 1
    )
)

echo Extracting Python to: %PYTHON_DIR%
echo.

REM Extract using PowerShell (available on all modern Windows)
powershell -Command "Expand-Archive -Path '%PYTHON_ZIP%' -DestinationPath '%PYTHON_DIR%' -Force"

if errorlevel 1 (
    echo ERROR: Failed to extract Python
    pause
    exit /b 1
)

echo Python extracted successfully
echo.

REM Verify python.exe exists
if not exist "%PYTHON_DIR%\python.exe" (
    echo ERROR: python.exe not found after extraction
    pause
    exit /b 1
)

echo Testing Python:
"%PYTHON_DIR%\python.exe" --version
echo.

REM ============================================================================
REM Step 3: Fix ._pth File (CRITICAL)
REM ============================================================================

echo ============================================================================
echo Step 3: Configuring Python environment (fixing ._pth file)
echo ============================================================================
echo.

REM Find the ._pth file
set "PTH_FILE="
for %%F in ("%PYTHON_DIR%\python*._pth") do (
    set "PTH_FILE=%%F"
    goto :found_pth
)

:found_pth
if "%PTH_FILE%"=="" (
    echo ERROR: Could not find python*._pth file in %PYTHON_DIR%
    pause
    exit /b 1
)

echo Found PTH file: %PTH_FILE%

REM Backup original ._pth file
copy "%PTH_FILE%" "%PTH_FILE%.backup" >nul
echo Created backup: %PTH_FILE%.backup

REM Create new ._pth file with correct configuration
echo Creating new configuration...
(
    echo python311.zip
    echo .
    echo.
    echo # Lib\site-packages is required for pip to work
    echo Lib\site-packages
    echo.
    echo # Uncomment to run site.main^(^) automatically
    echo import site
) > "%PTH_FILE%.new"

REM Replace original with new configuration
move /y "%PTH_FILE%.new" "%PTH_FILE%" >nul

if errorlevel 1 (
    echo ERROR: Failed to update ._pth file
    echo Restoring backup...
    copy "%PTH_FILE%.backup" "%PTH_FILE%" >nul
    pause
    exit /b 1
)

echo Updated ._pth file successfully
echo.
echo New configuration:
type "%PTH_FILE%"
echo.

REM ============================================================================
REM Step 4: Install pip Offline
REM ============================================================================

echo ============================================================================
echo Step 4: Installing pip (offline)
echo ============================================================================
echo.

REM Copy get-pip.py to Python directory
copy "%PYTHON_EMBEDDED_DIR%\get-pip.py" "%PYTHON_DIR%\get-pip.py" >nul

if errorlevel 1 (
    echo ERROR: Failed to copy get-pip.py
    pause
    exit /b 1
)

echo Installing pip from get-pip.py...
echo.

REM Install pip using local wheels
"%PYTHON_DIR%\python.exe" "%PYTHON_DIR%\get-pip.py" --no-index --find-links="%WHEELS_DIR%"

if errorlevel 1 (
    echo.
    echo ERROR: pip installation failed
    echo.
    echo This may indicate:
    echo   - The ._pth file was not configured correctly
    echo   - Required wheel files are missing
    echo   - Python extraction was incomplete
    echo.
    pause
    exit /b 1
)

echo.
echo pip installed successfully
echo.

REM Verify pip installation
echo Verifying pip installation:
"%PYTHON_DIR%\python.exe" -m pip --version
echo.

REM ============================================================================
REM Step 5: Install Python Packages
REM ============================================================================

echo ============================================================================
echo Step 5: Installing Python packages (offline)
echo ============================================================================
echo.

echo Installing packages from wheels directory...
echo Source: %WHEELS_DIR%
echo.

REM Install all wheels from the wheels directory
REM This includes pymssql, ldap3, flask, flask-cors and all their dependencies

"%PYTHON_DIR%\python.exe" -m pip install --no-index --find-links="%WHEELS_DIR%" --force-reinstall pymssql ldap3 flask flask-cors

if errorlevel 1 (
    echo.
    echo ERROR: Package installation failed
    echo.
    echo Check the error messages above for details.
    echo Common issues:
    echo   - Missing wheel files
    echo   - Visual C++ Redistributable not installed (for pymssql)
    echo   - Incompatible package versions
    echo.
    pause
    exit /b 1
)

echo.
echo Packages installed successfully
echo.

REM List installed packages
echo Installed packages:
"%PYTHON_DIR%\python.exe" -m pip list
echo.

REM ============================================================================
REM Step 6: Handle Visual C++ Runtime DLLs (Optional)
REM ============================================================================

echo ============================================================================
echo Step 6: Checking Visual C++ Runtime DLLs
echo ============================================================================
echo.

set "DLL_COPIED=0"

REM Check if DLLs exist in package
if exist "%DLLS_DIR%\vcruntime140.dll" (
    echo Found Visual C++ Runtime DLLs in package
    echo.
    choice /C YN /M "Do you want to copy DLLs to Python directory"

    if not errorlevel 2 (
        REM User chose Yes
        echo.
        echo Copying DLLs...

        for %%D in (vcruntime140.dll msvcp140.dll vcruntime140_1.dll) do (
            if exist "%DLLS_DIR%\%%D" (
                copy "%DLLS_DIR%\%%D" "%PYTHON_DIR%\" >nul
                if not errorlevel 1 (
                    echo   Copied: %%D
                    set "DLL_COPIED=1"
                )
            )
        )
        echo.
    )
) else (
    echo No DLLs found in package (this is normal)
    echo.
    echo If pymssql fails with "DLL load failed", you need to:
    echo   1. Install Visual C++ Redistributable for Visual Studio 2015-2022
    echo   2. Download from: https://aka.ms/vs/17/release/vc_redist.x64.exe
    echo   3. Or copy DLLs manually (see 06_DLLS\README_DLLS.md)
    echo.
)

if %DLL_COPIED%==1 (
    echo DLLs copied successfully
) else (
    echo Using system Visual C++ Redistributable (recommended)
)
echo.

REM ============================================================================
REM Step 7: Update Migration_Environment.bat
REM ============================================================================

echo ============================================================================
echo Step 7: Updating Migration_Environment.bat configuration
echo ============================================================================
echo.

if exist "%SOURCE_DIR%\Migration_Environment.bat" (
    echo Found Migration_Environment.bat
    echo.

    REM Create backup
    copy "%SOURCE_DIR%\Migration_Environment.bat" "%SOURCE_DIR%\Migration_Environment.bat.backup" >nul
    echo Created backup: Migration_Environment.bat.backup

    REM Check if AIRGAP_PYTHON already exists
    findstr /C:"AIRGAP_PYTHON" "%SOURCE_DIR%\Migration_Environment.bat" >nul

    if errorlevel 1 (
        REM AIRGAP_PYTHON not found, add it
        echo.
        echo Adding AIRGAP_PYTHON configuration...

        REM Append to file
        (
            echo.
            echo REM -- Air-Gap Python Configuration --
            echo REM Added by install_airgap_python.bat on %DATE% %TIME%
            echo SET "AIRGAP_PYTHON=%PYTHON_DIR%\python.exe"
            echo.
        ) >> "%SOURCE_DIR%\Migration_Environment.bat"

        echo Updated Migration_Environment.bat
    ) else (
        echo AIRGAP_PYTHON already configured in Migration_Environment.bat
        echo To update, edit the file manually or restore from backup
    )
) else (
    echo Migration_Environment.bat not found at: %SOURCE_DIR%
    echo You will need to configure AIRGAP_PYTHON manually
    echo.
    echo Add this line to your batch files:
    echo   SET "AIRGAP_PYTHON=%PYTHON_DIR%\python.exe"
)
echo.

REM ============================================================================
REM Step 8: Run Verification
REM ============================================================================

echo ============================================================================
echo Step 8: Verifying installation
echo ============================================================================
echo.

if exist "%SCRIPT_DIR%\verify_installation.py" (
    echo Running verification script...
    echo.

    "%PYTHON_DIR%\python.exe" "%SCRIPT_DIR%\verify_installation.py"

    set "VERIFY_RESULT=!errorlevel!"

    if !VERIFY_RESULT! EQU 0 (
        echo.
        echo ============================================================================
        echo INSTALLATION COMPLETED SUCCESSFULLY
        echo ============================================================================
        echo.
        echo Python installation: %PYTHON_DIR%
        echo Python executable: %PYTHON_DIR%\python.exe
        echo.
        echo Environment variable set:
        echo   AIRGAP_PYTHON=%PYTHON_DIR%\python.exe
        echo.
        echo Next steps:
        echo   1. Update your batch files to use %%AIRGAP_PYTHON%% instead of python
        echo   2. Or run update_batch_files.py to automate batch file updates
        echo   3. Configure database connection in Migration_Environment.bat
        echo   4. Test with: 4. Migration_Instances\test_connection.py
        echo.
        echo For detailed usage instructions, see 00_README_INSTALLATION.md
        echo.
    ) else (
        echo.
        echo ============================================================================
        echo INSTALLATION COMPLETED WITH WARNINGS
        echo ============================================================================
        echo.
        echo Python was installed but some verification checks failed.
        echo Review the verification output above for details.
        echo.
        echo Python installation: %PYTHON_DIR%
        echo Python executable: %PYTHON_DIR%\python.exe
        echo.
        echo Common issues:
        echo   - Visual C++ Redistributable not installed (for pymssql)
        echo   - 7-Zip not installed (for ZipEncrypt project)
        echo.
        echo See 00_README_INSTALLATION.md for troubleshooting.
        echo.
    )
) else (
    echo Verification script not found: %SCRIPT_DIR%\verify_installation.py
    echo.
    echo Installation completed, but verification was skipped.
    echo Please test manually:
    echo   "%PYTHON_DIR%\python.exe" -m pip list
    echo.
)

pause
exit /b 0
