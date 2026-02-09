#!/bin/bash
# Build script for extract_unique_rids C++ program

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROGRAM_NAME="extract_unique_rids"
EXECUTABLE="${SCRIPT_DIR}/${PROGRAM_NAME}"

echo "Building ${PROGRAM_NAME}..."
echo "Source file: ${SCRIPT_DIR}/${PROGRAM_NAME}.cpp"
echo "Executable: ${EXECUTABLE}"
echo ""

# Compile with C++17 standard
g++ -std=c++17 -O2 "${SCRIPT_DIR}/${PROGRAM_NAME}.cpp" -o "${EXECUTABLE}"

if [ -f "${EXECUTABLE}" ]; then
    chmod +x "${EXECUTABLE}"
    echo "✓ Build successful!"
    echo ""
    echo "Usage:"
    echo "  ${EXECUTABLE} <folder_path>"
    echo "  ${EXECUTABLE} <folder_path> <output_file>"
    echo ""
    echo "Example:"
    echo "  ${EXECUTABLE} /path/to/Users_SG"
    echo "  ${EXECUTABLE} /path/to/Users_SG my_rids.csv"
else
    echo "✗ Build failed!"
    exit 1
fi
