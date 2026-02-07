# IntelliSTOR Air-Gap Installation Guide

## Overview

This package provides a complete offline installation of Python and all dependencies required for the IntelliSTOR Migration Tools. It is designed for deployment in air-gapped banking environments where internet access is restricted or prohibited.

**Package Contents:**
- Python 3.11.7 Embeddable Distribution (Windows x64)
- All required Python packages (pymssql, ldap3, Flask, Flask-CORS)
- IntelliSTOR Migration Tools source code
- Installation and verification scripts
- Documentation and troubleshooting guides

## System Requirements

### Minimum Requirements
- **Operating System**: Windows 10 or Windows Server 2016 (or later)
- **Architecture**: x64 (64-bit)
- **Disk Space**: 200 MB (installation) + space for migration data
- **Memory**: 2 GB RAM minimum, 4 GB recommended
- **Permissions**: Standard user (no admin rights required)

### Optional Requirements
- **Visual C++ Redistributable 2015-2022** (for SQL Server connectivity)
- **7-Zip** (for encrypted archive creation - Project 6 only)
- **SQL Server** (for database connectivity testing)
- **Active Directory/LDAP** (for LDAP browser - Project 2 only)

## Pre-Installation Checklist

Before beginning installation in the air-gap environment:

1. ✅ **Verify package integrity**
   - Check that all directories exist (02-08)
   - Verify `MANIFEST.json` exists
   - Confirm wheel files exist in `05_WHEELS/`

2. ✅ **Check system compatibility**
   - Confirm Windows version (Win 10+ or Server 2016+)
   - Verify x64 architecture: `wmic os get osarchitecture`
   - Check available disk space: `dir C:\` (need 200+ MB)

3. ✅ **Prepare installation location**
   - Choose installation directory (default: `IntelliSTOR_Python`)
   - Ensure write permissions to installation location
   - No existing Python installation required

4. ✅ **Review security documentation**
   - See `01_SECURITY_DOCUMENTATION.md`
   - Share with IT security/audit team if required

## Installation Instructions

### Step 1: Transfer Package to Air-Gap Environment

**On the internet-connected machine:**

1. Build the package (if not already built):
   ```batch
   cd 02_PACKAGE_BUILDER
   download_dependencies.bat
   ```

2. Transfer the entire package directory to the air-gap machine:
   - Use approved file transfer methods (USB drive, secure file transfer)
   - Transfer the complete directory structure
   - Verify file integrity after transfer

**On the air-gap machine:**

3. Extract the package to a working directory:
   ```batch
   C:\Temp\IntelliSTOR_AirGap_Package\
   ```

### Step 2: Run Installation Script

1. Open Command Prompt (standard user, no admin required)

2. Navigate to the installer directory:
   ```batch
   cd C:\Temp\IntelliSTOR_AirGap_Package\03_OFFLINE_INSTALLER
   ```

3. Run the installation script:
   ```batch
   install_airgap_python.bat
   ```

   Or specify a custom installation path:
   ```batch
   install_airgap_python.bat C:\MyCustomPath\IntelliSTOR_Python
   ```

4. Follow the on-screen prompts:
   - Review the configuration
   - Confirm installation when prompted
   - Wait for extraction and package installation (~2-5 minutes)
   - Review verification results

### Step 3: Verify Installation

The installation script automatically runs verification, but you can run it manually:

```batch
cd C:\Temp\IntelliSTOR_AirGap_Package\IntelliSTOR_Python\python
python.exe ..\..\03_OFFLINE_INSTALLER\verify_installation.py
```

**Expected output:**
- ✓ Python version check passed
- ✓ pip installed
- ✓ Standard library modules available
- ✓ pymssql installed (database connectivity)
- ✓ ldap3 installed (LDAP support)
- ✓ Flask and Flask-CORS installed (web interface)
- ⚠ 7-Zip warning (optional, only needed for Project 6)

### Step 4: Configure Database Connection

1. Navigate to the source directory:
   ```batch
   cd 08_SOURCE_CODE\IntelliSTOR_Migration
   ```

2. Edit `Migration_Environment.bat`:
   ```batch
   notepad Migration_Environment.bat
   ```

3. Update the database connection settings:
   ```batch
   REM -- Database Configuration --
   SET SQLServer=your-sql-server.company.com
   SET SQLDatabase=IntelliSTOR
   SET SQLUsername=migration_user
   SET SQLPassword=YourSecurePassword
   ```

4. Verify the air-gap Python path is set:
   ```batch
   SET "AIRGAP_PYTHON=C:\...\IntelliSTOR_Python\python\python.exe"
   ```

### Step 5: Update Batch Files (Optional)

You can either manually update batch files or use the automated updater:

**Option A: Automated Update (Recommended)**

```batch
cd 03_OFFLINE_INSTALLER
%AIRGAP_PYTHON% update_batch_files.py --source-dir ..\08_SOURCE_CODE\IntelliSTOR_Migration

