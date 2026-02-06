#!/usr/bin/env python3
"""
db_export_map_data.py - Export IntelliSTOR Database Tables for MAP File Analysis

Exports database tables to CSV files for offline analysis of MAP file to section
name relationships.

Output files:
- mapfile.csv - MAP file registry
- sst_storage.csv - Links MAP files to report instances
- section.csv - Section names
- report_instance_segment.csv - Segment information (sample, as full table is large)
- map_to_sections.csv - Complete JOIN for direct lookups

Usage:
    python db_export_map_data.py
    python db_export_map_data.py --output-dir ./exports
"""

import argparse
import csv
import os
import sys
from datetime import datetime

try:
    import pymssql
except ImportError:
    print("Error: pymssql not installed. Run: pip install pymssql")
    sys.exit(1)


def get_env_or_default(env_var, default):
    """Get environment variable or return default."""
    return os.environ.get(env_var, default)


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Export IntelliSTOR database tables for MAP file analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--server', default=get_env_or_default('SQLServer', 'localhost'),
                        help='SQL Server hostname (default: localhost)')
    parser.add_argument('--port', type=int, default=1433,
                        help='SQL Server port (default: 1433)')
    parser.add_argument('--database', default=get_env_or_default('SQL_SG_Database', 'iSTSGUAT'),
                        help='Database name (default: iSTSGUAT)')
    parser.add_argument('--user', default=get_env_or_default('SQLUser', 'sa'),
                        help='SQL Server username (default: sa)')
    parser.add_argument('--password', default=get_env_or_default('SQLPassword', ''),
                        help='SQL Server password')
    parser.add_argument('--output-dir', '-o', default='./exports',
                        help='Output directory for CSV files (default: ./exports)')

    return parser.parse_args()


def connect_to_database(server, port, database, user, password):
    """Connect to SQL Server database."""
    print(f"Connecting to {server}:{port}, database: {database}")

    try:
        conn = pymssql.connect(
            server=server,
            port=port,
            database=database,
            user=user,
            password=password
        )
        print("Connection successful!")
        return conn
    except Exception as e:
        print(f"Connection failed: {e}")
        sys.exit(1)


def export_table_to_csv(cursor, query, output_path, description, limit=None):
    """Export query results to CSV file."""
    print(f"\nExporting: {description}")
    print(f"  Output: {output_path}")

    start_time = datetime.now()

    try:
        cursor.execute(query)
        columns = [desc[0] for desc in cursor.description]

        row_count = 0
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(columns)

            while True:
                rows = cursor.fetchmany(10000)
                if not rows:
                    break

                for row in rows:
                    # Clean up values (strip strings, handle None)
                    cleaned_row = []
                    for val in row:
                        if isinstance(val, str):
                            cleaned_row.append(val.strip())
                        elif val is None:
                            cleaned_row.append('')
                        else:
                            cleaned_row.append(val)
                    writer.writerow(cleaned_row)
                    row_count += 1

                if row_count % 100000 == 0:
                    print(f"    Exported {row_count:,} rows...")

                if limit and row_count >= limit:
                    print(f"    Reached limit of {limit:,} rows")
                    break

        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"  Exported {row_count:,} rows in {elapsed:.1f}s")
        return row_count

    except Exception as e:
        print(f"  Error: {e}")
        return 0


