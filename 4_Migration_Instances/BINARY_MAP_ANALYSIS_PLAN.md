# Binary MAP File Analysis and Extraction Plan

## Executive Summary

We are analyzing 26,724 binary MAP files from an IntelliSTOR system. These MAP files serve as:
1. **Field-value search indices** - Enabling lookup of IS_INDEXED field values (e.g., ACCOUNT_NO) to find which page(s) contain a given value
2. **Multi-row column extraction rules** - Metadata for extracting tabular data from report pages

> **CORRECTION (2026-02-07):** MAP files do NOT define sections or segments for page segregation.
> Section segregation comes exclusively from **RPT file SECTIONHDR** binary structures.
> See `SECTION_SEGMENT_WORKFLOW.md` Sections 7-8 for the authoritative specification.

## Current Progress

### What We Know About Binary MAP Files

1. **File Format**: Binary files with UTF-16LE encoding
2. **Header Structure** (first 24 bytes):
   - Bytes 0-11: `MAPHDR` signature (UTF-16LE: `4d0041005000480044005200`)
   - Bytes 12-15: Unknown (usually zeros)
   - Bytes 16-17: Flags/type field
   - **Bytes 18-19: SEGMENT COUNT** (little-endian 16-bit unsigned integer)
   - Bytes 20-23: File size or offset information

3. **Section Markers**: `**ME` markers (UTF-16LE: `2a002a004d004500`)
   - Number of `**ME` markers = number of segments
   - Each marker starts a segment definition section

4. **Segment Section Structure** (after each `**ME` marker):
   - Bytes 0-3: Header value (often `00008e00`)
   - Bytes 4-7: Segment index (0, 1, 2...) as uint32 little-endian
   - Bytes 8-11: Offset to next section as uint32 little-endian
   - Remaining bytes: Segment metadata (structure not yet fully decoded)

### Working Scripts Created

Located in: `C:\Users\freddievr\claude-projects\IntelliSTOR_Migration\4. Migration_Instances\`

1. **batch_verify_binary_maps.py** - Counts segments in all MAP files
2. **parse_binary_map.py** - Analyzes single MAP file structure
3. **diagnose_map_files.py** - Shows raw content for debugging
4. **analyze_map_structure.py** - Detailed hex analysis of MAP structure
5. **extract_map_segments.py** - Extracts segment metadata

### Database Information Available

**section.csv** (H:\section.csv):
- 1000 section records
- Columns: `DOMAIN_ID, REPORT_SPECIES_ID, SECTION_ID, NAME, TIME_STAMP`
- Contains section names like "501 49", "503 00", etc.
- SECTION_ID ranges from 0, 1, 669, 670...

### CORRECTED INSIGHT: REPORT_INSTANCE_SEGMENT Table

> **CORRECTION (2026-02-07):** The original hypothesis below was **incorrect**.
> `REPORT_INSTANCE_SEGMENT` tracks **ingestion arrival chunks** (concatenation segments
> from spool arrivals), NOT MAP file binary segment positions. See `SECTION_SEGMENT_WORKFLOW.md`
> Section 3.2 for the correct explanation.

**What REPORT_INSTANCE_SEGMENT actually tracks:**
- `SEGMENT_NUMBER` = sequential arrival chunk index (0, 1, 2...) for spool concatenation
- `START_PAGE_NUMBER` / `NUMBER_OF_PAGES` = where that arrival chunk's pages land in the concatenated spool
- This table is about **ingestion logistics**, NOT section/page segregation

**What MAP file binary segments actually represent:**
- Each `**ME` marker organizes index data by (LINE_ID, FIELD_ID) combination
- Segment 0 = lookup/directory table mapping fields to segment numbers
- Segments 1-N = sorted field-value index entries for IS_INDEXED fields
- See `SESSION_SUMMARY.md` and `SECTION_SEGMENT_WORKFLOW.md` Section 6

**Section segregation** (which pages belong to which branch) comes from:
- **RPT file SECTIONHDR** binary structures (12-byte triplets: SECTION_ID, START_PAGE, PAGE_COUNT)
- Implemented in `rpt_section_reader.py`

## Phase 1: Database Schema Analysis

### Required Database Tables

Query these tables to understand the relationships:

```sql
-- 1. MAPFILE table - Links MAP files to reports
SELECT TOP 10 * FROM MAPFILE;
SELECT COUNT(*) AS total_mapfiles FROM MAPFILE;