REM Preview changes first (dry run):
%AIRGAP_PYTHON% update_batch_files.py --dry-run --source-dir ..\08_SOURCE_CODE\IntelliSTOR_Migration
```

**Option B: Manual Update**

Replace `python` with `%AIRGAP_PYTHON%` in each batch file:

```batch
REM Before:
python Extract_Users_Permissions.py --server %SQLServer%

REM After:
%AIRGAP_PYTHON% Extract_Users_Permissions.py --server %SQLServer%
```

### Step 6: Test Database Connectivity

```batch
cd 08_SOURCE_CODE\IntelliSTOR_Migration\4. Migration_Instances
call ..\Migration_Environment.bat
%AIRGAP_PYTHON% test_connection.py
```

**Expected output:**
```
Connecting to SQL Server...
Connection successful!
```

### Step 7: Run First Migration Task

Test with the user extraction tool:

```batch
cd ..\1_Migration_Users
Extract_Users_permissions_SG_Testdata.bat
```

**Expected output:**
- CSV files created in `Migration_data/` directory
- No Python errors
- Database connection successful

## Post-Installation Configuration

### Visual C++ Runtime (Required for pymssql)

If you see "DLL load failed" errors when using pymssql:

**Option 1: Install Redistributable (Recommended)**
1. Download from Microsoft: `vc_redist.x64.exe`
   - https://aka.ms/vs/17/release/vc_redist.x64.exe
2. Install: `vc_redist.x64.exe /install /quiet /norestart`

**Option 2: Copy DLLs Manually**
1. Locate DLLs on a system that has them:
   - `C:\Windows\System32\vcruntime140.dll`
   - `C:\Windows\System32\msvcp140.dll`
   - `C:\Windows\System32\vcruntime140_1.dll`
2. Copy to Python directory:
   - `IntelliSTOR_Python\python\`

See `06_DLLS/README_DLLS.md` for detailed instructions.

### 7-Zip Installation (Optional - Project 6 Only)

**Only required for Project 6 (ZipEncrypt)**

1. Download 7-Zip from: https://www.7-zip.org/
2. Install or extract to: `C:\Program Files\7-Zip\`
3. Update `Migration_Environment.bat`:
   ```batch
   SET SEVEN_ZIP=C:\Program Files\7-Zip\7z.exe
   ```

See `07_EXTERNAL_TOOLS/README_7ZIP.md` for detailed instructions.

## Usage Guide

### Running Migration Tools

All migration tools are located in `08_SOURCE_CODE/IntelliSTOR_Migration/`

**Project Structure:**
```
IntelliSTOR_Migration/
├── Migration_Environment.bat       # Central configuration
├── 1_Migration_Users/              # User extraction
├── 2_LDAP/                         # LDAP browser
├── 3_Migration_Report_Species_Folders/  # Folder analysis
├── 4. Migration_Instances/         # Instance management
├── 5. TestFileGeneration/          # Test file creation
├── 6. ZipEncrypt/                  # Archive encryption
├── 7. AFP_Resources/               # AFP analysis
└── ACL/                            # ACL parsing
```

**Basic workflow:**

1. Configure environment:
   ```batch
   call Migration_Environment.bat
   ```

2. Run project-specific batch files:
   ```batch
   cd 1_Migration_Users
   Extract_Users_permissions_SG.bat
   ```

### Country-Specific Configurations

Use the country-specific batch files:
- `*_SG.bat` - Singapore configuration
- `*_MY.bat` - Malaysia configuration

These automatically load the correct environment settings.

## Troubleshooting

### Installation Issues

#### Error: "Python embeddable distribution not found"
**Cause:** Incomplete package transfer or extraction
**Solution:**
1. Verify `04_PYTHON_EMBEDDED/python-3.11.7-embed-amd64.zip` exists
2. Re-transfer the package if necessary
3. Check file integrity against `MANIFEST.json`

#### Error: "No wheel files found"
**Cause:** Missing dependencies in `05_WHEELS/`
**Solution:**
1. Verify `05_WHEELS/` directory contains `.whl` files
2. Rebuild package on internet machine if necessary
3. Re-transfer the complete package

#### Error: "Failed to extract Python"
**Cause:** PowerShell execution restricted or disk space
**Solution:**
1. Check disk space: `dir C:\` (need 200+ MB)
2. Check PowerShell execution policy: `Get-ExecutionPolicy`
3. Manually extract ZIP file using Windows Explorer

### Runtime Issues

#### Error: "ModuleNotFoundError: No module named 'pymssql'"
**Cause:** Python not finding installed packages (._pth file issue)
**Solution:**
1. Check `python311._pth` file contains:
   ```
   Lib\site-packages
   import site
   ```
2. Reinstall if necessary: `install_airgap_python.bat`

#### Error: "DLL load failed while importing pymssql"
**Cause:** Visual C++ Redistributable not installed
**Solution:**
1. Install VC++ Redistributable: `vc_redist.x64.exe`
2. Or copy DLLs manually (see section above)
3. See `06_DLLS/README_DLLS.md` for details

#### Error: "Cannot connect to SQL Server"
**Cause:** Database configuration or network issues
**Solution:**
1. Verify SQL Server hostname/IP in `Migration_Environment.bat`
2. Test network connectivity: `ping sql-server-name`
3. Check firewall rules (port 1433)
4. Verify SQL Server credentials
5. Run: `4. Migration_Instances\test_connection.py`

#### Error: "python is not recognized"
**Cause:** Using system Python instead of air-gap Python
**Solution:**
1. Ensure batch files use `%AIRGAP_PYTHON%` instead of `python`
2. Run `update_batch_files.py` to automate updates
3. Or manually update each batch file

#### Warning: "7-Zip not found"
**Cause:** 7-Zip not installed (only affects Project 6)
**Solution:**
1. Install 7-Zip from https://www.7-zip.org/
2. Update path in `Migration_Environment.bat`
3. See `07_EXTERNAL_TOOLS/README_7ZIP.md`

### Verification Issues

#### Error: "verify_installation.py failed"
**Cause:** One or more dependencies not installed correctly
**Solution:**
1. Review verification output for specific failures
2. Common issues:
   - Visual C++ Redistributable (pymssql)
   - 7-Zip (ZipEncrypt project only)
3. Reinstall specific packages:
   ```batch
   %AIRGAP_PYTHON% -m pip install --no-index --find-links=05_WHEELS --force-reinstall pymssql
   ```

## Security Considerations

### Network Isolation

This installation is designed to work completely offline:
- ✅ No internet access required during installation
- ✅ No outbound network connections made by Python
- ✅ All dependencies included in package
- ✅ No telemetry or analytics

### File Integrity

Verify package integrity using checksums:
```batch
REM Check MANIFEST.json for SHA-256 checksums
type MANIFEST.json
```

### Permissions

Installation does not require:
- ❌ Administrator privileges
- ❌ Registry modifications
- ❌ System-wide changes
- ❌ Kernel drivers

Installation only writes to:
- ✅ User-specified installation directory
- ✅ IntelliSTOR source code directory (for configuration)

### Sensitive Data

Best practices:
- 🔒 Store database credentials securely in `Migration_Environment.bat`
- 🔒 Restrict file permissions on configuration files
- 🔒 Use encrypted archives for data transfer (Project 6)
- 🔒 Follow company data handling policies

See `01_SECURITY_DOCUMENTATION.md` for complete security information.

## Maintenance

### Updating Python Packages

To update packages in the future:

1. On internet machine, rebuild package with updated `requirements_full.txt`
2. Transfer new package to air-gap environment
3. Reinstall:
   ```batch
   %AIRGAP_PYTHON% -m pip install --no-index --find-links=05_WHEELS --force-reinstall --upgrade pymssql
   ```

### Backup and Recovery

**Backup these files before making changes:**
- `Migration_Environment.bat` (configuration)
- All `.bat` files (if manually modified)
- Generated CSV files in `Migration_data/`

**To restore from backup:**
```batch
cd 03_OFFLINE_INSTALLER
%AIRGAP_PYTHON% update_batch_files.py --restore
```

### Uninstallation

To remove the air-gap Python installation:

1. Delete the Python directory:
   ```batch
   rmdir /S /Q C:\...\IntelliSTOR_Python
   ```

2. Restore original batch files:
   ```batch
   cd 03_OFFLINE_INSTALLER
   %AIRGAP_PYTHON% update_batch_files.py --restore
   ```

3. Remove air-gap configuration from `Migration_Environment.bat`:
   - Delete the `AIRGAP_PYTHON` line

## Support and Documentation

### Additional Documentation
- `01_SECURITY_DOCUMENTATION.md` - Security and compliance information
- `06_DLLS/README_DLLS.md` - Visual C++ Runtime DLL handling
- `07_EXTERNAL_TOOLS/README_7ZIP.md` - 7-Zip installation and usage
- `MANIFEST.json` - Package contents and checksums

### Project-Specific Documentation
Each project directory contains:
- `README.md` or documentation files
- Example batch files
- Test data (in some projects)

### Getting Help

For issues not covered in this guide:
1. Review project-specific documentation
2. Check `MANIFEST.json` for package integrity
3. Run `verify_installation.py` for diagnostic information
4. Contact your system administrator or IntelliSTOR support

## Appendix

### File Structure Reference

```
IntelliSTOR_AirGap_Package/
├── 00_README_INSTALLATION.md          # This file
├── 01_SECURITY_DOCUMENTATION.md       # Security documentation
├── MANIFEST.json                      # Package manifest
│
├── 02_PACKAGE_BUILDER/                # Build scripts (internet machine)
│   ├── build_airgap_package.py
│   ├── requirements_full.txt
│   └── download_dependencies.bat
│
├── 03_OFFLINE_INSTALLER/              # Installation scripts (air-gap machine)
│   ├── install_airgap_python.bat      # Main installer
│   ├── verify_installation.py         # Verification script
│   └── update_batch_files.py          # Batch file updater
│
├── 04_PYTHON_EMBEDDED/                # Python distribution
│   ├── python-3.11.7-embed-amd64.zip
│   └── get-pip.py
│
├── 05_WHEELS/                         # Python packages
│   └── *.whl files
│
├── 06_DLLS/                           # Visual C++ Runtime
│   └── README_DLLS.md
│
├── 07_EXTERNAL_TOOLS/                 # External tools
│   └── README_7ZIP.md
│
├── 08_SOURCE_CODE/                    # IntelliSTOR source
│   └── IntelliSTOR_Migration/
│
└── IntelliSTOR_Python/                # Installation directory (created)
    └── python/
        ├── python.exe
        ├── python311.dll
        ├── python311._pth
        ├── Lib/
        └── Scripts/
```

### Quick Reference Commands

**Installation:**
```batch
cd 03_OFFLINE_INSTALLER
install_airgap_python.bat
```

**Verification:**
```batch
%AIRGAP_PYTHON% verify_installation.py
```

**Update batch files:**
```batch
%AIRGAP_PYTHON% update_batch_files.py --source-dir ..\08_SOURCE_CODE\IntelliSTOR_Migration
```

**Test database:**
```batch
cd 08_SOURCE_CODE\IntelliSTOR_Migration\4. Migration_Instances
%AIRGAP_PYTHON% test_connection.py
```

**Run migration:**
```batch
cd 08_SOURCE_CODE\IntelliSTOR_Migration\1_Migration_Users
Extract_Users_permissions_SG.bat
```

---

**Document Version:** 1.0.0
**Last Updated:** 2026-01-28
**Python Version:** 3.11.7
**Platform:** Windows x64
