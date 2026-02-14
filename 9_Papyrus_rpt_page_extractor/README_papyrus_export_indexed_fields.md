# papyrus_export_indexed_fields — Documentation

## Overview

Exports all indexed field definitions from the IntelliSTOR MS SQL database to a CSV file. For each report species that has indexed fields, this tool retrieves the field definitions including LINE_ID, FIELD_ID, field name, data type, column positions, and the corresponding line template.

This is a standalone tool designed to run at customer sites to capture field metadata before the MS SQL database is decommissioned.

## Available Versions

| Version | File | Requirements |
|---------|------|-------------|
| Python | `papyrus_export_indexed_fields.py` | Python 3 + pymssql |
| C++ (Windows) | `papyrus_export_indexed_fields.exe` | None (standalone) |

## Output

**File:** `Indexed_Fields.csv` (configurable via `--output-file`)

**Columns:**

| Column | Type | Description |
|--------|------|-------------|
| REPORT_SPECIES_NAME | text | Report species code (e.g., DDU017P, BC2060P) |
| REPORT_SPECIES_DISPLAYNAME | text | Display name from ITEM_ID=0 (may include description) |
| REPORT_SPECIES_ID | int | Internal species ID |
| STRUCTURE_DEF_ID | int | Structure definition ID (scopes field definitions) |
| LINE_ID | int | Line identifier within the structure |
| FIELD_ID | int | Field identifier within the line |
| FIELD_NAME | text | Human-readable field name (e.g., ACCOUNT_NO) |
| FIELD_TYPE | text | Data type: Text, DigitCode, Decimal, Mask, Date, Integer, etc. |
| START_COLUMN | int | Starting column position in the report line |
| END_COLUMN | int | Ending column position in the report line |
| FIELD_WIDTH | int | Calculated field width (END_COLUMN - START_COLUMN + 1) |
| IS_SIGNIFICANT | int | Whether the field is significant (0 or 1) |
| IS_INDEXED | int | Whether the field is indexed (always 1 in this output) |
| LINE_NAME | text | Name of the line definition |
| LINE_TEMPLATE | text | Pattern template for line matching (A=alpha, 9=digit) |

## Usage

### Python Version

**Requirements:**
```bash
pip install pymssql
```

**SQL Server Authentication:**
```bash
python papyrus_export_indexed_fields.py \
    --server localhost \
    --database IntelliSTOR \
    --user sa \
    --password MyPassword
```

**Windows Authentication:**
```bash
python papyrus_export_indexed_fields.py \
    --server localhost \
    --database IntelliSTOR \
    --windows-auth
```

**Custom output directory:**
```bash
python papyrus_export_indexed_fields.py \
    --server localhost \
    --database IntelliSTOR \
    --user sa \
    --password MyPassword \
    --output-dir C:\Output
```

**Custom output filename:**
```bash
python papyrus_export_indexed_fields.py \
    --server localhost \
    --database IntelliSTOR \
    --windows-auth \
    --output-file SG_Indexed_Fields.csv
```

**Quiet mode:**
```bash
python papyrus_export_indexed_fields.py \
    --server SQLSERVER01 \
    --database IntelliSTOR \
    --windows-auth \
    --quiet
```

### C++ Version (Windows)

**Compile first:**
```
compile_fieldlist.bat
```

**Run:**
```
papyrus_export_indexed_fields.exe --server localhost --database IntelliSTOR --windows-auth
papyrus_export_indexed_fields.exe --server localhost --database IntelliSTOR --user sa --password MyPassword
papyrus_export_indexed_fields.exe --server localhost --database IntelliSTOR --user sa --password MyPassword --output-dir C:\Output
```

## Command-Line Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `--server` | Yes | — | SQL Server host/IP address |
| `--database` | Yes | — | Database name |
| `--port` | No | 1433 | SQL Server port |
| `--user` | No* | — | Username for SQL Server authentication |
| `--password` | No* | — | Password for SQL Server authentication |
| `--windows-auth` | No* | False | Use Windows Authentication |
| `--output-dir`, `-o` | No | `.` | Output directory |
| `--output-file` | No | `Indexed_Fields.csv` | Output filename |
| `--quiet` | No | False | Minimal console output |

*Either `--windows-auth` OR both `--user` and `--password` must be provided.

## Database Tables Used

| Table | Purpose |
|-------|---------|
| FIELD | Field definitions (LINE_ID, FIELD_ID, NAME, type, columns, IS_INDEXED) |
| REPORT_INSTANCE | Maps REPORT_SPECIES_ID to STRUCTURE_DEF_ID |
| REPORT_SPECIES_NAME | Species names (ITEM_ID=0: display name, ITEM_ID=1: code name) |
| LINE | Line definitions and templates |

## REPORT_SPECIES_NAME Convention

The REPORT_SPECIES_NAME table uses a multi-record convention:
- **ITEM_ID = 0**: Always present. Contains the display name (may include description, e.g., "BC2108P:Address Advices")
- **ITEM_ID = 1**: Present for ~60% of species. Contains just the code name (e.g., "BC2108P")

The tool uses `COALESCE(ITEM_ID_1, ITEM_ID_0)` to get the clean species name code.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Invalid arguments |
| 2 | Database connection failed |
| 3 | Query or table error |
| 4 | Output file error |

## Logging

- **Python**: Log file written to `{output-dir}/papyrus_export_indexed_fields.log`
- **C++**: Errors printed to stderr

## Compilation (C++)

**Requirements:**
- MinGW-w64 (g++ with C++17 support)
- ODBC libraries (included in Windows)

**Compile:**
```
compile_fieldlist.bat
```

The batch file uses: `g++ -std=c++17 -O2 -static -lodbc32 -lodbccp32`

## Sample Output

```csv
REPORT_SPECIES_NAME,REPORT_SPECIES_DISPLAYNAME,REPORT_SPECIES_ID,STRUCTURE_DEF_ID,LINE_ID,FIELD_ID,FIELD_NAME,FIELD_TYPE,START_COLUMN,END_COLUMN,FIELD_WIDTH,IS_SIGNIFICANT,IS_INDEXED,LINE_NAME,LINE_TEMPLATE
DDU017P,DDU017P:Daily Deposit Update,1346,42,8,1,ACCOUNT_NO,Text,5,18,14,1,1,Detail Line,A 999-999999-999 AAAA*
DDU017P,DDU017P:Daily Deposit Update,1346,42,8,2,BRANCH_CODE,DigitCode,2,4,3,0,1,Detail Line,A 999-999999-999 AAAA*
```

## See Also

- `papyrus_rpt_search.py` / `papyrus_rpt_search.exe` — Search MAP file indexes using these field IDs
- `papyrus_export_metadata.py` — Full metadata export to JSON (for standalone operation after DB decommission)
- `PAPYRUS_REPLACEMENT_DESIGN.md` — System design document
