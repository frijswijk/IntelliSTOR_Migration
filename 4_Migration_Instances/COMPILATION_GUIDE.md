# Papyrus RPT Page Extractor - Compilation Guide

**Comprehensive instructions for compiling on Windows and macOS**

---

## 🪟 Windows Compilation

### Option 1: MSVC (Microsoft Visual C++) - RECOMMENDED

**Best for:** Production deployments, native Windows optimization, official support

#### Prerequisites

1. **Install Visual Studio**
   - Download: https://visualstudio.microsoft.com/downloads/
   - Choose: "Visual Studio Community" (free) or Professional/Enterprise
   - During installation, select: "Desktop development with C++"

2. **Install zlib Development Library**
   
   **Method A: Using vcpkg (Recommended)**
   ```batch
   # Clone vcpkg repository
   git clone https://github.com/Microsoft/vcpkg.git
   cd vcpkg
   
   # Build vcpkg
   .\bootstrap-vcpkg.bat
   
   # Install zlib for x64 (64-bit)
   .\vcpkg install zlib:x64-windows
   
   # Install zlib for x86 (32-bit) if needed
   .\vcpkg install zlib:x86-windows
   
   # Integrate with Visual Studio
   .\vcpkg integrate install
   ```
   
   **Method B: Manual Installation**
   - Download zlib from: http://www.zlib.net/
   - Extract to: `C:\zlib\` or similar
   - Build using the included Visual Studio project files

#### Compilation Steps

**Step 1: Open Developer Command Prompt**
- Press `Win + R`
- Type: `cmd`
- Navigate to where `papyrus_rpt_page_extractor.cpp` is located
  ```batch
  cd "C:\path\to\4_Migration_Instances"
  ```

**Step 2: Compile**
```batch
REM For x64 (64-bit) - Most common
cl.exe /O2 papyrus_rpt_page_extractor.cpp /Fe:papyrus_rpt_page_extractor.exe /link zlib.lib

REM OR with vcpkg integration
cl.exe /O2 papyrus_rpt_page_extractor.cpp /Fe:papyrus_rpt_page_extractor.exe /link zlib.lib
```

**Step 3: Verify**
```batch
dir papyrus_rpt_page_extractor.exe
```

Should show the executable file.

#### Full MSVC Compilation Example

```batch
REM Navigate to source directory
cd "C:\ISIS\apps\rpt_extractor"

REM Compile with optimization
cl.exe /O2 /EHsc /std:c++17 papyrus_rpt_page_extractor.cpp ^
  /Fe:papyrus_rpt_page_extractor.exe ^
  /link zlib.lib

REM Verify creation
if exist papyrus_rpt_page_extractor.exe (
  echo SUCCESS: Executable created
  papyrus_rpt_page_extractor.exe --help
) else (
  echo ERROR: Compilation failed
)
```

#### Compiler Flags Explained

| Flag | Meaning |
|------|---------|
| `/O2` | Optimize for speed (recommended) |
| `/EHsc` | Enable C++ exception handling |
| `/std:c++17` | Use C++17 standard (optional, auto-detected) |
| `/Fe:` | Output executable name |
| `/link` | Linker options follow |
| `zlib.lib` | Link with zlib library |

#### Troubleshooting MSVC

| Error | Solution |
|-------|----------|
| "zlib.h: No such file" | zlib not installed; use vcpkg method above |
| "undefined reference to 'uncompress'" | zlib.lib not found; add full path: `/link C:\path\to\zlib.lib` |
| "command not found: cl.exe" | Not in Visual Studio Developer Prompt; use "Developer Command Prompt for VS" |
| Very large exe file | Add `/O2` flag for optimization and smaller binary |

---

### Option 2: MinGW (GNU Compiler Collection for Windows)

**Best for:** Cross-platform compatibility, open-source toolchain

#### Prerequisites

1. **Install MinGW-w64**
   - Download: https://www.mingw-w64.org/
   - Or use: https://sourceforge.net/projects/mingw-w64/files/
   - Choose: x86_64 (for 64-bit) or i686 (for 32-bit)

2. **Install zlib Development Files**
   
   **Method A: Using MSYS2 (Easy)**
   ```bash
   # Install MSYS2 from: https://www.msys2.org/
   
   # In MSYS2 terminal:
   pacman -S mingw-w64-x86_64-zlib
   ```
   
   **Method B: Manual**
   - Download pre-built binaries from zlib.net
   - Extract to MinGW directory

#### Compilation Steps

**Step 1: Open Terminal**
- Open Command Prompt or PowerShell
- Navigate to source directory:
  ```batch
  cd "C:\path\to\4_Migration_Instances"
  ```

**Step 2: Compile**
```bash
g++ -std=c++17 -O2 -o papyrus_rpt_page_extractor.exe papyrus_rpt_page_extractor.cpp -lz
```

**Step 3: Verify**
```batch
dir papyrus_rpt_page_extractor.exe
```

#### Full MinGW Compilation Example

```bash
# Navigate to source
cd "C:\ISIS\apps\rpt_extractor"

