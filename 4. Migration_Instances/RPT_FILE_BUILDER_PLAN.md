# Plan: RPT File Builder (`rpt_file_builder.py`)

## Purpose

A Python program that **creates** new IntelliSTOR `.RPT` files from input text pages and optional binary documents (PDF/AFP). This is the inverse of `rpt_page_extractor.py` — it takes extracted content and assembles it back into a valid `.RPT` binary file that conforms to the IntelliSTOR RPT specification as reverse-engineered from production files.

## Use Cases

1. **Roundtrip testing** — Extract pages from an RPT file, modify them, re-pack into a new RPT file
2. **Report generation** — Create RPT files from text content (e.g., migrated reports, test data)
3. **PDF/AFP embedding** — Bundle a PDF or AFP document with its corresponding text pages into a single RPT file
4. **Section assembly** — Combine multiple text page sets with different SECTION_IDs into one RPT file
5. **Migration tooling** — Create RPT files for import into IntelliSTOR or replacement systems

---

## RPT Binary Format Specification (Builder Reference)

The builder must produce files that match this exact binary layout:

```
Offset    Size    Structure           Notes
------    ----    -----------------   ------------------------------------------
0x000     0x0F0   RPTFILEHDR Block    240 bytes (header line + zero-padding)
0x0F0     0x0E0   RPTINSTHDR Block    224 bytes (metadata + zero-padding)
0x1D0     0x030   Table Directory     3 rows x 16 bytes (12 used + 4 padding)
0x200     varies  COMPRESSED DATA     Per-page zlib streams + interleaved binary
...       varies  SECTIONHDR          Marker + 13-byte skip + section triplets
...       varies  PAGETBLHDR          Marker + 13-byte skip + 24-byte entries
...       varies  BPAGETBLHDR         Marker + 13-byte skip + 16-byte entries (optional)
```

### Block 1: RPTFILEHDR (0x000–0x0EF, 240 bytes)

```
"RPTFILEHDR\t{domain}:{species}\t{timestamp}\x1A" + zero-padding to 0x0F0
```

- **domain**: Zero-padded 4-digit string (e.g., `0001`)
- **species**: Integer species ID (e.g., `52759`)
- **timestamp**: Format `YYYY/MM/DD HH:MM:SS.mmm`
- Terminated by `0x1A`, then zero-padded to fill 240 bytes

Internal sub-structure at offsets (relative to 0x000):
```
0x0C0: [4 bytes] 0xE0, 0x00, 0x05, 0x01   — Fixed sub-header prefix
0x0C4: [4 bytes] 0x01, 0x00, 0x00, 0x00   — Constant (1)
0x0C8: [4 bytes] 0xE0, 0x00, 0x00, 0x00   — Pointer to 0xE0
0x0CC: [4 bytes] 0x00, 0x00, 0x00, 0x00   — Reserved
0x0D0: [4 bytes] 0x00, 0x00, 0x00, 0x00   — Reserved
0x0D4: [6 bytes] "ENDHDR\x00\x00"          — End-of-header marker
0x0DC: [4 bytes] 0x00, 0x00, 0x00, 0x00   — Padding
0x0E0: [4 bytes] 0xF0, 0x00, 0x00, 0x00   — Pointer to RPTINSTHDR
0x0E4: [4 bytes] 0x00, 0x00, 0x00, 0x00   — Reserved
0x0E8: [4 bytes] compressed_data_end LE    — Points to end of compressed data
0x0EC: [4 bytes] 0x00, 0x00, 0x00, 0x00   — Reserved
```

### Block 2: RPTINSTHDR (0x0F0–0x1CF, 224 bytes)

```
"RPTINSTHDR\x00\x00" + metadata fields + zero-padding to 0x1D0
```

