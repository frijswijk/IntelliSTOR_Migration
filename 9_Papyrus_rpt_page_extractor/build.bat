@echo off
REM ============================================================================
REM Build Script for papyrus_rpt_page_extractor.exe
REM ============================================================================
REM This script automatically detects available compilers and builds the
REM executable with optimal settings for Windows distribution.
REM ============================================================================

setlocal enabledelayedexpansion

echo ============================================================================
echo Papyrus RPT Page Extractor - Build Script
echo ============================================================================
echo.

REM Source and output files
set SOURCE=papyrus_rpt_page_extractor.cpp
set OUTPUT=papyrus_rpt_page_extractor.exe

REM Check if source file exists
if not exist "%SOURCE%" (
    echo ERROR: Source file not found: %SOURCE%
    echo.
    echo Please run this script from the directory containing %SOURCE%
    pause
    exit /b 1
)

REM Try to detect and use available compiler
echo Detecting available compilers...
echo.

REM ============================================================================
REM Option 1: Try MinGW-w64 (g++)
REM ============================================================================
where g++ >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [✓] Found: MinGW-w64 g++ compiler
    echo.
    echo Compiling with g++ ^(static linking^)...
    echo Command: g++ -o %OUTPUT% %SOURCE% -static -O2 -s
    echo.

    g++ -o %OUTPUT% %SOURCE% -static -O2 -s

    if exist %OUTPUT% (
        echo.
        echo ============================================================================
        echo [SUCCESS] Build completed successfully!
        echo ============================================================================
        echo.
        echo Executable: %OUTPUT%
        echo Compiler: MinGW-w64 g++
        echo Linking: Static ^(no DLL dependencies^)
        echo.

        REM Display file size
        for %%F in (%OUTPUT%) do (
            echo File size: %%~zF bytes
        )

        echo.
        echo The executable is ready for distribution to airgap machines.
        echo.
        echo Test it with:
        echo   %OUTPUT%
        echo.
        pause
        exit /b 0
    ) else (
        echo.
        echo [ERROR] Compilation failed. Check error messages above.
        echo.
        pause
        exit /b 1
    )
)

REM ============================================================================
REM Option 2: Try Microsoft Visual C++ (cl)
REM ============================================================================
where cl >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [✓] Found: Microsoft Visual C++ compiler
    echo.
    echo Compiling with MSVC ^(static runtime linking^)...
    echo Command: cl /EHsc /O2 /MT %SOURCE% /Fe:%OUTPUT%
    echo.

    cl /EHsc /O2 /MT %SOURCE% /Fe:%OUTPUT% /nologo

    if exist %OUTPUT% (
        echo.
        echo ============================================================================
        echo [SUCCESS] Build completed successfully!
        echo ============================================================================
        echo.
        echo Executable: %OUTPUT%
        echo Compiler: Microsoft Visual C++
        echo Linking: Static runtime ^(/MT flag^)
        echo.

        REM Display file size
        for %%F in (%OUTPUT%) do (
            echo File size: %%~zF bytes
        )

        echo.
        echo The executable is ready for distribution to airgap machines.
        echo.
        echo Test it with:
        echo   %OUTPUT%
        echo.

        REM Clean up MSVC intermediate files
        if exist papyrus_rpt_page_extractor.obj del papyrus_rpt_page_extractor.obj

        pause
        exit /b 0
    ) else (
        echo.
        echo [ERROR] Compilation failed. Check error messages above.
        echo.
        pause
        exit /b 1
    )
)

REM ============================================================================
REM Option 3: Try Clang
REM ============================================================================
where clang++ >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [✓] Found: Clang++ compiler
    echo.
    echo Compiling with clang++ ^(static linking^)...
    echo Command: clang++ -o %OUTPUT% %SOURCE% -static -O2
    echo.

    clang++ -o %OUTPUT% %SOURCE% -static -O2

    if exist %OUTPUT% (
        echo.
        echo ============================================================================
        echo [SUCCESS] Build completed successfully!
        echo ============================================================================
        echo.
        echo Executable: %OUTPUT%
        echo Compiler: Clang++
        echo Linking: Static ^(no DLL dependencies^)
        echo.

        REM Display file size
        for %%F in (%OUTPUT%) do (
            echo File size: %%~zF bytes
        )

        echo.
        echo The executable is ready for distribution to airgap machines.
        echo.
        echo Test it with:
        echo   %OUTPUT%
        echo.
        pause
        exit /b 0
    ) else (
        echo.
        echo [ERROR] Compilation failed. Check error messages above.
        echo.
        pause
        exit /b 1
    )
)

REM ============================================================================
REM No compiler found
REM ============================================================================
echo [✗] No C++ compiler found in PATH
echo.
echo Please install one of the following:
echo.
echo 1. MinGW-w64 ^(Recommended^)
echo    Download: https://www.mingw-w64.org/downloads/
echo    Or MSYS2: https://www.msys2.org/
echo.
echo 2. Visual Studio Community ^(Free^)
echo    Download: https://visualstudio.microsoft.com/
echo    Install "Desktop development with C++" workload
echo    Run this script from "Developer Command Prompt for VS"
echo.
echo 3. LLVM/Clang
echo    Download: https://releases.llvm.org/
echo.
echo After installation, ensure the compiler is in your PATH.
echo.
pause
exit /b 1
