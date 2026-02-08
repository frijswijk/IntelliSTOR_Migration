# Papyrus C++ Database Extractors

## Overview

This document describes the three **Papyrus** C++ database extractors created for airgap deployment. These are simplified, statically-linked versions of the Python extraction scripts, designed for environments without Python runtime or external dependencies.

## Extractors Summary

| Tool | Location | Purpose | Output Files |
|------|----------|---------|--------------|
| `papyrus_extract_users_permissions.exe` | `1_Migration_Users/` | Extract users, groups, sections, permissions | 6 CSV files |
| `papyrus_extract_folder_species.exe` | `3_Migration_Report_Species_Folders/` | Extract folder hierarchy and report species | 3 CSV files |
| `papyrus_extract_instances.exe` | `4_Migration_Instances/` | Extract report instances with year filtering | Multiple CSV files (one per species) |

## Key Features

✅ **Statically Linked**: No external DLL dependencies (except Windows system libraries)
✅ **Airgap Ready**: Single executable per tool, no Python runtime required
✅ **ODBC Connectivity**: MS SQL Server via Windows ODBC
✅ **Windows & SQL Auth**: Supports both authentication methods
✅ **Batch File Integration**: Each tool has a corresponding .bat file for automation
✅ **Progress Logging**: Timestamped log files with execution details
✅ **Error Handling**: Clear error messages and exit codes

## Compilation Instructions

### Prerequisites

- Windows 7 SP1 or later
- MinGW-w64 (GCC 11+) installed at `C:\Users\freddievr\mingw64`
- MS SQL Server ODBC Driver (pre-installed on Windows)

### Compile Commands

#### 1. Users & Permissions Extractor

```bash
cd C:\Users\freddievr\claude-projects\IntelliSTOR_Migration\1_Migration_Users

C:\Users\freddievr\mingw64\bin\g++.exe -std=c++17 -O2 -static ^
  -o papyrus_extract_users_permissions.exe ^
  papyrus_extract_users_permissions.cpp ^
  -lodbc32 -lodbccp32
```

#### 2. Folder & Species Extractor

```bash
cd C:\Users\freddievr\claude-projects\IntelliSTOR_Migration\3_Migration_Report_Species_Folders

C:\Users\freddievr\mingw64\bin\g++.exe -std=c++17 -O2 -static ^
  -o papyrus_extract_folder_species.exe ^
  papyrus_extract_folder_species.cpp ^
  -lodbc32 -lodbccp32
```

#### 3. Instances Extractor

```bash
cd C:\Users\freddievr\claude-projects\IntelliSTOR_Migration\4_Migration_Instances

C:\Users\freddievr\mingw64\bin\g++.exe -std=c++17 -O2 -static ^
  -o papyrus_extract_instances.exe ^
  papyrus_extract_instances.cpp ^
  -lodbc32 -lodbccp32
```

### Compilation Flags

- `-std=c++17`: C++17 standard (for filesystem support)
- `-O2`: Optimize for performance
- `-static`: Static linking for portability
- `-lodbc32 -lodbccp32`: Link ODBC libraries

## Usage

### 1. Users & Permissions Extractor

#### Direct Execution

```bash
papyrus_extract_users_permissions.exe ^
  --server SQLSRV01 ^
  --database IntelliSTOR_SG ^
  --output .\output\Users_SG ^
  --windows-auth
```

#### Batch File Execution

```batch
REM Edit environment variables in Migration_Environment.bat first
papyrus_extract_users_permissions.bat
```

#### Output Files

- `Users.csv` - User accounts
- `UserGroups.csv` - Security groups
- `UserGroupMemberships.csv` - User-group mappings
- `Sections.csv` - Report sections
- `SecurityDomains.csv` - Security domains
- `Permissions.csv` - Access permissions (SIDs from ACLs)

### 2. Folder & Species Extractor

#### Direct Execution

