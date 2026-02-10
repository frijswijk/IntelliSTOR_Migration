@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM  setup_test_ldap.bat - Full Test LDAP Setup Workflow
REM ============================================================
REM
REM  Phases:
REM    1. Prepare CSVs          (prepare_test_ldap.py)
REM    2. Create groups in LDAP (ldap_integration.py add-groups)
REM    3. Create users in LDAP  (ldap_integration.py add-users)
REM    4. Assign users to groups(ldap_integration.py assign-groups)
REM    5. Export RID mapping     (ldap_integration.py export-rid-mapping)
REM    6. Translate permissions  (ldap_integration.py translate-permissions)
REM
REM  Edit the configuration below before running.
REM ============================================================

REM --- Configuration -------------------------------------------

REM LDAP connection
set LDAP_SERVER=YLDAPTEST-DC01.ldap1test.loc
set LDAP_PORT=636
set LDAP_USE_SSL=--use-ssl --ssl-no-verify
set LDAP_BIND_DN=cn=administrator,cn=Users,dc=ldap1test,dc=loc
set LDAP_PASSWORD=Linked3-Shorten-Crestless
set LDAP_BASE_DN=dc=ldap1test,dc=loc

REM Organizational Units
set GROUPS_OU=ou=Groups,dc=ldap1test,dc=loc
set USERS_OU=ou=Users,dc=ldap1test,dc=loc

REM Source data directory (original CSVs from IntelliSTOR export)
set SOURCE_DIR=S:\transfer\Freddievr\ForPhilipp\Users_SG

REM Number of test users to import (1, 5, 10, 100, or "all")
set USER_COUNT=10

REM Password strategy for new users (skip, default, or random)
set PASSWORD_STRATEGY=skip

REM Working directories (created automatically)
set PREPARED_DIR=.\ldap_import
set TRANSLATED_DIR=.\translated_permissions
set RID_MAPPING_FILE=.\rid_mapping.csv

REM --- End Configuration ---------------------------------------

echo ============================================================
echo  Test LDAP Setup Workflow
echo ============================================================
echo.
echo  Server:      %LDAP_SERVER%:%LDAP_PORT%
echo  Base DN:     %LDAP_BASE_DN%
echo  Source:      %SOURCE_DIR%
echo  Users:       %USER_COUNT%
echo  Password:    %PASSWORD_STRATEGY%
echo ============================================================
echo.

REM ==============================================================
REM  Phase 1: Prepare CSVs
REM ==============================================================
echo [Phase 1/6] Preparing CSVs...
echo.

python prepare_test_ldap.py ^
  --input-dir "%SOURCE_DIR%" ^
  --output-dir "%PREPARED_DIR%" ^
  --users %USER_COUNT%

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
  --server %LDAP_SERVER% ^
  --port %LDAP_PORT% ^
  %LDAP_USE_SSL% ^
  --bind-dn "%LDAP_BIND_DN%" ^
  --password "%LDAP_PASSWORD%" ^
  --base-dn "%LDAP_BASE_DN%" ^
  --groups-ou "%GROUPS_OU%" ^
  --csv "%PREPARED_DIR%\UserGroups.csv"

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
  --server %LDAP_SERVER% ^
  --port %LDAP_PORT% ^
  %LDAP_USE_SSL% ^
  --bind-dn "%LDAP_BIND_DN%" ^
  --password "%LDAP_PASSWORD%" ^
  --base-dn "%LDAP_BASE_DN%" ^
  --users-ou "%USERS_OU%" ^
  --csv "%PREPARED_DIR%\Users.csv" ^
  --password-strategy %PASSWORD_STRATEGY%

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
  --server %LDAP_SERVER% ^
  --port %LDAP_PORT% ^
  %LDAP_USE_SSL% ^
  --bind-dn "%LDAP_BIND_DN%" ^
  --password "%LDAP_PASSWORD%" ^
  --base-dn "%LDAP_BASE_DN%" ^
  --groups-ou "%GROUPS_OU%" ^
  --users-ou "%USERS_OU%" ^
  --groups-csv "%PREPARED_DIR%\UserGroups.csv" ^
  --users-csv "%PREPARED_DIR%\Users.csv" ^
  --assignments-csv "%PREPARED_DIR%\UserGroupAssignments.csv"

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
  --server %LDAP_SERVER% ^
  --port %LDAP_PORT% ^
  %LDAP_USE_SSL% ^
  --bind-dn "%LDAP_BIND_DN%" ^
  --password "%LDAP_PASSWORD%" ^
  --base-dn "%LDAP_BASE_DN%" ^
  --groups-ou "%GROUPS_OU%" ^
  --users-ou "%USERS_OU%" ^
  --output-file "%RID_MAPPING_FILE%"

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
  --rid-mapping "%RID_MAPPING_FILE%" ^
  --input-dir "%SOURCE_DIR%" ^
  --output-dir "%TRANSLATED_DIR%"

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
echo  Prepared CSVs:      %PREPARED_DIR%
echo  RID mapping:         %RID_MAPPING_FILE%
echo  Translated perms:    %TRANSLATED_DIR%
echo.
echo  Next steps:
echo    1. Verify groups/users in LDAP browser
echo    2. Spot-check translated permission CSVs
echo    3. Use translated CSVs for IntelliSTOR permission import
echo ============================================================

:end
echo.
pause