# Compile with all flags
g++ -std=c++17 -O2 -Wall -Wextra ^
    -o papyrus_rpt_page_extractor.exe ^
    papyrus_rpt_page_extractor.cpp ^
    -lz

# Test execution
papyrus_rpt_page_extractor.exe
# Should show: "papyrus_rpt_page_extractor - RPT extraction for Papyrus"
```

#### Compiler Flags for MinGW

| Flag | Meaning |
|------|---------|
| `-std=c++17` | Use C++17 standard |
| `-O2` | Optimize for speed |
| `-Wall -Wextra` | Enable all warnings |
| `-o` | Output executable name |
| `-lz` | Link with zlib library |

#### Troubleshooting MinGW

| Error | Solution |
|-------|----------|
| "zlib.h: No such file or directory" | Install zlib-dev via MSYS2: `pacman -S mingw-w64-x86_64-zlib` |
| "undefined reference to 'uncompress'" | Add `-lz` flag at end of command |
| "command not found: g++" | MinGW not in PATH; use full path or add to PATH |

---

## 🍎 macOS Compilation

### Using GCC or Clang (Both Available)

**Best for:** Native macOS development, easy with Command Line Tools

#### Prerequisites

1. **Install Xcode Command Line Tools**
   ```bash
   xcode-select --install
   ```
   
   When prompted, click "Install" to install Command Line Tools
   - This includes gcc, clang, and zlib headers
   - Takes 5-10 minutes

2. **Verify Installation**
   ```bash
   clang --version
   gcc --version
   ```

#### Compilation Steps

**Step 1: Open Terminal**
- Press `Cmd + Space`, type `Terminal`, press Enter
- Navigate to source:
  ```bash
  cd ~/path/to/4_Migration_Instances
  # OR
  cd /Volumes/acasis/projects/python/ocbc/IntelliSTOR_Migration/4_Migration_Instances
  ```

**Step 2: Compile with Clang (Recommended)**
```bash
clang++ -std=c++17 -O2 -o papyrus_rpt_page_extractor papyrus_rpt_page_extractor.cpp -lz
```

**Step 3: Verify**
```bash
ls -lh papyrus_rpt_page_extractor
file papyrus_rpt_page_extractor
```

Should show an executable binary.

#### Full macOS Compilation Example

```bash
# Navigate to directory
cd /Volumes/acasis/projects/python/ocbc/IntelliSTOR_Migration/4_Migration_Instances

# Compile with Clang (preferred on macOS)
clang++ -std=c++17 -O2 -Wall -Wextra \
        -o papyrus_rpt_page_extractor \
        papyrus_rpt_page_extractor.cpp \
        -lz

# Verify executable
file papyrus_rpt_page_extractor
# Output: Mach-O 64-bit executable x86_64

