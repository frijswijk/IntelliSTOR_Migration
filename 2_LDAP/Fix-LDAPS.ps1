# Fix-LDAPS.ps1
# Automatically creates a self-signed certificate for LDAPS and enables it
# Run this on the Active Directory server as Administrator

param(
    [switch]$AutoRestart = $false
)

Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "LDAPS Quick Fix - Create Self-Signed Certificate" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "✗ This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "  Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Check if this is a Domain Controller
$isDC = (Get-WmiObject -Class Win32_ComputerSystem).DomainRole -ge 4
if (-not $isDC) {
    Write-Host "✗ This is NOT a Domain Controller!" -ForegroundColor Red
    Write-Host "  This script must be run on the AD server" -ForegroundColor Yellow
    exit 1
}

Write-Host "✓ Running as Administrator on Domain Controller" -ForegroundColor Green
Write-Host ""

# Get server information
Write-Host "Gathering server information..." -ForegroundColor Yellow
$computerName = $env:COMPUTERNAME
$fqdn = ([System.Net.Dns]::GetHostByName($computerName)).HostName
$domainDN = ([ADSI]"LDAP://RootDSE").defaultNamingContext

Write-Host "  Computer Name: $computerName" -ForegroundColor Gray
Write-Host "  FQDN:          $fqdn" -ForegroundColor Gray
Write-Host "  Domain DN:     $domainDN" -ForegroundColor Gray
Write-Host ""

# Check for existing valid certificate
Write-Host "Checking for existing LDAPS certificates..." -ForegroundColor Yellow
$existingCerts = Get-ChildItem -Path Cert:\LocalMachine\My | Where-Object {
    $_.EnhancedKeyUsageList.FriendlyName -contains "Server Authentication" -and
    $_.NotAfter -gt (Get-Date)
}

if ($existingCerts.Count -gt 0) {
    Write-Host "  ⚠ Found $($existingCerts.Count) valid certificate(s)" -ForegroundColor Yellow
    foreach ($cert in $existingCerts) {
        Write-Host "    Subject: $($cert.Subject)" -ForegroundColor Gray
        Write-Host "    Expires: $($cert.NotAfter)" -ForegroundColor Gray
    }
    Write-Host ""
    $continue = Read-Host "Do you want to create a new certificate anyway? (y/N)"
    if ($continue -ne "y" -and $continue -ne "Y") {
        Write-Host ""
        Write-Host "Certificate already exists. If LDAPS still doesn't work:" -ForegroundColor Yellow
        Write-Host "  1. Try restarting NTDS service: Restart-Service NTDS -Force" -ForegroundColor Gray
        Write-Host "  2. Check Event Viewer for errors: Get-EventLog -LogName System -Source NTDS -Newest 10" -ForegroundColor Gray
        Write-Host "  3. Test locally: [ADSI]'LDAPS://localhost:636'" -ForegroundColor Gray
        exit 0
    }
}

# Create self-signed certificate
Write-Host ""
Write-Host "Creating self-signed certificate for LDAPS..." -ForegroundColor Yellow