Key offsets (relative to 0x0F0):
```
0x00: "RPTINSTHDR\x00\x00"                 — 12 bytes: marker
0x0C: [4 bytes] 0xE0, 0x00, 0x00, 0x00     — Pointer back to RPTFILEHDR sub-header
0x10: [4 bytes] 0x01, 0x00, 0x00, 0x00     — Instance number (always 1)
0x14: [4 bytes] species_id LE               — Report species ID
0x18: [8 bytes] Report timestamp (BCD)      — YYYY MM DD HH MM SS (packed)
0x20: [2 bytes] ??                          — Unknown
0x22: [8 bytes] Creation timestamp (BCD)    — YYYY MM DD HH MM SS (packed)
0x2A: [4 bytes] 0x00, 0x00, 0x00, 0x00     — Reserved
0x2E: [5 bytes] Date/version field          — Observed as 0x07, 0xEA, ...
0x33: [8 bytes] Modification timestamp      — YYYY MM DD HH MM SS (packed)
0x3B: [5 bytes] 0x00 ...                    — Reserved
0x40: [4 bytes] 0x01, 0x01, 0x00, 0x00     — Fixed constants
...
0xA0: [4 bytes] report_format_info          — (0x0409 observed = 1033)
0xB0: [4 bytes] page_dimensions_info        — Line width, page lines hints
0xC0: [varies]  Additional metadata         — Zero-filled in most cases
0xD0: "ENDHDR\x00\x00" + padding            — End-of-header + zero-fill to 0x1D0
```

**Builder strategy**: Copy a template RPTINSTHDR from a reference RPT file, then patch the species ID, timestamps, and dimension fields. Fields we don't understand can be copied verbatim from a template or zero-filled.

### Block 3: Table Directory (0x1D0–0x1FF, 48 bytes)

Three rows of 16 bytes each (12 bytes used + 4 bytes zero padding):

```
Row 0 (0x1D0): PAGETBLHDR reference
  0x1D0: type          uint32 LE — 0x00010102 (observed: 02 01 00 00)
  0x1D4: page_count    uint32 LE — Number of text pages
  0x1D8: pagetbl_off   uint32 LE — Absolute offset to PAGETBLHDR marker
  0x1DC: [4 bytes]     zero padding

Row 1 (0x1E0): SECTIONHDR reference
  0x1E0: type          uint32 LE — 0x00010101 (observed: 01 01 00 00)
  0x1E4: section_count uint32 LE — Number of sections
  0x1E8: comp_data_end uint32 LE — Offset to end of compressed data area
  0x1EC: [4 bytes]     zero padding

Row 2 (0x1F0): BPAGETBLHDR reference
  0x1F0: type          uint32 LE — 0x00010103 (observed: 03 01 00 00)
  0x1F4: binary_count  uint32 LE — Number of binary objects (0 = text-only)
  0x1F8: bpagetbl_off  uint32 LE — Absolute offset to BPAGETBLHDR marker (0 if none)
  0x1FC: [4 bytes]     zero padding
```

**Note**: For text-only RPT files, Row 2 is all zeros. For binary RPT files, the type field at 0x1F0 is `0x00010103`.

### Block 4: Compressed Data Area (0x200–...)

Each text page is stored as:
```
[zlib_compressed_page_content]   — zlib.compress(page_text.encode('ascii'))
```

For files with binary objects, text pages and binary objects are **interleaved**:
```
text_page_1_zlib  →  binary_obj_1_zlib  →  text_page_2_zlib  →  binary_obj_2_zlib  →  ...
```

For text-only files, pages are stored sequentially:
```
text_page_1_zlib  →  text_page_2_zlib  →  text_page_3_zlib  →  ...
```

### Block 5: SECTIONHDR (after compressed data)

```
"SECTIONHDR\x00\x00\x00"   — 13 bytes: marker (10) + 2 null + 1 null
[section_triplet × N]       — N = section_count
"ENDDATA\x00\x00\x00\x00\x00\x00" — 13 bytes: end marker
```

Each section triplet is 12 bytes:
```
  [section_id:4]    uint32 LE — SECTION_ID from database
  [start_page:4]    uint32 LE — First page of this section (1-based)
  [page_count:4]    uint32 LE — Number of pages in this section
```

### Block 6: PAGETBLHDR (after SECTIONHDR)

```
"PAGETBLHDR\x00\x00\x00"   — 13 bytes: marker (10) + 2 null + 1 null
[page_entry × N]            — N = page_count
"ENDDATA\x00\x00\x00\x00\x00\x00" — 13 bytes: end marker
```

