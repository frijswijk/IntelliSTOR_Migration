#!/usr/bin/env python3
"""
rpt_file_builder.py - Create IntelliSTOR .RPT files from text pages and optional PDF/AFP

This is the inverse of rpt_page_extractor.py: it takes extracted text pages (and
optionally a binary document like a PDF) and assembles them into a valid .RPT binary
file that conforms to the IntelliSTOR RPT specification.

RPT File Layout (builder output):
  [0x000] RPTFILEHDR     - 240 bytes: header line + sub-header + zero-padding
  [0x0F0] RPTINSTHDR     - 224 bytes: instance metadata + zero-padding
  [0x1D0] Table Directory - 48 bytes: 3 rows x 16 bytes (offsets to trailer structures)
  [0x200] COMPRESSED DATA - Per-page zlib streams + interleaved binary object streams
  [...]   SECTIONHDR     - Marker + section triplets + ENDDATA
  [...]   PAGETBLHDR     - Marker + 24-byte page entries + ENDDATA
  [...]   BPAGETBLHDR    - Marker + 16-byte binary entries + ENDDATA (optional)

All offsets in the Table Directory, PAGETBLHDR, and BPAGETBLHDR are relative to
RPTINSTHDR at absolute position 0xF0.
"""

import struct
import zlib
import os
import sys
import argparse
import re
import glob as globmod
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# Add folder 4 to path for shared modules
_FOLDER_4 = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '4. Migration_Instances')
if _FOLDER_4 not in sys.path:
    sys.path.insert(0, _FOLDER_4)

from rpt_section_reader import parse_rpt_header, read_sectionhdr, SectionEntry, RptHeader


# ============================================================================
# Constants
# ============================================================================

RPTFILEHDR_SIZE   = 0x0F0   # 240 bytes
RPTINSTHDR_SIZE   = 0x0E0   # 224 bytes
TABLE_DIR_SIZE    = 0x030   # 48 bytes (3 rows x 16 bytes)
COMPRESSED_START  = 0x200   # Compressed data always starts here
RPTINSTHDR_OFFSET = 0x0F0   # Base for all relative offsets

ENDDATA_MARKER = b'ENDDATA\x00\x00'   # 9 bytes (7 + 2 null)
SECTIONHDR_MARKER = b'SECTIONHDR\x00\x00\x00'  # 13 bytes (10 + 3 null)
PAGETBLHDR_MARKER = b'PAGETBLHDR\x00\x00\x00'  # 13 bytes (10 + 3 null)
BPAGETBLHDR_MARKER = b'BPAGETBLHDR\x00\x00'    # 13 bytes (11 + 2 null)


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class SectionDef:
    """Section definition for building."""
    section_id: int
    start_page: int   # 1-based
    page_count: int

@dataclass
class PageInfo:
    """Analysis of one text page."""
    index: int           # 0-based index in text_pages list
    page_number: int     # 1-based page number in the output RPT
    line_width: int
    lines_per_page: int
    uncompressed_size: int
    compressed_data: bytes
    compressed_size: int

@dataclass
class BinaryChunkInfo:
    """Analysis of one binary chunk."""
    index: int           # 0-based index
    uncompressed_size: int
    compressed_data: bytes
    compressed_size: int

@dataclass
class BuildSpec:
    """Complete specification for building an RPT file."""
    species_id: int = 0
    domain_id: int = 1
    timestamp: str = ''                             # "YYYY/MM/DD HH:MM:SS.mmm"
    text_pages: List[bytes] = field(default_factory=list)  # Raw text content per page
    sections: List[SectionDef] = field(default_factory=list)
    binary_file: Optional[str] = None               # Path to PDF/AFP to embed
    object_header_page: Optional[bytes] = None       # Object Header text content
    template_rptinsthdr: Optional[bytes] = None      # 224-byte RPTINSTHDR from template
    template_table_dir: Optional[bytes] = None       # 48-byte Table Directory from template
    line_width_override: Optional[int] = None
    lines_per_page_override: Optional[int] = None


# ============================================================================
# Step 1: Input Collection and Validation
# ============================================================================

