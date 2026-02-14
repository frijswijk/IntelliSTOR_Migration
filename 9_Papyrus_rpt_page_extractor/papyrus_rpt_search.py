#!/usr/bin/env python3
"""
papyrus_rpt_search.py - Standalone MAP File Index Search Tool

Searches for indexed field values in binary MAP files without requiring
a database connection. Uses the existing MapFileParser from intellistor_viewer.py.

Three modes of operation:

1. Search by raw IDs (no metadata needed):
   python papyrus_rpt_search.py --map 25001002.MAP \
       --line-id 5 --field-id 3 --value "200-044295-001"

2. Search by field name (requires metadata JSON):
   python papyrus_rpt_search.py --map 25001002.MAP --metadata DDU017P_metadata.json \
       --field ACCOUNT_NO --value "200-044295-001"

3. List indexed fields in a MAP file:
   python papyrus_rpt_search.py --map 25001002.MAP --list-fields
   python papyrus_rpt_search.py --map 25001002.MAP --metadata DDU017P_metadata.json --list-fields

4. List all values for a specific field:
   python papyrus_rpt_search.py --map 25001002.MAP --line-id 5 --field-id 3 --list-values

Output formats: table (default), csv, json

Requirements:
    - MAP files on disk
    - intellistor_viewer.py (MapFileParser class) in same directory
    - Optional: metadata JSON files (from papyrus_export_metadata.py) for field name resolution
"""

import argparse
import csv
import json
import os
import struct
import sys
import time
from bisect import bisect_left
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Set

# Import existing MAP file parser
from intellistor_viewer import MapFileParser, MapSegmentInfo, IndexEntry


# ============================================================================
# Metadata Resolver — Maps field names to (LINE_ID, FIELD_ID) from JSON
# ============================================================================

class MetadataResolver:
    """
    Resolves human-readable field names to (LINE_ID, FIELD_ID) using
    exported metadata JSON files (from papyrus_export_metadata.py).

    Without metadata, the MAP file only contains numeric identifiers.
    This class bridges the gap.
    """

    def __init__(self, metadata_path: str):
        with open(metadata_path, 'r', encoding='utf-8') as f:
            self.metadata = json.load(f)
        self.species_name = self.metadata.get('species', {}).get('name', '')
        self._field_map: Dict[str, dict] = {}
        for field in self.metadata.get('indexed_fields', []):
            key = field['name'].strip().upper()
            self._field_map[key] = field

    def resolve_field(self, field_name: str) -> Optional[dict]:
        """
        Resolve a field name to its metadata dict containing line_id, field_id, etc.

        Args:
            field_name: Human-readable field name (e.g. "ACCOUNT_NO")

        Returns:
            Dict with 'name', 'line_id', 'field_id', 'start_column', 'end_column'
            or None if not found
        """
        return self._field_map.get(field_name.strip().upper())

    def list_indexed_fields(self) -> List[dict]:
        """Return all indexed fields from metadata."""
        return self.metadata.get('indexed_fields', [])

    def get_species_name(self) -> str:
        return self.species_name


# ============================================================================
# Binary Search on Sorted MAP Entries
# ============================================================================

