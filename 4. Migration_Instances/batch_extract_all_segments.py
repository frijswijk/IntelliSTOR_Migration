#!/usr/bin/env python3
"""
batch_extract_all_segments.py
Batch Process All 26,724 MAP Files

This script processes all binary .MAP files and extracts:
1. Header information (dates, version, flags)
2. Binary segment metadata (positions, lengths, internal structure)
3. Database correlation (DOMAIN_ID, REPORT_SPECIES_ID, page ranges, sections)

Output:
- results/map_segments_complete.csv - Complete mapping of all files
- results/map_file_statistics.json - Summary statistics
- results/errors.log - Any processing errors

Author: Migration Team
Date: January 2025
"""

import os
import sys
import struct
import json
import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict
import time

# Database connection
try:
    import pymssql
    HAS_PYMSSQL = True
except ImportError:
    HAS_PYMSSQL = False
    print("Warning: pymssql not installed. Database correlation will be disabled.")

# Configuration
MAP_FILES_DIR = "/Volumes/X9Pro/OCBC/250_MapFiles"
RESULTS_DIR = "results"
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

# Batch processing settings
BATCH_SIZE = 1000  # Process files in batches
COMMIT_INTERVAL = 100  # Write to CSV every N files
PROGRESS_INTERVAL = 500  # Print progress every N files


def setup_logging():
    """Set up logging to both file and console."""
    os.makedirs(RESULTS_DIR, exist_ok=True)

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'{RESULTS_DIR}/errors.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


