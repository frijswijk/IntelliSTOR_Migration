CLS
@Echo off
call ..\Migration_Environment.bat
:: --- 1. Capture Start Time ---
set "START_TIME=%TIME%"
set "LOG_FILE=Analyze_AFP_Resources_MY_LOG.txt"
set NAMESPACE=MY
rem set NAMESPACE=DEFAULT

echo Analyze_AFP_Resources_MY Script started at: %DATE% %START_TIME%
echo -----------------------------------------------------------------------
echo Source Folder: %AFP_Source_MY%
echo Output Folder: %AFP_Output%
echo Namespace: %NAMESPACE%
echo Version Compare: %AFP_VersionCompare%
echo -----------------------------------------------------------------------

rem Create output directory if it doesn't exist
if not exist "%AFP_Output%" mkdir "%AFP_Output%"

rem Build command with optional --version-compare flag
set "CMD=python Analyze_AFP_Resources.py --folder "%AFP_Source_MY%" --output-csv "%AFP_Output%\AFP_Resources_MY.csv" --namespace %NAMESPACE% --quiet"
if /I "%AFP_VersionCompare%"=="Yes" (
    set "CMD=%CMD% --version-compare"
)

rem Run the AFP Resource Analyzer
%CMD%

:: --- 2. Capture End Time and Calculate Duration ---
echo -----------------------------------------------------------------------
set "END_TIME=%TIME%"
echo Script finished at: %DATE% %END_TIME%

:: Robust calculation using New-TimeSpan to handle regional time formats
for /f "tokens=*" %%i in ('powershell -command "$start = [datetime]('%START_TIME%'.Replace(',', '.')); $end = [datetime]('%END_TIME%'.Replace(',', '.')); (New-TimeSpan -Start $start -End $end).ToString('hh\:mm\:ss')"') do set "DURATION=%%i"

echo Total Time Elapsed: %DURATION%
:: --- 3. Logging Section ---
:: We use ^| to tell Batch these are literal characters, not command pipes.
echo [%DATE% %START_TIME%] Country: MY ^| Source: %AFP_Source_MY% ^| Namespace: %NAMESPACE% ^| VersionCompare: %AFP_VersionCompare% ^| Duration: %DURATION% >> "%LOG_FILE%"

echo Log updated in %LOG_FILE%
pause
