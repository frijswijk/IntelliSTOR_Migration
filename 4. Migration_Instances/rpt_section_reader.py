#!/usr/bin/env python3
"""
rpt_section_reader.py - Extract SECTIONHDR from IntelliSTOR .RPT files

Reads the SECTIONHDR structure from RPT files without decompressing page data.
Returns (SECTION_ID, START_PAGE, PAGE_COUNT) triplets.

RPT File Layout:
  [0x000] RPTFILEHDR    - "RPTFILEHDR\t{domain}:{species}\t{timestamp}"
  [0x0F0] RPTINSTHDR    - Instance metadata
  [0x1D0] Table Directory (3 rows x 12 bytes):
          Row 0 (0x1D0): type=0x0102  count=page_count    offset → PAGETBLHDR
          Row 1 (0x1E0): type=0x0101  count=section_count  offset → SECTIONHDR
          Row 2 (0x1F0): type=0x0103  count=binary_count   offset → BPAGETBLHDR
  [0x200] COMPRESSED DATA - per-page zlib streams (text + interleaved binary objects)
  [...]   SECTIONHDR    - section triplets (SECTION_ID, START_PAGE, PAGE_COUNT)
  [...]   PAGETBLHDR    - 24-byte entries per text page
  [...]   BPAGETBLHDR   - 16-byte entries per binary object (PDF/AFP, if present)
"""

import struct
import os
import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class RptHeader:
    """Parsed RPT file header metadata."""
    domain_id: int
    report_species_id: int
    timestamp: str
    page_count: int
    section_count: int
    section_data_offset: int
    page_table_offset: int
    binary_object_count: int = 0  # Table Directory Row 2 (0x1F4): BPAGETBLHDR entry count


@dataclass
class SectionEntry:
    """One SECTIONHDR triplet."""
    section_id: int
    start_page: int
    page_count: int


def parse_rpt_header(data: bytes) -> Optional[RptHeader]:
    """
    Parse RPT file header to extract metadata and table directory offsets.

    Args:
        data: First ~512 bytes of the RPT file (minimum needed)

    Returns:
        RptHeader with metadata, or None if not a valid RPT file
    """
    # Check RPTFILEHDR signature
    if not data[:10] == b'RPTFILEHDR':
        return None

    # Parse header line: "RPTFILEHDR\t{domain}:{species}\t{timestamp}"
    # Find the end of the header line (terminated by 0x1A or null)
    header_end = data.find(b'\x1a')
    if header_end == -1:
        header_end = data.find(b'\x00')
    if header_end == -1:
        header_end = 192  # fallback

    header_line = data[:header_end].decode('ascii', errors='replace')
    parts = header_line.split('\t')

    domain_id = 0
    species_id = 0
    timestamp = ''

    if len(parts) >= 2:
        # Parse "0001:1346" -> domain=1, species=1346
        id_part = parts[1]
        if ':' in id_part:
            d, s = id_part.split(':', 1)
            try:
                domain_id = int(d)
                species_id = int(s)
            except ValueError:
                pass

    if len(parts) >= 3:
        timestamp = parts[2].strip()

    # Table Directory at 0x1D0 — three 12-byte rows:
    #   Row 0 (0x1D0): type=0x0102 | 0x1D4: page_count | 0x1D8: page_table_data_offset
    #   Row 1 (0x1E0): type=0x0101 | 0x1E4: section_count | 0x1E8: compressed_data_end
    #   Row 2 (0x1F0): type=0x0103 | 0x1F4: binary_object_count | 0x1F8: binary_table_offset
    page_count = 0
    section_count = 0
    section_data_offset = 0
    page_table_offset = 0
    binary_object_count = 0

    if len(data) >= 0x1F0:
        page_count = struct.unpack_from('<I', data, 0x1D4)[0]
        section_count = struct.unpack_from('<I', data, 0x1E4)[0]
        # These offsets point to related structures but not directly to SECTIONHDR marker
        # SECTIONHDR is found by scanning from compressed_data_end area
        page_table_data_offset = struct.unpack_from('<I', data, 0x1D8)[0]
        compressed_data_end = struct.unpack_from('<I', data, 0x1E8)[0]
        # SECTIONHDR marker is near compressed_data_end (within ~1KB after it)
        section_data_offset = compressed_data_end  # approximate; actual scan in read_sectionhdr

    # Row 2: binary object count (PDF/AFP embedded documents)
    if len(data) >= 0x200:
        binary_object_count = struct.unpack_from('<I', data, 0x1F4)[0]

    return RptHeader(
        domain_id=domain_id,
        report_species_id=species_id,
        timestamp=timestamp,
        page_count=page_count,
        section_count=section_count,
        section_data_offset=section_data_offset,
        page_table_offset=page_table_offset,
        binary_object_count=binary_object_count
    )


