# Python API Reference

## Module: papyrus_rpt_page_extractor

Complete API reference for the Python RPT Page Extractor module.

---

## Overview

The module exports the following main components:
- Classes: `PageEntry`, `BinaryEntry`, `SelectionRule`
- Functions: `parse_selection_rule()`, `extract_rpt()`
- Constants: Exit codes, file structure sizes, magic signatures

---

## Exit Codes (Constants)

```python
EXIT_SUCCESS = 0                    # Successful extraction
EXIT_INVALID_ARGS = 1              # Argument count/format error
EXIT_FILE_NOT_FOUND = 2            # Input file doesn't exist
EXIT_INVALID_RPT_FILE = 3          # Not a valid RPT file
EXIT_READ_ERROR = 4                # Failed to read file
EXIT_WRITE_ERROR = 5               # Failed to write output
EXIT_INVALID_SELECTION_RULE = 6    # Selection rule format error
EXIT_NO_PAGES_SELECTED = 7         # Selection matched no pages
EXIT_DECOMPRESSION_ERROR = 8       # Zlib decompression failed
EXIT_MEMORY_ERROR = 9              # Memory allocation failed
EXIT_UNKNOWN_ERROR = 10            # Unexpected error
```

---

## Classes

### PageEntry

Represents a single page in an RPT file.

**Attributes**:
```python
page_num : int              # Page number (1-based)
offset : int                # Byte offset in file
compressed_size : int       # Compressed data size (bytes)
uncompressed_size : int     # Decompressed data size (bytes)
section_id : int            # Section identifier
```

**Example**:
```python
entry = PageEntry(
    page_num=1,
    offset=1024,
    compressed_size=4096,
    uncompressed_size=16384,
    section_id=14259
)

print(f"Page {entry.page_num} at offset {entry.offset}")
```

---

### BinaryEntry

Represents a binary object (PDF/AFP) in an RPT file.

**Attributes**:
```python
entry_num : int             # Entry number
offset : int                # Byte offset in file
compressed_size : int       # Compressed size (bytes)
uncompressed_size : int     # Decompressed size (bytes)
object_type : int           # Binary object type
```

**Example**:
```python
entry = BinaryEntry(
    entry_num=0,
    offset=8192,
    compressed_size=2048,
    uncompressed_size=8192,
    object_type=1
)

print(f"Binary object {entry.entry_num}: {entry.uncompressed_size} bytes")
```

---

### SelectionRule

Represents a parsed page/section selection rule.

**Attributes**:
```python
mode : str                  # "all", "pages", or "sections"
page_ranges : List[Tuple[int, int]]  # List of (start, end) page ranges
section_ids : Set[int]      # Set of section identifiers
```

**Example**:
```python
rule = SelectionRule()
rule.mode = "pages"
rule.page_ranges = [(1, 10), (20, 30)]

print(f"Extract pages: {rule.page_ranges}")
```

---

## Functions

### parse_selection_rule(rule_str: str) -> SelectionRule

Parse a selection rule string into a SelectionRule object.

**Parameters**:
- `rule_str` (str): Selection rule string

**Returns**:
- `SelectionRule`: Parsed selection rule object

**Raises**:
- `ValueError`: If rule format is invalid

**Supported Formats**:
- `"all"` - All pages
- `"pages:1-5"` - Single range
- `"pages:1-5,10-20,50-60"` - Multiple ranges
- `"section:14259"` - Single section
- `"sections:14259,14260,14261"` - Multiple sections

**Examples**:

```python
# All pages
rule = parse_selection_rule("all")
assert rule.mode == "all"

# Single page range
rule = parse_selection_rule("pages:1-10")
assert rule.mode == "pages"
assert rule.page_ranges == [(1, 10)]

# Multiple ranges
rule = parse_selection_rule("pages:1-5,10-20,50-60")
assert rule.page_ranges == [(1, 5), (10, 20), (50, 60)]

# Single section
rule = parse_selection_rule("section:14259")
assert rule.mode == "sections"
assert 14259 in rule.section_ids

# Multiple sections
rule = parse_selection_rule("sections:14259,14260,14261")
assert len(rule.section_ids) == 3
```

---

### extract_rpt(input_path: str, selection_rule: SelectionRule, output_text_path: str, output_binary_path: str, extract_mode: str = "both") -> Tuple[int, str]

Extract pages from an RPT file.

**Parameters**:
- `input_path` (str): Path to RPT file or %TMPFILE% from Papyrus
- `selection_rule` (SelectionRule): Parsed selection rule
- `output_text_path` (str): Path for text output file
- `output_binary_path` (str): Path for binary output file
- `extract_mode` (str): "text", "binary", or "both" (default: "both")

**Returns**:
- `Tuple[int, str]`: (exit_code, message)

**Exit Codes**:
- `0` - Success
- `2` - File not found
- `3` - Invalid RPT file
- `6` - Invalid selection rule
- `7` - No pages selected
- `8` - Decompression error
- Other codes for various errors

**Examples**:

```python
# Extract all pages
rule = parse_selection_rule("all")
exit_code, message = extract_rpt(
    "report.rpt",
    rule,
    "output.txt",
    "output.pdf"
)

if exit_code == 0:
    print("Success:", message)
else:
    print("Error:", message)

# Extract specific pages
rule = parse_selection_rule("pages:1-10,20-30")
exit_code, message = extract_rpt(
    "report.rpt",
    rule,
    "pages_10_30.txt",
    "pages_10_30.pdf"
)

# Extract text only
exit_code, message = extract_rpt(
    "report.rpt",
    rule,
    "output.txt",
    "/dev/null",  # Discard binary
    extract_mode="text"
)

# Extract binary only
exit_code, message = extract_rpt(
    "report.rpt",
    rule,
    "/dev/null",  # Discard text
    "output.pdf",
    extract_mode="binary"
)
```

---

### read_rpt_header(filepath: str) -> Tuple[dict, int]

Read and validate RPT file header.

**Parameters**:
- `filepath` (str): Path to RPT file

**Returns**:
- `Tuple[dict, int]`: (header_dict, page_count)

**Raises**:
- `ValueError`: If file is invalid

**Example**:

```python
try:
    header, page_count = read_rpt_header("report.rpt")
    print(f"RPT file with {page_count} pages")
except ValueError as e:
    print(f"Invalid file: {e}")
```

---

### read_page_table(filepath: str, page_count: int) -> Tuple[List[PageEntry], int]

Read page table from RPT file.

**Parameters**:
- `filepath` (str): Path to RPT file
- `page_count` (int): Number of pages from header

**Returns**:
- `Tuple[List[PageEntry], int]`: (page_entries, first_offset)

**Example**:

```python
header, page_count = read_rpt_header("report.rpt")
pages, first_offset = read_page_table("report.rpt", page_count)

for page in pages[:5]:
    print(f"Page {page.page_num}: {page.uncompressed_size} bytes")
```

---

### decompress_page(filepath: str, entry: PageEntry) -> bytes

Decompress a single page.

**Parameters**:
- `filepath` (str): Path to RPT file
- `entry` (PageEntry): Page entry to decompress

**Returns**:
- `bytes`: Decompressed page data

**Raises**:
- `ValueError`: If decompression fails

**Example**:

```python
header, page_count = read_rpt_header("report.rpt")
pages, _ = read_page_table("report.rpt", page_count)

# Decompress first page
page_data = decompress_page("report.rpt", pages[0])
print(f"Decompressed {len(page_data)} bytes")
```

---

### decompress_pages(filepath: str, entries: List[PageEntry]) -> List[bytes]

Decompress multiple pages.

**Parameters**:
- `filepath` (str): Path to RPT file
- `entries` (List[PageEntry]): List of page entries

**Returns**:
- `List[bytes]`: List of decompressed pages

**Example**:

```python
pages, _ = read_page_table("report.rpt", page_count)

# Decompress first 10 pages
selected = pages[:10]
decompressed = decompress_pages("report.rpt", selected)

total_bytes = sum(len(p) for p in decompressed)
print(f"Decompressed {len(decompressed)} pages, {total_bytes} bytes total")
```

---

### read_binary_page_table(filepath: str) -> Tuple[List[BinaryEntry], int]

Read binary object table from RPT file.

**Parameters**:
- `filepath` (str): Path to RPT file

**Returns**:
- `Tuple[List[BinaryEntry], int]`: (binary_entries, binary_count)

**Example**:

```python
binaries, count = read_binary_page_table("report.rpt")
print(f"Found {count} binary objects")

for binary in binaries:
    print(f"Binary {binary.entry_num}: {binary.uncompressed_size} bytes")
```

---

### decompress_binary_objects(filepath: str, entries: List[BinaryEntry]) -> List[bytes]

Decompress and concatenate binary objects.

**Parameters**:
- `filepath` (str): Path to RPT file
- `entries` (List[BinaryEntry]): Binary entries to decompress

**Returns**:
- `List[bytes]`: List containing concatenated binary data

**Example**:

```python
binaries, _ = read_binary_page_table("report.rpt")

if binaries:
    concatenated = decompress_binary_objects("report.rpt", binaries)
    with open("output.pdf", "wb") as f:
        f.write(concatenated[0])
```

---

### select_pages_by_range(entries: List[PageEntry], page_ranges: List[Tuple[int, int]]) -> Tuple[List[PageEntry], List[int], List[int]]

Select pages matching specified ranges.

**Parameters**:
- `entries` (List[PageEntry]): All page entries
- `page_ranges` (List[Tuple[int, int]]): List of (start, end) page ranges

**Returns**:
- `Tuple[List[PageEntry], List[int], List[int]]`: (selected, found, skipped)

**Example**:

```python
pages, _ = read_page_table("report.rpt", page_count)

# Select pages 1-10 and 20-30
ranges = [(1, 10), (20, 30)]
selected, found, skipped = select_pages_by_range(pages, ranges)

print(f"Selected {len(selected)} pages")
print(f"Found: {found}")
print(f"Skipped: {skipped}")
```

---

