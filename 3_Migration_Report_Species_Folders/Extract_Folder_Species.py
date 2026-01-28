#!/usr/bin/env python3
"""
Extract_Folder_Species.py - MS SQL Database Folder and Report Extractor

Extracts folder hierarchy and report species data from MS SQL Server database.
Generates three CSV files:
1. Folder_Hierarchy.csv - Valid folder hierarchy (excluding orphans)
2. Folder_Report.csv - Folder-to-report mappings with names
3. Report_Species.csv - Unique report species with usage flag

Author: Generated for OCBC IntelliSTOR Migration
Date: 2026-01-21
"""

import pymssql
import csv
import argparse
import logging
import sys
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict


# ============================================================================
# Configuration and Setup
# ============================================================================

# Country code mapping
COUNTRY_CODES = {
    'SG': 'Singapore',
    'AU': 'Australia',
    'BN': 'Brunei',
    'CN': 'China',
    'HK': 'Hong Kong',
    'ID': 'Indonesia',
    'JP': 'Japan',
    'MY': 'Malaysia',
    'PH': 'Philippines',
    'KR': 'South Korea',
    'TH': 'Thailand',
    'TW': 'Taiwan',
    'UK': 'UK',
    'US': 'US',
    'VN': 'Vietnam'
}


def setup_logging(output_dir, quiet=False):
    """Setup logging to both console and file."""
    log_file = os.path.join(output_dir, 'Extract_Folder_Species.log')

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


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Extract folder hierarchy and report species from MS SQL Server database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Windows Authentication with fixed country code
  python Extract_Folder_Species.py --server localhost --database IntelliSTOR --windows-auth --Country SG

  # SQL Server Authentication with auto-detection
  python Extract_Folder_Species.py --server localhost --database IntelliSTOR --user sa --password MyP@ssw0rd --Country 0

  # With custom output directory
  python Extract_Folder_Species.py --server localhost --database IntelliSTOR --windows-auth --Country HK --output-dir C:\\Output

  # Quiet mode with auto-detection
  python Extract_Folder_Species.py --server localhost --database IntelliSTOR --windows-auth --Country 0 --quiet

