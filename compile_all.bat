@echo off
REM compile_all.bat - Compile all Papyrus C++ extractors
REM This master batch file compiles all three extractors in sequence

setlocal

echo ======================================================================
echo Compiling All Papyrus C++ Extractors
echo ======================================================================
echo.
echo This will compile:
echo   1. Users and Permissions Extractor
echo   2. Folder and Species Extractor
echo   3. Instances Extractor
echo.
echo Press Ctrl+C to cancel, or
pause

set START_TIME=%TIME%
set ERRORS=0

REM Compile Users and Permissions Extractor
echo.
echo ======================================================================
echo [1/3] Compiling Users and Permissions Extractor...
echo ======================================================================
call "%~dp01_Migration_Users\compile.bat"
if %ERRORLEVEL% neq 0 (
    set /a ERRORS+=1
    echo ERROR: Users extractor compilation failed
)

REM Compile Folder and Species Extractor
echo.
echo ======================================================================
echo [2/3] Compiling Folder and Species Extractor...
echo ======================================================================
call "%~dp03_Migration_Report_Species_Folders\compile.bat"
if %ERRORLEVEL% neq 0 (
    set /a ERRORS+=1
    echo ERROR: Folder/Species extractor compilation failed
)

REM Compile Instances Extractor
echo.
echo ======================================================================
echo [3/3] Compiling Instances Extractor...
echo ======================================================================
call "%~dp04_Migration_Instances\compile.bat"
if %ERRORLEVEL% neq 0 (
    set /a ERRORS+=1
    echo ERROR: Instances extractor compilation failed
)

set END_TIME=%TIME%

REM Summary
echo.
echo ======================================================================
echo Compilation Summary
echo ======================================================================
echo Start time: %START_TIME%
echo End time:   %END_TIME%
echo Errors:     %ERRORS%
echo.

if %ERRORS% equ 0 (
    echo ✓ SUCCESS: All extractors compiled successfully!
    echo.
    echo Executables created:
    echo   - 1_Migration_Users\papyrus_extract_users_permissions.exe
    echo   - 3_Migration_Report_Species_Folders\papyrus_extract_folder_species.exe
    echo   - 4_Migration_Instances\papyrus_extract_instances.exe
    echo.
    echo These are ready for airgap deployment.
    echo.
) else (
    echo ✗ FAILED: %ERRORS% compilation(s) failed
    echo.
    echo Review the error messages above and fix the issues.
    echo Common problems:
    echo   - MinGW not installed or wrong path
    echo   - Missing #include headers in .cpp files
    echo   - Syntax errors in C++ code
    echo.
    exit /b 1
)

endlocal
