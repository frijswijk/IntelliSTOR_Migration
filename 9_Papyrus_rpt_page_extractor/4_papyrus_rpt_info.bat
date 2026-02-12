CLS
@Echo off
REM ============================================================================
REM Papyrus RPT Info - Wrapper Script
REM ============================================================================
REM
REM Collects metadata from RPT spool files and outputs a CSV summary.
REM
REM Usage:
REM   4_papyrus_rpt_info.bat <file.rpt>                       - Single file
REM   4_papyrus_rpt_info.bat <directory>                       - All .RPT files
REM   4_papyrus_rpt_info.bat <file_or_dir> OUTPUT <path.csv>  - Write CSV to file
REM
REM Or set environment variables:
REM   set RPT_INPUT=F:\RPT
REM   set RPT_INFO_OUTPUT=F:\RPT\rpt_info.csv
REM
REM Output CSV columns:
REM   RPT_FILE, REPORT_SPECIES_ID, SECTION_COUNT, PAGES, BINARY
REM
REM ============================================================================

REM Load environment variables if Migration_Environment.bat exists
if exist "..\Migration_Environment.bat" (
    call ..\Migration_Environment.bat
)

REM Get start time
set "START_TIME=%TIME%"
set "LOG_FILE=papyrus_rpt_info_LOG.txt"

echo Papyrus RPT Info Script started at: %DATE% %START_TIME%
echo -----------------------------------------------------------------------

REM Determine input method: command-line arguments or environment variables
if "%~1" NEQ "" (
    set "INPUT_PATH=%~1"
    set "INPUT_METHOD=Command-line"
) else if "%RPT_INPUT%" NEQ "" (
    set "INPUT_PATH=%RPT_INPUT%"
    set "INPUT_METHOD=Environment variables"
) else (
    echo ERROR: No input parameters provided
    echo.
    echo Usage:
    echo   4_papyrus_rpt_info.bat ^<file.rpt^>                       - Single file
    echo   4_papyrus_rpt_info.bat ^<directory^>                       - All .RPT files
    echo   4_papyrus_rpt_info.bat ^<file_or_dir^> OUTPUT ^<path.csv^>  - Write CSV to file
    echo.
    echo Or set environment variables:
    echo   set RPT_INPUT=F:\RPT
    echo   set RPT_INFO_OUTPUT=F:\RPT\rpt_info.csv
    echo.
    pause
    exit /b 1
)

REM Build command-line arguments
set "EXTRA_ARGS="

REM Check for OUTPUT argument (command-line takes priority over env var)
if /i "%~2"=="OUTPUT" if "%~3" NEQ "" (
    set "EXTRA_ARGS=OUTPUT "%~3""
    set "OUTPUT_CSV=%~3"
) else if "%RPT_INFO_OUTPUT%" NEQ "" (
    set "EXTRA_ARGS=OUTPUT "%RPT_INFO_OUTPUT%""
    set "OUTPUT_CSV=%RPT_INFO_OUTPUT%"
)

echo Input Method: %INPUT_METHOD%
echo Input Path:   %INPUT_PATH%
if defined OUTPUT_CSV echo Output CSV:   %OUTPUT_CSV%
echo.

REM Check if input exists
if not exist "%INPUT_PATH%" (
    echo ERROR: Input not found: %INPUT_PATH%
    echo.
    pause
    exit /b 2
)

REM Check if executable exists
if not exist "%~dp0papyrus_rpt_info.exe" (
    echo ERROR: papyrus_rpt_info.exe not found in script directory
    echo Please compile first using compile_info.bat
    echo.
    pause
    exit /b 3
)

REM Run the Papyrus RPT Info tool
echo Running RPT info collector...
echo.

if defined EXTRA_ARGS (
    "%~dp0papyrus_rpt_info.exe" "%INPUT_PATH%" %EXTRA_ARGS%
) else (
    "%~dp0papyrus_rpt_info.exe" "%INPUT_PATH%"
)

REM Capture exit code
set EXIT_CODE=%ERRORLEVEL%

echo.
echo -----------------------------------------------------------------------

REM Check exit code
if %EXIT_CODE% EQU 0 (
    echo Status: SUCCESS
) else (
    echo Status: FAILED with exit code %EXIT_CODE%
)

REM Capture end time and calculate duration
set "END_TIME=%TIME%"
echo Script finished at: %DATE% %END_TIME%

REM Robust calculation using New-TimeSpan to handle regional time formats
for /f "tokens=*" %%i in ('powershell -command "$start = [datetime]('%START_TIME%'.Replace(',', '.')); $end = [datetime]('%END_TIME%'.Replace(',', '.')); (New-TimeSpan -Start $start -End $end).ToString('hh\:mm\:ss')"') do set "DURATION=%%i"

echo Total Time Elapsed: %DURATION%

REM Logging Section
if %EXIT_CODE% EQU 0 (
    echo [%DATE% %START_TIME%] Input: %INPUT_PATH% ^| Duration: %DURATION% ^| Status: SUCCESS >> "%LOG_FILE%"
) else (
    echo [%DATE% %START_TIME%] Input: %INPUT_PATH% ^| Duration: %DURATION% ^| Status: FAILED (Exit Code %EXIT_CODE%) >> "%LOG_FILE%"
)

echo Log updated in %LOG_FILE%
echo.

REM Show output file if CSV was written
if %EXIT_CODE% EQU 0 (
    if defined OUTPUT_CSV (
        if exist "%OUTPUT_CSV%" (
            for %%A in ("%OUTPUT_CSV%") do echo CSV Output: %%~zA bytes - %OUTPUT_CSV%
            echo.
        )
    )
)

pause
exit /b %EXIT_CODE%
