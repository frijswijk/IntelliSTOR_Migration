# IntelliSTOR Ingestion-to-Instance Pipeline - Complete Specification

## Overview

This document describes the complete lifecycle of a report in IntelliSTOR, from spool file arrival through indexing to instance creation. It covers:

1. **Ingestion Pipeline** - Spool arrival, SIGNATURE_GROUP routing, PAGINATOR processing
2. **Signature Pattern Matching** - How SIGNATURE and SENSITIVE_FIELD extract metadata
3. **Instance Creation** - Concatenation, segment tracking, RPT/MAP file linkage
4. **MAP File Binary Structure** - Segment 0 page-level index, field search indices
5. **RPT File Binary Structure** - SECTIONHDR, PAGETBLHDR, per-page zlib compression
6. **Section Segregation** - RPT file SECTIONHDR + SECTION/STYPE_SECTION permissions
7. **Index Search** - Finding field values (e.g., account numbers) via MAP file

---

## 1. Ingestion Pipeline

### 1.1 Spool File Arrival

Reports arrive as spool files from mainframe systems (Silverlake, MIDAS, etc.). Each spool file is a print stream in one of two formats:

**ASA Carriage Control Format** (most common at OCBC):
```
First character of each line is a control character:
  '1' = start new page (form feed equivalent)
  ' ' = normal line (single space)
  '0' = double space before line
  '-' = triple space before line
Lines terminated by CRLF (0x0D 0x0A)
```

**Form Feed Format**:
```
Pages separated by Form Feed character (ASCII 0x0C)
```

### 1.2 SIGNATURE_GROUP - Routing Label

Each arriving spool file is assigned a **SIGNATURE_GROUP** (e.g., `DEPOSITS_RD`, `MSCP_RPTS`, `MIDASPLUS_RPT`). This is a purely operational routing label that directs the spool to the correct processing pipeline.

```
Database: 369 SIGNATURE_GROUP entries
Table: SIGNATURE_GROUP (SIGNATURE_GROUP_ID, NAME, DESCRIPTION)

Key characteristic: NO foreign key relationship to any other table.
The mapping of which signatures belong to which group is configured
OUTSIDE the database (in IntelliSTOR admin UI / configuration files).
```

The SIGNATURE_GROUP determines which pool of SIGNATURE patterns to try when identifying the report. For example:
- `DEPOSITS_RD` serves ~871 report species (DDU017P, CDU100P, etc.)
- `MIDASPLUS_RPT` serves ~1,675 report species
- 754 species appear in multiple groups (different routing paths)

### 1.3 PAGINATOR_JOB - Processing Each Arrival

Each spool arrival creates a **PAGINATOR_JOB** record, tracked via `PAGINATOR_JOB_ID`. The job's attributes are stored as key-value pairs in **PAGINATOR_JOB_GEN_ATTR**:

| Attribute Key | Occurrence | Purpose |
|---------------|-----------|---------|
| `SIGNATURE GROUP` | 629,000 jobs | Routing label for pattern-matched reports |
| `REPORT DATE` | 48,000 jobs | Extracted report date |
| `REPORT NAME` | 25,000 jobs | For pre-identified reports (PDF/AFP) |
| `FORMDEF` | 16,000 jobs | AFP overlay definition |
| `SEPARATE_AS_GROUP` | 21,000 jobs | Parallel processing group |
| `MAX_SEP_CONNECTION` | 21,000 jobs | Max parallel connections |

**Two ingestion paths exist:**

1. **Pattern-matched** (majority): Spool arrives with only `SIGNATURE GROUP`. The paginator runs signature pattern matching to identify the report species, extract metadata, and build the index.

2. **Pre-identified** (PDF/AFP): Spool arrives with `REPORT NAME` and `REPORT DATE` already known. No pattern matching needed; the report species is already determined.

---

## 2. Signature Pattern Matching

### 2.1 SIGNATURE - Report Identification

The **SIGNATURE** table defines how to identify a report species from a raw spool file. Each signature contains LINE templates with patterns that match against spool file content.

```
SIGNATURE
  Keys: SIGNATURE_ID
  Data: REPORT_SPECIES_ID, STRUCTURE_DEF_ID
  Links to: LINE, FIELD (via STRUCTURE_DEF_ID)
```

The STRUCTURE_DEF_ID links to the field extraction rules:

```
LINE (STRUCTURE_DEF_ID, LINE_ID)
  - NAME: descriptive name (e.g., "Page Header", "Account Detail")
  - TEMPLATE: pattern string using A=alpha, 9=digit, ' '=space, '*'=literal

FIELD (STRUCTURE_DEF_ID, LINE_ID, FIELD_ID)
  - NAME: field name (e.g., "ACCOUNT_NO", "BRANCH")
  - START_COLUMN, END_COLUMN: column positions in the line
  - IS_INDEXED: 1 = values stored in MAP file for search
  - IS_SIGNIFICANT: 1 = values define section boundaries
```

### 2.2 SENSITIVE_FIELD - Metadata Extraction Rules

The **SENSITIVE_FIELD** table defines which fields in a signature extract which pieces of instance metadata. It links SIGNATURE to the specific LINE/FIELD positions that provide the report's identity.

```
SENSITIVE_FIELD
  Keys: SIGN_ID (= SIGNATURE_ID), LINE_ID, FIELD_ID
  Data: SENSITIVITY (encoded role identifier)
```

**SENSITIVITY encoding:**

| Value | Role | Description |
|-------|------|-------------|
| 0 | REPORT_NAME | Field extracts the report name (instance identity) |
| 2 | REPORT_DATE | Field extracts the report date (AS_OF_TIMESTAMP) |
| 4 (0x00004) | SECTION_FIELD_1 | First section-defining field |
| 65538 (0x10002) | SECTION_FIELD_2 | Second section-defining field |
| 131076 (0x20004) | SECTION_FIELD_3 | Third section-defining field (rare) |

