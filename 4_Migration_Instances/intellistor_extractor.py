#!/usr/bin/env python3
"""
intellistor_extractor.py - Data Extraction Tool for IntelliSTOR Reports

Searches for indexed field values (e.g., ACCOUNT_NO) using binary MAP file indices,
decompresses matching pages from RPT files, classifies lines using LINE.TEMPLATE
patterns, and extracts field values at column positions.

Pipeline:
  1. Resolve report → instance → MAP file + RPT file + STRUCTURE_DEF_ID
  2. Search MAP file for field value → page numbers
  3. Decompress matched pages from RPT file
  4. Match lines against LINE.TEMPLATE patterns
  5. Extract FIELD values at START_COLUMN:END_COLUMN
  6. Output structured data (CSV/JSON)

Usage:
    # Search by indexed field value
    python intellistor_extractor.py --report DDU017P --field ACCOUNT_NO --value "200-044295-001"

    # Search with specific date
    python intellistor_extractor.py --report DDU017P --field ACCOUNT_NO --value "200-044295-001" \\
        --date "2025-01-13"

    # Output as CSV
    python intellistor_extractor.py --report DDU017P --field ACCOUNT_NO --value "200-044295-001" \\
        --output results.csv --format csv

    # Output as JSON
    python intellistor_extractor.py --report DDU017P --field ACCOUNT_NO --value "200-044295-001" \\
        --output results.json --format json

    # Show raw page text (no field extraction)
    python intellistor_extractor.py --report DDU017P --field ACCOUNT_NO --value "200-044295-001" \\
        --raw-pages

    # List indexed fields for a report
    python intellistor_extractor.py --report DDU017P --list-fields

Requirements:
    - Database: iSTSGUAT on localhost:1433 (pymssql)
    - MAP files: /Volumes/X9Pro/OCBC/250_MapFiles/
    - RPT files: configurable via --rpt-dir
"""

import argparse
import csv
import json
import os
import struct
import sys
from dataclasses import dataclass, field as dataclass_field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set

# Import from existing modules
from intellistor_viewer import (
    Config, DatabaseAccess, MapFileParser,
    FieldDef, LineDef, ReportInstance, IndexEntry
)
from rpt_page_extractor import (
    read_page_table, decompress_pages, PageTableEntry
)
from rpt_section_reader import parse_rpt_header, RptHeader


# ============================================================================
# Template Matching Engine
# ============================================================================

def _prepare_template(template: str) -> str:
    """
    Prepare a LINE.TEMPLATE for matching.

    Database templates are padded to 255 chars with spaces and end with '*'.
    Strip the trailing '*' terminator and trailing whitespace to get the
    active matching region.
    """
    t = template.rstrip()
    if t.endswith('*'):
        t = t[:-1].rstrip()
    return t


