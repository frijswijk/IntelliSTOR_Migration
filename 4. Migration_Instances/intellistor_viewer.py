#!/usr/bin/env python3
"""
IntelliSTOR Report Viewer - Test Implementation

This program demonstrates the complete workflow for:
1. Section segregation (IS_SIGNIFICANT fields with permissions)
2. Index search (IS_INDEXED fields) using binary MAP file index
3. Fast page access in large spool files (Form Feed and ASA formats)

MAP File Index Structure:
- Segment 0: Lookup/Directory table mapping (LINE_ID, FIELD_ID) → segment number
- Segments 1-N: Index entries for each indexed field
- Entry format: [length:2][value:N][page:2][flags:3] where N = field_width

Usage:
    python intellistor_viewer.py --help

    # Analyze MAP file structure
    python intellistor_viewer.py --map 25001002.MAP
    python intellistor_viewer.py --map 25001002.MAP --show-entries

    # Search for value in MAP file index
    python intellistor_viewer.py --map 25001002.MAP --search EP24123109039499 --line 5 --field 3

    # Analyze spool file
    python intellistor_viewer.py --spool Report_TXT_Viewer/CDU100P.txt

    # Show report information (requires database)
    python intellistor_viewer.py --report CDU100P

Requirements:
    - Database: iSTSGUAT on localhost:1433 (optional, for --report)
    - MAP files: /Volumes/X9Pro/OCBC/250_MapFiles/
    - Spool files: matching .TXT/.RPT files
"""

import argparse
import struct
import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime

try:
    import pymssql
    HAS_PYMSSQL = True
except ImportError:
    HAS_PYMSSQL = False
    print("Warning: pymssql not installed. Database features disabled.")


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class Config:
    """Configuration for IntelliSTOR viewer"""
    db_server: str = 'localhost'
    db_port: int = 1433
    db_name: str = 'iSTSGUAT'
    db_user: str = 'sa'
    db_password: str = 'Fvrpgr40'
    map_file_dir: str = '/Volumes/X9Pro/OCBC/250_MapFiles'
    spool_file_dir: str = ''  # Set when spool files are available
    domain_id: int = 1


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class FieldDef:
    """Field definition from database"""
    structure_def_id: int
    line_id: int
    field_id: int
    name: str
    start_column: int
    end_column: int
    is_indexed: bool
    is_significant: bool


@dataclass
class LineDef:
    """Line definition from database"""
    structure_def_id: int
    line_id: int
    name: str
    template: str


@dataclass
class ReportInstance:
    """Report instance from database"""
    domain_id: int
    report_species_id: int
    as_of_timestamp: datetime
    structure_def_id: int
    rpt_file_size_kb: int
    map_file_size_kb: int


@dataclass
class Segment:
    """Segment from REPORT_INSTANCE_SEGMENT"""
    segment_number: int
    start_page_number: int
    number_of_pages: int


@dataclass
class Section:
    """Section from SECTION table"""
    section_id: int
    name: str


@dataclass
class MapFileInfo:
    """Information from binary MAP file"""
    filename: str
    segment_count: int
    date_string: str
    binary_segments: List[Dict[str, Any]] = field(default_factory=list)
    lookup_table: List[Dict[str, int]] = field(default_factory=list)


@dataclass
class MapSegmentInfo:
    """Information about a binary segment in MAP file"""
    index: int
    offset: int
    next_offset: int
    size: int
    page_start: int
    line_id: int
    field_id: int
    field_width: int
    entry_count: int
    data_offset: int


@dataclass
class IndexEntry:
    """Single index entry from MAP file"""
    value: str
    page_number: int
    raw_length: int


# ============================================================================
# Database Access
# ============================================================================