class BatchMAPParser:
    """Batch processor for MAP files with database correlation."""

    def __init__(self, db_connection=None, logger=None):
        self.db = db_connection
        self.logger = logger or logging.getLogger(__name__)

        # Statistics
        self.stats = {
            'total_files': 0,
            'processed': 0,
            'errors': 0,
            'valid_headers': 0,
            'with_db_info': 0,
            'with_sections': 0,
            'binary_segments_total': 0,
            'db_segments_total': 0,
            'segments_match_count': 0,
            'by_year': defaultdict(int),
            'by_domain': defaultdict(int),
            'segment_count_distribution': defaultdict(int),
            'processing_time': 0
        }

        # Database cache (loaded upfront for performance)
        self.db_cache = {
            'mapfile': {},      # filename -> {MAP_FILE_ID, LOCATION_ID, STORED_ON_SIDE}
            'sst_storage': {},  # MAP_FILE_ID -> {DOMAIN_ID, REPORT_SPECIES_ID, AS_OF_TIMESTAMP}
        }

    def load_db_cache(self):
        """Pre-load database information for faster processing."""
        if not self.db:
            self.logger.warning("No database connection - skipping cache load")
            return

        self.logger.info("Loading MAPFILE cache...")
        cursor = self.db.cursor(as_dict=True)

        # Load all MAPFILE entries
        cursor.execute("""
            SELECT MAP_FILE_ID, FILENAME, LOCATION_ID, STORED_ON_SIDE
            FROM MAPFILE
        """)
        for row in cursor.fetchall():
            self.db_cache['mapfile'][row['FILENAME']] = {
                'map_file_id': row['MAP_FILE_ID'],
                'location_id': row['LOCATION_ID'],
                'stored_on_side': row['STORED_ON_SIDE']
            }
        self.logger.info(f"Loaded {len(self.db_cache['mapfile']):,} MAPFILE entries")

        # Load all SST_STORAGE entries
        self.logger.info("Loading SST_STORAGE cache...")
        cursor.execute("""
            SELECT MAP_FILE_ID, DOMAIN_ID, REPORT_SPECIES_ID, AS_OF_TIMESTAMP
            FROM SST_STORAGE
        """)
        for row in cursor.fetchall():
            self.db_cache['sst_storage'][row['MAP_FILE_ID']] = {
                'domain_id': row['DOMAIN_ID'],
                'report_species_id': row['REPORT_SPECIES_ID'],
                'as_of_timestamp': row['AS_OF_TIMESTAMP']
            }
        self.logger.info(f"Loaded {len(self.db_cache['sst_storage']):,} SST_STORAGE entries")

    def parse_header(self, data: bytes) -> Dict[str, Any]:
        """Parse the MAPHDR header from binary data."""
        header = {
            'valid': False,
            'version': None,
            'date_created': None,
            'date_modified': None,
            'flags': None
        }

        if len(data) < 90:
            return header

        if data[:12] == MAPHDR_SIGNATURE:
            header['valid'] = True
        else:
            return header

        try:
            header['version'] = struct.unpack('<H', data[16:18])[0]

            # Extract dates
            date_str1 = data[24:48].decode('utf-16le', errors='ignore').strip('\x00')
            date_str2 = data[48:72].decode('utf-16le', errors='ignore').strip('\x00')

            if '/' in date_str1:
                header['date_created'] = date_str1.strip()[:10]  # Just the date part
            if '/' in date_str2:
                header['date_modified'] = date_str2.strip()[:10]

            if len(data) >= 76:
                header['flags'] = struct.unpack('<I', data[72:76])[0]

        except Exception as e:
            self.logger.debug(f"Header parse warning: {e}")

        return header

    def count_me_markers(self, data: bytes) -> int:
        """Count the number of **ME markers in the binary data."""
        count = 0
        pos = 0
        while True:
            pos = data.find(ME_MARKER, pos)
            if pos == -1:
                break
            count += 1
            pos += len(ME_MARKER)
        return count

    def get_db_info_cached(self, filename: str) -> Dict[str, Any]:
        """Get database information from cache."""
        db_info = {
            'map_file_id': None,
            'domain_id': None,
            'report_species_id': None,
            'as_of_timestamp': None,
            'location_id': None,
            'has_db_entry': False
        }

        # Get MAPFILE info from cache
        mapfile_info = self.db_cache['mapfile'].get(filename)
        if mapfile_info:
            db_info['map_file_id'] = mapfile_info['map_file_id']
            db_info['location_id'] = mapfile_info['location_id']

            # Get SST_STORAGE info from cache
            sst_info = self.db_cache['sst_storage'].get(mapfile_info['map_file_id'])
            if sst_info:
                db_info['domain_id'] = sst_info['domain_id']
                db_info['report_species_id'] = sst_info['report_species_id']
                db_info['as_of_timestamp'] = str(sst_info['as_of_timestamp']) if sst_info['as_of_timestamp'] else None
                db_info['has_db_entry'] = True

        return db_info

    def get_db_segments(self, domain_id: int, report_species_id: int, as_of_timestamp) -> List[Dict]:
        """Get segment information from database (not cached - too many)."""
        segments = []
        if not self.db or not as_of_timestamp:
            return segments

        try:
            cursor = self.db.cursor(as_dict=True)
            cursor.execute("""
                SELECT SEGMENT_NUMBER, START_PAGE_NUMBER, NUMBER_OF_PAGES
                FROM REPORT_INSTANCE_SEGMENT
                WHERE DOMAIN_ID = %s
                  AND REPORT_SPECIES_ID = %s
                  AND AS_OF_TIMESTAMP = %s
                ORDER BY SEGMENT_NUMBER
            """, (domain_id, report_species_id, as_of_timestamp))

            for row in cursor.fetchall():
                segments.append({
                    'segment_number': row['SEGMENT_NUMBER'],
                    'start_page': row['START_PAGE_NUMBER'],
                    'num_pages': row['NUMBER_OF_PAGES']
                })
        except Exception as e:
            self.logger.debug(f"Segment query error: {e}")

        return segments

    def get_section_count(self, domain_id: int, report_species_id: int) -> int:
        """Get section count from database."""
        if not self.db:
            return 0

        try:
            cursor = self.db.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM SECTION
                WHERE DOMAIN_ID = %s AND REPORT_SPECIES_ID = %s
            """, (domain_id, report_species_id))
            result = cursor.fetchone()
            return result[0] if result else 0
        except Exception as e:
            return 0

    def process_file(self, filepath: str) -> Dict[str, Any]:
        """Process a single MAP file."""
        filename = os.path.basename(filepath)

        result = {
            'filename': filename,
            'file_size': 0,
            'header_valid': False,
            'date_created': None,
            'version': None,
            'binary_segment_count': 0,
            'map_file_id': None,
            'domain_id': None,
            'report_species_id': None,
            'as_of_timestamp': None,
            'db_segment_count': 0,
            'section_count': 0,
            'segments_match': False,
            'error': None
        }

        try:
            # Read and parse binary file
            with open(filepath, 'rb') as f:
                data = f.read()

            result['file_size'] = len(data)

            # Parse header
            header = self.parse_header(data)
            result['header_valid'] = header['valid']
            result['date_created'] = header.get('date_created')
            result['version'] = header.get('version')

            # Count binary segments
            result['binary_segment_count'] = self.count_me_markers(data)

            # Get database info
            db_info = self.get_db_info_cached(filename)
            result['map_file_id'] = db_info['map_file_id']
            result['domain_id'] = db_info['domain_id']
            result['report_species_id'] = db_info['report_species_id']
            result['as_of_timestamp'] = db_info['as_of_timestamp']

            # Get DB segments if we have the info
            if db_info['has_db_entry'] and db_info['as_of_timestamp']:
                # Parse timestamp back to datetime for query
                from datetime import datetime as dt
                try:
                    ts = dt.strptime(db_info['as_of_timestamp'], '%Y-%m-%d %H:%M:%S.%f')
                except:
                    try:
                        ts = dt.strptime(db_info['as_of_timestamp'], '%Y-%m-%d %H:%M:%S')
                    except:
                        ts = None

                if ts:
                    db_segments = self.get_db_segments(
                        db_info['domain_id'],
                        db_info['report_species_id'],
                        ts
                    )
                    result['db_segment_count'] = len(db_segments)

                # Get section count
                result['section_count'] = self.get_section_count(
                    db_info['domain_id'],
                    db_info['report_species_id']
                )

            # Check if segments match
            result['segments_match'] = (result['binary_segment_count'] == result['db_segment_count'])

        except Exception as e:
            result['error'] = str(e)
            self.logger.error(f"Error processing {filename}: {e}")

        return result

    def process_all_files(self, limit: int = None):
        """Process all MAP files in the directory."""
        map_dir = Path(MAP_FILES_DIR)
        all_files = sorted(map_dir.glob("*.MAP"))

        if limit:
            all_files = all_files[:limit]

        self.stats['total_files'] = len(all_files)
        self.logger.info(f"Found {self.stats['total_files']:,} MAP files to process")

        # Pre-load database cache
        self.load_db_cache()

        # Prepare output files
        os.makedirs(RESULTS_DIR, exist_ok=True)
        csv_file = f'{RESULTS_DIR}/map_segments_complete.csv'

        # CSV fieldnames
        fieldnames = [
            'filename', 'file_size', 'header_valid', 'date_created', 'version',
            'binary_segment_count', 'map_file_id', 'domain_id', 'report_species_id',
            'as_of_timestamp', 'db_segment_count', 'section_count', 'segments_match', 'error'
        ]

        start_time = time.time()
        results_buffer = []

        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for i, filepath in enumerate(all_files):
                # Process file
                result = self.process_file(str(filepath))
                results_buffer.append(result)

                # Update statistics
                self.stats['processed'] += 1
                if result['error']:
                    self.stats['errors'] += 1
                if result['header_valid']:
                    self.stats['valid_headers'] += 1
                if result['domain_id']:
                    self.stats['with_db_info'] += 1
                    self.stats['by_domain'][result['domain_id']] += 1
                if result['section_count'] > 0:
                    self.stats['with_sections'] += 1
                if result['segments_match']:
                    self.stats['segments_match_count'] += 1

                self.stats['binary_segments_total'] += result['binary_segment_count']
                self.stats['db_segments_total'] += result['db_segment_count']
                self.stats['segment_count_distribution'][result['binary_segment_count']] += 1

                # Extract year from filename (first 2 digits)
                if len(result['filename']) >= 2:
                    year_code = result['filename'][:2]
                    self.stats['by_year'][year_code] += 1

                # Write to CSV periodically
                if len(results_buffer) >= COMMIT_INTERVAL:
                    writer.writerows(results_buffer)
                    results_buffer = []
                    f.flush()

                # Progress update
                if (i + 1) % PROGRESS_INTERVAL == 0:
                    elapsed = time.time() - start_time
                    rate = (i + 1) / elapsed
                    eta = (self.stats['total_files'] - i - 1) / rate if rate > 0 else 0
                    self.logger.info(
                        f"Progress: {i + 1:,}/{self.stats['total_files']:,} "
                        f"({100 * (i + 1) / self.stats['total_files']:.1f}%) "
                        f"- Rate: {rate:.1f} files/sec - ETA: {eta / 60:.1f} min"
                    )

            # Write remaining buffer
            if results_buffer:
                writer.writerows(results_buffer)

        self.stats['processing_time'] = time.time() - start_time
        self.logger.info(f"Processing complete: {self.stats['processed']:,} files in {self.stats['processing_time']:.1f} seconds")

        # Save statistics
        self.save_statistics()

        return self.stats

    def save_statistics(self):
        """Save statistics to JSON file."""
        # Convert defaultdicts to regular dicts for JSON serialization
        stats_json = {
            'summary': {
                'total_files': self.stats['total_files'],
                'processed': self.stats['processed'],
                'errors': self.stats['errors'],
                'valid_headers': self.stats['valid_headers'],
                'with_db_info': self.stats['with_db_info'],
                'with_sections': self.stats['with_sections'],
                'binary_segments_total': self.stats['binary_segments_total'],
                'db_segments_total': self.stats['db_segments_total'],
                'segments_match_count': self.stats['segments_match_count'],
                'processing_time_seconds': round(self.stats['processing_time'], 2)
            },
            'by_year': dict(sorted(self.stats['by_year'].items())),
            'by_domain': dict(sorted(self.stats['by_domain'].items(), key=lambda x: -x[1])),
            'segment_count_distribution': dict(sorted(self.stats['segment_count_distribution'].items()))
        }

        with open(f'{RESULTS_DIR}/map_file_statistics.json', 'w') as f:
            json.dump(stats_json, f, indent=2)

        self.logger.info(f"Statistics saved to {RESULTS_DIR}/map_file_statistics.json")


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
    """Main function to run batch processing."""
    print("=" * 70)
    print("Batch MAP File Processor")
    print("=" * 70)

    # Parse command line arguments
    limit = None
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
            print(f"Processing limited to {limit} files")
        except ValueError:
            print(f"Usage: {sys.argv[0]} [limit]")
            sys.exit(1)

    # Set up logging
    logger = setup_logging()
    logger.info("Starting batch processing")

    # Create database connection
    db = create_db_connection()
    if db:
        logger.info("Database connection: OK")
    else:
        logger.warning("Database connection: FAILED (continuing without DB)")

    # Create processor and run
    processor = BatchMAPParser(db, logger)
    stats = processor.process_all_files(limit)

    # Print final summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    print(f"Total Files: {stats['total_files']:,}")
    print(f"Processed: {stats['processed']:,}")
    print(f"Errors: {stats['errors']:,}")
    print(f"Valid Headers: {stats['valid_headers']:,}")
    print(f"With DB Info: {stats['with_db_info']:,}")
    print(f"With Sections: {stats['with_sections']:,}")
    print(f"Binary Segments Total: {stats['binary_segments_total']:,}")
    print(f"DB Segments Total: {stats['db_segments_total']:,}")
    print(f"Files with Matching Segment Counts: {stats['segments_match_count']:,}")
    print(f"Processing Time: {stats['processing_time']:.1f} seconds")

    if db:
        db.close()

    print("\nOutput files:")
    print(f"  - {RESULTS_DIR}/map_segments_complete.csv")
    print(f"  - {RESULTS_DIR}/map_file_statistics.json")
    print(f"  - {RESULTS_DIR}/errors.log")

    print("\nDone!")


if __name__ == "__main__":
    main()
