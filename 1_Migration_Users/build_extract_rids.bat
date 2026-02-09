@echo off
REM Build script for extract_unique_rids C++ program (Windows)

setlocal enabledelayedexpansion

set PROGRAM_NAME=extract_unique_rids
set EXECUTABLE=%~dp0%PROGRAM_NAME%.exe

echo Building %PROGRAM_NAME%...
echo Source file: %~dp0%PROGRAM_NAME%.cpp
echo Executable: %EXECUTABLE%
echo.

REM Try to find a C++ compiler
where g++ >nul 2>&1
if !errorlevel! equ 0 (
    echo Found g++, compiling...
    g++ -std=c++17 -O2 "%~dp0%PROGRAM_NAME%.cpp" -o "%EXECUTABLE%"
) else (
    where cl.exe >nul 2>&1
    if !errorlevel! equ 0 (
        echo Found cl.exe ^(MSVC^), compiling...
        cl.exe /std:latest /O2 /EHsc "%~dp0%PROGRAM_NAME%.cpp" /Fe"%EXECUTABLE%"
    ) else (
        echo Error: No C++ compiler found ^(g++ or MSVC required^)
        exit /b 1
    )
)

if exist "%EXECUTABLE%" (
    echo.
    echo ^-^- Build successful!
    echo.
    echo Usage:
    echo   %PROGRAM_NAME%.exe ^<folder_path^>
    echo   %PROGRAM_NAME%.exe ^<folder_path^> ^<output_file^>
    echo.
    echo Example:
    echo   %PROGRAM_NAME%.exe C:\Users_SG
    echo   %PROGRAM_NAME%.exe C:\Users_SG my_rids.csv
) else (
    echo.
    echo ^-^- Build failed!
    exit /b 1
)
