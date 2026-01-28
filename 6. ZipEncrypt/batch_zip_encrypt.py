#!/usr/bin/env python3
"""
Batch Zip and Encrypt Files Using 7zip

This script reads report species from CSV, extracts filenames from corresponding
output CSVs, finds matching files using wildcards, and creates 7z archives
organized by year with resume capability.

Improvements:
- Optional password (no password = no encryption)
- Adds "Compressed_Filename" column to instance CSVs (updated in real-time)
- Real-time log file writing with immediate flushing
- Real-time compress-log.csv writing (append mode, survives crashes)
- CSV logs for missing species and files
- Persistent statistics across interruptions
- Crash recovery: resumes from last processed file
- Batch processing: limit number of species per run (default: 5)
- Delete source files after compression (optional, requires --delete-after-compress Yes)
- Simulate mode: Skip actual compression and store simulated paths

Author: Claude Code
Date: 2025
"""

import argparse
import csv
import glob
import json
import logging
import os
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Tuple, Optional


# Constants
PROGRESS_FILE = "batch_zip_encrypt_progress.json"
LOG_FILE = "batch_zip_encrypt.log"
MISSING_SPECIES_CSV = "missing_species.csv"
MISSING_FILES_CSV = "missing_files.csv"
COMPRESS_LOG_CSV = "compress-log.csv"  # Complete audit trail
DEFAULT_SPECIES_CSV = "Report_Species.csv"
DEFAULT_INSTANCES_FOLDER = "Output_Extract_Instances"


# Statistics tracker
class Stats:
    def __init__(self, archives_created=0, files_skipped=0, errors=0, no_files_found=0, species_not_found=0):
        self.archives_created = archives_created
        self.files_skipped = files_skipped
        self.errors = errors
        self.no_files_found = no_files_found
        self.species_not_found = species_not_found

    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'archives_created': self.archives_created,
            'files_skipped': self.files_skipped,
            'errors': self.errors,
            'no_files_found': self.no_files_found,
            'species_not_found': self.species_not_found
        }

    @classmethod
    def from_dict(cls, data):
        """Create Stats from dictionary"""
        return cls(
            archives_created=data.get('archives_created', 0),
            files_skipped=data.get('files_skipped', 0),
            errors=data.get('errors', 0),
            no_files_found=data.get('no_files_found', 0),
            species_not_found=data.get('species_not_found', 0)
        )

    def report(self):
        """Generate summary report"""
        return (f"Summary: {self.archives_created} archives created, "
                f"{self.files_skipped} skipped, {self.no_files_found} no files found, "
                f"{self.species_not_found} species not found, {self.errors} errors")


# Global stats
stats = Stats()


# CSV loggers for missing items
missing_species_log = []
missing_files_log = []
compress_log = []  # Complete audit trail of all processing (kept for backwards compatibility)


def init_compress_log():
    """Initialize compress-log.csv with headers if it doesn't exist"""
    if not os.path.exists(COMPRESS_LOG_CSV):
        try:
            with open(COMPRESS_LOG_CSV, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'species_id', 'Species_name', 'Species_Instance_Filename',
                    'row', 'Filename', 'Status', 'Compressed_Filename'
                ])
                writer.writeheader()
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            logging.error(f"Error initializing compress log CSV: {e}")


def append_compress_log(entry: Dict):
    """
    Append a single entry to compress-log.csv in real-time

    Args:
        entry: Dict with keys: species_id, Species_name, Species_Instance_Filename,
               row, Filename, Status, Compressed_Filename
    """
    try:
        # Check if file exists to determine if we need headers
        file_exists = os.path.exists(COMPRESS_LOG_CSV)

        with open(COMPRESS_LOG_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'species_id', 'Species_name', 'Species_Instance_Filename',
                'row', 'Filename', 'Status', 'Compressed_Filename'
            ])

            # Write header if file is new
            if not file_exists:
                writer.writeheader()

            writer.writerow(entry)
            # Force immediate flush to disk
            f.flush()
            os.fsync(f.fileno())

        # Also keep in memory for backwards compatibility
        compress_log.append(entry)
    except Exception as e:
        logging.error(f"Error appending to compress log CSV: {e}")


