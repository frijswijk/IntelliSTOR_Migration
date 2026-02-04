#!/bin/bash
# Cleanup Report Instances
# macOS command wrapper for cleanup_report_instances.py

clear

# Change to script directory (important when launched from Finder)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# Source environment variables
source "${SCRIPT_DIR}/Migration_Environment.sh"

# Activate virtual environment
source "${SCRIPT_DIR}/venv/bin/activate"

# --- Display Header ---
echo "========================================================================"
echo "IntelliSTOR Database Cleanup Tool"
echo "========================================================================"
echo "Database: ${SQL_SG_Database}"
echo "Server: ${SQLServer}"
echo "========================================================================"
echo ""

# --- Get date range from user ---
echo "This script will DELETE report instances and associated data."
echo "You can specify a date range to delete instances."
echo ""
echo "Options:"
echo "  1) Delete up to a specific date (from beginning)"
echo "  2) Delete from a specific date onwards (e.g., future test data)"
echo "  3) Delete within a specific date range"
echo ""
read -p "Enter choice [1, 2, or 3]: " DATE_CHOICE

START_DATE=""
END_DATE=""

if [ "$DATE_CHOICE" = "1" ]; then
    echo ""
    echo "Delete all instances from the beginning up to (and including) a date."
    echo "Enter the end date (YYYY-MM-DD) or press Enter to cancel:"
    read -p "> " END_DATE

    if [ -z "$END_DATE" ]; then
        echo ""
        echo "Operation cancelled."
        echo ""
        read -p "Press Enter to exit..."
        exit 0
    fi

elif [ "$DATE_CHOICE" = "2" ]; then
    echo ""
    echo "Delete all instances from a start date onwards (useful for test data)."
    echo "Enter the start date (YYYY-MM-DD) or press Enter to cancel:"
    read -p "> " START_DATE

    if [ -z "$START_DATE" ]; then
        echo ""
        echo "Operation cancelled."
        echo ""
        read -p "Press Enter to exit..."
        exit 0
    fi

elif [ "$DATE_CHOICE" = "3" ]; then
    echo ""
    echo "Delete all instances within a specific date range."
    echo "Enter the start date (YYYY-MM-DD) or press Enter to cancel:"
    read -p "> " START_DATE

    if [ -z "$START_DATE" ]; then
        echo ""
        echo "Operation cancelled."
        echo ""
        read -p "Press Enter to exit..."
        exit 0
    fi

    echo "Enter the end date (YYYY-MM-DD) or press Enter to cancel:"
    read -p "> " END_DATE

    if [ -z "$END_DATE" ]; then
        echo ""
        echo "Operation cancelled."
        echo ""
        read -p "Press Enter to exit..."
        exit 0
    fi

else
    echo ""
    echo "Invalid choice. Operation cancelled."
    echo ""
    read -p "Press Enter to exit..."
    exit 0
fi

# --- Ask for dry run or actual deletion ---
echo ""
echo "Choose an option:"
echo "  1) Dry run (show what would be deleted, no actual deletion)"
echo "  2) Actually delete data (PERMANENT)"
echo ""
read -p "Enter choice [1 or 2]: " CHOICE

if [ "$CHOICE" = "1" ]; then
    DRY_RUN="--dry-run"
    echo ""
    echo "Running in DRY RUN mode..."
elif [ "$CHOICE" = "2" ]; then
    DRY_RUN=""
    echo ""
    echo "WARNING: This will PERMANENTLY delete data!"
else
    echo ""
    echo "Invalid choice. Operation cancelled."
    echo ""
    read -p "Press Enter to exit..."
    exit 0
fi

# --- Ask about performance mode ---
echo ""
echo "For large deletions (1000+ instances), do you want to use FAST MODE?"
echo "  Fast mode skips orphan file checking (much faster but may leave orphan MAP/RPT files)"
echo ""
echo "  1) Normal mode (checks for orphan files - SLOW for bulk deletions)"
echo "  2) Fast mode (skip orphan check - RECOMMENDED for 1000+ instances)"
echo ""
read -p "Enter choice [1 or 2]: " PERF_CHOICE

SKIP_ORPHAN=""
if [ "$PERF_CHOICE" = "2" ]; then
    SKIP_ORPHAN="--skip-orphan-check"
    echo ""
    echo "Using FAST MODE (orphan check disabled)"
fi

# --- Capture Start Time ---
START_TIME=$(date +"%Y-%m-%d %H:%M:%S")
START_SECONDS=$(date +%s)
LOG_FILE="Cleanup_Report_Instances_LOG.txt"

echo ""
echo "========================================================================"
echo "Cleanup started at: ${START_TIME}"
echo "========================================================================"
echo ""

# Build the command with appropriate arguments
CMD_ARGS="${DRY_RUN} ${SKIP_ORPHAN}"
if [ -n "$START_DATE" ]; then
    CMD_ARGS="${CMD_ARGS} --start-date ${START_DATE}"
fi
if [ -n "$END_DATE" ]; then
    CMD_ARGS="${CMD_ARGS} --end-date ${END_DATE}"
fi

# Run the cleanup script
python3 cleanup_report_instances.py ${CMD_ARGS}

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

    DATE_RANGE=""
    if [ -n "$START_DATE" ] && [ -n "$END_DATE" ]; then
        DATE_RANGE="Range: ${START_DATE} to ${END_DATE}"
    elif [ -n "$START_DATE" ]; then
        DATE_RANGE="From: ${START_DATE}"
    elif [ -n "$END_DATE" ]; then
        DATE_RANGE="Up to: ${END_DATE}"
    fi

    echo "[${START_TIME}] DB: ${SQL_SG_Database} | ${DATE_RANGE} | Mode: ${MODE} | Duration: ${DURATION} | Status: SUCCESS" >> "${LOG_FILE}"
    echo ""
    echo "Log updated in ${LOG_FILE}"
else
    DATE_RANGE=""
    if [ -n "$START_DATE" ] && [ -n "$END_DATE" ]; then
        DATE_RANGE="Range: ${START_DATE} to ${END_DATE}"
    elif [ -n "$START_DATE" ]; then
        DATE_RANGE="From: ${START_DATE}"
    elif [ -n "$END_DATE" ]; then
        DATE_RANGE="Up to: ${END_DATE}"
    fi

    echo "[${START_TIME}] DB: ${SQL_SG_Database} | ${DATE_RANGE} | Duration: ${DURATION} | Status: FAILED" >> "${LOG_FILE}"
    echo ""
    echo "ERROR: Script failed. Check log in ${LOG_FILE}"
fi

echo ""
read -p "Press Enter to exit..."
