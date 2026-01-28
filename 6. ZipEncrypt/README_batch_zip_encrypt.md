# Batch Zip and Encrypt Script

## Overview

This Python script automates the process of:
1. Reading report species from `Report_Species.csv`
2. Looking up corresponding instance CSVs in `Output_Extract_Instances/`
3. Extracting filenames and finding matching files using wildcards
4. Creating password-protected 7z archives organized by year
5. **Resume capability**: Can be interrupted and resumed from last position
6. **Complete audit trail**: Logs all processing to `compress-log.csv` for proof of work

## Features

- **Year-based organization**: Archives saved as `{output_folder}\{YEAR}\{filename}.7z`
- **Batch processing**: Process N species per run (default: 5), auto-resume for next batch
- **Resume capability**: Progress tracked in JSON file, can resume after interruption
- **Wildcard matching**: Finds all files matching pattern `{filename}.*`
- **AES-256 encryption**: Strong encryption with header encryption (hides filenames) - or no encryption if password omitted
- **Real-time logging**: Logs flushed immediately to disk, survives crashes
- **Real-time audit trail**: `compress-log.csv` written in append mode, survives crashes
- **Real-time CSV updates**: Instance CSVs updated immediately after each file is processed
- **Delete after compress**: Optional deletion of source files after successful compression
- **Single-line progress**: In quiet mode, progress displays on one line (no scrolling)
- **Crash-safe**: All progress and logs written immediately to disk
- **Error handling**: Graceful handling of missing files, corrupted data, etc.
- **Persistent statistics**: Statistics saved across interruptions

## Requirements

### Software
- **Python 3.7+**
- **7-Zip**: Must be installed and accessible
  - Download: https://www.7-zip.org/
  - Windows: Install and add to PATH, or specify full path with `--7zip-path`

### Python Modules
All standard library (no additional pip installs required):
- csv, argparse, subprocess, pathlib, glob, logging, json, sys, os

## Input Files

### Report_Species.csv
Contains report species list with columns:
- `Report_Species_Id`: Unique ID
- `Report_Species_Name`: Species name (e.g., "BC2060P")
- `Report_Species_DisplayName`: Display name
- `Country_Code`: Country code
- `In_Use`: Whether species is active (0 or 1)

### Instance CSVs (in Output_Extract_Instances/)
Named as `{species_name}_*.csv` (e.g., `BC2060P_2024.csv`)

Contains columns:
- `RPT_SPECIES_NAME`: Report species name
- `FILENAME`: Filename with .RPT extension (e.g., "2511304H.RPT")
- `YEAR`: Year for organizing output (e.g., "2025")
- `REPORT_SPECIES_ID`: Species ID
- `Compressed_Filename`: **Added by script** - compressed filename (e.g., "\2025\2511304H.7z" or "SIMULATE\2025\2511304H.7z" in simulate mode)
- Other columns...

## Usage

### Basic Usage (Encrypted)

```bash
python batch_zip_encrypt.py \
  --source-folder "C:\OCBC\Reports" \
  --output-folder "C:\OCBC\EncryptedArchives" \
  --password "YourSecurePassword123!"
```

### Basic Usage (No Encryption)

```bash
# Omit --password for faster, unencrypted archives
python batch_zip_encrypt.py \
  --source-folder "C:\OCBC\Reports" \
  --output-folder "C:\OCBC\Archives"
```

### Fast Processing (Low Compression)

```bash
python batch_zip_encrypt.py \
  --source-folder "C:\OCBC\Reports" \
  --output-folder "C:\OCBC\Archives" \
  --password "YourPassword" \
  --compression-level 1 \
  --quiet
```

### Process Only Specific Species

```bash
python batch_zip_encrypt.py \
  --source-folder "C:\OCBC\Reports" \
  --output-folder "C:\OCBC\EncryptedArchives" \
  --password "YourSecurePassword123!" \
  --filter-species "BC2060P,BC2061P,BC2035P"
```

### Custom 7zip Path (if not in PATH)

```bash
python batch_zip_encrypt.py \
  --source-folder "C:\OCBC\Reports" \
  --output-folder "C:\OCBC\EncryptedArchives" \
  --password "YourSecurePassword123!" \
  --7zip-path "C:\Program Files\7-Zip\7z.exe"
```

### Resume from Interrupted Run

