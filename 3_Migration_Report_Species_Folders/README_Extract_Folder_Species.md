# Extract_Folder_Species.py - Documentation

## Overview
Extract_Folder_Species.py is a database-driven version of generate_folder_report_csvs.py that extracts folder hierarchy and report species data directly from MS SQL Server instead of reading CSV files.

## Purpose
Extracts folder and report species data from IntelliSTOR MS SQL Server database and generates three CSV files for migration purposes.

## Output Files

1. **Folder_Hierarchy.csv** - Valid folder hierarchy (excluding orphans)
2. **Folder_Report.csv** - Folder-to-report mappings with names
3. **Report_Species.csv** - Unique report species with usage flag
4. **log.txt** - Country code conflicts (only if conflicts detected)

## Requirements

### Python Dependencies
```bash
pip install pymssql
```

### Database Tables
The script queries these tables:
- **FOLDER** - Folder hierarchy
- **FOLDER_SPECIES** - Folder-to-report mappings
- **REPORT_SPECIES_NAME** - Report names and display names

### Database Permissions
The database user needs SELECT permission on:
- FOLDER
- FOLDER_SPECIES
- REPORT_SPECIES_NAME

## Usage

### Basic Usage

#### Windows Authentication
```bash
python Extract_Folder_Species.py --server localhost --database IntelliSTOR --windows-auth --Country SG
```

#### SQL Server Authentication
```bash
python Extract_Folder_Species.py --server localhost --database IntelliSTOR --user sa --password MyPassword --Country 0
```

### Advanced Options

#### Custom Output Directory
```bash
python Extract_Folder_Species.py --server localhost --database IntelliSTOR --windows-auth --Country HK --output-dir C:\Output
```

#### Quiet Mode (Minimal Console Output)
```bash
python Extract_Folder_Species.py --server localhost --database IntelliSTOR --windows-auth --Country 0 --quiet
```

#### Full Example
```bash
python Extract_Folder_Species.py ^
    --server SQLSERVER01 ^
    --port 1433 ^
    --database IntelliSTOR ^
    --user dbuser ^
    --password dbpass ^
    --Country SG ^
    --output-dir C:\Migration\Taxonomy ^
    --quiet
```

## Command-Line Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--server` | Yes | - | SQL Server host/IP address |
| `--database` | Yes | - | Database name |
| `--Country` | Yes | - | Country code mode: 2-letter code (SG, HK, etc.) for fixed assignment, or "0" for auto-detection from folder names |
| `--port` | No | 1433 | SQL Server port |
| `--user` | No* | - | Username for SQL Server authentication |
| `--password` | No* | - | Password for SQL Server authentication |
| `--windows-auth` | No* | False | Use Windows Authentication |
| `--output-dir`, `-o` | No | . | Output directory for CSV files |
| `--quiet` | No | False | Quiet mode (minimal console output) |

*Either `--windows-auth` OR both `--user` and `--password` must be provided

## Output File Formats

### 1. Folder_Hierarchy.csv

**Columns:**
- ITEM_ID - Folder ID
- NAME - Folder name
- PARENT_ID - Parent folder ID (0 for root)
- ITEM_TYPE - Folder type
- Country_Code - Country code (e.g., SG, UK, US)

**Sample:**
```csv
ITEM_ID,NAME,PARENT_ID,ITEM_TYPE,Country_Code
1,Root,0,1,SG
2,SG,1,1,SG
3,UK,1,1,UK
4,Reports,2,1,SG
```

### 2. Folder_Report.csv

**Columns:**
- ITEM_ID - Folder ID
- ITEM_NAME - Folder name
- Report_Species_Id - Report species ID
- Report_Species_Name - Report name
- Report_Species_DisplayName - Display name
- Country_Code - Country code

**Sample:**
```csv
ITEM_ID,ITEM_NAME,Report_Species_Id,Report_Species_Name,Report_Species_DisplayName,Country_Code
4,Reports,100,BC2060P,Balance Confirmation,SG
4,Reports,101,BC2061P,Transaction Report,SG
```

### 3. Report_Species.csv

**Columns:**
- Report_Species_Id - Unique report ID
- Report_Species_Name - Report name
- Report_Species_DisplayName - Display name
- Country_Code - Country code
- In_Use - Usage flag (1 = in use)

**Sample:**
```csv
Report_Species_Id,Report_Species_Name,Report_Species_DisplayName,Country_Code,In_Use
100,BC2060P,Balance Confirmation,SG,1
101,BC2061P,Transaction Report,SG,1
```

## Logic and Features

