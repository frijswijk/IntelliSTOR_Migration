CLS
@Echo off
call ..\Migration_Environment.bat
:: RPT Page Extractor - Interactive Menu
:: Windows launcher for rpt_page_extractor.py

:: Default RPT file directory
if "%RPT_DIR%"=="" set "RPT_DIR=%Migration_data%"

echo ============================================================
echo   RPT Page Extractor - IntelliSTOR RPT File Tool
echo ============================================================
echo.
echo Current Directory: %CD%
echo RPT Files Directory: %RPT_DIR%
echo.
echo Options:
echo   1. Show RPT file info (sections, page table, compression)
echo   2. Extract all pages from an RPT file
echo   3. Extract page range from an RPT file
echo   4. Extract pages for one or more sections (by SECTION_ID)
echo   5. Extract all RPT files in a folder
echo   6. Show help
echo   7. Extract all content (text + PDF/AFP) from an RPT file
echo   8. Extract binary objects only (PDF/AFP) from an RPT file
echo   9. Extract all pages as single concatenated file
echo  10. Export sections as CSV file
echo   0. Exit
echo.
set /p OPTION="Select option [0-10]: "

if "%OPTION%"=="1" goto INFO
if "%OPTION%"=="2" goto EXTRACT_ALL
if "%OPTION%"=="3" goto EXTRACT_RANGE
if "%OPTION%"=="4" goto EXTRACT_SECTION
if "%OPTION%"=="5" goto EXTRACT_FOLDER
if "%OPTION%"=="6" goto SHOW_HELP
if "%OPTION%"=="7" goto EXTRACT_ALL_CONTENT
if "%OPTION%"=="8" goto EXTRACT_BINARY
if "%OPTION%"=="9" goto EXTRACT_CONCAT
if "%OPTION%"=="10" goto EXPORT_CSV
if "%OPTION%"=="0" goto EXIT
echo Invalid option
goto END

:INFO
echo.
echo Available RPT files in %RPT_DIR%:
dir /b "%RPT_DIR%\*.RPT" 2>nul
echo.
set /p RPT_FILE="Enter RPT filename or full path: "
if "%RPT_FILE%"=="" goto END
if not exist "%RPT_FILE%" set "RPT_FILE=%RPT_DIR%\%RPT_FILE%"
echo.
python rpt_page_extractor.py --info "%RPT_FILE%"
goto END

:EXTRACT_ALL
echo.
echo Available RPT files in %RPT_DIR%:
dir /b "%RPT_DIR%\*.RPT" 2>nul
echo.
set /p RPT_FILE="Enter RPT filename or full path: "
set /p OUTPUT_DIR="Enter output directory [.\extracted]: "
if "%OUTPUT_DIR%"=="" set "OUTPUT_DIR=.\extracted"
if "%RPT_FILE%"=="" goto END
if not exist "%RPT_FILE%" set "RPT_FILE=%RPT_DIR%\%RPT_FILE%"
echo.
python rpt_page_extractor.py --output "%OUTPUT_DIR%" "%RPT_FILE%"
goto END

:EXTRACT_RANGE
echo.
echo Available RPT files in %RPT_DIR%:
dir /b "%RPT_DIR%\*.RPT" 2>nul
echo.
set /p RPT_FILE="Enter RPT filename or full path: "
set /p PAGE_RANGE="Enter page range (e.g., 1-10, 5): "
set /p OUTPUT_DIR="Enter output directory [.\extracted]: "
if "%OUTPUT_DIR%"=="" set "OUTPUT_DIR=.\extracted"
if "%RPT_FILE%"=="" goto END
if "%PAGE_RANGE%"=="" goto END
if not exist "%RPT_FILE%" set "RPT_FILE=%RPT_DIR%\%RPT_FILE%"
echo.
python rpt_page_extractor.py --pages "%PAGE_RANGE%" --output "%OUTPUT_DIR%" "%RPT_FILE%"
goto END

:EXTRACT_SECTION
echo.
echo Available RPT files in %RPT_DIR%:
dir /b "%RPT_DIR%\*.RPT" 2>nul
echo.
set /p RPT_FILE="Enter RPT filename or full path: "
if "%RPT_FILE%"=="" goto END
if not exist "%RPT_FILE%" set "RPT_FILE=%RPT_DIR%\%RPT_FILE%"
:: Show sections first
echo.
echo Sections in this RPT file:
python rpt_page_extractor.py --info "%RPT_FILE%" 2>nul | findstr /R "SECTION_ID [0-9]"
echo.
echo Enter one or more SECTION_IDs separated by spaces.
echo Missing IDs will be skipped. Pages are extracted in the order given.
set /p SECTION_IDS="Enter SECTION_ID(s) to extract: "
set /p OUTPUT_DIR="Enter output directory [.\extracted]: "
if "%OUTPUT_DIR%"=="" set "OUTPUT_DIR=.\extracted"
if "%SECTION_IDS%"=="" goto END
echo.
python rpt_page_extractor.py --section-id %SECTION_IDS% --output "%OUTPUT_DIR%" "%RPT_FILE%"
goto END

