#!/usr/bin/env python3
"""
rpt_page_extractor.py - Decompress and extract pages from IntelliSTOR .RPT files

Extracts page content from RPT files using the PAGETBLHDR for fast random access.
Pages are decompressed from individual zlib streams and saved as .txt files.
Also extracts embedded binary objects (PDF/AFP) tracked by the BPAGETBLHDR structure.

Supports:
  - Full extraction: all pages from one or more RPT files
  - Page range:      --pages 10-20 (extract pages 10 through 20)
  - Section-based:   --section-id 14259 (extract only pages belonging to that section)
  - Multi-section:   --section-id 14259 14260 14261 (multiple sections, in order)
  - Folder mode:     --folder <dir> (process all RPT files in a directory)
  - Binary objects:  --binary-only (extract only PDF/AFP), --no-binary (skip binary)

RPT File Layout (reference):
  [0x000] RPTFILEHDR     - Header with domain:species, timestamp
  [0x0F0] RPTINSTHDR     - Instance metadata (base offset for page_offset)
  [0x1D0] Table Directory (3 rows x 12 bytes):
          Row 0 (0x1D0): type=0x0102  count=page_count    offset → PAGETBLHDR
          Row 1 (0x1E0): type=0x0101  count=section_count  offset → SECTIONHDR
          Row 2 (0x1F0): type=0x0103  count=binary_count   offset → BPAGETBLHDR
  [0x200] COMPRESSED DATA - per-page zlib streams + interleaved binary object streams
  [...]   SECTIONHDR     - section triplets (SECTION_ID, START_PAGE, PAGE_COUNT)
  [...]   PAGETBLHDR     - 24-byte entries per page (offset, size, dimensions)
  [...]   BPAGETBLHDR    - 16-byte entries per binary object (PDF/AFP, if present)

PAGETBLHDR Entry Format (24 bytes, little-endian):
  [page_offset:4]        - Byte offset relative to RPTINSTHDR (add 0xF0 for absolute)
  [pad:4]                - Reserved (always 0)
  [line_width:2]         - Max characters per line on this page
  [lines_per_page:2]     - Number of lines on this page
  [uncompressed_size:4]  - Decompressed page data size in bytes
  [compressed_size:4]    - zlib stream size in bytes
  [pad:4]                - Reserved (always 0)

BPAGETBLHDR Entry Format (16 bytes, little-endian):
  [page_offset:4]        - Byte offset relative to RPTINSTHDR (add 0xF0 for absolute)
  [reserved:4]           - Always 0
  [uncompressed_size:4]  - Decompressed data size in bytes
  [compressed_size:4]    - zlib stream size in bytes
"""

import struct
import zlib
import os
import sys
import argparse
from dataclasses import dataclass
from typing import List, Optional, Tuple

from rpt_section_reader import parse_rpt_header, read_sectionhdr, SectionEntry, RptHeader


# ============================================================================
# Data Structures
# ============================================================================

RPTINSTHDR_OFFSET = 0xF0  # Base offset for page_offset values

@dataclass
class PageTableEntry:
    """One PAGETBLHDR entry — metadata for a single page."""
    page_number: int          # 1-based page number
    page_offset: int          # Offset relative to RPTINSTHDR
    line_width: int           # Max characters per line
    lines_per_page: int       # Number of lines on this page
    uncompressed_size: int    # Decompressed data size
    compressed_size: int      # zlib stream size

    @property
    def absolute_offset(self) -> int:
        """Absolute file offset to the start of the zlib stream."""
        return self.page_offset + RPTINSTHDR_OFFSET


@dataclass
class BinaryObjectEntry:
    """One BPAGETBLHDR entry — metadata for an embedded binary object (PDF/AFP)."""
    index: int                # 1-based index
    page_offset: int          # Offset relative to RPTINSTHDR
    uncompressed_size: int    # Decompressed data size
    compressed_size: int      # zlib stream size

    @property
    def absolute_offset(self) -> int:
        """Absolute file offset to the start of the zlib stream."""
        return self.page_offset + RPTINSTHDR_OFFSET


