#!/bin/bash
# Extract Users Permissions - Singapore (Simple TESTDATA version)
# macOS equivalent of Extract_Users_permissions_SG_Testdata.bat

# Change to script directory (important when launched from Finder)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# Source environment variables
source "${SCRIPT_DIR}/../Migration_Environment.sh"

# Activate virtual environment
source "${SCRIPT_DIR}/../venv/bin/activate"

clear
python3 Extract_Users_Permissions.py --server "${SQLServer}" --database "${SQL_SG_Database}" --user "${SQLUser}" --password "${SQLPassword}" --output TestoutputSG --TESTDATA
echo ""
read -p "Press Enter to continue..."
