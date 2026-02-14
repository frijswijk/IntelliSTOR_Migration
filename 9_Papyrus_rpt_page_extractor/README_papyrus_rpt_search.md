# papyrus_rpt_search — Documentation

## Overview

Standalone MAP file index search tool. Searches for indexed field values in binary MAP files without requiring a database connection. Uses binary search (O(log n)) on sorted MAP entries for fast lookups.

This tool replaces the need for database access when searching for specific accounts, values, or identifiers within IntelliSTOR report archives.

## Available Versions

| Version | File | Requirements |
|---------|------|-------------|
| Python | `papyrus_rpt_search.py` | Python 3 + intellistor_viewer.py |
| C++ (Windows) | `papyrus_rpt_search.exe` | None (standalone) |
| macOS Launcher | `Papyrus_RPT_Search.command` | Python version |

## Features

- **Binary search** on sorted MAP entries — O(log n) vs O(n) linear scan
- **Two entry formats**: page format (small files) and u32_index format (large files with Segment 0 page resolution)
- **Multiple modes**: search, list fields, list values
- **Field name resolution** via optional metadata JSON
- **Output formats**: table (human-readable), CSV, JSON
- **Prefix matching** for partial value searches
- **No database required** — reads binary MAP files directly

## Modes of Operation

### Mode 1: Search by Raw IDs (No metadata needed)

Search using numeric LINE_ID and FIELD_ID. Use the Indexed_Fields.csv export or `--list-fields` to find the correct IDs.

```bash
# Python
python papyrus_rpt_search.py --map 25001002.MAP \
    --line-id 8 --field-id 1 --value "200-044295-001"

# C++
papyrus_rpt_search.exe --map 25001002.MAP \
    --line-id 8 --field-id 1 --value "200-044295-001"
```

### Mode 2: Search by Field Name (Requires metadata JSON)

Search using human-readable field names. Requires a metadata JSON file exported by `papyrus_export_metadata.py`.

```bash
# Python
python papyrus_rpt_search.py --map 25001002.MAP \
    --metadata DDU017P_metadata.json \
    --field ACCOUNT_NO --value "200-044295-001"

# C++
papyrus_rpt_search.exe --map 25001002.MAP \
    --metadata DDU017P_metadata.json \
    --field ACCOUNT_NO --value "200-044295-001"
```

### Mode 3: List Indexed Fields

Discover what fields are indexed in a MAP file.

```bash
# Without metadata (shows numeric IDs only)
python papyrus_rpt_search.py --map 25001002.MAP --list-fields

# With metadata (adds field names and column positions)
python papyrus_rpt_search.py --map 25001002.MAP \
    --metadata DDU017P_metadata.json --list-fields
```

**Example output:**
```
MAP File: 25001002.MAP
Date: 13/01/2025
Segment count: 3

Indexed Fields (2 segments):

  SEG  LINE_ID  FIELD_ID  NAME                  WIDTH  ENTRIES  COLUMNS
  ---  -------  --------  ----                  -----  --------  -------
    1        8         1  ACCOUNT_NO               14      1247  5-18
    2        8         2  BRANCH_CODE               3       485  2-4
```

### Mode 4: List All Values for a Field

Dump all indexed values with occurrence counts.

```bash
python papyrus_rpt_search.py --map 25001002.MAP \
    --line-id 8 --field-id 1 --list-values

# Limit to first 100 values
python papyrus_rpt_search.py --map 25001002.MAP \
    --line-id 8 --field-id 1 --list-values --max-values 100
```

### Prefix Search

Match all entries that start with a given prefix:

```bash
python papyrus_rpt_search.py --map 25001002.MAP \
    --line-id 8 --field-id 1 --value "200-044" --prefix
```

## Command-Line Arguments

### MAP File (Required)

| Argument | Description |
|----------|-------------|
| `--map FILE` | Path to the MAP file to search |

### Metadata (Optional)

| Argument | Description |
|----------|-------------|
| `--metadata JSON` | Path to species metadata JSON file (from `papyrus_export_metadata.py`) |

### Field Specification (One method required for search/list-values)

| Argument | Description |
|----------|-------------|
| `--field NAME` | Field name (requires `--metadata`). E.g., `ACCOUNT_NO` |
| `--line-id N` | LINE_ID (raw numeric). Works without metadata |
| `--field-id N` | FIELD_ID (raw numeric). Works without metadata |

### Search Options

| Argument | Description |
|----------|-------------|
| `--value TEXT` | Value to search for (required for search mode) |
| `--prefix` | Enable prefix matching (default: exact match) |

### Listing Modes

| Argument | Default | Description |
|----------|---------|-------------|
| `--list-fields` | — | List all indexed fields in the MAP file |
| `--list-values` | — | List all values for the specified field |
| `--max-values N` | 0 (all) | Maximum number of values to list |

