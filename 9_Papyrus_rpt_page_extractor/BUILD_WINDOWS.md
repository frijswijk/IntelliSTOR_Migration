# Building papyrus_rpt_page_extractor for Windows Distribution

## Overview
This guide provides instructions for compiling `papyrus_rpt_page_extractor.cpp` into a standalone Windows executable that can be distributed to airgap machines.

## Dependencies
- **None!** This program uses only C++ standard library components, so no external dependencies are required.

## Compilation Options

### Option 1: MinGW-w64 (Recommended for Airgap Distribution)

**Pros:**
- Free and open-source
- Produces small, portable executables
- Easy to statically link all dependencies

**Installation:**
1. Download MinGW-w64 from: https://www.mingw-w64.org/downloads/
   - Or use MSYS2: https://www.msys2.org/
2. Add MinGW bin directory to PATH (e.g., `C:\mingw64\bin`)

**Compile command:**
```batch
g++ -o papyrus_rpt_page_extractor.exe papyrus_rpt_page_extractor.cpp -static -O2 -s
```

**Flags explained:**
- `-static` - Statically link all libraries (no DLL dependencies)
- `-O2` - Optimize for speed
- `-s` - Strip debug symbols (smaller executable)

---

### Option 2: Microsoft Visual C++ (MSVC)

**Pros:**
- Official Microsoft compiler
- Best compatibility with Windows

**Installation:**
1. Download Visual Studio Community (free): https://visualstudio.microsoft.com/
2. Install "Desktop development with C++" workload

**Compile command (from Developer Command Prompt):**
```batch
cl /EHsc /O2 /MT papyrus_rpt_page_extractor.cpp /Fe:papyrus_rpt_page_extractor.exe
```

**Flags explained:**
- `/EHsc` - Enable C++ exception handling
- `/O2` - Optimize for speed
- `/MT` - Statically link runtime library (no DLL dependencies)
- `/Fe:` - Specify output filename

---

### Option 3: Clang for Windows

**Compile command:**
```batch
clang++ -o papyrus_rpt_page_extractor.exe papyrus_rpt_page_extractor.cpp -static -O2
```

---

## Quick Start: Using the Build Script

I've created `build.bat` for easy compilation:

```batch
build.bat
```

This will automatically detect available compilers and build the executable.

---

## Verification

After compilation, verify the executable:

1. **Check file size** - Should be ~100-500KB depending on compiler
2. **Test execution:**
   ```batch
   papyrus_rpt_page_extractor.exe
   ```
   Should display usage information

3. **Check dependencies** (ensure no external DLLs required):
   - Download Dependency Walker: https://dependencywalker.com/
   - Or use: `dumpbin /dependents papyrus_rpt_page_extractor.exe` (MSVC only)
   - Or use PowerShell:
     ```powershell
     Get-Command .\papyrus_rpt_page_extractor.exe | Format-List *
     ```

4. **Test with sample data:**
   ```batch
   papyrus_rpt_page_extractor.exe test.rpt rule_1 output.txt output.pdf
   ```

---

## Distribution to Airgap Machine

1. **Copy the executable** - Just copy `papyrus_rpt_page_extractor.exe` to the target machine
2. **No installation required** - It's a standalone executable
3. **No DLL dependencies** - Statically linked, runs on any Windows machine
4. **Minimum Windows version** - Windows 7 SP1 or later (64-bit)

---

## Troubleshooting

### "VCRUNTIME140.dll not found" error
**Solution:** You didn't use the `/MT` flag (MSVC) or `-static` flag (MinGW). Recompile with static linking.

### "The system cannot execute the specified program"
**Solution:** Ensure you're building for the correct architecture (x64 vs x86). Use `-m64` flag for 64-bit or `-m32` for 32-bit.

### Compiler not found
**Solution:** Ensure compiler's bin directory is in your PATH:
```batch
set PATH=%PATH%;C:\mingw64\bin
```
Or use the appropriate Developer Command Prompt.

---

## Build Output Comparison

| Compiler | Executable Size | Speed | Ease of Distribution |
|----------|----------------|-------|----------------------|
| MinGW-w64 | ~100-200 KB | Fast | ⭐⭐⭐⭐⭐ Excellent |
| MSVC | ~300-500 KB | Fastest | ⭐⭐⭐⭐ Very Good |
| Clang | ~150-250 KB | Fast | ⭐⭐⭐⭐ Very Good |

**Recommendation:** Use MinGW-w64 with `-static` flag for best airgap distribution.
