#!/usr/bin/env python3
"""
parse_binary_map_complete.py
Complete Binary MAP File Parser with Database Correlation

This script parses binary .MAP files and correlates them with database information
to extract maximum useful metadata for the IntelliSTOR migration.

Key findings from analysis:
- Binary **ME segments are internal formatting markers (not database segments)
- Database REPORT_INSTANCE_SEGMENT tracks logical page ranges
- Database SECTION contains named sections (for some report types only)
- Binary segment count != database segment count (they serve different purposes)

This parser extracts:
1. Header information (date, version, flags)
2. All **ME marker positions and their metadata
3. Database correlation (REPORT_SPECIES_ID, DOMAIN_ID, segments, sections)
4. Page range information from REPORT_INSTANCE_SEGMENT
5. Section names from SECTION table (where available)

Author: Migration Team
Date: January 2025
"""

import os
import sys
import struct
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

# Database connection
try:
    import pymssql
    HAS_PYMSSQL = True
except ImportError:
    HAS_PYMSSQL = False
    print("Warning: pymssql not installed. Database correlation will be disabled.")

# Configuration
MAP_FILES_DIR = "/Volumes/X9Pro/OCBC/250_MapFiles"
DB_CONFIG = {
    'server': 'localhost',
    'user': 'sa',
    'password': 'Fvrpgr40',
    'database': 'iSTSGUAT',
    'port': 1433
}

# Binary signatures
MAPHDR_SIGNATURE = b'M\x00A\x00P\x00H\x00D\x00R\x00'  # "MAPHDR" in UTF-16LE
ME_MARKER = b'\x2a\x00\x2a\x00\x4d\x00\x45\x00'  # "**ME" in UTF-16LE


