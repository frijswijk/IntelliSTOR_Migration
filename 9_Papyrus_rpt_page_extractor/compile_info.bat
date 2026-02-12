@echo off
REM ============================================================================
REM Compilation script for papyrus_rpt_info.exe
REM Minimal standalone tool - only needs zlib
REM ============================================================================

setlocal EnableDelayedExpansion

set MINGW=C:\Users\freddievr\mingw64\bin
set SOURCE=%~dp0papyrus_rpt_info.cpp
set OUTPUT=%~dp0papyrus_rpt_info.exe

echo ============================================================================
echo Compiling Papyrus RPT Info Tool (Standalone)
echo ============================================================================
echo Source: %SOURCE%
echo Output: %OUTPUT%
echo.

"%MINGW%\g++.exe" -std=c++17 -O2 -static -o "%OUTPUT%" "%SOURCE%" -lz -s

if !errorlevel! neq 0 (
    echo.
    echo ERROR: Compilation failed!
    goto :error
)

echo.
echo ============================================================================
echo SUCCESS: papyrus_rpt_info.exe created
echo ============================================================================
dir "%OUTPUT%"
echo.

endlocal
exit /b 0

:error
endlocal
pause
exit /b 1
