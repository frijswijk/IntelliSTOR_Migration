# Extract_Users_Permissions.py - Documentation

## Overview
Extract_Users_Permissions.py extracts user accounts, user groups, sections, and all permission data from the IntelliSTOR MS SQL Server database for migration purposes. It decodes binary Windows Security Descriptors (ACLs) to readable user/group permissions.

## Purpose
Provides a complete export of user and permission data from IntelliSTOR database, including:
- User accounts
- User group definitions
- Security domains
- Report sections
- **Decoded folder permissions** (extracted from binary ACL data)
- **Decoded report species permissions** (extracted from binary ACL data)
- **Decoded section permissions** (extracted from binary ACL data)
- **Aggregated section permissions** across all report species
- **Test data generation** for unmapped RIDs (optional)

## Output Files

1. **Users.csv** - User accounts (includes test users if `--TESTDATA` enabled)
2. **UserGroups.csv** - User group definitions (includes test groups if `--TESTDATA` enabled)
3. **SecurityDomains.csv** - Security domains
4. **Sections.csv** - Report sections
5. **STYPE_FOLDER_ACCESS.csv** - Decoded folder permissions (Group|User|RID|Everyone)
6. **STYPE_REPORT_SPECIES_ACCESS.csv** - Decoded report species permissions (Group|User|RID|Everyone)
7. **STYPE_SECTION_ACCESS.csv** - Decoded section permissions (Group|User|RID|Everyone)
8. **Unique_Sections_Access.csv** - Aggregated section permissions by SECTION.NAME
9. **UserGroupAssignments.csv** - User-group assignments (created if `--TESTDATA` enabled)

## Requirements

### Python Dependencies
```bash
pip install pymssql
```

### Database Tables
The script attempts to query these tables (with fallbacks for naming variations):

| Data Type | Primary Table Name | Alternative Names |
|-----------|-------------------|-------------------|
| Users | SCM_USERS | USER_PROFILE, USERS, USER |
| User Groups | SCM_GROUPS | SCM_USER_GROUP, USER_GROUP, USERGROUP, GROUPS |
| User-Group Assignments | SCM_USER_GROUP | USER_GROUP, USERGROUP |
| Security Domains | SCM_SECURITYDOMAIN | - |
| Sections | SECTION | - |
| Folder Permissions (ACL) | STYPE_FOLDER | FOLDER_PERMISSION, FOLDER_PERMISSIONS, ITEM_PERMISSION, PERMISSIONS |
| Report Permissions (ACL) | STYPE_REPORT_SPECIES | REPORT_SPECIES_PERMISSION, REPORT_SPECIES_PERMISSIONS, SPECIES_PERMISSION |
| Section Permissions (ACL) | STYPE_SECTION | SECTION_PERMISSION, SECTION_PERMISSIONS |

### Database Permissions
The database user needs SELECT permission on all tables listed above.

## Usage

### Basic Usage

#### Windows Authentication
```bash
python Extract_Users_Permissions.py --server localhost --database IntelliSTOR --windows-auth
```

#### SQL Server Authentication
```bash
python Extract_Users_Permissions.py --server localhost --database IntelliSTOR --user sa --password MyPassword
```

### Advanced Options

#### Custom Output Directory
```bash
python Extract_Users_Permissions.py --server localhost --database IntelliSTOR --windows-auth --output-dir C:\Output
```

#### Quiet Mode (Minimal Console Output)
```bash
python Extract_Users_Permissions.py --server localhost --database IntelliSTOR --windows-auth --quiet
```

#### Test Data Generation (Dry-Run)
```bash
python Extract_Users_Permissions.py --server localhost --database IntelliSTOR --windows-auth --TESTDATA-DRYRUN
```

#### Test Data Generation (5000 Users to CSV)
```bash
python Extract_Users_Permissions.py --server localhost --database IntelliSTOR --windows-auth --TESTDATA
```

#### Test Data Generation (Custom Parameters)
```bash
python Extract_Users_Permissions.py --server localhost --database IntelliSTOR --windows-auth --TESTDATA --TESTDATA-USERS 100 --TESTDATA-MIN-GROUPS 1 --TESTDATA-MAX-GROUPS 5
```

#### Full Example
```bash
python Extract_Users_Permissions.py ^
    --server SQLSERVER01 ^
    --port 1433 ^
    --database IntelliSTOR ^
    --user dbuser ^
    --password dbpass ^
    --output-dir C:\Migration\Users ^
    --quiet
```

