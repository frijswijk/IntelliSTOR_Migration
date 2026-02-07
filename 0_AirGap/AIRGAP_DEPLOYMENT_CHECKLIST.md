# IntelliSTOR Air-Gap Deployment Checklist

Use this checklist to ensure successful deployment of the air-gap installation package.

---

## Phase 1: Pre-Build (Internet Machine)

### Environment Preparation

- [ ] Internet-connected Windows machine available
- [ ] Python 3.7+ installed and in PATH
- [ ] pip installed and working (`python -m pip --version`)
- [ ] Sufficient disk space (500 MB)
- [ ] Repository cloned or extracted

### Build Configuration

- [ ] Reviewed `02_PACKAGE_BUILDER/requirements_full.txt`
- [ ] Confirmed Python version (default: 3.11.7)
- [ ] Noted any custom requirements

### Build Execution

- [ ] Navigated to `02_PACKAGE_BUILDER/`
- [ ] Ran: `download_dependencies.bat`
- [ ] Build completed successfully (no errors)
- [ ] Verified package size (~50-100 MB)

### Build Verification

- [ ] `MANIFEST.json` exists in root
- [ ] `04_PYTHON_EMBEDDED/python-3.11.7-embed-amd64.zip` exists
- [ ] `04_PYTHON_EMBEDDED/get-pip.py` exists
- [ ] `05_WHEELS/` contains `.whl` files (10+ files)
- [ ] `08_SOURCE_CODE/IntelliSTOR_Migration/` contains source code
- [ ] All directories created (02-08)

### Package Integrity

- [ ] Calculated checksum of entire package directory
- [ ] Documented checksum for transfer verification
- [ ] Created backup copy of package

**Package Checksum:** ________________ (record for verification)

---

## Phase 2: Transfer

### Transfer Preparation

- [ ] Selected approved transfer method:
  - [ ] Encrypted USB drive
  - [ ] Secure file transfer protocol
  - [ ] DVD/CD media
  - [ ] Other: ________________
- [ ] Compressed package (optional): `IntelliSTOR_AirGap_Package.zip`
- [ ] Transfer approved by security team

### Transfer Execution

- [ ] Package transferred to air-gap environment
- [ ] Transfer completed without errors
- [ ] File count verified (matches source)

### Post-Transfer Verification

- [ ] Extracted package (if compressed)
- [ ] Verified checksum matches pre-transfer value
- [ ] Confirmed all directories present (02-08)
- [ ] Spot-checked file integrity (random files)
- [ ] `MANIFEST.json` readable and valid JSON

**Post-Transfer Checksum:** ________________ (should match above)

---

## Phase 3: Pre-Installation (Air-Gap Machine)

### Target Environment Verification

- [ ] Windows version: ________________ (Win 10+ or Server 2016+)
- [ ] Architecture: x64 (verified with: `wmic os get osarchitecture`)
- [ ] Available disk space: ________________ MB (need 200+ MB)
- [ ] User account type: Standard user (admin NOT required)

### System Prerequisites

- [ ] Visual C++ Redistributable present (check: `where vcruntime140.dll`)
  - [ ] Installed: C++ Redistributable installer available if needed
  - [ ] Not installed: DLLs available for manual copy
- [ ] 7-Zip installed (optional, for Project 6 only)
  - [ ] Path: ________________
  - [ ] Or: Installation file available

### Security Review (Optional)

- [ ] Package reviewed by IT security team
- [ ] `01_SECURITY_DOCUMENTATION.md` reviewed by security officer
- [ ] Source code audit completed (if required)
- [ ] Installation approved by change control board

### Network Isolation Confirmation

- [ ] Confirmed air-gap environment (no internet access)
- [ ] Network connections monitored (if required)
- [ ] Firewall rules reviewed (if applicable)

---

## Phase 4: Installation

### Installation Preparation

- [ ] Extracted package to working directory: ________________
- [ ] Opened Command Prompt (standard user)
- [ ] Navigated to: `03_OFFLINE_INSTALLER/`
- [ ] Reviewed installation script (optional): `install_airgap_python.bat`

### Installation Execution

- [ ] Ran: `install_airgap_python.bat`
- [ ] Or custom path: `install_airgap_python.bat C:\CustomPath`
- [ ] Confirmed installation when prompted
- [ ] Installation completed without errors
- [ ] Installation directory created: ________________
- [ ] No UAC prompts appeared (verify no admin elevation)

### Installation Verification

