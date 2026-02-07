# Transfer Package for macOS Database Machine

## Files to Transfer

### 1. Plan Document
- **BINARY_MAP_ANALYSIS_PLAN.md** - Complete analysis plan and strategy

### 2. Working Scripts (all Python files)
- `batch_verify_binary_maps.py` - Count segments in all MAP files
- `parse_binary_map.py` - Analyze single MAP file
- `diagnose_map_files.py` - Debug MAP file content
- `analyze_map_structure.py` - Detailed hex analysis
- `extract_map_segments.py` - Extract segment metadata

### 3. Existing Scripts (already present)
- `extract_instances_sections.py` - Main extraction script
- `Extract_Instances.py` - Instance extractor
- `verify_map_file.py` - Text MAP verifier (won't work on binary MAPs)

## Quick Start Commands

### 1. Verify Database Access
```python
import pyodbc

conn_str = (
    'DRIVER={ODBC Driver 18 for SQL Server};'
    'SERVER=localhost,1433;'
    'DATABASE=IntelliSTOR;'
    'UID=sa;'
    'PWD=your_password;'
    'TrustServerCertificate=yes;'
)

conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

# Test queries
cursor.execute("SELECT COUNT(*) FROM MAPFILE")
print(f"Total MAP files in DB: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM SEGMENT_SPEC_TYPE")
print(f"Total segments in DB: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM SECTION")
print(f"Total sections in DB: {cursor.fetchone()[0]}")
```

### 2. Test Binary MAP Parser
```bash
# Test on single file
python batch_verify_binary_maps.py /path/to/mapfiles/ | head -20

# Full analysis of one file
python analyze_map_structure.py /path/to/mapfiles/25001001.MAP
```

### 3. Export Database Tables
```sql
-- Export to CSV (adjust paths as needed)
-- mapfile.csv
SELECT MAP_FILE_ID, FILENAME, REPORT_SPECIES_ID, DOMAIN_ID
FROM MAPFILE
ORDER BY MAP_FILE_ID;

-- segment_spec_type.csv
SELECT MAP_FILE_ID, SEGMENT_ID, NAME, SECTION_ID
FROM SEGMENT_SPEC_TYPE
ORDER BY MAP_FILE_ID, SEGMENT_ID;

-- map_to_sections.csv (complete mapping)
SELECT
    mf.MAP_FILE_ID,
    mf.FILENAME AS MAP_FILENAME,
    sst.SEGMENT_ID,
    sst.NAME AS SEGMENT_NAME,
    sst.SECTION_ID,
    s.NAME AS SECTION_NAME
FROM MAPFILE mf
LEFT JOIN SEGMENT_SPEC_TYPE sst ON sst.MAP_FILE_ID = mf.MAP_FILE_ID
LEFT JOIN SECTION s ON s.SECTION_ID = sst.SECTION_ID
ORDER BY mf.MAP_FILE_ID, sst.SEGMENT_ID;
```

## Key Findings Summary

### Binary MAP Structure (bytes 0-23)
```
0-11:   MAPHDR (UTF-16LE signature)
12-15:  Unknown (zeros)
16-17:  Flags/type
18-19:  SEGMENT COUNT ← This is what we need!
20-23:  File size/offset
```

### Segment Sections
- Each segment starts with `**ME` marker (UTF-16LE: 2a002a004d004500)
- After marker:
  - Bytes 4-7: Segment index (0, 1, 2...)
  - Bytes 8-11: Next section offset
  - Rest: Metadata (not fully decoded)

### Database Tables
- **MAPFILE**: MAP file records with FILENAME
- **SEGMENT_SPEC_TYPE**: Segment definitions per MAP file
- **SECTION**: Section names (already exported to H:\section.csv)

## Priority Tasks

1. ✅ Verify database connectivity
2. ✅ Export MAPFILE table to CSV
3. ✅ Export SEGMENT_SPEC_TYPE table to CSV
4. ✅ Export complete join (map_to_sections.csv)
5. ⏳ Correlate binary MAP segment count with database segment count
6. ⏳ Match segment order (binary index 0,1,2 → database SEGMENT_ID)
7. ⏳ Create complete segment name lookup
8. ⏳ Identify column extraction rules in binary data

## Expected Results

After completing the plan:
- CSV file with: MAP filename → Segment index → Segment name → Section name
- JSON lookup for fast access
- Updated scripts that work with binary MAP files
- Documentation of column extraction rules (if found)

## Notes

- Binary MAP files are NOT text files - they use UTF-16LE encoding
- Segment count is reliably at bytes 18-19 (little-endian 16-bit unsigned)
- Section names are in the database, not in binary MAP files
- MAP files are field-value search indices (ACCOUNT_NO indexing), NOT section/segment definitions
- Section segregation comes from RPT file SECTIONHDR — see `SECTION_SEGMENT_WORKFLOW.md`
- Some MAP files may have 0 segments (empty)
- Total MAP files: 26,724

## Support

If issues arise, refer to:
- Full plan: BINARY_MAP_ANALYSIS_PLAN.md
- Original analysis machine: Windows PC at `C:\Users\freddievr\claude-projects\IntelliSTOR_Migration\4. Migration_Instances\`
- This session's findings documented in both markdown files
