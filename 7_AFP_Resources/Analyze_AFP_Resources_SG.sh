#!/bin/bash
# Analyze AFP Resources - Singapore
# macOS equivalent of Analyze_AFP_Resources_SG.bat

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
LOG_FILE="Analyze_AFP_Resources_SG_LOG.txt"
NAMESPACE="SG"
# NAMESPACE="DEFAULT"

echo "Analyze_AFP_Resources_SG Script started at: ${START_TIME}"
echo "-----------------------------------------------------------------------"
echo "Source Folder: ${AFP_Source_SG}"
echo "Output Folder: ${AFP_Output}"
echo "Namespace: ${NAMESPACE}"
echo "Version Compare: ${AFP_VersionCompare}"
echo "From Year: ${AFP_FromYear}"
echo "All Namespaces: ${AFP_AllNameSpaces}"
echo "-----------------------------------------------------------------------"

# Create output directory if it doesn't exist
mkdir -p "${AFP_Output}"

# Build command with optional flags
CMD="python3 Analyze_AFP_Resources.py --folder \"${AFP_Source_SG}\" --output-csv \"${AFP_Output}/AFP_Resources_SG.csv\" --namespace ${NAMESPACE} --quiet"

# Add --version-compare flag if enabled
if [ "${AFP_VersionCompare,,}" == "yes" ]; then
    CMD="${CMD} --version-compare"
fi

# Add --FROMYEAR flag if specified
if [ -n "${AFP_FromYear}" ]; then
    CMD="${CMD} --FROMYEAR ${AFP_FromYear}"
fi

# Add --AllNameSpaces flag if enabled
if [ "${AFP_AllNameSpaces,,}" == "yes" ]; then
    CMD="${CMD} --AllNameSpaces"
fi

# Run the AFP Resource Analyzer
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
echo "[${START_TIME}] Country: SG | Source: ${AFP_Source_SG} | Namespace: ${NAMESPACE} | VersionCompare: ${AFP_VersionCompare} | FromYear: ${AFP_FromYear} | AllNameSpaces: ${AFP_AllNameSpaces} | Duration: ${DURATION}" >> "${LOG_FILE}"

echo "Log updated in ${LOG_FILE}"
echo ""
read -p "Press Enter to continue..."
