@echo off
echo ============================================================
echo LDAP Browser - Starting Flask API
echo ============================================================
echo.
echo This will start the LDAP Browser API on http://127.0.0.1:5000
echo After starting, open ldap_browser.html in your web browser
echo.
echo Press Ctrl+C to stop the server
echo ============================================================
echo.

python ldap_integration.py serve-browser ^
  --server YLDAPTEST-DC01.ldap1test.loc ^
  --port 636 ^
  --use-ssl ^
  --ssl-no-verify ^
  --bind-dn "cn=administrator,cn=Users,dc=ldap1test,dc=loc" ^
  --password "Linked3-Shorten-Crestless" ^
  --base-dn "dc=ldap1test,dc=loc"

pause
