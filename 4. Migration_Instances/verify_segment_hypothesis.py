#!/usr/bin/env python3
"""
verify_segment_hypothesis.py - Decode Binary MAP File Structure

Analyzes binary MAP files to understand the segment data structure and find
where SECTION_ID values are stored after **ME markers.

This script:
1. Reads binary MAP files
2. Finds **ME markers
3. Analyzes the byte structure after each marker
4. Attempts to identify SECTION_ID values
5. Cross-references with database section data if available

Usage:
    python verify_segment_hypothesis.py <map_file>
    python verify_segment_hypothesis.py --map-dir /path/to/mapfiles --exports-dir ./exports
"""

import argparse
import csv
import os
import struct
import sys
from collections import defaultdict


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Decode binary MAP file structure to find SECTION_ID locations',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('map_file', nargs='?', help='Single MAP file to analyze')
    parser.add_argument('--map-dir', help='Directory containing MAP files')
    parser.add_argument('--exports-dir', default='./exports',
                        help='Directory containing CSV exports from database')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Verbose output')

    return parser.parse_args()


def load_section_lookup(exports_dir):
    """Load section lookup data from CSV."""
    lookup_path = os.path.join(exports_dir, 'section_lookup.csv')
    if not os.path.exists(lookup_path):
        print(f"Warning: Section lookup file not found: {lookup_path}")
        return {}

    lookup = {}  # {(domain_id, species_id, section_id): name}
    with open(lookup_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (int(row['DOMAIN_ID']), int(row['REPORT_SPECIES_ID']), int(row['SECTION_ID']))
            lookup[key] = row['NAME']

    print(f"Loaded {len(lookup):,} section lookup entries")
    return lookup


def load_map_to_domain(exports_dir):
    """Load MAP filename to DOMAIN_ID/REPORT_SPECIES_ID mapping."""
    mapping_path = os.path.join(exports_dir, 'map_to_domain.csv')
    if not os.path.exists(mapping_path):
        print(f"Warning: Map to domain file not found: {mapping_path}")
        return {}

    mapping = {}  # {filename: (domain_id, species_id)}
    with open(mapping_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            mapping[row['FILENAME']] = (int(row['DOMAIN_ID']), int(row['REPORT_SPECIES_ID']))

    print(f"Loaded {len(mapping):,} MAP filename mappings")
    return mapping


def read_binary_map(map_file_path):
    """Read binary MAP file."""
    with open(map_file_path, 'rb') as f:
        return f.read()


def find_me_markers(data):
    """Find all **ME markers in binary data."""
    me_marker = b'*\x00*\x00M\x00E\x00'  # **ME in UTF-16LE
    positions = []
    pos = 0
    while True:
        pos = data.find(me_marker, pos)
        if pos == -1:
            break
        positions.append(pos)
        pos += len(me_marker)
    return positions


def analyze_segment_structure(data, me_pos, verbose=False):
    """Analyze the structure of a segment after **ME marker.

    Based on previous analysis, the structure after **ME marker is:
    - Bytes 0-7: **ME marker (already found)
    - Bytes 8-11: Header value (often 0x00008e00)
    - Bytes 12-15: Segment index (0, 1, 2...)
    - Bytes 16-19: Next section offset
    - Remaining: Segment metadata

    Returns dict with extracted values.
    """
    marker_len = 8  # **ME in UTF-16LE
    start = me_pos + marker_len

    if start + 100 > len(data):
        return None

    segment_data = data[start:start + 200]

    result = {
        'marker_pos': me_pos,
        'data_start': start,
        'raw_bytes': segment_data[:100].hex(),
    }

    # Try to parse known structure
    try:
        # First 4 bytes after marker - header/type
        result['header_uint32'] = struct.unpack('<I', segment_data[0:4])[0]

        # Next 4 bytes - often segment index
        result['field_1_uint32'] = struct.unpack('<I', segment_data[4:8])[0]

        # Next 4 bytes - offset to next section
        result['field_2_uint32'] = struct.unpack('<I', segment_data[8:12])[0]

        # Scan for potential SECTION_ID values (small-medium integers)
        potential_ids = []
        for offset in range(0, min(100, len(segment_data)), 2):
            try:
                val_16 = struct.unpack('<H', segment_data[offset:offset+2])[0]
                val_32 = struct.unpack('<I', segment_data[offset:offset+4])[0] if offset + 4 <= len(segment_data) else None

                # Look for values that could be SECTION_IDs (typically 0-100000 range)
                if 1 <= val_16 <= 100000:
                    potential_ids.append(('uint16', offset, val_16))
                if val_32 is not None and 1 <= val_32 <= 100000:
                    potential_ids.append(('uint32', offset, val_32))
            except:
                pass

        result['potential_section_ids'] = potential_ids[:20]

        # Look for specific byte patterns
        # Check bytes 12-13 and 12-15 specifically (common location for IDs)
        if len(segment_data) >= 16:
            result['bytes_12_13_uint16'] = struct.unpack('<H', segment_data[12:14])[0]
            result['bytes_12_15_uint32'] = struct.unpack('<I', segment_data[12:16])[0]
            result['bytes_14_15_uint16'] = struct.unpack('<H', segment_data[14:16])[0]
            result['bytes_16_17_uint16'] = struct.unpack('<H', segment_data[16:18])[0]
            result['bytes_16_19_uint32'] = struct.unpack('<I', segment_data[16:20])[0]

    except Exception as e:
        result['parse_error'] = str(e)

    return result


def analyze_map_file(map_file_path, section_lookup=None, map_to_domain=None, verbose=False):
    """Analyze a single MAP file."""
    filename = os.path.basename(map_file_path)
    print(f"\n{'='*60}")
    print(f"Analyzing: {filename}")
    print('='*60)

    # Check if we have database info for this file
    domain_id = None
    species_id = None
    if map_to_domain and filename in map_to_domain:
        domain_id, species_id = map_to_domain[filename]
        print(f"Database: DOMAIN_ID={domain_id}, REPORT_SPECIES_ID={species_id}")

        # Check how many sections exist for this species
        if section_lookup:
            sections = [(k, v) for k, v in section_lookup.items()
                        if k[0] == domain_id and k[1] == species_id]
            print(f"Sections in DB: {len(sections)}")
            if sections and verbose:
                print("  Sample sections:")
                for (d, s, sec_id), name in sorted(sections)[:5]:
                    print(f"    SECTION_ID {sec_id}: {name}")

    # Read binary file
    try:
        data = read_binary_map(map_file_path)
    except Exception as e:
        print(f"Error reading file: {e}")
        return None

    print(f"File size: {len(data):,} bytes")

    # Check header
    if len(data) < 20:
        print("File too small")
        return None

    if data[:12] != b'M\x00A\x00P\x00H\x00D\x00R\x00':
        print("Invalid MAPHDR header")
        return None

    # Get segment count from header
    segment_count = struct.unpack('<H', data[18:20])[0]
    print(f"Segment count (from header): {segment_count}")

    # Find **ME markers
    me_positions = find_me_markers(data)
    print(f"**ME markers found: {len(me_positions)}")

    if len(me_positions) != segment_count:
        print(f"  WARNING: Marker count ({len(me_positions)}) != segment count ({segment_count})")

    # Analyze each segment
    segments = []
    for i, me_pos in enumerate(me_positions):
        segment_info = analyze_segment_structure(data, me_pos, verbose)
        if segment_info:
            segment_info['segment_index'] = i
            segments.append(segment_info)

    # Print segment analysis
    print(f"\nSegment Analysis:")
    print("-" * 60)

    for seg in segments:
        print(f"\nSegment {seg['segment_index']}:")
        print(f"  Marker position: {seg['marker_pos']}")
        print(f"  Header uint32: {seg.get('header_uint32', 'N/A')} (0x{seg.get('header_uint32', 0):08x})")
        print(f"  Field 1 uint32: {seg.get('field_1_uint32', 'N/A')}")
        print(f"  Field 2 uint32: {seg.get('field_2_uint32', 'N/A')}")

        if 'bytes_12_15_uint32' in seg:
            print(f"  Bytes 12-15 uint32: {seg['bytes_12_15_uint32']}")
            print(f"  Bytes 12-13 uint16: {seg['bytes_12_13_uint16']}")
            print(f"  Bytes 16-19 uint32: {seg['bytes_16_19_uint32']}")

        # Check if any potential IDs match known sections
        if section_lookup and domain_id is not None:
            for type_name, offset, value in seg.get('potential_section_ids', []):
                key = (domain_id, species_id, value)
                if key in section_lookup:
                    print(f"  MATCH! {type_name} at offset {offset}: SECTION_ID={value} -> '{section_lookup[key]}'")

        if verbose:
            print(f"  Raw bytes (first 60): {seg['raw_bytes'][:120]}")

    # Summary of unique values at key offsets
    print(f"\n{'='*60}")
    print("VALUE DISTRIBUTION ANALYSIS")
    print("="*60)

    if segments:
        # Collect values at specific offsets
        offset_values = defaultdict(list)
        for seg in segments:
            if 'bytes_12_13_uint16' in seg:
                offset_values['bytes_12_13_uint16'].append(seg['bytes_12_13_uint16'])
            if 'bytes_12_15_uint32' in seg:
                offset_values['bytes_12_15_uint32'].append(seg['bytes_12_15_uint32'])
            if 'field_1_uint32' in seg:
                offset_values['field_1_uint32'].append(seg['field_1_uint32'])

        for offset_name, values in offset_values.items():
            unique = sorted(set(values))
            print(f"\n{offset_name}:")
            print(f"  Count: {len(values)}, Unique: {len(unique)}")
            if len(unique) <= 10:
                print(f"  Values: {unique}")
            else:
                print(f"  Sample: {unique[:5]} ... {unique[-5:]}")
                print(f"  Range: {min(unique)} - {max(unique)}")

    return segments


def main():
    args = parse_arguments()

    # Load database exports if available
    section_lookup = None
    map_to_domain = None

    if os.path.exists(args.exports_dir):
        section_lookup = load_section_lookup(args.exports_dir)
        map_to_domain = load_map_to_domain(args.exports_dir)
    else:
        print(f"Exports directory not found: {args.exports_dir}")
        print("Proceeding without database cross-reference")

    # Analyze single file or directory
    if args.map_file:
        analyze_map_file(args.map_file, section_lookup, map_to_domain, args.verbose)

    elif args.map_dir:
        # Analyze first few files from directory
        map_files = [f for f in os.listdir(args.map_dir) if f.upper().endswith('.MAP')][:5]
        print(f"\nAnalyzing first {len(map_files)} files from {args.map_dir}")

        for map_file in map_files:
            analyze_map_file(
                os.path.join(args.map_dir, map_file),
                section_lookup, map_to_domain, args.verbose
            )

    else:
        print("Error: Provide either a MAP file path or --map-dir")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("ANALYSIS COMPLETE")
    print("="*60)
    print("""
Key findings to look for:
1. Which byte offset consistently holds SECTION_ID values?
2. Do the values match SECTION_IDs in the database?
3. Is field_1_uint32 (bytes 4-7 after **ME) the segment index?
4. What does the header value (bytes 0-3 after **ME) represent?
""")


if __name__ == '__main__':
    main()
