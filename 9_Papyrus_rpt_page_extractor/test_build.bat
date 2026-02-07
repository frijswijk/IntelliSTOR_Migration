@echo off
REM ============================================================================
REM Test Script for papyrus_rpt_page_extractor.exe
REM ============================================================================
REM This script tests the built executable to ensure it works correctly.
REM ============================================================================

setlocal enabledelayedexpansion

echo ============================================================================
echo Papyrus RPT Page Extractor - Test Script
echo ============================================================================
echo.

set EXE=papyrus_rpt_page_extractor.exe

REM Check if executable exists
if not exist "%EXE%" (
    echo ERROR: Executable not found: %EXE%
    echo.
    echo Please run build.bat first to compile the program.
    pause
    exit /b 1
)

echo [✓] Found: %EXE%
echo.

REM Display file information
echo Executable Information:
echo -----------------------
for %%F in (%EXE%) do (
    echo File size: %%~zF bytes
    echo Modified: %%~tF
)
echo.

REM Test 1: Run without arguments (should show usage)
echo Test 1: Running without arguments ^(should show usage^)
echo -------------------------------------------------------
echo.
%EXE%
echo.
echo Return code: %ERRORLEVEL%
echo.
echo Press any key to continue to Test 2...
pause >nul
echo.

REM Test 2: Create sample input file and test processing
echo Test 2: Testing with sample input file
echo -------------------------------------------------------
echo.

REM Create sample RPT file
echo Creating sample test.rpt file...
(
    echo This is page 1
    echo Content line 1
    echo Content line 2
    echo %%PAGE%%
    echo This is page 2
    echo More content
    echo Even more content
    echo %%PAGE%%
    echo This is page 3
    echo Final page content
) > test.rpt

echo [✓] Created: test.rpt
echo.

REM Run the extractor
echo Running: %EXE% test.rpt rule_1 test_output.txt test_output.pdf
echo.
%EXE% test.rpt rule_1 test_output.txt test_output.pdf

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Processing completed successfully!
    echo.

    REM Show generated files
    echo Generated Files:
    echo ---------------
    if exist test_output.txt (
        echo [✓] test_output.txt
        for %%F in (test_output.txt) do echo     Size: %%~zF bytes
    )
    if exist test_output.pdf (
        echo [✓] test_output.pdf
        for %%F in (test_output.pdf) do echo     Size: %%~zF bytes
    )
    echo.

    REM Show preview of text output
    echo Preview of test_output.txt:
    echo --------------------------
    type test_output.txt
    echo.
    echo --------------------------
    echo.

) else (
    echo.
    echo [FAILED] Processing failed with return code: %ERRORLEVEL%
    echo.
)

echo.
echo Test complete!
echo.
echo Cleanup test files? ^(Y/N^)
set /p cleanup="> "

if /i "%cleanup%"=="Y" (
    if exist test.rpt del test.rpt
    if exist test_output.txt del test_output.txt
    if exist test_output.pdf del test_output.pdf
    echo [✓] Test files cleaned up
)

echo.
pause
