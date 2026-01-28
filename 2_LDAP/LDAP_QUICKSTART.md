# Quick Start Guide - LDAP Integration Tool

This guide will help you get started with the LDAP integration tool in minutes.

## Prerequisites Checklist

Before you begin, ensure you have:

- [ ] Python 3.7 or higher installed
- [ ] Access to Active Directory LDAP server
- [ ] LDAP administrator credentials (bind DN and password)
- [ ] Organizational Units (OUs) created in Active Directory:
  - Groups OU (e.g., `ou=Groups,dc=ocbc,dc=com`)
  - Users OU (e.g., `ou=Users,dc=ocbc,dc=com`)
- [ ] `UserGroups.csv` and `Users.csv` files from IntelliSTOR extraction

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `ldap3` - LDAP client library
- `flask` - Web framework for browser
- `flask-cors` - CORS support

## Step 2: Test Connection

Verify you can connect to Active Directory:

```bash
python ldap_integration.py test-connection \
  --server ldap.ocbc.com \
  --port 389 \
  --bind-dn "cn=admin,dc=ocbc,dc=com" \
  --password "YourPassword" \
  --base-dn "dc=ocbc,dc=com"
```

**Expected output:**
```
INFO - Testing LDAP connection...
INFO - Connection successful
INFO - Server: Microsoft Active Directory
```

If connection fails, check:
- Server address and port
- Bind DN and password
- Network connectivity and firewall rules

## Step 3: Dry-Run Import

Preview the import without making changes:

```bash
# Test groups import
python ldap_integration.py add-groups \
  --server ldap.ocbc.com \
  --port 389 \
  --bind-dn "cn=admin,dc=ocbc,dc=com" \
  --password "YourPassword" \
  --base-dn "dc=ocbc,dc=com" \
  --groups-ou "ou=Groups,dc=ocbc,dc=com" \
  --csv UserGroups.csv \
  --dry-run

# Test users import
python ldap_integration.py add-users \
  --server ldap.ocbc.com \
  --port 636 \
  --use-ssl \
  --bind-dn "cn=admin,dc=ocbc,dc=com" \
  --password "YourPassword" \
  --base-dn "dc=ocbc,dc=com" \
  --users-ou "ou=Users,dc=ocbc,dc=com" \
  --csv Users.csv \
  --password-strategy default \
  --default-password "TempP@ss123" \
  --dry-run
```

Review the output to ensure entries will be created correctly.

## Step 4: Import Groups

Import groups into Active Directory:

```bash
python ldap_integration.py add-groups \
  --server ldap.ocbc.com \
  --port 389 \
  --bind-dn "cn=admin,dc=ocbc,dc=com" \
  --password "YourPassword" \
  --base-dn "dc=ocbc,dc=com" \
  --groups-ou "ou=Groups,dc=ocbc,dc=com" \
  --csv UserGroups.csv
```

**Monitor output:**
```
INFO - Processing 50 groups...
INFO - Created group: Domain Users
INFO - Created group: MD system
...
======================================================================
GROUP IMPORT COMPLETE
Total: 50
Created: 50
Skipped: 0
Errors: 0
======================================================================
```

## Step 5: Import Users

Import users into Active Directory:

**IMPORTANT:** Use SSL (port 636) for password operations!

```bash
python ldap_integration.py add-users \
  --server ldap.ocbc.com \
  --port 636 \
  --use-ssl \
  --bind-dn "cn=admin,dc=ocbc,dc=com" \
  --password "YourPassword" \
  --base-dn "dc=ocbc,dc=com" \
  --users-ou "ou=Users,dc=ocbc,dc=com" \
  --csv Users.csv \
  --password-strategy default \
  --default-password "TempP@ss123"
```

**Monitor output:**
```
INFO - Processing 100 users...
INFO - Created user: jdoe (password set: True)
INFO - Created user: msmith (password set: True)
...
======================================================================
USER IMPORT COMPLETE
Total: 100
Created: 100
Skipped: 0
Errors: 0
Passwords Set: 100
======================================================================
```

## Step 6: Verify Import

Verify all entries were created:

```bash
python ldap_integration.py verify-import \
  --server ldap.ocbc.com \
  --port 389 \
  --bind-dn "cn=admin,dc=ocbc,dc=com" \
  --password "YourPassword" \
  --base-dn "dc=ocbc,dc=com" \
  --groups-csv UserGroups.csv \
  --users-csv Users.csv
```

**Expected output:**
```
INFO - Verifying groups...
INFO - Groups: 50 found, 0 missing
INFO - Verifying users...
INFO - Users: 100 found, 0 missing
```

## Step 7: Browse Directory (Optional)

Launch the LDAP browser to explore entries:

```bash
python ldap_integration.py serve-browser \
  --server ldap.ocbc.com \
  --port 389 \
  --bind-dn "cn=admin,dc=ocbc,dc=com" \
  --password "YourPassword" \
  --base-dn "dc=ocbc,dc=com"
```

Then open `ldap_browser.html` in your web browser.

## All-in-One Import

You can import both groups and users in a single command:

