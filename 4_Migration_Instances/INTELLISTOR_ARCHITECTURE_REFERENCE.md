# IntelliSTOR Architecture Reference
## Sections, Indexing, and Extraction — How They Work Together

---

## Overview

IntelliSTOR uses three independent but integrated systems to store, secure, and retrieve report data:

| System | Purpose | Data Source | Scope |
|--------|---------|-------------|-------|
| **Section Security** | Access control — who sees which pages | RPT SECTIONHDR + STYPE_SECTION ACL | Page ranges |
| **MAP File Indexing** | Search — find pages containing a value | MAP file binary segments | Whole report |
| **Extraction Patterns** | Structure — extract field values from text | LINE templates + FIELD positions | Per line |

---

## 1. Section Security (STYPE)

### How a User Gets Access to Pages

When a user opens a report instance (e.g. DDU017P from 2025-04-21):

**Phase 1 — Database permission check:**
- The system reads the user's Windows SID
- It checks `STYPE_SECTION` table for that `REPORT_SPECIES_ID` — each `SECTION_ID` has an ACL (binary Windows Security Descriptor) in the `VALUE` column
- Result: a list of `SECTION_ID`s the user is allowed to see

**Phase 2 — RPT file page mapping:**
- Open the RPT file, read the `SECTIONHDR` binary block
- Each entry is a 12-byte triplet: `(SECTION_ID, START_PAGE, PAGE_COUNT)`
- For each allowed SECTION_ID, get the page range
- Build the union of all allowed page ranges → those are the pages the user can see

**Result:** Different users see different pages of the same report, based on which sections (branches) they're authorized for.

### Section Names — How They Are Created

Section names come from report content during ingestion via `SENSITIVE_FIELD`:

```
SENSITIVE_FIELD.SENSITIVITY encoding:
  SENSITIVITY = 4      → First section field (e.g., branch code "501")
  SENSITIVITY = 65538  → Second section field (e.g., sub-code "01")
  Combined: "501" + " " + "01" = SECTION.NAME = "501 01"
```

### Tables Involved

```
SECTION (DOMAIN_ID, REPORT_SPECIES_ID, SECTION_ID, NAME)
    ↓
STYPE_SECTION (REPORT_SPECIES_ID, SECTION_ID, VALUE = ACL binary)
    ↓
RPT file SECTIONHDR (12-byte triplets: SECTION_ID, START_PAGE, PAGE_COUNT)
    ↓
Page ranges for permission-based access
```

---

## 2. MAP File Indexing — How Field Search Works

### What MAP Files Are

MAP files are **binary field-value search indices** (UTF-16LE encoded) that enable fast lookup:
- User queries: "ACCOUNT_NO = '200-044295-001'"
- MAP file returns: page numbers containing that value

They are **NOT** section/segment definitions — that's RPT SECTIONHDR.

### MAP File Binary Structure

```
MAPHDR (header, 24 bytes)
├── Signature: "MAPHDR" (UTF-16LE)
├── Bytes 18-19: Segment count
└── Date metadata

Segment 0: Directory/Lookup Table
├── Small files: (LINE_ID, FIELD_ID) → segment number mapping (4-byte entries)
└── Large files: 15-byte page-level records with record_id, page_number, flags

Segments 1-N: Sorted field-value index entries (one per IS_INDEXED field)
├── Entry format: [length:2][value:N][u32_index:4][last:1]
├── Values are SORTED for binary search
└── u32_index joins back to Segment 0 for page resolution
```

### How ACCOUNT_NO Search Works (Step by Step)

1. **Get field metadata from database**
   ```sql
   SELECT LINE_ID, FIELD_ID FROM FIELD
   WHERE NAME = 'ACCOUNT_NO' AND IS_INDEXED = 1
   ```

2. **Open MAP file, find correct segment**
   - Read Segment 0 lookup table
   - Find entry for (LINE_ID, FIELD_ID) → returns segment number N

