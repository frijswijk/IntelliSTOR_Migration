# papyrus_rpt_search_page_extract

Combined MAP file search + RPT page extractor. Searches MAP file indexes for specific values and extracts matching pages from RPT report files. Fully backward-compatible with `rpt_page_extractor`.

## Compilation

```cmd
compile_search_extract.bat
```

Requires: MinGW-w64 (C++17), zlib (`-lz`). No ODBC needed.

## Modes of Operation

### 1. RPT Info (no extraction)

```cmd
papyrus_rpt_search_page_extract.exe --info 260271NL.RPT
```

Shows file metadata: domain, species, timestamp, page count, sections, binary objects, compression ratios.

### 2. Page Range Extraction

```cmd
papyrus_rpt_search_page_extract.exe --pages 10-20 251110OD.RPT
papyrus_rpt_search_page_extract.exe --pages 5 251110OD.RPT
```

### 3. Section Extraction

```cmd
papyrus_rpt_search_page_extract.exe --section-id 14259 251110OD.RPT
papyrus_rpt_search_page_extract.exe --section-id 14259 14260 14261 251110OD.RPT
```

### 4. MAP Search + Page Extraction

```cmd
papyrus_rpt_search_page_extract.exe --map 2511109P.MAP --line-id 8 --field-id 1 ^
    --value "200-044295-001" 251110OD.RPT
```

Searches MAP file for value, then extracts all matching pages from the RPT file.

### 5. MAP Search + Section Intersection

```cmd
papyrus_rpt_search_page_extract.exe --map 2511109P.MAP --line-id 8 --field-id 1 ^
    --value "200-044295-001" --section-id 14259 251110OD.RPT
```

Extracts only pages that match the search AND fall within the specified section(s).

### 6. MAP Search with Field Name (metadata)

```cmd
papyrus_rpt_search_page_extract.exe --map 2511109P.MAP --metadata DDU017P_metadata.json ^
    --field ACCOUNT_NO --value "200-044295-001" 251110OD.RPT
```

### 7. Folder Processing

```cmd
papyrus_rpt_search_page_extract.exe --map 2511109P.MAP --line-id 8 --field-id 1 ^
    --value "200-044295-001" --folder /path/to/rpt/files
```

Processes all `.RPT` files in directory with the same search parameters.

## Command-Line Arguments

### RPT Extraction Options

| Argument | Description |
|----------|-------------|
| `--info` | Show RPT file info without extracting |
| `--pages <range>` | Page range `10-20` or `5` (1-based, inclusive) |
| `--section-id <id...>` | One or more SECTION_IDs (skips missing) |
| `--folder <dir>` | Process all .RPT files in directory |
| `--output <dir>` | Output base directory (default: `.`) |
| `--binary-only` | Extract only PDF/AFP, skip text pages |
| `--no-binary` | Extract only text pages, skip PDF/AFP |
| `--page-concat` | Concatenate text pages into single file (form-feed separated) |
| `--export-sections <file>` | Export section table as CSV |

### MAP Search Options

| Argument | Description |
|----------|-------------|
| `--map <file>` | Path to MAP file for index search |
| `--metadata <json>` | Path to species metadata JSON |
| `--field <name>` | Field name (requires `--metadata`) |
| `--line-id <n>` | LINE_ID (raw numeric) |
| `--field-id <n>` | FIELD_ID (raw numeric) |
| `--value <text>` | Value to search for (required when `--map` is used) |
| `--prefix` | Enable prefix matching (default: exact match) |

## Output Directory Structure

```
output_base/
  {rpt_name}/
    search_{field}={value}/               # MAP search only
    search_{field}={value}_in_section_N/  # MAP search + section
    section_N/                             # Section extraction
    pages_N-M/                             # Page range
      page_00001.txt
      page_00002.txt
      ...
      object_header.txt                    # If binary objects exist
      {rpt_name}_binary.pdf               # Assembled binary document
```

### Concatenated Mode

With `--page-concat`, all text pages are written to a single `{rpt_name}.txt` file with form-feed (`\x0c\n`) separators.

## RPT File Binary Format

### Header (`RPTFILEHDR`)

```
Offset 0x000:  RPTFILEHDR signature (10 bytes)
Offset 0x00A:  Tab-delimited metadata (domain:species, timestamp)
Offset 0x0F0:  RPTINSTHDR (base offset for all relative addresses)
Offset 0x1D0:  Table Directory:
  Row 0: Pages    - type 0x0102, count, offset -> PAGETBLHDR
  Row 1: Sections - type 0x0101, count, offset -> compressed_data_end
  Row 2: Binary   - type 0x0103, count, offset -> BPAGETBLHDR
```

### Page Table (`PAGETBLHDR`, 24 bytes per entry)

| Offset | Size | Field |
|--------|------|-------|
| 0-3 | uint32 | page_offset (relative to RPTINSTHDR) |
| 8-9 | uint16 | line_width |
| 10-11 | uint16 | lines_per_page |
| 12-15 | uint32 | uncompressed_size |
| 16-19 | uint32 | compressed_size |

Absolute offset = `page_offset + 0xF0`

### Section Table (`SECTIONHDR`, 12 bytes per entry)

| Offset | Size | Field |
|--------|------|-------|
| 0-3 | uint32 | section_id |
| 4-7 | uint32 | start_page (1-based) |
| 8-11 | uint32 | page_count |

### Binary Object Table (`BPAGETBLHDR`, 16 bytes per entry)

| Offset | Size | Field |
|--------|------|-------|
| 0-3 | uint32 | page_offset (relative to RPTINSTHDR) |
| 8-11 | uint32 | uncompressed_size |
| 12-15 | uint32 | compressed_size |

All page and binary data is **zlib-compressed**.

## Binary Object Detection

| Magic bytes | Type | Extension |
|-------------|------|-----------|
| `%PDF` | PDF document | `.pdf` |
| `0x5A` | AFP document | `.afp` |
| _(other)_ | Unknown binary | `.bin` |

Object filename can also be extracted from the "StorQM PLUS Object Header Page" in text page 1.

## Section Export CSV

With `--export-sections sections.csv`:

```csv
Report_Species_Id,Section_Id,Start_Page,Pages
260271,14259,1,45
260271,14260,46,52
```

## How MAP Search + RPT Extraction Combine

1. **Search MAP file** for value using binary search on sorted entries
2. **Collect matching page numbers** (resolve u32_index via Segment 0 if needed)
3. **If section filter also provided**: intersect search results with section page ranges
4. **Extract matching pages** from RPT file (decompress zlib data)

## Dependencies

- zlib (for RPT page decompression)
- No database or ODBC required
- Reads MAP and RPT binary files directly
