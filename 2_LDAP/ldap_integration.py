#!/usr/bin/env python3
"""
ldap_integration.py - LDAP Integration Tool for IntelliSTOR Migration

Imports users and groups from CSV files to Active Directory LDAP.
Provides testing, dry-run, and browser interface for LDAP directory.

Author: Generated for OCBC IntelliSTOR Migration
Date: 2026-01-23
"""

import ldap3
import csv
import argparse
import logging
import sys
import os
import ssl
from pathlib import Path
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import secrets
import string


# ============================================================================
# Configuration and Setup
# ============================================================================

def setup_logging(output_dir, quiet=False):
    """Setup logging to both console and file."""
    log_file = os.path.join(output_dir, 'ldap_integration.log')

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


def add_connection_args(parser):
    """Add common connection arguments to a parser."""
    parser.add_argument('--server', required=True, help='LDAP server hostname/IP')
    parser.add_argument('--port', type=int, default=389, help='LDAP port (default: 389, use 636 for SSL)')
    parser.add_argument('--bind-dn', required=True, help='Bind DN (e.g., cn=admin,dc=ocbc,dc=com)')
    parser.add_argument('--password', required=True, help='Bind password')
    parser.add_argument('--use-ssl', action='store_true', help='Use LDAPS (SSL/TLS)')
    parser.add_argument('--base-dn', required=True, help='Base DN (e.g., dc=ocbc,dc=com)')
    parser.add_argument('--output-dir', '-o', default='.', help='Output directory for logs (default: current directory)')
    parser.add_argument('--quiet', action='store_true', help='Quiet mode - minimal console output')

    # SSL Certificate Verification
    ssl_group = parser.add_argument_group('SSL Certificate Verification')
    ssl_group.add_argument('--ssl-no-verify', action='store_true',
                          help='Skip SSL certificate verification (INSECURE - for testing only)')
    ssl_group.add_argument('--ssl-ca-cert', metavar='PATH',
                          help='Path to CA certificate file for SSL verification (PEM format)')
    ssl_group.add_argument('--ssl-ca-path', metavar='PATH',
                          help='Path to directory containing CA certificates')


# ============================================================================
# LDAP Connection Manager
# ============================================================================

class LDAPConnectionManager:
    """Handles LDAP connections with Active Directory."""

    def __init__(self, server, port, bind_dn, password, use_ssl=False, base_dn=None,
                 ssl_no_verify=False, ssl_ca_cert=None, ssl_ca_path=None):
        """Initialize with connection parameters.

        Args:
            server: LDAP server hostname/IP
            port: LDAP port (389 or 636)
            bind_dn: Bind DN for authentication
            password: Bind password
            use_ssl: Use SSL/TLS connection
            base_dn: Base DN for searches
            ssl_no_verify: Skip SSL certificate verification (insecure)
            ssl_ca_cert: Path to CA certificate file for SSL verification
            ssl_ca_path: Path to directory containing CA certificates
        """
        self.server = server
        self.port = port
        self.bind_dn = bind_dn
        self.password = password
        self.use_ssl = use_ssl
        self.base_dn = base_dn
        self.ssl_no_verify = ssl_no_verify
        self.ssl_ca_cert = ssl_ca_cert
        self.ssl_ca_path = ssl_ca_path
        self.ldap_server = None
        self.connection = None

        # Validate SSL configuration
        self._validate_ssl_config()

    def _validate_ssl_config(self):
        """Validate SSL configuration parameters.

        Ensures:
        - Mutual exclusivity between --ssl-no-verify and CA cert options
        - CA cert file/path exists if provided
        - Warns if SSL options provided without --use-ssl
        - Displays security warning when verification is disabled
        """
        # Check mutual exclusivity
        if self.ssl_no_verify and (self.ssl_ca_cert or self.ssl_ca_path):
            raise ValueError(
                'Cannot use --ssl-no-verify with --ssl-ca-cert or --ssl-ca-path. '
                'Choose either certificate verification or skip verification.'
            )

        # Validate CA cert file exists
        if self.ssl_ca_cert and not os.path.isfile(self.ssl_ca_cert):
            raise ValueError(f'CA certificate file not found: {self.ssl_ca_cert}')

        # Validate CA cert path exists
        if self.ssl_ca_path and not os.path.isdir(self.ssl_ca_path):
            raise ValueError(f'CA certificate directory not found: {self.ssl_ca_path}')

        # Warn if SSL options provided without SSL
        if not self.use_ssl and (self.ssl_no_verify or self.ssl_ca_cert or self.ssl_ca_path):
            logging.warning('SSL certificate options provided but --use-ssl not set. Options will be ignored.')

        # Security warning when verification disabled
        if self.use_ssl and self.ssl_no_verify:
            logging.warning('='*70)
            logging.warning('SECURITY WARNING: SSL certificate verification is disabled!')
            logging.warning('This is INSECURE and should only be used for testing.')
            logging.warning('Man-in-the-middle attacks are possible.')
            logging.warning('='*70)

    def _create_tls_config(self):
        """Create TLS configuration based on SSL settings.

        Returns:
            ldap3.Tls or None: TLS configuration object or None if SSL not used
        """
        if not self.use_ssl:
            return None

        # Use older ldap3.Tls parameter format (compatible with ldap3 2.9.1)
        # Skip verification mode (insecure)
        if self.ssl_no_verify:
            return ldap3.Tls(validate=ssl.CERT_NONE)

        # Custom CA certificate mode (recommended for self-signed)
        if self.ssl_ca_cert or self.ssl_ca_path:
            tls_kwargs = {'validate': ssl.CERT_REQUIRED}
            if self.ssl_ca_cert:
                tls_kwargs['ca_certs_file'] = self.ssl_ca_cert
            if self.ssl_ca_path:
                tls_kwargs['ca_certs_path'] = self.ssl_ca_path
            return ldap3.Tls(**tls_kwargs)

        # Default mode (system certificate store)
        return ldap3.Tls(validate=ssl.CERT_REQUIRED)

    def test_connection(self):
        """Test LDAP connectivity and authentication.

        Returns:
            dict: {
                'success': bool,
                'message': str,
                'server_info': dict (if success),
                'error': str (if failed),
                'suggestion': str (optional, for certificate errors)
            }
        """
        # Log SSL configuration
        if self.use_ssl:
            logging.info('SSL/TLS enabled')
            if self.ssl_no_verify:
                logging.info('Certificate verification: DISABLED (insecure)')
            elif self.ssl_ca_cert or self.ssl_ca_path:
                logging.info('Certificate verification: Custom CA')
                if self.ssl_ca_cert:
                    logging.info(f'  CA cert file: {self.ssl_ca_cert}')
                if self.ssl_ca_path:
                    logging.info(f'  CA cert path: {self.ssl_ca_path}')
            else:
                logging.info('Certificate verification: System certificate store')

        try:
            # Create TLS configuration
            tls_config = self._create_tls_config()

            logging.debug(f'Creating LDAP server connection to {self.server}:{self.port}')
            logging.debug(f'SSL enabled: {self.use_ssl}, TLS config: {tls_config}')

            self.ldap_server = ldap3.Server(
                self.server,
                port=self.port,
                use_ssl=self.use_ssl,
                tls=tls_config,
                get_info=ldap3.ALL,
                connect_timeout=10
            )

            logging.debug('Server object created, attempting connection...')

            conn = ldap3.Connection(
                self.ldap_server,
                user=self.bind_dn,
                password=self.password,
                auto_bind=True
            )

            server_info = {
                'vendor': str(conn.server.info.vendor_name) if conn.server.info.vendor_name else 'Unknown',
                'version': str(conn.server.info.vendor_version) if conn.server.info.vendor_version else 'Unknown',
                'naming_contexts': [str(nc) for nc in conn.server.info.naming_contexts] if conn.server.info.naming_contexts else []
            }

            conn.unbind()

            return {
                'success': True,
                'message': 'Connection successful',
                'server_info': server_info
            }

        except ldap3.core.exceptions.LDAPBindError as e:
            return {
                'success': False,
                'message': 'Authentication failed',
                'error': str(e)
            }
        except ldap3.core.exceptions.LDAPSocketOpenError as e:
            error_str = str(e).lower()
            result = {
                'success': False,
                'message': 'Cannot connect to server',
                'error': str(e)
            }

            # Detect SSL/certificate errors
            if self.use_ssl and any(keyword in error_str for keyword in ['ssl', 'certificate', 'cert', 'verify', 'tls']):
                result['suggestion'] = (
                    'SSL certificate error detected. Try one of these options:\n'
                    '  1. Skip verification (testing only): --ssl-no-verify\n'
                    '  2. Use custom CA cert (recommended): --ssl-ca-cert path/to/ca-cert.pem\n'
                    '  3. Use system cert store (default): ensure server has valid certificate'
                )

            return result
        except Exception as e:
            return {
                'success': False,
                'message': 'Connection failed',
                'error': str(e)
            }

    def connect(self):
        """Establish and return LDAP connection.

        Returns:
            ldap3.Connection: Active LDAP connection
        """
        if not self.ldap_server:
            # Create TLS configuration
            tls_config = self._create_tls_config()

            self.ldap_server = ldap3.Server(
                self.server,
                port=self.port,
                use_ssl=self.use_ssl,
                tls=tls_config,
                get_info=ldap3.ALL
            )

        self.connection = ldap3.Connection(
            self.ldap_server,
            user=self.bind_dn,
            password=self.password,
            auto_bind=True
        )

        return self.connection

    def disconnect(self):
        """Close LDAP connection."""
        if self.connection:
            self.connection.unbind()
            self.connection = None

    def create_ou(self, ou_dn):
        """Create an organizational unit if it doesn't already exist.

        Args:
            ou_dn: Full DN of the OU (e.g., ou=Groups,dc=ldap1test,dc=loc)

        Returns:
            dict: {'success': bool, 'action': str, 'message': str}
        """
        if not self.connection:
            self.connect()

        # Check if already exists
        if self.verify_ou_exists(ou_dn):
            logging.info(f'OU already exists: {ou_dn}')
            return {'success': True, 'action': 'exists', 'message': 'OU already exists'}

        # Extract OU name from DN
        ou_name = ou_dn.split(',')[0].split('=')[1]

        try:
            success = self.connection.add(
                ou_dn,
                attributes={
                    'objectClass': ['top', 'organizationalUnit'],
                    'ou': ou_name
                }
            )

            if success:
                logging.info(f'Created OU: {ou_dn}')
                return {'success': True, 'action': 'created', 'message': f'OU created: {ou_dn}'}
            else:
                error_msg = self.connection.result.get('description', 'Unknown error')
                # entryAlreadyExists means the OU (or a container with that DN) is already there
                if 'AlreadyExists' in error_msg or self.connection.result.get('result', 0) == 68:
                    logging.info(f'OU already exists: {ou_dn}')
                    return {'success': True, 'action': 'exists', 'message': 'OU already exists'}
                logging.error(f'Failed to create OU {ou_dn}: {error_msg}')
                return {'success': False, 'action': 'error', 'message': error_msg}

        except Exception as e:
            logging.error(f'Exception creating OU {ou_dn}: {e}')
            return {'success': False, 'action': 'error', 'message': str(e)}

    def verify_ou_exists(self, ou_dn):
        """Verify organizational unit or container exists.

        Checks for any object at the given DN (OU, container, or other).
        AD has built-in containers (cn=Users) that aren't organizationalUnits
        but can still hold user/group objects.

        Args:
            ou_dn: DN of the organizational unit or container

        Returns:
            bool: True if an entry exists at this DN
        """
        if not self.connection:
            self.connect()

        try:
            result = self.connection.search(
                search_base=ou_dn,
                search_filter='(objectClass=*)',
                search_scope=ldap3.BASE
            )
            return result
        except Exception as e:
            logging.debug(f'Error verifying OU {ou_dn}: {e}')
            return False


