# IntelliSTOR Section/Index Algorithm - Complete Specification

## Overview

This document describes the complete algorithm for:
1. **Section Segregation** - Splitting spool files by BRANCH for permission-based viewing
2. **Index Search** - Finding values (like Account Numbers) in the spool file using the MAP index
3. **Fast Page Access** - How to quickly navigate to specific pages in large (3GB+) spool files

---

## Database Schema - Key Tables and Joins

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ REPORT_INSTANCE                                                             │
│ Keys: DOMAIN_ID, REPORT_SPECIES_ID, AS_OF_TIMESTAMP                         │
│ Data: STRUCTURE_DEF_ID, RPT_FILE_SIZE_KB, MAP_FILE_SIZE_KB                  │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         ├── JOIN ON: DOMAIN_ID + REPORT_SPECIES_ID + AS_OF_TIMESTAMP
         │   ▼
         │   ┌─────────────────────────────────────────────────────────────────┐
         │   │ SST_STORAGE                                                     │
         │   │ Data: MAP_FILE_ID                                               │
         │   └─────────────────────────────────────────────────────────────────┘
         │            │
         │            │ JOIN ON: MAP_FILE_ID
         │            ▼
         │   ┌─────────────────────────────────────────────────────────────────┐
         │   │ MAPFILE                                                         │
         │   │ Data: FILENAME, LOCATION_ID                                     │
         │   │       → Binary .MAP file = search index                         │
         │   └─────────────────────────────────────────────────────────────────┘
         │
         ├── JOIN ON: DOMAIN_ID + REPORT_SPECIES_ID + AS_OF_TIMESTAMP
         │   ▼
         │   ┌─────────────────────────────────────────────────────────────────┐
         │   │ RPTFILE_INSTANCE (links to spool file)                          │
         │   │ Data: RPT_FILE_ID                                               │
         │   └─────────────────────────────────────────────────────────────────┘
         │            │
         │            │ JOIN ON: RPT_FILE_ID
         │            ▼
         │   ┌─────────────────────────────────────────────────────────────────┐
         │   │ RPTFILE                                                         │
         │   │ Data: FILENAME, LOCATION_ID                                     │
         │   │       → Spool file (.TXT/.RPT) = actual report content          │
         │   └─────────────────────────────────────────────────────────────────┘
         │
         └── JOIN ON: DOMAIN_ID + REPORT_SPECIES_ID + AS_OF_TIMESTAMP
             ▼
         ┌─────────────────────────────────────────────────────────────────────┐
         │ REPORT_INSTANCE_SEGMENT                                             │
         │ Keys: + SEGMENT_NUMBER                                              │
         │ Data: START_PAGE_NUMBER, NUMBER_OF_PAGES                            │
         │       SEGMENT_NUMBER = positional index into sections               │
         └─────────────────────────────────────────────────────────────────────┘


FIELD DEFINITIONS PATH:

┌─────────────────────────────────────────────────────────────────────────────┐
│ REPORT_INSTANCE.STRUCTURE_DEF_ID                                            │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         │ JOIN ON: STRUCTURE_DEF_ID
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LINE                                                                        │
│ Keys: STRUCTURE_DEF_ID, LINE_ID                                             │
│ Data: NAME, TEMPLATE (pattern to match lines in spool file)                 │
│       Template uses: 'A'=alpha, '9'=digit, ' '=space, '*'=literal           │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         │ JOIN ON: STRUCTURE_DEF_ID + LINE_ID
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ FIELD                                                                       │
│ Keys: STRUCTURE_DEF_ID, LINE_ID, FIELD_ID                                   │
│ Data: NAME, START_COLUMN, END_COLUMN                                        │
│       IS_INDEXED=1 → Field is searchable (values stored in MAP index)       │
│       IS_SIGNIFICANT=1 → Field defines section boundaries (BRANCH)          │
└─────────────────────────────────────────────────────────────────────────────┘


SECTION PERMISSION PATH:

