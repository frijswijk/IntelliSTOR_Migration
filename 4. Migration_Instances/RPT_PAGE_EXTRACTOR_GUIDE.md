# RPT Page Extractor - User Guide

## Overview

The RPT Page Extractor decompresses and extracts pages from IntelliSTOR `.RPT` binary files. It uses the PAGETBLHDR for fast random-access decompression of individual zlib page streams, saving each page as a `.txt` file. It also extracts embedded binary objects (PDF/AFP documents) tracked by the BPAGETBLHDR structure.

Available in three implementations (identical CLI interface):

| Implementation | File | Dependencies |
|---------------|------|-------------|
| **Python** (primary) | `rpt_page_extractor.py` | Python 3.6+, `rpt_section_reader.py` |
| **JavaScript** | `rpt_page_extractor.js` | Node.js 14+ (no external deps) |
| **C++** | `rpt_page_extractor.cpp` | C++17 compiler, zlib |

All three versions produce identical output and support the same command-line options.

---

## Features

- **File info** - Display RPT file metadata, section table, page table, and binary object table without extracting
- **Full extraction** - Decompress all pages from one or more RPT files
- **Page range** - Extract a specific page range (e.g., pages 10-20)
- **Section-based** - Extract pages belonging to one or more SECTION_IDs
- **Multi-section** - Provide multiple SECTION_IDs; pages are collected in the order given, missing IDs are silently skipped
- **Batch/folder mode** - Process all `.RPT` files in a directory recursively
- **Binary objects** - Extract embedded PDF/AFP documents from RPT files (BPAGETBLHDR)
- **Binary-only mode** - Extract only the binary document, skip text pages
- **No-binary mode** - Extract only text pages, skip binary objects

---

## Installation & Compilation

### Python (primary)

No compilation needed. Requires Python 3.6+.

```bash
# Verify Python is available
python3 --version

# No external dependencies required (uses only stdlib)
```

**Note:** The Python version imports from `rpt_section_reader.py` (must be in the same directory).

### JavaScript (Node.js)

No compilation needed. Requires Node.js 14+. Zero external dependencies.

```bash
# Verify Node.js is available
node --version

# Make executable (Linux/macOS)
chmod +x rpt_page_extractor.js
```

The JavaScript version is fully self-contained (SECTIONHDR and PAGETBLHDR parsing are built-in).

### C++ (compiled)

Requires a C++17 compiler and zlib development headers.

**macOS:**
```bash
# zlib is included with Xcode Command Line Tools
xcode-select --install   # if not already installed

# Compile
clang++ -std=c++17 -O2 -o rpt_page_extractor rpt_page_extractor.cpp -lz
```

**Linux (Debian/Ubuntu):**
```bash
# Install zlib development headers
sudo apt-get install zlib1g-dev

# Compile
g++ -std=c++17 -O2 -o rpt_page_extractor rpt_page_extractor.cpp -lz
```

**Linux (RHEL/CentOS):**
```bash
# Install zlib development headers
sudo yum install zlib-devel

# Compile
g++ -std=c++17 -O2 -o rpt_page_extractor rpt_page_extractor.cpp -lz
```

**Windows (MSYS2/MinGW):**
```bash
# Install zlib
pacman -S mingw-w64-x86_64-zlib

# Compile
g++ -std=c++17 -O2 -o rpt_page_extractor.exe rpt_page_extractor.cpp -lz
```

**Windows (Visual Studio):**
```
1. Install vcpkg and run: vcpkg install zlib:x64-windows
2. Open Developer Command Prompt
3. cl /std:c++17 /O2 /EHsc rpt_page_extractor.cpp /link zlib.lib
```

The C++ version is fully self-contained (single file, no header dependencies beyond stdlib + zlib).

---

## Command Line Usage

All three versions share the same CLI interface. Replace the command prefix as needed:

| Version | Command prefix |
|---------|---------------|
| Python | `python3 rpt_page_extractor.py` |
| JavaScript | `node rpt_page_extractor.js` |
| C++ | `./rpt_page_extractor` |

### Help

```bash
python3 rpt_page_extractor.py --help
```