```bash
# Just run the same command again - it automatically resumes
python batch_zip_encrypt.py \
  --source-folder "C:\OCBC\Reports" \
  --output-folder "C:\OCBC\EncryptedArchives" \
  --password "YourSecurePassword123!"
```

### Reset Progress and Start Over

```bash
python batch_zip_encrypt.py \
  --source-folder "C:\OCBC\Reports" \
  --output-folder "C:\OCBC\EncryptedArchives" \
  --password "YourSecurePassword123!" \
  --reset-progress
```

### Custom CSV Locations

```bash
python batch_zip_encrypt.py \
  --source-folder "C:\OCBC\Reports" \
  --output-folder "C:\OCBC\EncryptedArchives" \
  --password "YourSecurePassword123!" \
  --species-csv "C:\Custom\Path\Report_Species.csv" \
  --instances-folder "C:\Custom\Path\Instances"
```

### Batch Processing (Process N Species Per Run)

```bash
# Process 5 species (default), run multiple times to complete all
python batch_zip_encrypt.py \
  --source-folder "C:\OCBC\Reports" \
  --output-folder "C:\OCBC\EncryptedArchives" \
  --password "YourSecurePassword123!"

# Process 10 species per run
python batch_zip_encrypt.py \
  --source-folder "C:\OCBC\Reports" \
  --output-folder "C:\OCBC\EncryptedArchives" \
  --password "YourSecurePassword123!" \
  --max-species 10

# Process all species at once (0 = unlimited)
python batch_zip_encrypt.py \
  --source-folder "C:\OCBC\Reports" \
  --output-folder "C:\OCBC\EncryptedArchives" \
  --password "YourSecurePassword123!" \
  --max-species 0
```

### Delete Source Files After Compression

```bash
# CAUTION: This deletes source files after successful compression
python batch_zip_encrypt.py \
  --source-folder "C:\OCBC\Reports" \
  --output-folder "C:\OCBC\EncryptedArchives" \
  --password "YourSecurePassword123!" \
  --delete-after-compress Yes

# Default (no deletion)
python batch_zip_encrypt.py \
  --source-folder "C:\OCBC\Reports" \
  --output-folder "C:\OCBC\EncryptedArchives" \
  --password "YourSecurePassword123!" \
  --delete-after-compress No
```

### Simulate Mode (Test Without Compression)

```bash
# Test the process without actually creating archives
python batch_zip_encrypt.py \
  --source-folder "C:\OCBC\Reports" \
  --output-folder "C:\OCBC\EncryptedArchives" \
  --SIMULATEZIP

# Simulated paths will be stored as "SIMULATE\YYYY\name.7z"
# Useful for testing, validation, or planning
```

## Command-Line Arguments

### Required Arguments

| Argument | Description |
|----------|-------------|
| `--source-folder` | Directory containing files to zip (e.g., "C:\Reports") |
| `--output-folder` | Directory to save 7z files |

### Optional Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--password` | Encryption password for 7z archives (optional) | No encryption |
| `--species-csv` | Path to Report_Species.csv | `Report_Species.csv` (in script directory) |
| `--instances-folder` | Path to Output_Extract_Instances folder | `Output_Extract_Instances` (in script directory) |
| `--filter-species` | Process only specific species (comma-separated) | Process all |
| `--7zip-path` | Path to 7z.exe | `7z` (assumes in PATH) |
| `--reset-progress` | Start from beginning, ignore existing progress | Resume from last position |
| `--max-species` | Maximum species to process per run (0=unlimited) | 5 |
| `--delete-after-compress` | Delete source files after compression (must specify "Yes") | No |
| `--compression-level` | Compression level 0-9 (0=store, 5=normal, 9=ultra) | 5 |
| `--quiet` | Suppress console output (single-line progress) | Show all output |
| `--SIMULATEZIP` | Simulate mode: Skip actual compression, store simulated paths | Disabled |

## Output Structure

```
output-folder/
├── 2024/
│   ├── 2410104A.7z
│   ├── 2410204B.7z
│   └── ...
├── 2025/
│   ├── 2511304H.7z
│   ├── 2511204W.7z
│   ├── 2510804E.7z
│   └── ...
└── ...

Script directory (Migration_Instances/):
├── batch_zip_encrypt.log                  # Full detailed log
├── batch_zip_encrypt_progress.json        # Progress tracker (deleted when complete)
├── compress-log.csv                       # ⭐ NEW: Complete audit trail
├── missing_species.csv                    # Species with no instance CSV
├── missing_files.csv                      # Files with no source files
└── Output_Extract_Instances/
    ├── BC2060P_2024.csv                   # Updated with Compressed_Filename column
    └── ...
```

