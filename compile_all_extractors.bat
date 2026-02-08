@echo off
echo Compiling all extractors...
echo.

echo ===== Compiling folder_species extractor =====
cd "C:\Users\freddievr\claude-projects\IntelliSTOR_Migration\3_Migration_Report_Species_Folders"
C:\Users\freddievr\mingw64\bin\g++.exe -std=c++17 -O2 -static -o papyrus_extract_folder_species.exe papyrus_extract_folder_species.cpp -lodbc32 -lodbccp32
if %ERRORLEVEL% equ 0 (
    echo SUCCESS: folder_species extractor compiled
) else (
    echo ERROR: folder_species extractor failed
    exit /b 1
)
echo.

echo ===== Compiling instances extractor =====
cd "C:\Users\freddievr\claude-projects\IntelliSTOR_Migration\4_Migration_Instances"
C:\Users\freddievr\mingw64\bin\g++.exe -std=c++17 -O2 -static -o papyrus_extract_instances.exe papyrus_extract_instances.cpp -lodbc32 -lodbccp32
if %ERRORLEVEL% equ 0 (
    echo SUCCESS: instances extractor compiled
) else (
    echo ERROR: instances extractor failed
    exit /b 1
)
echo.

echo ===== All extractors compiled successfully =====