# ============================================================================
# PAGETBLHDR Parsing
# ============================================================================

def read_page_table(filepath: str, page_count: int) -> List[PageTableEntry]:
    """
    Read PAGETBLHDR entries from an RPT file.

    Uses targeted scan to find the PAGETBLHDR marker, then reads
    page_count x 24-byte entries.

    Args:
        filepath: Path to .RPT file
        page_count: Number of pages (from header Table Directory)

    Returns:
        List of PageTableEntry objects (1-indexed page numbers)
    """
    entries = []

    with open(filepath, 'rb') as f:
        data = f.read()

    pt_pos = data.find(b'PAGETBLHDR')
    if pt_pos == -1:
        return entries

    # Skip marker (10 bytes) + 3 null padding bytes = 13 bytes
    entry_start = pt_pos + 13
    entry_size = 24

    for i in range(page_count):
        offset = entry_start + i * entry_size
        if offset + entry_size > len(data):
            break

        page_offset = struct.unpack_from('<I', data, offset)[0]
        # skip pad at offset+4
        line_width = struct.unpack_from('<H', data, offset + 8)[0]
        lines_per_page = struct.unpack_from('<H', data, offset + 10)[0]
        uncompressed_size = struct.unpack_from('<I', data, offset + 12)[0]
        compressed_size = struct.unpack_from('<I', data, offset + 16)[0]

        entries.append(PageTableEntry(
            page_number=i + 1,
            page_offset=page_offset,
            line_width=line_width,
            lines_per_page=lines_per_page,
            uncompressed_size=uncompressed_size,
            compressed_size=compressed_size
        ))

    return entries


# ============================================================================
# Page Decompression
# ============================================================================

def decompress_page(filepath: str, entry: PageTableEntry) -> Optional[bytes]:
    """
    Decompress a single page from the RPT file.

    Uses the PageTableEntry to seek directly to the zlib stream
    and decompress it.

    Args:
        filepath: Path to .RPT file
        entry: PageTableEntry with offset and size info

    Returns:
        Decompressed page content as bytes, or None on error
    """
    abs_offset = entry.absolute_offset

    with open(filepath, 'rb') as f:
        f.seek(abs_offset)
        compressed = f.read(entry.compressed_size)

    if len(compressed) < entry.compressed_size:
        return None

    try:
        return zlib.decompress(compressed)
    except zlib.error:
        # Try with extra bytes (some streams may need more)
        with open(filepath, 'rb') as f:
            f.seek(abs_offset)
            compressed = f.read(entry.compressed_size + 64)
        try:
            return zlib.decompress(compressed)
        except zlib.error:
            return None


def decompress_pages(filepath: str, entries: List[PageTableEntry]) -> List[Tuple[int, bytes]]:
    """
    Decompress multiple pages from the RPT file.

    Opens the file once and reads all requested pages for efficiency.

    Args:
        filepath: Path to .RPT file
        entries: List of PageTableEntry objects to decompress

    Returns:
        List of (page_number, decompressed_bytes) tuples
    """
    results = []
    file_size = os.path.getsize(filepath)

    with open(filepath, 'rb') as f:
        for entry in entries:
            abs_offset = entry.absolute_offset
            if abs_offset + entry.compressed_size > file_size:
                print(f"  WARNING: Page {entry.page_number} offset 0x{abs_offset:X} "
                      f"exceeds file size {file_size:,}", file=sys.stderr)
                continue

            f.seek(abs_offset)
            compressed = f.read(entry.compressed_size)

            try:
                page_data = zlib.decompress(compressed)
                results.append((entry.page_number, page_data))
            except zlib.error as e:
                print(f"  WARNING: Page {entry.page_number} decompression failed: {e}",
                      file=sys.stderr)

    return results


# ============================================================================
# BPAGETBLHDR Parsing
# ============================================================================

