CLS
@Echo off
call ..\Migration_Environment.bat
:: --- 1. Capture Start Time ---
set "START_TIME=%TIME%"
set "LOG_FILE=Translate_Permissions_LOG.txt"

echo Translate Permission CSVs started at: %DATE% %START_TIME%
echo ---------------------------------------------------------------------------
python ldap_integration.py translate-permissions --rid-mapping "%LDAP_RidMapping%" --input-dir "%Users-SG%" --output-dir "%LDAP_TranslatedDir%"

:: --- 2. Capture End Time and Calculate Duration ---
echo ---------------------------------------------------------------------------
set "END_TIME=%TIME%"
echo Script finished at: %DATE% %END_TIME%

:: Robust calculation using New-TimeSpan to handle regional time formats
for /f "tokens=*" %%i in ('powershell -command "$start = [datetime]('%START_TIME%'.Replace(',', '.')); $end = [datetime]('%END_TIME%'.Replace(',', '.')); (New-TimeSpan -Start $start -End $end).ToString('hh\:mm\:ss')"') do set "DURATION=%%i"

echo Total Time Elapsed: %DURATION%
:: --- 3. Logging Section ---
echo [%DATE% %START_TIME%] Mapping: %LDAP_RidMapping% ^| Output: %LDAP_TranslatedDir% ^| Duration: %DURATION% >> %LOG_FILE%

echo Log updated in %LOG_FILE%
pause
