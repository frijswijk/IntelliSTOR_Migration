# LDAP Browser Configuration Guide

## Overview

The LDAP Browser consists of two components:
1. **Frontend** (`ldap_browser.html`) - Web interface
2. **Backend** (Flask API) - LDAP connection handler

## Configuration Steps

### Step 1: Configure LDAP Connection (Backend)

The LDAP parameters are configured when starting the Flask API using the `serve-browser` command.

#### Basic Configuration (Non-SSL)

```bash
python ldap_integration.py serve-browser \
  --server YLDAPTEST-DC01.ldap1test.loc \
  --port 389 \
  --bind-dn "cn=administrator,cn=Users,dc=ldap1test,dc=loc" \
  --password "YourPassword" \
  --base-dn "dc=ldap1test,dc=loc"
```

#### SSL Configuration with Self-Signed Certificate

**Option A: Skip Certificate Verification (Testing Only)**
```bash
python ldap_integration.py serve-browser \
  --server YLDAPTEST-DC01.ldap1test.loc \
  --port 636 \
  --use-ssl \
  --ssl-no-verify \
  --bind-dn "cn=administrator,cn=Users,dc=ldap1test,dc=loc" \
  --password "YourPassword" \
  --base-dn "dc=ldap1test,dc=loc"
```

**Option B: Custom CA Certificate (Recommended)**
```bash
# First export certificate
openssl s_client -connect YLDAPTEST-DC01.ldap1test.loc:636 -showcerts < nul 2>&1 | openssl x509 -outform PEM > ca-cert.pem

# Then start browser with certificate
python ldap_integration.py serve-browser \
  --server YLDAPTEST-DC01.ldap1test.loc \
  --port 636 \
  --use-ssl \
  --ssl-ca-cert ca-cert.pem \
  --bind-dn "cn=administrator,cn=Users,dc=ldap1test,dc=loc" \
  --password "YourPassword" \
  --base-dn "dc=ldap1test,dc=loc"
```

#### Optional: Custom API Host and Port

By default, the API runs on `127.0.0.1:5000`. To change this:

```bash
python ldap_integration.py serve-browser \
  --server YLDAPTEST-DC01.ldap1test.loc \
  --port 636 \
  --use-ssl \
  --ssl-no-verify \
  --bind-dn "cn=administrator,cn=Users,dc=ldap1test,dc=loc" \
  --password "YourPassword" \
  --base-dn "dc=ldap1test,dc=loc" \
  --api-host 0.0.0.0 \
  --api-port 8080
```

**Note**: `--api-host 0.0.0.0` allows remote access to the browser.

### Step 2: Configure API Endpoint (Frontend)

If you changed the API host/port in Step 1, update `ldap_browser.html`:

#### Edit Line 317-318

**Default (local access only):**
```javascript
const API_BASE = 'http://127.0.0.1:5000/api';
```

**Custom port:**
```javascript
const API_BASE = 'http://127.0.0.1:8080/api';
```

**Remote access:**
```javascript
const API_BASE = 'http://192.168.1.100:5000/api';
```

Replace `192.168.1.100` with the actual IP address of the machine running the Flask API.

### Step 3: Start the Browser

1. **Start the Flask API** (from Step 1):
   ```bash
   python ldap_integration.py serve-browser [parameters]
   ```

2. **Open the HTML file** in your web browser:
   - Double-click `ldap_browser.html`, or
   - Open in browser: `file:///C:/path/to/ldap_browser.html`

3. **Verify connection**:
   - Check the connection status indicator in the header
   - Should show "Connected" in green

## Common Configuration Scenarios

### Scenario 1: Local Testing with Self-Signed Certificate

**Terminal 1 - Start API:**
```bash
cd C:\Users\freddievr\claude-projects\IntelliSTOR_Migration\2_LDAP
python ldap_integration.py serve-browser \
  --server YLDAPTEST-DC01.ldap1test.loc \
  --port 636 \
  --use-ssl \
  --ssl-no-verify \
  --bind-dn "cn=administrator,cn=Users,dc=ldap1test,dc=loc" \
  --password "Linked3-Shorten-Crestless" \
  --base-dn "dc=ldap1test,dc=loc"
```

**Browser - Open:**
```
file:///C:/Users/freddievr/claude-projects/IntelliSTOR_Migration/2_LDAP/ldap_browser.html
```

**No changes needed to HTML file** - uses default `127.0.0.1:5000`.

### Scenario 2: Remote Access (API on Server, Browser on Desktop)

**Server - Start API:**
```bash
python ldap_integration.py serve-browser \
  --server ldap.ocbc.com \
  --port 636 \
  --use-ssl \
  --ssl-ca-cert ca-cert.pem \
  --bind-dn "cn=admin,dc=ocbc,dc=com" \
  --password "YourPassword" \
  --base-dn "dc=ocbc,dc=com" \
  --api-host 0.0.0.0 \
  --api-port 5000
```