def read_binary_page_table(filepath: str, count: int) -> List[BinaryObjectEntry]:
    """
    Read BPAGETBLHDR entries from an RPT file.

    Scans for the BPAGETBLHDR marker and reads count x 16-byte entries
    describing embedded binary objects (PDF/AFP documents).

    Args:
        filepath: Path to .RPT file
        count: Number of binary objects (from header Table Directory Row 2)

    Returns:
        List of BinaryObjectEntry objects (1-indexed)
    """
    entries = []
    if count <= 0:
        return entries

    with open(filepath, 'rb') as f:
        data = f.read()

    bp_pos = data.find(b'BPAGETBLHDR')
    if bp_pos == -1:
        return entries

    # Skip marker (11 bytes) + 2 null padding bytes = 13 bytes
    entry_start = bp_pos + 13
    entry_size = 16

    for i in range(count):
        offset = entry_start + i * entry_size
        if offset + entry_size > len(data):
            break

        page_offset = struct.unpack_from('<I', data, offset)[0]
        # skip reserved at offset+4
        uncompressed_size = struct.unpack_from('<I', data, offset + 8)[0]
        compressed_size = struct.unpack_from('<I', data, offset + 12)[0]

        entries.append(BinaryObjectEntry(
            index=i + 1,
            page_offset=page_offset,
            uncompressed_size=uncompressed_size,
            compressed_size=compressed_size
        ))

    return entries


# ============================================================================
# Object Header Detection
# ============================================================================

OBJECT_HEADER_PREFIX = 'StorQM PLUS Object Header Page:'

def parse_object_header(page_content: bytes) -> Optional[dict]:
    """
    Parse an Object Header page to extract embedded document metadata.

    Object Header pages start with "StorQM PLUS Object Header Page:" and contain
    key-value pairs describing the embedded binary document (filename, timestamps,
    PDF/AFP creator info, etc.).

    Args:
        page_content: Decompressed text page content

    Returns:
        dict with metadata key-value pairs, or None if not an Object Header page
    """
    try:
        text = page_content.decode('ascii', errors='replace')
    except Exception:
        return None

    if OBJECT_HEADER_PREFIX not in text:
        return None

    metadata = {}
    for line in text.splitlines():
        line = line.strip()
        if ':' in line and not line.startswith(OBJECT_HEADER_PREFIX):
            key, _, value = line.partition(':')
            key = key.strip()
            value = value.strip()
            if key and value:
                metadata[key] = value

    return metadata


def detect_binary_type(data: bytes, object_header: Optional[dict] = None) -> str:
    """
    Detect the format of a binary object from its magic bytes.

    Args:
        data: First bytes of the decompressed binary object
        object_header: Optional Object Header metadata (for filename extension fallback)

    Returns:
        File extension string (e.g. '.pdf', '.afp', '.bin')
    """
    if data[:4] == b'%PDF':
        return '.pdf'

    # AFP: Begin Structured Field Introducer starts with 0x5A
    if len(data) >= 1 and data[0] == 0x5A:
        return '.afp'

    # Fallback: use Object Header's "Object File Name" extension if available
    if object_header:
        obj_filename = object_header.get('Object File Name', '')
        if '.' in obj_filename:
            ext = obj_filename.rsplit('.', 1)[-1].lower()
            if ext in ('pdf', 'afp'):
                return f'.{ext}'

    return '.bin'


# ============================================================================
# Binary Object Decompression and Assembly
# ============================================================================

