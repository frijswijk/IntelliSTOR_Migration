#!/usr/bin/env python3
"""
IntelliSTOR Signature Cleanup Script

Removes old signature versions, keeping only the latest version for each signature.
Handles cascading deletions across:
- SENSITIVE_FIELD (old versions)
- LINES_IN_SIGN (old versions)
- SIGNATURE (old versions)

Usage:
    python cleanup_old_signatures.py [--dry-run]
    python cleanup_old_signatures.py [--domain-id 1] [--dry-run]
"""

import pymssql
import argparse
from datetime import datetime
from typing import List, Dict, Set, Tuple
import sys


class DatabaseConfig:
    """Database connection configuration"""
    def __init__(self):
        self.server = 'localhost'
        self.port = 1433
        self.user = 'sa'
        self.password = 'Fvrpgr40'
        self.database = 'iSTSGUAT'


class SignatureCleaner:
    """Handles cleanup of old signature versions"""

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

    def get_old_signatures(self, domain_id: int = None) -> List[Dict]:
        """
        Get all old signature versions (not the latest version)

        Args:
            domain_id: Optional domain ID to filter by

        Returns:
            List of old signatures with their metadata
        """
        query = """
        SELECT
            s1.SIGN_ID,
            s1.MINOR_VERSION,
            s1.DOMAIN_ID,
            s1.REPORT_SPECIES_ID,
            s1.DESCRIPTION,
            s1.LAST_MODIFIED_DATE_TIME
        FROM SIGNATURE s1
        WHERE EXISTS (
            SELECT 1 FROM SIGNATURE s2
            WHERE s2.DOMAIN_ID = s1.DOMAIN_ID
              AND s2.REPORT_SPECIES_ID = s1.REPORT_SPECIES_ID
              AND s2.SIGN_ID = s1.SIGN_ID
              AND s2.MINOR_VERSION > s1.MINOR_VERSION
        )
        """

        params = []
        if domain_id is not None:
            query += " AND s1.DOMAIN_ID = %s"
            params.append(domain_id)

        query += " ORDER BY s1.DOMAIN_ID, s1.REPORT_SPECIES_ID, s1.SIGN_ID, s1.MINOR_VERSION"

        self.cursor.execute(query, tuple(params))
        old_sigs = self.cursor.fetchall()

        domain_filter = f" for domain {domain_id}" if domain_id is not None else ""
        print(f"\n✓ Found {len(old_sigs):,} old signature version(s){domain_filter}")
        return old_sigs

    def get_signature_stats(self, domain_id: int = None) -> Dict:
        """
        Get statistics about signatures

        Args:
            domain_id: Optional domain ID to filter by

        Returns:
            Dictionary with signature statistics
        """
        domain_filter = f"WHERE DOMAIN_ID = {domain_id}" if domain_id is not None else ""

        # Total signatures
        self.cursor.execute(f"SELECT COUNT(*) as cnt FROM SIGNATURE {domain_filter}")
        total_sigs = self.cursor.fetchone()['cnt']

        # Unique species/sign combinations
        self.cursor.execute(f"""
            SELECT COUNT(*) as cnt
            FROM (
                SELECT DISTINCT DOMAIN_ID, REPORT_SPECIES_ID, SIGN_ID
                FROM SIGNATURE
                {domain_filter}
            ) as t
        """)
        unique_sigs = self.cursor.fetchone()['cnt']

        # Old versions
        query = f"""
            SELECT COUNT(*) as cnt
            FROM SIGNATURE s1
            WHERE EXISTS (
                SELECT 1 FROM SIGNATURE s2
                WHERE s2.DOMAIN_ID = s1.DOMAIN_ID
                  AND s2.REPORT_SPECIES_ID = s1.REPORT_SPECIES_ID
                  AND s2.SIGN_ID = s1.SIGN_ID
                  AND s2.MINOR_VERSION > s1.MINOR_VERSION
            )
        """
        if domain_id is not None:
            query += f" AND s1.DOMAIN_ID = {domain_id}"

        self.cursor.execute(query)
        old_versions = self.cursor.fetchone()['cnt']

        return {
            'total': total_sigs,
            'unique': unique_sigs,
            'old_versions': old_versions,
            'latest_only': total_sigs - old_versions
        }

    def get_related_records_count(self, domain_id: int = None) -> Dict[str, int]:
        """
        Count related records that will be deleted using efficient SQL

        Args:
            domain_id: Optional domain ID to filter by

        Returns:
            Dictionary with counts of related records
        """
        counts = {'sensitive_field': 0, 'lines_in_sign': 0}

        # Build domain filter for subquery
        domain_filter = f"AND s1.DOMAIN_ID = {domain_id}" if domain_id is not None else ""

        # Count SENSITIVE_FIELD records (using efficient subquery)
        print("Counting SENSITIVE_FIELD records...", end="", flush=True)
        self.cursor.execute(f"""
            SELECT COUNT(*) as cnt
            FROM SENSITIVE_FIELD sf
            WHERE EXISTS (
                SELECT 1 FROM SIGNATURE s1
                WHERE s1.SIGN_ID = sf.SIGN_ID
                  AND s1.MINOR_VERSION = sf.MINOR_VERSION
                  {domain_filter}
                  AND EXISTS (
                      SELECT 1 FROM SIGNATURE s2
                      WHERE s2.DOMAIN_ID = s1.DOMAIN_ID
                        AND s2.REPORT_SPECIES_ID = s1.REPORT_SPECIES_ID
                        AND s2.SIGN_ID = s1.SIGN_ID
                        AND s2.MINOR_VERSION > s1.MINOR_VERSION
                  )
            )
        """)
        counts['sensitive_field'] = self.cursor.fetchone()['cnt']
        print(f" {counts['sensitive_field']:,}")

        # Count LINES_IN_SIGN records (using efficient subquery)
        print("Counting LINES_IN_SIGN records...", end="", flush=True)
        self.cursor.execute(f"""
            SELECT COUNT(*) as cnt
            FROM LINES_IN_SIGN lis
            WHERE EXISTS (
                SELECT 1 FROM SIGNATURE s1
                WHERE s1.SIGN_ID = lis.SIGN_ID
                  AND s1.MINOR_VERSION = lis.MINOR_VERSION
                  {domain_filter}
                  AND EXISTS (
                      SELECT 1 FROM SIGNATURE s2
                      WHERE s2.DOMAIN_ID = s1.DOMAIN_ID
                        AND s2.REPORT_SPECIES_ID = s1.REPORT_SPECIES_ID
                        AND s2.SIGN_ID = s1.SIGN_ID
                        AND s2.MINOR_VERSION > s1.MINOR_VERSION
                  )
            )
        """)
        counts['lines_in_sign'] = self.cursor.fetchone()['cnt']
        print(f" {counts['lines_in_sign']:,}")

        return counts

    def delete_old_signatures(self, domain_id: int = None, dry_run: bool = True) -> Dict[str, int]:
        """
        Execute deletion of old signature versions and related data

        Args:
            domain_id: Optional domain ID to filter by
            dry_run: If True, only report what would be deleted

        Returns:
            Dictionary with counts of deleted records
        """
        stats = {
            'signatures': 0,
            'sensitive_field': 0,
            'lines_in_sign': 0
        }

        # Get statistics first
        sig_stats = self.get_signature_stats(domain_id)

        print("\n" + "="*80)
        print("SIGNATURE STATISTICS:")
        print("="*80)
        print(f"Total signature records:              {sig_stats['total']:,}")
        print(f"Unique signatures (latest only):      {sig_stats['unique']:,}")
        print(f"Old versions (to be deleted):         {sig_stats['old_versions']:,}")
        print(f"Percentage to be deleted:             {(sig_stats['old_versions']/sig_stats['total']*100):.1f}%")

        # Get old signatures
        old_sigs = self.get_old_signatures(domain_id)

        if not old_sigs:
            print("\n⚠ No old signature versions found to delete")
            return stats

        # Show sample of what will be deleted (first 10 and last 10)
        print("\n" + "="*80)
        print("OLD SIGNATURE VERSIONS TO BE DELETED:")
        print("="*80)

        if len(old_sigs) <= 20:
            print(f"\n{'Domain':>8} | {'Species':>8} | {'Sign ID':>8} | {'MinVer':>10} | Description")
            print("-" * 80)
            for sig in old_sigs:
                print(f"{sig['DOMAIN_ID']:8d} | {sig['REPORT_SPECIES_ID']:8d} | "
                      f"{sig['SIGN_ID']:8d} | {sig['MINOR_VERSION']:10d} | "
                      f"{sig['DESCRIPTION'].strip()}")
        else:
            print(f"\n{'Domain':>8} | {'Species':>8} | {'Sign ID':>8} | {'MinVer':>10} | Description")
            print("-" * 80)
            # Show first 10
            for sig in old_sigs[:10]:
                print(f"{sig['DOMAIN_ID']:8d} | {sig['REPORT_SPECIES_ID']:8d} | "
                      f"{sig['SIGN_ID']:8d} | {sig['MINOR_VERSION']:10d} | "
                      f"{sig['DESCRIPTION'].strip()}")

            print(f"\n... ({len(old_sigs) - 20:,} more signatures) ...\n")

            # Show last 10
            for sig in old_sigs[-10:]:
                print(f"{sig['DOMAIN_ID']:8d} | {sig['REPORT_SPECIES_ID']:8d} | "
                      f"{sig['SIGN_ID']:8d} | {sig['MINOR_VERSION']:10d} | "
                      f"{sig['DESCRIPTION'].strip()}")

        # Count related records
        print("\n" + "="*80)
        print("COUNTING RELATED RECORDS:")
        print("="*80)
        related_counts = self.get_related_records_count(domain_id)

        if dry_run:
            print("\n" + "="*80)
            print("DRY RUN MODE - No data will be deleted")
            print("="*80)
            stats['signatures'] = len(old_sigs)
            stats['sensitive_field'] = related_counts['sensitive_field']
            stats['lines_in_sign'] = related_counts['lines_in_sign']
            return stats

        # Begin transaction
        print("\n" + "="*80)
        print("EXECUTING DELETIONS...")
        print("="*80)

        try:
            # Build set of signature keys for efficient deletion
            sig_keys = [(s['SIGN_ID'], s['MINOR_VERSION']) for s in old_sigs]
            total_sigs = len(sig_keys)
            progress_interval = max(1, total_sigs // 20)  # Show progress every 5%

            # 1. Delete SENSITIVE_FIELD records
            print("Deleting SENSITIVE_FIELD records...", end="", flush=True)
            for idx, (sign_id, minor_version) in enumerate(sig_keys, 1):
                self.cursor.execute("""
                    DELETE FROM SENSITIVE_FIELD
                    WHERE SIGN_ID = %s AND MINOR_VERSION = %s
                """, (sign_id, minor_version))
                stats['sensitive_field'] += self.cursor.rowcount

                if idx % progress_interval == 0 or idx == total_sigs:
                    pct = (idx / total_sigs) * 100
                    print(f"\rDeleting SENSITIVE_FIELD records... {pct:.0f}% ({idx:,}/{total_sigs:,})",
                          end="", flush=True)

            print(f"\n✓ Deleted {stats['sensitive_field']:,} SENSITIVE_FIELD record(s)")

            # 2. Delete LINES_IN_SIGN records
            print("Deleting LINES_IN_SIGN records...", end="", flush=True)
            for idx, (sign_id, minor_version) in enumerate(sig_keys, 1):
                self.cursor.execute("""
                    DELETE FROM LINES_IN_SIGN
                    WHERE SIGN_ID = %s AND MINOR_VERSION = %s
                """, (sign_id, minor_version))
                stats['lines_in_sign'] += self.cursor.rowcount

                if idx % progress_interval == 0 or idx == total_sigs:
                    pct = (idx / total_sigs) * 100
                    print(f"\rDeleting LINES_IN_SIGN records... {pct:.0f}% ({idx:,}/{total_sigs:,})",
                          end="", flush=True)

            print(f"\n✓ Deleted {stats['lines_in_sign']:,} LINES_IN_SIGN record(s)")

            # 3. Delete old SIGNATURE records
            print("Deleting old SIGNATURE records...", end="", flush=True)
            for idx, (sign_id, minor_version) in enumerate(sig_keys, 1):
                self.cursor.execute("""
                    DELETE FROM SIGNATURE
                    WHERE SIGN_ID = %s AND MINOR_VERSION = %s
                """, (sign_id, minor_version))
                stats['signatures'] += self.cursor.rowcount

                if idx % progress_interval == 0 or idx == total_sigs:
                    pct = (idx / total_sigs) * 100
                    print(f"\rDeleting old SIGNATURE records... {pct:.0f}% ({idx:,}/{total_sigs:,})",
                          end="", flush=True)

            print(f"\n✓ Deleted {stats['signatures']:,} old SIGNATURE record(s)")

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
        description='Clean up old IntelliSTOR signature versions, keeping only the latest',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run - see what would be deleted (all domains)
  python cleanup_old_signatures.py --dry-run

  # Actually delete old signatures (all domains)
  python cleanup_old_signatures.py

  # Dry run for specific domain
  python cleanup_old_signatures.py --domain-id 1 --dry-run

  # Delete old signatures for specific domain
  python cleanup_old_signatures.py --domain-id 1

Note:
  This script keeps the LATEST version of each signature and deletes all older versions.
  Related records in SENSITIVE_FIELD and LINES_IN_SIGN are also deleted.
  SIGN_GEN_INFO is NOT affected (not version-specific).
        """
    )

    parser.add_argument(
        '--domain-id',
        type=int,
        help='Optional: Only process signatures for this domain ID'
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
        print("⚠  WARNING: You are about to DELETE old signature versions!")
        print("="*80)

        if args.domain_id:
            print(f"All old signature versions for domain {args.domain_id} will be deleted.")
        else:
            print("All old signature versions across ALL domains will be deleted.")

        print("\nOnly the LATEST version of each signature will be kept.")
        print("This operation CANNOT be undone!")
        print("\nPress Ctrl+C to cancel, or type 'DELETE' to continue: ")

        confirmation = input().strip()
        if confirmation != 'DELETE':
            print("\n✓ Operation cancelled")
            sys.exit(0)

    # Execute cleanup
    config = DatabaseConfig()
    cleaner = SignatureCleaner(config)

    try:
        cleaner.connect()
        stats = cleaner.delete_old_signatures(args.domain_id, dry_run=args.dry_run)

        # Print summary
        print("\n" + "="*80)
        print("DELETION SUMMARY:")
        print("="*80)
        print(f"Old Signature Versions:   {stats['signatures']:,}")
        print(f"SENSITIVE_FIELD Records:  {stats['sensitive_field']:,}")
        print(f"LINES_IN_SIGN Records:    {stats['lines_in_sign']:,}")
        print("-" * 80)
        print(f"TOTAL RECORDS REMOVED:    {sum(stats.values()):,}")
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
