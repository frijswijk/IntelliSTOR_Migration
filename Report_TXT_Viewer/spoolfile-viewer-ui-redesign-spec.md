# Report/Spoolfile Viewer - UI Redesign Specification

## Objective
Consolidate the toolbar from 3 rows to a single toolbar row + enhanced ruler bar, improving usability on smaller screens while maintaining all functionality.

---

## Current State (Before)
```
Row 1: [Open File] | Title | Filename
Row 2: Zoom controls | Page nav | Zebra toggle | Ruler toggle | Line# toggle | Light toggle | Page Mode | Width
Row 3: Search input | Case Sensitive | Search btn | Clear btn | Nav arrows | Watermark | Ranges | Export PDF | Maximize
```
**Problems:** Too much vertical space, redundant toggles, poor responsive behavior

---

## Target State (After)

### Main Toolbar (Single Row)
```
┌────────────────────────────────────────────────────────────────────────────────────┐
│ [Open File]  📄 Report/Spoolfile Viewer   [🔍 Search...    ×][◄][►]  [⚙️] FRX16.txt│
└────────────────────────────────────────────────────────────────────────────────────┘
```

### Enhanced Ruler Bar
```
┌────────────────────────────────────────────────────────────────────────────────────┐
│ Ln 4 Col 33 │[#]│  ····10····20····30····40···· ... ····130────┤    [▼ Auto 132] │
└────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Specifications

### 1. Search Input with Inline Controls
```html
<div class="search-container">
  <span class="search-icon">🔍</span>
  <input type="text" placeholder="Search..." />
  <span class="match-info">3/17</span>  <!-- Only visible when matches found -->
  <button class="nav-prev">◄</button>
  <button class="nav-next">►</button>
  <button class="clear-btn">×</button>  <!-- Only visible when text present -->
</div>
```

**Behavior:**
- `×` clear button appears only when input has text
- Match count `3/17` appears only when search is active and matches exist
- `◄` `►` navigation buttons for cycling through matches
- Pressing Enter or typing triggers search (debounced)

### 2. Zoom Control (Compact Dropdown)
```html
<select class="zoom-dropdown">
  <option value="50">50%</option>
  <option value="75">75%</option>
  <option value="100">100%</option>
  <option value="125">125%</option>
  <option value="150" selected>150%</option>
  <option value="200">200%</option>
  <option value="fit">Fit Width</option>
</select>
```

**Placement:** Inside the Settings panel (⚙️), not in main toolbar

### 3. Settings Panel (⚙️)

The settings gear icon opens a dropdown/popover panel:

```
┌─────────────────────────────────────┐
│  ⚙️ Settings                     ✕  │
├─────────────────────────────────────┤
│                                     │
│  Theme                              │
│  ○ Light                            │
│  ○ Dark                             │
│  ○ High Contrast                    │
│                                     │
│  Zoom                               │
│  [▼ 150%                        ]   │
│                                     │
│  Display                            │
│  ☑ Zebra striping                   │
│     Even [▓]  Odd [░]               │  ← color pickers
│  ☐ Case sensitive search            │
│                                     │
│  Page Mode                          │
│  ○ Dynamic  ○ Fixed                 │
│                                     │
├─────────────────────────────────────┤
│  Tools                              │
│  [🎨 Watermark...]                  │
│  [📊 Ranges...]                     │
│  [📄 Export PDF]                    │
│                                     │
└─────────────────────────────────────┘
```

### 4. Ruler Bar Enhancements

**Left section:** Position indicator + Line number toggle
```html
<div class="ruler-left">
  <span class="position-indicator">Ln 4 Col 33</span>
  <button class="line-toggle" title="Toggle line numbers">#</button>
</div>
```

**Center section:** The ruler itself (unchanged)

**Right section:** Width selector
```html
<div class="ruler-right">
  <select class="width-dropdown">
    <option value="auto">Auto (132)</option>
    <option value="80">80</option>
    <option value="132">132</option>
    <option value="160">160</option>
    <option value="custom">Custom...</option>
  </select>
</div>
```

---

## Removed/Relocated Elements

| Element | Action | New Location |
|---------|--------|--------------|
| Ruler toggle | **REMOVE** | Always show ruler |
| Light/Dark toggle | **MOVE** | Settings panel → Theme |
| Zebra toggle | **MOVE** | Settings panel → Display |
| Zebra color pickers | **MOVE** | Settings panel → Display |
| Case Sensitive checkbox | **MOVE** | Settings panel → Display |
| Page Mode dropdown | **MOVE** | Settings panel |
| Watermark button | **MOVE** | Settings panel → Tools |
| Ranges button | **MOVE** | Settings panel → Tools |
| Clear button | **REPLACE** | Inline × in search input |
| Search button | **REMOVE** | Search on Enter/type (debounced) |
| Row/Col indicator | **MOVE** | Ruler bar left section |
| Width dropdown | **MOVE** | Ruler bar right section |
| Line # toggle | **MOVE** | Ruler bar (small `#` button) |
| Zoom +/- buttons | **REPLACE** | Dropdown in Settings |

---

## High Contrast Mode Implementation