def decompress_binary_objects(filepath: str,
                              entries: List[BinaryObjectEntry]) -> List[Tuple[int, bytes]]:
    """
    Decompress binary object zlib streams from the RPT file.

    Opens the file once and reads all binary object entries for efficiency.

    Args:
        filepath: Path to .RPT file
        entries: List of BinaryObjectEntry objects to decompress

    Returns:
        List of (index, decompressed_bytes) tuples
    """
    results = []
    file_size = os.path.getsize(filepath)

    with open(filepath, 'rb') as f:
        for entry in entries:
            abs_offset = entry.absolute_offset
            if abs_offset + entry.compressed_size > file_size:
                print(f"  WARNING: Binary object {entry.index} offset 0x{abs_offset:X} "
                      f"exceeds file size {file_size:,}", file=sys.stderr)
                continue

            f.seek(abs_offset)
            compressed = f.read(entry.compressed_size)

            try:
                obj_data = zlib.decompress(compressed)
                results.append((entry.index, obj_data))
            except zlib.error as e:
                print(f"  WARNING: Binary object {entry.index} decompression failed: {e}",
                      file=sys.stderr)

    return results


def assemble_binary_document(objects: List[Tuple[int, bytes]],
                              object_header: Optional[dict] = None,
                              rpt_name: str = '') -> Tuple[bytes, str, str]:
    """
    Assemble decompressed binary objects into a single document.

    Binary objects from an RPT file concatenate to form a complete document
    (e.g., a multi-part PDF or AFP file).

    Args:
        objects: List of (index, decompressed_bytes) tuples, in order
        object_header: Optional Object Header metadata (for filename and type detection)
        rpt_name: RPT filename stem (for fallback naming)

    Returns:
        Tuple of (combined_bytes, output_filename, format_description)
    """
    # Concatenate all objects in order
    combined = b''.join(data for _, data in objects)

    # Detect format from magic bytes
    ext = detect_binary_type(combined, object_header)

    # Determine filename
    if object_header and object_header.get('Object File Name'):
        filename = object_header['Object File Name'].strip()
    else:
        filename = f'{rpt_name}_binary{ext}'

    # Format description
    format_map = {'.pdf': 'PDF', '.afp': 'AFP', '.bin': 'Binary'}
    format_desc = format_map.get(ext, 'Binary')

    return combined, filename, format_desc


# ============================================================================
# Page Selection
# ============================================================================

def select_pages_by_range(entries: List[PageTableEntry],
                          start_page: int, end_page: int) -> List[PageTableEntry]:
    """Select page table entries for a page range (inclusive, 1-based)."""
    return [e for e in entries if start_page <= e.page_number <= end_page]


def select_pages_by_section(entries: List[PageTableEntry],
                            sections: List[SectionEntry],
                            section_id: int) -> Optional[List[PageTableEntry]]:
    """
    Select page table entries for a specific section.

    Args:
        entries: All page table entries
        sections: SECTIONHDR entries from the RPT file
        section_id: SECTION_ID to extract

    Returns:
        List of PageTableEntry for the section's pages, or None if section not found
    """
    # Find the section
    section = None
    for s in sections:
        if s.section_id == section_id:
            section = s
            break

    if section is None:
        return None

    start = section.start_page
    end = section.start_page + section.page_count - 1
    return select_pages_by_range(entries, start, end)


def select_pages_by_sections(entries: List[PageTableEntry],
                             sections: List[SectionEntry],
                             section_ids: List[int]) -> Tuple[List[PageTableEntry], List[int], List[int]]:
    """
    Select page table entries for multiple sections, preserving the requested order.

    Pages are collected in the order of section_ids provided. Sections that
    are not found are silently skipped.

    Args:
        entries: All page table entries
        sections: SECTIONHDR entries from the RPT file
        section_ids: List of SECTION_IDs to extract, in desired order

    Returns:
        Tuple of (selected_entries, found_ids, skipped_ids)
    """
    # Build lookup for sections
    section_map = {s.section_id: s for s in sections}

    selected = []
    found_ids = []
    skipped_ids = []

    for sid in section_ids:
        if sid not in section_map:
            skipped_ids.append(sid)
            continue
        found_ids.append(sid)
        section = section_map[sid]
        start = section.start_page
        end = section.start_page + section.page_count - 1
        selected.extend(select_pages_by_range(entries, start, end))

    return selected, found_ids, skipped_ids


# ============================================================================
# Output
# ============================================================================

