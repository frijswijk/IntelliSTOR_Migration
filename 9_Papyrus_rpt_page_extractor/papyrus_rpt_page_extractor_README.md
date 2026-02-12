# Papyrus RPT Page Extractor

Standalone C++17 CLI tool that extracts pages from Papyrus RPT spool files, producing plain-text and PDF/AFP output with optional watermark overlay.

All dependencies (QPDF, libjpeg, OpenSSL, zlib) are statically linked — the resulting executable has **zero external DLL requirements**.

## Usage

### Standard Mode (4 positional args)

```
papyrus_rpt_page_extractor.exe <input_rpt> <selection_rule> <output_txt> <output_binary> [watermark_options]
```

### Flexible Mode (keyword-based outputs)

```
papyrus_rpt_page_extractor.exe <input_rpt> <selection_rule> [OUTPUT_SPECS...] [OUTPUTFOLDER <path>] [watermark_options]
```

### Export Mode

```
papyrus_rpt_page_extractor.exe <input.rpt> Export [OUTPUT_SPECS...] [OUTPUTFOLDER <path>] [watermark_options]
papyrus_rpt_page_extractor.exe <directory>  Export [OUTPUT_SPECS...] [OUTPUTFOLDER <path>] [watermark_options]
```

### Required Parameters (Standard Mode)

| Parameter | Description |
|---|---|
| `input_rpt` | Path to the Papyrus RPT spool file |
| `selection_rule` | Which pages/sections to extract (see below) |
| `output_txt` | Path for the plain-text output file |
| `output_binary` | Path for the binary output file (PDF or AFP) |

### Output Keywords (Flexible Mode)

Instead of specifying fixed output file paths, you can use output keywords to control which outputs are generated. Each keyword is case-insensitive and can optionally be followed by an explicit output path.

| Keyword | Description |
|---|---|
| `TXT` / `TXT "path"` | Write text output |
| `AFP` / `AFP "path"` | Write binary output only if AFP format is detected |
| `PDF` / `PDF "path"` | Write binary output only if PDF format is detected |
| `BIN` / `BIN "path"` | Write binary output regardless of detected format |
| `CSV` / `CSV "path"` | Write section metadata CSV |
| `OUTPUTFOLDER <path>` | Base folder for generic (non-explicit) outputs |

**Path resolution:**
- When a keyword has no explicit path, the output is written to `<OUTPUTFOLDER>\<rpt_basename>.<ext>`
- Default OUTPUTFOLDER: `<rpt_parent_directory>\EXPORT\`
- Output directories are created automatically if they don't exist

**Binary format priority:** Format-specific keywords (`AFP`, `PDF`) take priority over `BIN`. If you specify `AFP PDF` and the RPT contains a PDF, only the PDF output is written. `BIN` acts as a catch-all fallback for any binary format.

### Selection Rules

| Format | Description | Example |
|---|---|---|
| `all` | Extract all pages | `all` |
| `<number>` | Extract a single page | `1` |
| `<range>` | Extract a page range | `1-3` |
| `<n>,<n>` | Multiple individual pages | `1,3` |
| `<n>,<range>` | Mixed pages and ranges | `1,3-5,8` |
| `pages:<spec>` | Explicit page selection | `pages:1,3,6` |
| `sections:<id>` | Extract a single section | `sections:14259` |
| `sections:<id>,<id>` | Multiple sections | `sections:14259,14260` |
| *(empty string)* | Same as `all` | `""` |

Bare numbers are always interpreted as **pages**. Sections require the `sections:` prefix.

**Selection rule examples:**
```
all              # all pages
1                # page 1 only
1-3              # pages 1 through 3
1,3              # pages 1 and 3
1-3,7,10-12      # pages 1-3, 7, and 10-12
pages:1,3,6      # pages 1, 3, and 6 (explicit)
sections:14259   # all pages in section 14259
```

### Watermark Options

All watermark options are optional. If `WatermarkImage` is not provided, no watermark is applied.

The `--` prefix is optional and matching is case-insensitive, so `--WatermarkImage`, `WatermarkImage`, and `watermarkimage` all work.

Watermarks are applied to PDF output only. For AFP output, watermark options are silently ignored.

| Option | Description | Default |
|---|---|---|
| `WatermarkImage <path>` | Path to watermark image (PNG, JPG, BMP, GIF) | *(none)* |
| `WatermarkPosition <pos>` | Placement on the page (see positions below) | `Center` |
| `WatermarkRotation <deg>` | Rotation angle in degrees (-180 to 180) | `0` |
| `WatermarkOpacity <pct>` | Opacity percentage (0 = invisible, 100 = fully opaque) | `30` |
| `WatermarkScale <factor>` | Scale factor (0.5 = half size, 2.0 = double size) | `1.0` |

### Watermark Positions

```
TopLeft        TopCenter        TopRight
MiddleLeft     Center           MiddleRight
BottomLeft     BottomCenter     BottomRight
```

Additionally:
- `Repeat` — single centered watermark repeated on every page
- `Tiling` — grid pattern filling the entire page with evenly spaced watermark copies

## Export Mode

Export mode automatically derives output filenames and creates an `export/` subfolder next to the input.

### Single File Export

```
papyrus_rpt_page_extractor.exe F:\RPT\26027272.RPT Export
```

Extracts all pages and creates:
- `export/<name>.txt` — text content
- `export/<name>.pdf` or `export/<name>.afp` — binary content (extension based on detected format)
- `export/<name>.csv` — section metadata

CSV format:
```
SPECIES_ID,SECTION_ID,START_PAGE,PAGES
20296,0,1,5
```

### Batch Directory Export

```
papyrus_rpt_page_extractor.exe F:\RPT Export
```

When the first argument is a directory:
- Finds all `.RPT` files in that directory
- Processes each one (same as single file Export)
- Tracks progress in `export/export_progress.txt`
- Prints summary at end

### Batch Restart

Running the same batch command again skips already-completed files:

```
papyrus_rpt_page_extractor.exe F:\RPT Export
```
```
BATCH EXPORT: 4 RPT files in F:\RPT
  Resuming: 4 already completed

