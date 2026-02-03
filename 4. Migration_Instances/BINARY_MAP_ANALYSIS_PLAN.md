# Binary MAP File Analysis and Extraction Plan

## Executive Summary

We are analyzing 26,724 binary MAP files from an IntelliSTOR system. These MAP files serve two purposes:
1. **Segment/Section definitions** - Identifying sections within reports
2. **Multi-row column extraction rules** - Metadata for extracting tabular data from report pages

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

### KEY INSIGHT: REPORT_INSTANCE_SEGMENT Table

**Critical Discovery** (User hypothesis - needs verification):

The `REPORT_INSTANCE_SEGMENT` table likely provides the missing link:
- `SEGMENT_NUMBER` field corresponds to the position in the binary MAP file (0, 1, 2...)
- This matches the `**ME` marker index in the binary structure
- `SECTION_ID` field links to the SECTION table for actual segment names

**Relationship Chain:**
```
Binary MAP File (25001001.MAP)
  └─ Segment at position 0 (first **ME marker)
      └─ REPORT_INSTANCE_SEGMENT.SEGMENT_NUMBER = 0
          └─ REPORT_INSTANCE_SEGMENT.SECTION_ID = 669
              └─ SECTION.NAME = "501 49"
```

This means segment names are NOT stored in the binary MAP files themselves, but rather:
1. Binary MAP files define the STRUCTURE (how many segments, their positions)
2. Database stores the MEANING (which section each segment number refers to)

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

-- 4. REPORT_INSTANCE_SEGMENT table - KEY TABLE for linking!
-- HYPOTHESIS: segment_number corresponds to position in binary MAP file (0,1,2...)
--             and links to SECTION_ID for the actual section name
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

### HYPOTHESIS (User Insight - HIGH PRIORITY TO VERIFY)

**REPORT_INSTANCE_SEGMENT table is the key linking mechanism:**

```
Binary MAP File Position (0, 1, 2...)
    ↓
REPORT_INSTANCE_SEGMENT.SEGMENT_NUMBER
    ↓
REPORT_INSTANCE_SEGMENT.SECTION_ID
    ↓
SECTION.NAME (actual segment name like "501 49")
```

**Key Assumption:**
- `SEGMENT_NUMBER` in REPORT_INSTANCE_SEGMENT corresponds to the segment index in the binary MAP file
- The `**ME` marker at position 0 = SEGMENT_NUMBER 0
- The `**ME` marker at position 1 = SEGMENT_NUMBER 1, etc.
- The SECTION_ID links to the SECTION table to get the actual name

**Verification Query:**
```sql
-- For a specific MAP file, compare:
-- 1. Binary segment count (from bytes 18-19)
-- 2. Database segment count (from REPORT_INSTANCE_SEGMENT)

SELECT
    ri.REPORT_INSTANCE_ID,
    mf.FILENAME AS MAP_FILENAME,
    COUNT(DISTINCT ris.SEGMENT_NUMBER) AS db_segment_count,
    STRING_AGG(CAST(ris.SEGMENT_NUMBER AS VARCHAR), ',') AS segment_numbers,
    STRING_AGG(s.NAME, ' | ') AS segment_names
FROM REPORT_INSTANCE ri
JOIN MAPFILE mf ON mf.MAP_FILE_ID = ri.MAP_FILE_ID
JOIN REPORT_INSTANCE_SEGMENT ris ON ris.REPORT_INSTANCE_ID = ri.REPORT_INSTANCE_ID
JOIN SECTION s ON s.SECTION_ID = ris.SECTION_ID
WHERE mf.FILENAME = '25001001.MAP'
GROUP BY ri.REPORT_INSTANCE_ID, mf.FILENAME;
```

### Tasks

1. **Verify the hypothesis**:
   - Pick 5-10 MAP files where we know the binary segment count
   - Query REPORT_INSTANCE_SEGMENT for those MAP files
   - Verify: Binary segment count = MAX(SEGMENT_NUMBER) + 1
   - Verify: SEGMENT_NUMBER values are 0, 1, 2... (sequential)

2. **Compare segment counts**:
   - Binary MAP files: Read segment count from bytes 18-19
   - Database: Count segments per MAP_FILE_ID via REPORT_INSTANCE_SEGMENT
   - Verify they match