class DatabaseAccess:
    """Database access layer for IntelliSTOR tables"""

    def __init__(self, config: Config):
        self.config = config
        self.conn = None

    def connect(self):
        """Connect to database"""
        if not HAS_PYMSSQL:
            raise RuntimeError("pymssql not installed")
        self.conn = pymssql.connect(
            server=self.config.db_server,
            port=self.config.db_port,
            user=self.config.db_user,
            password=self.config.db_password,
            database=self.config.db_name
        )

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None

    def get_report_instance(self, report_species_id: int,
                           as_of_timestamp: Optional[datetime] = None) -> Optional[ReportInstance]:
        """Get report instance by species ID and optional date"""
        cursor = self.conn.cursor(as_dict=True)

        if as_of_timestamp:
            cursor.execute("""
                SELECT DOMAIN_ID, REPORT_SPECIES_ID, AS_OF_TIMESTAMP,
                       STRUCTURE_DEF_ID, RPT_FILE_SIZE_KB, MAP_FILE_SIZE_KB
                FROM REPORT_INSTANCE
                WHERE DOMAIN_ID = %s AND REPORT_SPECIES_ID = %s
                      AND AS_OF_TIMESTAMP = %s
            """, (self.config.domain_id, report_species_id, as_of_timestamp))
        else:
            cursor.execute("""
                SELECT TOP 1 DOMAIN_ID, REPORT_SPECIES_ID, AS_OF_TIMESTAMP,
                       STRUCTURE_DEF_ID, RPT_FILE_SIZE_KB, MAP_FILE_SIZE_KB
                FROM REPORT_INSTANCE
                WHERE DOMAIN_ID = %s AND REPORT_SPECIES_ID = %s
                ORDER BY AS_OF_TIMESTAMP DESC
            """, (self.config.domain_id, report_species_id))

        row = cursor.fetchone()
        if row:
            return ReportInstance(
                domain_id=row['DOMAIN_ID'],
                report_species_id=row['REPORT_SPECIES_ID'],
                as_of_timestamp=row['AS_OF_TIMESTAMP'],
                structure_def_id=row['STRUCTURE_DEF_ID'],
                rpt_file_size_kb=row['RPT_FILE_SIZE_KB'] or 0,
                map_file_size_kb=row['MAP_FILE_SIZE_KB'] or 0
            )
        return None

    def get_report_species_id_by_name(self, name: str) -> Optional[int]:
        """Get REPORT_SPECIES_ID by report name"""
        cursor = self.conn.cursor(as_dict=True)
        cursor.execute("""
            SELECT REPORT_SPECIES_ID FROM REPORT_SPECIES_NAME
            WHERE DOMAIN_ID = %s AND NAME LIKE %s
        """, (self.config.domain_id, f'%{name}%'))
        row = cursor.fetchone()
        return row['REPORT_SPECIES_ID'] if row else None

    def get_map_filename(self, instance: ReportInstance) -> Optional[str]:
        """Get MAP filename for a report instance"""
        cursor = self.conn.cursor(as_dict=True)
        cursor.execute("""
            SELECT mf.FILENAME
            FROM SST_STORAGE sst
            JOIN MAPFILE mf ON sst.MAP_FILE_ID = mf.MAP_FILE_ID
            WHERE sst.DOMAIN_ID = %s AND sst.REPORT_SPECIES_ID = %s
                  AND sst.AS_OF_TIMESTAMP = %s
        """, (instance.domain_id, instance.report_species_id, instance.as_of_timestamp))
        row = cursor.fetchone()
        return row['FILENAME'].strip() if row else None

    def get_spool_filename(self, instance: ReportInstance) -> Optional[str]:
        """Get spool filename for a report instance"""
        cursor = self.conn.cursor(as_dict=True)
        cursor.execute("""
            SELECT rf.FILENAME
            FROM RPTFILE_INSTANCE rfi
            JOIN RPTFILE rf ON rfi.RPT_FILE_ID = rf.RPT_FILE_ID
            WHERE rfi.DOMAIN_ID = %s AND rfi.REPORT_SPECIES_ID = %s
                  AND rfi.AS_OF_TIMESTAMP = %s
        """, (instance.domain_id, instance.report_species_id, instance.as_of_timestamp))
        row = cursor.fetchone()
        return row['FILENAME'].strip() if row else None

    def get_segments(self, instance: ReportInstance) -> List[Segment]:
        """Get segments for a report instance"""
        cursor = self.conn.cursor(as_dict=True)
        cursor.execute("""
            SELECT SEGMENT_NUMBER, START_PAGE_NUMBER, NUMBER_OF_PAGES
            FROM REPORT_INSTANCE_SEGMENT
            WHERE DOMAIN_ID = %s AND REPORT_SPECIES_ID = %s
                  AND AS_OF_TIMESTAMP = %s
            ORDER BY SEGMENT_NUMBER
        """, (instance.domain_id, instance.report_species_id, instance.as_of_timestamp))

        return [
            Segment(
                segment_number=row['SEGMENT_NUMBER'],
                start_page_number=row['START_PAGE_NUMBER'],
                number_of_pages=row['NUMBER_OF_PAGES']
            )
            for row in cursor.fetchall()
        ]

    def get_sections(self, report_species_id: int) -> List[Section]:
        """Get all sections for a report species"""
        cursor = self.conn.cursor(as_dict=True)
        cursor.execute("""
            SELECT SECTION_ID, NAME
            FROM SECTION
            WHERE DOMAIN_ID = %s AND REPORT_SPECIES_ID = %s
            ORDER BY SECTION_ID
        """, (self.config.domain_id, report_species_id))

        return [
            Section(
                section_id=row['SECTION_ID'],
                name=row['NAME'].strip() if row['NAME'] else ''
            )
            for row in cursor.fetchall()
        ]

    def get_field_definitions(self, structure_def_id: int,
                             indexed_only: bool = False,
                             significant_only: bool = False) -> List[FieldDef]:
        """Get field definitions for a structure"""
        cursor = self.conn.cursor(as_dict=True)

        where_clause = "WHERE STRUCTURE_DEF_ID = %s"
        params = [structure_def_id]

        if indexed_only:
            where_clause += " AND IS_INDEXED = 1"
        if significant_only:
            where_clause += " AND IS_SIGNIFICANT = 1"

        cursor.execute(f"""
            SELECT STRUCTURE_DEF_ID, LINE_ID, FIELD_ID, NAME,
                   START_COLUMN, END_COLUMN, IS_INDEXED, IS_SIGNIFICANT
            FROM FIELD
            {where_clause}
            ORDER BY LINE_ID, FIELD_ID
        """, params)

        return [
            FieldDef(
                structure_def_id=row['STRUCTURE_DEF_ID'],
                line_id=row['LINE_ID'],
                field_id=row['FIELD_ID'],
                name=row['NAME'].strip() if row['NAME'] else '',
                start_column=row['START_COLUMN'],
                end_column=row['END_COLUMN'],
                is_indexed=row['IS_INDEXED'] == 1,
                is_significant=row['IS_SIGNIFICANT'] == 1
            )
            for row in cursor.fetchall()
        ]

    def get_line_definitions(self, structure_def_id: int) -> List[LineDef]:
        """Get line definitions for a structure"""
        cursor = self.conn.cursor(as_dict=True)
        cursor.execute("""
            SELECT STRUCTURE_DEF_ID, LINE_ID, NAME, TEMPLATE
            FROM LINE
            WHERE STRUCTURE_DEF_ID = %s
            ORDER BY LINE_ID
        """, (structure_def_id,))

        return [
            LineDef(
                structure_def_id=row['STRUCTURE_DEF_ID'],
                line_id=row['LINE_ID'],
                name=row['NAME'].strip() if row['NAME'] else '',
                template=row['TEMPLATE'].strip() if row['TEMPLATE'] else ''
            )
            for row in cursor.fetchall()
        ]


