# Deep Analysis: How .MAP Files Work and Related Database Tables

## Executive Answer

**MAP files do NOT store extracted data. They are binary field-value search indices that describe HOW to find data within the text spool files stored inside .RPT files.**

Specifically:
- A `.MAP` file is a **compiled binary index** that maps field values (e.g., ACCOUNT_NO="200-044295-001") to page numbers in the spool file
- The actual text data lives inside `.RPT` files as zlib-compressed pages
- The extraction layout (where fields sit on each line, what patterns to match) is defined in the **database** via LINE, FIELD, TABLE_DEF/TABLE_ITEM/TABLE_NAMES, and SIGNATURE tables
- MAP files enable **O(log N) search** — "which page contains this account number?" — without scanning every page

---

## 1. MAP File Binary Structure

### Format
- **Encoding**: UTF-16LE binary
- **Signature**: `MAPHDR` (first 12 bytes)
- **Segment count**: Bytes 18-19 (uint16 little-endian)
- **Section markers**: `**ME` delimiters between segments

### Internal Organization
```
MAPHDR (header, 24 bytes)
  ├─ Segment 0: Directory/lookup table
  │   Maps (LINE_ID, FIELD_ID) → segment number
  │   Enables O(1) routing to the right segment
  │
  ├─ Segment 1: Sorted index for 1st IS_INDEXED field
  │   Entry format: [length:2][value:N][page:2][flags:3]
  │   Values are SORTED for binary search
  │
  ├─ Segment 2: Sorted index for 2nd IS_INDEXED field
  │   ...
  └─ Segment N: Sorted index for Nth IS_INDEXED field
```

### What MAP Files Store
- **Field-value → page mappings**: For every IS_INDEXED field, every unique value and which page(s) it appears on
- **Segment 0 directory**: A routing table from (LINE_ID, FIELD_ID) to segment number

### What MAP Files Do NOT Store
- Extraction definitions (column positions, line templates) — those live in the database
- Section/branch boundaries — those live in RPT file SECTIONHDR
- The actual report text data — that's in RPT compressed pages

---

## 2. How ACCOUNT_NO (Indexed) Search Works

```
User searches: ACCOUNT_NO = "200-044295-001"
        ↓
Step 1: Query FIELD table
        WHERE NAME='ACCOUNT_NO' AND IS_INDEXED=1
        → Returns LINE_ID=5, FIELD_ID=3
        ↓
Step 2: Open MAP file, read Segment 0 (directory)
        Find entry for (LINE_ID=5, FIELD_ID=3)
        → Routes to Segment 2
        ↓
Step 3: Binary search Segment 2
        Entries are sorted by value
        Find "200-044295-001"
        → Returns page_number=117
        ↓
Step 4: Open RPT file, use PAGETBLHDR
        Jump to page 117's compressed data offset
        Decompress zlib stream
        → Returns full text of page 117
        ↓
Step 5: Extract field at START_COLUMN:END_COLUMN
        Read characters at columns 5-18 on matching LINE
        → "200-044295-001" confirmed
```

---

## 3. Database Tables — Complete Taxonomy

### 3.1 Report Structure Definition Tables

These tables define HOW to parse text spool files:

#### `LINE` — Line pattern definitions
```
STRUCTURE_DEF_ID  int     → Groups lines by report structure
MINOR_VERSION     int     → Version tracking
LINE_ID           int     → Line identifier
NAME              char    → Human name (e.g., "Page Header", "Detail Line")
TEMPLATE          char    → Pattern: A=alpha, 9=digit, *=literal, ' '=space
COLOR             int     → Display color
NOISE             smallint → Noise/skip indicator
TAG               smallint → Classification tag
OPTIMIZE_FLAGS    int     → Optimization hints
```

**Role**: Each line in a text spool page is matched against LINE.TEMPLATE patterns. When a match is found, the system knows which LINE_ID it is, and can extract FIELD values from that line.

