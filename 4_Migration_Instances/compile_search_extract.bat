@echo off
REM compile_search_extract.bat - Compile papyrus_rpt_search_page_extract.exe
REM Combined MAP File Search + RPT Page Extractor
REM Requires: MinGW-w64 (C++17) + zlib
REM No ODBC needed - reads binary MAP + RPT files directly

setlocal

REM Compiler location (MinGW-w64)
set MINGW=C:\Users\freddievr\mingw64\bin

REM Source and output files (relative to this batch file location)
set CPP_FILE=%~dp0papyrus_rpt_search_page_extract.cpp
set OUTPUT=%~dp0papyrus_rpt_search_page_extract.exe

echo ======================================================================
echo Compiling Papyrus RPT Search + Page Extract (Combined Tool)
echo ======================================================================
echo Source: %CPP_FILE%
echo Output: %OUTPUT%
echo Compiler: %MINGW%\g++.exe
echo.

REM Compilation command
REM Flags:
REM   -std=c++17       : Use C++17 standard (for filesystem, structured bindings, optional)
REM   -O2              : Optimize for performance (binary search + decompression)
REM   -static          : Static linking (no external DLLs needed)
REM   -lz              : Link zlib (for RPT page decompression)
REM
REM Note: No ODBC libraries needed - this tool reads binary files only

"%MINGW%\g++.exe" -std=c++17 -O2 -static ^
  -o "%OUTPUT%" ^
  "%CPP_FILE%" ^
  -lz

REM Check compilation result
if %ERRORLEVEL% equ 0 (
    echo.
    echo ======================================================================
    echo SUCCESS: Executable created
    echo ======================================================================
    echo File: %OUTPUT%
    dir "%OUTPUT%" | find ".exe"
    echo.
    echo You can now run: %OUTPUT% --help
    echo.
    echo Quick tests:
    echo.
    echo   # Normal RPT extraction (backward-compatible):
    echo   %OUTPUT% --info 260271NL.RPT
    echo   %OUTPUT% --section-id 14259 251110OD.RPT
    echo.
    echo   # MAP search + extract pages:
    echo   %OUTPUT% --map 2511109P.MAP --line-id 8 --field-id 1 --value "200-044295-001" 251110OD.RPT
    echo.
    echo   # MAP search + section intersection:
    echo   %OUTPUT% --map 2511109P.MAP --line-id 8 --field-id 1 --value "200-044295-001" --section-id 14259 251110OD.RPT
    echo.
) else (
    echo.
    echo ======================================================================
    echo ERROR: Compilation failed with error code %ERRORLEVEL%
    echo ======================================================================
    echo.
    echo Check the error messages above for details.
    echo Common issues:
    echo   - Missing MinGW: Install from https://winlibs.com/
    echo   - Wrong path: Update MINGW variable in this batch file
    echo   - Missing zlib: Ensure zlib is available (libz.a in MinGW lib path)
    echo   - Missing headers: Check #include statements in .cpp file
    echo.
    exit /b 1
)

endlocal
