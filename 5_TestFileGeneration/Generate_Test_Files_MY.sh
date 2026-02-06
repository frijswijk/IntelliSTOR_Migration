#!/bin/bash
# Generate Test Files - Malaysia
# macOS equivalent of Generate_Test_Files_MY.bat

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
LOG_FILE="Generate_Test_Files_MY_LOG.txt"

echo "Generate_Test_Files_MY Script started at: ${START_TIME}"
echo "-----------------------------------------------------------------------"
echo "Report Species CSV: ${TestGen_ReportSpecies_MY}"
echo "Folder Extract: ${TestGen_FolderExtract_MY}"
echo "Target Folder: ${TestGen_TargetFolder_MY}"
echo "Max Species per Run: ${TestGen_MaxSpecies}"
echo "-----------------------------------------------------------------------"

# Create target directory if it doesn't exist
mkdir -p "${TestGen_TargetFolder_MY}"

# Run the Generate_Test_Files script
python3 Generate_Test_Files.py --ReportSpecies "${TestGen_ReportSpecies_MY}" --FolderExtract "${TestGen_FolderExtract_MY}" --TargetFolder "${TestGen_TargetFolder_MY}" --Number "${TestGen_MaxSpecies}" --quiet

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
echo "[${START_TIME}] Country: MY | Max Species: ${TestGen_MaxSpecies} | Target: ${TestGen_TargetFolder_MY} | Duration: ${DURATION}" >> "${LOG_FILE}"

echo "Log updated in ${LOG_FILE}"
echo ""
read -p "Press Enter to continue..."