def binary_search_entries(
    parser: MapFileParser,
    segment: MapSegmentInfo,
    search_value: str,
    prefix_match: bool = False
) -> List[IndexEntry]:
    """
    Binary search for a value in a MAP file segment's sorted entries.

    MAP file entries are sorted alphabetically by value within each segment.
    This performs O(log n) binary search instead of O(n) linear scan.

    Args:
        parser: MapFileParser with loaded data
        segment: The segment to search in
        search_value: Value to search for
        prefix_match: If True, match entries that start with search_value

    Returns:
        List of matching IndexEntry objects
    """
    if segment.field_width == 0 or segment.field_width > 100:
        return []

    entry_size = 7 + segment.field_width
    end_boundary = min(segment.offset + segment.size, len(parser.data))
    data_start = segment.data_offset
    available_bytes = end_boundary - data_start
    total_entries = available_bytes // entry_size if entry_size > 0 else 0

    if total_entries == 0:
        return []

    # First detect format by sampling entries
    is_u32_format = _detect_entry_format(parser, segment, entry_size, data_start,
                                          end_boundary, min(100, total_entries))

    # Pad search value to field_width for comparison (MAP values are space-padded)
    padded_search = search_value.ljust(segment.field_width)[:segment.field_width]

    # Binary search for first occurrence
    lo, hi = 0, total_entries - 1
    first_match = -1

    while lo <= hi:
        mid = (lo + hi) // 2
        offset = data_start + mid * entry_size

        if offset + entry_size > end_boundary:
            hi = mid - 1
            continue

        # Read length field
        length = struct.unpack('<H', parser.data[offset:offset + 2])[0]
        if length != segment.field_width:
            # Invalid entry — entries are contiguous, so this is beyond valid data
            hi = mid - 1
            continue

        # Read value
        text_start = offset + 2
        text_end = text_start + segment.field_width
        try:
            entry_value = parser.data[text_start:text_end].decode('ascii', errors='replace')
        except Exception:
            hi = mid - 1
            continue

        if prefix_match:
            # For prefix match, compare only the prefix portion
            entry_prefix = entry_value[:len(search_value)]
            search_prefix = search_value
            if entry_prefix < search_prefix:
                lo = mid + 1
            elif entry_prefix > search_prefix:
                hi = mid - 1
            else:
                first_match = mid
                hi = mid - 1  # Keep searching left for first match
        else:
            # Exact match (padded)
            if entry_value < padded_search:
                lo = mid + 1
            elif entry_value > padded_search:
                hi = mid - 1
            else:
                first_match = mid
                hi = mid - 1  # Keep searching left for first match

    if first_match == -1:
        return []

    # Collect all matching entries starting from first_match
    matches = []
    for i in range(first_match, total_entries):
        offset = data_start + i * entry_size
        if offset + entry_size > end_boundary:
            break

        length = struct.unpack('<H', parser.data[offset:offset + 2])[0]
        if length != segment.field_width:
            break

        text_start = offset + 2
        text_end = text_start + segment.field_width
        try:
            entry_value = parser.data[text_start:text_end].decode('ascii', errors='replace')
        except Exception:
            break

        stripped_value = entry_value.strip()

        if prefix_match:
            if not stripped_value.startswith(search_value.strip()):
                break
        else:
            if stripped_value != search_value.strip():
                break

        # Read trailing bytes
        trailing_start = text_end
        trailing = parser.data[trailing_start:trailing_start + 5]

        if is_u32_format:
            u32_val = struct.unpack('<I', trailing[0:4])[0]
            last_byte = trailing[4] if len(trailing) >= 5 else 0
            matches.append(IndexEntry(
                value=stripped_value,
                page_number=0,
                raw_length=length,
                raw_trailing=trailing,
                u32_index=u32_val,
                entry_format='u32_index'
            ))
        else:
            page = struct.unpack('<H', trailing[0:2])[0]
            matches.append(IndexEntry(
                value=stripped_value,
                page_number=page,
                raw_length=length,
                raw_trailing=trailing,
                u32_index=0,
                entry_format='page'
            ))

    return matches


def _detect_entry_format(
    parser: MapFileParser,
    segment: MapSegmentInfo,
    entry_size: int,
    data_start: int,
    end_boundary: int,
    sample_count: int
) -> bool:
    """
    Detect whether entries use page format (small files) or u32_index format (large files).

    Heuristic: read a sample of entries and check if all uint16 values at the
    trailing position are odd. If ALL are odd, it's u32_index format.

    Returns True if u32_index format, False if page format.
    """
    odd_count = 0
    valid_count = 0

    for i in range(sample_count):
        offset = data_start + i * entry_size
        if offset + entry_size > end_boundary:
            break

        length = struct.unpack('<H', parser.data[offset:offset + 2])[0]
        if length != segment.field_width:
            break

        trailing_start = offset + 2 + segment.field_width
        if trailing_start + 2 > end_boundary:
            break

        u16 = struct.unpack('<H', parser.data[trailing_start:trailing_start + 2])[0]
        valid_count += 1
        if u16 % 2 == 1:
            odd_count += 1

    # All sampled uint16 values odd AND meaningful sample → u32_index format
    return odd_count == valid_count and valid_count >= 3


# ============================================================================
# Page Resolution for u32_index Format (Large MAP Files)
# ============================================================================

