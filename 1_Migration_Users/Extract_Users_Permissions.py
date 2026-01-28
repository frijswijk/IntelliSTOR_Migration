#!/usr/bin/env python3
"""
Extract_Users_Permissions.py - MS SQL Database Users and Permissions Extractor

Extracts users, user groups, sections, and permissions from MS SQL Server database.
Decodes binary Windows Security Descriptors (ACLs) to readable user/group permissions.

Generates CSV files:
1. Users.csv - User accounts (includes test users if --TESTDATA enabled)
2. UserGroups.csv - User groups (includes test groups if --TESTDATA enabled)
3. UserGroupAssignments.csv - User-group assignments (created if --TESTDATA enabled)
4. SecurityDomains.csv - Security domains
5. Sections.csv - Report sections
6. STYPE_FOLDER_ACCESS.csv - Decoded folder permissions (Group, User, Everyone)
7. STYPE_REPORT_SPECIES_ACCESS.csv - Decoded report species permissions
8. STYPE_SECTION_ACCESS.csv - Decoded section permissions
9. Unique_Sections_Access.csv - Aggregated section permissions by SECTION.NAME

Test Data Generation (--TESTDATA):
When --TESTDATA is enabled, the script:
1. Identifies unmapped RIDs in ACLs (RIDs not found in database)
2. Creates test groups for unmapped RIDs in UserGroups.csv
3. Creates test users in Users.csv
4. Creates user-group assignments in UserGroupAssignments.csv
Note: Test data is written to CSV files, NOT to the database.

Author: Generated for OCBC IntelliSTOR Migration
Date: 2026-01-22
"""

import pymssql
import csv
import argparse
import logging
import sys
import os
from pathlib import Path
from typing import Dict, List


# ============================================================================
# Configuration and Setup
# ============================================================================

def setup_logging(output_dir, quiet=False):
    """Setup logging to both console and file."""
    log_file = os.path.join(output_dir, 'Extract_Users_Permissions.log')

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
        description='Extract users, user groups, sections, and permissions from MS SQL Server database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Windows Authentication
  python Extract_Users_Permissions.py --server localhost --database IntelliSTOR --windows-auth

  # SQL Server Authentication
  python Extract_Users_Permissions.py --server localhost --database IntelliSTOR --user sa --password MyP@ssw0rd

  # With custom output directory
  python Extract_Users_Permissions.py --server localhost --database IntelliSTOR --windows-auth --output-dir C:\\Output

  # Quiet mode
  python Extract_Users_Permissions.py --server localhost --database IntelliSTOR --windows-auth --quiet

  # Test data generation (dry-run to preview changes)
  python Extract_Users_Permissions.py --server localhost --database IntelliSTOR --windows-auth --TESTDATA-DRYRUN

  # Test data generation (5000 users to CSV)
  python Extract_Users_Permissions.py --server localhost --database IntelliSTOR --windows-auth --TESTDATA

  # Test data generation (100 users to CSV, 1-5 groups each)
  python Extract_Users_Permissions.py --server localhost --database IntelliSTOR --windows-auth --TESTDATA --TESTDATA-USERS 100 --TESTDATA-MIN-GROUPS 1 --TESTDATA-MAX-GROUPS 5

Output Files:
  - Users.csv: User accounts (includes test users if --TESTDATA enabled)
  - UserGroups.csv: User groups (includes test groups if --TESTDATA enabled)
  - UserGroupAssignments.csv: User-group assignments (created if --TESTDATA enabled)
  - SecurityDomains.csv: Security domains
  - Sections.csv: Report sections
  - STYPE_FOLDER_ACCESS.csv: Decoded folder permissions (Group|User|Everyone)
  - STYPE_REPORT_SPECIES_ACCESS.csv: Decoded report species permissions
  - STYPE_SECTION_ACCESS.csv: Decoded section permissions
  - Unique_Sections_Access.csv: Aggregated section permissions by SECTION.NAME
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

    # Test data generation options
    parser.add_argument('--TESTDATA', action='store_true',
                        help='Enable test data generation for unmapped RIDs (writes to CSV files)')
    parser.add_argument('--TESTDATA-DRYRUN', action='store_true',
                        help='Preview test data generation without modifying CSV files')
    parser.add_argument('--TESTDATA-USERS', type=int, default=5000,
                        help='Number of test users to generate (default: 5000)')
    parser.add_argument('--TESTDATA-MIN-GROUPS', type=int, default=1,
                        help='Minimum groups per test user (default: 1)')
    parser.add_argument('--TESTDATA-MAX-GROUPS', type=int, default=3,
                        help='Maximum groups per test user (default: 3)')

    args = parser.parse_args()

    # Validate authentication parameters
    if not args.windows_auth and (not args.user or not args.password):
        parser.error('Either --windows-auth or both --user and --password must be provided')

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
# ACL Parsing Functions (from parse_acl_simple.py)
# ============================================================================

def parse_sid_from_bytes(data, offset):
    """Parse a SID from binary data."""
    if offset + 8 > len(data):
        return None, 0

    revision = data[offset]
    sub_authority_count = data[offset + 1]

    # Need enough space for full SID
    sid_size = 8 + (sub_authority_count * 4)
    if offset + sid_size > len(data):
        return None, 0

    # Authority (6 bytes, big-endian)
    authority = int.from_bytes(data[offset+2:offset+8], 'big')

    # Sub-authorities (4 bytes each, little-endian)
    sub_authorities = []
    for i in range(sub_authority_count):
        sa_offset = offset + 8 + (i * 4)
        sa = int.from_bytes(data[sa_offset:sa_offset+4], 'little')
        sub_authorities.append(sa)

    # Build SID string
    sid = f"S-{revision}-{authority}"
    for sa in sub_authorities:
        sid += f"-{sa}"

    return sid, sid_size


def identify_well_known_sid(sid):
    """Identify well-known SIDs."""
    well_known = {
        "S-1-1-0": "Everyone",
        "S-1-2-0": "Local",
        "S-1-3-0": "Creator Owner",
        "S-1-3-1": "Creator Group",
        "S-1-5-18": "Local System",
        "S-1-5-19": "NT Authority\\Local Service",
        "S-1-5-20": "NT Authority\\Network Service",
        "S-1-5-32-544": "BUILTIN\\Administrators",
        "S-1-5-32-545": "BUILTIN\\Users",
        "S-1-5-32-546": "BUILTIN\\Guests",
        "S-1-5-32-547": "BUILTIN\\Power Users",
        "S-1-5-32-551": "BUILTIN\\Backup Operators",
    }

    if sid in well_known:
        return well_known[sid]

    # Check for domain users/groups (S-1-5-21-...)
    if sid.startswith("S-1-5-21-"):
        parts = sid.split('-')
        if len(parts) >= 8:
            rid = int(parts[-1])
            return f"Domain User/Group (RID: {rid})"

    return sid