### Archive Properties
- **Format**: Native 7z format (better compression than ZIP)
- **Encryption**: AES-256 with header encryption (if password provided)
- **Compression**: Configurable 0-9 (default: 5 = normal)
- **Contents**: All files matching `{filename}.*` pattern from source folder

### Progress File
- **Name**: `batch_zip_encrypt_progress.json`
- **Content**: `{"report_species_id": 1, "row_index": 42, "stats": {...}}`
- **Purpose**: Tracks current position AND statistics for resume capability
- **Lifecycle**: Created during execution, deleted when complete

### ⭐ Complete Audit Log (NEW v2.2)
- **Name**: `compress-log.csv`
- **Columns**:
  - `species_id`: Report species ID
  - `Species_name`: Species name (e.g., "BC2060P")
  - `Species_Instance_Filename`: CSV filename (e.g., "BC2060P_2024.csv")
  - `row`: Row number in CSV (1-based)
  - `Filename`: Original filename from CSV
  - `Status`: SUCCESS, SIMULATED, NO_FILES_FOUND, SKIPPED, or FAILED
  - `Compressed_Filename`: Compressed filename (empty if not compressed)
- **Purpose**: Complete audit trail of ALL processing - proof of what was compressed and what wasn't
- **Use Cases**: Reporting, quality control, compliance, troubleshooting

### Instance CSV Updates
- **Automatic column addition**: `Compressed_Filename` column added to instance CSVs
- **Real-time updates**: CSV updated immediately after each file is processed
- **Values**:
  - Normal mode: `\2025\2511304H.7z`
  - Simulate mode: `SIMULATE\2025\2511304H.7z`
  - Empty if not compressed
- **Benefit**: Easy to see which files have been archived

## Resume Capability

The script tracks progress after each successful archive creation. If interrupted (Ctrl+C, power failure, etc.):

1. Progress is saved in `batch_zip_encrypt_progress.json`
2. Tracks current `report_species_id` and `row_index`
3. On restart, automatically resumes from last saved position
4. Skips already-created archives (checks if file exists)

### Interrupting the Script

Press **Ctrl+C** to interrupt. The script will:
- Save current progress
- Log the interruption
- Exit gracefully

### Resuming After Interruption

Simply run the same command again. The script will:
- Detect existing progress file
- Resume from last position
- Skip already-processed files

### Resetting Progress

To start from scratch:
```bash
python batch_zip_encrypt.py ... --reset-progress
```

Or manually delete `batch_zip_encrypt_progress.json`.

## Workflow

### High-Level Flow

1. **Load Progress**: Check for existing progress file
2. **Read Species CSV**: Load list of report species
3. **For each species**:
   - Find matching instance CSV
   - Read instance CSV rows
   - For each row:
     - Extract FILENAME and YEAR
     - Remove .RPT extension
     - Search for matching files in source folder
     - Create year subfolder if needed
     - Create encrypted 7z archive
     - Update progress
4. **Complete**: Delete progress file, show summary

### Detailed Processing Per File

For filename "2511304H.RPT" in year "2025":

1. Remove `.RPT` extension → `2511304H`
2. Search for files: `{source-folder}\2511304H.*`
   - Example matches: `2511304H.pdf`, `2511304H.xlsx`, `2511304H.rpt`
