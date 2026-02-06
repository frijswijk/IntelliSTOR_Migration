#!/bin/bash
# Environment Variable Test
# macOS equivalent of test_env.bat

# Change to script directory (important when launched from Finder)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# Source environment variables
source "${SCRIPT_DIR}/../Migration_Environment.sh"

# Activate virtual environment
source "${SCRIPT_DIR}/../venv/bin/activate"

clear
echo ""
echo "======================================================================"
echo "Environment Variable Test"
echo "======================================================================"
echo "AFP_VersionCompare = ${AFP_VersionCompare}"
echo ""
echo "Command that would be executed (SG):"

CMD="python3 Analyze_AFP_Resources.py --folder \"${AFP_Source_SG}\" --output-csv \"${AFP_Output}/AFP_Resources_SG.csv\" --namespace SG --quiet"

if [ "${AFP_VersionCompare,,}" == "yes" ]; then
    CMD="${CMD} --version-compare"
fi

echo "${CMD}"
echo ""
echo "======================================================================"
read -p "Press Enter to continue..."
