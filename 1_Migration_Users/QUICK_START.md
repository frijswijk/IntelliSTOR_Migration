# Quick Start Guide - Extract Unique RIDs

## Overview

Two programs to extract unique RIDs from permission CSV files. Choose Python for simplicity or C++ for speed.

## Files

```
extract_unique_rids.py      - Python script (ready to use)
extract_unique_rids.cpp     - C++ source code
extract_unique_rids         - C++ compiled binary (after build)
build_extract_rids.sh       - Build script for C++ (macOS/Linux)
build_extract_rids.bat      - Build script for C++ (Windows)
```

## Quick Usage

### Python (Easiest)

```bash
# Basic usage
python3 extract_unique_rids.py /path/to/Users_SG

# Custom output filename
python3 extract_unique_rids.py /path/to/Users_SG --output my_rids.csv
```

### C++ (Fastest)

```bash
# Build (one time only)
./build_extract_rids.sh

# Basic usage
./extract_unique_rids /path/to/Users_SG

# Custom output filename
./extract_unique_rids /path/to/Users_SG my_rids.csv
```

## Real-World Examples

### Example 1: Process Users_SG

**Python:**
```bash
python3 extract_unique_rids.py /Volumes/acasis/projects/python/ocbc/Migration_Data/Users_SG
```

**C++:**
```bash
./extract_unique_rids /Volumes/acasis/projects/python/ocbc/Migration_Data/Users_SG
```

### Example 2: Process Multiple Folders

**Bash Script:**
```bash
#!/bin/bash
for country in SG MY XX; do
    echo "Processing Users_${country}..."
    python3 extract_unique_rids.py "/path/to/Users_${country}"
done
```

### Example 3: Save with Country-Specific Filenames

**Python:**
```bash
python3 extract_unique_rids.py /path/to/Users_SG --output RIDs_SG.csv
python3 extract_unique_rids.py /path/to/Users_MY --output RIDs_MY.csv
python3 extract_unique_rids.py /path/to/Users_XX --output RIDs_XX.csv
```

### Example 4: Batch Processing (C++)

**Bash Script:**
```bash
#!/bin/bash
# Build first
./build_extract_rids.sh

# Process multiple countries
for country in SG MY XX; do
    ./extract_unique_rids "/data/Users_${country}" "RIDs_${country}.csv"
    echo "✓ Processed $country"
done
```

## Input Requirements

Each folder must contain these three CSV files:
- `STYPE_FOLDER_ACCESS.csv`
- `STYPE_REPORT_SPECIES_ACCESS.csv`
- `STYPE_SECTION_ACCESS.csv`

## Output

Creates a new CSV file (default: `Unique_RIDs.csv`) with:
- Column header: `RID`
- Deduplicated RID values
- Sorted numerically (ascending)

**Example output:**
```csv
RID
1120
1129
4590
10081
...
489744
```

## Which Version to Use?

### Use Python If:
- ✓ You want to run immediately (no compilation)
- ✓ You're on a machine without C++ compiler
- ✓ You're integrating with Python scripts
- ✓ You need cross-platform compatibility
- ✓ You're processing small to medium datasets

### Use C++ If:
- ✓ You need maximum speed
- ✓ You're processing very large datasets
- ✓ You're doing batch automation
- ✓ You have limited resources (memory/CPU)
- ✓ You want a standalone executable

## Typical Performance

**Test Data:** 115,074 rows (Users_SG folder)

| Version | Time | RIDs Extracted |
|---------|------|--------|
| Python | ~1-2 sec | 178 |
| C++ | ~0.2-0.5 sec | 178 |

## Common Tasks

### Task 1: Extract RIDs and Import to Excel

```bash
# Generate the CSV
python3 extract_unique_rids.py /path/to/Users_SG

# Open in Excel
open /path/to/Users_SG/Unique_RIDs.csv
```

### Task 2: Create a List of Unique RIDs Only

```bash
# Extract RIDs
python3 extract_unique_rids.py /path/to/Users_SG

# Get just the RID values (skip header)
tail -n +2 /path/to/Users_SG/Unique_RIDs.csv > rids_only.txt

# Or with awk
awk 'NR>1' /path/to/Users_SG/Unique_RIDs.csv > rids_only.txt
```