3. Create year folder: `{output-folder}\2025\`
4. Check if already exists: `{output-folder}\2025\2511304H.7z`
5. If not exists, create archive with all matched files
6. Update progress: Save current position
7. Log result: Success or error

## Error Handling

The script handles these scenarios gracefully:

| Scenario | Behavior |
|----------|----------|
| No matching files found | Log warning, skip to next, update progress |
| Missing species CSV | Log error, exit |
| Missing instance CSV | Log warning, skip species |
| Empty FILENAME or YEAR | Skip row |
| Archive already exists | Skip (don't recreate), update progress |
| 7zip not installed | Exit with installation instructions |
| Source folder doesn't exist | Exit with error |
| Script interrupted (Ctrl+C) | Save progress, exit gracefully |
| Corrupted progress file | Exit with message to use `--reset-progress` |
| Empty YEAR column | Use "UNKNOWN" as year folder |

## Logging

All operations are logged to multiple outputs:

### 1. Console Output
- **Normal mode**: Shows all INFO, WARNING, ERROR messages with scrolling
- **Quiet mode** (`--quiet`): ⭐ **Single line that updates in place** (no scrolling)
  - Shows current file being processed
  - Example: `Processing: BC2060P_2024.csv row 42/150: 2507601x - compressing 3 files...`
  - Line overwrites itself - always see latest progress
  - Cleaner, easier to monitor

### 2. Log File (`batch_zip_encrypt.log`)
- **All levels**: INFO, WARNING, ERROR
- **Full details**: Timestamped entries with complete information
- **Always created**: Even in quiet mode

### 3. Complete Audit Log (`compress-log.csv`) ⭐ NEW
- **Every file processed**: SUCCESS, NO_FILES_FOUND, SKIPPED, FAILED
- **CSV format**: Easy to analyze in Excel or scripts
- **Columns**: species_id, Species_name, Species_Instance_Filename, row, Filename, Status, Compressed_Path
- **Use for**: Proof of work, reporting, quality control

### 4. Missing Files Logs
- **missing_species.csv**: Species with no instance CSV
- **missing_files.csv**: Files with no source files found

### Log Levels

- **INFO**: Normal operations (archive created, files found, etc.)
- **WARNING**: Non-critical issues (no files found, archive exists, etc.)
- **ERROR**: Critical failures (7zip failed, file read errors, etc.)

### Log Format Examples

**Detailed log (batch_zip_encrypt.log):**
```
2025-01-23 14:30:45 - INFO - Processing species: BC2060P (id=1) - BC2060P_2024.csv
2025-01-23 14:30:45 - INFO - Found 150 rows in BC2060P_2024.csv
2025-01-23 14:30:46 - INFO - Processing: BC2060P_2024.csv row 1/150: 2511304H - creating archive (found 3 files)
2025-01-23 14:30:48 - INFO - Processing: BC2060P_2024.csv row 1/150: 2511304H - SUCCESS - \2025\2511304H.7z
2025-01-23 14:30:48 - INFO - CSV updated with: \2025\2511304H.7z
2025-01-23 14:30:50 - WARNING - Processing: BC2060P_2024.csv row 3/150: 2510804E - NO FILES FOUND in C:\Reports
```

**Audit log (compress-log.csv):**
```csv
species_id,Species_name,Species_Instance_Filename,row,Filename,Status,Compressed_Filename
1,BC2060P,BC2060P_2024.csv,1,2511304H.RPT,SUCCESS,\2025\2511304H.7z
1,BC2060P,BC2060P_2024.csv,2,2511204W.RPT,SUCCESS,\2025\2511204W.7z
1,BC2060P,BC2060P_2024.csv,3,2510804E.RPT,NO_FILES_FOUND,
1,BC2060P,BC2060P_2024.csv,4,2510704S.RPT,SKIPPED,\2025\2510704S.7z
```

**Audit log in simulate mode:**
```csv
species_id,Species_name,Species_Instance_Filename,row,Filename,Status,Compressed_Filename
1,BC2060P,BC2060P_2024.csv,1,2511304H.RPT,SIMULATED,SIMULATE\2025\2511304H.7z
1,BC2060P,BC2060P_2024.csv,2,2511204W.RPT,SIMULATED,SIMULATE\2025\2511204W.7z
```

**Quiet mode console (single line):**
```
Processing: BC2060P_2024.csv row 42/150: 2507601x - SUCCESS
```
(This line overwrites itself - no scrolling)

## Statistics

At completion, the script reports:

```
Summary: 125 archives created, 15 skipped, 3 no files found, 0 species not found, 2 errors
```

- **archives created**: Successfully created 7z files
- **skipped**: Archives that already existed (not recreated)
- **no files found**: Filenames with no matching files in source folder
- **species not found**: Species with no instance CSV file
- **errors**: Failed archive creations or other errors

**Statistics are persistent**: Saved in progress file, not lost on interruption.

**Audit trail**: All processing recorded in `compress-log.csv` for verification.

## Testing

### Test Extraction

Verify an archive was created correctly:

```bash
# With password (encrypted)
7z x -p"YourPassword" "output-folder\2025\2511304H.7z"

# Without password (unencrypted)
7z x "output-folder\2025\2511304H.7z"

# List contents without extracting
7z l -p"YourPassword" "output-folder\2025\2511304H.7z"

