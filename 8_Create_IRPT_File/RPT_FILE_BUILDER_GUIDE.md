# RPT File Builder Guide

## Overview

Tool for creating IntelliSTOR .RPT files from text pages and optional PDF/AFP binary documents.
This is the inverse of `rpt_page_extractor.py` -- it takes extracted content and assembles it
back into a valid `.RPT` binary file that conforms to the IntelliSTOR RPT specification.

## Requirements

- Python 3.6+
- No external dependencies (uses stdlib: `struct`, `zlib`, `argparse`, `datetime`, `dataclasses`, `re`, `glob`)
- Requires `rpt_section_reader.py` from folder `4_Migration_Instances` (resolved automatically via `sys.path`)

## Installation

Located in: `8_Create_IRPT_File/`

No installation needed -- run directly with Python 3. The script automatically adds
`../4_Migration_Instances/` to the Python path so it can find the shared `rpt_section_reader`
module.

## Quick Start

```bash
# Build a text-only RPT from extracted page files
python3 rpt_file_builder.py --species 49626 --domain 1 \
  -o output.RPT page_00001.txt page_00002.txt

# Build from a directory of previously extracted pages
python3 rpt_file_builder.py --species 49626 -o output.RPT ./extracted/260271NL/

# Build RPT with embedded PDF binary object
python3 rpt_file_builder.py --species 52759 --domain 1 \
  --binary document.PDF -o output.RPT ./extracted/report/

# Roundtrip: rebuild from extracted content using original as template
python3 rpt_file_builder.py --template original.RPT \
  --species 49626 -o rebuilt.RPT ./extracted/original/
```
## CLI Reference

```
usage: rpt_file_builder.py [-h] -o OUTPUT [--species SPECIES]
                           [--domain DOMAIN] [--timestamp TIMESTAMP]
                           [--binary BINARY] [--object-header OBJECT_HEADER]
                           [--section SEC_SPEC] [--line-width LINE_WIDTH]
                           [--lines-per-page LINES_PER_PAGE]
                           [--template TEMPLATE] [--info] [--verbose]
                           input_files [input_files ...]

Create IntelliSTOR .RPT files from text pages and optional PDF/AFP.

positional arguments:
  input_files           Text files (.txt) or a directory containing
                        page_NNNNN.txt files

options:
  -h, --help            show this help message and exit
  -o, --output OUTPUT   Output .RPT file path
  --species SPECIES     Report species ID (default: 0)
  --domain DOMAIN       Domain ID (default: 1)
  --timestamp TIMESTAMP
                        Report timestamp (default: current time). Format:
                        "YYYY/MM/DD HH:MM:SS.mmm"
  --binary BINARY       Path to PDF or AFP file to embed as binary object
  --object-header OBJECT_HEADER
                        Path to text file for Object Header page (page 1)
  --section SEC_SPEC    Section spec: "SECTION_ID:START_PAGE:PAGE_COUNT" (can
                        repeat)
  --line-width LINE_WIDTH
                        Override line width for all pages
  --lines-per-page LINES_PER_PAGE
                        Override lines per page for all pages
  --template TEMPLATE   Reference .RPT file to copy RPTINSTHDR metadata from
  --info                Dry run: show what would be built without writing
  --verbose, -v         Show detailed build progress

Examples:
  # Build text-only RPT from page files
  python3 rpt_file_builder.py --species 49626 --domain 1 \
    -o output.RPT page_00001.txt page_00002.txt

  # Build from a directory of extracted pages
  python3 rpt_file_builder.py --species 49626 -o output.RPT ./extracted/260271NL/

  # Build RPT with embedded PDF
  python3 rpt_file_builder.py --species 52759 --domain 1 \
    --binary HKCIF001_016_20280309.PDF \
    -o output.RPT object_header.txt page_00002.txt

  # Build with template (roundtrip)
  python3 rpt_file_builder.py --template original.RPT \
    --species 49626 -o rebuilt.RPT ./extracted/original/

  # Build RPT with multiple sections
  python3 rpt_file_builder.py --species 12345 \
    --section 14259:1:10 --section 14260:11:5 \
    -o output.RPT page_*.txt
```

### Options Summary

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `input_files` | positional | (required) | Text files or a directory of `page_NNNNN.txt` files |
| `-o, --output` | string | (required) | Output .RPT file path |
| `--species` | int | 0 | Report species ID |
| `--domain` | int | 1 | Domain ID (zero-padded to 4 digits in the header) |
| `--timestamp` | string | current time | Report timestamp in `YYYY/MM/DD HH:MM:SS.mmm` format |
| `--binary` | path | none | PDF or AFP file to embed as binary object |
| `--object-header` | path | none | Custom Object Header text file (page 1) |
| `--section` | string | auto | Section spec `SECTION_ID:START_PAGE:PAGE_COUNT` (repeatable) |
| `--line-width` | int | auto | Override line width for all pages |
| `--lines-per-page` | int | auto | Override lines per page for all pages |
| `--template` | path | none | Reference .RPT file to copy RPTINSTHDR metadata from |
| `--info` | flag | off | Dry run: show build plan without writing |
| `--verbose, -v` | flag | off | Show detailed build progress |
## Usage Examples