def collect_inputs(args) -> BuildSpec:
    """
    Collect and validate all input files, returning a BuildSpec object.

    Handles both directory input (scan for page_NNNNN.txt, object_header.txt,
    *.pdf, *.afp) and individual file inputs.
    """
    spec = BuildSpec()
    spec.species_id = args.species
    spec.domain_id = args.domain
    spec.timestamp = args.timestamp or datetime.now().strftime('%Y/%m/%d %H:%M:%S.') + \
                     f'{datetime.now().microsecond // 1000:03d}'

    if args.line_width:
        spec.line_width_override = args.line_width
    if args.lines_per_page:
        spec.lines_per_page_override = args.lines_per_page

    # Load template RPTINSTHDR if provided
    if args.template:
        if not os.path.exists(args.template):
            print(f"ERROR: Template file not found: {args.template}", file=sys.stderr)
            sys.exit(1)
        with open(args.template, 'rb') as f:
            tpl_data = f.read(COMPRESSED_START)
        if len(tpl_data) >= COMPRESSED_START:
            spec.template_rptinsthdr = tpl_data[RPTINSTHDR_OFFSET:RPTINSTHDR_OFFSET + RPTINSTHDR_SIZE]
            spec.template_table_dir = tpl_data[RPTINSTHDR_OFFSET + RPTINSTHDR_SIZE:COMPRESSED_START]

    # Collect text pages
    input_files = args.input_files
    text_pages = []
    binary_file = args.binary
    object_header_file = args.object_header

    if len(input_files) == 1 and os.path.isdir(input_files[0]):
        # Directory mode: scan for page_NNNNN.txt, object_header.txt, *.pdf, *.afp
        directory = input_files[0]
        page_files = sorted(globmod.glob(os.path.join(directory, 'page_*.txt')))
        obj_header_path = os.path.join(directory, 'object_header.txt')

        # Auto-detect binary file if not specified
        if not binary_file:
            for ext in ('*.pdf', '*.PDF', '*.afp', '*.AFP'):
                found = globmod.glob(os.path.join(directory, ext))
                if found:
                    binary_file = found[0]
                    break

        # Load object header if present and binary file exists
        if os.path.exists(obj_header_path) and binary_file:
            if not object_header_file:
                object_header_file = obj_header_path

        if not page_files:
            print(f"ERROR: No page_*.txt files found in {directory}", file=sys.stderr)
            sys.exit(1)

        for pf in page_files:
            with open(pf, 'rb') as f:
                text_pages.append(f.read())
    else:
        # Individual file mode: collect .txt files in order
        for fpath in input_files:
            if not os.path.exists(fpath):
                print(f"ERROR: Input file not found: {fpath}", file=sys.stderr)
                sys.exit(1)
            if fpath.lower().endswith('.txt'):
                with open(fpath, 'rb') as f:
                    text_pages.append(f.read())
            # Skip non-txt files (binary files should use --binary flag)

    if not text_pages:
        print("ERROR: At least 1 text page required", file=sys.stderr)
        sys.exit(1)

    # Load object header
    if object_header_file:
        if not os.path.exists(object_header_file):
            print(f"ERROR: Object header file not found: {object_header_file}", file=sys.stderr)
            sys.exit(1)
        with open(object_header_file, 'rb') as f:
            spec.object_header_page = f.read()

    # Binary file
    if binary_file:
        if not os.path.exists(binary_file):
            print(f"ERROR: Binary file not found: {binary_file}", file=sys.stderr)
            sys.exit(1)
        spec.binary_file = binary_file
        # Generate object header if not provided
        if not spec.object_header_page:
            spec.object_header_page = generate_object_header(binary_file)

    spec.text_pages = text_pages

    # Parse section specifications
    if args.section:
        for sec_spec in args.section:
            parts = sec_spec.split(':')
            if len(parts) != 3:
                print(f"ERROR: Invalid section spec: {sec_spec} (expected SECTION_ID:START_PAGE:PAGE_COUNT)",
                      file=sys.stderr)
                sys.exit(1)
            try:
                sid, sp, pc = int(parts[0]), int(parts[1]), int(parts[2])
            except ValueError:
                print(f"ERROR: Invalid section spec values: {sec_spec}", file=sys.stderr)
                sys.exit(1)
            spec.sections.append(SectionDef(section_id=sid, start_page=sp, page_count=pc))
    else:
        # Default: single section covering all pages
        total_pages = len(text_pages)
        if spec.binary_file and spec.object_header_page:
            total_pages += 1  # Object Header is page 1
        spec.sections.append(SectionDef(section_id=0, start_page=1, page_count=total_pages))

    return spec


# ============================================================================
# Step 2: Page Analysis
# ============================================================================

def analyze_page(page_data: bytes, index: int, page_number: int,
                 line_width_override: Optional[int] = None,
                 lines_per_page_override: Optional[int] = None) -> PageInfo:
    """
    Analyze a text page and compress it.

    Returns PageInfo with dimensions, sizes, and compressed data.
    """
    try:
        text = page_data.decode('ascii', errors='replace')
    except Exception:
        text = page_data.decode('latin-1', errors='replace')

    lines = text.splitlines()
    line_width = max((len(line) for line in lines), default=0) if lines else 0
    lines_count = len(lines)

    if line_width_override is not None:
        line_width = line_width_override
    if lines_per_page_override is not None:
        lines_count = lines_per_page_override

    compressed = zlib.compress(page_data)

    return PageInfo(
        index=index,
        page_number=page_number,
        line_width=line_width,
        lines_per_page=lines_count,
        uncompressed_size=len(page_data),
        compressed_data=compressed,
        compressed_size=len(compressed)
    )