BATCH EXPORT SUMMARY
  Total:     4 files
  Processed: 0 files
  Skipped:   4 files (already completed)
```

Delete `export/export_progress.txt` to force reprocessing.

## Flexible Mode Examples

**Extract text only (generic path):**
```
papyrus_rpt_page_extractor.exe F:\RPT\260271Q7.RPT all TXT
```
Creates `F:\RPT\EXPORT\260271Q7.txt`

**Extract text and auto-detect binary format:**
```
papyrus_rpt_page_extractor.exe F:\RPT\260271Q7.RPT all TXT AFP PDF
```
Creates `F:\RPT\EXPORT\260271Q7.txt` and either `.afp` or `.pdf` depending on what the RPT contains.

**Explicit output paths:**
```
papyrus_rpt_page_extractor.exe F:\RPT\260271Q7.RPT all TXT "D:\out\report.txt" PDF "D:\out\report.pdf"
```
Creates files at the specified paths.

**Custom output folder:**
```
papyrus_rpt_page_extractor.exe F:\RPT\260271Q7.RPT all TXT CSV OUTPUTFOLDER "D:\output"
```
Creates `D:\output\260271Q7.txt` and `D:\output\260271Q7.csv`

**BIN as format-agnostic fallback:**
```
papyrus_rpt_page_extractor.exe F:\RPT\260271Q7.RPT all BIN
```
Creates `F:\RPT\EXPORT\260271Q7.bin` regardless of whether the binary content is PDF or AFP.

**Page selection with flexible output:**
```
papyrus_rpt_page_extractor.exe F:\RPT\260271Q7.RPT pages:1-3 TXT PDF
```
Extracts only pages 1-3 to `EXPORT\260271Q7.txt` and `EXPORT\260271Q7.pdf`.

**Flexible export mode (single file):**
```
papyrus_rpt_page_extractor.exe F:\RPT\260271Q7.RPT Export TXT AFP PDF
```
Same as flexible mode with `all` selection, but uses the Export keyword.

**Flexible export mode (batch directory):**
```
papyrus_rpt_page_extractor.exe F:\RPT Export TXT AFP PDF
```
Processes all `.RPT` files in the directory, creating TXT + AFP/PDF for each.

**Flexible mode with watermark:**
```
papyrus_rpt_page_extractor.exe F:\RPT\260271Q7.RPT all TXT PDF WatermarkImage logo.png WatermarkOpacity 50
```

## Standard Mode Examples

**Extract all pages from a PDF-based RPT:**
```
papyrus_rpt_page_extractor.exe F:\RPT\260271Q7.RPT all output.txt output.pdf
```
```
SUCCESS: Extracted 2 pages
  TXT:  output.txt
  BIN:  output.pdf (PDF)
```

**Extract all pages from an AFP-based RPT:**
```
papyrus_rpt_page_extractor.exe F:\RPT\26027272.RPT all output.txt output.afp
```
```
SUCCESS: Extracted 5 pages
  TXT:  output.txt
  BIN:  output.afp (AFP)