# Test archive integrity
7z t -p"YourPassword" "output-folder\2025\2511304H.7z"
```

### Test Audit Log

Verify the complete audit trail:

```bash
# View audit log
type compress-log.csv

# Count successful compressions
findstr "SUCCESS" compress-log.csv | find /C /V ""

# Show files not found
findstr "NO_FILES_FOUND" compress-log.csv

# Open in Excel for analysis
start compress-log.csv
```

### Test Real-Time CSV Updates

Verify instance CSVs are updated in real-time:

```bash
# Start script
python batch_zip_encrypt.py ...

# In another terminal, watch CSV update
while ($true) {
    Clear-Host
    Get-Content Output_Extract_Instances\BC2060P_2024.csv | Select-Object -Last 5
    Start-Sleep -Seconds 2
}

# Or just open CSV in Notepad and press F5 to refresh
# You'll see Compressed_Filename column populate in real-time
```

### Test Resume Capability

1. Run script
2. Interrupt with Ctrl+C after a few archives
3. Verify `batch_zip_encrypt_progress.json` exists
4. Run script again with same command
5. Verify it resumes from saved position (check logs)

### Test Year Organization

1. Run script
2. Check output folder contains year subfolders (2024, 2025, etc.)
3. Verify archives are in correct year folders

## Security Considerations

### Password Handling

**Optional**: Password can be omitted for unencrypted archives (faster).

**If using password**:
- **Warning**: Password is passed as command-line argument, visible in:
  - Process list (Task Manager, ps, etc.)
  - Command history (shell history)
- **Alternatives**:
  - Store password in environment variable
  - Read from secure config file
  - Use Windows Credential Manager
  - Omit password for unencrypted archives

### Encryption

**With password** (`--password "..."`)
- **Algorithm**: AES-256 (industry standard)
- **Header Encryption**: Enabled (`-mhe=on`) - hides filenames
- **Password Strength**: Use strong passwords (12+ characters, mixed case, numbers, symbols)

**Without password** (omit `--password`)
- **No encryption**: Archives created without password protection
- **Faster**: 10-15% faster compression
- **Use case**: Internal archives, non-sensitive data

### Log File Security

- Password is **NOT** written to log file
- Log file contains: filenames, paths, operations, errors
- Keep log files secure if filenames are sensitive

## Troubleshooting

### "7zip not found"

**Problem**: 7-Zip is not installed or not in PATH

**Solution**:
1. Install 7-Zip from https://www.7-zip.org/
2. Add to PATH, or use `--7zip-path` parameter:
   ```bash
   --7zip-path "C:\Program Files\7-Zip\7z.exe"
   ```

### "Source folder does not exist"

**Problem**: Specified source folder path is incorrect

**Solution**:
- Verify path exists and is spelled correctly
- Use absolute path with quotes for paths with spaces
- Example: `--source-folder "C:\My Documents\Reports"`

### "Species CSV not found"

**Problem**: Report_Species.csv not in expected location

**Solution**:
- Verify file exists in script directory or use `--species-csv`:
  ```bash
  --species-csv "C:\Full\Path\To\Report_Species.csv"
  ```

### "Corrupted progress file"

**Problem**: Progress file is damaged or invalid JSON

**Solution**:
```bash
# Reset progress and start over
python batch_zip_encrypt.py ... --reset-progress

# Or manually delete progress file
del batch_zip_encrypt_progress.json
```

### "No files found" warnings

**Problem**: Filenames in CSV don't match files in source folder

**Solution**:
- Verify source folder contains expected files
- Check filename patterns match (case-sensitive on some systems)
- Review `batch_zip_encrypt.log` for details

### Script runs slowly

**Problem**: Processing large number of files/archives

**Solution**:
- Normal for large datasets (500+ species × 100+ files each)
- **Use lower compression**: `--compression-level 1` for 2-3x speedup
- **Use no compression**: `--compression-level 0` for 5-10x speedup
- **Omit password**: Saves 10-15% time
- **Use quiet mode**: `--quiet` for 5-10% speedup
- **Process in batches**: Use `--filter-species` to split workload
- **Manual parallel processing**: Run multiple instances with different `--filter-species`

**Example for speed**:
```bash
python batch_zip_encrypt.py \
  --source-folder "C:\Reports" \
  --output-folder "D:\Archives" \
  --compression-level 1 \
  --quiet
