#!/usr/bin/env python3
"""
AFP_Resource_Exporter.py - IntelliSTOR AFP Resource Exporter

Reads CSV output from Analyze_AFP_Resources.py and exports AFP resource files
to a target folder. Copies V1 (current version) files to the root folder and
creates version-specific subfolders for V2, V3, etc. when multiple versions exist.

Export Structure:
    output_folder/
    ├── SG/                    (namespace folder)
    │   ├── ResourceA.RCS      (V1 - current version)
    │   ├── ResourceB.RFD      (V1 - current version)
    │   ├── 2019_08_13_17/    (V2 folder - created only if V2 exists)
    │   │   ├── ResourceA.RCS  (older version)
    │   │   └── ResourceC.RPD
    │   └── 2018_10_26_14/    (V3 folder - created only if V3 exists)
    │       └── ResourceD.RPS
    └── DEFAULT/               (another namespace folder)
        └── ResourceE.RCS

Key Features:
- Reads CSV inventory from Analyze_AFP_Resources.py
- Copies V1 files to output folder root
- Creates subfolders for V2, V3, etc. when multiple versions exist
- Handles both CSV formats (with/without "# Versions" column)
- Provides comprehensive logging and statistics
- Supports --quiet mode
- Error handling for missing files

Author: Generated for OCBC IntelliSTOR Migration
Date: 2026-01-27
"""

import argparse
import csv
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Any


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
    log_file = os.path.join(output_dir, 'AFP_Resource_Exporter.log')

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
        description='Export AFP resources from version folders based on CSV inventory',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic export
  python AFP_Resource_Exporter.py --input-csv "C:\\Output\\AFP_Resources_SG.csv" --output-folder "C:\\Export\\AFP_SG"

  # Quiet mode
  python AFP_Resource_Exporter.py --input-csv "AFP_Resources.csv" --output-folder "Export" --quiet
