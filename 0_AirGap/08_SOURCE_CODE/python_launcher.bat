@echo off
REM ============================================================================
REM Python Launcher for Air-Gap Installation
REM ============================================================================
REM
REM This script acts as a wrapper for the air-gap Python installation.
REM It can be used instead of modifying all batch files individually.
REM
REM Usage:
REM   Instead of: python script.py
REM   Use:        python_launcher.bat script.py
REM
REM Configuration:
REM   Set AIRGAP_PYTHON environment variable to point to your Python installation
REM   Or configure in Migration_Environment.bat
REM
REM ============================================================================

setlocal

REM Check if AIRGAP_PYTHON is set
if not defined AIRGAP_PYTHON (
    echo ERROR: AIRGAP_PYTHON environment variable is not set
    echo.
    echo Please configure AIRGAP_PYTHON in Migration_Environment.bat:
    echo   SET "AIRGAP_PYTHON=C:\Path\To\IntelliSTOR_Python\python\python.exe"
    echo.
    echo Or call Migration_Environment.bat before using this launcher:
    echo   call Migration_Environment.bat
    echo   python_launcher.bat script.py
    echo.
    exit /b 1
)

REM Check if Python executable exists
if not exist "%AIRGAP_PYTHON%" (
    echo ERROR: Python executable not found at: %AIRGAP_PYTHON%
    echo.
    echo Please verify the AIRGAP_PYTHON path in Migration_Environment.bat
    echo.
    exit /b 1
)

REM Execute Python with all arguments passed through
"%AIRGAP_PYTHON%" %*

REM Exit with Python's exit code
exit /b %errorlevel%
