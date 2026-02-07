#!/usr/bin/env python3
"""
Papyrus RPT Page Extractor - Python Version
Extracts pages and binary objects from RPT (Report) files with Papyrus shell integration support.

Supports:
- Multiple page ranges: pages:1-5,10-20,50-60
- Multiple sections: sections:14259,14260,14261
- Dual input: %TMPFILE% binary or file path
- Papyrus shell method with 4 positional arguments
- Binary object concatenation (PDF/AFP)
- Comprehensive error handling with exit codes 0-10

Author: Claude Assistant
Version: 2.0.0
License: MIT
"""

import sys
import struct
import zlib
import os
from typing import Tuple, List, Dict, Optional, Set
from io import BytesIO


# ============================================================================
# Constants
# ============================================================================

# RPT File Structure Constants
RPTFILEHDR_SIZE = 40
RPTINSTHDR_SIZE = 12
PAGETBLHDR_SIZE = 28
SECTIONHDR_SIZE = 36
BPAGETBLHDR_SIZE = 28

# Magic signatures
RPTFILE_SIGNATURE = b'RPTFILE'
RPTINST_SIGNATURE = b'RPTINST'
PAGEOBJ_SIGNATURE = b'PAGEOBJ'
SECTIONHDR_SIGNATURE = b'SECTIONHDR'
BPAGEOBJ_SIGNATURE = b'BPAGEOBJ'

# Exit codes
EXIT_SUCCESS = 0
EXIT_INVALID_ARGS = 1
EXIT_FILE_NOT_FOUND = 2
EXIT_INVALID_RPT_FILE = 3
EXIT_READ_ERROR = 4
EXIT_WRITE_ERROR = 5
EXIT_INVALID_SELECTION_RULE = 6
EXIT_NO_PAGES_SELECTED = 7
EXIT_DECOMPRESSION_ERROR = 8
EXIT_MEMORY_ERROR = 9
EXIT_UNKNOWN_ERROR = 10


# ============================================================================
# Data Structures
# ============================================================================

class PageEntry:
    """Represents a single page entry from PAGETBLHDR"""
    def __init__(self, page_num: int, offset: int, compressed_size: int, 
                 uncompressed_size: int, section_id: int):
        self.page_num = page_num
        self.offset = offset
        self.compressed_size = compressed_size
        self.uncompressed_size = uncompressed_size
        self.section_id = section_id


class BinaryEntry:
    """Represents a binary object entry from BPAGETBLHDR"""
    def __init__(self, entry_num: int, offset: int, compressed_size: int, 
                 uncompressed_size: int, object_type: int):
        self.entry_num = entry_num
        self.offset = offset
        self.compressed_size = compressed_size
        self.uncompressed_size = uncompressed_size
        self.object_type = object_type


class SelectionRule:
    """Represents a parsed selection rule"""
    def __init__(self):
        self.mode = "all"  # "all", "pages", "sections"
        self.page_ranges: List[Tuple[int, int]] = []
        self.section_ids: Set[int] = set()


# ============================================================================
# Core RPT File Functions
# ============================================================================

def read_rpt_header(filepath: str) -> Tuple[dict, int]:
    """
    Read and validate RPTFILEHDR structure.
    Returns (header_dict, page_count) or raises exception
    """
    try:
        with open(filepath, 'rb') as f:
            header_data = f.read(RPTFILEHDR_SIZE)
            
        if len(header_data) < RPTFILEHDR_SIZE:
            raise ValueError("File too small for RPT header")
        
        # Parse RPTFILEHDR
        signature = header_data[0:7]
        if signature != RPTFILE_SIGNATURE:
            raise ValueError(f"Invalid RPT signature: {signature}")
        
        # Read page count and other fields
        page_count = struct.unpack('<I', header_data[8:12])[0]
        
        return {"signature": signature, "page_count": page_count}, page_count
    except Exception as e:
        raise ValueError(f"Failed to read RPT header: {e}")


def read_rpt_instance_header(filepath: str) -> dict:
    """Read RPTINSTHDR structure"""
    try:
        with open(filepath, 'rb') as f:
            f.seek(40)  # After main header
            inst_header = f.read(RPTINSTHDR_SIZE)
        
        if len(inst_header) < RPTINSTHDR_SIZE:
            raise ValueError("Invalid RPTINST header")
        
        signature = inst_header[0:7]
        if signature != RPTINST_SIGNATURE:
            raise ValueError(f"Invalid RPTINST signature: {signature}")
        
        return {"signature": signature}
    except Exception as e:
        raise ValueError(f"Failed to read RPT instance header: {e}")


