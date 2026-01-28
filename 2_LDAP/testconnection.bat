@echo off
echo ============================================================
echo LDAP SSL Connection Test with Self-Signed Certificates
echo ============================================================
echo.

echo Option 1: Skip verification (TESTING ONLY - INSECURE)
echo ------------------------------------------------------------
python ldap_integration.py test-connection ^
  --server YLDAPTEST-DC01.ldap1test.loc ^
  --port 636 ^
  --use-ssl ^
  --ssl-no-verify ^
  --bind-dn "cn=administrator,cn=Users,dc=ldap1test,dc=loc" ^
  --password "Linked3-Shorten-Crestless" ^
  --base-dn "dc=ldap1test,dc=loc"

echo.
echo.
echo Option 2: With custom CA certificate (SECURE)
echo ------------------------------------------------------------
echo First export certificate with:
echo   openssl s_client -connect YLDAPTEST-DC01.ldap1test.loc:636 -showcerts ^< nul 2^>^&1 ^| openssl x509 -outform PEM ^> ca-cert.pem
echo.
echo Then test connection:
rem python ldap_integration.py test-connection ^
rem   --server YLDAPTEST-DC01.ldap1test.loc ^
rem   --port 636 ^
rem   --use-ssl ^
rem   --ssl-ca-cert ca-cert.pem ^
rem   --bind-dn "cn=administrator,cn=Users,dc=ldap1test,dc=loc" ^
rem   --password "Linked3-Shorten-Crestless" ^
rem   --base-dn "dc=ldap1test,dc=loc"

echo.
pause