try {
    $cert = New-SelfSignedCertificate `
        -DnsName $fqdn, $computerName `
        -CertStoreLocation "Cert:\LocalMachine\My" `
        -KeyUsage DigitalSignature, KeyEncipherment `
        -KeySpec KeyExchange `
        -Provider "Microsoft RSA SChannel Cryptographic Provider" `
        -NotAfter (Get-Date).AddYears(5) `
        -FriendlyName "LDAPS Self-Signed Certificate for $fqdn" `
        -ErrorAction Stop

    Write-Host "  ✓ Certificate created successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Certificate Details:" -ForegroundColor Cyan
    Write-Host "    Thumbprint: $($cert.Thumbprint)" -ForegroundColor Gray
    Write-Host "    Subject:    $($cert.Subject)" -ForegroundColor Gray
    Write-Host "    Issuer:     $($cert.Issuer)" -ForegroundColor Gray
    Write-Host "    Expires:    $($cert.NotAfter)" -ForegroundColor Gray
    Write-Host ""

    # Export certificate for clients
    $exportPath = "C:\ldap-ca-cert.cer"
    $pemPath = "C:\ldap-ca-cert.pem"

    Write-Host "Exporting certificate for client use..." -ForegroundColor Yellow
    $cert | Export-Certificate -FilePath $exportPath -Type CERT -Force | Out-Null
    Write-Host "  ✓ Certificate exported to: $exportPath" -ForegroundColor Green

    # Try to convert to PEM format
    try {
        certutil -encode $exportPath $pemPath 2>&1 | Out-Null
        Write-Host "  ✓ PEM format created: $pemPath" -ForegroundColor Green
        Write-Host ""
        Write-Host "  Copy $pemPath to your client machine" -ForegroundColor Cyan
        Write-Host "  and use with --ssl-ca-cert flag" -ForegroundColor Cyan
    } catch {
        Write-Host "  ⚠ Could not create PEM format (certutil may not be available)" -ForegroundColor Yellow
    }

} catch {
    Write-Host "  ✗ Failed to create certificate: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Restart NTDS service
Write-Host ""
Write-Host "Certificate created. Now need to restart Active Directory service..." -ForegroundColor Yellow

if ($AutoRestart) {
    $restart = "y"
} else {
    $restart = Read-Host "Restart NTDS service now? This will briefly interrupt AD services (y/N)"
}

if ($restart -eq "y" -or $restart -eq "Y") {
    Write-Host ""
    Write-Host "Restarting Active Directory Domain Services..." -ForegroundColor Yellow

    try {
        Restart-Service -Name NTDS -Force -ErrorAction Stop
        Write-Host "  ✓ Service restart initiated" -ForegroundColor Green

        Write-Host ""
        Write-Host "Waiting for service to start..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5

        $ntds = Get-Service -Name NTDS
        if ($ntds.Status -eq "Running") {
            Write-Host "  ✓ NTDS service is running" -ForegroundColor Green
        } else {
            Write-Host "  ⚠ NTDS service status: $($ntds.Status)" -ForegroundColor Yellow
            Write-Host "    Waiting longer..." -ForegroundColor Yellow
            Start-Sleep -Seconds 10
        }

    } catch {
        Write-Host "  ✗ Failed to restart service: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "    You can manually restart later: Restart-Service NTDS -Force" -ForegroundColor Yellow
    }

    # Test LDAPS
    Write-Host ""
    Write-Host "Testing LDAPS connection..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5

    try {
        $ldapConn = [ADSI]"LDAPS://localhost:636"
        if ($ldapConn.Path) {
            Write-Host "  ✓✓✓ LDAPS IS WORKING! ✓✓✓" -ForegroundColor Green
            Write-Host "  Path: $($ldapConn.Path)" -ForegroundColor Gray
        } else {
            Write-Host "  ✗ LDAPS connection failed (no path returned)" -ForegroundColor Red
        }
    } catch {
        Write-Host "  ✗ LDAPS connection failed: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "    Wait a few more seconds and try: [ADSI]'LDAPS://localhost:636'" -ForegroundColor Yellow
    }

} else {
    Write-Host ""
    Write-Host "⚠ Service NOT restarted" -ForegroundColor Yellow
    Write-Host "  Certificate is created but LDAPS won't work until you restart NTDS" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  To restart manually:" -ForegroundColor Cyan
    Write-Host "    Restart-Service -Name NTDS -Force" -ForegroundColor Gray
    Write-Host ""
}

# Final instructions
Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "NEXT STEPS" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""

if (Test-Path $pemPath) {
    Write-Host "Certificate files created:" -ForegroundColor Green
    Write-Host "  CER format: $exportPath" -ForegroundColor Gray
    Write-Host "  PEM format: $pemPath" -ForegroundColor Gray
    Write-Host ""
    Write-Host "On your CLIENT machine, test with:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  # Option 1: Skip verification (testing only)" -ForegroundColor Gray
    Write-Host "  python ldap_integration.py test-connection ```" -ForegroundColor Gray
    Write-Host "    --server 172.16.103.2 ```" -ForegroundColor Gray
    Write-Host "    --port 636 ```" -ForegroundColor Gray
    Write-Host "    --use-ssl ```" -ForegroundColor Gray
    Write-Host "    --ssl-no-verify ```" -ForegroundColor Gray
    Write-Host "    --bind-dn 'cn=administrator,cn=Users,dc=ldap1test,dc=loc' ```" -ForegroundColor Gray
    Write-Host "    --password 'Linked3-Shorten-Crestless' ```" -ForegroundColor Gray
    Write-Host "    --base-dn 'dc=ldap1test,dc=loc'" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  # Option 2: With certificate (secure)" -ForegroundColor Gray
    Write-Host "  # First copy $pemPath to client, then:" -ForegroundColor Gray
    Write-Host "  python ldap_integration.py test-connection ```" -ForegroundColor Gray
    Write-Host "    --server 172.16.103.2 ```" -ForegroundColor Gray
    Write-Host "    --port 636 ```" -ForegroundColor Gray
    Write-Host "    --use-ssl ```" -ForegroundColor Gray
    Write-Host "    --ssl-ca-cert ldap-ca-cert.pem ```" -ForegroundColor Gray
    Write-Host "    --bind-dn 'cn=administrator,cn=Users,dc=ldap1test,dc=loc' ```" -ForegroundColor Gray
    Write-Host "    --password 'Linked3-Shorten-Crestless' ```" -ForegroundColor Gray
    Write-Host "    --base-dn 'dc=ldap1test,dc=loc'" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host ""
