# Map File Integration - Quick Reference

## Overview

The `extract_instances_sections.py` script now supports .MAP file integration to resolve missing segment names from the database. This feature ensures complete segment information even when the SECTION table has incomplete data.

---

## New Features (Version 2.0)

✓ **Automatic Fallback**: Uses .MAP files when database segment names are missing
✓ **Intelligent Caching**: Loads each .MAP file only once per session
✓ **Flexible ID Matching**: Handles both padded ('04') and unpadded ('4') segment IDs
✓ **Unknown Placeholder**: Marks segments as "Unknown" when not found anywhere
✓ **Comprehensive Logging**: Debug logs track all .MAP file operations

---

## Quick Start

### 1. Basic Usage

```bash
python extract_instances_sections.py \
  --server localhost \
  --database IntelliSTOR \
  --windows-auth \
  --start-year 2024 \
  --map-dir "C:\path\to\map\files"
```

### 2. Verify MAP File Contents

```bash
# Check specific MAP file
python verify_map_file.py "C:\path\to\260271NL.MAP"

# Search for specific segment
python verify_map_file.py "C:\path\to\260271NL.MAP" 850
```

### 3. Batch Verify All MAP Files

```bash
python batch_verify_maps.py "C:\path\to\map\files"
```

---

## Files in This Directory

| File | Purpose |
|------|---------|
| `extract_instances_sections.py` | Main extraction script with MAP file integration |
| `EXTRACT_INSTANCES_DOCUMENTATION.md` | Complete technical documentation (80+ pages) |
| `VERIFY_REPORT_SEGMENTS.md` | Segment verification guide with examples |
| `verify_map_file.py` | Tool to inspect individual MAP file contents |
| `batch_verify_maps.py` | Tool to scan and verify multiple MAP files |
| `QUICK_START.txt` | Basic usage instructions |
| `progress.txt` | Auto-generated progress tracking file |
| `Extract_Instances.log` | Auto-generated log file |

---

## Verifying Segment Extraction

### Example: Check "850-OCBC Bangkok Branch" in 260271NL

**Step 1:** Verify MAP file exists
```bash
dir "C:\path\to\map\files\260271NL.MAP"
```

**Step 2:** Check MAP file contains segment
```bash
python verify_map_file.py "C:\path\to\map\files\260271NL.MAP" 850
```

**Expected Output:**
```
Parsing MAP file: C:\path\to\map\files\260271NL.MAP
--------------------------------------------------------------------------------
Found 15 segments:

  Segment    1: Executive Summary
  Segment    2: Financial Overview
  ...
  Segment  850: OCBC Bangkok Branch <<< MATCH
  ...
================================================================================
Searching for segment ID: 850
================================================================================

✓ SUCCESS: Found segment 850
  Segment ID: 850
  Segment Name: OCBC Bangkok Branch
```

**Step 3:** Run extraction
```bash
python extract_instances_sections.py \
  --server localhost \
  --database IntelliSTOR \
  --windows-auth \
  --start-year 2024 \
  --map-dir "C:\path\to\map\files"
```

**Step 4:** Check log file
```bash
type Extract_Instances.log | findstr "260271NL.MAP"
```

**Expected Log Entry:**
```
2024-01-30 14:23:18 - DEBUG - Loaded 15 unique segments from 260271NL.MAP
```

**Step 5:** Verify output CSV

Open the generated CSV and check the Segments column:
```
Segments: "OCBC Bangkok Branch#850#0#10|..."
```

✓ Segment name correctly extracted from MAP file
✓ Not showing as "Unknown" or blank

---

## How It Works

### Processing Flow

```
Database Query Returns:
  Segment ID: 850
  Segment Name: NULL (missing from SECTION table)
  MAP Filename: 260271NL.MAP

       ↓

Script Checks MAP File Cache:
  - Is 260271NL.MAP already loaded? NO
  - Load and parse file
  - Extract segments using regex: r'\(\s+(\d+)-(.+?)\s{2,}'
  - Store in cache: {'850': 'OCBC Bangkok Branch', ...}

       ↓

Lookup Segment Name:
  - Check cache['260271NL.MAP']['850']
  - Found: 'OCBC Bangkok Branch'
  - Replace NULL with found name

       ↓

Output to CSV:
  Segments: "OCBC Bangkok Branch#850#0#10"
```

### Fallback Logic

```python
for each segment:
    if segment.name is empty:
        # Try MAP file
        name = map_cache.get_segment_name(map_filename, segment_id)

        if name:
            # Use MAP file name
            segment.name = name
        else:
            # Mark as unknown
            segment.name = 'Unknown'
            log.debug(f'Segment {segment_id} not found')
```

