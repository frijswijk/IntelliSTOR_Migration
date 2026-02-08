@echo off
REM compile.bat - Compile papyrus_extract_instances.exe
REM This batch file compiles the C++ extractor for report instances

setlocal

REM Compiler location (MinGW-w64)
set MINGW=C:\Users\freddievr\mingw64\bin

REM Source and output files (relative to this batch file location)
set CPP_FILE=%~dp0papyrus_extract_instances.cpp
set OUTPUT=%~dp0papyrus_extract_instances.exe

echo ======================================================================
echo Compiling Papyrus Instances Extractor
echo ======================================================================
echo Source: %CPP_FILE%
echo Output: %OUTPUT%
echo Compiler: %MINGW%\g++.exe
echo.

REM Compilation command
REM Flags:
REM   -std=c++17       : Use C++17 standard (for filesystem support)
REM   -O2              : Optimize for performance
REM   -static          : Static linking (no external DLLs needed)
REM   -lodbc32         : Link ODBC library for MS SQL Server
REM   -lodbccp32       : Link ODBC CP library

"%MINGW%\g++.exe" -std=c++17 -O2 -static ^
  -o "%OUTPUT%" ^
  "%CPP_FILE%" ^
  -lodbc32 -lodbccp32

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