## Command-Line Arguments

### Database Connection Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--server` | Yes | - | SQL Server host/IP address |
| `--database` | Yes | - | Database name |
| `--port` | No | 1433 | SQL Server port |
| `--user` | No* | - | Username for SQL Server authentication |
| `--password` | No* | - | Password for SQL Server authentication |
| `--windows-auth` | No* | False | Use Windows Authentication |

*Either `--windows-auth` OR both `--user` and `--password` must be provided

### Output Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--output-dir`, `-o` | No | . | Output directory for CSV files |
| `--quiet` | No | False | Quiet mode (minimal console output) |

### Test Data Generation Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--TESTDATA` | No | False | Enable test data generation for unmapped RIDs (writes to CSV files) |
| `--TESTDATA-DRYRUN` | No | False | Preview test data generation without modifying CSV files |
| `--TESTDATA-USERS` | No | 5000 | Number of test users to generate |
| `--TESTDATA-MIN-GROUPS` | No | 1 | Minimum groups per test user |
| `--TESTDATA-MAX-GROUPS` | No | 3 | Maximum groups per test user |

## Test Data Generation Feature

### Overview
When `--TESTDATA` is enabled, the script:
1. **Identifies unmapped RIDs** in ACLs (RIDs not found in database)
2. **Creates test groups** for unmapped RIDs in `UserGroups.csv`
3. **Creates test users** in `Users.csv`
4. **Creates user-group assignments** in `UserGroupAssignments.csv`

**IMPORTANT:** Test data is written to CSV files, NOT to the MS SQL database.

### Why Use Test Data Generation?
When processing Windows Security Descriptors (ACLs), the script may encounter RIDs (Relative IDs) that don't exist in the database. These are often:
- Deleted users/groups
- External domain users/groups
- System accounts

Test data generation creates placeholder entries for these unmapped RIDs, allowing permission checks to find the usergroups and complete the migration process.

### Dry-Run Mode
Use `--TESTDATA-DRYRUN` to preview what test data would be generated without modifying any CSV files:
```bash
python Extract_Users_Permissions.py --server localhost --database IntelliSTOR --windows-auth --TESTDATA-DRYRUN
```

This will log what would be created:
```
[DRY-RUN] Would add group to CSV: {'SECURITYDOMAIN_ID': 1, 'GROUP_ID': 35442, 'FLAGS': 0, 'GROUPNAME': '35442', 'DESCRIPTION': 'TEST-35442'}
[DRY-RUN] Would add user to CSV: {'SECURITYDOMAIN_ID': 1, 'USER_ID': 6000, 'USERNAME': 'testuser00001', ...}
```

### Example: Generate 100 Test Users
```bash
python Extract_Users_Permissions.py --server localhost --database IntelliSTOR --windows-auth --TESTDATA --TESTDATA-USERS 100 --TESTDATA-MIN-GROUPS 1 --TESTDATA-MAX-GROUPS 5
```

This creates:
- Test groups for unmapped RIDs in `UserGroups.csv`
- 100 test users in `Users.csv` (testuser00001, testuser00002, ...)
- Random group assignments (1-5 groups per user) in `UserGroupAssignments.csv`

## Output File Formats

### 1. Users.csv

**Dynamic columns** - All columns from the SCM_USERS (or equivalent) table

**Typical columns:**
- SECURITYDOMAIN_ID - Security domain ID
- USER_ID - Unique user ID (also serves as RID)
- USERNAME - Login username
- PASSWORD - Encrypted password
- FLAGS - User flags
- FULLNAME - User's full name
- DESCRIPTION - User description
- CREATION_TIME - Account creation timestamp
- LAST_MODIFIED_TIME - Last modification timestamp
- PASSWORD_LAST_MODIFIED_TIME - Password change timestamp

**Sample:**
```csv
SECURITYDOMAIN_ID,USER_ID,USERNAME,PASSWORD,FLAGS,FULLNAME,DESCRIPTION,CREATION_TIME,LAST_MODIFIED_TIME,PASSWORD_LAST_MODIFIED_TIME
1,1,jsmith,encrypted_hash,0,John Smith,Administrator,2023-01-15 10:30:00,2024-01-20 14:20:00,2023-06-10 09:00:00
1,2,mbrown,encrypted_hash,0,Mary Brown,Accountant,2023-02-20 11:00:00,2024-01-19 16:45:00,2023-11-05 10:15:00
```

