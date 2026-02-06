#!/usr/bin/env python3
"""
Diagnostic script for DDU017P report - Query database metadata
and analyze MAP file entry format.
"""

import pymssql
import struct
import os
import sys

# Database connection
DB_CONFIG = {
    'server': 'localhost',
    'port': 1433,
    'user': 'sa',
    'password': 'Fvrpgr40',
    'database': 'iSTSGUAT'
}

MAP_FILE = '/Volumes/acasis/projects/python/ocbc/Migration_Data/2511109P.MAP'
SPOOL_FILE = '/Volumes/acasis/projects/python/ocbc/Migration_Data/S94752001749_20250416'

ME_MARKER = b'\x2a\x00\x2a\x00\x4d\x00\x45\x00'


def query_database():
    """Query all DDU017P-related metadata from the database."""
    conn = pymssql.connect(**DB_CONFIG)
    cursor = conn.cursor(as_dict=True)

    # 1. REPORT_SPECIES_NAME
    print('=' * 70)
    print('1. REPORT_SPECIES_NAME for DDU017P')
    print('=' * 70)
    cursor.execute("SELECT * FROM REPORT_SPECIES_NAME WHERE NAME LIKE '%DDU017P%'")
    species_rows = cursor.fetchall()
    for row in species_rows:
        print(row)

    if not species_rows:
        print("No DDU017P found in database!")
        conn.close()
        return

    species_id = species_rows[0]['REPORT_SPECIES_ID']
    domain_id = species_rows[0]['DOMAIN_ID']
    print(f"\n→ REPORT_SPECIES_ID = {species_id}, DOMAIN_ID = {domain_id}")

    # 2. REPORT_INSTANCE
    print('\n' + '=' * 70)
    print('2. REPORT_INSTANCE for DDU017P')
    print('=' * 70)
    cursor.execute('''
        SELECT * FROM REPORT_INSTANCE
        WHERE DOMAIN_ID = %s AND REPORT_SPECIES_ID = %s
        ORDER BY AS_OF_TIMESTAMP DESC
    ''', (domain_id, species_id))
    instances = cursor.fetchall()
    for row in instances:
        print(row)

    if instances:
        structure_def_id = instances[0]['STRUCTURE_DEF_ID']
        as_of_timestamp = instances[0]['AS_OF_TIMESTAMP']
        print(f"\n→ STRUCTURE_DEF_ID = {structure_def_id}")
        print(f"→ AS_OF_TIMESTAMP = {as_of_timestamp}")

    # 3. MAPFILE for 2511109P
    print('\n' + '=' * 70)
    print('3. MAPFILE for 2511109P')
    print('=' * 70)
    cursor.execute("SELECT * FROM MAPFILE WHERE FILENAME LIKE '%2511109%'")
    mapfiles = cursor.fetchall()
    for row in mapfiles:
        print(row)

    # 4. SST_STORAGE linkage
    print('\n' + '=' * 70)
    print('4. SST_STORAGE for DDU017P')
    print('=' * 70)
    cursor.execute('''
        SELECT sst.*, mf.FILENAME
        FROM SST_STORAGE sst
        JOIN MAPFILE mf ON sst.MAP_FILE_ID = mf.MAP_FILE_ID
        WHERE sst.DOMAIN_ID = %s AND sst.REPORT_SPECIES_ID = %s
    ''', (domain_id, species_id))
    for row in cursor.fetchall():
        print(row)

    # 5. REPORT_INSTANCE_SEGMENT
    print('\n' + '=' * 70)
    print('5. REPORT_INSTANCE_SEGMENT for DDU017P')
    print('=' * 70)
    cursor.execute('''
        SELECT * FROM REPORT_INSTANCE_SEGMENT
        WHERE DOMAIN_ID = %s AND REPORT_SPECIES_ID = %s
        ORDER BY AS_OF_TIMESTAMP DESC, SEGMENT_NUMBER
    ''', (domain_id, species_id))
    segments = cursor.fetchall()
    for row in segments:
        print(row)
    print(f"\n→ Total segments: {len(segments)}")

    # 6. FIELD definitions
    print('\n' + '=' * 70)
    print(f'6. FIELD definitions (STRUCTURE_DEF_ID = {structure_def_id})')
    print('=' * 70)
    cursor.execute('''
        SELECT f.LINE_ID, f.FIELD_ID, f.NAME, f.START_COLUMN, f.END_COLUMN,
               f.IS_INDEXED, f.IS_SIGNIFICANT
        FROM FIELD f
        WHERE f.STRUCTURE_DEF_ID = %s
        ORDER BY f.LINE_ID, f.FIELD_ID
    ''', (structure_def_id,))
    fields = cursor.fetchall()

    print(f"{'LINE_ID':>8} {'FIELD_ID':>8} {'NAME':<30} {'START':>6} {'END':>6} {'INDEXED':>8} {'SIGNIF':>8}")
    print('-' * 100)
    indexed_fields = []
    significant_fields = []
    for row in fields:
        is_idx = 'YES' if row['IS_INDEXED'] else ''
        is_sig = 'YES' if row['IS_SIGNIFICANT'] else ''
        print(f"{row['LINE_ID']:>8} {row['FIELD_ID']:>8} {(row['NAME'] or '').strip():<30} {row['START_COLUMN']:>6} {row['END_COLUMN']:>6} {is_idx:>8} {is_sig:>8}")
        if row['IS_INDEXED']:
            indexed_fields.append(row)
        if row['IS_SIGNIFICANT']:
            significant_fields.append(row)

    print(f"\n→ IS_INDEXED fields: {len(indexed_fields)}")
    for f in indexed_fields:
        width = f['END_COLUMN'] - f['START_COLUMN'] + 1
        print(f"   LINE {f['LINE_ID']}, FIELD {f['FIELD_ID']}: {(f['NAME'] or '').strip()} (cols {f['START_COLUMN']}-{f['END_COLUMN']}, width={width})")

    print(f"\n→ IS_SIGNIFICANT fields: {len(significant_fields)}")
    for f in significant_fields:
        width = f['END_COLUMN'] - f['START_COLUMN'] + 1
        print(f"   LINE {f['LINE_ID']}, FIELD {f['FIELD_ID']}: {(f['NAME'] or '').strip()} (cols {f['START_COLUMN']}-{f['END_COLUMN']}, width={width})")

    # 7. LINE definitions
    print('\n' + '=' * 70)
    print(f'7. LINE definitions (STRUCTURE_DEF_ID = {structure_def_id})')
    print('=' * 70)
    cursor.execute('''
        SELECT l.LINE_ID, l.NAME, l.TEMPLATE
        FROM LINE l
        WHERE l.STRUCTURE_DEF_ID = %s
        ORDER BY l.LINE_ID
    ''', (structure_def_id,))
    lines = cursor.fetchall()
    for row in lines:
        name = (row['NAME'] or '').strip()
        template = (row['TEMPLATE'] or '').strip()[:80]
        print(f"  LINE {row['LINE_ID']:>4}: {name:<20} TEMPLATE: {template}")
    print(f"\n→ Total lines: {len(lines)}")

    # 8. SECTION entries
    print('\n' + '=' * 70)
    print('8. SECTION entries for DDU017P')
    print('=' * 70)
    cursor.execute('''
        SELECT * FROM SECTION
        WHERE DOMAIN_ID = %s AND REPORT_SPECIES_ID = %s
        ORDER BY SECTION_ID
    ''', (domain_id, species_id))
    sections = cursor.fetchall()
    for row in sections:
        print(f"  SECTION_ID={row['SECTION_ID']}, NAME='{(row['NAME'] or '').strip()}'")
    print(f"\n→ Total sections: {len(sections)}")

    # 9. RPTFILE (spool file)
    print('\n' + '=' * 70)
    print('9. RPTFILE_INSTANCE / RPTFILE for DDU017P')
    print('=' * 70)
    cursor.execute('''
        SELECT rfi.*, rf.FILENAME as RPT_FILENAME, rf.LOCATION_ID as RPT_LOCATION
        FROM RPTFILE_INSTANCE rfi
        JOIN RPTFILE rf ON rfi.RPT_FILE_ID = rf.RPT_FILE_ID
        WHERE rfi.DOMAIN_ID = %s AND rfi.REPORT_SPECIES_ID = %s
    ''', (domain_id, species_id))
    for row in cursor.fetchall():
        print(row)

    conn.close()


