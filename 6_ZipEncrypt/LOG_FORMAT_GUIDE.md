# Log Format Quick Reference Guide

## What You'll See When Running the Script

This guide shows the exact log format you'll see when running `batch_zip_encrypt.py` v2.1+.

---

## Startup Messages

```log
2025-01-23 14:30:00 - INFO - ================================================================================
2025-01-23 14:30:00 - INFO - Batch Zip and Encrypt - Starting
2025-01-23 14:30:00 - INFO - Mode: Encrypted archives (password protected)
2025-01-23 14:30:00 - INFO - Compression level: 1
2025-01-23 14:30:00 - INFO - ================================================================================
2025-01-23 14:30:00 - INFO - 7zip found: 7z
2025-01-23 14:30:00 - INFO - Loaded 12 species from Report_Species.csv
2025-01-23 14:30:00 - INFO - Processing 12 species...
```

**What it tells you:**
- ✅ Script started
- ✅ Mode (encrypted or not)
- ✅ Compression level
- ✅ 7zip found
- ✅ How many species will be processed

---

## Species Processing Header

```log
2025-01-23 14:30:00 - INFO - ================================================================================
2025-01-23 14:30:00 - INFO - Species 1/12: BC2035P (ID: 1)
2025-01-23 14:30:00 - INFO - ================================================================================
2025-01-23 14:30:00 - INFO - Processing species: BC2035P (id=1) - BC2035P_2024.csv
2025-01-23 14:30:00 - INFO - Loaded 150 rows from BC2035P_2024.csv
2025-01-23 14:30:00 - INFO - Found 150 rows in BC2035P_2024.csv
```

**Format:**
```
Species {current}/{total}: {species_name} (ID: {species_id})
Processing species: {species_name} (id={species_id}) - {csv_filename}
Found {total_rows} rows in {csv_filename}
```

**What it tells you:**
- ✅ Which species (1 of 12)
- ✅ Species name (BC2035P)
- ✅ Species ID (1)
- ✅ CSV filename being processed
- ✅ How many rows in this CSV

---

## Row Processing - Success

```log
2025-01-23 14:30:01 - INFO - Processing: BC2035P_2024.csv row 1/150: 2501001a - creating archive (found 3 files)
2025-01-23 14:30:03 - INFO - Updated instance CSV: BC2035P_2024.csv
2025-01-23 14:30:03 - INFO - Processing: BC2035P_2024.csv row 1/150: 2501001a - SUCCESS - \2025\2501001a.7z
```

**Format:**
```
Processing: {csv_filename} row {current}/{total}: {base_filename} - creating archive (found {count} files)
Updated instance CSV: {csv_filename}
Processing: {csv_filename} row {current}/{total}: {base_filename} - SUCCESS - {relative_path}
```

**What it tells you:**
- ✅ Which CSV file
- ✅ Current row / Total rows (1/150)
- ✅ Filename being processed (2501001a)
- ✅ How many source files found (3)
- ✅ CSV updated
- ✅ Success + archive location (\2025\2501001a.7z)

---

## Row Processing - Already Exists

```log
2025-01-23 14:30:05 - INFO - Processing: BC2035P_2024.csv row 4/150: 2501004d - already exists, CSV updated
2025-01-23 14:30:05 - INFO - Updated instance CSV: BC2035P_2024.csv
```

**Format:**
```
Processing: {csv_filename} row {current}/{total}: {base_filename} - already exists, CSV updated
Updated instance CSV: {csv_filename}
```

**What it tells you:**
- ✅ Archive already exists (skipping)
- ✅ CSV still updated with path

---

## Row Processing - Already Exists (No Update Needed)

```log
2025-01-23 14:30:06 - INFO - Processing: BC2035P_2024.csv row 5/150: 2501005e - skipping (already exists)
```

**Format:**
```
Processing: {csv_filename} row {current}/{total}: {base_filename} - skipping (already exists)
```

**What it tells you:**
- ✅ Archive exists AND CSV already has the path (no update needed)

---

## Row Processing - Files Not Found

```log
2025-01-23 14:30:05 - WARNING - Processing: BC2035P_2024.csv row 3/150: 2501003c - NO FILES FOUND in C:\Reports
2025-01-23 14:30:05 - INFO - Updated instance CSV: BC2035P_2024.csv
```

**Format:**
```
WARNING - Processing: {csv_filename} row {current}/{total}: {base_filename} - NO FILES FOUND in {source_folder}
Updated instance CSV: {csv_filename}
```

**What it tells you:**
- ⚠️ WARNING level (shown on console)
- ✅ Which file pattern couldn't be found
- ✅ Where it was searching (source folder)
- ✅ CSV updated with empty Compressed_Filename

---

## Row Processing - Failed