"""
    )

    parser.add_argument(
        '--input-csv',
        required=True,
        help='Input CSV file from Analyze_AFP_Resources.py'
    )

    parser.add_argument(
        '--output-folder',
        required=True,
        help='Output folder where resources will be exported'
    )

    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Quiet mode - disable console logging'
    )

    return parser.parse_args()


# ============================================================================
# AFP Resource Exporter
# ============================================================================

class AFPResourceExporter:
    """
    Main exporter class for AFP resources.

    Reads CSV inventory, copies V1 files to root, and creates
    version subfolders for V2, V3, etc. when multiple versions exist.
    """

    def __init__(self, input_csv: str, output_folder: str):
        """
        Initialize AFP Resource Exporter.

        Args:
            input_csv: Input CSV file path from Analyze_AFP_Resources.py
            output_folder: Output folder for exported resources
        """
        self.input_csv = input_csv
        self.output_folder = output_folder

        # Statistics tracking
        self.stats = {
            'resources_processed': 0,
            'v1_files_copied': 0,
            'vn_files_copied': 0,  # V2, V3, etc.
            'version_folders_created': 0,
            'files_missing': 0,
            'files_failed': 0,
            'total_bytes_copied': 0
        }

        # Data structures
        self.resources = []  # List of resource dictionaries parsed from CSV
        self.created_folders = set()  # Track created version folders

    def export(self) -> None:
        """
        Main entry point - executes full export workflow.

        Workflow:
        1. Validate inputs
        2. Parse CSV
        3. Export resources
        4. Print statistics
        """
        logging.info("=" * 70)
        logging.info("AFP Resource Exporter - Starting")
        logging.info("=" * 70)
        logging.info(f"Input CSV: {self.input_csv}")
        logging.info(f"Output folder: {self.output_folder}")

        # Step 1: Validate inputs
        self._validate_inputs()

        # Step 2: Parse CSV
        self._parse_csv()

        # Step 3: Export resources
        self._export_resources()

        # Step 4: Print statistics
        self._print_statistics()

    def _validate_inputs(self) -> None:
        """Validate input parameters."""
        # Validate input CSV
        if not os.path.exists(self.input_csv):
            raise ValueError(f"Input CSV does not exist: {self.input_csv}")

        if not os.path.isfile(self.input_csv):
            raise ValueError(f"Input CSV is not a file: {self.input_csv}")

        # Validate output folder parent
        output_parent = os.path.dirname(os.path.abspath(self.output_folder))
        if output_parent and not os.path.exists(output_parent):
            raise ValueError(f"Output folder parent does not exist: {output_parent}")

        logging.debug("Input validation passed")

    def _parse_csv(self) -> None:
        """
        Parse CSV file and extract resource information.

        Builds self.resources list with structure:
        [
            {
                'namespace': 'DEFAULT',
                'folder': 'C:\\Users\\...\\afp',
                'filename': 'C01DD05N.RCS',
                'type': 'CharSet_Raster',
                'num_versions': 2,
                'versions': {
                    'V1': '2017_05_03_09',
                    'V2': '2016_05_20_14',
                    'V3': None,
                    ...
                }
            },
            ...
        ]
        """
        logging.info("Parsing CSV file...")

        with open(self.input_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames

            # Validate required columns
            required_cols = ['NameSpace', 'Folder', 'Resource_Filename', 'Resource_Type']
            missing_cols = [col for col in required_cols if col not in fieldnames]
            if missing_cols:
                raise ValueError(f"CSV missing required columns: {', '.join(missing_cols)}")

            # Check if "# Versions" column exists
            has_versions_col = '# Versions' in fieldnames

            # Extract version columns
            version_cols = [col for col in fieldnames if col.startswith('V') and col[1:].isdigit()]
            version_cols.sort(key=lambda x: int(x[1:]))  # Sort V1, V2, V3, ...

            if not version_cols:
                raise ValueError("CSV has no version columns (V1, V2, etc.)")

            logging.debug(f"Found version columns: {', '.join(version_cols)}")

            # Parse rows
            for row in reader:
                # Extract versions
                versions = {}
                for vcol in version_cols:
                    version_value = row.get(vcol, '').strip()
                    versions[vcol] = version_value if version_value else None

                # Count non-empty versions
                num_versions = sum(1 for v in versions.values() if v)

                resource = {
                    'namespace': row['NameSpace'].strip(),
                    'folder': row['Folder'].strip(),
                    'filename': row['Resource_Filename'].strip(),
                    'type': row['Resource_Type'].strip(),
                    'num_versions': num_versions,
                    'versions': versions
                }

                self.resources.append(resource)

        logging.info(f"Parsed {len(self.resources)} resource(s) from CSV")

    def _copy_resource_file(self, source_path: Path, dest_path: Path) -> bool:
        """
        Copy single file with error handling.

        Args:
            source_path: Source file path
            dest_path: Destination file path

        Returns:
            True if copy succeeded, False otherwise
        """
        try:
            # Check if source exists
            if not source_path.exists():
                logging.warning(f"Source file not found: {source_path}")
                self.stats['files_missing'] += 1
                return False

            # Ensure destination directory exists
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy file (preserves metadata)
            shutil.copy2(str(source_path), str(dest_path))

            # Track bytes copied
            file_size = source_path.stat().st_size
            self.stats['total_bytes_copied'] += file_size

            logging.debug(f"Copied: {source_path.name} -> {dest_path}")
            return True

        except Exception as e:
            logging.error(f"Failed to copy {source_path.name}: {e}")
            self.stats['files_failed'] += 1
            return False

    def _export_resources(self) -> None:
        """
        Export resources to output folder.

        - V1 files go to namespace folder root
        - V2, V3, etc. go to version subfolders within namespace folder
        """
        logging.info("Exporting resources...")

        # Create output folder if not exists
        output_path = Path(self.output_folder)
        output_path.mkdir(parents=True, exist_ok=True)
        logging.info(f"Output folder created: {self.output_folder}")

        # Process each resource
        total = len(self.resources)
        for idx, resource in enumerate(self.resources, 1):
            self.stats['resources_processed'] += 1

            # Progress reporting (every 50 resources in non-quiet mode)
            if idx % 50 == 0 or idx == total:
                progress_pct = (idx / total) * 100
                logging.info(f"Processing: {idx}/{total} resources ({progress_pct:.1f}%)")

            base_folder = Path(resource['folder'])
            filename = resource['filename']
            namespace = resource['namespace']

            # Create namespace folder
            namespace_path = output_path / namespace
            namespace_path.mkdir(parents=True, exist_ok=True)

            # Process each version
            for version_key, version_name in resource['versions'].items():
                if not version_name:
                    continue  # Skip empty versions

                # Construct source path
                source_path = base_folder / version_name / filename

                # Determine destination path
                if version_key == 'V1':
                    # V1 goes to namespace folder root
                    dest_path = namespace_path / filename
                    if self._copy_resource_file(source_path, dest_path):
                        self.stats['v1_files_copied'] += 1
                else:
                    # V2, V3, etc. go to version subfolders within namespace
                    version_folder = namespace_path / version_name

                    # Track new folders (with namespace prefix to make unique)
                    folder_key = f"{namespace}/{version_name}"
                    if folder_key not in self.created_folders:
                        version_folder.mkdir(parents=True, exist_ok=True)
                        self.created_folders.add(folder_key)
                        self.stats['version_folders_created'] += 1
                        logging.debug(f"Created version folder: {namespace}/{version_name}")

                    dest_path = version_folder / filename
                    if self._copy_resource_file(source_path, dest_path):
                        self.stats['vn_files_copied'] += 1

        logging.info("Export complete")

    def _print_statistics(self) -> None:
        """Print export statistics."""
        # Convert bytes to human-readable format
        total_mb = self.stats['total_bytes_copied'] / (1024 * 1024)

        logging.info("=" * 70)
        logging.info("EXPORT COMPLETE")
        logging.info("Export Statistics:")
        logging.info(f"  Resources processed: {self.stats['resources_processed']}")
        logging.info(f"  V1 files copied: {self.stats['v1_files_copied']}")
        logging.info(f"  Version files copied (V2+): {self.stats['vn_files_copied']}")
        logging.info(f"  Version folders created: {self.stats['version_folders_created']}")
        logging.info(f"  Files missing: {self.stats['files_missing']}")
        logging.info(f"  Files failed: {self.stats['files_failed']}")
        logging.info(f"  Total size copied: {total_mb:.2f} MB")
        logging.info("=" * 70)


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point."""
    # Parse arguments
    args = parse_arguments()

    # Create output folder if it doesn't exist (for log file)
    output_folder = os.path.abspath(args.output_folder)
    os.makedirs(output_folder, exist_ok=True)

    # Setup logging
    logger = setup_logging(output_folder, args.quiet)

    try:
        # Create exporter
        exporter = AFPResourceExporter(
            input_csv=args.input_csv,
            output_folder=output_folder
        )

        # Run export
        exporter.export()

        # Print summary in quiet mode
        if args.quiet:
            print(f"Completed: {exporter.stats['v1_files_copied']} V1 files, "
                  f"{exporter.stats['vn_files_copied']} version files, "
                  f"{exporter.stats['files_missing']} missing")

        return 0

    except KeyboardInterrupt:
        logging.error("\nOperation cancelled by user")
        return 130

    except Exception as e:
        logging.error(f"Error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
