# TESTDATA Workflow Guide: RID Mapping for Document Management System

## Table of Contents

1. [Overview](#overview)
2. [Complete Workflow](#complete-workflow)
3. [Phase 1: Generate Test Data](#phase-1-generate-test-data)
4. [Phase 2: Import to Active Directory](#phase-2-import-to-active-directory)
5. [Phase 3: Export RID Mapping](#phase-3-export-rid-mapping)
6. [Phase 4: Query Special Group Members](#phase-4-query-special-group-members)
7. [Document Management System Integration](#document-management-system-integration)
8. [Verification Steps](#verification-steps)
9. [Troubleshooting](#troubleshooting)

---

## Overview

This guide explains how to use the TESTDATA mode with LDAP integration to create a mapping between original IntelliSTOR RIDs and new Active Directory RIDs. This mapping is essential for the document management system to correctly apply permissions after LDAP authentication.

### Problem Statement

When test users and groups are imported to Active Directory, AD automatically assigns new RIDs that differ from the original IntelliSTOR database RIDs. The document management system needs to translate permission CSVs (which use original RIDs) to use the new AD-assigned RIDs.

### Solution

1. Generate test data preserving original RIDs in metadata (employeeID, description fields)
2. Import to Active Directory (AD assigns new RIDs)
3. Export a mapping file (Original_RID → New_AD_RID)
4. Document management system uses mapping to translate permission CSVs

---

## Complete Workflow

```
Phase 1: Generate Test Data
  └─> Extract_Users_Permissions.py with --TESTDATA --TESTDATA-SPECIAL-GROUP

Phase 2: Import to Active Directory
  └─> ldap_integration.py add-all (imports groups, users, assignments)

Phase 3: Export RID Mapping
  └─> ldap_integration.py export-rid-mapping (creates rid_mapping.csv)

Phase 4: Document Management System Integration
  └─> Use rid_mapping.csv to translate permission CSVs
  └─> Query LDAP for special group members (DocMgmtUsers)
```

---

## Phase 1: Generate Test Data

### Command

```bash
cd 1_Migration_Users

python Extract_Users_Permissions.py \
  --server localhost \
  --database IntelliSTOR \
  --windows-auth \
  --output Users_Test \
  --TESTDATA \
  --TESTDATA-USERS 100 \
  --TESTDATA-MIN-GROUPS 1 \
  --TESTDATA-MAX-GROUPS 3 \
  --TESTDATA-SPECIAL-GROUP "DocMgmtUsers"
```

### Parameters Explained

- `--TESTDATA`: Enable test data generation mode
- `--TESTDATA-USERS 100`: Generate 100 test users
- `--TESTDATA-MIN-GROUPS 1`: Each user assigned to at least 1 random group
- `--TESTDATA-MAX-GROUPS 3`: Each user assigned to at most 3 random groups
- `--TESTDATA-SPECIAL-GROUP "DocMgmtUsers"`: Name of special group that all test users will be assigned to

### Output Files

The command creates the following CSV files in `Users_Test/` directory:

1. **Users.csv**
   - Contains 100 test users
   - `USER_ID` column contains original RIDs (e.g., 1001, 1002, ...)
   - Used for LDAP import with `employeeID` attribute set to original USER_ID

2. **UserGroups.csv**
   - Contains test groups with original GROUP_IDs
   - `DESCRIPTION` column contains pattern: `TEST-1105 [OriginalID:1105]`
   - Includes special group "DocMgmtUsers" with description containing original ID

3. **UserGroupAssignments.csv**
   - Maps users to groups
   - Each user assigned to 1-3 random test groups
   - **All users assigned to "DocMgmtUsers" group**

4. **Permission CSVs** (with original RIDs)
   - `STYPE_FOLDER_ACCESS.csv`
   - `STYPE_REPORT_SPECIES_ACCESS.csv`
   - `STYPE_SECTION_ACCESS.csv`

### Verification

```bash
# Check special group was created
grep "DocMgmtUsers" Users_Test/UserGroups.csv

# Check all test users are assigned to special group (should equal number of users)
grep -c "DocMgmtUsers" Users_Test/UserGroupAssignments.csv

# Check original IDs are embedded in group descriptions
grep "\[OriginalID:" Users_Test/UserGroups.csv | head -5

# Example output:
# 1105,1105,TEST-1105 [OriginalID:1105],0
# 1234567,DocMgmtUsers,Special group for document management system users [OriginalID:1234567],0
```

---

## Phase 2: Import to Active Directory

### Command

```bash
cd ../2_LDAP

python ldap_integration.py add-all \
  --server 172.16.103.2 \
  --port 636 \
  --use-ssl \
  --ssl-no-verify \
  --bind-dn "cn=administrator,cn=Users,dc=ldap1test,dc=loc" \
  --password "Linked3-Shorten-Crestless" \
  --base-dn "dc=ldap1test,dc=loc" \
  --groups-ou "ou=Groups,dc=ldap1test,dc=loc" \
  --users-ou "ou=Users,dc=ldap1test,dc=loc" \
  --groups-csv ../1_Migration_Users/Users_Test/UserGroups.csv \
  --users-csv ../1_Migration_Users/Users_Test/Users.csv \
  --assignments-csv ../1_Migration_Users/Users_Test/UserGroupAssignments.csv \
  --password-strategy random
```

### Parameters Explained

- `--server`: LDAP server address
- `--port 636`: SSL port (use 389 for non-SSL)
- `--use-ssl`: Enable SSL/TLS encryption
- `--ssl-no-verify`: Skip SSL certificate verification (for testing only)
- `--bind-dn`: Administrator DN for authentication
- `--password`: Administrator password
- `--base-dn`: Base DN for the LDAP directory
- `--groups-ou`: Organizational Unit for groups
- `--users-ou`: Organizational Unit for users
- `--password-strategy random`: Generate random passwords (saved to random_passwords.csv)

### What Happens

1. **Groups Import**
   - Groups created in AD with original ID preserved in description field
   - Example: `description = "TEST-1105 [OriginalID:1105]"`
   - AD assigns new GROUP RID (e.g., 6001) different from original (1105)

2. **Users Import**
   - Users created with original USER_ID in `employeeID` attribute
   - Example: `employeeID = "1001"` for original USER_ID 1001
   - AD assigns new USER RID (e.g., 5001) different from original (1001)

3. **Group Assignments**
   - All test users added to DocMgmtUsers special group
   - Users also added to random test groups

### Expected Output

```
======================================================================
GROUP IMPORT COMPLETE
Total: 51, Created: 51, Skipped: 0, Failed: 0
======================================================================

======================================================================
USER IMPORT COMPLETE
Total: 100, Created: 100, Skipped: 0, Failed: 0
======================================================================

======================================================================
GROUP ASSIGNMENT COMPLETE
Total: 250, Successful: 250, Failed: 0
======================================================================
```

### Output Files

- `random_passwords.csv`: Contains randomly generated passwords for all users

### Verification

```bash
# Verify user imported with employeeID
python ldap_integration.py search \
  --server 172.16.103.2 --port 636 --use-ssl --ssl-no-verify \
  --bind-dn "cn=administrator,cn=Users,dc=ldap1test,dc=loc" \
  --password "Linked3-Shorten-Crestless" \
  --base-dn "dc=ldap1test,dc=loc" \
  --filter "(sAMAccountName=testuser00001)" \
  --attributes "sAMAccountName,employeeID,memberOf"

# Expected output should show employeeID with original USER_ID
```

---

## Phase 3: Export RID Mapping

### Command

```bash
python ldap_integration.py export-rid-mapping \
  --server 172.16.103.2 \
  --port 636 \
  --use-ssl \
  --ssl-no-verify \
  --bind-dn "cn=administrator,cn=Users,dc=ldap1test,dc=loc" \
  --password "Linked3-Shorten-Crestless" \
  --base-dn "dc=ldap1test,dc=loc" \
  --users-ou "ou=Users,dc=ldap1test,dc=loc" \
  --groups-ou "ou=Groups,dc=ldap1test,dc=loc" \
  --output-file rid_mapping.csv
```

### Parameters Explained

- `--users-ou`: Users OU to query (optional, for filtering)
- `--groups-ou`: Groups OU to query (optional, for filtering)
- `--output-file`: Output CSV filename (default: rid_mapping.csv)

### What Happens

1. **Query Users**
   - Searches for all users with `employeeID` attribute set
   - Extracts: original USER_ID (from employeeID), AD SID, AD RID

2. **Query Groups**
   - Searches for all groups with description containing `[OriginalID:]` pattern
   - Extracts: original GROUP_ID (from description), AD SID, AD RID

3. **Create Mapping CSV**
   - Combines user and group mappings into single file
   - Format: `Original_ID,Object_Type,Name,AD_SID,AD_RID`

### Output File: rid_mapping.csv

```csv
Original_ID,Object_Type,Name,AD_SID,AD_RID
1001,User,testuser00001,S-1-5-21-3623811015-3361044348-30300820-5001,5001
1002,User,testuser00002,S-1-5-21-3623811015-3361044348-30300820-5002,5002
1003,User,testuser00003,S-1-5-21-3623811015-3361044348-30300820-5003,5003
...
1105,Group,1105,S-1-5-21-3623811015-3361044348-30300820-6001,6001
1106,Group,1106,S-1-5-21-3623811015-3361044348-30300820-6002,6002
...
1234567,Group,DocMgmtUsers,S-1-5-21-3623811015-3361044348-30300820-6050,6050
```

### Expected Output

```
======================================================================
MAPPING EXPORT COMPLETE
Total entries: 151
Users: 100
Groups: 51
Output file: rid_mapping.csv
======================================================================
```

### Verification

```bash
# Check mapping file exists and has expected entries
wc -l rid_mapping.csv
# Should be 152 lines (100 users + 51 groups + 1 header)

# Check special group is in mapping
grep "DocMgmtUsers" rid_mapping.csv

# Verify RIDs are different from original IDs
head -10 rid_mapping.csv
```

---

## Phase 4: Query Special Group Members

### Command

Query all users who are members of the special group (DocMgmtUsers):

```bash
python ldap_integration.py search \
  --server 172.16.103.2 \
  --port 636 \
  --use-ssl \
  --ssl-no-verify \
  --bind-dn "cn=administrator,cn=Users,dc=ldap1test,dc=loc" \
  --password "Linked3-Shorten-Crestless" \
  --base-dn "dc=ldap1test,dc=loc" \
  --filter "(&(objectClass=user)(memberOf=cn=DocMgmtUsers,ou=Groups,dc=ldap1test,dc=loc))" \
  --attributes "sAMAccountName,employeeID"
```

### Expected Output

All 100 test users should be listed with their employeeID (original USER_ID).

### Use Case

The document management system can use this query to:
- Determine which AD users should have access to the document system
- Verify user belongs to authorized group before granting access
- Query during authentication to check authorization

---

## Document Management System Integration

### Step 1: Load Mapping File

At startup, the document management system loads `rid_mapping.csv` into memory:

```python
import csv
import pandas as pd

# Load mapping
mapping_df = pd.read_csv('rid_mapping.csv')

# Create lookup dictionaries
user_mapping = dict(zip(
    mapping_df[mapping_df['Object_Type']=='User']['Original_ID'].astype(int),
    mapping_df[mapping_df['Object_Type']=='User']['AD_RID']
))

group_mapping = dict(zip(
    mapping_df[mapping_df['Object_Type']=='Group']['Original_ID'].astype(int),
    mapping_df[mapping_df['Object_Type']=='Group']['AD_RID']
))

print(f"Loaded {len(user_mapping)} user mappings")
print(f"Loaded {len(group_mapping)} group mappings")
```

### Step 2: Translate Permission CSVs

When importing permissions, translate original RIDs to new AD RIDs:

```python
def translate_folder_permissions(csv_path, user_mapping, group_mapping):
    """Translate STYPE_FOLDER_ACCESS.csv from original RIDs to AD RIDs.

    Args:
        csv_path: Path to STYPE_FOLDER_ACCESS.csv
        user_mapping: dict mapping original USER_ID to AD RID
        group_mapping: dict mapping original GROUP_ID to AD RID

    Returns:
        List of translated permission records
    """
    permissions = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            folder_id = row['FOLDER_ID']

            # Translate Group RIDs (pipe-separated list)
            old_groups = row['Group'].split('|') if row['Group'] else []
            new_groups = []
            for g in old_groups:
                if g:
                    original_id = int(g)
                    new_rid = group_mapping.get(original_id, original_id)
                    new_groups.append(str(new_rid))
            translated_groups = '|'.join(new_groups)

            # Translate User RIDs (pipe-separated list)
            old_users = row['User'].split('|') if row['User'] else []
            new_users = []
            for u in old_users:
                if u:
                    original_id = int(u)
                    new_rid = user_mapping.get(original_id, original_id)
                    new_users.append(str(new_rid))
            translated_users = '|'.join(new_users)

            permissions.append({
                'folder_id': folder_id,
                'groups': translated_groups,
                'users': translated_users,
                'rid': row['RID'],
                'flags': row['FLAGS']
            })

    return permissions

# Example usage
permissions = translate_folder_permissions(
    'STYPE_FOLDER_ACCESS.csv',
    user_mapping,
    group_mapping
)

print(f"Translated {len(permissions)} folder permissions")
```

### Step 3: LDAP Authentication

When a user logs in, authenticate via LDAP and retrieve metadata:

```python
from ldap3 import Server, Connection, SUBTREE

def authenticate_user(username, password, ldap_config):
    """Authenticate user via LDAP and retrieve metadata.

    Args:
        username: User's sAMAccountName
        password: User's password
        ldap_config: Dictionary with LDAP connection details

    Returns:
        dict: User info including original USER_ID and group memberships
    """
    server = Server(ldap_config['server'], port=ldap_config['port'], use_ssl=True)

    # Bind with user credentials
    user_dn = f"cn={username},{ldap_config['users_ou']}"
    conn = Connection(server, user=user_dn, password=password, auto_bind=True)

    # Search for user to get metadata
    conn.search(
        search_base=ldap_config['users_ou'],
        search_filter=f'(sAMAccountName={username})',
        search_scope=SUBTREE,
        attributes=['employeeID', 'memberOf', 'objectSid']
    )

    if len(conn.entries) == 0:
        return None

    entry = conn.entries[0]

    # Extract original USER_ID from employeeID
    original_user_id = int(entry.employeeID.value) if entry.employeeID else None

    # Extract group memberships
    member_of = [str(dn) for dn in entry.memberOf] if entry.memberOf else []

    # Check if user is in DocMgmtUsers special group
    special_group_dn = f"cn=DocMgmtUsers,{ldap_config['groups_ou']}"
    is_authorized = special_group_dn in member_of

    conn.unbind()

    return {
        'username': username,
        'original_user_id': original_user_id,
        'groups': member_of,
        'is_authorized': is_authorized
    }

# Example usage
ldap_config = {
    'server': '172.16.103.2',
    'port': 636,
    'users_ou': 'ou=Users,dc=ldap1test,dc=loc',
    'groups_ou': 'ou=Groups,dc=ldap1test,dc=loc'
}

user_info = authenticate_user('testuser00001', 'random_password', ldap_config)

if user_info and user_info['is_authorized']:
    print(f"User {user_info['username']} authenticated successfully")
    print(f"Original USER_ID: {user_info['original_user_id']}")
    print(f"Authorized for document management: {user_info['is_authorized']}")
else:
    print("Authentication failed or user not authorized")
```

### Step 4: Apply Permissions

Use translated RIDs to apply permissions when user accesses documents:

```python
def check_folder_access(user_info, folder_id, permissions):
    """Check if user has access to folder.

    Args:
        user_info: User info from LDAP authentication
        folder_id: Folder ID to check
        permissions: Translated permissions from translate_folder_permissions()

    Returns:
        bool: True if user has access
    """
    # Find permission entry for this folder
    folder_perm = next((p for p in permissions if p['folder_id'] == folder_id), None)
    if not folder_perm:
        return False  # No permissions defined

    # Get user's AD RID from mapping
    original_user_id = user_info['original_user_id']
    user_ad_rid = user_mapping.get(original_user_id)

    # Check if user's AD RID is in the allowed users list
    allowed_users = folder_perm['users'].split('|') if folder_perm['users'] else []
    if str(user_ad_rid) in allowed_users:
        return True

    # Check if any of user's groups are in the allowed groups list
    allowed_groups = folder_perm['groups'].split('|') if folder_perm['groups'] else []

    for group_dn in user_info['groups']:
        # Extract group name from DN
        group_name = group_dn.split(',')[0].replace('cn=', '')

        # Look up group's original ID from group name
        original_group_id = None
        for orig_id, name in mapping_df[mapping_df['Object_Type']=='Group'][['Original_ID', 'Name']].values:
            if name == group_name:
                original_group_id = orig_id
                break

        if original_group_id:
            group_ad_rid = group_mapping.get(int(original_group_id))
            if str(group_ad_rid) in allowed_groups:
                return True

    return False

# Example usage
has_access = check_folder_access(user_info, '12345', permissions)
print(f"User has access to folder: {has_access}")
```

---

## Verification Steps

### End-to-End Verification

#### 1. Verify Test Data Generated Correctly

```bash
cd 1_Migration_Users

# Check number of users
wc -l Users_Test/Users.csv
# Should be 101 lines (100 users + 1 header)

# Check special group exists
grep "DocMgmtUsers" Users_Test/UserGroups.csv

# Check all users assigned to special group
grep -c ",DocMgmtUsers," Users_Test/UserGroupAssignments.csv
# Should equal number of test users (100)
```

#### 2. Verify AD Import Succeeded

```bash
cd ../2_LDAP

# Count users in AD
python ldap_integration.py search \
  --server 172.16.103.2 --port 636 --use-ssl --ssl-no-verify \
  --bind-dn "cn=administrator,cn=Users,dc=ldap1test,dc=loc" \
  --password "Linked3-Shorten-Crestless" \
  --base-dn "dc=ldap1test,dc=loc" \
  --filter "(objectClass=user)" \
  --attributes "sAMAccountName" | grep -c "sAMAccountName:"
# Should include 100 test users

# Verify special group exists
python ldap_integration.py search \
  --server 172.16.103.2 --port 636 --use-ssl --ssl-no-verify \
  --bind-dn "cn=administrator,cn=Users,dc=ldap1test,dc=loc" \
  --password "Linked3-Shorten-Crestless" \
  --base-dn "dc=ldap1test,dc=loc" \
  --filter "(cn=DocMgmtUsers)" \
  --attributes "cn,member"
```

#### 3. Verify RID Mapping Exported Correctly

```bash
# Check mapping file format
head -5 rid_mapping.csv

# Expected format:
# Original_ID,Object_Type,Name,AD_SID,AD_RID
# 1001,User,testuser00001,S-1-5-21-...-5001,5001

# Verify RIDs are different
awk -F',' 'NR>1 && $2=="User" {print "Original:",$1," -> AD_RID:",$5}' rid_mapping.csv | head -5

# Check special group in mapping
grep "DocMgmtUsers" rid_mapping.csv
```

#### 4. Test RID Translation

Create a simple test script:

```python
# test_translation.py
import csv
import pandas as pd

# Load mapping
mapping_df = pd.read_csv('rid_mapping.csv')
group_map = dict(zip(
    mapping_df[mapping_df['Object_Type']=='Group']['Original_ID'].astype(int),
    mapping_df[mapping_df['Object_Type']=='Group']['AD_RID']
))

# Test translation
test_cases = [
    ("1105", "Group"),
    ("1106", "Group"),
]

print("Testing RID Translation:")
print("-" * 50)
for original_rid, obj_type in test_cases:
    original_id = int(original_rid)
    new_rid = group_map.get(original_id, "NOT FOUND")
    print(f"{obj_type} {original_rid} → AD RID {new_rid}")

    if new_rid != "NOT FOUND" and new_rid != original_id:
        print("  ✓ Translation successful (RIDs differ)")
    else:
        print("  ✗ Translation failed or RIDs match")
```

Run the test:

```bash
python test_translation.py
```

---

## Troubleshooting

### Issue: Special group not created

**Symptom:** `grep "DocMgmtUsers" Users_Test/UserGroups.csv` returns no results

**Solution:**
- Check that `--TESTDATA-SPECIAL-GROUP` parameter was provided
- Default is "DocMgmtUsers", verify the correct name
- Re-run test data generation with correct parameter

### Issue: Users not assigned to special group

**Symptom:** `grep -c "DocMgmtUsers" Users_Test/UserGroupAssignments.csv` returns 0 or less than expected

**Solution:**
- Check that special group was created successfully first
- Verify test data generation completed without errors
- Check console output for assignment statistics

### Issue: RID mapping export returns no groups

**Symptom:** `export-rid-mapping` only exports users, no groups

**Solution:**
- Verify groups have `[OriginalID:]` pattern in description field
- Check group import succeeded: `python ldap_integration.py search --filter "(objectClass=group)"`
- Verify `--groups-ou` parameter matches actual groups OU

### Issue: RID mapping export returns empty file

**Symptom:** `rid_mapping.csv` is empty or only has header

**Solution:**
- Check LDAP connection parameters (server, port, bind-dn, password)
- Verify users have `employeeID` attribute set
- Check search filters: users need `employeeID`, groups need `[OriginalID:]` in description

### Issue: AD import fails with SSL error

**Symptom:** `Connection failed: SSL error`

**Solution:**
- Use `--ssl-no-verify` flag for testing (NOT for production)
- Provide valid SSL certificate with `--ssl-ca-cert` parameter
- Use non-SSL connection (port 389 without `--use-ssl`) if SSL not configured

### Issue: Permission translation not working

**Symptom:** Users can't access documents after translation

**Debugging steps:**
1. Verify mapping file loaded correctly
2. Check original RIDs in permission CSV match mapping file
3. Log translated RIDs and compare with AD query results
4. Verify user's group memberships include expected groups
5. Check permission CSV format (pipe-separated values)

### Issue: LDAP authentication fails

**Symptom:** User can't log in with AD credentials

**Solution:**
- Verify user DN format: `cn=username,ou=Users,dc=ldap1test,dc=loc`
- Check password in `random_passwords.csv` matches user
- Test LDAP connection with `test-connection` command first
- Verify user exists in AD with `search` command

---

## Summary

This workflow provides a complete solution for:

1. **Generating test data** with original RIDs preserved in metadata
2. **Importing to Active Directory** where AD assigns new RIDs
3. **Exporting RID mapping** to translate between original and new RIDs
4. **Integrating with document management system** for LDAP authentication and permission translation

Key files:
- `Users_Test/Users.csv` - Test users with original USER_IDs
- `Users_Test/UserGroups.csv` - Test groups with original GROUP_IDs in descriptions
- `rid_mapping.csv` - Mapping from original RIDs to new AD RIDs
- `random_passwords.csv` - Passwords for test users (if using random strategy)

The special group "DocMgmtUsers" enables easy querying of authorized users and provides a way to control access to the document management system through LDAP group membership.
