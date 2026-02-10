CLS
@Echo off
call ..\Migration_Environment.bat
setlocal enabledelayedexpansion
:: --- 1. Capture Start Time ---
set "START_TIME=%TIME%"
set "LOG_FILE=Setup_Test_LDAP_LOG.txt"

echo ============================================================
echo  Test LDAP Setup Workflow - started at: %DATE% %START_TIME%
echo ============================================================
echo.
echo  Server:      %LDAP_Server%:%LDAP_Port%
echo  Base DN:     %LDAP_BaseDN%
echo  Source:      %Users-SG%
echo  Users:       %LDAP_TestUserCount%
echo  Password:    %LDAP_PasswordStrategy%
echo ============================================================
echo.

REM ==============================================================
REM  Phase 1: Prepare CSVs
REM ==============================================================
echo [Phase 1/6] Preparing CSVs...
echo.

python prepare_test_ldap.py ^
  --input-dir "%Users-SG%" ^
  --output-dir "%LDAP_PreparedDir%" ^
  --users %LDAP_TestUserCount%

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Phase 1 failed. Aborting.
    goto :end
)

echo.
echo Phase 1 complete.
echo.

REM ==============================================================
REM  Phase 2: Create groups in LDAP
REM ==============================================================
echo [Phase 2/6] Creating groups in LDAP...
echo.

python ldap_integration.py add-groups ^
  --server %LDAP_Server% ^
  --port %LDAP_Port% ^
  %LDAP_SSL% ^
  --bind-dn "%LDAP_BindDN%" ^
  --password "%LDAP_Password%" ^
  --base-dn "%LDAP_BaseDN%" ^
  --groups-ou "%LDAP_GroupsOU%" ^
  --csv "%LDAP_PreparedDir%\UserGroups.csv"

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Phase 2 failed. Aborting.
    goto :end
)

echo.
echo Phase 2 complete.
echo.

REM ==============================================================
REM  Phase 3: Create users in LDAP
REM ==============================================================
echo [Phase 3/6] Creating users in LDAP...
echo.

python ldap_integration.py add-users ^
  --server %LDAP_Server% ^
  --port %LDAP_Port% ^
  %LDAP_SSL% ^
  --bind-dn "%LDAP_BindDN%" ^
  --password "%LDAP_Password%" ^
  --base-dn "%LDAP_BaseDN%" ^
  --users-ou "%LDAP_UsersOU%" ^
  --csv "%LDAP_PreparedDir%\Users.csv" ^
  --password-strategy %LDAP_PasswordStrategy%

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Phase 3 failed. Aborting.
    goto :end
)

echo.
echo Phase 3 complete.
echo.

REM ==============================================================
REM  Phase 4: Assign users to groups
REM ==============================================================
echo [Phase 4/6] Assigning users to groups...
echo.

python ldap_integration.py assign-groups ^
  --server %LDAP_Server% ^
  --port %LDAP_Port% ^
  %LDAP_SSL% ^
  --bind-dn "%LDAP_BindDN%" ^
  --password "%LDAP_Password%" ^
  --base-dn "%LDAP_BaseDN%" ^
  --groups-ou "%LDAP_GroupsOU%" ^
  --users-ou "%LDAP_UsersOU%" ^
  --groups-csv "%LDAP_PreparedDir%\UserGroups.csv" ^
  --users-csv "%LDAP_PreparedDir%\Users.csv" ^
  --assignments-csv "%LDAP_PreparedDir%\UserGroupAssignments.csv"

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Phase 4 failed. Aborting.
    goto :end
)

echo.
echo Phase 4 complete.
echo.

REM ==============================================================
REM  Phase 5: Export RID mapping
REM ==============================================================
echo [Phase 5/6] Exporting RID mapping...
echo.

python ldap_integration.py export-rid-mapping ^
  --server %LDAP_Server% ^
  --port %LDAP_Port% ^
  %LDAP_SSL% ^
  --bind-dn "%LDAP_BindDN%" ^
  --password "%LDAP_Password%" ^
  --base-dn "%LDAP_BaseDN%" ^
  --groups-ou "%LDAP_GroupsOU%" ^
  --users-ou "%LDAP_UsersOU%" ^
  --output-file "%LDAP_RidMapping%"

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Phase 5 failed. Aborting.
    goto :end
)

echo.
echo Phase 5 complete.
echo.

REM ==============================================================
REM  Phase 6: Translate permission CSVs
REM ==============================================================
echo [Phase 6/6] Translating permission CSVs...
echo.

python ldap_integration.py translate-permissions ^
  --rid-mapping "%LDAP_RidMapping%" ^
  --input-dir "%Users-SG%" ^
  --output-dir "%LDAP_TranslatedDir%"

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Phase 6 failed.
    goto :end
)

echo.
echo Phase 6 complete.
echo.

REM ==============================================================
REM  Done
REM ==============================================================
echo ============================================================
echo  ALL PHASES COMPLETE
echo ============================================================
echo.
echo  Prepared CSVs:      %LDAP_PreparedDir%
echo  RID mapping:         %LDAP_RidMapping%
echo  Translated perms:    %LDAP_TranslatedDir%
echo.
echo  Next steps:
echo    1. Verify groups/users in LDAP browser
echo    2. Spot-check translated permission CSVs
echo    3. Use translated CSVs for IntelliSTOR permission import
echo ============================================================

:end
:: --- 2. Capture End Time and Calculate Duration ---
echo ---------------------------------------------------------------------------
set "END_TIME=%TIME%"
echo Script finished at: %DATE% %END_TIME%

:: Robust calculation using New-TimeSpan to handle regional time formats
for /f "tokens=*" %%i in ('powershell -command "$start = [datetime]('%START_TIME%'.Replace(',', '.')); $end = [datetime]('%END_TIME%'.Replace(',', '.')); (New-TimeSpan -Start $start -End $end).ToString('hh\:mm\:ss')"') do set "DURATION=%%i"

echo Total Time Elapsed: %DURATION%
:: --- 3. Logging Section ---
echo [%DATE% %START_TIME%] Users: %LDAP_TestUserCount% ^| Server: %LDAP_Server% ^| Duration: %DURATION% >> %LOG_FILE%

echo Log updated in %LOG_FILE%
pause