---

## Common Scenarios

### Scenario 1: Segment in Database
- **Database**: SECTION.NAME = "Financial Report"
- **MAP File**: Contains "850-Financial Report"
- **Result**: Uses database name (no MAP lookup needed)

### Scenario 2: Missing from Database, Found in MAP
- **Database**: SECTION.NAME = NULL
- **MAP File**: Contains "850-OCBC Bangkok Branch"
- **Result**: Uses MAP file name "OCBC Bangkok Branch"

### Scenario 3: Missing from Both Sources
- **Database**: SECTION.NAME = NULL
- **MAP File**: Does not contain segment 850
- **Result**: Uses placeholder "Unknown"
- **Log**: "Segment 850 not found in DB or map file 260271NL.MAP"

### Scenario 4: MAP File Not Found
- **Database**: SECTION.NAME = NULL
- **MAP File**: File doesn't exist
- **Result**: Uses placeholder "Unknown"
- **Log**: "Map file not found: C:\path\to\260271NL.MAP"

---

## Troubleshooting

### Issue: All segments showing as "Unknown"

**Check 1**: Verify --map-dir parameter
```bash
# Check directory exists
dir "C:\path\to\map\files"

# Check it contains .MAP files
dir "C:\path\to\map\files\*.MAP"
```

**Check 2**: Verify MAP filenames match database
```sql
-- Check MAP filenames in database
SELECT DISTINCT RTRIM(mf.FILENAME) AS MAP_FILENAME
FROM MAPFILE mf
ORDER BY MAP_FILENAME
```

**Check 3**: Review log file
```bash
type Extract_Instances.log | findstr /I "map"
```

---

### Issue: Specific segment shows as "Unknown"

**Check 1**: Verify segment exists in MAP file
```bash
python verify_map_file.py "C:\path\to\260271NL.MAP" 850
```

**Check 2**: Check segment ID format
- MAP file might use "850" or "0850"
- Script handles both formats automatically
- Verify regex pattern matches MAP file format

**Check 3**: Manually inspect MAP file
```bash
# Windows
type "C:\path\to\260271NL.MAP" | findstr "850"

# Linux/Mac
cat /path/to/260271NL.MAP | grep 850
```

---

### Issue: MAP file loading errors

**Check log file for:**
```
ERROR - Error parsing map file 260271NL.MAP: [error message]
```

**Common causes:**
- File permissions (ensure read access)
- File corruption
- Incorrect encoding (script uses errors='ignore' to handle this)

**Solution:**
```bash
# Check file permissions
icacls "C:\path\to\260271NL.MAP"

# Verify file is readable
type "C:\path\to\260271NL.MAP" > nul
```

---

## Performance Notes

### Caching Behavior

- Each MAP file loaded **once** per script execution
- Parsed segments stored in memory
- Subsequent lookups use cached data (instant)

### Memory Usage

- **Per MAP file**: ~1-5 MB depending on segment count
- **Total**: Depends on number of unique MAP files encountered
- **Example**: 100 MAP files × 3 MB avg = ~300 MB

### Disk I/O

- MAP file read on first access only
- Missing files tracked to avoid repeated checks
- Log file written incrementally

---

## Command-Line Reference

### New Parameter

```
--map-dir DIRECTORY
    Directory containing .MAP files for segment name lookups
    Default: . (current directory)
```

### Complete Example with All Options

```bash
python extract_instances_sections.py \
  --server localhost \
  --port 1433 \
  --database IntelliSTOR \
  --windows-auth \
  --start-year 2023 \
  --end-year 2024 \
  --timezone "Asia/Singapore" \
  --year-from-filename \
  --map-dir "C:\Users\freddievr\Downloads\RPTnMAP_Files" \
  --input "Report_Species.csv" \
  --output-dir "C:\output" \
  --quiet
```

---

## Output Format

### Segments Column Format

```
Name1#ID1#StartPage1#NumPages1|Name2#ID2#StartPage2#NumPages2|...
```

### Example Output

**CSV Row:**
```csv
RPT_SPECIES_NAME,FILENAME,Country,YEAR,AS_OF_TIMESTAMP,UTC,Segments,REPORT_FILE_ID
Bangkok_Report,260271NL.rpt,TH,2024,2024-01-30 14:00:00,2024-01-30 06:00:00,"Executive Summary#1#0#5|OCBC Bangkok Branch#850#5#10|Appendix#999#15#3",12345
```

