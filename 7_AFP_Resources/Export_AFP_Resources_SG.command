#!/bin/bash
# Export AFP Resources - Singapore
# macOS equivalent of Export_AFP_Resources_SG.bat

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
LOG_FILE="Export_AFP_Resources_SG_LOG.txt"

echo "Export_AFP_Resources_SG Script started at: ${START_TIME}"
echo "-----------------------------------------------------------------------"
echo "Input CSV: ${AFP_Output}/AFP_Resources_SG.csv"
echo "Export Folder: ${AFP_Export_SG}"
echo "-----------------------------------------------------------------------"

# Create output directory if it doesn't exist
mkdir -p "${AFP_Export_SG}"

# Run the AFP Resource Exporter
python3 AFP_Resource_Exporter.py --input-csv "${AFP_Output}/AFP_Resources_SG.csv" --output-folder "${AFP_Export_SG}" --quiet

# --- 2. Capture End Time and Calculate Duration ---
echo "-----------------------------------------------------------------------"
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

# --- 3. Logging Section ---
echo "[${START_TIME}] Country: SG | CSV: ${AFP_Output}/AFP_Resources_SG.csv | Export: ${AFP_Export_SG} | Duration: ${DURATION}" >> "${LOG_FILE}"

echo "Log updated in ${LOG_FILE}"
echo ""
read -p "Press Enter to continue..."
