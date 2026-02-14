CLS
@Echo off
call ..\Migration_Environment.bat
:: --- 1. Capture Start Time ---
set "START_TIME=%TIME%"

echo RPT Search + Page Extract (C++) started at: %DATE% %START_TIME%
echo ---------------------------------------------------------------------------

rem Prompt for RPT file or folder
:ask_rptfile
echo.
set /p "RPT_INPUT=Enter RPT file path or folder (e.g., 251110OD.RPT or C:\RPTFiles): "
if "%RPT_INPUT%"=="" (
    echo ERROR: RPT file or folder is required.
    goto ask_rptfile
)
if not exist "%RPT_INPUT%" (
    echo ERROR: Path does not exist: %RPT_INPUT%
    goto ask_rptfile
)

rem Detect if input is a folder
set "IS_FOLDER="
for %%A in ("%RPT_INPUT%") do if "%%~xA"=="" set "IS_FOLDER=1"
if exist "%RPT_INPUT%\*" set "IS_FOLDER=1"

rem Prompt for mode
echo.
echo Modes:
echo   1. Show RPT info (--info)
echo   2. Extract by page range (--pages)
echo   3. Extract by section ID (--section-id)
echo   4. MAP search + extract pages
echo.
set /p "MODE=Select mode (1/2/3/4): "

if "%MODE%"=="1" (
    echo.
    if defined IS_FOLDER (
        echo Running: papyrus_rpt_search_page_extract.exe --info --folder "%RPT_INPUT%"
        echo ---------------------------------------------------------------------------
        papyrus_rpt_search_page_extract.exe --info --folder "%RPT_INPUT%"
    ) else (
        echo Running: papyrus_rpt_search_page_extract.exe --info "%RPT_INPUT%"
        echo ---------------------------------------------------------------------------
        papyrus_rpt_search_page_extract.exe --info "%RPT_INPUT%"
    )
    goto done
)

if "%MODE%"=="2" (
    set /p "PAGE_RANGE=Enter page range (e.g., 10-20 or 5): "
    setlocal enabledelayedexpansion
    set /p "OUTPUT_DIR=Enter output directory (default: current): "
    set "OUTPUT_FLAG="
    if not "!OUTPUT_DIR!"=="" set "OUTPUT_FLAG=--output "!OUTPUT_DIR!""
    echo.
    if defined IS_FOLDER (
        echo Running: papyrus_rpt_search_page_extract.exe --pages !PAGE_RANGE! --folder "%RPT_INPUT%" !OUTPUT_FLAG!
        echo ---------------------------------------------------------------------------
        papyrus_rpt_search_page_extract.exe --pages !PAGE_RANGE! --folder "%RPT_INPUT%" !OUTPUT_FLAG!
    ) else (
        echo Running: papyrus_rpt_search_page_extract.exe --pages !PAGE_RANGE! "%RPT_INPUT%" !OUTPUT_FLAG!
        echo ---------------------------------------------------------------------------
        papyrus_rpt_search_page_extract.exe --pages !PAGE_RANGE! "%RPT_INPUT%" !OUTPUT_FLAG!
    )
    endlocal
    goto done
)

if "%MODE%"=="3" (
    set /p "SECTION_ID=Enter section ID(s) (space-separated): "
    setlocal enabledelayedexpansion
    set /p "OUTPUT_DIR=Enter output directory (default: current): "
    set "OUTPUT_FLAG="
    if not "!OUTPUT_DIR!"=="" set "OUTPUT_FLAG=--output "!OUTPUT_DIR!""
    echo.
    if defined IS_FOLDER (
        echo Running: papyrus_rpt_search_page_extract.exe --section-id !SECTION_ID! --folder "%RPT_INPUT%" !OUTPUT_FLAG!
        echo ---------------------------------------------------------------------------
        papyrus_rpt_search_page_extract.exe --section-id !SECTION_ID! --folder "%RPT_INPUT%" !OUTPUT_FLAG!
    ) else (
        echo Running: papyrus_rpt_search_page_extract.exe --section-id !SECTION_ID! "%RPT_INPUT%" !OUTPUT_FLAG!
        echo ---------------------------------------------------------------------------
        papyrus_rpt_search_page_extract.exe --section-id !SECTION_ID! "%RPT_INPUT%" !OUTPUT_FLAG!
    )
    endlocal
    goto done
)

if "%MODE%"=="4" (
    set /p "MAP_FILE=Enter MAP file path: "
    setlocal enabledelayedexpansion
    if not exist "!MAP_FILE!" (
        echo ERROR: MAP file does not exist: !MAP_FILE!
        endlocal
        goto done
    )
    set /p "LINE_ID=Enter LINE_ID: "
    set /p "FIELD_ID=Enter FIELD_ID: "
    set /p "SEARCH_VALUE=Enter search value: "
    set /p "USE_PREFIX=Use prefix matching? (Y/N, default N): "
    set "PREFIX_FLAG="
    if /i "!USE_PREFIX!"=="Y" set "PREFIX_FLAG=--prefix"
    set /p "OUTPUT_DIR=Enter output directory (default: current): "
    set "OUTPUT_FLAG="
    if not "!OUTPUT_DIR!"=="" set "OUTPUT_FLAG=--output "!OUTPUT_DIR!""
    echo.
    if defined IS_FOLDER (
        echo Running: papyrus_rpt_search_page_extract.exe --map "!MAP_FILE!" --line-id !LINE_ID! --field-id !FIELD_ID! --value "!SEARCH_VALUE!" !PREFIX_FLAG! --folder "%RPT_INPUT%" !OUTPUT_FLAG!
        echo ---------------------------------------------------------------------------
        papyrus_rpt_search_page_extract.exe --map "!MAP_FILE!" --line-id !LINE_ID! --field-id !FIELD_ID! --value "!SEARCH_VALUE!" !PREFIX_FLAG! --folder "%RPT_INPUT%" !OUTPUT_FLAG!
    ) else (
        echo Running: papyrus_rpt_search_page_extract.exe --map "!MAP_FILE!" --line-id !LINE_ID! --field-id !FIELD_ID! --value "!SEARCH_VALUE!" !PREFIX_FLAG! "%RPT_INPUT%" !OUTPUT_FLAG!
        echo ---------------------------------------------------------------------------
        papyrus_rpt_search_page_extract.exe --map "!MAP_FILE!" --line-id !LINE_ID! --field-id !FIELD_ID! --value "!SEARCH_VALUE!" !PREFIX_FLAG! "%RPT_INPUT%" !OUTPUT_FLAG!
    )
    endlocal
    goto done
)

echo ERROR: Invalid mode selected.

:done
:: --- 2. Capture End Time and Calculate Duration ---
echo ---------------------------------------------------------------------------
set "END_TIME=%TIME%"
echo Script finished at: %DATE% %END_TIME%

:: Robust calculation using New-TimeSpan to handle regional time formats
for /f "tokens=*" %%i in ('powershell -command "$start = [datetime]('%START_TIME%'.Replace(',', '.')); $end = [datetime]('%END_TIME%'.Replace(',', '.')); (New-TimeSpan -Start $start -End $end).ToString('hh\:mm\:ss')"') do set "DURATION=%%i"

echo Total Time Elapsed: %DURATION%
pause
