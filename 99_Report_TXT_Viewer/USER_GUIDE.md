# Report/Spoolfile Viewer - User Guide

## Version 1.0 | January 2026

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Loading Reports](#loading-reports)
3. [Viewing Features](#viewing-features)
4. [Search & Navigation](#search--navigation)
5. [Page Ranges](#page-ranges)
6. [Watermarks](#watermarks)
7. [PDF Export](#pdf-export)
8. [Keyboard Shortcuts](#keyboard-shortcuts)
9. [Tips & Tricks](#tips--tricks)
10. [Troubleshooting](#troubleshooting)

---

## Getting Started

### What is this tool?

The Report/Spoolfile Viewer is a specialized tool for viewing legacy mainframe and AS/400 spool files. These are text-based reports that were originally designed for wide-carriage printers and can range from 80 to 255 columns wide.

### Requirements

- Modern web browser (Chrome, Firefox, Edge, or Safari)
- No installation needed - just open the HTML file
- No internet connection required (after initial load)

### Opening the Viewer

1. Locate the `report-viewer.html` file
2. Double-click to open in your default browser
3. OR right-click → Open With → Choose your browser

---

## Loading Reports

### Method 1: Click to Upload

1. Click the **"📁 Open File"** button in the top-right
2. Navigate to your report file (`.txt` or `.TXT`)
3. Click **Open**
4. The report loads automatically

### Method 2: Drag & Drop

1. Open the viewer in your browser
2. Drag your `.txt` file from Windows Explorer
3. Drop it anywhere on the viewer window
4. The report loads automatically

### Supported Files

- **AS/400 Spool Files**: 80, 132, 198, or 255 column reports
- **Mainframe Listings**: With ASA carriage control or form feeds
- **Print Files**: Legacy `.txt` format reports

**File Size**: Files up to 10MB load quickly. Larger files may take longer.

---

## Viewing Features

### Zebra Stripes

**Purpose**: Alternating row colors for easier reading

**How to Use**:
1. Toggle the **Zebra** switch ON
2. Rows alternate between two colors
3. Click the color boxes to customize colors
4. Click **Reset** to restore default colors

**Tip**: Zebra stripes are great for wide reports where lines can blur together.

### Column Ruler

**Purpose**: Shows character positions 1-132 (or your report width)

**How to Use**:
1. Ruler appears at the top by default
2. Shows column numbers every 10 positions: `10`, `20`, `30`, etc.
3. Toggle the **Ruler** switch to hide/show
4. Ruler scrolls horizontally with the report

**Reading the Ruler**:
```
         10        20        30        40
.+....|.+....|.+....|.+....|.+....|.+...
```
- `|` = Every 10th column (10, 20, 30...)
- `+` = Every 5th column (5, 15, 25...)
- `.` = Every column

### Line Numbers

**Purpose**: Show original file line numbers on the left

**How to Use**:
1. Toggle the **Line #** switch ON
2. Line numbers appear in a left column
3. Helps reference specific lines in the original file
4. Line numbers are not selectable (for clean copying)

### Light Mode

**Purpose**: White background with black text (like printed paper)

**How to Use**:
1. Toggle the **Light** switch ON
2. Background changes to white
3. Text changes to black
4. Zebra stripes become light gray
5. Great for printing or traditional appearance

**When to Use**:
- Printing the report
- Sharing screenshots
- Preferring light backgrounds
- Matching original printed output

### Report Width

**Purpose**: Auto-detect or manually set report width

**Options**:
- **Auto** (default): Detects the widest line
- **80 Col**: Narrow portrait reports
- **132 Col**: Standard landscape (most common)
- **198 Col**: Extra-wide reports
- **255 Col**: Maximum width

**Auto-Detection**:
The viewer automatically detects your report width and shows it in parentheses: `Auto (132)`

### Page Mode

**Purpose**: How to split the report into pages

**Modes**:

1. **Dynamic** (default)
   - Uses form feed characters in the file
   - Most accurate for spool files
   - Recommended for most reports

2. **Fixed 66 Lines**
   - 11-inch paper at 6 lines per inch
   - Standard greenbar paper
   - Ignores form feeds

3. **Fixed 88 Lines**
   - 11-inch paper at 8 lines per inch
   - Condensed printing
   - Ignores form feeds

**When to Change**:
- Dynamic mode shows wrong page breaks → Try Fixed 66
- Pages too long → Try Fixed 88
- Pages too short → Try Dynamic

### Zoom

**Purpose**: Enlarge or reduce text size

**Controls**:
- **-** button: Zoom out (make smaller)
- **+** button: Zoom in (make larger)
- **Reset** button: Back to 100%
- Current level shown between buttons

**Range**: 50% to 200% in 10% increments

**Keyboard**:
- `Ctrl++` or `Ctrl+=` to zoom in
- `Ctrl+-` to zoom out
- `Ctrl+0` to reset

**Note**: Zoom affects both report and ruler together.

---

## Search & Navigation

### Basic Search

1. Click in the **Search box** (or press `Ctrl+F`)
2. Type your search term
3. Press **Enter** or click **Search**
4. Matches are highlighted in yellow
5. Current match highlighted in red
6. Counter shows: "Match 1 of 15"

### Search Options

**Case Sensitive**:
- Check the box to match exact case
- "ACCOUNT" will not match "account"
- Unchecked: case doesn't matter

### Navigate Results

**Buttons**:
- **◀** Previous result
- **▶** Next result

**Keyboard**:
- `F3`: Next result
- `Shift+F3`: Previous result

**Auto-Scroll**: Jumps to each result automatically

### Clear Search

1. Click **Clear** button
2. OR press `Escape` in search box
3. Highlights disappear
4. Counter clears

---

## Page Ranges

### What are Page Ranges?

Page ranges let you define sections of your report for easy viewing or exporting.

**Example Use Cases**:
- Extract only pages 1-10 (summary section)
- Export pages 50-75 (specific account data)
- View multiple non-contiguous ranges

### Creating Ranges

1. Click **📑 Ranges** button
2. Click **+ Add Range**
3. Enter details:
   - **Section Name**: "Summary", "Details", etc.
   - **Start Page**: First page to include
   - **Page Count**: How many pages
4. Click away from the row to save
5. Repeat to add more ranges

**Example**:
```
Section Name    Start Page    Page Count
Summary         1             5
Details         10            20
Totals          35            3
```

### Using Ranges

1. Define your ranges (see above)
2. Check **"Show Ranges Only"** checkbox
3. **Ranges button turns red** with a green dot ●
4. Only defined pages appear
5. Uncheck to show all pages again

**Visual Indicator**: When ranges are active, the Ranges button has:
- Red background
- Green indicator dot
- Tooltip: "Filter active: N range(s)"

### Deleting Ranges

1. Open Ranges modal
2. Click **Delete** button next to the range
3. Range removed immediately

---

## Watermarks

### What is a Watermark?

A semi-transparent image overlaid on your report pages (e.g., "CONFIDENTIAL", company logo).

### Adding a Watermark

1. Click **💧 Watermark** button
2. Click the upload area (or drag & drop image)
3. Select your image file (PNG, JPG, SVG)
4. Image appears in preview

**Image Size**: Large images auto-scale to 400px max (maintains quality while fitting better)

### Positioning

**9-Point Grid**:
```
Top-Left    Top-Center    Top-Right
Middle-Left   Center      Middle-Right
Bottom-Left Bottom-Center Bottom-Right
```

1. Click the position you want
2. Selected button turns red
3. Watermark moves immediately
4. Preview updates

**Tip**: "Center" positions the watermark in the middle of your report text, not the entire page.

### Adjusting Appearance

**Rotation**:
- Drag slider: -180° to +180°
- Typical use: 45° diagonal "CONFIDENTIAL"

**Opacity**:
- Drag slider: 0% (invisible) to 100% (solid)
- Recommended: 20-40% for subtle effect

**Scale**:
- Drag slider: 0.5x (half size) to 2.0x (double size)
- Default: 1.0x (actual size)

### Enabling Watermark

1. Configure your watermark (see above)
2. Check **"Enable Watermark"** checkbox
3. Watermark appears on all pages
4. Included in display and PDF export

### Preview

The preview pane shows:
- How your watermark looks
- Sample report text underneath
- Live updates as you adjust settings

---

## PDF Export

### Basic Export

1. Click **📥 Export PDF** button
2. Progress bar appears
3. PDF generates (may take 30s for large reports)
4. File downloads automatically

**Filename**: `YourReport_export_1643723456789.pdf`

### What's Included

Your PDF includes:
- ✅ All pages (or filtered by ranges)
- ✅ Zebra striping (if enabled)
- ✅ Watermark (if enabled)
- ✅ Proper page breaks

**Not included**:
- ❌ Ruler
- ❌ Line numbers
- ❌ Search highlights

### Exporting Page Ranges

1. Define page ranges (see [Page Ranges](#page-ranges))
2. Check **"Show Ranges Only"**
3. Click **Export PDF**
4. Only selected pages exported

**Example**: Define pages 1-5, export → PDF contains only those 5 pages

### Large Files

For reports with 100+ pages:
- Export may take 1-2 minutes
- Progress bar shows percentage
- Don't close the browser while exporting
- Wait for "PDF exported successfully!" message

---

## Keyboard Shortcuts

### File Operations
| Shortcut | Action |
|----------|--------|
| `Ctrl+O` | Open file dialog |
| `Ctrl+E` | Export to PDF |

### Navigation
| Shortcut | Action |
|----------|--------|
| `Ctrl+G` | Jump to page (focus page input) |
| `Page Up` | Scroll up |
| `Page Down` | Scroll down |
| `Home` | Go to top |
| `End` | Go to bottom |

### Search
| Shortcut | Action |
|----------|--------|
| `Ctrl+F` | Focus search box |
| `F3` | Next search result |
| `Shift+F3` | Previous search result |
| `Escape` | Clear search |

### View
| Shortcut | Action |
|----------|--------|
| `Ctrl++` or `Ctrl+=` | Zoom in |
| `Ctrl+-` | Zoom out |
| `Ctrl+0` | Reset zoom to 100% |
| `Ctrl+Z` | Toggle zebra stripes |
| `Ctrl+W` | Open watermark settings |

### Modals
| Shortcut | Action |
|----------|--------|
| `Escape` | Close any open modal |

---

## Tips & Tricks

### Best Practices

1. **Start with Auto Width**: Let the viewer detect your report width first
2. **Use Zebra Stripes**: Essential for wide reports (132+ columns)
3. **Search Before Scrolling**: Faster than manually looking
4. **Define Ranges for Large Reports**: Makes navigation easier
5. **Test Watermark in Light Mode**: See how it looks on white background

### Common Workflows

**Quick View**:
```
1. Open file (Ctrl+O or drag-drop)
2. Enable zebra stripes
3. Search for what you need (Ctrl+F)
4. Done!
```

**Professional Export**:
```
1. Open file
2. Enable zebra stripes + customize colors
3. Upload watermark (e.g., "CONFIDENTIAL")
4. Position watermark (center, 45° rotation, 30% opacity)
5. Enable watermark
6. Switch to light mode
7. Export PDF (Ctrl+E)
```

**Section Analysis**:
```
1. Open file
2. Define page ranges for each section
3. Toggle "Show Ranges Only"
4. Review each section
5. Export individual sections to PDF
```

### Performance Tips

**For Large Files** (>5,000 lines):
- Disable zebra stripes during initial load
- Use search to jump to sections
- Export in smaller page ranges
- Close other browser tabs

**For Slow Computers**:
- Set zoom to 80-90% (faster rendering)
- Disable watermark during viewing (enable for export only)
- Use fixed page mode instead of dynamic

---

## Troubleshooting

### File Won't Load

**Problem**: Nothing happens after selecting file

**Solutions**:
1. Check file is `.txt` or `.TXT`
2. Try drag & drop instead
3. Check file size (>10MB may be slow)
4. Refresh browser and try again
5. Try a different browser

### Page Breaks Wrong

**Problem**: Pages split in wrong places

**Solutions**:
1. Try **Fixed 66 Lines** page mode
2. If pages too long, try **Fixed 88 Lines**
3. If file has form feeds, use **Dynamic** mode
4. Check original file has proper page breaks

### Text Not Monospaced

**Problem**: Columns don't align

**Solutions**:
1. Ensure browser has Courier New font
2. Try different zoom level
3. Check if file actually uses spaces (not tabs)
4. This is a display issue only - PDF export will align

### Search Not Finding

**Problem**: Search says "No matches" but text is visible

**Solutions**:
1. Check **Case Sensitive** is unchecked
2. Check spelling of search term
3. Try shorter search term
4. Check if text is in control characters (first column)

### Watermark Too Large

**Problem**: Watermark covers entire page

**Solutions**:
1. Reduce **Scale** slider (try 0.5x)
2. Use smaller source image
3. Re-upload image (auto-scales to 400px max)
4. Adjust position to corner instead of center

### Watermark Off-Center

**Problem**: Watermark not where expected

**Solutions**:
1. Ensure correct report width selected
2. Try different position from grid
3. Refresh page and re-apply
4. This was fixed in v1.0 - update if using older version

### PDF Export Fails

**Problem**: "Error exporting PDF" message

**Solutions**:
1. Check internet connection (libraries load from CDN)
2. Try smaller page range first
3. Disable watermark and try again
4. Try different browser
5. Refresh page and retry

### PDF Export Slow

**Problem**: Export takes forever

**Solutions**:
1. Export in smaller page ranges (20-30 pages at a time)
2. Disable watermark for faster export
3. Close other applications
4. Wait patiently - 100 pages = ~1 minute

### Zebra Colors Not Saving

**Problem**: Colors reset after reload

**Solutions**:
1. Check browser allows localStorage
2. Don't use Private/Incognito mode
3. Click away from color picker after selecting
4. Try different browser

### Ruler Numbers Wrong

**Problem**: Ruler shows "0" instead of "10", "20", etc.

**Solutions**:
1. This was a bug fixed in v1.0
2. Refresh browser (hard refresh: Ctrl+F5)
3. Re-download latest version

---

## Frequently Asked Questions

**Q: Do I need internet to use this?**
A: Only for the first load (to download jsPDF and html2canvas libraries). After that, it works offline.

**Q: Can I print directly?**
A: Yes, use your browser's print function (Ctrl+P). However, PDF export gives better quality and includes watermarks.

**Q: Does it modify my original file?**
A: No. All processing is in memory. Your original file is never changed.

**Q: Can I use this for non-mainframe reports?**
A: Yes! Any monospaced text file works. It's optimized for 80-255 column reports.

**Q: Where are my settings saved?**
A: In your browser's localStorage. Settings persist per browser.

**Q: Can multiple people use the same HTML file?**
A: Yes, share the file freely. Each person's settings are saved locally.

**Q: What if my report is wider than 255 columns?**
A: The viewer supports up to 255 columns (AS/400 DDS limit). Wider reports will scroll horizontally.

**Q: Can I have different watermarks per section?**
A: Not currently. The same watermark applies to all pages. This is a future enhancement.

**Q: How do I update to a newer version?**
A: Replace the old `report-viewer.html` with the new one. Settings carry over (stored in browser).

---

## Support & Feedback

**Questions?** Check the [Technical Documentation](TECHNICAL_DOCUMENTATION.md) for developers.

**Found a bug?** Report issues with:
1. Browser name and version
2. Steps to reproduce
3. Sample file (if possible)
4. Screenshot of error

**Feature requests?** Describe:
1. What you want to do
2. Current workaround (if any)
3. Why it would help

---

## Version History

### Version 1.0 (January 2026)
- ✅ Initial release
- ✅ 80/132/198/255 column support
- ✅ ASA carriage control and form feed support
- ✅ Zebra striping with custom colors
- ✅ Column ruler
- ✅ Line numbers
- ✅ Light/dark mode
- ✅ Search with highlighting
- ✅ Page ranges with filtering
- ✅ Watermark with 9-point positioning
- ✅ PDF export with all features
- ✅ Zoom (50-200%)
- ✅ Auto width detection
- ✅ Keyboard shortcuts
- ✅ localStorage persistence

---

**Thank you for using the Report/Spoolfile Viewer!**

*This tool was designed to make viewing legacy reports easier and more powerful than ever before.*
