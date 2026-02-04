#!/bin/bash
# Cleanup Old Signature Versions
# macOS command wrapper for cleanup_old_signatures.py

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
echo "IntelliSTOR Signature Cleanup Tool"
echo "========================================================================"
echo "Database: ${SQL_SG_Database}"
echo "Server: ${SQLServer}"
echo "========================================================================"
echo ""

# --- Explain what will happen ---
echo "This script will DELETE old signature versions, keeping only the latest"
echo "version of each signature."
echo ""
echo "What will be cleaned:"
echo "  - Old SIGNATURE versions (keeps latest per species/sign)"
echo "  - Related SENSITIVE_FIELD records"
echo "  - Related LINES_IN_SIGN records"
echo ""
echo "What will NOT be affected:"
echo "  - Latest signature versions (preserved)"
echo "  - SIGN_GEN_INFO (not version-specific)"
echo "  - Report instances (don't link to signatures)"
echo ""

# --- Ask for scope ---
echo "Choose scope:"
echo "  1) Clean all domains (recommended)"
echo "  2) Clean specific domain only"
echo ""
read -p "Enter choice [1 or 2]: " SCOPE_CHOICE

DOMAIN_ARG=""

if [ "$SCOPE_CHOICE" = "2" ]; then
    echo ""
    echo "Enter domain ID (usually 1):"
    read -p "> " DOMAIN_ID

    if [ -z "$DOMAIN_ID" ]; then
        echo ""
        echo "Invalid domain ID. Operation cancelled."
        echo ""
        read -p "Press Enter to exit..."
        exit 0
    fi

    DOMAIN_ARG="--domain-id ${DOMAIN_ID}"
elif [ "$SCOPE_CHOICE" != "1" ]; then
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
    echo "WARNING: This will PERMANENTLY delete old signature versions!"
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
LOG_FILE="Cleanup_Old_Signatures_LOG.txt"

echo ""
echo "========================================================================"
echo "Cleanup started at: ${START_TIME}"
echo "========================================================================"
echo ""

# Run the cleanup script
python3 cleanup_old_signatures.py ${DOMAIN_ARG} ${DRY_RUN}

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

    SCOPE="All domains"
    if [ -n "$DOMAIN_ID" ]; then
        SCOPE="Domain ${DOMAIN_ID}"
    fi

    echo "[${START_TIME}] DB: ${SQL_SG_Database} | ${SCOPE} | Mode: ${MODE} | Duration: ${DURATION} | Status: SUCCESS" >> "${LOG_FILE}"
    echo ""
    echo "Log updated in ${LOG_FILE}"
else
    SCOPE="All domains"
    if [ -n "$DOMAIN_ID" ]; then
        SCOPE="Domain ${DOMAIN_ID}"
    fi

    echo "[${START_TIME}] DB: ${SQL_SG_Database} | ${SCOPE} | Duration: ${DURATION} | Status: FAILED" >> "${LOG_FILE}"
    echo ""
    echo "ERROR: Script failed. Check log in ${LOG_FILE}"
fi

echo ""
read -p "Press Enter to exit..."
