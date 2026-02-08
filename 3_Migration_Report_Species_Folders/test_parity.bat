@echo off
REM test_parity.bat - Test Python and C++ output parity
REM This script runs both extractors and compares their outputs

setlocal EnableDelayedExpansion

echo ======================================================================
echo Python and C++ Output Parity Test
echo ======================================================================
echo.

REM Check arguments
if "%~1"=="" (
    echo ERROR: Missing required arguments
    echo.
    echo Usage: test_parity.bat SERVER DATABASE COUNTRY
    echo.
    echo Arguments:
    echo   SERVER   - MS SQL Server hostname
    echo   DATABASE - Database name
    echo   COUNTRY  - Country code: 2-letter ^(SG, HK^) or "0" for auto-detect
    echo.
    echo Example:
    echo   test_parity.bat SQLSRV01 IntelliSTOR_SG 0
    echo   test_parity.bat SQLSRV01 IntelliSTOR_SG SG
    echo.
    exit /b 1
)

set SERVER=%~1
set DATABASE=%~2
set COUNTRY=%~3

echo Server:   %SERVER%
echo Database: %DATABASE%
echo Country:  %COUNTRY%
echo.

REM Create output directories
set PYTHON_OUT=test_output_python
set CPP_OUT=test_output_cpp

if exist "%PYTHON_OUT%" rmdir /s /q "%PYTHON_OUT%"
if exist "%CPP_OUT%" rmdir /s /q "%CPP_OUT%"

mkdir "%PYTHON_OUT%"
mkdir "%CPP_OUT%"

echo ======================================================================
echo Step 1: Running Python Extractor
echo ======================================================================
echo.

python Extract_Folder_Species.py ^
  --server %SERVER% ^
  --database %DATABASE% ^
  --windows-auth ^
  --Country %COUNTRY% ^
  --output-dir "%PYTHON_OUT%"

if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: Python extractor failed with error code %ERRORLEVEL%
    exit /b 1
)

echo.
echo ======================================================================
echo Step 2: Running C++ Extractor
echo ======================================================================
echo.

papyrus_extract_folder_species.exe ^
  --server %SERVER% ^
  --database %DATABASE% ^
  --windows-auth ^
  --Country %COUNTRY% ^
  --output-dir "%CPP_OUT%"

if %ERRORLEVEL% neq 0 (
    echo.
    echo ERROR: C++ extractor failed with error code %ERRORLEVEL%
    exit /b 1
)

echo.
echo ======================================================================
echo Step 3: Comparing Outputs
echo ======================================================================
echo.

python compare_outputs.py "%PYTHON_OUT%" "%CPP_OUT%"

set RESULT=%ERRORLEVEL%

echo.
echo ======================================================================
echo Test Complete
echo ======================================================================
echo.

if %RESULT% equ 0 (
    echo Result: SUCCESS - Outputs are identical!
    echo.
    echo Output files:
    echo   Python: %PYTHON_OUT%
    echo   C++:    %CPP_OUT%
    echo.
) else (
    echo Result: FAILURE - Outputs differ
    echo.
    echo Review the comparison output above for details.
    echo.
    echo Output files retained for inspection:
    echo   Python: %PYTHON_OUT%
    echo   C++:    %CPP_OUT%
    echo.
    exit /b 1
)

endlocal
