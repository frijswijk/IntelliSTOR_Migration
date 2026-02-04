#!/usr/bin/env python3
"""
IntelliSTOR Database Cleanup Script

Removes report instances and all associated records within a date range.
Handles cascading deletions across:
- REPORT_INSTANCE
- REPORT_INSTANCE_SEGMENT
- SST_STORAGE
- MAPFILE (if no other references exist)
- RPTFILE_INSTANCE
- RPTFILE (if no other references exist)

Usage:
    python cleanup_report_instances.py --end-date 2024-12-31 [--start-date 2024-01-01] [--dry-run]
"""

import pymssql
import argparse
from datetime import datetime
from typing import List, Dict, Tuple
import sys


class DatabaseConfig:
    """Database connection configuration"""
    def __init__(self):
        self.server = 'localhost'
        self.port = 1433
        self.user = 'sa'
        self.password = 'Fvrpgr40'
        self.database = 'iSTSGUAT'


class ReportInstanceCleaner:
    """Handles cleanup of report instances and associated data"""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.conn = None
        self.cursor = None

    def connect(self):
        """Establish database connection"""
        try:
            self.conn = pymssql.connect(
                server=self.config.server,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database
            )
            self.cursor = self.conn.cursor(as_dict=True)
            print(f"✓ Connected to database: {self.config.database}")
        except Exception as e:
            print(f"✗ Failed to connect to database: {e}")
            sys.exit(1)

    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
            print("✓ Database connection closed")

    def get_instances_to_delete(self, start_date: str = None, end_date: str = None) -> List[Dict]:
        """
        Get all report instances within the specified date range

        Args:
            start_date: Optional start date string in format 'YYYY-MM-DD' (inclusive)
            end_date: Optional end date string in format 'YYYY-MM-DD' (inclusive)

        Returns:
            List of report instances with their metadata
        """
        query = """
        SELECT
            ri.DOMAIN_ID,
            ri.REPORT_SPECIES_ID,
            ri.AS_OF_TIMESTAMP,
            ri.STRUCTURE_DEF_ID,
            rsn.NAME as REPORT_NAME,
            ri.RPT_FILE_SIZE_KB,
            ri.MAP_FILE_SIZE_KB
        FROM REPORT_INSTANCE ri
        LEFT JOIN REPORT_SPECIES_NAME rsn
            ON ri.DOMAIN_ID = rsn.DOMAIN_ID
            AND ri.REPORT_SPECIES_ID = rsn.REPORT_SPECIES_ID
        WHERE 1=1
        """

        params = []

        if start_date:
            query += " AND ri.AS_OF_TIMESTAMP >= %s"
            params.append(start_date)

        if end_date:
            query += " AND ri.AS_OF_TIMESTAMP <= %s"
            params.append(end_date)

        query += " ORDER BY ri.AS_OF_TIMESTAMP"

        self.cursor.execute(query, tuple(params))
        instances = self.cursor.fetchall()

        date_range = ""
        if start_date and end_date:
            date_range = f"between {start_date} and {end_date}"
        elif start_date:
            date_range = f"from {start_date} onwards"
        elif end_date:
            date_range = f"up to {end_date}"
        else:
            date_range = "all dates"

        print(f"\n✓ Found {len(instances)} report instance(s) {date_range}")
        return instances

    def get_mapfiles_to_delete(self, instances: List[Dict]) -> List[int]:
        """
        Get MAP file IDs associated with instances that have no other references

        Args:
            instances: List of report instances

        Returns:
            List of MAP_FILE_IDs that can be safely deleted
        """
        if not instances:
            return []

        # Build list of instance keys
        instance_keys = [(i['DOMAIN_ID'], i['REPORT_SPECIES_ID'], i['AS_OF_TIMESTAMP'])
                         for i in instances]

        # Get all MAP files for these instances
        query = """
        SELECT DISTINCT MAP_FILE_ID
        FROM SST_STORAGE
        WHERE DOMAIN_ID = %s
          AND REPORT_SPECIES_ID = %s
          AND AS_OF_TIMESTAMP = %s
        """

        map_file_ids = set()
        for domain_id, species_id, timestamp in instance_keys:
            self.cursor.execute(query, (domain_id, species_id, timestamp))
            results = self.cursor.fetchall()
            for row in results:
                if row['MAP_FILE_ID']:
                    map_file_ids.add(row['MAP_FILE_ID'])

        # Check which MAP files have no other references
        safe_to_delete = []

        # Create a temp table with instances to delete for more efficient checking
        instance_set = set(instance_keys)

        for map_id in map_file_ids:
            # Get total count of references
            simple_check = """
            SELECT COUNT(*) as ref_count
            FROM SST_STORAGE
            WHERE MAP_FILE_ID = %s
            """
            self.cursor.execute(simple_check, (map_id,))
            total_count = self.cursor.fetchone()['ref_count']

            # Count how many of those references match our instances to delete
            our_count = 0
            check_query = """
            SELECT DOMAIN_ID, REPORT_SPECIES_ID, AS_OF_TIMESTAMP
            FROM SST_STORAGE
            WHERE MAP_FILE_ID = %s
            """
            self.cursor.execute(check_query, (map_id,))
            refs = self.cursor.fetchall()

            for ref in refs:
                key = (ref['DOMAIN_ID'], ref['REPORT_SPECIES_ID'], ref['AS_OF_TIMESTAMP'])
                if key in instance_set:
                    our_count += 1

            # If all references are in our delete set, safe to delete
            if total_count == our_count:
                safe_to_delete.append(map_id)

        print(f"✓ Found {len(safe_to_delete)} MAP file(s) safe to delete")
        return safe_to_delete

    def get_rptfiles_to_delete(self, instances: List[Dict]) -> List[int]:
        """
        Get RPT file IDs associated with instances that have no other references

        Args:
            instances: List of report instances

        Returns:
            List of RPT_FILE_IDs that can be safely deleted
        """
        if not instances:
            return []

        instance_keys = [(i['DOMAIN_ID'], i['REPORT_SPECIES_ID'], i['AS_OF_TIMESTAMP'])
                         for i in instances]

        # Get all RPT files for these instances
        query = """
        SELECT DISTINCT RPT_FILE_ID
        FROM RPTFILE_INSTANCE
        WHERE DOMAIN_ID = %s
          AND REPORT_SPECIES_ID = %s
          AND AS_OF_TIMESTAMP = %s
        """

        rpt_file_ids = set()
        for domain_id, species_id, timestamp in instance_keys:
            self.cursor.execute(query, (domain_id, species_id, timestamp))
            results = self.cursor.fetchall()
            for row in results:
                if row['RPT_FILE_ID']:
                    rpt_file_ids.add(row['RPT_FILE_ID'])

        # Check which RPT files have no other references
        safe_to_delete = []
        instance_set = set(instance_keys)

        for rpt_id in rpt_file_ids:
            # Get total count of references
            simple_check = """
            SELECT COUNT(*) as ref_count
            FROM RPTFILE_INSTANCE
            WHERE RPT_FILE_ID = %s
            """
            self.cursor.execute(simple_check, (rpt_id,))
            total_count = self.cursor.fetchone()['ref_count']

            # Count how many of those references match our instances to delete
            our_count = 0
            check_query = """
            SELECT DOMAIN_ID, REPORT_SPECIES_ID, AS_OF_TIMESTAMP
            FROM RPTFILE_INSTANCE
            WHERE RPT_FILE_ID = %s
            """
            self.cursor.execute(check_query, (rpt_id,))
            refs = self.cursor.fetchall()

            for ref in refs:
                key = (ref['DOMAIN_ID'], ref['REPORT_SPECIES_ID'], ref['AS_OF_TIMESTAMP'])
                if key in instance_set:
                    our_count += 1

            # If all references are in our delete set, safe to delete
            if total_count == our_count:
                safe_to_delete.append(rpt_id)

        print(f"✓ Found {len(safe_to_delete)} RPT file(s) safe to delete")
        return safe_to_delete

    def delete_data(self, start_date: str = None, end_date: str = None, dry_run: bool = True, skip_orphan_check: bool = False) -> Dict[str, int]:
        """
        Execute deletion of report instances and associated data

        Args:
            start_date: Optional start date string in format 'YYYY-MM-DD'
            end_date: Optional end date string in format 'YYYY-MM-DD'
            dry_run: If True, only report what would be deleted
            skip_orphan_check: If True, skip slow orphan file checking (faster for bulk deletions)

        Returns:
            Dictionary with counts of deleted records
        """
        stats = {
            'report_instances': 0,
            'report_instance_segments': 0,
            'sst_storage': 0,
            'mapfiles': 0,
            'rptfile_instances': 0,
            'rptfiles': 0
        }

        # Get instances to delete
        instances = self.get_instances_to_delete(start_date, end_date)

        if not instances:
            print("\n⚠ No report instances found to delete")
            return stats

        # Display instances (show first 10 and last 10 if more than 20)
        print("\n" + "="*80)
        print("REPORT INSTANCES TO BE DELETED:")
        print("="*80)

        if len(instances) <= 20:
            # Show all if 20 or fewer
            for idx, inst in enumerate(instances, 1):
                print(f"{idx}. {inst['REPORT_NAME']:45s} | {inst['AS_OF_TIMESTAMP']} | "
                      f"Species: {inst['REPORT_SPECIES_ID']:5d} | "
                      f"RPT: {inst['RPT_FILE_SIZE_KB']:6d}KB | MAP: {inst['MAP_FILE_SIZE_KB']:6d}KB")
        else:
            # Show first 10
            for idx, inst in enumerate(instances[:10], 1):
                print(f"{idx}. {inst['REPORT_NAME']:45s} | {inst['AS_OF_TIMESTAMP']} | "
                      f"Species: {inst['REPORT_SPECIES_ID']:5d} | "
                      f"RPT: {inst['RPT_FILE_SIZE_KB']:6d}KB | MAP: {inst['MAP_FILE_SIZE_KB']:6d}KB")

            print(f"\n... ({len(instances) - 20} more instances) ...\n")

            # Show last 10
            for idx, inst in enumerate(instances[-10:], len(instances) - 9):
                print(f"{idx}. {inst['REPORT_NAME']:45s} | {inst['AS_OF_TIMESTAMP']} | "
                      f"Species: {inst['REPORT_SPECIES_ID']:5d} | "
                      f"RPT: {inst['RPT_FILE_SIZE_KB']:6d}KB | MAP: {inst['MAP_FILE_SIZE_KB']:6d}KB")

        # Get associated files (skip if requested for speed)
        if skip_orphan_check and len(instances) > 1000:
            print(f"\n⚠ Skipping orphan file check for {len(instances):,} instances (use for bulk deletions)")
            print("  MAP and RPT files will be deleted by CASCADE or remain as orphans")
            map_file_ids = []
            rpt_file_ids = []
        else:
            map_file_ids = self.get_mapfiles_to_delete(instances)
            rpt_file_ids = self.get_rptfiles_to_delete(instances)

        if dry_run:
            print("\n" + "="*80)
            print("DRY RUN MODE - No data will be deleted")
            print("="*80)
            stats['report_instances'] = len(instances)
            stats['mapfiles'] = len(map_file_ids)
            stats['rptfiles'] = len(rpt_file_ids)
            return stats

        # Begin transaction
        print("\n" + "="*80)
        print("EXECUTING DELETIONS...")
        print("="*80)

        try:
            # Delete in correct order (child to parent)
            total_instances = len(instances)
            progress_interval = max(1, total_instances // 20)  # Show progress every 5%

            # 1. Delete REPORT_INSTANCE_SEGMENT
            print("Deleting REPORT_INSTANCE_SEGMENT records...", end="", flush=True)
            for idx, inst in enumerate(instances, 1):
                self.cursor.execute("""
                    DELETE FROM REPORT_INSTANCE_SEGMENT
                    WHERE DOMAIN_ID = %s
                      AND REPORT_SPECIES_ID = %s
                      AND AS_OF_TIMESTAMP = %s
                """, (inst['DOMAIN_ID'], inst['REPORT_SPECIES_ID'], inst['AS_OF_TIMESTAMP']))
                stats['report_instance_segments'] += self.cursor.rowcount

                if idx % progress_interval == 0 or idx == total_instances:
                    pct = (idx / total_instances) * 100
                    print(f"\rDeleting REPORT_INSTANCE_SEGMENT records... {pct:.0f}% ({idx}/{total_instances})", end="", flush=True)

            print(f"\n✓ Deleted {stats['report_instance_segments']} REPORT_INSTANCE_SEGMENT record(s)")

            # 2. Delete SST_STORAGE
            print("Deleting SST_STORAGE records...", end="", flush=True)
            for idx, inst in enumerate(instances, 1):
                self.cursor.execute("""
                    DELETE FROM SST_STORAGE
                    WHERE DOMAIN_ID = %s
                      AND REPORT_SPECIES_ID = %s
                      AND AS_OF_TIMESTAMP = %s
                """, (inst['DOMAIN_ID'], inst['REPORT_SPECIES_ID'], inst['AS_OF_TIMESTAMP']))
                stats['sst_storage'] += self.cursor.rowcount

                if idx % progress_interval == 0 or idx == total_instances:
                    pct = (idx / total_instances) * 100
                    print(f"\rDeleting SST_STORAGE records... {pct:.0f}% ({idx}/{total_instances})", end="", flush=True)

            print(f"\n✓ Deleted {stats['sst_storage']} SST_STORAGE record(s)")

            # 3. Delete MAPFILE entries (no other references)
            if map_file_ids:
                print(f"Deleting {len(map_file_ids)} MAPFILE records...", end="", flush=True)
                for idx, map_id in enumerate(map_file_ids, 1):
                    self.cursor.execute("DELETE FROM MAPFILE WHERE MAP_FILE_ID = %s", (map_id,))
                    stats['mapfiles'] += self.cursor.rowcount

                    if len(map_file_ids) > 100 and idx % max(1, len(map_file_ids) // 20) == 0:
                        pct = (idx / len(map_file_ids)) * 100
                        print(f"\rDeleting MAPFILE records... {pct:.0f}% ({idx}/{len(map_file_ids)})", end="", flush=True)

                print(f"\n✓ Deleted {stats['mapfiles']} MAPFILE record(s)")

            # 4. Delete RPTFILE_INSTANCE
            print("Deleting RPTFILE_INSTANCE records...", end="", flush=True)
            for idx, inst in enumerate(instances, 1):
                self.cursor.execute("""
                    DELETE FROM RPTFILE_INSTANCE
                    WHERE DOMAIN_ID = %s
                      AND REPORT_SPECIES_ID = %s
                      AND AS_OF_TIMESTAMP = %s
                """, (inst['DOMAIN_ID'], inst['REPORT_SPECIES_ID'], inst['AS_OF_TIMESTAMP']))
                stats['rptfile_instances'] += self.cursor.rowcount

                if idx % progress_interval == 0 or idx == total_instances:
                    pct = (idx / total_instances) * 100
                    print(f"\rDeleting RPTFILE_INSTANCE records... {pct:.0f}% ({idx}/{total_instances})", end="", flush=True)

            print(f"\n✓ Deleted {stats['rptfile_instances']} RPTFILE_INSTANCE record(s)")

            # 5. Delete RPTFILE entries (no other references)
            if rpt_file_ids:
                print(f"Deleting {len(rpt_file_ids)} RPTFILE records...", end="", flush=True)
                for idx, rpt_id in enumerate(rpt_file_ids, 1):
                    self.cursor.execute("DELETE FROM RPTFILE WHERE RPT_FILE_ID = %s", (rpt_id,))
                    stats['rptfiles'] += self.cursor.rowcount

                    if len(rpt_file_ids) > 100 and idx % max(1, len(rpt_file_ids) // 20) == 0:
                        pct = (idx / len(rpt_file_ids)) * 100
                        print(f"\rDeleting RPTFILE records... {pct:.0f}% ({idx}/{len(rpt_file_ids)})", end="", flush=True)

                print(f"\n✓ Deleted {stats['rptfiles']} RPTFILE record(s)")

            # 6. Delete REPORT_INSTANCE
            print("Deleting REPORT_INSTANCE records...", end="", flush=True)
            for idx, inst in enumerate(instances, 1):
                self.cursor.execute("""
                    DELETE FROM REPORT_INSTANCE
                    WHERE DOMAIN_ID = %s
                      AND REPORT_SPECIES_ID = %s
                      AND AS_OF_TIMESTAMP = %s
                """, (inst['DOMAIN_ID'], inst['REPORT_SPECIES_ID'], inst['AS_OF_TIMESTAMP']))
                stats['report_instances'] += self.cursor.rowcount

                if idx % progress_interval == 0 or idx == total_instances:
                    pct = (idx / total_instances) * 100
                    print(f"\rDeleting REPORT_INSTANCE records... {pct:.0f}% ({idx}/{total_instances})", end="", flush=True)

            print(f"\n✓ Deleted {stats['report_instances']} REPORT_INSTANCE record(s)")

            # Commit transaction
            self.conn.commit()
            print("\n✓ All deletions committed successfully")

        except Exception as e:
            self.conn.rollback()
            print(f"\n✗ Error during deletion: {e}")
            print("✓ Transaction rolled back - no data was deleted")
            raise

        return stats


def main():
    parser = argparse.ArgumentParser(
        description='Clean up IntelliSTOR report instances and associated data within a date range',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run - see what would be deleted up to a date
  python cleanup_report_instances.py --end-date 2024-12-31 --dry-run

  # Actually delete data up to a date
  python cleanup_report_instances.py --end-date 2024-12-31

  # Delete test instances in the future (from a start date onwards)
  python cleanup_report_instances.py --start-date 2026-01-01 --dry-run

  # Delete instances in a specific date range
  python cleanup_report_instances.py --start-date 2024-01-01 --end-date 2024-12-31 --dry-run

  # Delete everything (use with caution!)
  python cleanup_report_instances.py --start-date 1900-01-01 --end-date 2099-12-31
        """
    )

    parser.add_argument(
        '--start-date',
        help='Delete instances from this date onwards (YYYY-MM-DD, inclusive)'
    )

    parser.add_argument(
        '--end-date',
        help='Delete instances up to and including this date (YYYY-MM-DD, inclusive)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )

    parser.add_argument(
        '--skip-orphan-check',
        action='store_true',
        help='Skip slow orphan file checking (recommended for bulk deletions >1000 instances)'
    )

    args = parser.parse_args()

    # Validate that at least one date is provided
    if not args.start_date and not args.end_date:
        print("✗ Error: You must specify at least one of --start-date or --end-date")
        parser.print_help()
        sys.exit(1)

    # Validate date formats
    try:
        if args.start_date:
            start_dt = datetime.strptime(args.start_date, '%Y-%m-%d')
        if args.end_date:
            end_dt = datetime.strptime(args.end_date, '%Y-%m-%d')

        # Check that start_date is before end_date if both provided
        if args.start_date and args.end_date:
            if start_dt > end_dt:
                print(f"✗ Error: start-date ({args.start_date}) must be before end-date ({args.end_date})")
                sys.exit(1)

    except ValueError as e:
        print(f"✗ Invalid date format: {e}")
        print("  Please use YYYY-MM-DD format (e.g., 2024-12-31)")
        sys.exit(1)

    # Confirm with user if not dry run
    if not args.dry_run:
        print("\n" + "="*80)
        print("⚠  WARNING: You are about to DELETE data from the database!")
        print("="*80)

        if args.start_date and args.end_date:
            print(f"All report instances between {args.start_date} and {args.end_date} will be deleted.")
        elif args.start_date:
            print(f"All report instances from {args.start_date} onwards will be deleted.")
        elif args.end_date:
            print(f"All report instances up to and including {args.end_date} will be deleted.")

        print("This operation CANNOT be undone!")
        print("\nPress Ctrl+C to cancel, or type 'DELETE' to continue: ")

        confirmation = input().strip()
        if confirmation != 'DELETE':
            print("\n✓ Operation cancelled")
            sys.exit(0)

    # Execute cleanup
    config = DatabaseConfig()
    cleaner = ReportInstanceCleaner(config)

    try:
        cleaner.connect()
        stats = cleaner.delete_data(args.start_date, args.end_date, dry_run=args.dry_run, skip_orphan_check=args.skip_orphan_check)

        # Print summary
        print("\n" + "="*80)
        print("DELETION SUMMARY:")
        print("="*80)
        print(f"Report Instances:        {stats['report_instances']}")
        print(f"Report Instance Segments: {stats['report_instance_segments']}")
        print(f"SST Storage Records:     {stats['sst_storage']}")
        print(f"MAP Files:               {stats['mapfiles']}")
        print(f"RPT File Instances:      {stats['rptfile_instances']}")
        print(f"RPT Files:               {stats['rptfiles']}")
        print("="*80)

        if args.dry_run:
            print("\n💡 This was a DRY RUN - no data was actually deleted")
            print("   Run without --dry-run to execute the deletion")

    except KeyboardInterrupt:
        print("\n\n✓ Operation cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        sys.exit(1)
    finally:
        cleaner.close()


if __name__ == '__main__':
    main()
