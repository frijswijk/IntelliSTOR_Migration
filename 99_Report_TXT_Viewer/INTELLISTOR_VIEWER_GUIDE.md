# IntelliSTOR Viewer - User Guide

## Overview

`intellistor_viewer.py` is a Python tool for analyzing IntelliSTOR report data including:
- Binary MAP file parsing and index searching
- Spool file analysis (page detection and extraction)
- Database integration for report metadata

## Installation

### Requirements
```bash
pip install pymssql  # Optional, for database features
```

### File Location
```
/Volumes/acasis/projects/python/ocbc/IntelliSTOR_Migration/4. Migration_Instances/intellistor_viewer.py
```

---

## Command Line Usage

### Help
```bash
python intellistor_viewer.py --help
```

### Analyze MAP File Structure
```bash
# Basic analysis - shows segments and lookup table
python intellistor_viewer.py --map 25001002.MAP

# With sample index entries from each segment
python intellistor_viewer.py --map 25001002.MAP --show-entries
```

**Output:**
```
============================================================
MAP File: 25001002.MAP
============================================================
Date: 1/01/2025
Segment Count (from header): 9

Binary Segments (9):
Seg   Offset  LINE_ID  FIELD_ID  WIDTH  ENTRIES
--------------------------------------------------
  0       90   (Lookup/Directory Segment)
  1      482        4         2     55       13
  2      748        5         3     18       13
  ...

Segment 0 Lookup Table (20 entries):
 SEG  LINE_ID  FIELD_ID  FLAGS
------------------------------
   1        2         2      0
   ...
```

### Search MAP File Index
```bash
# Search for a specific value
python intellistor_viewer.py --map 25001002.MAP --search EP24123109039499 --line 5 --field 3

# Partial match search
python intellistor_viewer.py --map 25001002.MAP --search EP2412310 --line 5 --field 3
```

**Output:**
```
============================================================
Searching MAP File: 25001002.MAP
============================================================
Search value: 'EP24123109039499'
LINE_ID: 5, FIELD_ID: 3

Found segment 2 with field_width=18

Search Results (1 matches):
  PAGE 2
```

### Analyze Spool File
```bash
python intellistor_viewer.py --spool Report_TXT_Viewer/CDU100P.txt
```

**Output:**
```
============================================================
Spool File: CDU100P.txt
============================================================
File Size: 21,553 bytes
Format: asa
Page Count: 4

Page Offsets (first 10):
  Page 1: byte offset 0
  Page 2: byte offset 7,182
  ...
```

### Show Report Information (requires database)
```bash
python intellistor_viewer.py --report CDU100P
```

---

## Programmatic Usage

### MapFileParser Class

```python
from intellistor_viewer import MapFileParser

# Load and parse MAP file
parser = MapFileParser('/path/to/25001002.MAP')
parser.load()

# Get file info
info = parser.parse_header()
print(f"Segments: {info.segment_count}, Date: {info.date_string}")

# Parse all segments
segments = parser.parse_segments()
for seg in segments:
    print(f"Segment {seg.index}: LINE={seg.line_id}, FIELD={seg.field_id}, WIDTH={seg.field_width}")

# Search for a value
pages = parser.search_index('EP24123109039499', line_id=5, field_id=3)
print(f"Found on pages: {pages}")

# Get all indexed values for a field
values = parser.get_all_indexed_values(line_id=5, field_id=3)
for value, page in values:
    print(f"'{value}' → PAGE {page}")
```

### SpoolFileHandler Class

```python
from intellistor_viewer import SpoolFileHandler

# Load spool file
handler = SpoolFileHandler('/path/to/report.txt')
handler.load()

# Build page index
page_count = handler.build_page_index()
print(f"Format: {handler.format_type}, Pages: {page_count}")

# Get specific page content
page_content = handler.get_page(2)  # 1-indexed

# Get page range
pages = handler.get_page_range(start_page=5, num_pages=3)
```

---

## MAP File Structure

### Segment 0: Lookup/Directory Table
Maps (LINE_ID, FIELD_ID) combinations to segment numbers.

```
Entry format: [SEG_NUM:1][LINE_ID:1][FIELD_ID:1][FLAGS:1] = 4 bytes
```

### Segments 1-N: Index Data
Each segment stores index entries for one specific field.

**Segment Metadata (offset +24 from **ME marker):**
| Offset | Size | Description |
|--------|------|-------------|
| +0 | 2B | page_start |
| +2 | 2B | LINE_ID |
| +6 | 2B | FIELD_ID |
| +10 | 2B | field_width |
| +14 | 2B | entry_count |

**Index Entry Format:**
```
[length:2][value:N][page:2][flags:3]

Total entry size = 7 + field_width bytes
```

**Example (Reference_ID, width=18):**
```
00 12                    Length indicator (18)
45 50 32 34 31 32 ...    'EP24123109039499  '
02 00                    Page number = 2
00 00 00                 Flags
```

---

## Spool File Formats

### Form Feed Format
- Pages separated by ASCII 0x0C (Form Feed character)
- Example: FRX16.txt

### ASA Carriage Control Format
- First character of each line is a control character
- '1' = start new page
- ' ' = normal line
- Example: CDU100P.txt

---

## Configuration

Default settings in `Config` class:
```python
db_server: str = 'localhost'
db_port: int = 1433
db_name: str = 'iSTSGUAT'
db_user: str = 'sa'
db_password: str = 'Fvrpgr40'
map_file_dir: str = '/Volumes/X9Pro/OCBC/250_MapFiles'
```

Override via command line:
```bash
python intellistor_viewer.py --db-server myserver --db-name mydb --map-dir /path/to/maps
```

---

## Key Classes

| Class | Purpose |
|-------|---------|
| `Config` | Configuration settings |
| `MapFileParser` | Parse binary MAP files |
| `SpoolFileHandler` | Handle spool files with page indexing |
| `DatabaseAccess` | Database queries for report metadata |
| `IntelliSTORViewer` | Main viewer combining all functionality |

## Data Classes

| Class | Purpose |
|-------|---------|
| `MapFileInfo` | MAP file header info |
| `MapSegmentInfo` | Binary segment metadata |
| `IndexEntry` | Single index entry (value, page) |
| `FieldDef` | Field definition from database |
| `LineDef` | Line definition from database |
| `ReportInstance` | Report instance metadata |
| `Segment` | Database segment (page range) |
| `Section` | Section (branch) info |
