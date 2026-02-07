# IntelliSTOR Air-Gap Package - START HERE

## Welcome

This is the **IntelliSTOR Air-Gap Installation Package** for deploying Python and migration tools in locked-down banking environments without internet access.

---

## Quick Navigation

### 🚀 I want to get started immediately

**For Internet Machine (Build Package):**
1. Run: `02_PACKAGE_BUILDER/download_dependencies.bat`
2. Wait for completion (~5-10 minutes)
3. Transfer entire directory to air-gap machine

**For Air-Gap Machine (Install):**
1. Run: `03_OFFLINE_INSTALLER/install_airgap_python.bat`
2. Follow on-screen prompts
3. Verify: `%AIRGAP_PYTHON% verify_installation.py`

**See:** `AIRGAP_QUICK_REFERENCE.md` for command reference

---

### 📖 I want to understand what this package does

**Read:** `AIRGAP_SYSTEM_OVERVIEW.md`
- Visual architecture diagrams
- Data flow charts
- Component relationships
- Complete system overview

---

### 📋 I want detailed installation instructions

**Read:** `00_README_INSTALLATION.md`
- Step-by-step installation guide
- System requirements
- Configuration instructions
- Troubleshooting guide
- ~800 lines of detailed documentation

---

### 🔒 I need security and compliance information

**Read:** `01_SECURITY_DOCUMENTATION.md`
- Security architecture
- Threat model and mitigations
- Compliance certifications (PCI-DSS, ISO 27001, GDPR, PDPA)
- Audit recommendations
- IT auditor checklist
- ~1000 lines of security documentation

---

### ✅ I want to follow a deployment checklist

**Read:** `AIRGAP_DEPLOYMENT_CHECKLIST.md`
- Phase-by-phase checklist
- Pre-build verification
- Transfer procedures
- Installation steps
- Testing procedures
- Documentation requirements
- Sign-off sections

---

### 🔍 I want technical implementation details

**Read:** `AIRGAP_IMPLEMENTATION_SUMMARY.md`
- What was implemented
- Technical details
- File inventory
- Dependencies packaged
- Integration guide
- Known issues and limitations

---

### ⚡ I want a quick command reference

**Read:** `AIRGAP_QUICK_REFERENCE.md`
- One-page command reference
- Quick troubleshooting
- File locations
- Configuration examples

---

## Document Index

### Core Documentation (READ THESE FIRST)

| Document | Purpose | Audience | Priority |
|----------|---------|----------|----------|
| `00_START_HERE.md` | Navigation guide | Everyone | **START** |
| `AIRGAP_QUICK_REFERENCE.md` | Command reference | Users | **HIGH** |
| `00_README_INSTALLATION.md` | Installation guide | Installers | **HIGH** |
| `AIRGAP_DEPLOYMENT_CHECKLIST.md` | Deployment checklist | Installers | **HIGH** |

### Technical Documentation

| Document | Purpose | Audience | Priority |
|----------|---------|----------|----------|
| `AIRGAP_SYSTEM_OVERVIEW.md` | Architecture diagrams | Technical staff | Medium |
| `AIRGAP_IMPLEMENTATION_SUMMARY.md` | Technical details | Developers | Medium |
| `README_AIRGAP_PACKAGE.md` | Package overview | Everyone | Medium |

### Security & Compliance

| Document | Purpose | Audience | Priority |
|----------|---------|----------|----------|
| `01_SECURITY_DOCUMENTATION.md` | Security analysis | IT Security, Auditors | **HIGH** |

### Component Documentation

| Document | Purpose | Audience | Priority |
|----------|---------|----------|----------|
| `06_DLLS/README_DLLS.md` | Visual C++ Runtime DLLs | Installers | Low |
| `07_EXTERNAL_TOOLS/README_7ZIP.md` | 7-Zip installation | Users (Project 6) | Low |

### Source Code Documentation

| Document | Purpose | Audience | Priority |
|----------|---------|----------|----------|
| `README.md` | IntelliSTOR project docs | Users | Medium |