-- 2. SEGMENT_SPEC_TYPE table - Links segments to MAP files
SELECT TOP 10 * FROM SEGMENT_SPEC_TYPE;
SELECT COUNT(*) AS total_segments FROM SEGMENT_SPEC_TYPE;

-- 3. SECTION table - Section definitions (already exported)
SELECT TOP 10 * FROM SECTION;
SELECT COUNT(*) AS total_sections FROM SECTION;

-- 4. REPORT_INSTANCE_SEGMENT table - tracks ingestion arrival chunks
-- NOTE: SEGMENT_NUMBER = arrival chunk index, NOT MAP binary segment position
--       See SECTION_SEGMENT_WORKFLOW.md Section 3.2
SELECT TOP 20 * FROM REPORT_INSTANCE_SEGMENT;
SELECT COUNT(*) AS total_instance_segments FROM REPORT_INSTANCE_SEGMENT;

-- 5. Verify the hypothesis - Check segment_number range
SELECT
    MIN(SEGMENT_NUMBER) AS min_segment_num,
    MAX(SEGMENT_NUMBER) AS max_segment_num,
    COUNT(DISTINCT SEGMENT_NUMBER) AS distinct_segment_numbers
FROM REPORT_INSTANCE_SEGMENT;

-- 6. Check for relationships
SELECT
    mf.MAP_FILE_ID,
    mf.FILENAME AS MAP_FILENAME,
    sst.SEGMENT_ID,
    sst.NAME AS SEGMENT_NAME,
    s.SECTION_ID,
    s.NAME AS SECTION_NAME
FROM MAPFILE mf
LEFT JOIN SEGMENT_SPEC_TYPE sst ON sst.MAP_FILE_ID = mf.MAP_FILE_ID
LEFT JOIN SECTION s ON s.SECTION_ID = sst.SECTION_ID
ORDER BY mf.MAP_FILE_ID, sst.SEGMENT_ID
LIMIT 50;

-- 7. Test the hypothesis - Link report instances to segments
SELECT TOP 50
    ris.REPORT_INSTANCE_ID,
    ris.SEGMENT_NUMBER,
    ris.SECTION_ID,
    s.NAME AS SECTION_NAME,
    mf.FILENAME AS MAP_FILENAME
FROM REPORT_INSTANCE_SEGMENT ris
LEFT JOIN SECTION s ON s.SECTION_ID = ris.SECTION_ID
LEFT JOIN REPORT_INSTANCE ri ON ri.REPORT_INSTANCE_ID = ris.REPORT_INSTANCE_ID
LEFT JOIN MAPFILE mf ON mf.MAP_FILE_ID = ri.MAP_FILE_ID
ORDER BY ris.REPORT_INSTANCE_ID, ris.SEGMENT_NUMBER;

-- 8. Find MAP file structure
EXEC sp_help 'MAPFILE';
EXEC sp_help 'SEGMENT_SPEC_TYPE';
EXEC sp_help 'SECTION';
EXEC sp_help 'REPORT_INSTANCE_SEGMENT';
EXEC sp_help 'REPORT_INSTANCE';
```

### Export Required Data

Export these queries to CSV files:

```sql
-- mapfile.csv
SELECT
    MAP_FILE_ID,
    FILENAME,
    REPORT_SPECIES_ID,
    DOMAIN_ID,
    TIME_STAMP
FROM MAPFILE
ORDER BY MAP_FILE_ID;

-- segment_spec_type.csv
SELECT
    MAP_FILE_ID,
    SEGMENT_ID,
    NAME,
    SECTION_ID,
    TIME_STAMP
FROM SEGMENT_SPEC_TYPE
ORDER BY MAP_FILE_ID, SEGMENT_ID;

-- report_instance_segment.csv (KEY TABLE!)
SELECT
    REPORT_INSTANCE_ID,
    SEGMENT_NUMBER,
    SECTION_ID,
    PAGE_NUMBER,
    TIME_STAMP
FROM REPORT_INSTANCE_SEGMENT
ORDER BY REPORT_INSTANCE_ID, SEGMENT_NUMBER;

