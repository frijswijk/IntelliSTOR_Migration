#!/usr/bin/env python3
"""
IntelliSTOR Report Viewer - Test Implementation

This program demonstrates the complete workflow for:
1. Section segregation (IS_SIGNIFICANT fields with permissions)
2. Index search (IS_INDEXED fields) using binary MAP file index
3. Fast page access in large spool files (Form Feed and ASA formats)

MAP File Index Structure:
- Segment 0: Lookup/Directory table + sections/branch index (IS_SIGNIFICANT fields)
- Segments 1-N: Index entries for each indexed field (IS_INDEXED fields)
- Two entry formats (both have total size = 7 + field_width):
  - Small files: [length:2][value:N][page:2][flags:3] — page is direct uint16 page number
  - Large files: [length:2][value:N][u32_index:4][last:1] — u32 is line occurrence index

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
    """Single index entry from MAP file

    Entry format varies by MAP file:
    - Small files: [length:2][value:N][page:2][flags:3] — page is uint16 page number
    - Large files: [length:2][value:N][u32_index:4][last:1] — u32 is line occurrence index

    In both cases, total entry_size = 7 + field_width.
    For large files: (u32_index - 1) / 2 = 0-based index into LINE occurrences in spool.
    """
    value: str
    page_number: int          # For small files: direct page; for large files: 0 (unresolved)
    raw_length: int
    raw_trailing: bytes = field(default=b'')  # The 5 bytes after the value text
    u32_index: int = 0        # For large files: the 4-byte index value
    entry_format: str = 'page'  # 'page' (small files) or 'u32_index' (large files)


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

        Segment 0 contains:
        1. A lookup table mapping (LINE_ID, FIELD_ID) to segment numbers
        2. The sections/branch index data (for IS_SIGNIFICANT fields)

        Lookup table entry format: [SEG_NUM:1][LINE_ID:1][FIELD_ID:1][FLAGS:1] = 4 bytes
        The table is small (one entry per indexed field) and is followed by the
        much larger sections/branch index data.
        """
        if not self.me_positions:
            self.find_me_markers()

        if len(self.me_positions) < 2:
            return []

        seg0_start = self.me_positions[0]
        seg1_start = self.me_positions[1]

        # Lookup table data starts approximately at offset 0xC2 from **ME marker
        lookup_start = seg0_start + 0xC2

        entries = []
        offset = lookup_start
        consecutive_invalid = 0

        while offset < seg1_start - 4:
            # Check for **ME marker (end of segment 0)
            if self.data[offset:offset+8] == self.ME_MARKER:
                break

            b = self.data[offset:offset+4]
            seg_num = b[0]
            line_id = b[1]
            field_id = b[2]
            flags = b[3]

            # Valid lookup entries have small segment numbers and non-zero line/field IDs.
            # LINE_ID is stored as 1 byte here (max 255), which covers most indexed fields.
            # Stop scanning after consecutive invalid entries (we've hit the branch index data).
            if seg_num <= 20 and 0 < line_id <= 255 and field_id > 0:
                entries.append({
                    'segment': seg_num,
                    'line_id': line_id,
                    'field_id': field_id,
                    'flags': flags
                })
                consecutive_invalid = 0
            else:
                consecutive_invalid += 1
                if consecutive_invalid >= 4:
                    # We've likely passed the lookup table into binary data
                    break

            offset += 4

        self.lookup_table = entries
        return entries

    def _find_data_offset(self, me_pos: int, next_pos: int, field_width: int) -> int:
        """
        Dynamically find the data offset within a segment by searching for
        the first entry whose 2-byte length field equals field_width.

        The data offset varies between MAP files (e.g., 0xCD for small files,
        0xCF for large files). We search in the range [me_pos+0xC0, me_pos+0xE0]
        which covers observed variation.
        """
        if field_width == 0 or field_width > 100:
            return me_pos + 0xCD  # Fallback for invalid/unknown segments

        search_start = me_pos + 0xC0
        search_end = min(me_pos + 0xE0, next_pos - 2)

        for probe in range(search_start, search_end):
            if probe + 2 > len(self.data):
                break
            probe_len = struct.unpack('<H', self.data[probe:probe+2])[0]
            if probe_len == field_width:
                # Verify: the text following should look like ASCII data
                if probe + 2 + field_width <= len(self.data):
                    text = self.data[probe+2:probe+2+field_width]
                    printable = sum(1 for b in text if 32 <= b < 127)
                    if printable > field_width * 0.5:  # >50% printable chars
                        return probe

        # Fallback to original hardcoded offset
        return me_pos + 0xCD

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

                # Dynamically find data_offset by searching for the first entry
                # whose length field == field_width. The offset varies between
                # MAP files (observed: 0xCD for small, 0xCF for large files).
                data_offset = self._find_data_offset(me_pos, next_pos, field_width)

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

    def read_index_entries(self, segment: MapSegmentInfo, max_entries: int = 0) -> List[IndexEntry]:
        """
        Read index entries from a segment.

        Two entry formats exist (both have total entry_size = 7 + field_width):
        - Small files: [length:2][value:N][page:2][flags:3] — page is uint16
        - Large files: [length:2][value:N][u32_index:4][last:1] — u32 is line occurrence index

        Format detection: read a batch of entries and check if all uint16 values
        at the page position are odd. If so, it's the u32_index format.

        Args:
            segment: The segment to read entries from
            max_entries: Maximum entries to read (0 = all entries in segment)
        """
        if segment.field_width == 0 or segment.field_width > 100:
            return []  # Invalid or non-text segment

        entries = []
        entry_size = 7 + segment.field_width
        offset = segment.data_offset
        end_boundary = min(segment.offset + segment.size, len(self.data))

        # Calculate max possible entries in this segment
        available_bytes = end_boundary - offset
        max_possible = available_bytes // entry_size if entry_size > 0 else 0

        if max_entries > 0:
            limit = min(max_entries, max_possible)
        else:
            limit = max_possible

        # First pass: read raw entries to detect format
        raw_entries = []
        probe_offset = offset
        probe_count = min(100, limit)  # Sample first 100 entries for format detection

        for _ in range(probe_count):
            if probe_offset + entry_size > end_boundary:
                break

            length = struct.unpack('<H', self.data[probe_offset:probe_offset+2])[0]
            if length != segment.field_width:
                break  # End of valid entries

            text_start = probe_offset + 2
            text_end = text_start + segment.field_width
            trailing_start = text_end
            trailing_end = trailing_start + 5  # 5 bytes after text

            try:
                value = self.data[text_start:text_end].decode('ascii', errors='replace').strip()
            except Exception:
                value = ''

            trailing = self.data[trailing_start:trailing_end]
            raw_entries.append((value, length, trailing, probe_offset))
            probe_offset += entry_size

        if not raw_entries:
            return []

        # Detect format: check if uint16 at trailing[0:2] are ALL odd
        # Small files have page numbers that are typically small and can be even.
        # Large files have u32 values where the low uint16 is always odd.
        odd_count = 0
        for _, _, trailing, _ in raw_entries:
            if len(trailing) >= 2:
                u16 = struct.unpack('<H', trailing[0:2])[0]
                if u16 % 2 == 1:
                    odd_count += 1

        # If ALL sampled uint16 values are odd AND we have a meaningful sample,
        # this is the u32_index format
        is_u32_format = (odd_count == len(raw_entries) and len(raw_entries) >= 3)

        # Now read all entries with the detected format
        read_offset = offset
        for i in range(limit):
            if read_offset + entry_size > end_boundary:
                break

            length = struct.unpack('<H', self.data[read_offset:read_offset+2])[0]
            if length != segment.field_width:
                break  # End of valid entries

            text_start = read_offset + 2
            text_end = text_start + segment.field_width
            trailing_start = text_end

            try:
                value = self.data[text_start:text_end].decode('ascii', errors='replace').strip()
            except Exception:
                value = ''

            trailing = self.data[trailing_start:trailing_start+5]

            if not value or not any(c.isalnum() for c in value[:5]):
                read_offset += entry_size
                continue

            if is_u32_format:
                # Large file format: [u32_index:4][last_byte:1]
                u32_val = struct.unpack('<I', trailing[0:4])[0]
                last_byte = trailing[4] if len(trailing) >= 5 else 0
                entries.append(IndexEntry(
                    value=value,
                    page_number=0,  # Cannot resolve without spool file
                    raw_length=length,
                    raw_trailing=trailing,
                    u32_index=u32_val,
                    entry_format='u32_index'
                ))
            else:
                # Small file format: [page:2][flags:3]
                page = struct.unpack('<H', trailing[0:2])[0]
                entries.append(IndexEntry(
                    value=value,
                    page_number=page,
                    raw_length=length,
                    raw_trailing=trailing,
                    u32_index=0,
                    entry_format='page'
                ))

            read_offset += entry_size

        return entries

    def search_index(self, search_value: str, line_id: int, field_id: int) -> List[IndexEntry]:
        """
        Search for a value in the MAP file index.

        Args:
            search_value: Value to search for
            line_id: LINE_ID from FIELD table
            field_id: FIELD_ID from FIELD table

        Returns: List of matching IndexEntry objects
        """
        segment = self.find_segment_for_field(line_id, field_id)
        if not segment:
            return []

        entries = self.read_index_entries(segment)
        matches = []

        for entry in entries:
            if entry.value == search_value or entry.value.startswith(search_value):
                matches.append(entry)

        return matches

    def get_all_indexed_values(self, line_id: int, field_id: int) -> List[IndexEntry]:
        """
        Get all indexed values for a field.

        Returns: List of IndexEntry objects
        """
        segment = self.find_segment_for_field(line_id, field_id)
        if not segment:
            return []

        return self.read_index_entries(segment)

    def get_unique_indexed_values(self, line_id: int, field_id: int) -> List[Tuple[str, int]]:
        """
        Get unique indexed values with occurrence counts.

        Returns: List of (value, count) tuples sorted by value
        """
        entries = self.get_all_indexed_values(line_id, field_id)
        counts: Dict[str, int] = {}
        for entry in entries:
            counts[entry.value] = counts.get(entry.value, 0) + 1
        return sorted(counts.items())

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
            print("Index Entries by Segment")
            print('='*60)

            for seg in segments[1:]:  # Skip segment 0
                if seg.field_width > 0 and seg.field_width <= 60:
                    entries = parser.read_index_entries(seg, max_entries=20)
                    if entries:
                        fmt = entries[0].entry_format
                        total = parser.read_index_entries(seg)
                        total_count = len(total)
                        print(f"\nSegment {seg.index} (LINE {seg.line_id}, FIELD {seg.field_id}, "
                              f"width={seg.field_width}, format={fmt}, total={total_count:,} entries):")

                        if fmt == 'u32_index':
                            # Show unique values with counts
                            counts: Dict[str, int] = {}
                            for e in total:
                                counts[e.value] = counts.get(e.value, 0) + 1
                            unique = sorted(counts.items())
                            print(f"  Unique values: {len(unique)}")
                            for val, cnt in unique[:20]:
                                print(f"  '{val}' × {cnt}")
                            if len(unique) > 20:
                                print(f"  ... and {len(unique) - 20} more unique values")
                        else:
                            for entry in entries:
                                print(f"  '{entry.value}' -> PAGE {entry.page_number}")

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
        matches = parser.search_index(search_value, line_id, field_id)

        if matches:
            fmt = matches[0].entry_format
            print(f"Entry format: {fmt}")
            print(f"\nSearch Results ({len(matches)} matches):")

            if fmt == 'u32_index':
                # u32_index format: show the index values
                for entry in matches[:30]:
                    line_occ = (entry.u32_index - 1) // 2
                    print(f"  '{entry.value}' -> line_occurrence={line_occ} (u32={entry.u32_index})")
                if len(matches) > 30:
                    print(f"  ... and {len(matches) - 30} more matches")
                print(f"\nNote: u32_index values represent LINE {line_id} occurrence "
                      f"indices in the spool file.")
                print(f"Formula: (u32_index - 1) / 2 = 0-based line occurrence number")
            else:
                # Page format: show page numbers directly
                for entry in matches[:30]:
                    print(f"  '{entry.value}' -> PAGE {entry.page_number}")
                if len(matches) > 30:
                    print(f"  ... and {len(matches) - 30} more pages")
        else:
            print("\nNo matches found.")

            # Show some sample values from this segment
            entries = parser.read_index_entries(segment, max_entries=10)
            if entries:
                fmt = entries[0].entry_format if entries else 'unknown'
                print(f"\nSample values in this segment (format={fmt}):")
                for entry in entries:
                    if entry.entry_format == 'u32_index':
                        print(f"  '{entry.value}' (u32={entry.u32_index})")
                    else:
                        print(f"  '{entry.value}' -> PAGE {entry.page_number}")

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
