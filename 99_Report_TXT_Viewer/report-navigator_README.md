# IntelliSTOR Report Navigator

A browser-based single-page application for navigating, searching, and viewing RPT (report) files from IntelliSTOR migration data. Provides hierarchical browsing (Species → Instances → Pages) with indexed field search via MAP files. Runs entirely client-side — no server required.

**Requirements:** Chrome or Edge (uses File System Access API)
**External dependency:** [Pako](https://github.com/nicolo-ribaudo/pako) (zlib decompression, loaded via CDN)

---

## User Guide

### Getting Started

1. Open `report-navigator.html` in Chrome or Edge.
2. Click **Folders** in the header to configure your data directories:
   - **CSV Data** — folder containing `species_summary_2025_2025.csv` and per-species CSV files
   - **RPT Files** — folder containing binary compressed report files (`.RPT`)
   - **MAP Files** — folder containing binary index map files (`.MAP`)
3. Click **Done**. The species list loads automatically.

Folder selections persist across sessions via IndexedDB — you only need to pick them once.

### Browsing Species and Instances

1. **Species panel** (left) — shows all report species with instance count, RPT files found, and MAP files found.
2. Click a species to load its instances in the **Instance panel** (center).
3. Click an instance to see its details, RPT sections, and indexed fields in the **tabbed panel** below.

### Filtering and Sorting

Both panels support:
- **Text filter** — type in the filter input to search by name/filename/date
- **Toggle buttons** — `RPT>0` / `MAP>0` (species) or `RPT` / `MAP` (instances) to show only rows with those files
- **Column sorting** — click any column header to sort; click again to reverse

### Viewing Report Pages

When an instance with an RPT file is selected:
- **Sections tab** shows clickable chips for each section (e.g., `#1 (p1-42)`). Click to extract and view all pages in that section.
- **Page navigation** in the viewer toolbar: use `<<` / `>>` to step through pages, or type a page number and press Enter.
- **All** button extracts every page from the RPT file.
- **Copy** button copies all displayed report text to the clipboard.

### Searching Report Text

- **Ctrl+F** focuses the viewer search input.
- Type to search — matches highlight in yellow, current match has a red outline.
- **F3** / **Shift+F3** cycle through matches (or use the ↑ ↓ buttons).

### Searching Indexed Fields (MAP Files)

1. In the **Details tab**, click a field chip (e.g., `CUSTOMER_NAME [L1/F3]`).
2. The **Index Search tab** opens with that field selected.
3. Type a value and click **Search** (or press Enter).
   - Check **Prefix** for prefix matching (e.g., "SMIT" matches "SMITH", "SMITHSON").
   - Uncheck for exact match.
4. Click **List All** to see every unique value in that field with counts.
5. Click a page number in the results to jump directly to that page in the viewer.

### Keyboard Navigation

| Key | Action |
|-----|--------|
| **Arrow Left** | Switch focus to species panel |
| **Arrow Right** | Switch focus to instances panel (if a species is selected) |
| **Arrow Up / Down** | Move selection up/down within the focused panel |
| **Ctrl+F** | Focus viewer search input |
| **F3** / **Shift+F3** | Next / previous search match |
| **Escape** | Close folder dialog, or clear viewer search |

Arrow key navigation is disabled while typing in any input field. The active panel shows a colored left-border indicator.

### Theme

Click **Theme** in the header to toggle between dark mode (default) and light mode.

### Panel Resizing

- **Vertical resizers** between panels: drag left/right to adjust panel widths.
- **Horizontal splitter** in the instance panel: drag up/down to adjust the split between the instance list and the tabbed detail panel.

---

## Technical Reference

### Architecture

Single HTML file (~2,200 lines) with embedded CSS and JavaScript. No build step, no frameworks. The only external dependency is Pako for zlib decompression.

### Panel Layout

```
┌── Panel 1 (25%) ──┬── Panel 2 (35%) ──────────────┬── Panel 3 (flex) ──────┐
│                    │                                │                        │
│  Species Table     │  Instance Table                │  Report Viewer         │
│  (virtual scroll)  │                                │  (virtual scroll)      │
│                    ├── horizontal splitter ─────────┤                        │
│                    │  Tabs: Details|Sections|Search  │                        │
└────────────────────┴────────────────────────────────┴────────────────────────┘
```

- Panel 1: min-width 200px
- Panel 2: min-width 280px
- Panel 3: min-width 300px

### Application State

All state lives in a single `AppState` object:

| Property | Type | Description |
|----------|------|-------------|
| `csvDirHandle` / `rptDirHandle` / `mapDirHandle` | `FileSystemDirectoryHandle` | Folder handles from File System Access API |
| `speciesList` / `speciesFiltered` | `Array` | Full and filtered/sorted species data |
| `instanceList` / `instanceFiltered` | `Array` | Full and filtered/sorted instance data |
| `selectedSpecies` / `selectedInstance` | `Object` | Currently selected items (by reference) |
| `speciesSortCol` / `instanceSortCol` | `string` | Current sort column |
| `speciesSortAsc` / `instanceSortAsc` | `boolean` | Sort direction |
| `filterRpt` / `filterMap` | `boolean` | Species panel filter toggles |
| `filterInstRpt` / `filterInstMap` | `boolean` | Instance panel filter toggles |
| `activePanel` | `'species'` \| `'instances'` | Which panel has keyboard focus |
| `rptData` / `rptHeader` / `rptPageEntries` / `rptSections` | Various | Parsed RPT file data |
| `mapParser` | `MapFileParser` | Loaded MAP file parser instance |
| `decompressedPages` | `Object` | Cache of decompressed pages (keyed by page number) |
| `viewerPages` / `viewerAllLines` / `viewerTotalPages` | Various | Viewer display state |
| `viewerSearchMatches` / `viewerSearchCurrentIdx` | `Array` / `number` | Viewer search state |

### Data Flow

```
Pick Folders → IndexedDB persistence
       ↓
Load species_summary CSV → speciesList → filter/sort → speciesFiltered → render
       ↓ (click species)
Load per-species CSV → instanceList → filter/sort → instanceFiltered → render
       ↓ (click instance)
Load RPT binary → parseRptHeader → readPageTable → readSectionHdr
       ↓ (click section or page link)
decompressPage (pako inflate) → decompressedPages cache → displayPages → viewer
       ↓ (click field chip)
Load MAP binary → MapFileParser → binarySearch / listAllValues → search results
```

### File Formats

#### CSV Files

**`species_summary_2025_2025.csv`** — one row per species:
- `REPORT_SPECIES_NAME`, `INSTANCE_COUNT`, `RPT_FILES_FOUND`, `MAP_FILES_FOUND`, `MAX_SECTIONS`, `INDEX_FIELD_NAMES`

**`<SPECIES_NAME>_2025_2025.csv`** — one row per instance:
- `FILENAME`, `REPORT_DATE`, `RPT_FILE_EXISTS`, `MAP_FILE_EXISTS`, `RPT_FILENAME`, `MAP_FILENAME`, `SEGMENTS`, `INDEXED_FIELDS`

#### RPT Files (Binary)

Compressed report pages with the following structure:
- **RPTFILEHDR** — file header with signature validation
- **PAGETBLHDR** — page table entries (one per page), each containing offset and compressed size
- **SECTIONHDR** — section definitions with start/end page ranges
- **BPAGETBLHDR** — binary page entries (PDF or AFP objects, detected by magic bytes)
- **Page data** — zlib-compressed chunks, decompressed with Pako

Header offset constant: `RPTINSTHDR_OFFSET = 0xF0`

#### MAP Files (Binary)

Indexed field data for search, structured as segments:
- **ME_MARKER** (`2A 00 2A 00 4D 00 45 00`) — segment delimiter
- **Segment 0** — page lookup table (15-byte records: u32 page, u8 recType, u32 joinKey, ...)
- **Segments 1+** — indexed field data, each with:
  - Header (24 bytes): lineId (u16), fieldId (u16), fieldWidth (u16), entryCount (u16)
  - Entries (7 + fieldWidth bytes each): length (u16), value (ASCII), recordIndex (u16)

Search uses binary search on sorted field values → recordIndex → Segment 0 page lookup. Performance is O(log n + matches).

### Virtual Scrolling

Two separate virtual scrolling implementations:

#### Species Table
- Row height: 26px
- Renders only visible rows based on `container.scrollTop` and `container.clientHeight`
- Re-renders on scroll via event listener on `speciesListContainer`
- Uses `data-idx` attributes to map rows back to `speciesFiltered` indices

#### Report Viewer
- Line height: 16px
- Activates for files > 500 lines
- `VirtualScroller` class with 50-line buffer above/below viewport
- Uses spacer divs (top/bottom) to maintain correct scroll height
- Re-renders on scroll via `requestAnimationFrame`
- `ResizeObserver` handles container resize
- Falls back to full DOM rendering for smaller files

### Keyboard Navigation Implementation

- **State:** `AppState.activePanel` tracks focused panel (`'species'` or `'instances'`)
- **Visual indicator:** `.panel-content.kb-active` CSS class adds 2px left border in accent color
- **`setActivePanel(panel)`** — toggles `kb-active` class on `speciesListContainer` / `instanceListContainer`
- **`scrollRowIntoView(container, idx, rowHeight)`** — adjusts `container.scrollTop` to ensure the row at `idx` is visible
- Arrow keys are handled in the global `keydown` listener, skipped when `activeElement` is `INPUT`, `TEXTAREA`, or `SELECT`
- For species: scrolls, re-renders virtual table, then calls `selectSpecies()` (async — loads CSV)
- For instances: scrolls, then calls `selectInstance()`
- Click handlers on both panels also call `setActivePanel()` to keep the indicator in sync

### IndexedDB Persistence

- **Database:** `ReportNavigator`
- **Store:** `folderHandles`
- **Keys:** `'csv'`, `'rpt'`, `'map'`
- **Values:** `FileSystemDirectoryHandle` objects
- On load: restores handles, checks `queryPermission({ mode: 'read' })`
- On folder pick: saves handle via `saveHandle()`

### CSS Theming

Uses CSS custom properties on `:root` (dark mode default) and `body.light-mode` override. Key variables:

| Variable | Dark | Light | Usage |
|----------|------|-------|-------|
| `--bg-primary` | `#1a1a2e` | `#f5f5f5` | Main background |
| `--bg-secondary` | `#16213e` | `#ffffff` | Panels, header |
| `--accent-primary` | `#e94560` | `#d63447` | Highlights, active states |
| `--accent-secondary` | `#3498db` | `#2980b9` | Secondary buttons |
| `--report-bg` | `#0a0a0a` | `#ffffff` | Viewer background |
| `--report-text` | `#e0e0e0` | `#333333` | Viewer text |
| `--highlight-bg` | `#ffff00` | `#ffff00` | Search match background |
| `--row-selected` | `rgba(233,69,96,0.3)` | `rgba(214,52,71,0.2)` | Selected row |

### Panel Resizing

- **Vertical resizers** (4px width): `mousedown` → capture initial positions → `mousemove` → apply deltas → `mouseup` → cleanup. Min-width 150px per panel.
- **Horizontal splitter** (5px height): same pattern. Min-height 60px (top) / 80px (bottom).

### Browser Compatibility

- **Required:** Chrome 86+ or Edge 86+ (File System Access API)
- **Not supported:** Firefox, Safari (no `showDirectoryPicker`)
- **Clipboard API:** Required for Copy button
- **Pako:** Loaded from CDN (`cdn.jsdelivr.net/npm/pako@2.1.0`)
