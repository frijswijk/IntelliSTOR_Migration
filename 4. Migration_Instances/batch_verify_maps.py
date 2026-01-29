#!/usr/bin/env python3
"""
Batch Verify MAP Files
Scans a directory and displays segment counts for all MAP files

Usage:
    python batch_verify_maps.py <map_directory>

Examples:
    python batch_verify_maps.py .
    python batch_verify_maps.py "C:\Users\freddievr\Downloads\RPTnMAP_Files"
"""

import os
import re
import sys


def count_segments(map_file_path):
    """Count segments in a MAP file.

    Args:
        map_file_path: Path to .MAP file

    Returns:
        tuple: (segment_count, error_message) - error_message is None on success
    """
    try:
        with open(map_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Regex pattern for segment definitions
        matches = re.findall(r'\(\s+(\d+)-(.+?)\s{2,}', content)

        return len(matches), None

    except Exception as e:
        return 0, str(e)


def verify_all_maps(map_dir):
    """Verify all MAP files in directory.

    Args:
        map_dir: Directory containing .MAP files
    """
    if not os.path.exists(map_dir):
        print(f"Error: Directory not found: {map_dir}")
        return

    if not os.path.isdir(map_dir):
        print(f"Error: Not a directory: {map_dir}")
        return

    print(f"Scanning directory: {map_dir}")
    print("=" * 80)

    # Find all .MAP files
    all_files = os.listdir(map_dir)
    map_files = [f for f in all_files if f.upper().endswith('.MAP')]

    if not map_files:
        print("\nNo .MAP files found in directory")
        print(f"Total files in directory: {len(all_files)}")
        return

    print(f"\nFound {len(map_files)} MAP file(s)\n")
    print(f"{'Filename':<35} {'Segments':>10} {'Status':<20}")
    print("-" * 80)

    total_segments = 0
    success_count = 0
    error_count = 0

    for map_file in sorted(map_files):
        path = os.path.join(map_dir, map_file)
        segment_count, error = count_segments(path)

        if error:
            print(f"{map_file:<35} {'-':>10} ERROR: {error}")
            error_count += 1
        else:
            status = "OK" if segment_count > 0 else "EMPTY"
            print(f"{map_file:<35} {segment_count:>10} {status:<20}")
            total_segments += segment_count
            success_count += 1

    print("-" * 80)
    print(f"\nSummary:")
    print(f"  Total MAP files: {len(map_files)}")
    print(f"  Successfully parsed: {success_count}")
    print(f"  Errors: {error_count}")
    print(f"  Total segments: {total_segments}")

    if success_count > 0:
        print(f"  Average segments per file: {total_segments // success_count}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    map_directory = sys.argv[1]
    verify_all_maps(map_directory)


if __name__ == '__main__':
    main()