Each page entry is 24 bytes:
```
  [page_offset:4]         uint32 LE — Byte offset relative to RPTINSTHDR (subtract 0xF0 from absolute)
  [reserved:4]            uint32 LE — Always 0
  [line_width:2]          uint16 LE — Max characters per line on this page
  [lines_per_page:2]      uint16 LE — Number of lines on this page
  [uncompressed_size:4]   uint32 LE — Decompressed page data size in bytes
  [compressed_size:4]     uint32 LE — zlib stream size in bytes
  [reserved:4]            uint32 LE — Always 0
```

### Block 7: BPAGETBLHDR (after PAGETBLHDR, optional)

Only present when `binary_count > 0`:

```
"BPAGETBLHDR\x00\x00"      — 13 bytes: marker (11) + 2 null
[binary_entry × N]          — N = binary_count
"ENDDATA\x00\x00\x00\x00\x00\x00" — 13 bytes: end marker
```

Each binary entry is 16 bytes:
```
  [page_offset:4]         uint32 LE — Byte offset relative to RPTINSTHDR (subtract 0xF0 from absolute)
  [reserved:4]            uint32 LE — Always 0
  [uncompressed_size:4]   uint32 LE — Decompressed data size in bytes
  [compressed_size:4]     uint32 LE — zlib stream size in bytes
```

---

## CLI Interface

```
rpt_file_builder.py - Create IntelliSTOR .RPT files from text pages and optional PDF/AFP

Usage:
  python3 rpt_file_builder.py [options] -o OUTPUT.RPT INPUT_FILES...

Arguments:
  INPUT_FILES               Text files (.txt) to include as pages, in order.
                            Each .txt file becomes one page.
                            Alternatively, a directory containing page_NNNNN.txt files.

Options:
  -o, --output FILE         Output .RPT file path (required)
  --species ID              Report species ID (default: 0)
  --domain ID               Domain ID (default: 1, formatted as 4-digit zero-padded)
  --timestamp TS            Report timestamp (default: current time)
                            Format: "YYYY/MM/DD HH:MM:SS.mmm"

  --binary FILE             Path to PDF or AFP file to embed as binary object.
                            The file will be split into chunks matching the text page count,
                            and interleaved with text page zlib streams.

  --object-header FILE      Path to a text file to use as Object Header page (page 1).
                            If --binary is given and this is not, a default Object Header
                            is generated from the binary file metadata.

  --section SEC_SPEC        Section specification. Can be repeated for multiple sections.
                            Format: "SECTION_ID:START_PAGE:PAGE_COUNT"
                            Example: --section 14259:1:10 --section 14260:11:5
                            If not specified, a single section with ID=0 covering all pages
                            is created.

  --line-width N            Default line width for pages (default: auto-detected per page)
  --lines-per-page N        Default lines per page (default: auto-detected per page)

  --template FILE           Path to a reference .RPT file to use as template for
                            RPTINSTHDR metadata. If not given, a generic template is used.

  --info                    Show what would be built without writing (dry run)
  --verbose                 Show detailed build progress
  --help                    Show this help message

Examples:
  # Build text-only RPT from page files
  python3 rpt_file_builder.py --species 49626 --domain 1 \
    -o output.RPT page_00001.txt page_00002.txt page_00003.txt

  # Build from a directory of extracted pages
  python3 rpt_file_builder.py --species 49626 -o output.RPT ./extracted/260271NL/

  # Build RPT with embedded PDF
  python3 rpt_file_builder.py --species 52759 --domain 1 \
    --binary HKCIF001_016_20280309.PDF \
    -o output.RPT object_header.txt page_00002.txt

  # Build RPT with multiple sections
  python3 rpt_file_builder.py --species 12345 \
    --section 14259:1:10 --section 14260:11:5 \
    -o output.RPT page_*.txt

  # Build from previously extracted content (roundtrip)
  python3 rpt_file_builder.py --template original.RPT \
    -o rebuilt.RPT ./extracted/original/
```

---

## Implementation Plan

### File Structure

```
rpt_file_builder.py       — Main builder program (single file, depends on rpt_section_reader.py)
```

### Step 1: Input Collection and Validation

```python
def collect_inputs(args) -> BuildSpec:
    """
    Collect and validate all input files, returning a BuildSpec object.

    - If INPUT_FILES is a directory: scan for page_NNNNN.txt, object_header.txt, *.pdf, *.afp
    - If INPUT_FILES are individual files: collect them in order
    - Validate: at least 1 text page required
    - If --binary given: validate file exists and is PDF or AFP
    - If directory contains a PDF/AFP and no --binary flag: auto-detect and include it
    """
```