**Encoding formula:** `high_word = ordinal (0-based)`, `low_word = role_type`
- Ordinal 0 + role 4 = 0x00004 = SECTION_FIELD_1
- Ordinal 1 + role 2 = 0x10002 = SECTION_FIELD_2

### 2.3 Impact on Instance Metadata

When the paginator processes a spool file, SENSITIVE_FIELD tells it:

1. **SENSITIVITY=0 field** -> Extract value -> becomes REPORT_NAME in REPORT_INSTANCE
2. **SENSITIVITY=2 field** -> Extract value -> becomes AS_OF_TIMESTAMP (report date)
3. **SENSITIVITY=4 field** -> Extract value -> becomes section key (SECTION.NAME)
4. **SENSITIVITY=65538 field** -> Extract value -> second part of composite section key

**Composite Section Keys:**

When a signature has BOTH sensitivity=4 AND sensitivity=65538, the extracted values are concatenated with a space separator to form the section name:

```
Example: "Token Welcome Letter Ctrl Report"
  SECTION_FIELD_1 (LINE=17): extracts branch code "501"
  SECTION_FIELD_2 (LINE=54): extracts sub-code "01"
  Combined SECTION.NAME = "501 01"
```

146 signatures in the database use composite section keys. The SECTION table stores the combined value (e.g., "501 01", "SG INB") as a single NAME string.

### 2.4 How Metadata Flows to Instance

```
Spool arrives
    |
    v
PAGINATOR reads spool lines, matches LINE.TEMPLATE patterns
    |
    v
For each matched line, extracts FIELD values at (START_COLUMN, END_COLUMN)
    |
    +-- SENSITIVE_FIELD(SENSITIVITY=0) -> Report Name
    +-- SENSITIVE_FIELD(SENSITIVITY=2) -> Report Date
    +-- SENSITIVE_FIELD(SENSITIVITY=4) -> Section Key Part 1
    +-- SENSITIVE_FIELD(SENSITIVITY=65538) -> Section Key Part 2
    +-- FIELD(IS_INDEXED=1) -> Stored in MAP file index
    +-- FIELD(IS_SIGNIFICANT=1) -> Section boundary marker
    |
    v
REPORT_INSTANCE created with:
  - DOMAIN_ID, REPORT_SPECIES_ID, AS_OF_TIMESTAMP (from SENSITIVITY 0 + 2)
  - STRUCTURE_DEF_ID (from SIGNATURE)
  - RPT_FILE_SIZE_KB, MAP_FILE_SIZE_KB
```

---

## 3. Instance Creation and Concatenation

### 3.1 INSTANCE_HANDLING Modes

Each REPORT_SPECIES has an `INSTANCE_HANDLING` attribute that determines how multiple spool arrivals for the same report date are processed:

| Value | Mode | Count | Behavior |
|-------|------|-------|----------|
| 1 | Keep Most Recent | 6,778 | Only latest arrival is kept |
| 2 | Keep All | 1 | Each arrival is a separate instance |
| 3 | Concatenate | 25,698 | Multiple arrivals stitched into one instance |

**Concatenation (value=3)** is by far the most common mode. When a report arrives in multiple spool chunks throughout the day (e.g., hourly branch extracts), they are concatenated into a single instance.

### 3.2 REPORT_INSTANCE_SEGMENT - Tracking Arrival Chunks

**Critical distinction: SEGMENT != SECTION**

| Concept | Definition | Scope |
|---------|-----------|-------|
| **SEGMENT** | Physical spool arrival chunk | Instance-level (one per arrival) |
| **SECTION** | Logical access-control grouping (by branch) | Species-level (shared across instances) |

There is **no database table** linking SEGMENT_NUMBER to SECTION_ID. They are completely independent concepts.

```
REPORT_INSTANCE_SEGMENT
  Keys: DOMAIN_ID, REPORT_SPECIES_ID, AS_OF_TIMESTAMP, SEGMENT_NUMBER
  Data: START_PAGE_NUMBER, NUMBER_OF_PAGES, PAGINATOR_JOB_ID
```

- `SEGMENT_NUMBER`: Sequential index (0, 1, 2, ...) of each spool arrival
- `START_PAGE_NUMBER`: Where this chunk's pages begin in the concatenated spool
- `NUMBER_OF_PAGES`: How many pages this chunk contributed
- `PAGINATOR_JOB_ID`: Which paginator job processed this chunk (audit trail)

**Example: PMSRTGSPDNGD (concatenated report, INSTANCE_HANDLING=3)**
```
17 segments arriving hourly throughout the day:
  Segment 0: PAGINATOR_JOB_ID=X, arrival 06:31, pages 1-15
  Segment 1: PAGINATOR_JOB_ID=Y, arrival 07:31, pages 16-28
  ...
  Segment 16: PAGINATOR_JOB_ID=Z, arrival 22:31, pages 240-255
```

Each segment has its own PAGINATOR_JOB_ID with `SIGNATURE GROUP` attribute in PAGINATOR_JOB_GEN_ATTR, providing a complete audit trail of when each chunk arrived and was processed.

### 3.3 One MAP File + One Spool File Per Instance

Regardless of how many segments (arrivals) an instance has, the final result is:

```
SST_STORAGE (DOMAIN_ID, REPORT_SPECIES_ID, AS_OF_TIMESTAMP)
  -> MAP_FILE_ID -> MAPFILE.FILENAME
  (No SEGMENT_NUMBER column - one MAP file for entire instance)

RPTFILE_INSTANCE (DOMAIN_ID, REPORT_SPECIES_ID, AS_OF_TIMESTAMP)
  -> RPT_FILE_ID -> RPTFILE.FILENAME
  (No SEGMENT_NUMBER column - one spool file for entire instance)
```

The concatenation process stitches all segment spool chunks into a single spool file and builds a single MAP file covering all pages across all segments.

### 3.4 Operational Audit Trail

The PAGINATOR_JOB system provides a complete operational history:

```
For any instance, the audit trail is:
  REPORT_INSTANCE_SEGMENT (SEGMENT_NUMBER, PAGINATOR_JOB_ID)
    -> PAGINATOR_JOB_GEN_ATTR (KEY_FIELD, VALUE_FIELD)
       - SIGNATURE GROUP: which routing path
       - REPORT NAME: identified report (if pre-identified)
       - REPORT DATE: extracted date
       - FORMDEF: AFP overlay used
```

This traces each piece of the concatenated spool back to its original arrival job, timing, and routing path. This is essential for diagnosing missing or incomplete reports.

---

## 4. Database Schema - Key Tables and Joins

```
REPORT_INSTANCE (DOMAIN_ID, REPORT_SPECIES_ID, AS_OF_TIMESTAMP)
  |  Data: STRUCTURE_DEF_ID, RPT_FILE_SIZE_KB, MAP_FILE_SIZE_KB
  |
  +-- SST_STORAGE -> MAPFILE (one MAP file per instance)
  +-- RPTFILE_INSTANCE -> RPTFILE (one spool file per instance)
  +-- REPORT_INSTANCE_SEGMENT (per-arrival chunks with page ranges)
  |     Data: SEGMENT_NUMBER, START_PAGE_NUMBER, NUMBER_OF_PAGES, PAGINATOR_JOB_ID
  |
  +-- via STRUCTURE_DEF_ID:
        LINE (STRUCTURE_DEF_ID, LINE_ID)
          Data: NAME, TEMPLATE
        FIELD (STRUCTURE_DEF_ID, LINE_ID, FIELD_ID)
          Data: NAME, START_COLUMN, END_COLUMN, IS_INDEXED, IS_SIGNIFICANT

SIGNATURE (SIGNATURE_ID)
  Data: REPORT_SPECIES_ID, STRUCTURE_DEF_ID
  +-- SENSITIVE_FIELD (SIGN_ID, LINE_ID, FIELD_ID)
        Data: SENSITIVITY

SECTION (DOMAIN_ID, REPORT_SPECIES_ID, SECTION_ID)
  Data: NAME (section value, e.g., "501", "501 01")
  +-- STYPE_SECTION (REPORT_SPECIES_ID, SECTION_ID)
        Data: VALUE (Windows Security Descriptor / ACL binary)

SIGNATURE_GROUP (SIGNATURE_GROUP_ID)
  Data: NAME, DESCRIPTION
  (No FK to SIGNATURE, REPORT_SPECIES, or any other table)

PAGINATOR_JOB_GEN_ATTR (PAGINATOR_JOB_ID, KEY_FIELD)
  Data: VALUE_FIELD
```

---

## 5. Spool File Format and Fast Page Access

### 5.1 Format Detection

```
ASA Carriage Control: first character of each line is control char
  '1' at start of line = new page
  Lines terminated by CRLF (0x0D 0x0A)

Form Feed: pages separated by 0x0C byte
```

### 5.2 Fast Page Access Strategy

For large spool files (up to 3GB with 300K+ pages):

```
1. BUILD PAGE OFFSET INDEX (on first access):
   For ASA: scan for lines starting with '1', record byte offsets
   For FF:  scan for 0x0C positions

2. SEEK TO PAGE N: file.seek(page_offsets[N-1])

3. PERFORMANCE:
   3GB file, 300K pages:
   - Index build: ~1-2 seconds
   - Index memory: ~1.2MB (4 bytes x 300K)
   - Page seek: instant
```

---

## 6. MAP File Binary Structure

### 6.1 Header (bytes 0-89)

```
Offset  Size   Description
0-11    12B    "MAPHDR" (UTF-16LE signature: 4D 00 41 00 50 00 48 00 44 00 52 00)
12-17   6B     Unknown/padding
18-19   2B     Segment count (number of **ME markers)
20-31   12B    Unknown
32-51   20B    Date string 1 (UTF-16LE: "01/01/2025")
52-71   20B    Date string 2 (UTF-16LE)
72-83   12B    Unknown
84-89   6B     Padding to first **ME marker
```

### 6.2 Segment Structure

Each segment starts with a **ME marker: `0x2a002a004d004500` (UTF-16LE for "**ME")

```
Segment Header (offset from **ME marker):
+0-7    8B     **ME marker
+8-11   4B     Header constant (0x008e0000)
+12-15  4B     Segment index (0, 1, 2, ...)
+16-19  4B     Offset to next **ME marker (absolute file position)
+20-23  4B     Unknown/flags

Segment Metadata (offset +24 from **ME):
+24-25  2B     Starting page number
+26-27  2B     LINE_ID
+28-29  2B     Unknown/reserved
+30-31  2B     FIELD_ID
+32-33  2B     Unknown/reserved
+34-35  2B     Field width in characters
+36-37  2B     Unknown/reserved
+38-39  2B     Entry count (from header; may not reflect actual count)
+40+    var    Additional metadata, then index entry data
```

### 6.3 Segment 0: Page-Level Master Index

Segment 0 has a different structure depending on the MAP file complexity.

#### A. Small MAP Files: Field-to-Segment Lookup Table

In small MAP files (multiple **ME segments for different indexed fields), Segment 0 contains a lookup table mapping (LINE_ID, FIELD_ID) combinations to their segment numbers:

```
Entry format: 4 bytes each
[SEG_NUM:1][LINE_ID:1][FIELD_ID:1][FLAGS:1]

Example (25001002.MAP, STRUCTURE_DEF_ID 9643):
  SEG=1, LINE_ID=4, FIELD_ID=2  -> Product field (width=55)
  SEG=2, LINE_ID=5, FIELD_ID=3  -> Reference_ID (width=18)
  SEG=3, LINE_ID=5, FIELD_ID=6  -> Value_date (width=4)
  SEG=4, LINE_ID=6, FIELD_ID=3  -> Amount field (width=4)
  ...up to SEG=8
```

#### B. Large MAP Files: 15-Byte Record Array (Page-Level Index)

In large MAP files (like 2511109P.MAP for DDU017P), Segment 0 contains a **flat array of 15-byte fixed-size records** — one record per field occurrence on every page of the spool file. This is NOT a section-to-page-range table.