def analyze_map_entries():
    """Read all 13 index entries from 2511109P.MAP Segment 1."""
    print('\n' + '=' * 70)
    print('MAP FILE ANALYSIS: 2511109P.MAP')
    print('=' * 70)

    with open(MAP_FILE, 'rb') as f:
        data = f.read()

    print(f"File size: {len(data):,} bytes")

    # Find **ME markers
    me_positions = []
    pos = 0
    while True:
        pos = data.find(ME_MARKER, pos)
        if pos == -1:
            break
        me_positions.append(pos)
        pos += 8

    print(f"**ME markers: {len(me_positions)} at positions: {[hex(p) for p in me_positions]}")

    # Parse header
    seg_count = struct.unpack('<H', data[18:20])[0]
    date_str = data[0x20:0x34].decode('utf-16le', errors='ignore').strip('\x00')
    print(f"Segment count: {seg_count}, Date: {date_str}")

    if len(me_positions) < 2:
        print("ERROR: Need at least 2 **ME markers")
        return

    # Parse Segment 1 metadata
    seg1_me = me_positions[1]
    meta_off = seg1_me + 24

    page_start = struct.unpack('<H', data[meta_off:meta_off+2])[0]
    line_id = struct.unpack('<H', data[meta_off+2:meta_off+4])[0]
    field_id = struct.unpack('<H', data[meta_off+6:meta_off+8])[0]
    field_width = struct.unpack('<H', data[meta_off+10:meta_off+12])[0]
    entry_count = struct.unpack('<H', data[meta_off+14:meta_off+16])[0]

    print(f"\nSegment 1 metadata:")
    print(f"  page_start={page_start}, LINE_ID={line_id}, FIELD_ID={field_id}")
    print(f"  field_width={field_width}, entry_count={entry_count}")

    # Dynamically find data_offset by searching for first valid length indicator
    search_start = seg1_me + 0xC0  # Start searching a bit before expected position
    search_end = min(seg1_me + 0x200, len(data))

    data_offset = None
    for probe in range(search_start, search_end):
        if probe + 2 > len(data):
            break
        probe_len = struct.unpack('<H', data[probe:probe+2])[0]
        if probe_len == field_width:
            # Check if the text after looks like an account number
            text = data[probe+2:probe+2+field_width].decode('ascii', errors='replace')
            if any(c.isdigit() for c in text[:3]):
                data_offset = probe
                break

    if data_offset is None:
        print("ERROR: Could not find data_offset!")
        return

    offset_from_me = data_offset - seg1_me
    print(f"\n→ data_offset found at {hex(data_offset)} (offset {hex(offset_from_me)} = {offset_from_me} from **ME)")

    # Read ALL entries
    print(f"\n{'#':>3} {'Account':<20} {'Raw 5 bytes after text':>30} {'uint16_1':>10} {'uint16_2':>10} {'uint32':>12} {'Last byte':>10}")
    print('-' * 100)

    entry_size = 2 + field_width + 5  # length(2) + text(14) + remaining(5)
    entries = []

    offset = data_offset
    for i in range(entry_count + 5):  # Read a few extra to be safe
        if offset + entry_size > len(data):
            break

        length = struct.unpack('<H', data[offset:offset+2])[0]
        if length != field_width:
            break

        text = data[offset+2:offset+2+field_width].decode('ascii', errors='replace').strip()
        remaining = data[offset+2+field_width:offset+2+field_width+5]

        # Interpret remaining bytes multiple ways
        if len(remaining) >= 5:
            uint16_1 = struct.unpack('<H', remaining[0:2])[0]
            uint16_2 = struct.unpack('<H', remaining[2:4])[0]
            uint32_val = struct.unpack('<I', remaining[0:4])[0]
            last_byte = remaining[4]

            hex_str = ' '.join(f'{b:02x}' for b in remaining)
            print(f"{i+1:>3} '{text}'  {hex_str:>30}  {uint16_1:>10} {uint16_2:>10} {uint32_val:>12}  {last_byte:>10}")

            entries.append({
                'index': i,
                'account': text,
                'raw': remaining,
                'uint16_1': uint16_1,
                'uint16_2': uint16_2,
                'uint32': uint32_val,
                'last_byte': last_byte
            })

        offset += entry_size

    print(f"\n→ Read {len(entries)} entries")
    return entries