### Example 1: Build text-only RPT from extracted pages

Given a directory of page files extracted by `rpt_page_extractor.py`:

```bash
python3 rpt_file_builder.py --species 49626 --domain 1 \
  -o report.RPT ./extracted/260271NL/
```

The builder scans the directory for `page_*.txt` files, sorts them by name, and
assembles them into a single RPT file with species ID 49626 and domain 1.

### Example 2: Build RPT from individual text files

```bash
python3 rpt_file_builder.py --species 49626 --domain 1 \
  -o output.RPT page_00001.txt page_00002.txt page_00003.txt
```

Each `.txt` file becomes one page in the RPT file, in the order specified.

### Example 3: Build RPT with embedded PDF

```bash
python3 rpt_file_builder.py --species 52759 --domain 1 \
  --binary HKCIF001_016_20280309.PDF \
  -o output.RPT ./extracted/report/
```

The PDF is split into chunks matching the number of text pages and interleaved
with the compressed text page streams. An Object Header page is auto-generated
from the PDF metadata and inserted as page 1.

### Example 4: Build RPT using a template

```bash
python3 rpt_file_builder.py --template original.RPT \
  --species 49626 -o rebuilt.RPT ./extracted/original/
```

The `--template` flag copies the 224-byte RPTINSTHDR metadata block from the
original RPT file, then patches the species ID and timestamp fields. This
preserves internal metadata fields that were set by the original IntelliSTOR
system.

### Example 5: Build RPT with multiple sections

```bash
python3 rpt_file_builder.py --species 12345 \
  --section 14259:1:10 --section 14260:11:5 \
  -o output.RPT page_*.txt
```

Each `--section` flag defines a section with format `SECTION_ID:START_PAGE:PAGE_COUNT`.
If no `--section` flags are given, a single default section (ID=0) covering all pages
is created automatically.

### Example 6: Roundtrip verification

Full extract, rebuild, and re-extract workflow:

```bash
# 1. Extract pages from the original RPT
python3 "../4_Migration_Instances/rpt_page_extractor.py" \
  --output ./extracted /path/to/original.RPT

# 2. Rebuild using template metadata
python3 rpt_file_builder.py --template /path/to/original.RPT \
  --species 49626 --domain 1 \
  -o rebuilt.RPT ./extracted/original/

# 3. Re-extract the rebuilt RPT and verify
python3 "../4_Migration_Instances/rpt_page_extractor.py" --info rebuilt.RPT
```

The rebuilt file should show the same species, domain, page count, and section
structure as the original. Text page content is byte-identical after roundtrip.

### Example 7: Dry run (preview)

```bash
python3 rpt_file_builder.py --species 49626 --domain 1 \
  --info ./extracted/260271NL/ -o output.RPT
```

The `--info` flag shows the build plan without writing any file:

```
Build plan:
  Species: 49626, Domain: 1
  Timestamp: 2026/02/06 15:30:42.301
  Text pages: 2
  Sections: 1
    0: pages 1-2
  Template: no
  Output: output.RPT
```
## Input Formats

### Text Page Files

- **Directory mode**: Pass a single directory containing `page_NNNNN.txt` files
  (as produced by `rpt_page_extractor.py`). Files are sorted by name and loaded in order.
- **File mode**: Pass individual `.txt` files as positional arguments. Each file becomes
  one page in the output RPT, in the order specified on the command line.
- Text content should be ASCII. Non-ASCII characters are replaced with `?`.

### Binary Files (PDF/AFP)

- Optional: pass with `--binary` flag to embed a PDF or AFP document.
- When using directory mode, if no `--binary` flag is given, the builder auto-detects
  `*.pdf`, `*.PDF`, `*.afp`, or `*.AFP` files in the directory.
- The binary file is split into N chunks (where N = number of text pages) and each
  chunk is zlib-compressed and interleaved with the text page streams.

### Object Header

- Auto-generated when `--binary` is provided, extracting metadata from the binary file:
  filename, modification timestamp, and (for PDFs) Title, Subject, Author, Creator,
  Producer, CreationDate, LastModifiedDate, Keywords.
