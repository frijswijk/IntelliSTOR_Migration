# Check-LDAPS.ps1
# Run this script on the Active Directory server as Administrator
# This will check if LDAPS is properly configured and help fix it

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "LDAPS Configuration Checker for Active Directory" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

# Check 1: Are we on a Domain Controller?
Write-Host "[1] Checking if this is a Domain Controller..." -ForegroundColor Yellow
$isDC = (Get-WmiObject -Class Win32_ComputerSystem).DomainRole -ge 4
if ($isDC) {
    Write-Host "    ✓ This is a Domain Controller" -ForegroundColor Green
} else {
    Write-Host "    ✗ This is NOT a Domain Controller" -ForegroundColor Red
    Write-Host "    Please run this script on the AD server (172.16.103.2)" -ForegroundColor Red
    exit 1
}

# Check 2: Is NTDS service running?
Write-Host ""
Write-Host "[2] Checking Active Directory service..." -ForegroundColor Yellow
$ntds = Get-Service -Name NTDS -ErrorAction SilentlyContinue
if ($ntds.Status -eq "Running") {
    Write-Host "    ✓ NTDS service is running" -ForegroundColor Green
} else {
    Write-Host "    ✗ NTDS service is not running: $($ntds.Status)" -ForegroundColor Red
    exit 1
}

# Check 3: Is port 636 listening?
Write-Host ""
Write-Host "[3] Checking if port 636 is listening..." -ForegroundColor Yellow
$port636 = netstat -an | Select-String ":636.*LISTENING"
if ($port636) {
    Write-Host "    ✓ Port 636 is listening" -ForegroundColor Green
    Write-Host "      $port636" -ForegroundColor Gray
} else {
    Write-Host "    ✗ Port 636 is NOT listening" -ForegroundColor Red
}

# Check 4: Does a valid certificate exist?
Write-Host ""
Write-Host "[4] Checking for LDAPS certificate..." -ForegroundColor Yellow
$certs = Get-ChildItem -Path Cert:\LocalMachine\My | Where-Object {
    $_.EnhancedKeyUsageList.FriendlyName -contains "Server Authentication"
}

if ($certs.Count -gt 0) {
    Write-Host "    ✓ Found $($certs.Count) certificate(s) with Server Authentication" -ForegroundColor Green
    foreach ($cert in $certs) {
        $expired = $cert.NotAfter -lt (Get-Date)
        $color = if ($expired) { "Red" } else { "Gray" }
        Write-Host ""
        Write-Host "      Subject:    $($cert.Subject)" -ForegroundColor $color
        Write-Host "      Issuer:     $($cert.Issuer)" -ForegroundColor $color
        Write-Host "      Thumbprint: $($cert.Thumbprint)" -ForegroundColor $color
        Write-Host "      Expires:    $($cert.NotAfter)" -ForegroundColor $color
        if ($expired) {
            Write-Host "      ⚠ EXPIRED!" -ForegroundColor Red
        } else {
            Write-Host "      ✓ Valid" -ForegroundColor Green
        }
    }
} else {
    Write-Host "    ✗ NO certificate found for LDAPS" -ForegroundColor Red
    Write-Host "      This is why LDAPS is not working!" -ForegroundColor Red
}