### Technical Approach
Use CSS custom properties with class toggling on `<body>`:

```css
/* Default/Dark theme variables */
:root {
  --bg-primary: #1a1a2e;
  --bg-secondary: #16213e;
  --accent-primary: #e94560;
  --report-text: #e0e0e0;
  --ruler-text: #888;
  --highlight-bg: #ffff00;
  --highlight-text: #000;
}

/* Light theme */
body.light-mode {
  --bg-primary: #f5f5f5;
  --bg-secondary: #ffffff;
  --accent-primary: #d63447;
  --report-text: #333333;
  --ruler-text: #666;
}

/* High Contrast theme - "Green Screen" terminal style */
body.high-contrast {
  --bg-primary: #000000;
  --bg-secondary: #000000;
  --accent-primary: #00ff00;
  --report-text: #00ff00;
  --ruler-text: #00ff00;
  --highlight-bg: #ffffff;
  --highlight-text: #000000;
  
  /* Alternative: White on Black */
  /* --report-text: #ffffff; */
}

/* High contrast specific overrides */
body.high-contrast .report-display {
  font-family: 'Courier New', monospace;
  text-shadow: 0 0 2px var(--report-text); /* Subtle glow effect */
}

body.high-contrast .ruler .decade-marker {
  color: #00ffff; /* Cyan for ruler markers */
  font-weight: bold;
}

body.high-contrast .search-highlight {
  background: #ffff00;
  color: #000000;
  outline: 2px solid #ffffff;
}
```

### JavaScript Toggle
```javascript
function setTheme(theme) {
  document.body.classList.remove('light-mode', 'dark-mode', 'high-contrast');
  if (theme !== 'dark') {
    document.body.classList.add(theme === 'light' ? 'light-mode' : 'high-contrast');
  }
  localStorage.setItem('viewer-theme', theme);
}
```

### Benefits of High Contrast Mode
- **Reduced eye strain:** Mimics legacy "Green Screen" terminals preferred for long-duration report analysis
- **Visual hierarchy:** Ruler decade markers (10, 20, 30) and search highlights pop more aggressively
- **Accessibility:** WCAG AAA contrast ratios for users with visual impairments

---

## Responsive Behavior

### Breakpoints

```css
/* Desktop (>1024px): Full layout */
/* Tablet (768-1024px): Collapse some elements */
/* Mobile (<768px): Maximum consolidation */
```

### Priority Levels for Collapsing

| Priority | Elements | Collapse Behavior |
|----------|----------|-------------------|
| 1 - Always visible | Open File, Search, Settings gear | Never hide |
| 2 - High priority | Filename, Page navigation | Hide label, keep icon on mobile |
| 3 - Collapse first | Position indicator | Move to tooltip on hover |
| 4 - Collapse second | Width dropdown | Move fully into Settings |

### Mobile Layout (<768px)
```
┌──────────────────────────────────────┐
│ [≡] 📄 Viewer  [🔍][⚙️]  FRX16.txt  │
├──────────────────────────────────────┤
│ [Search...                      ×]   │  ← Full width search row
├──────────────────────────────────────┤
│ Ln 4 Col 33  ····10····20····       │
└──────────────────────────────────────┘
```

The hamburger menu `[≡]` contains:
- Open File
- Zoom controls
- Export PDF
- Maximize

---

## Implementation Checklist

### Phase 1: Structure Changes
- [ ] Remove ruler toggle (always show ruler)
- [ ] Create Settings panel component with popover/dropdown
- [ ] Move theme toggle, zebra, page mode, zoom to Settings
- [ ] Move Watermark, Ranges, Export PDF to Settings → Tools section

### Phase 2: Search Consolidation
- [ ] Replace Search button with Enter/debounce trigger
- [ ] Replace Clear button with inline × (show/hide based on input)
- [ ] Add match count display (e.g., "3/17")
- [ ] Keep ◄ ► navigation inline with search

### Phase 3: Ruler Bar Enhancement
- [ ] Move Row/Col indicator to ruler bar left
- [ ] Move Width dropdown to ruler bar right
- [ ] Add small Line # toggle button next to position indicator

### Phase 4: High Contrast Mode
- [ ] Add CSS variables for high contrast theme
- [ ] Implement theme toggle in Settings (Light/Dark/High Contrast)
- [ ] Add localStorage persistence for theme preference
- [ ] Test with monospace report content

### Phase 5: Responsive
- [ ] Add CSS breakpoints
- [ ] Implement collapse behavior per priority table
- [ ] Test on tablet and mobile viewports
- [ ] Add hamburger menu for mobile

---

## Notes for Developer

1. **Search debounce:** Use 300ms debounce on input to avoid excessive searches while typing

2. **Settings panel:** Consider using a lightweight library like Floating UI/Popper for positioning, or implement a simple CSS-based dropdown

3. **Theme persistence:** Store in `localStorage` with key like `spoolfile-viewer-theme`

4. **Accessibility:** Ensure all interactive elements have proper `aria-labels` and keyboard navigation

5. **CSS approach:** Prefer CSS custom properties over SASS variables for runtime theme switching

6. **Animation:** Add subtle transitions (150-200ms) for theme changes and panel open/close
