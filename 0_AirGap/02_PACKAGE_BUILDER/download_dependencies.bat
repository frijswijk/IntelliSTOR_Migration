@echo off
REM ============================================================================
REM Air-Gap Package Builder - Windows Wrapper
REM ============================================================================
REM
REM This script runs the Python package builder on an internet-connected
REM machine to download all dependencies for air-gap installation.
REM
REM Prerequisites:
REM   - Python 3.7 or later installed
REM   - pip installed
REM   - Internet connection
REM
REM Usage:
REM   download_dependencies.bat [output_dir] [python_version]
REM
REM Examples:
REM   download_dependencies.bat
REM   download_dependencies.bat C:\AirGapPackage
REM   download_dependencies.bat .. 3.11.9
REM
REM ============================================================================

setlocal enabledelayedexpansion

echo ============================================================================
echo IntelliSTOR Air-Gap Package Builder
echo ============================================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo Please install Python 3.7 or later and ensure it's in your PATH.
    echo Download from: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo Python found:
python --version
echo.

REM Check if pip is available
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: pip is not installed
    echo.
    echo Please install pip using: python -m ensurepip --upgrade
    echo.
    pause
    exit /b 1
)

echo pip found:
python -m pip --version
echo.

REM Get script directory
set "SCRIPT_DIR=%~dp0"
set "BUILD_SCRIPT=%SCRIPT_DIR%build_airgap_package.py"

REM Check if build script exists
if not exist "%BUILD_SCRIPT%" (
    echo ERROR: Build script not found: %BUILD_SCRIPT%
    echo.
    echo Please ensure build_airgap_package.py is in the same directory.
    echo.
    pause
    exit /b 1
)

REM Parse arguments
set "OUTPUT_DIR=%~1"
set "PYTHON_VERSION=%~2"

if "%OUTPUT_DIR%"=="" set "OUTPUT_DIR=.."
if "%PYTHON_VERSION%"=="" set "PYTHON_VERSION=3.11.7"

echo Configuration:
echo   Build Script: %BUILD_SCRIPT%
echo   Output Directory: %OUTPUT_DIR%
echo   Python Version: %PYTHON_VERSION%
echo.

REM Confirm before proceeding
echo This will download approximately 50-100 MB of data from the internet.
echo.
choice /C YN /M "Do you want to proceed"
if errorlevel 2 goto :cancel
if errorlevel 1 goto :proceed

:cancel
echo.
echo Build cancelled by user.
pause
exit /b 0

:proceed
echo.
echo ============================================================================
echo Starting build process...
echo ============================================================================
echo.

REM Run the Python build script
python "%BUILD_SCRIPT%" --output-dir "%OUTPUT_DIR%" --python-version "%PYTHON_VERSION%"

if errorlevel 1 (
    echo.
    echo ============================================================================
    echo BUILD FAILED
    echo ============================================================================
    echo.
    echo The build process encountered an error.
    echo Please check the error messages above for details.
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================================
echo BUILD SUCCESSFUL
echo ============================================================================
echo.
echo The air-gap package has been created successfully.
echo.
echo Next steps:
echo   1. Review the package contents in the output directory
echo   2. Optionally add Visual C++ Runtime DLLs to 06_DLLS/
echo   3. Optionally add 7-Zip to 07_EXTERNAL_TOOLS/
echo   4. Transfer the entire package to the air-gap environment
echo   5. Run 03_OFFLINE_INSTALLER\install_airgap_python.bat
echo.
echo For detailed instructions, see 00_README_INSTALLATION.md
echo.
pause
exit /b 0
