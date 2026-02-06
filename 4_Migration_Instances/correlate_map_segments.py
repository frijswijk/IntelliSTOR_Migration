#!/usr/bin/env python3
"""
correlate_map_segments.py - Correlate MAP Files with REPORT_INSTANCE_SEGMENT

This script finds the correlation between:
1. Binary .MAP files (segment count, **ME marker positions, binary data)
2. REPORT_INSTANCE_SEGMENT table entries (SEGMENT_NUMBER, START_PAGE_NUMBER, NUMBER_OF_PAGES)

Focus: January 2025 data (MAP files starting with "25001")

Usage:
    python correlate_map_segments.py
    python correlate_map_segments.py --map-dir /Volumes/X9Pro/OCBC/250_MapFiles
"""

import argparse
import os
import struct
import sys

try:
    import pymssql
except ImportError:
    print("Error: pymssql not installed. Run: pip install pymssql")
    sys.exit(1)


def get_env_or_default(env_var, default):
    """Get environment variable or return default."""
    return os.environ.get(env_var, default)


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Correlate MAP files with REPORT_INSTANCE_SEGMENT entries',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--server', default=get_env_or_default('SQLServer', 'localhost'),
                        help='SQL Server hostname (default: localhost)')
    parser.add_argument('--port', type=int, default=1433,
                        help='SQL Server port (default: 1433)')
    parser.add_argument('--database', default=get_env_or_default('SQL_SG_Database', 'iSTSGUAT'),
                        help='Database name (default: iSTSGUAT)')
    parser.add_argument('--user', default=get_env_or_default('SQLUser', 'sa'),
                        help='SQL Server username (default: sa)')
    parser.add_argument('--password', default=get_env_or_default('SQLPassword', ''),
                        help='SQL Server password')
    parser.add_argument('--map-dir', default='/Volumes/X9Pro/OCBC/250_MapFiles',
                        help='Directory containing MAP files')
    parser.add_argument('--limit', type=int, default=10,
                        help='Limit number of files to analyze (default: 10)')

    return parser.parse_args()


def connect_to_database(server, port, database, user, password):
    """Connect to SQL Server database."""
    print(f"Connecting to {server}:{port}, database: {database}")

    try:
        conn = pymssql.connect(
            server=server,
            port=port,
            database=database,
            user=user,
            password=password
        )
        print("Connection successful!")
        return conn
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)


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


def parse_segment_data(data, me_pos):
    """Parse segment data after **ME marker.

    Returns dict with extracted values including potential page number info.
    """
    marker_len = 8  # **ME in UTF-16LE
    start = me_pos + marker_len

    if start + 50 > len(data):
        return None

    segment_data = data[start:start + 100]

    result = {
        'marker_pos': me_pos,
        'data_start': start,
    }

    try:
        # Parse various byte positions
        result['bytes_0_3'] = struct.unpack('<I', segment_data[0:4])[0]
        result['bytes_4_7'] = struct.unpack('<I', segment_data[4:8])[0]
        result['bytes_8_11'] = struct.unpack('<I', segment_data[8:12])[0]
        result['bytes_12_15'] = struct.unpack('<I', segment_data[12:16])[0]
        result['bytes_16_19'] = struct.unpack('<I', segment_data[16:20])[0]
        result['bytes_20_23'] = struct.unpack('<I', segment_data[20:24])[0]
        result['bytes_24_27'] = struct.unpack('<I', segment_data[24:28])[0]
        result['bytes_28_31'] = struct.unpack('<I', segment_data[28:32])[0]

        # Also try 16-bit values
        result['bytes_0_1'] = struct.unpack('<H', segment_data[0:2])[0]
        result['bytes_2_3'] = struct.unpack('<H', segment_data[2:4])[0]
        result['bytes_4_5'] = struct.unpack('<H', segment_data[4:6])[0]
        result['bytes_6_7'] = struct.unpack('<H', segment_data[6:8])[0]
        result['bytes_16_17'] = struct.unpack('<H', segment_data[16:18])[0]
        result['bytes_18_19'] = struct.unpack('<H', segment_data[18:20])[0]

        result['raw_hex'] = segment_data[:50].hex()

    except Exception as e:
        result['parse_error'] = str(e)

    return result


