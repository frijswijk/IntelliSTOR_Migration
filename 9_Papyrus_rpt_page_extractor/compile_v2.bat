@echo off
REM ============================================================================
REM Compilation script for papyrus_rpt_page_extractor_v2.exe
REM ============================================================================

setlocal

REM Compiler location (MinGW-w64)
set MINGW=C:\Users\freddievr\mingw64\bin

REM Source and output files (relative to this batch file location)
set SOURCE=%~dp0papyrus_rpt_page_extractor_v2.cpp
set OUTPUT=%~dp0papyrus_rpt_page_extractor_v2.exe

echo ============================================================================
echo Compiling Papyrus RPT Page Extractor V2 (with Watermarking)
echo ============================================================================
echo Source: %SOURCE%
echo Output: %OUTPUT%
echo Compiler: %MINGW%\g++.exe
echo.

REM Compilation command
REM Flags:
REM   -std=c++17       : Use C++17 standard (for filesystem support)
REM   -O2              : Optimize for performance
REM   -static          : Static linking (no external DLLs needed)
REM   -lz              : Link zlib library (for compression)
REM   -s               : Strip debug symbols (smaller executable)

"%MINGW%\g++.exe" -std=c++17 -O2 -static ^
  -o "%OUTPUT%" ^
  "%SOURCE%" ^
  -lz -s

REM Check compilation result
if %errorlevel% equ 0 (
    echo.
    echo ============================================================================
    echo SUCCESS: Executable created
    echo ============================================================================
    echo File: %OUTPUT%
    dir "%OUTPUT%" | find ".exe"
    echo.
    goto :success
) else (
    echo.
    echo ============================================================================
    echo ERROR: Compilation failed with error code %ERRORLEVEL%
    echo ============================================================================
    echo.
    echo Check the error messages above for details.
    echo Common issues:
    echo   - Missing MinGW: Install from https://winlibs.com/
    echo   - Wrong path: Update MINGW variable in this batch file
    echo   - Missing zlib: Ensure MinGW installation includes zlib
    echo.
    goto :error
)

:success
echo.
echo You can now run the extractor:
echo.
echo Basic usage (no watermark):
echo   %OUTPUT% input.rpt all output.txt output.pdf
echo.
echo With watermark:
echo   %OUTPUT% input.rpt all output.txt output.pdf --WatermarkImage logo.png
echo.
echo With custom watermark settings:
echo   %OUTPUT% input.rpt all output.txt output.pdf ^
echo     --WatermarkImage confidential.png ^
echo     --WatermarkPosition Center ^
echo     --WatermarkRotation -45 ^
echo     --WatermarkOpacity 30 ^
echo     --WatermarkScale 1.5
echo.
echo For help:
echo   %OUTPUT%
echo.

endlocal
exit /b 0

:error
endlocal
pause
exit /b 1
