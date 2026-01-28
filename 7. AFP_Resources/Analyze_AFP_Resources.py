#!/usr/bin/env python3
"""
Analyze_AFP_Resources.py - IntelliSTOR AFP Resource Analyzer

Scans AFP (Advanced Function Presentation) resources across multiple versions
and generates a comprehensive CSV report. Auto-detects folder structures
(flat vs. namespace-based) and aggregates resources by filename with version tracking.

AFP Resource Types Supported:
- Codepage (T1*.RCP)
- CharSet_Raster (C0*.RCS)
- CharSet_Outline (C1*.RCS, CZ*.RCS)
- Font_Raster (X0*)
- Font_Outline (XZ*)
- Formdef (F1*.RFD)
- PageDef (P1*.RPD)
- PageSegment (S1*.RPS)

Folder Structure Support:
1. Flat Structure:
   base_folder/
   ├── YYYY_MM_DD_HH/  (version folders)
   │   ├── *.RCS
   │   ├── *.RFD
   │   └── *.RPD
   └── ...

2. Namespace Structure:
   base_folder/
   ├── NamespaceA/
   │   ├── YYYY_MM_DD_HH/
   │   └── ...
   └── NamespaceB/
       └── ...

Output CSV Structure:
NameSpace,Folder,Resource_Filename,Resource_Type,V1,V2,V3,...
- V1 = newest version, V2 = second newest, etc.
- Dynamic version columns based on maximum versions found
- Sorted by Resource_Filename alphabetically

Author: Generated for OCBC IntelliSTOR Migration
Date: 2026-01-26
"""

import argparse
import csv
import logging
import os
import re
import sys
import zlib
from pathlib import Path
from typing import Dict, List, Tuple, Any


# ============================================================================
# Configuration and Constants
# ============================================================================

# AFP Resource Type Mapping (Prefix-based, 2 characters)
PREFIX_TYPE_MAP = {
    'T1': 'Codepage',
    'C0': 'CharSet_Raster',
    'C1': 'CharSet_Outline',
    'CZ': 'CharSet_Outline',
    'X0': 'Font_Raster',
    'XZ': 'Font_Outline',
    'F1': 'Formdef',
    'P1': 'PageDef',
    'S1': 'PageSegment'
}

# AFP Resource Type Mapping (Extension-based fallback)
EXTENSION_TYPE_MAP = {
    '.RCP': 'Codepage',
    '.RCS': 'CharSet',  # Generic - prefer prefix detection
    '.RFD': 'Formdef',
    '.RPD': 'PageDef',
    '.RPS': 'PageSegment'
}

# Version folder pattern: YYYY_MM_DD_HH
VERSION_FOLDER_PATTERN = re.compile(r'^\d{4}_\d{2}_\d{2}_\d{2}$')


# ============================================================================
# Logging Setup
# ============================================================================

def setup_logging(output_dir: str, quiet: bool = False) -> logging.Logger:
    """
    Setup logging to both console and file.

    Args:
        output_dir: Directory where log file will be created
        quiet: If True, disable console logging

    Returns:
        Configured logger instance
    """
    log_file = os.path.join(output_dir, 'Analyze_AFP_Resources.log')

    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter('%(levelname)s - %(message)s')

    # File handler (DEBUG level)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    # Console handler (INFO level) - only if not quiet
    if not quiet:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    return logger


# ============================================================================
# Argument Parsing
# ============================================================================

def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Analyze AFP resources across versioned folders and generate CSV report',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Flat structure with default namespace
  python Analyze_AFP_Resources.py --folder "C:\\Users\\freddievr\\Downloads\\afp\\afp" --output-csv "C:\\Output\\afp_resources.csv"

  # With optional namespace parameter (used as default for flat structure)
  python Analyze_AFP_Resources.py --namespace BB --folder "C:\\Users\\freddievr\\Downloads\\afp\\afp" --output-csv "afp_resources.csv"

  # Quiet mode
  python Analyze_AFP_Resources.py --folder "C:\\Users\\freddievr\\Downloads\\afp\\afp" --output-csv "afp_resources.csv" --quiet

  # Namespace structure (auto-detected)
  python Analyze_AFP_Resources.py --folder "C:\\Users\\freddievr\\Downloads\\afp\\afp" --output-csv "afp_resources.csv"