def read_map_file(map_path):
    """Read and parse a binary MAP file."""
    with open(map_path, 'rb') as f:
        data = f.read()

    result = {
        'file_size': len(data),
        'valid_header': False,
        'segment_count': 0,
        'me_marker_count': 0,
        'segments': []
    }

    # Check header
    if len(data) < 20:
        return result

    if data[:12] != b'M\x00A\x00P\x00H\x00D\x00R\x00':
        return result

    result['valid_header'] = True
    result['segment_count'] = struct.unpack('<H', data[18:20])[0]

    # Find **ME markers
    me_positions = find_me_markers(data)
    result['me_marker_count'] = len(me_positions)
    result['me_positions'] = me_positions

    # Parse each segment
    for i, me_pos in enumerate(me_positions):
        seg_data = parse_segment_data(data, me_pos)
        if seg_data:
            seg_data['segment_index'] = i
            result['segments'].append(seg_data)

    return result


def query_map_file_segments(cursor, filename):
    """Query database for segment information for a specific MAP file."""
    query = """
        SELECT
            m.FILENAME,
            m.MAP_FILE_ID,
            s.DOMAIN_ID,
            s.REPORT_SPECIES_ID,
            s.AS_OF_TIMESTAMP,
            ris.SEGMENT_NUMBER,
            ris.START_PAGE_NUMBER,
            ris.NUMBER_OF_PAGES,
            ris.PAGE_STREAM_INSTANCE_NUMBER
        FROM MAPFILE m
        INNER JOIN SST_STORAGE s ON m.MAP_FILE_ID = s.MAP_FILE_ID
        INNER JOIN REPORT_INSTANCE_SEGMENT ris
            ON s.DOMAIN_ID = ris.DOMAIN_ID
            AND s.REPORT_SPECIES_ID = ris.REPORT_SPECIES_ID
            AND s.AS_OF_TIMESTAMP = ris.AS_OF_TIMESTAMP
        WHERE m.FILENAME = %s
        ORDER BY ris.SEGMENT_NUMBER
    """
    cursor.execute(query, (filename,))
    return cursor.fetchall()


def query_january_2025_map_files(cursor, limit=10):
    """Query MAP files from January 2025 (filename starts with 25001)."""
    query = """
        SELECT DISTINCT TOP %s
            m.FILENAME,
            m.MAP_FILE_ID,
            s.DOMAIN_ID,
            s.REPORT_SPECIES_ID,
            (SELECT COUNT(*) FROM REPORT_INSTANCE_SEGMENT ris
             WHERE ris.DOMAIN_ID = s.DOMAIN_ID
               AND ris.REPORT_SPECIES_ID = s.REPORT_SPECIES_ID
               AND ris.AS_OF_TIMESTAMP = s.AS_OF_TIMESTAMP) as segment_count
        FROM MAPFILE m
        INNER JOIN SST_STORAGE s ON m.MAP_FILE_ID = s.MAP_FILE_ID
        WHERE m.FILENAME LIKE '25001%%'
        ORDER BY m.FILENAME
    """
    cursor.execute(query, (limit,))
    return cursor.fetchall()