# ============================================================================
# MAP File Parser
# ============================================================================

class MapFileParser:
    """Parser for binary MAP files"""

    ME_MARKER = b'\x2a\x00\x2a\x00\x4d\x00\x45\x00'  # **ME in UTF-16LE

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.data = None
        self.me_positions: List[int] = []
        self.segments: List[MapSegmentInfo] = []
        self.lookup_table: List[Dict[str, int]] = []

    def load(self) -> bool:
        """Load MAP file into memory"""
        try:
            with open(self.filepath, 'rb') as f:
                self.data = f.read()
            return True
        except Exception as e:
            print(f"Error loading MAP file: {e}")
            return False

    def parse_header(self) -> Optional[MapFileInfo]:
        """Parse MAP file header"""
        if not self.data or len(self.data) < 90:
            return None

        # Check signature
        signature = self.data[:12].decode('utf-16le', errors='ignore')
        if signature != 'MAPHDR':
            return None

        # Parse header fields
        segment_count = struct.unpack('<H', self.data[18:20])[0]

        # Date string at offset 0x20
        date_string = self.data[0x20:0x34].decode('utf-16le', errors='ignore').strip('\x00')

        return MapFileInfo(
            filename=os.path.basename(self.filepath),
            segment_count=segment_count,
            date_string=date_string
        )

    def find_me_markers(self) -> List[int]:
        """Find all **ME marker positions"""
        if self.me_positions:
            return self.me_positions

        positions = []
        pos = 0
        while True:
            pos = self.data.find(self.ME_MARKER, pos)
            if pos == -1:
                break
            positions.append(pos)
            pos += 8  # Move past marker
        self.me_positions = positions
        return positions

    def parse_segment_0_lookup_table(self) -> List[Dict[str, int]]:
        """
        Parse Segment 0 lookup/directory table.

        Segment 0 contains entries mapping (LINE_ID, FIELD_ID) to segment numbers.
        Entry format: [SEG_NUM:1][LINE_ID:1][FIELD_ID:1][FLAGS:1] = 4 bytes
        """
        if not self.me_positions:
            self.find_me_markers()

        if len(self.me_positions) < 2:
            return []

        seg0_start = self.me_positions[0]
        seg1_start = self.me_positions[1]

        # Lookup table data starts approximately at offset 0x11C from file start
        # (after segment 0 header and metadata)
        lookup_start = seg0_start + 0xC2  # Approximately 0x11C - 0x5A = 0xC2 from **ME

        entries = []
        offset = lookup_start

        while offset < seg1_start - 4:
            # Check for **ME marker (end of segment 0)
            if self.data[offset:offset+8] == self.ME_MARKER:
                break

            b = self.data[offset:offset+4]
            seg_num = b[0]
            line_id = b[1]
            field_id = b[2]
            flags = b[3]

            # Filter for valid entries (reasonable LINE_ID values)
            if seg_num <= 20 and line_id <= 30 and line_id > 0:
                entries.append({
                    'segment': seg_num,
                    'line_id': line_id,
                    'field_id': field_id,
                    'flags': flags
                })

            offset += 4

        self.lookup_table = entries
        return entries

    def parse_segments(self) -> List[MapSegmentInfo]:
        """Parse all binary segments with full metadata"""
        if not self.me_positions:
            self.find_me_markers()

        segments = []

        for i, me_pos in enumerate(self.me_positions):
            next_pos = self.me_positions[i + 1] if i + 1 < len(self.me_positions) else len(self.data)

            if me_pos + 48 > len(self.data):
                continue

            # Parse segment header (offset +8 from **ME marker)
            header_off = me_pos + 8
            const = struct.unpack('<I', self.data[header_off:header_off+4])[0]
            seg_index = struct.unpack('<I', self.data[header_off+4:header_off+8])[0]
            next_offset = struct.unpack('<I', self.data[header_off+8:header_off+12])[0]

            # Parse segment metadata (offset +24 from **ME marker)
            meta_off = me_pos + 24

            if i == 0:
                # Segment 0 is the lookup/directory - different structure
                segment = MapSegmentInfo(
                    index=seg_index,
                    offset=me_pos,
                    next_offset=next_offset,
                    size=next_pos - me_pos,
                    page_start=0,
                    line_id=0,
                    field_id=0,
                    field_width=0,
                    entry_count=0,
                    data_offset=me_pos + 0xC2  # Lookup table offset
                )
            else:
                # Segments 1+ contain index data for specific fields
                # Metadata structure at offset +24 from **ME:
                # +0:  page_start (2 bytes)
                # +2:  line_id (2 bytes)
                # +4:  unknown (2 bytes)
                # +6:  field_id (2 bytes)
                # +8:  unknown (2 bytes)
                # +10: field_width (2 bytes)
                # +12: unknown (2 bytes)
                # +14: entry_count (2 bytes)

                page_start = struct.unpack('<H', self.data[meta_off:meta_off+2])[0]
                line_id = struct.unpack('<H', self.data[meta_off+2:meta_off+4])[0]
                field_id = struct.unpack('<H', self.data[meta_off+6:meta_off+8])[0]
                field_width = struct.unpack('<H', self.data[meta_off+10:meta_off+12])[0]
                entry_count = struct.unpack('<H', self.data[meta_off+14:meta_off+16])[0]

                # Data offset is consistently 0xCD (205) bytes from **ME marker
                # This includes: **ME(8) + header(16) + metadata + padding
                data_offset = me_pos + 0xCD

                segment = MapSegmentInfo(
                    index=seg_index,
                    offset=me_pos,
                    next_offset=next_offset,
                    size=next_pos - me_pos,
                    page_start=page_start,
                    line_id=line_id,
                    field_id=field_id,
                    field_width=field_width,
                    entry_count=entry_count,
                    data_offset=data_offset
                )

            segments.append(segment)

        self.segments = segments
        return segments

    def find_segment_for_field(self, line_id: int, field_id: int) -> Optional[MapSegmentInfo]:
        """Find the segment that contains index data for a specific field"""
        if not self.segments:
            self.parse_segments()

        for seg in self.segments[1:]:  # Skip segment 0
            if seg.line_id == line_id and seg.field_id == field_id:
                return seg
        return None

    def read_index_entries(self, segment: MapSegmentInfo, max_entries: int = 100) -> List[IndexEntry]:
        """
        Read index entries from a segment.

        Entry format: [length:2][value:N][page:2][flags:3]
        where N = field_width and total entry size = 7 + field_width
        """
        if segment.field_width == 0 or segment.field_width > 100:
            return []  # Invalid or non-text segment

        entries = []
        entry_size = 7 + segment.field_width
        offset = segment.data_offset

        # Read entries directly from data_offset
        for i in range(max_entries):
            if offset + entry_size > segment.next_offset:
                break
            if offset + entry_size > len(self.data):
                break

            # Read entry: [length:2][text:N][page:2][flags:3]
            length = struct.unpack('<H', self.data[offset:offset+2])[0]

            # Validate length matches field_width
            if length != segment.field_width:
                # Entry format mismatch - this segment may have different structure
                # Try to find the correct start by searching for valid length
                found = False
                for probe in range(offset, min(offset + 50, segment.next_offset)):
                    probe_len = struct.unpack('<H', self.data[probe:probe+2])[0]
                    if probe_len == segment.field_width:
                        offset = probe
                        length = probe_len
                        found = True
                        break
                if not found:
                    break

            try:
                value = self.data[offset+2:offset+2+segment.field_width].decode('ascii', errors='replace').strip()
            except:
                value = ''

            page = struct.unpack('<H', self.data[offset+2+segment.field_width:offset+4+segment.field_width])[0]

            # Only add if the value looks like valid text (not binary garbage)
            if value and any(c.isalnum() for c in value[:5]):
                entries.append(IndexEntry(
                    value=value,
                    page_number=page,
                    raw_length=length
                ))

            offset += entry_size

        return entries

    def search_index(self, search_value: str, line_id: int, field_id: int) -> List[int]:
        """
        Search for a value in the MAP file index.

        Args:
            search_value: Value to search for
            line_id: LINE_ID from FIELD table
            field_id: FIELD_ID from FIELD table

        Returns: List of page numbers where value appears
        """
        segment = self.find_segment_for_field(line_id, field_id)
        if not segment:
            return []

        entries = self.read_index_entries(segment, max_entries=10000)
        pages = []

        for entry in entries:
            if entry.value == search_value or entry.value.startswith(search_value):
                pages.append(entry.page_number)

        return pages

    def get_all_indexed_values(self, line_id: int, field_id: int) -> List[Tuple[str, int]]:
        """
        Get all indexed values and their page numbers for a field.

        Returns: List of (value, page_number) tuples
        """
        segment = self.find_segment_for_field(line_id, field_id)
        if not segment:
            return []

        entries = self.read_index_entries(segment, max_entries=10000)
        return [(e.value, e.page_number) for e in entries]

    # Legacy method for backwards compatibility
    def parse_segments_legacy(self) -> List[Dict[str, Any]]:
        """Parse all binary segments (legacy format for backwards compatibility)"""
        segments = self.parse_segments()
        return [
            {
                'index': seg.index,
                'offset': seg.offset,
                'next_offset': seg.next_offset,
                'size': seg.size,
                'page_number': seg.page_start,
                'line_id': seg.line_id,
                'field_id': seg.field_id,
                'field_width': seg.field_width,
                'metadata': [seg.page_start, seg.line_id, 0, seg.field_id, 0, seg.field_width]
            }
            for seg in segments
        ]


