#!/usr/bin/env python3
"""
Extract_Instances.py - SQL Server Report Instance Extractor

This script processes report species from Report_Species.csv, executes SQL Server queries
to extract report instances, and outputs separate CSV files per report with results.

Features:
- Resume capability via progress tracking
- Support for Windows Authentication and SQL Server Authentication
- Automatic IN_USE=0 updates for reports with no instances
- Timezone conversion (AS_OF_TIMESTAMP to UTC) with configurable source timezone
- Comprehensive logging and error handling

Timezone Support:
- Uses IANA timezone database (pytz library)
- Common timezones: Asia/Singapore, America/New_York, Europe/London, Asia/Tokyo, UTC
- Full list: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
"""

import pymssql
import csv
import argparse
import logging
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import pytz
from rpt_section_reader import read_sectionhdr, format_segments


# ============================================================================
# Configuration and Setup
# ============================================================================

def setup_logging(output_dir, quiet=False):
    """Setup logging to both console and file.

    Args:
        output_dir: Directory for log file
        quiet: If True, suppress console output (file logging only)
    """
    log_file = os.path.join(output_dir, 'Extract_Instances.log')

    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter('%(levelname)s - %(message)s')

    # File handler (DEBUG level) - always enabled
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)

    # Console handler (INFO level) - only if not quiet mode
    if not quiet:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    return logger


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Extract report instances from SQL Server database to CSV files.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Windows Authentication with year filtering
  python Extract_Instances.py --server localhost --database IntelliSTOR --windows-auth --start-year 2023

  # SQL Server Authentication with year range
  python Extract_Instances.py --server localhost --database IntelliSTOR --user sa --password MyP@ssw0rd --start-year 2023 --end-year 2024

  # Using YEAR from filename instead of timestamp
  python Extract_Instances.py --server localhost --database IntelliSTOR --windows-auth --start-year 2023 --year-from-filename

  # Quiet mode with single-line progress counter
  python Extract_Instances.py --server localhost --database IntelliSTOR --windows-auth --start-year 2023 --quiet

  # Custom timezone for UTC conversion (default is Asia/Singapore)
  python Extract_Instances.py --server localhost --database IntelliSTOR --windows-auth --start-year 2023 --timezone "America/New_York"
  python Extract_Instances.py --server localhost --database IntelliSTOR --windows-auth --start-year 2023 --timezone "Europe/London"
  python Extract_Instances.py --server localhost --database IntelliSTOR --windows-auth --start-year 2023 --timezone "Asia/Tokyo"

  # SEGMENTS from RPT file SECTIONHDR (section_id#start_page#page_count format)
  python Extract_Instances.py --server localhost --database IntelliSTOR --windows-auth --start-year 2023 \\
      --rptfolder "/path/to/rpt/files"

  # Custom paths with all options
  python Extract_Instances.py --server myserver --database IntelliSTOR --windows-auth \\
      --start-year 2023 --end-year 2025 --year-from-filename --timezone "Asia/Singapore" --quiet \\
      --rptfolder "/data/rptfiles" --input "C:\\path\\to\\Report_Species.csv" --output-dir "C:\\output"
        """
    )

    # Database connection parameters
    parser.add_argument(
        '--server',
        required=True,
        help='SQL Server host/IP address'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=1433,
        help='SQL Server port (default: 1433)'
    )
    parser.add_argument(
        '--database',
        required=True,
        help='Database name'
    )
    parser.add_argument(
        '--user',
        help='Username for SQL Server authentication'
    )
    parser.add_argument(
        '--password',
        help='Password for SQL Server authentication'
    )
    parser.add_argument(
        '--windows-auth',
        action='store_true',
        help='Use Windows Authentication instead of SQL Server authentication'
    )

    # File parameters
    parser.add_argument(
        '--input', '-i',
        default=r'Report_Species.csv',
        help='Input CSV file path (default: Report_Species.csv in current directory)'
    )
    parser.add_argument(
        '--output-dir', '-o',
        default='.',
        help='Output directory for CSV files and logs (default: current directory)'
    )

    # Year filtering parameters
    parser.add_argument(
        '--start-year',
        type=int,
        required=True,
        help='Start year for filtering (e.g., 2023) - only include records from this year onwards'
    )
    parser.add_argument(
        '--end-year',
        type=int,
        help='Optional end year for filtering (e.g., 2024) - only include records up to this year'
    )
    parser.add_argument(
        '--year-from-filename',
        action='store_true',
        help='Calculate YEAR column from first 2 chars of filename (e.g., "24013001" -> "2024") instead of from AS_OF_TIMESTAMP'
    )
    parser.add_argument(
        '--timezone',
        default='Asia/Singapore',
        help='Timezone of AS_OF_TIMESTAMP values for UTC conversion. Uses IANA timezone names (e.g., "Asia/Singapore", "America/New_York", "Europe/London", "UTC"). Default: Asia/Singapore. For full list: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones'
    )

    # RPT folder parameter
    parser.add_argument(
        '--rptfolder',
        help='Directory containing .RPT files (as named in RPTFILE.FILENAME). '
             'When provided, SEGMENTS column is populated from RPT file SECTIONHDR '
             'instead of from the database REPORT_INSTANCE_SEGMENT table.'
    )

    # Output options
    parser.add_argument(
        '--quiet',
        action='store_true',
        help='Quiet mode - show single-line progress counter instead of detailed logging'
    )

    args = parser.parse_args()

    # Validate authentication parameters
    if not args.windows_auth and (not args.user or not args.password):
        parser.error('Either --windows-auth or both --user and --password must be provided')

    # Validate year parameters
    if args.end_year and args.end_year < args.start_year:
        parser.error(f'End year ({args.end_year}) cannot be before start year ({args.start_year})')

    # Validate timezone parameter
    try:
        pytz.timezone(args.timezone)
    except pytz.exceptions.UnknownTimeZoneError:
        parser.error(f'Invalid timezone: {args.timezone}. Use IANA timezone names like "Asia/Singapore", "America/New_York", "Europe/London", "Asia/Tokyo", "UTC". See: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones')

    # Validate rptfolder parameter
    if args.rptfolder and not os.path.isdir(args.rptfolder):
        parser.error(f'RPT folder does not exist: {args.rptfolder}')

    return args


# ============================================================================
# Progress Tracking
# ============================================================================

def read_progress(progress_file):
    """
    Read last processed REPORT_SPECIES_ID from progress file.

    Args:
        progress_file: Path to progress.txt file

    Returns:
        int: Last processed REPORT_SPECIES_ID, or 0 if file doesn't exist
    """
    if not os.path.exists(progress_file):
        logging.debug(f'Progress file not found: {progress_file}. Starting from beginning.')
        return 0

    try:
        with open(progress_file, 'r', encoding='utf-8') as f:
            last_id = int(f.read().strip())
            logging.info(f'Resuming from REPORT_SPECIES_ID: {last_id}')
            return last_id
    except (ValueError, IOError) as e:
        logging.warning(f'Failed to read progress file: {e}. Starting from beginning.')
        return 0


def write_progress(progress_file, report_species_id):
    """
    Write current REPORT_SPECIES_ID to progress file.

    Args:
        progress_file: Path to progress.txt file
        report_species_id: Current REPORT_SPECIES_ID being processed
    """
    try:
        with open(progress_file, 'w', encoding='utf-8') as f:
            f.write(str(report_species_id))
        logging.debug(f'Progress updated: {report_species_id}')
    except IOError as e:
        logging.warning(f'Failed to write progress file: {e}. Progress will not be saved.')


# ============================================================================
# Database Connection
# ============================================================================

def create_connection(server, port, database, user=None, password=None, windows_auth=False):
    """
    Create SQL Server connection using pymssql.

    Args:
        server: SQL Server host/IP
        port: SQL Server port
        database: Database name
        user: Username (for SQL Server auth)
        password: Password (for SQL Server auth)
        windows_auth: Use Windows Authentication if True

    Returns:
        pymssql.Connection: Database connection object

    Raises:
        Exception: If connection fails
    """
    try:
        connection_info = f'{server}:{port}, database: {database}'
        if windows_auth:
            logging.info(f'Connecting to SQL Server using Windows Authentication: {connection_info}')
            conn = pymssql.connect(
                server=server,
                port=port,
                database=database
                #trusted=True
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
# Report Species CSV Management
# ============================================================================

def load_report_species(csv_path):
    """
    Load Report_Species.csv into memory.

    Args:
        csv_path: Path to Report_Species.csv file

    Returns:
        list: List of dictionaries containing report species data
    """
    try:
        with open(csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            report_species = list(reader)

        logging.info(f'Loaded {len(report_species)} report species from {csv_path}')
        return report_species

    except FileNotFoundError:
        logging.error(f'Report_Species.csv not found: {csv_path}')
        raise
    except Exception as e:
        logging.error(f'Failed to load Report_Species.csv: {e}')
        raise


def update_in_use(csv_path, report_species_id, new_in_use_value=0):
    """
    Update IN_USE column for a specific report species.

    Args:
        csv_path: Path to Report_Species.csv file
        report_species_id: Report_Species_Id to update
        new_in_use_value: New value for IN_USE column (default: 0)
    """
    try:
        # Read entire CSV
        rows = []
        with open(csv_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                if row['REPORT_SPECIES_ID'] == str(report_species_id):
                    row['IN_USE'] = str(new_in_use_value)
                    logging.debug(f'Updating REPORT_SPECIES_ID {report_species_id}: IN_USE={new_in_use_value}')
                rows.append(row)

        # Write back atomically (temp file + rename)
        temp_path = csv_path + '.tmp'
        with open(temp_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        # Atomic replace
        os.replace(temp_path, csv_path)
        logging.info(f'Updated IN_USE={new_in_use_value} for REPORT_SPECIES_ID {report_species_id}')

    except Exception as e:
        logging.error(f'Failed to update IN_USE for REPORT_SPECIES_ID {report_species_id}: {e}')


# ============================================================================
# SQL Query Execution
# ============================================================================

def get_sql_query(start_year, end_year=None):
    """
    Return SQL Server query for extracting report instances with year filtering.

    This query uses SQL Server 2017+ STRING_AGG function.
    Only selects essential columns for output.

    Args:
        start_year: Start year for filtering (inclusive)
        end_year: Optional end year for filtering (exclusive)

    Returns:
        str: SQL query with appropriate WHERE clauses
    """
    # Build the base query with year filtering - only needed columns
    query = """