# ============================================================================
# CSV Importer
# ============================================================================

class CSVImporter:
    """Reads and validates CSV files, maps to LDAP attributes."""

    def __init__(self, csv_file):
        """Initialize with CSV file path.

        Args:
            csv_file: Path to CSV file
        """
        self.csv_file = csv_file
        self.data = []

    def validate_csv(self, expected_columns):
        """Validate CSV has required columns.

        Args:
            expected_columns: List of required column names

        Returns:
            dict: {'valid': bool, 'error': str (if invalid)}
        """
        try:
            with open(self.csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                columns = reader.fieldnames

                if not columns:
                    return {
                        'valid': False,
                        'error': 'CSV file is empty or has no headers'
                    }

                missing = [col for col in expected_columns if col not in columns]
                if missing:
                    return {
                        'valid': False,
                        'error': f'Missing columns: {", ".join(missing)}'
                    }

                return {'valid': True}
        except Exception as e:
            return {
                'valid': False,
                'error': f'Error reading CSV: {str(e)}'
            }

    def read_groups(self):
        """Read groups from UserGroups.csv.

        Returns:
            list: List of group dictionaries
        """
        groups = []
        with open(self.csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                groups.append({
                    'GROUP_ID': int(row['GROUP_ID']),
                    'GROUPNAME': row['GROUPNAME'].strip(),
                    'DESCRIPTION': row.get('DESCRIPTION', '').strip(),
                    'FLAGS': int(row.get('FLAGS', 0))
                })
        return groups

    def read_users(self):
        """Read users from Users.csv.

        Returns:
            list: List of user dictionaries
        """
        users = []
        with open(self.csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                users.append({
                    'USER_ID': int(row['USER_ID']),
                    'USERNAME': row['USERNAME'].strip(),
                    'PASSWORD': row.get('PASSWORD', ''),
                    'FULLNAME': row.get('FULLNAME', '').strip(),
                    'DESCRIPTION': row.get('DESCRIPTION', '').strip(),
                    'FLAGS': int(row.get('FLAGS', 0))
                })
        return users

    def map_group_to_ldap(self, group_row, groups_ou):
        """Map CSV group to LDAP entry.

        Args:
            group_row: Group dictionary from CSV
            groups_ou: Groups OU DN

        Returns:
            dict: {'dn': str, 'attributes': dict}
        """
        cn = group_row['GROUPNAME']
        dn = f"cn={cn},{groups_ou}"

        # Extract original ID and ensure it's in description
        description = group_row['DESCRIPTION'] if group_row['DESCRIPTION'] else cn
        original_id = group_row['GROUP_ID']

        # If description doesn't contain [OriginalID:], add it
        if '[OriginalID:' not in description:
            description = f"{description} [OriginalID:{original_id}]"

        return {
            'dn': dn,
            'attributes': {
                'objectClass': ['top', 'group'],
                'cn': cn,
                'sAMAccountName': cn,
                'description': description,
                'groupType': -2147483646  # Global security group
            }
        }

    def map_user_to_ldap(self, user_row, users_ou, password_strategy='use-csv', default_password=None):
        """Map CSV user to LDAP entry.

        Args:
            user_row: User dictionary from CSV
            users_ou: Users OU DN
            password_strategy: Password strategy (use-csv, default, skip, random)
            default_password: Default password if strategy is 'default'

        Returns:
            dict: {'dn': str, 'username': str, 'attributes': dict}
        """
        username = user_row['USERNAME']
        cn = username
        dn = f"cn={cn},{users_ou}"

        attributes = {
            'objectClass': ['top', 'person', 'organizationalPerson', 'user'],
            'cn': cn,
            'sAMAccountName': username,
            'userPrincipalName': f"{username}@ocbc.com",
            'displayName': user_row.get('FULLNAME', username) if user_row.get('FULLNAME') else username,
            'description': user_row.get('DESCRIPTION', '') if user_row.get('DESCRIPTION') else f'User {username}',
            'employeeID': str(user_row['USER_ID']),
        }

        # Handle password based on strategy
        password_to_encode = None
        if password_strategy == 'use-csv' and user_row.get('PASSWORD'):
            # CSV password is binary blob - cannot use directly
            # Log warning and skip password
            logging.warning(f'User {username}: CSV password is binary blob, skipping password (use --password-strategy default or random)')
        elif password_strategy == 'default' and default_password:
            password_to_encode = default_password
        elif password_strategy == 'random':
            password_to_encode = self._generate_random_password()
        # 'skip' strategy: don't set password

        if password_to_encode:
            attributes['unicodePwd'] = self._encode_password_for_ad(password_to_encode)
            attributes['userAccountControl'] = 512  # Normal account, enabled
        else:
            # AD requires a password for enabled accounts; create as disabled
            attributes['userAccountControl'] = 514  # Normal account, disabled

        return {
            'dn': dn,
            'username': username,
            'attributes': attributes,
            'password': password_to_encode if password_strategy == 'random' else None
        }

    def _encode_password_for_ad(self, password):
        """Encode password for AD unicodePwd attribute.

        AD requires:
        1. Password enclosed in double quotes
        2. Encoded as UTF-16LE
        3. SSL connection required (port 636)

        Args:
            password: Plain text password

        Returns:
            bytes: Encoded password for AD
        """
        password_with_quotes = f'"{password}"'
        return password_with_quotes.encode('utf-16-le')

    def _generate_random_password(self, length=12):
        """Generate random password.

        Args:
            length: Password length (default: 12)

        Returns:
            str: Random password
        """
        alphabet = string.ascii_letters + string.digits + '!@#$%^&*()'
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        return password

    def read_user_group_assignments(self):
        """Read user-group assignments from UserGroupAssignments.csv.

        Returns:
            list: List of assignment dictionaries with USER_ID and GROUP_ID
        """
        assignments = []
        with open(self.csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                assignments.append({
                    'USER_ID': int(row['USER_ID']),
                    'GROUP_ID': int(row['GROUP_ID']),
                    'SECURITYDOMAIN_ID': int(row.get('SECURITYDOMAIN_ID', 1)),
                    'FLAGS': int(row.get('FLAGS', 0))
                })
        return assignments


# ============================================================================
# LDAP Group Manager
# ============================================================================

class LDAPGroupManager:
    """Creates groups in Active Directory."""

    def __init__(self, conn_manager, groups_ou):
        """Initialize with connection manager and groups OU.

        Args:
            conn_manager: LDAPConnectionManager instance
            groups_ou: Groups OU DN
        """
        self.conn_manager = conn_manager
        self.groups_ou = groups_ou
        self.stats = {
            'total': 0,
            'created': 0,
            'skipped': 0,
            'errors': 0
        }

    def add_group(self, group_data, dry_run=False, continue_on_error=True):
        """Add single group to AD.

        Args:
            group_data: Group data dict with 'dn' and 'attributes'
            dry_run: Preview without executing
            continue_on_error: Continue if error occurs

        Returns:
            dict: Result with 'success', 'action', 'dn', and optional 'error'
        """
        cn = group_data['attributes']['cn']
        dn = group_data['dn']

        # Check if already exists
        if self.group_exists(cn):
            logging.warning(f'Group already exists: {cn}')
            return {
                'success': False,
                'action': 'skipped',
                'dn': dn,
                'message': 'Group already exists'
            }

        if dry_run:
            logging.info(f'[DRY-RUN] Would create group: {cn}')
            logging.debug(f'[DRY-RUN]   DN: {dn}')
            logging.debug(f'[DRY-RUN]   Attributes: {group_data["attributes"]}')
            return {
                'success': True,
                'action': 'would_create',
                'dn': dn,
                'message': 'Dry-run mode'
            }

        try:
            conn = self.conn_manager.connection
            if not conn:
                conn = self.conn_manager.connect()

            success = conn.add(dn, attributes=group_data['attributes'])

            if success:
                logging.info(f'Created group: {cn}')
                return {
                    'success': True,
                    'action': 'created',
                    'dn': dn,
                    'message': 'Group created successfully'
                }
            else:
                error_msg = conn.result.get('description', 'Unknown error')
                # Treat "already exists" as a skip (e.g., built-in groups like Domain Users)
                if 'AlreadyExists' in error_msg or conn.result.get('result', 0) == 68:
                    logging.warning(f'Group already exists (AD built-in): {cn}')
                    return {
                        'success': False,
                        'action': 'skipped',
                        'dn': dn,
                        'message': 'Group already exists in AD'
                    }
                logging.error(f'Failed to create group {cn}: {error_msg}')
                return {
                    'success': False,
                    'action': 'error',
                    'dn': dn,
                    'error': error_msg
                }

        except Exception as e:
            logging.error(f'Exception creating group {cn}: {e}')
            return {
                'success': False,
                'action': 'error',
                'dn': dn,
                'error': str(e)
            }

    def add_groups_from_csv(self, csv_file, dry_run=False, continue_on_error=True):
        """Bulk add groups from CSV.

        Args:
            csv_file: Path to UserGroups.csv
            dry_run: Preview without executing
            continue_on_error: Continue if entry fails

        Returns:
            dict: {'stats': dict, 'results': list} or None if validation fails
        """
        importer = CSVImporter(csv_file)

        # Validate CSV
        validation = importer.validate_csv(['GROUP_ID', 'GROUPNAME'])
        if not validation['valid']:
            logging.error(f'CSV validation failed: {validation["error"]}')
            return None

        # Read groups
        groups = importer.read_groups()
        self.stats['total'] = len(groups)

        logging.info(f'Processing {len(groups)} groups...')

        results = []
        for group_row in groups:
            group_data = importer.map_group_to_ldap(group_row, self.groups_ou)
            result = self.add_group(group_data, dry_run=dry_run, continue_on_error=continue_on_error)

            # Update stats
            if result['action'] in ('created', 'would_create'):
                self.stats['created'] += 1
            elif result['action'] == 'skipped':
                self.stats['skipped'] += 1
            elif result['action'] == 'error':
                self.stats['errors'] += 1
                if not continue_on_error:
                    logging.error('Stopping due to error (continue-on-error disabled)')
                    break

            results.append(result)

        return {
            'stats': self.stats,
            'results': results
        }

    def group_exists(self, cn):
        """Check if group exists.

        Args:
            cn: Group CN

        Returns:
            bool: True if group exists
        """
        conn = self.conn_manager.connection
        if not conn:
            conn = self.conn_manager.connect()

        search_filter = f'(&(objectClass=group)(cn={cn}))'
        try:
            result = conn.search(
                search_base=self.groups_ou,
                search_filter=search_filter,
                search_scope=ldap3.SUBTREE
            )
            return result and len(conn.entries) > 0
        except Exception as e:
            logging.debug(f'Error checking if group exists: {e}')
            return False


# ============================================================================
# LDAP User Manager
# ============================================================================

class LDAPUserManager:
    """Creates users in Active Directory."""

    def __init__(self, conn_manager, users_ou, password_strategy='use-csv', default_password=None):
        """Initialize with connection manager and users OU.

        Args:
            conn_manager: LDAPConnectionManager instance
            users_ou: Users OU DN
            password_strategy: Password strategy (use-csv, default, skip, random)
            default_password: Default password if strategy is 'default'
        """
        self.conn_manager = conn_manager
        self.users_ou = users_ou
        self.password_strategy = password_strategy
        self.default_password = default_password
        self.stats = {
            'total': 0,
            'created': 0,
            'skipped': 0,
            'errors': 0,
            'passwords_set': 0
        }
        self.random_passwords = []  # Store random passwords for export

        # Warn if password strategy requires SSL
        if password_strategy != 'skip' and not conn_manager.use_ssl:
            logging.warning('Password operations require SSL connection (port 636)')
            logging.warning('Passwords will not be set without SSL')

    def add_user(self, user_data, dry_run=False, continue_on_error=True):
        """Add single user to AD.

        Args:
            user_data: User data dict with 'dn', 'username', 'attributes'
            dry_run: Preview without executing
            continue_on_error: Continue if error occurs

        Returns:
            dict: Result with 'success', 'action', 'dn', 'username', and optional 'error'
        """
        username = user_data['username']
        dn = user_data['dn']

        # Check if already exists
        if self.user_exists(username):
            logging.warning(f'User already exists: {username}')
            return {
                'success': False,
                'action': 'skipped',
                'dn': dn,
                'username': username,
                'message': 'User already exists'
            }

        if dry_run:
            logging.info(f'[DRY-RUN] Would create user: {username}')
            logging.debug(f'[DRY-RUN]   DN: {dn}')
            logging.debug(f'[DRY-RUN]   Attributes: {user_data["attributes"]}')
            return {
                'success': True,
                'action': 'would_create',
                'dn': dn,
                'username': username,
                'message': 'Dry-run mode'
            }

        try:
            conn = self.conn_manager.connection
            if not conn:
                conn = self.conn_manager.connect()

            success = conn.add(dn, attributes=user_data['attributes'])

            if success:
                password_set = 'unicodePwd' in user_data['attributes']
                logging.info(f'Created user: {username} (password set: {password_set})')

                if password_set:
                    self.stats['passwords_set'] += 1

                # Store random password if applicable
                if user_data.get('password'):
                    self.random_passwords.append({
                        'username': username,
                        'password': user_data['password']
                    })

                return {
                    'success': True,
                    'action': 'created',
                    'dn': dn,
                    'username': username,
                    'password_set': password_set,
                    'message': 'User created successfully'
                }
            else:
                error_msg = conn.result.get('description', 'Unknown error')
                if 'AlreadyExists' in error_msg or conn.result.get('result', 0) == 68:
                    logging.warning(f'User already exists (AD): {username}')
                    return {
                        'success': False,
                        'action': 'skipped',
                        'dn': dn,
                        'username': username,
                        'message': 'User already exists in AD'
                    }
                logging.error(f'Failed to create user {username}: {error_msg}')
                return {
                    'success': False,
                    'action': 'error',
                    'dn': dn,
                    'username': username,
                    'error': error_msg
                }

        except Exception as e:
            logging.error(f'Exception creating user {username}: {e}')
            return {
                'success': False,
                'action': 'error',
                'dn': dn,
                'username': username,
                'error': str(e)
            }

    def add_users_from_csv(self, csv_file, dry_run=False, continue_on_error=True):
        """Bulk add users from CSV.

        Args:
            csv_file: Path to Users.csv
            dry_run: Preview without executing
            continue_on_error: Continue if entry fails

        Returns:
            dict: {'stats': dict, 'results': list} or None if validation fails
        """
        importer = CSVImporter(csv_file)

        # Validate CSV
        validation = importer.validate_csv(['USER_ID', 'USERNAME'])
        if not validation['valid']:
            logging.error(f'CSV validation failed: {validation["error"]}')
            return None

        # Read users
        users = importer.read_users()
        self.stats['total'] = len(users)

        logging.info(f'Processing {len(users)} users...')

        results = []
        for user_row in users:
            user_data = importer.map_user_to_ldap(
                user_row,
                self.users_ou,
                self.password_strategy,
                self.default_password
            )
            result = self.add_user(user_data, dry_run=dry_run, continue_on_error=continue_on_error)

            # Update stats
            if result['action'] in ('created', 'would_create'):
                self.stats['created'] += 1
            elif result['action'] == 'skipped':
                self.stats['skipped'] += 1
            elif result['action'] == 'error':
                self.stats['errors'] += 1
                if not continue_on_error:
                    logging.error('Stopping due to error (continue-on-error disabled)')
                    break

            results.append(result)

        # Export random passwords if applicable
        if self.random_passwords and not dry_run:
            self._export_random_passwords()

        return {
            'stats': self.stats,
            'results': results
        }

    def user_exists(self, sam_account_name):
        """Check if user exists.

        Args:
            sam_account_name: User sAMAccountName

        Returns:
            bool: True if user exists
        """
        conn = self.conn_manager.connection
        if not conn:
            conn = self.conn_manager.connect()

        search_filter = f'(&(objectClass=user)(sAMAccountName={sam_account_name}))'
        try:
            result = conn.search(
                search_base=self.users_ou,
                search_filter=search_filter,
                search_scope=ldap3.SUBTREE
            )
            return result and len(conn.entries) > 0
        except Exception as e:
            logging.debug(f'Error checking if user exists: {e}')
            return False

    def _export_random_passwords(self):
        """Export random passwords to CSV file."""
        if not self.random_passwords:
            return

        output_file = 'random_passwords.csv'
        logging.info(f'Exporting {len(self.random_passwords)} random passwords to {output_file}')

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['username', 'password'])
            writer.writeheader()
            writer.writerows(self.random_passwords)

        logging.info(f'Random passwords exported to {output_file}')


# ============================================================================
# LDAP Group Membership Manager
# ============================================================================

class LDAPGroupMembershipManager:
    """Manages user-group membership assignments in Active Directory."""

    def __init__(self, conn_manager, groups_ou, users_ou, users_csv, groups_csv):
        """Initialize with connection manager and OUs.

        Args:
            conn_manager: LDAPConnectionManager instance
            groups_ou: Groups OU DN
            users_ou: Users OU DN
            users_csv: Path to Users.csv (for USER_ID to USERNAME mapping)
            groups_csv: Path to UserGroups.csv (for GROUP_ID to GROUPNAME mapping)
        """
        self.conn_manager = conn_manager
        self.groups_ou = groups_ou
        self.users_ou = users_ou
        self.users_csv = users_csv
        self.groups_csv = groups_csv
        self.stats = {
            'total': 0,
            'assigned': 0,
            'skipped': 0,
            'errors': 0
        }

        # Build ID to name mappings
        self.user_id_to_username = {}
        self.group_id_to_groupname = {}
        self._build_id_mappings()

    def _build_id_mappings(self):
        """Build USER_ID → USERNAME and GROUP_ID → GROUPNAME mappings."""
        # Read Users.csv
        logging.info('Building USER_ID to USERNAME mapping...')
        importer = CSVImporter(self.users_csv)
        users = importer.read_users()
        for user in users:
            self.user_id_to_username[user['USER_ID']] = user['USERNAME']
        logging.debug(f'Mapped {len(self.user_id_to_username)} users')

        # Read UserGroups.csv
        logging.info('Building GROUP_ID to GROUPNAME mapping...')
        importer = CSVImporter(self.groups_csv)
        groups = importer.read_groups()
        for group in groups:
            self.group_id_to_groupname[group['GROUP_ID']] = group['GROUPNAME']
        logging.debug(f'Mapped {len(self.group_id_to_groupname)} groups')

    def assign_user_to_group(self, user_id, group_id, dry_run=False):
        """Assign single user to a group.

        Args:
            user_id: User ID from CSV
            group_id: Group ID from CSV
            dry_run: Preview without executing

        Returns:
            dict: Result with 'success', 'action', and optional 'error'
        """
        # Map IDs to names
        username = self.user_id_to_username.get(user_id)
        groupname = self.group_id_to_groupname.get(group_id)

        if not username:
            logging.warning(f'USER_ID {user_id} not found in Users.csv')
            return {
                'success': False,
                'action': 'error',
                'error': f'USER_ID {user_id} not found',
                'user_id': user_id,
                'group_id': group_id
            }

        if not groupname:
            logging.warning(f'GROUP_ID {group_id} not found in UserGroups.csv')
            return {
                'success': False,
                'action': 'error',
                'error': f'GROUP_ID {group_id} not found',
                'user_id': user_id,
                'group_id': group_id
            }

        # Build DNs
        user_dn = f"cn={username},{self.users_ou}"
        group_dn = f"cn={groupname},{self.groups_ou}"

        # Check if user is already in group
        if self._user_in_group(user_dn, group_dn):
            logging.debug(f'User {username} already in group {groupname}')
            return {
                'success': False,
                'action': 'skipped',
                'user_id': user_id,
                'group_id': group_id,
                'username': username,
                'groupname': groupname,
                'message': 'User already in group'
            }

        if dry_run:
            logging.info(f'[DRY-RUN] Would add {username} to group {groupname}')
            return {
                'success': True,
                'action': 'would_assign',
                'user_id': user_id,
                'group_id': group_id,
                'username': username,
                'groupname': groupname,
                'message': 'Dry-run mode'
            }

        try:
            conn = self.conn_manager.connection
            if not conn:
                conn = self.conn_manager.connect()

            # Add user to group by modifying group's member attribute
            success = conn.modify(
                group_dn,
                {'member': [(ldap3.MODIFY_ADD, [user_dn])]}
            )

            if success:
                logging.info(f'Added {username} to group {groupname}')
                return {
                    'success': True,
                    'action': 'assigned',
                    'user_id': user_id,
                    'group_id': group_id,
                    'username': username,
                    'groupname': groupname,
                    'message': 'User assigned to group successfully'
                }
            else:
                error_msg = conn.result.get('description', 'Unknown error')
                if 'AlreadyExists' in error_msg or conn.result.get('result', 0) == 68:
                    logging.debug(f'User {username} already in group {groupname}')
                    return {
                        'success': False,
                        'action': 'skipped',
                        'user_id': user_id,
                        'group_id': group_id,
                        'username': username,
                        'groupname': groupname,
                        'message': 'User already in group'
                    }
                logging.error(f'Failed to add {username} to group {groupname}: {error_msg}')
                return {
                    'success': False,
                    'action': 'error',
                    'user_id': user_id,
                    'group_id': group_id,
                    'username': username,
                    'groupname': groupname,
                    'error': error_msg
                }

        except Exception as e:
            logging.error(f'Exception adding {username} to group {groupname}: {e}')
            return {
                'success': False,
                'action': 'error',
                'user_id': user_id,
                'group_id': group_id,
                'username': username,
                'groupname': groupname,
                'error': str(e)
            }

    def _user_in_group(self, user_dn, group_dn):
        """Check if user is already in group.

        Args:
            user_dn: User DN
            group_dn: Group DN

        Returns:
            bool: True if user is already a member
        """
        conn = self.conn_manager.connection
        if not conn:
            conn = self.conn_manager.connect()

        try:
            result = conn.search(
                search_base=group_dn,
                search_filter='(objectClass=group)',
                search_scope=ldap3.BASE,
                attributes=['member']
            )

            if result and len(conn.entries) > 0:
                group_entry = conn.entries[0]
                members = group_entry.member.values if hasattr(group_entry, 'member') else []
                return user_dn in members

            return False
        except Exception as e:
            logging.debug(f'Error checking group membership: {e}')
            return False

    def assign_from_csv(self, csv_file, dry_run=False, continue_on_error=True):
        """Bulk assign users to groups from CSV.

        Args:
            csv_file: Path to UserGroupAssignments.csv
            dry_run: Preview without executing
            continue_on_error: Continue if assignment fails

        Returns:
            dict: {'stats': dict, 'results': list} or None if validation fails
        """
        importer = CSVImporter(csv_file)

        # Validate CSV
        validation = importer.validate_csv(['USER_ID', 'GROUP_ID'])
        if not validation['valid']:
            logging.error(f'CSV validation failed: {validation["error"]}')
            return None

        # Read assignments
        assignments = importer.read_user_group_assignments()
        self.stats['total'] = len(assignments)

        logging.info(f'Processing {len(assignments)} user-group assignments...')

        results = []
        for assignment in assignments:
            result = self.assign_user_to_group(
                assignment['USER_ID'],
                assignment['GROUP_ID'],
                dry_run=dry_run
            )

            # Update stats
            if result['action'] in ('assigned', 'would_assign'):
                self.stats['assigned'] += 1
            elif result['action'] == 'skipped':
                self.stats['skipped'] += 1
            elif result['action'] == 'error':
                self.stats['errors'] += 1
                if not continue_on_error:
                    logging.error('Stopping due to error (continue-on-error disabled)')
                    break

            results.append(result)

        return {
            'stats': self.stats,
            'results': results
        }


# ============================================================================
# LDAP Search Manager
# ============================================================================

class LDAPSearchManager:
    """Searches and browses LDAP directory."""

    def __init__(self, conn_manager, base_dn):
        """Initialize with connection manager and base DN.

        Args:
            conn_manager: LDAPConnectionManager instance
            base_dn: Base DN for searches
        """
        self.conn_manager = conn_manager
        self.base_dn = base_dn

    def search(self, filter_str, attributes=None, scope=ldap3.SUBTREE, base_dn=None):
        """Generic LDAP search.

        Args:
            filter_str: LDAP filter string
            attributes: List of attributes to retrieve
            scope: Search scope
            base_dn: Base DN for search (uses default if None)

        Returns:
            list: List of entry dictionaries
        """
        conn = self.conn_manager.connection
        if not conn:
            conn = self.conn_manager.connect()

        search_base = base_dn or self.base_dn

        try:
            result = conn.search(
                search_base=search_base,
                search_filter=filter_str,
                search_scope=scope,
                attributes=attributes or ldap3.ALL_ATTRIBUTES
            )

            if result:
                entries = []
                for entry in conn.entries:
                    entries.append({
                        'dn': entry.entry_dn,
                        'attributes': entry.entry_attributes_as_dict
                    })
                return entries

            return []
        except Exception as e:
            logging.error(f'Search error: {e}')
            return []

    def search_users(self, username_filter=None):
        """Search for users.

        Args:
            username_filter: Username pattern to filter (None for all)

        Returns:
            list: List of user entries
        """
        if username_filter:
            filter_str = f'(&(objectClass=user)(cn=*{username_filter}*))'
        else:
            filter_str = '(objectClass=user)'

        return self.search(filter_str)

    def search_groups(self, groupname_filter=None):
        """Search for groups.

        Args:
            groupname_filter: Groupname pattern to filter (None for all)

        Returns:
            list: List of group entries
        """
        if groupname_filter:
            filter_str = f'(&(objectClass=group)(cn=*{groupname_filter}*))'
        else:
            filter_str = '(objectClass=group)'

        return self.search(filter_str)

    def get_tree_structure(self, base_dn=None):
        """Get LDAP tree structure for browser.

        Args:
            base_dn: Base DN for tree (uses default if None)

        Returns:
            list: List of OU entries
        """
        filter_str = '(objectClass=organizationalUnit)'
        ous = self.search(filter_str, base_dn=base_dn)

        tree = []
        for ou in ous:
            ou_name = ou['attributes'].get('ou', ['Unknown'])[0] if isinstance(ou['attributes'].get('ou'), list) else ou['attributes'].get('ou', 'Unknown')
            tree.append({
                'dn': ou['dn'],
                'name': ou_name,
                'type': 'ou'
            })

        return tree


# ============================================================================
# LDAP Browser API (Flask)
# ============================================================================

class LDAPBrowserAPI:
    """HTTP API for standalone HTML browser."""

    def __init__(self, conn_manager, search_manager):
        """Initialize with connection and search managers.

        Args:
            conn_manager: LDAPConnectionManager instance
            search_manager: LDAPSearchManager instance
        """
        self.conn_manager = conn_manager
        self.search_manager = search_manager
        self.app = Flask(__name__)
        CORS(self.app)

        self._register_routes()

    def _register_routes(self):
        """Register Flask routes."""

        @self.app.route('/')
        def serve_browser():
            """Serve the LDAP browser HTML page."""
            return send_from_directory(
                os.path.dirname(os.path.abspath(__file__)),
                'ldap_browser.html'
            )

        @self.app.route('/api/health', methods=['GET'])
        def health():
            """Health check and connection status."""
            try:
                result = self.conn_manager.test_connection()
                return jsonify({
                    'connected': result['success'],
                    'message': result['message']
                })
            except Exception as e:
                return jsonify({
                    'connected': False,
                    'message': str(e)
                }), 500

        @self.app.route('/api/tree', methods=['GET'])
        def get_tree():
            """Get LDAP tree structure."""
            try:
                base_dn = request.args.get('base_dn', self.search_manager.base_dn)
                tree = self.search_manager.get_tree_structure(base_dn)
                return jsonify(tree)
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/search', methods=['GET'])
        def search():
            """Search LDAP directory."""
            try:
                query = request.args.get('q', '')
                search_type = request.args.get('type', 'all')

                if search_type == 'user':
                    results = self.search_manager.search_users(query)
                elif search_type == 'group':
                    results = self.search_manager.search_groups(query)
                else:
                    # Search both
                    users = self.search_manager.search_users(query)
                    groups = self.search_manager.search_groups(query)
                    results = users + groups

                return jsonify(results)
            except Exception as e:
                return jsonify({'error': str(e)}), 500

        @self.app.route('/api/entry/<path:dn>', methods=['GET'])
        def get_entry(dn):
            """Get entry details by DN."""
            try:
                results = self.search_manager.search(
                    f'(distinguishedName={dn})',
                    scope=ldap3.BASE
                )

                if results:
                    return jsonify(results[0])
                else:
                    return jsonify({'error': 'Entry not found'}), 404
            except Exception as e:
                return jsonify({'error': str(e)}), 500

    def run(self, host='127.0.0.1', port=5000):
        """Start Flask server.

        Args:
            host: API host
            port: API port
        """
        logging.info(f'Starting LDAP Browser API on {host}:{port}')
        logging.info('Open ldap_browser.html in your browser')
        self.app.run(host=host, port=port, debug=False)


# ============================================================================
# Command Implementations
# ============================================================================

def cmd_test_connection(args):
    """Test connection command."""
    logging.info('Testing LDAP connection...')

    conn_mgr = LDAPConnectionManager(
        server=args.server,
        port=args.port,
        bind_dn=args.bind_dn,
        password=args.password,
        use_ssl=args.use_ssl,
        base_dn=args.base_dn,
        ssl_no_verify=getattr(args, 'ssl_no_verify', False),
        ssl_ca_cert=getattr(args, 'ssl_ca_cert', None),
        ssl_ca_path=getattr(args, 'ssl_ca_path', None)
    )

    result = conn_mgr.test_connection()

    if result['success']:
        logging.info('Connection successful')
        logging.info(f"Server: {result['server_info']['vendor']}")
        logging.info(f"Version: {result['server_info']['version']}")
        logging.info(f"Naming contexts: {result['server_info']['naming_contexts']}")
        return 0
    else:
        logging.error(f'Connection failed: {result["message"]}')
        logging.error(f'Error: {result["error"]}')
        if 'suggestion' in result:
            logging.error('')
            logging.error(result['suggestion'])
        return 1


def cmd_create_ous(args):
    """Create organizational units in AD."""
    logging.info('Creating organizational units...')

    conn_mgr = LDAPConnectionManager(
        server=args.server,
        port=args.port,
        bind_dn=args.bind_dn,
        password=args.password,
        use_ssl=args.use_ssl,
        base_dn=args.base_dn,
        ssl_no_verify=getattr(args, 'ssl_no_verify', False),
        ssl_ca_cert=getattr(args, 'ssl_ca_cert', None),
        ssl_ca_path=getattr(args, 'ssl_ca_path', None)
    )

    result = conn_mgr.test_connection()
    if not result['success']:
        logging.error(f'Connection failed: {result["message"]}')
        return 1

    conn_mgr.connect()

    ou_list = []
    if hasattr(args, 'groups_ou') and args.groups_ou:
        ou_list.append(args.groups_ou)
    if hasattr(args, 'users_ou') and args.users_ou:
        ou_list.append(args.users_ou)

    if not ou_list:
        logging.error('No OUs specified. Use --groups-ou and/or --users-ou.')
        return 1

    errors = 0
    for ou_dn in ou_list:
        result = conn_mgr.create_ou(ou_dn)
        if not result['success']:
            errors += 1

    conn_mgr.disconnect()

    logging.info('=' * 70)
    logging.info('OU CREATION COMPLETE')
    logging.info(f'OUs processed: {len(ou_list)}')
    logging.info(f'Errors: {errors}')
    logging.info('=' * 70)

    return 0 if errors == 0 else 1


def cmd_add_groups(args):
    """Add groups command."""
    logging.info('Adding groups from CSV...')

    # Create connection manager
    conn_mgr = LDAPConnectionManager(
        server=args.server,
        port=args.port,
        bind_dn=args.bind_dn,
        password=args.password,
        use_ssl=args.use_ssl,
        base_dn=args.base_dn,
        ssl_no_verify=getattr(args, 'ssl_no_verify', False),
        ssl_ca_cert=getattr(args, 'ssl_ca_cert', None),
        ssl_ca_path=getattr(args, 'ssl_ca_path', None)
    )

    # Test connection
    result = conn_mgr.test_connection()
    if not result['success']:
        logging.error(f'Connection failed: {result["message"]}')
        return 1

    # Connect
    conn_mgr.connect()

    # Verify groups OU exists
    if not conn_mgr.verify_ou_exists(args.groups_ou):
        logging.error(f'Groups OU does not exist: {args.groups_ou}')
        return 1

    # Create group manager
    group_mgr = LDAPGroupManager(conn_mgr, args.groups_ou)

    # Add groups
    result = group_mgr.add_groups_from_csv(
        args.csv,
        dry_run=args.dry_run,
        continue_on_error=getattr(args, 'continue_on_error', True)
    )

    if result is None:
        return 1

    # Print summary
    stats = result['stats']
    logging.info('='*70)
    if args.dry_run:
        logging.info('DRY-RUN COMPLETE')
    else:
        logging.info('GROUP IMPORT COMPLETE')
    logging.info(f'Total: {stats["total"]}')
    logging.info(f'Created: {stats["created"]}')
    logging.info(f'Skipped: {stats["skipped"]}')
    logging.info(f'Errors: {stats["errors"]}')
    logging.info('='*70)

    conn_mgr.disconnect()
    return 0 if stats['errors'] == 0 else 1


def cmd_add_users(args):
    """Add users command."""
    logging.info('Adding users from CSV...')

    # Create connection manager
    conn_mgr = LDAPConnectionManager(
        server=args.server,
        port=args.port,
        bind_dn=args.bind_dn,
        password=args.password,
        use_ssl=args.use_ssl,
        base_dn=args.base_dn,
        ssl_no_verify=getattr(args, 'ssl_no_verify', False),
        ssl_ca_cert=getattr(args, 'ssl_ca_cert', None),
        ssl_ca_path=getattr(args, 'ssl_ca_path', None)
    )

    # Test connection
    result = conn_mgr.test_connection()
    if not result['success']:
        logging.error(f'Connection failed: {result["message"]}')
        return 1

    # Connect
    conn_mgr.connect()

    # Verify users OU exists
    if not conn_mgr.verify_ou_exists(args.users_ou):
        logging.error(f'Users OU does not exist: {args.users_ou}')
        return 1

    # Create user manager
    user_mgr = LDAPUserManager(
        conn_mgr,
        args.users_ou,
        password_strategy=args.password_strategy,
        default_password=getattr(args, 'default_password', None)
    )

    # Add users
    result = user_mgr.add_users_from_csv(
        args.csv,
        dry_run=args.dry_run,
        continue_on_error=getattr(args, 'continue_on_error', True)
    )

    if result is None:
        return 1

    # Print summary
    stats = result['stats']
    logging.info('='*70)
    if args.dry_run:
        logging.info('DRY-RUN COMPLETE')
    else:
        logging.info('USER IMPORT COMPLETE')
    logging.info(f'Total: {stats["total"]}')
    logging.info(f'Created: {stats["created"]}')
    logging.info(f'Skipped: {stats["skipped"]}')
    logging.info(f'Errors: {stats["errors"]}')
    logging.info(f'Passwords Set: {stats["passwords_set"]}')
    logging.info('='*70)

    conn_mgr.disconnect()
    return 0 if stats['errors'] == 0 else 1


def cmd_add_all(args):
    """Add all (groups, users, and assignments) command."""
    logging.info('Adding groups, users, and group assignments from CSV...')

    # Phase 1: Add groups first
    logging.info('Phase 1: Adding groups...')
    args.csv = args.groups_csv
    exit_code = cmd_add_groups(args)

    if exit_code != 0:
        logging.error('Group import failed, stopping')
        return exit_code

    # Phase 2: Add users
    logging.info('Phase 2: Adding users...')
    args.csv = args.users_csv
    exit_code = cmd_add_users(args)

    if exit_code != 0:
        logging.error('User import failed, stopping')
        return exit_code

    # Phase 3: Assign users to groups
    if hasattr(args, 'assignments_csv') and args.assignments_csv:
        logging.info('Phase 3: Assigning users to groups...')
        exit_code = cmd_assign_groups(args)

        if exit_code != 0:
            logging.warning('Group assignment had errors (see log for details)')
            # Don't stop - assignments can fail without breaking the import

    return exit_code


def cmd_search(args):
    """Search command."""
    logging.info('Searching LDAP directory...')

    # Create connection manager
    conn_mgr = LDAPConnectionManager(
        server=args.server,
        port=args.port,
        bind_dn=args.bind_dn,
        password=args.password,
        use_ssl=args.use_ssl,
        base_dn=args.base_dn,
        ssl_no_verify=getattr(args, 'ssl_no_verify', False),
        ssl_ca_cert=getattr(args, 'ssl_ca_cert', None),
        ssl_ca_path=getattr(args, 'ssl_ca_path', None)
    )

    # Test connection
    result = conn_mgr.test_connection()
    if not result['success']:
        logging.error(f'Connection failed: {result["message"]}')
        return 1

    # Connect
    conn_mgr.connect()

    # Create search manager
    search_mgr = LDAPSearchManager(conn_mgr, args.base_dn)

    # Parse attributes
    attributes = None
    if hasattr(args, 'attributes') and args.attributes:
        attributes = [attr.strip() for attr in args.attributes.split(',')]

    # Search
    results = search_mgr.search(args.filter, attributes=attributes)

    # Print results
    logging.info(f'Found {len(results)} entries')
    for i, entry in enumerate(results, 1):
        print(f"\n--- Entry {i} ---")
        print(f"DN: {entry['dn']}")
        print("Attributes:")
        for attr, values in entry['attributes'].items():
            if isinstance(values, list):
                for value in values:
                    print(f"  {attr}: {value}")
            else:
                print(f"  {attr}: {values}")

    conn_mgr.disconnect()
    return 0


def cmd_serve_browser(args):
    """Serve browser command."""
    logging.info('Starting LDAP Browser API...')

    # Create connection manager
    conn_mgr = LDAPConnectionManager(
        server=args.server,
        port=args.port,
        bind_dn=args.bind_dn,
        password=args.password,
        use_ssl=args.use_ssl,
        base_dn=args.base_dn,
        ssl_no_verify=getattr(args, 'ssl_no_verify', False),
        ssl_ca_cert=getattr(args, 'ssl_ca_cert', None),
        ssl_ca_path=getattr(args, 'ssl_ca_path', None)
    )

    # Test connection
    result = conn_mgr.test_connection()
    if not result['success']:
        logging.error(f'Connection failed: {result["message"]}')
        return 1

    # Create search manager
    search_mgr = LDAPSearchManager(conn_mgr, args.base_dn)

    # Create and run API
    api = LDAPBrowserAPI(conn_mgr, search_mgr)
    api.run(host=args.api_host, port=args.api_port)

    return 0


def extract_rid_from_sid(sid_value):
    """Extract RID (last component) from SID.

    Handles both binary SID bytes and string SID format (S-1-5-21-...-RID).

    Args:
        sid_value: SID from AD objectSid attribute (bytes or string)

    Returns:
        int: RID (last subauthority of SID)
    """
    import struct

    # Handle string SID format: S-1-5-21-1234-5678-9012-1105
    if isinstance(sid_value, str) and sid_value.startswith('S-'):
        parts = sid_value.split('-')
        return int(parts[-1])

    sid_bytes = sid_value
    if isinstance(sid_bytes, str):
        sid_bytes = sid_bytes.encode('latin-1')

    # Validate minimum SID length (8 bytes header + at least 4 bytes for one subauth)
    if len(sid_bytes) < 12:
        raise ValueError(f'SID too short: {len(sid_bytes)} bytes')

    # SID structure: S-R-I-S-S-S-RID
    # Parse binary: revision(1), subauth_count(1), authority(6), subauths(4*count)
    subauth_count = sid_bytes[1]

    # RID is the last subauthority (4 bytes, little-endian)
    rid_offset = 8 + (subauth_count - 1) * 4
    rid = struct.unpack('<I', sid_bytes[rid_offset:rid_offset+4])[0]

    return rid


def format_sid(sid_value):
    """Convert SID to string format S-1-5-21-...-RID.

    Handles both binary SID bytes and string SID format.

    Args:
        sid_value: SID from AD (bytes or string)

    Returns:
        str: SID in string format
    """
    import struct

    # Already a string SID
    if isinstance(sid_value, str) and sid_value.startswith('S-'):
        return sid_value

    sid_bytes = sid_value
    if isinstance(sid_bytes, str):
        sid_bytes = sid_bytes.encode('latin-1')

    revision = sid_bytes[0]
    subauth_count = sid_bytes[1]
    authority = struct.unpack('>Q', b'\x00\x00' + sid_bytes[2:8])[0]

    sid_parts = [f'S-{revision}-{authority}']

    for i in range(subauth_count):
        offset = 8 + i * 4
        subauth = struct.unpack('<I', sid_bytes[offset:offset+4])[0]
        sid_parts.append(str(subauth))

    return '-'.join(sid_parts)


def extract_original_id_from_description(description):
    """Extract original ID from group description field.

    Args:
        description: Description field like "TEST-1105 [OriginalID:1105]"

    Returns:
        str: Original ID or None
    """
    import re
    match = re.search(r'\[OriginalID:(\d+)\]', description)
    return match.group(1) if match else None


def cmd_export_rid_mapping(args):
    """Export RID mapping after LDAP import.

    Queries AD for all imported users/groups and creates a mapping file:
    Original_ID,Object_Type,Name,AD_SID,AD_RID

    This mapping allows the document management system to translate
    permission CSVs from original RIDs to new AD-assigned RIDs.
    """
    logging.info('Exporting RID mapping from Active Directory...')

    # Create connection manager
    conn_mgr = LDAPConnectionManager(
        server=args.server,
        port=args.port,
        bind_dn=args.bind_dn,
        password=args.password,
        use_ssl=args.use_ssl,
        base_dn=args.base_dn,
        ssl_no_verify=getattr(args, 'ssl_no_verify', False),
        ssl_ca_cert=getattr(args, 'ssl_ca_cert', None),
        ssl_ca_path=getattr(args, 'ssl_ca_path', None)
    )

    # Test connection
    result = conn_mgr.test_connection()
    if not result['success']:
        logging.error(f'Connection failed: {result["message"]}')
        return 1

    conn_mgr.connect()

    # Create search manager
    search_mgr = LDAPSearchManager(conn_mgr, args.base_dn)

    mapping_rows = []

    # Export user mappings
    logging.info('Querying users from AD...')
    users_filter = '(&(objectClass=user)(employeeID=*))'  # Only users with employeeID
    if hasattr(args, 'users_ou') and args.users_ou:
        users = search_mgr.search(users_filter, base_dn=args.users_ou,
                                  attributes=['sAMAccountName', 'employeeID', 'objectSid'])
    else:
        users = search_mgr.search(users_filter,
                                  attributes=['sAMAccountName', 'employeeID', 'objectSid'])

    for user in users:
        attrs = user['attributes']
        employee_id = attrs.get('employeeID', [None])[0]
        username = attrs.get('sAMAccountName', [None])[0]
        object_sid = attrs.get('objectSid', [None])[0]

        if employee_id and object_sid:
            try:
                rid = extract_rid_from_sid(object_sid)
                mapping_rows.append({
                    'Original_ID': employee_id,
                    'Object_Type': 'User',
                    'Name': username,
                    'AD_SID': format_sid(object_sid),
                    'AD_RID': rid
                })
            except Exception as e:
                logging.warning(f'Failed to parse SID for user {username}: {e} (type={type(object_sid).__name__}, value={repr(object_sid)[:100]})')

    logging.info(f'Found {len(mapping_rows)} users with employeeID')

    # Export group mappings
    logging.info('Querying groups from AD...')
    groups_filter = '(&(objectClass=group)(description=*[OriginalID:*))'  # Groups with original ID
    if hasattr(args, 'groups_ou') and args.groups_ou:
        groups = search_mgr.search(groups_filter, base_dn=args.groups_ou,
                                   attributes=['cn', 'description', 'objectSid'])
    else:
        groups = search_mgr.search(groups_filter,
                                   attributes=['cn', 'description', 'objectSid'])

    user_count = len(mapping_rows)
    for group in groups:
        attrs = group['attributes']
        cn = attrs.get('cn', [None])[0]
        description = attrs.get('description', [''])[0]
        object_sid = attrs.get('objectSid', [None])[0]

        # Extract original ID from description [OriginalID:12345]
        original_id = extract_original_id_from_description(description)

        if original_id and object_sid:
            try:
                rid = extract_rid_from_sid(object_sid)
                mapping_rows.append({
                    'Original_ID': original_id,
                    'Object_Type': 'Group',
                    'Name': cn,
                    'AD_SID': format_sid(object_sid),
                    'AD_RID': rid
                })
            except Exception as e:
                logging.warning(f'Failed to parse SID for group {cn}: {e} (type={type(object_sid).__name__}, value={repr(object_sid)[:100]})')

    logging.info(f'Found {len(mapping_rows) - user_count} groups with OriginalID')

    # Write mapping CSV
    output_file = args.output_file if hasattr(args, 'output_file') else 'rid_mapping.csv'
    logging.info(f'Writing RID mapping to {output_file}...')

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['Original_ID', 'Object_Type', 'Name', 'AD_SID', 'AD_RID']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(mapping_rows)

    logging.info(f'RID mapping exported: {len(mapping_rows)} entries')
    logging.info('='*70)
    logging.info('MAPPING EXPORT COMPLETE')
    logging.info(f'Total entries: {len(mapping_rows)}')
    logging.info(f'Users: {user_count}')
    logging.info(f'Groups: {len(mapping_rows) - user_count}')
    logging.info(f'Output file: {output_file}')
    logging.info('='*70)

    conn_mgr.disconnect()
    return 0


def cmd_translate_permissions(args):
    """Translate permission CSVs from original RIDs to new AD-assigned RIDs.

    Reads the RID mapping file (from export-rid-mapping) and rewrites
    permission CSVs, replacing original GROUP_IDs with new AD RIDs.
    This is a pure CSV-to-CSV translation; no LDAP connection required.
    """
    logging.info('Translating permission CSVs...')

    # Read RID mapping
    mapping_file = args.rid_mapping
    if not os.path.isfile(mapping_file):
        logging.error(f'RID mapping file not found: {mapping_file}')
        return 1

    rid_lookup = {}  # Original_ID (str) -> AD_RID (str)
    with open(mapping_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            original_id = row['Original_ID'].strip()
            ad_rid = str(row['AD_RID']).strip()
            if original_id in rid_lookup:
                logging.warning(f'Duplicate Original_ID {original_id} in mapping (keeping first)')
            else:
                rid_lookup[original_id] = ad_rid

    logging.info(f'Loaded RID mapping: {len(rid_lookup)} entries')

    # Validate input directory
    input_dir = args.input_dir
    if not os.path.isdir(input_dir):
        logging.error(f'Input directory not found: {input_dir}')
        return 1

    # Create output directory
    output_dir = args.output_dir
    os.makedirs(output_dir, exist_ok=True)

    # Define which files and columns to translate
    # Each entry: (filename, list of columns to translate)
    permission_files = [
        ('Unique_Sections_Access.csv', ['Group', 'User', 'RID']),
        ('STYPE_SECTION_ACCESS.csv', ['Group', 'RID']),
        ('STYPE_REPORT_SPECIES_ACCESS.csv', ['Group', 'RID']),
        ('STYPE_FOLDER_ACCESS.csv', ['Group', 'RID']),
    ]

    total_translated = 0
    total_unmapped = 0
    unmapped_rids = set()
    files_processed = 0

    for filename, columns in permission_files:
        input_path = os.path.join(input_dir, filename)
        if not os.path.isfile(input_path):
            logging.warning(f'Permission file not found, skipping: {input_path}')
            continue

        output_path = os.path.join(output_dir, filename)
        file_translated = 0
        file_unmapped = 0

        with open(input_path, 'r', encoding='utf-8') as fin:
            reader = csv.DictReader(fin)
            fieldnames = reader.fieldnames

            with open(output_path, 'w', newline='', encoding='utf-8') as fout:
                writer = csv.DictWriter(fout, fieldnames=fieldnames)
                writer.writeheader()

                for row in reader:
                    for col in columns:
                        value = row.get(col, '').strip()
                        if not value:
                            continue

                        # Handle pipe-delimited values (e.g., "35442|36986")
                        parts = value.split('|')
                        translated_parts = []

                        for part in parts:
                            part = part.strip()
                            if not part:
                                translated_parts.append(part)
                                continue

                            if part in rid_lookup:
                                translated_parts.append(rid_lookup[part])
                                file_translated += 1
                            else:
                                translated_parts.append(part)
                                if part.isdigit():
                                    file_unmapped += 1
                                    unmapped_rids.add(part)

                        row[col] = '|'.join(translated_parts)

                    writer.writerow(row)

        logging.info(f'{filename}: {file_translated} RIDs translated, {file_unmapped} unmapped')
        total_translated += file_translated
        total_unmapped += file_unmapped
        files_processed += 1

    # Log unmapped RIDs
    if unmapped_rids:
        logging.warning(f'Unmapped RIDs ({len(unmapped_rids)}): {", ".join(sorted(unmapped_rids))}')

    # Summary
    logging.info('=' * 70)
    logging.info('PERMISSION TRANSLATION COMPLETE')
    logging.info(f'Files processed:   {files_processed}')
    logging.info(f'RIDs translated:   {total_translated}')
    logging.info(f'RIDs unmapped:     {total_unmapped}')
    logging.info(f'Output directory:  {os.path.abspath(output_dir)}')
    logging.info('=' * 70)

    return 0


def cmd_verify_import(args):
    """Verify import command."""
    logging.info('Verifying imported entries...')

    # Create connection manager
    conn_mgr = LDAPConnectionManager(
        server=args.server,
        port=args.port,
        bind_dn=args.bind_dn,
        password=args.password,
        use_ssl=args.use_ssl,
        base_dn=args.base_dn,
        ssl_no_verify=getattr(args, 'ssl_no_verify', False),
        ssl_ca_cert=getattr(args, 'ssl_ca_cert', None),
        ssl_ca_path=getattr(args, 'ssl_ca_path', None)
    )

    # Test connection
    result = conn_mgr.test_connection()
    if not result['success']:
        logging.error(f'Connection failed: {result["message"]}')
        return 1

    # Connect
    conn_mgr.connect()

    # Create search manager
    search_mgr = LDAPSearchManager(conn_mgr, args.base_dn)

    # Verify groups
    if hasattr(args, 'groups_csv') and args.groups_csv:
        logging.info('Verifying groups...')
        importer = CSVImporter(args.groups_csv)
        groups = importer.read_groups()

        groups_found = 0
        groups_missing = 0
        for group in groups:
            cn = group['GROUPNAME']
            results = search_mgr.search(f'(&(objectClass=group)(cn={cn}))')
            if results:
                groups_found += 1
            else:
                groups_missing += 1
                logging.warning(f'Group not found: {cn}')

        logging.info(f'Groups: {groups_found} found, {groups_missing} missing')

    # Verify users
    if hasattr(args, 'users_csv') and args.users_csv:
        logging.info('Verifying users...')
        importer = CSVImporter(args.users_csv)
        users = importer.read_users()

        users_found = 0
        users_missing = 0
        for user in users:
            username = user['USERNAME']
            results = search_mgr.search(f'(&(objectClass=user)(sAMAccountName={username}))')
            if results:
                users_found += 1
            else:
                users_missing += 1
                logging.warning(f'User not found: {username}')

        logging.info(f'Users: {users_found} found, {users_missing} missing')

    conn_mgr.disconnect()
    return 0


def cmd_assign_groups(args):
    """Assign groups command."""
    logging.info('Assigning users to groups from CSV...')

    # Create connection manager
    conn_mgr = LDAPConnectionManager(
        server=args.server,
        port=args.port,
        bind_dn=args.bind_dn,
        password=args.password,
        use_ssl=args.use_ssl,
        base_dn=args.base_dn,
        ssl_no_verify=getattr(args, 'ssl_no_verify', False),
        ssl_ca_cert=getattr(args, 'ssl_ca_cert', None),
        ssl_ca_path=getattr(args, 'ssl_ca_path', None)
    )

    # Test connection
    result = conn_mgr.test_connection()
    if not result['success']:
        logging.error(f'Connection failed: {result["message"]}')
        return 1

    # Connect
    conn_mgr.connect()

    # Verify OUs exist
    if not conn_mgr.verify_ou_exists(args.groups_ou):
        logging.error(f'Groups OU does not exist: {args.groups_ou}')
        return 1

    if not conn_mgr.verify_ou_exists(args.users_ou):
        logging.error(f'Users OU does not exist: {args.users_ou}')
        return 1

    # Create membership manager
    membership_mgr = LDAPGroupMembershipManager(
        conn_mgr,
        args.groups_ou,
        args.users_ou,
        args.users_csv,
        args.groups_csv
    )

    # Assign users to groups
    result = membership_mgr.assign_from_csv(
        args.assignments_csv,
        dry_run=args.dry_run,
        continue_on_error=getattr(args, 'continue_on_error', True)
    )

    if result is None:
        return 1

    # Print summary
    stats = result['stats']
    logging.info('='*70)
    if args.dry_run:
        logging.info('DRY-RUN COMPLETE')
    else:
        logging.info('GROUP ASSIGNMENT COMPLETE')
    logging.info(f'Total: {stats["total"]}')
    logging.info(f'Assigned: {stats["assigned"]}')
    logging.info(f'Skipped: {stats["skipped"]}')
    logging.info(f'Errors: {stats["errors"]}')
    logging.info('='*70)

    conn_mgr.disconnect()
    return 0 if stats['errors'] == 0 else 1


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point with subcommand routing."""
    parser = argparse.ArgumentParser(
        description='LDAP Integration Tool for IntelliSTOR Migration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test connection
  python ldap_integration.py test-connection --server ldap.ocbc.com --port 389 \\
    --bind-dn "cn=admin,dc=ocbc,dc=com" --password "P@ssw0rd" --base-dn "dc=ocbc,dc=com"

  # Add groups (dry-run)
  python ldap_integration.py add-groups --server ldap.ocbc.com --port 389 \\
    --bind-dn "cn=admin,dc=ocbc,dc=com" --password "P@ssw0rd" --base-dn "dc=ocbc,dc=com" \\
    --groups-ou "ou=Groups,dc=ocbc,dc=com" --csv UserGroups.csv --dry-run

  # Add users with default password (SSL required)
  python ldap_integration.py add-users --server ldap.ocbc.com --port 636 --use-ssl \\
    --bind-dn "cn=admin,dc=ocbc,dc=com" --password "P@ssw0rd" --base-dn "dc=ocbc,dc=com" \\
    --users-ou "ou=Users,dc=ocbc,dc=com" --csv Users.csv \\
    --password-strategy default --default-password "TempP@ss123"

  # Add all (groups, users, and assignments)
  python ldap_integration.py add-all --server ldap.ocbc.com --port 636 --use-ssl \\
    --bind-dn "cn=admin,dc=ocbc,dc=com" --password "P@ssw0rd" --base-dn "dc=ocbc,dc=com" \\
    --groups-ou "ou=Groups,dc=ocbc,dc=com" --users-ou "ou=Users,dc=ocbc,dc=com" \\
    --groups-csv UserGroups.csv --users-csv Users.csv \\
    --assignments-csv UserGroupAssignments.csv \\
    --password-strategy default --default-password "TempP@ss123"

  # Assign users to groups
  python ldap_integration.py assign-groups --server ldap.ocbc.com --port 389 \\
    --bind-dn "cn=admin,dc=ocbc,dc=com" --password "P@ssw0rd" --base-dn "dc=ocbc,dc=com" \\
    --groups-ou "ou=Groups,dc=ocbc,dc=com" --users-ou "ou=Users,dc=ocbc,dc=com" \\
    --groups-csv UserGroups.csv --users-csv Users.csv \\
    --assignments-csv UserGroupAssignments.csv

  # Search LDAP
  python ldap_integration.py search --server ldap.ocbc.com --port 389 \\
    --bind-dn "cn=admin,dc=ocbc,dc=com" --password "P@ssw0rd" --base-dn "dc=ocbc,dc=com" \\
    --filter "(objectClass=user)" --attributes "cn,sAMAccountName,mail"

  # Start browser API
  python ldap_integration.py serve-browser --server ldap.ocbc.com --port 389 \\
    --bind-dn "cn=admin,dc=ocbc,dc=com" --password "P@ssw0rd" --base-dn "dc=ocbc,dc=com"

  # Translate permission CSVs using RID mapping
  python ldap_integration.py translate-permissions \\
    --rid-mapping rid_mapping.csv \\
    --input-dir "S:\\transfer\\Freddievr\\ForPhilipp\\Users_SG" \\
    --output-dir ./translated_permissions
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to execute')

    # Test connection
    test_parser = subparsers.add_parser('test-connection', help='Test LDAP connectivity')
    add_connection_args(test_parser)

    # Create OUs
    ous_parser = subparsers.add_parser('create-ous', help='Create organizational units (Groups/Users OUs)')
    add_connection_args(ous_parser)
    ous_parser.add_argument('--groups-ou', help='Groups OU DN to create')
    ous_parser.add_argument('--users-ou', help='Users OU DN to create')

    # Add groups
    groups_parser = subparsers.add_parser('add-groups', help='Import groups from CSV')
    add_connection_args(groups_parser)
    groups_parser.add_argument('--groups-ou', required=True, help='Groups OU DN')
    groups_parser.add_argument('--csv', required=True, help='Path to UserGroups.csv')
    groups_parser.add_argument('--dry-run', action='store_true', help='Preview without executing')
    groups_parser.add_argument('--continue-on-error', action='store_true', default=True, help='Continue if entry fails')

    # Add users
    users_parser = subparsers.add_parser('add-users', help='Import users from CSV')
    add_connection_args(users_parser)
    users_parser.add_argument('--users-ou', required=True, help='Users OU DN')
    users_parser.add_argument('--csv', required=True, help='Path to Users.csv')
    users_parser.add_argument('--password-strategy', choices=['use-csv', 'default', 'skip', 'random'],
                              default='use-csv', help='Password strategy')
    users_parser.add_argument('--default-password', help='Default password (required if strategy is default)')
    users_parser.add_argument('--dry-run', action='store_true', help='Preview without executing')
    users_parser.add_argument('--continue-on-error', action='store_true', default=True, help='Continue if entry fails')

    # Add all
    all_parser = subparsers.add_parser('add-all', help='Import groups, users, and assignments')
    add_connection_args(all_parser)
    all_parser.add_argument('--groups-ou', required=True, help='Groups OU DN')
    all_parser.add_argument('--users-ou', required=True, help='Users OU DN')
    all_parser.add_argument('--groups-csv', required=True, help='Path to UserGroups.csv')
    all_parser.add_argument('--users-csv', required=True, help='Path to Users.csv')
    all_parser.add_argument('--assignments-csv', help='Path to UserGroupAssignments.csv (optional)')
    all_parser.add_argument('--password-strategy', choices=['use-csv', 'default', 'skip', 'random'],
                            default='use-csv', help='Password strategy')
    all_parser.add_argument('--default-password', help='Default password (required if strategy is default)')
    all_parser.add_argument('--dry-run', action='store_true', help='Preview without executing')
    all_parser.add_argument('--continue-on-error', action='store_true', default=True, help='Continue if entry fails')

    # Search
    search_parser = subparsers.add_parser('search', help='Search LDAP directory')
    add_connection_args(search_parser)
    search_parser.add_argument('--filter', required=True, help='LDAP filter (e.g., "(objectClass=user)")')
    search_parser.add_argument('--attributes', help='Comma-separated attributes to retrieve')

    # Serve browser
    browser_parser = subparsers.add_parser('serve-browser', help='Start browser API')
    add_connection_args(browser_parser)
    browser_parser.add_argument('--api-host', default='127.0.0.1', help='API host (default: 127.0.0.1)')
    browser_parser.add_argument('--api-port', type=int, default=5000, help='API port (default: 5000)')

    # Verify import
    verify_parser = subparsers.add_parser('verify-import', help='Verify imported entries')
    add_connection_args(verify_parser)
    verify_parser.add_argument('--groups-csv', help='Path to UserGroups.csv')
    verify_parser.add_argument('--users-csv', help='Path to Users.csv')

    # Assign groups
    assign_parser = subparsers.add_parser('assign-groups', help='Assign users to groups from CSV')
    add_connection_args(assign_parser)
    assign_parser.add_argument('--groups-ou', required=True, help='Groups OU DN')
    assign_parser.add_argument('--users-ou', required=True, help='Users OU DN')
    assign_parser.add_argument('--groups-csv', required=True, help='Path to UserGroups.csv')
    assign_parser.add_argument('--users-csv', required=True, help='Path to Users.csv')
    assign_parser.add_argument('--assignments-csv', required=True, help='Path to UserGroupAssignments.csv')
    assign_parser.add_argument('--dry-run', action='store_true', help='Preview without executing')
    assign_parser.add_argument('--continue-on-error', action='store_true', default=True, help='Continue if assignment fails')

    # Export RID mapping
    export_parser = subparsers.add_parser('export-rid-mapping', help='Export Original RID to AD RID mapping')
    add_connection_args(export_parser)
    export_parser.add_argument('--users-ou', help='Users OU DN (optional, for filtering)')
    export_parser.add_argument('--groups-ou', help='Groups OU DN (optional, for filtering)')
    export_parser.add_argument('--output-file', default='rid_mapping.csv',
                              help='Output mapping file (default: rid_mapping.csv)')

    # Translate permissions
    translate_parser = subparsers.add_parser('translate-permissions',
                                             help='Translate permission CSVs using RID mapping')
    translate_parser.add_argument('--rid-mapping', required=True,
                                 help='Path to rid_mapping.csv (from export-rid-mapping)')
    translate_parser.add_argument('--input-dir', required=True,
                                 help='Directory containing permission CSVs')
    translate_parser.add_argument('--output-dir', default='./translated_permissions',
                                 help='Output directory for translated CSVs (default: ./translated_permissions)')
    translate_parser.add_argument('--output-dir-log', '-o', dest='output_dir_log', default='.',
                                 help='Output directory for log file (default: current directory)')
    translate_parser.add_argument('--quiet', action='store_true', help='Quiet mode')

    args = parser.parse_args()

    # Setup logging
    # translate-permissions uses --output-dir for translated files, so log to '.' for that command
    if args.command == 'translate-permissions':
        log_dir = getattr(args, 'output_dir_log', '.')
    else:
        log_dir = getattr(args, 'output_dir', '.')
    quiet = getattr(args, 'quiet', False)
    os.makedirs(log_dir, exist_ok=True)
    setup_logging(log_dir, quiet)

    # Route to subcommand
    if args.command == 'test-connection':
        sys.exit(cmd_test_connection(args))
    elif args.command == 'create-ous':
        sys.exit(cmd_create_ous(args))
    elif args.command == 'add-groups':
        sys.exit(cmd_add_groups(args))
    elif args.command == 'add-users':
        sys.exit(cmd_add_users(args))
    elif args.command == 'add-all':
        sys.exit(cmd_add_all(args))
    elif args.command == 'assign-groups':
        sys.exit(cmd_assign_groups(args))
    elif args.command == 'search':
        sys.exit(cmd_search(args))
    elif args.command == 'serve-browser':
        sys.exit(cmd_serve_browser(args))
    elif args.command == 'verify-import':
        sys.exit(cmd_verify_import(args))
    elif args.command == 'export-rid-mapping':
        sys.exit(cmd_export_rid_mapping(args))
    elif args.command == 'translate-permissions':
        sys.exit(cmd_translate_permissions(args))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
