#!/bin/bash
# Batch Zip Encrypt - Malaysia
# macOS equivalent of Batch_Zip_Encrypt_MY.bat

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
LOG_FILE="Batch_Zip_Encrypt_MY_LOG.txt"

echo "Batch_Zip_Encrypt_MY Script started at: ${START_TIME}"
echo "-----------------------------------------------------------------------"
echo "Source Folder: ${ZipEncrypt_SourceFolder_MY}"
echo "Output Folder: ${ZipEncrypt_OutputFolder_MY}"
echo "Species CSV: ${ZipEncrypt_SpeciesCSV_MY}"
echo "Instances Folder: ${ZipEncrypt_InstancesFolder_MY}"
echo "Compression Level: ${ZipEncrypt_CompressionLevel}"
echo "Max Species per Run: ${ZipEncrypt_MaxSpecies}"
echo "Delete After Compress: ${ZipEncrypt_DeleteAfterCompress}"
echo "Password Protected: Yes"
echo "-----------------------------------------------------------------------"

# Create output directory if it doesn't exist
mkdir -p "${ZipEncrypt_OutputFolder_MY}"

# Run the batch_zip_encrypt script
python3 batch_zip_encrypt.py --source-folder "${ZipEncrypt_SourceFolder_MY}" --output-folder "${ZipEncrypt_OutputFolder_MY}" --password "${ZipEncrypt_Password}" --species-csv "${ZipEncrypt_SpeciesCSV_MY}" --instances-folder "${ZipEncrypt_InstancesFolder_MY}" --compression-level "${ZipEncrypt_CompressionLevel}" --max-species "${ZipEncrypt_MaxSpecies}" --delete-after-compress "${ZipEncrypt_DeleteAfterCompress}" --quiet

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
echo "[${START_TIME}] Country: MY | Compression: ${ZipEncrypt_CompressionLevel} | Max Species: ${ZipEncrypt_MaxSpecies} | Delete: ${ZipEncrypt_DeleteAfterCompress} | Duration: ${DURATION}" >> "${LOG_FILE}"

echo "Log updated in ${LOG_FILE}"
echo ""
read -p "Press Enter to continue..."
