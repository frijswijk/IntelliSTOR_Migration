#!/usr/bin/env python3
"""
test_connection.py - SQL Server Connection Test Utility

Simple script to test SQL Server connectivity before running Extract_Instances.py.
This helps verify that pymssql is installed correctly and connection parameters are valid.
"""

import sys
import argparse


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Test SQL Server connection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Windows Authentication
  python test_connection.py --server localhost --database IntelliSTOR --windows-auth

  # SQL Server Authentication
  python test_connection.py --server localhost --database IntelliSTOR --user sa --password MyPassword
        """
    )

    parser.add_argument('--server', required=True, help='SQL Server host/IP address')
    parser.add_argument('--port', type=int, default=1433, help='SQL Server port (default: 1433)')
    parser.add_argument('--database', required=True, help='Database name')
    parser.add_argument('--user', help='Username for SQL Server authentication')
    parser.add_argument('--password', help='Password for SQL Server authentication')
    parser.add_argument('--windows-auth', action='store_true',
                        help='Use Windows Authentication')

    args = parser.parse_args()

    # Validate authentication parameters
    if not args.windows_auth and (not args.user or not args.password):
        parser.error('Either --windows-auth or both --user and --password must be provided')

    return args


def test_connection(server, port, database, user=None, password=None, windows_auth=False):
    """Test SQL Server connection."""

    print("=" * 60)
    print("SQL Server Connection Test")
    print("=" * 60)
    print()

    # Check if pymssql is installed
    print("[1/5] Checking if pymssql is installed...")
    try:
        import pymssql
        print("      ✓ pymssql is installed")
        print(f"      Version: {pymssql.__version__}")
    except ImportError:
        print("      ✗ ERROR: pymssql is not installed")
        print()
        print("To install pymssql, run:")
        print("  pip install pymssql")
        print()
        return False

    print()

    # Display connection info
    print("[2/5] Connection parameters:")
    print(f"      Server: {server}")
    print(f"      Port: {port}")
    print(f"      Database: {database}")
    if windows_auth:
        print(f"      Authentication: Windows Authentication")
    else:
        print(f"      Authentication: SQL Server Authentication")
        print(f"      User: {user}")
        print(f"      Password: {'*' * len(password)}")
    print()

    # Attempt connection
    print("[3/5] Attempting to connect to SQL Server...")
    try:
        if windows_auth:
            conn = pymssql.connect(
                server=server,
                port=port,
                database=database,
                trusted=True
            )
        else:
            conn = pymssql.connect(
                server=server,
                port=port,
                database=database,
                user=user,
                password=password
            )
        print("      ✓ Connection established successfully")
    except Exception as e:
        print(f"      ✗ Connection failed: {e}")
        print()
        print("Troubleshooting tips:")
        print("  - Verify the server name/IP is correct")
        print("  - Check that SQL Server is running")
        print("  - Verify the database name exists")
        print("  - Check username and password (if using SQL Server auth)")
        print("  - Ensure the user has permission to access the database")
        print("  - If connecting remotely, verify SQL Server accepts remote connections")
        print("  - Try using 'localhost' if on the same machine as SQL Server")
        print()
        return False

    print()

    # Test query execution
    print("[4/5] Testing query execution...")
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        version = cursor.fetchone()[0]
        print("      ✓ Query executed successfully")
        print()
        print("      SQL Server Version:")
        # Print first line of version string
        first_line = version.split('\n')[0].strip()
        print(f"      {first_line}")
        cursor.close()
    except Exception as e:
        print(f"      ✗ Query execution failed: {e}")
        conn.close()
        return False

    print()

    # Check for required tables
    print("[5/5] Checking for required tables...")
    required_tables = [
        'REPORT_INSTANCE',
        'REPORT_INSTANCE_SEGMENT',
        'RPTFILE_INSTANCE',
        'RPTFILE'
    ]

    try:
        cursor = conn.cursor()

        # Query to check if tables exist
        for table_name in required_tables:
            cursor.execute("""
                SELECT COUNT(*)
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_NAME = %s
            """, (table_name,))
            count = cursor.fetchone()[0]

            if count > 0:
                # Check row count
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = cursor.fetchone()[0]
                print(f"      ✓ {table_name} exists ({row_count:,} rows)")
            else:
                print(f"      ✗ {table_name} NOT FOUND")

        cursor.close()
    except Exception as e:
        print(f"      ⚠ Warning: Could not check tables: {e}")

    # Close connection
    conn.close()

    print()
    print("=" * 60)
    print("✓ CONNECTION TEST SUCCESSFUL!")
    print("=" * 60)
    print()
    print("You can now run Extract_Instances.py with the same connection parameters.")
    print()

    return True


def main():
    """Main entry point."""
    args = parse_arguments()

    success = test_connection(
        server=args.server,
        port=args.port,
        database=args.database,
        user=args.user,
        password=args.password,
        windows_auth=args.windows_auth
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
