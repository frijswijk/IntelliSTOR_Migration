#!/usr/bin/env python3
"""
Extract Unique RIDs from Permissions CSV Files

This script reads three permission CSV files from a specified folder:
  1. STYPE_FOLDER_ACCESS.csv
  2. STYPE_REPORT_SPECIES_ACCESS.csv
  3. STYPE_SECTION_ACCESS.csv

Extracts all unique RIDs (Relative IDs) from the RID column and outputs
them to a new CSV file with deduplication and sorting.

Usage:
  python3 extract_unique_rids.py <folder_path>
  python3 extract_unique_rids.py <folder_path> --output <output_file>

Example:
  python3 extract_unique_rids.py /path/to/Users_SG
  python3 extract_unique_rids.py /path/to/Users_SG --output my_rids.csv
"""

import csv
import sys
import argparse
from pathlib import Path
from typing import Set


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Extract unique RIDs from permissions CSV files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 extract_unique_rids.py /path/to/Users_SG
  python3 extract_unique_rids.py /path/to/Users_SG --output my_rids.csv

Input Files (expected in the folder):
  - STYPE_FOLDER_ACCESS.csv
  - STYPE_REPORT_SPECIES_ACCESS.csv
  - STYPE_SECTION_ACCESS.csv

Output:
  - Unique_RIDs.csv (or custom filename with --output)
        """
    )

    parser.add_argument(
        'folder',
        help='Path to folder containing the CSV files'
    )
    parser.add_argument(
        '--output', '-o',
        default='Unique_RIDs.csv',
        help='Output CSV filename (default: Unique_RIDs.csv)'
    )

    return parser.parse_args()


def extract_rids_from_files(folder_path: Path) -> Set[str]:
    """
    Extract all unique RIDs from the three permission CSV files.

    Args:
        folder_path: Path to folder containing CSV files

    Returns:
        Set of unique RID strings

    Raises:
        FileNotFoundError: If any required CSV file is not found
    """
    csv_files = [
        'STYPE_FOLDER_ACCESS.csv',
        'STYPE_REPORT_SPECIES_ACCESS.csv',
        'STYPE_SECTION_ACCESS.csv'
    ]

    all_rids = set()

    for filename in csv_files:
        filepath = folder_path / filename

        if not filepath.exists():
            raise FileNotFoundError(f'CSV file not found: {filepath}')

        print(f'Processing {filename}...')

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                if not reader.fieldnames or 'RID' not in reader.fieldnames:
                    raise ValueError(f'RID column not found in {filename}')

                row_count = 0
                for row in reader:
                    row_count += 1
                    rid_str = row.get('RID', '').strip()

                    if rid_str:
                        # Split by pipe delimiter in case there are multiple RIDs
                        rids = [r.strip() for r in rid_str.split('|') if r.strip()]
                        all_rids.update(rids)

                print(f'  Rows processed: {row_count}')
                print(f'  Unique RIDs so far: {len(all_rids)}')

        except Exception as e:
            print(f'Error processing {filename}: {e}', file=sys.stderr)
            raise

    return all_rids


def write_unique_rids(rids: Set[str], output_path: Path) -> None:
    """
    Write unique RIDs to a CSV file (sorted numerically).

    Args:
        rids: Set of RID strings
        output_path: Path to output CSV file
    """
    # Sort RIDs numerically
    sorted_rids = sorted(rids, key=lambda x: int(x) if x.isdigit() else float('inf'))

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['RID'])
        for rid in sorted_rids:
            writer.writerow([rid])

    print(f'\nOutput written to: {output_path}')
    print(f'Total unique RIDs: {len(sorted_rids)}')


def main():
    """Main entry point."""
    args = parse_arguments()

    # Validate folder path
    folder_path = Path(args.folder)
    if not folder_path.exists():
        print(f'Error: Folder not found: {folder_path}', file=sys.stderr)
        sys.exit(1)

    if not folder_path.is_dir():
        print(f'Error: Path is not a directory: {folder_path}', file=sys.stderr)
        sys.exit(1)

    try:
        # Extract RIDs
        print(f'Reading CSV files from: {folder_path}\n')
        all_rids = extract_rids_from_files(folder_path)

        # Write output
        output_path = folder_path / args.output
        write_unique_rids(all_rids, output_path)

        print('\nSuccess!')
        sys.exit(0)

    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