┌─────────────────────────────────────────────────────────────────────────────┐
│ SECTION                                                                     │
│ Keys: DOMAIN_ID, REPORT_SPECIES_ID, SECTION_ID                              │
│ Data: NAME (the section value, e.g., "501", "501 49")                       │
└─────────────────────────────────────────────────────────────────────────────┘
         │
         │ JOIN ON: REPORT_SPECIES_ID + SECTION_ID
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ STYPE_SECTION                                                               │
│ Keys: REPORT_SPECIES_ID, SECTION_ID                                         │
│ Data: VALUE (Windows Security Descriptor / ACL binary)                      │
│       → Determines WHO can view this section                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Spool File Format and Fast Page Access

### Two Common Spool File Formats

#### 1. Form Feed Format
```
- Pages separated by Form Feed character (ASCII 0x0C)
- Example: FRX16.txt uses this format
- Page detection: scan for 0x0C bytes

Page 1 content...
<0x0C>
Page 2 content...
<0x0C>
Page 3 content...
```

#### 2. ASA Carriage Control Format
```
- First character of each line is a control character
- '1' = start new page (equivalent to form feed)
- ' ' = normal line (single space)
- '0' = double space before line
- '-' = triple space before line
- Example: CDU100P.txt uses this format

1                                          ← Page 1 starts
 DATE PRINTED: 22/01/25   20:14:44
 OCBC BANK                BRANCH: 000
...
1                                          ← Page 2 starts
 DATE PRINTED: 22/01/25   20:14:44
...
```

### Fast Page Access Strategy

For large spool files (up to 3GB with 300K+ pages), fast access requires:

```
1. BUILD PAGE OFFSET INDEX (on first access or during indexing):

   For Form Feed format:
   - Scan file for all 0x0C positions
   - Store: page_offsets = [0, pos_of_first_0x0C + 1, pos_of_second_0x0C + 1, ...]

   For ASA format:
   - Scan file line by line
   - When line starts with '1', record byte offset
   - Store: page_offsets = [0, offset_of_line_with_1, ...]

2. SEEK TO PAGE:
   - To access page N: seek to page_offsets[N-1]
   - Read until page_offsets[N] (or next page marker)

3. CACHING STRATEGY:
   - Cache page offset index in memory or separate file
   - Index size: ~4 bytes per page (4MB for 1M pages)
   - Or: store in MAP file (not currently implemented)
```

### Page Size Statistics

From database analysis:
```
Report Type    RPT Size    Pages      Avg Page Size
-----------    --------    -----      -------------
Large GL       723 MB      309,560    ~2,400 bytes
Statements     522 MB      687,003    ~780 bytes
Typical        1-10 MB     100-1000   ~1,000-3,000 bytes
```

---

## Binary MAP File Structure

### Header (bytes 0-89)
```
Offset  Size   Description
0-11    12B    "MAPHDR" (UTF-16LE signature)
12-17   6B     Unknown/padding
18-19   2B     Segment count (number of **ME markers)
20-31   12B    Unknown
32-51   20B    Date string 1 (UTF-16LE: "01/01/2025")
52-71   20B    Date string 2 (UTF-16LE)
72-83   12B    Unknown
84-89   6B     Padding to first **ME marker
```

### Segment Structure (after each **ME marker)
```
Each segment starts with **ME marker: 0x2a002a004d004500 (UTF-16LE)

Segment Header (offset +0 from **ME):
Offset  Size   Description
+0      4B     Constant: 0x008e0000
+4      4B     Segment index (0, 1, 2, ...)
+8      4B     Offset to next **ME marker (absolute file position)
+12     4B     Unknown (zeros)

Segment Metadata (offset +16):
+16     2B     Page number where this segment's data starts
+18     2B     LINE_ID of indexed field
+20     2B     Unknown
+22     2B     FIELD_ID or related
+24     2B     Unknown
+26     2B     Value or count
... additional metadata varies by segment type

Index Entry Data (after metadata):
- Contains extracted field values and their page locations
- Format varies based on field type (text, numeric, date)
```