:EXTRACT_ALL_CONTENT
echo.
echo --- Extract ALL content (text pages + binary PDF/AFP) ---
echo.
set /p BROWSE_DIR="Enter folder containing RPT files [%RPT_DIR%]: "
if "%BROWSE_DIR%"=="" set "BROWSE_DIR=%RPT_DIR%"
echo.
echo Available RPT files in %BROWSE_DIR%:
dir /b "%BROWSE_DIR%\*.RPT" 2>nul
echo.
set /p RPT_FILE="Enter RPT filename or full path: "
set /p OUTPUT_DIR="Enter output directory [.\extracted]: "
if "%OUTPUT_DIR%"=="" set "OUTPUT_DIR=.\extracted"
if "%RPT_FILE%"=="" goto END
if not exist "%RPT_FILE%" set "RPT_FILE=%BROWSE_DIR%\%RPT_FILE%"
echo.
python rpt_page_extractor.py --output "%OUTPUT_DIR%" "%RPT_FILE%"
goto END

:EXTRACT_BINARY
echo.
echo --- Extract BINARY objects only (PDF/AFP) ---
echo.
set /p BROWSE_DIR="Enter folder containing RPT files [%RPT_DIR%]: "
if "%BROWSE_DIR%"=="" set "BROWSE_DIR=%RPT_DIR%"
echo.
echo Available RPT files in %BROWSE_DIR%:
dir /b "%BROWSE_DIR%\*.RPT" 2>nul
echo.
set /p RPT_FILE="Enter RPT filename or full path: "
set /p OUTPUT_DIR="Enter output directory [.\extracted]: "
if "%OUTPUT_DIR%"=="" set "OUTPUT_DIR=.\extracted"
if "%RPT_FILE%"=="" goto END
if not exist "%RPT_FILE%" set "RPT_FILE=%BROWSE_DIR%\%RPT_FILE%"
echo.
python rpt_page_extractor.py --binary-only --output "%OUTPUT_DIR%" "%RPT_FILE%"
goto END

:EXTRACT_CONCAT
echo.
echo --- Extract all pages as single CONCATENATED file ---
echo.
echo Available RPT files in %RPT_DIR%:
dir /b "%RPT_DIR%\*.RPT" 2>nul
echo.
set /p RPT_FILE="Enter RPT filename or full path: "
set /p OUTPUT_DIR="Enter output directory [.\extracted]: "
if "%OUTPUT_DIR%"=="" set "OUTPUT_DIR=.\extracted"
if "%RPT_FILE%"=="" goto END
if not exist "%RPT_FILE%" set "RPT_FILE=%RPT_DIR%\%RPT_FILE%"
echo.
python rpt_page_extractor.py --page-concat --output "%OUTPUT_DIR%" "%RPT_FILE%"
goto END

:EXTRACT_FOLDER
echo.
set /p FOLDER="Enter folder containing RPT files [%RPT_DIR%]: "
if "%FOLDER%"=="" set "FOLDER=%RPT_DIR%"
set /p OUTPUT_DIR="Enter output directory [.\extracted]: "
if "%OUTPUT_DIR%"=="" set "OUTPUT_DIR=.\extracted"
echo.
python rpt_page_extractor.py --folder "%FOLDER%" --output "%OUTPUT_DIR%"
goto END

:EXPORT_CSV
echo.
echo --- Export sections as CSV file ---
echo.
echo Available RPT files in %RPT_DIR%:
dir /b "%RPT_DIR%\*.RPT" 2>nul
echo.
set /p RPT_FILE="Enter RPT filename or full path: "
set /p CSV_FILE="Enter output CSV file path [.\sections.csv]: "
if "%CSV_FILE%"=="" set "CSV_FILE=.\sections.csv"
if "%RPT_FILE%"=="" goto END
if not exist "%RPT_FILE%" set "RPT_FILE=%RPT_DIR%\%RPT_FILE%"
echo.
python rpt_page_extractor.py --info --export-sections "%CSV_FILE%" "%RPT_FILE%"
goto END

:SHOW_HELP
echo.
python rpt_page_extractor.py --help
goto END

:EXIT
echo Exiting...
goto :EOF

:END
echo.
echo -----------------------------------------------------------------------
pause
