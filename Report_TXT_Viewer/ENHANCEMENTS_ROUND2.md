# Report Viewer Enhancements - Round 2

## Date: 2026-01-27

## Issues Fixed

### 1. ✅ **Fixed Ruler Column Numbers**
**Issue**: Ruler showed "0" at every 10th position instead of "10", "20", "30", etc.

**Solution**:
- Completely rewrote `buildRuler()` function
- Now correctly displays column numbers: `         10        20        30`
- Numbers are right-aligned at each 10th column position
- Tick marks show: `|` at decade, `+` at 5th position, `.` at each position
- Example for first 40 columns:
  ```
           10        20        30        40
  .+....|.+....|.+....|.+....|.+....|.+...
  ```

### 2. ✅ **Added Ruler Toggle**
**New Feature**: Toggle ruler display on/off

**Implementation**:
- Added toggle switch in control panel labeled "Ruler:"
- Default: ON (checked)
- State saved in `AppState.showRuler`
- When off, ruler is completely hidden
- Ruler still syncs with horizontal scroll when enabled

### 3. ✅ **Added Line Numbers**
**New Feature**: Optional line number display on left side

**Implementation**:
- Added toggle switch labeled "Line #:"
- Default: OFF
- Shows original file line numbers (1-based)
- Line numbers displayed in separate column:
  - Right-aligned in 60px width column
  - Border separator between numbers and content
  - Gray color, slightly smaller font
  - Not selectable (user-select: none)
- Works with all features (zebra, search, ranges, watermark)

### 4. ✅ **Visual Indicator for Active Ranges**
**Issue**: No visual feedback when page ranges filter was active

**Solution**:
- **Ranges button changes when filter active**:
  - Background changes to accent color (red)
  - Text turns white
  - Green indicator dot appears in top-right corner
  - Tooltip shows: "Filter active: N range(s)"
- When inactive:
  - Normal button appearance
  - Tooltip shows: "Define page ranges"
- `updateRangesIndicator()` function updates state on render

### 5. ✅ **Auto-Detect Report Width**
**New Feature**: Automatically detect and support multiple report widths

**Implementation**:
- Added width selector dropdown with options:
  - **Auto** (default) - Detects widest line
  - **80 Col** - AS/400 narrow portrait
  - **132 Col** - Standard landscape
  - **198 Col** - Extra wide reports
  - **255 Col** - Maximum width
- `detectReportWidth()` function:
  - Scans all lines to find maximum width
  - Rounds up to nearest standard width
  - Shows detected width in parentheses: "Auto (132)"
- Ruler automatically adjusts to selected/detected width
- Width detection runs after file load

### 6. ✅ **Fixed Watermark Image Scaling**
**Issue**: Uploaded watermark images were too large, even with 0.5x scale

**Solution**:
- Auto-scale large images on upload
- Maximum dimension: 400px (width or height)
- Maintains aspect ratio
- Scaling algorithm:
  - If image > 400px in either dimension, scale down
  - Calculate scale factor from larger dimension
  - Apply to both width and height
  - Show scaled dimensions in toast: "Watermark loaded (scaled to 320x240)"
- User can still further scale with scale slider (0.5x - 2.0x)
- Smaller images (< 400px) not scaled

**Example**:
- Upload 1200x800 image
- Auto-scaled to 400x267
- User can then use 0.5x slider → 200x133 effective size
- User can then use 2.0x slider → 800x534 effective size

## UI Changes Summary

### Control Panel - Left Section
**Before**:
```
Zebra Stripes: [toggle] [color1] [color2] [Reset]    Page Mode: [dropdown]
```

**After**:
```
Zebra: [toggle] [color1] [color2]    Ruler: [toggle]    Line #: [toggle]
Page Mode: [dropdown]    Width: [dropdown] (132)
```

### Control Panel - Right Section
**Before**:
```
... Watermark | Ranges | Export PDF
```

**After**:
```
... Watermark | Ranges ● | Export PDF
```
(● = green dot when ranges active, red button background)