```bash
papyrus_extract_folder_species.exe ^
  --server SQLSRV01 ^
  --database IntelliSTOR_SG ^
  --Country SG ^
  --output-dir .\output ^
  --windows-auth
```

**Country Code Options:**
- 2-letter code (e.g., `SG`, `HK`, `AU`) - assigns to all folders
- `0` - auto-detect from folder names in hierarchy

#### Batch File Execution

```batch
REM Edit environment variables in Migration_Environment.bat first
papyrus_extract_folder_species.bat
```

#### Output Files

- `Folder_Hierarchy.csv` - Valid folder hierarchy (excludes orphans and ITEM_TYPE=3)
- `Folder_Report.csv` - Folder-to-report species mappings
- `Report_Species.csv` - Unique report species with IN_USE flag

### 3. Instances Extractor

#### Direct Execution

```bash
papyrus_extract_instances.exe ^
  --server SQLSRV01 ^
  --database IntelliSTOR_SG ^
  --start-year 2023 ^
  --input Report_Species.csv ^
  --output-dir .\output ^
  --windows-auth
```

**Optional:**
- `--end-year 2024` - Filter up to end year (exclusive)
- `--quiet` - Minimal console output

#### Batch File Execution

```batch
REM Edit environment variables in Migration_Environment.bat first
set StartYear=2023
set EndYear=2024
papyrus_extract_instances.bat
```

#### Output Files

Multiple CSV files, one per report species:
- `{ReportName}_{StartYear}.csv` (e.g., `HKCIF001_2023.csv`)
- `{ReportName}_{StartYear}_{EndYear}.csv` (if end year specified)

Each file contains:
- REPORT_SPECIES_NAME, FILENAME, RPT_FILENAME, COUNTRY, YEAR, REPORT_DATE, AS_OF_TIMESTAMP, RPT_FILE_ID

## Command-Line Options

### Users & Permissions Extractor

| Option | Required | Description |
|--------|----------|-------------|
| `--server` | Yes | SQL Server hostname or IP |
| `--database` | Yes | Database name |
| `--output` | Yes | Output directory |
| `--windows-auth` | No* | Use Windows Authentication |
| `--user` | No* | SQL Server username |
| `--password` | No* | SQL Server password |
| `--quiet` | No | Suppress progress messages |

*Either `--windows-auth` or both `--user` and `--password` required

### Folder & Species Extractor

| Option | Required | Description |
|--------|----------|-------------|
| `--server` | Yes | SQL Server hostname or IP |
| `--database` | Yes | Database name |
| `--Country` | Yes | Country code (2-letter or "0") |
| `--output-dir` | No | Output directory (default: current) |
| `--windows-auth` | No* | Use Windows Authentication |
| `--user` | No* | SQL Server username |
| `--password` | No* | SQL Server password |
| `--quiet` | No | Suppress progress messages |

### Instances Extractor

| Option | Required | Description |
|--------|----------|-------------|
| `--server` | Yes | SQL Server hostname or IP |
| `--database` | Yes | Database name |
| `--start-year` | Yes | Start year (e.g., 2023) |
| `--end-year` | No | Optional end year |
| `--input` | No | Input Report_Species.csv (default: Report_Species.csv) |
| `--output-dir` | No | Output directory (default: current) |
| `--windows-auth` | No* | Use Windows Authentication |
| `--user` | No* | SQL Server username |
| `--password` | No* | SQL Server password |
| `--quiet` | No | Suppress progress messages |

## Environment Variables

The batch files load environment variables from `Migration_Environment.bat` if it exists in the parent directory:

### Users & Permissions

- `SQLServer` - SQL Server hostname (default: localhost)
- `SQL-SG-Database` - Database name (default: IntelliSTOR_SG)
- `Users-SG` - Output directory (default: .\output\Users_SG)

### Folder & Species

