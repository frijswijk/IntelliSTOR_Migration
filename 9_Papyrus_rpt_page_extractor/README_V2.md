# Papyrus RPT Page Extractor V2 - Parameter-Driven Watermarking

## What's New in V2

Version 2 adds **parameter-driven watermark support** while maintaining **100% backward compatibility** with the original version.

### Key Features

✅ **Optional watermarking** - no watermark if parameters not provided
✅ **Flexible positioning** - 10 position options including Center, corners, and Repeat (tile)
✅ **Page-aware placement** - calculates position based on actual PDF page dimensions
✅ **Customizable appearance** - rotation (-180° to 180°), opacity (0-100%), scale (0.5-2.0)
✅ **Repeat/tile mode** - watermark pattern from top-left to bottom-right
✅ **PDF-only application** - watermarks only applied to PDF output, not text files
✅ **Backward compatible** - works as drop-in replacement for original version

## Quick Start

### 1. Compile the Tool

```bash
# Run the compilation script
compile_v2.bat
```

Or compile manually:

```bash
# GCC/MinGW
g++ -std=c++17 -O2 -static -o papyrus_rpt_page_extractor_v2.exe papyrus_rpt_page_extractor_v2.cpp -lz -s

# MSVC
cl /EHsc /O2 /MT papyrus_rpt_page_extractor_v2.cpp /Fe:papyrus_rpt_page_extractor_v2.exe
```

### 2. Create Watermark Images (Optional)

```bash
# Run the watermark creation script
create_watermarks.bat
```

This creates common watermarks in the `watermarks/` directory:
- `confidential_red.png`, `confidential_gray.png`
- `draft.png`, `draft_blue.png`
- `sample.png`, `copy.png`
- `stamp_approved.png`, `stamp_void.png`
- And more...

### 3. Basic Usage (No Watermark)

```bash
# Extract all pages without watermark
papyrus_rpt_page_extractor_v2.exe input.rpt all output.txt output.pdf
```

This works exactly like the original version.

### 4. With Watermark

```bash
# Extract with centered watermark (default settings)
papyrus_rpt_page_extractor_v2.exe input.rpt all output.txt output.pdf ^
  --WatermarkImage watermarks\confidential_red.png

# Extract with custom watermark settings
papyrus_rpt_page_extractor_v2.exe input.rpt pages:1-10 output.txt output.pdf ^
  --WatermarkImage watermarks\confidential_red.png ^
  --WatermarkPosition Center ^
  --WatermarkRotation -45 ^
  --WatermarkOpacity 30 ^
  --WatermarkScale 1.5
```

## Command-Line Reference

### Required Arguments (same as V1)

```
papyrus_rpt_page_extractor_v2.exe <input_rpt> <selection_rule> <output_txt> <output_binary>
```

| Argument         | Description                                              |
|------------------|----------------------------------------------------------|
| `input_rpt`      | Path to input .rpt file                                  |
| `selection_rule` | `all`, `pages:1-5`, `sections:14259,14260`, or `14259,14260` |
| `output_txt`     | Path for text output                                     |
| `output_binary`  | Path for PDF/binary output                               |

### Watermark Parameters (all optional)

| Parameter                      | Description                          | Default | Range/Options                    |
|--------------------------------|--------------------------------------|---------|----------------------------------|
| `--WatermarkImage <path>`      | Path to watermark image              | *(none)* | Any PNG, JPG, GIF file          |
| `--WatermarkPosition <pos>`    | Watermark placement                  | `Center` | See positions table below        |
| `--WatermarkRotation <degrees>`| Rotation angle                       | `0`     | `-180` to `180` degrees          |
| `--WatermarkOpacity <percent>` | Transparency level                   | `30`    | `0` to `100`%                    |
| `--WatermarkScale <scale>`     | Size multiplier                      | `1.0`   | `0.5` to `2.0`                   |

### Watermark Positions

| Position         | Description                              |
|------------------|------------------------------------------|
| `Center`         | Centered on page (default)               |
| `TopLeft`        | Top-left corner                          |
| `TopCenter`      | Top center                               |
| `TopRight`       | Top-right corner                         |
| `MiddleLeft`     | Middle of left edge                      |
| `MiddleRight`    | Middle of right edge                     |
| `BottomLeft`     | Bottom-left corner                       |
| `BottomCenter`   | Bottom center                            |
| `BottomRight`    | Bottom-right corner                      |
| `Repeat`         | Tiled pattern (top-left to bottom-right) |

## Usage Examples