```log
2025-01-23 14:30:10 - INFO - Processing: BC2035P_2024.csv row 8/150: 2501008h - creating archive (found 2 files)
2025-01-23 14:30:10 - ERROR - 7zip command failed: ...
2025-01-23 14:30:10 - INFO - Updated instance CSV: BC2035P_2024.csv
2025-01-23 14:30:10 - ERROR - Processing: BC2035P_2024.csv row 8/150: 2501008h - FAILED to create archive
```

**Format:**
```
Processing: {csv_filename} row {current}/{total}: {base_filename} - creating archive (found {count} files)
ERROR - 7zip command failed: {error_details}
Updated instance CSV: {csv_filename}
ERROR - Processing: {csv_filename} row {current}/{total}: {base_filename} - FAILED to create archive
```

**What it tells you:**
- ❌ ERROR level (shown on console)
- ✅ Which file failed
- ✅ Error details from 7zip
- ✅ CSV updated with empty Compressed_Filename

---

## Species Completion

```log
2025-01-23 14:35:30 - INFO - Completed processing BC2035P_2024.csv: 150 rows processed
```

**Format:**
```
Completed processing {csv_filename}: {total_rows} rows processed
```

**What it tells you:**
- ✅ Finished processing this species
- ✅ How many rows were processed

---

## Resume Mode - Skipping Already Processed Rows

```log
2025-01-23 14:40:00 - INFO - Resuming from species_id=1, row_index=75
2025-01-23 14:40:00 - INFO - Loaded stats: Summary: 74 archives created, 1 skipped, 0 no files found, 0 species not found, 0 errors

2025-01-23 14:40:00 - INFO - ================================================================================
2025-01-23 14:40:00 - INFO - Species 1/12: BC2035P (ID: 1)
2025-01-23 14:40:00 - INFO - ================================================================================
2025-01-23 14:40:00 - INFO - Processing species: BC2035P (id=1) - BC2035P_2024.csv
2025-01-23 14:40:00 - INFO - Found 150 rows in BC2035P_2024.csv

2025-01-23 14:40:00 - INFO - Skipping BC2035P_2024.csv row 1/150 (already processed)
2025-01-23 14:40:00 - INFO - Skipping BC2035P_2024.csv row 2/150 (already processed)
2025-01-23 14:40:00 - INFO - Skipping BC2035P_2024.csv row 3/150 (already processed)
...
2025-01-23 14:40:01 - INFO - Skipping BC2035P_2024.csv row 75/150 (already processed)

2025-01-23 14:40:01 - INFO - Processing: BC2035P_2024.csv row 76/150: 2507601x - creating archive (found 3 files)
...
```

**Format:**
```
Resuming from species_id={id}, row_index={row}
Loaded stats: Summary: {stats}
...
Skipping {csv_filename} row {row}/{total} (already processed)
```

**What it tells you:**
- ✅ Resuming from where it left off
- ✅ Previous statistics loaded
- ✅ Which rows are being skipped
- ✅ When processing resumes

---

## Completion Messages

```log
2025-01-23 16:30:00 - INFO - ================================================================================
2025-01-23 16:30:00 - INFO - Processing Complete!
2025-01-23 16:30:00 - INFO - Summary: 1250 archives created, 45 skipped, 12 no files found, 0 species not found, 3 errors
2025-01-23 16:30:00 - INFO - ================================================================================
2025-01-23 16:30:00 - INFO - Saved 12 missing files to missing_files.csv
2025-01-23 16:30:00 - INFO - Progress file deleted (processing complete)
```

**What it tells you:**
- ✅ All processing complete
- ✅ Final statistics
- ✅ Missing files CSV created (if any)
- ✅ Progress file cleaned up

---

## Interruption (Ctrl+C)

```log
2025-01-23 15:15:30 - WARNING -
Interrupted by user (Ctrl+C)
2025-01-23 15:15:30 - INFO - Progress and statistics saved. Run script again to resume.
2025-01-23 15:15:30 - INFO - Summary: 450 archives created, 15 skipped, 3 no files found, 0 species not found, 1 errors
2025-01-23 15:15:30 - INFO - Saved 3 missing files to missing_files.csv
```

**What it tells you:**
- ⚠️ Interrupted by user
- ✅ Progress saved (can resume)
- ✅ Current statistics
- ✅ Missing files log saved

---

## Missing Species Warning

```log
2025-01-23 14:31:00 - WARNING - No instance CSV found for species BC9999P
```

**Format:**
```
WARNING - No instance CSV found for species {species_name}
```

**What it tells you:**
- ⚠️ This species has no instance CSV file
- ✅ Will be logged to missing_species.csv

---

## Quick Reference Table

| Log Level | Shown on Console? | Meaning |
|-----------|------------------|---------|
| INFO | No (unless verbose) | Normal operation, successful actions |
| WARNING | Yes | Missing files, skipped items, non-critical issues |
| ERROR | Yes | Failed operations, critical errors |

