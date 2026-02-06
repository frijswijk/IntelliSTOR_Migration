# Spec: IRPT-Viewer — PDF/AFP Binary Object Support

## Version: 2.0
## Date: 2026-02-06
## Status: Proposed

---

## 1. Overview

Extend the IRPT-Viewer (`IRPT_Viewer.html`) to detect, extract, and display embedded binary objects (PDF and AFP documents) found inside `.RPT` files. When an RPT file contains binary objects, the viewer should:

1. **Detect** the BPAGETBLHDR structure and binary object count during RPT loading
2. **Show** a visual indicator in the toolbar that binary content is present
3. **Provide** a button to open the extracted PDF in a new browser tab
4. **Provide** a download option for AFP files (which browsers cannot natively render)
5. **Display** the Object Header page as readable metadata (not raw binary)

---

## 2. Current Architecture (Relevant Parts)

The viewer already parses RPT files client-side using:

- `parseRptHeader(data)` → reads RPTFILEHDR, Table Directory Row 0 and Row 1
- `readPageTable(data, pageCount)` → reads PAGETBLHDR entries (24 bytes each)
- `readSectionHdr(data, header)` → reads SECTIONHDR entries (12 bytes each)
- `decompressPage(data, entry)` → zlib decompression via `pako.inflate()`
- `AppState.rptData` → holds the full `Uint8Array` of the RPT file

**What's missing**: Table Directory Row 2 (BPAGETBLHDR reference), binary page table parsing, binary object decompression/assembly, and UI for viewing/downloading binary content.

---

## 3. Data Model Changes

### 3.1 AppState Extensions

```javascript
// Add to AppState object:
rptBinaryEntries: [],       // Array of {index, pageOffset, absoluteOffset, uncompressedSize, compressedSize}
rptBinaryType: null,        // 'pdf' | 'afp' | null
rptBinaryBlob: null,        // Blob object of assembled binary document
rptBinaryFilename: null,    // Filename from Object Header (e.g., "HKCIF001_016_20280309.PDF")
rptObjectHeader: null,      // Parsed Object Header key-value pairs {key: value, ...}
rptHasBinary: false         // Quick flag: does this RPT contain binary objects?
```

### 3.2 Binary Object Entry Structure

```javascript
// Each entry in rptBinaryEntries:
{
    index: 1,                  // 1-based
    pageOffset: 0x1234,        // Relative to RPTINSTHDR
    absoluteOffset: 0x1324,    // pageOffset + 0xF0
    uncompressedSize: 45678,   // Decompressed chunk size
    compressedSize: 12345      // zlib stream size in file
}
```

---

## 4. Parsing Changes

### 4.1 `parseRptHeader()` — Read Table Directory Row 2

Add reading of the binary object count from offset 0x1F4:

```javascript
function parseRptHeader(data) {
    // ... existing code ...

    // NEW: Read Table Directory Row 2 (BPAGETBLHDR reference)
    const binaryType = view.getUint32(0x1F0, true);      // 0x00010103 if binary present
    const binaryObjectCount = view.getUint32(0x1F4, true);
    const binaryTableOffset = view.getUint32(0x1F8, true);

    return {
        // ... existing fields ...
        binaryObjectCount,        // NEW
        binaryTableOffset         // NEW
    };
}
```

### 4.2 New: `readBinaryPageTable(data, count)`

```javascript
function readBinaryPageTable(data, count) {
    // Search for 'BPAGETBLHDR' marker (11 bytes)
    // Search near end of file first (after PAGETBLHDR), then full scan
    const markerPos = findMarker(data, 'BPAGETBLHDR', Math.max(0, data.length - 4096), data.length);
    if (markerPos === -1) return [];

    const entryStart = markerPos + 13;  // 11-byte marker + 2 null bytes
    const entrySize = 16;
    const view = new DataView(data.buffer, data.byteOffset);
    const entries = [];

    for (let i = 0; i < count; i++) {
        const offset = entryStart + i * entrySize;
        if (offset + entrySize > data.length) break;
        entries.push({
            index: i + 1,
            pageOffset: view.getUint32(offset, true),
            absoluteOffset: view.getUint32(offset, true) + RPTINSTHDR_OFFSET,
            uncompressedSize: view.getUint32(offset + 8, true),
            compressedSize: view.getUint32(offset + 12, true)
        });
    }
    return entries;
}
```

### 4.3 New: `decompressBinaryObjects(data, entries)`

