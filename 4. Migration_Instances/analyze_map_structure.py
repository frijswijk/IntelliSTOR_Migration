#!/usr/bin/env python3
"""
Analyze Binary MAP File Structure
Deep analysis of binary MAP file to understand segment storage format

Usage:
    python analyze_map_structure.py <map_file_path>
"""

import os
import sys
import struct


def analyze_map_file(map_file_path):
    """Detailed analysis of binary MAP file structure."""

    if not os.path.exists(map_file_path):
        print(f"Error: File not found: {map_file_path}")
        return

    try:
        with open(map_file_path, 'rb') as f:
            data = f.read()

        print(f"File: {map_file_path}")
        print(f"Size: {len(data)} bytes")
        print("=" * 80)

        # Parse header
        if len(data) < 90:
            print("File too small")
            return

        print("\n[HEADER SECTION]")
        print(f"Bytes 0-11:  MAPHDR = {data[:12].hex()}")
        print(f"Bytes 12-15: {struct.unpack('<I', data[12:16])[0]} (0x{data[12:16].hex()})")
        print(f"Bytes 16-17: {struct.unpack('<H', data[16:18])[0]} (0x{data[16:18].hex()})")
        segment_count = struct.unpack('<H', data[18:20])[0]
        print(f"Bytes 18-19: Segment Count = {segment_count}")
        print(f"Bytes 20-23: {struct.unpack('<I', data[20:24])[0]} (0x{data[20:24].hex()})")

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

        print(f"\n[**ME MARKERS]")
        print(f"Found {len(me_positions)} **ME markers at positions: {me_positions}")

        # Analyze sections between markers
        print(f"\n[SECTIONS BETWEEN **ME MARKERS]")
        for i in range(len(me_positions)):
            start = me_positions[i]
            end = me_positions[i+1] if i+1 < len(me_positions) else len(data)
            section_size = end - start

            print(f"\n--- Section {i+1}: Bytes {start}-{end} (size: {section_size}) ---")

            # Show marker and following bytes
            marker_end = start + len(me_marker)
            print(f"Marker at {start}: {data[start:marker_end].hex()}")

            # Show next 100 bytes after marker in hex
            sample_end = min(marker_end + 100, end)
            print(f"Next bytes (hex): {data[marker_end:sample_end].hex()}")

            # Try to find patterns
            section_data = data[marker_end:end]

            # Look for potential segment IDs (small integers)
            if len(section_data) >= 4:
                # Try reading as various integer formats
                try:
                    val_32 = struct.unpack('<I', section_data[0:4])[0]
                    print(f"First 4 bytes as uint32: {val_32}")
                except:
                    pass

                try:
                    val_16 = struct.unpack('<H', section_data[0:2])[0]
                    print(f"First 2 bytes as uint16: {val_16}")
                except:
                    pass

            # Look for null-terminated or length-prefixed strings
            # Scan for repeated byte patterns
            print(f"Byte value distribution (first 50 bytes):")
            byte_counts = {}
            for b in section_data[:50]:
                byte_counts[b] = byte_counts.get(b, 0) + 1

            # Show most common bytes
            common = sorted(byte_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            print(f"  Most common: {[(hex(b), cnt) for b, cnt in common]}")

            # Try to decode as UTF-16LE text
            try:
                text = section_data[:200].decode('utf-16le', errors='ignore')
                printable = ''.join(c if c.isprintable() and c not in '\x00' else '·' for c in text)
                if printable.strip('·'):
                    print(f"As UTF-16LE: {printable[:80]}")
            except:
                pass

        print("\n" + "=" * 80)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    map_file = sys.argv[1]
    analyze_map_file(map_file)


if __name__ == '__main__':
    main()