# Test execution
./papyrus_rpt_page_extractor
# Should show: "papyrus_rpt_page_extractor - RPT extraction for Papyrus"
```

#### Alternative: Compile with GCC

```bash
g++ -std=c++17 -O2 -o papyrus_rpt_page_extractor papyrus_rpt_page_extractor.cpp -lz
```

#### Compiler Flags for macOS

| Flag | Meaning |
|------|---------|
| `-std=c++17` | Use C++17 standard |
| `-O2` | Optimize for speed |
| `-Wall -Wextra` | Enable warnings |
| `-o` | Output executable name |
| `-lz` | Link with zlib library |

#### macOS-Specific Notes

**Installing Additional Tools (if needed):**
```bash
# Using Homebrew for zlib (if not included with Command Line Tools)
brew install zlib

# If Homebrew not installed, install it first:
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

**Creating Executable Script (Optional):**
```bash
# Make it executable
chmod +x papyrus_rpt_page_extractor

# Create convenient launcher script
cat > extract_rpt.sh << 'EOF'
#!/bin/bash
./papyrus_rpt_page_extractor "$@"
EOF

chmod +x extract_rpt.sh
./extract_rpt.sh --help
```

#### Troubleshooting macOS

| Error | Solution |
|-------|----------|
| "command not found: clang++" | Install Xcode Command Line Tools: `xcode-select --install` |
| "zlib.h: No such file or directory" | Usually included; if not: `brew install zlib` |
| "undefined reference to 'uncompress'" | Ensure `-lz` flag at end of command |
| "permission denied" | Make executable: `chmod +x papyrus_rpt_page_extractor` |

---

## 🐧 Linux Compilation

**For reference (similar to macOS)**

```bash
# Install zlib development files (Ubuntu/Debian)
sudo apt-get install zlib1g-dev

# Or (RHEL/CentOS)
sudo yum install zlib-devel

# Compile
g++ -std=c++17 -O2 -o papyrus_rpt_page_extractor papyrus_rpt_page_extractor.cpp -lz

# Verify
./papyrus_rpt_page_extractor
```

---

## 🧪 Testing After Compilation

### Verify Executable Works

**Windows:**
```batch
papyrus_rpt_page_extractor.exe
# Shows help message and confirms executable works
```

**macOS/Linux:**
```bash
./papyrus_rpt_page_extractor
# Shows help message and confirms executable works
```

### Test with Sample File

**Create test script (Windows):**
```batch
REM Test with sample RPT (if available)
if exist sample.rpt (
    papyrus_rpt_page_extractor.exe sample.rpt "all" test_output.txt test_output.pdf
    echo.
    if %ERRORLEVEL% == 0 (
        echo SUCCESS: Extraction works
        dir test_output.*
    ) else (
        echo FAILED with code %ERRORLEVEL%
    )
)
```

**Test script (macOS/Linux):**
```bash
# Test with sample RPT (if available)
if [ -f sample.rpt ]; then
    ./papyrus_rpt_page_extractor sample.rpt "all" test_output.txt test_output.pdf
    
    if [ $? -eq 0 ]; then
        echo "SUCCESS: Extraction works"
        ls -lh test_output.*
    else
        echo "FAILED with code $?"
    fi
fi
```

---

## 📋 Compilation Checklist

### Windows - MSVC Path
- [ ] Visual Studio Community/Professional installed
- [ ] zlib installed (via vcpkg or manual)
- [ ] Developer Command Prompt opened
- [ ] Navigated to source directory
- [ ] Compilation command executed
- [ ] papyrus_rpt_page_extractor.exe created
- [ ] Executable tested successfully

### Windows - MinGW Path
- [ ] MinGW-w64 installed and in PATH
- [ ] zlib development files installed
- [ ] Terminal/PowerShell opened
- [ ] Navigated to source directory
- [ ] Compilation command executed
- [ ] papyrus_rpt_page_extractor.exe created
- [ ] Executable tested successfully