### Example 1: Basic Extraction (No Watermark)
```bash
papyrus_rpt_page_extractor_v2.exe report.rpt all output.txt output.pdf
```
**Output:** Standard extraction without watermark

---

### Example 2: Centered Watermark (Default Settings)
```bash
papyrus_rpt_page_extractor_v2.exe report.rpt all output.txt output.pdf ^
  --WatermarkImage watermarks\confidential_red.png
```
**Output:** 30% opacity watermark in center

---

### Example 3: Diagonal "CONFIDENTIAL" Banner
```bash
papyrus_rpt_page_extractor_v2.exe report.rpt all output.txt output.pdf ^
  --WatermarkImage watermarks\confidential_red.png ^
  --WatermarkPosition Center ^
  --WatermarkRotation -45 ^
  --WatermarkOpacity 25 ^
  --WatermarkScale 1.8
```
**Output:** Large diagonal watermark at 25% opacity

---

### Example 4: Top-Right Logo
```bash
papyrus_rpt_page_extractor_v2.exe report.rpt pages:1-10 output.txt output.pdf ^
  --WatermarkImage watermarks\company_logo.png ^
  --WatermarkPosition TopRight ^
  --WatermarkOpacity 50 ^
  --WatermarkScale 0.6
```
**Output:** Small company logo in top-right corner

---

### Example 5: Tiled/Repeated Pattern
```bash
papyrus_rpt_page_extractor_v2.exe report.rpt all output.txt output.pdf ^
  --WatermarkImage watermarks\pattern_confidential.png ^
  --WatermarkPosition Repeat ^
  --WatermarkOpacity 15 ^
  --WatermarkScale 0.4
```
**Output:** Subtle tiled watermark pattern across entire page

---

### Example 6: Bottom-Right Stamp
```bash
papyrus_rpt_page_extractor_v2.exe report.rpt sections:14259,14260 output.txt output.pdf ^
  --WatermarkImage watermarks\stamp_approved.png ^
  --WatermarkPosition BottomRight ^
  --WatermarkOpacity 80 ^
  --WatermarkScale 0.3
```
**Output:** Small "APPROVED" stamp in bottom-right corner

---

### Example 7: Rotated Top Watermark
```bash
papyrus_rpt_page_extractor_v2.exe report.rpt pages:1-5 output.txt output.pdf ^
  --WatermarkImage watermarks\draft_blue.png ^
  --WatermarkPosition TopCenter ^
  --WatermarkRotation 15 ^
  --WatermarkOpacity 45 ^
  --WatermarkScale 0.8
```
**Output:** Slightly rotated "DRAFT" watermark at top

---

## How It Works

### Page Size Detection

The tool automatically detects PDF page dimensions and calculates watermark placement accordingly:

- **Letter size**: 612 × 792 points
- **A4 size**: 595 × 842 points
- **Legal size**: 612 × 1008 points
- **Custom sizes**: Detected via QPDF

### Position Calculation

Watermark positions are calculated based on actual page dimensions:

```
TopLeft: (0, 0)
TopCenter: (page_width/2, 0)
TopRight: (page_width, 0)
MiddleLeft: (0, page_height/2)
Center: (page_width/2, page_height/2)
MiddleRight: (page_width, page_height/2)
BottomLeft: (0, page_height)
BottomCenter: (page_width/2, page_height)
BottomRight: (page_width, page_height)
Repeat: Tiled from (0,0) to (page_width, page_height)
```

### Scale Calculation

The base watermark size is **30% of the smaller page dimension**, then multiplied by scale factor:

```
base_size = min(page_width, page_height) × 0.3
final_size = base_size × scale_factor
```

Examples:
- `--WatermarkScale 0.5` → 15% of page (half default)
- `--WatermarkScale 1.0` → 30% of page (default)
- `--WatermarkScale 2.0` → 60% of page (double)

### Opacity/Transparency

Opacity controls how transparent the watermark appears:

- `0` = Invisible (0% opacity)
- `30` = Default (subtle, semi-transparent)
- `100` = Solid (fully opaque)

### Rotation

Watermarks rotate around their center point:

- Positive angles: Clockwise rotation
- Negative angles: Counter-clockwise rotation
- `-45` degrees: Classic diagonal watermark

## Dependencies

### Required

1. **QPDF** - For PDF page extraction
   - Download: https://github.com/qpdf/qpdf/releases
   - Place `qpdf.exe` in `./tools/` or system PATH

### Required for Watermarking

2. **ImageMagick** - For watermark processing
   - Download: https://imagemagick.org/
   - Place `magick.exe` in `./tools/` or system PATH

### Optional

3. **zlib** - Included with MinGW/MSVC (for compression)