```javascript
function decompressBinaryObjects(data, entries) {
    const chunks = [];
    for (const entry of entries) {
        const compressed = data.slice(entry.absoluteOffset, entry.absoluteOffset + entry.compressedSize);
        try {
            const decompressed = pako.inflate(compressed);
            chunks.push(decompressed);
        } catch (e) {
            console.error(`Binary object ${entry.index} decompression failed:`, e);
            return null;
        }
    }
    return chunks;
}
```

### 4.4 New: `assembleBinaryDocument(chunks)`

```javascript
function assembleBinaryDocument(chunks) {
    // Concatenate all decompressed chunks into one Uint8Array
    const totalSize = chunks.reduce((sum, c) => sum + c.length, 0);
    const result = new Uint8Array(totalSize);
    let offset = 0;
    for (const chunk of chunks) {
        result.set(chunk, offset);
        offset += chunk.length;
    }
    return result;
}
```

### 4.5 New: `detectBinaryType(binaryData, objectHeader)`

```javascript
function detectBinaryType(binaryData, objectHeader) {
    // Check magic bytes
    if (binaryData.length >= 4) {
        const magic = String.fromCharCode(...binaryData.slice(0, 5));
        if (magic.startsWith('%PDF')) return 'pdf';
    }
    if (binaryData.length >= 1 && binaryData[0] === 0x5A) return 'afp';

    // Fallback: check Object Header filename extension
    if (objectHeader && objectHeader['Object File Name']) {
        const name = objectHeader['Object File Name'].toUpperCase();
        if (name.endsWith('.PDF')) return 'pdf';
        if (name.endsWith('.AFP')) return 'afp';
    }
    return 'unknown';
}
```

### 4.6 New: `parseObjectHeader(pageText)`

```javascript
function parseObjectHeader(pageText) {
    const prefix = 'StorQM PLUS Object Header Page:';
    if (!pageText || !pageText.startsWith(prefix)) return null;

    const result = {};
    const lines = pageText.split(/\r?\n/);
    for (const line of lines) {
        const colonPos = line.indexOf(':');
        if (colonPos > 0 && colonPos < line.length - 1) {
            const key = line.substring(0, colonPos).trim();
            const value = line.substring(colonPos + 1).trim();
            if (key && value && key !== prefix.replace(':', '')) {
                result[key] = value;
            }
        }
    }
    return result;
}
```

---

## 5. Loading Flow Changes

### 5.1 Update `loadRptFile()`

After existing page table loading, add binary detection:

```javascript
function loadRptFile(file, arrayBuffer) {
    // ... existing code (header, sections, page table) ...

    // NEW: Binary object detection and loading
    AppState.rptBinaryEntries = [];
    AppState.rptBinaryType = null;
    AppState.rptBinaryBlob = null;
    AppState.rptBinaryFilename = null;
    AppState.rptObjectHeader = null;
    AppState.rptHasBinary = false;

    if (header.binaryObjectCount > 0) {
        AppState.rptHasBinary = true;

        // Read binary page table
        const binaryEntries = readBinaryPageTable(data, header.binaryObjectCount);
        AppState.rptBinaryEntries = binaryEntries;

        if (binaryEntries.length > 0) {
            // Parse Object Header from page 1
            const page1Text = decompressPage(data, pageEntries[0]);
            if (page1Text) {
                AppState.rptObjectHeader = parseObjectHeader(page1Text);
            }

            // Decompress and assemble binary document
            const chunks = decompressBinaryObjects(data, binaryEntries);
            if (chunks) {
                const assembled = assembleBinaryDocument(chunks);
                const type = detectBinaryType(assembled, AppState.rptObjectHeader);
                AppState.rptBinaryType = type;

                // Determine filename
                let filename = file.name.replace(/\.RPT$/i, '');
                if (AppState.rptObjectHeader && AppState.rptObjectHeader['Object File Name']) {
                    filename = AppState.rptObjectHeader['Object File Name'];
                } else {
                    filename += (type === 'pdf' ? '.pdf' : type === 'afp' ? '.afp' : '.bin');
                }
                AppState.rptBinaryFilename = filename;

                // Create Blob for viewing/download
                const mimeType = type === 'pdf' ? 'application/pdf' : 'application/octet-stream';
                AppState.rptBinaryBlob = new Blob([assembled], { type: mimeType });
            }
        }
    }

    // ... rest of existing code ...
}
```

---

## 6. UI Changes

### 6.1 Toolbar: Binary Indicator Button

Add a new button next to the existing `rptSectionsBtn`:

```html
<button class="tool-btn" id="rptBinaryBtn"
    onclick="openBinaryDocument()"
    title="Open embedded PDF/AFP document"
    style="display:none; font-size: 11px; padding: 4px 8px; white-space: nowrap;">
    📎 PDF
</button>
```

