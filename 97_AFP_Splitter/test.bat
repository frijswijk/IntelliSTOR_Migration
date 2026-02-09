@echo off
REM test.bat - Test AFP Splitter with sample file

setlocal

set EXE=afp_splitter.exe
set INPUT=F:\RPT\26027272.AFP
set OUTPUT_DIR=%~dp0test_output

echo ======================================================================
echo AFP Splitter Test Suite
echo ======================================================================
echo.

REM Check if executable exists
if not exist "%EXE%" (
    echo ERROR: %EXE% not found
    echo Please run compile.bat first
    echo.
    exit /b 1
)

REM Check if input file exists
if not exist "%INPUT%" (
    echo ERROR: Test input file not found: %INPUT%
    echo.
    exit /b 1
)

REM Create output directory
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

echo Running tests...
echo.

REM Test 1: Extract pages 1-2
echo Test 1: Extract pages 1-2
%EXE% "%INPUT%" 1-2 "%OUTPUT_DIR%\test1_pages_1_2.afp"
if %ERRORLEVEL% neq 0 (
    echo FAILED: Test 1
    exit /b 1
)
echo PASSED: Test 1
echo.

REM Test 2: Extract page 5 only
echo Test 2: Extract page 5
%EXE% "%INPUT%" 5 "%OUTPUT_DIR%\test2_page_5.afp"
if %ERRORLEVEL% neq 0 (
    echo FAILED: Test 2
    exit /b 1
)
echo PASSED: Test 2
echo.

REM Test 3: Extract multiple ranges
echo Test 3: Extract pages 1-2,4-5
%EXE% "%INPUT%" 1-2,4-5 "%OUTPUT_DIR%\test3_multi_range.afp"
if %ERRORLEVEL% neq 0 (
    echo FAILED: Test 3
    exit /b 1
)
echo PASSED: Test 3
echo.

REM Test 4: Extract with duplicates
echo Test 4: Extract pages 1-3,2-4 (with duplicates)
%EXE% "%INPUT%" 1-3,2-4 "%OUTPUT_DIR%\test4_duplicates.afp"
if %ERRORLEVEL% neq 0 (
    echo FAILED: Test 4
    exit /b 1
)
echo PASSED: Test 4
echo.

REM Test 5: Reversed range (should auto-correct)
echo Test 5: Extract pages 5-3 (reversed, should become 3-5)
%EXE% "%INPUT%" 5-3 "%OUTPUT_DIR%\test5_reversed.afp"
if %ERRORLEVEL% neq 0 (
    echo FAILED: Test 5
    exit /b 1
)
echo PASSED: Test 5
echo.

REM Test 6: Out of range (should clamp)
echo Test 6: Extract pages 1-100 (should clamp to 1-5)
%EXE% "%INPUT%" 1-100 "%OUTPUT_DIR%\test6_out_of_range.afp"
if %ERRORLEVEL% neq 0 (
    echo FAILED: Test 6
    exit /b 1
)
echo PASSED: Test 6
echo.

REM Test 7: Full copy
echo Test 7: Extract all pages (1-5)
%EXE% "%INPUT%" 1-5 "%OUTPUT_DIR%\test7_full_copy.afp"
if %ERRORLEVEL% neq 0 (
    echo FAILED: Test 7
    exit /b 1
)
echo PASSED: Test 7
echo.

echo ======================================================================
echo All tests passed!
echo ======================================================================
echo.
echo Output files created in: %OUTPUT_DIR%
dir /b "%OUTPUT_DIR%"
echo.

endlocal