**BuildSpec dataclass:**
```python
@dataclass
class BuildSpec:
    species_id: int
    domain_id: int
    timestamp: str                    # "YYYY/MM/DD HH:MM:SS.mmm"
    text_pages: List[bytes]           # Raw text content per page (ASCII bytes)
    sections: List[SectionDef]        # (section_id, start_page, page_count)
    binary_file: Optional[str]        # Path to PDF/AFP file to embed
    object_header_page: Optional[bytes]  # Object Header text content
    template_rptinsthdr: Optional[bytes] # 224-byte RPTINSTHDR from template
    line_width_override: Optional[int]
    lines_per_page_override: Optional[int]
```

### Step 2: Page Analysis

```python
def analyze_pages(text_pages: List[bytes]) -> List[PageInfo]:
    """
    Analyze each text page to determine:
    - line_width: max(len(line) for line in page_text.splitlines())
    - lines_per_page: len(page_text.splitlines())
    - uncompressed_size: len(page_text)
    """
```

### Step 3: Binary Object Chunking

When a PDF/AFP file is embedded, it must be split into N chunks where N = number of text pages (observed pattern: binary objects interleave 1:1 with text pages).

```python
def chunk_binary_file(binary_path: str, num_text_pages: int) -> List[bytes]:
    """
    Split a binary file into N roughly-equal chunks.

    Strategy (matching observed production behavior):
    - Read the entire binary file
    - Split into num_text_pages chunks of approximately equal size
    - Last chunk gets any remaining bytes

    The chunks concatenate to form the original file.
    """
```

### Step 4: Compression

```python
def compress_pages(text_pages: List[bytes]) -> List[Tuple[bytes, int, int]]:
    """
    Compress each text page using zlib.compress().
    Returns: [(compressed_bytes, uncompressed_size, compressed_size), ...]
    """

def compress_binary_chunks(chunks: List[bytes]) -> List[Tuple[bytes, int, int]]:
    """
    Compress each binary chunk using zlib.compress().
    Returns: [(compressed_bytes, uncompressed_size, compressed_size), ...]
    """
```

### Step 5: Object Header Generation

```python
def generate_object_header(binary_path: str) -> bytes:
    """
    Generate an Object Header page for an embedded binary file.

    Output format:
        StorQM PLUS Object Header Page:
        Object File Name: HKCIF001_016_20280309.PDF
        Object File Timestamp: 20260127090844
        ...

    Metadata is extracted from:
    - Filename → Object File Name
    - File modification time → Object File Timestamp
    - For PDFs: parse /Creator and /Producer from PDF header
    """
```

### Step 6: RPTFILEHDR Construction

```python
def build_rptfilehdr(domain_id: int, species_id: int, timestamp: str,
                      compressed_data_end: int) -> bytes:
    """
    Build the 240-byte RPTFILEHDR block.

    - Write header line: "RPTFILEHDR\t{domain}:{species}\t{timestamp}\x1A"
    - Zero-pad to 0xC0
    - Write fixed sub-header at 0xC0–0xEF
    - Patch compressed_data_end at 0xE8
    """
```

### Step 7: RPTINSTHDR Construction

```python
def build_rptinsthdr(spec: BuildSpec) -> bytes:
    """
    Build the 224-byte RPTINSTHDR block.

    If template provided: copy template and patch species_id + timestamps
    If no template: build from scratch with reasonable defaults
    """
```

### Step 8: Compressed Data Assembly

```python
def assemble_compressed_data(
    compressed_pages: List[Tuple[bytes, int, int]],
    compressed_binary: Optional[List[Tuple[bytes, int, int]]]
) -> Tuple[bytes, List[int], Optional[List[int]]]:
    """
    Assemble the compressed data area.

    Text-only: page1 + page2 + page3 + ...
    With binary: page1 + bin1 + page2 + bin2 + ...

    Returns:
    - Combined bytes
    - List of text page offsets (relative to RPTINSTHDR = value - 0xF0 from absolute)
    - List of binary object offsets (or None)
    """
```

### Step 9: Trailer Construction

