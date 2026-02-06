# Report Segment Verification Guide

## Purpose
This guide explains how to verify that report segments are correctly identified and extracted using the `extract_instances_sections.py` script with .MAP file integration.

---

## Example: Verifying 260271NL Report

### Report Details
- **Report File**: 260271NL.txt
- **Expected Segment**: "850-OCBC Bangkok Branch"
- **Purpose**: Verify segment extraction from database and .MAP file fallback

---

## Verification Steps

### Step 1: Locate Required Files

You need the following files for verification:

1. **Report File**: `260271NL.txt` (or `260271NL.rpt`)
   - The actual report document
   - Location: Typically in report storage directory

2. **MAP File**: `260271NL.MAP`
   - Contains segment definitions
   - Should be in the `--map-dir` directory
   - Format: Binary file with segment mappings

3. **Database Records**:
   - REPORT_INSTANCE records for this report
   - REPORT_INSTANCE_SEGMENT records
   - SECTION records (may be incomplete)

### Step 2: Check MAP File Contents

If you have the MAP file, verify it contains the expected segment:

```bash
# Method 1: Using Python script
python -c "import re; content = open('260271NL.MAP', 'r', encoding='utf-8', errors='ignore').read(); matches = re.findall(r'\(\s+(\d+)-(.+?)\s{2,}', content); print('\n'.join([f'{m[0]}: {m[1]}' for m in matches]))"

# Method 2: Using type command (Windows)
type "C:\path\to\map\files\260271NL.MAP"

# Method 3: Using cat command (Linux/Mac)
cat /path/to/map/files/260271NL.MAP
```

**Expected Output:**
```
01: Section Name 1
02: Section Name 2
...
850: OCBC Bangkok Branch
...
```

**Note**: MAP files may contain binary characters, so the output might include non-printable characters.

### Step 3: Create Verification Script

Create a Python script to parse and display MAP file segments:

**File: `verify_map_file.py`**

```python
#!/usr/bin/env python3
"""
Verify MAP File Contents
Displays all segments from a .MAP file in readable format
"""

import re
import sys
import os

def parse_map_file(map_file_path):
    """Parse .MAP file and return segment dictionary."""
    if not os.path.exists(map_file_path):
        print(f"Error: File not found: {map_file_path}")
        return None

    try:
        with open(map_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Regex pattern for segment definitions
        matches = re.findall(r'\(\s+(\d+)-(.+?)\s{2,}', content)

        segments = {}
        for seg_id, name in matches:
            segments[seg_id] = name.strip()

        return segments

    except Exception as e:
        print(f"Error parsing file: {e}")
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python verify_map_file.py <map_file_path> [segment_id_to_find]")
        print("Example: python verify_map_file.py 260271NL.MAP 850")
        sys.exit(1)

    map_file = sys.argv[1]
    search_id = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"Parsing MAP file: {map_file}")
    print("-" * 80)

    segments = parse_map_file(map_file)

    if segments is None:
        sys.exit(1)

    print(f"\nFound {len(segments)} segments:\n")

    # Display all segments
    for seg_id in sorted(segments.keys(), key=lambda x: int(x)):
        marker = " <<< MATCH" if search_id and seg_id == search_id.zfill(len(seg_id)) else ""
        print(f"  Segment {seg_id}: {segments[seg_id]}{marker}")

    # Search for specific segment if requested
    if search_id:
        print(f"\n" + "=" * 80)
        # Try both padded and unpadded versions
        found = False
        for test_id in [search_id, search_id.zfill(2), search_id.zfill(3)]:
            if test_id in segments:
                print(f"✓ Found segment {search_id}: {segments[test_id]}")
                found = True
                break

        if not found:
            print(f"✗ Segment {search_id} not found in MAP file")

    print("\n" + "-" * 80)
    print(f"Total unique segments: {len(segments)}")

if __name__ == '__main__':
    main()
```

**Usage:**