- [ ] Verification script ran automatically
- [ ] Or manual: `%AIRGAP_PYTHON% verify_installation.py`
- [ ] All critical checks passed:
  - [ ] Python version check
  - [ ] pip installed
  - [ ] Standard library modules
  - [ ] pymssql installed
  - [ ] ldap3 installed
  - [ ] Flask installed
  - [ ] Flask-CORS installed
- [ ] Warnings documented (7-Zip, DLLs): ________________

### Post-Installation Checks

- [ ] Python executable exists: `IntelliSTOR_Python\python\python.exe`
- [ ] `python311._pth` file modified correctly (contains `import site`)
- [ ] `Lib\site-packages` directory created and populated
- [ ] `Migration_Environment.bat` updated with `AIRGAP_PYTHON`

**Installation Path:** ________________

**Python Version:** ________________ (run: `%AIRGAP_PYTHON% --version`)

---

## Phase 5: Configuration

### Database Configuration

- [ ] Located: `08_SOURCE_CODE\IntelliSTOR_Migration\Migration_Environment.bat`
- [ ] Created backup: `Migration_Environment.bat.backup`
- [ ] Updated database settings:
  - [ ] SQLServer: ________________
  - [ ] SQLDatabase: ________________
  - [ ] SQLUsername: ________________
  - [ ] SQLPassword: ________________ (secure storage)
- [ ] Verified `AIRGAP_PYTHON` variable set

### Batch File Updates

- [ ] Selected update method:
  - [ ] Automated: `update_batch_files.py`
  - [ ] Manual: Edit each .bat file
  - [ ] Launcher: Use `python_launcher.bat`

**If using automated update:**
- [ ] Ran dry-run: `%AIRGAP_PYTHON% update_batch_files.py --dry-run --source-dir ..\08_SOURCE_CODE\IntelliSTOR_Migration`
- [ ] Reviewed proposed changes
- [ ] Ran actual update: `%AIRGAP_PYTHON% update_batch_files.py --source-dir ..\08_SOURCE_CODE\IntelliSTOR_Migration`
- [ ] Verified backups created (*.bat.backup files)
- [ ] Spot-checked updated batch files

### External Tools (Optional)

**Visual C++ Redistributable (if needed):**
- [ ] Downloaded: `vc_redist.x64.exe`
- [ ] Installed: `vc_redist.x64.exe /install /quiet /norestart`
- [ ] Verified: `where vcruntime140.dll`

**7-Zip (for Project 6):**
- [ ] Downloaded from: https://www.7-zip.org/
- [ ] Installed or extracted
- [ ] Updated `Migration_Environment.bat`:
  - [ ] SET SEVEN_ZIP=C:\...\7z.exe
- [ ] Verified: `"%SEVEN_ZIP%" --help`

---

## Phase 6: Testing

### Basic Python Tests

- [ ] Python version: `%AIRGAP_PYTHON% --version`
  - **Output:** ________________
- [ ] Pip version: `%AIRGAP_PYTHON% -m pip --version`
  - **Output:** ________________
- [ ] Package list: `%AIRGAP_PYTHON% -m pip list`
  - **Count:** ________________ packages
- [ ] Import test: `%AIRGAP_PYTHON% -c "import pymssql, ldap3, flask; print('OK')"`
  - **Output:** ________________

### Database Connectivity Test

- [ ] Navigated to: `08_SOURCE_CODE\IntelliSTOR_Migration\4. Migration_Instances`
- [ ] Called environment: `call ..\Migration_Environment.bat`
- [ ] Ran test: `%AIRGAP_PYTHON% test_connection.py`
- [ ] **Result:** Connection successful ☐ / Failed ☐
- [ ] If failed, error message: ________________

### LDAP Connectivity Test (if applicable)

- [ ] Navigated to: `08_SOURCE_CODE\IntelliSTOR_Migration\2_LDAP`
- [ ] Updated LDAP configuration in test script
- [ ] Ran test: `testconnection.bat`
- [ ] **Result:** Connection successful ☐ / Failed ☐
- [ ] If failed, error message: ________________

### Migration Task Test

- [ ] Selected test project: ________________
- [ ] Navigated to project directory
- [ ] Ran test batch file: ________________
- [ ] **Result:**
  - [ ] Script executed without errors
  - [ ] Output files created
  - [ ] Data appears valid
- [ ] Output location: ________________
- [ ] Output file count: ________________

### Network Monitoring (Security Requirement)

**If network monitoring required:**
- [ ] Captured baseline: `netstat -ano` (before execution)
- [ ] Executed test script
- [ ] Captured after: `netstat -ano` (during execution)
- [ ] Verified only expected connections (SQL Server, LDAP)
- [ ] No unexpected outbound connections
- [ ] Monitoring log location: ________________

---