def setup_logging(quiet=False):
    """Initialize logging configuration with real-time flushing"""
    # Create file handler with unbuffered writing
    file_handler = logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    # Force immediate flush after each log
    class FlushFileHandler(logging.FileHandler):
        def emit(self, record):
            super().emit(record)
            self.flush()

    # Replace with flushing handler
    file_handler = FlushFileHandler(LOG_FILE, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    handlers = [file_handler]

    if not quiet:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.WARNING)
        handlers.append(console_handler)

    # Get root logger and set it up
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.handlers = []  # Clear existing handlers
    for handler in handlers:
        logger.addHandler(handler)


def check_7zip(zip_path: str) -> bool:
    """
    Verify 7zip is installed and accessible

    Args:
        zip_path: Path to 7z executable

    Returns:
        True if 7zip is available, raises error otherwise
    """
    try:
        result = subprocess.run(
            [zip_path, "--help"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            logging.info(f"7zip found: {zip_path}")
            return True
        else:
            raise RuntimeError(f"7zip command failed with return code {result.returncode}")
    except FileNotFoundError:
        logging.error(f"7zip not found at: {zip_path}")
        logging.error("Please install 7-Zip from https://www.7-zip.org/")
        logging.error("Or specify the path with --7zip-path parameter")
        raise
    except Exception as e:
        logging.error(f"Error checking 7zip: {e}")
        raise


def load_progress(reset: bool = False) -> Tuple[Optional[int], int, Stats]:
    """
    Load progress from JSON file (Task 4: includes statistics)

    Args:
        reset: If True, ignore existing progress file

    Returns:
        Tuple of (report_species_id, row_index, Stats) or (None, 0, Stats()) if no progress
    """
    if reset:
        logging.info("Progress reset requested, starting from beginning")
        return None, 0, Stats()

    if not os.path.exists(PROGRESS_FILE):
        logging.info("No progress file found, starting from beginning")
        return None, 0, Stats()

    try:
        with open(PROGRESS_FILE, 'r') as f:
            progress = json.load(f)
            species_id = progress.get('report_species_id')
            row_idx = progress.get('row_index', 0)
            stats_data = progress.get('stats', {})
            loaded_stats = Stats.from_dict(stats_data)

            logging.info(f"Resuming from species_id={species_id}, row_index={row_idx}")
            logging.info(f"Loaded stats: {loaded_stats.report()}")
            return species_id, row_idx, loaded_stats
    except json.JSONDecodeError:
        logging.error("Corrupted progress file detected. Use --reset-progress to start over.")
        raise
    except Exception as e:
        logging.error(f"Error loading progress file: {e}")
        raise


def save_progress(species_id: int, row_idx: int, stats_obj: Stats):
    """
    Save current progress to JSON file (Task 4: includes statistics)

    Args:
        species_id: Current report_species_id being processed
        row_idx: Current row index within the species CSV
        stats_obj: Current statistics object
    """
    try:
        progress = {
            'report_species_id': species_id,
            'row_index': row_idx,
            'stats': stats_obj.to_dict()
        }
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(progress, f, indent=2)
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


def save_missing_logs():
    """
    Save CSV logs for missing species and files (Task 3)
    """
    # Save missing species log
    if missing_species_log:
        try:
            with open(MISSING_SPECIES_CSV, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['Species_Name', 'Species_ID'])
                writer.writeheader()
                writer.writerows(missing_species_log)
            logging.info(f"Saved {len(missing_species_log)} missing species to {MISSING_SPECIES_CSV}")
        except Exception as e:
            logging.error(f"Error saving missing species CSV: {e}")

    # Save missing files log
    if missing_files_log:
        try:
            with open(MISSING_FILES_CSV, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['Species_Name', 'Filename', 'Year', 'Base_Filename'])
                writer.writeheader()
                writer.writerows(missing_files_log)
            logging.info(f"Saved {len(missing_files_log)} missing files to {MISSING_FILES_CSV}")
        except Exception as e:
            logging.error(f"Error saving missing files CSV: {e}")

    # Save complete compress log (NEW: complete audit trail)
    if compress_log:
        try:
            with open(COMPRESS_LOG_CSV, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=[
                    'species_id', 'Species_name', 'Species_Instance_Filename',
                    'row', 'Filename', 'Status', 'Compressed_Filename'
                ])
                writer.writeheader()
                writer.writerows(compress_log)
            logging.info(f"Saved {len(compress_log)} entries to {COMPRESS_LOG_CSV}")
        except Exception as e:
            logging.error(f"Error saving compress log CSV: {e}")


def read_species_csv(csv_path: str, filter_species: Optional[List[str]] = None) -> List[Dict]:
    """
    Read Report_Species.csv and return list of species

    Args:
        csv_path: Path to Report_Species.csv
        filter_species: Optional list of species names to process

    Returns:
        List of dicts with keys: Report_Species_Id, Report_Species_Name
    """
    species_list = []

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                species_name = row['Report_Species_Name']
                species_id = int(row['Report_Species_Id'])

                # Apply filter if specified
                if filter_species and species_name not in filter_species:
                    continue

                species_list.append({
                    'Report_Species_Id': species_id,
                    'Report_Species_Name': species_name
                })

        logging.info(f"Loaded {len(species_list)} species from {csv_path}")
        return species_list

    except Exception as e:
        logging.error(f"Error reading species CSV: {e}")
        raise


def find_instance_csv(instances_folder: str, species_name: str) -> Optional[str]:
    """
    Find CSV file matching species name pattern

    Args:
        instances_folder: Path to Output_Extract_Instances folder
        species_name: Species name (e.g., "BC2060P")

    Returns:
        Path to matching CSV file or None if not found
    """
    pattern = os.path.join(instances_folder, f"{species_name}_*.csv")
    matches = glob.glob(pattern)

    if matches:
        # Return first match
        return matches[0]
    else:
        # Try exact match without wildcard
        exact_path = os.path.join(instances_folder, f"{species_name}.csv")
        if os.path.exists(exact_path):
            return exact_path

    return None


def read_instance_csv_full(csv_path: str) -> Tuple[List[str], List[Dict]]:
    """
    Read instance CSV and return fieldnames and all rows (Task 2)

    Args:
        csv_path: Path to instance CSV file

    Returns:
        Tuple of (fieldnames, rows as dicts)
    """
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)

        logging.info(f"Loaded {len(rows)} rows from {csv_path}")
        return fieldnames, rows

    except Exception as e:
        logging.error(f"Error reading instance CSV {csv_path}: {e}")
        raise


def write_instance_csv_full(csv_path: str, fieldnames: List[str], rows: List[Dict]):
    """
    Write updated instance CSV with new column (Task 2)
    Includes explicit flush to ensure real-time disk write

    Args:
        csv_path: Path to instance CSV file
        fieldnames: Column names
        rows: Row data
    """
    try:
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            # Explicit flush to ensure data is written to disk immediately
            f.flush()
            os.fsync(f.fileno())

        logging.info(f"Updated instance CSV: {csv_path}")
    except Exception as e:
        logging.error(f"Error writing instance CSV {csv_path}: {e}")
        raise


def find_files_by_pattern(source_folder: str, base_filename: str) -> List[str]:
    """
    Find files matching wildcard pattern

    Args:
        source_folder: Directory to search
        base_filename: Base filename without extension

    Returns:
        List of matching file paths
    """
    pattern = os.path.join(source_folder, f"{base_filename}.*")
    matches = glob.glob(pattern)
    return matches


def create_7z_archive(
    zip_path: str,
    output_file: str,
    input_files: List[str],
    password: Optional[str],
    compression_level: int = 5
) -> bool:
    """
    Create 7z archive (with optional password) (Task 1)

    Args:
        zip_path: Path to 7z executable
        output_file: Output 7z file path
        input_files: List of files to archive
        password: Encryption password (None = no encryption)
        compression_level: Compression level 0-9 (Task 5)

    Returns:
        True if successful, False otherwise
    """
    try:
        # Build 7zip command
        cmd = [
            zip_path,
            'a',              # Add to archive
            '-t7z',           # 7z format
            f'-mx={compression_level}',  # Compression level
            output_file
        ]

        # Add password options if provided (Task 1)
        if password:
            cmd.insert(3, f'-p{password}')  # Password
            cmd.insert(4, '-mhe=on')        # Encrypt headers

        cmd.extend(input_files)

        # Run 7zip
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode == 0:
            return True
        else:
            logging.error(f"7zip command failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logging.error(f"7zip command timed out for {output_file}")
        return False
    except Exception as e:
        logging.error(f"Error creating 7z archive {output_file}: {e}")
        return False


def sanitize_year(year: str) -> str:
    """
    Sanitize year value, handle empty or invalid values

    Args:
        year: Year string from CSV

    Returns:
        Sanitized year string
    """
    if not year or not year.strip():
        return "UNKNOWN"

    # Extract numeric year if present
    year = year.strip()
    if year.isdigit():
        return year

    # Try to extract year from datetime string
    for part in year.split():
        if part.isdigit() and len(part) == 4:
            return part

    return "UNKNOWN"


def print_progress_line(message: str, quiet: bool = False):
    """
    Print progress on a single line (overwrites previous line in quiet mode)

    Args:
        message: Message to display
        quiet: If True, use carriage return to overwrite line
    """
    if quiet:
        # Overwrite the same line
        sys.stdout.write('\r' + ' ' * 120 + '\r')  # Clear line
        sys.stdout.write(message)
        sys.stdout.flush()
    else:
        print(message)


def process_species(
    species: Dict,
    instances_folder: str,
    source_folder: str,
    output_folder: str,
    password: Optional[str],
    zip_path: str,
    compression_level: int,
    resume_species_id: Optional[int],
    resume_row_idx: int,
    stats_obj: Stats,
    delete_after_compress: bool = False,
    quiet: bool = False,
    simulate_zip: bool = False
) -> Tuple[bool, int]:
    """
    Process a single species (all instances in its CSV)

    Args:
        species: Dict with Report_Species_Id and Report_Species_Name
        instances_folder: Path to instance CSVs folder
        source_folder: Path to source files
        output_folder: Path to output archives
        password: Encryption password (None = no encryption)
        zip_path: Path to 7z executable
        compression_level: Compression level 0-9
        resume_species_id: Species ID to resume from (or None)
        resume_row_idx: Row index to resume from
        stats_obj: Statistics object
        delete_after_compress: Delete source files after successful compression
        quiet: Suppress console output
        simulate_zip: Skip actual compression and store simulated paths

    Returns:
        Tuple of (should_continue, last_row_idx)
    """
    species_id = species['Report_Species_Id']
    species_name = species['Report_Species_Name']

    # If resuming, skip species until we reach the resume point
    if resume_species_id is not None and species_id < resume_species_id:
        logging.info(f"Skipping species {species_name} (id={species_id}), not yet at resume point")
        return True, 0

    # Find instance CSV
    instance_csv = find_instance_csv(instances_folder, species_name)
    if not instance_csv:
        # Log missing species (Task 3)
        logging.warning(f"No instance CSV found for species {species_name}")
        missing_species_log.append({
            'Species_Name': species_name,
            'Species_ID': species_id
        })
        stats_obj.species_not_found += 1
        return True, 0

    # Get CSV filename for better logging
    csv_filename = os.path.basename(instance_csv)

    logging.info(f"Processing species: {species_name} (id={species_id}) - {csv_filename}")

    # Read instance CSV (full) (Task 2)
    try:
        fieldnames, rows = read_instance_csv_full(instance_csv)

        # Add "Compressed_Filename" column if not exists (Task 2)
        if 'Compressed_Filename' not in fieldnames:
            fieldnames = list(fieldnames) + ['Compressed_Filename']
            for row in rows:
                if 'Compressed_Filename' not in row:
                    row['Compressed_Filename'] = ''

    except Exception as e:
        logging.error(f"Failed to read instance CSV for {species_name}: {e}")
        stats_obj.errors += 1
        return True, 0

    total_rows = len(rows)
    logging.info(f"Found {total_rows} rows in {csv_filename}")

    # Process each row
    for row_idx, row in enumerate(rows, 1):  # Start from 1 for better readability
        # If resuming this species, skip rows until we reach resume point
        if resume_species_id == species_id and row_idx <= resume_row_idx:
            logging.info(f"Skipping {csv_filename} row {row_idx}/{total_rows} (already processed)")
            continue

        filename = row.get('FILENAME', '')
        year = row.get('YEAR', '')

        # Skip empty filenames
        if not filename or not filename.strip():
            logging.warning(f"Empty filename in {csv_filename} row {row_idx}/{total_rows}")
            continue

        # Remove .RPT extension
        base_filename = filename
        if base_filename.upper().endswith('.RPT'):
            base_filename = base_filename[:-4]

        # Sanitize year
        year = sanitize_year(year)

        # Create year subfolder (skip in simulate mode)
        if not simulate_zip:
            year_folder = os.path.join(output_folder, year)
            os.makedirs(year_folder, exist_ok=True)
            output_7z = os.path.join(year_folder, f"{base_filename}.7z")
        else:
            year_folder = None
            output_7z = None

        # Compressed filename for CSV column (Task 2)
        if simulate_zip:
            # In simulate mode, prefix with "SIMULATE\YYYY\name.7z"
            compressed_filename = f"SIMULATE\\{year}\\{base_filename}.7z"
        else:
            # Normal mode: just "\YYYY\name.7z"
            compressed_filename = f"\\{year}\\{base_filename}.7z"
        # Check if archive already exists (skip in simulate mode)
        if not simulate_zip and os.path.exists(output_7z):
            # Log to compress log (SKIPPED - already exists) - written in real-time
            append_compress_log({
                'species_id': species_id,
                'Species_name': species_name,
                'Species_Instance_Filename': csv_filename,
                'row': row_idx,
                'Filename': filename,
                'Status': 'SKIPPED',
                'Compressed_Filename': compressed_filename
            })

            # Already exists, update CSV if needed (Task 2)
            if row.get('Compressed_Filename') != compressed_filename:
                row['Compressed_Filename'] = compressed_filename
                # Write CSV immediately after update
                try:
                    write_instance_csv_full(instance_csv, fieldnames, rows)
                    logging.info(f"Processing: {csv_filename} row {row_idx}/{total_rows}: {base_filename} - already exists, CSV updated")
                except Exception as e:
                    logging.error(f"Failed to update CSV for {csv_filename}: {e}")
                    stats_obj.errors += 1
            else:
                logging.info(f"Processing: {csv_filename} row {row_idx}/{total_rows}: {base_filename} - skipping (already exists)")

            # Show progress in quiet mode
            if quiet:
                print_progress_line(f"Processing: {csv_filename} row {row_idx}/{total_rows}: {base_filename} - SKIPPED (exists)", quiet=True)

            stats_obj.files_skipped += 1
            save_progress(species_id, row_idx, stats_obj)
            continue

        # Find matching files (skip in simulate mode)
        if not simulate_zip:
            source_files = find_files_by_pattern(source_folder, base_filename)
        else:
            # In simulate mode, assume files exist
            source_files = [f"{base_filename}.*"]

        if not source_files:
            # Log to compress log (NO FILES FOUND) - written in real-time
            append_compress_log({
                'species_id': species_id,
                'Species_name': species_name,
                'Species_Instance_Filename': csv_filename,
                'row': row_idx,
                'Filename': filename,
                'Status': 'NO_FILES_FOUND',
                'Compressed_Filename': ''
            })

            # Log missing files (Task 3)
            logging.warning(f"Processing: {csv_filename} row {row_idx}/{total_rows}: {base_filename} - NO FILES FOUND in {source_folder}")
            missing_files_log.append({
                'Species_Name': species_name,
                'Filename': filename,
                'Year': year,
                'Base_Filename': base_filename
            })
            stats_obj.no_files_found += 1

            # Show progress in quiet mode
            if quiet:
                print_progress_line(f"Processing: {csv_filename} row {row_idx}/{total_rows}: {base_filename} - NO FILES FOUND", quiet=True)

            # Leave Compressed_Filename empty (Task 2)
            row['Compressed_Filename'] = ''

            # Write CSV immediately after update
            try:
                write_instance_csv_full(instance_csv, fieldnames, rows)
            except Exception as e:
                logging.error(f"Failed to update CSV for {csv_filename}: {e}")
                stats_obj.errors += 1

            save_progress(species_id, row_idx, stats_obj)
            continue

        # Create 7z archive (or simulate)
        if simulate_zip:
            # Simulate mode: skip actual compression
            logging.info(f"Processing: {csv_filename} row {row_idx}/{total_rows}: {base_filename} - SIMULATING archive (would compress {len(source_files)} files)")
            if quiet:
                print_progress_line(f"Processing: {csv_filename} row {row_idx}/{total_rows}: {base_filename} - SIMULATING...", quiet=True)
            success = True  # Always success in simulate mode
        else:
            # Normal mode: create actual archive
            logging.info(f"Processing: {csv_filename} row {row_idx}/{total_rows}: {base_filename} - creating archive (found {len(source_files)} files)")
            if quiet:
                print_progress_line(f"Processing: {csv_filename} row {row_idx}/{total_rows}: {base_filename} - compressing {len(source_files)} files...", quiet=True)
            success = create_7z_archive(zip_path, output_7z, source_files, password, compression_level)

        if success:
            # Log to compress log (SUCCESS or SIMULATED) - written in real-time
            append_compress_log({
                'species_id': species_id,
                'Species_name': species_name,
                'Species_Instance_Filename': csv_filename,
                'row': row_idx,
                'Filename': filename,
                'Status': 'SIMULATED' if simulate_zip else 'SUCCESS',
                'Compressed_Filename': compressed_filename
            })

            stats_obj.archives_created += 1
            # Update CSV with compressed filename (Task 2)
            row['Compressed_Filename'] = compressed_filename

            # Write CSV immediately after successful creation
            try:
                write_instance_csv_full(instance_csv, fieldnames, rows)
                # Log success AFTER CSV is written and flushed
                mode_msg = "SIMULATED" if simulate_zip else "SUCCESS"
                logging.info(f"Processing: {csv_filename} row {row_idx}/{total_rows}: {base_filename} - {mode_msg} - {compressed_filename}")
                logging.info(f"CSV updated with: {compressed_filename}")

                # Delete source files after successful compression if enabled (not in simulate mode)
                if delete_after_compress and not simulate_zip:
                    deleted_count = 0
                    for source_file in source_files:
                        try:
                            os.remove(source_file)
                            deleted_count += 1
                            logging.info(f"Deleted source file: {source_file}")
                        except Exception as e:
                            logging.error(f"Failed to delete source file {source_file}: {e}")
                    logging.info(f"Deleted {deleted_count}/{len(source_files)} source files")

                # Show progress in quiet mode
                if quiet:
                    delete_msg = f" (deleted {len(source_files)} files)" if (delete_after_compress and not simulate_zip) else ""
                    status_msg = "SIMULATED" if simulate_zip else "SUCCESS"
                    print_progress_line(f"Processing: {csv_filename} row {row_idx}/{total_rows}: {base_filename} - {status_msg}{delete_msg}", quiet=True)
            except Exception as e:
                logging.error(f"Failed to update CSV for {csv_filename}: {e}")
                stats_obj.errors += 1
        else:
            # Log to compress log (FAILED) - written in real-time
            append_compress_log({
                'species_id': species_id,
                'Species_name': species_name,
                'Species_Instance_Filename': csv_filename,
                'row': row_idx,
                'Filename': filename,
                'Status': 'FAILED',
                'Compressed_Filename': ''
            })

            stats_obj.errors += 1
            # Leave Compressed_Filename empty on error (Task 2)
            row['Compressed_Filename'] = ''

            # Write CSV immediately even on error
            try:
                write_instance_csv_full(instance_csv, fieldnames, rows)
            except Exception as e:
                logging.error(f"Failed to update CSV for {csv_filename}: {e}")
                stats_obj.errors += 1

            logging.error(f"Processing: {csv_filename} row {row_idx}/{total_rows}: {base_filename} - FAILED to create archive")

            # Show error in quiet mode
            if quiet:
                print_progress_line(f"Processing: {csv_filename} row {row_idx}/{total_rows}: {base_filename} - FAILED", quiet=True)

        # Save progress after each file
        save_progress(species_id, row_idx, stats_obj)

    logging.info(f"Completed processing {csv_filename}: {total_rows} rows processed")
    return True, total_rows


def main():
    """Main processing function"""
    parser = argparse.ArgumentParser(
        description='Batch zip and encrypt files using 7zip with resume capability'
    )

    # Required arguments
    parser.add_argument('--source-folder', required=True,
                        help='Directory containing files to zip')
    parser.add_argument('--output-folder', required=True,
                        help='Directory to save 7z files')

    # Task 1: Password is now optional
    parser.add_argument('--password',
                        help='Encryption password for 7z archives (optional, no password = no encryption)')

    # Optional arguments
    parser.add_argument('--species-csv',
                        help=f'Path to Report_Species.csv (default: {DEFAULT_SPECIES_CSV})')
    parser.add_argument('--instances-folder',
                        help=f'Path to Output_Extract_Instances folder (default: {DEFAULT_INSTANCES_FOLDER})')
    parser.add_argument('--filter-species',
                        help='Process only specific species (comma-separated)')
    parser.add_argument('--7zip-path', default='7z',
                        help='Path to 7z.exe (default: 7z)')
    parser.add_argument('--reset-progress', action='store_true',
                        help='Start from beginning, ignore existing progress')

    # Task 5: Performance options
    parser.add_argument('--compression-level', type=int, default=5, choices=range(0, 10),
                        help='Compression level 0-9 (0=store, 5=normal, 9=ultra, default: 5)')
    parser.add_argument('--quiet', action='store_true',
                        help='Suppress console output (log to file only)')

    # Batch processing options
    parser.add_argument('--max-species', type=int, default=5,
                        help='Maximum number of species to process in this run (default: 5, use 0 for unlimited)')
    parser.add_argument('--delete-after-compress', type=str, default='No',
                        help='Delete source files after successful compression (must specify "Yes" to enable, default: No)')
    parser.add_argument('--SIMULATEZIP', action='store_true',
                        help='Simulate mode: Skip actual compression and store simulated paths with SIMULATE prefix')

    args = parser.parse_args()

    # Setup logging (Task 3: reduced console output)
    setup_logging(quiet=args.quiet)

    # Initialize compress log CSV with headers (real-time writing)
    init_compress_log()

    # Parse delete-after-compress parameter
    delete_after_compress = args.delete_after_compress.strip().lower() == 'yes'

    logging.info("=" * 80)
    logging.info("Batch Zip and Encrypt - Starting")
    if args.SIMULATEZIP:
        logging.info("Mode: SIMULATION (no actual compression)")
    elif args.password:
        logging.info("Mode: Encrypted archives (password protected)")
    else:
        logging.info("Mode: Unencrypted archives (no password)")
    logging.info(f"Compression level: {args.compression_level}")
    logging.info(f"Max species per run: {args.max_species if args.max_species > 0 else 'unlimited'}")
    logging.info(f"Delete after compress: {'YES' if delete_after_compress else 'NO'}")
    if delete_after_compress:
        logging.warning("!!! DELETE MODE ENABLED: Source files will be deleted after successful compression !!!")
    logging.info("=" * 80)

    try:
        # Validate folders
        if not os.path.exists(args.source_folder):
            logging.error(f"Source folder does not exist: {args.source_folder}")
            sys.exit(1)

        # Create output folder if needed
        os.makedirs(args.output_folder, exist_ok=True)

        # Check 7zip
        check_7zip(args.__dict__['7zip_path'])

        # Resolve CSV paths
        script_dir = Path(__file__).parent
        species_csv = args.species_csv or os.path.join(script_dir, DEFAULT_SPECIES_CSV)
        instances_folder = args.instances_folder or os.path.join(script_dir, DEFAULT_INSTANCES_FOLDER)

        if not os.path.exists(species_csv):
            logging.error(f"Species CSV not found: {species_csv}")
            sys.exit(1)

        if not os.path.exists(instances_folder):
            logging.error(f"Instances folder not found: {instances_folder}")
            sys.exit(1)

        # Parse filter species
        filter_species = None
        if args.filter_species:
            filter_species = [s.strip() for s in args.filter_species.split(',')]
            logging.info(f"Filtering for species: {filter_species}")

        # Load progress (Task 4: includes statistics)
        resume_species_id, resume_row_idx, loaded_stats = load_progress(args.reset_progress)
        global stats
        stats = loaded_stats

        # Read species CSV
        species_list = read_species_csv(species_csv, filter_species)

        if not species_list:
            logging.warning("No species to process")
            sys.exit(0)

        logging.info(f"Processing {len(species_list)} species...")

        # Track species processed in this run
        species_processed_count = 0

        # Process each species
        for idx, species in enumerate(species_list, 1):
            # Check if we've reached max-species limit for this run
            if args.max_species > 0 and species_processed_count >= args.max_species:
                logging.info(f"=" * 80)
                logging.info(f"Reached max-species limit ({args.max_species}). Stopping this run.")
                logging.info(f"Run again to continue processing remaining species.")
                logging.info(f"=" * 80)
                break

            logging.info(f"=" * 80)
            logging.info(f"Species {idx}/{len(species_list)}: {species['Report_Species_Name']} (ID: {species['Report_Species_Id']})")
            logging.info(f"=" * 80)

            try:
                should_continue, last_row = process_species(
                    species,
                    instances_folder,
                    args.source_folder,
                    args.output_folder,
                    args.password,
                    args.__dict__['7zip_path'],
                    args.compression_level,
                    resume_species_id,
                    resume_row_idx if resume_species_id == species['Report_Species_Id'] else 0,
                    stats,
                    delete_after_compress=delete_after_compress,
                    quiet=args.quiet,
                    simulate_zip=args.SIMULATEZIP
                )

                # Increment species processed count (only count species that were actually processed, not skipped)
                if resume_species_id is None or resume_species_id == species['Report_Species_Id']:
                    species_processed_count += 1

                # Reset resume point after first species
                if resume_species_id == species['Report_Species_Id']:
                    resume_species_id = None
                    resume_row_idx = 0

                if not should_continue:
                    break

            except KeyboardInterrupt:
                if args.quiet:
                    # Clear progress line before exit message
                    sys.stdout.write('\r' + ' ' * 120 + '\r')
                    sys.stdout.flush()
                    print("\nInterrupted by user (Ctrl+C)")
                    print(f"Progress and statistics saved. Run script again to resume.")
                    print(stats.report())

                logging.warning("\nInterrupted by user (Ctrl+C)")
                logging.info(f"Progress and statistics saved. Run script again to resume.")
                logging.info(stats.report())

                # Save missing logs before exit (Task 3)
                save_missing_logs()
                sys.exit(0)
            except Exception as e:
                logging.error(f"Error processing species {species['Report_Species_Name']}: {e}")
                stats.errors += 1
                continue

        # Processing complete
        if args.quiet:
            # Clear the progress line and show completion
            sys.stdout.write('\r' + ' ' * 120 + '\r')
            sys.stdout.flush()
            if args.max_species > 0 and species_processed_count >= args.max_species:
                print(f"Batch Complete! Processed {species_processed_count} species in this run.")
                print("Run again to continue processing remaining species.")
            else:
                print("Processing Complete! All species processed.")
            print(stats.report())

        logging.info("=" * 80)
        if args.max_species > 0 and species_processed_count >= args.max_species:
            logging.info(f"Batch Complete! Processed {species_processed_count} species in this run.")
            logging.info("Run again to continue processing remaining species.")
        else:
            logging.info("Processing Complete! All species processed.")
        logging.info(stats.report())
        logging.info("=" * 80)

        # Save missing logs (Task 3)
        save_missing_logs()

        # Clear progress file only if all species were processed
        if not (args.max_species > 0 and species_processed_count >= args.max_species):
            clear_progress()
            logging.info("All species processed. Progress file cleared.")
        else:
            logging.info(f"Progress saved. {species_processed_count} species processed in this batch.")

    except KeyboardInterrupt:
        if args.quiet:
            # Clear progress line before exit message
            sys.stdout.write('\r' + ' ' * 120 + '\r')
            sys.stdout.flush()
            print("\nInterrupted by user (Ctrl+C)")
            print(f"Progress and statistics saved. Run script again to resume.")
            print(stats.report())

        logging.warning("\nInterrupted by user (Ctrl+C)")
        logging.info(f"Progress and statistics saved. Run script again to resume.")
        logging.info(stats.report())

        # Save missing logs before exit (Task 3)
        save_missing_logs()
        sys.exit(0)
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