### Segment Content Purpose
```
Binary Segment 0: Lookup/Directory segment - maps LINE_ID/FIELD_ID to segment numbers
Binary Segment 1+: Index data for IS_INDEXED fields

Example for STRUCTURE_DEF_ID 9643:
- Segment 0: Lookup table (which LINE_ID/FIELD_ID is in which segment)
- Segment 1: LINE 4, FIELD 2 data (product field, width=55)
- Segment 2: LINE 5, FIELD 3 data (Reference_ID, width=18)
- Segment 3: LINE 5, FIELD 6 data (value_date, width=4)
- Segment 4-8: LINE 6 data (multiple indexed fields)

The segment metadata [PAGE, LINE_ID, FIELD_ID, FIELD_WIDTH] tells which
field's indexed values are stored in this segment.
```

### Segment 0: Lookup/Directory Table

Segment 0 contains a lookup table that maps (LINE_ID, FIELD_ID) combinations
to their corresponding segment numbers. This allows quick lookup of which
segment contains index data for a specific field.

```
Segment 0 Lookup Table Structure:
┌────────────────────────────────────────────────────────────────────┐
│ Each entry is 4 bytes:                                             │
│ [SEG_NUM:1][LINE_ID:1][FIELD_ID:1][FLAGS:1]                        │
│                                                                    │
│ Example entries from 25001002.MAP Segment 0:                       │
│   SEG=1, LINE_ID= 2, FIELD_ID= 2, FLAGS=0                          │
│   SEG=1, LINE_ID= 7, FIELD_ID= 5, FLAGS=0                          │
│   SEG=2, LINE_ID= 7, FIELD_ID= 5, FLAGS=0                          │
│   SEG=3, LINE_ID=13, FIELD_ID= 6, FLAGS=0                          │
│   ...                                                              │
└────────────────────────────────────────────────────────────────────┘

Correlation with actual segments (25001002.MAP):
┌─────────┬─────────┬──────────┬─────────────┐
│ Segment │ LINE_ID │ FIELD_ID │ FIELD_WIDTH │
├─────────┼─────────┼──────────┼─────────────┤
│    1    │    4    │    2     │     55      │
│    2    │    5    │    3     │     18      │
│    3    │    5    │    6     │      4      │
│    4    │    6    │    3     │      4      │
│    5    │    6    │    4     │      5      │
│    6    │    6    │    5     │      3      │
│    7    │    6    │    9     │     19      │
│    8    │    6    │   11     │     19      │
└─────────┴─────────┴──────────┴─────────────┘
```

### Detailed Segment Metadata Structure

After each **ME marker, the segment metadata provides information about the indexed field:

```
Offset from **ME marker:
+0-7    8B     **ME marker itself (0x2a002a004d004500 UTF-16LE)
+8-11   4B     Header constant (e.g., 0x008e0000)
+12-15  4B     Segment index (0, 1, 2, 3...)
+16-19  4B     Offset to next **ME marker (absolute file position)
+20-23  4B     Unknown/flags

Segment Metadata Block (offset +24 from **ME):
+24-25  2B     Starting page number for this segment's data
+26-27  2B     LINE_ID (which LINE definition this segment indexes)
+28-29  2B     Unknown/reserved
+30-31  2B     FIELD_ID (which FIELD within the LINE)
+32-33  2B     Unknown/reserved
+34-35  2B     Field width in characters (column width)
+36-37  2B     Unknown/reserved
+38-39  2B     Entry count (number of index entries in this segment)
+40-47  8B     Additional metadata/padding
+48+    var    Index entry data begins
```

### Index Entry Format (IS_INDEXED Field Values)

Each index entry stores one extracted field value and its page location:

```
┌─────────────────────────────────────────────────────────────────┐
│ INDEX ENTRY STRUCTURE                                           │
├─────────────────────────────────────────────────────────────────┤
│ Bytes 0-1:    Length indicator (2 bytes, little-endian)         │
│               Usually equals field_width                         │
│                                                                 │
│ Bytes 2-(N+1): Text value (N = field_width bytes)               │
│               Space-padded to full width                         │
│               Encoding: ASCII or similar single-byte             │
│                                                                 │
│ Bytes (N+2)-(N+3): Page number (2 bytes, little-endian)         │
│               Page where this value appears in spool file        │
│                                                                 │
│ Bytes (N+4)-(N+6): Flags/separator (3 bytes)                    │
│               Usually 0x00 0x00 0x00                             │
├─────────────────────────────────────────────────────────────────┤
│ TOTAL ENTRY SIZE = 7 + field_width bytes                        │
└─────────────────────────────────────────────────────────────────┘

Example: Reference_ID field (width=18 characters)
Entry size = 7 + 18 = 25 bytes per entry

Hex dump of one entry:
00 12                          Length indicator (18 = 0x12)
45 50 32 34 31 32 33 31        'EP241231'
30 39 30 33 39 34 39 39        '09039499'
20 20                          '  ' (space padding)
02 00                          Page number = 2
00 00 00                       Flags/separator

Decoded: Value 'EP24123109039499' appears on PAGE 2
```

### Index Entry Examples from 25001002.MAP

Analysis of Segment 2 (Reference_ID field, width=18):
```
Entry 1: 'EP24123109039499  ' → PAGE 2
Entry 2: 'EP24123109039500  ' → PAGE 12
Entry 3: 'EP24123110039504  ' → PAGE 23
```

### Index Data Types

Different field types have slightly different encoding:

```
TEXT FIELDS (e.g., Reference_ID, Account_No):
- Length indicator = field width
- Value = ASCII text, space-padded right
- Standard entry format as described above

NUMERIC FIELDS (e.g., amounts):
- Length indicator may encode precision/scale
- Value may be binary-encoded decimal
- Additional bytes for sign/decimal position

DATE FIELDS (e.g., value_date):
- Often stored as packed date (YYYYMMDD as 4 bytes)
- Or as text in standard format
- Entry format: [length][date_bytes][page][flags]

Example DATE entry (from Segment 3, value_date field):
1F 0C E9 07  = Date encoding (2025-12-31 in packed format)
0C 00        = Page number (12)
00 00 00     = Flags
```

### Searching the Index

**Complete Search Algorithm:**

```
1. GET FIELD DEFINITION:
   - Query FIELD table for STRUCTURE_DEF_ID
   - Get LINE_ID, FIELD_ID for the search field (WHERE IS_INDEXED=1)

2. FIND SEGMENT IN MAP FILE:
   - Read Segment 0 lookup table
   - Find entry with matching LINE_ID and FIELD_ID
   - Get segment number for that field

3. ITERATE INDEX ENTRIES:
   - Go to the target segment
   - Read segment metadata to get FIELD_WIDTH
   - Entry size = 7 + FIELD_WIDTH bytes
   - For each entry: [length:2][value:N][page:2][flags:3]

4. MATCH VALUE:
   - Compare search value with entry value
   - If match, get PAGE number from entry

5. EXTRACT FROM SPOOL FILE:
   - Use PAGE number to seek to correct position
   - Return matching page content
```

**Python Implementation:**