# ============================================================================
# Spool File Handler
# ============================================================================

class SpoolFileHandler:
    """Handler for spool files with page indexing"""

    FORM_FEED = 0x0C
    ASA_NEW_PAGE = ord('1')

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.page_offsets: List[int] = []
        self.format_type: str = 'unknown'  # 'form_feed' or 'asa'
        self.file_size: int = 0

    def load(self) -> bool:
        """Load spool file and build page index"""
        try:
            self.file_size = os.path.getsize(self.filepath)
            return True
        except Exception as e:
            print(f"Error accessing spool file: {e}")
            return False

    def build_page_index(self) -> int:
        """Build index of page byte offsets, return page count"""
        self.page_offsets = [0]  # First page starts at offset 0

        with open(self.filepath, 'rb') as f:
            # Read first few bytes to detect format
            header = f.read(100)
            f.seek(0)

            # Check for form feed format
            if self.FORM_FEED in header:
                self.format_type = 'form_feed'
                self._build_form_feed_index(f)
            else:
                # Check for ASA format (first char of first line is '1')
                first_line = header.split(b'\n')[0]
                if first_line and first_line[0:1] == b'1':
                    self.format_type = 'asa'
                    self._build_asa_index(f)
                else:
                    # Default to form feed scan
                    self.format_type = 'form_feed'
                    self._build_form_feed_index(f)

        return len(self.page_offsets)

    def _build_form_feed_index(self, f):
        """Build index using form feed delimiters"""
        f.seek(0)
        data = f.read()

        pos = 0
        while True:
            pos = data.find(bytes([self.FORM_FEED]), pos)
            if pos == -1:
                break
            self.page_offsets.append(pos + 1)
            pos += 1

    def _build_asa_index(self, f):
        """Build index using ASA carriage control"""
        f.seek(0)
        offset = 0

        for line in f:
            if line and line[0:1] == b'1':
                if offset > 0:  # Skip first line which is already at offset 0
                    self.page_offsets.append(offset)
            offset += len(line)

    def get_page(self, page_number: int) -> Optional[bytes]:
        """Get content of a specific page (1-indexed)"""
        if page_number < 1 or page_number > len(self.page_offsets):
            return None

        start_offset = self.page_offsets[page_number - 1]

        if page_number < len(self.page_offsets):
            end_offset = self.page_offsets[page_number]
        else:
            end_offset = self.file_size

        with open(self.filepath, 'rb') as f:
            f.seek(start_offset)
            return f.read(end_offset - start_offset)

    def get_page_range(self, start_page: int, num_pages: int) -> Optional[bytes]:
        """Get content of a range of pages"""
        if start_page < 1 or start_page > len(self.page_offsets):
            return None

        end_page = min(start_page + num_pages - 1, len(self.page_offsets))

        start_offset = self.page_offsets[start_page - 1]

        if end_page < len(self.page_offsets):
            end_offset = self.page_offsets[end_page]
        else:
            end_offset = self.file_size

        with open(self.filepath, 'rb') as f:
            f.seek(start_offset)
            return f.read(end_offset - start_offset)