### Options

| Option | Description |
|--------|-------------|
| `--info` | Show RPT file info (sections, page table, binary objects) without extracting |
| `--pages RANGE` | Page range to extract, e.g. `10-20` or `5` (1-based, inclusive) |
| `--section-id ID [ID ...]` | Extract pages for one or more SECTION_IDs (in order, skips missing) |
| `--folder DIR` | Process all `.RPT` files in the given directory recursively |
| `--output DIR` / `-o DIR` | Output base directory (default: current directory) |
| `--binary-only` | Extract only the binary document (PDF/AFP), skip text pages |
| `--no-binary` | Extract only text pages, skip binary objects (PDF/AFP) |

**Constraints:**
- `--pages` and `--section-id` are mutually exclusive
- `--binary-only` and `--no-binary` are mutually exclusive

---

## Examples

### 1. Show RPT file info (no extraction)

```bash
python3 rpt_page_extractor.py --info 260271NL.RPT
```

**Output:**
```
======================================================================
File: 260271NL.RPT
  Species: 1346, Domain: 1
  Timestamp: 2026-01-15 10:30:00
  Pages: 150, Sections: 5
  Compressed: 245,328 bytes -> Uncompressed: 1,024,000 bytes (4.2x)

  Sections (5):
    SECTION_ID  START_PAGE  PAGE_COUNT
  ------------  ----------  ----------
         14259           1          30
         14260          31          25
         14261          56          40
         14262          96          20
         14263         116          35

  Page Table (first 5 / last 5):
    PAGE      OFFSET   WIDTH   LINES    UNCOMP      COMP
       1  0x00000200     132      66     8,712     1,634
       2  0x00000858     132      66     8,712     1,589
       ...
     150  0x0003B9A0     132      66     8,712     1,601
```

### 2. Extract all pages

```bash
python3 rpt_page_extractor.py --output ./extracted 260271NL.RPT
```

Output directory: `./extracted/260271NL/`

### 3. Extract a page range

```bash
python3 rpt_page_extractor.py --pages 10-20 --output ./extracted 260271NL.RPT
```

Output directory: `./extracted/260271NL/pages_10-20/`

### 4. Extract pages for a single section

```bash
python3 rpt_page_extractor.py --section-id 14259 --output ./extracted 260271NL.RPT
```

Output directory: `./extracted/260271NL/section_14259/`

### 5. Extract pages for multiple sections

```bash
python3 rpt_page_extractor.py --section-id 14259 14261 14263 --output ./extracted 260271NL.RPT
```

**Behavior:**
- Pages are collected in the order of IDs provided (14259 first, then 14261, then 14263)
- If an ID does not exist in the RPT file, it is silently skipped
- Output directory: `./extracted/260271NL/sections_14259_14261_14263/`

**Output:**
```
======================================================================
File: 260271NL.RPT
  Species: 1346, Domain: 1
  ...
  Sections (5):
    SECTION_ID  START_PAGE  PAGE_COUNT
  ------------  ----------  ----------
         14259           1          30 <--
         14260          31          25
         14261          56          40 <--
         14262          96          20
         14263         116          35 <--

  Extracting section 14259: pages 1-30 (30 pages)
  Extracting section 14261: pages 56-95 (40 pages)
  Extracting section 14263: pages 116-150 (35 pages)

  Total: 3 section(s), 105 pages
  Saved 105 pages to ./extracted/260271NL/sections_14259_14261_14263/
  Total decompressed: 914,760 bytes
```

### 6. Multi-section with missing IDs (graceful skip)

```bash
python3 rpt_page_extractor.py --section-id 14259 99999 14261 --output ./extracted 260271NL.RPT
```

**Output:**
```
  Skipped (not found): 99999

  Extracting section 14259: pages 1-30 (30 pages)
  Extracting section 14261: pages 56-95 (40 pages)

  Total: 2 section(s), 70 pages
```

If **none** of the requested IDs are found, an error is reported with the list of available section IDs.

### 7. Batch processing (folder mode)

```bash
python3 rpt_page_extractor.py --folder /path/to/rpt/files --output ./extracted
```

