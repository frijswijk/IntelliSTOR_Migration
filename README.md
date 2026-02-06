# IntelliSTOR Migration Tools

A comprehensive suite of Python scripts and batch files for migrating IntelliSTOR database systems between environments (Singapore and Malaysia).

## Overview

This project provides automated tools for extracting, transforming, and packaging data from IntelliSTOR databases. The migration process handles users, permissions, report species, instances, AFP resources, and test file generation with encryption.

## Project Structure

```
IntelliSTOR_Migration/
├── Migration_Environment.bat          # Central configuration file
├── 1_Migration_Users/                 # User and permission extraction
├── 2_LDAP/                           # LDAP/Active Directory integration
├── 3_Migration_Report_Species_Folders/# Report species extraction
├── 4_Migration_Instances/           # Instance extraction from database
├── 5_TestFileGeneration/            # Test data file generation
├── 6_ZipEncrypt/                    # Batch encryption and archiving
├── 7_AFP_Resources/                 # AFP resource analysis and export
├── 8_Create_IRPT_File/               # RPT file builder tool
├── ACL/                              # Access Control List parsing
└── 99_Report_TXT_Viewer/             # Report viewer application
```

## Migration Workflow

The migration follows this sequence:

1. **Extract Users & Permissions** - Extract user accounts and access rights
2. **LDAP Integration** - Sync with Active Directory (optional)
3. **Extract Report Species** - Identify report types and folder structures
4. **Extract Instances** - Pull report instances from database
5. **Generate Test Files** - Create sample test data
6. **Analyze AFP Resources** - Export AFP resource files
7. **Zip & Encrypt** - Package and secure files for transfer

## Key Features

- **Centralized Configuration**: Update `Migration_Environment.bat` once for all scripts
- **Dual Country Support**: Separate workflows for Singapore (SG) and Malaysia (MY)
- **Execution Logging**: All batch files track execution time and status
- **Resume Capability**: Can resume interrupted operations
- **Automatic Directory Creation**: Creates output folders as needed
- **LDAP/AD Integration**: Full Active Directory synchronization with SSL/TLS support
- **AFP Resource Management**: Version tracking and resource extraction
- **Password-Protected Archives**: Secure 7z encryption with configurable compression

## Python Modules

### Migration Scripts
- `Extract_Users_Permissions.py` - User extraction from database
- `Extract_Folder_Species.py` - Report species identification
- `Extract_Instances.py` - Instance data extraction
- `Generate_Test_Files.py` - Test data generation
- `batch_zip_encrypt.py` - Archive encryption utility
- `AFP_Resource_Exporter.py` - AFP resource export
- `Analyze_AFP_Resources.py` - AFP resource analysis

### LDAP Integration (2_LDAP/)
- `ldap_integration.py` - Core LDAP functionality
- `test_ldaps_sync.py` - LDAP sync testing
- `test_ssl_direct.py` - SSL connection testing
- `test_starttls.py` - STARTTLS testing
- `check_port_636.py` - LDAPS port verification

### Utilities
- `parse_acl.py` - ACL parsing (simple & advanced)
- `test_connection.py` - Database connection testing

## Quick Start

### 1. Configure Environment

Edit `Migration_Environment.bat` to set your paths:

```batch
set Migration_data=D:\_IntelliSTOR_Migration\Migration_data
set SQL-SG-Server=localhost
set SQL-SG-Database=iSTSGUAT
set SQL-MY-Server=localhost
set SQL-MY-Database=iSTMYUAT
```

### 2. Run Migration (Singapore Example)

```batch
# Step 1: Extract users
cd 1_Migration_Users
Extract_Users_permissions_SG.bat

# Step 2: Extract instances
cd ..\4_Migration_Instances
Extract_Instances.SG.bat

# Step 3: Generate test files
cd ..\5_TestFileGeneration
Generate_Test_Files_SG.bat

# Step 4: Encrypt and package
cd ..\6_ZipEncrypt
Batch_Zip_Encrypt_SG.bat
```

### 3. LDAP Setup (Optional)

See `2_LDAP/LDAP_QUICKSTART.md` for Active Directory integration.

## Requirements

- Python 3.8+
- SQL Server with Windows Authentication or SQL credentials
- 7-Zip (for encryption scripts)
- LDAP libraries: `python-ldap`, `ldap3` (for LDAP features)

### Python Dependencies

```bash
pip install pyodbc pandas python-ldap ldap3
```

## Database Schema

The project includes a complete database schema explorer:
- `IntelliSTOR_DB_Explorer.html` - Interactive schema browser
- `DB_SCHEMA.csv` - Complete table and column definitions

## Documentation

Each module has detailed documentation:

- **User Migration**: `1_Migration_Users/README_Extract_Users_Permissions.md`
- **LDAP Setup**: `2_LDAP/LDAP_IMPLEMENTATION_SUMMARY.md`
- **LDAP Quick Start**: `2_LDAP/LDAP_QUICKSTART.md`
- **AD Server Setup**: `2_LDAP/AD_SERVER_LDAPS_SETUP_GUIDE.md`
- **Report Species**: `3_Migration_Report_Species_Folders/README_Extract_Folder_Species.md`
- **Instance Extraction**: `4_Migration_Instances/SETUP_GUIDE.md`
- **Test File Generation**: `5_TestFileGeneration/README_Generate_Test_Files.md`
- **Zip Encryption**: `6_ZipEncrypt/README_batch_zip_encrypt.md`
- **AFP Resources**: `7_AFP_Resources/README.md`
- **ACL Parsing**: `ACL/README_ACL_Parsing.md`
- **Report Viewer**: `99_Report_TXT_Viewer/Report_Viewer_README.md`
- **Batch Updates**: `BATCH_FILES_UPDATE_SUMMARY.md`

## Execution Logs

Each batch file creates execution logs in the format:
```
[26-01-2026 14:15:32] Country: SG | DB: iSTSGUAT | Duration: 00:03:13
```

Log files: `*_LOG.txt` in each module directory.

## Migration to New Machine

1. Update `Migration_Environment.bat` with new paths
2. Install Python dependencies
3. Configure database connections
4. Run test scripts to verify connectivity
5. Execute migration workflow

See `BATCH_FILES_UPDATE_SUMMARY.md` for detailed migration instructions.

## Architecture

- **Database Layer**: SQL Server connectivity via pyodbc
- **Processing Layer**: Python scripts for data transformation
- **Integration Layer**: LDAP/AD synchronization
- **Packaging Layer**: Batch encryption and archiving
- **Execution Layer**: Windows batch orchestration

## Security

- **Password Protection**: All archives encrypted with 7z AES-256
- **LDAPS Support**: Secure LDAP over SSL/TLS
- **SQL Authentication**: Supports Windows Auth and SQL credentials
- **ACL Preservation**: Maintains access control lists during migration

## Testing

Test utilities included:
- `test_connection.py` - Verify database connectivity
- `test_ldaps_sync.py` - Test LDAP synchronization
- `test_ssl_direct.py` - Validate SSL connections
- See `2_LDAP/QUICK_TEST_GUIDE.md` for testing procedures

## Version History

- **v2.2** - Added new features for AFP and encryption
- **v2.1** - Bug fixes and performance improvements
- **v2.0** - Major refactor with centralized configuration
- **v1.0** - Initial release

See individual module documentation for detailed changelogs.

## Support

For issues or questions:
- Check module-specific README files
- Review execution logs (*_LOG.txt)
- Verify `Migration_Environment.bat` configuration

## License

Proprietary - OCBC IntelliSTOR Migration Project

## Author

Created for OCBC IntelliSTOR Migration
Last Updated: 2026-01-28