def score_line_against_template(line_text: str, template: str) -> float:
    """
    Score how well a text line matches an IntelliSTOR LINE template.

    IntelliSTOR templates are generated from sample lines and encode the
    character-class pattern of that sample. However, real data varies:
    - 'A' positions may contain digits, punctuation, or spaces
    - '9' positions may contain letters or spaces (e.g., short amounts)
    - The template is one snapshot; actual data fields have variable content

    Scoring approach:
    - Literal characters (-, /, ., ',', ':', etc.) are ANCHORS and weighted
      heavily — they define the structural skeleton of the line format
    - 'A' and '9' positions are flexible: exact type match scores full,
      other printable chars score partial, space scores less
    - Space positions: space matches fully, non-space gets partial credit

    Args:
        line_text: The text line to test (should be stripped of \\r)
        template: The raw LINE.TEMPLATE from database

    Returns:
        Score from 0.0 to 1.0 (1.0 = perfect match)
    """
    tmpl = _prepare_template(template)
    if not tmpl:
        return 0.0

    # Empty lines can't match meaningful templates
    stripped_line = line_text.rstrip()
    if not stripped_line and len(tmpl) > 10:
        return 0.0

    padded = line_text.ljust(len(tmpl))
    total_weight = 0.0
    earned = 0.0

    for i in range(len(tmpl)):
        t = tmpl[i]
        s = padded[i]

        if t == 'A':
            # Flex position — expect alpha but accept others
            total_weight += 1.0
            if s.isalpha():
                earned += 1.0
            elif s.isdigit():
                earned += 0.7  # digit in alpha slot — common for IDs
            elif s in ('*', '#', '@', '&', '(', ')'):
                earned += 0.5  # special chars in name fields
            elif s == ' ':
                earned += 0.3  # space in alpha slot — short/padded field
        elif t == '9':
            # Flex position — expect digit but accept others
            total_weight += 1.0
            if s.isdigit():
                earned += 1.0
            elif s.isalpha():
                earned += 0.7  # alpha in digit slot — common for codes
            elif s in ('*', '#', '.', ',', '-', '+'):
                earned += 0.5  # special chars in numeric fields
            elif s == ' ':
                earned += 0.3  # space in digit slot — short numbers
        elif t == ' ':
            # Space position — expect space
            total_weight += 0.5  # lower weight — spaces are less distinctive
            if s == ' ':
                earned += 0.5
            else:
                earned += 0.1  # non-space where space expected
        else:
            # LITERAL/ANCHOR — these are the structural markers
            # High weight — dashes, slashes, commas, dots, colons define format
            total_weight += 3.0
            if s == t:
                earned += 3.0
            # No partial credit for literal mismatches

    if total_weight == 0:
        return 0.0

    return earned / total_weight


# Minimum score threshold for a template to be considered a match.
# Empirically tuned: real data typically scores 0.65-0.85 against correct
# template due to variable field content. Wrong templates score < 0.50.
MIN_MATCH_SCORE = 0.55


def classify_lines(page_text: str, line_defs: List[LineDef]) -> List[Tuple[str, Optional[LineDef]]]:
    """
    Classify each line of a page against LINE templates using best-fit scoring.

    For each text line, scores it against all LINE templates and picks the
    highest-scoring match above MIN_MATCH_SCORE. This handles the reality
    that IntelliSTOR templates are generated from one sample and real data
    has variable content in A/9 positions.

    Args:
        page_text: Decompressed page text
        line_defs: List of LINE definitions with templates

    Returns:
        List of (line_text, matched_LineDef_or_None) tuples
    """
    results = []
    # Handle \r\n line endings — strip \r from each line
    lines = page_text.replace('\r\n', '\n').split('\n')
    lines = [l.rstrip('\r') for l in lines]

    # Pre-filter to only templates that have meaningful content
    active_defs = [(ld, _prepare_template(ld.template))
                   for ld in line_defs
                   if ld.template and len(_prepare_template(ld.template)) > 0]

    for line_text in lines:
        best_def = None
        best_score = MIN_MATCH_SCORE

        for line_def, prepped_tmpl in active_defs:
            score = score_line_against_template(line_text, line_def.template)
            if score > best_score:
                best_score = score
                best_def = line_def

        results.append((line_text, best_def))

    return results


# ============================================================================
# Field Extraction
# ============================================================================

def extract_field_value(line_text: str, field_def: FieldDef) -> str:
    """
    Extract a field value from a line at its column positions.

    Args:
        line_text: The text line
        field_def: Field definition with START_COLUMN and END_COLUMN

    Returns:
        Extracted and stripped field value
    """
    start = field_def.start_column
    end = field_def.end_column + 1  # END_COLUMN is inclusive
    if start >= len(line_text):
        return ''
    return line_text[start:min(end, len(line_text))].strip()


