# Report/Spoolfile Viewer

A modern, feature-rich web application for viewing legacy mainframe and AS/400 spool files with advanced visualization and export capabilities.

## Overview

The Report/Spoolfile Viewer is a standalone HTML application designed to make viewing and analyzing legacy text-based reports easier and more powerful than ever before. It supports reports from 80 to 255 columns wide, with intelligent page detection, search capabilities, watermarking, and professional PDF export.

### Key Features

✅ **Universal Format Support**
- AS/400 spool files (80, 132, 198, 255 column widths)
- Mainframe reports with ASA carriage control
- Form feed (`\f`) based pagination
- Auto-detection of file format and width

✅ **Professional Display**
- Zebra striping with customizable colors
- Column ruler showing character positions
- Optional line numbers (on by default)
- Light and dark themes
- Zoom: 50% to 200%

✅ **Advanced Features**
- Full-text search with highlighting
- Page range definitions for section viewing/export
- Watermarking with 9-point positioning, rotation, opacity, and scale
- PDF export with all visual features preserved
- Page detection: Dynamic, Fixed 66, or Fixed 88 lines

✅ **User Experience**
- Single standalone HTML file - no installation
- Works offline (after initial library load)
- Drag & drop file loading
- Comprehensive keyboard shortcuts
- Settings persistence via localStorage

## Quick Start

### 1. Open the Viewer

Simply double-click `report-viewer.html` or open it in your browser.

### 2. Load a Report

**Option A**: Click **"📁 Open File"** button and select your `.txt` file

**Option B**: Drag and drop your file onto the viewer window

### 3. Start Viewing

The report loads with these defaults:
- ✅ Line numbers ON
- ✅ Column ruler ON
- ✅ Auto-detected width
- ✅ Dynamic page detection
- ⬜ Zebra stripes OFF
- ⬜ Dark theme

## Feature Guide

### Display Options

| Feature | Control | Default | Purpose |
|---------|---------|---------|---------|
| **Zebra Stripes** | Toggle switch | OFF | Alternating row colors for readability |
| **Column Ruler** | Toggle switch | ON | Shows character positions 1-N |
| **Line Numbers** | Toggle switch | ON | Original file line numbers |
| **Light Mode** | Toggle switch | OFF | White background, black text |
| **Zoom** | +/- buttons | 100% | Text size (50-200%) |
| **Report Width** | Dropdown | Auto | Column width (80/132/198/255) |
| **Page Mode** | Dropdown | Dynamic | How to detect pages |
| **Column Highlight** | \| button (ruler bar) | ON | Visual column indicator on hover |

### Enhanced Ruler & Column Features

**Column Highlighting**
- Toggle the **\|** button in the ruler bar to enable/disable column highlighting
- When enabled, a red translucent column appears under your mouse cursor
- Helps align data across rows and identify exact column positions
- Works at all zoom levels (50% - 200%)

**Real-Time Position Tracking**
- Move your mouse over the report to see live position updates
- Top-right indicator shows: `Ln X Col Y`
- Updates as you hover (not just on click)
- Accurate at all zoom levels and report widths

**File Type Detection**
- **CH** badge = Channel Code format (ASA carriage control)
- **FF** badge = Form Feed format (ASCII form feed characters)
- Appears next to filename when file type is detected
- Channel Code files automatically strip control characters for proper column alignment

**Zoom-Aware Alignment**
- Ruler and line numbers scale correctly at all zoom levels
- Position 1 always aligns with first character of text
- No misalignment at 150%, 200%, or Fit Width zoom
- Line numbers stay fully visible (no truncation)

### Search

1. Press `Ctrl+F` or click search box
2. Type your search term
3. Press `Enter`
4. Use `F3` / `Shift+F3` to navigate results
5. Check "Case Sensitive" for exact matching

### Page Ranges

Define sections of your report for easier viewing or selective PDF export:

1. Click **📑 Ranges** button
2. Click **+ Add Range**
3. Enter section name, start page, and page count
4. Check **"Show Ranges Only"** to filter display
5. Export PDF with only selected ranges

**Visual Indicator**: Ranges button turns red with green dot (●) when filter is active.

### Watermarks

Add semi-transparent watermarks (e.g., "CONFIDENTIAL") to your reports:

1. Click **💧 Watermark** button
2. Upload image (PNG, JPG, SVG)
   - Large images auto-scale to 400px max
3. Select position from 9-point grid
4. Adjust rotation, opacity, and scale
5. Check **"Enable Watermark"** to apply
6. Watermark appears on display and in PDF exports

**Preview**: Shows realistic representation of watermark placement.

### PDF Export

Export your report with all visual features:

1. Click **📥 Export PDF** button
2. Wait for processing (shows progress bar)
3. PDF downloads automatically

**What's Included**:
- ✅ Selected pages (or all if no ranges defined)
- ✅ Zebra striping (if enabled)
- ✅ Watermark (if enabled)
- ✅ Proper page breaks

**What's Not Included**:
- ❌ Column ruler
- ❌ Line numbers
- ❌ Search highlights

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
| `Page Up/Down` | Scroll pages |
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
| `Escape` | Close modals |

## File Format Support

### AS/400 Spool File Widths

| Width | Description | Use Case |
|-------|-------------|----------|
| **80** | Portrait/Narrow | Simple reports, display sessions |
| **132** | Landscape/Wide | Standard wide reports (most common) |
| **198** | Extra Wide | Financial spreadsheets, detailed reports |
| **255** | Maximum | Custom printer files (DDS limit) |

### Control Characters

