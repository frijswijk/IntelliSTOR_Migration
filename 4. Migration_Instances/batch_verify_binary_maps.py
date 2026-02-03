#!/usr/bin/env python3
"""
Batch Verify Binary MAP Files
Scans a directory and displays segment counts for all binary .MAP files

Usage:
    python batch_verify_binary_maps.py <map_directory>

Examples:
    python batch_verify_binary_maps.py .
    python batch_verify_binary_maps.py "H:/OCBC/250_MapFiles"
"""

import os
import sys
import struct


def read_segment_count(map_file_path):
    """Read segment count from binary MAP file.

    Binary MAP file structure:
        Offset 0-11:   MAPHDR header (UTF-16LE)
        Offset 12-15:  Unknown (zeros)
        Offset 16-17:  Unknown flags/type
        Offset 18-19:  Segment count (little-endian 16-bit unsigned int)
        Offset 20+:    File data and segment definitions

    Args:
        map_file_path: Path to binary .MAP file

    Returns:
        tuple: (segment_count, error_message) - error_message is None on success
    """
    try:
        with open(map_file_path, 'rb') as f:
            # Read first 20 bytes
            header = f.read(20)

        if len(header) < 20:
            return 0, "File too small"

        # Verify MAPHDR header (UTF-16LE)
        expected_header = b'M\x00A\x00P\x00H\x00D\x00R\x00'
        if header[:12] != expected_header:
            return 0, "Invalid MAPHDR header"

        # Read segment count from bytes 18-19 (little-endian 16-bit unsigned)
        segment_count = struct.unpack('<H', header[18:20])[0]

        return segment_count, None

    except Exception as e:
        return 0, str(e)


def verify_all_maps(map_dir):
    """Verify all binary MAP files in directory.

    Args:
        map_dir: Directory containing binary .MAP files
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
    empty_count = 0

    for map_file in sorted(map_files):
        path = os.path.join(map_dir, map_file)
        segment_count, error = read_segment_count(path)

        if error:
            print(f"{map_file:<35} {'-':>10} ERROR: {error}")
            error_count += 1
        else:
            if segment_count == 0:
                status = "EMPTY"
                empty_count += 1
            else:
                status = "OK"
            print(f"{map_file:<35} {segment_count:>10} {status:<20}")
            total_segments += segment_count
            success_count += 1

    print("-" * 80)
    print(f"\nSummary:")
    print(f"  Total MAP files: {len(map_files)}")
    print(f"  Successfully parsed: {success_count}")
    print(f"  Empty (0 segments): {empty_count}")
    print(f"  Errors: {error_count}")
    print(f"  Total segments: {total_segments:,}")

    if success_count > 0:
        avg_segments = total_segments / success_count
        print(f"  Average segments per file: {avg_segments:.1f}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    map_directory = sys.argv[1]
    verify_all_maps(map_directory)


if __name__ == '__main__':
    main()
