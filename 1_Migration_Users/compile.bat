@echo off
REM compile.bat - Compile papyrus_extract_users_permissions.exe
REM This batch file compiles the C++ extractor for users and permissions

setlocal

REM Compiler location (MinGW-w64)
set MINGW=C:\Users\freddievr\mingw64\bin

REM Source and output files (relative to this batch file location)
set CPP_FILE=%~dp0papyrus_extract_users_permissions.cpp
set OUTPUT=%~dp0papyrus_extract_users_permissions.exe

echo ======================================================================
echo Compiling Papyrus Users and Permissions Extractor
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

echo.
echo.
echo ======================================================================
echo Compiling Extract Unique RIDs
echo ======================================================================

REM Source and output files for extract_unique_rids
set CPP_FILE2=%~dp0extract_unique_rids.cpp
set OUTPUT2=%~dp0extract_unique_rids.exe

echo Source: %CPP_FILE2%
echo Output: %OUTPUT2%
echo Compiler: %MINGW%\g++.exe
echo.

REM Compilation command for extract_unique_rids
REM Flags:
REM   -std=c++17       : Use C++17 standard (for filesystem support)
REM   -O2              : Optimize for performance
REM   -static          : Static linking (no external DLLs needed)

"%MINGW%\g++.exe" -std=c++17 -O2 -static ^
  -o "%OUTPUT2%" ^
  "%CPP_FILE2%"

REM Check compilation result
if %ERRORLEVEL% equ 0 (
    echo.
    echo ======================================================================
    echo SUCCESS: Executable created
    echo ======================================================================
    echo File: %OUTPUT2%
    dir "%OUTPUT2%" | find ".exe"
    echo.
    echo You can now run: %OUTPUT2% --help
    echo.
) else (
    echo.
    echo ======================================================================
    echo ERROR: Compilation failed with error code %ERRORLEVEL%
    echo ======================================================================
    echo.
    exit /b 1
)

endlocal
