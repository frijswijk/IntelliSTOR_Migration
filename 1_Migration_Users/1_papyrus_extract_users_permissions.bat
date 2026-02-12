CLS
@Echo off
call ..\Migration_Environment.bat

REM Get start time
set "START_TIME=%TIME%"
set "LOG_FILE=papyrus_extract_users_permissions_LOG.txt"

echo Papyrus Extract Users Permissions Script started at: %DATE% %START_TIME%
echo -----------------------------------------------------------------------

REM Run the Papyrus C++ extractor
papyrus_extract_users_permissions.exe --server %SQLServer% --database %SQL-SG-Database% --output %Users-SG% --windows-auth

REM Capture end time and calculate duration
echo -----------------------------------------------------------------------
set "END_TIME=%TIME%"
echo Script finished at: %DATE% %END_TIME%

REM Robust calculation using New-TimeSpan to handle regional time formats
for /f "tokens=*" %%i in ('powershell -command "$start = [datetime]('%START_TIME%'.Replace(',', '.')); $end = [datetime]('%END_TIME%'.Replace(',', '.')); (New-TimeSpan -Start $start -End $end).ToString('hh\:mm\:ss')"') do set "DURATION=%%i"

echo Total Time Elapsed: %DURATION%

REM Logging Section
echo [%DATE% %START_TIME%] Country: SG ^| DB: %SQL-SG-Database% ^| Duration: %DURATION% >> "%LOG_FILE%"

echo Log updated in %LOG_FILE%
pause
