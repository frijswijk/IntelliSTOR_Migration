# PoDoFo Setup for PDF Page Extraction and Watermarking

## What is PoDoFo?

PoDoFo is a C++ PDF library that allows you to:
- Read and parse PDF files
- Extract specific pages
- Create new PDFs
- Add watermarks (text or images)
- Preserve page orientation (portrait/landscape)

## Installation for MinGW on Windows

### Option 1: Download Pre-built Binaries (Recommended)

1. Visit: https://github.com/podofo/podofo/releases
2. Download latest Windows release (look for MinGW or Windows build)
3. Extract to: `C:\Users\freddievr\podofo\`

### Option 2: Build from Source

#### Prerequisites
```batch
# Install dependencies via MSYS2/MinGW
pacman -S mingw-w64-x86_64-freetype
pacman -S mingw-w64-x86_64-zlib
pacman -S mingw-w64-x86_64-libpng
pacman -S mingw-w64-x86_64-libjpeg-turbo
pacman -S mingw-w64-x86_64-cmake
```

#### Build Steps
```batch
# Clone PoDoFo
cd C:\Users\freddievr
git clone https://github.com/podofo/podofo.git
cd podofo

# Create build directory
mkdir build
cd build

# Configure with CMake
cmake .. -G "MinGW Makefiles" ^
  -DCMAKE_BUILD_TYPE=Release ^
  -DCMAKE_INSTALL_PREFIX=C:\Users\freddievr\podofo_install

# Build
mingw32-make -j4

# Install
mingw32-make install
```

### Option 3: Use QPDF Instead (Simpler Alternative)

QPDF is easier to build and has similar features:

```batch
# Download from: https://github.com/qpdf/qpdf/releases
# Or use vcpkg:
git clone https://github.com/microsoft/vcpkg
cd vcpkg
bootstrap-vcpkg.bat
vcpkg install qpdf:x64-windows-static
```

## Compilation with PoDoFo

### Updated compile.bat

```batch
set PODOFO=C:\Users\freddievr\podofo_install
set MINGW=C:\Users\freddievr\mingw64\bin

"%MINGW%\g++.exe" -std=c++17 -O2 -static ^
  -I"%PODOFO%\include" ^
  -o papyrus_rpt_page_extractor.exe ^
  papyrus_rpt_page_extractor.cpp ^
  -L"%PODOFO%\lib" ^
  -lpodofo ^
  -lfreetype -lpng -ljpeg -lz
```

## Alternative: Use Command-Line PDF Tools

If library integration is too complex, you can use external tools:

### Using PDFtk (PDF Toolkit)

Download: https://www.pdflabs.com/tools/pdftk-the-pdf-toolkit/

```cpp
// In your C++ code, call pdftk via system()
std::string cmd = "pdftk input.pdf cat 1-5 output pages_1_5.pdf";
system(cmd.c_str());

// For watermarking
std::string cmd2 = "pdftk input.pdf stamp watermark.pdf output watermarked.pdf";
system(cmd2.c_str());
```

### Using QPDF (Recommended for CLI)

Download: https://qpdf.sourceforge.io/

```cpp
// Extract pages 1-5
system("qpdf input.pdf --pages . 1-5 -- output.pdf");

// For watermarking, use qpdf + overlay
system("qpdf input.pdf --overlay watermark.pdf -- output.pdf");
```

## Recommended Approach

For your use case, I recommend:

**Use QPDF as an external tool** called from C++ via `system()` or `CreateProcess()`

**Why:**
- ✅ No compilation complexity
- ✅ Standalone executable (can be bundled)
- ✅ Excellent page extraction
- ✅ Supports watermarking via overlays
- ✅ Preserves PDF structure perfectly

**Implementation:**
1. Bundle `qpdf.exe` with your extractor
2. Call it programmatically for PDF operations
3. Keep the rest of your C++ code unchanged

This is much simpler than linking a PDF library statically!
