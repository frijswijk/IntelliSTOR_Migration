# rpt_page_extractor

Standalone RPT file page extractor. Decompresses and extracts individual pages and binary objects (PDF/AFP) from IntelliSTOR `.RPT` report files. C++ port of the Python tools `rpt_page_extractor.py` and `rpt_section_reader.py`.

**Note:** This tool has been superseded by `papyrus_rpt_search_page_extract.exe` which adds MAP file search capability while remaining fully backward-compatible. No compile batch file is provided for this tool.

## Compilation

```cmd
g++ -std=c++17 -O2 -static -o rpt_page_extractor.exe rpt_page_extractor.cpp -lz
```

Requires: MinGW-w64 (C++17), zlib (`-lz`). No ODBC needed.

## Modes of Operation

### 1. Show RPT Info (no extraction)

```cmd
rpt_page_extractor.exe --info report.RPT
```

Displays: domain, species, timestamp, page count, section count, binary object count, compression ratios, page table sample, section table, and object header metadata.

### 2. Extract All Pages

```cmd
rpt_page_extractor.exe report.RPT
```

### 3. Extract Page Range

```cmd
rpt_page_extractor.exe --pages 10-20 report.RPT
rpt_page_extractor.exe --pages 5 report.RPT
```

### 4. Extract by Section ID

```cmd
rpt_page_extractor.exe --section-id 14259 report.RPT
rpt_page_extractor.exe --section-id 14259 14260 14261 report.RPT
```

### 5. Binary Objects Only

```cmd
rpt_page_extractor.exe --binary-only report.RPT
```

### 6. Text Pages Only (skip binary)

```cmd
rpt_page_extractor.exe --no-binary report.RPT
```

### 7. Concatenated Output

```cmd
rpt_page_extractor.exe --page-concat report.RPT
```

All text pages concatenated into a single file with form-feed (`\x0c\n`) separators.

### 8. Folder Batch Processing

```cmd
rpt_page_extractor.exe --folder /path/to/rpt/files
```

Recursively finds and processes all `.RPT` files in directory.

### 9. Export Section Table as CSV

```cmd
rpt_page_extractor.exe --info --export-sections sections.csv report.RPT
```

## Command-Line Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--info` | `false` | Show RPT file info without extracting |
| `--pages <range>` | _(all)_ | Page range `10-20` or single page `5` (1-based, inclusive) |
| `--section-id <id...>` | _(none)_ | One or more SECTION_IDs (skips missing) |
| `--folder <dir>` | _(none)_ | Process all .RPT files in directory |
| `--output <dir>` | `.` | Output base directory |
| `--binary-only` | `false` | Extract only PDF/AFP, skip text pages |
| `--no-binary` | `false` | Extract only text pages, skip PDF/AFP |
| `--page-concat` | `false` | Concatenate all text pages into single file |
| `--export-sections <file>` | _(none)_ | Export section table as CSV |

### Constraints

- `--pages` and `--section-id` cannot be used together
- `--binary-only` and `--no-binary` cannot be used together
- `--page-concat` and `--binary-only` cannot be used together

## Output Directory Structure

```
output_base/
  {rpt_name}/                              # All pages
    page_00001.txt
    page_00002.txt
    ...
    object_header.txt                      # If binary objects exist
    {rpt_name}_binary.pdf                  # Assembled binary document

  {rpt_name}/pages_10-20/                  # Page range
  {rpt_name}/section_14259/                # Single section
  {rpt_name}/sections_14259_14260/         # Multiple sections
```

### Concatenated Mode

With `--page-concat`: single file `{rpt_name}/{rpt_name}.txt`

## RPT File Binary Format

### Header (`RPTFILEHDR`)

```
Offset 0x000:  RPTFILEHDR signature (10 bytes)
Offset 0x00A:  Tab-delimited: {domain}:{species}\t{timestamp}
Offset 0x0F0:  RPTINSTHDR (base for relative offsets)
Offset 0x1D0:  Table Directory (3 rows x 12 bytes):
  Row 0: Pages    (type 0x0102) - count + offset -> PAGETBLHDR
  Row 1: Sections (type 0x0101) - count + offset -> compressed_data_end
  Row 2: Binary   (type 0x0103) - count + offset -> BPAGETBLHDR
```

### Page Table (`PAGETBLHDR`, 24 bytes per entry)

| Offset | Size | Field |
|--------|------|-------|
| 0-3 | uint32 | page_offset (relative to RPTINSTHDR) |
| 8-9 | uint16 | line_width |
| 10-11 | uint16 | lines_per_page |
| 12-15 | uint32 | uncompressed_size |
| 16-19 | uint32 | compressed_size |

### Section Table (`SECTIONHDR`, 12 bytes per entry)

| Offset | Size | Field |
|--------|------|-------|
| 0-3 | uint32 | section_id |
| 4-7 | uint32 | start_page (1-based) |
| 8-11 | uint32 | page_count |

### Binary Object Table (`BPAGETBLHDR`, 16 bytes per entry)

| Offset | Size | Field |
|--------|------|-------|
| 0-3 | uint32 | page_offset |
| 8-11 | uint32 | uncompressed_size |
| 12-15 | uint32 | compressed_size |

All page and binary data is **zlib-compressed**. Absolute offset = `page_offset + 0xF0`.

## Binary Object Detection

| Magic bytes | Type | Extension |
|-------------|------|-----------|
| `%PDF` | PDF document | `.pdf` |
| `0x5A` | AFP document | `.afp` |
| _(other)_ | Unknown binary | `.bin` |

Filename may also come from "StorQM PLUS Object Header Page" metadata in text page 1.

## Section Export CSV Format

```csv
Report_Species_Id,Section_Id,Start_Page,Pages
260271,14259,1,45
260271,14260,46,52
```

## Dependencies

- zlib (for decompression)
- No database or ODBC required
- C++17 filesystem support

## Relationship to Other Tools

This is the **predecessor** to `papyrus_rpt_search_page_extract`, which adds MAP file search capability on top of the same RPT extraction functionality. For new usage, prefer `papyrus_rpt_search_page_extract.exe`.
