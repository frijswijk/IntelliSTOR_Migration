#!/usr/bin/env python3
"""
Air-Gap Package Builder for IntelliSTOR Migration Tools

This script creates a complete offline installation package for deployment
to air-gapped banking environments. It downloads Python embeddable distribution,
all required dependencies, and packages the source code.

Usage:
    python build_airgap_package.py [--python-version 3.11.7] [--output-dir ../]
"""

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import urllib.request
from datetime import datetime
from pathlib import Path


class AirGapPackageBuilder:
    """Builds complete air-gap installation packages"""

    PYTHON_VERSION = "3.11.7"
    PYTHON_MAJOR_MINOR = "3.11"

    def __init__(self, output_dir: Path, python_version: str = None):
        self.output_dir = Path(output_dir).resolve()
        self.python_version = python_version or self.PYTHON_VERSION
        self.python_major_minor = ".".join(self.python_version.split(".")[:2])

        # Directory structure
        self.dirs = {
            "root": self.output_dir,
            "builder": self.output_dir / "02_PACKAGE_BUILDER",
            "installer": self.output_dir / "03_OFFLINE_INSTALLER",
            "python": self.output_dir / "04_PYTHON_EMBEDDED",
            "wheels": self.output_dir / "05_WHEELS",
            "dlls": self.output_dir / "06_DLLS",
            "tools": self.output_dir / "07_EXTERNAL_TOOLS",
            "source": self.output_dir / "08_SOURCE_CODE"
        }

        self.manifest = {
            "package_name": "IntelliSTOR_AirGap_Package",
            "version": "1.0.0",
            "build_date": datetime.now().isoformat(),
            "python_version": self.python_version,
            "platform": "win_amd64",
            "builder_platform": platform.platform(),
            "dependencies": {},
            "files": {},
            "checksums": {}
        }

    def create_directory_structure(self):
        """Create the complete directory structure"""
        print("Creating directory structure...")
        for name, path in self.dirs.items():
            path.mkdir(parents=True, exist_ok=True)
            print(f"  ✓ {name}: {path.relative_to(self.output_dir)}")

    def download_file(self, url: str, destination: Path, description: str = None) -> bool:
        """Download a file with progress indication"""
        desc = description or destination.name
        print(f"Downloading {desc}...")
        print(f"  URL: {url}")
        print(f"  Destination: {destination}")

        try:
            with urllib.request.urlopen(url) as response:
                total_size = int(response.headers.get('content-length', 0))
                block_size = 8192
                downloaded = 0

                with open(destination, 'wb') as f:
                    while True:
                        block = response.read(block_size)
                        if not block:
                            break
                        f.write(block)
                        downloaded += len(block)

                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"  Progress: {percent:.1f}% ({downloaded:,} / {total_size:,} bytes)", end='\r')

                print(f"\n  ✓ Downloaded successfully: {destination.name}")
                return True

        except Exception as e:
            print(f"\n  ✗ Download failed: {e}")
            return False

    def download_python_embeddable(self) -> bool:
        """Download Python embeddable distribution"""
        print("\n" + "="*70)
        print("STEP 1: Downloading Python Embeddable Distribution")
        print("="*70)

        version_nodot = self.python_version.replace(".", "")
        filename = f"python-{self.python_version}-embed-amd64.zip"
        url = f"https://www.python.org/ftp/python/{self.python_version}/{filename}"
        destination = self.dirs["python"] / filename

        if destination.exists():
            print(f"Python embeddable already exists: {filename}")
            return True

        success = self.download_file(url, destination, "Python Embeddable")

        if success:
            self.manifest["files"]["python_embeddable"] = filename
            self.manifest["checksums"][filename] = self._calculate_checksum(destination)

        return success

    def download_get_pip(self) -> bool:
        """Download get-pip.py for offline pip installation"""
        print("\n" + "="*70)
        print("STEP 2: Downloading get-pip.py")
        print("="*70)

        url = "https://bootstrap.pypa.io/get-pip.py"
        destination = self.dirs["python"] / "get-pip.py"

        if destination.exists():
            print(f"get-pip.py already exists")
            return True

        success = self.download_file(url, destination, "get-pip.py")

        if success:
            self.manifest["files"]["get_pip"] = "get-pip.py"
            self.manifest["checksums"]["get-pip.py"] = self._calculate_checksum(destination)

        return success

    def download_wheels(self) -> bool:
        """Download all Python package wheels and dependencies"""
        print("\n" + "="*70)
        print("STEP 3: Downloading Python Package Wheels")
        print("="*70)

        requirements_file = self.dirs["builder"] / "requirements_full.txt"

        if not requirements_file.exists():
            print(f"ERROR: Requirements file not found: {requirements_file}")
            return False

        print(f"Using requirements file: {requirements_file}")
        print(f"Download destination: {self.dirs['wheels']}")
        print("\nDownloading wheels (this may take several minutes)...")

        try:
            # Use pip download to get all wheels
            cmd = [
                sys.executable, "-m", "pip", "download",
                "-r", str(requirements_file),
                "-d", str(self.dirs["wheels"]),
                "--platform", "win_amd64",
                "--python-version", self.python_major_minor.replace(".", ""),
                "--only-binary", ":all:",
                "--no-deps"  # We'll resolve deps in a second pass
            ]

            print(f"\nCommand: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                print("\nFirst pass completed, now downloading with dependencies...")
                # Second pass: get all dependencies
                cmd = [
                    sys.executable, "-m", "pip", "download",
                    "-r", str(requirements_file),
                    "-d", str(self.dirs["wheels"]),
                    "--platform", "win_amd64",
                    "--python-version", self.python_major_minor.replace(".", ""),
                    "--only-binary", ":all:"
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)

            print(result.stdout)
            if result.stderr:
                print("Warnings/Errors:", result.stderr)

            if result.returncode == 0:
                # List downloaded wheels
                wheels = list(self.dirs["wheels"].glob("*.whl"))
                print(f"\n✓ Downloaded {len(wheels)} wheel files:")

                for wheel in sorted(wheels):
                    size_mb = wheel.stat().st_size / (1024 * 1024)
                    print(f"  - {wheel.name} ({size_mb:.2f} MB)")
                    self.manifest["checksums"][wheel.name] = self._calculate_checksum(wheel)

                self.manifest["dependencies"]["wheels_count"] = len(wheels)
                return True
            else:
                print("\n✗ Wheel download failed")
                return False

        except Exception as e:
            print(f"\n✗ Error downloading wheels: {e}")
            return False

    def copy_source_code(self) -> bool:
        """Copy IntelliSTOR source code to package"""
        print("\n" + "="*70)
        print("STEP 4: Copying Source Code")
        print("="*70)

        # Source is the parent directory of the package builder
        source_root = self.dirs["builder"].parent
        dest_root = self.dirs["source"] / "IntelliSTOR_Migration"

        print(f"Source: {source_root}")
        print(f"Destination: {dest_root}")

        # Directories and files to exclude
        exclude_dirs = {
            ".git", "__pycache__", ".claude", "Migration_data",
            "02_PACKAGE_BUILDER", "03_OFFLINE_INSTALLER", "04_PYTHON_EMBEDDED",
            "05_WHEELS", "06_DLLS", "07_EXTERNAL_TOOLS", "08_SOURCE_CODE",
            ".pytest_cache", ".venv", "venv", "env"
        }

        exclude_extensions = {".pyc", ".pyo", ".pyd", ".so", ".dll"}

        copied_files = 0
        copied_dirs = 0

        try:
            for item in source_root.rglob("*"):
                # Skip excluded directories
                if any(excluded in item.parts for excluded in exclude_dirs):
                    continue

                # Skip excluded extensions
                if item.suffix in exclude_extensions:
                    continue

                # Calculate relative path
                rel_path = item.relative_to(source_root)
                dest_path = dest_root / rel_path

                if item.is_dir():
                    dest_path.mkdir(parents=True, exist_ok=True)
                    copied_dirs += 1
                elif item.is_file():
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest_path)
                    copied_files += 1

                    # Add to manifest for key files
                    if item.suffix in {".py", ".bat", ".md", ".txt", ".json"}:
                        rel_manifest_path = str(rel_path).replace("\\", "/")
                        self.manifest["checksums"][rel_manifest_path] = self._calculate_checksum(item)

            print(f"\n✓ Copied {copied_files} files and {copied_dirs} directories")
            self.manifest["source_files"] = copied_files
            return True

        except Exception as e:
            print(f"\n✗ Error copying source code: {e}")
            return False

    def create_dll_readme(self):
        """Create README for DLL handling"""
        print("\n" + "="*70)
        print("STEP 5: Creating DLL Documentation")
        print("="*70)

        readme_content = """# Visual C++ Runtime DLLs

## Overview

The `pymssql` package requires Visual C++ Redistributable DLLs to function correctly.
Most Windows systems (Windows 10/11, Windows Server 2016+) already have these installed.

## Required DLLs

- `vcruntime140.dll` - Visual C++ Runtime
- `msvcp140.dll` - C++ Standard Library
- `vcruntime140_1.dll` - Additional runtime (x64 only)

## Installation Options

### Option 1: Use System Installation (Recommended)

Most Windows systems already have Visual C++ Redistributable installed.
Try the air-gap installation first without additional steps.

To verify if installed:
1. Open Command Prompt
2. Run: `where vcruntime140.dll`
3. If found, no action needed

### Option 2: Install Redistributable Package

Download and install the official redistributable from Microsoft:
- **Package**: Visual C++ Redistributable for Visual Studio 2015-2022
- **File**: `vc_redist.x64.exe`
- **Link**: https://aka.ms/vs/17/release/vc_redist.x64.exe

Installation:
```batch
vc_redist.x64.exe /install /quiet /norestart
```

### Option 3: Bundle DLLs Manually

If you cannot install the redistributable, copy the DLLs manually:

1. **Locate DLLs on a system that has them:**
   - Check: `C:\\Windows\\System32\\`
   - Or: `C:\\Program Files\\Microsoft Visual Studio\\...`

2. **Copy to this directory** (`06_DLLS/`):
   - `vcruntime140.dll`
   - `msvcp140.dll`
   - `vcruntime140_1.dll`

3. **During installation**, these will be copied to the Python directory

## Verification

After installation, test if DLLs are accessible:

```batch
python -c "import pymssql; print('pymssql loaded successfully')"
```

If you see "DLL load failed", the Visual C++ Runtime is missing.

## Security Note

All DLLs should be sourced from:
1. Official Microsoft redistributable packages (preferred)
2. Existing Windows system directories
3. Official Visual Studio installations

Never download DLLs from third-party websites.

## Troubleshooting

### Error: "DLL load failed while importing pymssql"
- **Cause**: Missing Visual C++ Redistributable
- **Solution**: Install via Option 2 or copy DLLs via Option 3

### Error: "The code execution cannot proceed because vcruntime140.dll was not found"
- **Cause**: DLLs not in PATH or Python directory
- **Solution**: Copy DLLs to Python directory or install redistributable

### System has x86 DLLs but needs x64
- **Cause**: Architecture mismatch
- **Solution**: Install x64 redistributable (`vc_redist.x64.exe`)
"""

        readme_path = self.dirs["dlls"] / "README_DLLS.md"
        readme_path.write_text(readme_content, encoding="utf-8")
        print(f"✓ Created: {readme_path}")

    def download_7zip(self) -> bool:
        """Create documentation for 7-Zip (optional download)"""
        print("\n" + "="*70)
        print("STEP 6: 7-Zip Documentation")
        print("="*70)

        print("7-Zip is required for project 6 (ZipEncrypt)")
        print("Due to licensing, automatic download is optional.")
        print("\nCreating documentation...")

        readme_content = """# 7-Zip for IntelliSTOR Migration Tools

## Overview

Project 6 (ZipEncrypt) requires 7-Zip for creating encrypted archives.

## Download 7-Zip

**Official Website**: https://www.7-zip.org/

### Recommended Download

- **Version**: 7-Zip 23.01 (or later)
- **Architecture**: x64 (64-bit)
- **Installer**: `7z2301-x64.exe`
- **Download**: https://www.7-zip.org/a/7z2301-x64.exe

### Installation Options

#### Option 1: Standard Installation (Requires Admin)
1. Download `7z2301-x64.exe`
2. Run installer
3. Install to: `C:\\Program Files\\7-Zip\\`
4. 7z.exe will be at: `C:\\Program Files\\7-Zip\\7z.exe`

#### Option 2: Portable Installation (No Admin)
1. Download `7z2301-x64.exe`
2. Extract using: `7z2301-x64.exe /S /D=C:\\Path\\To\\7-Zip`
3. Or: Extract contents to `07_EXTERNAL_TOOLS\\7-Zip\\`
4. Update `Migration_Environment.bat` with path

## Integration with Migration Tools

The path to 7z.exe is configured in `Migration_Environment.bat`:

```batch
SET SEVEN_ZIP=C:\\Program Files\\7-Zip\\7z.exe
```

If you use a different installation path, update this variable.

## Verification

Test 7-Zip installation:

```batch
"C:\\Program Files\\7-Zip\\7z.exe" --help
```

Expected output: 7-Zip version information and usage instructions

## Usage in Migration Tools

Project 6 (ZipEncrypt) uses 7-Zip for encrypted archive creation:

```batch
7z.exe a -t7z -p[PASSWORD] -mhe=on archive.7z file1 file2
```

Parameters:
- `a` - Add to archive
- `-t7z` - Archive type (7z format)
- `-p[PASSWORD]` - Set password (encrypts filenames too with -mhe)
- `-mhe=on` - Encrypt headers (hides filenames)

## License

7-Zip is free software licensed under GNU LGPL.
See: https://www.7-zip.org/license.txt

## Alternative: Use Existing Installation

If the target environment already has 7-Zip installed, simply update
the `SEVEN_ZIP` variable in `Migration_Environment.bat` to point to
the existing installation.
"""

        readme_path = self.dirs["tools"] / "README_7ZIP.md"
        readme_path.write_text(readme_content, encoding="utf-8")
        print(f"✓ Created: {readme_path}")

        return True

    def save_manifest(self):
        """Save the package manifest with checksums"""
        print("\n" + "="*70)
        print("STEP 7: Generating Package Manifest")
        print("="*70)

        manifest_path = self.dirs["root"] / "MANIFEST.json"

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(self.manifest, f, indent=2, sort_keys=True)

        print(f"✓ Manifest saved: {manifest_path}")
        print(f"\nManifest Summary:")
        print(f"  Package: {self.manifest['package_name']} v{self.manifest['version']}")
        print(f"  Python: {self.manifest['python_version']}")
        print(f"  Platform: {self.manifest['platform']}")
        print(f"  Build Date: {self.manifest['build_date']}")
        print(f"  Source Files: {self.manifest.get('source_files', 0)}")
        print(f"  Wheel Files: {self.manifest['dependencies'].get('wheels_count', 0)}")
        print(f"  Total Checksums: {len(self.manifest['checksums'])}")

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of a file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def build(self) -> bool:
        """Execute the complete build process"""
        print("\n" + "="*70)
        print("IntelliSTOR Air-Gap Package Builder")
        print("="*70)
        print(f"Output Directory: {self.output_dir}")
        print(f"Python Version: {self.python_version}")
        print(f"Platform: win_amd64")
        print("="*70)

        steps = [
            ("Create directory structure", self.create_directory_structure),
            ("Download Python embeddable", self.download_python_embeddable),
            ("Download get-pip.py", self.download_get_pip),
            ("Download wheel packages", self.download_wheels),
            ("Copy source code", self.copy_source_code),
            ("Create DLL documentation", self.create_dll_readme),
            ("Create 7-Zip documentation", self.download_7zip),
            ("Save manifest", self.save_manifest),
        ]

        for step_name, step_func in steps:
            try:
                result = step_func()
                if result is False:
                    print(f"\n✗ FAILED: {step_name}")
                    return False
            except Exception as e:
                print(f"\n✗ FAILED: {step_name}")
                print(f"Error: {e}")
                import traceback
                traceback.print_exc()
                return False

        print("\n" + "="*70)
        print("✓ AIR-GAP PACKAGE BUILD COMPLETE")
        print("="*70)
        print(f"\nPackage location: {self.output_dir}")
        print("\nNext steps:")
        print("1. Review the generated package structure")
        print("2. Optionally add DLLs to 06_DLLS/ directory")
        print("3. Optionally add 7-Zip to 07_EXTERNAL_TOOLS/ directory")
        print("4. Transfer entire package to air-gap environment")
        print("5. Run 03_OFFLINE_INSTALLER/install_airgap_python.bat")
        print("\nSee 00_README_INSTALLATION.md for detailed instructions.")

        return True


def main():
    parser = argparse.ArgumentParser(
        description="Build air-gap installation package for IntelliSTOR Migration Tools"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="..",
        help="Output directory for the package (default: parent directory)"
    )
    parser.add_argument(
        "--python-version",
        type=str,
        default="3.11.7",
        help="Python version to download (default: 3.11.7)"
    )

    args = parser.parse_args()

    # Resolve output directory
    script_dir = Path(__file__).parent
    output_dir = (script_dir / args.output_dir).resolve()

    builder = AirGapPackageBuilder(output_dir, args.python_version)
    success = builder.build()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