### Folder Validation
The script identifies and excludes:
- **Orphaned folders** - Folders whose parent doesn't exist
- **ITEM_TYPE=3 folders** - Special folder types to be excluded
- **Descendants of excluded folders** - All children of orphaned/excluded folders

Only valid folders with complete parent chains to root are included.

### Country Code Modes

The `--Country` parameter controls how country codes are assigned:

**Fixed Mode (2-letter code):**
- Example: `--Country SG` or `--Country HK`
- Assigns the specified country code to ALL folders
- Folder names are ignored for country detection
- Value is automatically converted to uppercase

**Auto-Detection Mode ("0"):**
- Example: `--Country 0`
- Country codes detected from folder hierarchy:
  1. If folder name is exactly 2-character country code (SG, UK, etc.), that folder and descendants get that code
  2. Otherwise, folders inherit country code from parent
  3. Root folders default to 'SG'

### Country Code Assignment (Auto-Detection Mode Only)

When using `--Country 0`, country codes are assigned based on folder hierarchy:
1. If a folder name is exactly a 2-character country code (SG, UK, etc.), that folder and all descendants get that code
2. Otherwise, folders inherit the country code from their parent
3. Root folders default to 'SG'

### Conflict Detection
If a report species appears in folders with different country codes:
- The first non-SG code is used
- Conflicts are logged to `log.txt`
- SG codes can be overridden by specific country codes

### Report Name Logic
- **Report_Species_DisplayName**: Always from ITEM_ID=0 record
- **Report_Species_Name**: From ITEM_ID=1 if exists, otherwise from ITEM_ID=0

## Logging

### Log File
- **Location**: `Extract_Folder_Species.log` in output directory
- **Level**: DEBUG (all operations logged)

### Console Output

**Normal Mode:**
```
INFO - Connecting to SQL Server: localhost:1433, database: IntelliSTOR
INFO - Database connection established successfully
INFO - Loading folders from FOLDER table...
INFO - Loaded 5000 folders
INFO - Loading folder-species mappings from FOLDER_SPECIES table...
INFO - Loaded 15000 folder-species mappings
INFO - Validating folder hierarchy...
INFO - Valid folders: 4800
INFO - Excluded folders: 200
INFO - Generating Folder_Hierarchy.csv...
INFO - Written 4800 folders to Folder_Hierarchy.csv
...
```

**Quiet Mode:**
```
Completed: Generated Folder_Hierarchy.csv, Folder_Report.csv, and Report_Species.csv
```

## Error Handling

### Connection Errors
- Invalid credentials → Error message with connection details
- Server not reachable → Error message with server info
- Database not found → Error message with database name

### Data Errors
- Missing tables → Error message indicating which table is missing
- Missing columns → Error with column name
- Data type issues → Logged and skipped

### Recovery
All errors are logged to the log file for troubleshooting.

## Troubleshooting

### Error: "Failed to connect to SQL Server"
**Solutions:**
- Verify server name/IP is correct
- Check that SQL Server is running
- Verify port number (default: 1433)
- Check firewall settings
- Verify user has database access

### Error: "Login failed for user"
**Solutions:**
- Verify username and password
- Try using `--windows-auth` instead
- Check user permissions in SQL Server

### Error: "Invalid column name"
**Solutions:**
- Verify database schema matches expected structure
- Check that tables FOLDER, FOLDER_SPECIES, REPORT_SPECIES_NAME exist
- Verify column names are correct

### No Output Files Created
**Solutions:**
- Check log file for errors
- Verify tables contain data
- Check output directory permissions

## Performance

### Expected Performance
- **Small database** (<10,000 folders): 1-2 minutes
- **Medium database** (10,000-100,000 folders): 2-10 minutes
- **Large database** (>100,000 folders): 10-30 minutes

### Optimization Tips
- Run on the same machine as SQL Server
- Use Windows Authentication when possible
- Ensure database has proper indexes on ITEM_ID, REPORT_SPECIES_ID

## Comparison with generate_folder_report_csvs.py

| Feature | generate_folder_report_csvs.py | Extract_Folder_Species.py |
|---------|-------------------------------|---------------------------|
| Data Source | CSV files | MS SQL Database |
| Input Required | 3 CSV files | Database connection |
| Performance | Fast (file I/O) | Moderate (network queries) |
| Data Freshness | Requires export | Always current |
| Dependencies | None | pymssql |

## See Also
- `Extract_Instances.py` - Extract report instances
- `Extract_Users_Permissions.py` - Extract users and permissions
- `generate_folder_report_csvs.py` - CSV-based version