def read_page_table(filepath: str, page_count: int) -> Tuple[List[PageEntry], int]:
    """
    Read PAGETBLHDR entries for all pages.
    Returns (page_entries_list, first_page_offset)
    """
    page_entries = []
    
    try:
        with open(filepath, 'rb') as f:
            # Position after headers: RPTFILEHDR (40) + RPTINSTHDR (12)
            f.seek(52)
            
            for i in range(page_count):
                entry_data = f.read(PAGETBLHDR_SIZE)
                if len(entry_data) < PAGETBLHDR_SIZE:
                    raise ValueError(f"Incomplete page entry {i}")
                
                # Parse PAGETBLHDR structure
                page_num = struct.unpack('<I', entry_data[0:4])[0]
                offset = struct.unpack('<Q', entry_data[4:12])[0]
                compressed_size = struct.unpack('<I', entry_data[12:16])[0]
                uncompressed_size = struct.unpack('<I', entry_data[16:20])[0]
                section_id = struct.unpack('<I', entry_data[20:24])[0]
                
                entry = PageEntry(page_num, offset, compressed_size, 
                                 uncompressed_size, section_id)
                page_entries.append(entry)
            
            # First page offset for reference
            first_offset = page_entries[0].offset if page_entries else 0
            
        return page_entries, first_offset
    except Exception as e:
        raise ValueError(f"Failed to read page table: {e}")


def decompress_page(filepath: str, entry: PageEntry) -> bytes:
    """Decompress a single page using zlib"""
    try:
        with open(filepath, 'rb') as f:
            f.seek(entry.offset)
            compressed_data = f.read(entry.compressed_size)
        
        if len(compressed_data) != entry.compressed_size:
            raise ValueError("Incomplete compressed data")
        
        decompressed = zlib.decompress(compressed_data)
        return decompressed
    except zlib.error as e:
        raise ValueError(f"Decompression error: {e}")
    except Exception as e:
        raise ValueError(f"Failed to decompress page: {e}")


def decompress_pages(filepath: str, entries: List[PageEntry]) -> List[bytes]:
    """Decompress multiple pages"""
    pages = []
    for entry in entries:
        page_data = decompress_page(filepath, entry)
        pages.append(page_data)
    return pages


def read_binary_page_table(filepath: str) -> Tuple[List[BinaryEntry], int]:
    """
    Read BPAGETBLHDR entries for binary objects.
    Returns (binary_entries_list, binary_count)
    """
    binary_entries = []
    
    try:
        with open(filepath, 'rb') as f:
            # Binary table is after page data
            # Seek to find BPAGEOBJ signature
            f.seek(0, 2)  # End of file
            file_size = f.tell()
            
            # Search backwards for binary object table
            f.seek(max(0, file_size - 10000))
            data = f.read()
            
            # Look for binary object table signature
            binary_start = data.rfind(b'BPAGEOBJ')
            if binary_start == -1:
                return [], 0
            
            # Parse binary entries
            actual_offset = max(0, file_size - 10000) + binary_start
            f.seek(actual_offset)
            
            # Read count first
            count_data = f.read(4)
            if len(count_data) == 4:
                binary_count = struct.unpack('<I', count_data)[0]
                
                for i in range(binary_count):
                    entry_data = f.read(BPAGETBLHDR_SIZE)
                    if len(entry_data) < BPAGETBLHDR_SIZE:
                        break
                    
                    entry_num = struct.unpack('<I', entry_data[0:4])[0]
                    offset = struct.unpack('<Q', entry_data[4:12])[0]
                    compressed_size = struct.unpack('<I', entry_data[12:16])[0]
                    uncompressed_size = struct.unpack('<I', entry_data[16:20])[0]
                    object_type = struct.unpack('<I', entry_data[20:24])[0]
                    
                    entry = BinaryEntry(entry_num, offset, compressed_size,
                                      uncompressed_size, object_type)
                    binary_entries.append(entry)
                
                return binary_entries, binary_count
        
        return [], 0
    except Exception as e:
        # Binary table is optional
        return [], 0


