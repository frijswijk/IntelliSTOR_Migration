CLS
@Echo off
call ..\Migration_Environment.bat
:: --- 1. Capture Start Time ---
set "START_TIME=%TIME%"
set "LOG_FILE=Extract_RIDs_LOG.txt"
set "OUTPUT_FILE=%Users-SG%\unique_rids.csv"

echo Extract Unique RIDs started at: %DATE% %START_TIME%
echo ---------------------------------------------------------------------------
echo Input Folder: %Users-SG%
echo Output File:  %OUTPUT_FILE%
echo ---------------------------------------------------------------------------
extract_unique_rids.exe "%Users-SG%" "%OUTPUT_FILE%"

:: --- 2. Capture End Time and Calculate Duration ---
echo ---------------------------------------------------------------------------
set "END_TIME=%TIME%"
echo Script finished at: %DATE% %END_TIME%

:: Robust calculation using New-TimeSpan to handle regional time formats
for /f "tokens=*" %%i in ('powershell -command "$start = [datetime]('%START_TIME%'.Replace(',', '.')); $end = [datetime]('%END_TIME%'.Replace(',', '.')); (New-TimeSpan -Start $start -End $end).ToString('hh\:mm\:ss')"') do set "DURATION=%%i"

echo Total Time Elapsed: %DURATION%
:: --- 3. Logging Section ---
echo [%DATE% %START_TIME%] Source: %Users-SG% ^| Output: %OUTPUT_FILE% ^| Duration: %DURATION% >> %LOG_FILE%

echo Log updated in %LOG_FILE%
pause