def read_sectionhdr(filepath: str) -> Tuple[Optional[RptHeader], List[SectionEntry]]:
    """
    Read SECTIONHDR from an RPT file.

    Extracts section-to-page mapping without decompressing any page data.

    Args:
        filepath: Path to .RPT file

    Returns:
        Tuple of (RptHeader, list of SectionEntry), or (None, []) on error
    """
    file_size = os.path.getsize(filepath)
    sections = []

    with open(filepath, 'rb') as f:
        # Read header (first 512 bytes)
        header_data = f.read(0x200)
        if len(header_data) < 0x200:
            # Small file — read what we can
            header_data = header_data

        header = parse_rpt_header(header_data)
        if header is None:
            return None, []

        # Strategy 1: Targeted scan near compressed_data_end offset
        # SECTIONHDR marker is typically within ~1KB after the compressed data end offset
        if header.section_data_offset > 0:
            scan_start = max(0, header.section_data_offset - 16)
            scan_len = min(4096, file_size - scan_start)
            f.seek(scan_start)
            region = f.read(scan_len)
            marker_pos = region.find(b'SECTIONHDR')
            if marker_pos != -1:
                abs_pos = scan_start + marker_pos
                data_start = marker_pos + 13  # skip "SECTIONHDR\x00\x00\x00"
                # Read section_count triplets
                count = header.section_count if header.section_count > 0 else 1000
                needed = count * 12
                if data_start + needed <= len(region):
                    triplet_data = region[data_start:data_start + needed]
                else:
                    # Re-read from file
                    f.seek(abs_pos + 13)
                    triplet_data = f.read(needed)
                actual = min(len(triplet_data) // 12, count)
                for i in range(actual):
                    offset = i * 12
                    sid, sp, pc = struct.unpack_from('<III', triplet_data, offset)
                    if sp >= 1 and pc >= 1:
                        sections.append(SectionEntry(section_id=sid, start_page=sp, page_count=pc))
                    elif sid == 0 and sp == 0 and pc == 0:
                        break  # all-zero triplet = end of valid data
                if sections:
                    header.section_count = len(sections)
                    return header, sections

        # Strategy 2: Full file scan for SECTIONHDR marker (fallback)
        f.seek(0)
        full_data = f.read()
        marker_pos = full_data.find(b'SECTIONHDR')
        if marker_pos == -1:
            return header, []

        data_start = marker_pos + 13
        enddata_pos = full_data.find(b'ENDDATA', data_start)
        if enddata_pos == -1:
            section_bytes = full_data[data_start:]
        else:
            section_bytes = full_data[data_start:enddata_pos]

        num_triplets = len(section_bytes) // 12
        for i in range(num_triplets):
            offset = i * 12
            if offset + 12 > len(section_bytes):
                break
            sid, sp, pc = struct.unpack_from('<III', section_bytes, offset)
            if sp >= 1 and pc >= 1:
                sections.append(SectionEntry(section_id=sid, start_page=sp, page_count=pc))
        header.section_count = len(sections)

    return header, sections


def format_segments(sections: List[SectionEntry]) -> str:
    """
    Format section entries as pipe-separated string for CSV output.

    Format: section_id#start_page#page_count|section_id#start_page#page_count|...

    Args:
        sections: List of SectionEntry objects

    Returns:
        Formatted string, or empty string if no sections
    """
    if not sections:
        return ''
    return '|'.join(
        f'{s.section_id}#{s.start_page}#{s.page_count}'
        for s in sections
    )


# ============================================================================
# CLI: standalone testing
# ============================================================================

def main():
    """CLI entry point for testing RPT section extraction."""
    if len(sys.argv) < 2:
        print("Usage: python rpt_section_reader.py <file.RPT> [file2.RPT ...]")
        print("       python rpt_section_reader.py --scan <directory>")
        sys.exit(1)

    if sys.argv[1] == '--scan':
        # Scan directory for all RPT files
        if len(sys.argv) < 3:
            print("Usage: python rpt_section_reader.py --scan <directory>")
            sys.exit(1)
        scan_dir = sys.argv[2]
        rpt_files = []
        for root, dirs, files in os.walk(scan_dir):
            for fname in files:
                if fname.upper().endswith('.RPT'):
                    rpt_files.append(os.path.join(root, fname))
        if not rpt_files:
            print(f"No .RPT files found in {scan_dir}")
            sys.exit(0)
        print(f"Found {len(rpt_files)} RPT files in {scan_dir}")
    else:
        rpt_files = sys.argv[1:]

    for filepath in rpt_files:
        print(f"\n{'='*70}")
        print(f"File: {filepath}")
        print(f"Size: {os.path.getsize(filepath):,} bytes")

        header, sections = read_sectionhdr(filepath)

        if header is None:
            print("  ERROR: Not a valid RPT file (no RPTFILEHDR signature)")
            continue

        print(f"  Domain: {header.domain_id}, Species: {header.report_species_id}")
        print(f"  Timestamp: {header.timestamp}")
        print(f"  Pages: {header.page_count}, Sections: {header.section_count}")

        if sections:
            total_pages = sum(s.page_count for s in sections)
            print(f"  Section entries: {len(sections)}")
            print(f"  Total pages across sections: {total_pages}")
            print(f"\n  {'SECTION_ID':>12s}  {'START_PAGE':>10s}  {'PAGE_COUNT':>10s}")
            print(f"  {'-'*12}  {'-'*10}  {'-'*10}")
            for s in sections:
                print(f"  {s.section_id:>12d}  {s.start_page:>10d}  {s.page_count:>10d}")

            print(f"\n  Formatted: {format_segments(sections)[:120]}...")
        else:
            print("  No SECTIONHDR found (report may have no sections)")


if __name__ == '__main__':
    main()