def save_pages(pages: List[Tuple[int, bytes]], output_dir: str,
               page_prefix: str = 'page') -> int:
    """
    Save decompressed pages as .txt files.

    Args:
        pages: List of (page_number, content_bytes) tuples
        output_dir: Directory to save files in
        page_prefix: Prefix for page filenames

    Returns:
        Number of pages saved
    """
    os.makedirs(output_dir, exist_ok=True)
    saved = 0

    for page_num, content in pages:
        filename = f'{page_prefix}_{page_num:05d}.txt'
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'wb') as f:
            f.write(content)
        saved += 1

    return saved


def extract_rpt(filepath: str, output_base: str,
                page_range: Optional[Tuple[int, int]] = None,
                section_id: Optional[int] = None,
                section_ids: Optional[List[int]] = None,
                info_only: bool = False,
                binary_only: bool = False,
                no_binary: bool = False) -> dict:
    """
    Extract pages from a single RPT file.

    When the RPT file contains embedded binary objects (PDF/AFP), the default behavior
    extracts both text pages and the binary document as separate files. Use binary_only
    or no_binary to control this behavior.

    Args:
        filepath: Path to .RPT file
        output_base: Base directory for output
        page_range: Optional (start, end) page range (1-based, inclusive)
        section_id: Optional single SECTION_ID to extract (legacy, kept for compatibility)
        section_ids: Optional list of SECTION_IDs to extract (in order, skips missing)
        info_only: If True, show info without extracting
        binary_only: If True, extract only the binary document (skip text pages)
        no_binary: If True, extract only text pages (skip binary objects)

    Returns:
        dict with extraction statistics
    """
    stats = {
        'file': filepath,
        'pages_total': 0,
        'pages_selected': 0,
        'pages_extracted': 0,
        'bytes_compressed': 0,
        'bytes_decompressed': 0,
        'binary_objects': 0,
        'binary_filename': None,
        'binary_size': 0,
        'error': None
    }

    # Read header
    with open(filepath, 'rb') as f:
        header_data = f.read(0x200)
    header = parse_rpt_header(header_data)
    if header is None:
        stats['error'] = 'Not a valid RPT file (no RPTFILEHDR signature)'
        return stats

    stats['pages_total'] = header.page_count
    rpt_name = os.path.splitext(os.path.basename(filepath))[0]

    # Read page table
    page_entries = read_page_table(filepath, header.page_count)
    if not page_entries:
        stats['error'] = 'No PAGETBLHDR found'
        return stats

    # Read sections (needed for --section-id and info display)
    _, sections = read_sectionhdr(filepath)

    # Read binary object table (if present)
    binary_entries = []
    if header.binary_object_count > 0:
        binary_entries = read_binary_page_table(filepath, header.binary_object_count)

    # Parse Object Header from text page 1 (if binary objects exist)
    object_header = None
    if binary_entries and page_entries:
        first_page = decompress_page(filepath, page_entries[0])
        if first_page:
            object_header = parse_object_header(first_page)

    # Display info
    print(f"\n{'='*70}")
    print(f"File: {filepath}")
    print(f"  Species: {header.report_species_id}, Domain: {header.domain_id}")
    print(f"  Timestamp: {header.timestamp}")
    print(f"  Pages: {header.page_count}, Sections: {header.section_count}")
    if header.binary_object_count > 0:
        print(f"  Binary Objects: {header.binary_object_count}")

    total_comp = sum(e.compressed_size for e in page_entries)
    total_uncomp = sum(e.uncompressed_size for e in page_entries)
    if total_comp > 0:
        ratio = total_uncomp / total_comp
        print(f"  Compressed: {total_comp:,} bytes -> Uncompressed: {total_uncomp:,} bytes ({ratio:.1f}x)")

    # Collect all requested section IDs for marker display
    requested_sids = set()
    if section_ids:
        requested_sids = set(section_ids)
    elif section_id is not None:
        requested_sids = {section_id}

    if sections:
        print(f"\n  Sections ({len(sections)}):")
        print(f"  {'SECTION_ID':>12s}  {'START_PAGE':>10s}  {'PAGE_COUNT':>10s}")
        print(f"  {'-'*12}  {'-'*10}  {'-'*10}")
        for s in sections:
            marker = " <--" if s.section_id in requested_sids else ""
            print(f"  {s.section_id:>12d}  {s.start_page:>10d}  {s.page_count:>10d}{marker}")

    if info_only:
        # Show page table sample
        print(f"\n  Page Table (first 5 / last 5):")
        print(f"  {'PAGE':>6s}  {'OFFSET':>10s}  {'WIDTH':>6s}  {'LINES':>6s}  {'UNCOMP':>8s}  {'COMP':>8s}")
        if len(page_entries) <= 10:
            show = page_entries
        else:
            show = page_entries[:5]
            show.append(None)  # separator
            show.extend(page_entries[-5:])
        for e in show:
            if e is None:
                print(f"  {'...':>6s}")
                continue
            print(f"  {e.page_number:>6d}  0x{e.absolute_offset:08X}  {e.line_width:>6d}  "
                  f"{e.lines_per_page:>6d}  {e.uncompressed_size:>8,d}  {e.compressed_size:>8,d}")

        # Show binary object table if present
        if binary_entries:
            print(f"\n  Binary Objects ({len(binary_entries)}):  [BPAGETBLHDR]")
            print(f"  {'INDEX':>7s}  {'OFFSET':>10s}  {'UNCOMP_SIZE':>11s}  {'COMP_SIZE':>10s}")
            print(f"  {'-'*7}  {'-'*10}  {'-'*11}  {'-'*10}")
            for be in binary_entries:
                print(f"  {be.index:>7d}  0x{be.absolute_offset:08X}  "
                      f"{be.uncompressed_size:>11,d}  {be.compressed_size:>10,d}")

            if object_header:
                print(f"\n  Object Header:")
                for key, value in object_header.items():
                    print(f"    {key}: {value}")

            # Show assembled document info
            bin_objs = decompress_binary_objects(filepath, binary_entries)
            if bin_objs:
                combined, filename, format_desc = assemble_binary_document(
                    bin_objs, object_header, rpt_name)
                print(f"\n  Assembled document: {format_desc} ({len(combined):,} bytes)")
                print(f"  Output filename: {filename}")

        return stats

    # Select pages to extract
    selected = page_entries  # default: all pages

    # Normalize: single section_id into section_ids list
    effective_section_ids = section_ids if section_ids else ([section_id] if section_id is not None else None)

    if effective_section_ids is not None:
        selected, found_ids, skipped_ids = select_pages_by_sections(
            page_entries, sections, effective_section_ids)
        if skipped_ids:
            print(f"\n  Skipped (not found): {', '.join(str(sid) for sid in skipped_ids)}")
        if not found_ids:
            stats['error'] = f'None of the requested section IDs found in SECTIONHDR'
            print(f"\n  ERROR: {stats['error']}")
            if sections:
                print(f"  Available section IDs: {', '.join(str(s.section_id) for s in sections[:20])}")
            return stats
        section_map = {s.section_id: s for s in sections}
        for sid in found_ids:
            si = section_map[sid]
            print(f"\n  Extracting section {sid}: "
                  f"pages {si.start_page}-{si.start_page + si.page_count - 1} "
                  f"({si.page_count} pages)")
        total_section_pages = sum(section_map[sid].page_count for sid in found_ids)
        print(f"\n  Total: {len(found_ids)} section(s), {total_section_pages} pages")

    elif page_range is not None:
        start_p, end_p = page_range
        # Clamp to valid range
        start_p = max(1, start_p)
        end_p = min(header.page_count, end_p)
        selected = select_pages_by_range(page_entries, start_p, end_p)
        print(f"\n  Extracting page range: {start_p}-{end_p} ({len(selected)} pages)")

    else:
        print(f"\n  Extracting all {header.page_count} pages")

    # Determine output directory
    if effective_section_ids is not None:
        if len(found_ids) == 1:
            output_dir = os.path.join(output_base, rpt_name, f'section_{found_ids[0]}')
        else:
            label = '_'.join(str(sid) for sid in found_ids)
            output_dir = os.path.join(output_base, rpt_name, f'sections_{label}')
    elif page_range is not None:
        output_dir = os.path.join(output_base, rpt_name, f'pages_{page_range[0]}-{page_range[1]}')
    else:
        output_dir = os.path.join(output_base, rpt_name)

    stats['pages_selected'] = len(selected)

    # -----------------------------------------------------------------------
    # Extract text pages (unless --binary-only)
    # -----------------------------------------------------------------------
    if not binary_only:
        # Filter out Object Header page when binary objects are present
        text_selected = selected
        if binary_entries and object_header and selected:
            # Object Header is text page 1 — skip it from regular text output
            text_selected = [e for e in selected if e.page_number != 1]
            if text_selected != selected:
                print(f"  Object Header page (page 1) separated from text output")

        if text_selected:
            pages = decompress_pages(filepath, text_selected)
            stats['pages_extracted'] = len(pages)
            stats['bytes_compressed'] = sum(e.compressed_size for e in text_selected)
            stats['bytes_decompressed'] = sum(len(content) for _, content in pages)

            saved = save_pages(pages, output_dir, page_prefix='page')
            print(f"  Saved {saved} text pages to {output_dir}/")
            print(f"  Total decompressed: {stats['bytes_decompressed']:,} bytes")

            # Check for failures
            failed = len(text_selected) - stats['pages_extracted']
            if failed > 0:
                print(f"  WARNING: {failed} pages failed to decompress")

        # Save Object Header as separate file (for reference)
        if binary_entries and object_header:
            first_page = decompress_page(filepath, page_entries[0])
            if first_page:
                os.makedirs(output_dir, exist_ok=True)
                oh_path = os.path.join(output_dir, 'object_header.txt')
                with open(oh_path, 'wb') as f:
                    f.write(first_page)
                print(f"  Saved object_header.txt to {output_dir}/")
    else:
        if not binary_entries:
            stats['error'] = 'No binary objects found in this RPT file (--binary-only requires BPAGETBLHDR)'
            print(f"\n  ERROR: {stats['error']}")
            return stats

    # -----------------------------------------------------------------------
    # Extract binary objects (unless --no-binary)
    # -----------------------------------------------------------------------
    if not no_binary and binary_entries:
        bin_objs = decompress_binary_objects(filepath, binary_entries)
        if bin_objs:
            combined, filename, format_desc = assemble_binary_document(
                bin_objs, object_header, rpt_name)

            os.makedirs(output_dir, exist_ok=True)
            bin_path = os.path.join(output_dir, filename)
            with open(bin_path, 'wb') as f:
                f.write(combined)

            stats['binary_objects'] = len(bin_objs)
            stats['binary_filename'] = filename
            stats['binary_size'] = len(combined)

            print(f"  Saved {format_desc} document: {filename} ({len(combined):,} bytes) to {output_dir}/")
        else:
            print(f"  WARNING: Binary objects found but all decompression failed")

    return stats