### macOS Path
- [ ] Xcode Command Line Tools installed (`xcode-select --install`)
- [ ] Verified with `clang --version`
- [ ] Terminal opened
- [ ] Navigated to source directory
- [ ] Compilation command executed
- [ ] papyrus_rpt_page_extractor executable created
- [ ] Executable tested successfully

---

## 🚀 Next Steps After Compilation

1. **Place Executable** in Papyrus directory
   - Windows: `C:\ISIS\apps\rpt_extractor\papyrus_rpt_page_extractor.exe`
   - macOS: `/path/to/papyrus/bin/papyrus_rpt_page_extractor`

2. **Verify Accessible** to Papyrus service account
   - Check file permissions
   - Ensure directory in system PATH (optional)

3. **Configure in Papyrus**
   - Create RPTExtractor class
   - Set program path to executable
   - Configure parameters (see PAPYRUS_EXPERT_VALIDATION.md)

4. **Test Integration**
   - Run ExtractPages method
   - Check ToolReturnCode
   - Verify outputs

---

## 💡 Pro Tips

### Optimized Compilation (Smaller Binary)
```bash
# Additional optimization flags
g++ -std=c++17 -O3 -march=native -ffast-math \
    -o papyrus_rpt_page_extractor \
    papyrus_rpt_page_extractor.cpp -lz

# Results in smaller, faster binary
```

### Static Linking (No Dependencies)
```bash
# Windows (MSVC)
cl.exe /O2 papyrus_rpt_page_extractor.cpp /Fe:papyrus_rpt_page_extractor.exe /link zlib.lib /SUBSYSTEM:CONSOLE

# Creates standalone executable (no zlib.dll needed)
```

### Debug Build (for troubleshooting)
```bash
# With debug symbols
g++ -std=c++17 -g -o papyrus_rpt_page_extractor papyrus_rpt_page_extractor.cpp -lz

# Larger file but better for debugging
```

### Batch Compilation (Multiple Targets)
```batch
REM Windows - compile for both x86 and x64
cl /O2 papyrus_rpt_page_extractor.cpp /Fe:papyrus_rpt_page_extractor_x64.exe /link zlib_x64.lib
cl /O2 papyrus_rpt_page_extractor.cpp /Fe:papyrus_rpt_page_extractor_x86.exe /link zlib_x86.lib
```

---

## ❓ Common Issues & Solutions

| Issue | Platform | Cause | Solution |
|-------|----------|-------|----------|
| zlib not found | Windows | Library not installed | Use vcpkg: `vcpkg install zlib:x64-windows` |
| zlib not found | macOS | Rare, usually included | `brew install zlib` |
| Command not found | Windows | Not in Developer Prompt | Use "Developer Command Prompt for VS" |
| Permission denied | macOS/Linux | Not executable | `chmod +x papyrus_rpt_page_extractor` |
| Large binary | All | Missing optimization | Add `-O2` flag |
| Crashes on run | All | Missing dependency | Ensure zlib library available at runtime |

---

## ✅ Verification Commands

**After successful compilation:**

```bash
# Check file type and size
file papyrus_rpt_page_extractor
ls -lh papyrus_rpt_page_extractor

# Verify it runs (shows help)
./papyrus_rpt_page_extractor

# Check for dependencies (macOS/Linux)
ldd papyrus_rpt_page_extractor        # Linux
otool -L papyrus_rpt_page_extractor   # macOS

# On Windows with MSVC, check with dumpbin
dumpbin /dependents papyrus_rpt_page_extractor.exe
```

---

## 📞 Still Having Issues?

1. **Check zlib installation:**
   - Windows: `dir C:\path\to\zlib`
   - macOS: `brew list zlib`
   - Linux: `apt list --installed | grep zlib`

2. **Verify C++ compiler:**
   - Windows: `cl.exe /?`
   - macOS: `clang++ --version`
   - Linux: `g++ --version`

3. **Review error messages carefully** - they usually indicate exactly what's missing

4. **Try simplest approach first**, then optimize if needed

---

**Status: ✅ Comprehensive Compilation Guide Ready**