# ============================================================================
# Step 3: Binary Object Chunking
# ============================================================================

def chunk_binary_file(binary_path: str, num_chunks: int) -> List[bytes]:
    """
    Split a binary file into num_chunks roughly-equal chunks.

    The chunks concatenate to form the original file exactly.
    """
    with open(binary_path, 'rb') as f:
        binary_data = f.read()

    if num_chunks <= 0:
        return []
    if num_chunks == 1:
        return [binary_data]

    chunk_size = len(binary_data) // num_chunks
    chunks = []
    offset = 0
    for i in range(num_chunks):
        if i == num_chunks - 1:
            # Last chunk gets remaining bytes
            chunks.append(binary_data[offset:])
        else:
            chunks.append(binary_data[offset:offset + chunk_size])
            offset += chunk_size

    return chunks


# ============================================================================
# Step 4: Compression
# ============================================================================

def compress_chunks(chunks: List[bytes]) -> List[BinaryChunkInfo]:
    """Compress each binary chunk using zlib."""
    result = []
    for i, chunk in enumerate(chunks):
        compressed = zlib.compress(chunk)
        result.append(BinaryChunkInfo(
            index=i,
            uncompressed_size=len(chunk),
            compressed_data=compressed,
            compressed_size=len(compressed)
        ))
    return result


# ============================================================================
# Step 5: Object Header Generation
# ============================================================================

def generate_object_header(binary_path: str) -> bytes:
    """
    Generate an Object Header page for an embedded binary file.

    Mimics the format observed in production RPT files.
    """
    filename = os.path.basename(binary_path)
    mtime = os.path.getmtime(binary_path)
    mtime_str = datetime.fromtimestamp(mtime).strftime('%Y%m%d%H%M%S')

    lines = [
        'StorQM PLUS Object Header Page:',
        f'Object File Name: {filename}',
        f'Object File Timestamp: {mtime_str}',
    ]

    # Try to extract PDF metadata
    if filename.upper().endswith('.PDF'):
        try:
            with open(binary_path, 'rb') as f:
                pdf_header = f.read(4096)
            pdf_text = pdf_header.decode('latin-1', errors='replace')

            for field_name in ['Title', 'Subject', 'Author', 'Creator',
                               'Producer', 'CreationDate', 'LastModifiedDate', 'Keywords']:
                value = ''
                pattern = f'/{field_name}\\s*\\(([^)]*)\\)'
                m = re.search(pattern, pdf_text)
                if m:
                    value = m.group(1)
                elif f'/{field_name}' in pdf_text:
                    # Try parenthesized value on next chars
                    idx = pdf_text.index(f'/{field_name}')
                    snippet = pdf_text[idx:idx+200]
                    m2 = re.search(r'\(([^)]*)\)', snippet)
                    if m2:
                        value = m2.group(1)
                lines.append(f'PDF {field_name}: {value}')
        except Exception:
            for field_name in ['Title', 'Subject', 'Author', 'Creator',
                               'Producer', 'CreationDate', 'LastModifiedDate', 'Keywords']:
                lines.append(f'PDF {field_name}: ')

    text = '\n'.join(lines) + '\n'
    return text.encode('ascii', errors='replace')


# ============================================================================
# Step 6: RPTFILEHDR Construction (0x000-0x0EF, 240 bytes)
# ============================================================================