**Segments Breakdown:**
1. **Executive Summary**: Pages 0-4 (5 pages)
2. **OCBC Bangkok Branch**: Pages 5-14 (10 pages)
3. **Appendix**: Pages 15-17 (3 pages)

---

## Advanced Usage

### Custom MAP File Processing

If you need to process MAP files differently, modify the `MapFileCache` class:

**Location:** `extract_instances_sections.py` lines 37-117

**Regex Pattern:** `r'\(\s+(\d+)-(.+?)\s{2,}'`

**Customize for different formats:**
```python
# Current pattern: ( 850-OCBC Bangkok Branch
matches = re.findall(r'\(\s+(\d+)-(.+?)\s{2,}', content)

# Alternative pattern: [850] OCBC Bangkok Branch
matches = re.findall(r'\[(\d+)\]\s+(.+?)\s{2,}', content)

# Alternative pattern: 850|OCBC Bangkok Branch
matches = re.findall(r'(\d+)\|(.+?)\s*$', content, re.MULTILINE)
```

---

## File Locations

### Expected Directory Structure

```
IntelliSTOR_Migration/
└── 4. Migration_Instances/
    ├── extract_instances_sections.py          # Main script
    ├── Report_Species.csv                     # Input CSV
    ├── verify_map_file.py                     # Verification tool
    ├── batch_verify_maps.py                   # Batch verification tool
    ├── EXTRACT_INSTANCES_DOCUMENTATION.md     # Full documentation
    ├── VERIFY_REPORT_SEGMENTS.md              # Verification guide
    ├── README_MAP_FILE_INTEGRATION.md         # This file
    ├── progress.txt                           # Auto-generated
    └── Extract_Instances.log                  # Auto-generated

MAP Files Directory (configurable):
C:\Users\freddievr\Downloads\RPTnMAP_Files\
├── 260270DF.MAP
├── 260271NL.MAP
├── 260272SG.MAP
└── ...

Output Directory (configurable):
C:\output\
├── Report1_2024.csv
├── Report2_2024.csv
├── progress.txt
└── Extract_Instances.log
```

---

## Documentation Files

### Quick Reference (This File)
**File:** `README_MAP_FILE_INTEGRATION.md`
**Purpose:** Quick start and common scenarios

### Complete Technical Documentation
**File:** `EXTRACT_INSTANCES_DOCUMENTATION.md`
**Purpose:** Comprehensive guide (80+ pages)
**Includes:**
- Full command-line reference
- Database schema requirements
- Architecture details
- Troubleshooting guide
- Performance tuning
- Security considerations

### Segment Verification Guide
**File:** `VERIFY_REPORT_SEGMENTS.md`
**Purpose:** Step-by-step verification procedures
**Includes:**
- Manual verification steps
- SQL queries for debugging
- Example scenarios
- Troubleshooting checklist

---

## Support Checklist

When reporting issues, provide:

- [ ] Command-line used (remove passwords)
- [ ] Relevant excerpt from `Extract_Instances.log`
- [ ] MAP file name and location
- [ ] Output from `verify_map_file.py` for the MAP file
- [ ] Sample segment ID that's failing
- [ ] Expected vs actual segment name
- [ ] SQL Server version (`SELECT @@VERSION`)

---

## Next Steps

1. **Verify Installation**
   ```bash
   python --version
   pip show pymssql pytz
   ```

2. **Test MAP File Verification**
   ```bash
   python verify_map_file.py "C:\path\to\test.MAP"
   ```

3. **Run Extraction with MAP Files**
   ```bash
   python extract_instances_sections.py --server localhost --database IntelliSTOR --windows-auth --start-year 2024 --map-dir "C:\path\to\maps"
   ```

4. **Review Results**
   - Check `Extract_Instances.log` for MAP file loading messages
   - Open generated CSV files to verify segment names
   - Confirm no "Unknown" placeholders where MAP files exist

---

## Version Information

- **Script Version**: 2.0
- **Documentation Version**: 1.0
- **Last Updated**: 2024-01-30
- **Python Compatibility**: 3.7+
- **SQL Server**: 2017+ required

---

## Related Files

- `QUICK_START.txt` - Basic usage instructions
- `EXTRACT_INSTANCES_DOCUMENTATION.md` - Complete technical reference
- `VERIFY_REPORT_SEGMENTS.md` - Detailed verification procedures

---

**For complete documentation, see:** `EXTRACT_INSTANCES_DOCUMENTATION.md`
