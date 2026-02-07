# IRPT Viewer — IntelliSTOR Report File Viewer

A specialized viewer for IntelliSTOR `.RPT` binary report files with full section navigation, human-readable section names, and all the features of the standard Report/Spoolfile Viewer.

## Overview

The IRPT Viewer extends the Report/Spoolfile Viewer to support IntelliSTOR's proprietary `.RPT` binary format. It can read compressed report files exported from IntelliSTOR, decompress pages on-demand, and provides section-based navigation with human-readable section names from an embedded lookup table.

### Key Capabilities

✅ **IntelliSTOR RPT Support**
- Binary RPT file format parsing
- zlib-compressed page decompression (on-demand)
- Section table extraction and navigation
- Human-readable section names (142,744 entries)
- Automatic file type detection (RPT vs TXT)

✅ **All Standard Features**
- Multi-width support (80/132/198/255 columns)
- ASA carriage control and form feed detection
- Zebra striping, column ruler, line numbers
- Full-text search with highlighting
- Watermarking and PDF export
- Light/dark themes, zoom controls

## File Versions

| File | Size | Use Case |
|------|------|----------|
| **IRPT_Viewer.html** | ~2.9 MB | Standard version (requires internet for CDN libraries) |
| **IRPT-Viewer-Airgap.html** | ~3.5 MB | Offline/airgap version (all libraries embedded) |

Both versions include the embedded section name lookup table (~2.7 MB of data).

## Quick Start

### Opening an RPT File

1. **Open the viewer**: Double-click `IRPT_Viewer.html` (or `IRPT-Viewer-Airgap.html` for offline use)

2. **Load an RPT file**:
   - Click **📁 Open File** and select your `.RPT` file, OR
   - Drag and drop the file onto the viewer

3. **Automatic detection**: The viewer automatically detects:
   - File type (RPT binary vs text spool file)
   - Report width from actual content
   - Sections and their page ranges

4. **View sections**: Click the **📊 Sections** button to see:
   - All sections in the report
   - Human-readable section names
   - Branch IDs and page counts
   - Jump buttons for each section

### The RPT File Format

IntelliSTOR RPT files are binary files containing:

| Component | Description |
|-----------|-------------|
| **RPTFILEHDR** | File header with domain ID, species ID, report info |
| **SECTIONHDR** | Section table with section IDs, branch IDs, page counts |
| **PAGETBLHDR** | Page table with offsets and compressed sizes |
| **Compressed Pages** | zlib-compressed page content |

The viewer parses all headers and decompresses pages on-demand for efficient memory usage.

## Section Navigation

### The Sections Panel

Click **📊 Sections** (or **📊 (N)** where N = section count) to open the Section Table modal:

| Column | Description |
|--------|-------------|
| **#** | Section index (1-based) |
| **Section Name** | Human-readable name from lookup table |
| **Section ID** | Numeric section identifier |
| **Branch** | Branch ID for this section |
| **Start** | First page number of the section |
| **Pages** | Total pages in this section |
| **Action** | [Go] button to jump to section |

### Jumping to a Section

