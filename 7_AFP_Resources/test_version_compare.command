#!/bin/bash
# Test script to demonstrate version comparison feature
# macOS equivalent of test_version_compare.bat

# Change to script directory (important when launched from Finder)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# Activate virtual environment
source "${SCRIPT_DIR}/../venv/bin/activate"

clear
echo "======================================================================"
echo "AFP Resource Analyzer - Version Comparison Test"
echo "======================================================================"
echo ""

echo "Test 1: Baseline (without version comparison)"
echo "----------------------------------------------------------------------"
python3 Analyze_AFP_Resources.py --folder "$HOME/Downloads/afp/afp" --output-csv "test_baseline.csv"
echo ""

echo "Test 2: With Version Comparison"
echo "----------------------------------------------------------------------"
python3 Analyze_AFP_Resources.py --folder "$HOME/Downloads/afp/afp" --output-csv "test_compare.csv" --version-compare
echo ""

echo "======================================================================"
echo "Comparison Results"
echo "======================================================================"
echo ""
echo "Checking C04BAR10.RCS as example:"
echo ""
echo "Baseline:"
grep "C04BAR10.RCS" test_baseline.csv
echo ""
echo "With Version Compare:"
grep "C04BAR10.RCS" test_compare.csv
echo ""
echo "======================================================================"
echo "Test Complete"
echo "======================================================================"
read -p "Press Enter to continue..."