### select_pages_by_sections(entries: List[PageEntry], section_ids: Set[int]) -> Tuple[List[PageEntry], List[int], List[int]]

Select pages matching specified section IDs.

**Parameters**:
- `entries` (List[PageEntry]): All page entries
- `section_ids` (Set[int]): Section identifiers to select

**Returns**:
- `Tuple[List[PageEntry], List[int], List[int]]`: (selected, found_sections, skipped_sections)

**Example**:

```python
pages, _ = read_page_table("report.rpt", page_count)

# Select pages from sections 14259 and 14260
sections = {14259, 14260}
selected, found, skipped = select_pages_by_sections(pages, sections)

print(f"Selected {len(selected)} pages from {len(found)} sections")
```

---

## Usage Examples

### Example 1: Simple Extraction

```python
from papyrus_rpt_page_extractor import parse_selection_rule, extract_rpt

# Parse rule
rule = parse_selection_rule("pages:1-10")

# Extract
code, msg = extract_rpt("report.rpt", rule, "out.txt", "out.pdf")

if code == 0:
    print("Success!")
else:
    print(f"Error {code}: {msg}")
```

---

### Example 2: Complex Selection

```python
from papyrus_rpt_page_extractor import parse_selection_rule, extract_rpt

# Complex rule with multiple ranges
rule = parse_selection_rule("pages:1-5,10-20,50-60,100-110")

code, msg = extract_rpt("report.rpt", rule, "summary.txt", "summary.pdf")
```

---

### Example 3: Section-Based Extraction

```python
from papyrus_rpt_page_extractor import parse_selection_rule, extract_rpt

# Extract multiple sections
rule = parse_selection_rule("sections:14259,14260,14261")

code, msg = extract_rpt("report.rpt", rule, "depts.txt", "depts.pdf")
```

---

### Example 4: Error Handling

```python
from papyrus_rpt_page_extractor import (
    parse_selection_rule,
    extract_rpt,
    EXIT_SUCCESS,
    EXIT_FILE_NOT_FOUND,
    EXIT_INVALID_SELECTION_RULE
)

try:
    rule = parse_selection_rule("pages:1-10")
except ValueError as e:
    print(f"Invalid rule: {e}")
    exit(1)

code, msg = extract_rpt("report.rpt", rule, "out.txt", "out.pdf")

if code == EXIT_SUCCESS:
    print("Extraction successful")
elif code == EXIT_FILE_NOT_FOUND:
    print("Input file not found")
else:
    print(f"Error: {msg}")
```

---

### Example 5: Low-Level Access

```python
from papyrus_rpt_page_extractor import (
    read_rpt_header,
    read_page_table,
    decompress_pages,
    select_pages_by_range
)

# Read header
header, page_count = read_rpt_header("report.rpt")
print(f"Pages: {page_count}")

# Read page table
pages, _ = read_page_table("report.rpt", page_count)

# Select pages
selected, found, skipped = select_pages_by_range(pages, [(1, 10)])

# Decompress
decompressed = decompress_pages("report.rpt", selected)

# Write output
with open("output.txt", "wb") as f:
    for page in decompressed:
        f.write(page)
```

---

## Constants

### RPT File Structure Sizes

```python
RPTFILEHDR_SIZE = 40        # Main header size
RPTINSTHDR_SIZE = 12        # Instance header size
PAGETBLHDR_SIZE = 28        # Page table entry size
SECTIONHDR_SIZE = 36        # Section header size
BPAGETBLHDR_SIZE = 28       # Binary object table entry size
```

### Magic Signatures

```python
RPTFILE_SIGNATURE = b'RPTFILE'        # RPT file signature
RPTINST_SIGNATURE = b'RPTINST'        # Instance signature
PAGEOBJ_SIGNATURE = b'PAGEOBJ'        # Page object signature
SECTIONHDR_SIGNATURE = b'SECTIONHDR'  # Section header signature
BPAGEOBJ_SIGNATURE = b'BPAGEOBJ'      # Binary object signature
```

---

## Type Hints

All functions include type hints for better IDE support:

```python
from typing import Tuple, List, Dict, Optional, Set

def parse_selection_rule(rule_str: str) -> SelectionRule
def extract_rpt(
    input_path: str,
    selection_rule: SelectionRule,
    output_text_path: str,
    output_binary_path: str,
    extract_mode: str = "both"
) -> Tuple[int, str]
```

---

## Performance Tips

1. **Use sections for large selections**
   - Faster lookup than page ranges
   - Better for logical grouping

2. **Extract only needed modes**
   - Use `extract_mode="text"` or `"binary"` if you don't need both
   - Saves processing time

3. **Batch processing**
   - Extract multiple ranges in one call rather than multiple calls
   - Reduces file I/O overhead

4. **Cache parsed rules**
   - Parse rules once, reuse them
   - Avoid repeated parsing overhead

---

## Compatibility

- **Python**: 3.7+
- **Platforms**: Windows, macOS, Linux
- **Dependencies**: None (standard library only)

---

## Version

API Version: 2.0.0
Last Updated: February 2025