def build_rptfilehdr(domain_id: int, species_id: int, timestamp: str,
                     compressed_data_end_rel: int) -> bytes:
    """
    Build the 240-byte RPTFILEHDR block.

    Args:
        domain_id: Domain ID (formatted as 4-digit zero-padded)
        species_id: Report species ID
        timestamp: "YYYY/MM/DD HH:MM:SS.mmm"
        compressed_data_end_rel: End of compressed data area, relative to RPTINSTHDR (0xF0)
    """
    # Header line
    domain_str = f'{domain_id:04d}'
    header_line = f'RPTFILEHDR\t{domain_str}:{species_id}\t{timestamp}\x1a'
    buf = bytearray(RPTFILEHDR_SIZE)  # 240 bytes, zero-filled

    # Write header line
    header_bytes = header_line.encode('ascii')
    buf[:len(header_bytes)] = header_bytes

    # Fixed sub-header at 0xC0-0xEF
    # 0xC0: E0 00 05 01  (fixed prefix)
    struct.pack_into('<I', buf, 0xC0, 0x010500E0)
    # 0xC4: 01 00 00 00  (constant 1)
    struct.pack_into('<I', buf, 0xC4, 1)
    # 0xC8: E0 00 00 00  (pointer to 0xE0)
    struct.pack_into('<I', buf, 0xC8, 0xE0)
    # 0xCC: 00 00 00 00  (reserved - already zero)
    # 0xD0: 00 00 00 00  (reserved - already zero)
    # 0xD4: "ENDHDR\x00\x00" (8 bytes)
    buf[0xD4:0xDC] = b'ENDHDR\x00\x00'
    # 0xDC: 00 00 00 00  (padding - already zero)
    # 0xE0: F0 00 00 00  (pointer to RPTINSTHDR)
    struct.pack_into('<I', buf, 0xE0, 0xF0)
    # 0xE4: 00 00 00 00  (reserved - already zero)
    # 0xE8: compressed_data_end (relative to RPTINSTHDR)
    struct.pack_into('<I', buf, 0xE8, compressed_data_end_rel)
    # 0xEC: 00 00 00 00  (reserved - already zero)

    return bytes(buf)


# ============================================================================
# Step 7: RPTINSTHDR Construction (0x0F0-0x1CF, 224 bytes)
# ============================================================================

def encode_bcd_timestamp(timestamp_str: str) -> bytes:
    """
    Encode a timestamp as BCD bytes matching the RPTINSTHDR format.

    Input: "YYYY/MM/DD HH:MM:SS.mmm" or similar
    Output: 8 bytes: [YYYY_hi, YYYY_lo, MM, DD, HH, MM, SS, 0x00]

    The year is stored as two BCD bytes (big-endian): e.g., 2028 -> 0x07, 0xEC
    Actually from hex dumps: 2028 -> EC 07 (little-endian uint16)
    Then MM DD HH MM SS as raw bytes (not BCD, just integer values)
    """
    # Parse the timestamp
    m = re.match(r'(\d{4})/(\d{2})/(\d{2})\s+(\d{2}):(\d{2}):(\d{2})', timestamp_str)
    if not m:
        return b'\x00' * 8

    year = int(m.group(1))
    month = int(m.group(2))
    day = int(m.group(3))
    hour = int(m.group(4))
    minute = int(m.group(5))
    second = int(m.group(6))

    buf = bytearray(8)
    struct.pack_into('<H', buf, 0, year)  # Year as uint16 LE
    buf[2] = month
    buf[3] = day
    buf[4] = hour
    buf[5] = minute
    buf[6] = second
    buf[7] = 0x00
    return bytes(buf)


def build_rptinsthdr(spec: BuildSpec) -> bytes:
    """
    Build the 224-byte RPTINSTHDR block.

    If a template is provided, copy it and patch species_id and timestamps.
    Otherwise, build from scratch with reasonable defaults.
    """
    if spec.template_rptinsthdr and len(spec.template_rptinsthdr) == RPTINSTHDR_SIZE:
        # Use template as base, patch key fields
        buf = bytearray(spec.template_rptinsthdr)

        # Patch species_id at relative offset 0x14
        struct.pack_into('<I', buf, 0x14, spec.species_id)

        # Patch report timestamp at 0x18 (8 bytes)
        ts_bytes = encode_bcd_timestamp(spec.timestamp)
        buf[0x18:0x20] = ts_bytes

        return bytes(buf)
    else:
        # Build from scratch
        buf = bytearray(RPTINSTHDR_SIZE)  # 224 bytes, zero-filled

        # 0x00: "RPTINSTHDR\x00\x00"
        buf[0:12] = b'RPTINSTHDR\x00\x00'
        # 0x0C: pointer back to RPTFILEHDR sub-header (0xE0)
        struct.pack_into('<I', buf, 0x0C, 0xE0)
        # 0x10: instance number (always 1)
        struct.pack_into('<I', buf, 0x10, 1)
        # 0x14: species_id
        struct.pack_into('<I', buf, 0x14, spec.species_id)
        # 0x18: report timestamp (8 bytes BCD)
        ts_bytes = encode_bcd_timestamp(spec.timestamp)
        buf[0x18:0x20] = ts_bytes
        # 0x22: creation timestamp (same format)
        buf[0x22:0x2A] = ts_bytes
        # 0x33: modification timestamp
        buf[0x33:0x3B] = ts_bytes
        # 0x40: fixed constants 01 01 00 00
        buf[0x40] = 0x01
        buf[0x41] = 0x01
        # 0xA0: report format info (0x0409 = 1033)
        struct.pack_into('<I', buf, 0xA0, 0x0409)
        # 0xD0: "ENDHDR\x00\x00"
        buf[0xD0:0xD8] = b'ENDHDR\x00\x00'

        return bytes(buf)


