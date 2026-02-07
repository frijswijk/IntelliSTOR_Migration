# IntelliSTOR Air-Gap System - Quick Reference

## One-Page Command Reference

### Build Package (Internet Machine)

```batch
cd 02_PACKAGE_BUILDER
download_dependencies.bat
```

**Output:** Complete package in parent directory (~50-100 MB)

---

### Install (Air-Gap Machine)

```batch
cd 03_OFFLINE_INSTALLER
install_airgap_python.bat
```

**Installs to:** `IntelliSTOR_Python\python\python.exe`

---

### Verify Installation

```batch
%AIRGAP_PYTHON% verify_installation.py
```

**Expected:** All checks pass ✓

---

### Update Batch Files

```batch
REM Preview changes (dry run)
%AIRGAP_PYTHON% update_batch_files.py --dry-run --source-dir ..\08_SOURCE_CODE\IntelliSTOR_Migration

REM Apply updates
%AIRGAP_PYTHON% update_batch_files.py --source-dir ..\08_SOURCE_CODE\IntelliSTOR_Migration
```

**Result:** All batch files use `%AIRGAP_PYTHON%` instead of `python`

---

### Test Database Connection

```batch
cd 08_SOURCE_CODE\IntelliSTOR_Migration
call Migration_Environment.bat

cd "4. Migration_Instances"
%AIRGAP_PYTHON% test_connection.py
```

**Expected:** "Connection successful!"

---

### Run Migration Task

```batch
cd 08_SOURCE_CODE\IntelliSTOR_Migration\1_Migration_Users
Extract_Users_permissions_SG.bat
```

**Output:** CSV files in `Migration_data/`

---

### Uninstall

```batch
cd 03_OFFLINE_INSTALLER
uninstall_airgap.bat
```

**Removes:** Python installation and restores backups

---

## Configuration Files

### Migration_Environment.bat

```batch
REM Database Configuration
SET SQLServer=your-sql-server.company.com
SET SQLDatabase=IntelliSTOR
SET SQLUsername=migration_user
SET SQLPassword=YourPassword

REM Air-Gap Python (added by installer)
SET "AIRGAP_PYTHON=C:\...\IntelliSTOR_Python\python\python.exe"
```

---

## Troubleshooting

### "DLL load failed" (pymssql)
**Fix:** Install Visual C++ Redistributable
```
https://aka.ms/vs/17/release/vc_redist.x64.exe
```

### "ModuleNotFoundError: pymssql"
**Fix:** Verify `python311._pth` contains:
```
Lib\site-packages
import site
```

### "python is not recognized"
**Fix:** Use `%AIRGAP_PYTHON%` instead of `python`
```batch
REM Wrong:
python script.py

REM Correct:
%AIRGAP_PYTHON% script.py
```

---

## File Locations

| Component | Location |
|-----------|----------|
| Installation Guide | `00_README_INSTALLATION.md` |
| Security Docs | `01_SECURITY_DOCUMENTATION.md` |
| Build Script | `02_PACKAGE_BUILDER/build_airgap_package.py` |
| Installer | `03_OFFLINE_INSTALLER/install_airgap_python.bat` |
| Verification | `03_OFFLINE_INSTALLER/verify_installation.py` |
| DLL Guide | `06_DLLS/README_DLLS.md` |
| Python Executable | `IntelliSTOR_Python\python\python.exe` |
| Source Code | `08_SOURCE_CODE\IntelliSTOR_Migration\` |

---

## Package Contents

```
02_PACKAGE_BUILDER/     - Build scripts
03_OFFLINE_INSTALLER/   - Installation scripts
04_PYTHON_EMBEDDED/     - Python 3.11.7 (downloaded)
05_WHEELS/              - Python packages (downloaded)
06_DLLS/                - Visual C++ DLLs (optional)
07_EXTERNAL_TOOLS/      - 7-Zip docs
08_SOURCE_CODE/         - IntelliSTOR source
IntelliSTOR_Python/     - Installation (created)
```

---

## Requirements

- Windows 10+ or Server 2016+
- x64 (64-bit)
- 200 MB disk space
- No admin rights needed

---

## Dependencies

- Python 3.11.7
- pymssql 2.2.8+ (SQL Server)
- ldap3 2.9.1+ (LDAP)
- Flask 2.3.0+ (Web interface)
- Flask-CORS 4.0.0+ (CORS)

---

## Quick Test

```batch
REM 1. Check Python version
%AIRGAP_PYTHON% --version

REM 2. List installed packages
%AIRGAP_PYTHON% -m pip list

REM 3. Test imports
%AIRGAP_PYTHON% -c "import pymssql, ldap3, flask; print('OK')"

REM 4. Run verification
%AIRGAP_PYTHON% verify_installation.py
```

---

## Support

**Full Documentation:**
- Installation: `00_README_INSTALLATION.md`
- Security: `01_SECURITY_DOCUMENTATION.md`
- Summary: `AIRGAP_IMPLEMENTATION_SUMMARY.md`

**Verification:** Run `verify_installation.py` for diagnostics

---

**Version:** 1.0.0 | **Python:** 3.11.7 | **Platform:** Windows x64