def search_spool_for_accounts(entries):
    """Search the spool file for each account to find actual page/line positions."""
    print('\n' + '=' * 70)
    print('SPOOL FILE ANALYSIS: Finding account positions')
    print('=' * 70)

    if not os.path.exists(SPOOL_FILE):
        print(f"ERROR: Spool file not found: {SPOOL_FILE}")
        return

    # Read spool file and build page index
    with open(SPOOL_FILE, 'rb') as f:
        spool_data = f.read()

    print(f"Spool file size: {len(spool_data):,} bytes")

    # Decode to text (try different line endings)
    text = spool_data.decode('ascii', errors='replace')

    # Split into lines
    if '\r\n' in text[:1000]:
        lines = text.split('\r\n')
        line_ending = 'CRLF'
    else:
        lines = text.split('\n')
        line_ending = 'LF'

    print(f"Line ending: {line_ending}")
    print(f"Total lines: {len(lines):,}")

    # Build page index (ASA format: line starts with '1' = new page)
    page_starts = []  # (line_number, byte_offset)
    byte_offset = 0
    for line_num, line in enumerate(lines):
        if line and line[0] == '1':
            page_starts.append((line_num, byte_offset))
        byte_offset += len(line) + (2 if line_ending == 'CRLF' else 1)

    print(f"Total pages: {len(page_starts)}")

    # For each account, find its position
    print(f"\n{'Account':<20} {'First Line':>10} {'Page':>6} {'Line in Page':>12} {'Byte Offset':>14} {'Branch':>8}")
    print('-' * 80)

    if not entries:
        return

    results = []
    for entry in entries:
        account = entry['account']

        # Find first occurrence in spool
        found_line = None
        found_page = None
        found_branch = None
        found_byte_offset = None

        for line_num, line in enumerate(lines):
            if account in line:
                found_line = line_num
                # Determine which page this line is on
                for pg_idx, (pg_line, pg_byte) in enumerate(page_starts):
                    if pg_idx + 1 < len(page_starts) and page_starts[pg_idx + 1][0] > line_num:
                        found_page = pg_idx + 1  # 1-indexed
                        break
                    elif pg_idx + 1 == len(page_starts):
                        found_page = pg_idx + 1
                        break

                # Find branch for this page (look for BRANCH: pattern near page start)
                if found_page:
                    pg_line_start = page_starts[found_page - 1][0]
                    for check_line in range(pg_line_start, min(pg_line_start + 10, len(lines))):
                        if 'BRANCH:' in lines[check_line] or 'BRANCH :' in lines[check_line]:
                            # Extract branch number
                            branch_pos = lines[check_line].find('BRANCH')
                            branch_text = lines[check_line][branch_pos:branch_pos+15]
                            # Extract digits after ':'
                            colon_pos = branch_text.find(':')
                            if colon_pos >= 0:
                                found_branch = branch_text[colon_pos+1:].strip()[:5].strip()
                            break

                break  # Only first occurrence

        # Calculate byte offset of the line
        if found_line is not None:
            found_byte_offset = sum(len(lines[i]) + (2 if line_ending == 'CRLF' else 1) for i in range(found_line))

        line_in_page = None
        if found_line is not None and found_page is not None:
            line_in_page = found_line - page_starts[found_page - 1][0]

        print(f"'{account}'  {found_line if found_line is not None else 'N/A':>10} {found_page if found_page is not None else 'N/A':>6} {line_in_page if line_in_page is not None else 'N/A':>12} {found_byte_offset if found_byte_offset is not None else 'N/A':>14} {found_branch or 'N/A':>8}")

        results.append({
            'account': account,
            'spool_line': found_line,
            'spool_page': found_page,
            'line_in_page': line_in_page,
            'byte_offset': found_byte_offset,
            'branch': found_branch,
            'map_uint16_1': entry['uint16_1'],
            'map_uint16_2': entry['uint16_2'],
            'map_uint32': entry['uint32'],
            'map_last_byte': entry['last_byte']
        })

    # Correlation analysis
    print('\n' + '=' * 70)
    print('CORRELATION ANALYSIS')
    print('=' * 70)
    print(f"\n{'Account':<20} {'MAP uint16_1':>12} {'MAP uint16_2':>12} {'MAP uint32':>12} {'Spool Page':>10} {'Spool Line':>10} {'Byte Off':>12}")
    print('-' * 90)

    for r in results:
        print(f"'{r['account']}'  {r['map_uint16_1']:>12} {r['map_uint16_2']:>12} {r['map_uint32']:>12} {r['spool_page'] if r['spool_page'] else 'N/A':>10} {r['spool_line'] if r['spool_line'] is not None else 'N/A':>10} {r['byte_offset'] if r['byte_offset'] is not None else 'N/A':>12}")

    # Test hypotheses
    print('\n--- Hypothesis Testing ---')
    for r in results:
        if r['spool_page'] and r['spool_line'] is not None and r['byte_offset'] is not None:
            ratios = []
            if r['spool_page'] > 0:
                ratios.append(f"uint16_1/page = {r['map_uint16_1']/r['spool_page']:.2f}")
            if r['spool_line'] > 0:
                ratios.append(f"uint16_1/line = {r['map_uint16_1']/r['spool_line']:.4f}")
                ratios.append(f"uint32/line = {r['map_uint32']/r['spool_line']:.4f}")
            if r['byte_offset'] > 0:
                ratios.append(f"uint32/byte = {r['map_uint32']/r['byte_offset']:.6f}")
            print(f"  {r['account']}: {', '.join(ratios)}")

    return results


