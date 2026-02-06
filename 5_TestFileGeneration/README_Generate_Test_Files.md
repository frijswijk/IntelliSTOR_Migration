# Generate_Test_Files.py - Test File Generator for Report_Species

## Overview

Generate test files (.txt, .afp, .pdf) for Report_Species instances by copying template files and renaming them based on instance data from CSV files.

**Features:** Batch processing (default: 5 species per run), auto-resume capability, real-time logging, crash-safe progress tracking.

**Date:** 2026-01-26
**Author:** Generated using Claude Code

---

## Features

✅ **Filters Report Species** - Processes only species where `In_Use = 1`
✅ **Batch Processing** - Process N species per run (default: 5), auto-resume for next batch
✅ **Resume Capability** - Progress tracked in JSON file, can resume after interruption
✅ **Real-time Logging** - Logs flushed immediately to disk, survives crashes
✅ **Crash-safe** - All progress written immediately to disk
✅ **Flexible Range** - Start from specific ID and process N species
✅ **Wildcard Matching** - Automatically finds instance CSV files (e.g., BC2035P*.csv)
✅ **All Files in One Folder** - All test files placed directly in TargetFolder
✅ **Random File Type** - Each instance gets .TXT + random .AFP or .PDF
✅ **Quiet Mode** - Progress on single line with comprehensive final statistics
✅ **Comprehensive Validation** - Validates all inputs before processing

---

## Prerequisites

### Required Files

1. **Report_Species.csv** - Main species list with columns:
   - Report_Species_Id (numeric ID)
   - Report_Species_Name (e.g., BC2035P)
   - In_Use (1 = active, 0 = inactive)

2. **Instance CSV Files** - In FolderExtract directory:
   - Format: {Report_Species_Name}_YYYY.csv (e.g., BC2035P_2024.csv)
   - Required columns: FILENAME, YEAR

3. **Template Files** - In LocationTestFile directory:
   - test.txt
   - test.afp
   - test.pdf

---

## Usage

### Basic Syntax

```bash
python Generate_Test_Files.py \
    --ReportSpecies <path_to_csv> \
    --FolderExtract <instance_csv_folder> \
    --TargetFolder <output_folder> \
    [OPTIONS]
```

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--ReportSpecies` | No | `Report_Species.csv` | Path to Report_Species.csv |
| `--FolderExtract` | **Yes** | - | Folder with instance CSV files |
| `--TargetFolder` | **Yes** | - | Output directory (all files placed here) |
| `--Number` | No | `5` | Number of species to process per run (0 = all) |
| `--StartReport_Species_Id` | No | `0` (auto-resume) | Starting species ID (0 = resume from progress) |
| `--LocationTestFile` | No | `.` (current) | Template files location |
| `--reset-progress` | No | `false` | Start from beginning, ignore existing progress |
| `--quiet` | No | `false` | Quiet mode (progress on single line) |

---

## Examples

### Example 1: Process First 2 Species

```bash
python Generate_Test_Files.py \
    --FolderExtract Output_Extract_Instances \
    --TargetFolder TestOutput \
    --Number 2
```

**Result:**
- Processes first 2 species where In_Use=1
- Creates TestOutput\2024\ and TestOutput\2025\ folders
- Generates test files for all instances

### Example 2: Process From Specific ID

```bash
python Generate_Test_Files.py \
    --FolderExtract Output_Extract_Instances \
    --TargetFolder TestOutput \
    --StartReport_Species_Id 3 \
    --Number 5
```

**Result:**
- Starts from Report_Species_Id = 3
- Processes 5 species (starting from ID 3)

### Example 3: Quiet Mode

```bash
python Generate_Test_Files.py \
    --FolderExtract Output_Extract_Instances \
    --TargetFolder TestOutput \
    --Number 1 \
    --quiet
```

**Result:**
- Progress displayed on single line
- Final statistics at completion
- Minimal console output

### Example 4: Process All Species

```bash
python Generate_Test_Files.py \
    --FolderExtract Output_Extract_Instances \
    --TargetFolder TestOutputAll
```

**Result:**
- Processes ALL species where In_Use=1 (may be 30,000+)
- Can take significant time

### Example 5: Custom Paths

```bash
python Generate_Test_Files.py \
    --ReportSpecies "C:\Data\Reports\Report_Species.csv" \
    --FolderExtract "C:\Data\Instances" \
    --LocationTestFile "C:\Templates" \
    --TargetFolder "C:\Output\TestFiles"
