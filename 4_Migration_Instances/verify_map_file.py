#!/usr/bin/env python3
"""
Verify MAP File Contents
Displays all segments from a .MAP file in readable format

Usage:
    python verify_map_file.py <map_file_path> [segment_id_to_find]

Examples:
    python verify_map_file.py 260271NL.MAP
    python verify_map_file.py 260271NL.MAP 850
    python verify_map_file.py "C:\path\to\260271NL.MAP" 850
"""

import re
import sys
import os


def parse_map_file(map_file_path):
    """Parse .MAP file and return segment dictionary.

    Args:
        map_file_path: Path to .MAP file

    Returns:
        dict: {segment_id: segment_name} or None on error
    """
    if not os.path.exists(map_file_path):
        print(f"Error: File not found: {map_file_path}")
        return None

    try:
        with open(map_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Regex pattern for segment definitions
        # Pattern: ( [spaces] ID - Name [padding spaces]
        matches = re.findall(r'\(\s+(\d+)-(.+?)\s{2,}', content)

        segments = {}
        for seg_id, name in matches:
            segments[seg_id] = name.strip()

        return segments

    except Exception as e:
        print(f"Error parsing file: {e}")
        return None


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    map_file = sys.argv[1]
    search_id = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"Parsing MAP file: {map_file}")
    print("-" * 80)

    segments = parse_map_file(map_file)

    if segments is None:
        sys.exit(1)

    if not segments:
        print("\nWarning: No segments found in MAP file")
        print("This may indicate:")
        print("  - File is not a valid MAP file")
        print("  - File format doesn't match expected pattern")
        print("  - File is empty or corrupted")
        sys.exit(1)

    print(f"\nFound {len(segments)} segments:\n")

    # Display all segments, sorted by numeric ID
    sorted_ids = sorted(segments.keys(), key=lambda x: int(x))

    for seg_id in sorted_ids:
        marker = " <<< MATCH" if search_id and (seg_id == search_id or seg_id == search_id.zfill(len(seg_id))) else ""
        print(f"  Segment {seg_id:>4}: {segments[seg_id]}{marker}")

    # Search for specific segment if requested
    if search_id:
        print(f"\n" + "=" * 80)
        print(f"Searching for segment ID: {search_id}")
        print("=" * 80)

        # Try both padded and unpadded versions
        found = False
        for test_id in [search_id, search_id.zfill(2), search_id.zfill(3), search_id.zfill(4)]:
            if test_id in segments:
                print(f"\n✓ SUCCESS: Found segment {search_id}")
                print(f"  Segment ID: {test_id}")
                print(f"  Segment Name: {segments[test_id]}")
                found = True
                break

        if not found:
            print(f"\n✗ FAILED: Segment {search_id} not found in MAP file")
            print("\nAvailable segment IDs:")
            print("  " + ", ".join(sorted_ids))

    print("\n" + "-" * 80)
    print(f"Summary: {len(segments)} total segments")

    # Additional statistics
    print(f"ID Range: {sorted_ids[0]} to {sorted_ids[-1]}")
    print(f"Average name length: {sum(len(name) for name in segments.values()) // len(segments)} characters")


if __name__ == '__main__':
    main()
