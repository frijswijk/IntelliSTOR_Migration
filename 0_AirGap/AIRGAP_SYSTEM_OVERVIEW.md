# IntelliSTOR Air-Gap System - Visual Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     INTERNET-CONNECTED MACHINE                       │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  02_PACKAGE_BUILDER/                                       │    │
│  │  ├── build_airgap_package.py  ◄─── Main build script      │    │
│  │  ├── download_dependencies.bat ◄─── Windows wrapper        │    │
│  │  └── requirements_full.txt    ◄─── Dependencies list       │    │
│  └────────────────────────────────────────────────────────────┘    │
│                            │                                         │
│                            │ Downloads from Internet:                │
│                            │ • Python 3.11.7 embeddable             │
│                            │ • get-pip.py                           │
│                            │ • All .whl packages                    │
│                            ▼                                         │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  GENERATED PACKAGE STRUCTURE                               │    │
│  │  ├── 04_PYTHON_EMBEDDED/  ◄─── Python + get-pip.py         │    │
│  │  ├── 05_WHEELS/           ◄─── All .whl files              │    │
│  │  ├── 06_DLLS/             ◄─── DLL documentation           │    │
│  │  ├── 07_EXTERNAL_TOOLS/   ◄─── 7-Zip documentation         │    │
│  │  ├── 08_SOURCE_CODE/      ◄─── IntelliSTOR source          │    │
│  │  └── MANIFEST.json        ◄─── Checksums                   │    │
│  └────────────────────────────────────────────────────────────┘    │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               │ TRANSFER
                               │ • USB Drive (encrypted)
                               │ • Secure File Transfer
                               │ • DVD/CD
                               │
┌──────────────────────────────▼───────────────────────────────────────┐
│                        AIR-GAP MACHINE                                │
│                                                                       │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │  03_OFFLINE_INSTALLER/                                     │     │
│  │  ├── install_airgap_python.bat  ◄─── Main installer        │     │
│  │  ├── verify_installation.py    ◄─── Verification script    │     │
│  │  ├── update_batch_files.py     ◄─── Batch updater          │     │
│  │  └── uninstall_airgap.bat      ◄─── Uninstaller           │     │
│  └────────────────────────────────────────────────────────────┘     │
│                            │                                          │
│                            │ Installation Process:                   │
│                            │ 1. Extract Python                       │
│                            │ 2. Fix ._pth file                       │
│                            │ 3. Install pip                          │
│                            │ 4. Install packages                     │
│                            ▼                                          │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │  IntelliSTOR_Python/                                       │     │
│  │  └── python/                                               │     │
│  │      ├── python.exe        ◄─── Python interpreter         │     │
│  │      ├── python311.dll     ◄─── Core library               │     │
│  │      ├── python311._pth    ◄─── Path configuration (FIXED) │     │
│  │      ├── Lib/                                              │     │
│  │      │   └── site-packages/  ◄─── Installed packages       │     │
│  │      │       ├── pymssql/                                  │     │
│  │      │       ├── ldap3/                                    │     │
│  │      │       ├── flask/                                    │     │
│  │      │       └── flask_cors/                               │     │
│  │      └── Scripts/            ◄─── pip, etc.                │     │
│  └────────────────────────────────────────────────────────────┘     │
│                            │                                          │
│                            │ Integrated with:                        │
│                            ▼                                          │
│  ┌────────────────────────────────────────────────────────────┐     │
│  │  08_SOURCE_CODE/IntelliSTOR_Migration/                     │     │
│  │  ├── Migration_Environment.bat  ◄─── AIRGAP_PYTHON set     │     │
│  │  ├── 1_Migration_Users/         ◄─── Uses %AIRGAP_PYTHON%  │     │
│  │  ├── 2_LDAP/                    ◄─── Uses %AIRGAP_PYTHON%  │     │
│  │  ├── 3_Migration_Report_Species_Folders/                   │     │
│  │  ├── 4. Migration_Instances/                               │     │
│  │  ├── 5. TestFileGeneration/                                │     │
│  │  ├── 6. ZipEncrypt/                                         │     │
│  │  ├── 7. AFP_Resources/                                      │     │
│  │  └── ACL/                                                   │     │
│  └────────────────────────────────────────────────────────────┘     │
└───────────────────────────────────────────────────────────────────────┘
```

## Data Flow

```
BUILD PHASE (Internet Machine)
┌──────────┐
│ User     │
│ runs:    │ download_dependencies.bat
└────┬─────┘
     │
     ▼
