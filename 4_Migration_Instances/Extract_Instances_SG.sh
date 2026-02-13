#!/bin/bash
# Extract Instances (Sections) - Singapore
# macOS equivalent of Extract_Instances_SG.bat
# Uses extract_instances_sections.py with MAP file support

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
LOG_FILE="Extract_Instances_SG_LOG.txt"

echo "Extract_Instances_SG Script started at: ${START_TIME}"
echo "-----------------------------------------------------------------------"
echo "Database: ${SQL_SG_Database}"
echo "Input CSV: ${Instances_Input_SG}"
echo "Output Folder: ${Instances_Output_SG}"
echo "Start Year: ${Instances_StartYear_SG}"
echo "-----------------------------------------------------------------------"

# Prompt for MAP folder (for segment name lookups and MAP_FILE_EXISTS)
echo ""
if [ -n "${MapFiles_SG}" ] && [ -d "${MapFiles_SG}" ]; then
    echo "Default MAP folder: ${MapFiles_SG}"
    read -p "Enter MAP folder path [press Enter for default]: " MAP_FOLDER_INPUT
    if [ -z "${MAP_FOLDER_INPUT}" ]; then
        MAP_FOLDER="${MapFiles_SG}"
    else
        MAP_FOLDER="${MAP_FOLDER_INPUT}"
    fi
else
    read -p "Enter MAP folder path (contains .MAP files): " MAP_FOLDER
fi

# Validate MAP folder (optional - script works without it, SEGMENTS will be empty)
if [ -n "${MAP_FOLDER}" ] && [ ! -d "${MAP_FOLDER}" ]; then
    echo "WARNING: MAP folder does not exist: ${MAP_FOLDER}"
    echo "SEGMENTS and MAP_FILE_EXISTS columns will be empty."
    read -p "Continue anyway? (y/N): " CONTINUE
    if [ "${CONTINUE}" != "y" ] && [ "${CONTINUE}" != "Y" ]; then
        echo "Aborted."
        exit 1
    fi
fi
echo "MAP Folder: ${MAP_FOLDER:-<not set>}"

# Create output directory if it doesn't exist
mkdir -p "${Instances_Output_SG}"

# Run the extract_instances_sections script
CMD="python3 extract_instances_sections.py --server \"${SQLServer}\" --database \"${SQL_SG_Database}\" --user \"${SQLUser}\" --password \"${SQLPassword}\" --input \"${Instances_Input_SG}\" --output-dir \"${Instances_Output_SG}\" --start-year \"${Instances_StartYear_SG}\" --quiet"

if [ -n "${MAP_FOLDER}" ]; then
    CMD="${CMD} --map-dir \"${MAP_FOLDER}\""
fi

eval ${CMD}

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
echo "[${START_TIME}] Country: SG | DB: ${SQL_SG_Database} | Start Year: ${Instances_StartYear_SG} | Duration: ${DURATION}" >> "${LOG_FILE}"

echo "Log updated in ${LOG_FILE}"
echo ""
read -p "Press Enter to continue..."