```
Record format: 15 bytes each
[row_position:1][type:1][pad:1][record_id:4][flag:4][page_number:4]

Fields:
  row_position: Line/row position within the page
                Odd numbers 11, 13, 15, ..., 59 = up to 25 data rows per page
                Stride of 2, starting from 11

  type:         Record type byte
                0x03 = header/init (first record only)
                0x08 = data record (one per field occurrence)
                0x0c = companion/separator record

  record_id:    uint32, unique sequential ID for this record
                Used as JOIN KEY from Segment 1 entries

  flag:         uint32, always 1 for type 0x08 records

  page_number:  uint32, page number in the spool file (1-based)
                HIGH BIT (0x80000000): branch/section boundary flag
                When set, indicates a new branch starts on this page
```

**Example: 2511109P.MAP (DDU017P)**
```
Segment 0 size: 2,446,469 bytes
Total records: 163,084 (81,542 type-0x08 data + 81,542 type-0x0c separators)
Pages covered: 3,297 (matching spool file page count)
Records per page: ~25 (one per data row on the page)

Record example:
  row=11, type=0x08, record_id=136653, flag=1, page=2748
  -> Row 11 on page 2748, addressable via record_id 136653
```

#### C. How Segment 0 + Segment 1 Work Together

Segment 1 is the sorted field-value index (e.g., account numbers). Each Segment 1 entry contains a u32 value that is a **direct pointer** (join key) into Segment 0's record_id field:

```
SEARCH FLOW:
  Segment 1 entry: value="200-044295-001", u32=136653
                                              |
                                              v
  Segment 0 record: record_id=136653, page=2748, row=11
                                              |
                                              v
  Spool file: seek to page 2748, row 11

Verified: account "200-044295-001" has 484 Segment 1 entries
  -> pointing to 21 unique pages (pages 117-136 + page 3295)
```

#### D. Branch/Section Boundaries in Segment 0

Segment 0 encodes branch boundaries via a **high-bit flag** on the page_number field:

```
page_number & 0x7FFFFFFF = actual page number
page_number & 0x80000000 = branch boundary flag (1 = new branch starts here)
```

However, this is only a secondary marker. The authoritative section-to-page mapping is stored in the **RPT file**, not the MAP file (see Section 7.4).

### 6.4 Segments 1+: Field Search Indices (IS_INDEXED fields)

Each segment beyond Segment 0 contains the search index for one IS_INDEXED field. The segment metadata identifies which LINE_ID/FIELD_ID the segment covers.

### 6.5 Index Entry Format - Dual Format Detection

**Critical discovery:** MAP files use two different entry formats depending on file size/complexity:

#### Format A: Direct Page Reference (Small Files)

```
[length:2][value:N][page:2][flags:3]
Total entry size = 7 + field_width

length:  uint16, usually equals field_width
value:   ASCII text, space-padded to field_width
page:    uint16, direct page number in spool file
flags:   3 bytes, usually 0x00 0x00 0x00

Example (25001002.MAP, Reference_ID width=18):
  00 12                    Length = 18
  45 50 32 34 31 32 33 31  'EP241231'
  30 39 30 33 39 34 39 39  '09039499'
  20 20                    '  ' (padding)
  02 00                    Page = 2
  00 00 00                 Flags
  -> Value 'EP24123109039499' on PAGE 2
```

#### Format B: Line-Occurrence Index (Large Files)

```
[length:2][value:N][u32_index:4][last:1]
Total entry size = 7 + field_width

length:    uint16, usually equals field_width
value:     ASCII text, space-padded to field_width
u32_index: uint32, line-occurrence index (NOT a page number)
last:      1 byte, end-of-entry marker

Formula: (u32_index - 1) / 2 = 0-based index into sequential
         occurrences of this LINE_ID in the spool file

Example (2511109P.MAP, ACCOUNT_NO width=14):
  0E 00                    Length = 14
  32 30 30 2D 30 34 34 32  '200-0442'
  39 35 2D 30 30 31 20 20  '95-001  '
  CD 15 02 00              u32_index = 0x000215CD = 136,653
  00                       Last marker
  -> (136653 - 1) / 2 = 68,326th occurrence of LINE 8
```

#### Format Detection Heuristic

The parser reads the first 100 entries and checks if ALL 2-byte values at the page position are odd numbers. If they are all odd, the format is u32_index (Format B) because the uint16 is actually the lower 2 bytes of a uint32 where the formula `(val-1)/2` requires odd values. Otherwise, the format is direct page (Format A).

### 6.6 Dynamic Data Offset

The offset from the **ME marker to the first index entry is NOT fixed:

```
Small files (25001002.MAP): data_offset = me_pos + 0xCD (205 bytes)
Large files (2511109P.MAP): data_offset = me_pos + 0xCF (207 bytes)
```

The parser dynamically finds the data offset by searching for the first length indicator that equals the field_width in the range [me_pos + 0xC0, me_pos + 0xE0], with validation that the following bytes are printable text.

### 6.7 Entry Count vs Actual Entries

The entry_count in the segment header may not reflect the actual number of entries. For large MAP files:

```
2511109P.MAP Segment 1:
  Header entry_count = 13
  Actual entries = 81,541

The parser reads ALL entries until reaching the next segment or EOF,
rather than trusting the header count.
```

---

## 7. Section Segregation (Permission-Based Viewing)

### 7.1 SECTION and STYPE_SECTION

```
SECTION (DOMAIN_ID, REPORT_SPECIES_ID, SECTION_ID)
  NAME: the section value (e.g., "501", "501 01", "SG INB")
  This is a master list, shared across ALL instances of a report species.

STYPE_SECTION (REPORT_SPECIES_ID, SECTION_ID)
  VALUE: Windows Security Descriptor (binary ACL)
  Determines which users/groups can view this section.
```

### 7.2 Section Key Construction from SENSITIVE_FIELD

The section name in the SECTION table is constructed from the SENSITIVE_FIELD roles:

```
Single section field (most reports):
  SENSITIVITY=4 -> field value = SECTION.NAME
  Example: DDU017P branch "501" -> SECTION.NAME = "501"

Composite section fields (146 signatures):
  SENSITIVITY=4     -> field value = first part
  SENSITIVITY=65538 -> field value = second part
  Combined: "part1 part2" = SECTION.NAME
  Example: "501" + "01" -> SECTION.NAME = "501 01"
```

### 7.3 Section Segregation Workflow - Two-Phase Lookup

The section segregation process uses a **two-phase lookup** where SECTION_ID serves both phases:

- **Phase 1**: SECTION_ID for permission check (via STYPE_SECTION ACL)
- **Phase 2**: SECTION_ID for page range lookup (via RPT file SECTIONHDR)

```
PHASE 1: Permission Check (database)
──────────────────────────────────────
1. User requests report instance (DOMAIN_ID, REPORT_SPECIES_ID, AS_OF_TIMESTAMP)
2. Get user's Windows SID
3. Query STYPE_SECTION for this REPORT_SPECIES_ID
4. Parse Windows ACL in VALUE column to get list of allowed SECTION_IDs
5. If user can see ALL sections -> return full spool, done

PHASE 2: Page Resolution (RPT file SECTIONHDR)
────────────────────────────────────────────────
6. Open RPT file, read SECTIONHDR structure
7. For each allowed SECTION_ID:
   a. Find matching triplet: (SECTION_ID, START_PAGE, PAGE_COUNT)
   b. Page range = START_PAGE to START_PAGE + PAGE_COUNT - 1
8. Build union of all allowed page ranges
9. Extract those pages from spool file
10. Return segregated content

Example: User has permission for SECTION_ID=14259 ("501") and SECTION_ID=124525 ("201")
  Phase 1: ACL check confirms user can see these SECTION_IDs
  Phase 2: RPT SECTIONHDR lookup:
           SECTION_ID 14259  -> START_PAGE=890, PAGE_COUNT=2204
           SECTION_ID 124525 -> START_PAGE=1, PAGE_COUNT=111
           Return pages 1-111 and 890-3093 from spool file
```

**Key insight:** The SECTION_ID is used in BOTH phases — permissions AND page lookup. No text-name matching is needed. The RPT file stores SECTION_IDs as uint32 values that directly join to the SECTION and STYPE_SECTION database tables.

### 7.4 RPT File Format - Complete Binary Structure

The RPT file is a **structured binary container** that stores the report content as per-page zlib-compressed streams, plus metadata tables for sections and page offsets. It is NOT the raw spool file — it is IntelliSTOR's processed/compressed version.

```
RPT File Layout (verified: 251110OD.RPT, 2,107,836 bytes):

[0x000] RPTFILEHDR        "RPTFILEHDR\t0001:1346\t2025/04/16 15:53:07.470"
                           Contains: domain:species_id, timestamp (tab-separated ASCII)
                           Padded with 0x1A + nulls to 0xC0

[0x0C0] File Descriptor    Flags, self-references (32 bytes)
[0x0D4] ENDHDR             End of file header marker

[0x0E0] Content Directory   uint32 rptinsthdr_offset
                            uint32 compressed_data_end

[0x0F0] RPTINSTHDR         DOMAIN_ID=1, REPORT_SPECIES_ID=1346, timestamps
                           Instance-level metadata
[0x1C0] ENDHDR             End of instance header

[0x1D0] Table Directory     uint32 page_count (3,297)
                            uint32 section_count (36)
                            uint32 section_data_offset (-> SECTIONHDR)
                            uint32 page_table_offset (-> PAGETBLHDR)

[0x200] COMPRESSED DATA    3,297 individual zlib streams
        ...                Each page independently compressed (zlib, header 0x78 0x01)
                           ~2MB total (10.2x compression ratio from 20.6MB spool)

[0x1EF2C8] SECTIONHDR     "SECTIONHDR" marker + section triplets
                           36 x 12-byte triplets: (SECTION_ID, START_PAGE, PAGE_COUNT)
[0x1EF485] ENDDATA         End of section data

[0x1EF48E] PAGETBLHDR      "PAGETBLHDR" marker + page descriptors
                            3,297 x 24-byte entries (per-page metadata)
[0x2029B3] ENDDATA          End of page table
[0x2029BC] EOF              (2,107,836 bytes total)
```

### 7.5 SECTIONHDR - Section-to-Page Mapping

The SECTIONHDR can be read **without decompressing any page data**. Just seek to the section_data_offset from the Table Directory.

```
Marker: "SECTIONHDR" + 3 null bytes (13 bytes total)
Data: Array of 12-byte triplets (all little-endian uint32):
  [SECTION_ID:4][START_PAGE:4][PAGE_COUNT:4]

Example: DDU017P (251110OD.RPT)
  36 triplets = 36 branches = 3,297 total pages
  SECTION_ID=124525, START_PAGE=1,   PAGE_COUNT=111  -> branch "201"
  SECTION_ID=14259,  START_PAGE=890, PAGE_COUNT=2204 -> branch "501"
  ...

SECTION_IDs directly match the SECTION table in the database:
  SECTION(SECTION_ID=124525) -> NAME="201"
  SECTION(SECTION_ID=14259)  -> NAME="501"
```

### 7.6 PAGETBLHDR - Page Table (Per-Page Metadata)

The PAGETBLHDR provides per-page offsets and sizes for random access into the compressed data:

```
Marker: "PAGETBLHDR" + null bytes
Entry format: 24 bytes per page (little-endian):
  [page_offset:4][pad:4][line_width:2][lines_per_page:2][uncompressed_size:4][compressed_size:4][pad:4]

  page_offset:       Byte offset relative to RPTINSTHDR (add 0xF0 for absolute)
  line_width:        Max characters per line in this page
  lines_per_page:    Number of lines on this page
  uncompressed_size: Decompressed page data size in bytes
  compressed_size:   zlib stream size in bytes
```

### 7.7 Per-Page Compression