-- report_instance.csv (to link instances to MAP files)
SELECT
    REPORT_INSTANCE_ID,
    MAP_FILE_ID,
    REPORT_SPECIES_ID,
    DOMAIN_ID,
    TIME_STAMP
FROM REPORT_INSTANCE
ORDER BY REPORT_INSTANCE_ID;

-- Complete join for mapping (METHOD 1: via SEGMENT_SPEC_TYPE)
-- map_to_sections_v1.csv
SELECT
    mf.MAP_FILE_ID,
    mf.FILENAME AS MAP_FILENAME,
    sst.SEGMENT_ID,
    sst.NAME AS SEGMENT_NAME,
    sst.SECTION_ID,
    s.NAME AS SECTION_NAME,
    mf.REPORT_SPECIES_ID,
    mf.DOMAIN_ID
FROM MAPFILE mf
LEFT JOIN SEGMENT_SPEC_TYPE sst ON sst.MAP_FILE_ID = mf.MAP_FILE_ID
LEFT JOIN SECTION s ON s.SECTION_ID = sst.SECTION_ID
ORDER BY mf.MAP_FILE_ID, sst.SEGMENT_ID;

-- Complete join for mapping (METHOD 2: via REPORT_INSTANCE_SEGMENT - PREFERRED!)
-- map_to_sections_v2.csv
SELECT
    mf.MAP_FILE_ID,
    mf.FILENAME AS MAP_FILENAME,
    ris.SEGMENT_NUMBER,
    ris.SECTION_ID,
    s.NAME AS SECTION_NAME,
    COUNT(DISTINCT ris.REPORT_INSTANCE_ID) AS instance_count