# ============================================================================
# Step 8: Compressed Data Assembly
# ============================================================================

def assemble_compressed_data(
    page_infos: List[PageInfo],
    binary_chunks: Optional[List[BinaryChunkInfo]] = None
) -> Tuple[bytes, List[int], Optional[List[int]]]:
    """
    Assemble the compressed data area.

    Text-only: page1 + page2 + page3 + ...
    With binary: page1 + bin1 + page2 + bin2 + ...

    Returns:
    - Combined compressed bytes
    - List of absolute offsets for text pages
    - List of absolute offsets for binary chunks (or None)
    """
    data = bytearray()
    page_offsets = []
    binary_offsets = [] if binary_chunks else None

    abs_pos = COMPRESSED_START  # 0x200

    if binary_chunks:
        # Interleaved: text1, bin1, text2, bin2, ...
        for i, page_info in enumerate(page_infos):
            page_offsets.append(abs_pos)
            data.extend(page_info.compressed_data)
            abs_pos += page_info.compressed_size

            if i < len(binary_chunks):
                binary_offsets.append(abs_pos)
                data.extend(binary_chunks[i].compressed_data)
                abs_pos += binary_chunks[i].compressed_size
    else:
        # Text-only: sequential
        for page_info in page_infos:
            page_offsets.append(abs_pos)
            data.extend(page_info.compressed_data)
            abs_pos += page_info.compressed_size

    return bytes(data), page_offsets, binary_offsets


# ============================================================================
# Step 9: Trailer Construction
# ============================================================================

def build_sectionhdr(sections: List[SectionDef]) -> bytes:
    """Build SECTIONHDR block: marker + triplets + ENDDATA."""
    buf = bytearray()
    buf.extend(SECTIONHDR_MARKER)  # 13 bytes

    for sec in sections:
        buf.extend(struct.pack('<III', sec.section_id, sec.start_page, sec.page_count))

    buf.extend(ENDDATA_MARKER)  # 9 bytes
    return bytes(buf)


def build_pagetblhdr(page_infos: List[PageInfo], page_offsets: List[int]) -> bytes:
    """
    Build PAGETBLHDR block: marker + 24-byte entries + ENDDATA.

    Each entry: [page_offset_rel:4][pad:4][line_width:2][lines:2][uncomp:4][comp:4][pad:4]
    page_offset_rel = absolute_offset - 0xF0
    """
    buf = bytearray()
    buf.extend(PAGETBLHDR_MARKER)  # 13 bytes

    for i, pi in enumerate(page_infos):
        abs_offset = page_offsets[i]
        rel_offset = abs_offset - RPTINSTHDR_OFFSET  # subtract 0xF0

        entry = struct.pack('<IIHHIII',
                            rel_offset,              # page_offset (relative to RPTINSTHDR)
                            0,                       # reserved
                            pi.line_width,           # line_width
                            pi.lines_per_page,       # lines_per_page
                            pi.uncompressed_size,    # uncompressed_size
                            pi.compressed_size,      # compressed_size
                            0)                       # reserved
        buf.extend(entry)

    buf.extend(ENDDATA_MARKER)  # 9 bytes
    return bytes(buf)


def build_bpagetblhdr(binary_chunks: List[BinaryChunkInfo],
                       binary_offsets: List[int]) -> bytes:
    """
    Build BPAGETBLHDR block: marker + 16-byte entries + ENDDATA.

    Each entry: [page_offset_rel:4][reserved:4][uncomp:4][comp:4]
    page_offset_rel = absolute_offset - 0xF0
    """
    buf = bytearray()
    buf.extend(BPAGETBLHDR_MARKER)  # 13 bytes

    for i, chunk in enumerate(binary_chunks):
        abs_offset = binary_offsets[i]
        rel_offset = abs_offset - RPTINSTHDR_OFFSET

        entry = struct.pack('<IIII',
                            rel_offset,              # page_offset (relative to RPTINSTHDR)
                            0,                       # reserved
                            chunk.uncompressed_size, # uncompressed_size
                            chunk.compressed_size)   # compressed_size
        buf.extend(entry)

    buf.extend(ENDDATA_MARKER)  # 9 bytes
    return bytes(buf)


# ============================================================================
# Step 10: Table Directory Construction (0x1D0-0x1FF, 48 bytes)
# ============================================================================