SELECT
    ri.REPORT_SPECIES_ID,
    rfi.RPT_FILE_ID,
    RTRIM(rf.FILENAME) AS FILENAME,
    ri.AS_OF_TIMESTAMP,
    STRING_AGG(
        CONCAT(
            CAST(sec.NAME AS VARCHAR), '#',
            CAST(ris.SEGMENT_NUMBER AS VARCHAR), '#',
            CAST(ISNULL(ris.START_PAGE_NUMBER, 0) AS VARCHAR), '#',
            CAST(ris.NUMBER_OF_PAGES AS VARCHAR)
        ),
        '|'
    ) WITHIN GROUP (ORDER BY ris.SEGMENT_NUMBER ASC) AS segments
FROM REPORT_INSTANCE ri
LEFT JOIN RPTFILE_INSTANCE rfi
    ON ri.DOMAIN_ID = rfi.DOMAIN_ID
    AND ri.REPORT_SPECIES_ID = rfi.REPORT_SPECIES_ID
    AND ri.AS_OF_TIMESTAMP = rfi.AS_OF_TIMESTAMP
    AND ri.REPROCESS_IN_PROGRESS = rfi.REPROCESS_IN_PROGRESS
LEFT JOIN RPTFILE rf
    ON rfi.RPT_FILE_ID = rf.RPT_FILE_ID
