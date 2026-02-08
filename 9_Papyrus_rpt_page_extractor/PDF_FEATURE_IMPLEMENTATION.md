# PDF Page Extraction & Watermarking Implementation Guide

## Overview

This guide shows how to add PDF page extraction and watermarking to `papyrus_rpt_page_extractor`.

**Current behavior:**
- Extracts ALL PDF pages from RPT binary objects
- No page-level filtering
- No watermarking

**New behavior:**
- Extract specific PDF pages based on selection rules (same as text pages)
- Apply watermarks (confidential.png, etc.)
- Preserve page orientation (portrait/landscape)
- Create valid Adobe-compatible PDFs

---

## ✅ RECOMMENDED APPROACH: External QPDF Tool

**Why QPDF?**
- ✅ No compilation complexity (standalone .exe)
- ✅ Excellent PDF manipulation
- ✅ Can bundle with your extractor
- ✅ Called via `system()` - simple integration
- ✅ Supports all PDF versions and orientations
- ✅ Free and open-source

### Step 1: Download QPDF

**Download Location:**
https://github.com/qpdf/qpdf/releases

**For Windows:**
1. Download: `qpdf-11.9.0-bin-mingw64.zip` (or latest version)
2. Extract to: `C:\Users\freddievr\qpdf\`
3. Key file: `C:\Users\freddievr\qpdf\bin\qpdf.exe`

**Or use Chocolatey:**
```batch
choco install qpdf
```

### Step 2: Download ImageMagick (For Watermark Conversion)

ImageMagick converts PNG watermarks to PDF format.

**Download:**
https://imagemagick.org/script/download.php#windows

**Install:**
1. Download: `ImageMagick-7.1.x-portable-Q16-HDRI-x64.zip`
2. Extract to: `C:\Users\freddievr\imagemagick\`
3. Key file: `C:\Users\freddievr\imagemagick\magick.exe`

**Or use Chocolatey:**
```batch
choco install imagemagick
```

### Step 3: Verify Tools Work

```batch
# Test QPDF
C:\Users\freddievr\qpdf\bin\qpdf.exe --version

# Test ImageMagick
C:\Users\freddievr\imagemagick\magick.exe --version
```

---

## Implementation: Integrate into papyrus_rpt_page_extractor

### Option A: Bundle QPDF with Extractor (Recommended for Airgap)

Copy these files to your extractor directory:

```
9_Papyrus_rpt_page_extractor/
  ├── papyrus_rpt_page_extractor.exe
  ├── tools/
  │   ├── qpdf.exe
  │   ├── magick.exe
  │   └── watermarks/
  │       └── confidential.png
```

### Option B: Use System-Installed Tools

If QPDF and ImageMagick are in PATH, the extractor will find them automatically.

---

## Code Integration

### Modified Extractor Functions

Add these helper functions to `papyrus_rpt_page_extractor.cpp`:

```cpp
// ============================================================================
// PDF Page Extraction Functions
// ============================================================================

static std::string find_qpdf() {
    // Check bundled tools first
    std::string bundled = "./tools/qpdf.exe";
    if (fs::exists(bundled)) return bundled;

    // Check common install locations
    std::vector<std::string> paths = {
        "C:\\Users\\freddievr\\qpdf\\bin\\qpdf.exe",
        "C:\\Program Files\\qpdf\\bin\\qpdf.exe",
        "qpdf.exe"  // Try PATH
    };

    for (const auto& p : paths) {
        if (fs::exists(p) || system((p + " --version >nul 2>&1").c_str()) == 0) {
            return p;
        }
    }

    return "";
}

static std::string find_magick() {
    std::string bundled = "./tools/magick.exe";
    if (fs::exists(bundled)) return bundled;

    std::vector<std::string> paths = {
        "C:\\Users\\freddievr\\imagemagick\\magick.exe",
        "C:\\Program Files\\ImageMagick\\magick.exe",
        "magick.exe"
    };

    for (const auto& p : paths) {
        if (fs::exists(p) || system((p + " --version >nul 2>&1").c_str()) == 0) {
            return p;
        }
    }

    return "";
}

static bool extract_pdf_pages(const std::string& qpdf_exe,
                              const std::string& input_pdf,
                              const std::string& output_pdf,
                              const std::vector<int>& pages) {
    if (pages.empty()) {
        // No filtering - just copy the PDF
        fs::copy(input_pdf, output_pdf, fs::copy_options::overwrite_existing);
        return true;
    }

    // Build page specification: "1,3,5-7,10"
    std::ostringstream page_spec;
    for (size_t i = 0; i < pages.size(); ++i) {
        if (i > 0) page_spec << ",";
        page_spec << pages[i];
    }

    // QPDF command
    std::ostringstream cmd;
    cmd << "\"" << qpdf_exe << "\" \"" << input_pdf << "\" "
        << "--pages . " << page_spec.str() << " -- \"" << output_pdf << "\"";

    int result = system(cmd.str().c_str());
    return (result == 0);
}