**With Test Data:**
```csv
SECURITYDOMAIN_ID,USER_ID,USERNAME,PASSWORD,FLAGS,FULLNAME,DESCRIPTION,CREATION_TIME,LAST_MODIFIED_TIME,PASSWORD_LAST_MODIFIED_TIME
1,1,jsmith,encrypted_hash,0,John Smith,Administrator,2023-01-15 10:30:00,2024-01-20 14:20:00,2023-06-10 09:00:00
1,6000,testuser00001,,0,Test User 1,Generated test user 1,2026-01-23 12:00:00,2026-01-23 12:00:00,2026-01-23 12:00:00
1,6001,testuser00002,,0,Test User 2,Generated test user 2,2026-01-23 12:00:00,2026-01-23 12:00:00,2026-01-23 12:00:00
```

### 2. UserGroups.csv

**Dynamic columns** - All columns from the SCM_GROUPS table

**Typical columns:**
- SECURITYDOMAIN_ID - Security domain ID
- GROUP_ID - Unique group ID (also serves as RID)
- GROUPNAME - Group name
- DESCRIPTION - Group description
- FLAGS - Group flags

**Sample:**
```csv
SECURITYDOMAIN_ID,GROUP_ID,FLAGS,GROUPNAME,DESCRIPTION
1,1,0,Administrators,System administrators
1,2,0,Accountants,Accounting department
```

**With Test Data (unmapped RIDs):**
```csv
SECURITYDOMAIN_ID,GROUP_ID,FLAGS,GROUPNAME,DESCRIPTION
1,1,0,Administrators,System administrators
1,35442,0,35442,TEST-35442
1,35443,0,35443,TEST-35443
```

### 3. SecurityDomains.csv

**Dynamic columns** - All columns from the SCM_SECURITYDOMAIN table

**Sample:**
```csv
SECURITYDOMAIN_ID,DOMAIN_NAME,DESCRIPTION
1,IntelliSTOR,Primary security domain
```

### 4. Sections.csv

**Dynamic columns** - All columns from the SECTION table

**Typical columns:**
- REPORT_SPECIES_ID - Associated report species ID
- SECTION_ID - Unique section ID within report
- NAME - Section name (e.g., "501", "502")
- START_PAGE - Starting page number
- END_PAGE - Ending page number

**Sample:**
```csv
REPORT_SPECIES_ID,SECTION_ID,NAME,START_PAGE,END_PAGE
100,1,501,1,5
100,2,502,6,20
200,1,501,1,3
```

### 5. STYPE_FOLDER_ACCESS.csv

**Decoded ACL permissions for folders**

**Columns:**
- FOLDER_ID - Folder ID
- Group - Pipe-separated GROUP_IDs with access (e.g., "1|2|3")
- User - Pipe-separated USER_IDs with access (e.g., "10|15")
- RID - Pipe-separated RIDs extracted from ACL (includes unmapped)
- Everyone - 1 if Everyone has access, 0 otherwise

**Sample:**
```csv
FOLDER_ID,Group,User,RID,Everyone
1,1|2,10,1|2|10,0
2,1,10|15,1|10|15,1
3,,,35442,0
```

**Interpretation:**
- FOLDER_ID 1: Groups 1,2 and User 10 have access
- FOLDER_ID 2: Group 1, Users 10,15, and Everyone have access
- FOLDER_ID 3: Only RID 35442 (unmapped) has access

### 6. STYPE_REPORT_SPECIES_ACCESS.csv

**Decoded ACL permissions for report species**

**Columns:**
- REPORT_SPECIES_ID - Report species ID
- Group - Pipe-separated GROUP_IDs with access
- User - Pipe-separated USER_IDs with access
- RID - Pipe-separated RIDs extracted from ACL
- Everyone - 1 if Everyone has access, 0 otherwise

**Sample:**
```csv
REPORT_SPECIES_ID,Group,User,RID,Everyone
100,1|2,10|15,1|2|10|15,0
200,1,,1,1
```

### 7. STYPE_SECTION_ACCESS.csv

**Decoded ACL permissions for sections (per report species)**

**Columns:**
- REPORT_SPECIES_ID - Report species ID
- SECTION_ID - Section ID (unique within report)
- Group - Pipe-separated GROUP_IDs with access
- User - Pipe-separated USER_IDs with access
- RID - Pipe-separated RIDs extracted from ACL
- Everyone - 1 if Everyone has access, 0 otherwise

