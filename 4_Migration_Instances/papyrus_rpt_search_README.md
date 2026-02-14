# papyrus_rpt_search

Standalone MAP file index search tool. Searches for indexed field values in binary MAP files without requiring a database connection. Implements binary search on sorted MAP entries.

## Compilation

```cmd
compile_search.bat
```

Requires: MinGW-w64 (C++17). No ODBC needed - reads binary files directly.

## Modes of Operation

### 1. Search by Raw IDs

```cmd
papyrus_rpt_search.exe --map 25001002.MAP --line-id 5 --field-id 3 --value "200-044295-001"
```

### 2. Search by Field Name (requires metadata JSON)

```cmd
papyrus_rpt_search.exe --map 25001002.MAP --metadata DDU017P_metadata.json --field ACCOUNT_NO --value "200-044295-001"
```

### 3. List All Indexed Fields

```cmd
papyrus_rpt_search.exe --map 25001002.MAP --list-fields
papyrus_rpt_search.exe --map 25001002.MAP --list-fields --metadata DDU017P_metadata.json
```

### 4. List All Values for a Field

```cmd
papyrus_rpt_search.exe --map 25001002.MAP --line-id 5 --field-id 3 --list-values
papyrus_rpt_search.exe --map 25001002.MAP --line-id 5 --field-id 3 --list-values --max-values 100
```

### 5. Prefix Search

```cmd
papyrus_rpt_search.exe --map 25001002.MAP --line-id 5 --field-id 3 --value "200-044" --prefix
```

## Command-Line Arguments

| Argument | Description |
|----------|-------------|
| `--map FILE` | Path to MAP file (required) |
| `--metadata JSON` | Path to species metadata JSON file (optional) |
| `--field NAME` | Field name (requires `--metadata`) |
| `--line-id N` | LINE_ID (raw numeric) |
| `--field-id N` | FIELD_ID (raw numeric) |
| `--value TEXT` | Value to search for |
| `--prefix` | Enable prefix matching (default: exact match) |
| `--list-fields` | List all indexed fields in the MAP file |
| `--list-values` | List all values for the specified field |
| `--max-values N` | Max values to list (default: 0 = all) |
| `--format FMT` | Output format: `table` (default), `csv`, `json` |

## Output Formats

### Table (default)

```
Segment 2: LINE_ID=5, FIELD_ID=3 (ACCOUNT_NO)
Field width: 20, Entry count: 50000

3 match(es) found:

  VALUE                  PAGE
  -----                  ----
  200-044295-001         1234
  200-044295-001         5678
```

### CSV

```
value,page
200-044295-001,1234
200-044295-001,5678
```

### JSON

```json
{
  "matches": [
    {"value": "200-044295-001", "page": 1234}
  ],
  "match_count": 1,
  "field": "ACCOUNT_NO",
  "line_id": 5,
  "field_id": 3,
  "segment": 2,
  "entry_count": 50000,
  "format": "page"
}
```

## MAP File Binary Format

MAP files use **UTF-16LE** encoding throughout.

### File Structure

```
[File Header]
  Offset 18:      segment_count (uint16)
  Offset 0x20:    date_string (10 chars UTF-16LE)

[Segment 0 - Lookup Table]
  Marker: **ME (0x2A 0x00 0x2A 0x00 0x4D 0x00 0x45 0x00)
  Record size: 15 bytes
  Used for u32_index -> page resolution

[Segment 1+ - Index Data]
  Marker: **ME
  Metadata at offset +24 from marker:
    +2:  line_id      (uint16)
    +6:  field_id     (uint16)
    +10: field_width  (uint16)
    +14: entry_count  (uint16)
```

### Index Entry Format

Each entry is `7 + field_width` bytes:

```
[0-1]   length       (uint16, equals field_width)
[2..2+field_width]   value (space-padded ASCII)
[trailing]           page_number (uint16) OR u32_index (uint32)
```

### Two Index Formats

- **Page format**: Entries contain direct 2-byte page numbers
- **u32_index format**: Entries contain 4-byte u32_index values that must be resolved via Segment 0's lookup table

Detection is automatic based on sampling entry trailing bytes.

## Metadata JSON Format

```json
{
  "name": "DDU017P",
  "indexed_fields": [
    {
      "name": "ACCOUNT_NO",
      "line_id": 5,
      "field_id": 3,
      "start_column": 10,
      "end_column": 25
    }
  ]
}
```

Enables `--field ACCOUNT_NO` instead of `--line-id 5 --field-id 3`.

## Search Algorithm

1. Locate segment for requested (line_id, field_id)
2. Binary search (`O(log n)`) on sorted entries to find first match
3. Linear scan forward to collect all matching entries
4. Resolve u32_index values to page numbers via Segment 0 lookup (if applicable)

## Dependencies

- No database or ODBC required
- No external libraries (reads binary MAP files directly)
- C++17 standard library only