- Alternatively, provide a custom Object Header text file with `--object-header`.
- When using directory mode, if `object_header.txt` exists in the directory and a binary
  file is present, it is used automatically.

### Template RPT Files

- Optional: use with `--template` to copy the 224-byte RPTINSTHDR metadata block and
  the 48-byte Table Directory type fields from an existing RPT file.
- The template's species ID and timestamps are overwritten with the values from the
  command-line arguments.
- Useful for roundtrip workflows where you want to preserve metadata fields that
  the builder cannot generate from scratch.

## Output Format

The builder produces a binary `.RPT` file with this exact layout:

| Offset | Size | Structure | Description |
|--------|------|-----------|-------------|
| `0x000` | 240 bytes | RPTFILEHDR | Header line + sub-header + zero-padding |
| `0x0F0` | 224 bytes | RPTINSTHDR | Instance metadata + zero-padding |
| `0x1D0` | 48 bytes | Table Directory | 3 rows x 16 bytes (offsets to trailer structures) |
| `0x200` | varies | COMPRESSED DATA | Per-page zlib streams, interleaved with binary chunks |
| varies | varies | SECTIONHDR | Section marker + section triplets + ENDDATA |
| varies | varies | PAGETBLHDR | Page table marker + 24-byte page entries + ENDDATA |
| varies | varies | BPAGETBLHDR | Binary page table + 16-byte entries + ENDDATA (optional) |

All offsets stored in the Table Directory, PAGETBLHDR, and BPAGETBLHDR are relative
to the RPTINSTHDR block at absolute position `0xF0`.

The builder also runs automatic verification after writing, using `parse_rpt_header()`
and `read_sectionhdr()` to confirm the output is a valid RPT file.
## Error Handling

| Scenario | Behavior |
|----------|----------|
| No text pages provided | `ERROR: At least 1 text page required` -- exits with code 1 |
| Input file not found | `ERROR: Input file not found: <path>` -- exits with code 1 |
| Binary file not found | `ERROR: Binary file not found: <path>` -- exits with code 1 |
| Object header file not found | `ERROR: Object header file not found: <path>` -- exits with code 1 |
| Template file not found | `ERROR: Template file not found: <path>` -- exits with code 1 |
| Invalid section spec format | `ERROR: Invalid section spec: <spec>` -- exits with code 1 |
| Non-ASCII text content | Characters replaced with `?` (no error, silent replacement) |
| No `page_*.txt` in directory | `ERROR: No page_*.txt files found in <dir>` -- exits with code 1 |
| Verification fails after build | `VERIFY FAIL` warning printed to stderr |

## RPT Binary Format Reference

For the full binary format specification including byte-level field layouts for
RPTFILEHDR, RPTINSTHDR, Table Directory, SECTIONHDR, PAGETBLHDR, and BPAGETBLHDR,
see `RPT_FILE_BUILDER_PLAN.md` in this same directory.

Key points:
- All multi-byte integers are little-endian (`<` in struct format)
- Text pages are compressed with `zlib.compress()`
- Binary objects (PDF/AFP) are split into N chunks and interleaved 1:1 with text pages
- Page offsets in the page table are relative to RPTINSTHDR at `0xF0`
- The ENDDATA marker (`ENDDATA\x00\x00`) terminates each trailer block

## Roundtrip Workflow

The primary quality test for the builder is roundtrip fidelity with `rpt_page_extractor.py`:

```bash
# Step 1: Extract all content from the original RPT
cd "/path/to/8_Create_IRPT_File"
python3 "../4_Migration_Instances/rpt_page_extractor.py" \
  --output ./roundtrip_test /path/to/original.RPT

# Step 2: Rebuild using the extracted content
python3 rpt_file_builder.py \
  --template /path/to/original.RPT \
  --species 49626 --domain 1 \
  -o ./roundtrip_test/rebuilt.RPT \
  ./roundtrip_test/original/

# Step 3: Re-extract the rebuilt RPT
python3 "../4_Migration_Instances/rpt_page_extractor.py" \
  --output ./roundtrip_test/re-extracted \
  ./roundtrip_test/rebuilt.RPT

# Step 4: Compare extracted content (should be byte-identical)
diff ./roundtrip_test/original/page_00001.txt \
     ./roundtrip_test/re-extracted/rebuilt/page_00001.txt

# Step 5: For binary RPTs, compare the extracted PDF/AFP too
diff ./roundtrip_test/original/document.PDF \
     ./roundtrip_test/re-extracted/rebuilt/document.PDF

# Step 6: Clean up
rm -rf ./roundtrip_test
```

**Expected results**: Text pages and binary documents must be byte-identical after
roundtrip. The RPT file itself may differ in size (different zlib compression levels)
and timestamp, but the extracted content must match exactly.