def extract_fields_from_page(
    page_text: str,
    line_defs: List[LineDef],
    field_defs_by_line: Dict[int, List[FieldDef]],
    page_number: int = 0
) -> List[Dict[str, str]]:
    """
    Extract all field values from a decompressed page.

    For each text line:
    1. Match against LINE.TEMPLATE to identify LINE_ID
    2. Extract FIELD values at START_COLUMN:END_COLUMN

    Args:
        page_text: Decompressed page text
        line_defs: LINE definitions with templates
        field_defs_by_line: Dict mapping LINE_ID → List[FieldDef]
        page_number: Page number for metadata

    Returns:
        List of dicts, one per classified line with field values
    """
    records = []
    classified = classify_lines(page_text, line_defs)

    for line_text, line_def in classified:
        if line_def is None:
            continue

        fields = field_defs_by_line.get(line_def.line_id, [])
        if not fields:
            continue

        record = {
            '_page': str(page_number),
            '_line_id': str(line_def.line_id),
            '_line_name': line_def.name,
        }

        for fdef in fields:
            value = extract_field_value(line_text, fdef)
            record[fdef.name] = value

        records.append(record)

    return records


# ============================================================================
# Page Resolution for Large MAP Files (u32_index format)
# ============================================================================

def build_segment0_page_lookup(parser: MapFileParser) -> Dict[int, int]:
    """
    Build u32_join_key → page_number lookup from Segment 0 for large MAP files.

    In large MAP files, index entries use u32_index format where the 4-byte
    value is a join key into Segment 0's 15-byte record array. This function
    parses that array and builds a lookup dict.

    Segment 0 record format (15 bytes, little-endian):
      [page_number:4][rec_id_byte:1][type:1][pad:1][u32_join_key:4][u32_extra:4]

    Record types (byte 5):
      0x08 = data record (contains page mapping, u32_join_key is the key)
      0x0c = separator record (skip)

    The u32_join_key values are sequential odd numbers (1, 3, 5, 7...).
    MAP index entries reference these keys via their u32_index field.

    Args:
        parser: MapFileParser with loaded data and parsed segments

    Returns:
        Dict mapping u32_join_key → page_number
    """
    if not parser.segments:
        return {}

    seg0 = parser.segments[0]
    lookup = {}
    record_size = 15
    offset = seg0.data_offset
    end = seg0.offset + seg0.size

    while offset + record_size <= end:
        if offset + record_size > len(parser.data):
            break

        page_raw = struct.unpack('<I', parser.data[offset:offset+4])[0]
        rec_type = parser.data[offset + 5]  # type byte at position 5
        u32_join_key = struct.unpack('<I', parser.data[offset+7:offset+11])[0]

        if rec_type == 0x08:  # data record
            page_number = page_raw & 0x7FFFFFFF  # mask off branch boundary flag
            lookup[u32_join_key] = page_number

        offset += record_size

    return lookup


def resolve_pages_from_entries(
    entries: List[IndexEntry],
    parser: MapFileParser
) -> Set[int]:
    """
    Resolve page numbers from MAP index entries.

    Handles both entry formats:
    - 'page' format: page_number is directly available
    - 'u32_index' format: must resolve through Segment 0 lookup

    Args:
        entries: List of IndexEntry from MAP search
        parser: MapFileParser for u32_index resolution

    Returns:
        Set of unique page numbers (1-based)
    """
    pages = set()

    if not entries:
        return pages

    fmt = entries[0].entry_format

    if fmt == 'page':
        for entry in entries:
            if entry.page_number > 0:
                pages.add(entry.page_number)
    elif fmt == 'u32_index':
        # Build lookup from Segment 0
        seg0_lookup = build_segment0_page_lookup(parser)
        if seg0_lookup:
            for entry in entries:
                page = seg0_lookup.get(entry.u32_index)
                if page and page > 0:
                    pages.add(page)
        else:
            print("  WARNING: Could not build Segment 0 page lookup for u32_index resolution",
                  file=sys.stderr)

    return pages


# ============================================================================
# RPT File Resolution
# ============================================================================