```bash
# List all segments
python verify_map_file.py "C:\path\to\260271NL.MAP"

# Search for specific segment ID
python verify_map_file.py "C:\path\to\260271NL.MAP" 850

# Expected output:
# Parsing MAP file: C:\path\to\260271NL.MAP
# --------------------------------------------------------------------------------
# Found 15 segments:
#
#   Segment 01: Executive Summary
#   Segment 02: Financial Overview
#   ...
#   Segment 850: OCBC Bangkok Branch <<< MATCH
#   ...
# ================================================================================
# ✓ Found segment 850: OCBC Bangkok Branch
# --------------------------------------------------------------------------------
# Total unique segments: 15
```

---

## Step 4: Run Extract Script with MAP Files

Run the extraction script pointing to the directory containing MAP files:

```bash
python extract_instances_sections.py \
  --server localhost \
  --database IntelliSTOR \
  --windows-auth \
  --start-year 2024 \
  --map-dir "C:\Users\freddievr\Downloads\RPTnMAP_Files" \
  --output-dir "C:\output"
```

### Step 5: Check Log File

After running, examine `Extract_Instances.log`:

**Look for:**

```
2024-01-30 14:23:15 - INFO - Map file directory: C:\Users\freddievr\Downloads\RPTnMAP_Files
2024-01-30 14:23:18 - DEBUG - Loaded 15 unique segments from 260271NL.MAP
```

**If segment not found:**
```
2024-01-30 14:23:20 - DEBUG - Segment 850 not found in DB or map file 260271NL.MAP
```

### Step 6: Verify Output CSV

Open the generated CSV file for the report and check the Segments column:

**Expected Format:**
```csv
RPT_SPECIES_NAME,FILENAME,Country,YEAR,AS_OF_TIMESTAMP,UTC,Segments,REPORT_FILE_ID
Bangkok_Report,260271NL.rpt,TH,2024,2024-01-30 14:00:00,2024-01-30 06:00:00,"OCBC Bangkok Branch#850#0#10",12345
```

**Segments Column Breakdown:**
- `OCBC Bangkok Branch` - Segment name (from .MAP file)
- `850` - Segment ID
- `0` - Start page number
- `10` - Number of pages

---

## Troubleshooting Segment Verification

### Issue 1: Segment Name Shows as "Unknown"

**Possible Causes:**
1. MAP file not found in --map-dir
2. Segment ID not in MAP file
3. MAP file format not matching expected pattern

**Solutions:**
1. Verify MAP file exists:
   ```bash
   dir "C:\path\to\map\files\260271NL.MAP"
   ```

2. Check MAP file format using verification script above

3. Review log file for warnings:
   ```
   WARNING - Map file not found: C:\path\to\map\files\260271NL.MAP
   ```

### Issue 2: Segment Name Blank (Empty String)

**Cause:** Database SECTION table has NULL name AND MAP file lookup failed

**Solution:**
1. Check if MAP_FILENAME is present in SQL query results
2. Verify SST_STORAGE and MAPFILE tables have correct joins
3. Test SQL query directly:

```sql
SELECT
    ri.REPORT_SPECIES_ID,
    ri.AS_OF_TIMESTAMP,
    RTRIM(mf.FILENAME) AS MAP_FILENAME
FROM REPORT_INSTANCE ri
LEFT JOIN SST_STORAGE sst
    ON ri.DOMAIN_ID = sst.DOMAIN_ID
    AND ri.REPORT_SPECIES_ID = sst.REPORT_SPECIES_ID
    AND ri.AS_OF_TIMESTAMP = sst.AS_OF_TIMESTAMP
    AND ri.REPROCESS_IN_PROGRESS = sst.REPROCESS_IN_PROGRESS
LEFT JOIN MAPFILE mf
    ON sst.MAP_FILE_ID = mf.MAP_FILE_ID
WHERE ri.REPORT_SPECIES_ID = [your_report_id]
```

### Issue 3: Multiple Segments in One Report

If the report contains multiple segments, they should be pipe-delimited:

**Example:**
```
"Executive Summary#1#0#5|OCBC Bangkok Branch#850#5#10|Appendix#999#15#3"
```

