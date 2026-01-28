cls
@Echo off
Call ..\Migration_environment.bat

:: --- 1. Capture Start Time ---
set "START_TIME=%TIME%"
set "LOG_FILE=Extract_ReportSpecies_Folders_MY_LOG.txt"

echo Extract_Folder_Species_MY Script started at: %DATE% %START_TIME%
echo ---------------------------------------------------------------------------
rem python Extract_Folder_Species.py --server localhost --database iSTSGUAT --windows-auth --output-dir outputMY --Country MY
python Extract_Folder_Species.py --server %SQLServer% --database %SQL-MY-Database% --windows-auth --output-dir %ReportSpecies_MY% --Country MY

:: --- 2. Capture End Time and Calculate Duration ---
echo ---------------------------------------------------------------------------

set "END_TIME=%TIME%"
echo Script finished at: %DATE% %END_TIME%

:: Robust calculation using New-TimeSpan to handle regional time formats
for /f "tokens=*" %%i in ('powershell -command "$start = [datetime]('%START_TIME%'.Replace(',', '.')); $end = [datetime]('%END_TIME%'.Replace(',', '.')); (New-TimeSpan -Start $start -End $end).ToString('hh\:mm\:ss')"') do set "DURATION=%%i"

echo Total Time Elapsed: %DURATION%
:: --- 3. Logging Section ---
:: We use ^| to tell Batch these are literal characters, not command pipes.
echo [%DATE% %START_TIME%] Country: SG ^| DB: %SQL-SG-Database% ^| Flag: %FLAG% ^| Duration: %DURATION% >> "%LOG_FILE%"

echo Log updated in %LOG_FILE%
pause