**Sample:**
```csv
REPORT_SPECIES_ID,SECTION_ID,Group,User,RID,Everyone
100,1,1|2,10,1|2|10,0
100,2,1,10|15,1|10|15,1
200,1,1,,1|35442,0
```

### 8. Unique_Sections_Access.csv

**Aggregated section permissions by SECTION.NAME across all report species**

**Purpose:** Combines permissions for the same section name (e.g., "501") across different reports.

**Columns:**
- SECTION_NAME - Section name (e.g., "501", "502")
- Group - Pipe-separated GROUP_IDs with access (aggregated)
- User - Pipe-separated USER_IDs with access (aggregated)
- RID - Pipe-separated RIDs extracted from ACL (aggregated)
- Everyone - 1 if any instance has Everyone access, 0 otherwise

**Sample:**
```csv
SECTION_NAME,Group,User,RID,Everyone
501,1|2,10|15,1|2|10|15,1
502,1,10,1|10|35442,0
```

**Interpretation:**
- Section "501" appears in multiple reports; permissions are combined
- Any user/group with access to any "501" section is listed

### 9. UserGroupAssignments.csv

**Created only when `--TESTDATA` is enabled**

**Columns:**
- SECURITYDOMAIN_ID - Security domain ID
- USER_ID - User ID
- GROUP_ID - Group ID
- FLAGS - Assignment flags

**Sample:**
```csv
SECURITYDOMAIN_ID,USER_ID,GROUP_ID,FLAGS
1,6000,35442,0
1,6000,35443,0
1,6001,35442,0
```

**Interpretation:**
- Test user 6000 is assigned to groups 35442 and 35443
- Test user 6001 is assigned to group 35442

## Key Features

### Binary ACL Decoding
The script decodes Windows Security Descriptors (binary ACL data) stored in STYPE_* tables:
- **Parses SIDs** (Security Identifiers) from binary data
- **Extracts RIDs** (Relative IDs) from domain SIDs
- **Identifies well-known SIDs** (Everyone, Administrators, etc.)
- **Maps RIDs to users and groups** using database lookups

### RID Mapping
The script builds RID maps to resolve ACL entries:
- **user_rid_map**: {RID → USER_ID}
- **group_rid_map**: {RID → GROUP_ID}

After test data generation, RID maps are rebuilt from CSV files to include newly created entries.

### Table Name Flexibility
The script tries multiple table names for each data type:
- If SCM_USERS doesn't exist, tries USER_PROFILE, USERS, USER
- If SCM_GROUPS doesn't exist, tries SCM_USER_GROUP, USER_GROUP, USERGROUP, GROUPS
- Ensures compatibility with different IntelliSTOR schema versions

### Dynamic Schema Extraction
All columns from each table are extracted automatically:
- No hardcoded column names
- Works with custom fields and extensions
- Future-proof for schema changes

### Section Permission Aggregation
`Unique_Sections_Access.csv` aggregates permissions by SECTION.NAME:
- SECTION_ID is unique within each REPORT_SPECIES_ID
- NAME is the actual section identifier (e.g., "501")
- Permissions are combined across all reports containing that section

## Logging

### Log File
- **Location**: `Extract_Users_Permissions.log` in output directory
- **Level**: DEBUG (all operations logged)
- **Content**:
  - Database connection details
  - Table detection results
  - Row counts for each extraction
  - ACL decoding details (first 10 entries)
  - RID mapping results
  - Test data generation progress
  - Errors and warnings

### Console Output

**Normal Mode:**
```
INFO - Connecting to SQL Server using Windows Authentication: localhost:1433, database: IntelliSTOR
INFO - Database connection established successfully
INFO - Extracting users...
INFO - Written 150 users to Users.csv
INFO - Extracting user groups...
INFO - Written 25 user groups to UserGroups.csv
INFO - Extracting security domains...
INFO - Written 1 security domains to SecurityDomains.csv
INFO - Extracting sections...
INFO - Written 500 sections to Sections.csv
INFO - Extracting and decoding folder permissions...
INFO - Written 2500 folder permissions to STYPE_FOLDER_ACCESS.csv
INFO - Extracting and decoding report species permissions...
INFO - Written 1800 report species permissions to STYPE_REPORT_SPECIES_ACCESS.csv
INFO - Extracting and decoding section permissions...
INFO - Written 3200 section permissions to STYPE_SECTION_ACCESS.csv
INFO - Creating unique sections access aggregation...
INFO - Written 450 unique section permissions to Unique_Sections_Access.csv
INFO - Database connection closed
===================================================================
INFO - EXTRACTION COMPLETE
INFO - Statistics:
INFO -   Users: 150
INFO -   User Groups: 25
INFO -   Security Domains: 1
INFO -   Sections: 500
INFO -   Folder Permissions: 2500
INFO -   Report Permissions: 1800
INFO -   Section Permissions: 3200
===================================================================
```