┌──────────────────────────┐
│ build_airgap_package.py  │
└────┬────┬────┬───┬───────┘
     │    │    │   │
     ▼    ▼    ▼   ▼
┌────────────────────────────────────────┐
│ Downloads:                              │
│ • Python 3.11.7 from python.org        │
│ • get-pip.py from bootstrap.pypa.io    │
│ • Wheels from PyPI (pip download)      │
│ • Copies IntelliSTOR source code       │
└────────────────┬───────────────────────┘
                 │
                 ▼
         ┌──────────────┐
         │ MANIFEST.json │ ◄── SHA-256 checksums
         └──────────────┘


TRANSFER PHASE
┌──────────────┐      ┌─────────────┐      ┌──────────────┐
│ Internet     │ USB  │ Secure      │ USB  │ Air-Gap      │
│ Machine      │──────┤ Transfer    │──────┤ Machine      │
│              │  or  │ Media       │  or  │              │
│              │ DVD  │             │ DVD  │              │
└──────────────┘      └─────────────┘      └──────────────┘


INSTALLATION PHASE (Air-Gap Machine)
┌──────────┐
│ User     │
│ runs:    │ install_airgap_python.bat
└────┬─────┘
     │
     ▼
┌──────────────────────────────────────────┐
│ Installation Steps:                      │
│                                          │
│ 1. Validate package integrity            │
│    └─► Check files exist                 │
│                                          │
│ 2. Extract Python embeddable             │
│    └─► Unzip to IntelliSTOR_Python/     │
│                                          │
│ 3. Fix python311._pth (CRITICAL!)       │
│    └─► Add: Lib\site-packages           │
│    └─► Add: import site                 │
│                                          │
│ 4. Install pip offline                   │
│    └─► python get-pip.py --no-index     │
│                                          │
│ 5. Install packages offline              │
│    └─► pip install --no-index           │
│        --find-links=05_WHEELS            │
│        pymssql ldap3 flask flask-cors    │
│                                          │
│ 6. Copy DLLs (optional)                  │
│    └─► vcruntime140.dll, etc.           │
│                                          │
│ 7. Update Migration_Environment.bat      │
│    └─► SET AIRGAP_PYTHON=...            │
│                                          │
│ 8. Run verification                      │
│    └─► verify_installation.py           │
└──────────────────┬───────────────────────┘
                   │
                   ▼
         ┌──────────────────┐
         │ Installation     │
         │ Complete         │
         │ ✓ Python ready   │
         │ ✓ Packages ready │
         │ ✓ Verified       │
         └──────────────────┘