def main():
    args = parse_arguments()

    if not args.password:
        print("Error: Password required. Use --password or set SQLPassword environment variable.")
        sys.exit(1)

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    print(f"Output directory: {args.output_dir}")

    conn = connect_to_database(
        args.server, args.port, args.database, args.user, args.password
    )

    cursor = conn.cursor()

    print("\n" + "="*60)
    print("EXPORTING DATABASE TABLES FOR MAP FILE ANALYSIS")
    print("="*60)

    total_start = datetime.now()
    stats = {}

    # 1. Export MAPFILE table
    stats['mapfile'] = export_table_to_csv(
        cursor,
        "SELECT MAP_FILE_ID, LOCATION_ID, FILENAME, STORED_ON_SIDE FROM MAPFILE ORDER BY MAP_FILE_ID",
        os.path.join(args.output_dir, 'mapfile.csv'),
        "MAPFILE (MAP file registry)"
    )

    # 2. Export SST_STORAGE table
    stats['sst_storage'] = export_table_to_csv(
        cursor,
        "SELECT MAP_FILE_ID, DOMAIN_ID, REPORT_SPECIES_ID, AS_OF_TIMESTAMP, REPROCESS_IN_PROGRESS FROM SST_STORAGE ORDER BY MAP_FILE_ID",
        os.path.join(args.output_dir, 'sst_storage.csv'),
        "SST_STORAGE (MAP file to instance links)"
    )

    # 3. Export SECTION table
    stats['section'] = export_table_to_csv(
        cursor,
        "SELECT DOMAIN_ID, REPORT_SPECIES_ID, SECTION_ID, NAME, TIME_STAMP FROM SECTION ORDER BY DOMAIN_ID, REPORT_SPECIES_ID, SECTION_ID",
        os.path.join(args.output_dir, 'section.csv'),
        "SECTION (Section names)"
    )

    # 4. Export REPORT_INSTANCE_SEGMENT (sample - full table is 10M+ rows)
    stats['report_instance_segment'] = export_table_to_csv(
        cursor,
        """SELECT TOP 500000
            DOMAIN_ID, REPORT_SPECIES_ID, AS_OF_TIMESTAMP, SEGMENT_NUMBER,
            START_PAGE_NUMBER, NUMBER_OF_PAGES
           FROM REPORT_INSTANCE_SEGMENT
           ORDER BY DOMAIN_ID, REPORT_SPECIES_ID, AS_OF_TIMESTAMP, SEGMENT_NUMBER""",
        os.path.join(args.output_dir, 'report_instance_segment.csv'),
        "REPORT_INSTANCE_SEGMENT (sample: 500K rows)"
    )

    # 5. Create map_to_sections.csv - JOIN of MAPFILE -> SST_STORAGE -> SECTION info
    # This provides DOMAIN_ID and REPORT_SPECIES_ID for each MAP filename
    stats['map_to_domain'] = export_table_to_csv(
        cursor,
        """SELECT
            m.MAP_FILE_ID,
            m.FILENAME,
            s.DOMAIN_ID,
            s.REPORT_SPECIES_ID
           FROM MAPFILE m
           INNER JOIN SST_STORAGE s ON m.MAP_FILE_ID = s.MAP_FILE_ID
           ORDER BY m.MAP_FILE_ID""",
        os.path.join(args.output_dir, 'map_to_domain.csv'),
        "MAP filename to DOMAIN_ID/REPORT_SPECIES_ID mapping"
    )

    # 6. Export unique SECTION entries indexed by DOMAIN_ID, REPORT_SPECIES_ID
    # This allows lookup of section names by SECTION_ID once we extract it from binary
    stats['section_lookup'] = export_table_to_csv(
        cursor,
        """SELECT DISTINCT
            DOMAIN_ID,
            REPORT_SPECIES_ID,
            SECTION_ID,
            NAME
           FROM SECTION
           ORDER BY DOMAIN_ID, REPORT_SPECIES_ID, SECTION_ID""",
        os.path.join(args.output_dir, 'section_lookup.csv'),
        "SECTION lookup table (DOMAIN + SPECIES + SECTION_ID -> NAME)"
    )

    # 7. Find a sample MAP file we can use for testing
    print("\n" + "-"*60)
    print("Finding sample MAP files for testing...")

    cursor.execute("""
        SELECT TOP 10
            m.FILENAME,
            s.DOMAIN_ID,
            s.REPORT_SPECIES_ID,
            COUNT(sec.SECTION_ID) as section_count
        FROM MAPFILE m
        INNER JOIN SST_STORAGE s ON m.MAP_FILE_ID = s.MAP_FILE_ID
        LEFT JOIN SECTION sec ON s.DOMAIN_ID = sec.DOMAIN_ID
            AND s.REPORT_SPECIES_ID = sec.REPORT_SPECIES_ID
        GROUP BY m.FILENAME, s.DOMAIN_ID, s.REPORT_SPECIES_ID
        HAVING COUNT(sec.SECTION_ID) > 0
        ORDER BY COUNT(sec.SECTION_ID) DESC
    """)

    rows = cursor.fetchall()
    if rows:
        print("\nSample MAP files with sections defined:")
        print(f"  {'FILENAME':<20} {'DOMAIN_ID':<10} {'SPECIES_ID':<12} {'SECTIONS'}")
        print(f"  {'-'*20} {'-'*10} {'-'*12} {'-'*10}")
        for row in rows:
            print(f"  {row[0]:<20} {row[1]:<10} {row[2]:<12} {row[3]}")

        # Save test samples
        test_samples_path = os.path.join(args.output_dir, 'test_samples.csv')
        with open(test_samples_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['FILENAME', 'DOMAIN_ID', 'REPORT_SPECIES_ID', 'SECTION_COUNT'])
            writer.writerows(rows)
        print(f"\n  Saved to: {test_samples_path}")

    # Summary
    total_elapsed = (datetime.now() - total_start).total_seconds()

    print("\n" + "="*60)
    print("EXPORT COMPLETE")
    print("="*60)
    print(f"\nTotal time: {total_elapsed:.1f}s")
    print(f"\nFiles created in {args.output_dir}/:")
    for name, count in stats.items():
        print(f"  {name}.csv: {count:,} rows")

    print(f"""
Next steps:
1. Run verify_segment_hypothesis.py to decode binary MAP structure
2. Find where SECTION_ID is stored in the binary after **ME markers
3. Cross-reference with section_lookup.csv to verify section names
""")

    cursor.close()
    conn.close()
    print("Database connection closed.")


if __name__ == '__main__':
    main()