Output Files:
  - Folder_Hierarchy.csv: Valid folder hierarchy (no orphans)
  - Folder_Report.csv: Folder-to-report mappings with names
  - Report_Species.csv: Unique report species with In_Use flag
  - log.txt: Country code conflicts (if any)
        """
    )

    # Database connection parameters
    parser.add_argument('--server', required=True, help='SQL Server host/IP address')
    parser.add_argument('--port', type=int, default=1433, help='SQL Server port (default: 1433)')
    parser.add_argument('--database', required=True, help='Database name')
    parser.add_argument('--user', help='Username for SQL Server authentication')
    parser.add_argument('--password', help='Password for SQL Server authentication')
    parser.add_argument('--windows-auth', action='store_true',
                        help='Use Windows Authentication')

    # Output options
    parser.add_argument('--output-dir', '-o', default='.',
                        help='Output directory for CSV files (default: current directory)')
    parser.add_argument('--quiet', action='store_true',
                        help='Quiet mode - minimal console output')

    # Country code parameter
    parser.add_argument('--Country', required=True,
                        help='Country code mode: 2-letter code (e.g., SG, HK) to apply globally, or "0" to detect from folder names')

    args = parser.parse_args()

    # Validate authentication parameters
    if not args.windows_auth and (not args.user or not args.password):
        parser.error('Either --windows-auth or both --user and --password must be provided')

    # Validate and normalize Country parameter
    if args.Country != "0":
        if len(args.Country) != 2:
            parser.error('--Country must be either "0" or exactly 2 characters (e.g., SG, HK)')
        args.Country = args.Country.upper()

    return args


# ============================================================================
# Database Connection
# ============================================================================

def create_connection(server, port, database, user=None, password=None, windows_auth=False):
    """Create SQL Server connection using pymssql."""
    try:
        connection_info = f'{server}:{port}, database: {database}'
        if windows_auth:
            logging.info(f'Connecting to SQL Server using Windows Authentication: {connection_info}')
            conn = pymssql.connect(
                server=server,
                port=port,
                database=database
            )
        else:
            logging.info(f'Connecting to SQL Server using SQL Server Authentication: {connection_info}, user: {user}')
            if not user or not password:
                raise ValueError('Username and password required for SQL Server authentication')
            conn = pymssql.connect(
                server=server,
                port=port,
                database=database,
                user=user,
                password=password
            )

        logging.info('Database connection established successfully')
        return conn

    except Exception as e:
        logging.error(f'Failed to connect to SQL Server: {e}')
        logging.error(f'Connection details: {server}:{port}, database: {database}')
        raise


# ============================================================================
# Data Extraction
# ============================================================================

class FolderSpeciesExtractor:
    """Extracts folder and report species data from MS SQL Server."""

    def __init__(self, conn, output_dir, country_mode):
        """Initialize the extractor.

        Args:
            conn: Database connection
            output_dir: Output directory for CSV files
            country_mode: Country code mode - either a 2-letter code (e.g., 'SG', 'HK') or "0" for auto-detection
        """
        self.conn = conn
        self.output_dir = Path(output_dir)
        self.country_mode = country_mode  # Either a 2-letter code or "0"

        # Data structures
        self.folders: Dict[int, Dict] = {}           # ITEM_ID -> folder data
        self.folder_species: List[Dict] = []         # List of folder-species mappings
        self.report_names: Dict[Tuple, str] = {}     # (DOMAIN_ID, SPECIES_ID, ITEM_ID) -> NAME
        self.valid_folder_ids: Set[int] = set()      # Set of valid (non-orphaned) folder IDs
        self.folder_country_codes: Dict[int, str] = {}  # ITEM_ID -> country code
        self.report_country_codes: Dict[int, str] = {}  # REPORT_SPECIES_ID -> country code
        self.country_conflicts: List[str] = []       # List of conflict messages for log

    def load_folders(self):
        """Load folder hierarchy from database."""
        logging.info('Loading folders from FOLDER table...')

        cursor = self.conn.cursor()
        query = """
            SELECT ITEM_ID, NAME, PARENT_ID, PRIVATE_ROOT_ID, ITEM_TYPE
            FROM FOLDER
            ORDER BY ITEM_ID
        """

        cursor.execute(query)

        for row in cursor:
            item_id, name, parent_id, private_root_id, item_type = row
            self.folders[item_id] = {
                'ITEM_ID': item_id,
                'NAME': name.strip() if name else '',
                'PARENT_ID': parent_id,
                'PRIVATE_ROOT_ID': private_root_id,
                'ITEM_TYPE': item_type
            }

        cursor.close()
        logging.info(f'Loaded {len(self.folders)} folders')

    def load_folder_species(self):
        """Load folder-species mappings from database."""
        logging.info('Loading folder-species mappings from FOLDER_SPECIES table...')

        cursor = self.conn.cursor()
        query = """
            SELECT ITEM_ID, DOMAIN_ID, REPORT_SPECIES_ID
            FROM FOLDER_SPECIES
            ORDER BY ITEM_ID, REPORT_SPECIES_ID
        """

        cursor.execute(query)

        for row in cursor:
            item_id, domain_id, report_species_id = row
            self.folder_species.append({
                'ITEM_ID': item_id,
                'DOMAIN_ID': domain_id,
                'REPORT_SPECIES_ID': report_species_id
            })

        cursor.close()
        logging.info(f'Loaded {len(self.folder_species)} folder-species mappings')

    def load_report_names(self):
        """Load report species names from database."""
        logging.info('Loading report species names from REPORT_SPECIES_NAME table...')

        cursor = self.conn.cursor()
        query = """
            SELECT DOMAIN_ID, REPORT_SPECIES_ID, ITEM_ID, NAME
            FROM REPORT_SPECIES_NAME
            ORDER BY REPORT_SPECIES_ID, ITEM_ID
        """

        cursor.execute(query)

        for row in cursor:
            domain_id, species_id, item_id, name = row
            key = (domain_id, species_id, item_id)
            self.report_names[key] = name.strip() if name else ''

        cursor.close()
        logging.info(f'Loaded {len(self.report_names)} report species name records')

    def validate_folder_hierarchy(self):
        """Identify valid folders (exclude orphans and their descendants)."""
        logging.info('Validating folder hierarchy...')

        # Build set of all folder IDs
        all_folder_ids = set(self.folders.keys())

        # Recursive function to check if a folder and its ancestors are valid
        def is_valid(item_id: int, visited: Set[int] = None) -> bool:
            if visited is None:
                visited = set()

            # Circular reference detection
            if item_id in visited:
                logging.warning(f'Circular reference detected for folder {item_id}')
                return False

            # Already validated
            if item_id in self.valid_folder_ids:
                return True

            # Get folder data
            folder = self.folders.get(item_id)
            if not folder:
                return False

            # Skip folders with ITEM_TYPE = 3
            if folder['ITEM_TYPE'] == 3:
                return False

            parent_id = folder['PARENT_ID']

            # Root folder (PARENT_ID=0) is always valid
            if parent_id == 0:
                self.valid_folder_ids.add(item_id)
                return True

            # Check if parent exists
            if parent_id not in all_folder_ids:
                # Orphan - parent doesn't exist
                return False

            # Recursively check parent validity
            visited.add(item_id)
            if is_valid(parent_id, visited):
                self.valid_folder_ids.add(item_id)
                return True

            return False

        # Validate all folders
        for item_id in list(self.folders.keys()):
            is_valid(item_id)

        # Count excluded folders by type
        excluded_count = len(self.folders) - len(self.valid_folder_ids)
        type3_count = sum(1 for f in self.folders.values() if f['ITEM_TYPE'] == 3)

        logging.info(f'Valid folders: {len(self.valid_folder_ids)}')
        logging.info(f'Excluded folders: {excluded_count}')
        logging.info(f'  ITEM_TYPE=3 folders: {type3_count}')
        logging.info(f'  Orphaned folders: {excluded_count - type3_count}')

        if excluded_count > 0:
            logging.info('ITEM_TYPE=3 folders, orphaned folders, and their descendants excluded from output')

    def detect_country_code_from_name(self, folder_name: str) -> str:
        """Detect country code from folder name.

        Returns the country code if folder name is exactly a 2-character country code,
        otherwise returns None.
        """
        name_stripped = folder_name.strip()

        if len(name_stripped) == 2:
            name_upper = name_stripped.upper()
            if name_upper in COUNTRY_CODES:
                return name_upper

        return None

    def assign_country_codes(self):
        """Assign country codes to all valid folders based on hierarchy or fixed mode."""
        logging.info('Assigning country codes to folders...')

        if self.country_mode != "0":
            # Fixed country mode - assign to all folders
            for item_id in self.valid_folder_ids:
                self.folder_country_codes[item_id] = self.country_mode
            logging.info(f'Assigned country code {self.country_mode} to all {len(self.valid_folder_ids)} folders')
        else:
            # Auto-detection mode - existing detection logic from folder names
            # Build parent-to-children mapping
            children_map = defaultdict(list)
            for item_id in self.valid_folder_ids:
                folder = self.folders[item_id]
                parent_id = folder['PARENT_ID']
                if parent_id != 0:
                    children_map[parent_id].append(item_id)

            # Recursive function to assign country codes
            def assign_to_folder_and_children(item_id: int, parent_country_code: str = 'SG'):
                folder = self.folders[item_id]
                folder_name = folder['NAME']

                # Check if folder name is a country code
                detected_code = self.detect_country_code_from_name(folder_name)

                if detected_code:
                    country_code = detected_code
                else:
                    country_code = parent_country_code

                # Assign to this folder
                self.folder_country_codes[item_id] = country_code

                # Recursively assign to children
                for child_id in children_map.get(item_id, []):
                    assign_to_folder_and_children(child_id, country_code)

            # Find root folders (PARENT_ID = 0) and process them
            root_folders = [item_id for item_id in self.valid_folder_ids
                           if self.folders[item_id]['PARENT_ID'] == 0]

            for root_id in root_folders:
                assign_to_folder_and_children(root_id, 'SG')  # Default to SG

            # Count folders by country code
            country_counts = defaultdict(int)
            for country_code in self.folder_country_codes.values():
                country_counts[country_code] += 1

            logging.info(f'Assigned country codes to {len(self.folder_country_codes)} folders')
            for code in sorted(country_counts.keys()):
                logging.info(f'  {code}: {country_counts[code]} folders')

    def get_report_name_and_display(self, domain_id: int, species_id: int) -> Tuple[str, str]:
        """Get report name and display name.

        Logic:
        - Report_Species_DisplayName: Always from ITEM_ID=0
        - Report_Species_Name: From ITEM_ID=1 if exists, else from ITEM_ID=0
        """
        # Get display name (ITEM_ID=0)
        display_key = (domain_id, species_id, 0)
        display_name = self.report_names.get(display_key, f"UNKNOWN_{species_id}")

        # Get name (ITEM_ID=1 if exists, else use display name)
        name_key = (domain_id, species_id, 1)
        if name_key in self.report_names:
            name = self.report_names[name_key]
        else:
            name = display_name

        return (name, display_name)

    def track_report_country_code(self, species_id: int, folder_country_code: str):
        """Track country code for a report species and detect conflicts."""
        if species_id in self.report_country_codes:
            existing_code = self.report_country_codes[species_id]

            if existing_code != 'SG' and folder_country_code != existing_code:
                conflict_msg = (f"Report Species {species_id}: "
                              f"Already assigned to {existing_code}, "
                              f"cannot override with {folder_country_code}")
                self.country_conflicts.append(conflict_msg)
                return existing_code
            elif existing_code == 'SG' and folder_country_code != 'SG':
                self.report_country_codes[species_id] = folder_country_code
                return folder_country_code
            else:
                return existing_code
        else:
            self.report_country_codes[species_id] = folder_country_code
            return folder_country_code

    def write_conflict_log(self):
        """Write country code conflicts to log.txt file."""
        if self.country_conflicts:
            log_path = self.output_dir / "log.txt"
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write("Country Code Assignment Conflicts\n")
                f.write("=" * 70 + "\n\n")
                f.write(f"Total conflicts: {len(self.country_conflicts)}\n\n")

                for conflict in self.country_conflicts:
                    f.write(f"{conflict}\n")

            logging.warning(f'{len(self.country_conflicts)} country code conflicts detected')
            logging.info(f'Conflicts written to {log_path}')
        else:
            logging.info('No country code conflicts detected')

    def generate_folder_hierarchy_csv(self):
        """Generate Folder_Hierarchy.csv with valid folders only."""
        output_file = 'Folder_Hierarchy.csv'
        logging.info(f'Generating {output_file}...')

        records = []
        for item_id in sorted(self.valid_folder_ids):
            folder = self.folders[item_id]
            country_code = self.folder_country_codes.get(item_id, 'SG')
            records.append({
                'ITEM_ID': folder['ITEM_ID'],
                'NAME': folder['NAME'],
                'PARENT_ID': folder['PARENT_ID'],
                'ITEM_TYPE': folder['ITEM_TYPE'],
                'Country_Code': country_code
            })

        output_path = self.output_dir / output_file
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['ITEM_ID', 'NAME', 'PARENT_ID', 'ITEM_TYPE', 'Country_Code']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)

        logging.info(f'Written {len(records)} folders to {output_path}')

    def generate_folder_report_csv(self):
        """Generate Folder_Report.csv with folder-to-report mappings."""
        output_file = 'Folder_Report.csv'
        logging.info(f'Generating {output_file}...')

        records = []
        skipped_invalid_folder = 0
        skipped_species_zero = 0

        for fs in self.folder_species:
            item_id = fs['ITEM_ID']

            # Skip if folder is not valid (orphaned)
            if item_id not in self.valid_folder_ids:
                skipped_invalid_folder += 1
                continue

            species_id = fs['REPORT_SPECIES_ID']
            domain_id = fs['DOMAIN_ID']

            # Skip REPORT_SPECIES_ID=0 (unknown/placeholder)
            if species_id == 0:
                skipped_species_zero += 1
                continue

            # Get report names
            name, display_name = self.get_report_name_and_display(domain_id, species_id)

            # Get folder name
            folder_name = self.folders[item_id]['NAME']

            # Get folder's country code
            folder_country_code = self.folder_country_codes.get(item_id, 'SG')

            # Track report country code and detect conflicts
            report_country_code = self.track_report_country_code(species_id, folder_country_code)

            records.append({
                'ITEM_ID': item_id,
                'ITEM_NAME': folder_name,
                'Report_Species_Id': species_id,
                'Report_Species_Name': name,
                'Report_Species_DisplayName': display_name,
                'Country_Code': report_country_code
            })

        # Sort by ITEM_ID, then Report_Species_Id
        records.sort(key=lambda x: (x['ITEM_ID'], x['Report_Species_Id']))

        output_path = self.output_dir / output_file
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['ITEM_ID', 'ITEM_NAME', 'Report_Species_Id', 'Report_Species_Name', 'Report_Species_DisplayName', 'Country_Code']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)

        logging.info(f'Written {len(records)} folder-report mappings to {output_path}')
        logging.info(f'Skipped {skipped_invalid_folder} entries (invalid folders)')
        logging.info(f'Skipped {skipped_species_zero} entries (REPORT_SPECIES_ID=0)')

    def generate_report_species_csv(self):
        """Generate Report_Species.csv with unique report species."""
        output_file = 'Report_Species.csv'
        logging.info(f'Generating {output_file}...')

        # Collect unique report species with their domain_id from valid folder-species mappings
        unique_species = {}  # species_id -> domain_id

        for fs in self.folder_species:
            item_id = fs['ITEM_ID']
            species_id = fs['REPORT_SPECIES_ID']
            domain_id = fs['DOMAIN_ID']

            # Only include if folder is valid and species is not 0
            if item_id in self.valid_folder_ids and species_id > 0:
                if species_id not in unique_species:
                    unique_species[species_id] = domain_id

        # Create sorted list of records
        records = []
        for species_id in sorted(unique_species.keys()):
            domain_id = unique_species[species_id]

            # Get report name and display name
            name, display_name = self.get_report_name_and_display(domain_id, species_id)

            # Get country code
            country_code = self.report_country_codes.get(species_id, 'SG')

            records.append({
                'Report_Species_Id': species_id,
                'Report_Species_Name': name,
                'Report_Species_DisplayName': display_name,
                'Country_Code': country_code,
                'In_Use': 1
            })

        output_path = self.output_dir / output_file
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['Report_Species_Id', 'Report_Species_Name', 'Report_Species_DisplayName', 'Country_Code', 'In_Use']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)

        logging.info(f'Written {len(records)} unique report species to {output_path}')

    def extract_all(self):
        """Extract all data and generate CSV files."""
        # Load data from database
        self.load_folders()
        self.load_folder_species()
        self.load_report_names()

        # Validate hierarchy
        self.validate_folder_hierarchy()

        # Assign country codes
        self.assign_country_codes()

        # Generate outputs
        self.generate_folder_hierarchy_csv()
        self.generate_folder_report_csv()
        self.generate_report_species_csv()

        # Write conflict log
        self.write_conflict_log()


# ============================================================================
# Main Function
# ============================================================================

def main():
    """Main entry point."""
    args = parse_arguments()

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Setup logging
    setup_logging(args.output_dir, quiet=args.quiet)

    if not args.quiet:
        logging.info('='*70)
        logging.info('Extract_Folder_Species.py - Starting')
        logging.info('='*70)
        logging.info(f'Output directory: {args.output_dir}')

    try:
        # Connect to database
        conn = create_connection(
            server=args.server,
            port=args.port,
            database=args.database,
            user=args.user,
            password=args.password,
            windows_auth=args.windows_auth
        )

        # Extract data
        extractor = FolderSpeciesExtractor(conn, args.output_dir, args.Country)
        extractor.extract_all()

        # Close connection
        conn.close()
        if not args.quiet:
            logging.info('Database connection closed')

        # Print summary
        if args.quiet:
            print(f'Completed: Generated Folder_Hierarchy.csv, Folder_Report.csv, and Report_Species.csv')
        else:
            logging.info('='*70)
            logging.info('EXTRACTION COMPLETE')
            logging.info('Output files:')
            logging.info('  - Folder_Hierarchy.csv')
            logging.info('  - Folder_Report.csv')
            logging.info('  - Report_Species.csv')
            if extractor.country_conflicts:
                logging.info('  - log.txt (conflicts)')
            logging.info('='*70)

        sys.exit(0)

    except KeyboardInterrupt:
        if not args.quiet:
            logging.info('Process interrupted by user (Ctrl+C)')
        else:
            print('\nProcess interrupted by user (Ctrl+C)')
        sys.exit(130)

    except Exception as e:
        logging.error(f'Fatal error: {e}')
        if args.quiet:
            print(f'\nFatal error: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