**Verify:**
- All segments are present
- Correct order (sorted by SEGMENT_NUMBER)
- Each segment has 4 fields (Name#ID#StartPage#NumPages)

---

## Manual Database Verification

### Query 1: Check Report Instance Exists

```sql
SELECT
    ri.REPORT_SPECIES_ID,
    ri.AS_OF_TIMESTAMP,
    rf.FILENAME
FROM REPORT_INSTANCE ri
LEFT JOIN RPTFILE_INSTANCE rfi
    ON ri.DOMAIN_ID = rfi.DOMAIN_ID
    AND ri.REPORT_SPECIES_ID = rfi.REPORT_SPECIES_ID
    AND ri.AS_OF_TIMESTAMP = rfi.AS_OF_TIMESTAMP
    AND ri.REPROCESS_IN_PROGRESS = rfi.REPROCESS_IN_PROGRESS
LEFT JOIN RPTFILE rf
    ON rfi.RPT_FILE_ID = rf.RPT_FILE_ID
WHERE rf.FILENAME LIKE '%260271NL%'
```

### Query 2: Check Segments for Report

```sql
SELECT
    ris.SEGMENT_NUMBER,
    sec.NAME AS DB_NAME,
    ris.START_PAGE_NUMBER,
    ris.NUMBER_OF_PAGES
FROM REPORT_INSTANCE ri
LEFT JOIN REPORT_INSTANCE_SEGMENT ris
    ON ri.DOMAIN_ID = ris.DOMAIN_ID
    AND ri.REPORT_SPECIES_ID = ris.REPORT_SPECIES_ID
    AND ri.AS_OF_TIMESTAMP = ris.AS_OF_TIMESTAMP
    AND ri.REPROCESS_IN_PROGRESS = ris.REPROCESS_IN_PROGRESS
LEFT JOIN SECTION sec
    ON ris.DOMAIN_ID = sec.DOMAIN_ID
    AND ris.REPORT_SPECIES_ID = sec.REPORT_SPECIES_ID
    AND ris.SEGMENT_NUMBER = sec.SECTION_ID
WHERE ri.REPORT_SPECIES_ID = [report_id]
ORDER BY ris.SEGMENT_NUMBER
```

**Look for:**
- Segment with SEGMENT_NUMBER = 850
- DB_NAME might be NULL (this is where MAP file helps)

### Query 3: Check MAP File Association

```sql
SELECT
    ri.REPORT_SPECIES_ID,
    ri.AS_OF_TIMESTAMP,
    mf.FILENAME AS MAP_FILENAME,
    mf.MAP_FILE_ID
FROM REPORT_INSTANCE ri
LEFT JOIN SST_STORAGE sst
    ON ri.DOMAIN_ID = sst.DOMAIN_ID
    AND ri.REPORT_SPECIES_ID = sst.REPORT_SPECIES_ID
    AND ri.AS_OF_TIMESTAMP = sst.AS_OF_TIMESTAMP
    AND ri.REPROCESS_IN_PROGRESS = sst.REPROCESS_IN_PROGRESS
LEFT JOIN MAPFILE mf
    ON sst.MAP_FILE_ID = mf.MAP_FILE_ID
WHERE ri.REPORT_SPECIES_ID = [report_id]
```

**Expected Result:**
- MAP_FILENAME should be something like '260271NL.MAP'
- If NULL, MAP file association is missing

---

## Complete Verification Example

### Scenario: Verify "OCBC Bangkok Branch" segment extraction

**Step 1:** Locate files
```bash
# Find MAP file
dir "C:\Users\freddievr\Downloads\RPTnMAP_Files\260271NL.MAP"

# Verify it exists
# Expected: File found with size > 0 bytes
```

**Step 2:** Parse MAP file
```bash
python verify_map_file.py "C:\Users\freddievr\Downloads\RPTnMAP_Files\260271NL.MAP" 850

# Expected output:
# ✓ Found segment 850: OCBC Bangkok Branch
```

**Step 3:** Run extraction
```bash
python extract_instances_sections.py \
  --server localhost \
  --database IntelliSTOR \
  --windows-auth \
  --start-year 2024 \
  --map-dir "C:\Users\freddievr\Downloads\RPTnMAP_Files"
```

**Step 4:** Check log
```bash
type Extract_Instances.log | findstr /C:"260271NL.MAP"

# Expected:
# 2024-01-30 14:23:18 - DEBUG - Loaded 15 unique segments from 260271NL.MAP
```

**Step 5:** Verify CSV output
```bash
# Open the generated CSV file
# Find row with FILENAME containing "260271NL"
# Check Segments column contains: "OCBC Bangkok Branch#850#..."
```

**Step 6:** Validate segment data
- Segment name: "OCBC Bangkok Branch" (from MAP file)
- Segment ID: 850
- Start page and page count should match database values

---

## Expected Results Summary

For report 260271NL with segment "850-OCBC Bangkok Branch":

### Database State
- REPORT_INSTANCE: Contains record for this report
- REPORT_INSTANCE_SEGMENT: Contains segment with SEGMENT_NUMBER=850
- SECTION: MAY have NULL or missing record for this segment
- SST_STORAGE + MAPFILE: Links to 260271NL.MAP

### MAP File (260271NL.MAP)
- Contains line: `( 850-OCBC Bangkok Branch` (with padding)
- Parsed by regex: `r'\(\s+(\d+)-(.+?)\s{2,}'`
- Stored in cache as: `{'850': 'OCBC Bangkok Branch', ...}`

### Output CSV
- Segments column includes: `OCBC Bangkok Branch#850#[start_page]#[num_pages]`
- Segment name correctly extracted from MAP file (not "Unknown")

### Log File
- Shows MAP file loaded successfully
- No "Segment 850 not found" warnings
- Confirms segment processing completed

---

## Quick Verification Checklist

- [ ] MAP file exists in --map-dir location
- [ ] MAP file contains segment ID in question (use verify_map_file.py)
- [ ] Database has REPORT_INSTANCE record for the report
- [ ] Database has REPORT_INSTANCE_SEGMENT with correct SEGMENT_NUMBER
- [ ] SST_STORAGE links report instance to MAP file
- [ ] Script ran without errors (check Extract_Instances.log)
- [ ] Output CSV contains correct segment name (not "Unknown" or blank)
- [ ] Segment format is correct: `Name#ID#StartPage#NumPages`

---

## Additional Tools

### Tool 1: Batch Verify Multiple MAP Files

**File: `batch_verify_maps.py`**

```python
import os
import re
import sys

def verify_all_maps(map_dir):
    """Verify all MAP files in directory."""
    print(f"Scanning directory: {map_dir}\n")

    map_files = [f for f in os.listdir(map_dir) if f.upper().endswith('.MAP')]

    for map_file in sorted(map_files):
        path = os.path.join(map_dir, map_file)
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            matches = re.findall(r'\(\s+(\d+)-(.+?)\s{2,}', content)
            print(f"{map_file:30} - {len(matches):3} segments")

        except Exception as e:
            print(f"{map_file:30} - ERROR: {e}")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python batch_verify_maps.py <map_directory>")
        sys.exit(1)

    verify_all_maps(sys.argv[1])
```

**Usage:**
```bash
python batch_verify_maps.py "C:\Users\freddievr\Downloads\RPTnMAP_Files"

# Output:
# 260270DF.MAP                   -  12 segments
# 260271NL.MAP                   -  15 segments
# 260272SG.MAP                   -   8 segments
```

---

## Contact and Support

If verification fails or segments are not extracted correctly:

1. Review the [Troubleshooting](#troubleshooting-segment-verification) section
2. Check database schema matches requirements
3. Verify MAP file format is correct
4. Review Extract_Instances.log for detailed error messages
5. Run manual SQL queries to verify database state

---

**Document Version**: 1.0
**Last Updated**: 2024-01-30
**Related Script**: extract_instances_sections.py v2.0