USAGE PHASE
┌──────────────────────────────────────────┐
│ User runs migration batch files:         │
│                                          │
│ call Migration_Environment.bat           │
│   └─► Sets AIRGAP_PYTHON variable        │
│                                          │
│ %AIRGAP_PYTHON% script.py               │
│   └─► Uses air-gap Python                │
│   └─► Imports pymssql, ldap3, etc.       │
│   └─► Connects to SQL Server/LDAP        │
│   └─► Generates CSV output files         │
└──────────────────────────────────────────┘
```

## Component Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                    DOCUMENTATION LAYER                       │
│                                                              │
│  00_README_INSTALLATION.md        ◄── User guide             │
│  01_SECURITY_DOCUMENTATION.md     ◄── Security/compliance    │
│  AIRGAP_QUICK_REFERENCE.md        ◄── Command reference      │
│  AIRGAP_DEPLOYMENT_CHECKLIST.md   ◄── Deployment guide       │
│  AIRGAP_IMPLEMENTATION_SUMMARY.md ◄── Technical summary      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                      BUILD LAYER                             │
│                                                              │
│  02_PACKAGE_BUILDER/                                         │
│  ├── build_airgap_package.py      ◄── Core build logic      │
│  ├── download_dependencies.bat    ◄── User interface        │
│  └── requirements_full.txt        ◄── Dependency spec       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    INSTALLATION LAYER                        │
│                                                              │
│  03_OFFLINE_INSTALLER/                                       │
│  ├── install_airgap_python.bat    ◄── Main installer        │
│  ├── verify_installation.py       ◄── Post-install check    │
│  ├── update_batch_files.py        ◄── Integration tool      │
│  └── uninstall_airgap.bat         ◄── Cleanup tool          │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    PACKAGE LAYER                             │
│                                                              │
│  04_PYTHON_EMBEDDED/   ◄── Python distribution              │
│  05_WHEELS/            ◄── Python packages                  │
│  06_DLLS/              ◄── Runtime libraries                │
│  07_EXTERNAL_TOOLS/    ◄── 7-Zip docs                       │
│  08_SOURCE_CODE/       ◄── IntelliSTOR tools                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    RUNTIME LAYER                             │
│                                                              │
│  IntelliSTOR_Python/python/                                  │
│  ├── python.exe                   ◄── Interpreter           │
│  ├── python311._pth               ◄── Path config (FIXED)   │
│  └── Lib/site-packages/           ◄── Installed packages    │
│                                                              │
│  08_SOURCE_CODE/IntelliSTOR_Migration/                       │
│  ├── Migration_Environment.bat    ◄── Configuration         │
│  ├── python_launcher.bat          ◄── Python wrapper        │
│  └── [8 migration projects]       ◄── Migration tools       │
└─────────────────────────────────────────────────────────────┘
```

## Dependency Tree

```
IntelliSTOR Migration Tools
│
├── Python 3.11.7 (PSF License)
│   ├── Standard Library
│   │   ├── csv
│   │   ├── json
│   │   ├── pathlib
│   │   ├── subprocess
│   │   └── ...
│   │
│   └── pip (installed offline)
│       ├── setuptools
│       └── wheel
│
├── pymssql 2.2.8+ (LGPL v2.1)
│   ├── FreeTDS (bundled)
│   └── Visual C++ Runtime (system)
│       ├── vcruntime140.dll
│       ├── msvcp140.dll
│       └── vcruntime140_1.dll
│
├── ldap3 2.9.1+ (LGPL v3)
│   └── pyasn1 (BSD-2-Clause)
│
├── Flask 2.3.0+ (BSD-3-Clause)
│   ├── Werkzeug (BSD-3-Clause)
│   ├── Jinja2 (BSD-3-Clause)
│   ├── Click (BSD-3-Clause)
│   ├── ItsDangerous (BSD-3-Clause)
│   └── MarkupSafe (BSD-3-Clause)
│
├── Flask-CORS 4.0.0+ (MIT)
│   └── Flask (dependency above)
│
└── 7-Zip 23.01+ (LGPL) [External, Optional]
    └── Required for Project 6 only
```

## Project Integration Map

```
IntelliSTOR_Python/python/python.exe  (Air-Gap Python)
                    │
                    │ via %AIRGAP_PYTHON%
                    │
                    ▼
┌────────────────────────────────────────────────────────┐
│ Migration_Environment.bat                              │
│ SET "AIRGAP_PYTHON=C:\...\python.exe"                  │
└────────────────┬───────────────────────────────────────┘
                 │
                 │ Called by all batch files
                 │
    ┌────────────┼────────────┬─────────────┬───────────────┐
    │            │            │             │               │
    ▼            ▼            ▼             ▼               ▼
┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐   ┌─────────┐
│Project 1│  │Project 2│  │Project 3│  │Project 4│...│Project 8│
│Users    │  │LDAP     │  │Reports  │  │Instances│   │ACL      │
└────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘   └────┬────┘
     │            │            │            │             │
     │ pymssql    │ ldap3      │ pymssql    │ pymssql     │ stdlib
     │            │ flask      │            │             │
     ▼            ▼            ▼            ▼             ▼
┌──────────────────────────────────────────────────────────────┐
│ Air-Gap Python Environment                                   │
│ Lib/site-packages/                                           │
│ ├── pymssql/       ◄── SQL Server connectivity               │
│ ├── ldap3/         ◄── LDAP integration                      │
│ ├── flask/         ◄── Web framework                         │
│ └── flask_cors/    ◄── CORS support                          │
└──────────────────────────────────────────────────────────────┘
```

