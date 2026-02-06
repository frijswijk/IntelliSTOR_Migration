CLS
@Echo off
call ..\Migration_Environment.bat
:: RPT File Builder - Interactive Menu
:: Windows launcher for rpt_file_builder.py

:: Default data directory
if "%INPUT_DIR%"=="" set "INPUT_DIR=%Migration_data%"
if "%RPT_DIR%"=="" set "RPT_DIR=%Migration_data%"

echo ============================================================
echo   RPT File Builder - Create IntelliSTOR RPT Files
echo ============================================================
echo.
echo Current Directory: %CD%
echo Data Directory:    %INPUT_DIR%
echo.
echo Options:
echo   1. Build RPT from text pages (directory)
echo   2. Build RPT from text pages (select files)
echo   3. Build RPT with embedded PDF/AFP binary
echo   4. Build RPT from template (roundtrip rebuild)
echo   5. Build RPT with multiple sections
echo   6. Dry run / show build plan (--info)
echo   7. Show help
echo   0. Exit
echo.
set /p OPTION="Select option [0-7]: "

if "%OPTION%"=="1" goto BUILD_DIR
if "%OPTION%"=="2" goto BUILD_FILES
if "%OPTION%"=="3" goto BUILD_BINARY
if "%OPTION%"=="4" goto BUILD_TEMPLATE
if "%OPTION%"=="5" goto BUILD_SECTIONS
if "%OPTION%"=="6" goto DRY_RUN
if "%OPTION%"=="7" goto SHOW_HELP
if "%OPTION%"=="0" goto EXIT
echo Invalid option
goto END

:BUILD_DIR
echo.
echo --- Build RPT from a directory of page_NNNNN.txt files ---
echo.
set /p PAGE_DIR="Enter directory containing page_*.txt files [%INPUT_DIR%]: "
if "%PAGE_DIR%"=="" set "PAGE_DIR=%INPUT_DIR%"
set /p OUTPUT_FILE="Enter output RPT file path: "
set /p SPECIES="Enter species ID [0]: "
if "%SPECIES%"=="" set "SPECIES=0"
set /p DOMAIN="Enter domain ID [1]: "
if "%DOMAIN%"=="" set "DOMAIN=1"
if "%OUTPUT_FILE%"=="" goto END
echo.
python rpt_file_builder.py --species %SPECIES% --domain %DOMAIN% -o "%OUTPUT_FILE%" "%PAGE_DIR%"
goto END

:BUILD_FILES
echo.
echo --- Build RPT from selected text files ---
echo.
set /p TEXT_FILES="Enter text file paths (space-separated): "
set /p OUTPUT_FILE="Enter output RPT file path: "
set /p SPECIES="Enter species ID [0]: "
if "%SPECIES%"=="" set "SPECIES=0"
set /p DOMAIN="Enter domain ID [1]: "
if "%DOMAIN%"=="" set "DOMAIN=1"
if "%OUTPUT_FILE%"=="" goto END
if "%TEXT_FILES%"=="" goto END
echo.
python rpt_file_builder.py --species %SPECIES% --domain %DOMAIN% -o "%OUTPUT_FILE%" %TEXT_FILES%
goto END

:BUILD_BINARY
echo.
echo --- Build RPT with embedded PDF/AFP binary object ---
echo.
set /p PAGE_INPUT="Enter directory or text files (page sources): "
set /p BINARY_FILE="Enter path to PDF/AFP file to embed: "
set /p OBJ_HEADER="Enter path to Object Header text file (optional): "
set /p OUTPUT_FILE="Enter output RPT file path: "
set /p SPECIES="Enter species ID [0]: "
if "%SPECIES%"=="" set "SPECIES=0"
set /p DOMAIN="Enter domain ID [1]: "
if "%DOMAIN%"=="" set "DOMAIN=1"
if "%OUTPUT_FILE%"=="" goto END
if "%PAGE_INPUT%"=="" goto END
set "BINARY_ARG="
if not "%BINARY_FILE%"=="" set "BINARY_ARG=--binary %BINARY_FILE%"
set "OBJ_ARG="
if not "%OBJ_HEADER%"=="" set "OBJ_ARG=--object-header %OBJ_HEADER%"
echo.
python rpt_file_builder.py --species %SPECIES% --domain %DOMAIN% %BINARY_ARG% %OBJ_ARG% -o "%OUTPUT_FILE%" %PAGE_INPUT%
goto END

