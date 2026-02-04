# Report Instance Cleanup Tool

## Overview

The cleanup tool allows you to safely delete report instances and their associated data from the IntelliSTOR database. This is useful for:
- Removing old/archived data
- Deleting test instances (especially those in the future)
- Cleaning up specific date ranges

## Files

- **`cleanup_report_instances.py`** - Main Python script (located in parent directory)
- **`Cleanup_Report_Instances.command`** - macOS launcher (double-click to run)
- **`Cleanup_Report_Instances_LOG.txt`** - Execution log file (created automatically)

## What Gets Deleted

The script safely removes:
1. `REPORT_INSTANCE` records
2. `REPORT_INSTANCE_SEGMENT` records
3. `SST_STORAGE` records
4. `MAPFILE` records (only if no other instances reference them)
5. `RPTFILE_INSTANCE` records
6. `RPTFILE` records (only if no other instances reference them)

**Smart Deletion:** MAP and RPT files are only deleted if they have no other references, preventing accidental deletion of shared files.

## Usage

### Method 1: Using the .command file (Recommended)

1. Double-click `Cleanup_Report_Instances.command` in Finder
2. Choose your deletion option:
   - **Option 1:** Delete up to a specific date (from beginning)
   - **Option 2:** Delete from a specific date onwards (e.g., future test data)
   - **Option 3:** Delete within a specific date range
3. Enter the date(s) in YYYY-MM-DD format
4. Choose dry-run (1) or actual deletion (2)
5. For actual deletion, type `DELETE` to confirm

### Method 2: Using Python directly

```bash
# Activate virtual environment first
source ../venv/bin/activate

# Dry run - delete up to a date
python3 ../cleanup_report_instances.py --end-date 2024-12-31 --dry-run

# Dry run - delete from a date onwards (e.g., test data)
python3 ../cleanup_report_instances.py --start-date 2026-01-01 --dry-run

# Dry run - delete within a date range
python3 ../cleanup_report_instances.py --start-date 2024-01-01 --end-date 2024-12-31 --dry-run

# Actually delete (requires typing 'DELETE' to confirm)
python3 ../cleanup_report_instances.py --start-date 2026-01-01
```

## Safety Features

### 1. Dry Run Mode (Default)
Always test with `--dry-run` first to see what would be deleted without actually deleting anything.

### 2. Confirmation Required
For actual deletions, you must type `DELETE` to proceed. This prevents accidental data loss.

### 3. Transaction Rollback
All deletions happen in a database transaction. If any error occurs, everything rolls back automatically.

### 4. Smart File Deletion
MAP and RPT files are only deleted if they have no other references, preventing accidental deletion of files still in use.

### 5. Detailed Logging
Every execution is logged with:
- Timestamp
- Date range
- Mode (dry-run or actual deletion)
- Duration
- Success/failure status

## Examples

### Example 1: Remove Old Data (Before 2024)
```bash
python3 ../cleanup_report_instances.py --end-date 2023-12-31 --dry-run
```

### Example 2: Remove Future Test Data
```bash
# Check what test instances exist in the future
python3 ../cleanup_report_instances.py --start-date 2026-01-01 --dry-run

# Delete them
python3 ../cleanup_report_instances.py --start-date 2026-01-01
```

### Example 3: Remove Specific Year
```bash
python3 ../cleanup_report_instances.py --start-date 2024-01-01 --end-date 2024-12-31 --dry-run
```

### Example 4: Remove Everything (USE WITH CAUTION!)
```bash
python3 ../cleanup_report_instances.py --start-date 1900-01-01 --end-date 2099-12-31 --dry-run
```

## Output Example

```
✓ Connected to database: iSTSGUAT

✓ Found 15 report instance(s) from 2026-01-01 onwards

================================================================================
REPORT INSTANCES TO BE DELETED:
================================================================================
1. CDU100P | 2026-01-15 10:30:00 | Species ID: 25 | RPT: 1024KB | MAP: 512KB
2. CDU200P | 2026-02-01 14:20:00 | Species ID: 26 | RPT: 2048KB | MAP: 768KB
...

✓ Found 10 MAP file(s) safe to delete
✓ Found 12 RPT file(s) safe to delete

================================================================================
DRY RUN MODE - No data will be deleted
================================================================================

================================================================================
DELETION SUMMARY:
================================================================================
Report Instances:         15
Report Instance Segments: 45
SST Storage Records:      15
MAP Files:                10
RPT File Instances:       15
RPT Files:                12
================================================================================

💡 This was a DRY RUN - no data was actually deleted
   Run without --dry-run to execute the deletion
```

## Troubleshooting

### "Error: You must specify at least one of --start-date or --end-date"
You need to provide at least one date parameter. You can use:
- Just `--end-date` to delete from beginning up to that date
- Just `--start-date` to delete from that date onwards
- Both to delete within a specific range

### "Invalid date format"
Dates must be in YYYY-MM-DD format (e.g., 2024-12-31)

### "start-date must be before end-date"
When using both dates, ensure the start date comes before the end date

### Connection Errors
Ensure the IntelliSTOR database is running and accessible at localhost:1433

## Best Practices

1. **Always test with dry-run first**
   - Run with `--dry-run` to see what will be deleted
   - Review the output carefully
   - Only proceed with actual deletion after confirming

2. **Keep logs**
   - Check `Cleanup_Report_Instances_LOG.txt` for history
   - Useful for auditing and troubleshooting

3. **Backup first** (if deleting production data)
   - Consider backing up the database before large deletions
   - Test on a non-production database first

4. **Use specific date ranges**
   - Be as specific as possible with your date ranges
   - Avoid deleting everything unless absolutely necessary

## Database Schema Reference

For more details on the database structure, see `database_reference.md` in the parent directory.