def build_table_directory(page_count: int, section_count: int,
                          binary_count: int,
                          sectionhdr_abs: int,
                          pagetblhdr_abs: int,
                          bpagetblhdr_abs: int,
                          template_table_dir: Optional[bytes] = None) -> bytes:
    """
    Build the 48-byte Table Directory (3 rows x 16 bytes).

    All offsets are relative to RPTINSTHDR (0xF0).

    Row 0 (0x1D0): PAGETBLHDR reference - type=0x0102, page_count, pagetbl_off
    Row 1 (0x1E0): SECTIONHDR reference - type=0x0101, section_count, sectionhdr_off
    Row 2 (0x1F0): BPAGETBLHDR reference - type=0x0103, binary_count, bpagetbl_off (or all zeros)
    """
    buf = bytearray(TABLE_DIR_SIZE)  # 48 bytes, zero-filled

    # Extract type prefix bytes from template if available
    type_extra_0 = 0  # bytes 2-3 of type field for Row 0
    type_extra_1 = 0  # bytes 2-3 of type field for Row 1
    if template_table_dir and len(template_table_dir) >= TABLE_DIR_SIZE:
        type_extra_0 = struct.unpack_from('<H', template_table_dir, 2)[0]
        type_extra_1 = struct.unpack_from('<H', template_table_dir, 0x10 + 2)[0]

    # Row 0: PAGETBLHDR
    pagetbl_rel = pagetblhdr_abs - RPTINSTHDR_OFFSET
    buf[0] = 0x02
    buf[1] = 0x01
    struct.pack_into('<H', buf, 2, type_extra_0)
    struct.pack_into('<I', buf, 4, page_count)
    struct.pack_into('<I', buf, 8, pagetbl_rel)
    # bytes 12-15: zero padding (already zero)

    # Row 1: SECTIONHDR
    sectionhdr_rel = sectionhdr_abs - RPTINSTHDR_OFFSET
    buf[0x10] = 0x01
    buf[0x11] = 0x01
    struct.pack_into('<H', buf, 0x12, type_extra_1)
    struct.pack_into('<I', buf, 0x14, section_count)
    struct.pack_into('<I', buf, 0x18, sectionhdr_rel)
    # bytes 0x1C-0x1F: zero padding (already zero)

    # Row 2: BPAGETBLHDR (or all zeros for text-only)
    if binary_count > 0:
        bpagetbl_rel = bpagetblhdr_abs - RPTINSTHDR_OFFSET
        buf[0x20] = 0x03
        buf[0x21] = 0x01
        # bytes 0x22-0x23: zero (no template extra needed for BPAGETBLHDR)
        struct.pack_into('<I', buf, 0x24, binary_count)
        struct.pack_into('<I', buf, 0x28, bpagetbl_rel)

    return bytes(buf)


# ============================================================================
# Step 10: Final Assembly
# ============================================================================

