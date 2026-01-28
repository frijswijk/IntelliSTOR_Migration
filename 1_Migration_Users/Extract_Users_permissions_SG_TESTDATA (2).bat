CLS
@Echo off
call ..\Migration_Environment.bat
:: --- 1. Capture Start Time ---
set "START_TIME=%TIME%"
set "LOG_FILE=Extract_Users_Permissions_SG_LOG_TESTDATA.txt"
set FLAG=
set FLAG=--TESTDATA

echo Extract TESTDATA_users_Permissions_SG Script started at: %DATE% %START_TIME%
echo ---------------------------------------------------------------------------

rem python extract_users_permissions.py --server localhost --database iSTSGUAT --windows-auth --output Users_SG
python Extract_Users_Permissions.py --server %SQLServer% --database %SQL-SG-Database% --output %Users-TEST% --windows-auth --quiet %FLAG%

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