#!/bin/bash
# RPT Page Extractor - Interactive Menu
# macOS launcher for rpt_page_extractor.py
# Double-click this file in Finder to launch

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

# Default RPT file directory (from Migration_Environment or fallback)
RPT_DIR="${RPT_DIR:-${Migration_data:-/Volumes/acasis/projects/python/ocbc/Migration_Data}}"

echo "============================================================"
echo "  RPT Page Extractor - IntelliSTOR RPT File Tool"
echo "============================================================"
echo ""
echo "Current Directory: ${SCRIPT_DIR}"
echo "RPT Files Directory: ${RPT_DIR}"
echo ""
echo "Options:"
echo "  1. Show RPT file info (sections, page table, compression)"
echo "  2. Extract all pages from an RPT file"
echo "  3. Extract page range from an RPT file"
echo "  4. Extract pages for one or more sections (by SECTION_ID)"
echo "  5. Extract all RPT files in a folder"
echo "  6. Show help"
echo "  0. Exit"
echo ""
read -p "Select option [0-6]: " OPTION

case $OPTION in
    1)
        echo ""
        echo "Available RPT files in ${RPT_DIR}:"
        ls -1 "${RPT_DIR}"/*.RPT 2>/dev/null | xargs -I {} basename {}
        echo ""
        read -p "Enter RPT filename or full path: " RPT_FILE
        if [ -n "$RPT_FILE" ]; then
            # If just a filename, prepend RPT_DIR
            if [ ! -f "$RPT_FILE" ]; then
                RPT_FILE="${RPT_DIR}/${RPT_FILE}"
            fi
            echo ""
            python3 rpt_page_extractor.py --info "$RPT_FILE"
        fi
        ;;
    2)
        echo ""
        echo "Available RPT files in ${RPT_DIR}:"
        ls -1 "${RPT_DIR}"/*.RPT 2>/dev/null | xargs -I {} basename {}
        echo ""
        read -p "Enter RPT filename or full path: " RPT_FILE
        read -p "Enter output directory [./extracted]: " OUTPUT_DIR
        OUTPUT_DIR="${OUTPUT_DIR:-./extracted}"
        if [ -n "$RPT_FILE" ]; then
            if [ ! -f "$RPT_FILE" ]; then
                RPT_FILE="${RPT_DIR}/${RPT_FILE}"
            fi
            echo ""
            python3 rpt_page_extractor.py --output "$OUTPUT_DIR" "$RPT_FILE"
        fi
        ;;
    3)
        echo ""
        echo "Available RPT files in ${RPT_DIR}:"
        ls -1 "${RPT_DIR}"/*.RPT 2>/dev/null | xargs -I {} basename {}
        echo ""
        read -p "Enter RPT filename or full path: " RPT_FILE
        read -p "Enter page range (e.g., 1-10, 5): " PAGE_RANGE
        read -p "Enter output directory [./extracted]: " OUTPUT_DIR
        OUTPUT_DIR="${OUTPUT_DIR:-./extracted}"
        if [ -n "$RPT_FILE" ] && [ -n "$PAGE_RANGE" ]; then
            if [ ! -f "$RPT_FILE" ]; then
                RPT_FILE="${RPT_DIR}/${RPT_FILE}"
            fi
            echo ""
            python3 rpt_page_extractor.py --pages "$PAGE_RANGE" --output "$OUTPUT_DIR" "$RPT_FILE"
        fi
        ;;
    4)
        echo ""
        echo "Available RPT files in ${RPT_DIR}:"
        ls -1 "${RPT_DIR}"/*.RPT 2>/dev/null | xargs -I {} basename {}
        echo ""
        read -p "Enter RPT filename or full path: " RPT_FILE
        if [ -n "$RPT_FILE" ]; then
            if [ ! -f "$RPT_FILE" ]; then
                RPT_FILE="${RPT_DIR}/${RPT_FILE}"
            fi
            # First show sections so user can pick one
            echo ""
            echo "Sections in this RPT file:"
            python3 rpt_page_extractor.py --info "$RPT_FILE" 2>/dev/null | grep -E '(SECTION_ID|^\s+[0-9])'
            echo ""
            echo "Enter one or more SECTION_IDs separated by spaces."
            echo "Missing IDs will be skipped. Pages are extracted in the order given."
            read -p "Enter SECTION_ID(s) to extract: " SECTION_IDS
            read -p "Enter output directory [./extracted]: " OUTPUT_DIR
            OUTPUT_DIR="${OUTPUT_DIR:-./extracted}"
            if [ -n "$SECTION_IDS" ]; then
                echo ""
                # shellcheck disable=SC2086
                python3 rpt_page_extractor.py --section-id $SECTION_IDS --output "$OUTPUT_DIR" "$RPT_FILE"
            fi
        fi
        ;;
    5)
        echo ""
        read -p "Enter folder containing RPT files [${RPT_DIR}]: " FOLDER
        FOLDER="${FOLDER:-${RPT_DIR}}"
        read -p "Enter output directory [./extracted]: " OUTPUT_DIR
        OUTPUT_DIR="${OUTPUT_DIR:-./extracted}"
        echo ""
        python3 rpt_page_extractor.py --folder "$FOLDER" --output "$OUTPUT_DIR"
        ;;
    6)
        echo ""
        python3 rpt_page_extractor.py --help
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
