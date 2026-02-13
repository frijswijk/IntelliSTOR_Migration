# Papyrus IntelliSTOR Replacement — Design Proposal

## Overview

This document describes the design for a new system to replace IntelliSTOR on the Papyrus platform. The three main components are:

1. **`papyrus_rpt_search`** — Standalone MAP file search tool (Python + C++)
2. **`papyrus_export_metadata`** — Database metadata export to JSON (before decommission)
3. **Browser-based pattern definition tool** — For defining extraction patterns, indexes, and document ingestion

---

## The Big Picture

We are replacing a 25-year-old tightly-coupled system (IntelliSTOR + MS SQL) with a loosely-coupled architecture:

- **Papyrus** is the new platform (REST API, document store, workflow engine)
- **MAP + RPT files** stay as-is (already exported, ~85K MAP files + RPT files on disk)
- **MS SQL goes away** → all metadata (LINE templates, FIELD positions, TABLE_DEF, etc.) must be exported and stored elsewhere
- **New tools** need to be self-contained (no database dependency at runtime)

---

## Component 1: `papyrus_rpt_search` — MAP File Search Tool

### What It Does

Takes a MAP file + field identifier + search value → returns page numbers.

### Architecture

```
┌──────────────────────────────────────────────────┐
│ papyrus_rpt_search                               │
│                                                  │
│ Input:  --map <file> --line-id <N> --field-id <N>│
│         --value <search_term>                    │
│         [--metadata <json>] (for --field NAME)   │
│                                                  │
│ Output: JSON to stdout                           │
│ {                                                │
│   "matches": [                                   │
│     {"value": "200-044295-001", "page": 117},    │
│     {"value": "200-044295-001", "page": 3200}    │
│   ],                                             │
│   "field": "ACCOUNT_NO",                         │
│   "format": "page" | "u32_index",                │
│   "segment": 3,                                  │
│   "entry_count": 14523                           │
│ }                                                │
│                                                  │
│ Additional modes:                                │
│   --list-fields    → list all indexed segments   │
│   --list-values    → dump all values in segment  │
│   --segment-info   → show segment metadata       │
└──────────────────────────────────────────────────┘
```

### The Field Identification Problem

**Field names are NOT globally unique** — they are scoped per `STRUCTURE_DEF_ID`:

```
REPORT_SPECIES (e.g. "DDU017P")
  → REPORT_INSTANCE (has STRUCTURE_DEF_ID = 42)
    → FIELD (keyed by STRUCTURE_DEF_ID + LINE_ID + FIELD_ID)
         NAME="ACCOUNT_NO", LINE_ID=5, FIELD_ID=3

REPORT_SPECIES (e.g. "BC2060P")
  → REPORT_INSTANCE (has STRUCTURE_DEF_ID = 87)
    → FIELD (keyed by STRUCTURE_DEF_ID + LINE_ID + FIELD_ID)
         NAME="ACCOUNT_NO", LINE_ID=2, FIELD_ID=1
```

Same name, different `(LINE_ID, FIELD_ID)` — because each species has its own STRUCTURE_DEF_ID.

**Within one species** (one STRUCTURE_DEF_ID), field names ARE unique.

**The MAP file does NOT contain field names** — only numeric `(LINE_ID, FIELD_ID)` in each segment's metadata (offset +24 from `**ME` marker).

**Solution:** The metadata JSON (from the export tool) provides the name→ID mapping.

### What the MAP File Contains vs What Comes from Database

| Data | Source | Details |
|------|--------|---------|
| Indexed field LINE_ID | MAP file (Segment 0 + segments 1+) | Numeric only |
| Indexed field FIELD_ID | MAP file (Segment 0 + segments 1+) | Numeric only |
| Which segment has the index | MAP file (Segment 0 lookup table) | 4-byte entries |
| Field name (e.g. "ACCOUNT_NO") | **DATABASE ONLY** → exported to JSON | From FIELD.NAME |
| Field width | MAP file (segments 1+) | 2 bytes at metadata offset |
| Entry count | MAP file (segments 1+) | 2 bytes at metadata offset |
| Actual indexed values | MAP file (segments 1+) | Sorted entries in segment data |
| IS_INDEXED flag | **DATABASE ONLY** → exported to JSON | From FIELD.IS_INDEXED |
| IS_SIGNIFICANT flag | **DATABASE ONLY** → exported to JSON | From FIELD.IS_SIGNIFICANT |

### CLI Modes

**Mode 1: Search by raw IDs (no metadata needed)**
```bash
papyrus_rpt_search --map 25001002.MAP \
    --line-id 5 --field-id 3 --value "200-044295-001"
```

