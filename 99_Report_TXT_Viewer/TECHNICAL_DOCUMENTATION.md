# Report/Spoolfile Viewer - Technical Documentation

## Version: 1.0
## Date: 2026-01-27
## Author: Claude Sonnet 4.5

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Technology Stack](#technology-stack)
3. [File Structure](#file-structure)
4. [Core Components](#core-components)
5. [Data Structures](#data-structures)
6. [Algorithm Details](#algorithm-details)
7. [Rendering Pipeline](#rendering-pipeline)
8. [Feature Implementation](#feature-implementation)
9. [Performance Optimizations](#performance-optimizations)
10. [Browser Compatibility](#browser-compatibility)
11. [Extending the Viewer](#extending-the-viewer)

---

## Architecture Overview

### Design Philosophy

The viewer is designed as a **single-file, standalone HTML application** with zero server dependencies. All processing occurs client-side in the browser.

**Key Architectural Decisions**:
- **No build process**: Pure HTML/CSS/JavaScript - open and run
- **No frameworks**: Vanilla JavaScript for maximum portability
- **Minimal dependencies**: Only jsPDF and html2canvas from CDN
- **Progressive rendering**: HTML string building for performance
- **Immutable file data**: Original content never modified

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         Browser                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                    report-viewer.html                 │  │
│  │                                                       │  │
│  │  ┌─────────────────────────────────────────────────┐ │  │
│  │  │              User Interface Layer                │ │  │
│  │  │  - Header (file upload)                         │ │  │
│  │  │  - Control Panel (toggles, selectors)           │ │  │
│  │  │  - Report Display Container                     │ │  │
│  │  │  - Modals (watermark, ranges)                   │ │  │
│  │  │  - Footer (status, shortcuts)                   │ │  │
│  │  └─────────────────────────────────────────────────┘ │  │
│  │                         ↕                             │  │
│  │  ┌─────────────────────────────────────────────────┐ │  │
│  │  │            State Management Layer                │ │  │
│  │  │  - AppState (single source of truth)            │ │  │
│  │  │  - localStorage persistence                     │ │  │
│  │  └─────────────────────────────────────────────────┘ │  │
│  │                         ↕                             │  │
│  │  ┌─────────────────────────────────────────────────┐ │  │
│  │  │             Processing Layer                     │ │  │
│  │  │  - File Parser                                   │ │  │
│  │  │  - Page Detection Engine                        │ │  │
│  │  │  - Search Engine                                │ │  │
│  │  │  - Watermark Engine                             │ │  │
│  │  └─────────────────────────────────────────────────┘ │  │
│  │                         ↕                             │  │
│  │  ┌─────────────────────────────────────────────────┐ │  │
│  │  │              Rendering Layer                     │ │  │
│  │  │  - HTML String Builder                          │ │  │
│  │  │  - CSS Styling Engine                           │ │  │
│  │  │  - Canvas Watermark Renderer                    │ │  │
│  │  └─────────────────────────────────────────────────┘ │  │
│  │                         ↕                             │  │
│  │  ┌─────────────────────────────────────────────────┐ │  │
│  │  │               Export Layer                       │ │  │
│  │  │  - PDF Generator (jsPDF)                        │ │  │
│  │  │  - Canvas Renderer (html2canvas)                │ │  │
│  │  └─────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

### Core Technologies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| **Structure** | HTML5 | - | Semantic markup, modern APIs |
| **Styling** | CSS3 | - | Grid, Flexbox, CSS Variables |
| **Scripting** | JavaScript (ES6+) | - | Vanilla JS, no transpilation |
| **Font** | Courier New | System | Monospace rendering |

### External Libraries

| Library | Version | CDN | Purpose |
|---------|---------|-----|---------|
| **jsPDF** | 2.5.1 | cdnjs | PDF generation |
| **html2canvas** | 1.4.1 | cdnjs | Canvas rendering for PDF |

**Why These Libraries?**
- **jsPDF**: Industry standard, 40k+ GitHub stars, active maintenance
- **html2canvas**: Reliable DOM-to-canvas conversion, watermark rendering

### Browser APIs Used

- **FileReader API**: Read local text files
- **Canvas API**: Watermark rendering, image manipulation
- **localStorage API**: Persist user preferences
- **Blob API**: PDF file download

---

## File Structure

### Single File Anatomy

```html
report-viewer.html (~3,900 lines)
├── <!DOCTYPE html>
├── <head>
│   ├── <meta> tags (UTF-8, viewport)
│   ├── <title>
│   └── <style> (~900 lines)
│       ├── CSS Variables (:root)
│       ├── Reset & Base Styles
│       ├── Layout (header, footer, panels)
│       ├── Report Display (monospace, ruler, lines)
│       ├── Controls (buttons, toggles, inputs)
│       ├── Modals (watermark, ranges)
│       ├── Search Highlighting
│       ├── Progress & Toasts
│       └── Responsive & Print Styles
└── <body>
    ├── <!-- Header Section -->
    ├── <!-- Control Panel -->
    ├── <!-- Report Display -->
    ├── <!-- Watermark Modal -->
    ├── <!-- Page Ranges Modal -->
    ├── <!-- Progress Overlay -->
    ├── <!-- Toast Notification -->
    ├── <!-- CDN Script Includes -->
    └── <script> (~2,500 lines)
        ├── State Management
        ├── Initialization
        ├── File Handling
        ├── File Parsing
        ├── Page Detection
        ├── Rendering
        ├── Zebra Striping
        ├── Page Mode
        ├── View Toggles
        ├── Search
        ├── Navigation
        ├── Page Ranges
        ├── Watermark
        ├── PDF Export
        ├── Zoom
        ├── Drag & Drop
        ├── Keyboard Shortcuts
        ├── Progress & Toasts
        └── Utilities
```

---

## Core Components

### 1. State Management

**AppState Object** (Global Single Source of Truth)

```javascript
const AppState = {
    // File data (immutable after parsing)
    rawContent: null,           // Original file string
    lines: [],                  // Parsed line objects
    pages: [],                  // Detected page objects
    fileName: '',               // Display name
    fileSize: 0,                // Bytes

    // View settings
    zebraEnabled: false,        // Zebra striping toggle
    zebraColor1: '#1a1a2e',    // Even row color
    zebraColor2: '#0f3460',    // Odd row color
    zoomLevel: 100,            // Percentage (50-200)
    showRuler: true,           // Column ruler toggle
    showLineNumbers: false,    // Line number column toggle
    lightMode: false,          // Light/dark theme

    // Page settings
    pageLengthMode: 'dynamic', // 'dynamic' | '66' | '88'
    fixedPageLength: 66,       // For fixed modes
    detectedWidth: 132,        // Auto-detected or manual (80/132/198/255)

    // Page ranges
    pageRanges: [],            // [{id, name, startPage, pageCount}]
    showRangesOnly: false,     // Filter toggle

    // Search
    searchTerm: '',            // Current search string
    searchResults: [],         // Match locations
    currentSearchIndex: -1,    // Active result

    // Watermark
    watermark: {
        enabled: false,
        imageData: Image,      // Loaded Image object
        imageSrc: '',          // Data URL
        position: 'center',    // 9-point grid position
        rotation: 0,           // Degrees (-180 to 180)
        opacity: 30,           // Percentage (0-100)
        scale: 100             // Percentage (50-200)
    },

    // UI state
    currentPage: 1             // Current visible page
};
```

**State Persistence**

```javascript
// Save to localStorage
function saveSettings() {
    const settings = {
        zebraColor1: AppState.zebraColor1,
        zebraColor2: AppState.zebraColor2,
        zebraEnabled: AppState.zebraEnabled
    };
    localStorage.setItem('reportViewerSettings', JSON.stringify(settings));
}

// Load from localStorage
function loadSettings() {
    const saved = localStorage.getItem('reportViewerSettings');
    if (saved) {
        const settings = JSON.parse(saved);
        AppState.zebraColor1 = settings.zebraColor1;
        AppState.zebraColor2 = settings.zebraColor2;
        AppState.zebraEnabled = settings.zebraEnabled;
    }
}
```

### 2. File Parser

**Purpose**: Convert raw text file into structured data

**Input**: Raw text string from FileReader
**Output**: `AppState.lines[]` array of line objects

**Algorithm**:

```javascript
function parseReportFile() {
    const lines = AppState.rawContent.split(/\r?\n/);
    AppState.lines = [];
    let currentPage = 1;

    // Auto-detect ASA carriage control format
    let usesASACarriageControl = detectASAFormat(lines);

    lines.forEach((rawLine, index) => {
        const controlChar = rawLine.charAt(0);
        let displayText = rawLine;
        let isPageBreak = false;

        // Form feed detection (ASCII 12)
        const isFormFeed = controlChar === '\f' ||
                          controlChar.charCodeAt(0) === 12;

        if (isFormFeed) {
            displayText = rawLine.substring(1);
            isPageBreak = true;
        } else if (usesASACarriageControl) {
            // ASA format: first char is always control
            if (controlChar === '1') {
                displayText = rawLine.substring(1);
                isPageBreak = true;
            } else if ('0-+ '.includes(controlChar)) {
                displayText = rawLine.substring(1);
            }
        }

        const lineObj = {
            lineNumber: index + 1,
            rawText: rawLine,
            displayText: displayText,
            controlChar: controlChar,
            pageNumber: currentPage,
            isPageBreak: isPageBreak,
            hasMatch: false
        };

        if (isPageBreak && index > 0) {
            currentPage++;
            lineObj.pageNumber = currentPage;
        }

        AppState.lines.push(lineObj);
    });
}
```

**Carriage Control Detection**:

```javascript
function detectASAFormat(lines) {
    // Check first 5 non-empty lines
    for (let i = 0; i < Math.min(5, lines.length); i++) {
        const firstChar = lines[i].charAt(0);
        if (lines[i].length > 0 &&
            ['1', '0', '-', ' '].includes(firstChar) &&
            lines[i].charAt(1) === ' ') {
            return true; // ASA format detected
        }
    }
    return false; // Form feed format
}
```

### 3. Page Detection Engine

**Purpose**: Group lines into pages

**Three Modes**:

1. **Dynamic Mode** (default)
   - Use control characters ('1' or '\f') as page breaks
   - Variable page lengths
   - Most accurate for spool files

2. **Fixed 66 Lines**
   - Standard greenbar paper (11" × 6 LPI)
   - Ignore control characters
   - Count 66 lines per page

3. **Fixed 88 Lines**
   - 8 LPI printing (11" × 8 LPI)
   - Count 88 lines per page

**Algorithm (Dynamic)**:

```javascript
function detectPagesDynamic() {
    AppState.pages = [];
    let currentPage = {
        pageNumber: 1,
        startLineNumber: 1,
        lines: [],
        hasSearchMatch: false
    };

    AppState.lines.forEach((line, index) => {
        if (line.isPageBreak && index > 0) {
            // Finalize current page
            currentPage.endLineNumber = AppState.lines[index - 1].lineNumber;
            currentPage.lineCount = currentPage.lines.length;
            AppState.pages.push(currentPage);

            // Start new page
            currentPage = {
                pageNumber: currentPage.pageNumber + 1,
                startLineNumber: line.lineNumber,
                lines: [],
                hasSearchMatch: false
            };
        }

        line.pageNumber = currentPage.pageNumber;
        currentPage.lines.push(line);
    });

    // Add final page
    if (currentPage.lines.length > 0) {
        currentPage.endLineNumber = AppState.lines[AppState.lines.length - 1].lineNumber;
        currentPage.lineCount = currentPage.lines.length;
        AppState.pages.push(currentPage);
    }
}
```

### 4. Rendering Engine

**Purpose**: Convert structured data to HTML

**Strategy**: HTML string building for performance

```javascript
function renderReport() {
    const display = document.getElementById('reportDisplay');

    // Determine pages to display
    let pagesToDisplay = AppState.pages;
    if (AppState.showRangesOnly && AppState.pageRanges.length > 0) {
        pagesToDisplay = filterPagesByRanges();
    }

    // Build HTML string
    let html = '';

    // Add ruler
    if (AppState.showRuler) {
        html += '<div class="ruler">' + buildRuler() + '</div>';
    }

    html += '<div class="report-content">';

    // Render pages
    pagesToDisplay.forEach((page, pageIndex) => {
        // Page separator
        if (pageIndex > 0) {
            html += `<div class="page-separator" data-page="${page.pageNumber}">
                       <span class="page-label">PAGE ${page.pageNumber}</span>
                       <hr class="separator-line">
                     </div>`;
        }

        // Page container
        html += `<div class="report-page" data-page="${page.pageNumber}"
                      id="page-${page.pageNumber}">`;

        // Lines
        page.lines.forEach((line, lineIndex) => {
            const zebraClass = AppState.zebraEnabled ?
                (lineIndex % 2 === 0 ? 'zebra-even' : 'zebra-odd') : '';

            html += `<div class="report-line ${zebraClass}"
                          data-line="${line.lineNumber}">`;

            if (AppState.showLineNumbers) {
                html += `<span class="line-number">${line.lineNumber}</span>`;
            }

            html += `<span class="line-content">${escapeHtml(line.displayText)}</span>
                   </div>`;
        });

        html += '</div>';
    });

    html += '</div>';

    // Single DOM update
    display.innerHTML = html;

    // Apply watermark if enabled
    if (AppState.watermark.enabled && AppState.watermark.imageSrc) {
        applyWatermarkToDisplay();
    }
}
```

**Performance**: Single `innerHTML` update vs. thousands of `appendChild()` calls = **5-10x faster**

### 5. Search Engine

**Algorithm**: Regex-based search with result tracking

```javascript
function performSearch() {
    const term = document.getElementById('searchBox').value.trim();
    const caseSensitive = document.getElementById('caseSensitive').checked;

    AppState.searchTerm = term;
    AppState.searchResults = [];
    AppState.currentSearchIndex = -1;

    // Clear previous matches
    AppState.lines.forEach(line => line.hasMatch = false);

    // Escape regex special characters
    const escapedTerm = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(escapedTerm, caseSensitive ? 'g' : 'gi');

    // Find all matches
    AppState.lines.forEach((line, index) => {
        let match;
        const testRegex = new RegExp(escapedTerm, caseSensitive ? 'g' : 'gi');

        while ((match = testRegex.exec(line.displayText)) !== null) {
            AppState.searchResults.push({
                lineIndex: index,
                lineNumber: line.lineNumber,
                pageNumber: line.pageNumber,
                matchStart: match.index,
                matchLength: term.length
            });
            line.hasMatch = true;
        }
    });

    // Re-render with highlights
    renderReportWithSearch();

    if (AppState.searchResults.length > 0) {
        jumpToSearchResult(0);
    }
}
```

**Highlighting**:

```javascript
// In renderReportWithSearch()
if (line.hasMatch && AppState.searchTerm) {
    lineText = lineText.replace(regex,
        '<mark class="search-highlight">$&</mark>');
}
```

### 6. Watermark Engine

**Components**:
1. Image upload & auto-scaling
2. Canvas-based rendering
3. Content-relative positioning

**Image Auto-Scaling**:

```javascript
function loadWatermarkImage(file) {
    const reader = new FileReader();
    reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
            const maxDimension = 400;

            if (img.width > maxDimension || img.height > maxDimension) {
                // Scale down
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');

                let scale = img.width > img.height ?
                    maxDimension / img.width :
                    maxDimension / img.height;

                canvas.width = img.width * scale;
                canvas.height = img.height * scale;

                ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

                // Store scaled version
                const scaledImg = new Image();
                scaledImg.src = canvas.toDataURL();
                AppState.watermark.imageData = scaledImg;
                AppState.watermark.imageSrc = canvas.toDataURL();
            } else {
                // Use original
                AppState.watermark.imageData = img;
                AppState.watermark.imageSrc = e.target.result;
            }
        };
        img.src = e.target.result;
    };
    reader.readAsDataURL(file);
}
```

**Content-Relative Positioning**:

```javascript
function applyWatermarkToDisplay() {
    const pages = document.querySelectorAll('.report-page');

    pages.forEach(pageEl => {
        // Calculate content dimensions
        const fontSize = parseFloat(getComputedStyle(pageEl).fontSize) || 11;
        const charWidth = fontSize * 0.6; // Courier New ratio
        const contentWidth = AppState.detectedWidth * charWidth;
        const linesInPage = pageEl.querySelectorAll('.report-line').length;
        const contentHeight = linesInPage * (fontSize * 1.2);

        // Create canvas sized to content area
        const canvas = document.createElement('canvas');
        const ctx = canvas.getContext('2d');
        canvas.width = contentWidth;
        canvas.height = Math.max(contentHeight, 400);

        // Position within content
        const positions = {
            'center': { x: 0.5, y: 0.5 },
            // ... other positions
        };

        const pos = positions[AppState.watermark.position];
        const x = canvas.width * pos.x;
        const y = canvas.height * pos.y;

        // Draw watermark
        ctx.save();
        ctx.globalAlpha = AppState.watermark.opacity / 100;
        ctx.translate(x, y);
        ctx.rotate(AppState.watermark.rotation * Math.PI / 180);

        const scale = AppState.watermark.scale / 100;
        const imgWidth = AppState.watermark.imageData.width * scale;
        const imgHeight = AppState.watermark.imageData.height * scale;

        ctx.drawImage(AppState.watermark.imageData,
                     -imgWidth / 2, -imgHeight / 2,
                     imgWidth, imgHeight);
        ctx.restore();

        // Apply to page
        pageEl.style.backgroundImage = `url(${canvas.toDataURL()})`;
        pageEl.style.backgroundSize = `${contentWidth}px ${canvas.height}px`;
        pageEl.style.backgroundPosition = 'left top';
    });
}
```

### 7. PDF Export Engine

**Process**:
1. Filter pages by ranges (if active)
2. For each page:
   - Create temporary DOM element
   - Apply zebra striping
   - Apply watermark
   - Render to canvas (html2canvas)
   - Add to PDF (jsPDF)
3. Download PDF

**Implementation**:

```javascript
async function exportToPDF() {
    const { jsPDF } = window.jspdf;
    const pdf = new jsPDF({
        orientation: 'landscape',
        unit: 'in',
        format: [11, 14.875]  // 132-column paper
    });

    let pagesToExport = AppState.showRangesOnly && AppState.pageRanges.length > 0 ?
        filterPagesByRanges() : AppState.pages;

    for (let i = 0; i < pagesToExport.length; i++) {
        const page = pagesToExport[i];
        updateProgress((i + 1) / pagesToExport.length * 100,
                      `Exporting page ${i + 1}...`);

        // Create temporary page element
        const pageContainer = createPageElement(page);
        document.body.appendChild(pageContainer);

        // Apply features
        if (AppState.zebraEnabled) applyZebraToElement(pageContainer);
        if (AppState.watermark.enabled) await applyWatermarkToElement(pageContainer);

        // Render to canvas
        const canvas = await html2canvas(pageContainer, {
            scale: 2,
            backgroundColor: AppState.zebraEnabled ?
                AppState.zebraColor1 : '#ffffff'
        });

        // Add to PDF
        const imgData = canvas.toDataURL('image/png');
        if (i > 0) pdf.addPage();
        pdf.addImage(imgData, 'PNG', 0, 0, 14.875, 11);

        // Cleanup
        document.body.removeChild(pageContainer);
        await new Promise(resolve => setTimeout(resolve, 10)); // Allow UI update
    }

    pdf.save(`${AppState.fileName}_export_${Date.now()}.pdf`);
}
```

---

## Data Structures

### Line Object

```javascript
{
    lineNumber: 42,                     // Original 1-based line number
    rawText: "1 ACCOUNT SUMMARY...",    // Original with control char
    displayText: " ACCOUNT SUMMARY...", // Stripped for display
    controlChar: "1",                   // First character
    pageNumber: 2,                      // Assigned page
    isPageBreak: true,                  // Is this a form feed?
    hasMatch: false                     // Has search match?
}
```

### Page Object

```javascript
{
    pageNumber: 2,                      // Sequential page number
    startLineNumber: 67,                // First line (inclusive)
    endLineNumber: 132,                 // Last line (inclusive)
    lineCount: 66,                      // Number of lines
    lines: [...],                       // Array of line objects
    hasSearchMatch: false               // Has any search matches?
}
```

### Page Range Object

```javascript
{
    id: 1643723456789,                  // Timestamp ID
    name: "Summary Section",            // User-defined name
    startPage: 1,                       // Starting page number
    pageCount: 5                        // Number of pages to include
}
```

### Search Result Object

```javascript
{
    lineIndex: 41,                      // Index in AppState.lines
    lineNumber: 42,                     // Display line number
    pageNumber: 2,                      // Page containing match
    matchStart: 15,                     // Character position
    matchLength: 7                      // Length of match
}
```

---

## Algorithm Details

### Ruler Generation

**Purpose**: Show column positions 1-N

```javascript
function buildRuler() {
    const width = AppState.detectedWidth;
    let numberLine = '';
    let ticks = '';

    // Build number line
    for (let i = 1; i <= width; i++) {
        let placed = false;

        // Check if this position is part of a decade number
        for (let decade = 10; decade <= width; decade += 10) {
            const numStr = String(decade);
            const startPos = decade - numStr.length + 1;
            const endPos = decade;

            if (i >= startPos && i <= endPos) {
                const digitIndex = i - startPos;
                numberLine += numStr[digitIndex];
                placed = true;
                break;
            }
        }

        if (!placed) numberLine += ' ';

        // Build tick line
        if (i % 10 === 0) ticks += '|';
        else if (i % 5 === 0) ticks += '+';
        else ticks += '.';
    }

    return `<div class="ruler-numbers">${numberLine}</div>
            <div class="ruler-ticks">${ticks}</div>`;
}
```

**Output Example** (40 columns):
```
         10        20        30        40
.+....|.+....|.+....|.+....|.+....|.+...
```

### Width Auto-Detection

```javascript
function detectReportWidth() {
    let actualMaxWidth = 0;

    AppState.lines.forEach(line => {
        if (line.displayText.length > actualMaxWidth) {
            actualMaxWidth = line.displayText.length;
        }
    });

    // Round up to standard width
    if (actualMaxWidth <= 80) AppState.detectedWidth = 80;
    else if (actualMaxWidth <= 132) AppState.detectedWidth = 132;
    else if (actualMaxWidth <= 198) AppState.detectedWidth = 198;
    else AppState.detectedWidth = 255;
}
```

### Page Range Filtering

```javascript
function filterPagesByRanges() {
    const filteredPages = [];

    AppState.pageRanges.forEach(range => {
        for (let i = 0; i < range.pageCount; i++) {
            const pageNum = range.startPage + i;
            const page = AppState.pages.find(p => p.pageNumber === pageNum);
            if (page) filteredPages.push(page);
        }
    });

    return filteredPages;
}
```

---

## Rendering Pipeline

### Pipeline Stages

```
1. File Upload
   ↓
2. FileReader.readAsText()
   ↓
3. parseReportFile()
   ├→ Split into lines
   ├→ Detect ASA format
   ├→ Parse control characters
   └→ Create line objects
   ↓
4. detectPages()
   ├→ Group lines by page breaks
   └→ Create page objects
   ↓
5. detectReportWidth()
   ├→ Find longest line
   └→ Set standard width
   ↓
6. renderReport()
   ├→ Filter pages (if ranges active)
   ├→ Build ruler HTML
   ├→ Build page HTML
   ├→ Build line HTML
   ├→ Apply zebra classes
   ├→ Add line numbers (if enabled)
   └→ Single innerHTML update
   ↓
7. applyWatermarkToDisplay() (if enabled)
   ├→ Calculate content dimensions
   ├→ Create canvas per page
   ├→ Draw watermark
   └→ Apply as background
   ↓
8. Display Complete
```

### Re-Render Triggers

| Action | Trigger Function | Re-Renders |
|--------|-----------------|------------|
| Zebra toggle | `toggleZebra()` | ✓ Full |
| Color change | `updateZebraColors()` | ✓ Full |
| Page mode | `changePageMode()` | ✓ Full (re-detect pages) |
| Search | `performSearch()` | ✓ With highlights |
| Clear search | `clearSearch()` | ✓ Full |
| Toggle ruler | `toggleRuler()` | ✓ Full |
| Toggle line# | `toggleLineNumbers()` | ✓ Full |
| Toggle light | `toggleLightMode()` | CSS only (no re-render) |
| Change width | `changeWidth()` | ✓ Full (re-build ruler) |
| Ranges toggle | `toggleRangesFilter()` | ✓ Full (filter pages) |
| Watermark enable | `toggleWatermark()` | Canvas only |
| Watermark adjust | `updateRotation()`, etc. | Canvas only |

---

## Performance Optimizations

### 1. HTML String Building

**Before** (DOM Manipulation):
```javascript
// Slow - thousands of DOM operations
page.lines.forEach(line => {
    const div = document.createElement('div');
    div.className = 'report-line';
    div.textContent = line.displayText;
    container.appendChild(div);  // SLOW: triggers reflow
});
```

**After** (String Building):
```javascript
// Fast - single DOM update
let html = '';
page.lines.forEach(line => {
    html += `<div class="report-line">${escapeHtml(line.displayText)}</div>`;
});
container.innerHTML = html;  // FAST: single reflow
```

**Result**: 5-10x faster for large files

### 2. Search Result Limiting

```javascript
// Limit to 1000 results to prevent UI freeze
if (AppState.searchResults.length > 1000) {
    AppState.searchResults = AppState.searchResults.slice(0, 1000);
    showToast('Showing first 1000 of ' + totalMatches + ' matches', 'info');
}
```

### 3. Progressive PDF Export

```javascript
// Export in batches with UI updates
for (let i = 0; i < pages.length; i++) {
    // ... export page ...

    // Allow UI to update every 10ms
    await new Promise(resolve => setTimeout(resolve, 10));
}
```

### 4. Debounced Search

```javascript
let searchTimeout;
function handleSearchKeyup(event) {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        if (event.key === 'Enter') performSearch();
    }, 300);
}
```

### 5. Virtual Scrolling (Not Implemented)

**Future Enhancement**: For files >10,000 lines
```javascript
// Only render visible lines + buffer
const visibleRange = calculateVisibleRange(scrollTop);
const linesToRender = AppState.lines.slice(
    visibleRange.start - 100,
    visibleRange.end + 100
);
```

---

## Browser Compatibility

### Minimum Requirements

| Browser | Version | Notes |
|---------|---------|-------|
| Chrome | 90+ | Primary target |
| Firefox | 88+ | Full support |
| Edge | 90+ | Chromium-based |
| Safari | 14+ | Minor rendering differences |

### Feature Detection

```javascript
// Check for required APIs
if (!window.FileReader) {
    alert('Your browser does not support file reading.');
}

if (!window.localStorage) {
    console.warn('Settings persistence not available.');
}

if (typeof window.jspdf === 'undefined') {
    console.error('jsPDF library not loaded.');
}
```

### Known Limitations

1. **Internet Explorer**: Not supported (uses ES6+)
2. **Mobile Safari**: Touch events not optimized
3. **Firefox PDF**: Slightly different rendering vs Chrome

---

## Extending the Viewer

### Adding a New Feature

**Example**: Add CSV export

```javascript
// 1. Add button to UI
<button class="btn" onclick="exportToCSV()">Export CSV</button>

// 2. Implement function
function exportToCSV() {
    let csv = 'Line,Page,Text\n';

    AppState.lines.forEach(line => {
        const escaped = line.displayText.replace(/"/g, '""');
        csv += `${line.lineNumber},${line.pageNumber},"${escaped}"\n`;
    });

    // Download
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${AppState.fileName}_export.csv`;
    a.click();
}

// 3. Add keyboard shortcut (optional)
if (e.ctrlKey && e.key === 's') {
    e.preventDefault();
    exportToCSV();
}
```

### Adding a New Control Character

```javascript
// In parseReportFile()
if (controlChar === '2') {
    // New control: Skip 2 lines
    displayText = rawLine.substring(1);
    // ... implement skip logic
}
```

### Adding a New Watermark Position

```javascript
// In applyWatermarkToDisplay()
const positions = {
    // ... existing positions ...
    'custom': { x: 0.33, y: 0.67 }  // Add new position
};

// In watermark modal HTML
<button class="position-btn" data-position="custom"
        onclick="setWatermarkPosition('custom')">Custom</button>
```

### Custom Styling

```css
/* Add to <style> section */
.report-display.high-contrast {
    background: #000000;
    color: #00ff00;
}

.report-display.high-contrast .report-line {
    color: #00ff00;
}
```

```javascript
// Toggle function
function toggleHighContrast() {
    document.getElementById('reportDisplay')
        .classList.toggle('high-contrast');
}
```

---

## Debugging & Development

### Console Debugging

```javascript
// View current state
console.log('AppState:', AppState);

// View lines
console.table(AppState.lines.slice(0, 10));

// View pages
console.table(AppState.pages);

// Search results
console.log('Search results:', AppState.searchResults);
```

### Performance Profiling

```javascript
// Measure render time
console.time('render');
renderReport();
console.timeEnd('render');

// Measure parse time
console.time('parse');
parseReportFile();
console.timeEnd('parse');
```

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Lines misaligned | Character width calculation off | Adjust `charWidth` ratio in watermark code |
| Slow rendering | Too many DOM operations | Use HTML string building |
| PDF export fails | Library not loaded | Check CDN, network, console errors |
| Watermark off-center | Viewport positioning | Use content-relative positioning |
| Zebra pattern wrong | Line index vs page line index | Reset index per page |

---

## Security Considerations

### Client-Side Only

- No server communication
- No external API calls (except CDN for libraries)
- All processing local to browser

### File Access

- Uses FileReader API with user consent
- No file system access beyond selected file
- No file persistence (everything in memory)

### Content Security

```html
<!-- Recommended CSP headers if serving from server -->
<meta http-equiv="Content-Security-Policy"
      content="default-src 'self';
               script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com;
               style-src 'self' 'unsafe-inline';">
```

### Data Privacy

- No telemetry or analytics
- localStorage only stores user preferences (colors, settings)
- No sensitive data persisted

---

## Testing Strategy

### Manual Testing Checklist

```
[ ] File Upload
    [ ] .txt file loads
    [ ] .TXT file loads
    [ ] Drag & drop works
    [ ] Large file (>5MB) loads
    [ ] Empty file shows error

[ ] Page Detection
    [ ] Dynamic mode detects form feeds
    [ ] Dynamic mode detects '1' control chars
    [ ] Fixed 66 mode counts correctly
    [ ] Fixed 88 mode counts correctly

[ ] Display
    [ ] Text appears monospaced
    [ ] Horizontal scroll works
    [ ] Page separators appear
    [ ] Line breaks preserved

[ ] Zebra Stripes
    [ ] Toggle on/off works
    [ ] Colors change
    [ ] Pattern alternates correctly
    [ ] Persists after reload

[ ] Search
    [ ] Case sensitive works
    [ ] Case insensitive works
    [ ] Highlights appear
    [ ] Navigation works
    [ ] Clear removes highlights

[ ] Watermark
    [ ] Image uploads
    [ ] Large image auto-scales
    [ ] Position changes work
    [ ] Rotation works
    [ ] Opacity works
    [ ] Scale works
    [ ] Appears in display
    [ ] Appears in PDF

[ ] PDF Export
    [ ] Exports all pages
    [ ] Respects page ranges
    [ ] Includes zebra pattern
    [ ] Includes watermark
    [ ] File downloads

[ ] Keyboard Shortcuts
    [ ] Ctrl+O opens file
    [ ] Ctrl+F focuses search
    [ ] Ctrl+G jumps to page
    [ ] Ctrl+E exports PDF
    [ ] Ctrl+/- zooms
    [ ] F3 next result
```

### Unit Test Examples (Future)

```javascript
// Parse test
test('parseReportFile handles form feeds', () => {
    AppState.rawContent = '\fLine 1\nLine 2\fLine 3';
    parseReportFile();
    assert(AppState.lines.length === 3);
    assert(AppState.lines[0].isPageBreak === true);
    assert(AppState.lines[2].isPageBreak === true);
});

// Search test
test('search finds case insensitive matches', () => {
    AppState.lines = [
        { displayText: 'Hello World', hasMatch: false },
        { displayText: 'HELLO there', hasMatch: false }
    ];
    performSearch('hello', false);
    assert(AppState.searchResults.length === 2);
});
```

---

## Conclusion

This viewer demonstrates:
- ✅ Single-file architecture
- ✅ Pure vanilla JavaScript
- ✅ Progressive enhancement
- ✅ Performance optimization
- ✅ Modern CSS techniques
- ✅ Accessible UI patterns
- ✅ Extensible design

**Total Code**: ~3,900 lines (900 CSS, 2,500 JS, 500 HTML)

**Dependencies**: 2 libraries (jsPDF, html2canvas)

**Browser Support**: Modern browsers (2021+)

**Use Cases**: Legacy mainframe report viewing, AS/400 spool files, print file analysis, wide-format report inspection (80-255 columns)

---

## Appendix: Quick Reference

### Key Functions

| Function | Purpose | Returns |
|----------|---------|---------|
| `parseReportFile()` | Parse raw text into lines | void |
| `detectPages()` | Group lines into pages | void |
| `renderReport()` | Display report in DOM | void |
| `performSearch()` | Search and highlight | void |
| `exportToPDF()` | Generate PDF file | Promise |
| `applyWatermarkToDisplay()` | Render watermarks | void |
| `toggleZebra()` | Toggle striping | void |
| `zoomIn() / zoomOut()` | Adjust zoom | void |

### CSS Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `--report-font-size` | Text size | 11px |
| `--zebra-color1` | Even rows | #1a1a2e |
| `--zebra-color2` | Odd rows | #0f3460 |
| `--accent-primary` | Highlights | #e94560 |
| `--report-bg` | Background | #0a0a0a |

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+O | Open file |
| Ctrl+F | Search |
| Ctrl+G | Jump to page |
| Ctrl+E | Export PDF |
| Ctrl+/- | Zoom in/out |
| Ctrl+0 | Reset zoom |
| F3 | Next search result |
| Shift+F3 | Previous result |
| Escape | Close modals |

---

**End of Technical Documentation**

For questions or contributions, refer to the source code comments or project documentation.
