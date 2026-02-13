@echo off
REM compile_search.bat - Compile papyrus_rpt_search.exe
REM This batch file compiles the C++ MAP file search tool
REM Note: No ODBC needed - this tool reads binary MAP files directly

setlocal

REM Compiler location (MinGW-w64)
set MINGW=C:\Users\freddievr\mingw64\bin

REM Source and output files (relative to this batch file location)
set CPP_FILE=%~dp0papyrus_rpt_search.cpp
set OUTPUT=%~dp0papyrus_rpt_search.exe

echo ======================================================================
echo Compiling Papyrus RPT Search (MAP File Index Search Tool)
echo ======================================================================
echo Source: %CPP_FILE%
echo Output: %OUTPUT%
echo Compiler: %MINGW%\g++.exe
echo.

REM Compilation command
REM Flags:
REM   -std=c++17       : Use C++17 standard (for filesystem, structured bindings)
REM   -O2              : Optimize for performance (important for binary search)
REM   -static          : Static linking (no external DLLs needed)
REM
REM Note: No ODBC libraries needed - this tool reads binary files only

"%MINGW%\g++.exe" -std=c++17 -O2 -static ^
  -o "%OUTPUT%" ^
  "%CPP_FILE%"

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
    echo Quick test:
    echo   %OUTPUT% --map 25001002.MAP --list-fields
    echo   %OUTPUT% --map 25001002.MAP --line-id 8 --field-id 1 --value "200-044295-001"
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
    echo   - Missing headers: Check #include statements in .cpp file
    echo.
    exit /b 1
)

endlocal