```python
def search_map_index(map_data, search_value, line_id, field_id):
    """
    Search for a value in the MAP file index.

    Args:
        map_data: Raw bytes of .MAP file
        search_value: Value to search for
        line_id: LINE_ID from FIELD table
        field_id: FIELD_ID from FIELD table

    Returns: List of page numbers where value appears
    """
    pages = []

    # 1. Find segment with matching LINE_ID and FIELD_ID
    for segment in parse_segments(map_data):
        if segment.line_id == line_id and segment.field_id == field_id:

            # 2. Get field width from segment metadata
            field_width = segment.field_width
            entry_size = 7 + field_width

            # 3. Iterate through index entries
            offset = segment.data_offset
            for i in range(segment.entry_count):
                # Read entry: [length:2][text:N][page:2][flags:3]
                length = read_uint16(map_data, offset)
                value = map_data[offset+2 : offset+2+field_width].decode('ascii').strip()
                page = read_uint16(map_data, offset+2+field_width)

                # 4. Compare values
                if value == search_value or value.startswith(search_value):
                    pages.append(page)

                offset += entry_size

    return pages

def parse_segment_metadata(map_data, me_offset):
    """
    Parse segment metadata from **ME marker position.

    Returns dict with: line_id, field_id, field_width, data_offset
    """
    import struct

    # Header is at me_offset + 8 (after **ME marker)
    # Metadata is at me_offset + 24
    meta_off = me_offset + 24

    page_start = struct.unpack_from('<H', map_data, meta_off)[0]
    line_id = struct.unpack_from('<H', map_data, meta_off + 2)[0]
    field_id = struct.unpack_from('<H', map_data, meta_off + 6)[0]
    field_width = struct.unpack_from('<H', map_data, meta_off + 10)[0]
    entry_count = struct.unpack_from('<H', map_data, meta_off + 12)[0]

    return {
        'page_start': page_start,
        'line_id': line_id,
        'field_id': field_id,
        'field_width': field_width,
        'entry_count': entry_count,
        'data_offset': meta_off + 40  # Approximate; may need adjustment
    }
```

### Binary vs Database Segments

**Important distinction:**

| Concept | Purpose | Count Relation |
|---------|---------|----------------|
| Binary **ME segments | Internal index structure | Multiple per MAP file |
| REPORT_INSTANCE_SEGMENT | Page ranges per section | Based on IS_SIGNIFICANT fields |
| SECTION table entries | Named sections (branches) | Master list per report type |

Binary segment count often differs from database segment count because:
- Binary segments organize index data by LINE_ID/FIELD_ID
- Database segments track page ranges per section (branch)
- A report with 1 section may have 9 binary index segments (one per indexed field)

---

## Algorithm 1: Section Segregation (IS_SIGNIFICANT Fields)

**Purpose:** Split spool file by BRANCH for permission-based viewing.

### When IS_SIGNIFICANT = 1:
- The field value defines a **section boundary**
- Can have **multiple IS_SIGNIFICANT fields** (e.g., BRANCH + SEGMENT)
- Combined values form the section name (e.g., "501 49")
- **Permission check via STYPE_SECTION.VALUE (Windows ACL)**

### Workflow:
```
1. User requests report (DOMAIN_ID, REPORT_SPECIES_ID, AS_OF_TIMESTAMP)

2. CHECK PERMISSIONS:
   a. Get user's Windows SID
   b. Query STYPE_SECTION for this REPORT_SPECIES_ID
   c. Parse ACL in VALUE column to determine allowed SECTION_IDs
   d. If user can see ALL sections → no segregation needed
   e. If user can only see specific sections → continue to step 3

3. GET ALLOWED PAGE RANGES:
   For each allowed SECTION_ID:
   a. Lookup SECTION.NAME → get section value (e.g., "501")
   b. Find SEGMENT_NUMBER: position in ordered section list for instance
   c. REPORT_INSTANCE_SEGMENT at that SEGMENT_NUMBER
   d. Get START_PAGE_NUMBER, NUMBER_OF_PAGES

4. EXTRACT PAGES:
   a. Load/build page offset index for spool file
   b. For each allowed page range:
      - Seek to page_offsets[START_PAGE_NUMBER - 1]
      - Read NUMBER_OF_PAGES pages
   c. Return segregated content to user
```

---

## Algorithm 2: Index Search (IS_INDEXED Fields)

**Purpose:** Find specific values (Account Numbers, etc.) in the spool file.