```python
def build_sectionhdr(sections: List[SectionDef]) -> bytes:
    """Build SECTIONHDR block: marker + triplets + ENDDATA"""

def build_pagetblhdr(page_infos: List[PageTableRecord]) -> bytes:
    """Build PAGETBLHDR block: marker + 24-byte entries + ENDDATA"""

def build_bpagetblhdr(binary_infos: List[BinaryTableRecord]) -> bytes:
    """Build BPAGETBLHDR block: marker + 16-byte entries + ENDDATA"""
```

### Step 10: Final Assembly

```python
def build_rpt(spec: BuildSpec, output_path: str):
    """
    Assemble all blocks into a complete RPT file:

    1. Analyze pages (line widths, line counts)
    2. If binary: chunk the binary file, generate/use Object Header
    3. Compress all text pages and binary chunks
    4. Assemble compressed data area (interleaved if binary)
    5. Build trailer structures (SECTIONHDR, PAGETBLHDR, BPAGETBLHDR)
    6. Calculate all offsets (backpatch Table Directory)
    7. Build RPTFILEHDR and RPTINSTHDR
    8. Write: RPTFILEHDR + RPTINSTHDR + TableDir + CompData + SECTIONHDR + PAGETBLHDR + BPAGETBLHDR

    Offset calculation:
    - compressed_data_start = 0x200 (always)
    - compressed_data_end = 0x200 + len(compressed_data_area)
    - sectionhdr_offset = compressed_data_end
    - pagetblhdr_offset = sectionhdr_offset + len(sectionhdr_block)
    - bpagetblhdr_offset = pagetblhdr_offset + len(pagetblhdr_block)
    - page_offset values = absolute_offset - 0xF0 (RPTINSTHDR-relative)
    """
```

### Step 11: Verification

```python
def verify_rpt(output_path: str):
    """
    Verify the built RPT file by reading it back with rpt_page_extractor:

    1. Parse header with parse_rpt_header()
    2. Read page table
    3. Decompress first and last page
    4. If binary: read BPAGETBLHDR, decompress binary objects, verify concatenation
    5. Compare page count, section count, binary count with expected values
    """
```

---

## Roundtrip Verification Strategy

The key quality check is **roundtrip fidelity**:

```bash
# 1. Extract
python3 rpt_page_extractor.py --output ./extracted 260271Q7.RPT

# 2. Rebuild
python3 rpt_file_builder.py --template 260271Q7.RPT \
  --species 52759 --domain 1 \
  --binary ./extracted/260271Q7/HKCIF001_016_20280309.PDF \
  -o rebuilt.RPT \
  ./extracted/260271Q7/

# 3. Re-extract
python3 rpt_page_extractor.py --output ./re-extracted rebuilt.RPT

# 4. Compare
diff ./extracted/260271Q7/page_00002.txt ./re-extracted/rebuilt/page_00002.txt
diff ./extracted/260271Q7/HKCIF001_016_20280309.PDF ./re-extracted/rebuilt/HKCIF001_016_20280309.PDF
```

The text pages and binary documents must be **byte-identical** after roundtrip. The RPT file binary layout may differ slightly (different zlib compression levels, timestamp differences), but the extracted content must match exactly.

---

## Dependencies

```
rpt_file_builder.py  ──imports──▶  rpt_section_reader.py (for parse_rpt_header, RptHeader)
                     ──imports──▶  rpt_page_extractor.py (for read_page_table, verify)
                     ──stdlib──▶   struct, zlib, os, sys, argparse, datetime
```

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| No text pages provided | Error: at least 1 text page required |
| Binary file not found | Error with path |
| Binary file given but only 1 text page | Warning: single chunk (Object Header + binary = 2 pages minimum for interleaving) |
| Section ranges overlap | Error with details |
| Section ranges exceed page count | Error with details |
| Template RPT file invalid | Warning, falls back to generic template |
| Page text contains non-ASCII | Warning per page, replaces with `?` |
| Output file already exists | Error unless `--force` flag used |
| Verification fails | Warning with details of mismatch |

---

## Future Extensions

- **`--append`** mode: Add pages/sections to an existing RPT file
- **`--merge`** mode: Merge multiple RPT files into one
- **GUI wrapper**: Integrate with the RPT_Page_Extractor menu scripts
- **JS/C++ ports**: Match the three-implementation pattern of rpt_page_extractor