### Output Options

| Argument | Default | Description |
|----------|---------|-------------|
| `--format FMT` | `table` | Output format: `table`, `csv`, `json` |
| `--output FILE` | stdout | Write output to file (Python only) |

## Output Formats

### Table (Default)

```
Segment 1: LINE_ID=8, FIELD_ID=1 (ACCOUNT_NO)
Field width: 14, Entry count: 1247

1 match(es) found:

  VALUE           PAGE
  --------------  --------
  200-044295-001         2

Search completed in 0.3ms
```

### CSV

```csv
value,page
200-044295-001,2
```

### JSON

```json
{
  "matches": [
    {"value": "200-044295-001", "page": 2}
  ],
  "match_count": 1,
  "field": "ACCOUNT_NO",
  "line_id": 8,
  "field_id": 1,
  "segment": 1,
  "entry_count": 1247,
  "format": "page"
}
```

## MAP File Format

MAP files contain sorted index entries for fast lookups. Key internals:

- **Segment 0**: Page lookup table (15-byte records for u32_index resolution)
- **Segments 1+**: Index entries sorted by value, one segment per indexed field
- **Entry format**: `[length:2][value:field_width][trailing:5]`
  - Small files: trailing = `[page:2][flags:3]` (page format)
  - Large files: trailing = `[u32_index:4][last:1]` (u32_index format, resolved via Segment 0)
- **Segment markers**: `**ME` (4 bytes) at the start of each segment
- **Field metadata**: At offset +24 from `**ME`: `[line_id:2][field_id:2][field_width:2]`

## Performance

Binary search provides O(log n) lookup:

| File Size | Entries | Linear Scan | Binary Search |
|-----------|---------|-------------|---------------|
| Small (200 KB) | 1,247 | ~1,247 comparisons | ~11 comparisons |
| Large (4 MB) | 14,523 | ~14,523 comparisons | ~14 comparisons |

Typical search times: **0.3ms** (small) to **5.6ms** (large) on modern hardware.

## macOS Launcher (.command)

The `Papyrus_RPT_Search.command` file provides an interactive menu-driven interface:

1. **Search mode** — Enter MAP file, LINE_ID, FIELD_ID, and search value
2. **List fields mode** — Discover indexed fields in a MAP file
3. **List values mode** — Browse all indexed values for a field

Double-click to launch from Finder, or run from Terminal:
```bash
./Papyrus_RPT_Search.command
```

The launcher reads the MAP folder path from `Migration_Environment.sh` (MapFiles_SG).

## Compilation (C++)

**Requirements:**
- MinGW-w64 (g++ with C++17 support)
- No ODBC or database libraries needed

**Compile:**
```
compile_search.bat
```

The batch file uses: `g++ -std=c++17 -O2 -static` (no `-lodbc32` — this tool reads files directly)

## Workflow Example

1. **Export indexed fields** to know which fields are available:
   ```bash
   python papyrus_export_indexed_fields.py --server localhost --database IntelliSTOR --windows-auth
   ```
   Check `Indexed_Fields.csv` to find LINE_ID=8, FIELD_ID=1 for ACCOUNT_NO in DDU017P.

2. **List fields** in a specific MAP file to verify:
   ```bash
   python papyrus_rpt_search.py --map 25001002.MAP --list-fields
   ```

3. **Search** for a specific account:
   ```bash
   python papyrus_rpt_search.py --map 25001002.MAP --line-id 8 --field-id 1 --value "200-044295-001"
   ```

4. **Prefix search** to find all accounts starting with "200-044":
   ```bash
   python papyrus_rpt_search.py --map 25001002.MAP --line-id 8 --field-id 1 --value "200-044" --prefix
   ```

## Error Handling

| Error | Solution |
|-------|----------|
| MAP file not found | Verify path and filename |
| No segment found for LINE_ID/FIELD_ID | Use `--list-fields` to see available fields |
| Field name not found in metadata | Check metadata JSON, use `--list-fields --metadata` to verify |
| No matches found | Verify search value; check field width with `--list-fields`; try `--prefix` |
| Could not build Segment 0 page lookup | MAP file may be corrupt or use unsupported format |

## See Also

- `papyrus_export_indexed_fields.py` — Export indexed field definitions (LINE_ID, FIELD_ID mappings)
- `papyrus_export_metadata.py` — Full metadata export to JSON (for `--field NAME` mode)
- `intellistor_viewer.py` — Core MAP file parser (Python version depends on this)
- `PAPYRUS_REPLACEMENT_DESIGN.md` — System design document
- `INTELLISTOR_ARCHITECTURE_REFERENCE.md` — MAP file format details