:BUILD_TEMPLATE
echo.
echo --- Build RPT from template (roundtrip rebuild) ---
echo.
echo Uses an existing RPT as template to copy instance metadata.
echo.
set /p TEMPLATE_FILE="Enter template RPT file path: "
set /p PAGE_DIR="Enter directory containing page_*.txt files: "
set /p OUTPUT_FILE="Enter output RPT file path: "
set /p SPECIES="Enter species ID [0]: "
if "%SPECIES%"=="" set "SPECIES=0"
if "%OUTPUT_FILE%"=="" goto END
if "%TEMPLATE_FILE%"=="" goto END
if "%PAGE_DIR%"=="" goto END
echo.
python rpt_file_builder.py --template "%TEMPLATE_FILE%" --species %SPECIES% -o "%OUTPUT_FILE%" "%PAGE_DIR%"
goto END

:BUILD_SECTIONS
echo.
echo --- Build RPT with multiple sections ---
echo.
set /p PAGE_INPUT="Enter directory or text files (page sources): "
set /p OUTPUT_FILE="Enter output RPT file path: "
echo.
echo Use a sections CSV file? (from RPT Page Extractor --export-sections)
set /p CSV_PATH="  Enter CSV path (or press Enter for manual entry): "
if not "%CSV_PATH%"=="" goto BUILD_SECTIONS_CSV
goto BUILD_SECTIONS_MANUAL

:BUILD_SECTIONS_CSV
set /p SPECIES="Enter species ID [0, auto from CSV]: "
if "%SPECIES%"=="" set "SPECIES=0"
set /p DOMAIN="Enter domain ID [1]: "
if "%DOMAIN%"=="" set "DOMAIN=1"
if "%OUTPUT_FILE%"=="" goto END
if "%PAGE_INPUT%"=="" goto END
echo.
python rpt_file_builder.py --species %SPECIES% --domain %DOMAIN% --section-csv "%CSV_PATH%" -o "%OUTPUT_FILE%" %PAGE_INPUT%
goto END

:BUILD_SECTIONS_MANUAL
set /p SPECIES="Enter species ID [0]: "
if "%SPECIES%"=="" set "SPECIES=0"
set /p DOMAIN="Enter domain ID [1]: "
if "%DOMAIN%"=="" set "DOMAIN=1"
echo.
echo Enter section specs (format: SECTION_ID:START_PAGE:PAGE_COUNT)
echo Enter up to 5 sections. Leave blank to stop.
set "SECTION_ARGS="
set /p SEC1="  Section 1: "
if not "%SEC1%"=="" set "SECTION_ARGS=%SECTION_ARGS% --section %SEC1%"
if "%SEC1%"=="" goto BUILD_SECTIONS_RUN
set /p SEC2="  Section 2: "
if not "%SEC2%"=="" set "SECTION_ARGS=%SECTION_ARGS% --section %SEC2%"
if "%SEC2%"=="" goto BUILD_SECTIONS_RUN
set /p SEC3="  Section 3: "
if not "%SEC3%"=="" set "SECTION_ARGS=%SECTION_ARGS% --section %SEC3%"
if "%SEC3%"=="" goto BUILD_SECTIONS_RUN
set /p SEC4="  Section 4: "
if not "%SEC4%"=="" set "SECTION_ARGS=%SECTION_ARGS% --section %SEC4%"
if "%SEC4%"=="" goto BUILD_SECTIONS_RUN
set /p SEC5="  Section 5: "
if not "%SEC5%"=="" set "SECTION_ARGS=%SECTION_ARGS% --section %SEC5%"
:BUILD_SECTIONS_RUN
if "%OUTPUT_FILE%"=="" goto END
if "%PAGE_INPUT%"=="" goto END
echo.
python rpt_file_builder.py --species %SPECIES% --domain %DOMAIN% %SECTION_ARGS% -o "%OUTPUT_FILE%" %PAGE_INPUT%
goto END

:DRY_RUN
echo.
echo --- Dry run: show build plan without writing ---
echo.
set /p PAGE_INPUT="Enter directory or text files (page sources): "
set /p OUTPUT_FILE="Enter output RPT file path (for plan display): "
set /p SPECIES="Enter species ID [0]: "
if "%SPECIES%"=="" set "SPECIES=0"
if "%OUTPUT_FILE%"=="" goto END
if "%PAGE_INPUT%"=="" goto END
echo.
python rpt_file_builder.py --info --species %SPECIES% -o "%OUTPUT_FILE%" %PAGE_INPUT%
goto END

:SHOW_HELP
echo.
python rpt_file_builder.py --help
goto END

:EXIT
echo Exiting...
goto :EOF

:END
echo.
echo -----------------------------------------------------------------------
pause
