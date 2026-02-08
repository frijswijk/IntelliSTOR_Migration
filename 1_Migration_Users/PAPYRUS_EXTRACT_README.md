# Papyrus Users & Permissions Extractor

## Overview

`papyrus_extract_users_permissions.exe` is a C++ command-line tool that extracts users, groups, sections, and permissions from IntelliSTOR MS SQL Server databases. This is a simplified version of the Python `Extract_Users_Permissions.py` script, designed for airgap deployment and Papyrus integration.

## Features

✅ **Database Extraction**: Connects to MS SQL Server using ODBC
✅ **Windows Authentication**: Supports both Windows Auth and SQL Auth
✅ **User Management**: Extracts users from SCM_USERS or USER_PROFILE tables
✅ **Group Management**: Extracts groups and user-group memberships
✅ **Section Security**: Extracts sections and security domains
✅ **ACL Parsing**: Decodes binary Security Descriptors and extracts SIDs
✅ **CSV Output**: Generates multiple CSV files for easy import/analysis
✅ **Airgap Ready**: Statically linked, no external dependencies

## Output Files

The tool generates the following CSV files in the specified output directory:

| File | Description |
|------|-------------|
| `Users.csv` | User accounts with ID, username, full name, email, status |
| `UserGroups.csv` | Security groups with ID, name, description |
| `UserGroupMemberships.csv` | User-to-group membership mappings |
| `Sections.csv` | Report sections with ID, name, owner, security domain |
| `SecurityDomains.csv` | Security domains with ID, name, description |
| `Permissions.csv` | Access permissions extracted from ACLs (SIDs) |

## Compilation

### Prerequisites

- Windows 7 SP1 or later
- MinGW-w64 (GCC 11+) installed at `C:\Users\freddievr\mingw64`
- MS SQL Server ODBC Driver (usually pre-installed on Windows)

### Compile Command

```bash
cd C:\Users\freddievr\claude-projects\IntelliSTOR_Migration\1_Migration_Users

C:\Users\freddievr\mingw64\bin\g++.exe -std=c++17 -O2 -static ^
  -o papyrus_extract_users_permissions.exe ^
  papyrus_extract_users_permissions.cpp ^
  -lodbc32 -lodbccp32
```

**Flags:**
- `-std=c++17`: Use C++17 standard for filesystem support
- `-O2`: Optimize for performance
- `-static`: Static linking for airgap deployment
- `-lodbc32 -lodbccp32`: Link ODBC libraries

### Verify Compilation

```bash
papyrus_extract_users_permissions.exe --help
```

Expected output:
```
Usage: papyrus_extract_users_permissions.exe [OPTIONS]

Required:
  --server SERVER       MS SQL Server hostname or IP
  --database DATABASE   Database name
  --output OUTPUT_DIR   Output directory for CSV files
...
```

## Usage

### Basic Usage with Windows Authentication

```bash
papyrus_extract_users_permissions.exe ^
  --server SQLSRV01 ^
  --database IntelliSTOR_SG ^
  --output .\output\Users_SG ^
  --windows-auth
```

### Usage with SQL Server Authentication

```bash
papyrus_extract_users_permissions.exe ^
  --server SQLSRV01 ^
  --database IntelliSTOR_SG ^
  --output .\output\Users_SG ^
  --user sa ^
  --password MyPassword123
```

### Quiet Mode (No Progress Messages)

```bash
papyrus_extract_users_permissions.exe ^
  --server SQLSRV01 ^
  --database IntelliSTOR_SG ^
  --output .\output\Users_SG ^
  --windows-auth ^
  --quiet
```

## Batch File Usage

### Using papyrus_extract_users_permissions.bat

The included batch file simplifies execution by loading environment variables from `Migration_Environment.bat`:

```batch
papyrus_extract_users_permissions.bat
```

Or with quiet mode:

```batch
papyrus_extract_users_permissions.bat --quiet
```

### Environment Variables

The batch file uses these environment variables (from `Migration_Environment.bat`):

| Variable | Description | Default |
|----------|-------------|---------|
| `SQLServer` | MS SQL Server hostname | `localhost` |
| `SQL-SG-Database` | Database name | `IntelliSTOR_SG` |
| `Users-SG` | Output directory | `.\output\Users_SG` |

### Batch File Output

The batch file creates a timestamped log file:
```
papyrus_extract_users_permissions_YYYYMMDD_HHMMSS.log
```