def build_rpt(spec: BuildSpec, output_path: str, verbose: bool = False):
    """
    Assemble all blocks into a complete RPT file.

    1. Prepare all pages (including Object Header if binary)
    2. Analyze and compress text pages
    3. Chunk and compress binary file (if present)
    4. Assemble compressed data area
    5. Build trailer structures
    6. Calculate offsets and build Table Directory
    7. Build RPTFILEHDR and RPTINSTHDR
    8. Write the final RPT file
    """
    # ---- Prepare all text pages ----
    all_pages = []
    if spec.binary_file and spec.object_header_page:
        # Object Header is page 1
        all_pages.append(spec.object_header_page)
    all_pages.extend(spec.text_pages)

    total_text_pages = len(all_pages)
    if verbose:
        print(f"  Text pages: {total_text_pages}")
        if spec.binary_file:
            print(f"  Binary file: {spec.binary_file}")

    # ---- Analyze and compress text pages ----
    page_infos = []
    for i, page_data in enumerate(all_pages):
        pi = analyze_page(page_data, i, i + 1,
                          spec.line_width_override, spec.lines_per_page_override)
        page_infos.append(pi)

    # ---- Chunk and compress binary file ----
    binary_chunks = None
    if spec.binary_file:
        # Number of chunks = number of text pages
        num_chunks = total_text_pages
        raw_chunks = chunk_binary_file(spec.binary_file, num_chunks)
        binary_chunks = compress_chunks(raw_chunks)
        if verbose:
            total_bin_uncomp = sum(c.uncompressed_size for c in binary_chunks)
            total_bin_comp = sum(c.compressed_size for c in binary_chunks)
            print(f"  Binary chunks: {len(binary_chunks)}, "
                  f"uncomp={total_bin_uncomp:,}, comp={total_bin_comp:,}")

    # ---- Assemble compressed data area ----
    comp_data, page_offsets, binary_offsets = assemble_compressed_data(
        page_infos, binary_chunks)

    compressed_data_end_abs = COMPRESSED_START + len(comp_data)
    compressed_data_end_rel = compressed_data_end_abs - RPTINSTHDR_OFFSET

    if verbose:
        print(f"  Compressed data: {len(comp_data):,} bytes "
              f"(0x{COMPRESSED_START:X} - 0x{compressed_data_end_abs:X})")

    # ---- Build trailer structures ----
    # Update section definitions if using default single section
    if len(spec.sections) == 1 and spec.sections[0].section_id == 0:
        spec.sections[0].page_count = total_text_pages

    sectionhdr_block = build_sectionhdr(spec.sections)
    pagetblhdr_block = build_pagetblhdr(page_infos, page_offsets)

    bpagetblhdr_block = b''
    binary_count = 0
    if binary_chunks and binary_offsets:
        binary_count = len(binary_chunks)
        bpagetblhdr_block = build_bpagetblhdr(binary_chunks, binary_offsets)

    # ---- Calculate absolute offsets for trailer structures ----
    sectionhdr_abs = compressed_data_end_abs
    pagetblhdr_abs = sectionhdr_abs + len(sectionhdr_block)
    bpagetblhdr_abs = pagetblhdr_abs + len(pagetblhdr_block)

    if verbose:
        print(f"  SECTIONHDR at: 0x{sectionhdr_abs:X}")
        print(f"  PAGETBLHDR at: 0x{pagetblhdr_abs:X}")
        if binary_count > 0:
            print(f"  BPAGETBLHDR at: 0x{bpagetblhdr_abs:X}")

    # ---- Build Table Directory ----
    table_dir = build_table_directory(
        page_count=total_text_pages,
        section_count=len(spec.sections),
        binary_count=binary_count,
        sectionhdr_abs=sectionhdr_abs,
        pagetblhdr_abs=pagetblhdr_abs,
        bpagetblhdr_abs=bpagetblhdr_abs,
        template_table_dir=spec.template_table_dir
    )

    # ---- Build RPTFILEHDR ----
    rptfilehdr = build_rptfilehdr(
        spec.domain_id, spec.species_id, spec.timestamp,
        compressed_data_end_rel
    )

    # ---- Build RPTINSTHDR ----
    rptinsthdr = build_rptinsthdr(spec)

    # ---- Final Assembly ----
    output = bytearray()
    output.extend(rptfilehdr)       # 0x000 - 0x0EF (240 bytes)
    output.extend(rptinsthdr)       # 0x0F0 - 0x1CF (224 bytes)
    output.extend(table_dir)        # 0x1D0 - 0x1FF (48 bytes)
    output.extend(comp_data)        # 0x200 - ...
    output.extend(sectionhdr_block) # SECTIONHDR
    output.extend(pagetblhdr_block) # PAGETBLHDR
    if bpagetblhdr_block:
        output.extend(bpagetblhdr_block)  # BPAGETBLHDR

    # ---- Write output ----
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(output)

    print(f"  Built RPT file: {output_path} ({len(output):,} bytes)")
    print(f"  Pages: {total_text_pages}, Sections: {len(spec.sections)}, "
          f"Binary objects: {binary_count}")

    return len(output)


# ============================================================================
# Step 11: Verification
# ============================================================================

def verify_rpt(output_path: str, verbose: bool = False):
    """
    Verify the built RPT file by reading it back with parse_rpt_header.
    """
    with open(output_path, 'rb') as f:
        header_data = f.read(0x200)

    header = parse_rpt_header(header_data)
    if header is None:
        print(f"  VERIFY FAIL: Not a valid RPT file", file=sys.stderr)
        return False

    if verbose:
        print(f"\n  Verification:")
        print(f"    Domain: {header.domain_id}, Species: {header.report_species_id}")
        print(f"    Timestamp: {header.timestamp}")
        print(f"    Pages: {header.page_count}, Sections: {header.section_count}")
        print(f"    Binary objects: {header.binary_object_count}")

    # Verify we can read sections
    _, sections = read_sectionhdr(output_path)
    if verbose:
        print(f"    Sections read back: {len(sections)}")
        for s in sections:
            print(f"      Section {s.section_id}: pages {s.start_page}-{s.start_page + s.page_count - 1}")

    # Try to import and use the page extractor for deeper verification
    try:
        from rpt_page_extractor import read_page_table, decompress_page
        entries = read_page_table(output_path, header.page_count)
        if verbose:
            print(f"    Page table entries: {len(entries)}")

        if entries:
            # Decompress first page
            first_page = decompress_page(output_path, entries[0])
            if first_page is not None:
                if verbose:
                    preview = first_page[:80].decode('ascii', errors='replace')
                    print(f"    First page preview: {preview}...")
            else:
                print(f"  VERIFY FAIL: Could not decompress first page", file=sys.stderr)
                return False

            # Decompress last page
            if len(entries) > 1:
                last_page = decompress_page(output_path, entries[-1])
                if last_page is not None:
                    if verbose:
                        preview = last_page[:80].decode('ascii', errors='replace')
                        print(f"    Last page preview: {preview}...")
                else:
                    print(f"  VERIFY FAIL: Could not decompress last page", file=sys.stderr)
                    return False
    except ImportError:
        if verbose:
            print(f"    (rpt_page_extractor not available for deep verification)")

    if verbose:
        print(f"    Verification: PASSED")
    return True


