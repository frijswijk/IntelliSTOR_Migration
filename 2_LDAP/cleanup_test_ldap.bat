CLS
@Echo off
call ..\Migration_Environment.bat
:: --- 1. Capture Start Time ---
set "START_TIME=%TIME%"
set "LOG_FILE=Cleanup_Test_LDAP_LOG.txt"

echo ============================================================
echo  Cleanup Test LDAP - started at: %DATE% %START_TIME%
echo ============================================================
echo.
echo  This will DELETE all imported users and groups from LDAP.
echo  Server: %LDAP_Server%:%LDAP_Port%
echo.
echo  Press Ctrl+C to abort, or
pause

echo.
echo [Step 1/2] Deleting users...
echo.

python ldap_integration.py delete-users ^
  --server %LDAP_Server% ^
  --port %LDAP_Port% ^
  %LDAP_SSL% ^
  --bind-dn "%LDAP_BindDN%" ^
  --password "%LDAP_Password%" ^
  --base-dn "%LDAP_BaseDN%" ^
  --users-ou "%LDAP_UsersOU%" ^
  --csv "%LDAP_PreparedDir%\Users.csv"

echo.
echo [Step 2/2] Deleting groups...
echo.

python ldap_integration.py delete-groups ^
  --server %LDAP_Server% ^
  --port %LDAP_Port% ^
  %LDAP_SSL% ^
  --bind-dn "%LDAP_BindDN%" ^
  --password "%LDAP_Password%" ^
  --base-dn "%LDAP_BaseDN%" ^
  --groups-ou "%LDAP_GroupsOU%" ^
  --csv "%LDAP_PreparedDir%\UserGroups.csv"

:: --- 2. Capture End Time and Calculate Duration ---
echo ---------------------------------------------------------------------------
set "END_TIME=%TIME%"
echo Script finished at: %DATE% %END_TIME%

:: Robust calculation using New-TimeSpan to handle regional time formats
for /f "tokens=*" %%i in ('powershell -command "$start = [datetime]('%START_TIME%'.Replace(',', '.')); $end = [datetime]('%END_TIME%'.Replace(',', '.')); (New-TimeSpan -Start $start -End $end).ToString('hh\:mm\:ss')"') do set "DURATION=%%i"

echo Total Time Elapsed: %DURATION%
:: --- 3. Logging Section ---
echo [%DATE% %START_TIME%] Server: %LDAP_Server% ^| Duration: %DURATION% >> %LOG_FILE%

echo Log updated in %LOG_FILE%
echo.
echo Done. You can now re-run setup_test_ldap.bat to recreate everything.
pause