**Placement**: Between `rptSectionsBtn` and the Settings button (`⚙️`).

**Visibility rules**:
- Hidden by default (`display: none`)
- Shown only when `AppState.rptHasBinary === true`
- Button text changes based on type: `📎 PDF` or `📎 AFP` or `📎 BIN`

### 6.2 RPT Section Modal: Binary Info Panel

Add a binary information section to the existing RPT Section Modal (`rptSectionModal`):

```html
<!-- Inside rptSectionModal .modal-body, after rptInfoPanel -->
<div id="rptBinaryPanel" style="display:none; margin-bottom: 16px; padding: 12px;
     background: var(--bg-tertiary); border-radius: 6px; font-size: 13px;
     color: var(--text-primary); border-left: 3px solid var(--accent-primary);">
    <div style="font-weight: bold; margin-bottom: 8px;">📎 Embedded Binary Document</div>
    <div><strong>Type:</strong> <span id="rptBinaryTypeLabel">-</span></div>
    <div><strong>Filename:</strong> <span id="rptBinaryFilenameLabel">-</span></div>
    <div><strong>Size:</strong> <span id="rptBinarySizeLabel">-</span></div>
    <div><strong>Chunks:</strong> <span id="rptBinaryChunkCount">-</span></div>
    <div id="rptObjectHeaderInfo" style="margin-top: 8px; display: none;">
        <strong>Object Header:</strong>
        <pre id="rptObjectHeaderText" style="margin: 4px 0 0 0; font-size: 12px;
             white-space: pre-wrap; color: var(--text-secondary);"></pre>
    </div>
    <div style="margin-top: 12px; display: flex; gap: 8px;">
        <button class="btn" id="rptBinaryOpenBtn" onclick="openBinaryDocument()">
            🔗 Open in New Tab
        </button>
        <button class="btn" id="rptBinaryDownloadBtn" onclick="downloadBinaryDocument()">
            💾 Download
        </button>
    </div>
</div>
```

### 6.3 Footer: Binary Metadata

Extend the existing RPT metadata line in the footer:

```
RPT: Species 52759 | Domain 1 | 2028/03/09 09:15:22 | 📎 PDF (85.2 KB)
```

### 6.4 Object Header Page Display

When displaying page 1 (which is the Object Header), add a subtle visual indicator:

```css
.object-header-page {
    border-left: 3px solid var(--accent-primary);
    background: linear-gradient(90deg, rgba(233, 69, 96, 0.05) 0%, transparent 10%);
}

.object-header-badge {
    display: inline-block;
    background: var(--accent-primary);
    color: white;
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 10px;
    font-weight: bold;
    margin-left: 8px;
    vertical-align: middle;
}
```

In the page rendering logic, when a page is detected as the Object Header:

```javascript
// In the page rendering section, check if this is the Object Header page
if (AppState.rptHasBinary && pageIdx === 0 && AppState.rptObjectHeader) {
    // Add 'object-header-page' CSS class to the page container
    // Add badge: <span class="object-header-badge">OBJECT HEADER</span>
}
```

---

## 7. User Actions

### 7.1 `openBinaryDocument()` — Open PDF in New Tab

```javascript
function openBinaryDocument() {
    if (!AppState.rptBinaryBlob) {
        showToast('No binary document available', 'error');
        return;
    }

    if (AppState.rptBinaryType === 'pdf') {
        // PDF: open in new browser tab using Object URL
        const url = URL.createObjectURL(AppState.rptBinaryBlob);
        const newTab = window.open(url, '_blank');
        if (!newTab) {
            showToast('Pop-up blocked. Please allow pop-ups for this page.', 'error');
        } else {
            showToast(`Opened ${AppState.rptBinaryFilename} in new tab`, 'success');
        }
        // Note: URL.revokeObjectURL should be called after tab loads,
        // but timing is tricky. Revoke after 60 seconds as safety net.
        setTimeout(() => URL.revokeObjectURL(url), 60000);

    } else if (AppState.rptBinaryType === 'afp') {
        // AFP: browsers cannot render AFP natively, offer download instead
        showToast('AFP files cannot be viewed in browser. Downloading instead...', 'info');
        downloadBinaryDocument();

    } else {
        // Unknown: download
        showToast('Unknown binary format. Downloading...', 'info');
        downloadBinaryDocument();
    }
}
```

### 7.2 `downloadBinaryDocument()` — Download Binary File

