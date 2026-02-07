# Visual C++ Runtime DLLs

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
   - Check: `C:\Windows\System32\`
   - Or: `C:\Program Files\Microsoft Visual Studio\...`

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