# ============================================================================
# Main Viewer Class
# ============================================================================

class IntelliSTORViewer:
    """Main viewer class combining all functionality"""

    def __init__(self, config: Config):
        self.config = config
        self.db: Optional[DatabaseAccess] = None

    def connect_db(self):
        """Connect to database"""
        self.db = DatabaseAccess(self.config)
        self.db.connect()

    def close(self):
        """Close connections"""
        if self.db:
            self.db.close()

    def show_report_info(self, report_name: str):
        """Show information about a report"""
        # Get report species ID
        species_id = self.db.get_report_species_id_by_name(report_name)
        if not species_id:
            print(f"Report '{report_name}' not found")
            return

        print(f"\n{'='*60}")
        print(f"Report: {report_name} (REPORT_SPECIES_ID: {species_id})")
        print('='*60)

        # Get latest instance
        instance = self.db.get_report_instance(species_id)
        if not instance:
            print("No instances found")
            return

        print(f"\nLatest Instance:")
        print(f"  AS_OF_TIMESTAMP: {instance.as_of_timestamp}")
        print(f"  STRUCTURE_DEF_ID: {instance.structure_def_id}")
        print(f"  RPT_FILE_SIZE: {instance.rpt_file_size_kb} KB")
        print(f"  MAP_FILE_SIZE: {instance.map_file_size_kb} KB")

        # Get MAP file
        map_filename = self.db.get_map_filename(instance)
        print(f"\nMAP File: {map_filename or 'Not found'}")

        # Get spool file
        spool_filename = self.db.get_spool_filename(instance)
        print(f"Spool File: {spool_filename or 'Not found'}")

        # Get segments
        segments = self.db.get_segments(instance)
        print(f"\nSegments ({len(segments)}):")
        for seg in segments[:10]:
            end_page = seg.start_page_number + seg.number_of_pages - 1
            print(f"  Segment {seg.segment_number}: pages {seg.start_page_number}-{end_page} ({seg.number_of_pages} pages)")
        if len(segments) > 10:
            print(f"  ... and {len(segments) - 10} more")

        # Get sections
        sections = self.db.get_sections(species_id)
        print(f"\nSections ({len(sections)}):")
        for sec in sections[:10]:
            print(f"  {sec.section_id}: {sec.name}")
        if len(sections) > 10:
            print(f"  ... and {len(sections) - 10} more")

        # Get field definitions
        indexed_fields = self.db.get_field_definitions(
            instance.structure_def_id, indexed_only=True)
        print(f"\nIndexed Fields ({len(indexed_fields)}):")
        for f in indexed_fields[:10]:
            print(f"  LINE {f.line_id}, FIELD {f.field_id}: {f.name} (cols {f.start_column}-{f.end_column})")

        significant_fields = self.db.get_field_definitions(
            instance.structure_def_id, significant_only=True)
        print(f"\nSignificant Fields (section markers) ({len(significant_fields)}):")
        for f in significant_fields[:10]:
            print(f"  LINE {f.line_id}, FIELD {f.field_id}: {f.name} (cols {f.start_column}-{f.end_column})")

    def analyze_map_file(self, map_filename: str, show_entries: bool = False):
        """Analyze a MAP file"""
        filepath = os.path.join(self.config.map_file_dir, map_filename)

        if not os.path.exists(filepath):
            print(f"MAP file not found: {filepath}")
            return

        parser = MapFileParser(filepath)
        if not parser.load():
            return

        info = parser.parse_header()
        if not info:
            print("Failed to parse MAP file header")
            return

        print(f"\n{'='*60}")
        print(f"MAP File: {info.filename}")
        print('='*60)
        print(f"Date: {info.date_string}")
        print(f"Segment Count (from header): {info.segment_count}")

        # Parse segments with new detailed metadata
        segments = parser.parse_segments()
        print(f"\nBinary Segments ({len(segments)}):")
        print(f"{'Seg':>3} {'Offset':>8} {'LINE_ID':>8} {'FIELD_ID':>9} {'WIDTH':>6} {'ENTRIES':>8}")
        print("-" * 50)

        for seg in segments:
            if seg.index == 0:
                print(f"{seg.index:3d} {seg.offset:8d}   (Lookup/Directory Segment)")
            else:
                print(f"{seg.index:3d} {seg.offset:8d} {seg.line_id:8d} {seg.field_id:9d} {seg.field_width:6d} {seg.entry_count:8d}")

        # Parse and show lookup table from Segment 0
        lookup = parser.parse_segment_0_lookup_table()
        if lookup:
            print(f"\nSegment 0 Lookup Table ({len(lookup)} entries):")
            print(f"{'SEG':>4} {'LINE_ID':>8} {'FIELD_ID':>9} {'FLAGS':>6}")
            print("-" * 30)
            for entry in lookup[:20]:
                print(f"{entry['segment']:4d} {entry['line_id']:8d} {entry['field_id']:9d} {entry['flags']:6d}")
            if len(lookup) > 20:
                print(f"  ... and {len(lookup) - 20} more entries")

        # Show sample index entries for each segment with data
        if show_entries:
            print(f"\n{'='*60}")
            print("Sample Index Entries by Segment")
            print('='*60)

            for seg in segments[1:]:  # Skip segment 0
                if seg.field_width > 0 and seg.field_width <= 60:
                    entries = parser.read_index_entries(seg, max_entries=5)
                    if entries:
                        print(f"\nSegment {seg.index} (LINE {seg.line_id}, FIELD {seg.field_id}, width={seg.field_width}):")
                        for entry in entries:
                            print(f"  '{entry.value}' → PAGE {entry.page_number}")

    def search_map_index(self, map_filename: str, search_value: str,
                         line_id: int, field_id: int):
        """Search for a value in a MAP file index"""
        filepath = os.path.join(self.config.map_file_dir, map_filename)

        if not os.path.exists(filepath):
            print(f"MAP file not found: {filepath}")
            return

        parser = MapFileParser(filepath)
        if not parser.load():
            return

        print(f"\n{'='*60}")
        print(f"Searching MAP File: {map_filename}")
        print('='*60)
        print(f"Search value: '{search_value}'")
        print(f"LINE_ID: {line_id}, FIELD_ID: {field_id}")

        # Find the segment
        parser.parse_segments()
        segment = parser.find_segment_for_field(line_id, field_id)

        if not segment:
            print(f"\nNo segment found for LINE_ID={line_id}, FIELD_ID={field_id}")
            print("\nAvailable segments:")
            for seg in parser.segments[1:]:
                print(f"  Segment {seg.index}: LINE_ID={seg.line_id}, FIELD_ID={seg.field_id}")
            return

        print(f"\nFound segment {segment.index} with field_width={segment.field_width}")

        # Search
        pages = parser.search_index(search_value, line_id, field_id)

        if pages:
            print(f"\nSearch Results ({len(pages)} matches):")
            for page in pages[:20]:
                print(f"  PAGE {page}")
            if len(pages) > 20:
                print(f"  ... and {len(pages) - 20} more pages")
        else:
            print("\nNo matches found.")

            # Show some sample values from this segment
            entries = parser.read_index_entries(segment, max_entries=10)
            if entries:
                print(f"\nSample values in this segment:")
                for entry in entries:
                    print(f"  '{entry.value}' → PAGE {entry.page_number}")

    def analyze_spool_file(self, spool_filepath: str):
        """Analyze a spool file"""
        if not os.path.exists(spool_filepath):
            print(f"Spool file not found: {spool_filepath}")
            return

        handler = SpoolFileHandler(spool_filepath)
        if not handler.load():
            return

        print(f"\n{'='*60}")
        print(f"Spool File: {os.path.basename(spool_filepath)}")
        print('='*60)
        print(f"File Size: {handler.file_size:,} bytes")

        page_count = handler.build_page_index()
        print(f"Format: {handler.format_type}")
        print(f"Page Count: {page_count}")

        if handler.page_offsets:
            print(f"\nPage Offsets (first 10):")
            for i, offset in enumerate(handler.page_offsets[:10], 1):
                print(f"  Page {i}: byte offset {offset:,}")

        # Show first page preview
        page1 = handler.get_page(1)
        if page1:
            print(f"\nPage 1 Preview (first 500 bytes):")
            preview = page1[:500].decode('utf-8', errors='replace')
            for line in preview.split('\n')[:10]:
                print(f"  {line}")