def find_rpt_file(rpt_filename: str, rpt_dirs: List[str]) -> Optional[str]:
    """
    Find an RPT file on disk given the database filename and search directories.

    The database FILENAME may contain path prefixes like 'MIDASRPT\\5\\260271NL.RPT'.
    We strip the prefix and search for the basename in the provided directories.

    Args:
        rpt_filename: Filename from RPTFILE.FILENAME (may include path prefix)
        rpt_dirs: List of directories to search

    Returns:
        Full path to the RPT file, or None if not found
    """
    # Get basename, handling both Windows and Unix path separators
    basename = rpt_filename.replace('\\', '/').split('/')[-1]

    for rpt_dir in rpt_dirs:
        candidate = os.path.join(rpt_dir, basename)
        if os.path.exists(candidate):
            return candidate

    return None


# ============================================================================
# Output Formatters
# ============================================================================

def output_csv(records: List[Dict[str, str]], output_path: str):
    """Write extracted records as CSV."""
    if not records:
        print("No records to output.")
        return

    # Collect all field names preserving order (metadata first, then fields)
    fieldnames = []
    for record in records:
        for key in record:
            if key not in fieldnames:
                fieldnames.append(key)

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"Wrote {len(records)} records to {output_path}")


def output_json(records: List[Dict[str, str]], output_path: str):
    """Write extracted records as JSON."""
    if not records:
        print("No records to output.")
        return

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(records, f, indent=2, default=str)

    print(f"Wrote {len(records)} records to {output_path}")


def output_table(records: List[Dict[str, str]], max_rows: int = 50):
    """Print records as a formatted table to stdout."""
    if not records:
        print("No records found.")
        return

    # Collect field names (skip metadata prefixed with _)
    meta_fields = [k for k in records[0] if k.startswith('_')]
    data_fields = [k for k in records[0] if not k.startswith('_')]

    # Calculate column widths
    all_fields = meta_fields + data_fields
    widths = {}
    for field in all_fields:
        widths[field] = max(len(field), max(len(str(r.get(field, ''))) for r in records[:max_rows]))
        widths[field] = min(widths[field], 40)  # cap width

    # Print header
    header = ' | '.join(f"{f:{widths[f]}s}" for f in all_fields)
    print(header)
    print('-' * len(header))

    # Print rows
    for i, record in enumerate(records[:max_rows]):
        row = ' | '.join(
            f"{str(record.get(f, '')):{widths[f]}s}" for f in all_fields
        )
        print(row)

    if len(records) > max_rows:
        print(f"... ({len(records) - max_rows} more records)")

    print(f"\nTotal: {len(records)} records")


# ============================================================================
# Main Extraction Pipeline
# ============================================================================