**With Test Data Generation:**
```
INFO - TEST DATA MODE: Test users and groups will be written to CSV files
... (extraction output) ...
===================================================================
INFO - GENERATING TEST DATA TO CSV FILES
===================================================================
INFO - Found 3 unmapped RIDs: [35442, 35443, 35444]
INFO - Using table schemas from: SCM_GROUPS (groups), SCM_USERS (users)
INFO - Using SECURITYDOMAIN_ID: 1
INFO - Task 1: Creating test groups for unmapped RIDs to UserGroups.csv...
INFO - Creating 3 new test groups (filtered 0 duplicates)
INFO - Successfully added 3 test groups to UserGroups.csv
INFO - Task 2: Creating {self.testdata_user_count} test users to Users.csv...
INFO - Max existing USER_ID: 150, starting new users at 1150
INFO - Prepared 1000/5000 test users...
INFO - Prepared 2000/5000 test users...
... (progress updates) ...
INFO - Successfully added 5000 test users to Users.csv
INFO - Task 3: Creating user-group assignments to UserGroupAssignments.csv...
INFO - Processed assignments for 1000/5000 users...
... (progress updates) ...
INFO - Successfully created 12500 user-group assignments in UserGroupAssignments.csv
===================================================================
INFO - TEST DATA GENERATION TO CSV COMPLETE
INFO -   Test Groups Added to CSV: 3
INFO -   Test Users Added to CSV: 5000
INFO -   User-Group Assignments in CSV: 12500
===================================================================
INFO - Rebuilt RID maps from CSV after test data generation
INFO - Creating unique sections access aggregation...
INFO - Written 450 unique section permissions to Unique_Sections_Access.csv
```

**Quiet Mode:**
```
Completed: Extracted 150 users, 25 groups, 1 domains, 500 sections
```

**Quiet Mode with Test Data:**
```
Completed: Extracted 150 users, 25 groups, 1 domains, 500 sections | Test Data: 3 groups, 5000 users, 12500 assignments
```

## Error Handling

### Missing Tables
If a table doesn't exist:
- A WARNING is logged
- The corresponding CSV file is not created
- Extraction continues with remaining tables

**Example:**
```
WARNING - No user group table found (tried SCM_GROUPS, SCM_USER_GROUP, USER_GROUP, USERGROUP, GROUPS)
```

### Query Errors
If a query fails:
- The error is logged with full stack trace
- The corresponding CSV file may be empty or partial
- Extraction continues with remaining queries

### Graceful Degradation
The script continues even if some tables are missing or queries fail, extracting as much data as possible.

## Troubleshooting

### Error: "No user table found"
**Cause:** The database doesn't have any of the expected user table names
**Solutions:**
1. Check what user tables exist in your database
2. Verify table names in SQL Server Management Studio:
   ```sql
   SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE '%USER%'
   ```
3. Update the script to try your table names
4. Contact support if using a custom schema

### Warning: "No folder permission table found"
**Cause:** Permission table names don't match expected patterns
**Solutions:**
1. Check permission table names in your database:
   ```sql
   SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE '%STYPE%'
   ```
2. Update the script to try your table names
3. Verify permissions schema

### Empty CSV Files
**Cause:** Tables exist but contain no data
**Solutions:**
- Check if tables have data using SQL queries
- Verify you're connecting to the correct database
- Check if data has been migrated or deleted

### Partial Data Extraction
**Cause:** Some queries succeed, others fail
**Solutions:**
- Check the log file (`Extract_Users_Permissions.log`) for specific errors
- Verify database schema matches expectations
- Check user permissions on all tables:
  ```sql
  SELECT * FROM fn_my_permissions('SCM_USERS', 'OBJECT')
  ```

### Unmapped RIDs in ACLs
**Cause:** ACLs contain RIDs not found in database (deleted users, external domains)
**Solutions:**
- Enable test data generation: `--TESTDATA`
- Review unmapped RIDs in log file
- Manually investigate RIDs in Active Directory
- Use `--TESTDATA-DRYRUN` to preview what would be created

