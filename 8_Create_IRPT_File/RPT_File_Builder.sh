#!/bin/bash
# RPT File Builder - Interactive Menu
# Linux/macOS shell script for rpt_file_builder.py

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

# Default directories (from Migration_Environment or fallback)
INPUT_DIR="${INPUT_DIR:-${Migration_data:-/Volumes/acasis/projects/python/ocbc/Migration_Data}}"
RPT_DIR="${RPT_DIR:-${Migration_data:-/Volumes/acasis/projects/python/ocbc/Migration_Data}}"

echo "============================================================"
echo "  RPT File Builder - Create IntelliSTOR RPT Files"
echo "============================================================"
echo ""
echo "Current Directory: ${SCRIPT_DIR}"
echo "Data Directory:    ${INPUT_DIR}"
echo ""
echo "Options:"
echo "  1. Build RPT from text pages (directory)"
echo "  2. Build RPT from text pages (select files)"
echo "  3. Build RPT with embedded PDF/AFP binary"
echo "  4. Build RPT from template (roundtrip rebuild)"
echo "  5. Build RPT with multiple sections"
echo "  6. Dry run / show build plan (--info)"
echo "  7. Show help"
echo "  0. Exit"
echo ""
read -p "Select option [0-7]: " OPTION

case $OPTION in
    1)
        echo ""
        echo "--- Build RPT from a directory of page_NNNNN.txt files ---"
        echo ""
        read -p "Enter directory containing page_*.txt files [${INPUT_DIR}]: " PAGE_DIR
        PAGE_DIR="${PAGE_DIR:-${INPUT_DIR}}"
        read -p "Enter output RPT file path: " OUTPUT_FILE
        read -p "Enter species ID [0]: " SPECIES
        SPECIES="${SPECIES:-0}"
        read -p "Enter domain ID [1]: " DOMAIN
        DOMAIN="${DOMAIN:-1}"
        if [ -n "$OUTPUT_FILE" ]; then
            echo ""
            python3 rpt_file_builder.py --species "$SPECIES" --domain "$DOMAIN" \
                -o "$OUTPUT_FILE" "$PAGE_DIR"
        fi
        ;;
    2)
        echo ""
        echo "--- Build RPT from selected text files ---"
        echo ""
        read -p "Enter text file paths (space-separated): " TEXT_FILES
        read -p "Enter output RPT file path: " OUTPUT_FILE
        read -p "Enter species ID [0]: " SPECIES
        SPECIES="${SPECIES:-0}"
        read -p "Enter domain ID [1]: " DOMAIN
        DOMAIN="${DOMAIN:-1}"
        if [ -n "$OUTPUT_FILE" ] && [ -n "$TEXT_FILES" ]; then
            echo ""
            # shellcheck disable=SC2086
            python3 rpt_file_builder.py --species "$SPECIES" --domain "$DOMAIN" \
                -o "$OUTPUT_FILE" $TEXT_FILES
        fi
        ;;
    3)
        echo ""
        echo "--- Build RPT with embedded PDF/AFP binary object ---"
        echo ""
        read -p "Enter directory or text files (page sources): " PAGE_INPUT
        read -p "Enter path to PDF/AFP file to embed: " BINARY_FILE
        read -p "Enter path to Object Header text file (optional): " OBJ_HEADER
        read -p "Enter output RPT file path: " OUTPUT_FILE
        read -p "Enter species ID [0]: " SPECIES
        SPECIES="${SPECIES:-0}"
        read -p "Enter domain ID [1]: " DOMAIN
        DOMAIN="${DOMAIN:-1}"
        if [ -n "$OUTPUT_FILE" ] && [ -n "$PAGE_INPUT" ]; then
            BINARY_ARG=""
            if [ -n "$BINARY_FILE" ]; then
                BINARY_ARG="--binary $BINARY_FILE"
            fi
            OBJ_ARG=""
            if [ -n "$OBJ_HEADER" ]; then
                OBJ_ARG="--object-header $OBJ_HEADER"
            fi
            echo ""
            # shellcheck disable=SC2086
            python3 rpt_file_builder.py --species "$SPECIES" --domain "$DOMAIN" \
                $BINARY_ARG $OBJ_ARG \
                -o "$OUTPUT_FILE" $PAGE_INPUT
        fi
        ;;
    4)
        echo ""
        echo "--- Build RPT from template (roundtrip rebuild) ---"
        echo ""
        echo "Uses an existing RPT as template to copy instance metadata."
        echo ""
        read -p "Enter template RPT file path: " TEMPLATE_FILE
        read -p "Enter directory containing page_*.txt files: " PAGE_DIR
        read -p "Enter output RPT file path: " OUTPUT_FILE
        read -p "Enter species ID [0]: " SPECIES
        SPECIES="${SPECIES:-0}"
        if [ -n "$OUTPUT_FILE" ] && [ -n "$TEMPLATE_FILE" ] && [ -n "$PAGE_DIR" ]; then
            echo ""
            python3 rpt_file_builder.py --template "$TEMPLATE_FILE" \
                --species "$SPECIES" \
                -o "$OUTPUT_FILE" "$PAGE_DIR"
        fi
        ;;
    5)
        echo ""
        echo "--- Build RPT with multiple sections ---"
        echo ""
        read -p "Enter directory or text files (page sources): " PAGE_INPUT
        read -p "Enter output RPT file path: " OUTPUT_FILE
        echo ""
        echo "Use a sections CSV file? (from RPT Page Extractor --export-sections)"
        read -p "  Enter CSV path (or press Enter for manual entry): " CSV_PATH
        if [ -n "$CSV_PATH" ]; then
            # CSV mode
            read -p "Enter species ID [0, auto from CSV]: " SPECIES
            SPECIES="${SPECIES:-0}"
            read -p "Enter domain ID [1]: " DOMAIN
            DOMAIN="${DOMAIN:-1}"
            if [ -n "$OUTPUT_FILE" ] && [ -n "$PAGE_INPUT" ]; then
                echo ""
                # shellcheck disable=SC2086
                python3 rpt_file_builder.py --species "$SPECIES" --domain "$DOMAIN" \
                    --section-csv "$CSV_PATH" \
                    -o "$OUTPUT_FILE" $PAGE_INPUT
            fi
        else
            # Manual entry mode
            read -p "Enter species ID [0]: " SPECIES
            SPECIES="${SPECIES:-0}"
            read -p "Enter domain ID [1]: " DOMAIN
            DOMAIN="${DOMAIN:-1}"
            echo ""
            echo "Enter section specs, one per line (format: SECTION_ID:START_PAGE:PAGE_COUNT)"
            echo "Enter empty line when done."
            SECTION_ARGS=""
            while true; do
                read -p "  Section spec (or Enter to finish): " SEC_SPEC
                if [ -z "$SEC_SPEC" ]; then
                    break
                fi
                SECTION_ARGS="$SECTION_ARGS --section $SEC_SPEC"
            done
            if [ -n "$OUTPUT_FILE" ] && [ -n "$PAGE_INPUT" ]; then
                echo ""
                # shellcheck disable=SC2086
                python3 rpt_file_builder.py --species "$SPECIES" --domain "$DOMAIN" \
                    $SECTION_ARGS \
                    -o "$OUTPUT_FILE" $PAGE_INPUT
            fi
        fi
        ;;
    6)
        echo ""
        echo "--- Dry run: show build plan without writing ---"
        echo ""
        read -p "Enter directory or text files (page sources): " PAGE_INPUT
        read -p "Enter output RPT file path (for plan display): " OUTPUT_FILE
        read -p "Enter species ID [0]: " SPECIES
        SPECIES="${SPECIES:-0}"
        if [ -n "$OUTPUT_FILE" ] && [ -n "$PAGE_INPUT" ]; then
            echo ""
            # shellcheck disable=SC2086
            python3 rpt_file_builder.py --info --species "$SPECIES" \
                -o "$OUTPUT_FILE" $PAGE_INPUT
        fi
        ;;
    7)
        echo ""
        python3 rpt_file_builder.py --help
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
