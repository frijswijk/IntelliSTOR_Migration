# IntelliSTOR Air-Gap Installation Package

Complete offline Python environment for IntelliSTOR Migration Tools deployment in air-gapped banking environments.

## Quick Start

### On Internet-Connected Machine (Build Package)

```batch
cd 02_PACKAGE_BUILDER
download_dependencies.bat
```

Transfer entire package to air-gap machine.

### On Air-Gap Machine (Install)

```batch
cd 03_OFFLINE_INSTALLER
install_airgap_python.bat
```

### Verify Installation

```batch
%AIRGAP_PYTHON% verify_installation.py
```

## Package Structure

```
IntelliSTOR_AirGap_Package/
├── 00_README_INSTALLATION.md          # Detailed installation guide
├── 01_SECURITY_DOCUMENTATION.md       # Security and compliance docs
├── README.md                          # Main project README
├── README_AIRGAP_PACKAGE.md           # This file
├── MANIFEST.json                      # Package manifest (generated)
│
├── 02_PACKAGE_BUILDER/                # Build scripts (internet machine)
│   ├── build_airgap_package.py        # Main packaging script
│   ├── requirements_full.txt          # Python dependencies
│   └── download_dependencies.bat      # Windows wrapper
│
├── 03_OFFLINE_INSTALLER/              # Installation scripts (air-gap)
│   ├── install_airgap_python.bat      # Main installer
│   ├── verify_installation.py         # Verification script
│   ├── update_batch_files.py          # Batch file updater
│   └── uninstall_airgap.bat           # Uninstaller
│
├── 04_PYTHON_EMBEDDED/                # Python distribution (downloaded)
│   ├── python-3.11.7-embed-amd64.zip
│   └── get-pip.py
│
├── 05_WHEELS/                         # Python packages (downloaded)
│   └── *.whl files
│
├── 06_DLLS/                           # Visual C++ Runtime
│   └── README_DLLS.md
│
├── 07_EXTERNAL_TOOLS/                 # External tools
│   └── README_7ZIP.md
│
├── 08_SOURCE_CODE/                    # IntelliSTOR source (copied)
│   └── IntelliSTOR_Migration/
│       ├── Migration_Environment.bat
│       ├── python_launcher.bat
│       ├── 1_Migration_Users/
│       ├── 2_LDAP/
│       ├── 3_Migration_Report_Species_Folders/
│       ├── 4. Migration_Instances/
│       ├── 5. TestFileGeneration/
│       ├── 6. ZipEncrypt/
│       ├── 7. AFP_Resources/
│       └── ACL/
│
└── IntelliSTOR_Python/                # Installation directory (created)
    └── python/
        └── python.exe
```

## Key Features

- **Complete Offline Installation**: No internet required on target machine
- **No Admin Rights**: Installs to user directory
- **Portable**: Self-contained Python environment
- **Verified**: SHA-256 checksums for all files
- **Secure**: Full source code included for audit
- **Automated**: One-click installation and verification

## System Requirements

- Windows 10+ or Windows Server 2016+
- x64 (64-bit) architecture
- 200 MB disk space
- Standard user account (no admin required)

## Dependencies

### Python Packages
- **pymssql** 2.2.8+ - SQL Server connectivity
- **ldap3** 2.9.1+ - LDAP/Active Directory integration
- **Flask** 2.3.0+ - Web framework for LDAP browser
- **Flask-CORS** 4.0.0+ - CORS support

### External Tools (Optional)
- **Visual C++ Redistributable** - Required for pymssql
- **7-Zip** - Required for Project 6 (ZipEncrypt) only

## Documentation

- **00_README_INSTALLATION.md** - Complete installation instructions
- **01_SECURITY_DOCUMENTATION.md** - Security audit and compliance
- **06_DLLS/README_DLLS.md** - Visual C++ Runtime handling
- **07_EXTERNAL_TOOLS/README_7ZIP.md** - 7-Zip installation
- **README.md** - Main IntelliSTOR Migration Tools documentation

## Usage Example

After installation:

```batch
REM Configure environment
cd 08_SOURCE_CODE\IntelliSTOR_Migration
call Migration_Environment.bat

REM Test database connection
cd "4. Migration_Instances"
%AIRGAP_PYTHON% test_connection.py

REM Run user extraction
cd ..\1_Migration_Users
Extract_Users_permissions_SG.bat
```

## Support

For detailed instructions, troubleshooting, and security information, see:
- `00_README_INSTALLATION.md` - Installation guide
- `01_SECURITY_DOCUMENTATION.md` - Security documentation

## License

This package includes open-source software:
- Python 3.11.7 - PSF License
- pymssql - LGPL v2.1
- ldap3 - LGPL v3
- Flask - BSD-3-Clause
- Flask-CORS - MIT

See individual package documentation for complete license information.

## Version

- **Package Version**: 1.0.0
- **Python Version**: 3.11.7
- **Platform**: Windows x64
- **Build Date**: 2026-01-28
