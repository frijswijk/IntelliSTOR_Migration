# Report & IRPT Viewer — IntelliSTOR Report Visualization Suite

A suite of modern, standalone HTML viewers for legacy mainframe/AS/400 spool files and IntelliSTOR `.RPT` binary report files — with advanced search, section navigation, embedded PDF/AFP extraction, watermarking, and professional PDF export.

## Overview

This folder contains two viewers that share a common codebase:

| Viewer | File | Size | Purpose |
|--------|------|------|---------|
| **Report Viewer** | `report-viewer.html` | ~190 KB | Text spool files (`.TXT`) |
| **IRPT Viewer** | `IRPT_Viewer.html` | ~2.9 MB | IntelliSTOR `.RPT` binary files **+** text files |
| **IRPT Viewer (Airgap)** | `IRPT-Viewer-Airgap.html` | ~3.7 MB | Fully offline version of IRPT Viewer |

> **Tip**: The IRPT Viewer is a superset — it handles both `.RPT` and `.TXT` files. Use it as your single viewer if you work with IntelliSTOR reports.

---

## Key Features at a Glance

### Shared Features (both viewers)

✅ **Universal Format Support**
- AS/400 spool files (80, 132, 198, 255 column widths)
- Mainframe reports with ASA carriage control
- Form feed (`\f`) based pagination
- Auto-detection of file format and width

✅ **Professional Display**
- Zebra striping with customizable colors
- Column ruler showing character positions
- Optional line numbers (on by default)
- Light, dark, and high-contrast themes
- Zoom: 50% to 300%

✅ **Search & Navigation**
- Full-text search with highlighting
- Case-sensitive search toggle
- Page range definitions for selective viewing and export
- Jump to page number

✅ **Export & Watermarking**
- PDF export with all visual features preserved
- Watermarking with 9-point positioning, rotation, opacity, and scale
- Page detection: Dynamic, Fixed 66, or Fixed 88 lines

✅ **User Experience**
- Single standalone HTML file — no installation
- Drag & drop file loading
- Comprehensive keyboard shortcuts
- Settings persistence via localStorage

### IRPT Viewer Only

✅ **IntelliSTOR RPT Binary Format**
- Full RPTFILEHDR, SECTIONHDR, PAGETBLHDR parsing
- zlib-compressed page decompression (on-demand / lazy)
- Automatic report width detection from content

✅ **Section Navigation**
- Section table modal with jump-to-section buttons
- Human-readable section names (142,744 entries from lookup table)
- Section-based page filtering and PDF export

✅ **Embedded Binary Object Extraction (PDF/AFP)**
- Detects BPAGETBLHDR entries for embedded binary documents
- Decompresses and assembles binary PDF or AFP files client-side
- Open PDF in new browser tab or download to disk
- Object Header metadata display (filename, creator, timestamps)
- Toolbar button `📎 PDF` / `📎 AFP` appears when binary content is detected

✅ **Airgap Version**
- All three CDN libraries (pako, jsPDF, html2canvas) embedded inline
- Works completely offline — send as a single email attachment
- Identical feature set to the standard version

---

## Quick Start

### Report Viewer (text files)

1. Open `report-viewer.html` in your browser
2. Click **📁 Open File** or drag & drop a `.TXT` spool file
3. Browse, search, and export

### IRPT Viewer (RPT + text files)

1. Open `IRPT_Viewer.html` (or `IRPT-Viewer-Airgap.html` for offline use)
2. Click **📁 Open File** or drag & drop an `.RPT` or `.TXT` file
3. For RPT files:
   - Sections appear automatically — click **📊 Sections** to navigate
   - If the file contains an embedded PDF/AFP, the **📎 PDF** button appears in the toolbar
   - Press **B** to open the binary document, **Shift+B** to download it

---

## Display Options

| Feature | Control | Default | Purpose |
|---------|---------|---------|---------|
| **Zebra Stripes** | Toggle / `Ctrl+Z` | OFF | Alternating row colors for readability |
| **Column Ruler** | Toggle | ON | Character position markers (every 10 columns) |
| **Line Numbers** | Toggle `#` button | ON | Original file line numbers |
| **Theme** | Dropdown | Dark | Dark / Light / High Contrast |
| **Zoom** | Dropdown / `Ctrl++/-` | 100% | 50%–300% |
| **Report Width** | Dropdown | Auto | 80 / 132 / 198 / 255 columns |
| **Page Mode** | Dropdown | Dynamic | Dynamic / Fixed 66 / Fixed 88 |
| **Column Highlight** | `|` button | ON | Red column indicator on hover |

