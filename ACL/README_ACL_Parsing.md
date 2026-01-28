# IntelliSTOR Access Control List (ACL) Documentation

## Overview

IntelliSTOR stores Windows Security Descriptors (ACLs) in binary format as hexadecimal values in the database. These ACLs define permissions for folders and reports, controlling which users and groups can access specific resources.

## What is an ACL?

An **Access Control List (ACL)** is a Windows security structure that specifies:
- **Who** has access (users and groups identified by SIDs)
- **What** they can do (permissions like Read, Write, Execute, Delete)
- **How** access is granted or denied (Allow/Deny entries)

## Database Storage

### Table: STYPE_FOLDER (and similar tables)

ACLs are stored in columns as binary data, represented in hexadecimal format:

**Example:**
```
0x94000000010014800000000000000000140000003000000002001C000100000002C0140007000000010100000000000100000000020064000300000000001400070000000101000000000001000000000000240007000000010500000000000515000000D67B9C550F50215711305578728A00000000240007000000010500000000000515000000D67B9C550F50215711305578ED940000
```

This 152-byte binary blob contains complete permission information for a folder or report.

## ACL Structure

### Components

1. **Security Descriptor Header** (20 bytes)
   - Revision
   - Control flags
   - Offsets to Owner, Group, SACL, DACL

2. **Owner SID** (variable length)
   - Security Identifier of the owner

3. **Group SID** (variable length)
   - Security Identifier of the primary group

4. **DACL (Discretionary Access Control List)**
   - Contains Access Control Entries (ACEs)
   - Each ACE specifies permissions for a user/group

5. **SACL (System Access Control List)** (optional)
   - Auditing information

### SID (Security Identifier) Format

A SID uniquely identifies a user, group, or computer:

**Format:** `S-R-I-SA-SA-SA-...-RID`

**Example:** `S-1-5-21-1436318678-1461800975-2018848785-35442`

**Components:**
- **S**: Literal "S" prefix
- **R**: Revision (always 1)
- **I**: Identifier Authority (5 = NT Authority)
- **SA**: Sub-Authority values (domain identifiers)
- **RID**: Relative Identifier (user/group identifier within the domain)

### Common Well-Known SIDs

| SID | Account | Description |
|-----|---------|-------------|
| S-1-1-0 | Everyone | All users |
| S-1-5-18 | Local System | System account |
| S-1-5-32-544 | BUILTIN\Administrators | Local administrators |
| S-1-5-32-545 | BUILTIN\Users | Local users |
| S-1-5-21-...-500 | Domain Administrator | Domain admin account |
| S-1-5-21-...-512 | Domain Admins | Domain admins group |
| S-1-5-21-...-513 | Domain Users | Domain users group |

### Permission Flags (Access Mask)

Common access masks:

| Mask | Value | Permissions |
|------|-------|-------------|
| FULL_CONTROL | 0x001F01FF | All permissions |
| READ & EXECUTE | 0x00000007 | Read data, execute, read attributes |
| MODIFY | 0x00000006 | Read, write, delete |
| READ | 0x00000001 | Read data only |
| WRITE | 0x00000002 | Write data only |

**Individual Rights:**

| Flag | Hex Value | Description |
|------|-----------|-------------|
| FILE_READ_DATA | 0x00000001 | Read file contents or list directory |
| FILE_WRITE_DATA | 0x00000002 | Write file or add file to directory |
| FILE_APPEND_DATA | 0x00000004 | Append to file or add subdirectory |
| FILE_EXECUTE | 0x00000020 | Execute file or traverse directory |
| DELETE | 0x00010000 | Delete the object |
| READ_CONTROL | 0x00020000 | Read security descriptor |
| WRITE_DAC | 0x00040000 | Modify permissions |
| WRITE_OWNER | 0x00080000 | Change owner |
| SYNCHRONIZE | 0x00100000 | Synchronize access |
| GENERIC_READ | 0x80000000 | Generic read access |
| GENERIC_WRITE | 0x40000000 | Generic write access |
| GENERIC_EXECUTE | 0x20000000 | Generic execute access |
| GENERIC_ALL | 0x10000000 | All generic rights |

## Using the ACL Parser

### Prerequisites

- Python 3.7 or higher
- No external dependencies required

### Parser Scripts

Two parser scripts are provided:

1. **parse_acl_simple.py** - Recommended for most use cases
   - Easier to understand output
   - Focuses on SIDs and permissions
   - Better error handling

2. **parse_acl.py** - Advanced parser
   - Complete security descriptor parsing
   - Detailed structure breakdown

### Basic Usage

#### 1. Extract ACL from Database

First, extract the ACL hex value from the database:

```sql
SELECT ITEM_ID, NAME, VALUE
FROM STYPE_FOLDER
WHERE ITEM_ID = 123;
```

**Example result:**
```
VALUE: 0x94000000010014800000000000000000140000003000000002001C000100000002C0140007000000010100000000000100000000020064000300000000001400070000000101000000000001000000000000240007000000010500000000000515000000D67B9C550F50215711305578728A00000000240007000000010500000000000515000000D67B9C550F50215711305578ED940000
```