```

**Extract a single page (bare number):**
```
papyrus_rpt_page_extractor.exe F:\RPT\26027272.RPT 2 output.txt output.afp
```
```
SUCCESS: Extracted 1 pages
  TXT:  output.txt
  BIN:  output.afp (AFP - 1 pages extracted)
```

**Extract a page range from AFP:**
```
papyrus_rpt_page_extractor.exe F:\RPT\26027272.RPT pages:2-3 output.txt output.afp
```
```
SUCCESS: Extracted 2 pages
  TXT:  output.txt
  BIN:  output.afp (AFP - 2 pages extracted)
```

**Text-only RPT (no binary objects):**
```
papyrus_rpt_page_extractor.exe F:\RPT\260271NL.RPT all output.txt output.bin
```
```
NOTE: No binary objects (PDF/AFP) found in RPT file. Only text extracted.
SUCCESS: Extracted 2 pages
  TXT:  output.txt
```

**Extract specific sections:**
```
papyrus_rpt_page_extractor.exe F:\RPT\260271Q7.RPT sections:14259,14260 output.txt output.pdf
```

**Watermark with default settings (centered, 30% opacity):**
```
papyrus_rpt_page_extractor.exe F:\RPT\260271Q7.RPT all output.txt output.pdf WatermarkImage confidential.png
```

**Watermark without `--` prefix, custom opacity (case-insensitive):**
```
papyrus_rpt_page_extractor.exe F:\RPT\260271Q7.RPT all output.txt output.pdf WatermarkImage confidential.png watermarkopacity 50
```

**Watermark with full customization (bottom-right, 50% opacity, half-size):**
```
papyrus_rpt_page_extractor.exe F:\RPT\260271Q7.RPT all output.txt output.pdf WatermarkImage logo.png WatermarkPosition BottomRight WatermarkOpacity 50 WatermarkScale 0.5
```

**Tiling watermark with rotation:**
```
papyrus_rpt_page_extractor.exe F:\RPT\260271Q7.RPT all output.txt output.pdf WatermarkImage draft.png WatermarkPosition Tiling WatermarkRotation -45 WatermarkOpacity 20
```

**AFP with watermark (silently skipped):**
```
papyrus_rpt_page_extractor.exe F:\RPT\26027272.RPT all output.txt output.afp WatermarkImage confidential.png
```
```
SUCCESS: Extracted 5 pages
  TXT:  output.txt
  BIN:  output.afp (AFP)
```

**Export single file:**
```
papyrus_rpt_page_extractor.exe F:\RPT\26027272.RPT Export
```
```
EXPORT: 26027272.RPT
SUCCESS: Extracted 5 pages
  TXT:  F:\RPT\export\26027272.txt
  BIN:  F:\RPT\export\26027272.afp (AFP)
  CSV:  F:\RPT\export\26027272.csv
```

**Export with watermark (applied to PDFs only):**
```
papyrus_rpt_page_extractor.exe F:\RPT\260271Q7.RPT Export WatermarkImage confidential.png WatermarkOpacity 50
```

**Batch export entire directory:**
```
papyrus_rpt_page_extractor.exe F:\RPT Export
```
```
BATCH EXPORT: 4 RPT files in F:\RPT

--- [1/4] EXPORT: 251110OD.RPT
NOTE: No binary objects (PDF/AFP) found in RPT file. Only text extracted.
SUCCESS: Extracted 3297 pages
  TXT:  F:\RPT\export\251110OD.txt
  CSV:  F:\RPT\export\251110OD.csv

--- [2/4] EXPORT: 260271NL.RPT
...

BATCH EXPORT SUMMARY
  Total:     4 files
  Processed: 4 files
  Skipped:   0 files (already completed)
  Output:    F:\RPT\export
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
| 8 | Decompression error |
| 9 | Memory error |
| 10 | Unknown error |

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
| `papyrus_rpt_page_extractor.cpp` | Main source — RPT parsing, page extraction, PDF/AFP generation, watermark overlay |
| `afp_parser.h` / `afp_parser.cpp` | AFP structured field parser and page splitter |
| `watermark_lean.h` | Pure C++ watermark PDF generator (uses stb_image) |
| `compat_shims.c` | Symbol compatibility bridge for MSYS2-built libs on WinLibs MinGW |
| `compile.bat` | Build script with all compiler/linker flags |
| `stb_image.h` | Image loading (bundled, header-only) |
| `stb_image_resize2.h` | Image resizing (bundled, header-only) |
| `stb_image_write.h` | Image writing (bundled, header-only) |