Log includes:
- Start/end timestamps
- Command executed
- Extraction progress
- Error messages (if any)
- Exit code

## Command-Line Options

| Option | Type | Description |
|--------|------|-------------|
| `--server` | required | MS SQL Server hostname or IP address |
| `--database` | required | Database name (e.g., IntelliSTOR_SG) |
| `--output` | required | Output directory for CSV files |
| `--windows-auth` | flag | Use Windows Authentication (default) |
| `--user` | optional | SQL Server username (disables Windows auth) |
| `--password` | optional | SQL Server password (used with --user) |
| `--quiet` | flag | Suppress progress messages |
| `--help` | flag | Show help message |

## Database Tables

The extractor queries these IntelliSTOR tables:

### Primary Tables
- `SCM_USERS` or `USER_PROFILE` - User accounts
- `SCM_GROUPS` or `USER_GROUPS` - Security groups
- `SCM_USER_GROUP` or `USER_GROUP_MEMBERSHIP` - Memberships
- `SECTIONS` - Report sections
- `SECURITY_DOMAINS` - Security domains
- `SECTION_SECURITY` - ACL data (binary)

### Fallback Logic
If a primary table is not found, the extractor tries alternative table names. This ensures compatibility with different IntelliSTOR versions.

## SID Parsing

The tool parses Windows Security Identifiers (SIDs) from binary ACL data:

### SID Format
```
S-<Revision>-<Authority>-<SubAuthority1>-<SubAuthority2>-...
```

Example:
```
S-1-5-21-123456789-987654321-1122334455-1001
```

### Well-Known SIDs
- `S-1-1-0` - Everyone
- `S-1-5-32-*` - Built-in groups
- `S-1-5-21-*-*-*-<RID>` - Domain users/groups
  - RID < 1000: Well-known groups
  - RID >= 1000: Domain users

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Invalid arguments |
| 2 | Database connection failed |
| 3 | Extraction failed |
| 4 | Output directory error |

## Troubleshooting

### Connection Failed

**Error:** `Connection failed: [Microsoft][ODBC SQL Server Driver]...`

**Solutions:**
1. Verify SQL Server is running and accessible
2. Check server name/IP is correct
3. Verify Windows Authentication is enabled (if using --windows-auth)
4. Check SQL Server login credentials (if using --user/--password)
5. Ensure ODBC Driver is installed: `odbcad32.exe`

### Table Not Found

**Error:** `Could not find users table` or similar

**Solutions:**
1. Verify database name is correct
2. Check user has SELECT permissions on tables
3. Confirm database is an IntelliSTOR database
4. Tables may have different names in your IntelliSTOR version

### Output Directory Error

**Error:** `Error creating output directory`

**Solutions:**
1. Check you have write permissions
2. Verify parent directory exists
3. Check path length is not too long
4. Ensure no special characters in path

### Missing ODBC Driver

**Error:** `DRIVER={SQL Server}...not found`

**Solutions:**
1. Install "ODBC Driver for SQL Server" from Microsoft
2. Or install "SQL Server Native Client"
3. Check installed drivers: Run `odbcad32.exe` → Drivers tab

## Performance

### Typical Performance
- **Small database** (< 1,000 users): 1-5 seconds
- **Medium database** (1,000 - 10,000 users): 5-30 seconds
- **Large database** (> 10,000 users): 30-120 seconds

Performance depends on:
- Network latency to SQL Server
- Database size and complexity
- Number of ACL entries to parse
- Disk I/O speed for CSV writing

## Limitations

### Compared to Python Version

**Not Implemented:**
- Test data generation (--TESTDATA flag)
- Detailed ACE (Access Control Entry) parsing
- Full permission flags decoding
- LDAP integration
- Advanced logging options

**Simplified:**
- SID-to-username resolution (outputs SIDs only)
- ACL parsing (extracts SIDs but not full access masks)
- Error handling (basic ODBC error messages)

### Why Simplified?

This is a **Papyrus** variant - focused on core extraction for airgap deployment:
- ✅ Smaller executable size (< 1 MB)
- ✅ No Python runtime required
- ✅ Faster startup time
- ✅ Static linking for portability
- ✅ Simplified command-line interface

## Airgap Deployment

### Files Required

Copy to airgap machine:
```
✓ papyrus_extract_users_permissions.exe (< 1 MB)
✓ papyrus_extract_users_permissions.bat
✓ Migration_Environment.bat (optional)
```