FROM MAPFILE mf
JOIN REPORT_INSTANCE ri ON ri.MAP_FILE_ID = mf.MAP_FILE_ID
JOIN REPORT_INSTANCE_SEGMENT ris ON ris.REPORT_INSTANCE_ID = ri.REPORT_INSTANCE_ID
JOIN SECTION s ON s.SECTION_ID = ris.SECTION_ID
GROUP BY mf.MAP_FILE_ID, mf.FILENAME, ris.SEGMENT_NUMBER, ris.SECTION_ID, s.NAME
ORDER BY mf.MAP_FILE_ID, ris.SEGMENT_NUMBER;
```

## Phase 2: Correlation Analysis

### Goal
Determine how the binary MAP file structure correlates with database records.

### CORRECTED UNDERSTANDING (2026-02-07)

> The original hypothesis that REPORT_INSTANCE_SEGMENT links MAP binary segments to SECTION names
> was **incorrect**. REPORT_INSTANCE_SEGMENT tracks ingestion arrival chunks, not MAP structure.

**Correct correlation for MAP binary segments:**

MAP `**ME` segments correspond to **indexed field definitions** (LINE_ID, FIELD_ID from FIELD table where IS_INDEXED=1):

```
Binary MAP File Segment N (at **ME marker #N)
    ↓
Contains index entries for field: (LINE_ID, FIELD_ID)
    ↓
FIELD table: FIELD.NAME (e.g., "ACCOUNT_NO")
```

**Segment 0** is special — it's a directory/lookup table mapping (LINE_ID, FIELD_ID) to segment numbers.

### Tasks

1. **Correlate MAP segments with FIELD definitions**:
   - For each MAP file, read Segment 0 (directory) to extract (LINE_ID, FIELD_ID) mappings
   - Join to FIELD table to get field names
   - Verify: number of `**ME` markers matches number of IS_INDEXED fields + 1 (for Segment 0)

2. **Compare binary segment count with field count**:
   - Binary MAP files: Read segment count from bytes 18-19
   - Database: Count IS_INDEXED fields for the report species
   - Expected: binary segment count = IS_INDEXED field count + 1 (Segment 0)

3. **Create field-to-segment lookup table**:
   ```python
   # map_field_lookup.json
   {
       "25001001.MAP": {
           "map_file_id": 12345,
           "binary_segment_count": 9,
           "segments": [
               {
                   "segment_index": 0,       # Segment 0 = directory/lookup table
                   "type": "directory"
               },
               {
                   "segment_index": 1,       # First indexed field
                   "line_id": 4,
                   "field_id": 2,
                   "field_name": "ACCOUNT_NO",
                   "field_width": 55,
                   "entry_count": 13
               },
               {
                   "segment_index": 2,       # Second indexed field
                   "line_id": 5,
                   "field_id": 3,
                   "field_name": "CUSTOMER_NAME",
                   "field_width": 18,
                   "entry_count": 13
               }
           ]
       }
   }
   ```

## Phase 3: Binary MAP Parser Enhancement

### Create: `parse_binary_map_complete.py`

```python
#!/usr/bin/env python3
"""
Complete Binary MAP File Parser
Extracts field-value index structure with database field definitions

Requires:
    - map_field_lookup.json (from Phase 2)
    - Database connection OR CSV exports (FIELD table)

Usage:
    python parse_binary_map_complete.py <map_file_path>
    python parse_binary_map_complete.py --batch <map_directory>
"""

import struct
import json

def parse_binary_map_with_fields(map_file_path, field_definitions):
    """
    Parse binary MAP file and correlate with FIELD table definitions

    Returns:
        {
            'filename': '25001001.MAP',
            'segment_count': 9,
            'segments': [
                {
                    'index': 0,
                    'type': 'directory',
                    'me_marker_position': 90,
                    'entries': [(line_id, field_id, segment_num), ...]
                },
                {
                    'index': 1,
                    'type': 'field_index',
                    'line_id': 4,
                    'field_id': 2,
                    'field_name': 'ACCOUNT_NO',
                    'field_width': 55,
                    'entry_count': 13,
                    'me_marker_position': 482,
                    'next_offset': 748
                }
            ]
        }
    """
    # Implementation here
    pass
```

### Create: `batch_extract_all_fields.py`

Batch process all 26,724 MAP files and create:
- **map_fields_complete.csv** - All MAP segments with field definitions
- **map_field_statistics.json** - Summary statistics
- **missing_fields.txt** - MAP files with unresolved field definitions

## Phase 4: Multi-Row Column Extraction Rules

### Goal
Some MAP files contain rules for extracting multi-row/column data from report pages.

### Investigation Needed

1. **Identify MAP files with column rules**:
   - Look for specific patterns in binary data
   - Check if certain DOMAIN_ID or REPORT_SPECIES_ID values indicate column extraction
   - Query database for tables related to column definitions

2. **Database tables to check**:
   ```sql
   -- Look for column/field definition tables
   SELECT * FROM INFORMATION_SCHEMA.TABLES
   WHERE TABLE_NAME LIKE '%COLUMN%'
      OR TABLE_NAME LIKE '%FIELD%'
      OR TABLE_NAME LIKE '%EXTRACT%';
   ```

3. **Binary structure analysis**:
   - The remaining bytes after segment header might contain column rules
   - Look for patterns indicating: column positions, widths, data types

## Phase 5: Output Deliverables

### 1. Complete Field-to-Segment Mapping

**File: `map_fields_complete.csv`**

Columns:
```
MAP_FILENAME, MAP_FILE_ID, SEGMENT_INDEX, LINE_ID, FIELD_ID, FIELD_NAME, FIELD_WIDTH, ENTRY_COUNT, REPORT_SPECIES_ID, DOMAIN_ID
```

Example:
```csv
25001001.MAP,12345,0,0,0,"(directory)",0,20,45279,1
25001001.MAP,12345,1,4,2,"ACCOUNT_NO",55,13,45279,1
25001001.MAP,12345,2,5,3,"CUSTOMER_NAME",18,13,45279,1
```

### 2. MAP File Statistics

**File: `map_file_statistics.json`**

```json
{
    "total_map_files": 26724,
    "total_segments": 125000,
    "avg_segments_per_file": 4.7,
    "segment_count_distribution": {
        "0": 50,
        "1": 500,
        "2": 5000,
        "3": 8000,
        "4": 7000,
        "5+": 6174
    },
    "files_with_column_rules": 1500,
    "missing_data": {
        "files_without_db_match": 10,
        "segments_without_field_defs": 5
    }
}
```

### 3. Python Module for Reuse

**File: `intellistor_map_parser.py`**

```python
"""
IntelliSTOR Binary MAP File Parser
Reusable module for parsing binary MAP files and extracting field-value indices
"""

class MapFileParser:
    def __init__(self, db_connection=None, field_lookup_file=None):
        """Initialize with database connection or field lookup JSON"""
        pass

    def parse_file(self, map_file_path):
        """Parse single MAP file binary structure"""
        pass

    def get_indexed_fields(self, map_file_path):
        """Get list of indexed fields (LINE_ID, FIELD_ID, FIELD_NAME) from MAP file"""
        pass

    def search_field_value(self, map_file_path, line_id, field_id, value):
        """Search for a field value and return matching page numbers"""
        pass

    def get_column_rules(self, map_file_path):
        """Extract column extraction rules if present"""
        pass
```

## Phase 6: Integration with Migration

> **NOTE (2026-02-07):** `Extract_Instances.py` v3.0 already uses RPT file SECTIONHDR for
> section data (via `rpt_section_reader.py`). MAP file parsing is NOT needed for section extraction.

MAP binary parsing is relevant for:

1. **Account-index migration** — migrating ACCOUNT_NO search functionality to the new system
   - See `SECTION_SEGMENT_WORKFLOW.md` Section 12.2B (INSTANCE_ACCOUNT_INDEX table)
   - Extract field-value → page mappings from MAP files
   - Build new database index tables for the replacement system

2. **Column extraction rules** — understanding how multi-row/column tabular data is defined
   - MAP file metadata may contain column position/width definitions
   - Useful for automating data extraction from spool pages

## Success Criteria

- [ ] All 26,724 MAP files successfully parsed
- [ ] MAP binary segment count matches IS_INDEXED field count per report species
- [ ] All MAP segments correlated with FIELD table definitions (LINE_ID, FIELD_ID, FIELD_NAME)
- [ ] Column extraction rules identified and documented
- [ ] Reusable Python module created for field-value index extraction
- [ ] Account-index migration deliverables produced (field-value → page mappings)

## Questions to Answer

1. What is the relationship between MAP_FILE_ID and MAP filename?
   - Is the filename stored in MAPFILE.FILENAME?
   - Or is there a naming convention?

2. How are segments ordered?
   - Does segment index in binary (0,1,2) match SEGMENT_ID?
   - Or is there a separate ordering field?

3. What determines if a MAP file has column extraction rules?
   - Specific REPORT_SPECIES_ID values?
   - Additional database table?
   - Binary format indicators?

4. Are there multiple MAP file formats?
   - Do all files have MAPHDR header?
   - Are there version differences?

## Machine Setup Notes

### Environment
- **OS**: macOS M4
- **Database**: MS SQL Server running in Docker (Windows container)
- **Python**: Version 3.x required
- **Dependencies**:
  ```bash
  pip install pyodbc pandas
  # For SQL Server connection from macOS:
  # Install FreeTDS and unixODBC if needed
  ```

### Database Connection

```python
import pyodbc

# Connection string for SQL Server in Docker
conn_str = (
    'DRIVER={ODBC Driver 18 for SQL Server};'
    'SERVER=localhost,1433;'  # Or Docker container IP
    'DATABASE=IntelliSTOR;'
    'UID=sa;'
    'PWD=your_password;'
    'TrustServerCertificate=yes;'
)

conn = pyodbc.connect(conn_str)
```

### File Locations
- **MAP Files**: H:\OCBC\250_MapFiles\ (26,724 files)
- **Database Exports**: H:\section.csv (and others to be created)
- **Scripts**: Transfer from Windows machine

## Next Steps for New Claude Instance

1. Verify database connectivity
2. Run Phase 1 queries to understand schema
3. Export required CSV files
4. Analyze correlation between binary MAP structure and database
5. Create complete parser with database integration
6. Process all MAP files and generate deliverables

## Contact Information

Original analysis performed on Windows machine:
- Location: `C:\Users\freddievr\claude-projects\IntelliSTOR_Migration\4. Migration_Instances\`
- Scripts created: See "Working Scripts Created" section above

---

*Plan created: 2026-02-03*
*Updated: 2026-02-07 (corrected MAP file purpose — field-value search indices, not section definitions)*
*For: IntelliSTOR to new system migration*
*Binary MAP file analysis and field-value index extraction*
