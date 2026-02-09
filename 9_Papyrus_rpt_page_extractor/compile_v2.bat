@echo off
REM ============================================================================
REM Compilation script for papyrus_rpt_page_extractor_v2.exe
REM ============================================================================

setlocal

set SOURCE=papyrus_rpt_page_extractor_v2.cpp
set OUTPUT=papyrus_rpt_page_extractor_v2.exe

echo ============================================================================
echo Compiling %SOURCE%
echo ============================================================================
echo.

REM ============================================================================
REM Try GCC/MinGW first (recommended)
REM ============================================================================

where g++ >nul 2>&1
if %errorlevel% equ 0 (
    echo Using GCC/MinGW compiler...
    echo.
    echo Command: g++ -std=c++17 -O2 -static -o %OUTPUT% %SOURCE% -lz -s
    echo.

    g++ -std=c++17 -O2 -static -o %OUTPUT% %SOURCE% -lz -s

    if %errorlevel% equ 0 (
        echo.
        echo ============================================================================
        echo Compilation successful!
        echo Output: %OUTPUT%
        echo ============================================================================
        echo.
        dir %OUTPUT%
        echo.
        goto :success
    ) else (
        echo.
        echo ERROR: GCC compilation failed
        echo.
        goto :error
    )
)

REM ============================================================================
REM Try MSVC (Visual Studio)
REM ============================================================================

where cl >nul 2>&1
if %errorlevel% equ 0 (
    echo Using MSVC compiler...
    echo.
    echo Command: cl /EHsc /O2 /MT %SOURCE% /Fe:%OUTPUT%
    echo.

    cl /EHsc /O2 /MT %SOURCE% /Fe:%OUTPUT%

    if %errorlevel% equ 0 (
        echo.
        echo ============================================================================
        echo Compilation successful!
        echo Output: %OUTPUT%
        echo ============================================================================
        echo.
        dir %OUTPUT%
        echo.
        goto :success
    ) else (
        echo.
        echo ERROR: MSVC compilation failed
        echo.
        goto :error
    )
)

REM ============================================================================
REM No compiler found
REM ============================================================================

echo ERROR: No C++ compiler found in PATH
echo.
echo Please install one of the following:
echo.
echo 1. GCC/MinGW (recommended for Windows)
echo    Download from: https://www.mingw-w64.org/
echo    Or use: https://github.com/skeeto/w64devkit/releases
echo.
echo 2. Microsoft Visual Studio (with C++ tools)
echo    Download from: https://visualstudio.microsoft.com/
echo    Make sure to run this script from "Developer Command Prompt for VS"
echo.

goto :error

REM ============================================================================
REM Success
REM ============================================================================

:success
echo Testing executable...
echo.
%OUTPUT% >nul 2>&1
if %errorlevel% equ 1 (
    echo Test run successful - executable is working
    echo.
    echo Usage:
    echo   %OUTPUT% input.rpt all output.txt output.pdf
    echo.
    echo With watermark:
    echo   %OUTPUT% input.rpt all output.txt output.pdf --WatermarkImage logo.png
    echo.
    echo For help:
    echo   %OUTPUT%
    echo.
) else (
    echo Warning: Executable may not be working correctly
    echo.
)

endlocal
exit /b 0

REM ============================================================================
REM Error
REM ============================================================================

:error
endlocal
pause
exit /b 1