Processes all `.RPT` files recursively, shows per-file results and a summary:
```
SUMMARY: 12 files, 1,847 pages extracted, 15,234,560 bytes decompressed, 0 errors
```

### 8. Show info for RPT file with binary objects (PDF/AFP)

```bash
python3 rpt_page_extractor.py --info 260271Q7.RPT
```

**Output:**
```
======================================================================
File: 260271Q7.RPT
  Species: 52759, Domain: 1
  Timestamp: 2028/03/09 09:15:22.120
  Pages: 2, Sections: 1
  Binary Objects: 2
  Compressed: 514 bytes -> Uncompressed: 980 bytes (1.9x)

  Sections (1):
    SECTION_ID  START_PAGE  PAGE_COUNT
  ------------  ----------  ----------
             0           1           2

  Page Table (first 5 / last 5):
    PAGE      OFFSET   WIDTH   LINES    UNCOMP      COMP
       1  0x00000200      11      89       359       262
       2  0x00004E41      20     123       621       252

  Binary Objects (2):  [BPAGETBLHDR]
    INDEX      OFFSET  UNCOMP_SIZE   COMP_SIZE
  -------  ----------  -----------  ----------
        1  0x00000306       19,462      19,259
        2  0x00004F3D       19,463      18,386

  Object Header:
    Object File Name: HKCIF001_016_20280309.PDF
    Object File Timestamp: 20260127090844
    PDF Creator: JasperReports Library version 7.0.1
    PDF Producer: OpenPDF 1.3.32

  Assembled document: PDF (38,925 bytes)
  Output filename: HKCIF001_016_20280309.PDF
```

### 9. Extract all (text + binary) from RPT with embedded PDF

```bash
python3 rpt_page_extractor.py --output ./extracted 260271Q7.RPT
```

**Output:**
```
  Extracting all 2 pages
  Object Header page (page 1) separated from text output
  Saved 1 text pages to ./extracted/260271Q7/
  Total decompressed: 621 bytes
  Saved object_header.txt to ./extracted/260271Q7/
  Saved PDF document: HKCIF001_016_20280309.PDF (38,925 bytes) to ./extracted/260271Q7/
```

**Output files:**
```
./extracted/260271Q7/
  object_header.txt              # Object Header metadata (page 1)
  page_00002.txt                 # Report text page
  HKCIF001_016_20280309.PDF      # Assembled PDF document
```

### 10. Extract only the binary document (PDF/AFP)

```bash
python3 rpt_page_extractor.py --binary-only --output ./extracted 260271Q7.RPT
```

Produces only the assembled binary document (no text pages, no object_header.txt).

### 11. Extract only text pages (skip binary objects)

```bash
python3 rpt_page_extractor.py --no-binary --output ./extracted 260271Q7.RPT
```

Produces text pages and object_header.txt, but no binary document.

### 12. Equivalent commands across implementations

```bash
# Python
python3 rpt_page_extractor.py --section-id 14259 14260 --output ./out file.RPT

# JavaScript (identical CLI)
node rpt_page_extractor.js --section-id 14259 14260 --output ./out file.RPT

# C++ (identical CLI)
./rpt_page_extractor --section-id 14259 14260 --output ./out file.RPT
```

---

## Interactive Menu (Launcher Scripts)

Cross-platform launcher scripts provide an interactive menu for users who prefer not to type CLI commands.

| Script | Platform |
|--------|----------|
| `RPT_Page_Extractor.bat` | Windows |
| `RPT_Page_Extractor.sh` | Linux |
| `RPT_Page_Extractor.command` | macOS (double-click in Finder) |

### Menu Options

```
============================================================
  RPT Page Extractor - IntelliSTOR RPT File Tool
============================================================

Options:
  1. Show RPT file info (sections, page table, compression)
  2. Extract all pages from an RPT file
  3. Extract page range from an RPT file
  4. Extract pages for one or more sections (by SECTION_ID)
  5. Extract all RPT files in a folder
  6. Show help
  7. Extract binary objects (PDF/AFP) from an RPT file
  0. Exit
```

