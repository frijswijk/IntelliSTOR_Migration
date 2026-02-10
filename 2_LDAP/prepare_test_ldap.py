#!/usr/bin/env python3
"""
prepare_test_ldap.py - Preprocess CSVs for test LDAP import

Reads IntelliSTOR Users_SG CSV files and produces LDAP-ready CSVs:
- Renames numeric group names to IST_* format (e.g., 35442 -> IST_35442)
- Keeps system groups as-is (Domain Users, MD system, etc.)
- Filters users by count (--users N) while always including admin users
- Filters group assignments to only the selected users

Usage:
  python prepare_test_ldap.py --input-dir "S:\\transfer\\...\\Users_SG" --output-dir ./ldap_import --users 10
"""

import csv
import argparse
import os
import sys


# Admin users are always included regardless of --users count
ADMIN_USERNAMES = {'idadmin', 'istoruser'}


def read_csv(filepath):
    """Read a CSV file and return list of row dicts and fieldnames.

    Args:
        filepath: Path to CSV file

    Returns:
        tuple: (list of OrderedDict rows, list of fieldnames)
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    return rows, fieldnames


def is_system_group(row):
    """Check if a group row is a system group (non-numeric GROUPNAME).

    System groups like 'Domain Users', 'MD system', 'DocMgmtUsers' have
    non-numeric names, while test groups have purely numeric names matching
    their GROUP_ID.

    Args:
        row: Group CSV row dict

    Returns:
        bool: True if system group
    """
    groupname = row.get('GROUPNAME', '').strip()
    return not groupname.isdigit()


def prepare_groups(rows):
    """Rename numeric groups to IST_* format, keep system groups as-is.

    Args:
        rows: List of group row dicts from UserGroups.csv

    Returns:
        list: Modified group rows with IST_ prefix on numeric group names
    """
    prepared = []
    renamed_count = 0
    system_count = 0

    for row in rows:
        row = dict(row)  # copy
        groupname = row.get('GROUPNAME', '').strip()

        if is_system_group(row):
            system_count += 1
            prepared.append(row)
            continue

        # Numeric group: rename to IST_<GROUP_ID>
        group_id = row['GROUP_ID'].strip()
        new_name = f'IST_{group_id}'

        # Build description with original ID tag
        original_desc = row.get('DESCRIPTION', '').strip()
        if original_desc:
            description = f'{original_desc} [OriginalID:{group_id}]'
        else:
            description = f'{new_name} [OriginalID:{group_id}]'

        row['GROUPNAME'] = new_name
        row['DESCRIPTION'] = description
        prepared.append(row)
        renamed_count += 1

    print(f'  Groups: {len(prepared)} total ({system_count} system, {renamed_count} renamed to IST_*)')
    return prepared


def filter_users(rows, user_count):
    """Filter users: always include admins, take first N test users.

    Args:
        rows: List of user row dicts from Users.csv
        user_count: Number of test users to include, or 'all'

    Returns:
        list: Filtered user rows
    """
    admins = []
    test_users = []

    for row in rows:
        username = row.get('USERNAME', '').strip()
        if username in ADMIN_USERNAMES:
            admins.append(row)
        else:
            test_users.append(row)

    if user_count == 'all':
        selected_test = test_users
    else:
        n = int(user_count)
        selected_test = test_users[:n]

    result = admins + selected_test
    print(f'  Users: {len(result)} selected ({len(admins)} admins + {len(selected_test)} test users)')
    return result


def filter_assignments(rows, selected_user_ids):
    """Filter group assignments to only selected users.

    Args:
        rows: List of assignment row dicts from UserGroupAssignments.csv
        selected_user_ids: Set of USER_ID strings to include

    Returns:
        list: Filtered assignment rows
    """
    filtered = [row for row in rows if row['USER_ID'].strip() in selected_user_ids]
    print(f'  Assignments: {len(filtered)} of {len(rows)} (filtered to selected users)')
    return filtered


def write_csv(output_dir, filename, rows, fieldnames):
    """Write rows to a CSV file.

    Args:
        output_dir: Output directory path
        filename: Output filename
        rows: List of row dicts
        fieldnames: CSV column headers
    """
    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f'  Written: {filepath} ({len(rows)} rows)')


def main():
    parser = argparse.ArgumentParser(
        description='Preprocess Users_SG CSVs for test LDAP import',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Prepare with 10 test users
  python prepare_test_ldap.py --input-dir "S:\\transfer\\Freddievr\\ForPhilipp\\Users_SG" --users 10

  # Prepare with all users, custom output directory
  python prepare_test_ldap.py --input-dir "S:\\transfer\\Freddievr\\ForPhilipp\\Users_SG" --output-dir ./my_import --users all
        """
    )

    parser.add_argument('--input-dir', required=True,
                        help='Directory containing source CSVs (UserGroups.csv, Users.csv, UserGroupAssignments.csv)')
    parser.add_argument('--output-dir', default='./ldap_import',
                        help='Output directory for processed CSVs (default: ./ldap_import)')
    parser.add_argument('--users', default='all',
                        help='Number of test users to include: 1, 5, 10, ... or "all" (default: all). '
                             'Admin users (idadmin, istoruser) are always included.')

    args = parser.parse_args()

    # Validate input directory
    if not os.path.isdir(args.input_dir):
        print(f'ERROR: Input directory not found: {args.input_dir}', file=sys.stderr)
        sys.exit(1)

    # Validate --users argument
    if args.users != 'all':
        try:
            n = int(args.users)
            if n < 1:
                raise ValueError
        except ValueError:
            print(f'ERROR: --users must be a positive integer or "all", got: {args.users}', file=sys.stderr)
            sys.exit(1)

    # Validate required input files exist
    required_files = ['UserGroups.csv', 'Users.csv', 'UserGroupAssignments.csv']
    for fname in required_files:
        fpath = os.path.join(args.input_dir, fname)
        if not os.path.isfile(fpath):
            print(f'ERROR: Required file not found: {fpath}', file=sys.stderr)
            sys.exit(1)

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    print(f'Input directory:  {args.input_dir}')
    print(f'Output directory: {args.output_dir}')
    print(f'User count:       {args.users}')
    print()

    # Phase 1: Process groups
    print('Processing UserGroups.csv...')
    groups_rows, groups_fields = read_csv(os.path.join(args.input_dir, 'UserGroups.csv'))
    prepared_groups = prepare_groups(groups_rows)
    write_csv(args.output_dir, 'UserGroups.csv', prepared_groups, groups_fields)
    print()

    # Phase 2: Filter users
    print('Processing Users.csv...')
    users_rows, users_fields = read_csv(os.path.join(args.input_dir, 'Users.csv'))
    filtered_users = filter_users(users_rows, args.users)
    write_csv(args.output_dir, 'Users.csv', filtered_users, users_fields)

    # Collect selected USER_IDs for assignment filtering
    selected_user_ids = {row['USER_ID'].strip() for row in filtered_users}
    print()

    # Phase 3: Filter assignments
    print('Processing UserGroupAssignments.csv...')
    assignments_rows, assignments_fields = read_csv(
        os.path.join(args.input_dir, 'UserGroupAssignments.csv'))
    filtered_assignments = filter_assignments(assignments_rows, selected_user_ids)
    write_csv(args.output_dir, 'UserGroupAssignments.csv', filtered_assignments, assignments_fields)
    print()

    # Summary
    print('=' * 60)
    print('PREPARATION COMPLETE')
    print(f'  Groups:      {len(prepared_groups)}')
    print(f'  Users:       {len(filtered_users)}')
    print(f'  Assignments: {len(filtered_assignments)}')
    print(f'  Output dir:  {os.path.abspath(args.output_dir)}')
    print('=' * 60)


if __name__ == '__main__':
    main()
