@echo off
REM compile.bat - Compile AFP Page Splitter
REM This batch file compiles the AFP page splitter tool

setlocal

REM Compiler location (MinGW-w64)
set MINGW=C:\Users\freddievr\mingw64\bin

REM Source and output files (relative to this batch file location)
set CPP_FILE1=%~dp0afp_parser.cpp
set CPP_FILE2=%~dp0afp_splitter.cpp
set OUTPUT=%~dp0afp_splitter.exe

echo ======================================================================
echo Compiling AFP Page Splitter
echo ======================================================================
echo Sources:  %CPP_FILE1%
echo           %CPP_FILE2%
echo Output:   %OUTPUT%
echo Compiler: %MINGW%\g++.exe
echo.

REM Compilation command
REM Flags:
REM   -std=c++17       : Use C++17 standard
REM   -O2              : Optimize for performance
REM   -static          : Static linking (no external DLLs needed)
REM   -Wall            : Enable all warnings

"%MINGW%\g++.exe" -std=c++17 -O2 -Wall -static ^
  -o "%OUTPUT%" ^
  "%CPP_FILE1%" ^
  "%CPP_FILE2%"

REM Check compilation result
if %ERRORLEVEL% equ 0 (
    echo.
    echo ======================================================================
    echo SUCCESS: Executable created
    echo ======================================================================
    echo File: %OUTPUT%
    dir "%OUTPUT%" | find ".exe"
    echo.
    echo You can now run:
    echo   %OUTPUT% --help
    echo.
    echo Example usage:
    echo   %OUTPUT% input.afp 1-5 output.afp
    echo   %OUTPUT% input.afp 1-2,5-8 output.afp
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
    echo   - Missing headers: Check #include statements in .cpp files
    echo.
    exit /b 1
)

endlocal