3. **Binary search segment N for field value**
   - Entries are sorted → binary search for "200-044295-001"
   - Extract u32_index value (e.g., 136,653)

4. **Join to Segment 0 for page resolution**
   - Use u32_index as join key into Segment 0
   - Get back: (record_id, page_number, row_position)

5. **Extract from RPT file**
   - Seek to matched page via PAGETBLHDR
   - Decompress zlib stream
   - Extract line at row position
   - Extract field value at START_COLUMN:END_COLUMN

### Database Tables

```
FIELD (IS_INDEXED = 1)          → which fields are searchable
    ↓
SST_STORAGE                     → links REPORT_INSTANCE to MAPFILE
    ↓
MAPFILE (MAP_FILE_ID, FILENAME) → physical MAP file on disk
```

---

## 3. Sections vs Indexed Fields — How They Interact

### Are They Independent?

**Yes, conceptually independent:**
- **Sections** = access control grouping (branches, cost centers)
- **Indexed Fields** = searchable content fields (account numbers)

### How They Interact at Search Time

**Scenario A — No section segregation** (user has access to all sections):
- User searches ACCOUNT_NO = '200-044295-001'
- MAP returns pages [117, 120, 3200]
- User sees all 3 pages (no restriction)

**Scenario B — Section segregation** (user only authorized for section "501" = pages 890-3093):
- User searches ACCOUNT_NO = '200-044295-001'
- MAP returns pages [117, 120, 3200]
- Intersection with allowed pages: only page 3200 falls in range 890-3093
- User sees only page 3200

**Key insight:** MAP search is always **report-wide**, but results are **filtered by section permissions** at serve time.

---

## 4. Extraction Patterns — How Transaction Rows/Columns Are Extracted

### Core Concept: LINE and FIELD Templates

**LINE table** — Pattern templates for each line type in the report:
- Each report species has a `STRUCTURE_DEF_ID` that links to a set of LINE definitions
- Each LINE has a `TEMPLATE` column using pattern characters:
  - `A` = alpha character expected
  - `9` = digit expected
  - ` ` = space expected
  - Literal chars (`-`, `/`, `:`, `.`) = exact match required (structural anchors)

**FIELD table** — Column positions within each LINE:
- Each LINE has multiple FIELDs at (`START_COLUMN`, `END_COLUMN`)
- `IS_INDEXED = 1` → value goes into MAP file during ingestion
- `IS_SIGNIFICANT = 1` → defines section boundaries

### Template Matching Engine (from intellistor_extractor.py)

```
For each text line on a page:
  For each LINE template:
    Score = weighted match:
      - Literal chars (-, /, :)  → weight 3.0 (structural anchors)
      - A positions              → weight 1.0 (alpha expected, partial credit for digits)
      - 9 positions              → weight 1.0 (digit expected, partial credit for alpha)
      - Space positions          → weight 0.5

    Final score = earned / total_weight (0.0 to 1.0)

  Best match above 0.55 threshold → classified as that LINE type
```

### Field Value Extraction

Once a line is classified:
```
For each FIELD in the matched LINE:
  value = line_text[START_COLUMN : END_COLUMN].strip()
```

### Multi-Row Table Assembly (TABLE_DEF/TABLE_ITEM)

For extracting repeating structures (e.g., transaction tables):

```
TABLE_DEF:  table_id → table_name (e.g., "Transaction Details")
TABLE_ITEM: table_id → list of LINE_IDs that compose the table
  LINE_ID 10 = Header row
  LINE_ID 11 = Detail row (repeating)
  LINE_ID 12 = Subtotal row
  SORT_LEVEL = hierarchical grouping
```

**Status:** Database tables exist but multi-row extraction code is NOT yet implemented (Phase 2/3).

### Complete Extraction Pipeline