- `SQLServer` - SQL Server hostname
- `SQL-SG-Database` - Database name
- `CountryCode` - Country code (default: SG)
- `FolderSpeciesOutput` - Output directory (default: .\output)

### Instances

- `SQLServer` - SQL Server hostname
- `SQL-SG-Database` - Database name
- `StartYear` - Start year (default: 2023)
- `EndYear` - Optional end year
- `InstancesOutput` - Output directory (default: .\output)
- `ReportSpeciesCSV` - Input CSV (default: Report_Species.csv)

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Invalid arguments |
| 2 | Database connection failed |
| 3 | Extraction failed / Input file error |
| 4 | Output directory error |

## Airgap Deployment

### Files to Copy

For each extractor, copy to airgap machine:

**Users & Permissions:**
```
✓ papyrus_extract_users_permissions.exe
✓ papyrus_extract_users_permissions.bat
```

**Folder & Species:**
```
✓ papyrus_extract_folder_species.exe
✓ papyrus_extract_folder_species.bat
```

**Instances:**
```
✓ papyrus_extract_instances.exe
✓ papyrus_extract_instances.bat
✓ Report_Species.csv (generated by Folder & Species extractor)
```

**Optional:**
```
✓ Migration_Environment.bat (environment variables)
```

### Airgap Machine Requirements

- Windows 7 SP1 or later
- MS SQL Server ODBC Driver (usually pre-installed)
- Network access to SQL Server
- Write permissions to output directories

### No Additional Dependencies

The executables are statically linked and require:
- ❌ No Python runtime
- ❌ No Visual C++ Redistributables
- ❌ No external DLLs
- ✅ Only Windows system libraries (kernel32.dll, odbc32.dll)

### Verification

Check static linking:
```bash
dumpbin /dependents papyrus_extract_users_permissions.exe
```

Should only show Windows system DLLs.

## Workflow Example

### Complete Extraction Workflow

```batch
REM 1. Extract users and permissions
cd C:\Migration\1_Migration_Users
papyrus_extract_users_permissions.bat

REM 2. Extract folder hierarchy and report species
cd C:\Migration\3_Migration_Report_Species_Folders
papyrus_extract_folder_species.bat

REM 3. Extract report instances (uses Report_Species.csv from step 2)
cd C:\Migration\4_Migration_Instances
copy ..\3_Migration_Report_Species_Folders\output\Report_Species.csv .
papyrus_extract_instances.bat
```

### Automated Script

```batch
@echo off
setlocal

set BASE_DIR=C:\Migration
set LOG_FILE=%BASE_DIR%\extraction_log_%date:~10,4%%date:~4,2%%date:~7,2%.txt

echo ================================================= > "%LOG_FILE%"
echo IntelliSTOR Papyrus Extraction - Full Workflow >> "%LOG_FILE%"
echo ================================================= >> "%LOG_FILE%"
echo. >> "%LOG_FILE%"

echo Step 1: Users and Permissions >> "%LOG_FILE%"
cd %BASE_DIR%\1_Migration_Users
call papyrus_extract_users_permissions.bat >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% neq 0 goto :error

echo. >> "%LOG_FILE%"
echo Step 2: Folder Hierarchy and Report Species >> "%LOG_FILE%"
cd %BASE_DIR%\3_Migration_Report_Species_Folders
call papyrus_extract_folder_species.bat >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% neq 0 goto :error

echo. >> "%LOG_FILE%"
echo Step 3: Report Instances >> "%LOG_FILE%"
cd %BASE_DIR%\4_Migration_Instances
copy ..\3_Migration_Report_Species_Folders\output\Report_Species.csv . >> "%LOG_FILE%" 2>&1
call papyrus_extract_instances.bat >> "%LOG_FILE%" 2>&1
if %ERRORLEVEL% neq 0 goto :error

echo. >> "%LOG_FILE%"
echo ================================================= >> "%LOG_FILE%"
echo All extractions completed successfully >> "%LOG_FILE%"
echo ================================================= >> "%LOG_FILE%"
exit /b 0

:error
echo. >> "%LOG_FILE%"
echo ================================================= >> "%LOG_FILE%"
echo ERROR: Extraction failed at step >> "%LOG_FILE%"
echo ================================================= >> "%LOG_FILE%"
exit /b 1
```