**Note**: By default, only WARNING and ERROR are shown on console. All levels are written to `batch_zip_encrypt.log`.

---

## Monitoring Progress

### Real-Time Log Tail
```bash
# PowerShell
Get-Content batch_zip_encrypt.log -Wait -Tail 20

# Git Bash
tail -f batch_zip_encrypt.log
```

### Check Current Row
```bash
# Find latest "Processing:" line
findstr /C:"Processing:" batch_zip_encrypt.log | more +100

# Last few processing lines
tail -20 batch_zip_encrypt.log | findstr "Processing:"
```

### Count Successful Archives
```bash
# Count SUCCESS lines
findstr /C:"SUCCESS" batch_zip_encrypt.log | find /C /V ""

# Or from stats line
findstr /C:"Summary:" batch_zip_encrypt.log
```

### Check for Errors
```bash
# Show all ERROR lines
findstr /C:"ERROR" batch_zip_encrypt.log

# Show all WARNING lines
findstr /C:"WARNING" batch_zip_encrypt.log
```

---

## Understanding Progress

### Example Progress Tracking

```log
Species 3/12: BC2074P (ID: 7)
Processing: BC2074P_2024.csv row 45/200: 2503045x - SUCCESS
```

**Calculation:**
- **Species**: 3 of 12 completed = 25% of species done
- **Rows**: 45 of 200 = 22.5% of current species done
- **Overall**: (2 complete species × 100%) + (1 partial species × 22.5%) ≈ 24.4% overall

**Note**: This is approximate since species have different numbers of rows.

---

## Example Full Session

```log
2025-01-23 14:30:00 - INFO - Batch Zip and Encrypt - Starting
2025-01-23 14:30:00 - INFO - Loaded 3 species from Report_Species.csv
2025-01-23 14:30:00 - INFO - Processing 3 species...

2025-01-23 14:30:00 - INFO - ================================================================================
2025-01-23 14:30:00 - INFO - Species 1/3: BC2035P (ID: 1)
2025-01-23 14:30:00 - INFO - ================================================================================
2025-01-23 14:30:00 - INFO - Processing species: BC2035P (id=1) - BC2035P_2024.csv
2025-01-23 14:30:00 - INFO - Found 5 rows in BC2035P_2024.csv

2025-01-23 14:30:01 - INFO - Processing: BC2035P_2024.csv row 1/5: 2501001a - creating archive (found 3 files)
2025-01-23 14:30:03 - INFO - Processing: BC2035P_2024.csv row 1/5: 2501001a - SUCCESS - \2025\2501001a.7z

2025-01-23 14:30:03 - INFO - Processing: BC2035P_2024.csv row 2/5: 2501002b - creating archive (found 2 files)
2025-01-23 14:30:05 - INFO - Processing: BC2035P_2024.csv row 2/5: 2501002b - SUCCESS - \2025\2501002b.7z

2025-01-23 14:30:05 - WARNING - Processing: BC2035P_2024.csv row 3/5: 2501003c - NO FILES FOUND in C:\Reports

2025-01-23 14:30:06 - INFO - Processing: BC2035P_2024.csv row 4/5: 2501004d - already exists, CSV updated

2025-01-23 14:30:06 - INFO - Processing: BC2035P_2024.csv row 5/5: 2501005e - creating archive (found 1 files)
2025-01-23 14:30:07 - INFO - Processing: BC2035P_2024.csv row 5/5: 2501005e - SUCCESS - \2025\2501005e.7z

2025-01-23 14:30:07 - INFO - Completed processing BC2035P_2024.csv: 5 rows processed

2025-01-23 14:30:07 - INFO - ================================================================================
2025-01-23 14:30:07 - INFO - Species 2/3: BC2061P (ID: 2)
2025-01-23 14:30:07 - INFO - ================================================================================
...

2025-01-23 14:35:00 - INFO - ================================================================================
2025-01-23 14:35:00 - INFO - Processing Complete!
2025-01-23 14:35:00 - INFO - Summary: 12 archives created, 1 skipped, 1 no files found, 0 species not found, 0 errors
2025-01-23 14:35:00 - INFO - ================================================================================
2025-01-23 14:35:00 - INFO - Saved 1 missing files to missing_files.csv
2025-01-23 14:35:00 - INFO - Progress file deleted (processing complete)
```

---

## Tips for Reading Logs

1. **Focus on console output** (WARNING/ERROR) - shows problems only
2. **Check log file** for full details - shows all INFO messages
3. **Search for "Processing:"** to see current progress
4. **Search for "WARNING"** to find missing files
5. **Search for "ERROR"** to find failures
6. **Search for "Summary:"** to see statistics
7. **Last line with "Species X/Y"** shows current species being processed

---

**Author**: Claude Code
**Date**: 2025-01-23
**Version**: 2.1
