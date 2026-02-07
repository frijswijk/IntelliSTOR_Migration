# Virtual Scrolling - Quick Testing Guide

## Quick Start

1. **Open the viewer**:
   ```
   Open report-viewer.html in Chrome/Edge/Firefox
   ```

2. **Load large test file**:
   - Click "📁 Open File"
   - Select: `S94752001749_20250416.txt` (184,807 lines)
   - File should load quickly (~150ms vs previous ~1,500ms)

3. **Verify virtual scrolling is active**:
   - Open DevTools (F12) → Elements tab
   - Inspect `#reportDisplay`
   - Should see only ~200 `.report-line` elements (not 184,807!)

## Performance Testing

### Test 1: Initial Load Performance ⚡
**Expected**: Load completes in ~150ms (was ~1,500ms)

1. Open DevTools → Performance tab
2. Click Record
3. Load large file
4. Stop recording
5. Check "Loading" section duration

**Success Criteria**: < 500ms total load time

### Test 2: Scroll Performance 🖱️
**Expected**: Smooth 60fps scrolling (was ~15fps)

1. Open DevTools → Rendering tab
2. Enable "Frame Rendering Stats"
3. Scroll rapidly up and down in report
4. Watch FPS counter

**Success Criteria**:
- FPS stays ~58-60fps
- No dropped frames
- No UI freezing

### Test 3: INP (Interaction to Next Paint) 📊
**Expected**: < 200ms (was 1,136ms)

1. Open DevTools → Performance tab
2. Enable "Web Vitals" in settings
3. Record while scrolling and interacting
4. Check INP metric

**Success Criteria**: INP < 200ms (target: 50-80ms)

### Test 4: Memory Usage 💾
**Expected**: ~50MB (was 400MB+)

1. Open DevTools → Memory tab
2. Take heap snapshot after loading large file
3. Check "Shallow Size" total

**Success Criteria**: < 100MB heap size

## Functional Testing

### Test 5: Search Functionality 🔍
**Expected**: Search works correctly with virtual scrolling

1. Load large file
2. Type search term in search box (e.g., "ERROR")
3. Click next/previous buttons
4. Verify:
   - ✅ Results highlight correctly
   - ✅ Navigation scrolls to correct line
   - ✅ UI remains responsive during search
   - ✅ Match count displays correctly

### Test 6: Mouse Tracking 🖱️
**Expected**: Smooth cursor position tracking

1. Move mouse over report lines
2. Watch cursor position in ruler (top-left)
3. Verify:
   - ✅ Position updates smoothly (no lag)
   - ✅ Column highlight appears (if enabled)
   - ✅ No stuttering or freezing

### Test 7: Print Support 🖨️
**Expected**: All content renders in print preview

1. Press Ctrl+P (or Cmd+P on Mac)
2. Check print preview
3. Verify:
   - ✅ All pages appear
   - ✅ Page breaks at separators
   - ✅ Content is readable
4. Cancel print
5. Verify:
   - ✅ Returns to normal view
   - ✅ Virtual scrolling restored

### Test 8: Zoom Functionality 🔎
**Expected**: Zoom works correctly

1. Change zoom to 50%
2. Move mouse over lines
3. Change zoom to 200%
4. Move mouse over lines
5. Select "Fit Width"
6. Verify:
   - ✅ Content scales correctly
   - ✅ Column highlighting adjusts
   - ✅ Mouse tracking accurate at all zoom levels

### Test 9: Keyboard Navigation ⌨️
**Expected**: Keyboard shortcuts work

1. Click in report area to focus
2. Test keys:
   - PageDown → Should scroll down one viewport
   - PageUp → Should scroll up one viewport
   - Ctrl+Home → Should jump to top
   - Ctrl+End → Should jump to bottom
3. Verify:
   - ✅ All shortcuts work
   - ✅ Scrolling is smooth
   - ✅ No errors in console

### Test 10: Feature Toggle 🎚️
**Expected**: Can disable virtual scrolling

