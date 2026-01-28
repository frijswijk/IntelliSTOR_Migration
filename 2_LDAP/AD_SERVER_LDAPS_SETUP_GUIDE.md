# Active Directory LDAPS Configuration Guide

## Problem Summary

Your tests show:
- ✓ Port 389 is open (basic LDAP)
- ✓ Port 636 is open (but SSL handshake fails)
- ✗ LDAPS (SSL on port 636) is NOT configured
- ✗ StartTLS is NOT enabled
- ⚠ Server requires encryption ("StrongerAuthRequired" error)

**This is a server configuration issue.** The AD server needs a certificate for LDAPS to work.

## Step-by-Step Fix on Active Directory Server

### Step 1: Check if LDAPS Certificate Exists

**On the Active Directory server**, run PowerShell as Administrator:

```powershell
# Check for LDAP service certificate
Get-ChildItem -Path Cert:\LocalMachine\My | Where-Object {
    $_.EnhancedKeyUsageList.FriendlyName -contains "Server Authentication"
} | Format-Table Subject, Thumbprint, NotAfter -AutoSize
```

**Expected Output:**
- If you see certificates listed → Certificate exists, proceed to Step 2
- If empty → No certificate, proceed to Step 3 to create one

### Step 2: Verify LDAPS is Listening on Port 636

```powershell
# Check if LDAPS is listening
netstat -an | Select-String ":636"

# Check AD DS service
Get-Service -Name NTDS | Format-List *
```

**Expected Output:**
```
  TCP    0.0.0.0:636            0.0.0.0:0              LISTENING
  TCP    [::]:636               [::]:0                 LISTENING
```

If port 636 is listening but SSL fails, the certificate might be invalid or expired.

### Step 3: Check Certificate Details

```powershell
# Get domain controller name
$dc = $env:COMPUTERNAME

# Check certificate for this DC
Get-ChildItem -Path Cert:\LocalMachine\My | Where-Object {
    $_.Subject -like "*$dc*" -and
    $_.EnhancedKeyUsageList.FriendlyName -contains "Server Authentication"
} | Format-List Subject, Issuer, NotBefore, NotAfter, Thumbprint
```

**Check for issues:**
- ❌ Certificate expired (NotAfter is in the past)
- ❌ Certificate subject doesn't match server name
- ❌ Certificate is self-signed (Issuer = Subject) but not trusted

### Step 4: Create Self-Signed Certificate for LDAPS (Quick Fix)

If no valid certificate exists, create a self-signed certificate:

```powershell
# Get the fully qualified domain name
$fqdn = ([System.Net.Dns]::GetHostByName($env:COMPUTERNAME)).HostName

# Create self-signed certificate for LDAPS
$cert = New-SelfSignedCertificate `
    -DnsName $fqdn, $env:COMPUTERNAME `
    -CertStoreLocation "Cert:\LocalMachine\My" `
    -KeyUsage DigitalSignature, KeyEncipherment `
    -KeySpec KeyExchange `
    -Provider "Microsoft RSA SChannel Cryptographic Provider" `
    -NotAfter (Get-Date).AddYears(5)

Write-Host "Certificate created with thumbprint: $($cert.Thumbprint)"
Write-Host "Subject: $($cert.Subject)"
Write-Host "Expires: $($cert.NotAfter)"
```

**Important**: Write down the **thumbprint** - you'll need it later.

### Step 5: Restart Active Directory Services

After creating/importing a certificate, restart AD services:

```powershell
# Restart Active Directory Domain Services
Restart-Service -Name NTDS -Force

# Wait for service to start
Start-Sleep -Seconds 10

# Verify service is running
Get-Service -Name NTDS
```

**Expected Output:**
```
Status   Name               DisplayName
------   ----               -----------
Running  NTDS               Active Directory Domain Services
```

### Step 6: Test LDAPS is Working

From the **Active Directory server itself**:

```powershell
# Test LDAPS connection locally
$ldapConn = [ADSI]"LDAPS://localhost:636"
if ($ldapConn.Path) {
    Write-Host "✓ LDAPS is working on port 636" -ForegroundColor Green
    Write-Host "  Path: $($ldapConn.Path)"
} else {
    Write-Host "✗ LDAPS connection failed" -ForegroundColor Red
}
```

### Step 7: Enable LDAP Event Logging (for troubleshooting)

```powershell
# Enable LDAP diagnostic logging
New-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Services\NTDS\Diagnostics" `
    -Name "16 LDAP Interface Events" `
    -Value 2 `
    -PropertyType DWord `
    -Force

Write-Host "LDAP diagnostic logging enabled. Check Event Viewer > Applications and Services Logs > Directory Service"
```

### Step 8: Export Certificate for Client Use

If you created a self-signed certificate, export it for use with `--ssl-ca-cert`:

```powershell
# Find the certificate (replace thumbprint with yours from Step 4)
$thumbprint = "YOUR_THUMBPRINT_HERE"  # Replace this

$cert = Get-ChildItem -Path Cert:\LocalMachine\My\$thumbprint

# Export to file
$cert | Export-Certificate -FilePath "C:\ldap-ca-cert.cer" -Type CERT

Write-Host "Certificate exported to C:\ldap-ca-cert.cer"

# Convert to PEM format (if OpenSSL is available)
# certutil -encode C:\ldap-ca-cert.cer C:\ldap-ca-cert.pem
```

## Alternative: Use Enterprise CA Certificate

If you have an Enterprise Certificate Authority (CA), request a certificate properly:

### Option A: Auto-Enrollment (Preferred)

```powershell
# Check if auto-enrollment is configured
gpupdate /force
certutil -pulse
```

Wait 5-10 minutes for auto-enrollment to issue the certificate.

### Option B: Request Certificate Manually

1. Open **Certificate Manager** (certlm.msc)
2. Right-click **Personal → Certificates**
3. Select **All Tasks → Request New Certificate**
4. Choose **Domain Controller Authentication** template
5. Complete the wizard
6. Restart NTDS service (Step 5 above)

## Troubleshooting

### Issue: "netstat shows port 636 listening but SSL still fails"

**Check Event Viewer:**

1. Open **Event Viewer** (eventvwr.msc)
2. Navigate to: **Windows Logs → System**
3. Filter for **Source: NTDS** and **Event ID: 1220, 1221, 1222**

**Common Event IDs:**
- **1220**: LDAPS is not available (no valid certificate)
- **1221**: Certificate is not valid for LDAPS
- **1222**: Certificate is about to expire

**Solution**: Create/renew certificate (Step 4)

### Issue: "Certificate exists but LDAPS still doesn't work"

**Verify certificate requirements:**

```powershell
$cert = Get-ChildItem Cert:\LocalMachine\My | Where-Object {
    $_.Subject -like "*$env:COMPUTERNAME*"
} | Select-Object -First 1

# Check requirements
Write-Host "Certificate Details:"
Write-Host "  Subject: $($cert.Subject)"
Write-Host "  Expires: $($cert.NotAfter)"
Write-Host "  Key Usage: $($cert.Extensions | Where-Object {$_.Oid.FriendlyName -eq 'Key Usage'})"
Write-Host "  Enhanced Key Usage: $($cert.EnhancedKeyUsageList.FriendlyName -join ', ')"

# Certificate MUST have:
# - Key Usage: Digital Signature, Key Encipherment
# - Enhanced Key Usage: Server Authentication
# - Subject: CN=<DC FQDN>
```

**If requirements not met**: Delete invalid certificate and create new one (Step 4)

### Issue: "Self-signed certificate created but client still can't connect"

**This is expected!** Self-signed certificates need to be:

1. **Exported from server** (Step 8)
2. **Copied to client machine**
3. **Used with --ssl-ca-cert** flag:

```bash
python ldap_integration.py test-connection \
  --server 172.16.103.2 \
  --port 636 \
  --use-ssl \
  --ssl-ca-cert ldap-ca-cert.pem \
  --bind-dn "cn=administrator,cn=Users,dc=ldap1test,dc=loc" \
  --password "Linked3-Shorten-Crestless" \
  --base-dn "dc=ldap1test,dc=loc"
```