class IntelliSTORExtractor:
    """Main data extraction tool."""

    def __init__(self, config: Config, rpt_dirs: Optional[List[str]] = None):
        self.config = config
        self.rpt_dirs = rpt_dirs or []
        self.db: Optional[DatabaseAccess] = None

    def connect(self):
        """Connect to database."""
        self.db = DatabaseAccess(self.config)
        self.db.connect()

    def close(self):
        """Close connections."""
        if self.db:
            self.db.close()

    def _get_instance_by_date(self, species_id: int, date_str: str) -> Optional[ReportInstance]:
        """
        Get a report instance matching a date (YYYY-MM-DD) using date-range query.
        Falls back to the closest instance on or before the given date.
        """
        cursor = self.db.conn.cursor(as_dict=True)
        cursor.execute("""
            SELECT TOP 1 DOMAIN_ID, REPORT_SPECIES_ID, AS_OF_TIMESTAMP,
                   STRUCTURE_DEF_ID, RPT_FILE_SIZE_KB, MAP_FILE_SIZE_KB
            FROM REPORT_INSTANCE
            WHERE DOMAIN_ID = %s AND REPORT_SPECIES_ID = %s
                  AND CAST(AS_OF_TIMESTAMP AS DATE) = %s
            ORDER BY AS_OF_TIMESTAMP DESC
        """, (self.config.domain_id, species_id, date_str))

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

    def list_indexed_fields(self, report_name: str):
        """List all indexed fields for a report."""
        species_id = self.db.get_report_species_id_by_name(report_name)
        if not species_id:
            print(f"Report '{report_name}' not found in database.")
            return

        instance = self.db.get_report_instance(species_id)
        if not instance:
            print(f"No instances found for report '{report_name}'.")
            return

        print(f"\nIndexed fields for {report_name} "
              f"(STRUCTURE_DEF_ID={instance.structure_def_id}):\n")

        fields = self.db.get_field_definitions(instance.structure_def_id, indexed_only=True)
        if not fields:
            print("  No indexed fields found.")
            return

        print(f"  {'LINE_ID':>7} {'FIELD_ID':>8} {'NAME':<30} {'COLUMNS':<15}")
        print(f"  {'-'*7} {'-'*8} {'-'*30} {'-'*15}")
        for f in fields:
            print(f"  {f.line_id:7d} {f.field_id:8d} {f.name:<30} {f.start_column}-{f.end_column}")

    def search_and_extract(
        self,
        report_name: str,
        field_name: str,
        search_value: str,
        as_of_date: Optional[str] = None,
        raw_pages: bool = False,
        output_path: Optional[str] = None,
        output_format: str = 'table',
        detail_only: bool = False,
        line_filter: Optional[List[int]] = None
    ) -> List[Dict[str, str]]:
        """
        Full extraction pipeline: search → decompress → classify → extract.

        Args:
            report_name: Report species name (e.g., 'DDU017P')
            field_name: Indexed field name (e.g., 'ACCOUNT_NO')
            search_value: Value to search for
            as_of_date: Optional date filter (YYYY-MM-DD)
            raw_pages: If True, print raw page text instead of extracting fields
            output_path: Optional file path for CSV/JSON output
            output_format: 'table', 'csv', or 'json'
            detail_only: If True, only include the LINE that contains the search field
            line_filter: Optional list of LINE_IDs to include

        Returns:
            List of extracted records
        """
        # === Step 1: Resolve report → instance ===
        print(f"Resolving report '{report_name}'...")
        species_id = self.db.get_report_species_id_by_name(report_name)
        if not species_id:
            print(f"  ERROR: Report '{report_name}' not found in database.")
            return []

        instance = None
        if as_of_date:
            instance = self._get_instance_by_date(species_id, as_of_date)
        else:
            instance = self.db.get_report_instance(species_id)

        if not instance:
            print(f"  ERROR: No instance found for report '{report_name}'"
                  + (f" on {as_of_date}" if as_of_date else "") + ".")
            return []

        print(f"  Instance: {instance.as_of_timestamp} "
              f"(STRUCTURE_DEF_ID={instance.structure_def_id})")

        # === Step 2: Find indexed field ===
        indexed_fields = self.db.get_field_definitions(
            instance.structure_def_id, indexed_only=True)

        target_field = None
        for f in indexed_fields:
            if f.name.strip().upper() == field_name.strip().upper():
                target_field = f
                break

        if not target_field:
            print(f"  ERROR: Field '{field_name}' is not indexed for this report.")
            print(f"  Available indexed fields:")
            for f in indexed_fields:
                print(f"    {f.name} (LINE {f.line_id}, FIELD {f.field_id})")
            return []

        print(f"  Target field: {target_field.name} "
              f"(LINE {target_field.line_id}, FIELD {target_field.field_id}, "
              f"cols {target_field.start_column}-{target_field.end_column})")

        # === Step 3: Get MAP file and search ===
        map_filename = self.db.get_map_filename(instance)
        if not map_filename:
            print(f"  ERROR: No MAP file found for this instance.")
            return []

        map_filepath = os.path.join(self.config.map_file_dir, map_filename)
        if not os.path.exists(map_filepath):
            print(f"  ERROR: MAP file not found: {map_filepath}")
            return []

        print(f"  MAP file: {map_filename}")

        parser = MapFileParser(map_filepath)
        if not parser.load():
            print(f"  ERROR: Failed to load MAP file.")
            return []

        parser.parse_segments()
        matches = parser.search_index(search_value, target_field.line_id, target_field.field_id)

        if not matches:
            print(f"  No matches found for '{search_value}' in MAP index.")
            return []

        print(f"  Found {len(matches)} index entries for '{search_value}'")

        # === Step 4: Resolve page numbers ===
        page_numbers = resolve_pages_from_entries(matches, parser)

        if not page_numbers:
            print(f"  WARNING: Could not resolve any page numbers from MAP entries.")
            return []

        sorted_pages = sorted(page_numbers)
        print(f"  Resolved to {len(sorted_pages)} unique pages: "
              + (', '.join(str(p) for p in sorted_pages[:10])
                 + (f"... (+{len(sorted_pages)-10} more)" if len(sorted_pages) > 10 else "")))

        # === Step 5: Get RPT file and decompress pages ===
        rpt_filename = self.db.get_spool_filename(instance)
        if not rpt_filename:
            print(f"  ERROR: No RPT file found for this instance.")
            return []

        rpt_filepath = find_rpt_file(rpt_filename, self.rpt_dirs)
        if not rpt_filepath:
            print(f"  ERROR: RPT file '{rpt_filename}' not found in search directories:")
            for d in self.rpt_dirs:
                print(f"    {d}")
            return []

        print(f"  RPT file: {rpt_filepath}")

        # Parse RPT header to get page count
        with open(rpt_filepath, 'rb') as f:
            header_data = f.read(0x200)
        rpt_header = parse_rpt_header(header_data)
        if not rpt_header:
            print(f"  ERROR: Failed to parse RPT file header.")
            return []

        print(f"  RPT pages: {rpt_header.page_count}")

        # Read page table
        page_table = read_page_table(rpt_filepath, rpt_header.page_count)
        if not page_table:
            print(f"  ERROR: Failed to read page table from RPT file.")
            return []

        # Select entries for our pages
        target_entries = [e for e in page_table if e.page_number in page_numbers]

        if not target_entries:
            print(f"  ERROR: None of the resolved pages exist in the page table.")
            return []

        # Decompress
        print(f"  Decompressing {len(target_entries)} pages...")
        decompressed = decompress_pages(rpt_filepath, target_entries)

        if not decompressed:
            print(f"  ERROR: Failed to decompress any pages.")
            return []

        print(f"  Successfully decompressed {len(decompressed)} pages.")

        # === Step 6: Raw pages mode ===
        if raw_pages:
            for page_num, page_data in decompressed:
                print(f"\n{'='*60}")
                print(f"PAGE {page_num}")
                print('='*60)
                text = page_data.decode('utf-8', errors='replace')
                print(text)
            return []

        # === Step 7: Classify lines and extract fields ===
        print(f"  Loading LINE templates and FIELD definitions...")

        line_defs = self.db.get_line_definitions(instance.structure_def_id)
        all_fields = self.db.get_field_definitions(instance.structure_def_id)

        # Group fields by LINE_ID
        field_defs_by_line: Dict[int, List[FieldDef]] = {}
        for fdef in all_fields:
            if fdef.line_id not in field_defs_by_line:
                field_defs_by_line[fdef.line_id] = []
            field_defs_by_line[fdef.line_id].append(fdef)

        print(f"  {len(line_defs)} LINE templates, "
              f"{len(all_fields)} FIELD definitions")

        # Extract from each page
        all_records = []
        for page_num, page_data in decompressed:
            text = page_data.decode('utf-8', errors='replace')
            records = extract_fields_from_page(text, line_defs, field_defs_by_line, page_num)
            all_records.extend(records)

        print(f"  Extracted {len(all_records)} records from {len(decompressed)} pages.")

        # === Step 8: Filter records ===
        if detail_only:
            # Only keep records from the LINE that contains the search field
            target_line_id = str(target_field.line_id)
            all_records = [r for r in all_records if r.get('_line_id') == target_line_id]
            print(f"  Filtered to {len(all_records)} detail records (LINE {target_line_id}).")
        elif line_filter:
            line_filter_strs = [str(lid) for lid in line_filter]
            all_records = [r for r in all_records if r.get('_line_id') in line_filter_strs]
            print(f"  Filtered to {len(all_records)} records (LINEs {','.join(line_filter_strs)}).")

        # === Step 9: Output ===
        if output_path:
            if output_format == 'csv':
                output_csv(all_records, output_path)
            elif output_format == 'json':
                output_json(all_records, output_path)
            else:
                output_csv(all_records, output_path)
        else:
            output_table(all_records)

        return all_records


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='IntelliSTOR Data Extraction Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List indexed fields for a report
  %(prog)s --report DDU017P --list-fields

  # Search and extract (table output)
  %(prog)s --report DDU017P --field ACCOUNT_NO --value "200-044295-001"

  # Output as CSV
  %(prog)s --report DDU017P --field ACCOUNT_NO --value "200-044295-001" \\
      --output results.csv --format csv

  # Show raw page text
  %(prog)s --report DDU017P --field ACCOUNT_NO --value "200-044295-001" --raw-pages
        """
    )

    # Required arguments
    parser.add_argument('--report', required=True, help='Report name (e.g., DDU017P)')

    # Search parameters
    parser.add_argument('--field', help='Indexed field name to search (e.g., ACCOUNT_NO)')
    parser.add_argument('--value', help='Value to search for')
    parser.add_argument('--date', help='Report instance date (YYYY-MM-DD)')

    # Output
    parser.add_argument('--output', '-o', help='Output file path')
    parser.add_argument('--format', '-f', choices=['table', 'csv', 'json'],
                        default='table', help='Output format (default: table)')
    parser.add_argument('--raw-pages', action='store_true',
                        help='Print raw page text instead of extracting fields')

    # Filtering
    parser.add_argument('--detail-only', action='store_true',
                        help='Only output records from the search field\'s LINE (detail records)')
    parser.add_argument('--line-filter', type=int, nargs='+', metavar='LINE_ID',
                        help='Only output records from specific LINE_ID(s)')

    # List mode
    parser.add_argument('--list-fields', action='store_true',
                        help='List indexed fields for the report')

    # Configuration
    parser.add_argument('--db-server', default='localhost', help='Database server')
    parser.add_argument('--db-name', default='iSTSGUAT', help='Database name')
    parser.add_argument('--map-dir', default='/Volumes/X9Pro/OCBC/250_MapFiles',
                        help='MAP files directory')
    parser.add_argument('--rpt-dir', action='append', default=[],
                        help='RPT files directory (can specify multiple)')

    args = parser.parse_args()

    config = Config(
        db_server=args.db_server,
        db_name=args.db_name,
        map_file_dir=args.map_dir
    )

    extractor = IntelliSTORExtractor(config, rpt_dirs=args.rpt_dir)

    try:
        extractor.connect()

        if args.list_fields:
            extractor.list_indexed_fields(args.report)
        elif args.field and args.value:
            extractor.search_and_extract(
                report_name=args.report,
                field_name=args.field,
                search_value=args.value,
                as_of_date=args.date,
                raw_pages=args.raw_pages,
                output_path=args.output,
                output_format=args.format,
                detail_only=args.detail_only,
                line_filter=args.line_filter
            )
        else:
            parser.print_help()
            print("\nError: Must specify either --list-fields or both --field and --value")
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        extractor.close()


if __name__ == '__main__':
    main()
