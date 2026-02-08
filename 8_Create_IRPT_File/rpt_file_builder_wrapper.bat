CLS
@Echo off
REM ============================================================================
REM RPT File Builder - Wrapper Script (Non-Interactive)
REM ============================================================================
REM
REM Usage Option 1: With environment variables (set in Migration_Environment.bat)
REM   rpt_file_builder_wrapper.bat
REM
REM Usage Option 2: With command-line arguments
REM   rpt_file_builder_wrapper.bat <input_path> <output_rpt> [options]
REM
REM Examples:
REM   rpt_file_builder_wrapper.bat ./pages/ output.RPT --species 49626 --domain 1
REM   rpt_file_builder_wrapper.bat page_*.txt output.RPT --species 49626
REM   rpt_file_builder_wrapper.bat ./pages/ output.RPT --species 49626 --binary report.pdf
REM
REM ============================================================================

REM Load environment variables if Migration_Environment.bat exists
if exist "..\Migration_Environment.bat" (
    call ..\Migration_Environment.bat
)

REM Get start time
set "START_TIME=%TIME%"
set "LOG_FILE=rpt_file_builder_LOG.txt"

echo RPT File Builder Script started at: %DATE% %START_TIME%
echo -----------------------------------------------------------------------

REM Determine input method: command-line arguments or environment variables
if "%~2" NEQ "" (
    REM Command-line arguments provided
    set "INPUT_PATH=%~1"
    set "OUTPUT_RPT=%~2"
    set "EXTRA_ARGS=%~3 %~4 %~5 %~6 %~7 %~8 %~9"
    set "INPUT_METHOD=Command-line"
) else if "%RPT_BUILDER_INPUT%" NEQ "" (
    REM Environment variables provided
    set "INPUT_PATH=%RPT_BUILDER_INPUT%"
    set "OUTPUT_RPT=%RPT_BUILDER_OUTPUT%"
    set "SPECIES_ARG="
    set "DOMAIN_ARG="
    set "BINARY_ARG="
    set "TEMPLATE_ARG="

    if "%RPT_SPECIES%" NEQ "" set "SPECIES_ARG=--species %RPT_SPECIES%"
    if "%RPT_DOMAIN%" NEQ "" set "DOMAIN_ARG=--domain %RPT_DOMAIN%"
    if "%RPT_BINARY%" NEQ "" set "BINARY_ARG=--binary %RPT_BINARY%"
    if "%RPT_TEMPLATE%" NEQ "" set "TEMPLATE_ARG=--template %RPT_TEMPLATE%"

    set "EXTRA_ARGS=%SPECIES_ARG% %DOMAIN_ARG% %BINARY_ARG% %TEMPLATE_ARG%"
    set "INPUT_METHOD=Environment variables"
) else (
    echo ERROR: No input parameters provided
    echo.
    echo Usage:
    echo   rpt_file_builder_wrapper.bat ^<input_path^> ^<output_rpt^> [options]
    echo.
    echo Example:
    echo   rpt_file_builder_wrapper.bat ./pages/ output.RPT --species 49626 --domain 1
    echo.
    echo Or set environment variables:
    echo   set RPT_BUILDER_INPUT=./pages/
    echo   set RPT_BUILDER_OUTPUT=output.RPT
    echo   set RPT_SPECIES=49626
    echo   set RPT_DOMAIN=1
    echo.
    pause
    exit /b 1
)

echo Input Method:  %INPUT_METHOD%
echo Input Path:    %INPUT_PATH%
echo Output RPT:    %OUTPUT_RPT%
echo Extra Args:    %EXTRA_ARGS%
echo.

REM Check if input path exists
if not exist "%INPUT_PATH%" (
    echo ERROR: Input path not found: %INPUT_PATH%
    echo.
    pause
    exit /b 2
)

REM Check if executable exists
if not exist "rpt_file_builder.exe" (
    echo ERROR: rpt_file_builder.exe not found in current directory
    echo Please compile first or ensure the executable is in the correct location
    echo.
    pause
    exit /b 3
)

REM Run the RPT File Builder
echo Running RPT File Builder...
echo.
rpt_file_builder.exe -o "%OUTPUT_RPT%" %EXTRA_ARGS% "%INPUT_PATH%"

REM Capture exit code
set BUILDER_EXIT_CODE=%ERRORLEVEL%

echo.
echo -----------------------------------------------------------------------

REM Check exit code
if %BUILDER_EXIT_CODE% EQU 0 (
    echo Status: SUCCESS
) else (
    echo Status: FAILED with exit code %BUILDER_EXIT_CODE%
    echo.
    echo Common exit codes:
    echo   1  - Invalid arguments or input
    echo   2  - File not found or cannot open
    echo   3  - Parse error (invalid page format)
    echo   4  - Write error (cannot create output)
    echo   5  - Compression error
)

REM Capture end time and calculate duration
set "END_TIME=%TIME%"
echo Script finished at: %DATE% %END_TIME%

REM Robust calculation using New-TimeSpan to handle regional time formats
for /f "tokens=*" %%i in ('powershell -command "$start = [datetime]('%START_TIME%'.Replace(',', '.')); $end = [datetime]('%END_TIME%'.Replace(',', '.')); (New-TimeSpan -Start $start -End $end).ToString('hh\:mm\:ss')"') do set "DURATION=%%i"

echo Total Time Elapsed: %DURATION%

REM Logging Section
if %BUILDER_EXIT_CODE% EQU 0 (
    echo [%DATE% %START_TIME%] Input: %INPUT_PATH% ^| Output: %OUTPUT_RPT% ^| Duration: %DURATION% ^| Status: SUCCESS >> "%LOG_FILE%"
) else (
    echo [%DATE% %START_TIME%] Input: %INPUT_PATH% ^| Output: %OUTPUT_RPT% ^| Duration: %DURATION% ^| Status: FAILED (Exit Code %BUILDER_EXIT_CODE%) >> "%LOG_FILE%"
)

echo Log updated in %LOG_FILE%
echo.

REM Show output file size if successful
if %BUILDER_EXIT_CODE% EQU 0 (
    if exist "%OUTPUT_RPT%" (
        for %%A in ("%OUTPUT_RPT%") do echo RPT Output: %%~zA bytes - %OUTPUT_RPT%
        echo.

        REM Show basic info about the created RPT
        echo RPT file created successfully!
        echo You can verify it with: rpt_file_builder.exe --info -o verify.RPT "%INPUT_PATH%"
        echo.
    )
)

pause
exit /b %BUILDER_EXIT_CODE%