---

## Directory Structure

```
IntelliSTOR_AirGap_Package/
│
├── 00_START_HERE.md                   ◄── You are here
├── 00_README_INSTALLATION.md          ◄── Installation guide
├── 01_SECURITY_DOCUMENTATION.md       ◄── Security docs
├── AIRGAP_*.md                        ◄── Air-gap documentation
├── README.md                          ◄── IntelliSTOR docs
├── MANIFEST.json                      ◄── Package manifest (after build)
│
├── 02_PACKAGE_BUILDER/                ◄── Build scripts (internet machine)
│   ├── build_airgap_package.py
│   ├── download_dependencies.bat
│   └── requirements_full.txt
│
├── 03_OFFLINE_INSTALLER/              ◄── Install scripts (air-gap machine)
│   ├── install_airgap_python.bat      ◄── RUN THIS to install
│   ├── verify_installation.py
│   ├── update_batch_files.py
│   └── uninstall_airgap.bat
│
├── 04_PYTHON_EMBEDDED/                ◄── Python distribution (after build)
├── 05_WHEELS/                         ◄── Python packages (after build)
├── 06_DLLS/                           ◄── DLL documentation
├── 07_EXTERNAL_TOOLS/                 ◄── 7-Zip documentation
├── 08_SOURCE_CODE/                    ◄── IntelliSTOR source (after build)
└── IntelliSTOR_Python/                ◄── Installation (after install)
```

---

## Workflow

### 1️⃣ BUILD PHASE (Internet Machine)

```
You are here ───┐
                │
                ▼
Run: 02_PACKAGE_BUILDER/download_dependencies.bat
                │
                ▼
Wait for completion (~5-10 minutes)
                │
                ▼
Package ready for transfer
```

**Documentation:** None required (automated)

---

### 2️⃣ TRANSFER PHASE

```
Package on internet machine
                │
                ▼
Transfer via USB/DVD/Secure FTP
                │
                ▼
Package on air-gap machine
```

**Documentation:** `AIRGAP_DEPLOYMENT_CHECKLIST.md` (Phase 2)

---

### 3️⃣ INSTALLATION PHASE (Air-Gap Machine)

```
Package on air-gap machine
                │
                ▼
Run: 03_OFFLINE_INSTALLER/install_airgap_python.bat
                │
                ▼
Follow on-screen prompts
                │
                ▼
Installation complete
```

**Documentation:**
- Quick: `AIRGAP_QUICK_REFERENCE.md`
- Detailed: `00_README_INSTALLATION.md`
- Checklist: `AIRGAP_DEPLOYMENT_CHECKLIST.md` (Phase 4-5)

---

### 4️⃣ CONFIGURATION PHASE

```
Edit: 08_SOURCE_CODE/IntelliSTOR_Migration/Migration_Environment.bat
                │
                ▼
Set database credentials
                │
                ▼
Update batch files (automated or manual)
```

**Documentation:** `00_README_INSTALLATION.md` (Step 4-5)

---

### 5️⃣ VERIFICATION PHASE

```
Run: %AIRGAP_PYTHON% verify_installation.py
                │
                ▼
Test: test_connection.py
                │
                ▼
Run sample migration task
```

**Documentation:** `AIRGAP_DEPLOYMENT_CHECKLIST.md` (Phase 6)

---

## Common Scenarios

### 🆕 First-Time User

**Start here:**
1. Read: `AIRGAP_QUICK_REFERENCE.md` (5 minutes)
2. Read: `00_README_INSTALLATION.md` (20 minutes)
3. Follow: `AIRGAP_DEPLOYMENT_CHECKLIST.md`

### 👨‍💼 IT Security / Auditor

**Start here:**
1. Read: `01_SECURITY_DOCUMENTATION.md`
2. Review: Security checklist (Appendix A)
3. Read: `AIRGAP_IMPLEMENTATION_SUMMARY.md` (Technical details)

### 👨‍💻 Developer / Technical Staff