### When IS_INDEXED = 1:
- Field values are extracted and stored in binary MAP file
- **No permission check** - this is direct data lookup
- Used for searching accounts, reference IDs, dates, amounts, etc.

### Workflow:
```
1. User searches: "ACCOUNT_NO = 301-609191-501"

2. GET MAP FILE:
   REPORT_INSTANCE (DOMAIN_ID, REPORT_SPECIES_ID, AS_OF_TIMESTAMP)
       → SST_STORAGE.MAP_FILE_ID
       → MAPFILE.FILENAME
       → Read binary .MAP file

3. GET FIELD DEFINITION:
   REPORT_INSTANCE.STRUCTURE_DEF_ID
       → FIELD (WHERE IS_INDEXED=1 AND NAME='ACCOUNT_NO')
       → Get LINE_ID, FIELD_ID, START_COLUMN, END_COLUMN

4. SEARCH MAP FILE INDEX:
   a. Find segment with matching LINE_ID in metadata
   b. Search index entries for matching value
   c. Get page number(s) where value appears

5. EXTRACT MATCHING PAGES:
   a. Build page offset index for spool file
   b. Seek to page_offsets[found_page - 1]
   c. Read and return matching page(s)
```

### Multi-Line Table Handling (e.g., FXR16)

For reports where a logical "row" spans multiple physical lines:
```
FXR16 Example:
LINE 1: CLIENT ACCT/  CURR  DEAL...  (header - different LINE_ID)
LINE 2: NAME               TYPE...   (header continued)
LINE 3: ********************...      (separator line)
LINE 4: 1230035-005                  (account - matches LINE template)
LINE 5: CITI LON      DM    SPOT...  (details - different LINE_ID)

The LINE.TEMPLATE determines which physical lines match:
- Template for account line: starts with digits in account format
- Indexed field ACCOUNT_NO has specific LINE_ID
- MAP file stores index entries only for matching lines
```

---

## Example: CDU100P Report

### Structure Definition (STRUCTURE_DEF_ID = 10065):

**LINE 2** (Page header with BRANCH):
```
TEMPLATE: AAAA AAAA                AAAAAA: 999 ...
MATCHES:  OCBC BANK                BRANCH: 000 ...

Field_2_4: IS_SIGNIFICANT=1, cols 33-35 → BRANCH value "000"
```

**LINE 7** (Data line with ACCOUNT_NO):
```
TEMPLATE: 999-999999-999  999999 AAAAAAAAAAAAAAAAAAAA  A9 ...
MATCHES:  301-609191-501  001098 UA AZHAR ATM          F1 ...

ACCOUNT_NO: IS_INDEXED=1, cols 0-13 → searchable
```

### Spool File Format: ASA Carriage Control
- First character '1' = new page
- 4 pages in sample file
- Page byte offsets: [0, 7182, 14364, 20194]

---

## Summary

| Field Flag | Purpose | Permission Check | Uses MAP Index |
|------------|---------|------------------|----------------|
| IS_SIGNIFICANT=1 | Section segregation | Yes (STYPE_SECTION ACL) | No |
| IS_INDEXED=1 | Search/extraction | No | Yes |

### Complete Data Flow:
```
REPORT_INSTANCE
    ├── STRUCTURE_DEF_ID → LINE → FIELD (defines extraction rules)
    ├── SST_STORAGE → MAPFILE (binary search index)
    ├── RPTFILE_INSTANCE → RPTFILE (spool file path)
    └── REPORT_INSTANCE_SEGMENT (page ranges per section)

SECTION + STYPE_SECTION (permission control for sections)

SPOOL FILE (actual content)
    └── Page offsets built from 0x0C or '1' markers
```

### Performance Considerations:
```
For 3GB spool file with 300K pages:
1. Build page offset index once: ~1-2 seconds scan
2. Index size in memory: ~1.2MB (4 bytes × 300K)
3. Seek to any page: instant (no scanning)
4. MAP file index search: milliseconds
```