def decompress_binary_objects(filepath: str, entries: List[BinaryEntry]) -> List[bytes]:
    """Decompress and concatenate binary objects"""
    concatenated_data = BytesIO()
    
    try:
        for entry in entries:
            with open(filepath, 'rb') as f:
                f.seek(entry.offset)
                compressed_data = f.read(entry.compressed_size)
            
            if len(compressed_data) != entry.compressed_size:
                raise ValueError(f"Incomplete binary object {entry.entry_num}")
            
            decompressed = zlib.decompress(compressed_data)
            concatenated_data.write(decompressed)
        
        return [concatenated_data.getvalue()] if entries else []
    except zlib.error as e:
        raise ValueError(f"Binary decompression error: {e}")
    except Exception as e:
        raise ValueError(f"Failed to decompress binary objects: {e}")


# ============================================================================
# Selection Rule Parsing
# ============================================================================

def parse_selection_rule(rule_str: str) -> SelectionRule:
    """
    Parse selection rule string.
    Formats:
    - "all": All pages
    - "pages:1-5": Pages 1-5
    - "pages:1-5,10-20,50-60": Multiple ranges
    - "section:14259": Single section
    - "sections:14259,14260,14261": Multiple sections
    """
    rule = SelectionRule()
    
    if rule_str.lower() == "all":
        rule.mode = "all"
        return rule
    
    parts = rule_str.split(':')
    if len(parts) != 2:
        raise ValueError(f"Invalid selection rule format: {rule_str}")
    
    selector_type = parts[0].lower()
    selector_value = parts[1]
    
    if selector_type == "pages":
        rule.mode = "pages"
        ranges = selector_value.split(',')
        for range_str in ranges:
            range_str = range_str.strip()
            if '-' in range_str:
                try:
                    start, end = range_str.split('-')
                    start = int(start.strip())
                    end = int(end.strip())
                    if start < 1 or end < start:
                        raise ValueError(f"Invalid range: {range_str}")
                    rule.page_ranges.append((start, end))
                except ValueError as e:
                    raise ValueError(f"Invalid page range: {range_str}: {e}")
            else:
                try:
                    page = int(range_str.strip())
                    if page < 1:
                        raise ValueError(f"Invalid page number: {page}")
                    rule.page_ranges.append((page, page))
                except ValueError as e:
                    raise ValueError(f"Invalid page number: {range_str}: {e}")
    
    elif selector_type in ["section", "sections"]:
        rule.mode = "sections"
        section_strs = selector_value.split(',')
        for section_str in section_strs:
            try:
                section_id = int(section_str.strip())
                if section_id < 0:
                    raise ValueError(f"Invalid section ID: {section_id}")
                rule.section_ids.add(section_id)
            except ValueError as e:
                raise ValueError(f"Invalid section ID: {section_str}: {e}")
    
    else:
        raise ValueError(f"Unknown selector type: {selector_type}")
    
    return rule


def select_pages_by_range(entries: List[PageEntry], 
                         page_ranges: List[Tuple[int, int]]) -> Tuple[List[PageEntry], List[int], List[int]]:
    """
    Select pages matching page ranges.
    Returns (selected_entries, found_pages, skipped_pages)
    """
    selected = []
    found = []
    skipped = []
    
    for entry in entries:
        page_num = entry.page_num
        is_selected = False
        
        for start, end in page_ranges:
            if start <= page_num <= end:
                selected.append(entry)
                found.append(page_num)
                is_selected = True
                break
        
        if not is_selected:
            skipped.append(page_num)
    
    return selected, found, skipped


def select_pages_by_sections(entries: List[PageEntry], 
                            section_ids: Set[int]) -> Tuple[List[PageEntry], List[int], List[int]]:
    """
    Select pages matching section IDs.
    Returns (selected_entries, found_sections, skipped_sections)
    """
    selected = []
    found_sections = set()
    skipped_sections = set()
    
    for entry in entries:
        if entry.section_id in section_ids:
            selected.append(entry)
            found_sections.add(entry.section_id)
        else:
            if entry.section_id not in section_ids:
                skipped_sections.add(entry.section_id)
    
    return selected, list(found_sections), list(skipped_sections)


# ============================================================================
# Main Extraction Function
# ============================================================================