# This will be ~10x faster than defaults
```

## Performance

### Expected Performance

**Default settings** (compression level 5, with password):
- **Small archives** (1-3 files, <10MB): ~2-5 seconds per archive
- **Large archives** (10+ files, >100MB): ~30-60 seconds per archive
- **Overall throughput**: ~10-30 archives per minute

**Fast settings** (compression level 1, with password, quiet mode):
- **Small archives**: ~1-2 seconds per archive
- **Large archives**: ~10-20 seconds per archive
- **Overall throughput**: ~25-50 archives per minute
- **Speed increase**: 2-3x faster

**Fastest settings** (compression level 0, no password, quiet mode):
- **Small archives**: ~0.5-1 seconds per archive
- **Large archives**: ~3-8 seconds per archive
- **Overall throughput**: ~50-100 archives per minute
- **Speed increase**: 5-10x faster

### Large-Scale Processing

For 500 species with 100 files each:
- **Total archives**: ~50,000
- **Default settings**: 28-83 hours
- **Fast settings**: 10-28 hours
- **Fastest settings**: 8-17 hours
- **Recommendation**:
  - Use `--compression-level 1 --quiet` for best balance
  - Use `--filter-species` to process in batches
  - Run multiple instances in parallel for different species groups

## Simulate Mode Details

### What is Simulate Mode?

Simulate mode (`--SIMULATEZIP`) processes all CSV records and updates them with simulated paths **without** actually creating 7z archives.

### Use Cases

1. **Testing & Validation**
   - Validate CSV data before committing to actual compression
   - Test script configuration and workflow
   - Verify file matching logic works correctly

2. **Planning & Analysis**
   - Estimate how many archives will be created
   - Preview archive organization by year
   - Identify missing files without compression overhead

3. **Disk Space Management**
   - Test on systems with limited disk space
   - Plan storage requirements before actual compression
   - Verify year-based organization structure

4. **Development & Debugging**
   - Test script changes without time-consuming compression
   - Debug CSV update logic
   - Verify audit trail functionality

### Behavior in Simulate Mode

- **No compression**: 7z archives are NOT created
- **No file system operations**: Year folders NOT created
- **No file existence checks**: Assumes all files exist
- **CSV updates**: Instance CSVs updated with simulated paths
- **Audit log**: All entries marked as "SIMULATED"
- **Path format**: `SIMULATE\YYYY\name.7z`
- **Speed**: 10-100x faster than actual compression
- **No deletion**: Source files never deleted (even with `--delete-after-compress`)

### Example Output

**Instance CSV (Compressed_Filename column):**
```
SIMULATE\2025\2511304H.7z
SIMULATE\2025\2511204W.7z
SIMULATE\2024\2410104A.7z
```

**Audit log (compress-log.csv):**
```csv
species_id,Species_name,Species_Instance_Filename,row,Filename,Status,Compressed_Filename
1,BC2060P,BC2060P_2024.csv,1,2511304H.RPT,SIMULATED,SIMULATE\2025\2511304H.7z
```

## Future Enhancements

Potential improvements for future versions:

- Built-in parallel processing (automatic multi-threading)
- Progress bar (visual progress indicator using tqdm)
- Verify mode (check existing archives for corruption)
- Statistics report (file size savings, compression ratios)
- Email notification on completion
- Web dashboard for monitoring progress

## Examples

### Example 1: Production Use (Encrypted, Balanced)

```bash
python batch_zip_encrypt.py \
  --source-folder "C:\OCBC\Reports" \
  --output-folder "C:\OCBC\Archives" \
  --password "SecurePass123!" \
  --compression-level 1 \
  --quiet

# After completion, check audit log
type compress-log.csv
findstr "NO_FILES_FOUND" compress-log.csv
```

### Example 2: Fast Processing (No Encryption)

```bash
python batch_zip_encrypt.py \
  --source-folder "C:\OCBC\Reports" \
  --output-folder "C:\OCBC\Archives" \
  --compression-level 0 \
  --quiet

# No password = no encryption, 5-10x faster
```

### Example 3: Process Specific Species

```bash
python batch_zip_encrypt.py \
  --source-folder "C:\OCBC\Reports" \
  --output-folder "C:\OCBC\Archives" \
  --password "SecurePass123!" \
  --filter-species "BC2060P,BC2061P" \
  --compression-level 1 \
  --quiet
```

### Example 4: Resume After Interruption

```bash
# First run (interrupted)
python batch_zip_encrypt.py \
  --source-folder "C:\OCBC\Reports" \
  --output-folder "C:\OCBC\Archives" \
  --password "SecurePass123!" \
  --quiet