### Enhanced Ruler & Column Features

- **Column Highlighting**: Toggle the `|` button — a red translucent column follows your mouse
- **Real-Time Position**: Top-right shows `Ln X Col Y` as you hover
- **File Type Badge**: **RPT**, **CH** (Channel/ASA), or **FF** (Form Feed) next to filename
- **Zoom-Aware Alignment**: Ruler, line numbers, and content stay aligned at all zoom levels

---

## Search

1. Press `Ctrl+F` or click the search box
2. Type your search term and press **Enter**
3. Use `F3` / `Shift+F3` to navigate results
4. Toggle **Aa** for case-sensitive matching
5. Results count displayed next to the search box

---

## Page Ranges

Define named sections of your report for selective viewing or export:

1. Click **📑 Ranges** button
2. Click **+ Add Range** — enter name, start page, page count
3. Check **"Show Ranges Only"** to filter the display
4. Export PDF with only selected ranges

**Visual Indicator**: Ranges button turns red with green dot (●) when a filter is active.

---

## Section Navigation (IRPT Viewer — RPT files)

### The Sections Panel

Click **📊 Sections** (or the badge showing section count) to open the Section Table:

| Column | Description |
|--------|-------------|
| **#** | Section index (1-based) |
| **Section Name** | Human-readable name from lookup table |
| **Section ID** | Numeric section identifier |
| **Branch** | Branch ID |
| **Start** | First page of the section |
| **Pages** | Number of pages |
| **Action** | **[Go]** button to jump to the section |

### How Section Names Work

RPT files contain only numeric `SECTION_ID` values. The viewer includes an embedded lookup table (142,744 entries) that maps `{speciesId},{sectionId}` to human-readable names.

```
Header speciesId: 1346, Section sectionId: 14259
Lookup key: "1346,14259" → "UBF NY"
Display: "UBF NY (14259)"
```

### Section Filtering

When you click **[Go]** on a section:
- Only that section's pages are displayed
- Navigation and page numbers are section-relative
- PDF export includes only that section

Click a different section to switch, or reload the file to clear the filter.

---

## Embedded Binary Objects — PDF/AFP (IRPT Viewer)

Some RPT files contain embedded binary documents (PDF or AFP) alongside text pages. The IRPT Viewer detects, extracts, and displays these automatically.

### How It Works

1. **Detection**: On file load, the viewer reads the Table Directory and checks for BPAGETBLHDR entries (binary page table)
2. **Decompression**: Binary object chunks are decompressed using pako (zlib)
3. **Assembly**: Chunks are concatenated into a single document
4. **Type Detection**: Magic bytes identify the format — `%PDF` for PDF, `0x5A` for AFP
5. **Object Header**: Text page 1 is parsed for metadata (filename, creator, timestamps)

### Using Binary Objects

| Action | Method |
|--------|--------|
| **Open in new tab** | Click **📎 PDF** button in toolbar, or press **B** |
| **Download** | Press **Shift+B**, or use Download button in Section modal |
| **View metadata** | Open **📊 Sections** modal — binary info panel shows filename, size, creator |

### Binary Info Panel (in Section Modal)

When a binary object is present, the Section modal shows an additional panel:

```
📎 Embedded Binary Document
  Type:     PDF
  Filename: HKCIF001_016_20280309.PDF
  Size:     38,925 bytes
  Creator:  JasperReports Library version 7.0.1
  [Open PDF]  [Download]
```

### Object Header Page

The first text page in binary-containing RPT files is typically a metadata page starting with `"StorQM PLUS Object Header Page:"`. It contains information about the embedded document and is displayed as a regular text page.

---

## Watermarks

Add semi-transparent watermarks (e.g., "CONFIDENTIAL") to your reports:

1. Click **💧 Watermark** or press `Ctrl+W`
2. Upload an image (PNG, JPG, SVG) — auto-scaled to 400px max
3. Select position from 9-point grid
4. Adjust rotation, opacity, and scale
5. Check **"Enable Watermark"** to apply
6. Watermark appears on display and in PDF exports

---

## PDF Export

Export your report (or selected section) with all visual features:

1. Click **📥 Export PDF** or press `Ctrl+E`
2. Wait for processing (progress bar shown)
3. PDF downloads automatically

**Included**: Selected pages, zebra striping (if on), watermark (if on)
**Excluded**: Column ruler, line numbers, search highlights