# Check 5: Test LDAPS locally
Write-Host ""
Write-Host "[5] Testing LDAPS connection locally..." -ForegroundColor Yellow
try {
    $ldapConn = [ADSI]"LDAPS://localhost:636"
    if ($ldapConn.Path) {
        Write-Host "    ✓ LDAPS connection successful!" -ForegroundColor Green
        Write-Host "      Path: $($ldapConn.Path)" -ForegroundColor Gray
    } else {
        Write-Host "    ✗ LDAPS connection failed (no path returned)" -ForegroundColor Red
    }
} catch {
    Write-Host "    ✗ LDAPS connection failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Check 6: Event log errors
Write-Host ""
Write-Host "[6] Checking Event Log for LDAPS errors..." -ForegroundColor Yellow
$events = Get-EventLog -LogName System -Source NTDS -Newest 20 -ErrorAction SilentlyContinue |
    Where-Object { $_.EventID -in 1220, 1221, 1222 }

if ($events) {
    Write-Host "    ⚠ Found LDAPS-related errors:" -ForegroundColor Yellow
    foreach ($event in $events) {
        Write-Host ""
        Write-Host "      Event ID: $($event.EventID)" -ForegroundColor Yellow
        Write-Host "      Time:     $($event.TimeGenerated)" -ForegroundColor Gray
        Write-Host "      Message:  $($event.Message.Substring(0, [Math]::Min(100, $event.Message.Length)))..." -ForegroundColor Gray
    }
} else {
    Write-Host "    ✓ No LDAPS errors in Event Log" -ForegroundColor Green
}

# Summary and Recommendations
Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "SUMMARY AND RECOMMENDATIONS" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

$validCert = $certs | Where-Object { $_.NotAfter -gt (Get-Date) }

if ($validCert.Count -gt 0 -and $port636) {
    Write-Host "✓ LDAPS appears to be configured correctly!" -ForegroundColor Green
    Write-Host ""
    Write-Host "If clients still can't connect, the certificate might be self-signed." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "OPTIONS FOR CLIENT:" -ForegroundColor Cyan
    Write-Host "  1. Use --ssl-no-verify flag (testing only, insecure)"
    Write-Host "  2. Export this certificate and use --ssl-ca-cert on client (secure)"
    Write-Host ""
    Write-Host "To export the certificate for clients:" -ForegroundColor Cyan
    Write-Host "  `$cert = Get-ChildItem Cert:\LocalMachine\My\$($validCert[0].Thumbprint)" -ForegroundColor Gray
    Write-Host "  `$cert | Export-Certificate -FilePath C:\ldap-ca-cert.cer -Type CERT" -ForegroundColor Gray
    Write-Host "  certutil -encode C:\ldap-ca-cert.cer C:\ldap-ca-cert.pem" -ForegroundColor Gray
    Write-Host ""

} elseif ($certs.Count -eq 0) {
    Write-Host "✗ NO CERTIFICATE FOUND - This is the problem!" -ForegroundColor Red
    Write-Host ""
    Write-Host "SOLUTION: Create a self-signed certificate for LDAPS" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Run these commands to fix:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  # Get server FQDN" -ForegroundColor Gray
    Write-Host "  `$fqdn = ([System.Net.Dns]::GetHostByName(`$env:COMPUTERNAME)).HostName" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  # Create certificate" -ForegroundColor Gray
    Write-Host "  `$cert = New-SelfSignedCertificate ```" -ForegroundColor Gray
    Write-Host "      -DnsName `$fqdn, `$env:COMPUTERNAME ```" -ForegroundColor Gray
    Write-Host "      -CertStoreLocation 'Cert:\LocalMachine\My' ```" -ForegroundColor Gray
    Write-Host "      -KeyUsage DigitalSignature, KeyEncipherment ```" -ForegroundColor Gray
    Write-Host "      -KeySpec KeyExchange ```" -ForegroundColor Gray
    Write-Host "      -Provider 'Microsoft RSA SChannel Cryptographic Provider' ```" -ForegroundColor Gray
    Write-Host "      -NotAfter (Get-Date).AddYears(5)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  # Restart AD service" -ForegroundColor Gray
    Write-Host "  Restart-Service -Name NTDS -Force" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  # Wait and test" -ForegroundColor Gray
    Write-Host "  Start-Sleep -Seconds 10" -ForegroundColor Gray
    Write-Host "  [ADSI]'LDAPS://localhost:636'" -ForegroundColor Gray
    Write-Host ""

} elseif ($validCert.Count -eq 0 -and $certs.Count -gt 0) {
    Write-Host "✗ Certificate exists but is EXPIRED!" -ForegroundColor Red
    Write-Host ""
    Write-Host "SOLUTION: Delete expired certificate and create a new one" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Run these commands:" -ForegroundColor Cyan
    Write-Host "  # Delete expired certificates" -ForegroundColor Gray
    Write-Host "  Get-ChildItem Cert:\LocalMachine\My | Where-Object {`$_.NotAfter -lt (Get-Date)} | Remove-Item" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  # Then follow steps above to create new certificate" -ForegroundColor Gray
    Write-Host ""
}

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""
Write-Host "For detailed instructions, see: AD_SERVER_LDAPS_SETUP_GUIDE.md" -ForegroundColor Cyan
Write-Host ""
