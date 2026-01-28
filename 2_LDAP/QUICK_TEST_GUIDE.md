# Quick Test Guide for SSL Certificate Verification

## Prerequisites
- Copy entire `2_LDAP` directory to test machine with LDAP server access
- Ensure Python 3.7+ installed
- Install dependencies: `pip install ldap3 flask flask-cors`

## Test 1: Skip Verification (Quick Win)

Run the batch file:
```batch
testconnection.bat
```

**Expected Output**:
```
WARNING - ======================================================================
WARNING - SECURITY WARNING: SSL certificate verification is disabled!
WARNING - This is INSECURE and should only be used for testing.
WARNING - Man-in-the-middle attacks are possible.
WARNING - ======================================================================
INFO - SSL/TLS enabled
INFO - Certificate verification: DISABLED (insecure)
INFO - Testing LDAP connection...
INFO - Connection successful
INFO - Server: Microsoft Active Directory
```

## Test 2: Export CA Certificate

```bash
openssl s_client -connect YLDAPTEST-DC01.ldap1test.loc:636 -showcerts < nul 2>&1 | openssl x509 -outform PEM > ca-cert.pem
```

Verify certificate was created:
```bash
dir ca-cert.pem
openssl x509 -in ca-cert.pem -text -noout
```

## Test 3: Custom CA Certificate

Edit `testconnection.bat`:
- Uncomment lines 26-33 (Option 2)
- Comment out lines 9-16 (Option 1)

Run:
```batch
testconnection.bat
```

**Expected Output**:
```
INFO - SSL/TLS enabled
INFO - Certificate verification: Custom CA
INFO -   CA cert file: ca-cert.pem
INFO - Testing LDAP connection...
INFO - Connection successful
INFO - Server: Microsoft Active Directory
```

(No security warning - proper verification used)

## Test 4: Error Handling

### Test Mutual Exclusivity
```bash
python ldap_integration.py test-connection ^
  --server YLDAPTEST-DC01.ldap1test.loc ^
  --port 636 ^
  --use-ssl ^
  --ssl-no-verify ^
  --ssl-ca-cert ca-cert.pem ^
  --bind-dn "cn=administrator,cn=Users,dc=ldap1test,dc=loc" ^
  --password "Linked3-Shorten-Crestless" ^
  --base-dn "dc=ldap1test,dc=loc"
```

**Expected**: Error about conflicting options

### Test Missing Certificate File
```bash
python ldap_integration.py test-connection ^
  --server YLDAPTEST-DC01.ldap1test.loc ^
  --port 636 ^
  --use-ssl ^
  --ssl-ca-cert nonexistent.pem ^
  --bind-dn "cn=administrator,cn=Users,dc=ldap1test,dc=loc" ^
  --password "Linked3-Shorten-Crestless" ^
  --base-dn "dc=ldap1test,dc=loc"
```

**Expected**: Error about file not found

## Test 5: Full Workflow Commands

### Test Groups Import
```bash
python ldap_integration.py add-groups ^
  --server YLDAPTEST-DC01.ldap1test.loc ^
  --port 636 ^
  --use-ssl ^
  --ssl-no-verify ^
  --bind-dn "cn=administrator,cn=Users,dc=ldap1test,dc=loc" ^
  --password "Linked3-Shorten-Crestless" ^
  --base-dn "dc=ldap1test,dc=loc" ^
  --groups-ou "ou=Groups,dc=ldap1test,dc=loc" ^
  --csv UserGroups.csv ^
  --dry-run
```

**Expected**: Dry-run completes successfully with security warning

### Test Users Import
```bash
python ldap_integration.py add-users ^
  --server YLDAPTEST-DC01.ldap1test.loc ^
  --port 636 ^
  --use-ssl ^
  --ssl-ca-cert ca-cert.pem ^
  --bind-dn "cn=administrator,cn=Users,dc=ldap1test,dc=loc" ^
  --password "Linked3-Shorten-Crestless" ^
  --base-dn "dc=ldap1test,dc=loc" ^
  --users-ou "ou=Users,dc=ldap1test,dc=loc" ^
  --csv Users.csv ^
  --password-strategy skip ^
  --dry-run
```

**Expected**: Dry-run completes successfully, no security warning (using CA cert)

## Test 6: Backward Compatibility

Test non-SSL connection (should work as before):
```bash
python ldap_integration.py test-connection ^
  --server YLDAPTEST-DC01.ldap1test.loc ^
  --port 389 ^
  --bind-dn "cn=administrator,cn=Users,dc=ldap1test,dc=loc" ^
  --password "Linked3-Shorten-Crestless" ^
  --base-dn "dc=ldap1test,dc=loc"
```

**Expected**: Connection works, no SSL-related messages

## Success Checklist

- [ ] Test 1: Skip verification works, security warning displayed
- [ ] Test 2: Certificate export successful
- [ ] Test 3: Custom CA certificate works, no security warning
- [ ] Test 4: Error handling catches invalid configurations
- [ ] Test 5: Full workflow commands work with new SSL options
- [ ] Test 6: Backward compatibility maintained

## Troubleshooting

### Connection Refused
- Check LDAP server is running
- Verify port 636 is open
- Check firewall settings

### Certificate Export Fails
- Ensure OpenSSL is installed
- Verify server hostname is correct
- Check port 636 is accessible

### Certificate Verification Fails (with --ssl-ca-cert)
- Verify certificate file is PEM format
- Check certificate matches server
- Try re-exporting certificate

## Files to Check

After implementation, verify these files exist:
- `ldap_integration.py` (modified)
- `testconnection.bat` (modified)
- `README_LDAP_Integration.md` (modified)
- `SSL_IMPLEMENTATION_SUMMARY.md` (new)
- `QUICK_TEST_GUIDE.md` (this file)

## Support

If issues persist:
1. Check `ldap_integration.log` for detailed errors
2. Review `SSL_IMPLEMENTATION_SUMMARY.md` for implementation details
3. Consult README section "SSL Certificate Verification"