```javascript
function downloadBinaryDocument() {
    if (!AppState.rptBinaryBlob) {
        showToast('No binary document available', 'error');
        return;
    }

    const url = URL.createObjectURL(AppState.rptBinaryBlob);
    const a = document.createElement('a');
    a.href = url;
    a.download = AppState.rptBinaryFilename || 'binary_document';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast(`Downloaded ${AppState.rptBinaryFilename}`, 'success');
}
```

---

## 8. UI State Updates

### 8.1 `updateStatusBar()` — Extend for Binary

```javascript
// In updateStatusBar(), after existing RPT metadata display:
const binaryBtn = document.getElementById('rptBinaryBtn');
if (binaryBtn) {
    if (AppState.rptHasBinary && AppState.rptBinaryBlob) {
        binaryBtn.style.display = 'inline-block';
        const typeLabel = (AppState.rptBinaryType || 'BIN').toUpperCase();
        binaryBtn.textContent = `📎 ${typeLabel}`;
        binaryBtn.title = `Open embedded ${typeLabel}: ${AppState.rptBinaryFilename}`;
    } else {
        binaryBtn.style.display = 'none';
    }
}

// Extend RPT metadata in footer
if (AppState.fileType === 'RPT' && AppState.rptHeader) {
    const h = AppState.rptHeader;
    let metaText = `Species ${h.speciesId} | Domain ${h.domainId} | ${h.timestamp}`;
    if (AppState.rptHasBinary && AppState.rptBinaryBlob) {
        const sizeKB = (AppState.rptBinaryBlob.size / 1024).toFixed(1);
        metaText += ` | 📎 ${(AppState.rptBinaryType || 'BIN').toUpperCase()} (${sizeKB} KB)`;
    }
    document.getElementById('rptMetadata').textContent = metaText;
}
```

### 8.2 `openRptSectionModal()` — Extend for Binary Panel

```javascript
// In openRptSectionModal(), after existing section table population:
const binaryPanel = document.getElementById('rptBinaryPanel');
if (binaryPanel) {
    if (AppState.rptHasBinary) {
        binaryPanel.style.display = 'block';
        document.getElementById('rptBinaryTypeLabel').textContent =
            (AppState.rptBinaryType || 'Unknown').toUpperCase();
        document.getElementById('rptBinaryFilenameLabel').textContent =
            AppState.rptBinaryFilename || '-';
        document.getElementById('rptBinarySizeLabel').textContent =
            AppState.rptBinaryBlob
                ? `${(AppState.rptBinaryBlob.size / 1024).toFixed(1)} KB`
                : '-';
        document.getElementById('rptBinaryChunkCount').textContent =
            AppState.rptBinaryEntries.length;

        // Object Header details
        const ohInfo = document.getElementById('rptObjectHeaderInfo');
        if (AppState.rptObjectHeader && Object.keys(AppState.rptObjectHeader).length > 0) {
            ohInfo.style.display = 'block';
            const lines = Object.entries(AppState.rptObjectHeader)
                .map(([k, v]) => `${k}: ${v}`)
                .join('\n');
            document.getElementById('rptObjectHeaderText').textContent = lines;
        } else {
            ohInfo.style.display = 'none';
        }

        // Enable/disable open button based on type
        const openBtn = document.getElementById('rptBinaryOpenBtn');
        if (AppState.rptBinaryType === 'pdf') {
            openBtn.disabled = false;
            openBtn.textContent = '🔗 Open PDF in New Tab';
        } else if (AppState.rptBinaryType === 'afp') {
            openBtn.disabled = true;
            openBtn.textContent = '🔗 AFP (not viewable in browser)';
            openBtn.title = 'AFP format cannot be rendered by browsers. Use the Download button instead.';
        } else {
            openBtn.disabled = true;
            openBtn.textContent = '🔗 Unknown format';
        }
    } else {
        binaryPanel.style.display = 'none';
    }
}
```

### 8.3 File Reset — Clear Binary State

```javascript
// In the text file loading path (when clearing RPT state):
AppState.rptBinaryEntries = [];
AppState.rptBinaryType = null;
AppState.rptBinaryBlob = null;
AppState.rptBinaryFilename = null;
AppState.rptObjectHeader = null;
AppState.rptHasBinary = false;
```

---

## 9. Toast Notifications

| Event | Message | Type |
|-------|---------|------|
| RPT loaded with binary | `RPT loaded! 2 pages, 1 section, 📎 PDF (85.2 KB)` | success |
| PDF opened in new tab | `Opened HKCIF001.PDF in new tab` | success |
| AFP download triggered | `AFP files cannot be viewed in browser. Downloading instead...` | info |
| Binary download complete | `Downloaded HKCIF001.PDF` | success |
| Pop-up blocked | `Pop-up blocked. Please allow pop-ups for this page.` | error |
| Binary decompression failed | `Failed to extract binary document from RPT` | error |
| No binary in RPT | `This RPT file does not contain binary objects` | info |