```
1. Resolve Report
   report name → REPORT_SPECIES_ID → latest REPORT_INSTANCE
   → STRUCTURE_DEF_ID, MAP file, RPT file

2. MAP Search (if searching by field value)
   ACCOUNT_NO → MAP segment → binary search → page numbers

3. RPT Page Decompression
   page number → PAGETBLHDR byte offset → zlib decompress → raw text

4. LINE Template Matching
   each text line → score against all LINE templates → best match

5. FIELD Value Extraction
   matched line → extract at [START_COLUMN:END_COLUMN] → field values

6. Output
   structured CSV/JSON with all extracted fields
```

---

## 5. How All Three Systems Work Together

### Complete Data Flow: Ingestion → Storage → Access

```
SPOOL ARRIVES
├── SIGNATURE_GROUP routes to processing pool
└── PAGINATOR matches report using SIGNATURE patterns

FIELD EXTRACTION (during ingestion)
├── For each matched line:
│   ├── FIELD extraction at column positions
│   ├── IS_INDEXED fields → stored in MAP file (sorted indices)
│   └── IS_SIGNIFICANT fields → define SECTION boundaries
└── SENSITIVE_FIELD extraction:
    ├── SENSITIVITY=0 → Report Name
    ├── SENSITIVITY=2 → Report Date
    └── SENSITIVITY=4,65538 → Section values

OUTPUT: ONE INSTANCE
├── REPORT_INSTANCE record (domain, species, timestamp)
├── RPT file (compressed spool + SECTIONHDR + PAGETBLHDR)
│   └── SECTIONHDR: (SECTION_ID, START_PAGE, PAGE_COUNT) triplets
└── MAP file (field search index)
    ├── Segment 0: page-level master index
    └── Segments 1-N: sorted field-value indices

USER ACCESS
├── User auth → Windows SID
├── STYPE_SECTION ACL check → allowed SECTION_IDs
├── RPT SECTIONHDR → page ranges for allowed sections
└── MAP search → find pages → intersect with allowed pages → serve
```

---

## 6. Existing Code

### Production-Ready (Phase 1)

| File | Lines | Purpose |
|------|-------|---------|
| `intellistor_extractor.py` | ~875 | Main extraction tool: MAP search, RPT decompress, LINE matching, FIELD extraction |
| `intellistor_viewer.py` | ~600+ | Database access layer, MAP file parser, data classes |
| `rpt_page_extractor.py` | ~830 | RPT page decompression, PAGETBLHDR parsing, binary object extraction |
| `rpt_section_reader.py` | ~200 | RPT SECTIONHDR binary parsing |
| `extract_instances_sections.py` | ~1000 | Report instance CSV extraction with section/MAP support |

### Not Yet Implemented

| Feature | Tables Involved | Status |
|---------|-----------------|--------|
| TABLE_DEF/TABLE_ITEM multi-row extraction | TABLE_DEF, TABLE_ITEM | Phase 2 - not started |
| FOLLOW_LIST line sequence validation | FOLLOW_LIST | Phase 2 - not started |
| FIELD_TYPE formatting rules | FIELD_TYPE, FIELD_TYPE_PARAMETERS | Phase 4 - not started |

---

## 7. Key Database Tables Summary

| Table | Purpose |
|-------|---------|
| REPORT_SPECIES | Report type definitions |
| REPORT_INSTANCE | Individual report occurrences |
| STRUCTURE_DEF | Links species to LINE/FIELD structure |
| LINE | Template patterns per line type (TEMPLATE column) |
| FIELD | Column positions and flags (START_COLUMN, END_COLUMN, IS_INDEXED, IS_SIGNIFICANT) |
| SECTION | Section definitions per species (branch names) |
| STYPE_SECTION | ACL permissions per section |
| SST_STORAGE | Links instances to MAP files |
| MAPFILE | MAP file registry |
| RPTFILE | RPT file registry |
| TABLE_DEF | Table name definitions |
| TABLE_ITEM | LINE composition of tables |
| SENSITIVE_FIELD | Metadata extraction rules (report name, date, section fields) |
| FOLLOW_LIST | Valid line succession rules |