## Phase 7: Documentation

### Installation Documentation

- [ ] Documented installation path
- [ ] Documented Python version
- [ ] Documented installed packages (pip list output)
- [ ] Recorded any installation warnings or errors
- [ ] Noted any deviations from standard installation

### Configuration Documentation

- [ ] Documented database server/database names
- [ ] Documented service account used (no passwords)
- [ ] Documented external tool paths (7-Zip, etc.)
- [ ] Recorded batch file update method used
- [ ] Saved backup locations

### Testing Results

- [ ] Recorded verification script results
- [ ] Documented database connectivity test results
- [ ] Documented LDAP connectivity test results (if applicable)
- [ ] Recorded sample migration task results
- [ ] Saved test output files for reference

### Security Compliance

- [ ] Completed security checklist (if required)
- [ ] Documented network monitoring results (if required)
- [ ] Verified no admin elevation occurred
- [ ] Confirmed no registry modifications
- [ ] Verified file permissions on sensitive files

---

## Phase 8: Handover

### User Training

- [ ] Demonstrated installation process
- [ ] Walked through configuration
- [ ] Explained batch file updates
- [ ] Showed how to run migration tasks
- [ ] Demonstrated verification script
- [ ] Provided troubleshooting guidance

### Documentation Handover

- [ ] Provided `00_README_INSTALLATION.md`
- [ ] Provided `01_SECURITY_DOCUMENTATION.md`
- [ ] Provided `AIRGAP_QUICK_REFERENCE.md`
- [ ] Provided `AIRGAP_IMPLEMENTATION_SUMMARY.md`
- [ ] Provided this checklist (completed)
- [ ] Provided installation notes/logs

### Support Handover

- [ ] Identified support contact: ________________
- [ ] Provided troubleshooting documentation
- [ ] Explained how to verify installation issues
- [ ] Documented escalation path
- [ ] Provided access to backup packages

### Sign-Off

**Installed By:** ________________ **Date:** ________________

**Verified By:** ________________ **Date:** ________________

**Approved By:** ________________ **Date:** ________________

---

## Phase 9: Post-Deployment

### Monitoring (First Week)

- [ ] Day 1: Verify all scheduled tasks run successfully
- [ ] Day 2: Check error logs for issues
- [ ] Day 3: Verify output data quality
- [ ] Day 5: Review with users for feedback
- [ ] Day 7: Confirm no installation issues

### Issue Tracking

| Date | Issue | Resolution | Status |
|------|-------|------------|--------|
| | | | |
| | | | |
| | | | |

### Maintenance Planning

- [ ] Scheduled review date: ________________
- [ ] Python update schedule: ________________
- [ ] Package rebuild schedule: ________________
- [ ] Backup schedule: ________________

---

## Rollback Plan

**If installation fails or issues arise:**

### Immediate Rollback Steps

1. [ ] Stop all migration activities
2. [ ] Run: `03_OFFLINE_INSTALLER\uninstall_airgap.bat`
3. [ ] Verify Python installation removed
4. [ ] Restore batch files from backups
5. [ ] Restore `Migration_Environment.bat` from backup
6. [ ] Document issue for troubleshooting
7. [ ] Contact support: ________________

### Rollback Verification

- [ ] Python installation directory removed
- [ ] Original batch files restored
- [ ] Environment configuration restored
- [ ] No residual files or changes
- [ ] System returned to pre-installation state

---

## Appendix: Quick Commands

**Build Package:**
```batch
cd 02_PACKAGE_BUILDER
download_dependencies.bat
```

**Install:**
```batch
cd 03_OFFLINE_INSTALLER
install_airgap_python.bat
```

**Verify:**
```batch
%AIRGAP_PYTHON% verify_installation.py
```

**Update Batch Files:**
```batch
%AIRGAP_PYTHON% update_batch_files.py --source-dir ..\08_SOURCE_CODE\IntelliSTOR_Migration
```

**Test Database:**
```batch
cd 08_SOURCE_CODE\IntelliSTOR_Migration\4. Migration_Instances
%AIRGAP_PYTHON% test_connection.py
```

**Uninstall:**
```batch
cd 03_OFFLINE_INSTALLER
uninstall_airgap.bat
```

---

**Checklist Version:** 1.0
**Last Updated:** 2026-01-28
**For Package Version:** 1.0.0 (Python 3.11.7)

---

## Sign-Off

I certify that I have completed all applicable items in this checklist and that the IntelliSTOR Air-Gap Installation has been successfully deployed.

**Name:** ________________

**Signature:** ________________

**Date:** ________________

**Organization:** ________________

**Role:** ________________
