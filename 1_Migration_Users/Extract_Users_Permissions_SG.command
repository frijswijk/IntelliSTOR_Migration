#!/bin/bash
# Extract Users Permissions - Singapore
# macOS equivalent of Extract_Users_permissions_SG.bat

clear

# Change to script directory (important when launched from Finder)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# Source environment variables
source "${SCRIPT_DIR}/../Migration_Environment.sh"

# Activate virtual environment
source "${SCRIPT_DIR}/../venv/bin/activate"

# --- 1. Capture Start Time ---
START_TIME=$(date +"%Y-%m-%d %H:%M:%S")
START_SECONDS=$(date +%s)
LOG_FILE="Extract_Users_Permissions_SG_LOG.txt"
FLAG=""
# FLAG="--TESTDATA"

echo "Extract_Users_Permissions_SG Script started at: ${START_TIME}"
echo "-----------------------------------------------------------------------"

# Run the Python script
python3 Extract_Users_Permissions.py --server "${SQLServer}" --database "${SQL_SG_Database}" --output "${Users_SG}" --user "${SQLUser}" --password "${SQLPassword}" --quiet ${FLAG}

# --- 2. Capture End Time and Calculate Duration ---
echo "-----------------------------------------------------------------------"
END_TIME=$(date +"%Y-%m-%d %H:%M:%S")
END_SECONDS=$(date +%s)
echo "Script finished at: ${END_TIME}"

# Calculate duration
DURATION_SECONDS=$((END_SECONDS - START_SECONDS))
HOURS=$((DURATION_SECONDS / 3600))
MINUTES=$(((DURATION_SECONDS % 3600) / 60))
SECONDS=$((DURATION_SECONDS % 60))
DURATION=$(printf "%02d:%02d:%02d" $HOURS $MINUTES $SECONDS)

echo "Total Time Elapsed: ${DURATION}"

# --- 3. Logging Section ---
echo "[${START_TIME}] Country: SG | DB: ${SQL_SG_Database} | Flag: ${FLAG} | Duration: ${DURATION}" >> "${LOG_FILE}"

echo "Log updated in ${LOG_FILE}"
echo ""
read -p "Press Enter to continue..."