#### `FIELD` — Field definitions within lines
```
STRUCTURE_DEF_ID  int      → Report structure
LINE_ID           int      → Which LINE this field belongs to
FIELD_ID          int      → Field identifier within line
NAME              char     → Field name (e.g., "ACCOUNT_NO", "BrCode001")
START_COLUMN      smallint → Starting column (0-indexed)
END_COLUMN        smallint → Ending column
IS_INDEXED        smallint → 1 = searchable via MAP index
IS_SIGNIFICANT    smallint → 1 = section boundary field
IS_DISTINGUISHER  smallint → Distinguisher flag
IS_WATERMARKED    smallint → Watermark flag
FIELD_TYPE_NAME   char     → Data type name
FIELD_TYPE_LOCALEID int    → Locale for type
LINE_SEGMENT_ID   int      → FK to LINE_SEGMENT (sub-line grouping)
STICKY            int      → Sticky field behavior
```

**Role**: Defines exactly WHERE each field sits on a matched line (column range), and what properties it has (indexed, significant, etc.).

#### `FIELD_TYPE` — Extended type definitions per field
```
STRUCTURE_DEF_ID     int
LINE_ID              int
FIELD_ID             int
TYPE_LEVEL           smallint  → Type hierarchy level
FIELD_TYPE_LOCALEID  int       → Locale
FIELD_TYPE_NAME      char      → Type name (e.g., date format, numeric format)
```

**Role**: Defines parsing/formatting rules for fields. A field might be typed as "Date(DD/MM/YYYY)" or "Number(2dp)". TYPE_LEVEL allows multiple type definitions per field (hierarchical).

#### `FIELD_TYPE_PARAMETERS` — Type parameters
```
STRUCTURE_DEF_ID  int
LINE_ID           int
FIELD_ID          int
TYPE_LEVEL        smallint
PARAMETER_NUMBER  int       → Which parameter
PARAMETER_VALUE   varbinary → Parameter data (binary)
```

**Role**: Stores additional parsing parameters for FIELD_TYPE (e.g., date format strings, decimal precision, thousands separator).

#### `LINE_SEGMENT` — Sub-line grouping
```
STRUCTURE_DEF_ID  int
LINE_ID           int
LINE_SEGMENT_ID   int   → Segment within a line
NAME              char  → Segment name
TAG               smallint
```

**Role**: Groups fields within a single LINE into logical segments. A "Detail Line" might have segments for "Account Info" and "Transaction Amount". Fields reference LINE_SEGMENT_ID to indicate which sub-group they belong to.

#### `LINE_OVERLAP_GROUP` — Overlapping line patterns
```
STRUCTURE_DEF_ID  int
LINE_INDEX        smallint → Index of line in overlap group
GROUP_LINE_INDEX  smallint → Group identifier
POSITION          smallint → Position within group
PRECEDENCE        smallint → Which line wins on conflict
MASK              int      → Bitmask for overlap rules
```

**Role**: Handles cases where multiple LINE templates could match the same text line. Defines precedence rules and grouping to resolve ambiguity.

#### `FOLLOW_LIST` — Line sequence rules
```
STRUCTURE_DEF_ID  int
LINE_ID           int      → The line
FOLLOWER_LINE_ID  int      → Which line can follow it
POSITION          smallint → Position in sequence
```

**Role**: Defines valid line sequences. If LINE_ID=5 (Detail Header) is matched, FOLLOW_LIST says which LINE_IDs can appear next (e.g., LINE_ID=6 Detail Row). This is critical for **multi-line column extraction** — the system knows a Detail Row must follow a Detail Header.

---

### 3.2 TABLE_DEF / TABLE_ITEM / TABLE_NAMES — Multi-Row Table Extraction

These three tables work together to define **tabular/repeating data extraction** from report pages:

#### `TABLE_NAMES` — Named table definitions
```
TABLE_NAME_ID     int   → Primary key
TABLE_NAME        char  → Human name (e.g., "Transaction Details", "Account Summary")
STRUCTURE_DEF_ID  int   → Report structure
MINOR_VERSION     int   → Version
```

**Role**: Names a logical table/grid that can be extracted from report pages. Think of it as naming a repeating data region.

#### `TABLE_DEF` — Table-to-structure mapping
```
STRUCTURE_DEF_ID  int → Report structure
MINOR_VERSION     int → Version
TABLE_ID          int → Table identifier (used by TABLE_ITEM)
TABLE_NAME_ID     int → FK to TABLE_NAMES (the named table)
```

**Role**: Links a TABLE_ID to its name (TABLE_NAME_ID) and report structure. One report structure can have multiple tables (e.g., a report with both a "Summary" grid and a "Detail" grid).