## Critical Success Factors

```
┌─────────────────────────────────────────────────────────────┐
│ CRITICAL: python311._pth File Fix                           │
│                                                              │
│ Before (default):           After (fixed by installer):     │
│ ┌──────────────────┐       ┌───────────────────────┐       │
│ │ python311.zip    │       │ python311.zip         │       │
│ │ .                │       │ .                     │       │
│ │                  │       │ Lib\site-packages  ◄──┼─ ADD  │
│ │ #import site     │       │ import site        ◄──┼─ ADD  │
│ └──────────────────┘       └───────────────────────┘       │
│                                                              │
│ Without this fix:                                            │
│ ✗ pip won't work                                            │
│ ✗ Installed packages won't be found                         │
│ ✗ "ModuleNotFoundError" for all packages                   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ VERIFICATION POINTS                                          │
│                                                              │
│ ✓ Package Integrity                                         │
│   └─► MANIFEST.json checksums match                         │
│                                                              │
│ ✓ Python Installation                                       │
│   └─► python.exe exists and runs                            │
│                                                              │
│ ✓ pip Installation                                          │
│   └─► pip list shows installed packages                     │
│                                                              │
│ ✓ Package Imports                                           │
│   └─► import pymssql, ldap3, flask works                    │
│                                                              │
│ ✓ Database Connectivity                                     │
│   └─► test_connection.py succeeds                           │
│                                                              │
│ ✓ Integration                                               │
│   └─► Batch files use %AIRGAP_PYTHON%                       │
└─────────────────────────────────────────────────────────────┘
```

## File Count Summary

```
Created Files:        20
Documentation:        6 files (~4,000 lines)
Python Scripts:       3 files (~850 lines)
Batch Scripts:        4 files (~900 lines)
Configuration:        1 file
Directories:          8 directories
Total Code:          ~5,750 lines
```

## Success Metrics

```
┌─────────────────────────────────────────────────────────────┐
│ BUILD PHASE                                                  │
│ ✓ Python 3.11.7 downloaded                                  │
│ ✓ All wheels downloaded (pymssql, ldap3, flask, flask-cors) │
│ ✓ Source code copied                                        │
│ ✓ MANIFEST.json generated                                   │
│ ✓ Package size: ~50-100 MB                                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ INSTALLATION PHASE                                           │
│ ✓ Python extracted without errors                           │
│ ✓ ._pth file fixed correctly                                │
│ ✓ pip installed successfully                                │
│ ✓ All packages installed                                    │
│ ✓ Verification passed                                       │
│ ✓ No admin rights required                                  │
│ ✓ No network access required                                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ INTEGRATION PHASE                                            │
│ ✓ Migration_Environment.bat updated                         │
│ ✓ Batch files updated (or launcher created)                 │
│ ✓ Database connectivity works                               │
│ ✓ LDAP connectivity works                                   │
│ ✓ All 8 projects compatible                                 │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ SECURITY COMPLIANCE                                          │
│ ✓ No internet access during installation                    │
│ ✓ No registry modifications                                 │
│ ✓ File integrity verified (checksums)                       │
│ ✓ Source code audit available                               │
│ ✓ Security documentation complete                           │
└─────────────────────────────────────────────────────────────┘
```

---

**Document Version:** 1.0
**Created:** 2026-01-28
**For Package Version:** 1.0.0 (Python 3.11.7)