"""
    )

    parser.add_argument(
        '--folder',
        required=True,
        help='Base folder containing version folders or namespace subfolders'
    )

    parser.add_argument(
        '--output-csv',
        required=True,
        help='Output CSV file path (e.g., "C:\\Output\\afp_resources.csv")'
    )

    parser.add_argument(
        '--namespace',
        default='DEFAULT',
        help='Default namespace name for flat structure (default: DEFAULT)'
    )

    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Quiet mode - disable console logging'
    )

    parser.add_argument(
        '--version-compare',
        action='store_true',
        help='Enable binary content comparison using CRC32. Only list versions with different content.'
    )

    return parser.parse_args()


# ============================================================================
# Resource Type Detection
# ============================================================================

def parse_resource_type(filename: str) -> str:
    """
    Determine AFP resource type from filename.

    Priority: Prefix (first 2 characters) > Extension

    Args:
        filename: Resource filename (e.g., 'C0ARL05B.RCS')

    Returns:
        Resource type string (e.g., 'CharSet_Raster') or 'Unknown'

    Examples:
        >>> parse_resource_type('C0ARL05B.RCS')
        'CharSet_Raster'
        >>> parse_resource_type('C1ARL05B.RCS')
        'CharSet_Outline'
        >>> parse_resource_type('F1ABR10.RFD')
        'Formdef'
        >>> parse_resource_type('P1PRSDEF.RPD')
        'PageDef'
        >>> parse_resource_type('T1CDPG01.RCP')
        'Codepage'
        >>> parse_resource_type('README.txt')
        'Unknown'
    """
    # Check prefix (first 2 characters)
    if len(filename) >= 2:
        prefix = filename[:2].upper()
        if prefix in PREFIX_TYPE_MAP:
            return PREFIX_TYPE_MAP[prefix]

    # Fallback to extension
    ext = os.path.splitext(filename)[1].upper()
    if ext in EXTENSION_TYPE_MAP:
        return EXTENSION_TYPE_MAP[ext]

    return 'Unknown'


# ============================================================================
# Folder Structure Detection
# ============================================================================

def detect_folder_structure(base_folder: str, default_namespace: str = 'DEFAULT') -> Dict[str, Any]:
    """
    Auto-detect folder structure and return namespace mapping.

    Detection Logic:
    1. List immediate subfolders
    2. Check if subfolders match version pattern (YYYY_MM_DD_HH)
    3. If yes → Flat structure (use default_namespace)
    4. If no → Check subfolders for nested version folders
    5. If nested found → Namespace structure (scan all namespace subfolders)
    6. Sort version folders in descending order (newest first)

    Args:
        base_folder: Base folder path to analyze
        default_namespace: Namespace name to use for flat structure

    Returns:
        {
            'pattern': 'flat' | 'namespace',
            'namespaces': {
                'namespace_name': [version_folder_paths],  # sorted descending
                ...
            }
        }

    Raises:
        ValueError: If no valid version folders found
    """
    base_path = Path(base_folder)

    if not base_path.exists():
        raise ValueError(f"Base folder does not exist: {base_folder}")

    if not base_path.is_dir():
        raise ValueError(f"Base folder is not a directory: {base_folder}")

    # List immediate subfolders
    subfolders = [f for f in base_path.iterdir() if f.is_dir()]

    if not subfolders:
        raise ValueError(f"No subfolders found in base folder: {base_folder}")

    # Check if immediate subfolders are version folders (flat structure)
    version_folders = []
    for subfolder in subfolders:
        if VERSION_FOLDER_PATTERN.match(subfolder.name):
            version_folders.append(subfolder)

    if version_folders:
        # Flat structure detected
        # Sort version folders in descending order (newest first)
        version_folders.sort(key=lambda x: x.name, reverse=True)

        return {
            'pattern': 'flat',
            'namespaces': {
                default_namespace: version_folders
            }
        }

    # No version folders found at root level
    # Check for namespace structure (version folders nested in subfolders)
    namespace_mapping = {}

    for subfolder in subfolders:
        nested_folders = [f for f in subfolder.iterdir() if f.is_dir()]
        nested_version_folders = [
            f for f in nested_folders
            if VERSION_FOLDER_PATTERN.match(f.name)
        ]

        if nested_version_folders:
            # Sort version folders in descending order (newest first)
            nested_version_folders.sort(key=lambda x: x.name, reverse=True)
            namespace_mapping[subfolder.name] = nested_version_folders

    if namespace_mapping:
        # Namespace structure detected
        return {
            'pattern': 'namespace',
            'namespaces': namespace_mapping
        }

    # No valid structure found
    raise ValueError(
        f"No valid folder structure found in {base_folder}. "
        f"Expected version folders (YYYY_MM_DD_HH) at root level or in namespace subfolders."
    )


# ============================================================================
# AFP Resource Analyzer
# ============================================================================

class AFPResourceAnalyzer:
    """
    Main analyzer class for AFP resources.

    Scans version folders, aggregates resources by filename,
    tracks versions, and generates CSV report.
    """

    def __init__(self, base_folder: str, output_csv: str, namespace: str = 'DEFAULT'):
        """
        Initialize AFP Resource Analyzer.

        Args:
            base_folder: Base folder containing version folders
            output_csv: Output CSV file path
            namespace: Default namespace for flat structure
        """
        self.base_folder = base_folder
        self.output_csv = output_csv
        self.default_namespace = namespace
        self.version_compare = False  # Set from args

        # Statistics tracking
        self.stats = {
            'namespaces_found': 0,
            'version_folders_scanned': 0,
            'total_files_scanned': 0,
            'resources_identified': 0,
            'unique_resources': 0,
            'max_versions_per_resource': 0,
            'unknown_files_skipped': 0,
            'versions_before_dedup': 0,
            'versions_after_dedup': 0,
            'duplicate_versions_removed': 0
        }

        # Data structures
        self.folder_structure = None
        self.aggregated_resources = {}  # {namespace: {filename: {type, versions[]}}}

    def analyze(self) -> None:
        """
        Main entry point - executes full analysis workflow.

        Workflow:
        1. Validate inputs
        2. Detect folder structure
        3. Scan version folders
        4. Aggregate resources
        5. Generate CSV
        6. Print statistics
        """
        logging.info("=" * 70)
        logging.info("AFP Resource Analyzer - Starting")
        logging.info("=" * 70)
        logging.info(f"Base folder: {self.base_folder}")
        logging.info(f"Output CSV: {self.output_csv}")

        # Step 1: Validate inputs
        self._validate_inputs()

        # Step 2: Detect folder structure
        self.folder_structure = detect_folder_structure(
            self.base_folder,
            self.default_namespace
        )

        logging.info(f"Detected folder structure: {self.folder_structure['pattern']}")
        logging.info(f"Found {len(self.folder_structure['namespaces'])} namespace(s): {', '.join(self.folder_structure['namespaces'].keys())}")

        # Count total version folders
        total_version_folders = sum(
            len(folders) for folders in self.folder_structure['namespaces'].values()
        )
        logging.info(f"Found {total_version_folders} version folder(s)")

        # Step 3 & 4: Scan and aggregate resources
        self._scan_and_aggregate()

        # Step 4b: Filter versions by content (if enabled)
        if self.version_compare:
            logging.info("Filtering versions by content using CRC32...")
            self._filter_versions_by_content()
            logging.info(f"Version filtering complete: {self.stats['duplicate_versions_removed']} duplicate(s) removed")

        # Step 5: Generate CSV
        self._generate_csv()

        # Step 6: Print statistics
        self._print_statistics()

    def _validate_inputs(self) -> None:
        """Validate input parameters."""
        # Validate base folder
        if not os.path.exists(self.base_folder):
            raise ValueError(f"Base folder does not exist: {self.base_folder}")

        if not os.path.isdir(self.base_folder):
            raise ValueError(f"Base folder is not a directory: {self.base_folder}")

        # Validate output CSV path
        output_dir = os.path.dirname(os.path.abspath(self.output_csv))
        if not os.path.exists(output_dir):
            raise ValueError(f"Output directory does not exist: {output_dir}")

        # Check if output directory is writable
        if not os.access(output_dir, os.W_OK):
            raise ValueError(f"Output directory is not writable: {output_dir}")

    def _calculate_crc32(self, file_path: str) -> int:
        """
        Calculate CRC32 checksum for file content.

        Args:
            file_path: Absolute path to file

        Returns:
            CRC32 checksum as integer
        """
        crc = 0
        with open(file_path, 'rb') as f:
            while chunk := f.read(65536):  # 64KB chunks
                crc = zlib.crc32(chunk, crc)
        return crc & 0xffffffff

    def _scan_and_aggregate(self) -> None:
        """
        Scan version folders and aggregate resources.

        Builds aggregated_resources structure:
        {
            'namespace': {
                'filename.ext': {
                    'type': 'ResourceType',
                    'versions': [('2024_12_27_16', 'path'), ('2023_11_30_09', 'path'), ...]
                }
            }
        }
        """
        for namespace, version_folders in self.folder_structure['namespaces'].items():
            if namespace not in self.aggregated_resources:
                self.aggregated_resources[namespace] = {}

            logging.info(f"Scanning namespace: {namespace} ({len(version_folders)} version folders)")

            for idx, version_folder in enumerate(version_folders, 1):
                version_name = version_folder.name

                # Progress reporting
                if not logging.getLogger().handlers[0].stream.isatty():
                    # Not a terminal, use regular logging
                    logging.debug(f"Scanning {version_name} ({idx}/{len(version_folders)})")
                else:
                    # Terminal, use carriage return for same-line updates
                    print(f"\rScanning {version_name}: {idx}/{len(version_folders)} version folders...",
                          end='', flush=True)

                self.stats['version_folders_scanned'] += 1

                # Scan files in version folder
                try:
                    files = list(version_folder.iterdir())

                    for file_path in files:
                        if not file_path.is_file():
                            continue

                        self.stats['total_files_scanned'] += 1
                        filename = file_path.name

                        # Determine resource type
                        resource_type = parse_resource_type(filename)

                        if resource_type == 'Unknown':
                            self.stats['unknown_files_skipped'] += 1
                            logging.debug(f"Skipping unknown file: {filename}")
                            continue

                        self.stats['resources_identified'] += 1

                        # Add to aggregated structure
                        if filename not in self.aggregated_resources[namespace]:
                            self.aggregated_resources[namespace][filename] = {
                                'type': resource_type,
                                'versions': []
                            }

                        # Calculate CRC if version comparison is enabled
                        crc32_value = None
                        if self.version_compare:
                            try:
                                crc32_value = self._calculate_crc32(str(file_path))
                            except Exception as e:
                                logging.warning(f"Failed to calculate CRC for {filename}: {e}")

                        # Append version tuple (now includes CRC)
                        self.aggregated_resources[namespace][filename]['versions'].append(
                            (version_name, str(file_path), crc32_value)
                        )

                except Exception as e:
                    logging.warning(f"Error scanning folder {version_folder}: {e}")
                    continue

            # Clear progress line
            if logging.getLogger().handlers[0].stream.isatty():
                print()  # New line after progress

        # Calculate statistics
        self.stats['namespaces_found'] = len(self.aggregated_resources)
        self.stats['unique_resources'] = sum(
            len(resources) for resources in self.aggregated_resources.values()
        )

        # Calculate max versions
        max_versions = 0
        for namespace_resources in self.aggregated_resources.values():
            for resource_data in namespace_resources.values():
                max_versions = max(max_versions, len(resource_data['versions']))
        self.stats['max_versions_per_resource'] = max_versions

        # Track versions before deduplication
        self.stats['versions_before_dedup'] = sum(
            len(res['versions']) for ns in self.aggregated_resources.values()
            for res in ns.values()
        )

        logging.info(f"Aggregation complete: {self.stats['unique_resources']} unique resource(s) identified")

    def _filter_versions_by_content(self) -> None:
        """
        Filter versions to keep only those with different content.

        Processes each resource's versions from newest to oldest,
        keeping only versions where CRC differs from BOTH:
        1. The immediately previous kept version
        2. V1 (the current/newest version)

        This eliminates:
        - Sequential duplicates (same as previous version)
        - Reversions (versions that match V1 content)

        Updates aggregated_resources in place.
        """
        if not self.version_compare:
            return

        for namespace, resources in self.aggregated_resources.items():
            for filename, resource_data in resources.items():
                original_count = len(resource_data['versions'])

                if original_count <= 1:
                    continue

                # Filter: keep V1 (always) + versions different from both previous AND V1
                filtered_versions = []
                v1_crc = None  # CRC of V1 (newest/current version)
                prev_kept_crc = None  # CRC of last kept version

                for idx, (version_name, file_path, crc32_value) in enumerate(resource_data['versions']):
                    # First version (V1) - always keep
                    if idx == 0:
                        filtered_versions.append((version_name, file_path, crc32_value))
                        v1_crc = crc32_value
                        prev_kept_crc = crc32_value
                        continue

                    # For subsequent versions: check against both previous kept AND V1
                    different_from_prev = (crc32_value != prev_kept_crc)
                    different_from_v1 = (crc32_value != v1_crc)

                    if different_from_prev and different_from_v1:
                        # Keep this version - it's different from both
                        filtered_versions.append((version_name, file_path, crc32_value))
                        prev_kept_crc = crc32_value
                        logging.debug(f"Keeping version {version_name} for {filename} (CRC: {crc32_value}, different from both previous and V1)")
                    else:
                        # Skip - matches either previous kept version or V1
                        if not different_from_prev:
                            logging.debug(f"Skipping version {version_name} for {filename} (CRC: {crc32_value}, same as previous version)")
                        elif not different_from_v1:
                            logging.debug(f"Skipping version {version_name} for {filename} (CRC: {crc32_value}, same as V1)")

                # Update versions list
                resource_data['versions'] = filtered_versions

                # Track statistics
                removed = original_count - len(filtered_versions)
                if removed > 0:
                    self.stats['duplicate_versions_removed'] += removed
                    logging.debug(f"{filename}: {original_count} versions -> {len(filtered_versions)} unique versions ({removed} removed)")

        # Update statistics
        self.stats['versions_after_dedup'] = sum(
            len(res['versions']) for ns in self.aggregated_resources.values()
            for res in ns.values()
        )

    def _generate_csv(self) -> None:
        """
        Generate CSV report with dynamic version columns.

        CSV Structure:
        NameSpace,Folder,Resource_Filename,Resource_Type,V1,V2,V3,...
        """
        max_versions = self.stats['max_versions_per_resource']

        # Build fieldnames
        fieldnames = [
            'NameSpace',
            'Folder',
            'Resource_Filename',
            'Resource_Type',
            '# Versions'
        ]
        fieldnames.extend([f'V{i+1}' for i in range(max_versions)])

        # Build rows
        rows = []
        for namespace, resources in self.aggregated_resources.items():
            # Sort resources by filename
            sorted_filenames = sorted(resources.keys())

            for filename in sorted_filenames:
                resource_data = resources[filename]

                row = {
                    'NameSpace': namespace,
                    'Folder': self.base_folder,
                    'Resource_Filename': filename,
                    'Resource_Type': resource_data['type'],
                    '# Versions': len(resource_data['versions'])
                }

                # Add version columns (extract just the version name from tuple)
                for i, version_tuple in enumerate(resource_data['versions']):
                    version_name = version_tuple[0]  # Extract just the version name
                    row[f'V{i+1}'] = version_name

                # Fill remaining version columns with empty strings
                for i in range(len(resource_data['versions']), max_versions):
                    row[f'V{i+1}'] = ''

                rows.append(row)

        # Write CSV
        logging.info(f"Writing CSV with {len(rows)} row(s), {max_versions} version column(s)")

        with open(self.output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        logging.info(f"CSV file created: {self.output_csv}")

    def _print_statistics(self) -> None:
        """Print analysis statistics."""
        logging.info("=" * 70)
        logging.info("ANALYSIS COMPLETE")
        logging.info("Statistics:")
        logging.info(f"  Namespaces: {self.stats['namespaces_found']}")
        logging.info(f"  Version folders scanned: {self.stats['version_folders_scanned']}")
        logging.info(f"  Total files scanned: {self.stats['total_files_scanned']}")
        logging.info(f"  Resources identified: {self.stats['resources_identified']}")
        logging.info(f"  Unique resources: {self.stats['unique_resources']}")
        logging.info(f"  Max versions per resource: {self.stats['max_versions_per_resource']}")
        logging.info(f"  Unknown files skipped: {self.stats['unknown_files_skipped']}")
        if self.version_compare:
            logging.info(f"  Versions before dedup: {self.stats['versions_before_dedup']}")
            logging.info(f"  Versions after dedup: {self.stats['versions_after_dedup']}")
            logging.info(f"  Duplicate versions removed: {self.stats['duplicate_versions_removed']}")
        logging.info("=" * 70)


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point."""
    # Parse arguments
    args = parse_arguments()

    # Setup logging (output directory is parent of output CSV)
    output_dir = os.path.dirname(os.path.abspath(args.output_csv))
    logger = setup_logging(output_dir, args.quiet)

    try:
        # Create analyzer
        analyzer = AFPResourceAnalyzer(
            base_folder=args.folder,
            output_csv=args.output_csv,
            namespace=args.namespace
        )
        analyzer.version_compare = args.version_compare

        # Run analysis
        analyzer.analyze()

        # Print summary in quiet mode
        if args.quiet:
            print(f"Completed: {analyzer.stats['unique_resources']} unique resources, "
                  f"{analyzer.stats['version_folders_scanned']} versions")

        return 0

    except KeyboardInterrupt:
        logging.error("\nOperation cancelled by user")
        return 130

    except Exception as e:
        logging.error(f"Error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
