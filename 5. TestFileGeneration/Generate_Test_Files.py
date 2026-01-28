#!/usr/bin/env python3
"""
Generate_Test_Files.py

Generate test files for Report_Species instances by copying template files
and renaming them based on instance data from CSV files.

All output files are placed directly in TargetFolder (no year subfolders).
File distribution per instance:
  - 10% (1 out of 10): .AFP + .TXT (from test.afp and test.txt)
  - 20% (2 out of 10): .PDF + .TXT (from test.pdf and test.txt)
  - 70% (7 out of 10): ONLY .TXT (from FRX16.txt or CFSUL003.txt, randomly chosen)

Improvements:
- Batch processing: limit number of species per run (default: 5)
- Real-time log file writing with immediate flushing
- Persistent progress tracking across interruptions
- Crash recovery: resumes from last processed species

Usage:
    python Generate_Test_Files.py \
        --ReportSpecies Report_Species.csv \
        --FolderExtract Output_Extract_Instances \
        --Number 5 \
        --LocationTestFile . \
        --TargetFolder TargetSG \
        --quiet

Date: 2026-01-26
"""

import argparse
import csv
import os
import sys
import glob
import shutil
import random
import time
import json
import logging
from pathlib import Path


# Constants
PROGRESS_FILE = "generate_test_files_progress.json"
LOG_FILE = "generate_test_files.log"


# ============================================================================
# Logging and Progress Tracking
# ============================================================================