Each page is independently compressed using standard **zlib** (RFC 1950, compression level 1, header `0x78 0x01`). Python's `zlib.decompress()` works directly.

**Decompressed page format** (differs from raw spool):
- ASA carriage control column 1 **stripped** ('1', ' ', '0', '-' removed)
- ASA '0' (double-space) interpreted as an inserted blank line
- Lines separated by CRLF (`\r\n`)
- Form Feed (`\x0c`) appended at end of page

**Compression ratio:** ~10x (DDU017P: 20.6MB spool → 2.0MB RPT)

### 7.8 Key Implications

1. **SECTIONHDR is trivially extractable** — seek to offset, read triplets, done. No decompression needed.
2. **Page content is extractable** — standard zlib per page, with page table providing offsets.
3. **RPT file is self-contained** — contains everything needed for both section segregation AND page content delivery.
4. **RPT file replaces the raw spool** — IntelliSTOR stores the RPT file, not the raw spool. The raw spool (`S94752001749_20250416`) is the ingestion input; the RPT file (`251110OD.RPT`) is the stored output.

**Why RPT file and not MAP file for sections?**

The MAP file's role is field-value search (IS_INDEXED fields like ACCOUNT_NO). Section segregation is a separate concern — it's about which pages belong to which branch for permission-based viewing. The RPT file's SECTIONHDR provides a direct, efficient lookup: SECTION_ID → (START_PAGE, PAGE_COUNT). No text matching, no MAP parsing needed.

---

## 8. Index Search Workflow

```
1. User searches: "ACCOUNT_NO = 200-044295-001"

2. Get MAP file:
   REPORT_INSTANCE -> SST_STORAGE -> MAPFILE -> read binary .MAP

3. Get field definition:
   STRUCTURE_DEF_ID -> FIELD (WHERE IS_INDEXED=1 AND NAME='ACCOUNT_NO')
   -> Get LINE_ID, FIELD_ID, field_width

4. Find segment in MAP:
   Read Segment 0 lookup table -> find segment for (LINE_ID, FIELD_ID)

5. Search index entries in target segment:
   For each entry:
     if entry.value matches search_value:
       if format == 'page': -> direct page number
       if format == 'u32_index': -> resolve via line-occurrence formula

6. Extract matching pages from spool file
```

---

## 9. Complete Data Flow Summary

```
SPOOL ARRIVES
  |
  v
SIGNATURE_GROUP (routing label, no DB FK)
  - Configured outside database
  - Routes spool to correct processing pool
  |
  v
PAGINATOR_JOB created
  - PAGINATOR_JOB_GEN_ATTR stores: SIGNATURE GROUP, REPORT NAME, REPORT DATE, FORMDEF
  |
  v
SIGNATURE pattern matching (or pre-identified)
  - SIGNATURE.STRUCTURE_DEF_ID -> LINE.TEMPLATE -> match spool lines
  - SENSITIVE_FIELD extracts:
      SENSITIVITY=0 -> Report Name (identity)
      SENSITIVITY=2 -> Report Date (AS_OF_TIMESTAMP)
      SENSITIVITY=4 -> Section Key Part 1
      SENSITIVITY=65538 -> Section Key Part 2 (composite)
  - IS_INDEXED fields -> values stored in MAP file (for field-value search)
  - IS_SIGNIFICANT fields -> section boundaries stored in RPT file SECTIONHDR
  |
  v
REPORT_INSTANCE created (or appended if INSTANCE_HANDLING=3)
  - One MAP file (field search index) + one spool/RPT file (content + SECTIONHDR) per instance
  - REPORT_INSTANCE_SEGMENT tracks each arrival chunk:
      SEGMENT_NUMBER, START_PAGE_NUMBER, NUMBER_OF_PAGES, PAGINATOR_JOB_ID
  |
  v
TWO OUTPUT FILES per instance:

  RPT FILE contains:
    - Spool/report content (pages of print data)
    - SECTIONHDR: array of (SECTION_ID, START_PAGE, PAGE_COUNT) triplets
      Direct lookup: SECTION_ID -> page range (for section segregation)

  MAP FILE contains:
    - Segment 0: Page-level master index (15-byte records: record_id + page + row)
    - Segment 1+: Sorted field value index (account numbers, etc.)
      Each entry's u32 is a join key into Segment 0 -> resolves to page + row
    - Purpose: field-value SEARCH only (IS_INDEXED fields)
  |
  v
ACCESS CONTROL (section segregation):
  STYPE_SECTION (ACL) -> permission check via SECTION_ID
  RPT file SECTIONHDR -> SECTION_ID -> (START_PAGE, PAGE_COUNT)
  No MAP file involvement. No text matching needed.
  Composite section keys from SENSITIVITY 4 + 65538

SEARCH (field-value lookup):
  MAP Segment 1: search sorted entries for field value (e.g., account number)
  -> follow u32 join key to Segment 0 record -> get page number + row position
  -> extract matching pages from spool file
```

---

## 10. Key Statistics (OCBC Production)

```
Total report species:          32,477
  INSTANCE_HANDLING=1 (Keep Recent): 6,778
  INSTANCE_HANDLING=2 (Keep All):        1
  INSTANCE_HANDLING=3 (Concatenate): 25,698

Signature groups:              369
Paginator jobs with SIGNATURE GROUP: 629,000
Paginator jobs pre-identified:       25,000
Signatures with composite sections:  146

Largest spool files:           ~3 GB (300K+ pages)
Largest MAP files:             ~4 MB (80K+ entries)
```

---

## 11. Migration Considerations

### 11.1 Paginator History as Operational Audit Trail

The PAGINATOR_JOB and PAGINATOR_JOB_GEN_ATTR tables provide a critical operational audit trail:

- **When** each spool chunk arrived (PAGINATOR_JOB timestamps)
- **How** it was routed (SIGNATURE GROUP attribute)
- **What** was identified (REPORT NAME, REPORT DATE)
- **Which** instance segment it became (via REPORT_INSTANCE_SEGMENT.PAGINATOR_JOB_ID)

