#!/bin/bash
# Extract Users Permissions - Generic Country Code version
# macOS equivalent of Extract_Users_Permissions_xx.bat
# Usage: ./Extract_Users_Permissions_xx.sh [COUNTRY_CODE] [TESTDATA]
# Example: ./Extract_Users_Permissions_xx.sh MY
# Example: ./Extract_Users_Permissions_xx.sh SG TESTDATA

clear

# Get country code from argument or prompt
COUNTRY_CODE="$1"
if [ -z "$COUNTRY_CODE" ]; then
    read -p "Please enter the Country Code (e.g., MY, SG): " COUNTRY_CODE
fi

# Terminate if still empty
if [ -z "$COUNTRY_CODE" ]; then
    echo "Error: No Country Code provided. Terminating script."
    read -p "Press Enter to continue..."
    exit 1
fi

# Convert to uppercase
COUNTRY_CODE=$(echo "$COUNTRY_CODE" | tr '[:lower:]' '[:upper:]')

# --- TESTDATA LOGIC ---
EXTRA_FLAGS=""
TEST_PARAM="$2"

if [ "$(echo "$TEST_PARAM" | tr '[:lower:]' '[:upper:]')" == "TESTDATA" ]; then
    EXTRA_FLAGS="--TESTDATA"
else
    echo ""
    echo "Would you like to include TESTDATA for ${COUNTRY_CODE}?"
    read -p "Enter Y for Yes, N for No: " CHOICE
    if [ "$(echo "$CHOICE" | tr '[:lower:]' '[:upper:]')" == "Y" ]; then
        EXTRA_FLAGS="--TESTDATA"
    else
        echo "Skipping Test Data..."
    fi
fi

# Change to script directory (important when launched from Finder)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# Source environment variables
source "${SCRIPT_DIR}/../Migration_Environment.sh"

# Activate virtual environment
source "${SCRIPT_DIR}/../venv/bin/activate"

# Dynamically construct variable names and get their values
DB_KEY="SQL_${COUNTRY_CODE}_Database"
DB_ACTUAL_VALUE="${!DB_KEY}"

if [ -z "$DB_ACTUAL_VALUE" ]; then
    echo "Error: Could not find a database setting for \"${DB_KEY}\" in Migration_Environment.sh"
    read -p "Press Enter to continue..."
    exit 1
fi

# Get output path
OUTPUT_KEY="Users_${COUNTRY_CODE}"
OUTPUT_VALUE="${!OUTPUT_KEY}"

if [ -z "$OUTPUT_VALUE" ]; then
    OUTPUT_VALUE="Users-${COUNTRY_CODE}"
fi

echo ""
echo "Database: ${DB_ACTUAL_VALUE}"
echo "Output:   ${OUTPUT_VALUE}"
echo "Flags:    --user [SQLUser] --password [hidden] --quiet ${EXTRA_FLAGS}"
echo ""

python3 Extract_Users_Permissions.py --server "${SQLServer}" --database "${DB_ACTUAL_VALUE}" --output "${OUTPUT_VALUE}" --user "${SQLUser}" --password "${SQLPassword}" --quiet ${EXTRA_FLAGS}

echo ""
read -p "Press Enter to continue..."