LEFT JOIN REPORT_INSTANCE_SEGMENT ris
    ON ri.DOMAIN_ID = ris.DOMAIN_ID
    AND ri.REPORT_SPECIES_ID = ris.REPORT_SPECIES_ID
    AND ri.AS_OF_TIMESTAMP = ris.AS_OF_TIMESTAMP
    AND ri.REPROCESS_IN_PROGRESS = ris.REPROCESS_IN_PROGRESS
LEFT JOIN SECTION sec
    ON ris.DOMAIN_ID = sec.DOMAIN_ID
    AND ris.REPORT_SPECIES_ID = sec.REPORT_SPECIES_ID
    AND ris.SEGMENT_NUMBER = sec.SECTION_ID
WHERE ri.REPORT_SPECIES_ID = %s
    AND ri.AS_OF_TIMESTAMP >= %s"""

    # Add end year filter if provided
    if end_year:
        query += "\n    AND ri.AS_OF_TIMESTAMP < %s"

    query += """
GROUP BY
    ri.REPORT_SPECIES_ID,
    ri.AS_OF_TIMESTAMP,
    rfi.RPT_FILE_ID,
    rf.FILENAME
ORDER BY ri.AS_OF_TIMESTAMP ASC
"""

    return query


def execute_query(cursor, report_species_id, start_year, end_year=None):
    """
    Execute SQL query for a specific report species with year filtering.

    Args:
        cursor: Database cursor
        report_species_id: Report_Species_Id to query
        start_year: Start year for filtering
        end_year: Optional end year for filtering

    Returns:
        list: List of dictionaries containing query results, or empty list if no results
    """
    try:
        sql = get_sql_query(start_year, end_year)
        logging.debug(f'Executing query for REPORT_SPECIES_ID: {report_species_id}, years: {start_year}-{end_year or "present"}')

        # Build parameters: report_species_id, start_date, and optionally end_date
        start_date = f'{start_year}-01-01 00:00:00'
        params = [report_species_id, start_date]

        if end_year:
            end_date = f'{end_year + 1}-01-01 00:00:00'  # Exclusive end (next year)
            params.append(end_date)

        cursor.execute(sql, tuple(params))

        # Get column names from cursor
        columns = [column[0] for column in cursor.description]

        # Fetch all rows
        rows = cursor.fetchall()

        # Convert to list of dicts
        results = []
        for row in rows:
            results.append(dict(zip(columns, row)))

        logging.debug(f'Query returned {len(results)} rows')
        return results

    except Exception as e:
        logging.error(f'Query failed for REPORT_SPECIES_ID {report_species_id}: {e}')
        raise


# ============================================================================
# CSV Output
# ============================================================================

def calculate_year(row, year_from_filename):
    """
    Calculate the YEAR value based on the specified mode.

    Args:
        row: Dictionary containing row data
        year_from_filename: If True, extract from filename; if False, from AS_OF_TIMESTAMP

    Returns:
        str: Year value (e.g., "2024")
    """
    if year_from_filename:
        # Extract first 2 characters from filename and concatenate with "20"
        filename = row.get('FILENAME', '')
        if filename and len(filename) >= 2:
            try:
                year_prefix = filename[:2]
                return f'20{year_prefix}'
            except:
                logging.warning(f'Failed to extract year from filename: {filename}')
                return ''
        return ''
    else:
        # Extract year from AS_OF_TIMESTAMP
        timestamp = row.get('AS_OF_TIMESTAMP', '')
        if timestamp:
            try:
                if isinstance(timestamp, datetime):
                    return str(timestamp.year)
                else:
                    # Parse string timestamp
                    dt = datetime.strptime(str(timestamp)[:10], '%Y-%m-%d')
                    return str(dt.year)
            except:
                logging.warning(f'Failed to extract year from AS_OF_TIMESTAMP: {timestamp}')
                return ''
        return ''


def convert_julian_date(filename):
    """
    Convert julian date from filename to regular date format.

    Filename format: YYDDDXXX where YY=year, DDD=day of year
    Example: "24013001" -> "2024-01-13"

    Args:
        filename: Filename containing julian date (e.g., "24013001")

    Returns:
        str: Date in YYYY-MM-DD format, or empty string on error
    """
    if not filename or len(filename) < 5:
        return ''

    try:
        # Extract YY (first 2 chars) and DDD (next 3 chars)
        year_prefix = filename[:2]
        day_of_year = filename[2:5]

        # Convert to full year
        year = int(f'20{year_prefix}')
        day = int(day_of_year)

        # Create date from year and day of year
        date_obj = datetime(year, 1, 1) + timedelta(days=day - 1)
        return date_obj.strftime('%Y-%m-%d')
    except (ValueError, IndexError) as e:
        logging.warning(f'Failed to convert julian date from filename: {filename}, error: {e}')
        return ''


def convert_to_utc(timestamp, source_timezone):
    """
    Convert timestamp from source timezone to UTC.

    Args:
        timestamp: Timestamp value (datetime object or string)
        source_timezone: Timezone name (e.g., 'Asia/Singapore')

    Returns:
        str: UTC timestamp in ISO format (YYYY-MM-DD HH:MM:SS) or empty string on error
    """
    if not timestamp:
        return ''

    try:
        # Get timezone objects
        source_tz = pytz.timezone(source_timezone)
        utc_tz = pytz.UTC

        # Handle datetime object
        if isinstance(timestamp, datetime):
            # If timestamp is naive, localize it to source timezone
            if timestamp.tzinfo is None:
                localized = source_tz.localize(timestamp)
            else:
                localized = timestamp
            # Convert to UTC
            utc_time = localized.astimezone(utc_tz)
            return utc_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            # Parse string timestamp (assume format: YYYY-MM-DD HH:MM:SS.mmm or YYYY-MM-DD HH:MM:SS)
            timestamp_str = str(timestamp)
            # Try parsing with milliseconds first
            try:
                dt = datetime.strptime(timestamp_str[:23], '%Y-%m-%d %H:%M:%S.%f')
            except:
                dt = datetime.strptime(timestamp_str[:19], '%Y-%m-%d %H:%M:%S')

            # Localize to source timezone
            localized = source_tz.localize(dt)
            # Convert to UTC
            utc_time = localized.astimezone(utc_tz)
            return utc_time.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        logging.warning(f'Failed to convert timestamp to UTC: {timestamp}, error: {e}')
        return ''


# Cache for RPT segment lookups (avoids re-reading same RPT file for multiple instances)
_rpt_segments_cache = {}


def get_rpt_segments(rptfolder, filename):
    """
    Extract SECTIONHDR segments from an RPT file.

    Looks up the RPT file in the rptfolder by FILENAME (as stored in RPTFILE table).
    Returns formatted segments string: section_id#start_page#page_count|...
    Results are cached per filename to avoid re-reading the same RPT file.

    Args:
        rptfolder: Directory containing RPT files
        filename: RPT filename from RPTFILE table (e.g., "260271NL.RPT")

    Returns:
        str: Formatted segments string, or empty string if file not found or has no sections
    """
    if not rptfolder or not filename:
        return ''

    # The FILENAME from RPTFILE may or may not have .RPT extension
    rpt_filename = filename.strip()
    if not rpt_filename.upper().endswith('.RPT'):
        rpt_filename = rpt_filename + '.RPT'

    # Check cache first
    cache_key = rpt_filename.upper()
    if cache_key in _rpt_segments_cache:
        return _rpt_segments_cache[cache_key]

    rpt_path = os.path.join(rptfolder, rpt_filename)

    if not os.path.exists(rpt_path):
        logging.debug(f'RPT file not found: {rpt_path}')
        _rpt_segments_cache[cache_key] = ''
        return ''

    try:
        header, sections = read_sectionhdr(rpt_path)
        if header is None or not sections:
            result = ''
        else:
            result = format_segments(sections)
        _rpt_segments_cache[cache_key] = result
        return result
    except Exception as e:
        logging.warning(f'Failed to read SECTIONHDR from {rpt_path}: {e}')
        _rpt_segments_cache[cache_key] = ''
        return ''


def write_output_csv(output_path, results, report_species_name, country, year_from_filename, source_timezone, rptfolder=None):
    """
    Write query results to CSV file with simplified column set.

    Args:
        output_path: Path to output CSV file
        results: List of dictionaries containing query results
        report_species_name: Report_Species_Name from Report_Species.csv
        country: COUNTRY from Report_Species.csv
        year_from_filename: If True, calculate YEAR from filename; else from AS_OF_TIMESTAMP
        source_timezone: Timezone of AS_OF_TIMESTAMP for UTC conversion
        rptfolder: Optional directory containing RPT files for SECTIONHDR extraction
    """
    # Define output header - only essential columns
    output_header = [
        'REPORT_SPECIES_NAME',
        'FILENAME',
        'COUNTRY',
        'YEAR',
        'REPORT_DATE',
        'AS_OF_TIMESTAMP',
        'UTC',
        'SEGMENTS',
        'REPORT_FILE_ID'
    ]

    try:
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(output_header)

            for row in results:
                # Calculate YEAR value
                year = calculate_year(row, year_from_filename)

                # Convert AS_OF_TIMESTAMP to UTC
                utc_timestamp = convert_to_utc(row.get('AS_OF_TIMESTAMP'), source_timezone)

                # Get filename and remove .rpt/.RPT extension (case-insensitive)
                filename = row.get('FILENAME', '')
                if filename.upper().endswith('.RPT'):
                    filename = filename[:-4]
               # if filename and not filename.startswith('\\'):
               #     filename = '\\' + filename

                # Convert julian date from filename to REPORT_DATE
                report_date = convert_julian_date(row.get('FILENAME', ''))

                # Determine SEGMENTS value
                if rptfolder:
                    # Extract SECTIONHDR from RPT file (format: section_id#start_page#page_count|...)
                    segments = get_rpt_segments(rptfolder, row.get('FILENAME', ''))
                else:
                    # Use database STRING_AGG result (format: section_name#segment_number#start_page#pages|...)
                    segments = row.get('segments', '')

                # Map database columns to simplified output format
                output_row = [
                    report_species_name,  # From Report_Species.csv
                    filename,  # With leading backslash
                    country,  # From Report_Species.csv
                    year,  # Calculated YEAR column
                    report_date,  # REPORT_DATE from julian date
                    row.get('AS_OF_TIMESTAMP', ''),
                    utc_timestamp,  # UTC converted timestamp
                    segments,  # SEGMENTS column (RPT-based or DB-based)
                    row.get('RPT_FILE_ID', '')  # REPORT_FILE_ID
                ]
                writer.writerow(output_row)

        logging.debug(f'Wrote {len(results)} rows to {output_path}')

    except Exception as e:
        logging.error(f'Failed to write CSV file {output_path}: {e}')
        raise


# ============================================================================
# Main Processing Loop
# ============================================================================

def process_reports(conn, report_species_list, csv_path, output_dir, last_processed_id,
                    start_year, end_year, year_from_filename, source_timezone, quiet=False,
                    rptfolder=None):
    """
    Main processing loop for extracting report instances.

    Args:
        conn: Database connection
        report_species_list: List of report species from CSV
        csv_path: Path to Report_Species.csv
        output_dir: Output directory for CSV files
        last_processed_id: Last processed Report_Species_Id
        start_year: Start year for filtering
        end_year: Optional end year for filtering
        year_from_filename: If True, calculate YEAR from filename; else from AS_OF_TIMESTAMP
        source_timezone: Timezone of AS_OF_TIMESTAMP for UTC conversion
        quiet: If True, show single-line progress counter instead of detailed logs
        rptfolder: Optional directory containing RPT files for SECTIONHDR extraction

    Returns:
        dict: Statistics about processing
    """
    cursor = conn.cursor()
    progress_file = os.path.join(output_dir, 'progress.txt')

    # Statistics
    stats = {
        'total_reports': 0,
        'reports_with_instances': 0,
        'reports_without_instances': 0,
        'errors': 0
    }

    # Filter reports to process (those after last_processed_id)
    reports_to_process = [
        r for r in report_species_list
        if int(r['REPORT_SPECIES_ID']) > last_processed_id
    ]

    total_count = len(reports_to_process)
    year_range = f'{start_year}-{end_year}' if end_year else f'{start_year}+'

    if not quiet:
        logging.info(f'Processing {total_count} report species (starting after ID {last_processed_id})')
        logging.info(f'Year filter: {year_range}, YEAR column from: {"filename" if year_from_filename else "AS_OF_TIMESTAMP"}')
        logging.info(f'Timezone: {source_timezone} (converting to UTC)')
        if rptfolder:
            logging.info(f'SEGMENTS source: RPT file SECTIONHDR from {rptfolder}')
        else:
            logging.info(f'SEGMENTS source: database REPORT_INSTANCE_SEGMENT table')
    else:
        rpt_info = f' | RPT folder: {rptfolder}' if rptfolder else ''
        print(f'Processing {total_count} report species | Year filter: {year_range} | Timezone: {source_timezone}{rpt_info}')

    for idx, report in enumerate(reports_to_process, 1):
        report_species_id = int(report['REPORT_SPECIES_ID'])
        report_name = report['REPORT_SPECIES_NAME']
        country = report.get('COUNTRY_CODE', '')  # Get COUNTRY_Code from CSV

        if not quiet:
            logging.info(f'Processing REPORT_SPECIES_ID: {report_species_id}, Name: {report_name} ({idx}/{total_count})')

        try:
            # Execute query with year filtering
            results = execute_query(cursor, report_species_id, start_year, end_year)

            if results:
                # Write CSV file with REPORT_SPECIES_NAME, COUNTRY, and YEAR columns
                # Add year suffix to output filename
                if end_year:
                    output_filename = f'{report_name}_{start_year}_{end_year}.csv'
                else:
                    output_filename = f'{report_name}_{start_year}.csv'
                output_path = os.path.join(output_dir, output_filename)
                write_output_csv(output_path, results, report_name, country, year_from_filename, source_timezone, rptfolder=rptfolder)

                if not quiet:
                    logging.info(f'Query returned {len(results)} instances for {report_name}')
                    logging.info(f'Wrote {len(results)} rows to {output_filename}')

                stats['reports_with_instances'] += 1
            else:
                # No results - update IN_USE=0
                if not quiet:
                    logging.warning(f'Query returned 0 instances for {report_name} (year range: {year_range}), updating IN_USE=0')

                update_in_use(csv_path, report_species_id, new_in_use_value=0)
                stats['reports_without_instances'] += 1

            # Update progress
            write_progress(progress_file, report_species_id)
            stats['total_reports'] += 1

            # Update progress counter in quiet mode (after processing, not before)
            if quiet:
                # Single-line progress counter (updates in place)
                progress_msg = f'\rProgress: {idx}/{total_count} reports processed | {stats["reports_with_instances"]} exported | {stats["reports_without_instances"]} skipped'
                sys.stdout.write(progress_msg)
                sys.stdout.flush()

        except Exception as e:
            # Always log errors to file
            logging.error(f'Error processing REPORT_SPECIES_ID {report_species_id}: {e}')
            stats['errors'] += 1
            # Continue with next report
            continue

    cursor.close()
    return stats


# ============================================================================
# Main Function
# ============================================================================

def main():
    """Main entry point."""
    # Parse arguments
    args = parse_arguments()

    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)

    # Setup logging (quiet mode suppresses console output)
    setup_logging(args.output_dir, quiet=args.quiet)

    if not args.quiet:
        logging.info('========================================')
        logging.info('Extract_Instances.py - Starting')
        logging.info('========================================')

    try:
        # Load Report_Species.csv
        report_species_list = load_report_species(args.input)

        # Read progress
        progress_file = os.path.join(args.output_dir, 'progress.txt')
        last_processed_id = read_progress(progress_file)

        # Connect to database
        conn = create_connection(
            server=args.server,
            port=args.port,
            database=args.database,
            user=args.user,
            password=args.password,
            windows_auth=args.windows_auth
        )

        # Process reports
        stats = process_reports(
            conn=conn,
            report_species_list=report_species_list,
            csv_path=args.input,
            output_dir=args.output_dir,
            last_processed_id=last_processed_id,
            start_year=args.start_year,
            end_year=args.end_year,
            year_from_filename=args.year_from_filename,
            source_timezone=args.timezone,
            quiet=args.quiet,
            rptfolder=args.rptfolder
        )

        # Close connection
        conn.close()
        if not args.quiet:
            logging.info('Database connection closed')

        # Print summary
        if args.quiet:
            # Clean summary for quiet mode
            print(f'\n\nCompleted: {stats["total_reports"]} reports processed | {stats["reports_with_instances"]} exported | {stats["reports_without_instances"]} skipped | {stats["errors"]} errors')
        else:
            logging.info('========================================')
            logging.info('PROCESSING COMPLETE')
            logging.info(f'Total reports processed: {stats["total_reports"]}')
            logging.info(f'Reports with instances: {stats["reports_with_instances"]}')
            logging.info(f'Reports with no instances (IN_USE set to 0): {stats["reports_without_instances"]}')
            logging.info(f'Errors encountered: {stats["errors"]}')
            logging.info('========================================')

        # Exit with appropriate code
        sys.exit(0 if stats['errors'] == 0 else 1)

    except KeyboardInterrupt:
        if not args.quiet:
            logging.info('Process interrupted by user (Ctrl+C)')
        else:
            print('\n\nProcess interrupted by user (Ctrl+C)')
        sys.exit(130)

    except Exception as e:
        logging.error(f'Fatal error: {e}')
        if args.quiet:
            print(f'\n\nFatal error: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