static bool create_watermark_pdf(const std::string& magick_exe,
                                 const std::string& image_path,
                                 const std::string& watermark_pdf,
                                 int width = 612, int height = 792) {
    // Convert PNG to PDF with page size (Letter: 612x792, A4: 595x842)
    std::ostringstream cmd;
    cmd << "\"" << magick_exe << "\" convert \"" << image_path << "\" "
        << "-page " << width << "x" << height << " "
        << "-gravity center "
        << "\"" << watermark_pdf << "\"";

    int result = system(cmd.str().c_str());
    return (result == 0);
}

static bool apply_watermark(const std::string& qpdf_exe,
                           const std::string& input_pdf,
                           const std::string& watermark_pdf,
                           const std::string& output_pdf) {
    // QPDF overlay command
    std::ostringstream cmd;
    cmd << "\"" << qpdf_exe << "\" \"" << input_pdf << "\" "
        << "--overlay \"" << watermark_pdf << "\" -- \"" << output_pdf << "\"";

    int result = system(cmd.str().c_str());
    return (result == 0);
}

static bool process_pdf_with_options(const std::string& input_pdf,
                                     const std::string& output_pdf,
                                     const std::vector<int>& pages,
                                     const std::string& watermark_image) {
    std::string qpdf_exe = find_qpdf();
    if (qpdf_exe.empty()) {
        std::cerr << "WARNING: QPDF not found. Copying full PDF without page extraction.\n";
        fs::copy(input_pdf, output_pdf, fs::copy_options::overwrite_existing);
        return false;
    }

    // Step 1: Extract pages (or copy if no filtering)
    std::string temp_extracted = output_pdf + ".temp.pdf";
    if (!extract_pdf_pages(qpdf_exe, input_pdf, temp_extracted, pages)) {
        std::cerr << "ERROR: Failed to extract PDF pages\n";
        return false;
    }

    // Step 2: Apply watermark if provided
    if (!watermark_image.empty() && fs::exists(watermark_image)) {
        std::string magick_exe = find_magick();
        if (magick_exe.empty()) {
            std::cerr << "WARNING: ImageMagick not found. Skipping watermark.\n";
            fs::rename(temp_extracted, output_pdf);
        } else {
            std::string watermark_pdf = output_pdf + ".watermark.pdf";

            // Convert image to PDF
            if (!create_watermark_pdf(magick_exe, watermark_image, watermark_pdf)) {
                std::cerr << "WARNING: Failed to create watermark PDF. Skipping watermark.\n";
                fs::rename(temp_extracted, output_pdf);
            } else {
                // Apply watermark
                if (!apply_watermark(qpdf_exe, temp_extracted, watermark_pdf, output_pdf)) {
                    std::cerr << "WARNING: Failed to apply watermark.\n";
                    fs::rename(temp_extracted, output_pdf);
                } else {
                    // Cleanup temp files
                    fs::remove(temp_extracted);
                    fs::remove(watermark_pdf);
                }
            }
        }
    } else {
        // No watermark requested
        fs::rename(temp_extracted, output_pdf);
    }

    return true;
}
```

### Modified main() Function

Update the binary extraction section in `main()`:

```cpp
// OLD CODE (extracts all PDF pages):
for (const auto& entry : binary_entries) {
    auto bin_data = decompress_data(input_rpt, entry.absolute_offset(),
                                   entry.compressed_size, entry.uncompressed_size);
    if (bin_data) {
        bin_out.write(reinterpret_cast<const char*>(bin_data->data()),
                     bin_data->size());
    }
}

// NEW CODE (extracts selected PDF pages):
// First, extract full PDF to temp file
std::string temp_full_pdf = output_binary + ".full.pdf";
std::ofstream full_pdf_out(temp_full_pdf, std::ios::binary);
for (const auto& entry : binary_entries) {
    auto bin_data = decompress_data(input_rpt, entry.absolute_offset(),
                                   entry.compressed_size, entry.uncompressed_size);
    if (bin_data) {
        full_pdf_out.write(reinterpret_cast<const char*>(bin_data->data()),
                          bin_data->size());
    }
}
full_pdf_out.close();

// Now extract selected pages with optional watermark
std::string watermark = "./tools/watermarks/confidential.png";
if (!fs::exists(watermark)) watermark = "";

// Convert text page numbers to PDF page numbers
// (Assuming 1:1 mapping for simplicity - adjust if needed)
std::vector<int> pdf_pages;
for (int page : selected_pages) {
    pdf_pages.push_back(page);  // May need adjustment based on your RPT structure
}

process_pdf_with_options(temp_full_pdf, output_binary, pdf_pages, watermark);

