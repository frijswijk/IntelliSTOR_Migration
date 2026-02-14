#!/usr/bin/env python3
"""
papyrus_export_indexed_fields.py - Export Indexed Field Definitions from MS SQL

Exports all indexed field definitions from the IntelliSTOR database to a CSV file.
For each report species, retrieves the indexed fields with their LINE_ID, FIELD_ID,
field name, type, column positions, and line template.

This is a standalone tool for running at customer sites to capture field metadata
before the MS SQL database is decommissioned.

Output CSV columns:
    REPORT_SPECIES_NAME, REPORT_SPECIES_DISPLAYNAME, REPORT_SPECIES_ID,
    STRUCTURE_DEF_ID, LINE_ID, FIELD_ID, FIELD_NAME, FIELD_TYPE,
    START_COLUMN, END_COLUMN, FIELD_WIDTH, IS_SIGNIFICANT, IS_INDEXED,
    LINE_NAME, LINE_TEMPLATE

Requirements:
    pip install pymssql

Usage:
    # SQL Server Authentication
    python papyrus_export_indexed_fields.py --server localhost --database IntelliSTOR --user sa --password MyPassword

    # Windows Authentication
    python papyrus_export_indexed_fields.py --server localhost --database IntelliSTOR --windows-auth

    # Custom output directory
    python papyrus_export_indexed_fields.py --server localhost --database IntelliSTOR --user sa --password MyPassword --output-dir C:\\Output
"""

import pymssql
import csv
import argparse
import logging
import sys
import os
from pathlib import Path
from datetime import datetime


# ============================================================================
# SQL Query
# ============================================================================

INDEXED_FIELDS_QUERY = """
SELECT
    RTRIM(COALESCE(rsn1.NAME, rsn0.NAME)) AS REPORT_SPECIES_NAME,
    RTRIM(rsn0.NAME) AS REPORT_SPECIES_DISPLAYNAME,
    ri.REPORT_SPECIES_ID,
    f.STRUCTURE_DEF_ID,
    f.LINE_ID,
    f.FIELD_ID,
    RTRIM(f.NAME) AS FIELD_NAME,
    RTRIM(f.FIELD_TYPE_NAME) AS FIELD_TYPE,
    f.START_COLUMN,
    f.END_COLUMN,
    (f.END_COLUMN - f.START_COLUMN + 1) AS FIELD_WIDTH,
    f.IS_SIGNIFICANT,
    f.IS_INDEXED,
    RTRIM(l.NAME) AS LINE_NAME,
    RTRIM(l.TEMPLATE) AS LINE_TEMPLATE
FROM FIELD f
INNER JOIN (
    SELECT ri2.REPORT_SPECIES_ID, ri2.STRUCTURE_DEF_ID,
           ROW_NUMBER() OVER (PARTITION BY ri2.REPORT_SPECIES_ID ORDER BY ri2.AS_OF_TIMESTAMP DESC) AS rn
    FROM REPORT_INSTANCE ri2
) ri ON ri.STRUCTURE_DEF_ID = f.STRUCTURE_DEF_ID AND ri.rn = 1
INNER JOIN REPORT_SPECIES_NAME rsn0
    ON rsn0.REPORT_SPECIES_ID = ri.REPORT_SPECIES_ID AND rsn0.ITEM_ID = 0
LEFT JOIN REPORT_SPECIES_NAME rsn1
    ON rsn1.REPORT_SPECIES_ID = ri.REPORT_SPECIES_ID
    AND rsn1.DOMAIN_ID = rsn0.DOMAIN_ID AND rsn1.ITEM_ID = 1
LEFT JOIN LINE l ON l.STRUCTURE_DEF_ID = f.STRUCTURE_DEF_ID AND l.LINE_ID = f.LINE_ID
WHERE f.IS_INDEXED = 1
ORDER BY COALESCE(rsn1.NAME, rsn0.NAME), f.LINE_ID, f.FIELD_ID
"""

# CSV column headers
CSV_HEADERS = [
    'REPORT_SPECIES_NAME',
    'REPORT_SPECIES_DISPLAYNAME',
    'REPORT_SPECIES_ID',
    'STRUCTURE_DEF_ID',
    'LINE_ID',
    'FIELD_ID',
    'FIELD_NAME',
    'FIELD_TYPE',
    'START_COLUMN',
    'END_COLUMN',
    'FIELD_WIDTH',
    'IS_SIGNIFICANT',
    'IS_INDEXED',
    'LINE_NAME',
    'LINE_TEMPLATE',
]


# ============================================================================
# Database Operations
# ============================================================================

def connect_database(server, database, user=None, password=None, windows_auth=False, port=1433):
    """
    Connect to MS SQL Server.

    Args:
        server: SQL Server hostname or IP
        database: Database name
        user: Username (SQL auth)
        password: Password (SQL auth)
        windows_auth: Use Windows Authentication
        port: SQL Server port (default 1433)

    Returns:
        pymssql connection object
    """
    logging.info(f"Connecting to SQL Server: {server}:{port}, database: {database}")

    if windows_auth:
        conn = pymssql.connect(
            server=server,
            database=database,
            port=port,
            autocommit=True
        )
    else:
        conn = pymssql.connect(
            server=server,
            user=user,
            password=password,
            database=database,
            port=port,
            autocommit=True
        )

    logging.info("Database connection established successfully")
    return conn


