#!/bin/bash
# IntelliSTOR Viewer - Interactive Menu
# macOS launcher for intellistor_viewer.py

clear

# Change to script directory (important when launched from Finder)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# Source environment variables if available
if [ -f "${SCRIPT_DIR}/../Migration_Environment.sh" ]; then
    source "${SCRIPT_DIR}/../Migration_Environment.sh"
fi

# Activate virtual environment if available
if [ -f "${SCRIPT_DIR}/../venv/bin/activate" ]; then
    source "${SCRIPT_DIR}/../venv/bin/activate"
fi

# Default MAP file directory
MAP_DIR="${MAP_DIR:-/Volumes/X9Pro/OCBC/250_MapFiles}"

echo "============================================================"
echo "  IntelliSTOR Viewer - Interactive Menu"
echo "============================================================"
echo ""
echo "Current Directory: ${SCRIPT_DIR}"
echo "MAP Files Directory: ${MAP_DIR}"
echo ""
echo "Options:"
echo "  1. Analyze MAP file"
echo "  2. Analyze MAP file with sample entries"
echo "  3. Search MAP file index"
echo "  4. Analyze spool file"
echo "  5. Show report info (requires database)"
echo "  6. Run default sample analysis"
echo "  7. Show help"
echo "  0. Exit"
echo ""
read -p "Select option [0-7]: " OPTION

case $OPTION in
    1)
        echo ""
        echo "Available MAP files (first 20):"
        ls -1 "${MAP_DIR}"/*.MAP 2>/dev/null | head -20 | xargs -I {} basename {}
        echo ""
        read -p "Enter MAP filename (e.g., 25001002.MAP): " MAP_FILE
        if [ -n "$MAP_FILE" ]; then
            echo ""
            python3 intellistor_viewer.py --map "$MAP_FILE" --map-dir "$MAP_DIR"
        fi
        ;;
    2)
        echo ""
        echo "Available MAP files (first 20):"
        ls -1 "${MAP_DIR}"/*.MAP 2>/dev/null | head -20 | xargs -I {} basename {}
        echo ""
        read -p "Enter MAP filename (e.g., 25001002.MAP): " MAP_FILE
        if [ -n "$MAP_FILE" ]; then
            echo ""
            python3 intellistor_viewer.py --map "$MAP_FILE" --show-entries --map-dir "$MAP_DIR"
        fi
        ;;
    3)
        echo ""
        echo "Available MAP files (first 20):"
        ls -1 "${MAP_DIR}"/*.MAP 2>/dev/null | head -20 | xargs -I {} basename {}
        echo ""
        read -p "Enter MAP filename (e.g., 25001002.MAP): " MAP_FILE
        read -p "Enter search value: " SEARCH_VALUE
        read -p "Enter LINE_ID: " LINE_ID
        read -p "Enter FIELD_ID: " FIELD_ID
        if [ -n "$MAP_FILE" ] && [ -n "$SEARCH_VALUE" ] && [ -n "$LINE_ID" ] && [ -n "$FIELD_ID" ]; then
            echo ""
            python3 intellistor_viewer.py --map "$MAP_FILE" --search "$SEARCH_VALUE" --line "$LINE_ID" --field "$FIELD_ID" --map-dir "$MAP_DIR"
        fi
        ;;
    4)
        echo ""
        read -p "Enter spool file path: " SPOOL_FILE
        if [ -n "$SPOOL_FILE" ]; then
            echo ""
            python3 intellistor_viewer.py --spool "$SPOOL_FILE"
        fi
        ;;
    5)
        echo ""
        read -p "Enter report name (e.g., CDU100P): " REPORT_NAME
        if [ -n "$REPORT_NAME" ]; then
            echo ""
            python3 intellistor_viewer.py --report "$REPORT_NAME"
        fi
        ;;
    6)
        echo ""
        python3 intellistor_viewer.py
        ;;
    7)
        echo ""
        python3 intellistor_viewer.py --help
        ;;
    0)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo "Invalid option"
        ;;
esac

echo ""
echo "-----------------------------------------------------------------------"
read -p "Press Enter to continue..."