### Task 3: Compare RIDs Between Countries

```bash
# Extract RIDs for each country
python3 extract_unique_rids.py /path/to/Users_SG --output SG_RIDs.csv
python3 extract_unique_rids.py /path/to/Users_MY --output MY_RIDs.csv

# Find common RIDs
comm -12 \
  <(tail -n +2 SG_RIDs.csv | sort) \
  <(tail -n +2 MY_RIDs.csv | sort) > common_rids.txt

# Find unique to SG
comm -23 \
  <(tail -n +2 SG_RIDs.csv | sort) \
  <(tail -n +2 MY_RIDs.csv | sort) > unique_to_sg.txt
```

### Task 4: Check Number of Unique RIDs

```bash
# Python version - check output message
python3 extract_unique_rids.py /path/to/Users_SG 2>&1 | grep "Total unique"

# C++ version - check output message
./extract_unique_rids /path/to/Users_SG 2>&1 | grep "Total unique"

# Or count lines in output (subtract 1 for header)
wc -l /path/to/Users_SG/Unique_RIDs.csv
```

## Troubleshooting

### Error: "Folder not found"
```bash
# Check the folder path
ls -la /path/to/folder

# Verify the three CSV files exist
ls -la /path/to/folder/STYPE_*.csv
```

### Error: "CSV file not found"
```bash
# Verify all three files are in the folder
ls /path/to/Users_SG/ | grep STYPE_
```

### Error: "RID column not found"
```bash
# Check the CSV header
head -1 /path/to/Users_SG/STYPE_FOLDER_ACCESS.csv
```

### Python: "Command not found"
```bash
# Find Python location
which python3

# Use full path if needed
/usr/bin/python3 extract_unique_rids.py /path/to/Users_SG
```

### C++: "Command not found" (after build)
```bash
# Rebuild
./build_extract_rids.sh

# Verify the binary exists
ls -la extract_unique_rids

# Run from current directory
./extract_unique_rids /path/to/Users_SG
```

## Integration with Other Tools

### With grep to find specific RID patterns

```bash
# Extract RIDs, then search for ones in a specific range
python3 extract_unique_rids.py /path/to/Users_SG
grep -E "^[789][0-9]{4}$" /path/to/Users_SG/Unique_RIDs.csv
```

### With awk to analyze

```bash
# Count RIDs and show min/max
python3 extract_unique_rids.py /path/to/Users_SG
awk 'NR>1 {print}' /path/to/Users_SG/Unique_RIDs.csv | \
  awk 'NR==1 {min=$1; max=$1} {if($1<min) min=$1; if($1>max) max=$1} END {print "Count:", NR, "Min:", min, "Max:", max}'
```

### With Python for further processing

```python
import csv

# Read the RIDs
with open('/path/to/Users_SG/Unique_RIDs.csv') as f:
    reader = csv.DictReader(f)
    rids = [int(row['RID']) for row in reader]

print(f"Total RIDs: {len(rids)}")
print(f"Range: {min(rids)} - {max(rids)}")
print(f"Average: {sum(rids) / len(rids):.0f}")
```

## Automation Examples

### Cron Job (macOS/Linux)

```bash
# Run daily at 2 AM
0 2 * * * /path/to/extract_unique_rids /data/Users_SG >> /var/log/rids.log 2>&1
```

### Scheduled Task (Windows)

```batch
REM Run daily at 2 AM
schtasks /create /tn "Extract RIDs" /tr "C:\path\extract_unique_rids.exe C:\data\Users_SG" /sc daily /st 02:00
```

## Help & Support

### Python Help
```bash
python3 extract_unique_rids.py --help
```

### C++ Help
```bash
./extract_unique_rids
```

Both will show usage information and examples.

## See Also

- `README_Extract_Unique_RIDs.md` - Full documentation
- `IMPLEMENTATION_SUMMARY.md` - Technical details
- `Unique_RIDs_Summary.txt` - Previously generated RID list
- `Unique_RIDs_Detailed_Report.md` - Analysis of RIDs

## Version Info

- **Created:** 2026-02-09
- **Python:** 3.6+ (tested with 3.14.2)
- **C++:** C++17 or later
- **Status:** Production ready

---

**Ready to use! Choose your preferred version and run it on your data.**
