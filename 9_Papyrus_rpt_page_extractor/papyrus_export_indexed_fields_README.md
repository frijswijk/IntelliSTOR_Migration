# papyrus_export_indexed_fields

Exports indexed field definitions from an IntelliSTOR MS SQL database to a CSV file. Retrieves metadata about all fields marked as indexed (`IS_INDEXED = 1`) across all report species, including field names, types, column positions, and line templates.

## Compilation

```cmd
compile_fieldlist.bat
```

Requires: MinGW-w64 (C++17), ODBC libraries (`-lodbc32 -lodbccp32`)

## Command-Line Arguments

### Required

| Argument | Description |
|----------|-------------|
| `--server HOST` | SQL Server host/IP address |
| `--database DB` | Database name |

### Authentication (one required)

| Argument | Description |
|----------|-------------|
| `--windows-auth` | Use Windows Authentication |
| `--user USER` | SQL Server username |
| `--password PASS` | SQL Server password |

### Optional

| Argument | Default | Description |
|----------|---------|-------------|
| `--port PORT` | `1433` | SQL Server port |
| `--output-dir DIR` | `.` | Output directory |
| `--output-file FILE` | `Indexed_Fields.csv` | Output filename |
| `--quiet` | `false` | Minimal console output |

## Output File

**Location:** `{output-dir}/{output-file}` (default: `./Indexed_Fields.csv`)

| Column | Description |
|--------|-------------|
| `REPORT_SPECIES_NAME` | Primary species name (ITEM_ID=1, fallback to ITEM_ID=0) |
| `REPORT_SPECIES_DISPLAYNAME` | Display name (ITEM_ID=0) |
| `REPORT_SPECIES_ID` | Species identifier |
| `STRUCTURE_DEF_ID` | Structure definition ID |
| `LINE_ID` | Line identifier |
| `FIELD_ID` | Field identifier |
| `FIELD_NAME` | Field name (trimmed) |
| `FIELD_TYPE` | Field type name |
| `START_COLUMN` | Starting column position (1-based) |
| `END_COLUMN` | Ending column position |
| `FIELD_WIDTH` | Calculated width (`END_COLUMN - START_COLUMN + 1`) |
| `IS_SIGNIFICANT` | Whether field is significant (0 or 1) |
| `IS_INDEXED` | Always 1 (filter applied in query) |
| `LINE_NAME` | Line name from LINE table |
| `LINE_TEMPLATE` | Line template from LINE table |

## Database Tables Used

| Table | Purpose |
|-------|---------|
| `FIELD` | Field definitions (name, type, column positions, indexed flag) |
| `REPORT_INSTANCE` | Links species to structure definitions (latest instance per species) |
| `REPORT_SPECIES_NAME` | Species naming (ITEM_ID 0=display, 1=primary) |
| `LINE` | Line definitions with names and templates |

The tool validates that all four required tables exist before executing the query.

## SQL Query

Uses a windowed query (`ROW_NUMBER() OVER PARTITION BY`) to select the most recent `REPORT_INSTANCE` per species, then joins to `FIELD` where `IS_INDEXED = 1`, ordered by species name, LINE_ID, FIELD_ID.

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | Invalid or missing command-line arguments |
| `2` | Database connection failed |
| `3` | Query failed or required table missing |
| `4` | Cannot create output directory or write file |

## Example

```cmd
papyrus_export_indexed_fields.exe ^
  --server SQLSRV01 ^
  --database IntelliSTOR_SG ^
  --windows-auth ^
  --output-dir C:\Migration\FieldDefinitions
```