**Mode 2: Search by field name (requires metadata JSON)**
```bash
papyrus_rpt_search --map 25001002.MAP --metadata DDU017P_metadata.json \
    --field ACCOUNT_NO --value "200-044295-001"
```

**Mode 3: List indexed fields**
```bash
# From MAP only (numeric IDs):
papyrus_rpt_search --map 25001002.MAP --list-fields

# With metadata enrichment (adds names):
papyrus_rpt_search --map 25001002.MAP --metadata DDU017P_metadata.json --list-fields
```

### Search Flow Without Database

```
Step 1: Load metadata JSON → MetadataResolver
Step 2: resolver.resolve_field("ACCOUNT_NO") → {line_id: 5, field_id: 3}
Step 3: Load MAP file → MapFileParser (existing from intellistor_viewer.py)
Step 4: parser.find_segment_for_field(5, 3) → segment
Step 5: Binary search entries in segment for value → matches
Step 6: Output results (JSON/CSV/table)
```

### Key Improvements Over Current Python Implementation

1. **Binary search** — MAP entries are sorted; current code does linear scan. Binary search: ~14 comparisons vs 14,523 for linear.
2. **u32_index → page resolution** — Current code sets `page_number=0` for Format B (large files). Need to resolve via Segment 0 page-level records.
3. **Memory-mapped I/O** — In C++ version, use `mmap`/`CreateFileMapping` instead of reading entire file.
4. **Cross-validation** — Compare metadata JSON field_width against MAP segment field_width.

---

## Component 2: `papyrus_export_metadata` — Database Metadata Export

### Purpose

One-time export of all species metadata from MS SQL to JSON files, for use after database decommission.

### What Gets Exported

For each report species:
- **FIELD table**: All field definitions (name, LINE_ID, FIELD_ID, START_COLUMN, END_COLUMN, IS_INDEXED, IS_SIGNIFICANT)
- **LINE table**: Line definitions (LINE_ID, name, template pattern)
- **SECTION table**: Section definitions (SECTION_ID, name)
- **Report metadata**: STRUCTURE_DEF_ID, REPORT_SPECIES_ID, DOMAIN_ID

### JSON Format

Per-species file (`{species_name}_metadata.json`):
```json
{
  "format_version": "1.0",
  "export_timestamp": "2026-02-13T10:00:00Z",
  "species": {
    "name": "DDU017P",
    "report_species_id": 123,
    "structure_def_id": 42,
    "domain_id": 1
  },
  "indexed_fields": [
    {
      "name": "ACCOUNT_NO",
      "line_id": 5, "field_id": 3,
      "start_column": 5, "end_column": 18
    }
  ],
  "all_fields": [
    {
      "line_id": 1, "field_id": 1, "name": "PAGE_HEADER",
      "start_column": 0, "end_column": 79,
      "is_indexed": false, "is_significant": false
    }
  ],
  "lines": [
    {
      "line_id": 1, "name": "Page Header",
      "template": "A AAAA 99/99/9999    AAAAAAA*"
    }
  ],
  "sections": [
    { "section_id": 1, "name": "501 01" }
  ]
}
```

Combined index file (`metadata_index.json`):
```json
{
  "species": [
    {
      "name": "DDU017P",
      "report_species_id": 123,
      "indexed_fields": ["ACCOUNT_NO"],
      "metadata_file": "DDU017P_metadata.json"
    }
  ]
}
```

### Urgency

**CRITICAL — must complete before MS SQL is decommissioned.** Once the database is gone, this data is unrecoverable.

---

## Component 3: Browser-Based Pattern Definition Tool

### The Pattern Complexity Problem

Current IntelliSTOR approach:
- LINE.TEMPLATE uses character-level patterns (`A` = alpha, `9` = digit, literals)
- Weighted scoring (literals 3.0×, alpha/digit 1.0×, spaces 0.5×)
- Best match above 0.55 threshold
- One template per line type, multiple fields per line at fixed columns

For fixed-format spool files (mainframe output), this approach is well-suited. The real complexity isn't the matching — it's the setup (defining all those templates and field positions manually).

**Proposal: Keep the matching engine, simplify the definition process.**

### Visual Pattern Builder

Instead of hand-coding templates and column positions, build a visual tool:

