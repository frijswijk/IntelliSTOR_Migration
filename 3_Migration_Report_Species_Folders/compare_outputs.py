#!/usr/bin/env python3
"""
CSV Output Comparison Tool
Compares Python and C++ folder species extractor outputs for parity verification
"""

import sys
import os
import csv
from pathlib import Path
from typing import List, Tuple


def compare_binary(file1: Path, file2: Path) -> bool:
    """Quick binary comparison - fastest check for perfect match"""
    try:
        with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
            return f1.read() == f2.read()
    except Exception as e:
        print(f"Error reading files: {e}")
        return False


def count_line_endings(file_path: Path) -> Tuple[int, int]:
    """Count CRLF and LF line endings"""
    with open(file_path, 'rb') as f:
        content = f.read()

    crlf_count = content.count(b'\r\n')
    lf_count = content.count(b'\n') - crlf_count  # Subtract CRLF instances

    return crlf_count, lf_count


def compare_csv_content(file1: Path, file2: Path, max_diffs: int = 5) -> Tuple[bool, List[str]]:
    """Compare CSV files row by row, report differences"""
    differences = []

    try:
        with open(file1, 'r', encoding='utf-8', newline='') as f1, \
             open(file2, 'r', encoding='utf-8', newline='') as f2:

            reader1 = csv.reader(f1)
            reader2 = csv.reader(f2)

            row_num = 0
            for row1, row2 in zip(reader1, reader2):
                row_num += 1
                if row1 != row2:
                    if len(differences) < max_diffs:
                        differences.append(f"Line {row_num}: MISMATCH")
                        differences.append(f"  File1: {row1}")
                        differences.append(f"  File2: {row2}")
                        differences.append("")
                    else:
                        differences.append(f"... and more differences (showing first {max_diffs})")
                        break

            # Check for different number of rows
            remaining1 = list(reader1)
            remaining2 = list(reader2)

            if remaining1:
                differences.append(f"File1 has {len(remaining1)} extra rows")
            if remaining2:
                differences.append(f"File2 has {len(remaining2)} extra rows")

        return len(differences) == 0, differences

    except Exception as e:
        return False, [f"Error comparing files: {e}"]


def compare_file_pair(file1: Path, file2: Path, filename: str) -> bool:
    """Compare a single pair of files"""
    print(f"\n{'='*70}")
    print(f"Comparing: {filename}")
    print(f"{'='*70}")

    # Check existence
    if not file1.exists():
        print(f"❌ File not found: {file1}")
        return False
    if not file2.exists():
        print(f"❌ File not found: {file2}")
        return False

    # File sizes
    size1 = file1.stat().st_size
    size2 = file2.stat().st_size
    print(f"File sizes: {size1:,} bytes vs {size2:,} bytes")

    if size1 != size2:
        print(f"⚠️  Size difference: {abs(size1 - size2):,} bytes")

    # Binary comparison
    print("Checking binary match...", end=" ")
    if compare_binary(file1, file2):
        print("✅ PERFECT MATCH (byte-for-byte identical)")
        return True

    print("❌ Binary mismatch - analyzing differences...")

    # Line endings analysis
    crlf1, lf1 = count_line_endings(file1)
    crlf2, lf2 = count_line_endings(file2)

    print(f"\nLine endings:")
    print(f"  File1: {crlf1} CRLF, {lf1} LF")
    print(f"  File2: {crlf2} CRLF, {lf2} LF")

    if (crlf1, lf1) != (crlf2, lf2):
        print("  ⚠️  Line ending difference detected")

    # Content comparison
    print("\nComparing CSV content...")
    is_identical, differences = compare_csv_content(file1, file2)

    if is_identical:
        print("✅ CSV CONTENT IDENTICAL (only line endings differ)")
        return True
    else:
        print(f"❌ CSV CONTENT DIFFERS:")
        for diff in differences:
            print(f"  {diff}")
        return False


def main():
    if len(sys.argv) != 3:
        print("Usage: python compare_outputs.py <python_output_dir> <cpp_output_dir>")
        print("\nExample:")
        print("  python compare_outputs.py python_output cpp_output")
        sys.exit(1)

    python_dir = Path(sys.argv[1])
    cpp_dir = Path(sys.argv[2])

    if not python_dir.exists():
        print(f"❌ Python output directory not found: {python_dir}")
        sys.exit(1)

    if not cpp_dir.exists():
        print(f"❌ C++ output directory not found: {cpp_dir}")
        sys.exit(1)

    print(f"\n{'='*70}")
    print("CSV OUTPUT COMPARISON TOOL")
    print(f"{'='*70}")
    print(f"Python output: {python_dir}")
    print(f"C++ output:    {cpp_dir}")

    # Files to compare
    csv_files = [
        "Folder_Hierarchy.csv",
        "Folder_Report.csv",
        "Report_Species.csv"
    ]

    results = {}

    for filename in csv_files:
        file1 = python_dir / filename
        file2 = cpp_dir / filename
        results[filename] = compare_file_pair(file1, file2, filename)

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")

    all_passed = True
    for filename, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {filename}")
        if not passed:
            all_passed = False

    print(f"{'='*70}")

    if all_passed:
        print("✅ ALL FILES MATCH - Python and C++ outputs are identical!")
        print("Downstream tools can use either version interchangeably.")
        return 0
    else:
        print("❌ DIFFERENCES DETECTED - Review and fix discrepancies above")
        return 1


if __name__ == "__main__":
    sys.exit(main())