1. Click **📊 Sections** button
2. Find your section in the table (use browser's Ctrl+F to search)
3. Click **[Go]** to jump to that section

When you click [Go]:
- The viewer shows **only** that section's pages
- Navigation is restricted to the section
- The footer shows section-specific page numbers
- PDF export includes only that section's pages

### Clearing Section Filter

To view all pages again:
- Click a different section, or
- Reload the file

## Section Name Lookup

### How It Works

RPT files contain only numeric `SECTION_ID` values. The viewer includes an embedded lookup table that maps these IDs to human-readable names.

**Lookup Key**: `{speciesId},{sectionId}` → `"Section Name"`

The `speciesId` comes from the RPT file header, and `sectionId` from each section entry.

### Example

```
RPT Header: speciesId = 1346
Section Entry: sectionId = 14259

Lookup key: "1346,14259"
Result: "UBF NY"

Display: "UBF NY (14259)"
```

### Lookup Table Statistics

- **Total entries**: 142,744 section names
- **Data size**: ~2.7 MB (embedded JSON)
- **Source**: Exported from IntelliSTOR SECTION database table

## PDF Export

### Exporting a Section

1. Click **📊 Sections** and select a section with **[Go]**
2. (Optional) Enable zebra stripes, add watermark
3. Click **📥 Export PDF**
4. Only the selected section's pages are exported

### Export Options

| Feature | Included in PDF |
|---------|-----------------|
| ✅ Selected section pages | Yes |
| ✅ Zebra striping | Yes (if enabled) |
| ✅ Watermark | Yes (if enabled) |
| ❌ Column ruler | No |
| ❌ Line numbers | No |
| ❌ Search highlights | No |

### Export Performance

| File Size | Pages | Expected Time |
|-----------|-------|---------------|
| Small | 1-20 | < 10 seconds |
| Medium | 20-100 | 30-60 seconds |
| Large | 100-500 | 1-3 minutes |
| Very Large | 500+ | Export in sections |

**Tip**: For large reports, export individual sections rather than the entire file.

## Lazy Page Decompression

### How It Works

RPT files can contain thousands of compressed pages. The IRPT Viewer uses **lazy decompression** for efficiency:

1. **On file load**: Only first 3 pages are decompressed
2. **On scroll**: Pages are decompressed as they come into view
3. **On section select**: Section pages are decompressed on-demand
4. **On export**: Required pages are decompressed before PDF generation

This approach allows viewing multi-thousand page reports without memory issues.

### Memory Optimization

```
File: 251110OD.RPT
Total pages: 3,297
Compressed size: 2.1 MB
Initial memory: ~500 KB (3 pages)
Full decompression: ~50 MB (if all pages viewed)
```

## Keyboard Shortcuts

All shortcuts from the standard Report Viewer work in IRPT Viewer:

| Shortcut | Action |
|----------|--------|
| `Ctrl+O` | Open file |
| `Ctrl+F` | Search |
| `Ctrl+G` | Go to page |
| `Ctrl+E` | Export PDF |
| `Ctrl+Z` | Toggle zebra stripes |
| `Ctrl+W` | Watermark settings |
| `F3` / `Shift+F3` | Next/prev search result |
| `Ctrl++` / `Ctrl+-` | Zoom in/out |
| `Escape` | Close modals |

## File Type Detection

The viewer automatically detects file types:

| Badge | Format | Detection |
|-------|--------|-----------|
| **RPT** | IntelliSTOR binary | Magic bytes + header structure |
| **CH** | Channel Code (ASA) | Control characters at position 0 |
| **FF** | Form Feed | ASCII 12 (`\f`) characters |
| (none) | Plain text | Default fallback |

## Technical Specifications

### RPT Binary Format

```
Offset 0x00: RPTFILEHDR (variable length)
  - domainId (4 bytes)
  - speciesId (4 bytes)
  - reportId (4 bytes)
  - pageCount (4 bytes)
  - sectionCount (4 bytes)
  - ... additional fields

After RPTFILEHDR: SECTIONHDR entries
  - sectionId (4 bytes)
  - branchId (4 bytes)
  - startPage (4 bytes)
  - pageCount (4 bytes)

After SECTIONHDR: PAGETBLHDR entries
  - offset (4 bytes)
  - compressedSize (4 bytes)
  - ... per page

After PAGETBLHDR: Compressed page data (zlib)
```

### Width Detection

The viewer detects report width from actual content:

1. Decompress first 3 pages
2. Find maximum line length
3. Round to standard width (80/132/198/255)
4. Apply to ruler and display

This is more reliable than the `lineWidth` field in PAGETBLHDR.

### Dependencies

| Library | Version | Purpose |
|---------|---------|---------|
| **pako** | 2.1.0 | zlib decompression for page content |
| **jsPDF** | 2.5.1 | PDF generation |
| **html2canvas** | 1.4.1 | Page rendering for PDF |

The airgap version has all libraries embedded inline.

## Troubleshooting

### File Won't Load

**Symptoms**: Error message or blank display after selecting RPT file

**Solutions**:
- Verify file has `.RPT` extension
- Check file isn't corrupted (should be > 1 KB)
- Try drag & drop instead of file picker
- Use Chrome or Firefox (best compatibility)

### Section Names Show as "Section XXXX"

**Symptoms**: Numeric IDs instead of names

**Cause**: Section not in lookup table (speciesId,sectionId combination not found)

**Note**: This is normal for sections not in the exported database table

### Pages Not Displaying

**Symptoms**: Blank pages or decompression errors

**Solutions**:
- Check browser console for errors
- Verify RPT file isn't truncated
- Try a different RPT file to isolate the issue

### PDF Export Fails

**Symptoms**: Error during export or incomplete PDF

**Solutions**:
- Export smaller sections (20-50 pages)
- Disable watermark for faster export
- Use Chrome (best PDF generation support)
- Check available memory

### Slow Performance

**Symptoms**: Laggy scrolling or long load times

**Solutions**:
- Large files (1000+ pages) may take longer
- Pages are decompressed on-demand, some delay is normal
- Close other browser tabs to free memory
- Use section navigation to focus on specific pages

## Version History

### Version 1.0 (February 2026)

**RPT Binary Support**:
- Full RPTFILEHDR, SECTIONHDR, PAGETBLHDR parsing
- zlib decompression with pako.js
- Lazy page decompression for memory efficiency
- Automatic width detection from content

**Section Features**:
- Section table modal with navigation
- Human-readable section names (142,744 entries)
- Section-based page filtering
- PDF export respects section selection

**UI Enhancements**:
- Dedicated Sections button in toolbar
- RPT file type badge
- Section name display in page indicator
- Active section filtering for rendering

**Airgap Version**:
- All dependencies embedded inline
- Works completely offline
- Larger file size (~3.5 MB)

## Files Reference

| File | Description |
|------|-------------|
| `IRPT_Viewer.html` | Main viewer (CDN dependencies) |
| `IRPT-Viewer-Airgap.html` | Offline version (embedded dependencies) |
| `section_names.json` | Section lookup data (142,744 entries) |
| `report-viewer.html` | Original text-only viewer |
| `README.md` | Documentation for report-viewer.html |
| `IRPT_VIEWER_README.md` | This documentation |

## Related Tools

### Python Scripts

| Script | Purpose |
|--------|---------|
| `rpt_section_reader.py` | Extract section info from RPT files |
| `rpt_page_extractor.py` | Extract and decompress individual pages |

### Export Files

| File | Description |
|------|-------------|
| `section_lookup.csv` | Source data for section names |
| `section_names.json` | Compiled lookup table |

---

**IRPT Viewer** — Modern visualization for IntelliSTOR legacy reports