# ============================================================================
# CLI
# ============================================================================

def parse_page_range(s: str) -> Tuple[int, int]:
    """Parse a page range string like '10-20' or '5'."""
    if '-' in s:
        parts = s.split('-', 1)
        return int(parts[0]), int(parts[1])
    else:
        n = int(s)
        return n, n


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Extract and decompress pages from IntelliSTOR .RPT files.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show RPT file info (no extraction)
  python rpt_page_extractor.py --info 260271NL.RPT

  # Extract all pages from an RPT file
  python rpt_page_extractor.py 260271NL.RPT

  # Extract specific page range
  python rpt_page_extractor.py --pages 10-20 251110OD.RPT

  # Extract pages for a specific section (by SECTION_ID)
  python rpt_page_extractor.py --section-id 14259 251110OD.RPT

  # Extract pages for multiple sections (in order, skips missing)
  python rpt_page_extractor.py --section-id 14259 14260 14261 251110OD.RPT

  # Process all RPT files in a folder
  python rpt_page_extractor.py --folder /path/to/rpt/files

  # Extract only the binary document (PDF/AFP) from an RPT file
  python rpt_page_extractor.py --binary-only 260271Q7.RPT

  # Extract only text pages (skip binary objects)
  python rpt_page_extractor.py --no-binary 260271Q7.RPT

  # Custom output directory
  python rpt_page_extractor.py --output /tmp/extracted 251110OD.RPT
        """
    )

    parser.add_argument(
        'rptfile',
        nargs='*',
        help='Path(s) to .RPT file(s) (or use --folder for batch mode)'
    )
    parser.add_argument(
        '--folder',
        help='Process all .RPT files in this directory'
    )
    parser.add_argument(
        '--output', '-o',
        default='.',
        help='Output base directory (default: current directory)'
    )
    parser.add_argument(
        '--pages',
        help='Page range to extract (e.g., "10-20", "5") — 1-based, inclusive'
    )
    parser.add_argument(
        '--section-id',
        type=int,
        nargs='+',
        metavar='ID',
        help='Extract pages belonging to one or more SECTION_IDs (in order, skips missing)'
    )
    parser.add_argument(
        '--info',
        action='store_true',
        help='Show RPT file info and page table without extracting'
    )
    parser.add_argument(
        '--binary-only',
        action='store_true',
        help='Extract only the binary document (PDF/AFP), skip text pages'
    )
    parser.add_argument(
        '--no-binary',
        action='store_true',
        help='Extract only text pages, skip binary objects (PDF/AFP)'
    )

    args = parser.parse_args()

    # Validate arguments
    if not args.rptfile and not args.folder:
        parser.error('Provide either RPT file path(s) or --folder <directory>')

    if args.pages and args.section_id:
        parser.error('Cannot use both --pages and --section-id')

    if args.binary_only and args.no_binary:
        parser.error('Cannot use both --binary-only and --no-binary')

    # Parse page range
    page_range = None
    if args.pages:
        try:
            page_range = parse_page_range(args.pages)
        except ValueError:
            parser.error(f'Invalid page range: {args.pages}. Use format "10-20" or "5".')

    # Collect RPT files
    rpt_files = []
    if args.folder:
        if not os.path.isdir(args.folder):
            parser.error(f'Folder does not exist: {args.folder}')
        for root, dirs, files in os.walk(args.folder):
            for fname in files:
                if fname.upper().endswith('.RPT'):
                    rpt_files.append(os.path.join(root, fname))
        if not rpt_files:
            print(f"No .RPT files found in {args.folder}")
            sys.exit(0)
        rpt_files.sort()
        print(f"Found {len(rpt_files)} RPT files in {args.folder}")
    else:
        for f in args.rptfile:
            if not os.path.exists(f):
                parser.error(f'RPT file not found: {f}')
        rpt_files = args.rptfile

    # Process each RPT file
    all_stats = []
    for filepath in rpt_files:
        stats = extract_rpt(
            filepath=filepath,
            output_base=args.output,
            page_range=page_range,
            section_ids=args.section_id,
            info_only=args.info,
            binary_only=args.binary_only,
            no_binary=args.no_binary
        )
        all_stats.append(stats)

        if stats['error']:
            print(f"  ERROR: {stats['error']}")

    # Summary for batch mode
    if len(rpt_files) > 1:
        total_pages = sum(s['pages_extracted'] for s in all_stats)
        total_bytes = sum(s['bytes_decompressed'] for s in all_stats)
        errors = sum(1 for s in all_stats if s['error'])
        print(f"\n{'='*70}")
        print(f"SUMMARY: {len(rpt_files)} files, {total_pages} pages extracted, "
              f"{total_bytes:,} bytes decompressed, {errors} errors")


if __name__ == '__main__':
    main()