# ... Ctrl+C pressed ...

# Resume (same command) - statistics preserved!
python batch_zip_encrypt.py \
  --source-folder "C:\OCBC\Reports" \
  --output-folder "C:\OCBC\Archives" \
  --password "SecurePass123!" \
  --quiet
# Automatically resumes from last position
```

### Example 5: Maximum Compression (Archival)

```bash
python batch_zip_encrypt.py \
  --source-folder "C:\OCBC\Reports" \
  --output-folder "E:\LongTermArchive" \
  --password "SecurePass123!" \
  --compression-level 9

# Slowest, but smallest files (90%+ compression)
```

### Example 6: Analyze Results

```bash
# After processing, analyze the audit log

# Count successful compressions
findstr "SUCCESS" compress-log.csv | find /C /V ""

# Show files not found
findstr "NO_FILES_FOUND" compress-log.csv

# Export specific species
findstr "BC2060P" compress-log.csv > BC2060P_audit.csv

# Open in Excel for analysis
start compress-log.csv
```

### Example 7: Watch Progress in Real-Time

```bash
# Terminal 1: Run script
python batch_zip_encrypt.py \
  --source-folder "C:\Reports" \
  --output-folder "D:\Archives" \
  --password "Pass123" \
  --quiet

# Terminal 2: Watch CSV update in real-time
while ($true) {
    Clear-Host
    Get-Content Output_Extract_Instances\BC2060P_2024.csv | Select-Object -Last 5
    Start-Sleep -Seconds 2
}

# Terminal 3: Watch log for details
Get-Content batch_zip_encrypt.log -Wait -Tail 20
```

### Example 8: Simulate Mode (Testing)

```bash
# Test without actually creating archives
python batch_zip_encrypt.py \
  --source-folder "C:\Reports" \
  --output-folder "D:\Archives" \
  --SIMULATEZIP \
  --quiet

# Check what would be created
type compress-log.csv

# Review simulated paths in CSV
findstr "SIMULATE" compress-log.csv

# Use this to:
# - Validate CSV data before actual compression
# - Estimate storage requirements
# - Test workflow without consuming disk space
# - Plan archive organization
```

## Support

For issues or questions:
1. Check `batch_zip_encrypt.log` for detailed error messages
2. Review this README for common solutions
3. Verify all requirements are met (Python 3.7+, 7-Zip installed)

## Version History

- **v2.4** (2026-01-28): Simulate mode and column rename
  - ⭐ Simulate mode: `--SIMULATEZIP` parameter to test without actual compression
  - ⭐ Column rename: `Compressed_Path` → `Compressed_Filename` for consistency
  - Simulated paths prefixed with "SIMULATE\YYYY\name.7z"
  - Normal paths format: "\YYYY\name.7z"
  - Simulate mode useful for validation, planning, and testing

- **v2.3** (2026-01-26): Batch processing and disk space management
  - ⭐ Batch processing: `--max-species` parameter (default: 5 species per run)
  - ⭐ Delete after compress: `--delete-after-compress Yes` to free disk space
  - ⭐ Real-time log flushing: Logs survive crashes and interruptions
  - ⭐ Real-time compress-log.csv: Append mode, written immediately
  - Auto-resume between batches
  - Progress file cleared only when all species processed

- **v2.2** (2025-01-23): Audit trail and UX improvements
  - ⭐ Complete audit log (`compress-log.csv`) - proof of all processing
  - ⭐ Single-line progress in quiet mode (no scrolling)
  - Real-time CSV updates with disk flush
  - Enhanced logging with detailed progress

- **v2.1** (2025-01-23): Critical fixes
  - Real-time CSV updates (after each file, not just at end)
  - Enhanced logging with species name, CSV filename, row numbers
  - Fixed resume logic for row numbering

- **v2.0** (2025-01-23): Major improvements
  - Optional password (no encryption mode)
  - Compressed_Path column in instance CSVs
  - CSV logs for missing items
  - Persistent statistics across interruptions
  - Performance optimizations (compression level, quiet mode)

- **v1.0** (2025-01-23): Initial release
  - Year-based organization
  - Resume capability
  - AES-256 encryption
  - Comprehensive logging

---

**Author**: Claude Code
**Date**: 2026-01-28
**License**: MIT (or as specified by project)