def correlate_single_file(cursor, filename, map_dir):
    """Correlate a single MAP file with its database segment entries."""
    print(f"\n{'='*70}")
    print(f"Analyzing: {filename}")
    print('='*70)

    # Query database for segment info
    db_segments = query_map_file_segments(cursor, filename)

    if not db_segments:
        print("  No segment entries found in database")
        return None

    print(f"\nDatabase entries ({len(db_segments)} segments):")
    print(f"  {'SEG#':<5} {'START_PAGE':<12} {'NUM_PAGES':<10} {'PAGE_STREAM_INST'}")
    print(f"  {'-'*5} {'-'*12} {'-'*10} {'-'*16}")

    for row in db_segments:
        # row: FILENAME, MAP_FILE_ID, DOMAIN_ID, REPORT_SPECIES_ID, AS_OF_TIMESTAMP,
        #      SEGMENT_NUMBER, START_PAGE_NUMBER, NUMBER_OF_PAGES, PAGE_STREAM_INSTANCE_NUMBER
        seg_num = row[5]
        start_page = row[6]
        num_pages = row[7]
        page_stream = row[8]
        print(f"  {seg_num:<5} {start_page:<12} {num_pages:<10} {page_stream}")

    # Read binary MAP file
    map_path = os.path.join(map_dir, filename)
    if not os.path.exists(map_path):
        print(f"\n  Binary file not found: {map_path}")
        return None

    map_data = read_map_file(map_path)

    print(f"\nBinary file analysis:")
    print(f"  File size: {map_data['file_size']} bytes")
    print(f"  Valid header: {map_data['valid_header']}")
    print(f"  Segment count (header): {map_data['segment_count']}")
    print(f"  **ME markers found: {map_data['me_marker_count']}")

    # Compare counts
    db_segment_count = len(db_segments)
    binary_segment_count = map_data['segment_count']

    print(f"\n  COMPARISON:")
    print(f"    Database segments: {db_segment_count}")
    print(f"    Binary segments: {binary_segment_count}")
    print(f"    Match: {'✓' if db_segment_count == binary_segment_count else '✗'}")

    # Detailed segment analysis
    if map_data['segments']:
        print(f"\n  Binary segment data after **ME markers:")
        print(f"  {'IDX':<4} {'POS':<8} {'b4-7(idx?)':<12} {'b8-11(next)':<12} {'b16-17':<10} {'b20-23':<10}")
        print(f"  {'-'*4} {'-'*8} {'-'*12} {'-'*12} {'-'*10} {'-'*10}")

        for seg in map_data['segments']:
            idx = seg['segment_index']
            pos = seg['marker_pos']
            b4_7 = seg.get('bytes_4_7', 'N/A')
            b8_11 = seg.get('bytes_8_11', 'N/A')
            b16_17 = seg.get('bytes_16_17', 'N/A')
            b20_23 = seg.get('bytes_20_23', 'N/A')
            print(f"  {idx:<4} {pos:<8} {b4_7:<12} {b8_11:<12} {b16_17:<10} {b20_23:<10}")

        # Try to find correlation with START_PAGE_NUMBER
        print(f"\n  Looking for page number correlation:")
        for i, (seg, db_row) in enumerate(zip(map_data['segments'], db_segments)):
            db_start_page = db_row[6]
            db_num_pages = db_row[7]

            # Check all parsed values against START_PAGE_NUMBER
            matches = []
            for key, value in seg.items():
                if isinstance(value, int) and value == db_start_page:
                    matches.append(f"{key}={value}")
                if isinstance(value, int) and value == db_num_pages:
                    matches.append(f"{key}={value} (num_pages)")

            if matches:
                print(f"    Segment {i}: DB(start={db_start_page}, num={db_num_pages}) -> Binary matches: {', '.join(matches)}")
            else:
                print(f"    Segment {i}: DB(start={db_start_page}, num={db_num_pages}) -> No direct matches found")
                # Show all non-zero values
                values = [(k, v) for k, v in seg.items() if isinstance(v, int) and 0 < v < 1000 and k.startswith('bytes')]
                if values:
                    print(f"              Binary values: {values[:8]}")

    return {
        'filename': filename,
        'db_segments': db_segments,
        'map_data': map_data,
        'match': db_segment_count == binary_segment_count
    }


def main():
    args = parse_arguments()

    if not args.password:
        print("Error: Password required. Use --password or set SQLPassword environment variable.")
        sys.exit(1)

    conn = connect_to_database(
        args.server, args.port, args.database, args.user, args.password
    )

    cursor = conn.cursor()

    print("\n" + "="*70)
    print("CORRELATING MAP FILES WITH REPORT_INSTANCE_SEGMENT")
    print("="*70)
    print(f"\nMAP directory: {args.map_dir}")
    print(f"Analyzing January 2025 files (filename starts with '25001')")

    # Query January 2025 MAP files
    print(f"\nQuerying MAP files from January 2025 (limit: {args.limit})...")
    map_files = query_january_2025_map_files(cursor, args.limit)

    if not map_files:
        print("No January 2025 MAP files found in database")
        sys.exit(1)

    print(f"\nFound {len(map_files)} MAP files with segment data:")
    for row in map_files:
        print(f"  {row[0]}: DOMAIN={row[2]}, SPECIES={row[3]}, DB_SEGMENTS={row[4]}")

    # Analyze each file
    results = []
    for row in map_files:
        filename = row[0]
        result = correlate_single_file(cursor, filename, args.map_dir)
        if result:
            results.append(result)

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    if results:
        matches = sum(1 for r in results if r['match'])
        print(f"\nFiles analyzed: {len(results)}")
        print(f"Segment count matches: {matches}/{len(results)}")

        print(f"""
Key observations:
- bytes_4_7 after **ME marker: appears to be segment index (0, 1, 2...)
- bytes_8_11 after **ME marker: offset to next **ME marker
- Need to check if START_PAGE_NUMBER or NUMBER_OF_PAGES appear in binary data

Next steps:
1. Look at raw hex dump for segments
2. Compare byte-by-byte with known page numbers
3. Document the exact structure
""")
    else:
        print("\nNo files could be analyzed")

    cursor.close()
    conn.close()
    print("\nDatabase connection closed.")


if __name__ == '__main__':
    main()