```

### Example 6: Batch Processing (Default)

```bash
# Process 5 species (default), run multiple times to complete all
python Generate_Test_Files.py \
    --FolderExtract Output_Extract_Instances \
    --TargetFolder TestOutput
# Automatically resumes from where it left off

# Process 10 species per run
python Generate_Test_Files.py \
    --FolderExtract Output_Extract_Instances \
    --TargetFolder TestOutput \
    --Number 10

# Process all species at once (0 = unlimited)
python Generate_Test_Files.py \
    --FolderExtract Output_Extract_Instances \
    --TargetFolder TestOutput \
    --Number 0
```

### Example 7: Resume After Interruption

```bash
# First run (interrupted)
python Generate_Test_Files.py \
    --FolderExtract Output_Extract_Instances \
    --TargetFolder TestOutput
# ... Ctrl+C pressed after 3 species ...

# Resume (same command) - automatically picks up from species 4
python Generate_Test_Files.py \
    --FolderExtract Output_Extract_Instances \
    --TargetFolder TestOutput
```

### Example 8: Reset Progress and Start Over

```bash
python Generate_Test_Files.py \
    --FolderExtract Output_Extract_Instances \
    --TargetFolder TestOutput \
    --reset-progress
```

---

## Output Structure

### Folder Structure

All files are placed directly in the TargetFolder (no year subfolders):

```
TargetFolder\
  2418405N.TXT
  2418405N.AFP
  2412301B.TXT
  2412301B.PDF
  2511304A.TXT
  2511304A.PDF
  2511204S.TXT
  2511204S.AFP
```

### File Naming

- **Source**: FILENAME column from instance CSV (e.g., `2511304A.RPT`)
- **Output**: Strip `.RPT` extension, add `.TXT` / `.AFP` / `.PDF`
- **Example**: `2511304A.RPT` → `2511304A.TXT` + `2511304A.AFP` or `.PDF`

### File Selection

For each instance, the script generates files based on a distribution pattern:
- **10% (1 out of 10)**: `.AFP` + `.TXT` (from test.afp and test.txt)
- **20% (2 out of 10)**: `.PDF` + `.TXT` (from test.pdf and test.txt)
- **70% (7 out of 10)**: ONLY `.TXT` (from FRX16.txt or CFSUL003.txt, randomly chosen)

### Progress and Log Files

The script creates files in the script directory:
```
Script Directory\
  generate_test_files_progress.json    # Progress tracker (deleted when complete)
  generate_test_files.log              # Full detailed log with timestamps
```

**Progress File:**
- Tracks last completed species ID
- Preserves statistics across runs
- Deleted automatically when all species are processed
- Can be manually deleted or use `--reset-progress` to start over

**Log File:**
- All operations logged with timestamps
- Real-time writing (survives crashes)
- Append mode (grows with each run)
- Contains detailed information for troubleshooting

---

## Resume Capability

The script tracks progress after each species is processed. If interrupted (Ctrl+C, power failure, etc.):

1. Progress is saved in `generate_test_files_progress.json`
2. Tracks last completed species ID and cumulative statistics
3. On restart, automatically resumes from next species
4. Statistics continue from where they left off (not reset)

### Interrupting the Script

Press **Ctrl+C** to interrupt. The script will:
- Save current progress
- Log the interruption
- Display current statistics
- Exit gracefully

### Resuming After Interruption

Simply run the same command again (or use the batch file). The script will:
- Detect existing progress file
- Resume from next species after last completed
- Continue accumulating statistics

### Resetting Progress

To start from scratch:
```bash
python Generate_Test_Files.py ... --reset-progress
```

Or manually delete `generate_test_files_progress.json`.

### Batch Processing Flow

With default `--Number 5`:
1. First run: Processes species 1-5, saves progress
2. Second run: Automatically resumes from species 6-10, saves progress
3. Third run: Automatically resumes from species 11-15, saves progress
4. Continues until all species are processed
5. Progress file deleted when complete

---

## Statistics Output

After completion, the tool displays:

```
================================================================================
Test File Generation Complete
================================================================================
Report Species Processed: 10
Total Instances: 1,234
Total Files Created: 2,468