def analyze_segment0_lookup():
    """Analyze Segment 0 lookup table and branch index."""
    print('\n' + '=' * 70)
    print('SEGMENT 0 ANALYSIS')
    print('=' * 70)

    with open(MAP_FILE, 'rb') as f:
        data = f.read()

    me_positions = []
    pos = 0
    while True:
        pos = data.find(ME_MARKER, pos)
        if pos == -1:
            break
        me_positions.append(pos)
        pos += 8

    seg0_start = me_positions[0]
    seg1_start = me_positions[1]
    seg0_size = seg1_start - seg0_start

    print(f"Segment 0: {hex(seg0_start)} to {hex(seg1_start)} ({seg0_size:,} bytes)")

    # Parse Segment 0 header
    header_off = seg0_start + 8
    const = struct.unpack('<I', data[header_off:header_off+4])[0]
    seg_index = struct.unpack('<I', data[header_off+4:header_off+8])[0]
    next_offset = struct.unpack('<I', data[header_off+8:header_off+12])[0]

    print(f"Header: const={hex(const)}, index={seg_index}, next_offset={hex(next_offset)}")

    # Dump first 512 bytes of Segment 0 (after **ME)
    print(f"\nFirst 512 bytes of Segment 0 data (from {hex(seg0_start)}):")
    for row_start in range(0, 512, 16):
        offset = seg0_start + row_start
        hex_bytes = ' '.join(f'{data[offset+i]:02x}' for i in range(min(16, len(data) - offset)))
        ascii_bytes = ''.join(chr(data[offset+i]) if 32 <= data[offset+i] < 127 else '.' for i in range(min(16, len(data) - offset)))
        print(f"  {hex(offset)}: {hex_bytes:<48} {ascii_bytes}")

    # Parse lookup table at offset 0xC2 from **ME
    lookup_start = seg0_start + 0xC2
    print(f"\nLookup table starting at {hex(lookup_start)}:")
    print(f"{'Offset':>10} {'SEG':>4} {'LINE':>5} {'FIELD':>6} {'FLAGS':>6} {'Hex':>15}")
    print('-' * 50)

    entries_found = 0
    offset = lookup_start
    while offset < seg1_start - 4 and entries_found < 100:
        b = data[offset:offset+4]
        seg_num, line_id, field_id, flags = b[0], b[1], b[2], b[3]

        # Check for all-zeros (end of table)
        if b == b'\x00\x00\x00\x00':
            # Check if next 4 bytes are also zeros
            if data[offset+4:offset+8] == b'\x00\x00\x00\x00':
                print(f"  {hex(offset)}: (end of lookup table - consecutive zeros)")
                break

        hex_str = ' '.join(f'{x:02x}' for x in b)

        # Only show entries that look valid
        if seg_num <= 50 and line_id > 0:
            print(f"  {hex(offset)}: {seg_num:>4} {line_id:>5} {field_id:>6} {flags:>6}  [{hex_str}]")
            entries_found += 1
        elif any(x != 0 for x in b):
            print(f"  {hex(offset)}: {seg_num:>4} {line_id:>5} {field_id:>6} {flags:>6}  [{hex_str}] (unusual)")
            entries_found += 1

        offset += 4

    # Look for branch codes in Segment 0 data
    print(f"\nSearching for branch codes in Segment 0...")
    branch_codes = ['201', '217', '218', '270', '291', '501', '503', '563']

    for branch in branch_codes:
        # Search for the branch as ASCII bytes
        branch_bytes = branch.encode('ascii')
        search_pos = seg0_start
        found_positions = []
        while True:
            search_pos = data.find(branch_bytes, search_pos, seg1_start)
            if search_pos == -1:
                break
            found_positions.append(search_pos)
            search_pos += 1

        if found_positions:
            print(f"  Branch '{branch}': found at {len(found_positions)} positions")
            for fp in found_positions[:3]:  # Show first 3
                context = data[fp-4:fp+8]
                hex_ctx = ' '.join(f'{b:02x}' for b in context)
                print(f"    {hex(fp)}: [{hex_ctx}]")

    # Analyze data patterns - look at structure after lookup table
    # Check for 16-byte repeating structures
    print(f"\nAnalyzing data structure after lookup table...")
    data_start = offset  # Where lookup table ended
    print(f"Data section starts at {hex(data_start)}")

    # Show first 20 x 16-byte blocks
    for i in range(20):
        block_off = data_start + (i * 16)
        if block_off + 16 > seg1_start:
            break
        block = data[block_off:block_off+16]
        hex_str = ' '.join(f'{b:02x}' for b in block)

        # Try to interpret
        w0 = struct.unpack('<H', block[0:2])[0]
        w1 = struct.unpack('<H', block[2:4])[0]
        w2 = struct.unpack('<H', block[4:6])[0]
        w3 = struct.unpack('<H', block[6:8])[0]
        d0 = struct.unpack('<I', block[0:4])[0]
        d1 = struct.unpack('<I', block[4:8])[0]
        d2 = struct.unpack('<I', block[8:12])[0]
        d3 = struct.unpack('<I', block[12:16])[0]

        print(f"  {hex(block_off)}: {hex_str}  words: [{w0}, {w1}, {w2}, {w3}]  dwords: [{d0}, {d1}, {d2}, {d3}]")


if __name__ == '__main__':
    print("DDU017P Diagnostic Script")
    print("=" * 70)

    # Part 1: Database
    try:
        query_database()
    except Exception as e:
        print(f"Database error: {e}")
        import traceback
        traceback.print_exc()

    # Part 2: MAP file entry analysis
    try:
        entries = analyze_map_entries()
    except Exception as e:
        print(f"MAP analysis error: {e}")
        import traceback
        traceback.print_exc()
        entries = None

    # Part 3: Spool file correlation
    if entries:
        try:
            search_spool_for_accounts(entries)
        except Exception as e:
            print(f"Spool analysis error: {e}")
            import traceback
            traceback.print_exc()

    # Part 4: Segment 0 analysis
    try:
        analyze_segment0_lookup()
    except Exception as e:
        print(f"Segment 0 analysis error: {e}")
        import traceback
        traceback.print_exc()

    print("\nDone.")