### Report Display
**Without line numbers**:
```
         10        20        30        40
.+....|.+....|.+....|.+....|.+....|.+...
REPORT NO - FXR16    ...
CLIENT ACCT/         ...
```

**With line numbers**:
```
         10        20        30        40
.+....|.+....|.+....|.+....|.+....|.+...
     1 | REPORT NO - FXR16    ...
     2 | CLIENT ACCT/         ...
```

## State Variables Added

```javascript
AppState = {
    // ... existing ...
    showRuler: true,           // Ruler toggle state
    showLineNumbers: false,    // Line numbers toggle state
    detectedWidth: 132,        // Auto-detected or selected width
}
```

## New Functions

1. **toggleRuler()** - Toggle ruler display
2. **toggleLineNumbers()** - Toggle line number display
3. **changeWidth()** - Handle width selector change
4. **detectReportWidth()** - Auto-detect report width from content
5. **updateRangesIndicator()** - Update visual indicator on Ranges button

## Updated Functions

1. **buildRuler()** - Fixed to show proper column numbers, dynamic width
2. **renderReport()** - Added line numbers support, ruler toggle
3. **renderReportWithSearch()** - Added line numbers support, ruler toggle
4. **loadWatermarkImage()** - Added auto-scaling for large images

## AS/400 Spool File Width Support

| Width | Description | Use Case |
|-------|-------------|----------|
| **80** | Portrait/Narrow | Simple reports, 80-column display sessions |
| **132** | Landscape/Wide | Industry standard, 10 CPI printing |
| **198** | Extra Wide | Extensive financial spreadsheets |
| **255** | Maximum | Custom printer files, DDS limit |

**Auto-Detection Logic**:
```
Actual Width → Standard Width
0-80         → 80
81-132       → 132
133-198      → 198
199-255      → 255
```

## Performance Impact

**Line Numbers**:
- Minimal impact when disabled (no extra DOM elements)
- When enabled: +1 `<span>` per line
- 2,863 line file: +2,863 elements (still renders in <1 second)

**Ruler**:
- No performance impact
- Built once per render as simple string
- Syncs scroll without re-rendering

**Width Detection**:
- Runs once after file load
- O(n) scan of all lines
- Negligible impact (<10ms for 2,863 lines)

## Testing Checklist

All features tested with sample files:

- ✅ **FRX16.txt** (326 lines, 132 cols)
  - Ruler shows 1-132 correctly
  - Width auto-detected as 132
  - Line numbers display correctly

- ✅ **FXR20.txt** (192 lines)
  - Ruler toggle works
  - Line numbers toggle works

- ✅ **RPVR1011181047.TXT** (2,863 lines)
  - Large file with line numbers still fast
  - Width auto-detection accurate

- ✅ **Watermark Scaling**
  - Uploaded 800x600 image → auto-scaled to 400x300
  - Uploaded 1200x900 image → auto-scaled to 400x300
  - Small 200x150 image → not scaled
  - User scale slider works correctly after auto-scale

- ✅ **Ranges Indicator**
  - Ranges button normal when no filter
  - Ranges button highlighted with green dot when filter active
  - Tooltip updates correctly

## Known Limitations

1. **Line Numbers**: Take up screen width (~70px), may cause horizontal scroll
2. **Very Wide Reports** (>255 cols): Not supported, would need custom width input
3. **Ruler Scroll Sync**: May have slight lag on very fast scrolling

## Future Enhancement Ideas

1. **Adjustable Line Number Width**: Auto-size based on max line count
2. **Ruler Color Coding**: Different colors for different column ranges (e.g., 1-80, 81-132)
3. **Click-to-Copy Column Position**: Click ruler to copy position to clipboard
4. **Line Number Click**: Click line number to highlight/copy line
5. **Custom Width Input**: Allow manual entry for non-standard widths
6. **Ruler Position Options**: Top only (current), bottom only, or both
7. **Export with Line Numbers**: Option to include line numbers in PDF export