### Test Data Generation Fails
**Cause:** CSV file is locked or schema discovery fails
**Solutions:**
- Close CSV files in Excel/other programs
- Verify output directory is writable
- Check log file for specific errors
- Use `--TESTDATA-DRYRUN` to preview without modifying files

## Performance

### Expected Performance
- **Small database** (<1,000 users): 30 seconds - 2 minutes
- **Medium database** (1,000-10,000 users): 2-10 minutes
- **Large database** (>10,000 users): 10-30 minutes

Performance depends on:
- Number of users and groups
- Number of permission records (ACLs to decode)
- Network latency to SQL Server
- Database server performance
- Test data generation (if enabled)

### Performance Tips
- Use `--quiet` for faster execution (less console I/O)
- Run on database server to minimize network latency
- Use Windows Authentication (faster than SQL authentication)
- Close unnecessary applications

## Security Considerations

### Password Handling
- Passwords are passed via command-line (visible in process list)
- For production, consider using:
  - Windows Authentication (recommended)
  - Environment variables
  - Secure credential storage
  - SQL Server integrated security

### Sensitive Data
The extracted CSV files may contain:
- User credentials (encrypted passwords)
- User email addresses
- User names
- Permission settings
- Security domain information

**Recommendations:**
- Store CSV files securely
- Restrict access to output directory
- Delete files after migration
- Do not commit to version control
- Use encryption for file transfer

### Test Data
- Test data contains placeholder users/groups
- Test users have no passwords
- Test data is clearly marked (USERNAME starts with "testuser", DESCRIPTION contains "TEST-")
- Review and delete test data after migration if not needed

## Use Cases

### Pre-Migration Audit
```bash
python Extract_Users_Permissions.py --server prod --database IntelliSTOR --windows-auth --output-dir audit_2024_01_23
```
Extract current state before migration for comparison.

### Backup Before Changes
```bash
python Extract_Users_Permissions.py --server localhost --database IntelliSTOR --windows-auth --output-dir backup_%date%
```
Create backup before making permission changes.

### Migration with Test Data
```bash
python Extract_Users_Permissions.py --server localhost --database IntelliSTOR --windows-auth --TESTDATA --output-dir migration_data
```
Extract all data and generate test users/groups for unmapped RIDs.

### Dry-Run Test Data Preview
```bash
python Extract_Users_Permissions.py --server localhost --database IntelliSTOR --windows-auth --TESTDATA-DRYRUN
```
Preview what test data would be generated without modifying CSV files.

### Documentation
Extract data for documentation purposes:
- User lists for training
- Permission matrices for compliance
- Section lists for reporting
- Access audit reports

### Permission Analysis
Analyze permissions using the decoded ACL files:
- Who has access to which folders
- Which sections are restricted
- Group membership analysis
- Identify overly permissive access (Everyone)

## Integration with Migration Process

### Typical Workflow
1. **Extract data** from source database:
   ```bash
   python Extract_Users_Permissions.py --server source --database IntelliSTOR --windows-auth --TESTDATA --output-dir extract
   ```

2. **Review extracted data**:
   - Check `Extract_Users_Permissions.log` for warnings
   - Review unmapped RIDs
   - Verify test data looks correct

3. **Transform data** (if needed):
   - Convert CSV formats
   - Map users to new system
   - Adjust permissions

4. **Load data** into target system:
   - Import Users.csv
   - Import UserGroups.csv
   - Import UserGroupAssignments.csv
   - Apply permissions from decoded ACL files

5. **Validate migration**:
   - Verify user count matches
   - Test permissions
   - Compare access matrices

## See Also
- `Extract_Instances.py` - Extract report instances
- `Extract_Folder_Species.py` - Extract folder hierarchy and reports
- `README_LDAP_Integration.md` - LDAP integration documentation
- `ACL_INTEGRATION_COMPLETE.md` - ACL decoding implementation details

## Version History

### Version 2.0 (2026-01-23)
- Added binary ACL decoding for folder/report/section permissions
- Added test data generation to CSV files (not database)
- Added SecurityDomains.csv extraction
- Added Unique_Sections_Access.csv aggregation
- Added RID mapping and unmapped RID tracking
- Added UserGroupAssignments.csv for test data
- Improved logging and error handling

### Version 1.0 (2026-01-22)
- Initial version
- Basic user and permission extraction

## Support
For issues or questions:
1. Check the log file: `Extract_Users_Permissions.log`
2. Enable DEBUG logging for detailed diagnostics
3. Review this documentation
4. Contact: OCBC IntelliSTOR Migration Team
