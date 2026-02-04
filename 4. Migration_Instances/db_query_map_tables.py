#!/usr/bin/env python3
"""
db_query_map_tables.py - Query IntelliSTOR Database Schema for MAP File Analysis

Queries the database to understand table structures and relationships needed
for correlating binary MAP files with section names.

Key tables:
- MAPFILE: MAP file registry
- SST_STORAGE: Links MAP files to report instances
- SECTION: Section names
- REPORT_INSTANCE: Report instances
- REPORT_INSTANCE_SEGMENT: Segment information

Usage:
    python db_query_map_tables.py
    python db_query_map_tables.py --server localhost --database iSTSGUAT --user sa --password Fvrpgr40
"""

import argparse
import os
import sys

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
        description='Query IntelliSTOR database schema for MAP file analysis',
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

    return parser.parse_args()


def connect_to_database(server, port, database, user, password):
    """Connect to SQL Server database."""
    print(f"Connecting to {server}:{port}, database: {database}, user: {user}")

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


def query_table_schema(cursor, table_name):
    """Query and display schema for a specific table."""
    print(f"\n{'='*60}")
    print(f"Table: {table_name}")
    print('='*60)

    # Check if table exists
    cursor.execute("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_NAME = %s
    """, (table_name,))

    if cursor.fetchone()[0] == 0:
        print(f"  Table '{table_name}' does not exist in database")
        return False

    # Get column information
    cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = %s
        ORDER BY ORDINAL_POSITION
    """, (table_name,))

    columns = cursor.fetchall()

    print(f"\nColumns ({len(columns)}):")
    print(f"  {'Column Name':<30} {'Data Type':<15} {'Max Length':<12} {'Nullable'}")
    print(f"  {'-'*30} {'-'*15} {'-'*12} {'-'*8}")

    for col in columns:
        col_name, data_type, max_len, nullable = col
        max_len_str = str(max_len) if max_len else '-'
        print(f"  {col_name:<30} {data_type:<15} {max_len_str:<12} {nullable}")

    # Get row count
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    row_count = cursor.fetchone()[0]
    print(f"\nTotal rows: {row_count:,}")

    return True


def query_sample_data(cursor, table_name, limit=5):
    """Query and display sample data from a table."""
    print(f"\nSample data (first {limit} rows):")

    try:
        cursor.execute(f"SELECT TOP {limit} * FROM {table_name}")
        rows = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]

        if not rows:
            print("  (no data)")
            return

        # Print column headers
        header = " | ".join(f"{col[:20]:<20}" for col in columns[:6])
        print(f"  {header}")
        print(f"  {'-'*len(header)}")

        # Print rows
        for row in rows:
            row_str = " | ".join(f"{str(val)[:20]:<20}" for val in row[:6])
            print(f"  {row_str}")

        if len(columns) > 6:
            print(f"  ... ({len(columns) - 6} more columns)")

    except Exception as e:
        print(f"  Error querying data: {e}")


def query_mapfile_to_section_relationship(cursor):
    """Query to understand the relationship between MAPFILE and SECTION."""
    print(f"\n{'='*60}")
    print("Relationship Analysis: MAPFILE → SST_STORAGE → SECTION")
    print('='*60)

    # Query a sample joining MAPFILE to SST_STORAGE
    print("\n1. MAPFILE → SST_STORAGE link (sample):")
    try:
        cursor.execute("""
            SELECT TOP 10
                m.MAP_FILE_ID,
                m.FILENAME,
                s.DOMAIN_ID,
                s.REPORT_SPECIES_ID,
                s.AS_OF_TIMESTAMP
            FROM MAPFILE m
            INNER JOIN SST_STORAGE s ON m.MAP_FILE_ID = s.MAP_FILE_ID
            ORDER BY m.MAP_FILE_ID
        """)
        rows = cursor.fetchall()

        if rows:
            print(f"  {'MAP_FILE_ID':<12} {'FILENAME':<20} {'DOMAIN_ID':<10} {'SPECIES_ID':<12} {'AS_OF_TIMESTAMP'}")
            print(f"  {'-'*12} {'-'*20} {'-'*10} {'-'*12} {'-'*20}")
            for row in rows:
                print(f"  {row[0]:<12} {str(row[1])[:20]:<20} {row[2]:<10} {row[3]:<12} {row[4]}")
        else:
            print("  (no data - tables may not be linked)")
    except Exception as e:
        print(f"  Error: {e}")

    # Query SECTION for a specific DOMAIN_ID and REPORT_SPECIES_ID
    print("\n2. SECTION entries for first DOMAIN_ID/REPORT_SPECIES_ID pair:")
    try:
        cursor.execute("""
            SELECT TOP 1 DOMAIN_ID, REPORT_SPECIES_ID
            FROM SST_STORAGE
        """)
        row = cursor.fetchone()

        if row:
            domain_id, species_id = row
            print(f"  Using DOMAIN_ID={domain_id}, REPORT_SPECIES_ID={species_id}")

            cursor.execute("""
                SELECT SECTION_ID, NAME, TIME_STAMP
                FROM SECTION
                WHERE DOMAIN_ID = %s AND REPORT_SPECIES_ID = %s
                ORDER BY SECTION_ID
            """, (domain_id, species_id))

            sections = cursor.fetchall()
            print(f"\n  Found {len(sections)} sections:")
            print(f"  {'SECTION_ID':<12} {'NAME':<40} {'TIME_STAMP'}")
            print(f"  {'-'*12} {'-'*40} {'-'*20}")
            for sec in sections[:20]:
                print(f"  {sec[0]:<12} {str(sec[1]).strip():<40} {sec[2]}")
            if len(sections) > 20:
                print(f"  ... ({len(sections) - 20} more sections)")
    except Exception as e:
        print(f"  Error: {e}")