3. **Identify segment ordering**:
   - Binary MAP files have segments at specific `**ME` marker positions (0, 1, 2...)
   - REPORT_INSTANCE_SEGMENT has SEGMENT_NUMBER (likely 0, 1, 2...)
   - Verify: Binary position index = SEGMENT_NUMBER

3. **Create lookup table** (based on verified hypothesis):
   ```python
   # map_file_lookup.json
   {
       "25001001.MAP": {
           "map_file_id": 12345,
           "binary_segment_count": 3,
           "segments": [
               {
                   "segment_number": 0,      # Position in binary MAP (at **ME marker #0)
                   "section_id": 669,        # From REPORT_INSTANCE_SEGMENT
                   "section_name": "501 49"  # From SECTION table
               },
               {
                   "segment_number": 1,      # Position in binary MAP (at **ME marker #1)
                   "section_id": 670,
                   "section_name": "503 00"
               },
               {
                   "segment_number": 2,      # Position in binary MAP (at **ME marker #2)
                   "section_id": 671,
                   "section_name": "504 00"
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
Extracts all segment information using database lookups

Requires:
    - map_file_lookup.json (from Phase 2)
    - Database connection OR CSV exports

Usage:
    python parse_binary_map_complete.py <map_file_path>
    python parse_binary_map_complete.py --batch <map_directory>
"""

import struct
import json

def parse_binary_map_with_db(map_file_path, lookup_data):
    """
    Parse binary MAP file and enrich with database information

    Returns:
        {
            'filename': '25001001.MAP',
            'segment_count': 3,
            'segments': [
                {
                    'index': 0,
                    'segment_id': 850,
                    'segment_name': 'Header Section',
                    'section_id': 669,
                    'section_name': '501 49',
                    'me_marker_position': 90,
                    'next_offset': 386,
                    'metadata': {...}
                }
            ]
        }
    """
    # Implementation here
    pass
```

### Create: `batch_extract_all_segments.py`

Batch process all 26,724 MAP files and create:
- **segments_complete.csv** - All segments with names
- **segments_summary.json** - Summary statistics
- **missing_segments.txt** - MAP files with missing data

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

### 1. Complete Segment Mapping

**File: `map_segments_complete.csv`**

Columns:
```
MAP_FILENAME, MAP_FILE_ID, SEGMENT_INDEX, SEGMENT_ID, SEGMENT_NAME, SECTION_ID, SECTION_NAME, REPORT_SPECIES_ID, DOMAIN_ID
```

Example:
```csv
25001001.MAP,12345,0,850,"Header Section",669,"501 49",0,1
25001001.MAP,12345,1,851,"Detail Section",670,"503 00",0,1
25001001.MAP,12345,2,852,"Footer Section",671,"504 00",0,1
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
        "segments_without_names": 5
    }
}
```

### 3. Python Module for Reuse

**File: `intellistor_map_parser.py`**

```python
"""
IntelliSTOR Binary MAP File Parser
Reusable module for parsing binary MAP files with database lookups
"""

class MapFileParser:
    def __init__(self, db_connection=None, lookup_file=None):
        """Initialize with database connection or lookup JSON"""
        pass

    def parse_file(self, map_file_path):
        """Parse single MAP file"""
        pass

    def get_segment_names(self, map_file_path):
        """Get list of segment names for MAP file"""
        pass

    def get_column_rules(self, map_file_path):
        """Extract column extraction rules if present"""
        pass
```

## Phase 6: Integration with Existing Scripts

Update existing scripts to use the new MAP parser:

1. **extract_instances_sections.py**:
   - Replace text MAP file parsing with binary MAP parser
   - Use database-backed segment name lookups

2. **Extract_Instances.py**:
   - Add segment name resolution
   - Integrate column extraction rules

## Success Criteria

- [ ] All 26,724 MAP files successfully parsed
- [ ] Segment counts match between binary files and database
- [ ] All segment names resolved from database
- [ ] Column extraction rules identified and documented
- [ ] Reusable Python module created
- [ ] Existing migration scripts updated

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
*For: IntelliSTOR to new system migration*
*Binary MAP file analysis and segment extraction*
