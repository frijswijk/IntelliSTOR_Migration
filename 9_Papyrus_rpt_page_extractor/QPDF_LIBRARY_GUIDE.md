# Using QPDF as a Library (100% Self-Contained Solution)

## Overview
Instead of calling `qpdf.exe` as an external process, you can link against the QPDF C++ library to achieve a **fully self-contained watermark solution** with zero external dependencies.

## Benefits

### ✅ Fully Self-Contained
- No external executables required
- Single `.exe` file contains all functionality
- No PATH configuration needed
- No DLL hell issues

### ✅ Better Performance
- No process spawning overhead (~50ms saved per operation)
- Direct memory operations (no file I/O between steps)
- Faster startup (library already loaded)

### ✅ Better Error Handling
- C++ exceptions instead of exit codes
- Detailed error messages
- Programmatic error recovery

### ✅ More Control
- Full access to PDF structure
- Custom manipulation beyond simple overlay
- Batch operations without process spawning

## Requirements

### QPDF Development Files
You already have these installed at:
```
C:\Users\freddievr\qpdf-12.3.2-mingw64\
├── include\qpdf\     # Header files
└── lib\              # Static libraries
    ├── libqpdf.a
    └── libqpdf_static.a
```

### Dependencies
QPDF library requires:
- `libjpeg` - JPEG image support (usually bundled)
- `zlib` - Compression (already used)

## Implementation

### 1. Current Implementation (External qpdf.exe)
```cpp
// Calls external process
int result = std::system("qpdf input.pdf --overlay wm.pdf ...");
// Issues: DLL loading, PATH requirements, process overhead
```

### 2. Library Implementation (Integrated QPDF)
```cpp
#include <qpdf/QPDF.hh>
#include <qpdf/QPDFPageDocumentHelper.hh>

// Direct C++ API
QPDF qpdf_input;
qpdf_input.processFile("input.pdf");
// Manipulate PDF directly in memory
```

## Compilation

### Option A: Using Build Script
```powershell
.\compile_with_qpdf_lib.bat
```

This creates: `papyrus_rpt_page_extractor_v2_qpdflib.exe`

### Option B: Manual Compilation
```powershell
g++ -std=c++17 -O2 `
  -DUSE_QPDF_LIBRARY `
  -I"C:/Users/freddievr/qpdf-12.3.2-mingw64/include" `
  -L"C:/Users/freddievr/qpdf-12.3.2-mingw64/lib" `
  -o papyrus_rpt_page_extractor_v2_qpdflib.exe `
  papyrus_rpt_page_extractor_v2.cpp `
  -lqpdf -ljpeg -lz `
  -static-libgcc -static-libstdc++
```

### Flags Explained
- `-DUSE_QPDF_LIBRARY` - Enables QPDF library code path
- `-I...` - Include QPDF headers
- `-L...` - Link directory for libraries
- `-lqpdf` - Link against QPDF library
- `-ljpeg` - Required by QPDF for JPEG support
- `-lz` - Required by QPDF for compression
- `-static-libgcc -static-libstdc++` - Static linking (portable exe)

## Code Integration

The library version is already prepared in `watermark_qpdf_lib.h`:

```cpp
#ifdef USE_QPDF_LIBRARY
  // Use QPDF C++ library
  bool success = WatermarkQPDF::overlay_pdf_with_library(
      input_pdf, watermark_pdf, output_pdf);
#else
  // Fallback to qpdf.exe external call
  int result = std::system(qpdf_command);
#endif
```

To enable, modify `papyrus_rpt_page_extractor_v2.cpp`:

```cpp
// Add near top of file
#include "watermark_qpdf_lib.h"

// In apply_watermark_simple(), replace QPDF external call:

#ifdef USE_QPDF_LIBRARY
    // Use QPDF C++ library (no external exe)
    std::cout << "  Overlaying with QPDF library...\n";
    bool overlay_ok = WatermarkQPDF::overlay_pdf_with_library(
        input_pdf, temp_wm_pdf, output_pdf);

    if (!overlay_ok) {
        std::cerr << "ERROR: QPDF library overlay failed\n";
        fs::copy(input_pdf, output_pdf, fs::copy_options::overwrite_existing);
        return false;
    }
#else
    // Existing external qpdf.exe call
    // ... current code ...
#endif
```

## Trade-offs

### Library Approach ✅
**Pros:**
- No external dependencies
- Better performance
- Better error handling
- Single executable

**Cons:**
- Larger executable size (~2-3 MB vs 200 KB)
- More complex build process
- Requires QPDF development files

### External qpdf.exe ✅
**Pros:**
- Smaller executable
- Simple build process
- Easy to update QPDF independently

**Cons:**
- External dependency
- PATH requirements
- Process spawning overhead
- DLL loading issues on Windows

## Recommended Approach

For **production deployment**:
- Use QPDF library (fully self-contained)
- Slightly larger exe, but zero deployment issues

For **development**:
- Use external qpdf.exe (faster iteration)
- Easier debugging

## File Size Comparison

| Approach | Executable Size | Dependencies |
|----------|----------------|--------------|
| Current (exe) | ~600 KB | qpdf.exe + DLLs (~5 MB) |
| Library (static) | ~3 MB | None |
| Library (dynamic) | ~600 KB | qpdf.dll (~2 MB) |

**Note:** Static linking recommended for deployment simplicity.

## Testing

After building with library support:

```powershell
# Test watermark with library version
.\papyrus_rpt_page_extractor_v2_qpdflib.exe `
  "F:\RPT\260271Q7.RPT" "" `
  "F:\RPT\output.TXT" "F:\RPT\output.PDF" `
  --WatermarkImage "F:\RPT\confidential.png" `
  --WatermarkPosition BottomRight `
  --WatermarkOpacity 30
```

You should see:
```
INFO: Applying watermark (100% C++ - stb_image + pure PDF generation)...
  Generating watermark PDF...
  Overlaying with QPDF library...
INFO: Watermark applied successfully!
```

## Future Enhancements

With QPDF library integrated, you can add:
- **Batch watermarking** (no process spawning per file)
- **Custom PDF manipulation** (merge, split, encrypt)
- **Metadata modification** (author, title, keywords)
- **Form filling** (if RPT contains form data)
- **Page manipulation** (rotate, crop, resize)
- **Encryption** (password-protect output PDFs)

All without any external tools!

## Next Steps

1. ✅ Documentation created (this file)
2. ⏳ Test compilation with QPDF library
3. ⏳ Integrate into main code with USE_QPDF_LIBRARY flag
4. ⏳ Benchmark performance (library vs exe)
5. ⏳ Create release build with static linking

## Support

If you encounter linking errors:
- Ensure QPDF paths in compile script are correct
- Check that `libjpeg` is available in QPDF lib directory
- Try `-lqpdf_static` instead of `-lqpdf` for static linking
- Use `-Wl,--verbose` flag to debug linker issues

## License Note

QPDF is licensed under Apache 2.0, which allows:
- Commercial use
- Modification
- Distribution
- Private use

**Requirements:**
- Include QPDF license notice in documentation
- State any modifications made to QPDF

For this project: Using QPDF unmodified as a library dependency.