Files by Year:
  2024: 1,200 files (600 instances)
  2025: 1,268 files (634 instances)

Files by Type:
  TXT: 1,234
  AFP: 615
  PDF: 619

Processing Time: 12.5 seconds
================================================================================
```

---

## Error Handling

### Validation Errors

The tool validates inputs before processing:

**Missing Report_Species.csv:**
```
ERROR: Report_Species.csv not found: C:\path\to\Report_Species.csv
```

**Missing Template Files:**
```
ERROR: Missing template files: test.afp, test.pdf
  Location: C:\Templates
```

**No Instance CSV Files:**
```
ERROR: No CSV files found in: C:\Data\Instances
```

### Processing Warnings

**No Instance CSV Found:**
```
WARNING: No instance CSV found for BC2035P
```
→ The tool skips this species and continues with others

---

## Troubleshooting

### Issue: "No report species found matching criteria"

**Causes:**
- `StartReport_Species_Id` is too high (no species with higher IDs)
- No species have `In_Use = 1`
- Report_Species.csv is empty or malformed

**Solution:**
- Check Report_Species.csv content
- Verify In_Use column values
- Try without `--StartReport_Species_Id`

### Issue: "Missing template files"

**Causes:**
- test.txt, test.afp, or test.pdf not in LocationTestFile directory

**Solution:**
- Create template files in the specified location
- Or use `--LocationTestFile` to point to correct directory

### Issue: Permission Denied

**Causes:**
- No write permission to TargetFolder

**Solution:**
- Run with appropriate permissions
- Choose different TargetFolder location

### Issue: "Corrupted progress file"

**Causes:**
- Progress file was modified or corrupted

**Solution:**
- Use `--reset-progress` to start over:
  ```bash
  python Generate_Test_Files.py ... --reset-progress
  ```
- Or manually delete `generate_test_files_progress.json`

### Issue: Script resumes from wrong species

**Causes:**
- Using `--StartReport_Species_Id` when progress file exists

**Solution:**
- Remove `--StartReport_Species_Id` parameter to use auto-resume
- Or use `--reset-progress` to start fresh from specified ID

---

## Performance Notes

### File Copy Speed
- Uses `shutil.copy2()` (fast, preserves metadata)
- Processes 1000+ instances in seconds

### Memory Usage
- Streams CSV files row-by-row
- Low memory footprint even with 30,000+ species

### Progress Display
- Quiet mode: Progress on same line (carriage return)
- Non-quiet: Verbose output for each species

---

## Development

### Testing the Script

**Syntax Check:**
```bash
python -m py_compile Generate_Test_Files.py
```

**Help Output:**
```bash
python Generate_Test_Files.py --help
```

**Test Run (2 species):**
```bash
python Generate_Test_Files.py \
    --FolderExtract Output_Extract_Instances \
    --TargetFolder TestOutput \
    --Number 2
```

---

## File Locations

### Working Directory
```
C:\Users\freddievr\Documents\isis\Sales\proposal and lettes\2025\SG - OCBC\Project-Scoping\Intellistor\IST_DB_Schema\Migration_Instances\
```

### Key Files
- **Script:** Generate_Test_Files.py
- **Report Species:** Report_Species.csv (30,418 rows)
- **Instance CSVs:** Output_Extract_Instances\*.csv (12 files)
- **Templates:** test.txt, test.afp, test.pdf

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 2.0 | 2026-01-26 | Batch processing and resume capability |
|  |  | - ⭐ Batch processing: `--Number` default changed to 5 species per run |
|  |  | - ⭐ Resume capability: Auto-resume from last processed species |
|  |  | - ⭐ Real-time logging: Logs flushed immediately to disk |
|  |  | - ⭐ Progress tracking: Persistent progress across interruptions |
|  |  | - `--reset-progress` parameter to start fresh |
|  |  | - Statistics preserved across runs |
|  |  | - Crash-safe: All progress written immediately |
| 1.0 | 2026-01-23 | Initial release with full functionality |

---

## Support

For issues or questions:
1. Check this README for troubleshooting
2. Verify input files and paths
3. Run with `--help` for usage information
4. Test with small sample first (--Number 1)

---

**End of Documentation**
