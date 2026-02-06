#!/usr/bin/env python3
"""
Extract Segments from Binary MAP Files
Attempts to extract segment information from binary MAP files

Usage:
    python extract_map_segments.py <map_file_path>
"""

import os
import sys
import struct


def extract_segments(map_file_path):
    """Extract segment information from binary MAP file."""

    if not os.path.exists(map_file_path):
        print(f"Error: File not found: {map_file_path}")
        return None

    try:
        with open(map_file_path, 'rb') as f:
            data = f.read()

        # Read segment count
        if len(data) < 20:
            print("File too small")
            return None

        segment_count = struct.unpack('<H', data[18:20])[0]

        # Find **ME markers
        me_marker = b'*\x00*\x00M\x00E\x00'
        me_positions = []
        pos = 0
        while True:
            pos = data.find(me_marker, pos)
            if pos == -1:
                break
            me_positions.append(pos)
            pos += len(me_marker)

        if len(me_positions) != segment_count:
            print(f"Warning: Segment count ({segment_count}) doesn't match **ME markers ({len(me_positions)})")

        print(f"File: {os.path.basename(map_file_path)}")
        print(f"Segment Count: {segment_count}")
        print(f"**ME Markers: {len(me_positions)}")
        print("=" * 80)

        segments = []
        for i, me_pos in enumerate(me_positions):
            marker_end = me_pos + len(me_marker)

            # Read structured data after marker
            if marker_end + 20 <= len(data):
                seg_data = data[marker_end:marker_end+100]

                # Parse what we know:
                # Bytes 0-3: Header (usually 00008e00)
                # Bytes 4-7: Segment index
                # Bytes 8-11: Next section offset

                header_val = struct.unpack('<I', seg_data[0:4])[0]
                seg_index = struct.unpack('<I', seg_data[4:8])[0]
                next_offset = struct.unpack('<I', seg_data[8:12])[0]

                # Look for potential segment ID in nearby bytes
                # Try bytes 12-50 for small integers that might be IDs
                potential_ids = []
                for offset in range(12, min(50, len(seg_data)), 4):
                    try:
                        val = struct.unpack('<I', seg_data[offset:offset+4])[0]
                        if 0 < val < 10000:  # Reasonable segment ID range
                            potential_ids.append((offset, val))
                    except:
                        pass

                segment_info = {
                    'index': i,
                    'me_position': me_pos,
                    'segment_index': seg_index,
                    'next_offset': next_offset,
                    'header': hex(header_val),
                    'potential_ids': potential_ids[:5],  # First 5
                    'raw_bytes': seg_data[:50].hex()
                }

                segments.append(segment_info)

                print(f"\nSegment {i+1}:")
                print(f"  ME Position: {me_pos}")
                print(f"  Segment Index: {seg_index}")
                print(f"  Next Offset: {next_offset}")
                print(f"  Header: {hex(header_val)}")
                if potential_ids:
                    print(f"  Potential IDs: {potential_ids[:3]}")
                print(f"  Raw (first 50 bytes): {seg_data[:50].hex()}")

        return segments

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    map_file = sys.argv[1]
    extract_segments(map_file)


if __name__ == '__main__':
    main()
