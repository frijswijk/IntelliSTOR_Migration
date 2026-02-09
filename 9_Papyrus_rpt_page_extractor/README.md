# Papyrus RPT Page Extractor

Standalone C++17 CLI tool that extracts pages from Papyrus RPT spool files, producing plain-text and PDF output with optional watermark overlay.

All dependencies (QPDF, libjpeg, OpenSSL, zlib) are statically linked — the resulting executable has **zero external DLL requirements**.

## Usage

```
papyrus_rpt_page_extractor.exe <input_rpt> <selection_rule> <output_txt> <output_pdf> [options]
```

### Required Parameters

| Parameter | Description |
|---|---|
| `input_rpt` | Path to the Papyrus RPT spool file |
| `selection_rule` | Which pages/sections to extract (see below) |
| `output_txt` | Path for the plain-text output file |
| `output_pdf` | Path for the PDF output file |

### Selection Rules

| Format | Description | Example |
|---|---|---|
| `all` | Extract all pages | `all` |
| `pages:<range>` | Extract specific page ranges | `pages:1-5` |
| `pages:<range>,<range>` | Multiple page ranges | `pages:1-5,10-20` |
| `sections:<id>` | Extract a single section | `sections:14259` |
| `sections:<id>,<id>` | Multiple sections | `sections:14259,14260,14261` |
| `<id>,<id>` | Shorthand for sections | `14259,14260` |
| *(empty string)* | Same as `all` | `""` |

### Watermark Options

All watermark options are optional. If `--WatermarkImage` is not provided, no watermark is applied.

| Option | Description | Default |
|---|---|---|
| `--WatermarkImage <path>` | Path to watermark image (PNG, JPG, BMP, GIF) | *(none)* |
| `--WatermarkPosition <pos>` | Placement on the page (see positions below) | `Center` |
| `--WatermarkRotation <deg>` | Rotation angle in degrees (-180 to 180) | `0` |
| `--WatermarkOpacity <pct>` | Opacity percentage (0 = invisible, 100 = fully opaque) | `30` |
| `--WatermarkScale <factor>` | Scale factor (0.5 = half size, 2.0 = double size) | `1.0` |

### Watermark Positions

```
TopLeft        TopCenter        TopRight
MiddleLeft     Center           MiddleRight
BottomLeft     BottomCenter     BottomRight
```

Additionally:
- `Repeat` — single centered watermark repeated on every page
- `Tiling` — grid pattern filling the entire page with evenly spaced watermark copies

## Examples

**Extract all pages (no watermark):**
```
papyrus_rpt_page_extractor.exe "F:\RPT\260271Q7.RPT" all "F:\RPT\output.TXT" "F:\RPT\output.PDF"
```

**Extract pages 1-5 with empty selection rule (equivalent to `all`):**
```
papyrus_rpt_page_extractor.exe "F:\RPT\260271Q7.RPT" "" "F:\RPT\output.TXT" "F:\RPT\output.PDF"
```

**Extract specific sections:**
```
papyrus_rpt_page_extractor.exe "F:\RPT\260271Q7.RPT" "sections:14259,14260" "F:\RPT\output.TXT" "F:\RPT\output.PDF"
```

**With centered watermark at default settings:**
```
papyrus_rpt_page_extractor.exe "F:\RPT\260271Q7.RPT" all "F:\RPT\output.TXT" "F:\RPT\output.PDF" --WatermarkImage "F:\RPT\confidential.png"
```

**With custom watermark (bottom-right, 50% opacity, half-size):**
```
papyrus_rpt_page_extractor.exe "F:\RPT\260271Q7.RPT" all "F:\RPT\output.TXT" "F:\RPT\output.PDF" --WatermarkImage "F:\RPT\logo.png" --WatermarkPosition BottomRight --WatermarkOpacity 50 --WatermarkScale 0.5
```

**With rotated watermark across entire page:**
```
papyrus_rpt_page_extractor.exe "F:\RPT\260271Q7.RPT" all "F:\RPT\output.TXT" "F:\RPT\output.PDF" --WatermarkImage "F:\RPT\draft.png" --WatermarkPosition Repeat --WatermarkRotation -45 --WatermarkOpacity 20
```

## Exit Codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Invalid arguments |
| 2 | File not found |
| 3 | Invalid RPT file |
| 4 | Read error |
| 5 | Write error |
| 6 | Invalid selection rule |
| 7 | No pages selected |

## Building from Source

### Prerequisites

- MinGW-w64 (WinLibs ucrt build, GCC 15+)
- QPDF 12.x development files (headers + static library)
- libjpeg-turbo static library (MSYS2 package)
- OpenSSL static library (MSYS2 package)

### Compile

Run `compile.bat` from the project directory. The paths for MinGW and QPDF are configured at the top of the script.

```
compile.bat
```

This produces a single fully-static executable with no external DLL dependencies.

## PDF Document Properties

Output PDFs are automatically stamped with:
- **Application (Creator):** Papyrus Content Governance
- **PDF Producer:** ISIS Papyrus

## Parallel Execution

The executable is fully safe for parallel invocation. Each call runs as an independent OS process with its own memory — no shared state, no locks, no serialization. Multiple threads from a calling application can launch instances simultaneously, as long as each call writes to a different output file path.

## Source Files

| File | Description |
|---|---|
| `papyrus_rpt_page_extractor.cpp` | Main source — RPT parsing, page extraction, PDF generation, watermark overlay |
| `watermark_lean.h` | Pure C++ watermark PDF generator (uses stb_image) |
| `compat_shims.c` | Symbol compatibility bridge for MSYS2-built libs on WinLibs MinGW |
| `compile.bat` | Build script with all compiler/linker flags |
| `stb_image.h` | Image loading (bundled, header-only) |
| `stb_image_resize2.h` | Image resizing (bundled, header-only) |
| `stb_image_write.h` | Image writing (bundled, header-only) |
