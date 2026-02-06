#!/usr/bin/env python3
"""
Parse Binary MAP Files
Attempts to extract segment information from binary .MAP files

Usage:
    python parse_binary_map.py <map_file_path>
"""

import os
import sys
import struct


def parse_binary_map(map_file_path):
    """Parse binary MAP file and try to extract segment info.

    Args:
        map_file_path: Path to binary .MAP file

    Returns:
        dict: Extracted information
    """
    if not os.path.exists(map_file_path):
        print(f"Error: File not found: {map_file_path}")
        return None

    try:
        with open(map_file_path, 'rb') as f:
            data = f.read()

        info = {}

        # Check for MAPHDR header (UTF-16LE)
        if data[:12] == b'M\x00A\x00P\x00H\x00D\x00R\x00':
            info['format'] = 'Binary MAP with MAPHDR header (UTF-16LE)'

            # Try to extract some basic info
            # Bytes 12-16 might be counts or offsets
            if len(data) >= 20:
                # Try reading as little-endian integers
                try:
                    val1 = struct.unpack('<I', data[12:16])[0]
                    val2 = struct.unpack('<I', data[16:20])[0]
                    info['header_value_1'] = val1
                    info['header_value_2'] = val2
                except:
                    pass

            # Look for text patterns that might be segment names
            # Try UTF-16LE decoding in chunks
            segments_found = []
            i = 0
            while i < len(data) - 1:
                # Look for patterns that might be segment IDs
                # In the diagnostic output, we see patterns like numbers followed by data
                try:
                    # Try to find printable ASCII/text in UTF-16LE
                    chunk = data[i:i+100]
                    text = chunk.decode('utf-16le', errors='ignore')
                    # Look for segment-like patterns
                    if text and len(text.strip()) > 2 and text.isprintable():
                        clean_text = ''.join(c for c in text if c.isprintable() and c not in '\x00\r\n')
                        if clean_text and len(clean_text) > 3:
                            segments_found.append((i, clean_text[:50]))
                except:
                    pass
                i += 2  # Move by 2 bytes for UTF-16LE

            info['potential_text_sections'] = segments_found[:20]  # First 20 findings

        else:
            info['format'] = 'Unknown binary format'

        info['file_size'] = len(data)

        # Try to find the **ME marker (often appears in the data)
        me_marker = b'*\x00*\x00M\x00E\x00'
        me_positions = []
        pos = 0
        while True:
            pos = data.find(me_marker, pos)
            if pos == -1:
                break
            me_positions.append(pos)
            pos += len(me_marker)

        info['me_marker_count'] = len(me_positions)
        info['me_marker_positions'] = me_positions

        return info

    except Exception as e:
        print(f"Error: {e}")
        return None


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    map_file = sys.argv[1]

    print(f"Parsing binary MAP file: {map_file}")
    print("=" * 80)

    info = parse_binary_map(map_file)

    if info:
        print("\nFile Information:")
        print("-" * 80)
        for key, value in info.items():
            if isinstance(value, list) and len(value) > 5:
                print(f"  {key}: {len(value)} items")
                print(f"    First 5: {value[:5]}")
            else:
                print(f"  {key}: {value}")
        print("-" * 80)
    else:
        print("\nFailed to parse file")
        sys.exit(1)


if __name__ == '__main__':
    main()
