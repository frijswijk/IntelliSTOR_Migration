#!/bin/bash
# Extract Instances - Malaysia
# macOS equivalent of Extract_Instances_MY.bat

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
LOG_FILE="Extract_Instances_MY_LOG.txt"

echo "Extract_Instances_MY Script started at: ${START_TIME}"
echo "-----------------------------------------------------------------------"
echo "Database: ${SQL_MY_Database}"
echo "Input CSV: ${Instances_Input_MY}"
echo "Output Folder: ${Instances_Output_MY}"
echo "Start Year: ${Instances_StartYear_MY}"
echo "-----------------------------------------------------------------------"

# Prompt for RPT folder (mandatory - SEGMENTS come from RPT file SECTIONHDR)
while true; do
    echo ""
    read -p "Enter RPT folder path (contains .RPT files for SEGMENTS extraction): " RPT_FOLDER
    if [ -z "${RPT_FOLDER}" ]; then
        echo "ERROR: RPT folder is required for SEGMENTS extraction."
    elif [ ! -d "${RPT_FOLDER}" ]; then
        echo "ERROR: Directory does not exist: ${RPT_FOLDER}"
    else
        echo "RPT Folder: ${RPT_FOLDER}"
        break
    fi
done

# Create output directory if it doesn't exist
mkdir -p "${Instances_Output_MY}"

# Run the Extract_Instances script
python3 Extract_Instances.py --server "${SQLServer}" --database "${SQL_MY_Database}" --user "${SQLUser}" --password "${SQLPassword}" --input "${Instances_Input_MY}" --output "${Instances_Output_MY}" --start-year "${Instances_StartYear_MY}" --rptfolder "${RPT_FOLDER}" --quiet

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
echo "[${START_TIME}] Country: MY | DB: ${SQL_MY_Database} | Start Year: ${Instances_StartYear_MY} | Duration: ${DURATION}" >> "${LOG_FILE}"

echo "Log updated in ${LOG_FILE}"
echo ""
read -p "Press Enter to continue..."