This audit trail is essential for diagnosing missing or incomplete reports: if a branch's daily extract fails to arrive, the absence of a PAGINATOR_JOB for that expected time window is the evidence.

### 11.2 MAP File Values Are Plain Text (Not Compressed or Hashed)

Verified by hex inspection: MAP file index entries store field values as **plain ASCII text**, space-padded to the field width. There is no compression, hashing, or encoding beyond plain ASCII.

```
Evidence from 2511109P.MAP (81,541 entries, field_width=14):
  Entry hex: 3131332d3030303634302d303031 = "113-000640-001"
  Entry hex: 3230302d3034343239352d303031 = "200-044295-001"

Every byte maps 1:1 to a printable ASCII character.
No dictionary encoding, no hash table, no compression.
```

This means the MAP file is a straightforward flat index that can be directly converted to database rows without any decompression or decoding step. Each entry is simply: `(value_text, page_or_line_reference)`.

### 11.3 What Must Be Migrated

| Component | Migration Approach |
|-----------|-------------------|
| Spool files | Copy binary files; preserve ASA/FF format |
| MAP files | Re-generate or convert (format-dependent) |
| REPORT_INSTANCE | Recreate with same keys |
| REPORT_INSTANCE_SEGMENT | Migrate page ranges per arrival chunk |
| SECTION + STYPE_SECTION | Migrate section names and ACLs |
| LINE + FIELD definitions | Migrate structure definitions |
| SIGNATURE + SENSITIVE_FIELD | Migrate pattern matching rules |
| PAGINATOR_JOB history | Migrate for audit trail continuity |

---

## 12. New Solution Design: Replacing MAP Files with Database Tables

### 12.1 Rationale

The migration requires two capabilities:
1. **Section segregation** — Given a SECTION_ID, find start page and page count
2. **Account search** — Given an account number, find which pages contain it (future phase)

With the RPT file format fully decoded (Section 7.4-7.8), we now know:
- **Section data** is in the RPT file SECTIONHDR — trivially extractable (no decompression)
- **Page content** is in the RPT file as per-page zlib streams — standard decompression
- **Account index** is in the MAP file Segment 0+1 — extractable as plain ASCII text
- **The RPT file is self-contained** — it has sections, page table, AND compressed page content

For the new solution, section data can be extracted from RPT files into a database table at migration time. Account index data can be extracted from MAP files as a separate (future) step. Both eliminate the need to parse binary files at query time.

### 12.2 Proposed Table Design

#### A. INSTANCE_SECTION — Replaces MAP Segment 0 Section Index

```sql
CREATE TABLE INSTANCE_SECTION (
    DOMAIN_ID           INT NOT NULL,
    REPORT_SPECIES_ID   INT NOT NULL,
    AS_OF_TIMESTAMP     DATETIME NOT NULL,
    SECTION_ID          INT NOT NULL,          -- FK to SECTION table
    START_PAGE          INT NOT NULL,
    NUMBER_OF_PAGES     INT NOT NULL,
    PRIMARY KEY (DOMAIN_ID, REPORT_SPECIES_ID, AS_OF_TIMESTAMP, SECTION_ID)
);
```

**Key design choice:** Use `SECTION_ID` (not the text name) as the key. This directly mirrors the RPT file's SECTIONHDR format, which already stores SECTION_IDs as uint32 values:
- During migration, we read the RPT file's SECTIONHDR triplets: (SECTION_ID, START_PAGE, PAGE_COUNT)
- Each triplet maps 1:1 to an INSTANCE_SECTION row — no text matching or resolution needed
- The SECTION_ID directly joins to SECTION (for name) and STYPE_SECTION (for permissions)
- If a new SECTION_ID is found (not yet in SECTION table), we INSERT it

**Advantage:** Permission check and page lookup collapse into a single query:

```sql
-- Old approach: Phase 1 (ACL check) then Phase 2 (parse MAP binary for page ranges)
-- New approach: Single query combining permission check and page lookup

SELECT s.NAME, isec.START_PAGE, isec.NUMBER_OF_PAGES
FROM INSTANCE_SECTION isec
JOIN SECTION s ON s.DOMAIN_ID = isec.DOMAIN_ID
              AND s.REPORT_SPECIES_ID = isec.REPORT_SPECIES_ID
              AND s.SECTION_ID = isec.SECTION_ID
JOIN STYPE_SECTION st ON st.REPORT_SPECIES_ID = isec.REPORT_SPECIES_ID
                      AND st.SECTION_ID = isec.SECTION_ID
WHERE isec.DOMAIN_ID = @domain
  AND isec.REPORT_SPECIES_ID = @species
  AND isec.AS_OF_TIMESTAMP = @timestamp
  AND dbo.CheckACL(st.VALUE, @user_sid) = 1  -- permission check
ORDER BY isec.START_PAGE;
```

#### B. INSTANCE_ACCOUNT_INDEX — Replaces MAP Segment 1+ Search Index

```sql
CREATE TABLE INSTANCE_ACCOUNT_INDEX (
    DOMAIN_ID           INT NOT NULL,
    REPORT_SPECIES_ID   INT NOT NULL,
    AS_OF_TIMESTAMP     DATETIME NOT NULL,
    ACCOUNT_NO          VARCHAR(20) NOT NULL,  -- plain text, not encoded
    PAGE_NUMBER         INT NOT NULL,          -- resolved page (not u32_index)
    PRIMARY KEY (DOMAIN_ID, REPORT_SPECIES_ID, AS_OF_TIMESTAMP, ACCOUNT_NO, PAGE_NUMBER)
);

-- Search index for fast account lookup
CREATE INDEX IX_ACCOUNT_LOOKUP
ON INSTANCE_ACCOUNT_INDEX (ACCOUNT_NO, DOMAIN_ID, REPORT_SPECIES_ID, AS_OF_TIMESTAMP);
```

**Key design choice:** Store resolved `PAGE_NUMBER`, not the raw u32 join key from large MAP files. During migration, the u32 value is resolved to a page number via the Segment 0 record lookup (see Section 12.7). This eliminates the need to understand dual entry formats at query time.