1. Open report-viewer.html in text editor
2. Find line ~2497: `const USE_VIRTUAL_SCROLLING = true;`
3. Change to: `const USE_VIRTUAL_SCROLLING = false;`
4. Save and reload page
5. Load large file
6. Verify:
   - ✅ Falls back to traditional rendering
   - ✅ All features still work (search, print, etc.)
   - ✅ Performance is worse (expected)
7. Change back to `true` and verify performance improves

## Regression Testing

### Test 11: Small Files (<1000 lines)
**Expected**: Uses traditional rendering

1. Load small test file (e.g., IG2350P.txt)
2. Open DevTools → Elements
3. Check `#reportDisplay` structure
4. Verify:
   - ✅ Uses traditional `.report-content` structure
   - ✅ No virtual scroller spacers
   - ✅ All features work normally

### Test 12: Watermark Feature 💧
**Expected**: Watermark appears correctly

1. Load large file
2. Open Settings (⚙️)
3. Enable watermark, upload image
4. Verify:
   - ✅ Watermark appears on visible content
   - ✅ Watermark updates when scrolling
   - ✅ No performance degradation

### Test 13: Zebra Striping 🦓
**Expected**: Zebra colors apply correctly

1. Load large file
2. Open Settings → Toggle "Zebra Striping"
3. Scroll through report
4. Verify:
   - ✅ Alternating colors apply to lines
   - ✅ Colors stay consistent when scrolling
   - ✅ No flickering

### Test 14: Page Ranges 📄
**Expected**: Page ranges work with virtual scrolling

1. Load large file
2. Click "Page Ranges" button
3. Enter range (e.g., "1-10")
4. Click Apply
5. Verify:
   - ✅ Only specified pages show
   - ✅ Virtual scrolling still active
   - ✅ Page indicators correct

## Browser Compatibility

### Test 15: Cross-Browser Testing 🌐
Test in multiple browsers:

**Chrome/Edge** (Primary):
- ✅ All features work
- ✅ Performance optimal

**Firefox**:
- ✅ All features work
- ✅ Performance comparable to Chrome

**Safari** (macOS only):
- ✅ All features work
- ✅ Performance good

## Performance Benchmarks

### Expected Results Summary

| Test | Before | After | Pass Criteria |
|------|--------|-------|---------------|
| Initial Load | ~1,500ms | ~150ms | < 500ms |
| Scroll FPS | ~15fps | ~58fps | > 50fps |
| INP | 1,136ms | ~50-80ms | < 200ms |
| Memory | 400MB | ~50MB | < 100MB |
| DOM Nodes | 184,807 | ~200 | < 500 |
| Mousemove | ~20ms | ~2ms | < 5ms |

## Troubleshooting

### Issue: Virtual scrolling not activating
**Check**:
- File has >1000 lines
- `USE_VIRTUAL_SCROLLING = true` (line ~2497)
- No JavaScript errors in console

### Issue: Search not working correctly
**Check**:
- Wait for search to complete
- Check console for errors
- Verify `AppState.searchResults` populated

### Issue: Print preview empty
**Check**:
- `beforeprint` event firing (check console)
- `renderFullReportForPrint()` called
- Print CSS applied

### Issue: Poor performance even with virtual scrolling
**Check**:
- File size (might be other bottleneck)
- Browser DevTools open (can slow performance)
- Other extensions interfering
- Hardware acceleration enabled

## Quick Console Checks

Open DevTools console and run:

```javascript
// Check if virtual scrolling is active
console.log('Virtual scroller:', virtualScroller);

// Check flattened lines count
console.log('Flattened lines:', AppState.flattenedLines?.length);

// Check visible DOM nodes
console.log('Visible lines:', document.querySelectorAll('.report-line').length);

// Check cached positions
console.log('Cached positions:', cachedPagePositions.length);

// Check feature flag
console.log('Virtual scrolling enabled:', USE_VIRTUAL_SCROLLING);
```

## Reporting Issues

If you find issues, please report:
1. Browser version
2. File size (line count)
3. Steps to reproduce
4. Console errors (if any)
5. Performance metrics from DevTools
6. Screenshot/video if possible

---

**Testing completed**: 2026-02-05
**Status**: Ready for production testing