#### `TABLE_ITEM` — Lines that compose a table
```
STRUCTURE_DEF_ID  int      → Report structure
MINOR_VERSION     int      → Version
TABLE_ID          int      → Which table this line belongs to
LINE_ID           int      → FK to LINE (which line pattern)
LINE_SEGMENT_ID   int      → FK to LINE_SEGMENT (sub-group within line)
POSITION          smallint → Position of this line in the table layout
SORT_LEVEL        smallint → Sort/group level
ITEM_ORDER        smallint → Display order
OPTIONAL          smallint → 1 = line may be absent
```

**Role**: Defines which LINE patterns make up a table. A "Transaction Details" table might consist of:
- LINE_ID=10 (Header row) at POSITION=0
- LINE_ID=11 (Detail row) at POSITION=1, repeating
- LINE_ID=12 (Subtotal row) at POSITION=2

**SORT_LEVEL** enables hierarchical grouping (e.g., group transactions by account, then by date).

### How TABLE_DEF/TABLE_ITEM/TABLE_NAMES Enable Multi-Line Extraction

```
Report Page (text):
┌──────────────────────────────────────────────┐
│ Branch: 501    Report Date: 01/01/2025  Pg 1 │  ← LINE_ID=1 (Header)
│                                              │
│ Account No    Customer Name     Balance      │  ← LINE_ID=10 (Table Header)
│ ──────────    ──────────────    ─────────    │
│ 200-044295    ACME Corp         1,234.56     │  ← LINE_ID=11 (Detail Row)
│ 200-044296    Beta Inc          2,345.67     │  ← LINE_ID=11 (Detail Row)
│ 200-044297    Gamma Ltd         3,456.78     │  ← LINE_ID=11 (Detail Row)
│                                              │
│               Subtotal:         7,037.01     │  ← LINE_ID=12 (Subtotal)
└──────────────────────────────────────────────┘

TABLE_DEF links TABLE_ID=1 → TABLE_NAMES "Transaction Details"
TABLE_ITEM entries:
  TABLE_ID=1, LINE_ID=10, POSITION=0  (Header)
  TABLE_ID=1, LINE_ID=11, POSITION=1  (Detail - repeats)
  TABLE_ID=1, LINE_ID=12, POSITION=2  (Subtotal)

FIELD entries for LINE_ID=11:
  FIELD_ID=1, NAME="ACCOUNT_NO",    START_COLUMN=1,  END_COLUMN=10, IS_INDEXED=1
  FIELD_ID=2, NAME="CUSTOMER_NAME", START_COLUMN=15, END_COLUMN=30, IS_INDEXED=0
  FIELD_ID=3, NAME="BALANCE",       START_COLUMN=35, END_COLUMN=45, IS_INDEXED=0

Result: The system can:
1. Match LINE templates to identify header, detail, subtotal lines
2. Extract FIELD values at column positions from each matching line
3. Build structured tabular data from repeating detail lines
4. Index ACCOUNT_NO values into MAP file for search
```

---

### 3.3 Signature & Metadata Extraction Tables

#### `SIGNATURE` — Report identification rules
```
SIGN_ID            int   → Primary key
REPORT_SPECIES_ID  int   → Which report type
REPORT_DATE_TYPE   int   → 0=Today, 1=LastBusinessDay, 2=FromField
LBD_OFFSETS        int   → Business day calculation offsets
POSITION           int   → Matching position
MATCHING           int   → Matching criteria
```

#### `SENSITIVE_FIELD` — Field role assignments
```
SIGN_ID            int   → FK to SIGNATURE
LINE_ID            int   → Which line
FIELD_ID           int   → Which field
LINE_OF_OCCURENCE  int   → Which occurrence (0-based)
SENSITIVITY        int   → Role code:
                            1 = Report Name field
                            2 = Report Date field
                            3 = Page Number field
                            4 = Section/Branch field
                            65538 = Extended
```

#### `LINES_IN_SIGN` — Lines used for signature matching
```
SIGN_ID       int → FK to SIGNATURE
LINE_ID       int → Which line to match
LINE_NUMBER   int → Position in spool where this line appears
```

**Role**: During ingestion, the PAGINATOR matches incoming spool text against SIGNATURE patterns to identify which report type it is. LINES_IN_SIGN specifies which lines must be matched and where.

---

### 3.4 Instance & Storage Tables

