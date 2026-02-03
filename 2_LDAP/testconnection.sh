#!/bin/bash
# LDAP SSL Connection Test with Self-Signed Certificates
# macOS equivalent of testconnection.bat

# Change to script directory (important when launched from Finder)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

# Activate virtual environment
source "${SCRIPT_DIR}/../venv/bin/activate"

clear
echo "============================================================"
echo "LDAP SSL Connection Test with Self-Signed Certificates"
echo "============================================================"
echo ""

echo "Option 1: Skip verification (TESTING ONLY - INSECURE)"
echo "------------------------------------------------------------"
python3 ldap_integration.py test-connection \
  --server YLDAPTEST-DC01.ldap1test.loc \
  --port 636 \
  --use-ssl \
  --ssl-no-verify \
  --bind-dn "cn=administrator,cn=Users,dc=ldap1test,dc=loc" \
  --password "Linked3-Shorten-Crestless" \
  --base-dn "dc=ldap1test,dc=loc"

echo ""
echo ""
echo "Option 2: With custom CA certificate (SECURE)"
echo "------------------------------------------------------------"
echo "First export certificate with:"
echo "  openssl s_client -connect YLDAPTEST-DC01.ldap1test.loc:636 -showcerts < /dev/null 2>&1 | openssl x509 -outform PEM > ca-cert.pem"
echo ""
echo "Then test connection (uncomment below):"
# python3 ldap_integration.py test-connection \
#   --server YLDAPTEST-DC01.ldap1test.loc \
#   --port 636 \
#   --use-ssl \
#   --ssl-ca-cert ca-cert.pem \
#   --bind-dn "cn=administrator,cn=Users,dc=ldap1test,dc=loc" \
#   --password "Linked3-Shorten-Crestless" \
#   --base-dn "dc=ldap1test,dc=loc"

echo ""
read -p "Press Enter to continue..."