**OR** use `--ssl-no-verify` (testing only):

```bash
python ldap_integration.py test-connection \
  --server 172.16.103.2 \
  --port 636 \
  --use-ssl \
  --ssl-no-verify \
  --bind-dn "cn=administrator,cn=Users,dc=ldap1test,dc=loc" \
  --password "Linked3-Shorten-Crestless" \
  --base-dn "dc=ldap1test,dc=loc"
```

## Quick Validation Checklist

Run these on the **AD server** in order:

```powershell
# 1. Certificate exists?
Get-ChildItem Cert:\LocalMachine\My | Where-Object {$_.EnhancedKeyUsageList.FriendlyName -contains "Server Authentication"}

# 2. Port 636 listening?
netstat -an | Select-String ":636"

# 3. LDAPS works locally?
[ADSI]"LDAPS://localhost:636"

# 4. Event log errors?
Get-EventLog -LogName System -Source NTDS -Newest 10 | Where-Object {$_.EventID -in 1220,1221,1222}
```

**All checks pass?** → Try connection from client machine

## After Fixing on Server

Once LDAPS is configured on the server, test from your client machine:

```bash
# Test 1: With --ssl-no-verify (should work now)
python ldap_integration.py test-connection \
  --server 172.16.103.2 \
  --port 636 \
  --use-ssl \
  --ssl-no-verify \
  --bind-dn "cn=administrator,cn=Users,dc=ldap1test,dc=loc" \
  --password "Linked3-Shorten-Crestless" \
  --base-dn "dc=ldap1test,dc=loc"

# Test 2: With exported certificate (more secure)
python ldap_integration.py test-connection \
  --server 172.16.103.2 \
  --port 636 \
  --use-ssl \
  --ssl-ca-cert ldap-ca-cert.pem \
  --bind-dn "cn=administrator,cn=Users,dc=ldap1test,dc=loc" \
  --password "Linked3-Shorten-Crestless" \
  --base-dn "dc=ldap1test,dc=loc"
```

## Common Scenarios

### Scenario 1: Lab/Test Environment (Quick Fix)

```powershell
# Create self-signed cert
$cert = New-SelfSignedCertificate -DnsName ([System.Net.Dns]::GetHostByName($env:COMPUTERNAME)).HostName -CertStoreLocation Cert:\LocalMachine\My -Provider "Microsoft RSA SChannel Cryptographic Provider" -NotAfter (Get-Date).AddYears(5)

# Restart AD
Restart-Service NTDS -Force

# Use --ssl-no-verify on client
```

### Scenario 2: Production Environment (Proper Setup)

1. Request certificate from Enterprise CA
2. Ensure auto-enrollment is configured
3. Wait for certificate to be issued
4. Restart NTDS service
5. Export certificate for clients (if needed)

### Scenario 3: Domain Controller is Also CA

If your DC is also a CA:

```powershell
# Request cert from local CA
certreq -new -f C:\temp\request.inf C:\temp\request.req
certreq -submit -config "DC\CA" C:\temp\request.req C:\temp\cert.cer
certreq -accept C:\temp\cert.cer
```

## References

- **Microsoft Docs**: [How to enable LDAP over SSL with a third-party certification authority](https://docs.microsoft.com/en-us/troubleshoot/windows-server/identity/enable-ldap-over-ssl-3rd-certification-authority)
- **Event ID 1220**: LDAP over SSL not available
- **Port 636**: LDAPS default port
- **Port 389**: LDAP default port (can use StartTLS)

## Summary

**The issue is**: Your AD server doesn't have a valid certificate for LDAPS.

**The fix is**:
1. Create/request a certificate (Step 4)
2. Restart NTDS service (Step 5)
3. Test locally on server (Step 6)
4. Test from client with --ssl-no-verify (or with exported cert)

**Expected outcome**: WinError 10054 will disappear, and LDAPS will work!