#### `REPORT_INSTANCE` ↔ `SST_STORAGE` ↔ `MAPFILE`
```
REPORT_INSTANCE (composite PK: DOMAIN_ID, REPORT_SPECIES_ID, AS_OF_TIMESTAMP)
    │ STRUCTURE_DEF_ID → defines which LINE/FIELD/TABLE defs apply
    │
    ├── SST_STORAGE.MAP_FILE_ID → MAPFILE.MAP_FILE_ID
    │   └── MAPFILE.FILENAME = "25001002.MAP"
    │
    └── RPTFILE_INSTANCE.RPT_FILE_ID → RPTFILE.RPT_FILE_ID
        └── RPTFILE.FILENAME = "MIDASRPT\5\260271NL.RPT"
```

#### `REPORT_INSTANCE_SEGMENT` — Ingestion arrival tracking
```
SEGMENT_NUMBER        int → Sequential arrival chunk (0, 1, 2...)
START_PAGE_NUMBER     int → First page of this chunk
NUMBER_OF_PAGES       int → Pages in this chunk
PAGINATOR_JOB_ID      binary → Which ingestion job
ARRIVAL_TIMESTAMP     datetime → When this chunk arrived
```

**Important**: This is NOT section segregation. This tracks how spool files were delivered in chunks during ingestion. Section boundaries come from RPT file SECTIONHDR.

---

### 3.5 Other Supporting Tables

#### `DATA_MAPPING` — Field value transformation rules
```
STRUCTURE_DEF_ID   int
LINE_ID            int
FIELD_ID           int
TYPE_LEVEL         smallint
DATA_MAPPING_ID    int
INSTRUCTION        smallint     → Transformation instruction code
SECONDARY_VALUE    char         → Secondary lookup value
PRIMARY_EQUIVALENT char         → What to map to
```

**Role**: Transforms extracted field values (e.g., map code "01" to "New York Branch").

#### `SAMPLE_CHAR_LINES` — Sample lines for template matching
```
STRUCTURE_DEF_ID      int
LINE_ID               int
SAMPLE_CHAR_LINES_ID  int
CHAR_LINE             char  → A sample text line from real spool
```

**Role**: Stores example text lines used during structure definition. Helps administrators see what a LINE_ID actually looks like in practice.

#### `SEGMENT_SPEC_TYPE` — MAP segment metadata
```
MAP_FILE_ID  int → FK to MAPFILE
SEGMENT_ID   int → Segment number within MAP
NAME         varchar → Segment name
SECTION_ID   int → FK to SECTION (for section association)
TIME_STAMP   datetime
```

**Role**: Database-side metadata about MAP file segments, linking them to sections.

---

## 4. Complete Data Flow: Ingestion → Storage → Search → Extraction

```
INGESTION PIPELINE (PAGINATOR):
┌─────────────────────────────────────────────────────────┐
│ Raw Spool Text File                                     │
│   ↓                                                     │
│ 1. Match SIGNATURE (via LINES_IN_SIGN + LINE.TEMPLATE)  │
│   → Identifies report type (REPORT_SPECIES_ID)          │
│   ↓                                                     │
│ 2. Extract metadata (via SENSITIVE_FIELD)                │
│   → Report Name (SENSITIVITY=1)                         │
│   → Report Date (SENSITIVITY=2)                         │
│   → Section values (SENSITIVITY=4)                      │
│   ↓                                                     │
│ 3. Match all lines against LINE.TEMPLATE                │
│   → Identify each line's LINE_ID                        │
│   ↓                                                     │
│ 4. Extract FIELD values at START_COLUMN:END_COLUMN      │
│   → For IS_INDEXED=1 fields: write to MAP index         │
│   → For IS_SIGNIFICANT=1 fields: create SECTION entries │
│   ↓                                                     │
│ 5. Compress pages with zlib → write RPT file            │
│   → PAGETBLHDR (24-byte per page, enables random access)│
│   → SECTIONHDR (section-to-page mapping)                │
│   ↓                                                     │
│ 6. Write MAP file (binary field-value index)            │
│   → Segment 0: (LINE_ID, FIELD_ID) → segment directory  │
│   → Segments 1-N: sorted values per IS_INDEXED field    │
└─────────────────────────────────────────────────────────┘

SEARCH (via MAP):
  User queries ACCOUNT_NO → MAP binary search → page number(s)

EXTRACTION (via RPT):
  Page number → PAGETBLHDR → zlib offset → decompress → text page
  LINE.TEMPLATE match → FIELD at columns → structured data

TABLE EXTRACTION (via TABLE_DEF/TABLE_ITEM):
  TABLE_NAMES gives named grids
  TABLE_ITEM lists which LINEs compose each grid
  FIELD defines columns within each LINE
  → Produces structured tabular output from repeating detail lines
```