// Cleanup
fs::remove(temp_full_pdf);
```

---

## Usage Examples

### Example 1: Extract Pages 1-5 from RPT (with PDF)

```batch
papyrus_rpt_page_extractor.exe input.rpt "pages:1-5" output.txt output.pdf

# Output:
# - output.txt: Concatenated text pages 1-5
# - output.pdf: PDF pages 1-5 only (if binary objects present)
```

### Example 2: Extract Sections with Watermark

```batch
# First, place watermark image
copy confidential.png .\tools\watermarks\confidential.png

# Extract sections
papyrus_rpt_page_extractor.exe input.rpt "sections:14259,14260" output.txt output.pdf

# Output PDF will have watermark on each page
```

### Example 3: Extract All Pages (No Filtering)

```batch
papyrus_rpt_page_extractor.exe input.rpt "all" output.txt output.pdf

# Extracts full PDF with optional watermark
```

---

## Watermark Customization

### Watermark Placement Options

Edit the `create_watermark_pdf()` function to customize:

```cpp
// Center watermark
"-gravity center"

// Top-right corner
"-gravity northeast"

// Bottom-left corner
"-gravity southwest"

// Custom position
"-gravity center -geometry +50+100"  // Offset by 50x, 100y

// Transparency
"-alpha on -channel A -evaluate set 30%"  // 30% opacity

// Rotate
"-rotate 45"  // 45-degree diagonal
```

### Multiple Watermark Images

```cpp
// Choose watermark based on classification
std::string watermark;
if (is_confidential) {
    watermark = "./tools/watermarks/confidential.png";
} else if (is_internal) {
    watermark = "./tools/watermarks/internal.png";
} else {
    watermark = "";  // No watermark
}

process_pdf_with_options(temp_pdf, output_pdf, pages, watermark);
```

---

## Page Orientation Handling

QPDF automatically preserves page orientation (portrait/landscape). No special handling needed!

**Verification:**
```batch
# Check orientation of pages in PDF
qpdf --show-pages input.pdf

# Output shows:
# page 1: 612 x 792 (portrait)
# page 2: 792 x 612 (landscape)
```

---

## Deployment for Airgap

### Files to Bundle

```
papyrus_rpt_page_extractor.exe
tools/
  ├── qpdf.exe
  ├── magick.exe
  ├── qpdf-dll-14.dll  (if needed)
  └── watermarks/
      ├── confidential.png
      ├── internal.png
      └── draft.png
```

### Size Estimate

- `qpdf.exe`: ~2 MB
- `magick.exe`: ~50 MB (can be reduced with static build)
- Your extractor: ~3 MB
- **Total**: ~55 MB

**Alternative (Smaller):**
Use `pdftk.exe` instead of ImageMagick for watermarking (only ~3 MB total).

---

## Testing Checklist

- [ ] Extract pages 1-5 from test RPT
- [ ] Verify output PDF opens in Adobe Reader
- [ ] Check page count matches selection
- [ ] Verify landscape pages preserve orientation
- [ ] Apply watermark and verify visibility
- [ ] Test with no PDF present (should skip gracefully)
- [ ] Test "all" selection (full PDF)
- [ ] Test section-based extraction

---

## Troubleshooting

### "QPDF not found"
- Verify `qpdf.exe` is in `./tools/` or PATH
- Try running: `qpdf.exe --version` manually
- Check file permissions

### "Failed to extract PDF pages"
- Check if input PDF is valid: `qpdf --check input.pdf`
- Verify page numbers are within range
- Check disk space for temp files

### "Failed to create watermark PDF"
- Verify ImageMagick is installed
- Check watermark image exists and is valid PNG
- Try converting manually: `magick convert confidential.png test.pdf`

### Watermark not visible
- Increase opacity in ImageMagick command
- Check watermark image has transparency (PNG with alpha channel)
- Verify watermark PDF was created successfully

---

## Performance Considerations

**Processing Time:**
- Page extraction: ~1-2 seconds per PDF
- Watermarking: +1-2 seconds per PDF
- Total overhead: ~2-4 seconds per RPT file with PDF

**Memory Usage:**
- Minimal - QPDF streams data efficiently
- Temp files are cleaned up automatically

---

## Summary: Recommended Implementation

1. ✅ Download QPDF and ImageMagick
2. ✅ Bundle with your extractor in `./tools/` directory
3. ✅ Add the helper functions from this guide
4. ✅ Modify `main()` to call `process_pdf_with_options()`
5. ✅ Place watermark images in `./tools/watermarks/`
6. ✅ Test with various RPT files
7. ✅ Deploy to airgap machine

**Result:** Full PDF page extraction and watermarking support, bundled as standalone executables!

---

**Last Updated:** 2026-02-08
**Status:** Ready for implementation
**Dependencies:** QPDF 11.x, ImageMagick 7.x (optional for watermarks)
