# Extract Instances Sections - Complete Documentation

## Overview

`Extract_Instances.py` is a Python script that extracts report instance data from a SQL Server IntelliSTOR database and exports it to CSV files. The script processes report species from a master CSV file, queries the database for report instances, and generates separate CSV files per report. SEGMENTS are populated from RPT file SECTIONHDR binary structures. RPTFILE.FILENAME values are automatically path-stripped for display and date parsing.

**Version**: 3.0 (SEGMENTS from RPT file SECTIONHDR)
**Database**: SQL Server (STRING_AGG no longer required)
**Python Version**: 3.7+

---

## Table of Contents

1. [Features](#features)
2. [Installation](#installation)
3. [Command-Line Arguments](#command-line-arguments)
4. [Database Schema Requirements](#database-schema-requirements)
5. [Input/Output Format](#inputoutput-format)
6. [RPT File SECTIONHDR Extraction](#rpt-file-sectionhdr-extraction)
7. [Usage Examples](#usage-examples)
8. [Processing Workflow](#processing-workflow)
9. [Troubleshooting](#troubleshooting)
10. [Architecture](#architecture)
11. [Logging](#logging)

---

## Features

### Core Functionality
- **Batch Processing**: Processes multiple report species from a master CSV file
- **Resume Capability**: Tracks progress and can resume from last processed report
- **Year Filtering**: Filters report instances by year range (start/end year)
- **Timezone Conversion**: Converts AS_OF_TIMESTAMP from source timezone to UTC
- **RPT File SECTIONHDR**: SEGMENTS populated from RPT file binary SECTIONHDR structure (requires --rptfolder)
- **Automatic In_Use Updates**: Sets In_Use=0 for reports with no instances in specified year range

### Important Note on SEGMENTS
The SEGMENTS column is populated exclusively from the RPT file's SECTIONHDR binary structure
(via `rpt_section_reader.py`), NOT from the database `REPORT_INSTANCE_SEGMENT` table.
The `REPORT_INSTANCE_SEGMENT` table tracks ingestion arrival chunks, not section segregation of pages.
When `--rptfolder` is not provided, the SEGMENTS column will be empty.

### Performance & Reliability
- **Progress Tracking**: Saves progress after each report for safe interruption
- **Connection Pooling**: Efficient database connection management
- **Caching**: RPT SECTIONHDR results cached in memory per filename
- **Error Recovery**: Continues processing remaining reports after errors

### Output Modes
- **Normal Mode**: Detailed logging with INFO level messages
- **Quiet Mode**: Single-line progress counter for minimal output

---

## Installation

### Prerequisites

```bash
# Python 3.7 or higher
python --version

# Install required packages
pip install pymssql pytz
```

### Package Requirements

- **pymssql**: SQL Server database connectivity
- **pytz**: IANA timezone database for timezone conversions
- **csv, argparse, logging, sys, os, pathlib, datetime, re**: Standard library (included)

### Database Requirements

- SQL Server (STRING_AGG no longer required)
- Read access to tables: REPORT_INSTANCE, RPTFILE_INSTANCE, RPTFILE
- Network connectivity to SQL Server instance
- Note: REPORT_INSTANCE_SEGMENT and SECTION tables are no longer queried (SEGMENTS comes from RPT files)

---

## Command-Line Arguments

### Required Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| `--server` | SQL Server hostname or IP address | `localhost`, `192.168.1.100` |
| `--database` | Database name | `IntelliSTOR` |
| `--start-year` | Start year for filtering (inclusive) | `2023` |

### Authentication (Choose One)

| Argument | Description | Example |
|----------|-------------|---------|
| `--windows-auth` | Use Windows Authentication | Flag only |
| `--user` + `--password` | SQL Server authentication credentials | `--user sa --password MyP@ss` |

### Optional Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--port` | `1433` | SQL Server port number |
| `--end-year` | None | End year for filtering (exclusive) |
| `--year-from-filename` | False | Calculate YEAR column from filename (first 2 chars) instead of AS_OF_TIMESTAMP |
| `--timezone` | `Asia/Singapore` | Source timezone for AS_OF_TIMESTAMP values (IANA format) |
| `--rptfolder` | None | Directory containing .RPT files for SECTIONHDR-based SEGMENTS extraction. Without this, SEGMENTS will be empty. |
| `--input` / `-i` | `Report_Species.csv` | Path to input CSV file containing report species |
| `--output-dir` / `-o` | `.` (current) | Output directory for CSV files and logs |
| `--quiet` | False | Quiet mode - single-line progress counter only |

### Timezone Values

Common IANA timezone values:
- `Asia/Singapore` (UTC+8)
- `America/New_York` (Eastern Time)
- `Europe/London` (GMT/BST)
- `Asia/Tokyo` (JST)
- `UTC` (Coordinated Universal Time)

Full list: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones

---

## Database Schema Requirements

### Required Tables and Columns

#### 1. REPORT_INSTANCE
Primary table for report instances.

**Required Columns:**
- `DOMAIN_ID` (int)
- `REPORT_SPECIES_ID` (int)
- `AS_OF_TIMESTAMP` (datetime)
- `REPROCESS_IN_PROGRESS` (bit/tinyint)

#### 2. RPTFILE_INSTANCE
Links report instances to report files.

**Required Columns:**
- `DOMAIN_ID` (int)
- `REPORT_SPECIES_ID` (int)
- `AS_OF_TIMESTAMP` (datetime)
- `REPROCESS_IN_PROGRESS` (bit/tinyint)
- `RPT_FILE_ID` (int)

#### 3. RPTFILE
Contains report file metadata.

**Required Columns:**
- `RPT_FILE_ID` (int, PRIMARY KEY)
- `FILENAME` (varchar) — may contain a path prefix (e.g., `MIDASRPT\5\260271NL.RPT`); the script extracts the basename automatically

#### 4. REPORT_INSTANCE_SEGMENT (NO LONGER USED)
~~Previously used for segment information. Now known to track ingestion arrival chunks, not section segregation.~~
SEGMENTS are now extracted from RPT file SECTIONHDR via `rpt_section_reader.py`.

#### 5. SECTION (NO LONGER USED)
~~Previously used for segment name definitions.~~
Section data now comes from RPT file SECTIONHDR binary structure.

### Join Relationships

```
REPORT_INSTANCE (ri)
├─ LEFT JOIN RPTFILE_INSTANCE (rfi)
│  └─ LEFT JOIN RPTFILE (rf)
└─ SEGMENTS from RPT file SECTIONHDR (via --rptfolder, not from database)
```

---

## Input/Output Format

### Input: Report_Species.csv

**Required Columns:**
- `Report_Species_Id` (int) - Unique identifier
- `Report_Species_Name` (varchar) - Report name (used for output filename)
- `Country_Code` (varchar) - Country code
- `In_Use` (int) - Flag indicating if report is active (script updates to 0 if no instances found)

**Example:**
```csv
Report_Species_Id,Report_Species_Name,Country_Code,In_Use
1,Daily_Sales_Report,SG,1
2,Monthly_Inventory,MY,1
3,Annual_Summary,TH,1
```

### Output CSV Files

**Naming Convention:**
- With end year: `{Report_Species_Name}_{start_year}_{end_year}.csv`
- Without end year: `{Report_Species_Name}_{start_year}.csv`

**Example:** `Daily_Sales_Report_2023_2024.csv`

**Output Columns:**

| Column | Description | Example |
|--------|-------------|---------|
| REPORT_SPECIES_NAME | Report species name from input CSV | Daily_Sales_Report |
| FILENAME | Display name (basename of RPTFILE.FILENAME with path and extension stripped) | 260271NL |
| RPT_FILENAME | Original RPTFILE.FILENAME from database (may include path prefix) | MIDASRPT\5\260271NL.RPT |
| COUNTRY | Country code from input CSV | SG |
| YEAR | Calculated year (from filename or timestamp) | 2024 |
| REPORT_DATE | Date derived from julian date in filename | 2024-01-13 |
| AS_OF_TIMESTAMP | Original timestamp from database | 2024-01-30 14:23:15.000 |
| UTC | Converted UTC timestamp | 2024-01-30 06:23:15 |
| SEGMENTS | Pipe-delimited segment information from RPT SECTIONHDR | See below |
| REPORT_FILE_ID | Report file ID from RPTFILE.RPT_FILE_ID | 12345 |

**Segments Column Format (from RPT file SECTIONHDR):**

Format: `SectionID#StartPage#PageCount|SectionID#StartPage#PageCount|...`

**Example:**
```
124525#1#110|68102#111#1|14259#117#2204
```

**Segment Field Breakdown:**
- **SectionID**: Section identifier from RPT file SECTIONHDR (uint32)
- **StartPage**: Starting page number, 1-based (from SECTIONHDR)
- **PageCount**: Number of pages in this section (from SECTIONHDR)

Note: SEGMENTS will be empty if `--rptfolder` is not provided or if the RPT file is not found.

---

## RPT File SECTIONHDR Extraction

### Purpose

SEGMENTS are populated by reading the SECTIONHDR binary structure directly from RPT files.
This is the only correct source for section/page segregation data. The `REPORT_INSTANCE_SEGMENT`
database table was found to track ingestion arrival chunks, not section boundaries.

### How It Works

1. The `--rptfolder` argument specifies where RPT files are stored
2. For each report instance, the FILENAME from the database is path-stripped (`os.path.basename`) to get the RPT filename
3. The basename is used to locate the RPT file in the flat `--rptfolder` directory
4. `rpt_section_reader.py` reads the SECTIONHDR binary structure (12-byte triplets)
5. Each triplet contains: SECTION_ID (uint32), START_PAGE (uint32), PAGE_COUNT (uint32)
6. Results are cached per basename to avoid re-reading the same RPT file

### Format

```
section_id#start_page#page_count|section_id#start_page#page_count|...
```

**Example:** `124525#1#110|68102#111#1|14259#117#2204`

### When RPT File Is Not Found

If no RPT file is found for a given instance (or `--rptfolder` is not provided),
the SEGMENTS column is left empty. This is correct behavior — no data is better than wrong data.

---

## Usage Examples

### Example 1: Basic Windows Authentication

```bash
python extract_instances_sections.py \
  --server localhost \
  --database IntelliSTOR \
  --windows-auth \
  --start-year 2023
```

**Output:** Processes all reports from 2023 onwards, outputs to current directory

---

### Example 2: SQL Server Authentication with Year Range

```bash
python extract_instances_sections.py \
  --server 192.168.1.100 \
  --database IntelliSTOR \
  --user sa \
  --password MyP@ssw0rd \
  --start-year 2023 \
  --end-year 2024
```

**Output:** Processes reports from 2023 only (end year is exclusive)

---

### Example 3: Custom Timezone and RPT Folder

```bash
python extract_instances_sections.py \
  --server localhost \
  --database IntelliSTOR \
  --windows-auth \
  --start-year 2024 \
  --timezone "America/New_York" \
  --rptfolder "C:\Users\freddievr\Downloads\RPTnMAP_Files" \
  --output-dir "C:\output"
```

**Output:**
- Uses New York timezone for UTC conversion
- Reads RPT files from specified directory for SECTIONHDR extraction
- Saves results to C:\output

---

### Example 4: Year from Filename Mode

```bash
python extract_instances_sections.py \
  --server localhost \
  --database IntelliSTOR \
  --windows-auth \
  --start-year 2023 \
  --year-from-filename
```

**Behavior:**
- Filename: `24013001.rpt` → YEAR column = `2024`
- Extracts first 2 characters of the basename (path stripped) and prepends "20"
- Example: `MIDASRPT\5\24013001.RPT` → basename `24013001.RPT` → `2024`

---

### Example 5: Quiet Mode for Automation

```bash
python extract_instances_sections.py \
  --server localhost \
  --database IntelliSTOR \
  --windows-auth \
  --start-year 2023 \
  --quiet
```

**Output:**
```
Processing 150 report species | Year filter: 2023+ | Timezone: Asia/Singapore
Progress: 75/150 reports processed | 68 exported | 7 skipped
```

---

### Example 6: Custom Input CSV and Output Directory

```bash
python extract_instances_sections.py \
  --server localhost \
  --database IntelliSTOR \
  --windows-auth \
  --start-year 2023 \
  --input "C:\data\My_Reports.csv" \
  --output-dir "C:\exports\2023_data"
```

---

## Processing Workflow

### Step-by-Step Process

```
┌─────────────────────────────────────────┐
│ 1. Parse Command-Line Arguments         │
│    - Validate authentication parameters  │
│    - Validate year range                 │
│    - Validate timezone                   │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│ 2. Setup Logging                         │
│    - Create Extract_Instances.log        │
│    - Configure console output            │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│ 3. Load Report_Species.csv               │
│    - Read all report species             │
│    - Store in memory                     │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│ 4. Read Progress File                    │
│    - Check progress.txt                  │
│    - Get last processed Report_Species_Id│
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│ 5. Connect to Database                   │
│    - Establish SQL Server connection     │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│ 6. Initialize RPT Segment Cache          │
│    - Set rptfolder directory (if given)  │
│    - Prepare SECTIONHDR cache            │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│ 7. Process Each Report Species           │
│    ┌────────────────────────────────┐   │
│    │ 7a. Execute SQL Query           │   │
│    │     - Apply year filters        │   │
│    │     - Join RPTFILE tables       │   │
│    │     - Get FILENAME, RPT_FILE_ID │   │
│    └────────────┬───────────────────┘   │
│                 │                        │
│    ┌────────────▼───────────────────┐   │
│    │ 7b. Process Results             │   │
│    │     - Strip path from FILENAME  │   │
│    │     - Calculate YEAR column     │   │
│    │     - Convert timezone to UTC   │   │
│    │     - Extract SEGMENTS from RPT │   │
│    │       SECTIONHDR (or empty)     │   │
│    └────────────┬───────────────────┘   │
│                 │                        │
│    ┌────────────▼───────────────────┐   │
│    │ 7c. Write Output CSV            │   │
│    │     - Create output file        │   │
│    │     - Write header              │   │
│    │     - Write all rows            │   │
│    └────────────┬───────────────────┘   │
│                 │                        │
│    ┌────────────▼───────────────────┐   │
│    │ 7d. Update Progress             │   │
│    │     - Write current ID          │   │
│    │     - Update statistics         │   │
│    └────────────┬───────────────────┘   │
│                 │                        │
│    ┌────────────▼───────────────────┐   │
│    │ 7e. Handle Empty Results        │   │
│    │     - Update In_Use=0 in CSV    │   │
│    └────────────────────────────────┘   │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│ 8. Close Database Connection             │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│ 9. Print Summary Statistics              │
│    - Total reports processed             │
│    - Reports with instances              │
│    - Reports without instances           │
│    - Errors encountered                  │
└──────────────────────────────────────────┘
```

### Segment Processing Detail

```python
# For each report instance result:
for row in results:
    rpt_filename = row.get('FILENAME', '')  # Original from DB (may include path)
    # Strip path prefix: "MIDASRPT\5\260271NL.RPT" → "260271NL.RPT"
    rpt_basename = os.path.basename(rpt_filename.replace('\\', '/'))
    filename = rpt_basename[:-4] if rpt_basename.upper().endswith('.RPT') else rpt_basename
    # SEGMENTS always from RPT file SECTIONHDR (or empty if no --rptfolder)
    segments = get_rpt_segments(rptfolder, rpt_basename) if rptfolder else ''
    # Example result: "124525#1#110|68102#111#1|14259#117#2204"
```

The `get_rpt_segments()` function handles:
- Looking up the RPT file in the --rptfolder directory
- Reading the SECTIONHDR binary structure via `rpt_section_reader.read_sectionhdr()`
- Formatting as pipe-separated triplets via `format_segments()`
- Caching results per filename to avoid re-reading the same file

---

## Troubleshooting

### Common Issues

#### 1. Connection Errors

**Symptom:** `Failed to connect to SQL Server`

**Solutions:**
- Verify server hostname/IP is correct
- Check port number (default: 1433)
- Ensure SQL Server is running and accepting connections
- Verify firewall allows connections on SQL Server port
- For Windows Authentication, ensure account has database access

**Test Connection:**
```bash
# Using sqlcmd (SQL Server command-line tool)
sqlcmd -S localhost -d IntelliSTOR -E
```

---

#### 2. Authentication Failures

**Symptom:** `Login failed for user`

**Solutions:**
- For SQL Auth: Verify username and password
- For Windows Auth: Ensure current user has database permissions
- Check SQL Server authentication mode (mixed mode required for SQL auth)

---

#### 3. Missing Columns

**Symptom:** `Invalid column name` or query execution errors

**Solutions:**
- Verify all required tables exist in database (REPORT_INSTANCE, RPTFILE_INSTANCE, RPTFILE)
- Check column names match schema requirements
- Note: STRING_AGG is no longer used; no SQL Server 2017+ requirement

---

#### 4. RPT Files Not Found

**Symptom:** Log shows `RPT file not found: [path]`

**Behavior:**
- Script continues processing
- SEGMENTS column will be empty for that instance

**Solutions:**
- Verify --rptfolder path is correct
- Check .RPT files exist in specified directory
- Verify file permissions allow read access
- Check FILENAME values from RPTFILE table match actual filenames in the folder

**Debug:**
```bash
# List RPT files in folder
ls /path/to/rptfolder/*.RPT

# Test extraction standalone
python rpt_section_reader.py --scan /path/to/rptfolder/
```

---

#### 5. Timezone Errors

**Symptom:** `Invalid timezone: [timezone_name]`

**Solutions:**
- Use IANA timezone format (e.g., "Asia/Singapore", not "SGT")
- Verify timezone name spelling
- See full list: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones

**Test Timezone:**
```python
import pytz
print(pytz.timezone('Asia/Singapore'))  # Should not raise exception
```

---

#### 6. Progress File Issues

**Symptom:** Processing restarts from beginning despite previous progress

**Solutions:**
- Check progress.txt exists in output directory
- Verify file contains valid integer (last Report_Species_Id)
- Ensure write permissions on output directory

**Manual Reset:**
```bash
# Delete progress file to restart from beginning
del progress.txt
```

---

#### 7. Empty Segments Column

**Symptom:** Segments column is empty in output CSV

**Possible Causes:**
- `--rptfolder` was not provided (SEGMENTS will always be empty)
- RPT file not found in the specified folder
- RPT file has no SECTIONHDR structure (single-section report)

**Investigation:**
```bash
# Check if RPT file exists and has sections
python rpt_section_reader.py /path/to/rptfolder/FILENAME.RPT
```

---

#### 8. Year Filtering Not Working

**Symptom:** Too many or too few records returned

**Solutions:**
- Verify --start-year is correct (inclusive)
- Remember --end-year is EXCLUSIVE (use 2025 to include 2024)
- Check AS_OF_TIMESTAMP values in database

**Test Query:**
```sql
-- Check timestamp distribution
SELECT YEAR(AS_OF_TIMESTAMP) as Year, COUNT(*) as Count
FROM REPORT_INSTANCE
WHERE REPORT_SPECIES_ID = 1
GROUP BY YEAR(AS_OF_TIMESTAMP)
ORDER BY Year;
```

---

## Architecture

### Module Structure

```
extract_instances_sections.py
│
├─ Imports
│  ├─ pymssql (SQL Server connectivity)
│  ├─ csv (CSV file handling)
│  ├─ argparse (Command-line parsing)
│  ├─ logging (Logging framework)
│  ├─ pytz (Timezone conversion)
│  └─ rpt_section_reader (RPT file SECTIONHDR extraction)
│
├─ Configuration and Setup
│  ├─ setup_logging(output_dir, quiet)
│  └─ parse_arguments()
│
├─ Progress Tracking
│  ├─ read_progress(progress_file)
│  └─ write_progress(progress_file, report_species_id)
│
├─ Database Connection
│  └─ create_connection(server, port, database, user, password, windows_auth)
│
├─ Report Species CSV Management
│  ├─ load_report_species(csv_path)
│  └─ update_in_use(csv_path, report_species_id, new_in_use_value)
│
├─ SQL Query Execution
│  ├─ get_sql_query(start_year, end_year)
│  └─ execute_query(cursor, report_species_id, start_year, end_year)
│
├─ CSV Output
│  ├─ calculate_year(row, year_from_filename)
│  ├─ convert_to_utc(timestamp, source_timezone)
│  ├─ get_rpt_segments(rptfolder, filename)
│  └─ write_output_csv(output_path, results, report_species_name,
│                        country, year_from_filename, source_timezone, rptfolder)
│
├─ Main Processing Loop
│  └─ process_reports(conn, report_species_list, csv_path, output_dir,
│                      last_processed_id, start_year, end_year,
│                      year_from_filename, source_timezone, quiet, rptfolder)
│
└─ Main Function
   └─ main()
```

### Data Flow

```
Report_Species.csv ──┐
                     │
                     ├─→ load_report_species()
                     │
SQL Server DB ───────┼─→ create_connection()
                     │
RPT Files ───────────┼─→ rpt_section_reader (SECTIONHDR extraction)
(--rptfolder)        │
                     ├─→ process_reports()
                     │   │
                     │   ├─→ execute_query()
                     │   │   │
                     │   │   └─→ SQL Query with JOINs
                     │   │       ├─ REPORT_INSTANCE
                     │   │       ├─ RPTFILE_INSTANCE
                     │   │       └─ RPTFILE
                     │   │
                     │   ├─→ write_output_csv()
                     │   │   │
                     │   │   ├─→ calculate_year()
                     │   │   ├─→ convert_to_utc()
                     │   │   └─→ get_rpt_segments() → rpt_section_reader
                     │   │
                     │   └─→ update_in_use() [if no results]
                     │
                     └─→ Output CSV Files
                         progress.txt
                         Extract_Instances.log
```

### Key Design Patterns

#### 1. RPT Segment Caching
```python
# RPT file SECTIONHDR cached per filename to avoid re-reading
_rpt_segments_cache = {}
cache_key = rpt_filename.upper()
if cache_key in _rpt_segments_cache:
    return _rpt_segments_cache[cache_key]
```

#### 3. Progress Checkpoint Pattern
```python
# After each report, save progress
for report in reports:
    process(report)
    write_progress(report_id)  # Safe interruption point
```

#### 4. Graceful Error Handling
```python
try:
    process_report()
except Exception as e:
    log.error(f'Error: {e}')
    continue  # Process next report
```

---

## Logging

### Log Files

**Location:** `{output_dir}/Extract_Instances.log`

**Format:**
```
2024-01-30 14:23:15 - INFO - Processing Report_Species_Id: 1, Name: Daily_Sales
2024-01-30 14:23:16 - DEBUG - Executing query for Report_Species_Id: 1
2024-01-30 14:23:17 - DEBUG - Query returned 145 rows
2024-01-30 14:23:18 - INFO - Wrote 145 rows to Daily_Sales_2023.csv
```

### Log Levels

#### DEBUG
- SQL query execution details
- Row counts from queries
- RPT file SECTIONHDR extraction details
- Progress file updates

#### INFO
- Processing start/completion
- Report processing status
- File write operations
- Connection status

#### WARNING
- RPT files not found
- Progress file read/write failures
- Timestamp conversion errors
- Reports with no instances

#### ERROR
- Query execution failures
- CSV write failures
- Connection errors
- RPT file read errors

### Example Log Entries

**Normal Processing:**
```
2024-01-30 14:20:00 - INFO - Connecting to SQL Server using Windows Authentication: localhost:1433, database: IntelliSTOR
2024-01-30 14:20:01 - INFO - Database connection established successfully
2024-01-30 14:20:01 - INFO - Loaded 150 report species from Report_Species.csv
2024-01-30 14:20:01 - INFO - Resuming from Report_Species_Id: 0
2024-01-30 14:20:01 - INFO - Processing 150 report species (starting after ID 0)
2024-01-30 14:20:01 - INFO - Year filter: 2023+, YEAR column from: AS_OF_TIMESTAMP
2024-01-30 14:20:01 - INFO - Timezone: Asia/Singapore (converting to UTC)
2024-01-30 14:20:02 - INFO - Processing Report_Species_Id: 1, Name: Daily_Sales (1/150)
2024-01-30 14:20:02 - DEBUG - Executing query for Report_Species_Id: 1, years: 2023-present
2024-01-30 14:20:03 - DEBUG - Query returned 145 rows
2024-01-30 14:20:04 - DEBUG - Wrote 145 rows to Daily_Sales_2023.csv
2024-01-30 14:20:04 - INFO - Query returned 145 instances for Daily_Sales
2024-01-30 14:20:04 - INFO - Wrote 145 rows to Daily_Sales_2023.csv
```

**RPT File Lookup:**
```
2024-01-30 14:25:12 - DEBUG - RPT file not found: /path/to/rptfolder/MISSING.RPT
```

**Empty Results:**
```
2024-01-30 14:35:22 - WARNING - Query returned 0 instances for Old_Report (year range: 2023+), updating In_Use=0
2024-01-30 14:35:22 - INFO - Updated In_Use=0 for Report_Species_Id 45
```

**Error Handling:**
```
2024-01-30 14:40:10 - ERROR - Query failed for Report_Species_Id 67: Invalid column name 'FILENAME'
2024-01-30 14:40:10 - ERROR - Error processing Report_Species_Id 67: Invalid column name 'FILENAME'
```

**Final Summary:**
```
2024-01-30 15:45:30 - INFO - Database connection closed
2024-01-30 15:45:30 - INFO - ========================================
2024-01-30 15:45:30 - INFO - PROCESSING COMPLETE
2024-01-30 15:45:30 - INFO - Total reports processed: 150
2024-01-30 15:45:30 - INFO - Reports with instances: 142
2024-01-30 15:45:30 - INFO - Reports with no instances (In_Use set to 0): 7
2024-01-30 15:45:30 - INFO - Errors encountered: 1
2024-01-30 15:45:30 - INFO - ========================================
```

---

## Performance Considerations

### Optimization Tips

1. **Use --quiet Mode for Large Batches**
   - Reduces console I/O overhead
   - Better for automated scripts

2. **Place .RPT Files on Fast Storage**
   - SSD preferred for --rptfolder directory
   - Reduces disk I/O during SECTIONHDR extraction

3. **Network Latency**
   - Run script close to SQL Server (same network)
   - Consider batch size for progress checkpoints

4. **Database Indexes**
   - Ensure indexes on join columns (DOMAIN_ID, REPORT_SPECIES_ID, AS_OF_TIMESTAMP)
   - Index on REPORT_INSTANCE.AS_OF_TIMESTAMP for year filtering

### Memory Usage

- **Report_Species.csv**: Loaded entirely into memory
- **RPT SECTIONHDR**: Cached in memory per filename after first read (very small footprint)
- **Query Results**: Processed per report (not all at once)

---

## Security Considerations

### Credentials

**Best Practices:**
1. **Use Windows Authentication when possible**
   - Avoids storing passwords
   - Leverages OS security

2. **For SQL Server Authentication:**
   - Use environment variables:
     ```bash
     set DB_USER=sa
     set DB_PASSWORD=MyP@ssw0rd
     python extract_instances_sections.py --server localhost --database IntelliSTOR --user %DB_USER% --password %DB_PASSWORD% --start-year 2023
     ```
   - Use configuration files with restricted permissions
   - Never commit passwords to version control

### File Permissions

- **Output Directory**: Ensure appropriate write permissions
- **.RPT Files** (--rptfolder): Read-only access sufficient
- **Report_Species.csv**: Script requires read/write (for In_Use updates)

### SQL Injection Protection

- Script uses parameterized queries (pymssql `%s` placeholders)
- No user input concatenated into SQL strings
- Safe from SQL injection attacks

---

## Version History

### Version 3.0 (Current)
- SEGMENTS now exclusively from RPT file SECTIONHDR (via rpt_section_reader.py)
- Removed REPORT_INSTANCE_SEGMENT and SECTION table queries (tracked ingestion, not sections)
- Simplified SQL query (no STRING_AGG, no GROUP BY)
- SQL Server 2017+ no longer required
- --rptfolder provides SECTIONHDR-based SEGMENTS; without it, SEGMENTS is empty
- Added RPT_FILENAME column (original RPTFILE.FILENAME from database, may include path)
- FILENAME column now path-stripped (`os.path.basename`) — handles `MIDASRPT\5\260271NL.RPT` → `260271NL`
- `calculate_year()` now uses basename for year extraction (fixes path-prefixed filenames)

### Version 2.0
- Added .MAP file integration for segment name lookups
- Added MapFileCache class with intelligent caching
- Added --map-dir command-line argument
- Enhanced segment processing with fallback logic

### Version 1.0
- Initial release
- Basic report instance extraction
- Year filtering
- Timezone conversion
- Progress tracking
- Resume capability

---

## Appendix

### SQL Query Reference

**Complete Query (Generated by get_sql_query()):**

```sql
SELECT
    ri.REPORT_SPECIES_ID,
    rfi.RPT_FILE_ID,
    RTRIM(rf.FILENAME) AS FILENAME,
    ri.AS_OF_TIMESTAMP
FROM REPORT_INSTANCE ri
LEFT JOIN RPTFILE_INSTANCE rfi
    ON ri.DOMAIN_ID = rfi.DOMAIN_ID
    AND ri.REPORT_SPECIES_ID = rfi.REPORT_SPECIES_ID
    AND ri.AS_OF_TIMESTAMP = rfi.AS_OF_TIMESTAMP
    AND ri.REPROCESS_IN_PROGRESS = rfi.REPROCESS_IN_PROGRESS
LEFT JOIN RPTFILE rf
    ON rfi.RPT_FILE_ID = rf.RPT_FILE_ID
WHERE ri.REPORT_SPECIES_ID = %s
    AND ri.AS_OF_TIMESTAMP >= %s
    AND ri.AS_OF_TIMESTAMP < %s  -- Only if --end-year specified
ORDER BY ri.AS_OF_TIMESTAMP ASC
```

Note: SEGMENTS are no longer queried from the database. They are extracted from RPT file
SECTIONHDR binary structures via `rpt_section_reader.py` when `--rptfolder` is provided.

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success - no errors encountered |
| 1 | Failure - one or more errors occurred |
| 130 | User interrupt (Ctrl+C) |

---

## Support and Contact

For issues, questions, or contributions related to this script:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review log file (`Extract_Instances.log`) for detailed error messages
3. Verify database schema matches requirements
4. Ensure all prerequisites are installed

---

**Document Version**: 3.0
**Last Updated**: 2026-02-06
**Script Version**: 3.0 (SEGMENTS from RPT file SECTIONHDR)