### Export Performance

| Pages | Expected Time |
|-------|---------------|
| 1–20 | < 10 seconds |
| 20–100 | 30–60 seconds |
| 100–500 | 1–3 minutes |
| 500+ | Export by section |

---

## Keyboard Shortcuts

### Essential

| Shortcut | Action |
|----------|--------|
| `Ctrl+O` | Open file |
| `Ctrl+F` | Focus search |
| `Ctrl+G` | Jump to page |
| `Ctrl+E` | Export PDF |

### Navigation

| Shortcut | Action |
|----------|--------|
| `F3` | Next search result |
| `Shift+F3` | Previous search result |
| `Page Up / Down` | Scroll pages |
| `Home` | Go to top |
| `End` | Go to bottom |

### View Controls

| Shortcut | Action |
|----------|--------|
| `Ctrl++` or `Ctrl+=` | Zoom in |
| `Ctrl+-` | Zoom out |
| `Ctrl+0` | Reset zoom to 100% |
| `Ctrl+Z` | Toggle zebra stripes |
| `Ctrl+W` | Watermark settings |
| `Ctrl+M` or `F11` | Toggle maximize view |
| `Escape` | Close modals |

### Binary Objects (IRPT Viewer)

| Shortcut | Action |
|----------|--------|
| `B` | Open embedded binary document in new tab |
| `Shift+B` | Download binary document |

---

## File Format Support

### Text File Widths

| Width | Description | Use Case |
|-------|-------------|----------|
| **80** | Portrait / Narrow | Simple reports, display sessions |
| **132** | Landscape / Wide | Standard wide reports (most common) |
| **198** | Extra Wide | Financial spreadsheets, detailed reports |
| **255** | Maximum | Custom printer files (DDS limit) |

### Control Characters

**ASA Carriage Control** (detected automatically):
- `'1'` at position 0 = Form feed (new page)
- `'0'` at position 0 = Double space
- `'-'` at position 0 = Single space
- `' '` or `'*'` = Normal line

**Form Feed**: ASCII 12 (`\f`) character for page breaks

### RPT Binary Format

IntelliSTOR RPT files contain:

| Component | Offset | Description |
|-----------|--------|-------------|
| **RPTFILEHDR** | 0x000 | File header — domain ID, species ID, report info |
| **RPTINSTHDR** | 0x0F0 | Instance header — timestamps, metadata |
| **Table Directory** | 0x1D0 | 3 × 16-byte rows: PAGETBLHDR, SECTIONHDR, BPAGETBLHDR |
| **Compressed data** | 0x200+ | zlib-compressed text pages and binary objects (interleaved) |
| **SECTIONHDR** | trailer | Section table — section ID, branch ID, start page, page count |
| **PAGETBLHDR** | trailer | Page table — 24-byte entries: offset, sizes per page |
| **BPAGETBLHDR** | trailer | Binary object table — 16-byte entries (if binary objects exist) |

---

## Technical Specifications

### Requirements

- **Browser**: Chrome 90+, Firefox 88+, Edge 90+, Safari 14+
- **File Size**: Optimized for files up to 10 MB
- **Internet**: Required once for CDN libraries (not needed for Airgap version)
- **Installation**: None — single HTML file

### Architecture

- **Technology**: Pure HTML5, CSS3, JavaScript (ES6+)
- **Processing**: 100% client-side, no server required
- **Storage**: localStorage for user preferences

### Dependencies

| Library | Version | Purpose | In Airgap? |
|---------|---------|---------|------------|
| **pako** | 2.1.0 | zlib decompression for RPT pages | ✅ Embedded |
| **jsPDF** | 2.5.1 | PDF generation for export | ✅ Embedded |
| **html2canvas** | 1.4.1 | Page rendering for PDF export | ✅ Embedded |

### Performance

- **Rendering**: < 1 second for 2,863-line files
- **Search**: < 100ms for 1000+ results
- **Lazy decompression**: Only 3 pages decompressed on load; rest on-demand
- **PDF Export**: ~1–2 minutes for 100+ page files
- **Optimization**: HTML string building (5–10× faster than DOM manipulation)

---

## The Airgap Version

`IRPT-Viewer-Airgap.html` is a fully self-contained, single-file viewer:

- **All libraries inlined** — pako, jsPDF, html2canvas embedded as `<script>` blocks
- **No internet required** — works completely offline
- **Single file to distribute** — send as an email attachment (~3.7 MB)
- **Identical features** — same as IRPT_Viewer.html in every way
- **Section names included** — the 142,744-entry lookup table is embedded