### Requirements on Airgap Machine

- Windows 7 SP1 or later
- MS SQL Server ODBC Driver (usually pre-installed)
- Network access to SQL Server
- Write permissions to output directory

### No Additional Dependencies

The executable is statically linked and requires:
- ❌ No Python runtime
- ❌ No Visual C++ Redistributables
- ❌ No external DLLs
- ✅ Only Windows system libraries (kernel32.dll, odbc32.dll)

## Examples

### Example 1: Extract from Singapore Database

```batch
papyrus_extract_users_permissions.exe ^
  --server SQLSRV-SG ^
  --database IntelliSTOR_SG ^
  --output .\output\Users_SG ^
  --windows-auth
```

**Output:**
```
=================================================
IntelliSTOR Users & Permissions Extractor (Papyrus)
=================================================

Connected to SQLSRV-SG/IntelliSTOR_SG
Extracting users...
  Extracted 245 users
Extracting groups...
  Extracted 18 groups
Extracting user-group memberships...
  Extracted 512 memberships
Extracting sections...
  Extracted 1,832 sections
Extracting security domains...
  Extracted 3 security domains
Extracting permissions from ACLs...
  Extracted 4,291 permission entries

=================================================
Extraction completed successfully
Output directory: .\output\Users_SG
=================================================
```

### Example 2: Extract Using Batch File

```batch
REM Set environment variables first
set SQLServer=SQLSRV-SG
set SQL-SG-Database=IntelliSTOR_SG
set Users-SG=C:\Migration\Users_SG

REM Run extraction
papyrus_extract_users_permissions.bat
```

### Example 3: Quiet Mode for Automation

```batch
papyrus_extract_users_permissions.exe ^
  --server SQLSRV01 ^
  --database IntelliSTOR ^
  --output .\output ^
  --windows-auth ^
  --quiet

if %ERRORLEVEL% equ 0 (
    echo Success
) else (
    echo Failed
    exit /b 1
)
```

## CSV File Formats

### Users.csv
```csv
USER_ID,USERNAME,FULL_NAME,EMAIL,STATUS,EXTRACTED_AT
1001,jsmith,John Smith,jsmith@example.com,ACTIVE,2026-02-07 14:30:00
1002,mjones,Mary Jones,mjones@example.com,ACTIVE,2026-02-07 14:30:00
```

### UserGroups.csv
```csv
GROUP_ID,GROUP_NAME,DESCRIPTION,EXTRACTED_AT
501,Administrators,System administrators,2026-02-07 14:30:00
502,Report_Viewers,Users who can view reports,2026-02-07 14:30:00
```

### UserGroupMemberships.csv
```csv
USER_ID,GROUP_ID,EXTRACTED_AT
1001,501,2026-02-07 14:30:00
1002,502,2026-02-07 14:30:00
```

### Sections.csv
```csv
SECTION_ID,SECTION_NAME,OWNER_ID,SECURITY_DOMAIN_ID,EXTRACTED_AT
55737,Financial Reports,1001,1,2026-02-07 14:30:00
14260,HR Reports,1002,2,2026-02-07 14:30:00
```

### Permissions.csv
```csv
RESOURCE_TYPE,RESOURCE_ID,PRINCIPAL_SID,PRINCIPAL_TYPE,ACCESS_MASK,EXTRACTED_AT
SECTION,55737,S-1-5-21-123-456-789-1001,USER,UNKNOWN,2026-02-07 14:30:00
SECTION,55737,S-1-1-0,EVERYONE,UNKNOWN,2026-02-07 14:30:00
```

## Integration with Python Tools

The Papyrus C++ extractor generates CSV files compatible with Python import scripts:

```python
import pandas as pd

# Load extracted data
users = pd.read_csv('output/Users.csv')
groups = pd.read_csv('output/UserGroups.csv')
memberships = pd.read_csv('output/UserGroupMemberships.csv')

# Process or import to target system
...
```

## Version History

- **v1.0** (2026-02-07): Initial release
  - MS SQL Server ODBC connectivity
  - User/group/section extraction
  - Basic ACL/SID parsing
  - CSV output generation
  - Windows and SQL authentication
  - Airgap deployment ready

## License

Proprietary - IntelliSTOR Migration Project

## Support

For issues or questions, contact the migration team.