```
┌──────────────────────────────────────────────────────────┐
│ Pattern Builder                                          │
│                                                          │
│ Report: DDU017P  │  Sample Page: 117 of 3400            │
│                                                          │
│ ┌──────────────────────────────────────────────────────┐ │
│ │ 501  13/01/2025  DAILY DEPOSIT UPDATE REPORT   P.001│ │
│ │                                                      │ │
│ │ ACC NO           NAME              BALANCE     DATE  │ │
│ │ ──────────────────────────────────────────────────── │ │
│ │ 200-044295-001   JOHN TAN KH      12,500.00   13/01│ │
│ │ 200-044295-002   SARAH LIM MF      8,300.50   13/01│ │
│ │ 200-044295-003   AHMAD BIN ISM     45,000.00  13/01│ │
│ │                                    ──────────       │ │
│ │ SUBTOTAL: 3 ACCOUNTS               65,800.50       │ │
│ └──────────────────────────────────────────────────────┘ │
│                                                          │
│ Actions:                                                 │
│ [1] Click a line → auto-generates LINE template          │
│ [2] Drag to select columns → creates FIELD definitions   │
│ [3] Mark line roles: Header / Detail / Subtotal / Skip   │
│ [4] Mark fields: Indexed / Significant / Normal          │
│ [5] Test pattern → shows match scores for all lines      │
└──────────────────────────────────────────────────────────┘
```

### Document Ingestion Wizard

For new unknown documents that need to be onboarded:

1. **Upload sample spool file** (or paste text)
2. **Auto-detect report boundaries** — page delimiters, recurring patterns
3. **Cluster lines by pattern similarity** — identify header/detail/subtotal line types
4. **Suggest section boundaries** — find columns where values change per page group
5. **Auto-generate templates** — from cluster centroids
6. **User confirms and adjusts** — visual editing
7. **Test against full file** — match scores and field extraction preview
8. **Deploy to Papyrus** — save metadata JSON via REST API

### Architecture

```
┌─────────────────────────────────────────────────┐
│                 Browser (React)                  │
│                                                  │
│  Pattern Builder │ Ingestion Wizard │ Search UI  │
│         ↕                ↕               ↕       │
│     REST API calls                               │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│            Papyrus Application Server            │
│                                                  │
│  REST API endpoints:                             │
│  POST /api/species/{name}/metadata    (save)     │
│  GET  /api/species/{name}/metadata    (load)     │
│  POST /api/species/{name}/test        (test)     │
│  POST /api/search                     (search)   │
│  POST /api/ingest/analyze             (auto)     │
│                                                  │
│  Calls native tools:                             │
│  - papyrus_rpt_search.exe (MAP search)           │
│  - papyrus_rpt_extract.exe (page decompress)     │
│  - pattern_matcher (template scoring)            │
└─────────────────────────────────────────────────┘
```

---

## Build Order

| Phase | What | Effort | Dependencies |
|-------|------|--------|-------------|
| **7B** | `papyrus_rpt_search.py` — Python search tool | 3 days | MAP files on disk |
| **7A** | `papyrus_export_metadata.py` — metadata export | 2 days | DB access (before decommission!) |
| **7C** | `papyrus_rpt_search.exe` — C++ port | 4 days | Phase 7B proven |
| **F** | `papyrus_rpt_extract.exe` — standalone page extraction | 3 days | Existing `rpt_page_extractor.py` |
| **G** | Pattern Builder browser UI (React) | 1-2 weeks | Phase 7A (JSON format) |
| **H** | Ingestion Wizard with auto-detection | 2-3 weeks | Phase G |
| **I** | Papyrus REST integration | 1-2 weeks | Papyrus platform ready |

---

## Existing Code Inventory

### Already Built and Working

| Tool | File | Status |
|------|------|--------|
| MAP file parser (binary) | `intellistor_viewer.py` (MapFileParser class) | ✅ Production |
| Field extraction engine | `intellistor_extractor.py` (score_line_against_template) | ✅ Phase 1 complete |
| RPT page decompression | `rpt_page_extractor.py` | ✅ Production |
| Instance CSV export | `extract_instances_sections.py` + `papyrus_extract_instances.cpp` | ✅ Production |

### Not Yet Implemented

- TABLE_DEF / TABLE_ITEM — multi-row table extraction (header + detail + subtotal)
- FOLLOW_LIST — line succession validation
- FIELD_TYPE — field data type handling
- Binary search in MAP files (currently linear scan)
- u32_index → page resolution for large MAP files

---

## References

- `INTELLISTOR_ARCHITECTURE_REFERENCE.md` — How sections, indexing, and extraction work together
- `IntelliSTOR_Architecture.pptx` — Visual slides explaining the architecture
- `intellistor_viewer.py` — Core MAP file parser and database access layer
- `intellistor_extractor.py` — Complete extraction pipeline (Phase 1)
