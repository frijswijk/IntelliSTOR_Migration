CLS
@Echo off
REM ============================================================================
REM Papyrus RPT Page Extractor - Wrapper Script
REM ============================================================================
REM
REM Usage Option 1: With environment variables (set in Migration_Environment.bat)
REM   papyrus_rpt_page_extractor.bat
REM
REM Usage Option 2: With command-line arguments
REM   papyrus_rpt_page_extractor.bat <input_rpt> <selection_rule> <output_txt> <output_binary>
REM
REM Examples:
REM   papyrus_rpt_page_extractor.bat input.rpt "pages:1-5" output.txt output.pdf
REM   papyrus_rpt_page_extractor.bat input.rpt "sections:14259,14260" output.txt output.pdf
REM   papyrus_rpt_page_extractor.bat input.rpt "all" output.txt output.pdf
REM
REM ============================================================================

REM Load environment variables if Migration_Environment.bat exists
if exist "..\Migration_Environment.bat" (
    call ..\Migration_Environment.bat
)

REM Get start time
set "START_TIME=%TIME%"
set "LOG_FILE=papyrus_rpt_page_extractor_LOG.txt"

echo Papyrus RPT Page Extractor Script started at: %DATE% %START_TIME%
echo -----------------------------------------------------------------------

REM Determine input method: command-line arguments or environment variables
if "%~4" NEQ "" (
    REM Command-line arguments provided
    set "INPUT_RPT=%~1"
    set "SELECTION_RULE=%~2"
    set "OUTPUT_TXT=%~3"
    set "OUTPUT_BINARY=%~4"
    set "INPUT_METHOD=Command-line"
) else if "%RPT_INPUT%" NEQ "" (
    REM Environment variables provided
    set "INPUT_RPT=%RPT_INPUT%"
    set "SELECTION_RULE=%RPT_SELECTION%"
    set "OUTPUT_TXT=%RPT_OUTPUT_TXT%"
    set "OUTPUT_BINARY=%RPT_OUTPUT_BINARY%"
    set "INPUT_METHOD=Environment variables"
) else (
    echo ERROR: No input parameters provided
    echo.
    echo Usage:
    echo   papyrus_rpt_page_extractor.bat ^<input_rpt^> ^<selection_rule^> ^<output_txt^> ^<output_binary^>
    echo.
    echo Example:
    echo   papyrus_rpt_page_extractor.bat input.rpt "pages:1-5" output.txt output.pdf
    echo.
    echo Or set environment variables:
    echo   set RPT_INPUT=input.rpt
    echo   set RPT_SELECTION=pages:1-5
    echo   set RPT_OUTPUT_TXT=output.txt
    echo   set RPT_OUTPUT_BINARY=output.pdf
    echo.
    pause
    exit /b 1
)

echo Input Method: %INPUT_METHOD%
echo Input RPT:     %INPUT_RPT%
echo Selection:     %SELECTION_RULE%
echo Output TXT:    %OUTPUT_TXT%
echo Output Binary: %OUTPUT_BINARY%
echo.

REM Check if input file exists
if not exist "%INPUT_RPT%" (
    echo ERROR: Input file not found: %INPUT_RPT%
    echo.
    pause
    exit /b 2
)

REM Check if executable exists
if not exist "papyrus_rpt_page_extractor.exe" (
    echo ERROR: papyrus_rpt_page_extractor.exe not found in current directory
    echo Please compile first using compile.bat
    echo.
    pause
    exit /b 3
)

REM Run the Papyrus RPT Page Extractor
echo Running extractor...
echo.
papyrus_rpt_page_extractor.exe "%INPUT_RPT%" "%SELECTION_RULE%" "%OUTPUT_TXT%" "%OUTPUT_BINARY%"
rem papyrus_rpt_page_extractor.bat d:\RPT\260271Q7.RPT "pages:1-2,4-5" D:\RPT\pages_1_2-4-5.txt D:\RPT\pages_1_2-4-5.pdf

REM Capture exit code
set EXTRACTOR_EXIT_CODE=%ERRORLEVEL%

echo.
echo -----------------------------------------------------------------------

REM Check exit code
if %EXTRACTOR_EXIT_CODE% EQU 0 (
    echo Status: SUCCESS
) else (
    echo Status: FAILED with exit code %EXTRACTOR_EXIT_CODE%
    echo.
    echo Exit codes:
    echo   1  - Invalid arguments
    echo   2  - File not found
    echo   3  - Invalid RPT file
    echo   4  - Read error
    echo   5  - Write error
    echo   6  - Invalid selection rule
    echo   7  - No pages selected
    echo   8  - Decompression error
    echo   9  - Memory error
    echo   10 - Unknown error
)

REM Capture end time and calculate duration
set "END_TIME=%TIME%"
echo Script finished at: %DATE% %END_TIME%

REM Robust calculation using New-TimeSpan to handle regional time formats
for /f "tokens=*" %%i in ('powershell -command "$start = [datetime]('%START_TIME%'.Replace(',', '.')); $end = [datetime]('%END_TIME%'.Replace(',', '.')); (New-TimeSpan -Start $start -End $end).ToString('hh\:mm\:ss')"') do set "DURATION=%%i"

echo Total Time Elapsed: %DURATION%

REM Logging Section
if %EXTRACTOR_EXIT_CODE% EQU 0 (
    echo [%DATE% %START_TIME%] RPT: %INPUT_RPT% ^| Selection: %SELECTION_RULE% ^| Duration: %DURATION% ^| Status: SUCCESS >> "%LOG_FILE%"
) else (
    echo [%DATE% %START_TIME%] RPT: %INPUT_RPT% ^| Selection: %SELECTION_RULE% ^| Duration: %DURATION% ^| Status: FAILED (Exit Code %EXTRACTOR_EXIT_CODE%) >> "%LOG_FILE%"
)

echo Log updated in %LOG_FILE%
echo.

REM Show output files if successful
if %EXTRACTOR_EXIT_CODE% EQU 0 (
    if exist "%OUTPUT_TXT%" (
        for %%A in ("%OUTPUT_TXT%") do echo TXT Output: %%~zA bytes - %OUTPUT_TXT%
    )
    if exist "%OUTPUT_BINARY%" (
        for %%A in ("%OUTPUT_BINARY%") do echo BIN Output: %%~zA bytes - %OUTPUT_BINARY%
    )
    echo.
)

pause
exit /b %EXTRACTOR_EXIT_CODE%