```bash
python ldap_integration.py add-all \
  --server ldap.ocbc.com \
  --port 636 \
  --use-ssl \
  --bind-dn "cn=admin,dc=ocbc,dc=com" \
  --password "YourPassword" \
  --base-dn "dc=ocbc,dc=com" \
  --groups-ou "ou=Groups,dc=ocbc,dc=com" \
  --users-ou "ou=Users,dc=ocbc,dc=com" \
  --groups-csv UserGroups.csv \
  --users-csv Users.csv \
  --password-strategy default \
  --default-password "TempP@ss123"
```

## Password Strategies

### Option 1: Default Password (Recommended for Testing)

Set the same temporary password for all users:

```bash
--password-strategy default --default-password "TempP@ss123"
```

Users should change password on first login.

### Option 2: Random Passwords (Recommended for Production)

Generate random secure passwords (exported to `random_passwords.csv`):

```bash
--password-strategy random
```

### Option 3: Skip Passwords

Create users without passwords (set manually later):

```bash
--password-strategy skip
```

**Note:** SSL (port 636) is required for password operations!

## Troubleshooting

### Connection Failed

**Error:** `Authentication failed`
- Verify bind DN and password
- Check user has appropriate permissions

**Error:** `Cannot connect to server`
- Check server address and port
- Verify network connectivity
- Check firewall rules

### OU Does Not Exist

**Error:** `Groups OU does not exist`
- Create the OU in Active Directory first
- Verify OU DN format

### SSL Errors

**Error:** `SSL error`
- Use correct port: 636
- Add `--use-ssl` flag
- Verify server SSL certificate

### Password Not Set

**Warning:** `Password operations require SSL`
- Use port 636 with `--use-ssl` flag
- Password operations require SSL/TLS

## Best Practices

1. **Always test connection first** before importing
2. **Use dry-run mode** to preview operations
3. **Start with small batch** (5-10 entries) for initial testing
4. **Use SSL for passwords** (port 636)
5. **Verify import** after completion
6. **Backup AD** before production import
7. **Review logs** in `ldap_integration.log`

## Common Use Cases

### Development/Testing Environment

```bash
# Non-SSL, default password, dry-run first
python ldap_integration.py add-all \
  --server ldap-test.ocbc.com \
  --port 389 \
  --bind-dn "cn=admin,dc=test,dc=ocbc,dc=com" \
  --password "TestPassword" \
  --base-dn "dc=test,dc=ocbc,dc=com" \
  --groups-ou "ou=Groups,dc=test,dc=ocbc,dc=com" \
  --users-ou "ou=Users,dc=test,dc=ocbc,dc=com" \
  --groups-csv UserGroups.csv \
  --users-csv Users.csv \
  --password-strategy skip \
  --dry-run
```

### Production Environment

```bash
# SSL, random passwords, verification
python ldap_integration.py add-all \
  --server ldap.ocbc.com \
  --port 636 \
  --use-ssl \
  --bind-dn "cn=admin,dc=ocbc,dc=com" \
  --password "ProductionPassword" \
  --base-dn "dc=ocbc,dc=com" \
  --groups-ou "ou=Groups,dc=ocbc,dc=com" \
  --users-ou "ou=Users,dc=ocbc,dc=com" \
  --groups-csv UserGroups.csv \
  --users-csv Users.csv \
  --password-strategy random

# Verify
python ldap_integration.py verify-import \
  --server ldap.ocbc.com \
  --port 389 \
  --bind-dn "cn=admin,dc=ocbc,dc=com" \
  --password "ProductionPassword" \
  --base-dn "dc=ocbc,dc=com" \
  --groups-csv UserGroups.csv \
  --users-csv Users.csv
```

## Next Steps

After successful import:

1. **Verify entries in Active Directory Users and Computers**
2. **Test user authentication** with created accounts
3. **Set up group memberships** if needed
4. **Configure password policies** (expiration, complexity)
5. **Implement password change on first login**
6. **Review and archive logs**

## Getting Help

For detailed documentation, see `README_LDAP_Integration.md`

For common issues and solutions, check the Troubleshooting section in the README.

Review logs in `ldap_integration.log` for detailed error messages.

## Command Reference Card

```bash
# Test connection
python ldap_integration.py test-connection --server <server> --port 389 --bind-dn <dn> --password <pwd> --base-dn <dn>

# Import groups (dry-run)
python ldap_integration.py add-groups --server <server> --port 389 --bind-dn <dn> --password <pwd> --base-dn <dn> --groups-ou <ou> --csv UserGroups.csv --dry-run

# Import users (SSL + default password)
python ldap_integration.py add-users --server <server> --port 636 --use-ssl --bind-dn <dn> --password <pwd> --base-dn <dn> --users-ou <ou> --csv Users.csv --password-strategy default --default-password <pwd>

# Import all
python ldap_integration.py add-all --server <server> --port 636 --use-ssl --bind-dn <dn> --password <pwd> --base-dn <dn> --groups-ou <ou> --users-ou <ou> --groups-csv UserGroups.csv --users-csv Users.csv --password-strategy default --default-password <pwd>

# Verify
python ldap_integration.py verify-import --server <server> --port 389 --bind-dn <dn> --password <pwd> --base-dn <dn> --groups-csv UserGroups.csv --users-csv Users.csv

# Browser
python ldap_integration.py serve-browser --server <server> --port 389 --bind-dn <dn> --password <pwd> --base-dn <dn>
```

---

**Ready to start?** Begin with Step 1: Install Dependencies!