def setup_logging(quiet=False):
    """Initialize logging configuration with real-time flushing"""
    # Create file handler with unbuffered writing
    class FlushFileHandler(logging.FileHandler):
        def emit(self, record):
            super().emit(record)
            self.flush()

    file_handler = FlushFileHandler(LOG_FILE, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    handlers = [file_handler]

    if not quiet:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        handlers.append(console_handler)

    # Get root logger and set it up
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.handlers = []  # Clear existing handlers
    for handler in handlers:
        logger.addHandler(handler)


def load_progress(reset=False):
    """
    Load progress from JSON file

    Args:
        reset: If True, ignore existing progress file

    Returns:
        Tuple of (last_species_id, stats_dict) or (None, {}) if no progress
    """
    if reset:
        logging.info("Progress reset requested, starting from beginning")
        return None, {}

    if not os.path.exists(PROGRESS_FILE):
        logging.info("No progress file found, starting from beginning")
        return None, {}

    try:
        with open(PROGRESS_FILE, 'r') as f:
            progress = json.load(f)
            last_species_id = progress.get('last_species_id')
            stats = progress.get('stats', {})

            logging.info(f"Resuming from last_species_id={last_species_id}")
            logging.info(f"Loaded stats: Species={stats.get('species_processed', 0)}, "
                        f"Instances={stats.get('instances_processed', 0)}, "
                        f"Files={stats.get('files_created', 0)}")
            return last_species_id, stats
    except json.JSONDecodeError:
        logging.error("Corrupted progress file detected. Use --reset-progress to start over.")
        raise
    except Exception as e:
        logging.error(f"Error loading progress file: {e}")
        raise


def save_progress(last_species_id, stats):
    """
    Save current progress to JSON file

    Args:
        last_species_id: Last completed species ID
        stats: Statistics dictionary
    """
    try:
        progress = {
            'last_species_id': last_species_id,
            'stats': stats
        }
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(progress, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        logging.error(f"Error saving progress: {e}")


def clear_progress():
    """Delete progress file when processing is complete"""
    try:
        if os.path.exists(PROGRESS_FILE):
            os.remove(PROGRESS_FILE)
            logging.info("Progress file deleted (processing complete)")
    except Exception as e:
        logging.warning(f"Could not delete progress file: {e}")


# ============================================================================
# Argument Parsing
# ============================================================================

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Generate test files for Report_Species instances',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process first 2 species
  python Generate_Test_Files.py --FolderExtract Output_Extract_Instances --TargetFolder TestOutput --Number 2

  # Process from specific ID with quiet mode
  python Generate_Test_Files.py --FolderExtract Output_Extract_Instances --TargetFolder TestOutput --StartReport_Species_Id 3 --Number 5 --quiet

  # Process all species
  python Generate_Test_Files.py --FolderExtract Output_Extract_Instances --TargetFolder TestOutput
        """
    )

    parser.add_argument(
        '--ReportSpecies',
        type=str,
        default='Report_Species.csv',
        help='Path to Report_Species.csv (default: Report_Species.csv)'
    )

    parser.add_argument(
        '--FolderExtract',
        type=str,
        required=True,
        help='Folder containing instance CSV files (e.g., BC2035P_2024.csv)'
    )

    parser.add_argument(
        '--Number',
        type=int,
        default=5,
        help='Number of Report_Species to process per run (0 = all, default: 5)'
    )

    parser.add_argument(
        '--StartReport_Species_Id',
        type=int,
        default=0,
        help='Starting Report_Species_Id (0 = auto-resume from progress, default: 0)'
    )

    parser.add_argument(
        '--reset-progress',
        action='store_true',
        help='Start from beginning, ignore existing progress'
    )

    parser.add_argument(
        '--LocationTestFile',
        type=str,
        default='.',
        help='Directory with template files (test.txt, test.afp, test.pdf, FRX16.txt, CFSUL003.txt) (default: current directory)'
    )

    parser.add_argument(
        '--TargetFolder',
        type=str,
        required=True,
        help='Output directory for generated test files'
    )

    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Quiet mode (minimal console output, progress on same line)'
    )

    return parser.parse_args()


# ============================================================================
# Validation Functions
# ============================================================================

def validate_template_files(location):
    """
    Validate that test.txt, test.afp, test.pdf, FRX16.txt, and CFSUL003.txt exist.

    Args:
        location: Directory containing template files

    Returns:
        tuple: (success: bool, missing_files: list)
    """
    required_files = ['test.txt', 'test.afp', 'test.pdf', 'FRX16.txt', 'CFSUL003.txt']
    missing = []

    for filename in required_files:
        filepath = os.path.join(location, filename)
        if not os.path.isfile(filepath):
            missing.append(filename)

    return (len(missing) == 0, missing)


def validate_report_species_csv(filepath):
    """
    Validate Report_Species.csv exists and has correct structure.

    Args:
        filepath: Path to Report_Species.csv

    Returns:
        tuple: (success: bool, error_message: str)
    """
    if not os.path.isfile(filepath):
        return (False, f"Report_Species.csv not found: {filepath}")

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames

            if headers is None:
                return (False, "CSV file is empty or has no headers")

            required_cols = ['Report_Species_Id', 'Report_Species_Name', 'In_Use']
            missing = [col for col in required_cols if col not in headers]

            if missing:
                return (False, f"Missing columns: {', '.join(missing)}")

            return (True, "")
    except Exception as e:
        return (False, f"Error reading CSV: {str(e)}")


def validate_folder_extract(folder_path):
    """
    Validate FolderExtract exists and contains CSV files.

    Args:
        folder_path: Path to folder containing instance CSV files

    Returns:
        tuple: (success: bool, error_message: str, csv_count: int)
    """
    if not os.path.isdir(folder_path):
        return (False, f"FolderExtract not found: {folder_path}", 0)

    csv_files = glob.glob(os.path.join(folder_path, "*.csv"))

    if len(csv_files) == 0:
        return (False, f"No CSV files found in: {folder_path}", 0)

    return (True, "", len(csv_files))


# ============================================================================
# Core Processing Functions
# ============================================================================

def read_report_species(filepath, start_id=0, max_count=0):
    """
    Read Report_Species.csv and return filtered rows.

    Args:
        filepath: Path to Report_Species.csv
        start_id: Starting Report_Species_Id (0 = all)
        max_count: Maximum number to return (0 = all)

    Returns:
        list: List of dicts with filtered report species
    """
    species_list = []

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            try:
                species_id = int(row['Report_Species_Id'])
                in_use = int(row['In_Use'])
            except (ValueError, KeyError) as e:
                # Skip malformed rows
                continue

            # Skip if before start_id
            if start_id > 0 and species_id < start_id:
                continue

            # Only process In_Use = 1
            if in_use != 1:
                continue

            species_list.append({
                'id': species_id,
                'name': row['Report_Species_Name'],
                'display_name': row.get('Report_Species_DisplayName', row['Report_Species_Name'])
            })

            # Stop if reached max_count
            if max_count > 0 and len(species_list) >= max_count:
                break

    return species_list


def find_instance_csv(folder_extract, species_name):
    """
    Find instance CSV file for a report species using wildcard.

    Args:
        folder_extract: Directory containing instance CSV files
        species_name: Report species name (e.g., "BC2035P")

    Returns:
        str: Path to found CSV file, or None if not found
    """
    pattern = os.path.join(folder_extract, f"{species_name}*.csv")
    matches = glob.glob(pattern)

    if len(matches) == 0:
        return None

    # Return first match (should only be one)
    return matches[0]


# ============================================================================
# Progress Display and Statistics
# ============================================================================

def print_progress(species_name, species_idx, species_total, instances, files, current_file):
    """
    Print progress on same line (carriage return).

    Args:
        species_name: Current report species name
        species_idx: Current species index (1-based)
        species_total: Total species to process
        instances: Total instances processed
        files: Total files created
        current_file: Current filename being processed
    """
    progress = f"Processing: {species_name} ({species_idx}/{species_total}) | "
    progress += f"Instances: {instances} | Files: {files} | Current: {current_file}"

    # Carriage return to overwrite line (max 120 chars)
    if len(progress) > 120:
        progress = progress[:117] + "..."

    print(f"\r{progress:<120}", end='', flush=True)


def print_statistics(stats, elapsed_time):
    """
    Print final statistics after processing completes.

    Args:
        stats: Dictionary with statistics
        elapsed_time: Processing time in seconds
    """
    print("\n")  # New line after progress
    print("=" * 80)
    print("Test File Generation Complete")
    print("=" * 80)

    print(f"Report Species Processed: {stats['species_processed']:,}")
    print(f"Total Instances: {stats['instances_processed']:,}")
    print(f"Total Files Created: {stats['files_created']:,}")
    print()

    if stats['files_by_year']:
        print("Files by Year:")
        for year in sorted(stats['files_by_year'].keys()):
            count = stats['files_by_year'][year]
            print(f"  {year}: {count:,} files")
        print()

    if stats['files_by_type']:
        print("Files by Type:")
        for file_type in sorted(stats['files_by_type'].keys()):
            count = stats['files_by_type'][file_type]
            print(f"  {file_type}: {count:,}")
        print()

    print(f"Processing Time: {elapsed_time:.1f} seconds")
    print("=" * 80)


# ============================================================================
# Main Execution
# ============================================================================

def main():
    """Main execution function."""
    # Parse arguments
    args = parse_arguments()

    # Setup logging
    setup_logging(quiet=args.quiet)

    # Load progress
    last_species_id, loaded_stats = load_progress(args.reset_progress)

    # Initialize statistics (or use loaded stats)
    stats = {
        'species_processed': loaded_stats.get('species_processed', 0),
        'instances_processed': loaded_stats.get('instances_processed', 0),
        'files_created': loaded_stats.get('files_created', 0),
        'files_by_year': loaded_stats.get('files_by_year', {}),
        'files_by_type': loaded_stats.get('files_by_type', {})
    }

    start_time = time.time()

    # Determine start ID (priority: explicit arg > progress file)
    start_id = args.StartReport_Species_Id
    if start_id == 0 and last_species_id is not None:
        # Resume from next species after last completed
        start_id = last_species_id + 1
        logging.info(f"Auto-resuming from species ID {start_id}")

    # Validation Phase
    logging.info("=" * 80)
    logging.info("Test File Generator for Report_Species Instances")
    logging.info("=" * 80)
    if not args.quiet:
        print("=" * 80)
        print("Test File Generator for Report_Species Instances")
        print("=" * 80)
        print("Validating inputs...")
        print()

    # Validate Report_Species.csv
    success, error = validate_report_species_csv(args.ReportSpecies)
    if not success:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)

    if not args.quiet:
        print(f"[OK] Report_Species.csv found: {args.ReportSpecies}")

    # Validate FolderExtract
    success, error, csv_count = validate_folder_extract(args.FolderExtract)
    if not success:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)

    if not args.quiet:
        print(f"[OK] FolderExtract found: {args.FolderExtract}")
        print(f"     Found {csv_count} instance CSV files")

    # Validate template files
    success, missing = validate_template_files(args.LocationTestFile)
    if not success:
        print(f"ERROR: Missing template files: {', '.join(missing)}", file=sys.stderr)
        print(f"  Location: {args.LocationTestFile}", file=sys.stderr)
        sys.exit(1)

    if not args.quiet:
        print(f"[OK] Template files found: {args.LocationTestFile}")
        print(f"     test.txt, test.afp, test.pdf, FRX16.txt, CFSUL003.txt")
        print()

    # Create target folder if not exists
    os.makedirs(args.TargetFolder, exist_ok=True)

    # Read Report_Species
    logging.info(f"Reading Report_Species from {args.ReportSpecies}...")
    if not args.quiet:
        print(f"Reading Report_Species from {args.ReportSpecies}...")

    species_list = read_report_species(
        args.ReportSpecies,
        start_id=start_id,
        max_count=args.Number
    )

    if len(species_list) == 0:
        logging.error("No report species found matching criteria")
        logging.error(f"  StartReport_Species_Id: {start_id}")
        logging.error(f"  Number: {args.Number if args.Number > 0 else 'all'}")
        print("ERROR: No report species found matching criteria", file=sys.stderr)
        print(f"  StartReport_Species_Id: {start_id}", file=sys.stderr)
        print(f"  Number: {args.Number if args.Number > 0 else 'all'}", file=sys.stderr)
        sys.exit(1)

    logging.info(f"Found {len(species_list)} report species to process (In_Use=1)")
    if start_id > 0:
        logging.info(f"  Starting from Report_Species_Id: {start_id}")
    if args.Number > 0:
        logging.info(f"  Processing maximum: {args.Number} species")

    if not args.quiet:
        print(f"Found {len(species_list)} report species to process (In_Use=1)")
        if start_id > 0:
            print(f"  Starting from Report_Species_Id: {start_id}")
        if args.Number > 0:
            print(f"  Processing maximum: {args.Number} species")
        print()
        print("Processing instances...")

    # Process each report species
    instance_counter = 0  # Track instance number for distribution

    for idx, species in enumerate(species_list, start=1):
        species_id = species['id']
        species_name = species['name']

        logging.info(f"Processing species: {species_name} (ID={species_id}) [{idx}/{len(species_list)}]")

        # Find instance CSV
        instance_csv = find_instance_csv(args.FolderExtract, species_name)

        if instance_csv is None:
            logging.warning(f"No instance CSV found for {species_name}")
            if not args.quiet:
                print(f"WARNING: No instance CSV found for {species_name}", file=sys.stderr)
            # Still save progress even if CSV not found
            save_progress(species_id, stats)
            continue

        # Process instances
        if not args.quiet and not args.quiet:
            print(f"  Processing {species_name} ({idx}/{len(species_list)})...")

        # Read and process each instance
        try:
            with open(instance_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    try:
                        filename_rpt = row['FILENAME']
                        year = row['YEAR']

                        # Strip .RPT extension
                        if '.' in filename_rpt:
                            filename_base = filename_rpt.rsplit('.', 1)[0]
                        else:
                            filename_base = filename_rpt

                        # Determine distribution category based on instance counter
                        # 10% (1 out of 10): AFP + TXT (from test files)
                        # 20% (2 out of 10): PDF + TXT (from test files)
                        # 70% (7 out of 10): ONLY TXT (from FRX16.txt or CFSUL003.txt) - NO AFP/PDF

                        category = instance_counter % 10
                        instance_counter += 1

                        # Category 0: 10% - AFP + TXT (from test files)
                        if category == 0:
                            # Copy test.txt → {filename}.TXT
                            src_txt = os.path.join(args.LocationTestFile, 'test.txt')
                            dst_txt = os.path.join(args.TargetFolder, f"{filename_base}.TXT")
                            shutil.copy2(src_txt, dst_txt)

                            stats['files_created'] += 1
                            stats['files_by_year'][year] = stats['files_by_year'].get(year, 0) + 1
                            stats['files_by_type']['TXT'] = stats['files_by_type'].get('TXT', 0) + 1

                            # Copy test.afp → {filename}.AFP
                            src_afp = os.path.join(args.LocationTestFile, 'test.afp')
                            dst_afp = os.path.join(args.TargetFolder, f"{filename_base}.AFP")
                            shutil.copy2(src_afp, dst_afp)

                            stats['files_created'] += 1
                            stats['files_by_year'][year] = stats['files_by_year'].get(year, 0) + 1
                            stats['files_by_type']['AFP'] = stats['files_by_type'].get('AFP', 0) + 1

                        # Category 1-2: 20% - PDF + TXT (from test files)
                        elif category in [1, 2]:
                            # Copy test.txt → {filename}.TXT
                            src_txt = os.path.join(args.LocationTestFile, 'test.txt')
                            dst_txt = os.path.join(args.TargetFolder, f"{filename_base}.TXT")
                            shutil.copy2(src_txt, dst_txt)

                            stats['files_created'] += 1
                            stats['files_by_year'][year] = stats['files_by_year'].get(year, 0) + 1
                            stats['files_by_type']['TXT'] = stats['files_by_type'].get('TXT', 0) + 1

                            # Copy test.pdf → {filename}.PDF
                            src_pdf = os.path.join(args.LocationTestFile, 'test.pdf')
                            dst_pdf = os.path.join(args.TargetFolder, f"{filename_base}.PDF")
                            shutil.copy2(src_pdf, dst_pdf)

                            stats['files_created'] += 1
                            stats['files_by_year'][year] = stats['files_by_year'].get(year, 0) + 1
                            stats['files_by_type']['PDF'] = stats['files_by_type'].get('PDF', 0) + 1

                        # Category 3-9: 70% - ONLY TXT (from FRX16.txt or CFSUL003.txt)
                        else:
                            # Randomly choose between FRX16.txt or CFSUL003.txt for TXT source
                            txt_source = random.choice(['FRX16.txt', 'CFSUL003.txt'])
                            src_txt = os.path.join(args.LocationTestFile, txt_source)
                            dst_txt = os.path.join(args.TargetFolder, f"{filename_base}.TXT")
                            shutil.copy2(src_txt, dst_txt)

                            stats['files_created'] += 1
                            stats['files_by_year'][year] = stats['files_by_year'].get(year, 0) + 1
                            stats['files_by_type']['TXT'] = stats['files_by_type'].get('TXT', 0) + 1

                            # NO AFP or PDF file for this category

                        stats['instances_processed'] += 1

                        # Progress display (quiet mode)
                        if args.quiet:
                            print_progress(
                                species_name,
                                idx,
                                len(species_list),
                                stats['instances_processed'],
                                stats['files_created'],
                                filename_rpt
                            )

                    except (KeyError, OSError) as e:
                        # Skip malformed rows or file copy errors
                        if not args.quiet:
                            print(f"    WARNING: Error processing row: {str(e)}", file=sys.stderr)
                        continue

        except Exception as e:
            logging.error(f"Failed to process {instance_csv}: {str(e)}")
            if not args.quiet:
                print(f"  ERROR: Failed to process {instance_csv}: {str(e)}", file=sys.stderr)
            # Save progress even on error
            save_progress(species_id, stats)
            continue

        stats['species_processed'] += 1

        # Save progress after each species
        save_progress(species_id, stats)
        logging.info(f"Completed species {species_name} (ID={species_id}). Progress saved.")

    # Calculate elapsed time
    elapsed_time = time.time() - start_time

    # Print final statistics
    print_statistics(stats, elapsed_time)

    # Clear progress file if all species processed
    if args.Number == 0 or len(species_list) < args.Number:
        clear_progress()
        logging.info("All species processed. Progress file cleared.")
    else:
        logging.info(f"Batch complete. Processed {len(species_list)} species. Run again to continue.")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user (Ctrl+C)")
        print("Progress saved. Run script again to resume.")
        logging.warning("Interrupted by user (Ctrl+C)")
        logging.info("Progress saved. Run script again to resume.")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)