---

## 10. Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `B` | Open binary document (PDF → new tab, AFP → download) |
| `Shift+B` | Download binary document |

Add to the existing keyboard event handler:

```javascript
// In the keydown handler:
case 'b':
    if (!e.shiftKey && AppState.rptHasBinary) {
        e.preventDefault();
        openBinaryDocument();
    } else if (e.shiftKey && AppState.rptHasBinary) {
        e.preventDefault();
        downloadBinaryDocument();
    }
    break;
```

---

## 11. Drag & Drop Enhancement

Update the file input `accept` attribute and drag/drop handler to also accept `.pdf` and `.afp` files when used standalone (not embedded in RPT):

```html
<input type="file" id="fileInput" accept=".rpt,.RPT,.txt,.TXT,.pdf,.PDF,.afp,.AFP" ...>
```

**Note**: When a standalone PDF is dropped/opened, the viewer should simply open it in a new tab (since the viewer is a text viewer, not a PDF viewer). This is a convenience shortcut.

---

## 12. Airgap Version

The `IRPT-Viewer-Airgap.html` version must also receive these changes. Since it bundles `pako.min.js` inline, no additional dependencies are needed for binary decompression. The `URL.createObjectURL()` API works offline.

---

## 13. Theme Support

All new UI elements must respect the existing three themes:

| Element | Dark | Light | High Contrast |
|---------|------|-------|---------------|
| Binary button | Default toolbar styling | Default | Green border, green text |
| Binary panel border-left | `var(--accent-primary)` | Same | `#00ff00` |
| Object Header badge | `var(--accent-primary)` bg, white text | Same | Green bg, black text |
| Object Header pre text | `var(--text-secondary)` | Same | `#00ff00` |

---

## 14. Performance Considerations

- **Lazy binary extraction**: Binary objects should be decompressed and assembled **on first access** (when user clicks the binary button or opens the Section modal), not during initial RPT load. This keeps the initial load fast.
- **Memory**: The assembled binary Blob should be created once and cached in `AppState.rptBinaryBlob`. Subsequent opens/downloads reuse the same Blob.
- **Large binaries**: Some PDFs could be several MB. The `Blob` + `URL.createObjectURL()` approach handles this efficiently without base64 encoding overhead.
- **Object URL cleanup**: Revoke Object URLs after use (60-second timeout for new-tab opens, immediate for downloads).

**Alternative (eager loading)**: If the binary is small (< 1 MB, which is typical for these reports), eager loading during `loadRptFile()` is acceptable and simplifies the code. The spec above uses eager loading for simplicity. Switch to lazy if performance testing shows issues.

---

## 15. Testing Checklist

- [ ] Load text-only RPT (`260271NL.RPT`) → no binary button, no binary panel, no errors
- [ ] Load binary RPT (`260271Q7.RPT`) → binary button appears with `📎 PDF`
- [ ] Click binary button → PDF opens in new browser tab, renders correctly
- [ ] Open Section modal → binary panel shows: PDF, filename, size, chunk count
- [ ] Object Header displayed in binary panel with key-value pairs
- [ ] Download button → PDF file downloads with correct filename
- [ ] Page 1 (Object Header) shows visual badge indicator
- [ ] Press `B` key → opens PDF in new tab
- [ ] Press `Shift+B` → downloads PDF
- [ ] All three themes render correctly (dark, light, high contrast)
- [ ] Load a .txt file after an RPT → binary state fully cleared
- [ ] Load another RPT after a binary RPT → binary state correctly updated
- [ ] Airgap version works identically
- [ ] AFP RPT file (if available) → shows `📎 AFP`, open button disabled, download works

---

## 16. Implementation Priority

1. **Phase 1** (Core): `parseRptHeader` update, `readBinaryPageTable`, `decompressBinaryObjects`, `assembleBinaryDocument`, `detectBinaryType` — the data pipeline
2. **Phase 2** (UI): Binary button in toolbar, `openBinaryDocument()`, `downloadBinaryDocument()` — the user-facing actions
3. **Phase 3** (Polish): Section modal binary panel, Object Header display, page badge, footer metadata, keyboard shortcuts
4. **Phase 4** (Airgap): Port all changes to `IRPT-Viewer-Airgap.html`

Estimated effort: ~200 lines of JavaScript, ~40 lines of HTML, ~20 lines of CSS.