# ============================================================================
# Command Line Interface
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='IntelliSTOR Report Viewer - Test Implementation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --report CDU100P
  %(prog)s --map 25001002.MAP
  %(prog)s --map 25001002.MAP --show-entries
  %(prog)s --map 25001002.MAP --search EP24123109039499 --line 5 --field 3
  %(prog)s --spool Report_TXT_Viewer/CDU100P.txt
        """
    )

    parser.add_argument('--report', help='Show report information by name')
    parser.add_argument('--map', help='Analyze MAP file')
    parser.add_argument('--show-entries', action='store_true', help='Show sample index entries')
    parser.add_argument('--search', help='Search for value in MAP file index')
    parser.add_argument('--line', type=int, help='LINE_ID for search')
    parser.add_argument('--field', type=int, help='FIELD_ID for search')
    parser.add_argument('--spool', help='Analyze spool file')
    parser.add_argument('--db-server', default='localhost', help='Database server')
    parser.add_argument('--db-name', default='iSTSGUAT', help='Database name')
    parser.add_argument('--map-dir', default='/Volumes/X9Pro/OCBC/250_MapFiles',
                       help='MAP files directory')

    args = parser.parse_args()

    config = Config(
        db_server=args.db_server,
        db_name=args.db_name,
        map_file_dir=args.map_dir
    )

    viewer = IntelliSTORViewer(config)

    try:
        if args.report:
            if not HAS_PYMSSQL:
                print("Error: pymssql required for --report option")
                sys.exit(1)
            viewer.connect_db()
            viewer.show_report_info(args.report)

        elif args.map:
            if args.search and args.line and args.field:
                # Search mode
                viewer.search_map_index(args.map, args.search, args.line, args.field)
            else:
                # Analysis mode
                viewer.analyze_map_file(args.map, show_entries=args.show_entries)

        elif args.spool:
            viewer.analyze_spool_file(args.spool)

        else:
            # Default: show sample analysis
            print("IntelliSTOR Viewer - Sample Analysis")
            print("="*60)

            # Analyze sample spool files
            sample_files = [
                'Report_TXT_Viewer/CDU100P.txt',
                'Report_TXT_Viewer/FRX16.txt'
            ]

            base_dir = '/Volumes/acasis/projects/python/ocbc/IntelliSTOR_Migration'
            for filename in sample_files:
                filepath = os.path.join(base_dir, filename)
                if os.path.exists(filepath):
                    viewer.analyze_spool_file(filepath)

    finally:
        viewer.close()


if __name__ == '__main__':
    main()