**Start here:**
1. Read: `AIRGAP_SYSTEM_OVERVIEW.md` (Architecture)
2. Read: `AIRGAP_IMPLEMENTATION_SUMMARY.md` (Details)
3. Review: Source code in `02_PACKAGE_BUILDER/` and `03_OFFLINE_INSTALLER/`

### 🆘 Troubleshooting Issues

**Start here:**
1. Check: `AIRGAP_QUICK_REFERENCE.md` (Troubleshooting section)
2. Check: `00_README_INSTALLATION.md` (Troubleshooting section)
3. Run: `%AIRGAP_PYTHON% verify_installation.py` (Diagnostics)

---

## Key Concepts

### What is "Air-Gap"?

An air-gap environment has **no internet access**. This package enables Python installation in such environments by:
- Pre-downloading everything on an internet-connected machine
- Transferring the complete package via USB/DVD
- Installing offline on the air-gap machine

### What is `%AIRGAP_PYTHON%`?

An environment variable pointing to the air-gap Python installation:
```
SET "AIRGAP_PYTHON=C:\Path\To\IntelliSTOR_Python\python\python.exe"
```

Used in batch files instead of `python` to use the air-gap installation.

### What is the "._pth file fix"?

Python embeddable doesn't enable pip by default. The installer fixes this by modifying `python311._pth` to:
- Add `Lib\site-packages` to the path
- Enable `import site`

**This is the most critical installation step.**

---

## Quick Start Commands

### Build Package (Internet Machine)
```batch
cd 02_PACKAGE_BUILDER
download_dependencies.bat
```

### Install (Air-Gap Machine)
```batch
cd 03_OFFLINE_INSTALLER
install_airgap_python.bat
```

### Verify Installation
```batch
%AIRGAP_PYTHON% verify_installation.py
```

### Test Database
```batch
cd 08_SOURCE_CODE\IntelliSTOR_Migration\4. Migration_Instances
%AIRGAP_PYTHON% test_connection.py
```

### Run Migration
```batch
cd 08_SOURCE_CODE\IntelliSTOR_Migration\1_Migration_Users
Extract_Users_permissions_SG.bat
```

---

## System Requirements

- **OS:** Windows 10+ or Windows Server 2016+
- **Architecture:** x64 (64-bit)
- **Disk Space:** 200 MB
- **Permissions:** Standard user (no admin required)
- **Network:** Internet (build phase) / None (install phase)

---

## Support

### Documentation
- Installation: `00_README_INSTALLATION.md`
- Security: `01_SECURITY_DOCUMENTATION.md`
- Quick Ref: `AIRGAP_QUICK_REFERENCE.md`

### Verification
```batch
%AIRGAP_PYTHON% verify_installation.py
```

### Troubleshooting
See `00_README_INSTALLATION.md` - Troubleshooting section

---

## Version Information

- **Package Version:** 1.0.0
- **Python Version:** 3.11.7
- **Platform:** Windows x64
- **Release Date:** 2026-01-28

---

## Next Steps

Choose your path:

- **Quick Start** → `AIRGAP_QUICK_REFERENCE.md`
- **Full Installation** → `00_README_INSTALLATION.md`
- **Security Review** → `01_SECURITY_DOCUMENTATION.md`
- **Deployment** → `AIRGAP_DEPLOYMENT_CHECKLIST.md`
- **Technical Details** → `AIRGAP_IMPLEMENTATION_SUMMARY.md`
- **Architecture** → `AIRGAP_SYSTEM_OVERVIEW.md`

---

**Ready to begin?** Run `02_PACKAGE_BUILDER/download_dependencies.bat` (if building) or `03_OFFLINE_INSTALLER/install_airgap_python.bat` (if installing).

**Need help?** Read `00_README_INSTALLATION.md` or `AIRGAP_QUICK_REFERENCE.md`.

**Have questions?** Check the troubleshooting sections in the installation guide.

---

**Document Version:** 1.0
**Last Updated:** 2026-01-28
**Package:** IntelliSTOR Air-Gap Installation System