def find_all_sids_in_data(data):
    """Scan through data to find all SID patterns."""
    results = []

    # Look for SID patterns (starts with revision=1, sub-auth count, then authority)
    for i in range(len(data) - 8):
        if data[i] == 0x01:  # Revision 1
            sub_auth_count = data[i + 1]

            # Reasonable range for sub-authority count
            if 0 < sub_auth_count <= 15:
                sid, size = parse_sid_from_bytes(data, i)
                if sid:
                    # Look back for possible access mask (4 bytes before SID)
                    access_mask = None
                    if i >= 4:
                        access_mask = int.from_bytes(data[i-4:i], 'little')

                    results.append({
                        'offset': i,
                        'sid': sid,
                        'name': identify_well_known_sid(sid),
                        'access_mask': access_mask,
                        'size': size
                    })

    return results


# ============================================================================
# Data Extraction
# ============================================================================

class UsersPermissionsExtractor:
    """Extracts users and permissions data from MS SQL Server."""

    def __init__(self, conn, output_dir):
        """Initialize the extractor.

        Args:
            conn: Database connection
            output_dir: Output directory for CSV files
        """
        self.conn = conn
        self.output_dir = Path(output_dir)
        self.stats = {
            'users': 0,
            'user_groups': 0,
            'security_domains': 0,
            'sections': 0,
            'folder_permissions': 0,
            'report_permissions': 0,
            'section_permissions': 0,
            'test_groups_created': 0,
            'test_users_created': 0,
            'test_assignments_created': 0,
            'unmapped_rids_found': 0
        }

        # Test data generation settings
        self.testdata_mode = False
        self.testdata_dryrun = False
        self.testdata_user_count = 5000
        self.testdata_min_groups = 1
        self.testdata_max_groups = 3
        self.unmapped_rids = set()

        # RID maps (will be built during extraction)
        self.user_rid_map = {}
        self.group_rid_map = {}

    def table_exists(self, table_name):
        """Check if a table exists in the database."""
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                SELECT COUNT(*)
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_NAME = %s
            """, (table_name,))
            count = cursor.fetchone()[0]
            return count > 0
        except:
            return False
        finally:
            cursor.close()

    def extract_users(self):
        """Extract users from USER_PROFILE table."""
        output_file = 'Users.csv'
        logging.info(f'Extracting users...')

        # Try common table names
        table_name = None
        for name in ['SCM_USERS', 'USER_PROFILE', 'USERS', 'USER']:
            if self.table_exists(name):
                table_name = name
                break

        if not table_name:
            logging.warning('No user table found (tried SCM_USERS, USER_PROFILE, USERS, USER)')
            return

        cursor = self.conn.cursor()

        # Get all columns from the table
        cursor.execute(f"""
            SELECT *
            FROM {table_name}
            ORDER BY USER_ID
        """)

        # Get column names
        columns = [column[0] for column in cursor.description]

        # Fetch all rows and trim string values
        rows = cursor.fetchall()
        cursor.close()

        # Trim string values (remove trailing spaces)
        trimmed_rows = []
        for row in rows:
            trimmed_row = []
            for value in row:
                if isinstance(value, str):
                    trimmed_row.append(value.strip())
                else:
                    trimmed_row.append(value)
            trimmed_rows.append(trimmed_row)

        # Write to CSV
        output_path = self.output_dir / output_file
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(trimmed_rows)

        self.stats['users'] = len(trimmed_rows)
        logging.info(f'Written {len(trimmed_rows)} users to {output_path}')

    def extract_user_groups(self):
        """Extract user groups from USER_GROUP table."""
        output_file = 'UserGroups.csv'
        logging.info(f'Extracting user groups...')

        # Try common table names
        table_name = None
        for name in ['SCM_GROUPS', 'SCM_USER_GROUP', 'USER_GROUP', 'USERGROUP', 'GROUPS']:
            if self.table_exists(name):
                table_name = name
                break

        if not table_name:
            logging.warning('No user group table found (tried SCM_GROUPS, SCM_USER_GROUP, USER_GROUP, USERGROUP, GROUPS)')
            return

        cursor = self.conn.cursor()

        # Get all columns from the table
        cursor.execute(f"""
            SELECT *
            FROM {table_name}
            ORDER BY GROUP_ID
        """)

        # Get column names
        columns = [column[0] for column in cursor.description]

        # Fetch all rows and trim string values
        rows = cursor.fetchall()
        cursor.close()

        # Trim string values (remove trailing spaces)
        trimmed_rows = []
        for row in rows:
            trimmed_row = []
            for value in row:
                if isinstance(value, str):
                    trimmed_row.append(value.strip())
                else:
                    trimmed_row.append(value)
            trimmed_rows.append(trimmed_row)

        # Write to CSV
        output_path = self.output_dir / output_file
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(trimmed_rows)

        self.stats['user_groups'] = len(trimmed_rows)
        logging.info(f'Written {len(trimmed_rows)} user groups to {output_path}')

    def extract_security_domains(self):
        """Extract security domains from SCM_SECURITYDOMAIN table."""
        output_file = 'SecurityDomains.csv'
        logging.info(f'Extracting security domains...')

        if not self.table_exists('SCM_SECURITYDOMAIN'):
            logging.warning('SCM_SECURITYDOMAIN table not found')
            return

        cursor = self.conn.cursor()

        # Get all columns from the table
        cursor.execute("""
            SELECT *
            FROM SCM_SECURITYDOMAIN
            ORDER BY SECURITYDOMAIN_ID
        """)

        # Get column names
        columns = [column[0] for column in cursor.description]

        # Fetch all rows and trim string values
        rows = cursor.fetchall()
        cursor.close()

        # Trim string values (remove trailing spaces)
        trimmed_rows = []
        for row in rows:
            trimmed_row = []
            for value in row:
                if isinstance(value, str):
                    trimmed_row.append(value.strip())
                else:
                    trimmed_row.append(value)
            trimmed_rows.append(trimmed_row)

        # Write to CSV
        output_path = self.output_dir / output_file
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(trimmed_rows)

        self.stats['security_domains'] = len(trimmed_rows)
        logging.info(f'Written {len(trimmed_rows)} security domains to {output_path}')

    def extract_sections(self):
        """Extract sections from SECTION table."""
        output_file = 'Sections.csv'
        logging.info(f'Extracting sections...')

        if not self.table_exists('SECTION'):
            logging.warning('SECTION table not found')
            return

        cursor = self.conn.cursor()

        # Get all columns from the table
        cursor.execute("""
            SELECT *
            FROM SECTION
            ORDER BY SECTION_ID
        """)

        # Get column names
        columns = [column[0] for column in cursor.description]

        # Fetch all rows and trim string values
        rows = cursor.fetchall()
        cursor.close()

        # Trim string values (remove trailing spaces)
        trimmed_rows = []
        for row in rows:
            trimmed_row = []
            for value in row:
                if isinstance(value, str):
                    trimmed_row.append(value.strip())
                else:
                    trimmed_row.append(value)
            trimmed_rows.append(trimmed_row)

        # Write to CSV
        output_path = self.output_dir / output_file
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(trimmed_rows)

        self.stats['sections'] = len(trimmed_rows)
        logging.info(f'Written {len(trimmed_rows)} sections to {output_path}')

    def extract_folder_permissions(self):
        """Extract and decode folder permissions from STYPE_FOLDER."""
        output_file = 'STYPE_FOLDER_ACCESS.csv'
        logging.info(f'Extracting and decoding folder permissions...')

        # Try common table names
        table_name = None
        for name in ['STYPE_FOLDER', 'FOLDER_PERMISSION', 'FOLDER_PERMISSIONS', 'ITEM_PERMISSION', 'PERMISSIONS']:
            if self.table_exists(name):
                table_name = name
                break

        if not table_name:
            logging.warning('No folder permission table found (tried STYPE_FOLDER, FOLDER_PERMISSION, FOLDER_PERMISSIONS, ITEM_PERMISSION, PERMISSIONS)')
            return

        # Use instance RID mappings
        user_rid_map = self.user_rid_map
        group_rid_map = self.group_rid_map

        cursor = self.conn.cursor()

        try:
            # Query STYPE_FOLDER for binary ACL data
            cursor.execute(f"""
                SELECT FOLDER_ID, VALUE
                FROM {table_name}
                WHERE VALUE IS NOT NULL
                ORDER BY FOLDER_ID
            """)

            # Decode ACLs and build output
            decoded_rows = []
            row_count = 0
            for row in cursor:
                folder_id = row[0]
                value_binary = row[1]

                # Debug first 10 entries
                debug_idx = row_count if row_count < 10 else None
                if debug_idx is not None:
                    logging.debug(f"[{debug_idx}] Processing FOLDER_ID: {folder_id}")
                    logging.debug(f"[{debug_idx}] Value type: {type(value_binary)}")

                # Decode ACL
                acl_info = self.decode_acl_value(value_binary, user_rid_map, group_rid_map, debug_idx)

                decoded_rows.append({
                    'FOLDER_ID': folder_id,
                    'Group': '|'.join(str(gid) for gid in acl_info['groups']),
                    'User': '|'.join(str(uid) for uid in acl_info['users']),
                    'RID': '|'.join(str(rid) for rid in acl_info['rids']),
                    'Everyone': acl_info['everyone']
                })

                row_count += 1

            # Write CSV
            if decoded_rows:
                output_path = self.output_dir / output_file
                fieldnames = ['FOLDER_ID', 'Group', 'User', 'RID', 'Everyone']

                with open(output_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(decoded_rows)

                self.stats['folder_permissions'] = len(decoded_rows)
                logging.info(f'Written {len(decoded_rows)} folder permissions to {output_file}')
            else:
                logging.warning('No folder permissions found')

        except Exception as e:
            logging.error(f'Error extracting folder permissions: {e}', exc_info=True)
        finally:
            cursor.close()

    def extract_report_species_permissions(self):
        """Extract and decode report species permissions."""
        output_file = 'STYPE_REPORT_SPECIES_ACCESS.csv'
        logging.info(f'Extracting and decoding report species permissions...')

        # Try common table names
        table_name = None
        for name in ['STYPE_REPORT_SPECIES', 'REPORT_SPECIES_PERMISSION', 'REPORT_SPECIES_PERMISSIONS', 'SPECIES_PERMISSION']:
            if self.table_exists(name):
                table_name = name
                break

        if not table_name:
            logging.warning('No report species permission table found (tried STYPE_REPORT_SPECIES, REPORT_SPECIES_PERMISSION, REPORT_SPECIES_PERMISSIONS, SPECIES_PERMISSION)')
            return

        # Use instance RID mappings
        user_rid_map = self.user_rid_map
        group_rid_map = self.group_rid_map

        cursor = self.conn.cursor()

        try:
            # Query STYPE_REPORT_SPECIES for binary ACL data
            cursor.execute(f"""
                SELECT REPORT_SPECIES_ID, VALUE
                FROM {table_name}
                WHERE VALUE IS NOT NULL
                ORDER BY REPORT_SPECIES_ID
            """)

            # Decode ACLs and build output
            decoded_rows = []
            row_count = 0
            for row in cursor:
                report_species_id = row[0]
                value_binary = row[1]

                # Debug first 10 entries
                debug_idx = row_count if row_count < 10 else None
                if debug_idx is not None:
                    logging.debug(f"[{debug_idx}] Processing REPORT_SPECIES_ID: {report_species_id}")
                    logging.debug(f"[{debug_idx}] Value type: {type(value_binary)}")

                # Decode ACL
                acl_info = self.decode_acl_value(value_binary, user_rid_map, group_rid_map, debug_idx)

                decoded_rows.append({
                    'REPORT_SPECIES_ID': report_species_id,
                    'Group': '|'.join(str(gid) for gid in acl_info['groups']),
                    'User': '|'.join(str(uid) for uid in acl_info['users']),
                    'RID': '|'.join(str(rid) for rid in acl_info['rids']),
                    'Everyone': acl_info['everyone']
                })

                row_count += 1

            # Write CSV
            if decoded_rows:
                output_path = self.output_dir / output_file
                fieldnames = ['REPORT_SPECIES_ID', 'Group', 'User', 'RID', 'Everyone']

                with open(output_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(decoded_rows)

                self.stats['report_permissions'] = len(decoded_rows)
                logging.info(f'Written {len(decoded_rows)} report species permissions to {output_file}')
            else:
                logging.warning('No report species permissions found')

        except Exception as e:
            logging.error(f'Error extracting report species permissions: {e}', exc_info=True)
        finally:
            cursor.close()

    def extract_section_permissions(self):
        """Extract and decode section permissions."""
        output_file = 'STYPE_SECTION_ACCESS.csv'
        logging.info(f'Extracting and decoding section permissions...')

        # Try common table names
        table_name = None
        for name in ['STYPE_SECTION', 'SECTION_PERMISSION', 'SECTION_PERMISSIONS']:
            if self.table_exists(name):
                table_name = name
                break

        if not table_name:
            logging.warning('No section permission table found (tried STYPE_SECTION, SECTION_PERMISSION, SECTION_PERMISSIONS)')
            return

        # Use instance RID mappings
        user_rid_map = self.user_rid_map
        group_rid_map = self.group_rid_map

        cursor = self.conn.cursor()

        try:
            # Query STYPE_SECTION for binary ACL data
            cursor.execute(f"""
                SELECT REPORT_SPECIES_ID, SECTION_ID, VALUE
                FROM {table_name}
                WHERE VALUE IS NOT NULL
                ORDER BY REPORT_SPECIES_ID, SECTION_ID
            """)

            # Decode ACLs and build output
            decoded_rows = []
            row_count = 0
            for row in cursor:
                report_species_id = row[0]
                section_id = row[1]
                value_binary = row[2]

                # Debug first 10 entries
                debug_idx = row_count if row_count < 10 else None
                if debug_idx is not None:
                    logging.debug(f"[{debug_idx}] Processing REPORT_SPECIES_ID: {report_species_id}, SECTION_ID: {section_id}")
                    logging.debug(f"[{debug_idx}] Value type: {type(value_binary)}")

                # Decode ACL
                acl_info = self.decode_acl_value(value_binary, user_rid_map, group_rid_map, debug_idx)

                decoded_rows.append({
                    'REPORT_SPECIES_ID': report_species_id,
                    'SECTION_ID': section_id,
                    'Group': '|'.join(str(gid) for gid in acl_info['groups']),
                    'User': '|'.join(str(uid) for uid in acl_info['users']),
                    'RID': '|'.join(str(rid) for rid in acl_info['rids']),
                    'Everyone': acl_info['everyone']
                })

                row_count += 1

            # Write CSV
            if decoded_rows:
                output_path = self.output_dir / output_file
                fieldnames = ['REPORT_SPECIES_ID', 'SECTION_ID', 'Group', 'User', 'RID', 'Everyone']

                with open(output_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(decoded_rows)

                self.stats['section_permissions'] = len(decoded_rows)
                logging.info(f'Written {len(decoded_rows)} section permissions to {output_file}')
            else:
                logging.warning('No section permissions found')

        except Exception as e:
            logging.error(f'Error extracting section permissions: {e}', exc_info=True)
        finally:
            cursor.close()

    def build_user_group_maps(self):
        """
        Build dictionaries mapping RIDs to USER_IDs and GROUP_IDs.

        Returns:
            (user_rid_map, group_rid_map) where:
            - user_rid_map: {RID: USER_ID}
            - group_rid_map: {RID: GROUP_ID}
        """
        user_rid_map = {}
        group_rid_map = {}

        cursor = self.conn.cursor()

        # Query all users
        for user_table in ['SCM_USERS', 'USER_PROFILE', 'USERS', 'USER']:
            if self.table_exists(user_table):
                cursor.execute(f"SELECT USER_ID FROM {user_table}")
                for row in cursor:
                    user_id = row[0]
                    user_rid_map[user_id] = user_id
                break

        # Query all groups
        for group_table in ['SCM_GROUPS', 'SCM_USER_GROUP', 'USER_GROUP', 'USERGROUP', 'GROUPS']:
            if self.table_exists(group_table):
                cursor.execute(f"SELECT GROUP_ID FROM {group_table}")
                for row in cursor:
                    group_id = row[0]
                    group_rid_map[group_id] = group_id
                break

        cursor.close()
        logging.debug(f'Built RID maps: {len(user_rid_map)} users, {len(group_rid_map)} groups')
        logging.debug(f'User RID map: {user_rid_map}')
        logging.debug(f'Group RID map: {group_rid_map}')
        return user_rid_map, group_rid_map

    def build_user_group_maps_from_csv(self):
        """
        Build dictionaries mapping RIDs to USER_IDs and GROUP_IDs from CSV files.

        Returns:
            (user_rid_map, group_rid_map) where:
            - user_rid_map: {RID: USER_ID}
            - group_rid_map: {RID: GROUP_ID}
        """
        user_rid_map = {}
        group_rid_map = {}

        # Read users from CSV
        users_csv_path = self.output_dir / 'Users.csv'
        if users_csv_path.exists():
            with open(users_csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    user_id = int(row['USER_ID'])
                    user_rid_map[user_id] = user_id
        else:
            logging.warning('Users.csv not found - user RID map will be empty')

        # Read groups from CSV
        groups_csv_path = self.output_dir / 'UserGroups.csv'
        if groups_csv_path.exists():
            with open(groups_csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    group_id = int(row['GROUP_ID'])
                    group_rid_map[group_id] = group_id
        else:
            logging.warning('UserGroups.csv not found - group RID map will be empty')

        logging.debug(f'Built RID maps from CSV: {len(user_rid_map)} users, {len(group_rid_map)} groups')
        return user_rid_map, group_rid_map

    def get_security_domain_id(self):
        """
        Get the SECURITYDOMAIN_ID from SCM_SECURITYDOMAIN table.

        Returns:
            SECURITYDOMAIN_ID (int), defaults to 1 if table is empty or doesn't exist
        """
        cursor = self.conn.cursor()
        try:
            if self.table_exists('SCM_SECURITYDOMAIN'):
                cursor.execute("SELECT TOP 1 SECURITYDOMAIN_ID FROM SCM_SECURITYDOMAIN ORDER BY SECURITYDOMAIN_ID")
                row = cursor.fetchone()
                if row:
                    return row[0]
            logging.warning('No security domain found, defaulting to SECURITYDOMAIN_ID = 1')
            return 1
        except Exception as e:
            logging.warning(f'Error querying security domain: {e}, defaulting to SECURITYDOMAIN_ID = 1')
            return 1
        finally:
            cursor.close()

    def get_max_user_id(self):
        """
        Get the maximum USER_ID from the users table.

        Returns:
            MAX(USER_ID) or 0 if table is empty
        """
        cursor = self.conn.cursor()
        try:
            for user_table in ['SCM_USERS', 'USER_PROFILE', 'USERS', 'USER']:
                if self.table_exists(user_table):
                    cursor.execute(f"SELECT MAX(USER_ID) FROM {user_table}")
                    row = cursor.fetchone()
                    max_id = row[0] if row and row[0] is not None else 0
                    logging.debug(f'Max USER_ID from {user_table}: {max_id}')
                    return max_id
            logging.warning('No user table found, returning 0')
            return 0
        except Exception as e:
            logging.error(f'Error getting max USER_ID: {e}')
            return 0
        finally:
            cursor.close()

    def get_table_name_for_groups(self):
        """
        Detect the actual group table name (handles variations).

        Returns:
            Table name (str) or None if not found
        """
        for name in ['SCM_GROUPS', 'SCM_USER_GROUP', 'USER_GROUP', 'USERGROUP', 'GROUPS']:
            if self.table_exists(name):
                return name
        return None

    def get_table_name_for_users(self):
        """
        Detect the actual user table name (handles variations).

        Returns:
            Table name (str) or None if not found
        """
        for name in ['SCM_USERS', 'USER_PROFILE', 'USERS', 'USER']:
            if self.table_exists(name):
                return name
        return None

    def discover_group_table_columns(self, table_name):
        """
        Query INFORMATION_SCHEMA.COLUMNS to discover group table schema.

        Args:
            table_name: Name of the group table

        Returns:
            dict: {column_name: {'type': data_type, 'nullable': is_nullable}}
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = %s
                ORDER BY ORDINAL_POSITION
            """, (table_name,))

            columns = {}
            for row in cursor:
                columns[row[0]] = {
                    'type': row[1],
                    'nullable': row[2] == 'YES'
                }
            return columns
        except Exception as e:
            logging.error(f'Error discovering group table columns: {e}')
            return {}
        finally:
            cursor.close()

    def discover_user_table_columns(self, table_name):
        """
        Query INFORMATION_SCHEMA.COLUMNS to discover user table schema.

        Args:
            table_name: Name of the user table

        Returns:
            dict: {column_name: {'type': data_type, 'nullable': is_nullable}}
        """
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = %s
                ORDER BY ORDINAL_POSITION
            """, (table_name,))

            columns = {}
            for row in cursor:
                columns[row[0]] = {
                    'type': row[1],
                    'nullable': row[2] == 'YES'
                }
            return columns
        except Exception as e:
            logging.error(f'Error discovering user table columns: {e}')
            return {}
        finally:
            cursor.close()

    def extract_rid_from_sid(self, sid):
        """
        Extract RID (Relative ID) from a domain SID.

        Args:
            sid: SID string (e.g., "S-1-5-21-1436318678-1461800975-2018848785-35442")

        Returns:
            RID (int) or None if not a domain SID
        """
        parts = sid.split('-')
        # Domain SID format: S-1-5-21-domain1-domain2-domain3-RID
        # parts: ['S', '1', '5', '21', 'domain1', 'domain2', 'domain3', 'RID']
        # Check parts[3] == '21' (not parts[2])
        if len(parts) >= 8 and parts[3] == '21':  # Domain SID format
            try:
                return int(parts[-1])
            except ValueError:
                return None
        return None

    def decode_acl_value(self, value_binary, user_rid_map, group_rid_map, debug_idx=None):
        """
        Decode binary ACL VALUE to extract user/group permissions.

        Args:
            value_binary: Binary ACL data from database
            user_rid_map: {RID: USER_ID} mapping
            group_rid_map: {RID: GROUP_ID} mapping
            debug_idx: Index for debug logging (only log first 10)

        Returns:
            {
                'users': [list of USER_IDs],
                'groups': [list of GROUP_IDs],
                'rids': [list of all extracted RIDs],
                'everyone': 1 or 0
            }
        """
        result = {
            'users': [],
            'groups': [],
            'rids': [],
            'everyone': 0
        }

        debug = debug_idx is not None and debug_idx < 10

        # Handle hex string vs bytes
        if isinstance(value_binary, str):
            if debug:
                logging.debug(f"[{debug_idx}] ACL is string type, length: {len(value_binary)}")
                logging.debug(f"[{debug_idx}] First 100 chars: {value_binary[:100]}")
            if value_binary.startswith('0x'):
                value_binary = value_binary[2:]
            try:
                data = bytes.fromhex(value_binary)
                if debug:
                    logging.debug(f"[{debug_idx}] Converted to {len(data)} bytes")
            except Exception as e:
                logging.debug(f"Failed to decode hex ACL: {str(value_binary)[:50]}... Error: {e}")
                return result
        else:
            data = value_binary
            if debug:
                logging.debug(f"[{debug_idx}] ACL is bytes type, length: {len(data)}")
                logging.debug(f"[{debug_idx}] First 64 bytes (hex): {data[:64].hex()}")

        # Parse all SIDs from ACL
        sids = find_all_sids_in_data(data)

        if debug:
            logging.debug(f"[{debug_idx}] Found {len(sids)} SID(s) in ACL")

        for sid_info in sids:
            sid = sid_info['sid']

            if debug:
                logging.debug(f"[{debug_idx}]   SID: {sid}, Name: {sid_info['name']}")

            # Check for Everyone
            if sid == 'S-1-1-0':
                result['everyone'] = 1
                if debug:
                    logging.debug(f"[{debug_idx}]   → Everyone detected")
                continue

            # Extract RID from domain SIDs
            rid = self.extract_rid_from_sid(sid)
            if rid is None:
                if debug:
                    logging.debug(f"[{debug_idx}]   → No RID extracted (not domain SID)")
                continue

            if debug:
                logging.debug(f"[{debug_idx}]   → Extracted RID: {rid}")
                logging.debug(f"[{debug_idx}]   → Checking if {rid} in user_rid_map: {rid in user_rid_map}")
                logging.debug(f"[{debug_idx}]   → Checking if {rid} in group_rid_map: {rid in group_rid_map}")

            # Add RID to rids list (always, even if not in database)
            if rid not in result['rids']:
                result['rids'].append(rid)

            # Try to map to USER_ID
            if rid in user_rid_map:
                if rid not in result['users']:
                    result['users'].append(rid)
                    if debug:
                        logging.debug(f"[{debug_idx}]   → Mapped to USER_ID: {rid}")

            # Try to map to GROUP_ID
            if rid in group_rid_map:
                if rid not in result['groups']:
                    result['groups'].append(rid)
                    if debug:
                        logging.debug(f"[{debug_idx}]   → Mapped to GROUP_ID: {rid}")

            # Track unmapped RIDs if in testdata mode
            if self.testdata_mode:
                if rid not in user_rid_map and rid not in group_rid_map:
                    self.unmapped_rids.add(rid)
                    if debug:
                        logging.debug(f"[{debug_idx}]   → Unmapped RID tracked: {rid}")

        if debug:
            logging.debug(f"[{debug_idx}] Final result: Users={result['users']}, Groups={result['groups']}, RIDs={result['rids']}, Everyone={result['everyone']}")

        return result

    def generate_test_data(self):
        """
        Generate test data for unmapped RIDs found during ACL processing.

        Creates:
        1. Test groups for unmapped RIDs (GROUP_ID = RID, NAME = str(RID), DESCRIPTION = "TEST-{RID}")
        2. Test users (5000 by default)
        3. Random group assignments (1-3 groups per user)

        IMPORTANT: Writes to CSV files (UserGroups.csv, Users.csv) instead of database.
        """
        import random
        from datetime import datetime

        logging.info('='*70)
        logging.info('GENERATING TEST DATA TO CSV FILES')
        logging.info('='*70)

        # Validation: Check if there are unmapped RIDs
        if not self.unmapped_rids:
            logging.info('No unmapped RIDs found - no test data to generate')
            return

        logging.info(f'Found {len(self.unmapped_rids)} unmapped RIDs: {sorted(self.unmapped_rids)}')
        self.stats['unmapped_rids_found'] = len(self.unmapped_rids)

        # Detect table names for schema discovery
        groups_table = self.get_table_name_for_groups()
        users_table = self.get_table_name_for_users()

        if not groups_table:
            logging.error('Cannot generate test data: Group table not found')
            return

        if not users_table:
            logging.error('Cannot generate test data: User table not found')
            return

        logging.info(f'Using table schemas from: {groups_table} (groups), {users_table} (users)')

        # Discover table schemas
        group_columns = self.discover_group_table_columns(groups_table)
        user_columns = self.discover_user_table_columns(users_table)

        if not group_columns:
            logging.error('Cannot generate test data: Failed to discover group table schema')
            return

        if not user_columns:
            logging.error('Cannot generate test data: Failed to discover user table schema')
            return

        logging.debug(f'Group table columns: {group_columns}')
        logging.debug(f'User table columns: {user_columns}')

        # Get SECURITYDOMAIN_ID
        security_domain_id = self.get_security_domain_id()
        logging.info(f'Using SECURITYDOMAIN_ID: {security_domain_id}')

        cursor = self.conn.cursor()

        try:
            # ================================================================
            # TASK 1: Create Test Groups for Unmapped RIDs (to CSV)
            # ================================================================

            logging.info('Task 1: Creating test groups for unmapped RIDs to UserGroups.csv...')

            # Read existing groups from CSV to avoid duplicates
            groups_csv_path = self.output_dir / 'UserGroups.csv'
            existing_group_ids = set()
            existing_group_rows = []

            if groups_csv_path.exists():
                with open(groups_csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    csv_columns = reader.fieldnames
                    for row in reader:
                        existing_group_rows.append(row)
                        existing_group_ids.add(int(row['GROUP_ID']))
                logging.debug(f'Existing GROUP_IDs from CSV: {existing_group_ids}')
            else:
                # Use discovered columns from database schema
                csv_columns = list(group_columns.keys())
                logging.debug(f'No existing CSV, using columns from schema: {csv_columns}')

            # Filter unmapped RIDs against existing GROUP_IDs
            new_groups = []
            for rid in self.unmapped_rids:
                if rid not in existing_group_ids:
                    new_groups.append(rid)

            logging.info(f'Creating {len(new_groups)} new test groups (filtered {len(self.unmapped_rids) - len(new_groups)} duplicates)')

            if new_groups:
                # Prepare new group rows
                new_group_rows = []
                for rid in new_groups:
                    row = {}

                    # Fill columns based on CSV schema
                    for col in csv_columns:
                        if col == 'SECURITYDOMAIN_ID':
                            row[col] = security_domain_id
                        elif col == 'GROUP_ID':
                            row[col] = rid
                        elif col == 'FLAGS':
                            row[col] = 0
                        elif col == 'GROUPNAME':
                            row[col] = str(rid)
                        elif col == 'DESCRIPTION':
                            row[col] = f'TEST-{rid}'
                        else:
                            row[col] = ''  # Default empty for other columns

                    new_group_rows.append(row)

                    if self.testdata_dryrun:
                        logging.info(f'[DRY-RUN] Would add group to CSV: {row}')

                # Write back to CSV (existing + new)
                if not self.testdata_dryrun:
                    with open(groups_csv_path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=csv_columns)
                        writer.writeheader()
                        writer.writerows(existing_group_rows)
                        writer.writerows(new_group_rows)
                    logging.info(f'Successfully added {len(new_groups)} test groups to UserGroups.csv')

                self.stats['test_groups_created'] = len(new_groups)
            else:
                logging.info('No new test groups to create (all RIDs already exist)')

            # ================================================================
            # TASK 2: Create Test Users (to CSV)
            # ================================================================

            logging.info(f'Task 2: Creating {self.testdata_user_count} test users to Users.csv...')

            # Read existing users from CSV
            users_csv_path = self.output_dir / 'Users.csv'
            existing_user_rows = []
            max_user_id = 0

            if users_csv_path.exists():
                with open(users_csv_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    csv_columns = reader.fieldnames
                    for row in reader:
                        existing_user_rows.append(row)
                        user_id = int(row['USER_ID'])
                        if user_id > max_user_id:
                            max_user_id = user_id
            else:
                # Use discovered columns from database schema
                csv_columns = list(user_columns.keys())
                logging.debug(f'No existing Users CSV, using columns from schema: {csv_columns}')

            start_user_id = max_user_id + 1000
            logging.info(f'Max existing USER_ID: {max_user_id}, starting new users at {start_user_id}')

            # Check if PASSWORD column is nullable
            password_nullable = user_columns.get('PASSWORD', {}).get('nullable', True)
            logging.debug(f'PASSWORD column nullable: {password_nullable}')

            # Create new user rows
            new_user_rows = []
            current_time = datetime.now()

            for i in range(1, self.testdata_user_count + 1):
                user_id = start_user_id + i
                username = f'testuser{i:05d}'

                row = {}
                for col in csv_columns:
                    if col == 'SECURITYDOMAIN_ID':
                        row[col] = security_domain_id
                    elif col == 'USER_ID':
                        row[col] = user_id
                    elif col == 'USERNAME':
                        row[col] = username
                    elif col == 'PASSWORD':
                        row[col] = '' if password_nullable else ''
                    elif col == 'FLAGS':
                        row[col] = 0
                    elif col == 'PASSWORD_LAST_MODIFIED_TIME':
                        row[col] = current_time.strftime('%Y-%m-%d %H:%M:%S')
                    elif col == 'CREATION_TIME':
                        row[col] = current_time.strftime('%Y-%m-%d %H:%M:%S')
                    elif col == 'LAST_MODIFIED_TIME':
                        row[col] = current_time.strftime('%Y-%m-%d %H:%M:%S')
                    elif col == 'FULLNAME':
                        row[col] = f'Test User {i}'
                    elif col == 'DESCRIPTION':
                        row[col] = f'Generated test user {i}'
                    else:
                        row[col] = ''  # Default empty for other columns

                new_user_rows.append(row)

                if self.testdata_dryrun:
                    if i <= 5:  # Only log first 5 in dry-run
                        logging.info(f'[DRY-RUN] Would add user to CSV: {row}')

                if i % 1000 == 0:
                    logging.info(f'Prepared {i}/{self.testdata_user_count} test users...')

            # Write back to CSV (existing + new)
            if not self.testdata_dryrun:
                with open(users_csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=csv_columns)
                    writer.writeheader()
                    writer.writerows(existing_user_rows)
                    writer.writerows(new_user_rows)
                logging.info(f'Successfully added {self.testdata_user_count} test users to Users.csv')

            self.stats['test_users_created'] = self.testdata_user_count

            # ================================================================
            # TASK 3: Assign Users to Test Groups (to CSV)
            # ================================================================

            logging.info(f'Task 3: Creating user-group assignments to UserGroupAssignments.csv...')

            # Only assign to test groups we just created
            test_groups_list = list(new_groups) if new_groups else []

            if not test_groups_list:
                logging.warning('No test groups available for assignment - skipping user-group assignments')
            else:
                # Create user-group assignments CSV
                assignments_csv_path = self.output_dir / 'UserGroupAssignments.csv'
                assignment_rows = []

                # Read existing assignments if file exists
                if assignments_csv_path.exists():
                    with open(assignments_csv_path, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            assignment_rows.append(row)

                assignment_count = 0
                for i in range(1, self.testdata_user_count + 1):
                    user_id = start_user_id + i

                    # Random number of groups (between min and max)
                    num_groups = random.randint(self.testdata_min_groups, self.testdata_max_groups)
                    num_groups = min(num_groups, len(test_groups_list))  # Don't exceed available groups

                    # Random selection from test groups
                    selected_groups = random.sample(test_groups_list, num_groups)

                    for group_id in selected_groups:
                        row = {
                            'SECURITYDOMAIN_ID': security_domain_id,
                            'USER_ID': user_id,
                            'GROUP_ID': group_id,
                            'FLAGS': 0
                        }
                        assignment_rows.append(row)

                        if self.testdata_dryrun:
                            if i <= 3:  # Only log first 3 users in dry-run
                                logging.info(f'[DRY-RUN] Would add assignment to CSV: USER_ID {user_id} to GROUP_ID {group_id}')

                        assignment_count += 1

                    if i % 1000 == 0:
                        logging.info(f'Processed assignments for {i}/{self.testdata_user_count} users...')

                # Write assignments CSV
                if not self.testdata_dryrun:
                    with open(assignments_csv_path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=['SECURITYDOMAIN_ID', 'USER_ID', 'GROUP_ID', 'FLAGS'])
                        writer.writeheader()
                        writer.writerows(assignment_rows)
                    logging.info(f'Successfully created {assignment_count} user-group assignments in UserGroupAssignments.csv')

                self.stats['test_assignments_created'] = assignment_count

            # ================================================================
            # Summary
            # ================================================================

            logging.info('='*70)
            if self.testdata_dryrun:
                logging.info('TEST DATA GENERATION DRY-RUN COMPLETE')
                logging.info('(No CSV files were modified)')
            else:
                logging.info('TEST DATA GENERATION TO CSV COMPLETE')
            logging.info(f'  Test Groups Added to CSV: {self.stats["test_groups_created"]}')
            logging.info(f'  Test Users Added to CSV: {self.stats["test_users_created"]}')
            logging.info(f'  User-Group Assignments in CSV: {self.stats["test_assignments_created"]}')
            logging.info('='*70)

        except Exception as e:
            logging.error(f'Error generating test data to CSV: {e}', exc_info=True)
            raise
        finally:
            cursor.close()

    def create_unique_sections_access(self):
        """
        Create aggregated section permissions across all report species.

        Aggregates by SECTION.NAME (e.g., "501", "502"), not SECTION_ID.
        SECTION_ID is unique within REPORT_SPECIES_ID, but NAME is the actual section identifier.
        """
        output_file = 'Unique_Sections_Access.csv'
        logging.info('Creating unique sections access aggregation...')

        # Use instance RID mappings
        user_rid_map = self.user_rid_map
        group_rid_map = self.group_rid_map

        cursor = self.conn.cursor()

        try:
            # Query STYPE_SECTION joined with SECTION to get NAME
            cursor.execute("""
                SELECT s.NAME, st.VALUE
                FROM STYPE_SECTION st
                INNER JOIN SECTION s
                  ON st.REPORT_SPECIES_ID = s.REPORT_SPECIES_ID
                  AND st.SECTION_ID = s.SECTION_ID
                WHERE st.VALUE IS NOT NULL
                ORDER BY s.NAME
            """)

            # Aggregate permissions by NAME
            section_perms = {}  # {NAME: {users: set, groups: set, rids: set, everyone: int}}

            row_count = 0
            for row in cursor:
                section_name = row[0]
                value_binary = row[1]

                # Debug first 10 entries
                debug_idx = row_count if row_count < 10 else None
                if debug_idx is not None:
                    logging.debug(f"[{debug_idx}] Processing SECTION_NAME: {section_name}")
                    logging.debug(f"[{debug_idx}] Value type: {type(value_binary)}")

                # Decode ACL
                acl_info = self.decode_acl_value(value_binary, user_rid_map, group_rid_map, debug_idx)

                row_count += 1

                if section_name not in section_perms:
                    section_perms[section_name] = {
                        'users': set(),
                        'groups': set(),
                        'rids': set(),
                        'everyone': 0
                    }

                # Aggregate users, groups, and rids
                section_perms[section_name]['users'].update(acl_info['users'])
                section_perms[section_name]['groups'].update(acl_info['groups'])
                section_perms[section_name]['rids'].update(acl_info['rids'])

                # If any instance has Everyone=1, set it
                if acl_info['everyone'] == 1:
                    section_perms[section_name]['everyone'] = 1

            cursor.close()

            # Write aggregated output
            if section_perms:
                output_path = self.output_dir / output_file
                fieldnames = ['SECTION_NAME', 'Group', 'User', 'RID', 'Everyone']

                with open(output_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()

                    for section_name in sorted(section_perms.keys()):
                        perms = section_perms[section_name]
                        writer.writerow({
                            'SECTION_NAME': section_name,
                            'Group': '|'.join(str(gid) for gid in sorted(perms['groups'])),
                            'User': '|'.join(str(uid) for uid in sorted(perms['users'])),
                            'RID': '|'.join(str(rid) for rid in sorted(perms['rids'])),
                            'Everyone': perms['everyone']
                        })

                logging.info(f'Written {len(section_perms)} unique section permissions to {output_file}')
            else:
                logging.warning('No unique section permissions to aggregate')

        except Exception as e:
            logging.error(f'Error creating unique sections access: {e}', exc_info=True)
        finally:
            if cursor:
                cursor.close()

    def extract_all(self):
        """Extract all users and permissions data."""
        # Phase 1: Extract existing data
        self.extract_users()
        self.extract_user_groups()
        self.extract_security_domains()
        self.extract_sections()

        # Build initial RID maps
        self.user_rid_map, self.group_rid_map = self.build_user_group_maps()

        # Phase 2: Extract ACLs (populates unmapped_rids if in testdata mode)
        self.extract_folder_permissions()
        self.extract_report_species_permissions()
        self.extract_section_permissions()

        # Phase 3: Generate test data (if enabled)
        if self.testdata_mode:
            self.generate_test_data()
            # Rebuild RID maps from CSV to include newly created groups/users
            self.user_rid_map, self.group_rid_map = self.build_user_group_maps_from_csv()
            logging.info('Rebuilt RID maps from CSV after test data generation')

            # Phase 3.5: Re-extract ACL permissions with updated RID maps
            logging.info('Re-extracting ACL permissions with updated RID maps...')
            self.extract_folder_permissions()
            self.extract_report_species_permissions()
            self.extract_section_permissions()
            logging.info('ACL permissions updated with test data groups')

        # Phase 4: Create aggregated sections
        self.create_unique_sections_access()


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
        logging.info('Extract_Users_Permissions.py - Starting')
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
        extractor = UsersPermissionsExtractor(conn, args.output_dir)

        # Configure test data mode
        if args.TESTDATA or args.TESTDATA_DRYRUN:
            extractor.testdata_mode = True
            extractor.testdata_dryrun = args.TESTDATA_DRYRUN
            extractor.testdata_user_count = args.TESTDATA_USERS
            extractor.testdata_min_groups = args.TESTDATA_MIN_GROUPS
            extractor.testdata_max_groups = args.TESTDATA_MAX_GROUPS

            if args.TESTDATA_DRYRUN:
                logging.info('TEST DATA DRY-RUN MODE: No CSV files will be modified')
            else:
                logging.info('TEST DATA MODE: Test users and groups will be written to CSV files')

        extractor.extract_all()

        # Close connection
        conn.close()
        if not args.quiet:
            logging.info('Database connection closed')

        # Print summary
        if args.quiet:
            summary = (f'Completed: Extracted {extractor.stats["users"]} users, '
                      f'{extractor.stats["user_groups"]} groups, '
                      f'{extractor.stats["security_domains"]} domains, '
                      f'{extractor.stats["sections"]} sections')
            if args.TESTDATA or args.TESTDATA_DRYRUN:
                summary += (f' | Test Data: {extractor.stats["test_groups_created"]} groups, '
                          f'{extractor.stats["test_users_created"]} users, '
                          f'{extractor.stats["test_assignments_created"]} assignments')
            print(summary)
        else:
            logging.info('='*70)
            logging.info('EXTRACTION COMPLETE')
            logging.info('Statistics:')
            logging.info(f'  Users: {extractor.stats["users"]}')
            logging.info(f'  User Groups: {extractor.stats["user_groups"]}')
            logging.info(f'  Security Domains: {extractor.stats["security_domains"]}')
            logging.info(f'  Sections: {extractor.stats["sections"]}')
            logging.info(f'  Folder Permissions: {extractor.stats["folder_permissions"]}')
            logging.info(f'  Report Permissions: {extractor.stats["report_permissions"]}')
            logging.info(f'  Section Permissions: {extractor.stats["section_permissions"]}')

            # Test data statistics (if applicable)
            if args.TESTDATA or args.TESTDATA_DRYRUN:
                logging.info('')
                if args.TESTDATA_DRYRUN:
                    logging.info('Test Data Statistics (DRY-RUN):')
                else:
                    logging.info('Test Data Statistics:')
                logging.info(f'  Unmapped RIDs Found: {extractor.stats["unmapped_rids_found"]}')
                logging.info(f'  Test Groups Created: {extractor.stats["test_groups_created"]}')
                logging.info(f'  Test Users Created: {extractor.stats["test_users_created"]}')
                logging.info(f'  Test Assignments Created: {extractor.stats["test_assignments_created"]}')

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
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