#### 2. Parse the ACL

Edit the parser script to include your hex value:

```python
if __name__ == "__main__":
    # Your hex ACL from database
    hex_acl = "0x9400000001001480..." # Full hex string

    analyze_hex_acl(hex_acl)
```

#### 3. Run the Parser

```bash
python parse_acl_simple.py
```

### Example Output

```
================================================================================
WINDOWS ACL BINARY ANALYSIS
================================================================================

Data length: 152 bytes (304 hex chars)

Found 4 SID(s) in the binary data:
--------------------------------------------------------------------------------

SID #1:
  Offset: 0x0028 (40 bytes)
  SID: S-1-1-0
  Account: Everyone
  Possible Access Mask: 0x00000007
  Permissions:
    - READ & EXECUTE

SID #2:
  Offset: 0x0044 (68 bytes)
  SID: S-1-1-0
  Account: Everyone
  Possible Access Mask: 0x00000007
  Permissions:
    - READ & EXECUTE

SID #3:
  Offset: 0x0058 (88 bytes)
  SID: S-1-5-21-1436318678-1461800975-2018848785-35442
  Account: Domain User/Group (RID: 35442)
  Possible Access Mask: 0x00000007
  Permissions:
    - READ & EXECUTE

SID #4:
  Offset: 0x007C (124 bytes)
  SID: S-1-5-21-1436318678-1461800975-2018848785-38125
  Account: Domain User/Group (RID: 38125)
  Possible Access Mask: 0x00000007
  Permissions:
    - READ & EXECUTE

================================================================================
DOMAIN INFORMATION
================================================================================

Domain SID: S-1-5-21-1436318678-1461800975-2018848785
  Domain ID components:
    - 1436318678: 0x559C7BD6
    - 1461800975: 0x5721500F
    - 2018848785: 0x78553011

Users/Groups in this ACL:
  - RID 35442: Domain User/Group (RID: 35442)
  - RID 38125: Domain User/Group (RID: 38125)

================================================================================
```

## Interpreting Results

### Understanding the Output

**1. Everyone Group (S-1-1-0)**
- **Meaning**: Permissions apply to all users
- **Common Use**: Base-level access for all authenticated users
- **In Example**: Everyone has READ & EXECUTE rights

**2. Domain Users/Groups**
- **SID Format**: S-1-5-21-[Domain-ID]-[RID]
- **Domain ID**: Unique identifier for the Windows domain
- **RID**: Relative ID identifying the specific user or group
- **In Example**: Two domain users/groups (RID 35442 and 38125) have READ & EXECUTE

**3. Permission Levels**

| Permission | Typical Use | Access Rights |
|------------|-------------|---------------|
| READ & EXECUTE | View and run | Can read files, list folders, execute programs |
| MODIFY | Edit content | Can read, write, delete files |
| FULL_CONTROL | Complete access | All rights including changing permissions |

### Mapping RIDs to Users/Groups

To identify the actual user or group name from a RID:

#### Option 1: Query IntelliSTOR Database

Check if IntelliSTOR has user/group tables:

```sql
-- Look for user tables
SELECT * FROM USER_TABLE WHERE USER_ID = 35442;

-- Look for group tables
SELECT * FROM GROUP_TABLE WHERE GROUP_ID = 35442;

-- Check security-related tables
SELECT * FROM STYPE_SEC WHERE RID = 35442;
```

#### Option 2: Active Directory Query

If you have access to the Windows domain:

```powershell
# Get user/group by RID
Get-ADObject -Filter {objectSid -like "*-35442"}

# Or using SID directly
Get-ADObject -Identity "S-1-5-21-1436318678-1461800975-2018848785-35442"
```

#### Option 3: Windows Command Line

```cmd
wmic useraccount where "SID='S-1-5-21-1436318678-1461800975-2018848785-35442'" get name
```

## Common ACL Patterns in IntelliSTOR

### Pattern 1: Public Folder Access
```
- Everyone: READ & EXECUTE
- Domain Users: READ & EXECUTE
```
**Use**: Reports/folders accessible to all employees

### Pattern 2: Restricted Folder Access
```
- Administrators: FULL_CONTROL
- Specific Group (RID): MODIFY
- Domain Users: READ
```
**Use**: Department-specific folders with limited access

### Pattern 3: Secured Folder Access
```
- Administrators: FULL_CONTROL
- Specific Users (RIDs): READ & EXECUTE
```
**Use**: Confidential reports with explicit user access

## Migration Considerations

### For IntelliSTOR to New System Migration

**1. Permission Mapping Strategy:**
- Extract all unique SIDs from ACLs
- Map RIDs to actual user/group names
- Create equivalent permissions in target system

**2. Permission Simplification:**
- Identify common permission patterns
- Group similar ACLs together
- Create role-based access groups

**3. Data Export for Migration:**

Create a permission mapping CSV:

```csv
Folder_ID,Folder_Name,SID,RID,Permission_Level,User_Group_Name
123,Reports,S-1-5-21-...-35442,35442,READ_EXECUTE,Finance_Readers
123,Reports,S-1-5-21-...-38125,38125,READ_EXECUTE,Audit_Team
```

### SQL Query for Permission Analysis

```sql
-- Extract all ACLs with folder information
SELECT
    f.ITEM_ID,
    f.NAME AS Folder_Name,
    sf.VALUE AS ACL_Hex
FROM DB_FOLDER f
JOIN STYPE_FOLDER sf ON f.ITEM_ID = sf.ITEM_ID
WHERE sf.VALUE IS NOT NULL;

-- Count folders by permission complexity
SELECT
    LENGTH(VALUE) AS ACL_Size,
    COUNT(*) AS Folder_Count
FROM STYPE_FOLDER
WHERE VALUE IS NOT NULL
GROUP BY LENGTH(VALUE)
ORDER BY ACL_Size;
```

## Batch Processing ACLs

For processing multiple ACLs, modify the parser:

```python
import csv

def process_multiple_acls(csv_file):
    """Process ACLs from CSV export."""
    results = []

    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            folder_id = row['ITEM_ID']
            acl_hex = row['VALUE']

            # Parse ACL
            sids = find_all_sids_in_data(bytes.fromhex(acl_hex[2:]))

            for sid_info in sids:
                results.append({
                    'Folder_ID': folder_id,
                    'SID': sid_info['sid'],
                    'Account': sid_info['name'],
                    'Permissions': parse_access_mask(sid_info['access_mask'])
                })

    return results

# Usage
permissions = process_multiple_acls('folder_acls.csv')

# Export to CSV
with open('permissions_report.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=['Folder_ID', 'SID', 'Account', 'Permissions'])
    writer.writeheader()
    writer.writerows(permissions)
```

## Troubleshooting

### Issue: Parser returns "Invalid SID"

**Cause**: Corrupted or non-standard ACL format

**Solution:**
1. Verify hex string is complete
2. Check for extra spaces or characters
3. Ensure 0x prefix is included
4. Try parsing a known-good ACL first

### Issue: Unknown RIDs

**Cause**: RIDs not in well-known list

**Solution:**
1. Query Active Directory for the domain
2. Check IntelliSTOR user/group tables
3. Contact domain administrators for user/group mapping

### Issue: Multiple permissions for same SID

**Cause**: Inherited and explicit permissions combine

**Solution:**
- ACLs may contain both inherited and explicit entries
- The most restrictive permission typically applies
- Review all entries for the SID to understand effective permissions

## Security Best Practices

1. **Least Privilege**: Only grant minimum required permissions
2. **Group-Based Access**: Use groups rather than individual users
3. **Regular Audits**: Review ACLs periodically for unnecessary access
4. **Document Exceptions**: Record why specific users have elevated access
5. **Remove Orphaned SIDs**: Clean up permissions for deleted users/groups

## Reference Documents

- IntelliSTOR Database Schema (DB_SCHEMA.csv)
- IntelliSTOR DB Explorer (IntelliSTOR_DB_Explorer.html)
- Screenshots Permissions folder (visual examples)
- Microsoft Security Descriptor Format: [MS-DTYP] documentation

## Tools Provided

### parse_acl_simple.py
**Purpose**: Quick analysis of ACL hex values
**Best For**:
- Identifying users/groups with access
- Understanding permission levels
- Bulk processing of ACLs

### parse_acl.py
**Purpose**: Detailed security descriptor analysis
**Best For**:
- Complete ACL structure examination
- Advanced security auditing
- Understanding inheritance and propagation

## Example Use Cases

### Use Case 1: Audit Department Access

**Objective**: Find all folders accessible by Finance department

**Steps:**
1. Export all ACLs to CSV
2. Run batch parser
3. Filter results for Finance group RID
4. Generate access report

### Use Case 2: Migration Planning

**Objective**: Map IntelliSTOR permissions to new system

**Steps:**
1. Parse all ACLs
2. Extract unique SIDs
3. Map SIDs to user/group names
4. Create role definitions in new system
5. Assign users to roles based on mapping

### Use Case 3: Security Compliance

**Objective**: Identify overly permissive folders

**Steps:**
1. Parse all ACLs
2. Flag folders with "Everyone" or "Domain Users" FULL_CONTROL
3. Review flagged folders with security team
4. Implement least privilege corrections

## Contact and Support

For questions about ACL parsing or IntelliSTOR permissions:
- Review this documentation
- Check the parser script comments
- Consult IntelliSTOR database schema documentation
- Contact domain administrators for user/group mapping

## Version History

- **v1.0** (2026-01-20): Initial documentation
  - Basic ACL parsing functionality
  - Simple and advanced parsers
  - Migration guidance

---

**Document Location:** Migration_Taxonomy/README_ACL_Parsing.md
**Related Scripts:** parse_acl_simple.py, parse_acl.py
**Project:** OCBC IntelliSTOR Migration
