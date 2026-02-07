#!/usr/bin/env python3
"""
IntelliSTOR Batch File Updater

This script automatically updates all batch files in the IntelliSTOR Migration
repository to use the air-gap Python installation instead of system Python.

Usage:
    python update_batch_files.py [--source-dir PATH] [--dry-run]

Options:
    --source-dir PATH   Path to IntelliSTOR_Migration source directory
                        Default: ../08_SOURCE_CODE/IntelliSTOR_Migration
    --dry-run           Show what would be changed without making changes
    --restore           Restore batch files from .backup copies

Examples:
    python update_batch_files.py
    python update_batch_files.py --dry-run
    python update_batch_files.py --source-dir C:\IntelliSTOR_Migration
    python update_batch_files.py --restore
"""

import argparse
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path


class BatchFileUpdater:
    """Updates batch files to use air-gap Python"""

    def __init__(self, source_dir: Path, dry_run: bool = False):
        self.source_dir = Path(source_dir).resolve()
        self.dry_run = dry_run
        self.updated_files = []
        self.skipped_files = []
        self.backed_up_files = []
        self.errors = []

    def find_batch_files(self):
        """Find all .bat files in the source directory"""
        print(f"Scanning for batch files in: {self.source_dir}")
        print()

        batch_files = list(self.source_dir.rglob("*.bat"))

        # Exclude certain directories
        exclude_dirs = {
            "02_PACKAGE_BUILDER",
            "03_OFFLINE_INSTALLER",
            "04_PYTHON_EMBEDDED",
            "05_WHEELS",
            "06_DLLS",
            "07_EXTERNAL_TOOLS",
            "IntelliSTOR_Python"
        }

        filtered_files = []
        for bat_file in batch_files:
            # Check if any excluded directory is in the path
            if any(excluded in bat_file.parts for excluded in exclude_dirs):
                continue
            filtered_files.append(bat_file)

        print(f"Found {len(filtered_files)} batch files to process")
        return filtered_files

    def backup_file(self, file_path: Path) -> bool:
        """Create a backup of the batch file"""
        backup_path = file_path.with_suffix(file_path.suffix + ".backup")

        # Don't overwrite existing backups
        if backup_path.exists():
            return True

        try:
            shutil.copy2(file_path, backup_path)
            self.backed_up_files.append(file_path)
            return True
        except Exception as e:
            self.errors.append(f"Failed to backup {file_path}: {e}")
            return False

    def update_batch_file(self, file_path: Path) -> bool:
        """Update a single batch file to use %AIRGAP_PYTHON%"""
        try:
            # Read the file
            content = file_path.read_text(encoding="utf-8", errors="ignore")

            # Check if already updated
            if "%AIRGAP_PYTHON%" in content:
                self.skipped_files.append((file_path, "Already uses %AIRGAP_PYTHON%"))
                return False

            # Patterns to replace
            # Pattern 1: "python script.py" -> "%AIRGAP_PYTHON% script.py"
            # Pattern 2: "python -m module" -> "%AIRGAP_PYTHON% -m module"
            # Pattern 3: "python.exe script.py" -> "%AIRGAP_PYTHON% script.py"

            # Use word boundaries to avoid matching "python" inside words
            # Match "python" or "python.exe" at start of line or after whitespace
            # followed by space, then arguments

            patterns = [
                # Match: python script.py (with various whitespace)
                (r'\bpython\.exe\s+', r'%AIRGAP_PYTHON% '),
                (r'\bpython\s+', r'%AIRGAP_PYTHON% '),
            ]

            new_content = content
            changes_made = False

            for pattern, replacement in patterns:
                if re.search(pattern, new_content, re.IGNORECASE):
                    new_content = re.sub(pattern, replacement, new_content, flags=re.IGNORECASE)
                    changes_made = True

            if not changes_made:
                self.skipped_files.append((file_path, "No 'python' commands found"))
                return False

            # Show the changes
            if self.dry_run:
                print(f"\n{'='*70}")
                print(f"Would update: {file_path.relative_to(self.source_dir)}")
                print(f"{'='*70}")
                self._show_diff(content, new_content)
                self.updated_files.append(file_path)
                return True

            # Backup before modifying
            if not self.backup_file(file_path):
                return False

            # Write the updated content
            file_path.write_text(new_content, encoding="utf-8")
            self.updated_files.append(file_path)

            print(f"✓ Updated: {file_path.relative_to(self.source_dir)}")
            return True

        except Exception as e:
            self.errors.append(f"Failed to update {file_path}: {e}")
            return False

    def _show_diff(self, old_content: str, new_content: str):
        """Show differences between old and new content"""
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()

        # Find lines that changed
        changes = []
        for i, (old_line, new_line) in enumerate(zip(old_lines, new_lines), 1):
            if old_line != new_line:
                changes.append((i, old_line, new_line))

        if changes:
            print("\nChanges:")
            for line_num, old_line, new_line in changes[:10]:  # Show first 10 changes
                print(f"\nLine {line_num}:")
                print(f"  - {old_line.strip()}")
                print(f"  + {new_line.strip()}")

            if len(changes) > 10:
                print(f"\n... and {len(changes) - 10} more changes")

    def restore_backups(self):
        """Restore batch files from backups"""
        print(f"Scanning for backup files in: {self.source_dir}")
        print()

        backup_files = list(self.source_dir.rglob("*.bat.backup"))

        if not backup_files:
            print("No backup files found")
            return 0

        print(f"Found {len(backup_files)} backup files")
        print()

        restored = 0
        for backup_file in backup_files:
            original_file = backup_file.with_suffix("")

            if self.dry_run:
                print(f"Would restore: {original_file.relative_to(self.source_dir)}")
                restored += 1
            else:
                try:
                    shutil.copy2(backup_file, original_file)
                    print(f"✓ Restored: {original_file.relative_to(self.source_dir)}")
                    restored += 1
                except Exception as e:
                    print(f"✗ Failed to restore {original_file}: {e}")
                    self.errors.append(f"Failed to restore {original_file}: {e}")

        return restored

    def print_summary(self):
        """Print summary of changes"""
        print("\n" + "="*70)
        print("UPDATE SUMMARY")
        print("="*70)

        if self.updated_files:
            print(f"\nUpdated files: {len(self.updated_files)}")
            for file_path in self.updated_files:
                print(f"  ✓ {file_path.relative_to(self.source_dir)}")

        if self.backed_up_files:
            print(f"\nBacked up files: {len(self.backed_up_files)}")
            print("  (Original files saved with .backup extension)")

        if self.skipped_files:
            print(f"\nSkipped files: {len(self.skipped_files)}")
            for file_path, reason in self.skipped_files[:5]:
                print(f"  - {file_path.relative_to(self.source_dir)}: {reason}")
            if len(self.skipped_files) > 5:
                print(f"  ... and {len(self.skipped_files) - 5} more")

        if self.errors:
            print(f"\nErrors: {len(self.errors)}")
            for error in self.errors:
                print(f"  ✗ {error}")

        print()

        if self.dry_run:
            print("DRY RUN - No files were modified")
            print("Run without --dry-run to apply these changes")
        else:
            print(f"Successfully updated {len(self.updated_files)} batch files")
            if self.backed_up_files:
                print(f"Original files backed up ({len(self.backed_up_files)} files)")
                print("Use --restore to revert changes")

    def run(self):
        """Execute the batch file update process"""
        print("="*70)
        print("IntelliSTOR Batch File Updater")
        print("="*70)
        print(f"Source directory: {self.source_dir}")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE UPDATE'}")
        print("="*70)
        print()

        if not self.source_dir.exists():
            print(f"ERROR: Source directory not found: {self.source_dir}")
            return False

        # Find all batch files
        batch_files = self.find_batch_files()

        if not batch_files:
            print("No batch files found to update")
            return True

        print()

        # Update each batch file
        for bat_file in batch_files:
            self.update_batch_file(bat_file)

        # Print summary
        self.print_summary()

        return len(self.errors) == 0


