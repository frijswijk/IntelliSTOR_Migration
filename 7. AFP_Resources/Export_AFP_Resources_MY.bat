CLS
@Echo off
call ..\Migration_Environment.bat
:: --- 1. Capture Start Time ---
set "START_TIME=%TIME%"
set "LOG_FILE=Export_AFP_Resources_MY_LOG.txt"

echo Export_AFP_Resources_MY Script started at: %DATE% %START_TIME%
echo -----------------------------------------------------------------------
echo Input CSV: %AFP_Output%\AFP_Resources_MY.csv
echo Export Folder: %AFP_Export_MY%
echo -----------------------------------------------------------------------

rem Create output directory if it doesn't exist
if not exist "%AFP_Export_MY%" mkdir "%AFP_Export_MY%"

rem Run the AFP Resource Exporter
python AFP_Resource_Exporter.py --input-csv "%AFP_Output%\AFP_Resources_MY.csv" --output-folder "%AFP_Export_MY%" --quiet

:: --- 2. Capture End Time and Calculate Duration ---
echo -----------------------------------------------------------------------
set "END_TIME=%TIME%"
echo Script finished at: %DATE% %END_TIME%

:: Robust calculation using New-TimeSpan to handle regional time formats
for /f "tokens=*" %%i in ('powershell -command "$start = [datetime]('%START_TIME%'.Replace(',', '.')); $end = [datetime]('%END_TIME%'.Replace(',', '.')); (New-TimeSpan -Start $start -End $end).ToString('hh\:mm\:ss')"') do set "DURATION=%%i"

echo Total Time Elapsed: %DURATION%
:: --- 3. Logging Section ---
:: We use ^| to tell Batch these are literal characters, not command pipes.
echo [%DATE% %START_TIME%] Country: MY ^| CSV: %AFP_Output%\AFP_Resources_MY.csv ^| Export: %AFP_Export_MY% ^| Duration: %DURATION% >> "%LOG_FILE%"

echo Log updated in %LOG_FILE%
pause