---

## 5. Key Files in Working Directory

| File | Purpose |
|------|---------|
| `DATABASE_REFERENCE.md` | Database schema and connection details |
| `BINARY_MAP_ANALYSIS_PLAN.md` | MAP file binary structure specification |
| `SIGNATURE_FIELD_MAPPING_REFERENCE.md` | SIGNATURE/SENSITIVE_FIELD field role system |
| `DB_SCHEMA.csv` | Complete database schema export (all tables/columns) |
| `intellistor_viewer.py` | Interactive MAP file analysis tool |
| `rpt_section_reader.py` | RPT SECTIONHDR extraction |
| `rpt_page_extractor.py` | Full page extraction from RPT files |
| `Extract_Instances.py` | Main instance extraction script (v3.0) |
| `query_signature_fields.py` | Database query for field mappings |

---

## 6. Database Connection

```
Server: localhost:1433
Database: iSTSGUAT
User: sa
Password: Fvrpgr40
Library: pymssql
```

---

## 7. Summary Answers to Your Questions

| Question | Answer |
|----------|--------|
| Do MAP files store extracted data? | **No.** They store a search index (field-value → page mappings) |
| Do MAP files describe how to extract? | **Partially.** They tell you which PAGE contains a value, but column positions/templates come from LINE and FIELD database tables |
| What role do TABLE_DEF/TABLE_ITEM/TABLE_NAMES play? | They define **multi-row tabular data regions** — which LINE patterns compose a named grid, their ordering, and grouping |
| What role does FIELD_TYPE play? | Defines **parsing/formatting rules** for fields (date formats, numeric precision, locale) |
| What about LINE-related tables? | `LINE` = pattern templates; `LINE_SEGMENT` = sub-groups within lines; `LINE_OVERLAP_GROUP` = conflict resolution; `FOLLOW_LIST` = valid line sequences |
| How does ACCOUNT_NO search work? | FIELD.IS_INDEXED=1 → value stored in MAP segment → binary search finds page → RPT decompresses page → FIELD.START_COLUMN:END_COLUMN extracts value |
| How does MAP relate to REPORT_INSTANCE? | REPORT_INSTANCE → SST_STORAGE.MAP_FILE_ID → MAPFILE.FILENAME |

---

## 8. Data Extraction Tool — Feasibility & Implementation Plan

### Verdict: Fully Feasible

~70% of the needed functionality already exists in the codebase. The remaining ~30% (LINE template matching, FIELD value extraction, TABLE_DEF multi-row assembly, orchestration) requires new code but follows well-understood patterns.

### Tool Pipeline

```
USER INPUT: --report DDU017P --field ACCOUNT_NO --value "200-044295-001"
    ↓
[1] DB Lookup → resolve report → instance → MAP file + RPT file + STRUCTURE_DEF_ID
[2] MAP Search → binary search for value → page number(s)
[3] RPT Decompress → matched pages via PAGETBLHDR → raw text
[4] LINE Matching → classify each text line against LINE.TEMPLATE patterns
[5] FIELD Extraction → extract column-positioned values from classified lines
[6] TABLE Assembly → group related lines into tabular records (TABLE_DEF/TABLE_ITEM)
[7] Output → CSV or JSON
```

### What Exists vs What Needs Building

| Component | Existing Code | New Code Needed |
|-----------|--------------|-----------------|
| DB lookup & resolution | `DatabaseAccess` class in `intellistor_viewer.py` | Add `find_indexed_field_by_name()`, add RPT dir config |
| MAP binary search | `MapFileParser` class in `intellistor_viewer.py` | u32_index → page resolver for large MAP files |
| RPT page decompression | `read_page_table()`, `decompress_pages()` in `rpt_page_extractor.py` | None |
| LINE template matching | Templates loaded via `get_line_definitions()` | **Template matching engine** + FOLLOW_LIST queries |
| FIELD value extraction | Field defs via `get_field_definitions()` | **Column extraction function** |
| TABLE_DEF multi-row | Nothing | **Full TABLE_DEF/TABLE_ITEM query + assembly engine** |
| CSV/JSON output | Nothing | Straightforward formatter |

