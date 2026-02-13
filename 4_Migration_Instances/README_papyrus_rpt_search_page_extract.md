# papyrus_rpt_search_page_extract — Documentation

## Overview

Combined MAP file search + RPT page extractor. Searches for indexed field values in binary MAP files, then extracts the matching pages from compressed RPT files — all in a single step.

This tool answers the question: *"Show me the pages where ACCOUNT_NO = 200-044295-001, but only within the sections I'm allowed to see."*

It is **fully backward-compatible** with `rpt_page_extractor` — when no `--map` flag is provided, it behaves identically to the original page extractor.

## Available Versions

| Version | File | Requirements |
|---------|------|-------------|
| C++ (Windows) | `papyrus_rpt_search_page_extract.exe` | None (standalone) |
| C++ (macOS) | `papyrus_rpt_search_page_extract` | zlib (system) |

**No Python version** — this is a C++ only tool.

## Four Modes of Operation

| Mode | CLI Flags | Behavior |
|------|-----------|----------|
| **Normal extraction** | `--section-id 14259 FILE.RPT` | Same as `rpt_page_extractor` — extract section's pages |
| **MAP search + extract** | `--map FILE.MAP --line-id 8 --field-id 1 --value "200-044" FILE.RPT` | Search MAP, extract matching pages from RPT |
| **Search + Section** (intersection) | `--map FILE.MAP --line-id 8 --field-id 1 --value "200-044" --section-id 14259 FILE.RPT` | Search MAP, intersect with section pages, extract only overlapping pages |
| **All existing modes** | `--info`, `--pages`, `--folder`, `--page-concat`, `--binary-only`, etc. | 100% backward-compatible with `rpt_page_extractor` |

## Quick Start

### 1. Search MAP + extract matching pages

```bash
# Find which pages contain account "200-044295-001" and extract them
papyrus_rpt_search_page_extract.exe --map 2511109P.MAP \
    --line-id 8 --field-id 1 --value "200-044295-001" 251110OD.RPT
```

### 2. Search MAP + restrict to a section

```bash
# Same search, but only extract pages within section 14259
papyrus_rpt_search_page_extract.exe --map 2511109P.MAP \
    --line-id 8 --field-id 1 --value "200-044295-001" \
    --section-id 14259 251110OD.RPT
```

### 3. Prefix search + extract

```bash
# Find all pages where value starts with "200-044"
papyrus_rpt_search_page_extract.exe --map 2511109P.MAP \
    --line-id 8 --field-id 1 --value "200-044" --prefix 251110OD.RPT
```

### 4. Search using field name (requires metadata JSON)

```bash
papyrus_rpt_search_page_extract.exe --map 2511109P.MAP \
    --metadata DDU017P_metadata.json \
    --field ACCOUNT_NO --value "200-044295-001" 251110OD.RPT
```

### 5. Normal extraction (backward-compatible)

```bash
# These work exactly as rpt_page_extractor
papyrus_rpt_search_page_extract.exe --info 260271NL.RPT
papyrus_rpt_search_page_extract.exe --section-id 14259 251110OD.RPT
papyrus_rpt_search_page_extract.exe --pages 10-20 251110OD.RPT
```

## Command-Line Arguments

### RPT Extraction Options (from rpt_page_extractor)

| Argument | Description |
|----------|-------------|
| `--info` | Show RPT file info without extracting |
| `--pages <range>` | Page range "10-20" or "5" (1-based, inclusive) |
| `--section-id <id...>` | One or more SECTION_IDs (in order, skips missing) |
| `--folder <dir>` | Process all .RPT files in directory |
| `--output <dir>` | Output base directory (default: `.`) |
| `--binary-only` | Extract only the binary document (PDF/AFP), skip text pages |
| `--no-binary` | Extract only text pages, skip binary objects (PDF/AFP) |
| `--page-concat` | Concatenate all text pages into a single file (form-feed separated) |
| `--export-sections <file>` | Export section table as CSV |

### MAP Search Options (new)

| Argument | Description |
|----------|-------------|
| `--map <file>` | Path to MAP file for index search |
| `--metadata <json>` | Path to species metadata JSON (for `--field NAME` mode) |
| `--field <name>` | Field name (requires `--metadata`), e.g., `ACCOUNT_NO` |
| `--line-id <n>` | LINE_ID (raw numeric, no metadata needed) |
| `--field-id <n>` | FIELD_ID (raw numeric) |
| `--value <text>` | Value to search for (required when `--map` is used) |
| `--prefix` | Enable prefix matching (default: exact match) |

### Validation Rules

- `--map` requires `--value`
- `--map` + `--value` requires either (`--line-id` + `--field-id`) or (`--field` + `--metadata`)
- `--map` and `--pages` are mutually exclusive (MAP search determines which pages to extract)
- All existing `rpt_page_extractor` validations remain