# ============================================================================
# CLI
# ============================================================================

def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Create IntelliSTOR .RPT files from text pages and optional PDF/AFP.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build text-only RPT from page files
  python3 rpt_file_builder.py --species 49626 --domain 1 \\
    -o output.RPT page_00001.txt page_00002.txt

  # Build from a directory of extracted pages
  python3 rpt_file_builder.py --species 49626 -o output.RPT ./extracted/260271NL/

  # Build RPT with embedded PDF
  python3 rpt_file_builder.py --species 52759 --domain 1 \\
    --binary HKCIF001_016_20280309.PDF \\
    -o output.RPT object_header.txt page_00002.txt

  # Build with template (roundtrip)
  python3 rpt_file_builder.py --template original.RPT \\
    --species 49626 -o rebuilt.RPT ./extracted/original/

  # Build RPT with multiple sections
  python3 rpt_file_builder.py --species 12345 \\
    --section 14259:1:10 --section 14260:11:5 \\
    -o output.RPT page_*.txt
        """
    )

    parser.add_argument(
        'input_files',
        nargs='+',
        help='Text files (.txt) or a directory containing page_NNNNN.txt files'
    )
    parser.add_argument(
        '-o', '--output',
        required=True,
        help='Output .RPT file path'
    )
    parser.add_argument(
        '--species',
        type=int,
        default=0,
        help='Report species ID (default: 0)'
    )
    parser.add_argument(
        '--domain',
        type=int,
        default=1,
        help='Domain ID (default: 1)'
    )
    parser.add_argument(
        '--timestamp',
        help='Report timestamp (default: current time). Format: "YYYY/MM/DD HH:MM:SS.mmm"'
    )
    parser.add_argument(
        '--binary',
        help='Path to PDF or AFP file to embed as binary object'
    )
    parser.add_argument(
        '--object-header',
        help='Path to text file for Object Header page (page 1)'
    )
    parser.add_argument(
        '--section',
        action='append',
        metavar='SEC_SPEC',
        help='Section spec: "SECTION_ID:START_PAGE:PAGE_COUNT" (can repeat)'
    )
    parser.add_argument(
        '--line-width',
        type=int,
        help='Override line width for all pages'
    )
    parser.add_argument(
        '--lines-per-page',
        type=int,
        help='Override lines per page for all pages'
    )
    parser.add_argument(
        '--template',
        help='Reference .RPT file to copy RPTINSTHDR metadata from'
    )
    parser.add_argument(
        '--info',
        action='store_true',
        help='Dry run: show what would be built without writing'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed build progress'
    )

    args = parser.parse_args()

    # Collect inputs
    spec = collect_inputs(args)

    if args.info:
        print(f"\nBuild plan:")
        print(f"  Species: {spec.species_id}, Domain: {spec.domain_id}")
        print(f"  Timestamp: {spec.timestamp}")
        print(f"  Text pages: {len(spec.text_pages)}")
        if spec.binary_file:
            bin_size = os.path.getsize(spec.binary_file)
            print(f"  Binary file: {spec.binary_file} ({bin_size:,} bytes)")
            if spec.object_header_page:
                print(f"  Object Header: {len(spec.object_header_page)} bytes")
        print(f"  Sections: {len(spec.sections)}")
        for s in spec.sections:
            print(f"    {s.section_id}: pages {s.start_page}-{s.start_page + s.page_count - 1}")
        print(f"  Template: {'yes' if spec.template_rptinsthdr else 'no'}")
        print(f"  Output: {args.output}")
        return

    # Build
    print(f"\nBuilding RPT file: {args.output}")
    file_size = build_rpt(spec, args.output, verbose=args.verbose)

    # Verify
    verify_rpt(args.output, verbose=args.verbose)


if __name__ == '__main__':
    main()
