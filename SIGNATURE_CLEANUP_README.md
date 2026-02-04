# Signature Cleanup Tool

## Overview

The signature cleanup tool removes old signature versions from the IntelliSTOR database, keeping only the latest version of each signature. This is useful for:
- Reducing database size (99.1% of signature records are old versions!)
- Improving query performance
- Eliminating historical versions that serve no operational purpose

## Files

- **`cleanup_old_signatures.py`** - Main Python script
- **`Cleanup_Old_Signatures.command`** - macOS launcher (double-click to run)
- **`Cleanup_Old_Signatures_LOG.txt`** - Execution log file (created automatically)
- **`SIGNATURE_CLEANUP_ANALYSIS.md`** - Detailed investigation and analysis

## What Gets Deleted

The script removes OLD versions only, keeping the LATEST version of each signature:

1. **SIGNATURE** - Old versions (99.1% of records)
2. **SENSITIVE_FIELD** - Records linked to old signature versions
3. **LINES_IN_SIGN** - Records linked to old signature versions

**What is NOT affected:**
- Latest signature versions (preserved)
- SIGN_GEN_INFO (not version-specific)
- Report instances (don't link to signature versions)
- SIGNATURE_GROUP (independent)

## Key Statistics (Before Cleanup)

- **Total signature records:** 312,011
- **Unique signatures (latest only):** 2,723
- **Old versions to delete:** 309,288 (99.1%)
- **SENSITIVE_FIELD records to delete:** 726,218
- **LINES_IN_SIGN records to delete:** 836,791
- **Total records to remove:** ~1.87 million records!

## Usage

### Method 1: Using the .command file (Recommended)

1. Double-click `Cleanup_Old_Signatures.command` in Finder
2. Choose scope:
   - **Option 1:** Clean all domains (recommended)
   - **Option 2:** Clean specific domain only
3. Choose mode:
   - **Option 1:** Dry-run (safe preview)
   - **Option 2:** Actually delete data
4. For actual deletion, type `DELETE` to confirm

### Method 2: Using Python directly

```bash
# Activate virtual environment first
source venv/bin/activate

# Dry run - see what would be deleted (all domains)
python3 cleanup_old_signatures.py --dry-run

# Actually delete (all domains)
python3 cleanup_old_signatures.py

# Dry run for specific domain
python3 cleanup_old_signatures.py --domain-id 1 --dry-run

# Actually delete for specific domain
python3 cleanup_old_signatures.py --domain-id 1
```

## How It Works

### Version Selection Logic

For each unique combination of (DOMAIN_ID, REPORT_SPECIES_ID, SIGN_ID):
- **KEEP:** The record with MAX(MINOR_VERSION) - the latest version
- **DELETE:** All records with MINOR_VERSION < MAX(MINOR_VERSION) - old versions

### Example

If a signature has these versions:
```
DOMAIN=1, SPECIES=832, SIGN_ID=5
  - MINOR_VERSION=100  ← DELETE (old)
  - MINOR_VERSION=200  ← DELETE (old)
  - MINOR_VERSION=250  ← DELETE (old)
  - MINOR_VERSION=300  ← KEEP (latest)
```

Only version 300 is kept; versions 100, 200, and 250 are deleted.

## Safety Features

### 1. Dry Run Mode (Default)
Always test with `--dry-run` first to see what would be deleted without actually deleting anything.

### 2. Confirmation Required
For actual deletions, you must type `DELETE` to proceed. This prevents accidental data loss.

### 3. Transaction Rollback
All deletions happen in a database transaction. If any error occurs, everything rolls back automatically.

### 4. Efficient SQL Queries
Uses optimized SQL with subqueries instead of iterating through records, making it fast even for large datasets.

### 5. Progress Indicators
Shows real-time progress during deletion so you know the script is working.

### 6. Detailed Logging
Every execution is logged with:
- Timestamp
- Scope (all domains or specific domain)
- Mode (dry-run or actual deletion)
- Duration
- Success/failure status

## Output Example

```
================================================================================
SIGNATURE STATISTICS:
================================================================================
Total signature records:              312,011
Unique signatures (latest only):      2,723
Old versions (to be deleted):         309,288
Percentage to be deleted:             99.1%

================================================================================
OLD SIGNATURE VERSIONS TO BE DELETED:
================================================================================

  Domain |  Species |  Sign ID |     MinVer | Description
--------------------------------------------------------------------------------
       1 |        0 |        1 |          4 |
       1 |        0 |        1 |          6 |
       1 |        0 |        1 |          8 |
       ...

... (309,268 more signatures) ...

================================================================================
COUNTING RELATED RECORDS:
================================================================================
Counting SENSITIVE_FIELD records... 726,218
Counting LINES_IN_SIGN records... 836,791

================================================================================
DRY RUN MODE - No data will be deleted
================================================================================

================================================================================
DELETION SUMMARY:
================================================================================
Old Signature Versions:   309,288
SENSITIVE_FIELD Records:  726,218
LINES_IN_SIGN Records:    836,791
--------------------------------------------------------------------------------
TOTAL RECORDS REMOVED:    1,872,297
================================================================================

💡 This was a DRY RUN - no data was actually deleted
   Run without --dry-run to execute the deletion
```

## Execution Time

With ~309,000 signatures to process:
- **Dry-run mode:** ~1-2 minutes (just counting)
- **Actual deletion:** ~15-30 minutes (depends on database performance)

The script shows progress indicators so you know it's working.

## Troubleshooting

### Connection Errors
Ensure the IntelliSTOR database is running and accessible at localhost:1433

### Slow Execution
The script processes each signature individually to maintain transaction safety. With 309,000 records, expect 15-30 minutes for actual deletion.

### "Operation cancelled"
Make sure you type exactly `DELETE` (5 letters, all caps) to confirm.

## Why Clean Up Old Signatures?

### 1. Massive Space Savings
- **Before:** 312,011 signature records + 730,952 SENSITIVE_FIELD + 842,490 LINES_IN_SIGN = 1.88 million records
- **After:** 2,723 signature records + 4,734 SENSITIVE_FIELD + 5,699 LINES_IN_SIGN = 13,156 records
- **Savings:** 99.3% reduction (1.87 million records removed)

### 2. Performance Improvements
- Faster signature queries (99% fewer records to scan)
- Reduced index sizes
- Faster backups and maintenance operations

### 3. No Functional Impact
- Only the latest signature version is used for report processing
- Historical versions serve no operational purpose
- Report instances don't reference specific signature versions

### 4. Maintenance Benefits
- Easier to understand signature structure
- Simpler troubleshooting (less noise)
- Cleaner database for migration/upgrades

## Compliance Considerations

⚠️ **Before running in production:**

1. **Check audit requirements** - Some organizations need to keep signature history for regulatory reasons
2. **Get business approval** - Confirm with stakeholders that historical signature versions aren't needed
3. **Backup first** - Always backup the database before large deletions
4. **Test on non-production** - Run on a test database first to verify

## Verification After Cleanup

After running the cleanup, you can verify the results:

```bash
# Check signature counts
python3 investigate_signatures.py

# Should show:
# - Total signatures: ~2,723 (down from 312,011)
# - No species with multiple versions
# - SENSITIVE_FIELD: ~4,734 (down from 730,952)
# - LINES_IN_SIGN: ~5,699 (down from 842,490)
```

## Related Documentation

- **`SIGNATURE_CLEANUP_ANALYSIS.md`** - Detailed investigation results
- **`investigate_signatures.py`** - Investigation script
- **`verify_signature_relationships.py`** - Relationship verification script

## Best Practices

1. **Always run dry-run first**
   ```bash
   python3 cleanup_old_signatures.py --dry-run
   ```

2. **Review the output carefully**
   - Check the statistics
   - Verify the percentage seems reasonable
   - Look at the sample records being deleted

3. **Backup the database** (if in production)
   ```bash
   # Example backup command (adjust for your setup)
   sqlcmd -S localhost -U sa -Q "BACKUP DATABASE iSTSGUAT TO DISK='/path/to/backup.bak'"
   ```

4. **Run during off-peak hours**
   - Deletion takes 15-30 minutes
   - May impact database performance during execution

5. **Monitor the logs**
   ```bash
   tail -f Cleanup_Old_Signatures_LOG.txt
   ```

## Conclusion

The signature cleanup tool safely removes 99.1% of signature-related records (1.87 million total) while preserving all functional signature data. This is a highly recommended cleanup operation that significantly improves database performance and maintainability with zero functional impact.

**Your original assessment was 100% correct:** keeping only the latest version makes perfect sense, and the investigation confirmed there are no technical barriers to doing so.