**Option 4 (multi-section):** The script first shows the available sections in the file, then prompts for one or more space-separated SECTION_IDs. Missing IDs are skipped automatically.

**Option 7 (binary objects):** Extracts embedded PDF or AFP documents from RPT files that contain binary objects. Uses `--binary-only` mode — only the assembled binary document is saved.

---

## Output Structure

### Text-only RPT files

Extracted pages are saved as text files with zero-padded page numbers:

```
<output_dir>/
  <RPT_NAME>/
    page_00001.txt
    page_00002.txt
    ...
```

When extracting by section or page range, a subdirectory is created:

```
# Single section
<output_dir>/<RPT_NAME>/section_14259/page_00001.txt ...

# Multiple sections
<output_dir>/<RPT_NAME>/sections_14259_14261_14263/page_00001.txt ...

# Page range
<output_dir>/<RPT_NAME>/pages_10-20/page_00010.txt ...
```

### RPT files with binary objects (PDF/AFP)

When an RPT file contains embedded binary objects (BPAGETBLHDR), the default extraction produces both text pages and the assembled binary document:

```
<output_dir>/
  <RPT_NAME>/
    object_header.txt              # Object Header page (metadata about the binary object)
    page_00002.txt                 # Report text page(s) — page 1 (Object Header) is separated
    HKCIF001_016_20280309.PDF      # Assembled binary document (filename from Object Header)
```

- **Object Header** (text page 1) is treated as metadata, not a regular text page. It is saved as `object_header.txt` for reference.
- **Binary document** filename comes from the Object Header's "Object File Name" field. Fallback: `<RPT_NAME>_binary.<ext>`.
- **`--binary-only`** produces only the binary document (no text files).
- **`--no-binary`** produces only text pages + object_header.txt (no binary document).

---

## RPT File Binary Format (Reference)

```
Offset    Structure          Description
-------   -----------------  ------------------------------------------
0x000     RPTFILEHDR         "RPTFILEHDR\t{domain}:{species}\t{timestamp}"
0x0F0     RPTINSTHDR         Instance metadata (base for page offsets)
0x1D0     Table Directory    3 rows x 12 bytes:
  Row 0 (0x1D0):
    0x1D0   type             uint32 LE - 0x0102 (PAGETBLHDR)
    0x1D4   page_count       uint32 LE - number of text pages
    0x1D8   page_tbl_offset  uint32 LE - offset to PAGETBLHDR marker
  Row 1 (0x1E0):
    0x1E0   type             uint32 LE - 0x0101 (SECTIONHDR)
    0x1E4   section_count    uint32 LE - number of sections
    0x1E8   comp_data_end    uint32 LE - end of compressed data area
  Row 2 (0x1F0):
    0x1F0   type             uint32 LE - 0x0103 (BPAGETBLHDR)
    0x1F4   binary_count     uint32 LE - number of binary objects (0 = text-only)
    0x1F8   binary_tbl_off   uint32 LE - offset to BPAGETBLHDR marker
0x200     COMPRESSED DATA    Per-page zlib streams + interleaved binary objects
...       SECTIONHDR         Marker + 12-byte triplets per section
...       PAGETBLHDR         Marker + 24-byte entries per page
...       BPAGETBLHDR        Marker + 16-byte entries per binary object (if present)
```

### PAGETBLHDR Entry (24 bytes, little-endian)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 4 | page_offset | Byte offset relative to RPTINSTHDR (add 0xF0) |
| 4 | 4 | (reserved) | Always 0 |
| 8 | 2 | line_width | Max characters per line |
| 10 | 2 | lines_per_page | Number of lines on this page |
| 12 | 4 | uncompressed_size | Decompressed data size (bytes) |
| 16 | 4 | compressed_size | zlib stream size (bytes) |
| 20 | 4 | (reserved) | Always 0 |

### SECTIONHDR Triplet (12 bytes, little-endian)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 4 | section_id | SECTION_ID from database |
| 4 | 4 | start_page | First page of this section (1-based) |
| 8 | 4 | page_count | Number of pages in this section |

### BPAGETBLHDR Entry (16 bytes, little-endian)