---

## Troubleshooting

### File Won't Load

- Check file extension is `.RPT`, `.TXT`, or `.txt`
- Try drag & drop instead of file picker
- Refresh browser and retry
- For RPT files, verify the file isn't truncated (should be > 1 KB)

### Pages Breaking Wrong

- Try **Fixed 66 Lines** page mode
- If pages are too long, try **Fixed 88 Lines**
- If file has form feeds, use **Dynamic** mode

### Section Names Show as "Section XXXX"

- This means the speciesId,sectionId combination isn't in the lookup table
- Normal for sections not in the exported IntelliSTOR database

### Binary Button Doesn't Appear

- The file may not contain embedded binary objects
- Check with `rpt_page_extractor.py --info <file>` — look for BPAGETBLHDR entry count > 0

### PDF Export Slow

- Normal for 100+ page files (~1–2 minutes)
- Export smaller sections (20–50 pages at a time)
- Disable watermark for faster export

### Text Not Aligned

- Ensure browser zoom is at 100%
- Check the Report Width dropdown matches your file
- Ruler adjusts automatically for line numbers

---

## File Reference

| File | Description |
|------|-------------|
| `report-viewer.html` | Original text-only spool file viewer |
| `IRPT_Viewer.html` | Full-featured viewer (RPT + text + binary objects) |
| `IRPT-Viewer-Airgap.html` | Offline version with all libraries embedded |
| `section_names.json` | Section name lookup data (142,744 entries) |
| `libs/` | Local copies of CDN libraries (used to build Airgap version) |

### Documentation

| File | Description |
|------|-------------|
| `Report_Viewer_README.md` | This document — covers both viewers |
| `IRPT_VIEWER_BINARY_SUPPORT_SPEC.md` | Technical spec for binary PDF/AFP support |
| `USER_GUIDE.md` | End-user manual for the Report Viewer |
| `TECHNICAL_DOCUMENTATION.md` | Developer reference and architecture |

### Related Tools

| Tool | Location | Purpose |
|------|----------|---------|
| `rpt_section_reader.py` | `4_Migration_Instances/` | Extract section info from RPT files |
| `rpt_page_extractor.py` | `4_Migration_Instances/` | Extract and decompress pages (Python) |
| `rpt_page_extractor.js` | `4_Migration_Instances/` | Extract and decompress pages (Node.js) |
| `rpt_page_extractor.cpp` | `4_Migration_Instances/` | Extract and decompress pages (C++) |
| `rpt_file_builder.py` | `8_Create_IRPT_File/` | Create RPT files from text + binary |

---

## Version History

### Version 2.0 (February 2026) — IRPT Viewer

**Binary Object Support**:
- BPAGETBLHDR parsing for embedded PDF/AFP documents
- Client-side decompression and assembly of binary objects
- Open PDF in new browser tab or download to disk
- Object Header metadata extraction and display
- Toolbar button with keyboard shortcuts (B / Shift+B)

**Page Concatenation**:
- `--page-concat` option in all extractor tools (Python, JS, C++)
- Concatenates all text pages into single file with form-feed separators

**RPT File Builder**:
- New tool to create RPT files from text pages and optional binary objects
- Roundtrip-verified: extract → rebuild → re-extract produces identical output

**Airgap Version**:
- Fully self-contained single HTML file (~3.7 MB)
- All CDN libraries embedded inline
- Distributable as email attachment

### Version 1.1 (February 2026) — IRPT Viewer

**RPT Binary Format**:
- Full RPTFILEHDR, SECTIONHDR, PAGETBLHDR parsing
- zlib decompression with pako.js (lazy, on-demand)
- Automatic width detection from content

**Section Features**:
- Section table modal with navigation
- Human-readable section names (142,744 entries)
- Section-based page filtering and PDF export

### Version 1.0 (January 2026) — Report Viewer

**Core Features**:
- Multi-width support (80/132/198/255 columns)
- ASA carriage control and form feed detection
- Zebra striping, column ruler, line numbers
- Light/dark themes, zoom (50–200%)

**Advanced Features**:
- Full-text search with highlighting
- Page ranges with visual indicator
- Watermark with 9-point grid positioning
- PDF export with all visual features
- Comprehensive keyboard shortcuts

---

**Report & IRPT Viewer** — Modern visualization for legacy and IntelliSTOR reports