**ASA Carriage Control** (detected automatically):
- `'1'` at position 0 = Form feed (new page)
- `'0'` at position 0 = Skip line (double space)
- `'-'` at position 0 = Single space
- `' '` or `'*'` = Normal line

**Form Feed**:
- ASCII 12 (`\f`) character for page breaks
- Common in modern spool file exports

## Technical Specifications

### Requirements

- **Browser**: Chrome 90+, Firefox 88+, Edge 90+, Safari 14+
- **File Size**: Optimized for files up to 10MB
- **Internet**: Required once to load jsPDF and html2canvas libraries
- **Installation**: None - single HTML file

### Architecture

- **Technology**: Pure HTML5, CSS3, JavaScript (ES6+)
- **Dependencies**: jsPDF 2.5.1, html2canvas 1.4.1 (loaded via CDN)
- **Storage**: localStorage for user preferences
- **Processing**: 100% client-side, no server required

### Performance

- **Rendering**: <1 second for 2,863 line files
- **Search**: <100ms for 1000+ results
- **PDF Export**: ~1-2 minutes for 100+ page files
- **Optimization**: HTML string building (5-10x faster than DOM manipulation)

## Documentation

### For End Users

📖 **[USER_GUIDE.md](USER_GUIDE.md)** - Comprehensive user manual
- Step-by-step tutorials
- Feature explanations
- Troubleshooting guide
- FAQs

### For Developers

🔧 **[TECHNICAL_DOCUMENTATION.md](TECHNICAL_DOCUMENTATION.md)** - Technical reference
- Architecture diagrams
- Algorithm details
- Data structures
- Extension guide
- Performance optimizations

### Change Logs

📝 **Enhancement Documentation**:
- [ENHANCEMENTS_ROUND2.md](ENHANCEMENTS_ROUND2.md) - Ruler, line numbers, width detection
- [FINAL_POLISH.md](FINAL_POLISH.md) - Watermark positioning, light mode
- [FINAL_ADJUSTMENTS.md](FINAL_ADJUSTMENTS.md) - Preview fixes, page separators
- [PAGE_BREAK_FIX.md](PAGE_BREAK_FIX.md) - Form feed and ASA control detection

## Sample Workflow

### Quick View
```
1. Open report-viewer.html
2. Drag & drop your .txt file
3. Scroll and browse
4. Search for specific terms (Ctrl+F)
5. Done!
```

### Professional Export
```
1. Load report
2. Enable zebra stripes
3. Customize colors (optional)
4. Upload watermark image
5. Position watermark (center, 45° rotation, 30% opacity)
6. Enable watermark
7. Toggle light mode (for white background)
8. Export PDF (Ctrl+E)
9. Share professional PDF!
```

### Section Analysis
```
1. Load large report
2. Define page ranges for each section
   - Summary: Pages 1-5
   - Details: Pages 10-50
   - Totals: Pages 51-55
3. Toggle "Show Ranges Only"
4. Review each section individually
5. Export specific sections to separate PDFs
```

## Troubleshooting

### Common Issues

**File won't load**
- Check file extension is `.txt` or `.TXT`
- Try drag & drop instead of file picker
- Refresh browser and retry

**Pages breaking wrong**
- Try **Fixed 66 Lines** page mode
- If pages too long, try **Fixed 88 Lines**
- If file has form feeds, use **Dynamic** mode

**Watermark too large**
- Watermark auto-scales to 400px on upload
- Use **Scale** slider to adjust (0.5x - 2.0x)
- Re-upload image if needed

**Text not aligned**
- Ensure **Line #** toggle matches your preference
- Ruler automatically adjusts for line numbers
- Check browser zoom is 100%

**PDF export slow**
- Normal for 100+ page files (~1-2 minutes)
- Export smaller page ranges (20-30 pages at a time)
- Disable watermark for faster export

## Browser Compatibility

| Browser | Version | Status | Notes |
|---------|---------|--------|-------|
| Chrome | 90+ | ✅ Full | Primary target, best performance |
| Firefox | 88+ | ✅ Full | Fully supported |
| Edge | 90+ | ✅ Full | Chromium-based, excellent support |
| Safari | 14+ | ✅ Good | Minor rendering differences |
| IE 11 | - | ❌ No | Not supported (requires ES6+) |

## Version History

### Version 1.0 (January 2026)

**Core Features**:
- Multi-width support (80/132/198/255 columns)
- ASA carriage control and form feed detection
- Zebra striping with custom colors
- Column ruler with accurate positioning
- Line numbers (on by default)
- Light/dark themes
- Zoom (50-200%)
- Auto width detection

**Advanced Features**:
- Full-text search with highlighting
- Page ranges with visual indicator
- Watermark with 9-point grid positioning
- PDF export with all features
- Comprehensive keyboard shortcuts

**Performance**:
- HTML string building for 5-10x faster rendering
- Optimized for files up to 10,000 lines
- Progressive PDF export with progress tracking

**Documentation**:
- Complete user guide
- Technical documentation
- Multiple changelog files

## License & Credits

**Created**: January 2026
**Author**: Claude Sonnet 4.5 (Anthropic)
**Technology**: HTML5, CSS3, JavaScript (ES6+)
**Libraries**: jsPDF, html2canvas

## Support

For questions, issues, or feature requests, refer to:
- **User Guide**: [USER_GUIDE.md](USER_GUIDE.md)
- **Technical Docs**: [TECHNICAL_DOCUMENTATION.md](TECHNICAL_DOCUMENTATION.md)

---

**Report/Spoolfile Viewer** - Modern visualization for legacy reports