def build_segment0_page_lookup(parser: MapFileParser) -> Dict[int, int]:
    """
    Build u32_join_key → page_number lookup from Segment 0 for large MAP files.

    In large MAP files, index entries use u32_index format where the 4-byte
    value is a join key into Segment 0's 15-byte record array.

    Segment 0 record format (15 bytes, little-endian):
      [page_number:4][rec_id_byte:1][type:1][pad:1][u32_join_key:4][u32_extra:4]

    Record types (byte 5):
      0x08 = data record (contains page mapping)
      0x0c = separator record (skip)

    The u32_join_key values are sequential odd numbers (1, 3, 5, 7...).

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

        page_raw = struct.unpack('<I', parser.data[offset:offset + 4])[0]
        rec_type = parser.data[offset + 5]
        u32_join_key = struct.unpack('<I', parser.data[offset + 7:offset + 11])[0]

        if rec_type == 0x08:  # data record
            page_number = page_raw & 0x7FFFFFFF  # mask off branch boundary flag
            lookup[u32_join_key] = page_number

        offset += record_size

    return lookup


def resolve_pages(entries: List[IndexEntry], parser: MapFileParser) -> List[dict]:
    """
    Resolve page numbers from MAP index entries.

    Handles both entry formats:
    - 'page' format: page_number is directly available
    - 'u32_index' format: resolve through Segment 0 lookup

    Returns list of dicts with 'value', 'page', 'u32_index' for each match.
    """
    results = []

    if not entries:
        return results

    fmt = entries[0].entry_format

    if fmt == 'page':
        for entry in entries:
            results.append({
                'value': entry.value,
                'page': entry.page_number,
                'u32_index': None,
                'format': 'page'
            })
    elif fmt == 'u32_index':
        seg0_lookup = build_segment0_page_lookup(parser)
        for entry in entries:
            page = seg0_lookup.get(entry.u32_index)
            results.append({
                'value': entry.value,
                'page': page if page else 0,
                'u32_index': entry.u32_index,
                'format': 'u32_index'
            })
        if not seg0_lookup:
            print("WARNING: Could not build Segment 0 page lookup for u32_index resolution",
                  file=sys.stderr)

    return results


# ============================================================================
# Output Formatters
# ============================================================================

def output_table(results: List[dict], field_info: dict = None, segment_info: dict = None):
    """Print results as a human-readable table."""
    if segment_info:
        print(f"\nSegment {segment_info.get('segment_index', '?')}: "
              f"LINE_ID={segment_info.get('line_id', '?')}, "
              f"FIELD_ID={segment_info.get('field_id', '?')}", end='')
        if field_info:
            print(f" ({field_info.get('name', '?')})", end='')
        print(f"\nField width: {segment_info.get('field_width', '?')}, "
              f"Entry count: {segment_info.get('entry_count', '?')}")

    if not results:
        print("\nNo matches found.")
        return

    print(f"\n{len(results)} match(es) found:\n")

    # Determine column widths
    val_width = max(len(r['value']) for r in results) if results else 10
    val_width = max(val_width, 5)

    if results[0].get('format') == 'u32_index':
        print(f"  {'VALUE':<{val_width}}  {'PAGE':>8}  {'U32_INDEX':>12}")
        print(f"  {'-' * val_width}  {'--------':>8}  {'------------':>12}")
        for r in results:
            page_str = str(r['page']) if r['page'] else '(unresolved)'
            print(f"  {r['value']:<{val_width}}  {page_str:>8}  {r['u32_index']:>12}")
    else:
        print(f"  {'VALUE':<{val_width}}  {'PAGE':>8}")
        print(f"  {'-' * val_width}  {'--------':>8}")
        for r in results:
            print(f"  {r['value']:<{val_width}}  {r['page']:>8}")


def output_csv(results: List[dict], output_path: str = None):
    """Write results as CSV."""
    if not results:
        return

    fieldnames = ['value', 'page']
    if results[0].get('format') == 'u32_index':
        fieldnames.append('u32_index')

    if output_path:
        f = open(output_path, 'w', newline='', encoding='utf-8')
    else:
        f = sys.stdout

    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    for r in results:
        writer.writerow(r)

    if output_path:
        f.close()
        print(f"Results written to {output_path}", file=sys.stderr)


def output_json(results: List[dict], field_info: dict = None,
                segment_info: dict = None, output_path: str = None):
    """Write results as JSON."""
    output = {
        'matches': results,
        'match_count': len(results),
    }
    if field_info:
        output['field'] = field_info.get('name', '')
        output['line_id'] = field_info.get('line_id')
        output['field_id'] = field_info.get('field_id')
    if segment_info:
        output['segment'] = segment_info.get('segment_index')
        output['entry_count'] = segment_info.get('entry_count')
        output['format'] = segment_info.get('entry_format', 'unknown')

    json_str = json.dumps(output, indent=2)

    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(json_str)
        print(f"Results written to {output_path}", file=sys.stderr)
    else:
        print(json_str)


# ============================================================================
# List Fields Mode
# ============================================================================

def list_fields(parser: MapFileParser, metadata: MetadataResolver = None):
    """
    List all indexed fields found in the MAP file.

    Enumerates segments 1+ from the MAP file, showing LINE_ID, FIELD_ID,
    field_width, and entry_count. If metadata is provided, enriches with
    human-readable field names.
    """
    if not parser.segments:
        parser.parse_segments()

    if not parser.segments or len(parser.segments) <= 1:
        print("No indexed field segments found in MAP file.")
        return

    header = parser.parse_header()
    if header:
        print(f"\nMAP File: {header.filename}")
        print(f"Date: {header.date_string}")
        print(f"Segment count: {header.segment_count}")

    if metadata:
        print(f"Species: {metadata.get_species_name()}")

    print(f"\nIndexed Fields ({len(parser.segments) - 1} segments):\n")

    if metadata:
        print(f"  {'SEG':>3}  {'LINE_ID':>7}  {'FIELD_ID':>8}  {'NAME':<20}  {'WIDTH':>5}  {'ENTRIES':>8}  {'COLUMNS'}")
        print(f"  {'---':>3}  {'-------':>7}  {'--------':>8}  {'----':<20}  {'-----':>5}  {'--------':>8}  {'-------'}")
    else:
        print(f"  {'SEG':>3}  {'LINE_ID':>7}  {'FIELD_ID':>8}  {'WIDTH':>5}  {'ENTRIES':>8}")
        print(f"  {'---':>3}  {'-------':>7}  {'--------':>8}  {'-----':>5}  {'--------':>8}")

    for seg in parser.segments[1:]:
        name = ''
        columns = ''
        if metadata:
            # Find matching field in metadata
            for f in metadata.list_indexed_fields():
                if f.get('line_id') == seg.line_id and f.get('field_id') == seg.field_id:
                    name = f.get('name', '')
                    sc = f.get('start_column', '')
                    ec = f.get('end_column', '')
                    if sc != '' and ec != '':
                        columns = f"{sc}-{ec}"
                    break

        if metadata:
            print(f"  {seg.index:>3}  {seg.line_id:>7}  {seg.field_id:>8}  {name:<20}  {seg.field_width:>5}  {seg.entry_count:>8}  {columns}")
        else:
            print(f"  {seg.index:>3}  {seg.line_id:>7}  {seg.field_id:>8}  {seg.field_width:>5}  {seg.entry_count:>8}")


# ============================================================================
# List Values Mode
# ============================================================================

def list_values(parser: MapFileParser, line_id: int, field_id: int,
                metadata: MetadataResolver = None, max_values: int = 0):
    """
    List all unique indexed values for a specific field.

    Reads all entries from the matching segment and shows unique values
    with occurrence counts.
    """
    if not parser.segments:
        parser.parse_segments()

    segment = parser.find_segment_for_field(line_id, field_id)
    if not segment:
        print(f"No segment found for LINE_ID={line_id}, FIELD_ID={field_id}", file=sys.stderr)
        return

    # Get field name from metadata if available
    field_name = f"LINE {line_id} / FIELD {field_id}"
    if metadata:
        for f in metadata.list_indexed_fields():
            if f.get('line_id') == line_id and f.get('field_id') == field_id:
                field_name = f.get('name', field_name)
                break

    entries = parser.read_index_entries(segment, max_entries=max_values if max_values > 0 else 0)

    # Count unique values
    value_counts: Dict[str, int] = {}
    for entry in entries:
        value_counts[entry.value] = value_counts.get(entry.value, 0) + 1

    sorted_values = sorted(value_counts.items())

    print(f"\nField: {field_name} (LINE_ID={line_id}, FIELD_ID={field_id})")
    print(f"Total entries: {len(entries)}, Unique values: {len(sorted_values)}")
    print(f"\n  {'VALUE':<{segment.field_width + 2}}  {'COUNT':>6}")
    print(f"  {'-' * (segment.field_width + 2)}  {'------':>6}")

    for value, count in sorted_values:
        print(f"  {value:<{segment.field_width + 2}}  {count:>6}")


# ============================================================================
# Main Search Function
# ============================================================================

def do_search(
    map_path: str,
    line_id: int,
    field_id: int,
    search_value: str,
    prefix_match: bool = False,
    metadata: MetadataResolver = None,
    output_format: str = 'table',
    output_path: str = None
):
    """
    Main search function.

    Args:
        map_path: Path to MAP file
        line_id: LINE_ID of the indexed field
        field_id: FIELD_ID of the indexed field
        search_value: Value to search for
        prefix_match: If True, match entries starting with search_value
        metadata: Optional MetadataResolver for field name enrichment
        output_format: 'table', 'csv', or 'json'
        output_path: Optional output file path
    """
    t0 = time.time()

    # Load and parse MAP file
    parser = MapFileParser(map_path)
    if not parser.load():
        print(f"ERROR: Failed to load MAP file: {map_path}", file=sys.stderr)
        sys.exit(1)

    parser.parse_segments()

    # Find target segment
    segment = parser.find_segment_for_field(line_id, field_id)
    if not segment:
        print(f"ERROR: No segment found for LINE_ID={line_id}, FIELD_ID={field_id}",
              file=sys.stderr)
        print(f"\nAvailable segments:", file=sys.stderr)
        for seg in parser.segments[1:]:
            print(f"  Segment {seg.index}: LINE_ID={seg.line_id}, FIELD_ID={seg.field_id}",
                  file=sys.stderr)
        sys.exit(1)

    # Build field info dict
    field_info = {'line_id': line_id, 'field_id': field_id, 'name': f"L{line_id}/F{field_id}"}
    if metadata:
        resolved = metadata.resolve_field_by_ids(line_id, field_id) if hasattr(metadata, 'resolve_field_by_ids') else None
        if not resolved:
            for f in metadata.list_indexed_fields():
                if f.get('line_id') == line_id and f.get('field_id') == field_id:
                    field_info = f
                    break

    segment_info = {
        'segment_index': segment.index,
        'line_id': segment.line_id,
        'field_id': segment.field_id,
        'field_width': segment.field_width,
        'entry_count': segment.entry_count,
        'entry_format': 'unknown'
    }

    # Search using binary search
    matches = binary_search_entries(parser, segment, search_value, prefix_match)

    t1 = time.time()

    # Resolve pages
    results = resolve_pages(matches, parser)

    if results:
        segment_info['entry_format'] = results[0].get('format', 'unknown')

    # Add timing info
    elapsed_ms = (t1 - t0) * 1000

    # Output
    if output_format == 'table':
        output_table(results, field_info, segment_info)
        print(f"\nSearch completed in {elapsed_ms:.1f}ms")
    elif output_format == 'csv':
        output_csv(results, output_path)
    elif output_format == 'json':
        output_json(results, field_info, segment_info, output_path)


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Standalone MAP file index search tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search by raw IDs (no metadata needed):
  python papyrus_rpt_search.py --map 25001002.MAP --line-id 5 --field-id 3 --value "200-044295-001"

  # Search by field name (requires metadata JSON):
  python papyrus_rpt_search.py --map 25001002.MAP --metadata DDU017P_metadata.json --field ACCOUNT_NO --value "200-044295-001"

  # Prefix search:
  python papyrus_rpt_search.py --map 25001002.MAP --line-id 5 --field-id 3 --value "200-044" --prefix

  # List all indexed fields:
  python papyrus_rpt_search.py --map 25001002.MAP --list-fields

  # List all values for a field:
  python papyrus_rpt_search.py --map 25001002.MAP --line-id 5 --field-id 3 --list-values

  # Output as JSON:
  python papyrus_rpt_search.py --map 25001002.MAP --line-id 5 --field-id 3 --value "200-044295-001" --format json
        """)

    # MAP file specification
    parser.add_argument('--map', required=True, help='Path to MAP file')

    # Metadata (optional)
    parser.add_argument('--metadata', help='Path to species metadata JSON file')

    # Field specification (by name or raw IDs)
    field_group = parser.add_argument_group('Field specification')
    field_group.add_argument('--field', help='Field name (requires --metadata)')
    field_group.add_argument('--line-id', type=int, help='LINE_ID (raw numeric)')
    field_group.add_argument('--field-id', type=int, help='FIELD_ID (raw numeric)')

    # Search
    search_group = parser.add_argument_group('Search')
    search_group.add_argument('--value', help='Value to search for')
    search_group.add_argument('--prefix', action='store_true',
                              help='Enable prefix matching (default: exact)')

    # Listing modes
    list_group = parser.add_argument_group('Listing modes')
    list_group.add_argument('--list-fields', action='store_true',
                            help='List all indexed fields in the MAP file')
    list_group.add_argument('--list-values', action='store_true',
                            help='List all values for the specified field')
    list_group.add_argument('--max-values', type=int, default=0,
                            help='Max values to list (0 = all)')

    # Output
    output_group = parser.add_argument_group('Output')
    output_group.add_argument('--format', choices=['table', 'csv', 'json'],
                              default='table', help='Output format (default: table)')
    output_group.add_argument('--output', help='Output file path')

    args = parser.parse_args()

    # Validate MAP file exists
    if not os.path.isfile(args.map):
        print(f"ERROR: MAP file not found: {args.map}", file=sys.stderr)
        sys.exit(1)

    # Load metadata if provided
    metadata = None
    if args.metadata:
        if not os.path.isfile(args.metadata):
            print(f"ERROR: Metadata file not found: {args.metadata}", file=sys.stderr)
            sys.exit(1)
        metadata = MetadataResolver(args.metadata)

    # === Mode: List fields ===
    if args.list_fields:
        p = MapFileParser(args.map)
        if not p.load():
            print(f"ERROR: Failed to load MAP file: {args.map}", file=sys.stderr)
            sys.exit(1)
        p.parse_segments()
        list_fields(p, metadata)
        return

    # === Resolve field specification ===
    line_id = args.line_id
    field_id = args.field_id

    if args.field:
        # Resolve field name via metadata
        if not metadata:
            print("ERROR: --field requires --metadata to resolve field names.", file=sys.stderr)
            print("Use --line-id and --field-id for raw ID mode (no metadata needed).",
                  file=sys.stderr)
            sys.exit(1)

        resolved = metadata.resolve_field(args.field)
        if not resolved:
            print(f"ERROR: Field '{args.field}' not found in metadata for "
                  f"species '{metadata.get_species_name()}'.", file=sys.stderr)
            print(f"\nAvailable indexed fields:", file=sys.stderr)
            for f in metadata.list_indexed_fields():
                print(f"  {f['name']} (LINE_ID={f['line_id']}, FIELD_ID={f['field_id']})",
                      file=sys.stderr)
            sys.exit(1)

        line_id = resolved['line_id']
        field_id = resolved['field_id']
        print(f"Resolved '{args.field}' → LINE_ID={line_id}, FIELD_ID={field_id}",
              file=sys.stderr)

    # Check that we have field IDs
    if line_id is None or field_id is None:
        if not args.list_values:
            print("ERROR: Must specify either --field NAME (with --metadata) "
                  "or --line-id N --field-id N", file=sys.stderr)
            sys.exit(1)
        else:
            print("ERROR: --list-values requires --line-id and --field-id (or --field with --metadata)",
                  file=sys.stderr)
            sys.exit(1)

    # === Mode: List values ===
    if args.list_values:
        p = MapFileParser(args.map)
        if not p.load():
            print(f"ERROR: Failed to load MAP file: {args.map}", file=sys.stderr)
            sys.exit(1)
        p.parse_segments()
        list_values(p, line_id, field_id, metadata, args.max_values)
        return

    # === Mode: Search ===
    if not args.value:
        print("ERROR: --value is required for search mode.", file=sys.stderr)
        print("Use --list-fields to see available fields, or --list-values to see all values.",
              file=sys.stderr)
        sys.exit(1)

    do_search(
        map_path=args.map,
        line_id=line_id,
        field_id=field_id,
        search_value=args.value,
        prefix_match=args.prefix,
        metadata=metadata,
        output_format=args.format,
        output_path=args.output
    )


if __name__ == '__main__':
    main()