**Desktop - Edit `ldap_browser.html` line 318:**
```javascript
const API_BASE = 'http://192.168.1.50:5000/api';  // Replace with server IP
```

**Desktop - Open browser:**
```
file:///C:/Users/your-name/Desktop/ldap_browser.html
```

### Scenario 3: Production with Valid Certificate

**Start API:**
```bash
python ldap_integration.py serve-browser \
  --server ldaps.ocbc.com \
  --port 636 \
  --use-ssl \
  --bind-dn "cn=admin,dc=ocbc,dc=com" \
  --password "YourPassword" \
  --base-dn "dc=ocbc,dc=com"
```

**No SSL flags needed** - uses system certificate store.

## Quick Start Script

Create `start_browser.bat`:

```batch
@echo off
echo Starting LDAP Browser API...
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
```

Then:
1. Run `start_browser.bat`
2. Open `ldap_browser.html` in browser

## Troubleshooting

### Issue: "Connection Failed" in Browser

**Check 1: Is Flask API running?**
```bash
# Look for this message in terminal:
INFO - Starting LDAP Browser API on 127.0.0.1:5000
INFO - Open ldap_browser.html in your browser
```

**Check 2: Is API endpoint correct?**
- Browser console (F12) should show API calls
- Verify `API_BASE` in HTML matches Flask API host:port

**Check 3: CORS issues?**
- Flask API uses `flask-cors` to allow browser access
- Ensure `flask-cors` is installed: `pip install flask-cors`

### Issue: "Disconnected" Status

**Cause**: LDAP connection failed

**Solution**: Check Flask API terminal for LDAP errors:
- Authentication failed?
- SSL certificate error?
- Server unreachable?

### Issue: Empty Tree or Search Results

**Cause 1**: Base DN incorrect
- Verify `--base-dn` matches your LDAP structure

**Cause 2**: No organizational units
- Tree browser only shows OUs
- Use search to find users/groups

**Cause 3**: Permissions
- Bind DN must have read permissions

### Issue: Cross-Origin Errors

**Error in browser console**:
```
Access to fetch at 'http://127.0.0.1:5000/api/health' from origin 'null' has been blocked by CORS
```

**Solution**: Ensure `flask-cors` is installed and imported in `ldap_integration.py` (already done).

## Advanced Configuration

### Using Environment Variables

Create `browser_config.bat`:

```batch
@echo off
set LDAP_SERVER=YLDAPTEST-DC01.ldap1test.loc
set LDAP_PORT=636
set LDAP_BIND_DN=cn=administrator,cn=Users,dc=ldap1test,dc=loc
set LDAP_PASSWORD=Linked3-Shorten-Crestless
set LDAP_BASE_DN=dc=ldap1test,dc=loc

python ldap_integration.py serve-browser ^
  --server %LDAP_SERVER% ^
  --port %LDAP_PORT% ^
  --use-ssl ^
  --ssl-no-verify ^
  --bind-dn "%LDAP_BIND_DN%" ^
  --password "%LDAP_PASSWORD%" ^
  --base-dn "%LDAP_BASE_DN%"
```

### Multiple LDAP Servers

To browse multiple LDAP servers, create separate HTML files:

```bash
# Copy and configure for each server
cp ldap_browser.html ldap_browser_dev.html
cp ldap_browser.html ldap_browser_prod.html
```

Edit each file with different `API_BASE` endpoints, then run multiple Flask API instances on different ports.

## API Endpoints Reference

The browser uses these endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Check connection status |
| `/api/tree` | GET | Get OU tree structure |
| `/api/search?q=&type=` | GET | Search users/groups |
| `/api/entry/<dn>` | GET | Get entry details |

All endpoints are automatically handled by the Flask API when you start `serve-browser`.

## Security Considerations

### 1. Protect Passwords
- Don't hardcode passwords in scripts
- Use secure credential storage
- Consider using service accounts with limited permissions

### 2. Network Security
- Use `--api-host 127.0.0.1` for local-only access
- Use firewall rules for remote access
- Consider using HTTPS for Flask API (requires additional configuration)

### 3. SSL/TLS
- Use `--ssl-ca-cert` instead of `--ssl-no-verify` when possible
- Never use `--ssl-no-verify` in production

## Summary

**Minimal Configuration (Local, Self-Signed Cert):**

1. Start API:
   ```bash
   python ldap_integration.py serve-browser --server YOUR_SERVER --port 636 --use-ssl --ssl-no-verify --bind-dn "YOUR_DN" --password "YOUR_PASSWORD" --base-dn "YOUR_BASE_DN"
   ```

2. Open `ldap_browser.html` in browser

**That's it!** The HTML file works out-of-the-box with default settings.