## File Structure

```
9_Papyrus_rpt_page_extractor/
│
├── papyrus_rpt_page_extractor.cpp          # Original version
├── papyrus_rpt_page_extractor_v2.cpp       # V2 with watermarks
│
├── compile_v2.bat                          # Compilation script
├── create_watermarks.bat                   # Watermark image creator
├── watermark_examples.bat                  # Usage examples
│
├── README_V2.md                            # This file
├── WATERMARK_USAGE.md                      # Detailed usage guide
│
├── tools/                                  # Optional dependencies
│   ├── qpdf.exe
│   └── magick.exe
│
└── watermarks/                             # Generated watermarks
    ├── confidential_red.png
    ├── confidential_gray.png
    ├── draft.png
    ├── sample.png
    ├── stamp_approved.png
    ├── pattern_confidential.png
    └── ...
```

## Troubleshooting

### "WARNING: QPDF not found"
**Solution:** Install QPDF or place `qpdf.exe` in `./tools/` directory

### "WARNING: ImageMagick not found. Skipping watermark."
**Solution:** Install ImageMagick or place `magick.exe` in `./tools/` directory
**Note:** PDF extraction still works, just without watermarking

### Watermark too large/small
**Solution:** Adjust `--WatermarkScale` parameter (try 0.3 to 1.5 range)

### Watermark too visible/invisible
**Solution:** Adjust `--WatermarkOpacity` parameter (try 20-50 for subtle, 60-90 for prominent)

### Repeat mode watermarks overlap
**Solution:** Reduce `--WatermarkScale` to 0.3-0.5 and increase `--WatermarkOpacity` slightly

### Compilation fails with zlib error
**Solution:**
- GCC: Install zlib development package or use static linking (`-lz`)
- MSVC: Ensure zlib is in include/lib paths

## Performance Considerations

| Mode                    | Pages/Second | Notes                                      |
|-------------------------|--------------|--------------------------------------------|
| No watermark            | ~50-100      | Fast extraction only                       |
| With watermark (Center) | ~0.5-2       | Depends on page complexity & image size    |
| With watermark (Repeat) | ~0.3-1       | Slower due to tiling calculations          |

**Recommendations:**
- For large documents, test with small page range first
- Use simpler watermark images (smaller file size)
- Lower opacity = faster processing
- Batch process overnight for very large files

## Migration from V1

V2 is **100% backward compatible** with V1:

```bash
# V1 command
papyrus_rpt_page_extractor.exe input.rpt all output.txt output.pdf

# V2 command (same behavior)
papyrus_rpt_page_extractor_v2.exe input.rpt all output.txt output.pdf

# V2 with watermark (new feature)
papyrus_rpt_page_extractor_v2.exe input.rpt all output.txt output.pdf --WatermarkImage logo.png
```

You can safely replace V1 with V2 in all existing scripts and batch files.

## Best Practices

### For Confidential Documents
```bash
--WatermarkImage watermarks\confidential_red.png
--WatermarkPosition Center
--WatermarkRotation -45
--WatermarkOpacity 25
--WatermarkScale 1.5
```

### For Draft Documents
```bash
--WatermarkImage watermarks\draft.png
--WatermarkPosition TopCenter
--WatermarkOpacity 40
--WatermarkScale 1.0
```

### For Logo Branding
```bash
--WatermarkImage company_logo.png
--WatermarkPosition TopRight
--WatermarkOpacity 60
--WatermarkScale 0.5
```

### For Subtle Background Pattern
```bash
--WatermarkImage watermarks\pattern_confidential.png
--WatermarkPosition Repeat
--WatermarkOpacity 12
--WatermarkScale 0.4
```

## Support & Documentation

- **Detailed Usage Guide**: See `WATERMARK_USAGE.md`
- **Example Scripts**: See `watermark_examples.bat`
- **Create Watermarks**: Run `create_watermarks.bat`
- **Compilation Help**: Run `compile_v2.bat`

## Exit Codes

| Code | Meaning                    |
|------|----------------------------|
| 0    | Success                    |
| 1    | Invalid arguments          |
| 2    | File not found             |
| 3    | Invalid RPT file           |
| 4    | Read error                 |
| 5    | Write error                |
| 6    | Invalid selection rule     |
| 7    | No pages selected          |
| 8    | Decompression error        |
| 9    | Memory error               |
| 10   | Unknown error              |

## License & Credits

Based on the original Papyrus RPT page extractor with enhanced watermarking capabilities.

**Version:** 2.0
**Date:** 2026-02-09
**Author:** IntelliSTOR Migration Project
