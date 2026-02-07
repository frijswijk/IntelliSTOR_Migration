#!/usr/bin/env python3
"""
IntelliSTOR Orphaned Files Cleanup Script

Removes orphaned MAP and RPT files that are no longer referenced by any report instances.
This is useful after bulk instance deletions using --skip-orphan-check.

Usage:
    python cleanup_orphaned_files.py [--dry-run]
"""

import pymssql
import argparse
from typing import List, Dict
import sys


class DatabaseConfig:
    """Database connection configuration"""
    def __init__(self):
        self.server = 'localhost'
        self.port = 1433
        self.user = 'sa'
        self.password = 'Fvrpgr40'
        self.database = 'iSTSGUAT'


class OrphanedFileCleaner:
    """Handles cleanup of orphaned MAP and RPT files"""

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

    def get_orphaned_mapfiles(self) -> List[int]:
        """
        Get MAP files that are not referenced by any SST_STORAGE record

        Returns:
            List of orphaned MAP_FILE_IDs
        """
        print("\nSearching for orphaned MAP files...")

        query = """
        SELECT m.MAP_FILE_ID
        FROM MAPFILE m
        WHERE NOT EXISTS (
            SELECT 1 FROM SST_STORAGE s
            WHERE s.MAP_FILE_ID = m.MAP_FILE_ID
        )
        ORDER BY m.MAP_FILE_ID
        """

        self.cursor.execute(query)
        orphans = self.cursor.fetchall()

        print(f"✓ Found {len(orphans):,} orphaned MAP file(s)")

        return [o['MAP_FILE_ID'] for o in orphans]

    def get_orphaned_rptfiles(self) -> List[int]:
        """
        Get RPT files that are not referenced by any RPTFILE_INSTANCE record

        Returns:
            List of orphaned RPT_FILE_IDs
        """
        print("\nSearching for orphaned RPT files...")

        query = """
        SELECT r.RPT_FILE_ID
        FROM RPTFILE r
        WHERE NOT EXISTS (
            SELECT 1 FROM RPTFILE_INSTANCE ri
            WHERE ri.RPT_FILE_ID = r.RPT_FILE_ID
        )
        ORDER BY r.RPT_FILE_ID
        """

        self.cursor.execute(query)
        orphans = self.cursor.fetchall()

        print(f"✓ Found {len(orphans):,} orphaned RPT file(s)")

        return [o['RPT_FILE_ID'] for o in orphans]

    def delete_orphaned_files(self, dry_run: bool = True) -> Dict[str, int]:
        """
        Execute deletion of orphaned MAP and RPT files

        Args:
            dry_run: If True, only report what would be deleted

        Returns:
            Dictionary with counts of deleted records
        """
        stats = {
            'mapfiles': 0,
            'rptfiles': 0
        }

        print("\n" + "="*80)
        print("ORPHANED FILE ANALYSIS:")
        print("="*80)

        # Get orphaned files
        map_file_ids = self.get_orphaned_mapfiles()
        rpt_file_ids = self.get_orphaned_rptfiles()

        if not map_file_ids and not rpt_file_ids:
            print("\n✓ No orphaned files found - database is clean!")
            return stats

        # Show what will be deleted
        print("\n" + "="*80)
        print("FILES TO BE DELETED:")
        print("="*80)
        print(f"Orphaned MAP files:  {len(map_file_ids):,}")
        print(f"Orphaned RPT files:  {len(rpt_file_ids):,}")
        print(f"Total files:         {len(map_file_ids) + len(rpt_file_ids):,}")

        if dry_run:
            print("\n" + "="*80)
            print("DRY RUN MODE - No data will be deleted")
            print("="*80)
            stats['mapfiles'] = len(map_file_ids)
            stats['rptfiles'] = len(rpt_file_ids)
            return stats

        # Begin transaction
        print("\n" + "="*80)
        print("EXECUTING DELETIONS...")
        print("="*80)

        try:
            # Delete orphaned MAP files
            if map_file_ids:
                print(f"Deleting {len(map_file_ids):,} MAP file(s)...", end="", flush=True)

                progress_interval = max(1, len(map_file_ids) // 20)
                for idx, map_id in enumerate(map_file_ids, 1):
                    self.cursor.execute("DELETE FROM MAPFILE WHERE MAP_FILE_ID = %s", (map_id,))
                    stats['mapfiles'] += self.cursor.rowcount

                    if idx % progress_interval == 0 or idx == len(map_file_ids):
                        pct = (idx / len(map_file_ids)) * 100
                        print(f"\rDeleting MAP files... {pct:.0f}% ({idx:,}/{len(map_file_ids):,})",
                              end="", flush=True)

                print(f"\n✓ Deleted {stats['mapfiles']:,} MAPFILE record(s)")

            # Delete orphaned RPT files
            if rpt_file_ids:
                print(f"Deleting {len(rpt_file_ids):,} RPT file(s)...", end="", flush=True)

                progress_interval = max(1, len(rpt_file_ids) // 20)
                for idx, rpt_id in enumerate(rpt_file_ids, 1):
                    self.cursor.execute("DELETE FROM RPTFILE WHERE RPT_FILE_ID = %s", (rpt_id,))
                    stats['rptfiles'] += self.cursor.rowcount

                    if idx % progress_interval == 0 or idx == len(rpt_file_ids):
                        pct = (idx / len(rpt_file_ids)) * 100
                        print(f"\rDeleting RPT files... {pct:.0f}% ({idx:,}/{len(rpt_file_ids):,})",
                              end="", flush=True)

                print(f"\n✓ Deleted {stats['rptfiles']:,} RPTFILE record(s)")

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
        description='Clean up orphaned MAP and RPT files in IntelliSTOR database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run - see what would be deleted
  python cleanup_orphaned_files.py --dry-run

  # Actually delete orphaned files
  python cleanup_orphaned_files.py

Note:
  Orphaned files are created when:
  - Report instances are deleted using --skip-orphan-check
  - Bulk deletions leave MAP/RPT files without references

  These files don't cause problems but waste space.
        """
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )

    args = parser.parse_args()

    # Confirm with user if not dry run
    if not args.dry_run:
        print("\n" + "="*80)
        print("⚠  WARNING: You are about to DELETE orphaned files!")
        print("="*80)
        print("All MAP and RPT files without instance references will be deleted.")
        print("This operation CANNOT be undone!")
        print("\nPress Ctrl+C to cancel, or type 'DELETE' to continue: ")

        confirmation = input().strip()
        if confirmation != 'DELETE':
            print("\n✓ Operation cancelled")
            sys.exit(0)

    # Execute cleanup
    config = DatabaseConfig()
    cleaner = OrphanedFileCleaner(config)

    try:
        cleaner.connect()
        stats = cleaner.delete_orphaned_files(dry_run=args.dry_run)

        # Print summary
        print("\n" + "="*80)
        print("DELETION SUMMARY:")
        print("="*80)
        print(f"Orphaned MAP Files:  {stats['mapfiles']:,}")
        print(f"Orphaned RPT Files:  {stats['rptfiles']:,}")
        print("-" * 80)
        print(f"TOTAL FILES REMOVED: {sum(stats.values()):,}")
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
