#!/bin/bash
# Cleanup Orphaned MAP/RPT Files
# macOS command wrapper for cleanup_orphaned_files.py

clear

# Change to script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# Source environment variables
source "${SCRIPT_DIR}/Migration_Environment.sh"

# Activate virtual environment
source "${SCRIPT_DIR}/venv/bin/activate"

# --- Display Header ---
echo "========================================================================"
echo "IntelliSTOR Orphaned Files Cleanup Tool"
echo "========================================================================"
echo "Database: ${SQL_SG_Database}"
echo "Server: ${SQLServer}"
echo "========================================================================"
echo ""

# --- Explain what will happen ---
echo "This script will DELETE orphaned MAP and RPT files."
echo ""
echo "Orphaned files are:"
echo "  - MAP files not referenced by any SST_STORAGE record"
echo "  - RPT files not referenced by any RPTFILE_INSTANCE record"
echo ""
echo "These files are typically left behind when using --skip-orphan-check"
echo "during bulk instance deletions."
echo ""
echo "They don't cause problems but waste database space."
echo ""

# --- Ask for dry run or actual deletion ---
echo "Choose an option:"
echo "  1) Dry run (show what would be deleted, no actual deletion)"
echo "  2) Actually delete orphaned files (PERMANENT)"
echo ""
read -p "Enter choice [1 or 2]: " CHOICE

if [ "$CHOICE" = "1" ]; then
    DRY_RUN="--dry-run"
    echo ""
    echo "Running in DRY RUN mode..."
elif [ "$CHOICE" = "2" ]; then
    DRY_RUN=""
    echo ""
    echo "WARNING: This will PERMANENTLY delete orphaned files!"
else
    echo ""
    echo "Invalid choice. Operation cancelled."
    echo ""
    read -p "Press Enter to exit..."
    exit 0
fi

# --- Capture Start Time ---
START_TIME=$(date +"%Y-%m-%d %H:%M:%S")
START_SECONDS=$(date +%s)
LOG_FILE="Cleanup_Orphaned_Files_LOG.txt"

echo ""
echo "========================================================================"
echo "Cleanup started at: ${START_TIME}"
echo "========================================================================"
echo ""

# Run the cleanup script
python3 cleanup_orphaned_files.py ${DRY_RUN}

SCRIPT_EXIT_CODE=$?

# --- Capture End Time and Calculate Duration ---
echo ""
echo "========================================================================"
END_TIME=$(date +"%Y-%m-%d %H:%M:%S")
END_SECONDS=$(date +%s)
echo "Script finished at: ${END_TIME}"

# Calculate duration
DURATION_SECONDS=$((END_SECONDS - START_SECONDS))
HOURS=$((DURATION_SECONDS / 3600))
MINUTES=$(((DURATION_SECONDS % 3600) / 60))
SECS=$((DURATION_SECONDS % 60))
DURATION=$(printf "%02d:%02d:%02d" $HOURS $MINUTES $SECS)

echo "Total Time Elapsed: ${DURATION}"
echo "========================================================================"

# --- Logging Section ---
if [ $SCRIPT_EXIT_CODE -eq 0 ]; then
    MODE="DRY_RUN"
    if [ -z "$DRY_RUN" ]; then
        MODE="DELETED"
    fi

    echo "[${START_TIME}] DB: ${SQL_SG_Database} | Mode: ${MODE} | Duration: ${DURATION} | Status: SUCCESS" >> "${LOG_FILE}"
    echo ""
    echo "Log updated in ${LOG_FILE}"
else
    echo "[${START_TIME}] DB: ${SQL_SG_Database} | Duration: ${DURATION} | Status: FAILED" >> "${LOG_FILE}"
    echo ""
    echo "ERROR: Script failed. Check log in ${LOG_FILE}"
fi

echo ""
read -p "Press Enter to exit..."