def check_required_tables(cursor):
    """Check that all required tables exist."""
    required = ['FIELD', 'REPORT_INSTANCE', 'REPORT_SPECIES_NAME', 'LINE']
    missing = []
    for table in required:
        cursor.execute(
            "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = %s",
            (table,)
        )
        row = cursor.fetchone()
        if not row or row[0] == 0:
            missing.append(table)

    if missing:
        raise RuntimeError(f"Missing required tables: {', '.join(missing)}")

    logging.info(f"All required tables verified: {', '.join(required)}")


def export_indexed_fields(cursor, output_path, quiet=False):
    """
    Execute the indexed fields query and write results to CSV.

    Args:
        cursor: Database cursor
        output_path: Path to output CSV file
        quiet: Minimal console output

    Returns:
        Tuple of (row_count, species_count)
    """
    logging.info("Executing indexed fields query...")

    cursor.execute(INDEXED_FIELDS_QUERY)
    rows = cursor.fetchall()

    row_count = len(rows)
    species_set = set()

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADERS)

        for row in rows:
            # row is a tuple: (name, displayname, species_id, structure_def_id,
            #   line_id, field_id, field_name, field_type,
            #   start_col, end_col, field_width, is_significant, is_indexed,
            #   line_name, line_template)
            species_name = (row[0] or '').strip()
            species_set.add(species_name)

            writer.writerow([
                species_name,                          # REPORT_SPECIES_NAME
                (row[1] or '').strip(),                # REPORT_SPECIES_DISPLAYNAME
                row[2],                                 # REPORT_SPECIES_ID
                row[3],                                 # STRUCTURE_DEF_ID
                row[4],                                 # LINE_ID
                row[5],                                 # FIELD_ID
                (row[6] or '').strip(),                # FIELD_NAME
                (row[7] or '').strip(),                # FIELD_TYPE
                row[8],                                 # START_COLUMN
                row[9],                                 # END_COLUMN
                row[10],                                # FIELD_WIDTH
                row[11],                                # IS_SIGNIFICANT
                row[12],                                # IS_INDEXED
                (row[13] or '').strip(),               # LINE_NAME
                (row[14] or '').strip(),               # LINE_TEMPLATE
            ])

    species_count = len(species_set)
    logging.info(f"Exported {row_count} indexed fields across {species_count} species to {output_path}")

    if not quiet:
        print(f"Exported {row_count} indexed fields across {species_count} species")
        print(f"Output: {output_path}")

    return row_count, species_count


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Export indexed field definitions from IntelliSTOR MS SQL database to CSV',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # SQL Server Authentication
  python papyrus_export_indexed_fields.py --server localhost --database IntelliSTOR --user sa --password MyPassword

  # Windows Authentication
  python papyrus_export_indexed_fields.py --server localhost --database IntelliSTOR --windows-auth

  # Custom output directory
  python papyrus_export_indexed_fields.py --server localhost --database IntelliSTOR --user sa --password MyPassword -o C:\\Output

  # Quiet mode
  python papyrus_export_indexed_fields.py --server localhost --database IntelliSTOR --windows-auth --quiet
        """)

    parser.add_argument('--server', required=True, help='SQL Server host/IP address')
    parser.add_argument('--database', required=True, help='Database name')
    parser.add_argument('--port', type=int, default=1433, help='SQL Server port (default: 1433)')
    parser.add_argument('--user', help='Username for SQL Server authentication')
    parser.add_argument('--password', help='Password for SQL Server authentication')
    parser.add_argument('--windows-auth', action='store_true', help='Use Windows Authentication')
    parser.add_argument('--output-dir', '-o', default='.', help='Output directory (default: current)')
    parser.add_argument('--output-file', default='Indexed_Fields.csv', help='Output filename (default: Indexed_Fields.csv)')
    parser.add_argument('--quiet', action='store_true', help='Quiet mode (minimal console output)')

    args = parser.parse_args()

    # Validate authentication
    if not args.windows_auth and (not args.user or not args.password):
        print("ERROR: Either --windows-auth OR both --user and --password must be provided.",
              file=sys.stderr)
        sys.exit(1)

    # Setup logging
    log_level = logging.WARNING if args.quiet else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(levelname)s - %(message)s',
        stream=sys.stderr
    )

    # Also log to file
    os.makedirs(args.output_dir, exist_ok=True)
    log_path = os.path.join(args.output_dir, 'papyrus_export_indexed_fields.log')
    file_handler = logging.FileHandler(log_path, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(file_handler)

    output_path = os.path.join(args.output_dir, args.output_file)

    try:
        # Connect
        conn = connect_database(
            server=args.server,
            database=args.database,
            user=args.user,
            password=args.password,
            windows_auth=args.windows_auth,
            port=args.port
        )
        cursor = conn.cursor()

        # Verify tables
        check_required_tables(cursor)

        # Export
        start_time = datetime.now()
        row_count, species_count = export_indexed_fields(cursor, output_path, args.quiet)
        elapsed = (datetime.now() - start_time).total_seconds()

        if not args.quiet:
            print(f"Completed in {elapsed:.1f}s")

        logging.info(f"Export completed: {row_count} rows, {species_count} species, {elapsed:.1f}s")

        conn.close()
        logging.info("Database connection closed")

    except pymssql.Error as e:
        logging.error(f"Database error: {e}")
        print(f"ERROR: Database error: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(3)


if __name__ == '__main__':
    main()
