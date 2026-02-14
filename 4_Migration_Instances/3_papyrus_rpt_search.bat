CLS
@Echo off
call ..\Migration_Environment.bat
:: --- 1. Capture Start Time ---
set "START_TIME=%TIME%"

echo RPT Search (C++) started at: %DATE% %START_TIME%
echo ---------------------------------------------------------------------------

rem Prompt for MAP file path
:ask_mapfile
echo.
set /p "MAP_FILE=Enter MAP file path (e.g., 25001002.MAP): "
if "%MAP_FILE%"=="" (
    echo ERROR: MAP file is required.
    goto ask_mapfile
)
if not exist "%MAP_FILE%" (
    echo ERROR: File does not exist: %MAP_FILE%
    goto ask_mapfile
)
echo MAP File: %MAP_FILE%

rem Prompt for search mode
echo.
echo Search modes:
echo   1. List indexed fields (--list-fields)
echo   2. List values for a field (--list-values)
echo   3. Search by LINE_ID / FIELD_ID
echo.
set /p "SEARCH_MODE=Select mode (1/2/3): "

if "%SEARCH_MODE%"=="1" (
    echo.
    echo Running: papyrus_rpt_search.exe --map "%MAP_FILE%" --list-fields
    echo ---------------------------------------------------------------------------
    papyrus_rpt_search.exe --map "%MAP_FILE%" --list-fields
    goto done
)

if "%SEARCH_MODE%"=="2" (
    set /p "LINE_ID=Enter LINE_ID: "
    set /p "FIELD_ID=Enter FIELD_ID: "
    echo.
    echo Running: papyrus_rpt_search.exe --map "%MAP_FILE%" --line-id !LINE_ID! --field-id !FIELD_ID! --list-values
    echo ---------------------------------------------------------------------------
    setlocal enabledelayedexpansion
    papyrus_rpt_search.exe --map "%MAP_FILE%" --line-id !LINE_ID! --field-id !FIELD_ID! --list-values
    endlocal
    goto done
)

if "%SEARCH_MODE%"=="3" (
    set /p "LINE_ID=Enter LINE_ID: "
    set /p "FIELD_ID=Enter FIELD_ID: "
    set /p "SEARCH_VALUE=Enter search value: "
    set /p "USE_PREFIX=Use prefix matching? (Y/N, default N): "
    setlocal enabledelayedexpansion
    set "PREFIX_FLAG="
    if /i "!USE_PREFIX!"=="Y" set "PREFIX_FLAG=--prefix"
    echo.
    echo Running: papyrus_rpt_search.exe --map "%MAP_FILE%" --line-id !LINE_ID! --field-id !FIELD_ID! --value "!SEARCH_VALUE!" !PREFIX_FLAG!
    echo ---------------------------------------------------------------------------
    papyrus_rpt_search.exe --map "%MAP_FILE%" --line-id !LINE_ID! --field-id !FIELD_ID! --value "!SEARCH_VALUE!" !PREFIX_FLAG!
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
