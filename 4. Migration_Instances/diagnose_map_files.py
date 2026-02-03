#!/usr/bin/env python3
"""
Diagnose MAP File Format
Shows raw content from first few MAP files to understand format

Usage:
    python diagnose_map_files.py <map_directory>
"""

import os
import sys


def diagnose_map_files(map_dir, max_files=5):
    """Show content from first few MAP files."""
    if not os.path.exists(map_dir):
        print(f"Error: Directory not found: {map_dir}")
        return

    # Find all .MAP files
    all_files = os.listdir(map_dir)
    map_files = [f for f in all_files if f.upper().endswith('.MAP')]

    if not map_files:
        print("\nNo .MAP files found in directory")
        return

    print(f"Found {len(map_files)} total MAP files")
    print(f"Showing first {min(max_files, len(map_files))} files:\n")
    print("=" * 80)

    for i, map_file in enumerate(sorted(map_files)[:max_files]):
        path = os.path.join(map_dir, map_file)
        print(f"\n[{i+1}] File: {map_file}")
        print(f"    Path: {path}")

        try:
            # Check file size
            size = os.path.getsize(path)
            print(f"    Size: {size} bytes")

            if size == 0:
                print("    Status: EMPTY FILE")
                continue

            # Try to read first 500 bytes
            with open(path, 'rb') as f:
                raw_bytes = f.read(500)

            # Show raw bytes (hex)
            print(f"    First 100 bytes (hex): {raw_bytes[:100].hex()}")

            # Try different encodings
            encodings_to_try = ['utf-8', 'latin-1', 'cp1252', 'ascii']

            for encoding in encodings_to_try:
                try:
                    with open(path, 'r', encoding=encoding, errors='ignore') as f:
                        content = f.read(500)

                    print(f"\n    Encoding: {encoding}")
                    print(f"    First 500 characters:")
                    print("    " + "-" * 76)
                    for line in content.split('\n')[:15]:
                        print(f"    {repr(line)}")

                    # Only show first successful encoding
                    break

                except Exception as e:
                    print(f"    Failed with {encoding}: {e}")

        except Exception as e:
            print(f"    ERROR: {e}")

        print("-" * 80)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    map_directory = sys.argv[1]
    diagnose_map_files(map_directory)


if __name__ == '__main__':
    main()
