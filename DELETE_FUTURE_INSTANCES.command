#!/bin/bash
# Quick script to delete future test instances (2026 onwards)

clear

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# Source environment
source "${SCRIPT_DIR}/Migration_Environment.sh"
source "${SCRIPT_DIR}/venv/bin/activate"

echo "========================================================================"
echo "DELETE FUTURE TEST INSTANCES (2026 onwards)"
echo "========================================================================"
echo "Database: ${SQL_SG_Database}"
echo "Server: ${SQLServer}"
echo "========================================================================"
echo ""
echo "This will delete ALL instances from 2026-01-01 onwards."
echo ""
echo "⚠️  WARNING: This is NOT a dry-run - this will ACTUALLY DELETE data!"
echo ""
read -p "Type exactly 'DELETE' (without quotes) to proceed, or press Enter to cancel: " CONFIRM

if [ "$CONFIRM" != "DELETE" ]; then
    echo ""
    echo "✓ Operation cancelled (you typed: '$CONFIRM')"
    echo "  You must type exactly: DELETE"
    echo ""
    read -p "Press Enter to exit..."
    exit 0
fi

echo ""
echo "========================================================================"
echo "Starting deletion process..."
echo "========================================================================"

# Run the cleanup script WITHOUT --dry-run flag
python3 cleanup_report_instances.py --start-date 2026-01-01

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ Deletion completed successfully"
else
    echo "✗ Deletion failed with exit code: $EXIT_CODE"
fi

echo ""
read -p "Press Enter to exit..."