def extract_rpt(input_path: str, selection_rule: SelectionRule, 
                output_text_path: str, output_binary_path: str,
                extract_mode: str = "both") -> Tuple[int, str]:
    """
    Extract pages from RPT file.
    extract_mode: "text", "binary", or "both"
    Returns (exit_code, message)
    """
    try:
        # Validate input file
        if not os.path.exists(input_path):
            return EXIT_FILE_NOT_FOUND, f"Input file not found: {input_path}"
        
        if not os.path.isfile(input_path):
            return EXIT_FILE_NOT_FOUND, f"Not a file: {input_path}"
        
        # Read RPT header
        header, page_count = read_rpt_header(input_path)
        
        # Read page table
        page_entries, _ = read_page_table(input_path, page_count)
        
        # Apply selection rule
        if selection_rule.mode == "all":
            selected_entries = page_entries
        elif selection_rule.mode == "pages":
            selected_entries, found, skipped = select_pages_by_range(
                page_entries, selection_rule.page_ranges)
        elif selection_rule.mode == "sections":
            selected_entries, found, skipped = select_pages_by_sections(
                page_entries, selection_rule.section_ids)
        else:
            return EXIT_INVALID_SELECTION_RULE, "Invalid selection rule"
        
        if not selected_entries:
            return EXIT_NO_PAGES_SELECTED, "No pages matched the selection rule"
        
        # Extract text pages
        if extract_mode in ["text", "both"]:
            try:
                page_data = decompress_pages(input_path, selected_entries)
                
                with open(output_text_path, 'wb') as f:
                    for page_bytes in page_data:
                        f.write(page_bytes)
            except Exception as e:
                return EXIT_DECOMPRESSION_ERROR, f"Failed to extract text: {e}"
        
        # Extract binary objects
        if extract_mode in ["binary", "both"]:
            try:
                binary_entries, binary_count = read_binary_page_table(input_path)
                
                if binary_entries:
                    binary_data = decompress_binary_objects(input_path, binary_entries)
                    if binary_data:
                        with open(output_binary_path, 'wb') as f:
                            f.write(binary_data[0])
            except Exception as e:
                return EXIT_DECOMPRESSION_ERROR, f"Failed to extract binary: {e}"
        
        return EXIT_SUCCESS, f"Successfully extracted {len(selected_entries)} pages"
    
    except Exception as e:
        if "Decompression" in str(e):
            return EXIT_DECOMPRESSION_ERROR, str(e)
        elif "Memory" in str(e):
            return EXIT_MEMORY_ERROR, str(e)
        else:
            return EXIT_UNKNOWN_ERROR, f"Extraction failed: {e}"


# ============================================================================
# Main CLI
# ============================================================================

def main():
    """
    Papyrus shell command interface.
    Usage: papyrus_rpt_page_extractor.py <input_rpt> <selection_rule> <output_txt> <output_binary>
    
    Arguments:
        input_rpt: Path to RPT file or %TMPFILE% for binary input
        selection_rule: "all", "pages:1-5", "pages:1-5,10-20", "section:123", "sections:123,456"
        output_txt: Path to output text file
        output_binary: Path to output binary file (PDF/AFP)
    
    Exit codes:
        0: Success
        1: Invalid arguments
        2: File not found
        3: Invalid RPT file
        4: Read error
        5: Write error
        6: Invalid selection rule
        7: No pages selected
        8: Decompression error
        9: Memory error
        10: Unknown error
    """
    
    # Validate arguments
    if len(sys.argv) != 5:
        print(f"Usage: {sys.argv[0]} <input_rpt> <selection_rule> <output_txt> <output_binary>",
              file=sys.stderr)
        print("Example: papyrus_rpt_page_extractor.py report.rpt 'pages:1-5,10-20' output.txt output.bin",
              file=sys.stderr)
        sys.exit(EXIT_INVALID_ARGS)
    
    input_rpt = sys.argv[1]
    selection_rule_str = sys.argv[2]
    output_txt = sys.argv[3]
    output_binary = sys.argv[4]
    
    try:
        # Parse selection rule
        selection_rule = parse_selection_rule(selection_rule_str)
        
        # Extract pages
        exit_code, message = extract_rpt(input_rpt, selection_rule, 
                                        output_txt, output_binary)
        
        if exit_code == EXIT_SUCCESS:
            print(message)
        else:
            print(f"ERROR: {message}", file=sys.stderr)
        
        sys.exit(exit_code)
    
    except ValueError as e:
        print(f"ERROR: Invalid selection rule: {e}", file=sys.stderr)
        sys.exit(EXIT_INVALID_SELECTION_RULE)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(EXIT_UNKNOWN_ERROR)


if __name__ == "__main__":
    main()
