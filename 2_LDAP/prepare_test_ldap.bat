CLS
@Echo off
call ..\Migration_Environment.bat
:: --- 1. Capture Start Time ---
set "START_TIME=%TIME%"
set "LOG_FILE=Prepare_Test_LDAP_LOG.txt"

echo Prepare Test LDAP CSVs started at: %DATE% %START_TIME%
echo ---------------------------------------------------------------------------
python prepare_test_ldap.py --input-dir "%Users-SG%" --output-dir "%LDAP_PreparedDir%" --users %LDAP_TestUserCount%

:: --- 2. Capture End Time and Calculate Duration ---
echo ---------------------------------------------------------------------------
set "END_TIME=%TIME%"
echo Script finished at: %DATE% %END_TIME%

:: Robust calculation using New-TimeSpan to handle regional time formats
for /f "tokens=*" %%i in ('powershell -command "$start = [datetime]('%START_TIME%'.Replace(',', '.')); $end = [datetime]('%END_TIME%'.Replace(',', '.')); (New-TimeSpan -Start $start -End $end).ToString('hh\:mm\:ss')"') do set "DURATION=%%i"

echo Total Time Elapsed: %DURATION%
:: --- 3. Logging Section ---
echo [%DATE% %START_TIME%] Users: %LDAP_TestUserCount% ^| Output: %LDAP_PreparedDir% ^| Duration: %DURATION% >> %LOG_FILE%

echo Log updated in %LOG_FILE%
pause