### Implementation Phases

#### Phase 1: Core Pipeline (single-field search + flat extraction)
**New file**: `intellistor_extractor.py`

1. Reuse `Config`, `DatabaseAccess`, `MapFileParser` from `intellistor_viewer.py`
2. Reuse `read_page_table`, `decompress_pages` from `rpt_page_extractor.py`
3. Build template matching engine:
   ```python
   def match_line_to_template(line_text: str, template: str) -> bool:
       # A=alpha, 9=digit, ' '=space, other=literal
   def classify_line(line_text: str, line_defs: List[LineDef]) -> Optional[LineDef]:
       # Match against all LINE templates
   ```
4. Build field extraction:
   ```python
   def extract_field_value(line_text: str, field_def: FieldDef) -> str:
       return line_text[field_def.start_column : field_def.end_column + 1].strip()
   ```
5. Build u32_index page resolver for large MAP files (Segment 0 record array parsing)
6. Wire up end-to-end and output CSV/JSON

**CLI**:
```bash
python intellistor_extractor.py \
    --report DDU017P \
    --field ACCOUNT_NO \
    --value "200-044295-001" \
    --output results.csv --format csv
```

#### Phase 2: FOLLOW_LIST + Template Disambiguation
1. Add `FOLLOW_LIST` query to `DatabaseAccess`
2. Implement line-sequence validation (only allow valid follower LINE_IDs)
3. Handle `LINE_OVERLAP_GROUP` precedence for ambiguous matches

#### Phase 3: TABLE_DEF Multi-Row Extraction
1. Add `TABLE_DEF`, `TABLE_ITEM`, `TABLE_NAMES` queries to `DatabaseAccess`
2. Build table grouping logic — scan classified lines, detect repeating patterns
3. Handle `LINE_SEGMENT_ID` sub-grouping and `OPTIONAL` items
4. CLI addition: `--table "Transaction Details"`

#### Phase 4: FIELD_TYPE Formatting & Batch Mode
1. Add `FIELD_TYPE` + `FIELD_TYPE_PARAMETERS` queries
2. Implement date/numeric/string parsing rules
3. Add batch mode (all instances for a date range)
4. Add section-filtered extraction (specific branches only)

### Prerequisites
- Python packages: `pymssql`, `struct`, `zlib`, `csv`, `json`, `argparse` (all already available)
- Database: `iSTSGUAT` on `localhost:1433`
- MAP files: `/Volumes/X9Pro/OCBC/250_MapFiles/`
- RPT files: path needs configuration (add `rpt_file_dir` to Config)

### Verification Plan
1. **MAP search**: Compare results with `intellistor_viewer.py` existing search output
2. **Page decompression**: Compare with `rpt_page_extractor.py` known-good output
3. **Template matching**: Manual inspection against decompressed page text
4. **End-to-end**: For DDU017P ACCOUNT_NO search — verify extracted fields match page content
5. **Cross-report**: Test with CDU100P or another report type to ensure generalization

### Critical Files to Modify/Create
| File | Action |
|------|--------|
| `intellistor_extractor.py` | **CREATE** — Main extraction tool |
| `intellistor_viewer.py` | **REUSE** — Import DatabaseAccess, MapFileParser, Config, dataclasses |
| `rpt_page_extractor.py` | **REUSE** — Import read_page_table, decompress_pages |
| `rpt_section_reader.py` | **REUSE** — Import parse_rpt_header |

### Risk Areas
| Risk | Mitigation |
|------|------------|
| Template matching edge cases | Test with multiple report types; handle short/padded lines |
| u32_index resolution (large MAPs) | Algorithm documented in SECTION_SEGMENT_WORKFLOW.md Section 12.7 |
| TABLE_DEF semantics not fully clear | Phase 3 is iterative; query real data first |
| FIELD_TYPE_PARAMETERS binary format | Defer to Phase 4; raw strings work for Phase 1-3 |
| RPT file path resolution | Add config; strip DB path prefixes from RPTFILE.FILENAME |
