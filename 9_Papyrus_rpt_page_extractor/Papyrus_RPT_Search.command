#!/bin/bash
# Papyrus RPT Search - MAP File Index Search Tool
# macOS launcher for papyrus_rpt_search.py
# Searches for indexed field values in binary MAP files

clear

# Change to script directory (important when launched from Finder)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# Source environment variables
source "${SCRIPT_DIR}/../Migration_Environment.sh"

# Activate virtual environment
source "${SCRIPT_DIR}/../venv/bin/activate"

echo "======================================================================="
echo "  Papyrus RPT Search - MAP File Index Search Tool"
echo "======================================================================="
echo ""

# --- Determine MAP folder ---
MAP_DIR=""
if [ -n "${MapFiles_SG}" ] && [ -d "${MapFiles_SG}" ]; then
    MAP_DIR="${MapFiles_SG}"
    echo "Default MAP folder: ${MAP_DIR}"
else
    echo "No default MAP folder found in environment."
fi

read -p "Enter MAP folder path [${MAP_DIR:-none}]: " MAP_DIR_INPUT
if [ -n "${MAP_DIR_INPUT}" ]; then
    MAP_DIR="${MAP_DIR_INPUT}"
fi

if [ -z "${MAP_DIR}" ] || [ ! -d "${MAP_DIR}" ]; then
    echo "ERROR: MAP folder not found: ${MAP_DIR:-<not set>}"
    echo "Please provide a valid directory containing .MAP files."
    read -p "Press Enter to exit..."
    exit 1
fi

echo ""
echo "MAP Folder: ${MAP_DIR}"
echo "-----------------------------------------------------------------------"
echo ""

# --- Select mode ---
echo "Modes:"
echo "  1) Search for a value in a MAP file"
echo "  2) List indexed fields in a MAP file"
echo "  3) List all values for a field"
echo ""
read -p "Select mode [1/2/3]: " MODE

case "${MODE}" in
    1)
        # --- Search mode ---
        echo ""
        echo "--- Search Mode ---"
        echo ""

        # Select MAP file
        read -p "Enter MAP filename (e.g. 25001002.MAP): " MAP_FILE
        MAP_PATH="${MAP_DIR}/${MAP_FILE}"

        if [ ! -f "${MAP_PATH}" ]; then
            echo "ERROR: MAP file not found: ${MAP_PATH}"
            read -p "Press Enter to exit..."
            exit 1
        fi

        # Get field IDs
        echo ""
        echo "Specify the field to search (LINE_ID and FIELD_ID)."
        echo "Use --list-fields mode (option 2) to discover available fields."
        echo ""
        read -p "Enter LINE_ID: " LINE_ID
        read -p "Enter FIELD_ID: " FIELD_ID

        # Get search value
        echo ""
        read -p "Enter search value: " SEARCH_VALUE

        # Prefix match?
        read -p "Enable prefix matching? (y/N): " PREFIX_INPUT
        PREFIX_FLAG=""
        if [ "${PREFIX_INPUT}" = "y" ] || [ "${PREFIX_INPUT}" = "Y" ]; then
            PREFIX_FLAG="--prefix"
        fi

        # Output format
        read -p "Output format (table/csv/json) [table]: " FORMAT
        FORMAT="${FORMAT:-table}"

        echo ""
        echo "-----------------------------------------------------------------------"
        echo "Searching..."
        echo ""

        python3 papyrus_rpt_search.py \
            --map "${MAP_PATH}" \
            --line-id "${LINE_ID}" \
            --field-id "${FIELD_ID}" \
            --value "${SEARCH_VALUE}" \
            --format "${FORMAT}" \
            ${PREFIX_FLAG}
        ;;

    2)
        # --- List fields mode ---
        echo ""
        echo "--- List Fields Mode ---"
        echo ""

        read -p "Enter MAP filename (e.g. 25001002.MAP): " MAP_FILE
        MAP_PATH="${MAP_DIR}/${MAP_FILE}"

        if [ ! -f "${MAP_PATH}" ]; then
            echo "ERROR: MAP file not found: ${MAP_PATH}"
            read -p "Press Enter to exit..."
            exit 1
        fi

        # Optional metadata
        read -p "Metadata JSON file (optional, press Enter to skip): " METADATA_FILE
        METADATA_FLAG=""
        if [ -n "${METADATA_FILE}" ] && [ -f "${METADATA_FILE}" ]; then
            METADATA_FLAG="--metadata ${METADATA_FILE}"
        fi

        echo ""
        python3 papyrus_rpt_search.py \
            --map "${MAP_PATH}" \
            --list-fields \
            ${METADATA_FLAG}
        ;;

    3)
        # --- List values mode ---
        echo ""
        echo "--- List Values Mode ---"
        echo ""

        read -p "Enter MAP filename (e.g. 25001002.MAP): " MAP_FILE
        MAP_PATH="${MAP_DIR}/${MAP_FILE}"

        if [ ! -f "${MAP_PATH}" ]; then
            echo "ERROR: MAP file not found: ${MAP_PATH}"
            read -p "Press Enter to exit..."
            exit 1
        fi

        read -p "Enter LINE_ID: " LINE_ID
        read -p "Enter FIELD_ID: " FIELD_ID

        read -p "Max values to show (0 = all) [0]: " MAX_VALUES
        MAX_VALUES="${MAX_VALUES:-0}"

        echo ""
        python3 papyrus_rpt_search.py \
            --map "${MAP_PATH}" \
            --line-id "${LINE_ID}" \
            --field-id "${FIELD_ID}" \
            --list-values \
            --max-values "${MAX_VALUES}"
        ;;

    *)
        echo "Invalid selection."
        ;;
esac

echo ""
echo "-----------------------------------------------------------------------"
echo ""
read -p "Press Enter to continue..."