def query_report_instance_segment_analysis(cursor):
    """Analyze REPORT_INSTANCE_SEGMENT to understand SEGMENT_NUMBER."""
    print(f"\n{'='*60}")
    print("Analysis: REPORT_INSTANCE_SEGMENT")
    print('='*60)

    # Check SEGMENT_NUMBER range and distribution
    print("\n1. SEGMENT_NUMBER statistics:")
    try:
        cursor.execute("""
            SELECT
                MIN(SEGMENT_NUMBER) as min_seg,
                MAX(SEGMENT_NUMBER) as max_seg,
                COUNT(*) as total_rows,
                COUNT(DISTINCT SEGMENT_NUMBER) as distinct_values
            FROM REPORT_INSTANCE_SEGMENT
        """)
        row = cursor.fetchone()
        if row:
            print(f"  Min SEGMENT_NUMBER: {row[0]}")
            print(f"  Max SEGMENT_NUMBER: {row[1]}")
            print(f"  Total rows: {row[2]:,}")
            print(f"  Distinct values: {row[3]:,}")
    except Exception as e:
        print(f"  Error: {e}")

    # Sample of SEGMENT_NUMBER distribution per instance
    print("\n2. Sample: SEGMENT_NUMBER per report instance:")
    try:
        cursor.execute("""
            SELECT TOP 5
                DOMAIN_ID,
                REPORT_SPECIES_ID,
                AS_OF_TIMESTAMP,
                COUNT(*) as segment_count,
                MIN(SEGMENT_NUMBER) as min_seg,
                MAX(SEGMENT_NUMBER) as max_seg
            FROM REPORT_INSTANCE_SEGMENT
            GROUP BY DOMAIN_ID, REPORT_SPECIES_ID, AS_OF_TIMESTAMP
            ORDER BY COUNT(*) DESC
        """)
        rows = cursor.fetchall()

        if rows:
            print(f"  {'DOMAIN_ID':<10} {'SPECIES_ID':<12} {'SEG_COUNT':<10} {'MIN_SEG':<8} {'MAX_SEG'}")
            print(f"  {'-'*10} {'-'*12} {'-'*10} {'-'*8} {'-'*8}")
            for row in rows:
                print(f"  {row[0]:<10} {row[1]:<12} {row[3]:<10} {row[4]:<8} {row[5]}")
    except Exception as e:
        print(f"  Error: {e}")


def main():
    args = parse_arguments()

    if not args.password:
        print("Error: Password required. Use --password or set SQLPassword environment variable.")
        sys.exit(1)

    conn = connect_to_database(
        args.server, args.port, args.database, args.user, args.password
    )

    cursor = conn.cursor()

    # Key tables to analyze
    tables = [
        'MAPFILE',
        'SST_STORAGE',
        'SECTION',
        'REPORT_INSTANCE',
        'REPORT_INSTANCE_SEGMENT'
    ]

    print("\n" + "="*60)
    print("DATABASE SCHEMA ANALYSIS FOR MAP FILE CORRELATION")
    print("="*60)

    # Query schema for each table
    for table in tables:
        if query_table_schema(cursor, table):
            query_sample_data(cursor, table)

    # Analyze relationships
    query_mapfile_to_section_relationship(cursor)
    query_report_instance_segment_analysis(cursor)

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print("""
Key findings to verify:
1. MAPFILE.FILENAME contains the .MAP filename
2. SST_STORAGE links MAP_FILE_ID to DOMAIN_ID + REPORT_SPECIES_ID
3. SECTION table has NAME indexed by DOMAIN_ID + REPORT_SPECIES_ID + SECTION_ID
4. SEGMENT_NUMBER in REPORT_INSTANCE_SEGMENT is a sequential counter (1,2,3...)
5. The SECTION_ID must be extracted from the binary .MAP file

Next step: Run db_export_map_data.py to export these tables to CSV
""")

    cursor.close()
    conn.close()
    print("Database connection closed.")


if __name__ == '__main__':
    main()