## Output

### Search + Extract Output

When `--map` is used, the tool prints a search summary before extraction:

```
MAP Search: 25001002.MAP
  Field: LINE_ID=5, FIELD_ID=3 (width=18)
  Search value: "EP24123109039499" (exact match)
  Matches: 1, Unique pages: 1
  Search time: 0.0ms

Processing: 25001002.RPT
  Extracting 1 search-matched page(s)...
  Page 2 -> 25001002/search_5_3=EP24123109039499/page_002.txt (1,247 bytes)
```

### Output Directory Structure

| Mode | Directory Pattern |
|------|-------------------|
| Search + section | `{rpt_name}/search_{field}={value}_in_section_{sid}/` |
| Search only | `{rpt_name}/search_{field}={value}/` |
| Section only | `{rpt_name}/section_{sid}/` (unchanged) |
| Page range | `{rpt_name}/pages_{start}-{end}/` (unchanged) |
| All pages | `{rpt_name}/` (unchanged) |

### Intersection Mode Output

When both `--map` and `--section-id` are provided:

```
MAP search returned 5 pages, section allows 20 pages, intersection: 3 pages
```

Only pages that appear in BOTH the search results AND the section's page range are extracted.

## Workflow Example

### Finding the right LINE_ID and FIELD_ID

Before searching, you need to know which fields are indexed. Use `papyrus_rpt_search` or the exported `Indexed_Fields.csv`:

```bash
# Option 1: List fields in a MAP file
papyrus_rpt_search.exe --map 25001002.MAP --list-fields

# Option 2: Check the Indexed_Fields.csv export
# Look for your report species (e.g., DDU017P) to find LINE_ID and FIELD_ID
```

### Complete workflow

1. **Find indexed fields** for your report species:
   ```bash
   papyrus_rpt_search.exe --map 2511109P.MAP --list-fields
   ```
   Output shows LINE_ID=8, FIELD_ID=1 with width=14 (ACCOUNT_NO).

2. **Search and extract** matching pages:
   ```bash
   papyrus_rpt_search_page_extract.exe --map 2511109P.MAP \
       --line-id 8 --field-id 1 --value "200-044295-001" 251110OD.RPT
   ```

3. **Restrict to a section** (optional):
   ```bash
   papyrus_rpt_search_page_extract.exe --map 2511109P.MAP \
       --line-id 8 --field-id 1 --value "200-044295-001" \
       --section-id 14259 251110OD.RPT
   ```

4. **Concatenate results** into a single file:
   ```bash
   papyrus_rpt_search_page_extract.exe --map 2511109P.MAP \
       --line-id 8 --field-id 1 --value "200-044295-001" \
       --page-concat 251110OD.RPT
   ```

### Batch processing (folder mode)

Search across all RPT files in a folder:

```bash
papyrus_rpt_search_page_extract.exe --map 2511109P.MAP \
    --line-id 8 --field-id 1 --value "200-044295-001" \
    --folder C:\RPT_Files --output C:\Output
```

## Compilation

### Windows (MinGW-w64)

```
compile_search_extract.bat
```

The batch file uses: `g++ -std=c++17 -O2 -static -o papyrus_rpt_search_page_extract.exe papyrus_rpt_search_page_extract.cpp -lz`

**Requirements:**
- MinGW-w64 (g++ with C++17 support)
- zlib (static library, typically at `C:\Users\freddievr\mingw64\lib\libz.a`)
- No ODBC or database libraries needed

### macOS

```bash
clang++ -std=c++17 -O2 -o papyrus_rpt_search_page_extract papyrus_rpt_search_page_extract.cpp -lz
```

### Linux

```bash
g++ -std=c++17 -O2 -o papyrus_rpt_search_page_extract papyrus_rpt_search_page_extract.cpp -lz
```

## Error Handling

| Error | Solution |
|-------|----------|
| MAP file not found | Verify path and filename |
| `--map` without `--value` | Provide `--value` for search |
| `--map` with `--pages` | These are mutually exclusive; remove `--pages` |
| No segment found for LINE_ID/FIELD_ID | Use `papyrus_rpt_search --list-fields` to see available fields |
| No matches found | Verify search value; try `--prefix` for partial matching |
| Empty intersection | Search pages don't overlap with the section; check section ID |
| RPT file not found | Verify path and filename |
| Decompression failed | RPT file may be corrupt |

## See Also

- `papyrus_rpt_search.exe` — Standalone MAP search tool (search, list fields, list values, CSV/JSON output)
- `rpt_page_extractor.cpp` — Original RPT page extractor (this tool is a superset)
- `papyrus_export_indexed_fields.py` — Export indexed field definitions from database
- `README_papyrus_rpt_search.md` — MAP search tool documentation
- `INTELLISTOR_ARCHITECTURE_REFERENCE.md` — MAP/RPT file format details