def main():
    parser = argparse.ArgumentParser(
        description="Update IntelliSTOR batch files to use air-gap Python",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview changes without modifying files
  python update_batch_files.py --dry-run

  # Apply updates
  python update_batch_files.py

  # Specify custom source directory
  python update_batch_files.py --source-dir C:\\IntelliSTOR_Migration

  # Restore original files from backups
  python update_batch_files.py --restore
        """
    )

    parser.add_argument(
        "--source-dir",
        type=str,
        help="Path to IntelliSTOR_Migration source directory"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes"
    )

    parser.add_argument(
        "--restore",
        action="store_true",
        help="Restore batch files from .backup copies"
    )

    args = parser.parse_args()

    # Determine source directory
    if args.source_dir:
        source_dir = Path(args.source_dir)
    else:
        # Default: ../08_SOURCE_CODE/IntelliSTOR_Migration
        script_dir = Path(__file__).parent
        source_dir = script_dir.parent / "08_SOURCE_CODE" / "IntelliSTOR_Migration"

        # If that doesn't exist, try current directory
        if not source_dir.exists():
            source_dir = Path.cwd()

    updater = BatchFileUpdater(source_dir, dry_run=args.dry_run)

    if args.restore:
        # Restore mode
        print("="*70)
        print("IntelliSTOR Batch File Restore")
        print("="*70)
        print(f"Source directory: {source_dir}")
        print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE RESTORE'}")
        print("="*70)
        print()

        restored = updater.restore_backups()

        print("\n" + "="*70)
        print("RESTORE SUMMARY")
        print("="*70)
        print(f"Restored {restored} files")
        if args.dry_run:
            print("\nDRY RUN - No files were modified")
            print("Run without --dry-run to restore from backups")
        print()

        sys.exit(0)

    # Normal update mode
    success = updater.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