class MAPFileParser:
    """Complete parser for binary MAP files with database correlation."""

    def __init__(self, db_connection=None):
        self.db = db_connection
        self.cache = {
            'mapfile': {},      # filename -> MAP_FILE_ID
            'sst_storage': {},  # MAP_FILE_ID -> (DOMAIN_ID, REPORT_SPECIES_ID, AS_OF_TIMESTAMP)
            'sections': {},     # (DOMAIN_ID, REPORT_SPECIES_ID) -> [(SECTION_ID, NAME), ...]
            'segments': {}      # (DOMAIN_ID, REPORT_SPECIES_ID, AS_OF_TIMESTAMP) -> segment info
        }

    def parse_header(self, data: bytes) -> Dict[str, Any]:
        """Parse the MAPHDR header from binary data."""
        header = {
            'valid': False,
            'signature': None,
            'version': None,
            'total_size': None,
            'date_created': None,
            'date_modified': None,
            'flags': None,
            'segment_count': 0,
            'raw_header': None
        }

        if len(data) < 90:
            return header

        # Check signature (bytes 0-11)
        if data[:12] == MAPHDR_SIGNATURE:
            header['valid'] = True
            header['signature'] = 'MAPHDR'
        else:
            return header

        # Parse header fields
        try:
            # Bytes 12-15: Unknown (usually zeros)
            header['unknown_12_15'] = struct.unpack('<I', data[12:16])[0]

            # Bytes 16-17: Version or type flags
            header['version'] = struct.unpack('<H', data[16:18])[0]

            # Bytes 18-19: Total file size or segment indicator
            header['total_size'] = struct.unpack('<H', data[18:20])[0]

            # Bytes 20-23: More size/offset info
            header['offset_20'] = struct.unpack('<I', data[20:24])[0]

            # Look for date strings (format: 01/01/2025 in UTF-16LE)
            # Typically around bytes 24-49 and 50-75
            date_str1 = data[24:48].decode('utf-16le', errors='ignore').strip('\x00')
            date_str2 = data[48:72].decode('utf-16le', errors='ignore').strip('\x00')

            if '/' in date_str1:
                header['date_created'] = date_str1
            if '/' in date_str2:
                header['date_modified'] = date_str2

            # Bytes 72-75: Additional flags
            if len(data) >= 76:
                header['flags'] = struct.unpack('<I', data[72:76])[0]

            # Save raw header for debugging
            header['raw_header'] = data[:90].hex()

        except Exception as e:
            header['parse_error'] = str(e)

        return header

    def find_me_markers(self, data: bytes) -> List[int]:
        """Find all **ME marker positions in the binary data."""
        positions = []
        pos = 0
        while True:
            pos = data.find(ME_MARKER, pos)
            if pos == -1:
                break
            positions.append(pos)
            pos += len(ME_MARKER)
        return positions

    def parse_me_segment(self, data: bytes, start_pos: int, next_pos: Optional[int] = None) -> Dict[str, Any]:
        """Parse a single **ME segment starting at the given position."""
        segment = {
            'position': start_pos,
            'marker': '**ME',
            'data_offset': start_pos + 8,  # Data starts after **ME marker
            'length': None,
            'metadata': {}
        }

        # Calculate segment length
        if next_pos:
            segment['length'] = next_pos - start_pos
        else:
            segment['length'] = len(data) - start_pos

        # Extract data after **ME marker
        data_start = start_pos + 8
        segment_data = data[data_start:data_start + min(100, segment['length'] - 8)]

        if len(segment_data) >= 4:
            # Parse metadata fields
            try:
                # First 4 bytes after **ME: typically 0x008e0000 or similar header
                segment['metadata']['header'] = struct.unpack('<I', segment_data[:4])[0]

                # Next 4 bytes: often segment index
                if len(segment_data) >= 8:
                    segment['metadata']['index'] = struct.unpack('<I', segment_data[4:8])[0]

                # Next 4 bytes: offset or size
                if len(segment_data) >= 12:
                    segment['metadata']['offset'] = struct.unpack('<I', segment_data[8:12])[0]

                # Additional fields
                if len(segment_data) >= 16:
                    segment['metadata']['flags'] = struct.unpack('<I', segment_data[12:16])[0]

                # Look for any embedded text (UTF-16LE)
                text_data = segment_data[16:80] if len(segment_data) > 16 else b''
                try:
                    text = text_data.decode('utf-16le', errors='ignore').strip('\x00')
                    if text and len(text) > 2:
                        segment['metadata']['embedded_text'] = text
                except:
                    pass

            except Exception as e:
                segment['parse_error'] = str(e)

        # Store raw hex for first 50 bytes of segment data
        segment['raw_data'] = segment_data[:50].hex() if segment_data else ''

        return segment

    def parse_map_file(self, filepath: str) -> Dict[str, Any]:
        """Parse a complete MAP file and return all extracted information."""
        result = {
            'filepath': filepath,
            'filename': os.path.basename(filepath),
            'file_size': 0,
            'header': {},
            'segments': [],
            'segment_count_binary': 0,
            'parse_timestamp': datetime.now().isoformat(),
            'errors': []
        }

        try:
            with open(filepath, 'rb') as f:
                data = f.read()

            result['file_size'] = len(data)

            # Parse header
            result['header'] = self.parse_header(data)

            # Find all **ME markers
            me_positions = self.find_me_markers(data)
            result['segment_count_binary'] = len(me_positions)

            # Parse each segment
            for i, pos in enumerate(me_positions):
                next_pos = me_positions[i + 1] if i + 1 < len(me_positions) else None
                segment = self.parse_me_segment(data, pos, next_pos)
                segment['segment_index'] = i
                result['segments'].append(segment)

        except Exception as e:
            result['errors'].append(f"Parse error: {str(e)}")

        return result

    def get_db_info(self, filename: str) -> Dict[str, Any]:
        """Get database information for a MAP file."""
        db_info = {
            'map_file_id': None,
            'domain_id': None,
            'report_species_id': None,
            'as_of_timestamp': None,
            'location_id': None,
            'stored_on_side': None,
            'db_segments': [],
            'sections': [],
            'errors': []
        }

        if not self.db:
            db_info['errors'].append("No database connection")
            return db_info

        try:
            cursor = self.db.cursor(as_dict=True)

            # Get MAPFILE info
            cursor.execute("""
                SELECT MAP_FILE_ID, LOCATION_ID, STORED_ON_SIDE
                FROM MAPFILE
                WHERE FILENAME = %s
            """, (filename,))

            row = cursor.fetchone()
            if row:
                db_info['map_file_id'] = row['MAP_FILE_ID']
                db_info['location_id'] = row['LOCATION_ID']
                db_info['stored_on_side'] = row['STORED_ON_SIDE']
            else:
                db_info['errors'].append(f"MAPFILE entry not found for {filename}")
                return db_info

            # Get SST_STORAGE info
            cursor.execute("""
                SELECT DOMAIN_ID, REPORT_SPECIES_ID, AS_OF_TIMESTAMP
                FROM SST_STORAGE
                WHERE MAP_FILE_ID = %s
            """, (db_info['map_file_id'],))

            row = cursor.fetchone()
            if row:
                db_info['domain_id'] = row['DOMAIN_ID']
                db_info['report_species_id'] = row['REPORT_SPECIES_ID']
                # Keep as datetime object for proper comparison
                db_info['as_of_timestamp'] = row['AS_OF_TIMESTAMP']
                db_info['as_of_timestamp_str'] = str(row['AS_OF_TIMESTAMP']) if row['AS_OF_TIMESTAMP'] else None
            else:
                db_info['errors'].append("SST_STORAGE entry not found")
                return db_info

            # Get REPORT_INSTANCE_SEGMENT info
            # Use the datetime object directly
            cursor.execute("""
                SELECT SEGMENT_NUMBER, START_PAGE_NUMBER, NUMBER_OF_PAGES
                FROM REPORT_INSTANCE_SEGMENT
                WHERE DOMAIN_ID = %s
                  AND REPORT_SPECIES_ID = %s
                  AND AS_OF_TIMESTAMP = %s
                ORDER BY SEGMENT_NUMBER
            """, (db_info['domain_id'], db_info['report_species_id'], db_info['as_of_timestamp']))

            for row in cursor.fetchall():
                db_info['db_segments'].append({
                    'segment_number': row['SEGMENT_NUMBER'],
                    'start_page': row['START_PAGE_NUMBER'],
                    'num_pages': row['NUMBER_OF_PAGES']
                })

            # Get SECTION info
            cursor.execute("""
                SELECT SECTION_ID, NAME
                FROM SECTION
                WHERE DOMAIN_ID = %s
                  AND REPORT_SPECIES_ID = %s
                ORDER BY SECTION_ID
            """, (db_info['domain_id'], db_info['report_species_id']))

            for row in cursor.fetchall():
                db_info['sections'].append({
                    'section_id': row['SECTION_ID'],
                    'name': row['NAME']
                })

        except Exception as e:
            db_info['errors'].append(f"Database error: {str(e)}")

        return db_info

    def parse_with_db_correlation(self, filepath: str) -> Dict[str, Any]:
        """Parse a MAP file and correlate with database information."""
        # Parse the binary file
        result = self.parse_map_file(filepath)

        # Get database info
        result['database'] = self.get_db_info(result['filename'])

        # Add correlation analysis
        result['correlation'] = {
            'binary_segment_count': result['segment_count_binary'],
            'db_segment_count': len(result['database']['db_segments']),
            'section_count': len(result['database']['sections']),
            'segments_match': result['segment_count_binary'] == len(result['database']['db_segments']),
            'has_sections': len(result['database']['sections']) > 0
        }

        return result


