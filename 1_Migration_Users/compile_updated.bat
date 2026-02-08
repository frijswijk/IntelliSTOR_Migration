@echo off
echo Compiling updated papyrus_extract_users_permissions.cpp with TESTDATA support...
echo.

cd "C:\Users\freddievr\claude-projects\IntelliSTOR_Migration\1_Migration_Users"
C:\Users\freddievr\mingw64\bin\g++.exe -std=c++17 -O2 -static -o papyrus_extract_users_permissions.exe papyrus_extract_users_permissions.cpp -lodbc32 -lodbccp32

if %ERRORLEVEL% equ 0 (
    echo.
    echo ===== SUCCESS: papyrus_extract_users_permissions.exe compiled =====
    dir papyrus_extract_users_permissions.exe | find ".exe"
    echo.
    echo Test the new flags:
    echo   papyrus_extract_users_permissions.exe --help
    echo   papyrus_extract_users_permissions.exe --server SERVER --database DB --output ./output --windows-auth --TESTDATA
) else (
    echo.
    echo ===== ERROR: Compilation failed =====
    exit /b 1
)