| Offset | Size | Field | Description |
|--------|------|-------|-------------|
| 0 | 4 | page_offset | Byte offset relative to RPTINSTHDR (add 0xF0) |
| 4 | 4 | (reserved) | Always 0 |
| 8 | 4 | uncompressed_size | Decompressed data size (bytes) |
| 12 | 4 | compressed_size | zlib stream size (bytes) |

### Binary Object Format Detection (magic bytes)

| Format | Magic Bytes | Extension | Description |
|--------|-------------|-----------|-------------|
| PDF | `%PDF` (0x25 0x50 0x44 0x46) | `.pdf` | Portable Document Format |
| AFP | `0x5A` (Begin Structured Field) | `.afp` | Advanced Function Presentation |
| Unknown | — | `.bin` | Fallback (or uses Object Header filename) |

### Object Header Page

When binary objects are present, text page 1 is typically a "StorQM PLUS Object Header Page" containing metadata about the embedded binary document:

```
StorQM PLUS Object Header Page:
Object File Name: HKCIF001_016_20280309.PDF
Object File Timestamp: 20260127090844
PDF Creator: JasperReports Library version 7.0.1
PDF Producer: OpenPDF 1.3.32
PDF CreationDate: D:20260126174224+08'00'
```

This page is NOT a regular report page — the extractor separates it as `object_header.txt`.

### Interleaved Data Layout (Binary RPT files)

In RPT files with binary objects, the compressed data area contains text pages and binary objects interleaved:

```
0x200     Text page 1 zlib stream    (Object Header)
          Binary object 1 zlib stream (PDF/AFP part 1)
          Text page 2 zlib stream    (Report page)
          Binary object 2 zlib stream (PDF/AFP part 2)
          ...
```

All binary object chunks concatenate in order to form a single complete document (e.g., a multi-page PDF).

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Invalid RPT file (no RPTFILEHDR) | Error reported, file skipped in batch mode |
| No PAGETBLHDR found | Error reported |
| Page decompression failure | Warning per page, continues with remaining pages |
| Section ID not found | Silently skipped, reported in "Skipped" line |
| All section IDs not found | Error with list of available section IDs |
| `--pages` and `--section-id` combined | Rejected with error message |
| `--binary-only` and `--no-binary` combined | Rejected with error message |
| `--binary-only` on text-only RPT | Error: no binary objects found |
| Binary object decompression failure | Warning per object, continues with remaining |
| No BPAGETBLHDR in file | Binary objects silently skipped (text-only RPT) |
| No Object Header detected | Binary objects still extracted; fallback filename used |

---

## File Dependencies

```
rpt_page_extractor.py  ──imports──▶  rpt_section_reader.py
                                     (parse_rpt_header, read_sectionhdr,
                                      SectionEntry, RptHeader)

rpt_page_extractor.js  (self-contained, no imports)
rpt_page_extractor.cpp (self-contained, links to -lz)
```

---

## Troubleshooting

**Python: `ModuleNotFoundError: No module named 'rpt_section_reader'`**
Ensure `rpt_section_reader.py` is in the same directory as `rpt_page_extractor.py`.

**Node.js: `Error: Cannot find module ...`**
Run directly: `node rpt_page_extractor.js` (not `require()` from another script).

**C++: `zlib.h: No such file or directory`**
Install zlib development headers for your platform (see Compilation section above).

**C++: `undefined reference to 'uncompress'`**
Ensure `-lz` is at the end of the compile command: `g++ ... rpt_page_extractor.cpp -lz`

**All: `WARNING: Page N decompression failed`**
The zlib stream for that page may be corrupt. Remaining pages are still extracted.

**All: `ERROR: None of the requested section IDs found`**
Use `--info` first to see available SECTION_IDs in the file.

**All: `ERROR: No binary objects found in this RPT file`**
The `--binary-only` flag was used but the RPT file has no BPAGETBLHDR (it is text-only). Use `--info` to check if the file contains binary objects (look for "Binary Objects:" in the output).

**All: Output PDF/AFP file is corrupted**
The binary objects may have been partially decompressed. Check for `WARNING: Binary object N decompression failed` messages. The assembled document requires all parts to be valid.