def create_db_connection():
    """Create a database connection."""
    if not HAS_PYMSSQL:
        return None

    try:
        conn = pymssql.connect(
            server=DB_CONFIG['server'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            port=DB_CONFIG['port']
        )
        return conn
    except Exception as e:
        print(f"Database connection failed: {e}")
        return None


def main():
    """Main function to demonstrate the parser."""
    print("=" * 70)
    print("Binary MAP File Complete Parser")
    print("=" * 70)

    # Create database connection
    db = create_db_connection()
    if db:
        print("Database connection: OK")
    else:
        print("Database connection: FAILED (continuing without DB)")

    # Create parser
    parser = MAPFileParser(db)

    # Get sample MAP files (first 5 from January 2025)
    map_dir = Path(MAP_FILES_DIR)
    sample_files = sorted([f for f in map_dir.glob("25001*.MAP")])[:5]

    if not sample_files:
        print(f"\nNo MAP files found in {MAP_FILES_DIR}")
        return

    print(f"\nParsing {len(sample_files)} sample MAP files...")
    print("-" * 70)

    results = []
    for filepath in sample_files:
        print(f"\nFile: {filepath.name}")

        result = parser.parse_with_db_correlation(str(filepath))
        results.append(result)

        # Display summary
        print(f"  File Size: {result['file_size']:,} bytes")
        print(f"  Header Valid: {result['header'].get('valid', False)}")
        print(f"  Date Created: {result['header'].get('date_created', 'N/A')}")
        print(f"  Binary Segments: {result['segment_count_binary']}")

        if result['database']['domain_id']:
            print(f"  Domain ID: {result['database']['domain_id']}")
            print(f"  Report Species ID: {result['database']['report_species_id']}")
            print(f"  DB Segments: {len(result['database']['db_segments'])}")
            print(f"  Sections: {len(result['database']['sections'])}")

        print(f"  Segments Match: {result['correlation']['segments_match']}")

        if result['database']['errors']:
            print(f"  DB Errors: {result['database']['errors']}")

    # Save results to JSON
    output_file = "parse_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n\nResults saved to: {output_file}")

    # Summary statistics
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    total_binary_segments = sum(r['segment_count_binary'] for r in results)
    total_db_segments = sum(len(r['database']['db_segments']) for r in results)
    matches = sum(1 for r in results if r['correlation']['segments_match'])

    print(f"Files Parsed: {len(results)}")
    print(f"Total Binary Segments: {total_binary_segments}")
    print(f"Total DB Segments: {total_db_segments}")
    print(f"Files with Matching Counts: {matches}/{len(results)}")

    if db:
        db.close()

    print("\nDone!")


if __name__ == "__main__":
    main()