## Troubleshooting

### Connection Failed

**Error:** `Connection failed: [Microsoft][ODBC SQL Server Driver]...`

**Solutions:**
1. Verify SQL Server is running and accessible
2. Check server name/IP is correct
3. Test with `sqlcmd` or SQL Server Management Studio
4. Verify Windows Authentication is enabled (if using --windows-auth)
5. Check firewall allows SQL Server port (default: 1433)
6. Ensure ODBC Driver is installed: Run `odbcad32.exe` → Drivers tab

### Table Not Found

**Error:** `Could not find users table` or similar

**Solutions:**
1. Verify database name is correct
2. Check user has SELECT permissions on tables
3. Confirm database is an IntelliSTOR database
4. Tables may have different names in your IntelliSTOR version

### Missing ODBC Driver

**Error:** `DRIVER={SQL Server}...not found`

**Solutions:**
1. Install "ODBC Driver for SQL Server" from Microsoft
2. Or install "SQL Server Native Client"
3. Check installed drivers: Run `odbcad32.exe` → Drivers tab
4. Use "SQL Server Native Client 11.0" if available

### Output Directory Error

**Error:** `Error creating output directory`

**Solutions:**
1. Check you have write permissions
2. Verify parent directory exists
3. Check path length is not too long (< 260 characters)
4. Ensure no special characters in path

## Comparison with Python Versions

### Users & Permissions Extractor

**Python Features NOT Implemented:**
- Test data generation (--TESTDATA flag)
- Detailed ACE (Access Control Entry) parsing
- Full permission flags decoding
- LDAP integration
- Advanced logging options

**Simplified:**
- Basic SID parsing from binary ACLs
- Minimal output columns
- Simplified command-line interface

### Folder & Species Extractor

**Python Features NOT Implemented:**
- Country code conflict logging (log.txt)
- Detailed progress tracking
- Multiple table name fallbacks

**Simplified:**
- Core folder hierarchy validation
- Country code assignment (fixed or auto-detect)
- Essential CSV outputs

### Instances Extractor

**Python Features NOT Implemented:**
- Timezone conversion (AS_OF_TIMESTAMP → UTC)
- SEGMENTS population from RPT file SECTIONHDR
- Progress tracking and resume capability
- IN_USE flag updates in Report_Species.csv
- Julian date conversion (REPORT_DATE column)
- Year extraction from filename

**Simplified:**
- Basic instance extraction with year filtering
- Minimal CSV output columns
- Sequential processing (no progress file)

## Performance

### Typical Performance

| Tool | Small DB | Medium DB | Large DB |
|------|----------|-----------|----------|
| Users & Permissions | 1-5s | 5-30s | 30-120s |
| Folder & Species | 5-15s | 15-60s | 60-300s |
| Instances | 1-5 min | 5-30 min | 30-120 min |

Performance depends on:
- Network latency to SQL Server
- Database size and complexity
- Number of reports/instances
- Disk I/O speed for CSV writing

## Version History

- **v1.0** (2026-02-07): Initial release
  - Users & Permissions Extractor
  - Folder & Species Extractor
  - Instances Extractor
  - Batch file integration
  - Static linking for airgap deployment

## Support

For issues or questions, contact the migration team.

## Related Documentation

- `1_Migration_Users/PAPYRUS_EXTRACT_README.md` - Detailed users/permissions extractor docs
- `8_Create_IRPT_File/CONCATENATED_FILE_SUPPORT.md` - RPT file builder documentation
- `9_Papyrus_rpt_page_extractor/README.md` - RPT page extractor documentation
