# papyrus_extract_instances

Extracts report instances from an IntelliSTOR MS SQL database and generates per-species CSV files with instance details including RPT segments, MAP file status, and indexed field information.

## Compilation

```cmd
compile.bat
```

Requires: MinGW-w64 (C++17), ODBC libraries (`-lodbc32 -lodbccp32`)

## Command-Line Arguments

### Required

| Argument | Description |
|----------|-------------|
| `--server SERVER` | MS SQL Server hostname |
| `--database DATABASE` | Database name |
| `--start-year YEAR` | Start year for filtering (e.g., 2023) |

### Authentication (one required)

| Argument | Description |
|----------|-------------|
| `--windows-auth` | Use Windows Authentication (default) |
| `--user USERNAME` | SQL Server username |
| `--password PASSWORD` | SQL Server password |

### Optional

| Argument | Default | Description |
|----------|---------|-------------|
| `--input CSV` | `Report_Species.csv` | Input Report_Species.csv file |
| `--output-dir DIR` | `.` | Output directory for instance CSVs |
| `--end-year YEAR` | _(none)_ | End year for date filtering |
| `--year-from-filename` | `false` | Extract YEAR from filename instead of AS_OF_TIMESTAMP |
| `--timezone TZ` | `Asia/Singapore` | Timezone for UTC conversion |
| `--rptfolder DIR` | _(none)_ | Directory with RPT files for SEGMENTS extraction |
| `--mapfolder DIR` | _(none)_ | Directory with MAP files for MAP_FILE_EXISTS check |
| `--quiet` | `false` | Minimal console output |

### Supported Timezones

`UTC`, `Asia/Singapore`, `Asia/Hong_Kong`, `America/New_York`, `Europe/London`, `Asia/Tokyo`, `Australia/Sydney`

## Output Files

### Per-Species Instance CSVs

**Location:** `{output-dir}/{SpeciesName}_{start_year}[_{end_year}].csv`

| Column | Description |
|--------|-------------|
| `REPORT_SPECIES_NAME` | Report species name |
| `FILENAME` | RPT basename without path and `.RPT` extension (display only) |
| `RPT_FILENAME` | RPT filename with extension |
| `MAP_FILENAME` | Associated MAP filename from database |
| `MAP_FILE_EXISTS` | `Y` or `N` (checked on disk via `--mapfolder`) |
| `COUNTRY` | Country code |
| `YEAR` | From filename or timestamp |
| `REPORT_DATE` | Julian date converted to `YYYY-MM-DD` |
| `AS_OF_TIMESTAMP` | Original timestamp from database |
| `UTC` | Timestamp converted to UTC |
| `SEGMENTS` | RPT sections: `section_id#start_page#page_count\|...` |
| `REPORT_FILE_ID` | RPT_FILE_ID from database |
| `INDEXED_FIELDS` | Indexed fields: `NAME#LINE_ID#FIELD_ID\|...` |

### Species Summary CSV

**Location:** Parent directory of `{output-dir}/species_summary_{start_year}[_{end_year}].csv`

| Column | Description |
|--------|-------------|
| `REPORT_SPECIES_ID` | Species ID |
| `REPORT_SPECIES_NAME` | Species name |
| `INSTANCE_COUNT` | Number of instances extracted |
| `RPT_FILES_FOUND` | Unique RPT files found on disk |
| `MAX_SECTIONS` | Maximum section count across RPT files |
| `MAP_FILES_FOUND` | Unique MAP files found on disk |
| `INDEX_FIELD_NAMES` | Indexed fields: `NAME#LINE_ID#FIELD_ID\|...` |

### Progress File

**Location:** `{output-dir}/progress.txt`

Contains the last processed REPORT_SPECIES_ID for resume capability.

## Key Features

- **Progress Tracking / Resume** - Reads `progress.txt` on startup, skips already-processed species. Safe to interrupt and restart.
- **RPT Segment Extraction** - Reads SECTIONHDR from binary RPT files (two-strategy scan: targeted near offset hint, then full file fallback). Results cached in memory.
- **MAP File Existence Check** - Validates MAP files exist on disk via `--mapfolder`. Populates `MAP_FILE_EXISTS` column.
- **Indexed Fields** - Queries FIELD table for `IS_INDEXED=1` fields, formatted as `NAME#LINE_ID#FIELD_ID` separated by `|`.
- **Julian Date Conversion** - Extracts `YYnnn` from RPT filename, converts to `YYYY-MM-DD`.
- **Timezone Conversion** - Converts `AS_OF_TIMESTAMP` to UTC using static timezone offsets (not DST-aware).
- **IN_USE Update** - Sets `IN_USE=0` in input CSV for species with zero instances.
- **Filename Sanitization** - Illegal characters `\/:*?"<>|` replaced with `_` in output filenames.

## Database Tables Used

| Table | Purpose |
|-------|---------|
| `REPORT_INSTANCE` | Main instances with timestamps and structure definitions |
| `RPTFILE_INSTANCE` | Links instances to RPT files |
| `RPTFILE` | RPT file metadata (FILENAME) |
| `SST_STORAGE` | Storage info linking to MAP files |
| `MAPFILE` | MAP file metadata (FILENAME) |
| `FIELD` | Indexed field definitions (NAME, LINE_ID, FIELD_ID) |

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Invalid command-line arguments |
| `2` | Database connection failed |
| `3` | Input file error (cannot open Report_Species.csv) |
| `4` | Extraction failed |

## Example

```cmd
papyrus_extract_instances.exe ^
  --server SQLSRV01 ^
  --database IntelliSTOR_SG ^
  --windows-auth ^
  --start-year 2023 --end-year 2025 ^
  --output-dir C:\Migration\Instances_SG ^
  --rptfolder D:\RPT_Archive ^
  --mapfolder D:\MAP_Archive ^
  --timezone "Asia/Singapore" ^
  --quiet
```