**Query example:**

```sql
-- Find all pages in a specific instance containing account 200-044295-001
SELECT PAGE_NUMBER
FROM INSTANCE_ACCOUNT_INDEX
WHERE DOMAIN_ID = @domain
  AND REPORT_SPECIES_ID = @species
  AND AS_OF_TIMESTAMP = @timestamp
  AND ACCOUNT_NO = '200-044295-001'
ORDER BY PAGE_NUMBER;

-- Cross-instance search: find all instances containing an account
SELECT ri.REPORT_SPECIES_ID, rs.REPORT_NAME, ia.AS_OF_TIMESTAMP, ia.PAGE_NUMBER
FROM INSTANCE_ACCOUNT_INDEX ia
JOIN REPORT_INSTANCE ri ON ri.DOMAIN_ID = ia.DOMAIN_ID
                       AND ri.REPORT_SPECIES_ID = ia.REPORT_SPECIES_ID
                       AND ri.AS_OF_TIMESTAMP = ia.AS_OF_TIMESTAMP
JOIN REPORT_SPECIES rs ON rs.REPORT_SPECIES_ID = ia.REPORT_SPECIES_ID
WHERE ia.ACCOUNT_NO = '200-044295-001'
ORDER BY ia.AS_OF_TIMESTAMP DESC;
```

### 12.3 Migration ETL: RPT + MAP Files to Database Tables

```
For each REPORT_INSTANCE:

  A. SECTION SEGREGATION (from RPT file — simple and direct):
     1. Open RPT file, find SECTIONHDR marker
     2. Read array of 12-byte triplets: (SECTION_ID, START_PAGE, PAGE_COUNT)
     3. For each triplet:
        - Verify SECTION_ID exists in SECTION table (INSERT if new)
        - INSERT into INSTANCE_SECTION (SECTION_ID, START_PAGE, PAGE_COUNT)
     Done. No MAP file, no text matching, no field definitions needed.

  B. ACCOUNT INDEX (from MAP file — for field-value search):
     1. Read MAP file (binary)
     2. Parse Segment 0 (15-byte records for large files):
        a. Read all type-0x08 records: (record_id, page_number, row_position)
        b. Build lookup dict: record_id -> page_number
     3. Parse Segment 1 (sorted field value index):
        a. For each index entry:
           - Extract field value (plain ASCII text, e.g., account number)
           - Read u32 join key
           - Resolve page: lookup record_id in Segment 0 dict -> page_number
           - INSERT into INSTANCE_ACCOUNT_INDEX (value, page_number)

     Note: For small MAP files (direct page format), step 2-3 simplify:
     the u32 value in Segment 1 entries IS the page number directly.
```

### 12.4 What This Eliminates

| IntelliSTOR Component | New Solution | Why Not Needed |
|----------------------|-------------|----------------|
| MAP binary files | INSTANCE_SECTION + INSTANCE_ACCOUNT_INDEX tables | Data extracted to DB at migration time |
| SST_STORAGE / MAPFILE | Not needed | No more binary MAP files to reference |
| Segment 0 lookup table | Not needed | No LINE_ID/FIELD_ID segment directory needed |
| Dual entry format detection | Not needed | Page numbers resolved at migration time |
| Dynamic data offset probing | Not needed | No binary parsing at query time |
| LINE / FIELD definitions | Not needed for query | Only needed during one-time migration ETL |
| SIGNATURE / SENSITIVE_FIELD | Not needed for query | Only needed during one-time migration ETL |
| STRUCTURE_DEF_ID | Not needed for query | Only needed during one-time migration ETL |

### 12.5 What Must Still Be Maintained

| Component | Reason |
|-----------|--------|
| SECTION table | Master list of sections per species; new sections may appear in future instances |
| STYPE_SECTION | ACL permissions per section — must be migrated and maintained |
| REPORT_INSTANCE | Core instance identity (species + date) |
| REPORT_INSTANCE_SEGMENT | Audit trail for concatenated arrivals |
| Spool files | Still needed for page content extraction |
| Page offset index | For fast seek into spool files; could be pre-built during migration |

### 12.6 Volume Estimates

```
INSTANCE_SECTION:
  Avg sections per instance: ~30-50 (branches)
  Per instance: ~50 rows x ~30 bytes = ~1.5 KB
  1,000 instances: ~1.5 MB
  Very manageable.

INSTANCE_ACCOUNT_INDEX:
  DDU017P example: 81,541 entries for one instance
  Per entry: ~50 bytes (keys + account_no + page)
  Per instance: 81,541 x 50 = ~4 MB
  1,000 instances: ~4 GB
  Large but manageable with proper indexing.

  Note: Many reports will have far fewer entries.
  Reports without IS_INDEXED account fields: 0 rows.
```

### 12.7 u32 Join Key Resolution Strategy

For large MAP files (Format B), the u32 value in Segment 1 entries is a **join key** (record_id) into Segment 0's type-0x08 record array, NOT a line-occurrence index.

**Resolution approach:**
```
1. Parse Segment 0: build dict of record_id -> (page_number, row_position)
   - Read all 15-byte records
   - For type 0x08: key = U32@3 (record_id), value = U32@11 & 0x7FFFFFFF (page)
   - ~81K records for DDU017P, fits easily in memory

2. Parse Segment 1: for each entry, resolve u32 via the dict
   - u32 -> dict lookup -> page_number (instant, no spool scanning needed)

3. Store resolved page_number in INSTANCE_ACCOUNT_INDEX
```

**No spool file scanning required.** The page resolution is entirely within the MAP file itself — Segment 0 is the page-level master index, and Segment 1 entries point into it. This makes the migration ETL simple and fast.

**Note on the earlier (u32-1)/2 formula:** This formula was derived from pattern observation and produces the correct line-occurrence index as a secondary reference. However, the primary resolution path is the Segment 0 join, which directly provides the page number without needing to scan the spool file.
