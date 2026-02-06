#!/usr/bin/env node
/**
 * rpt_page_extractor.js - Decompress and extract pages from IntelliSTOR .RPT files
 *
 * Node.js port of rpt_page_extractor.py + rpt_section_reader.py (standalone, no deps).
 *
 * Extracts page content from RPT files using the PAGETBLHDR for fast random access.
 * Pages are decompressed from individual zlib streams and saved as .txt files.
 * Also extracts embedded binary objects (PDF/AFP) tracked by the BPAGETBLHDR structure.
 *
 * Supports:
 *   - Full extraction: all pages from one or more RPT files
 *   - Page range:      --pages 10-20 (extract pages 10 through 20)
 *   - Section-based:   --section-id 14259 (extract only pages belonging to that section)
 *   - Multi-section:   --section-id 14259 14260 14261 (multiple sections, in order)
 *   - Folder mode:     --folder <dir> (process all RPT files in a directory)
 *   - Binary objects:  --binary-only (extract only PDF/AFP), --no-binary (skip binary)
 *
 * RPT File Layout (reference):
 *   [0x000] RPTFILEHDR     - Header with domain:species, timestamp
 *   [0x0F0] RPTINSTHDR     - Instance metadata (base offset for page_offset)
 *   [0x1D0] Table Directory (3 rows x 12 bytes):
 *           Row 0 (0x1D0): type=0x0102  count=page_count    offset -> PAGETBLHDR
 *           Row 1 (0x1E0): type=0x0101  count=section_count  offset -> SECTIONHDR
 *           Row 2 (0x1F0): type=0x0103  count=binary_count   offset -> BPAGETBLHDR
 *   [0x200] COMPRESSED DATA - per-page zlib streams + interleaved binary object streams
 *   [...]   SECTIONHDR     - section triplets (SECTION_ID, START_PAGE, PAGE_COUNT)
 *   [...]   PAGETBLHDR     - 24-byte entries per page (offset, size, dimensions)
 *   [...]   BPAGETBLHDR    - 16-byte entries per binary object (PDF/AFP, if present)
 *
 * PAGETBLHDR Entry Format (24 bytes, little-endian):
 *   [page_offset:4]        - Byte offset relative to RPTINSTHDR (add 0xF0 for absolute)
 *   [pad:4]                - Reserved (always 0)
 *   [line_width:2]         - Max characters per line on this page
 *   [lines_per_page:2]     - Number of lines on this page
 *   [uncompressed_size:4]  - Decompressed page data size in bytes
 *   [compressed_size:4]    - zlib stream size in bytes
 *   [pad:4]                - Reserved (always 0)
 *
 * BPAGETBLHDR Entry Format (16 bytes, little-endian):
 *   [page_offset:4]        - Byte offset relative to RPTINSTHDR (add 0xF0 for absolute)
 *   [reserved:4]           - Always 0
 *   [uncompressed_size:4]  - Decompressed data size in bytes
 *   [compressed_size:4]    - zlib stream size in bytes
 */

'use strict';

const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

// ============================================================================
// Constants
// ============================================================================

const RPTINSTHDR_OFFSET = 0xF0; // Base offset for page_offset values

// ============================================================================
// Data Structures
// ============================================================================

/**
 * Parsed RPT file header metadata.
 */
class RptHeader {
    constructor({ domainId, reportSpeciesId, timestamp, pageCount, sectionCount, sectionDataOffset, pageTableOffset, binaryObjectCount }) {
        this.domainId = domainId;
        this.reportSpeciesId = reportSpeciesId;
        this.timestamp = timestamp;
        this.pageCount = pageCount;
        this.sectionCount = sectionCount;
        this.sectionDataOffset = sectionDataOffset;
        this.pageTableOffset = pageTableOffset;
        this.binaryObjectCount = binaryObjectCount || 0;
    }
}

/**
 * One SECTIONHDR triplet.
 */
class SectionEntry {
    constructor(sectionId, startPage, pageCount) {
        this.sectionId = sectionId;
        this.startPage = startPage;
        this.pageCount = pageCount;
    }
}

/**
 * One PAGETBLHDR entry -- metadata for a single page.
 */
class PageTableEntry {
    constructor({ pageNumber, pageOffset, lineWidth, linesPerPage, uncompressedSize, compressedSize }) {
        this.pageNumber = pageNumber;       // 1-based page number
        this.pageOffset = pageOffset;       // Offset relative to RPTINSTHDR
        this.lineWidth = lineWidth;         // Max characters per line
        this.linesPerPage = linesPerPage;   // Number of lines on this page
        this.uncompressedSize = uncompressedSize;
        this.compressedSize = compressedSize;
    }

    /** Absolute file offset to the start of the zlib stream. */
    get absoluteOffset() {
        return this.pageOffset + RPTINSTHDR_OFFSET;
    }
}

/**
 * One BPAGETBLHDR entry -- metadata for an embedded binary object (PDF/AFP).
 */
class BinaryObjectEntry {
    constructor({ index, pageOffset, uncompressedSize, compressedSize }) {
        this.index = index;                 // 1-based index
        this.pageOffset = pageOffset;       // Offset relative to RPTINSTHDR
        this.uncompressedSize = uncompressedSize;
        this.compressedSize = compressedSize;
    }

    /** Absolute file offset to the start of the zlib stream. */
    get absoluteOffset() {
        return this.pageOffset + RPTINSTHDR_OFFSET;
    }
}

// ============================================================================
// RPT Header Parsing (ported from rpt_section_reader.py)
// ============================================================================

/**
 * Parse RPT file header to extract metadata and table directory offsets.
 *
 * @param {Buffer} data - First ~512 bytes of the RPT file
 * @returns {RptHeader|null} Parsed header, or null if not a valid RPT file
 */
function parseRptHeader(data) {
    // Check RPTFILEHDR signature
    const sig = data.slice(0, 10).toString('ascii');
    if (sig !== 'RPTFILEHDR') {
        return null;
    }

    // Find end of header line (terminated by 0x1A or null)
    let headerEnd = data.indexOf(0x1A);
    if (headerEnd === -1) {
        headerEnd = data.indexOf(0x00);
    }
    if (headerEnd === -1) {
        headerEnd = 192; // fallback
    }

    const headerLine = data.slice(0, headerEnd).toString('ascii');
    const parts = headerLine.split('\t');

    let domainId = 0;
    let speciesId = 0;
    let timestamp = '';

    if (parts.length >= 2) {
        const idPart = parts[1];
        if (idPart.includes(':')) {
            const [d, s] = idPart.split(':', 2);
            const dInt = parseInt(d, 10);
            const sInt = parseInt(s, 10);
            if (!isNaN(dInt)) domainId = dInt;
            if (!isNaN(sInt)) speciesId = sInt;
        }
    }

    if (parts.length >= 3) {
        timestamp = parts[2].trim();
    }

    // Table Directory at 0x1D0
    let pageCount = 0;
    let sectionCount = 0;
    let sectionDataOffset = 0;
    let pageTableOffset = 0;
    let binaryObjectCount = 0;

    if (data.length >= 0x1F0) {
        pageCount = data.readUInt32LE(0x1D4);
        sectionCount = data.readUInt32LE(0x1E4);
        const compressedDataEnd = data.readUInt32LE(0x1E8);
        sectionDataOffset = compressedDataEnd; // approximate; actual scan in readSectionhdr
    }

    // Table Directory Row 2 at 0x1F0: type=0x0103, count=binary_count
    if (data.length >= 0x200) {
        binaryObjectCount = data.readUInt32LE(0x1F4);
    }

    return new RptHeader({
        domainId,
        reportSpeciesId: speciesId,
        timestamp,
        pageCount,
        sectionCount,
        sectionDataOffset,
        pageTableOffset,
        binaryObjectCount,
    });
}

// ============================================================================
// SECTIONHDR Reading (ported from rpt_section_reader.py)
// ============================================================================

/**
 * Read SECTIONHDR from an RPT file.
 *
 * Extracts section-to-page mapping without decompressing any page data.
 *
 * @param {string} filepath - Path to .RPT file
 * @returns {{ header: RptHeader|null, sections: SectionEntry[] }}
 */
function readSectionhdr(filepath) {
    const fileSize = fs.statSync(filepath).size;
    const sections = [];

    const fd = fs.openSync(filepath, 'r');
    try {
        // Read header (first 512 bytes)
        const headerBuf = Buffer.alloc(0x200);
        const headerBytesRead = fs.readSync(fd, headerBuf, 0, 0x200, 0);
        const headerData = headerBuf.slice(0, headerBytesRead);

        const header = parseRptHeader(headerData);
        if (header === null) {
            return { header: null, sections: [] };
        }

        // Strategy 1: Targeted scan near compressed_data_end offset
        if (header.sectionDataOffset > 0) {
            const scanStart = Math.max(0, header.sectionDataOffset - 16);
            const scanLen = Math.min(4096, fileSize - scanStart);
            const regionBuf = Buffer.alloc(scanLen);
            fs.readSync(fd, regionBuf, 0, scanLen, scanStart);

            const markerStr = 'SECTIONHDR';
            const markerPos = regionBuf.indexOf(markerStr, 0, 'ascii');

            if (markerPos !== -1) {
                const absPos = scanStart + markerPos;
                const dataStart = markerPos + 13; // skip "SECTIONHDR" + 3 null bytes
                const count = header.sectionCount > 0 ? header.sectionCount : 1000;
                const needed = count * 12;

                let tripletData;
                if (dataStart + needed <= regionBuf.length) {
                    tripletData = regionBuf.slice(dataStart, dataStart + needed);
                } else {
                    // Re-read from file
                    tripletData = Buffer.alloc(needed);
                    fs.readSync(fd, tripletData, 0, needed, absPos + 13);
                }

                const actual = Math.min(Math.floor(tripletData.length / 12), count);
                for (let i = 0; i < actual; i++) {
                    const offset = i * 12;
                    const sid = tripletData.readUInt32LE(offset);
                    const sp = tripletData.readUInt32LE(offset + 4);
                    const pc = tripletData.readUInt32LE(offset + 8);

                    if (sp >= 1 && pc >= 1) {
                        sections.push(new SectionEntry(sid, sp, pc));
                    } else if (sid === 0 && sp === 0 && pc === 0) {
                        break; // all-zero triplet = end of valid data
                    }
                }

                if (sections.length > 0) {
                    header.sectionCount = sections.length;
                    return { header, sections };
                }
            }
        }

        // Strategy 2: Full file scan for SECTIONHDR marker (fallback)
        const fullData = Buffer.alloc(fileSize);
        fs.readSync(fd, fullData, 0, fileSize, 0);

        const markerPos2 = fullData.indexOf('SECTIONHDR', 0, 'ascii');
        if (markerPos2 === -1) {
            return { header, sections: [] };
        }

        const dataStart2 = markerPos2 + 13;
        const endDataPos = fullData.indexOf('ENDDATA', dataStart2, 'ascii');
        let sectionBytes;
        if (endDataPos === -1) {
            sectionBytes = fullData.slice(dataStart2);
        } else {
            sectionBytes = fullData.slice(dataStart2, endDataPos);
        }

        const numTriplets = Math.floor(sectionBytes.length / 12);
        for (let i = 0; i < numTriplets; i++) {
            const offset = i * 12;
            if (offset + 12 > sectionBytes.length) break;
            const sid = sectionBytes.readUInt32LE(offset);
            const sp = sectionBytes.readUInt32LE(offset + 4);
            const pc = sectionBytes.readUInt32LE(offset + 8);
            if (sp >= 1 && pc >= 1) {
                sections.push(new SectionEntry(sid, sp, pc));
            }
        }
        header.sectionCount = sections.length;

        return { header, sections };
    } finally {
        fs.closeSync(fd);
    }
}

// ============================================================================
// PAGETBLHDR Parsing
// ============================================================================

/**
 * Read PAGETBLHDR entries from an RPT file.
 *
 * Uses scan to find the PAGETBLHDR marker, then reads
 * pageCount x 24-byte entries.
 *
 * @param {string} filepath - Path to .RPT file
 * @param {number} pageCount - Number of pages (from header Table Directory)
 * @returns {PageTableEntry[]}
 */
function readPageTable(filepath, pageCount) {
    const entries = [];
    const data = fs.readFileSync(filepath);

    const ptPos = data.indexOf('PAGETBLHDR', 0, 'ascii');
    if (ptPos === -1) {
        return entries;
    }

    // Skip marker (10 bytes) + 3 null padding bytes = 13 bytes
    const entryStart = ptPos + 13;
    const entrySize = 24;

    for (let i = 0; i < pageCount; i++) {
        const offset = entryStart + i * entrySize;
        if (offset + entrySize > data.length) break;

        const pageOffset = data.readUInt32LE(offset);
        // skip pad at offset+4
        const lineWidth = data.readUInt16LE(offset + 8);
        const linesPerPage = data.readUInt16LE(offset + 10);
        const uncompressedSize = data.readUInt32LE(offset + 12);
        const compressedSize = data.readUInt32LE(offset + 16);

        entries.push(new PageTableEntry({
            pageNumber: i + 1,
            pageOffset,
            lineWidth,
            linesPerPage,
            uncompressedSize,
            compressedSize,
        }));
    }

    return entries;
}

// ============================================================================
// Page Decompression
// ============================================================================

/**
 * Decompress multiple pages from the RPT file.
 *
 * Opens the file once and reads all requested pages for efficiency.
 *
 * @param {string} filepath - Path to .RPT file
 * @param {PageTableEntry[]} entries - Page table entries to decompress
 * @returns {{ pageNumber: number, data: Buffer }[]}
 */
function decompressPages(filepath, entries) {
    const results = [];
    const fileSize = fs.statSync(filepath).size;
    const fd = fs.openSync(filepath, 'r');

    try {
        for (const entry of entries) {
            const absOffset = entry.absoluteOffset;
            if (absOffset + entry.compressedSize > fileSize) {
                process.stderr.write(
                    `  WARNING: Page ${entry.pageNumber} offset 0x${absOffset.toString(16).toUpperCase()} ` +
                    `exceeds file size ${fileSize.toLocaleString()}\n`
                );
                continue;
            }

            const compressed = Buffer.alloc(entry.compressedSize);
            fs.readSync(fd, compressed, 0, entry.compressedSize, absOffset);

            try {
                const pageData = zlib.inflateSync(compressed);
                results.push({ pageNumber: entry.pageNumber, data: pageData });
            } catch (e) {
                // Try with extra bytes (some streams may need more)
                try {
                    const extraBuf = Buffer.alloc(entry.compressedSize + 64);
                    fs.readSync(fd, extraBuf, 0, Math.min(entry.compressedSize + 64, fileSize - absOffset), absOffset);
                    const pageData = zlib.inflateSync(extraBuf);
                    results.push({ pageNumber: entry.pageNumber, data: pageData });
                } catch (e2) {
                    process.stderr.write(
                        `  WARNING: Page ${entry.pageNumber} decompression failed: ${e2.message}\n`
                    );
                }
            }
        }
    } finally {
        fs.closeSync(fd);
    }

    return results;
}

// ============================================================================
// BPAGETBLHDR Parsing
// ============================================================================

/**
 * Read BPAGETBLHDR entries from an RPT file.
 *
 * Scans for the BPAGETBLHDR marker and reads count x 16-byte entries
 * describing embedded binary objects (PDF/AFP documents).
 *
 * @param {string} filepath - Path to .RPT file
 * @param {number} count - Number of binary objects (from header Table Directory Row 2)
 * @returns {BinaryObjectEntry[]}
 */
function readBinaryPageTable(filepath, count) {
    const entries = [];
    if (count <= 0) return entries;

    const data = fs.readFileSync(filepath);

    const bpPos = data.indexOf('BPAGETBLHDR', 0, 'ascii');
    if (bpPos === -1) return entries;

    // Skip marker (11 bytes) + 2 null padding bytes = 13 bytes
    const entryStart = bpPos + 13;
    const entrySize = 16;

    for (let i = 0; i < count; i++) {
        const offset = entryStart + i * entrySize;
        if (offset + entrySize > data.length) break;

        const pageOffset = data.readUInt32LE(offset);
        // skip reserved at offset+4
        const uncompressedSize = data.readUInt32LE(offset + 8);
        const compressedSize = data.readUInt32LE(offset + 12);

        entries.push(new BinaryObjectEntry({
            index: i + 1,
            pageOffset,
            uncompressedSize,
            compressedSize,
        }));
    }

    return entries;
}

// ============================================================================
// Object Header Detection
// ============================================================================

const OBJECT_HEADER_PREFIX = 'StorQM PLUS Object Header Page:';

/**
 * Parse an Object Header page to extract embedded document metadata.
 *
 * Object Header pages start with "StorQM PLUS Object Header Page:" and contain
 * key-value pairs describing the embedded binary document (filename, timestamps,
 * PDF/AFP creator info, etc.).
 *
 * @param {Buffer} pageContent - Decompressed text page content
 * @returns {Object|null} dict with metadata key-value pairs, or null if not an Object Header page
 */
function parseObjectHeader(pageContent) {
    let text;
    try {
        text = pageContent.toString('ascii');
    } catch (e) {
        return null;
    }

    if (!text.includes(OBJECT_HEADER_PREFIX)) {
        return null;
    }

    const metadata = {};
    for (const line of text.split(/\r?\n/)) {
        const trimmed = line.trim();
        if (trimmed.includes(':') && !trimmed.startsWith(OBJECT_HEADER_PREFIX)) {
            const colonIdx = trimmed.indexOf(':');
            const key = trimmed.slice(0, colonIdx).trim();
            const value = trimmed.slice(colonIdx + 1).trim();
            if (key && value) {
                metadata[key] = value;
            }
        }
    }

    return metadata;
}

/**
 * Detect the format of a binary object from its magic bytes.
 *
 * @param {Buffer} data - First bytes of the decompressed binary object
 * @param {Object|null} objectHeader - Optional Object Header metadata (for filename extension fallback)
 * @returns {string} File extension string (e.g. '.pdf', '.afp', '.bin')
 */
function detectBinaryType(data, objectHeader) {
    // Check for PDF magic bytes
    if (data.length >= 4 && data.slice(0, 4).toString('ascii') === '%PDF') {
        return '.pdf';
    }

    // AFP: Begin Structured Field Introducer starts with 0x5A
    if (data.length >= 1 && data[0] === 0x5A) {
        return '.afp';
    }

    // Fallback: use Object Header's "Object File Name" extension if available
    if (objectHeader) {
        const objFilename = objectHeader['Object File Name'] || '';
        if (objFilename.includes('.')) {
            const ext = objFilename.split('.').pop().toLowerCase();
            if (ext === 'pdf' || ext === 'afp') {
                return `.${ext}`;
            }
        }
    }

    return '.bin';
}

// ============================================================================
// Binary Object Decompression and Assembly
// ============================================================================

/**
 * Decompress binary object zlib streams from the RPT file.
 *
 * Opens the file once and reads all binary object entries for efficiency.
 *
 * @param {string} filepath - Path to .RPT file
 * @param {BinaryObjectEntry[]} entries - Binary object entries to decompress
 * @returns {{ index: number, data: Buffer }[]}
 */
function decompressBinaryObjects(filepath, entries) {
    const results = [];
    const fileSize = fs.statSync(filepath).size;
    const fd = fs.openSync(filepath, 'r');

    try {
        for (const entry of entries) {
            const absOffset = entry.absoluteOffset;
            if (absOffset + entry.compressedSize > fileSize) {
                process.stderr.write(
                    `  WARNING: Binary object ${entry.index} offset 0x${absOffset.toString(16).toUpperCase()} ` +
                    `exceeds file size ${fileSize.toLocaleString()}\n`
                );
                continue;
            }

            const compressed = Buffer.alloc(entry.compressedSize);
            fs.readSync(fd, compressed, 0, entry.compressedSize, absOffset);

            try {
                const objData = zlib.inflateSync(compressed);
                results.push({ index: entry.index, data: objData });
            } catch (e) {
                process.stderr.write(
                    `  WARNING: Binary object ${entry.index} decompression failed: ${e.message}\n`
                );
            }
        }
    } finally {
        fs.closeSync(fd);
    }

    return results;
}

/**
 * Assemble decompressed binary objects into a single document.
 *
 * Binary objects from an RPT file concatenate to form a complete document
 * (e.g., a multi-part PDF or AFP file).
 *
 * @param {{ index: number, data: Buffer }[]} objects - Decompressed binary objects, in order
 * @param {Object|null} objectHeader - Optional Object Header metadata (for filename and type detection)
 * @param {string} rptName - RPT filename stem (for fallback naming)
 * @returns {{ combined: Buffer, filename: string, formatDesc: string }}
 */
function assembleBinaryDocument(objects, objectHeader, rptName) {
    // Concatenate all objects in order
    const combined = Buffer.concat(objects.map(o => o.data));

    // Detect format from magic bytes
    const ext = detectBinaryType(combined, objectHeader);

    // Determine filename
    let filename;
    if (objectHeader && objectHeader['Object File Name']) {
        filename = objectHeader['Object File Name'].trim();
    } else {
        filename = `${rptName}_binary${ext}`;
    }

    // Format description
    const formatMap = { '.pdf': 'PDF', '.afp': 'AFP', '.bin': 'Binary' };
    const formatDesc = formatMap[ext] || 'Binary';

    return { combined, filename, formatDesc };
}

// ============================================================================
// Page Selection
// ============================================================================

/**
 * Select page table entries for a page range (inclusive, 1-based).
 */
function selectPagesByRange(entries, startPage, endPage) {
    return entries.filter(e => e.pageNumber >= startPage && e.pageNumber <= endPage);
}

/**
 * Select page table entries for multiple sections, preserving the requested order.
 *
 * Pages are collected in the order of sectionIds provided. Sections that
 * are not found are silently skipped.
 *
 * @param {PageTableEntry[]} entries
 * @param {SectionEntry[]} sections
 * @param {number[]} sectionIds
 * @returns {{ selected: PageTableEntry[], foundIds: number[], skippedIds: number[] }}
 */
function selectPagesBySections(entries, sections, sectionIds) {
    const sectionMap = new Map();
    for (const s of sections) {
        sectionMap.set(s.sectionId, s);
    }

    const selected = [];
    const foundIds = [];
    const skippedIds = [];

    for (const sid of sectionIds) {
        if (!sectionMap.has(sid)) {
            skippedIds.push(sid);
            continue;
        }
        foundIds.push(sid);
        const section = sectionMap.get(sid);
        const start = section.startPage;
        const end = section.startPage + section.pageCount - 1;
        selected.push(...selectPagesByRange(entries, start, end));
    }

    return { selected, foundIds, skippedIds };
}

// ============================================================================
// Output
// ============================================================================

/**
 * Recursively create directories (like mkdir -p).
 */
function mkdirp(dir) {
    fs.mkdirSync(dir, { recursive: true });
}

/**
 * Save decompressed pages as .txt files.
 *
 * @param {{ pageNumber: number, data: Buffer }[]} pages
 * @param {string} outputDir
 * @param {string} pagePrefix
 * @returns {number} Number of pages saved
 */
function savePages(pages, outputDir, pagePrefix = 'page') {
    mkdirp(outputDir);
    let saved = 0;

    for (const { pageNumber, data } of pages) {
        const filename = `${pagePrefix}_${String(pageNumber).padStart(5, '0')}.txt`;
        const filepath = path.join(outputDir, filename);
        fs.writeFileSync(filepath, data);
        saved++;
    }

    return saved;
}

// ============================================================================
// Number formatting helper
// ============================================================================

/**
 * Format a number with comma separators.
 */
function formatNumber(n) {
    return n.toLocaleString('en-US');
}

// ============================================================================
// Main Extraction
// ============================================================================

/**
 * Decompress a single page from the RPT file (for Object Header detection).
 *
 * @param {string} filepath - Path to .RPT file
 * @param {PageTableEntry} entry - PageTableEntry with offset and size info
 * @returns {Buffer|null} Decompressed page content, or null on error
 */
function decompressPage(filepath, entry) {
    const absOffset = entry.absoluteOffset;
    const fd = fs.openSync(filepath, 'r');

    try {
        const compressed = Buffer.alloc(entry.compressedSize);
        fs.readSync(fd, compressed, 0, entry.compressedSize, absOffset);

        try {
            return zlib.inflateSync(compressed);
        } catch (e) {
            // Try with extra bytes
            const fileSize = fs.statSync(filepath).size;
            const extraBuf = Buffer.alloc(Math.min(entry.compressedSize + 64, fileSize - absOffset));
            fs.readSync(fd, extraBuf, 0, extraBuf.length, absOffset);
            try {
                return zlib.inflateSync(extraBuf);
            } catch (e2) {
                return null;
            }
        }
    } finally {
        fs.closeSync(fd);
    }
}

/**
 * Extract pages from a single RPT file.
 *
 * When the RPT file contains embedded binary objects (PDF/AFP), the default behavior
 * extracts both text pages and the binary document as separate files. Use binaryOnly
 * or noBinary to control this behavior.
 *
 * @param {string} filepath - Path to .RPT file
 * @param {string} outputBase - Base directory for output
 * @param {object} options
 * @param {[number,number]|null} options.pageRange - [start, end] page range (1-based, inclusive)
 * @param {number[]|null} options.sectionIds - SECTION_IDs to extract (in order, skips missing)
 * @param {boolean} options.infoOnly - Show info without extracting
 * @param {boolean} options.binaryOnly - Extract only the binary document (skip text pages)
 * @param {boolean} options.noBinary - Extract only text pages (skip binary objects)
 * @returns {object} Extraction statistics
 */
function extractRpt(filepath, outputBase, { pageRange = null, sectionIds = null, infoOnly = false, binaryOnly = false, noBinary = false } = {}) {
    const stats = {
        file: filepath,
        pagesTotal: 0,
        pagesSelected: 0,
        pagesExtracted: 0,
        bytesCompressed: 0,
        bytesDecompressed: 0,
        binaryObjects: 0,
        binaryFilename: null,
        binarySize: 0,
        error: null,
    };

    // Read header
    const headerBuf = Buffer.alloc(0x200);
    const fd = fs.openSync(filepath, 'r');
    let headerBytesRead;
    try {
        headerBytesRead = fs.readSync(fd, headerBuf, 0, 0x200, 0);
    } finally {
        fs.closeSync(fd);
    }
    const header = parseRptHeader(headerBuf.slice(0, headerBytesRead));
    if (header === null) {
        stats.error = 'Not a valid RPT file (no RPTFILEHDR signature)';
        return stats;
    }

    stats.pagesTotal = header.pageCount;
    const rptName = path.basename(filepath, path.extname(filepath));

    // Read page table
    const pageEntries = readPageTable(filepath, header.pageCount);
    if (pageEntries.length === 0) {
        stats.error = 'No PAGETBLHDR found';
        return stats;
    }

    // Read sections (needed for --section-id and info display)
    const { sections } = readSectionhdr(filepath);

    // Read binary object table (if present)
    let binaryEntries = [];
    if (header.binaryObjectCount > 0) {
        binaryEntries = readBinaryPageTable(filepath, header.binaryObjectCount);
    }

    // Parse Object Header from text page 1 (if binary objects exist)
    let objectHeader = null;
    if (binaryEntries.length > 0 && pageEntries.length > 0) {
        const firstPage = decompressPage(filepath, pageEntries[0]);
        if (firstPage) {
            objectHeader = parseObjectHeader(firstPage);
        }
    }

    // Display info
    console.log('');
    console.log('='.repeat(70));
    console.log(`File: ${filepath}`);
    console.log(`  Species: ${header.reportSpeciesId}, Domain: ${header.domainId}`);
    console.log(`  Timestamp: ${header.timestamp}`);
    console.log(`  Pages: ${header.pageCount}, Sections: ${header.sectionCount}`);
    if (header.binaryObjectCount > 0) {
        console.log(`  Binary Objects: ${header.binaryObjectCount}`);
    }

    const totalComp = pageEntries.reduce((sum, e) => sum + e.compressedSize, 0);
    const totalUncomp = pageEntries.reduce((sum, e) => sum + e.uncompressedSize, 0);
    if (totalComp > 0) {
        const ratio = (totalUncomp / totalComp).toFixed(1);
        console.log(`  Compressed: ${formatNumber(totalComp)} bytes -> Uncompressed: ${formatNumber(totalUncomp)} bytes (${ratio}x)`);
    }

    // Collect all requested section IDs for marker display
    const requestedSids = new Set(sectionIds || []);

    if (sections.length > 0) {
        console.log(`\n  Sections (${sections.length}):`);
        console.log(`  ${'SECTION_ID'.padStart(12)}  ${'START_PAGE'.padStart(10)}  ${'PAGE_COUNT'.padStart(10)}`);
        console.log(`  ${'-'.repeat(12)}  ${'-'.repeat(10)}  ${'-'.repeat(10)}`);
        for (const s of sections) {
            const marker = requestedSids.has(s.sectionId) ? ' <--' : '';
            console.log(
                `  ${String(s.sectionId).padStart(12)}  ${String(s.startPage).padStart(10)}  ${String(s.pageCount).padStart(10)}${marker}`
            );
        }
    }

    if (infoOnly) {
        // Show page table sample
        console.log(`\n  Page Table (first 5 / last 5):`);
        console.log(`  ${'PAGE'.padStart(6)}  ${'OFFSET'.padStart(10)}  ${'WIDTH'.padStart(6)}  ${'LINES'.padStart(6)}  ${'UNCOMP'.padStart(8)}  ${'COMP'.padStart(8)}`);

        let show;
        if (pageEntries.length <= 10) {
            show = [...pageEntries];
        } else {
            show = [...pageEntries.slice(0, 5), null, ...pageEntries.slice(-5)];
        }

        for (const e of show) {
            if (e === null) {
                console.log(`  ${'...'.padStart(6)}`);
                continue;
            }
            const offsetHex = '0x' + e.absoluteOffset.toString(16).toUpperCase().padStart(8, '0');
            console.log(
                `  ${String(e.pageNumber).padStart(6)}  ${offsetHex}  ${String(e.lineWidth).padStart(6)}  ` +
                `${String(e.linesPerPage).padStart(6)}  ${formatNumber(e.uncompressedSize).padStart(8)}  ${formatNumber(e.compressedSize).padStart(8)}`
            );
        }

        // Show binary object table if present
        if (binaryEntries.length > 0) {
            console.log(`\n  Binary Objects (${binaryEntries.length}):  [BPAGETBLHDR]`);
            console.log(`  ${'INDEX'.padStart(7)}  ${'OFFSET'.padStart(10)}  ${'UNCOMP_SIZE'.padStart(11)}  ${'COMP_SIZE'.padStart(10)}`);
            console.log(`  ${'-'.repeat(7)}  ${'-'.repeat(10)}  ${'-'.repeat(11)}  ${'-'.repeat(10)}`);
            for (const be of binaryEntries) {
                const offsetHex = '0x' + be.absoluteOffset.toString(16).toUpperCase().padStart(8, '0');
                console.log(
                    `  ${String(be.index).padStart(7)}  ${offsetHex}  ` +
                    `${formatNumber(be.uncompressedSize).padStart(11)}  ${formatNumber(be.compressedSize).padStart(10)}`
                );
            }

            if (objectHeader) {
                console.log(`\n  Object Header:`);
                for (const [key, value] of Object.entries(objectHeader)) {
                    console.log(`    ${key}: ${value}`);
                }
            }

            // Show assembled document info
            const binObjs = decompressBinaryObjects(filepath, binaryEntries);
            if (binObjs.length > 0) {
                const { combined, filename, formatDesc } = assembleBinaryDocument(
                    binObjs, objectHeader, rptName);
                console.log(`\n  Assembled document: ${formatDesc} (${formatNumber(combined.length)} bytes)`);
                console.log(`  Output filename: ${filename}`);
            }
        }

        return stats;
    }

    // Select pages to extract
    let selected = pageEntries; // default: all pages
    let foundIds = null;

    if (sectionIds !== null && sectionIds.length > 0) {
        const result = selectPagesBySections(pageEntries, sections, sectionIds);
        selected = result.selected;
        foundIds = result.foundIds;
        const skippedIds = result.skippedIds;

        if (skippedIds.length > 0) {
            console.log(`\n  Skipped (not found): ${skippedIds.join(', ')}`);
        }
        if (foundIds.length === 0) {
            stats.error = 'None of the requested section IDs found in SECTIONHDR';
            console.log(`\n  ERROR: ${stats.error}`);
            if (sections.length > 0) {
                const availableIds = sections.slice(0, 20).map(s => s.sectionId).join(', ');
                console.log(`  Available section IDs: ${availableIds}`);
            }
            return stats;
        }

        const sectionMap = new Map();
        for (const s of sections) {
            sectionMap.set(s.sectionId, s);
        }
        for (const sid of foundIds) {
            const si = sectionMap.get(sid);
            console.log(
                `\n  Extracting section ${sid}: ` +
                `pages ${si.startPage}-${si.startPage + si.pageCount - 1} ` +
                `(${si.pageCount} pages)`
            );
        }
        const totalSectionPages = foundIds.reduce((sum, sid) => sum + sectionMap.get(sid).pageCount, 0);
        console.log(`\n  Total: ${foundIds.length} section(s), ${totalSectionPages} pages`);

    } else if (pageRange !== null) {
        let [startP, endP] = pageRange;
        // Clamp to valid range
        startP = Math.max(1, startP);
        endP = Math.min(header.pageCount, endP);
        selected = selectPagesByRange(pageEntries, startP, endP);
        console.log(`\n  Extracting page range: ${startP}-${endP} (${selected.length} pages)`);
    } else {
        console.log(`\n  Extracting all ${header.pageCount} pages`);
    }

    // Determine output directory
    let outputDir;
    if (sectionIds !== null && foundIds !== null && foundIds.length > 0) {
        if (foundIds.length === 1) {
            outputDir = path.join(outputBase, rptName, `section_${foundIds[0]}`);
        } else {
            const label = foundIds.join('_');
            outputDir = path.join(outputBase, rptName, `sections_${label}`);
        }
    } else if (pageRange !== null) {
        outputDir = path.join(outputBase, rptName, `pages_${pageRange[0]}-${pageRange[1]}`);
    } else {
        outputDir = path.join(outputBase, rptName);
    }

    stats.pagesSelected = selected.length;

    // -------------------------------------------------------------------
    // Extract text pages (unless --binary-only)
    // -------------------------------------------------------------------
    if (!binaryOnly) {
        // Filter out Object Header page when binary objects are present
        let textSelected = selected;
        if (binaryEntries.length > 0 && objectHeader && selected.length > 0) {
            // Object Header is text page 1 -- skip it from regular text output
            textSelected = selected.filter(e => e.pageNumber !== 1);
            if (textSelected.length !== selected.length) {
                console.log(`  Object Header page (page 1) separated from text output`);
            }
        }

        if (textSelected.length > 0) {
            const pages = decompressPages(filepath, textSelected);
            stats.pagesExtracted = pages.length;
            stats.bytesCompressed = textSelected.reduce((sum, e) => sum + e.compressedSize, 0);
            stats.bytesDecompressed = pages.reduce((sum, p) => sum + p.data.length, 0);

            const saved = savePages(pages, outputDir, 'page');
            console.log(`  Saved ${saved} text pages to ${outputDir}/`);
            console.log(`  Total decompressed: ${formatNumber(stats.bytesDecompressed)} bytes`);

            // Check for failures
            const failed = textSelected.length - stats.pagesExtracted;
            if (failed > 0) {
                console.log(`  WARNING: ${failed} pages failed to decompress`);
            }
        }

        // Save Object Header as separate file (for reference)
        if (binaryEntries.length > 0 && objectHeader) {
            const firstPage = decompressPage(filepath, pageEntries[0]);
            if (firstPage) {
                mkdirp(outputDir);
                const ohPath = path.join(outputDir, 'object_header.txt');
                fs.writeFileSync(ohPath, firstPage);
                console.log(`  Saved object_header.txt to ${outputDir}/`);
            }
        }
    } else {
        if (binaryEntries.length === 0) {
            stats.error = 'No binary objects found in this RPT file (--binary-only requires BPAGETBLHDR)';
            console.log(`\n  ERROR: ${stats.error}`);
            return stats;
        }
    }

    // -------------------------------------------------------------------
    // Extract binary objects (unless --no-binary)
    // -------------------------------------------------------------------
    if (!noBinary && binaryEntries.length > 0) {
        const binObjs = decompressBinaryObjects(filepath, binaryEntries);
        if (binObjs.length > 0) {
            const { combined, filename, formatDesc } = assembleBinaryDocument(
                binObjs, objectHeader, rptName);

            mkdirp(outputDir);
            const binPath = path.join(outputDir, filename);
            fs.writeFileSync(binPath, combined);

            stats.binaryObjects = binObjs.length;
            stats.binaryFilename = filename;
            stats.binarySize = combined.length;

            console.log(`  Saved ${formatDesc} document: ${filename} (${formatNumber(combined.length)} bytes) to ${outputDir}/`);
        } else {
            console.log(`  WARNING: Binary objects found but all decompression failed`);
        }
    }

    return stats;
}

// ============================================================================
// CLI Argument Parsing
// ============================================================================

/**
 * Parse a page range string like '10-20' or '5'.
 * @param {string} s
 * @returns {[number, number]}
 */
function parsePageRange(s) {
    if (s.includes('-')) {
        const parts = s.split('-', 2);
        return [parseInt(parts[0], 10), parseInt(parts[1], 10)];
    }
    const n = parseInt(s, 10);
    return [n, n];
}

/**
 * Recursively find all .RPT files in a directory.
 * @param {string} dir
 * @returns {string[]}
 */
function findRptFiles(dir) {
    const results = [];

    function walk(currentDir) {
        let entries;
        try {
            entries = fs.readdirSync(currentDir, { withFileTypes: true });
        } catch (e) {
            return;
        }
        for (const entry of entries) {
            const fullPath = path.join(currentDir, entry.name);
            if (entry.isDirectory()) {
                walk(fullPath);
            } else if (entry.isFile() && entry.name.toUpperCase().endsWith('.RPT')) {
                results.push(fullPath);
            }
        }
    }

    walk(dir);
    return results.sort();
}

/**
 * Print usage/help text.
 */
function printHelp() {
    console.log(`Usage: node rpt_page_extractor.js [options] <rptfile...>

Extract and decompress pages from IntelliSTOR .RPT files.

Options:
  --info                Show RPT file info and page table without extracting
  --pages <range>       Page range to extract (e.g., "10-20", "5") -- 1-based, inclusive
  --section-id <id...>  Extract pages belonging to one or more SECTION_IDs
                        (space-separated, in order, skips missing)
  --binary-only         Extract only the binary document (PDF/AFP), skip text pages
  --no-binary           Extract only text pages, skip binary objects (PDF/AFP)
  --folder <dir>        Process all .RPT files in this directory
  --output <dir>        Output base directory (default: ".")
  --help                Show this help message

Examples:
  # Show RPT file info (no extraction)
  node rpt_page_extractor.js --info 260271NL.RPT

  # Extract all pages from an RPT file
  node rpt_page_extractor.js 260271NL.RPT

  # Extract specific page range
  node rpt_page_extractor.js --pages 10-20 251110OD.RPT

  # Extract pages for a specific section (by SECTION_ID)
  node rpt_page_extractor.js --section-id 14259 251110OD.RPT

  # Extract pages for multiple sections (in order, skips missing)
  node rpt_page_extractor.js --section-id 14259 14260 14261 251110OD.RPT

  # Process all RPT files in a folder
  node rpt_page_extractor.js --folder /path/to/rpt/files

  # Extract only the binary document (PDF/AFP) from an RPT file
  node rpt_page_extractor.js --binary-only 260271Q7.RPT

  # Extract only text pages (skip binary objects)
  node rpt_page_extractor.js --no-binary 260271Q7.RPT

  # Custom output directory
  node rpt_page_extractor.js --output /tmp/extracted 251110OD.RPT`);
}

/**
 * Parse command-line arguments (no external deps).
 * @param {string[]} argv - process.argv.slice(2)
 * @returns {object} Parsed arguments
 */
function parseArgs(argv) {
    const args = {
        info: false,
        pages: null,
        sectionIds: null,
        binaryOnly: false,
        noBinary: false,
        folder: null,
        output: '.',
        help: false,
        rptFiles: [],
    };

    let i = 0;
    while (i < argv.length) {
        const arg = argv[i];

        if (arg === '--help' || arg === '-h') {
            args.help = true;
            i++;
        } else if (arg === '--info') {
            args.info = true;
            i++;
        } else if (arg === '--pages') {
            i++;
            if (i >= argv.length) {
                console.error('Error: --pages requires a value (e.g., "10-20" or "5")');
                process.exit(1);
            }
            args.pages = argv[i];
            i++;
        } else if (arg === '--section-id') {
            i++;
            // Collect all subsequent numeric arguments as section IDs
            const ids = [];
            while (i < argv.length && !argv[i].startsWith('--')) {
                const parsed = parseInt(argv[i], 10);
                if (isNaN(parsed)) {
                    break; // Not a number, treat as positional arg (file path)
                }
                ids.push(parsed);
                i++;
            }
            if (ids.length === 0) {
                console.error('Error: --section-id requires at least one numeric ID');
                process.exit(1);
            }
            args.sectionIds = ids;
        } else if (arg === '--folder') {
            i++;
            if (i >= argv.length) {
                console.error('Error: --folder requires a directory path');
                process.exit(1);
            }
            args.folder = argv[i];
            i++;
        } else if (arg === '--binary-only') {
            args.binaryOnly = true;
            i++;
        } else if (arg === '--no-binary') {
            args.noBinary = true;
            i++;
        } else if (arg === '--output' || arg === '-o') {
            i++;
            if (i >= argv.length) {
                console.error('Error: --output requires a directory path');
                process.exit(1);
            }
            args.output = argv[i];
            i++;
        } else if (arg.startsWith('--')) {
            console.error(`Error: Unknown option: ${arg}`);
            process.exit(1);
        } else {
            // Positional argument (RPT file path)
            args.rptFiles.push(arg);
            i++;
        }
    }

    return args;
}

// ============================================================================
// Main
// ============================================================================

function main() {
    const args = parseArgs(process.argv.slice(2));

    if (args.help) {
        printHelp();
        process.exit(0);
    }

    // Validate arguments
    if (args.rptFiles.length === 0 && args.folder === null) {
        console.error('Error: Provide either RPT file path(s) or --folder <directory>');
        console.error('Use --help for usage information.');
        process.exit(1);
    }

    if (args.pages !== null && args.sectionIds !== null) {
        console.error('Error: Cannot use both --pages and --section-id');
        process.exit(1);
    }

    if (args.binaryOnly && args.noBinary) {
        console.error('Error: Cannot use both --binary-only and --no-binary');
        process.exit(1);
    }

    // Parse page range
    let pageRange = null;
    if (args.pages !== null) {
        const parsed = parsePageRange(args.pages);
        if (isNaN(parsed[0]) || isNaN(parsed[1])) {
            console.error(`Error: Invalid page range: ${args.pages}. Use format "10-20" or "5".`);
            process.exit(1);
        }
        pageRange = parsed;
    }

    // Collect RPT files
    let rptFiles = [];
    if (args.folder !== null) {
        if (!fs.existsSync(args.folder) || !fs.statSync(args.folder).isDirectory()) {
            console.error(`Error: Folder does not exist: ${args.folder}`);
            process.exit(1);
        }
        rptFiles = findRptFiles(args.folder);
        if (rptFiles.length === 0) {
            console.log(`No .RPT files found in ${args.folder}`);
            process.exit(0);
        }
        console.log(`Found ${rptFiles.length} RPT files in ${args.folder}`);
    } else {
        for (const f of args.rptFiles) {
            if (!fs.existsSync(f)) {
                console.error(`Error: RPT file not found: ${f}`);
                process.exit(1);
            }
        }
        rptFiles = args.rptFiles;
    }

    // Process each RPT file
    const allStats = [];
    for (const filepath of rptFiles) {
        const stats = extractRpt(filepath, args.output, {
            pageRange,
            sectionIds: args.sectionIds,
            infoOnly: args.info,
            binaryOnly: args.binaryOnly,
            noBinary: args.noBinary,
        });
        allStats.push(stats);

        if (stats.error) {
            console.log(`  ERROR: ${stats.error}`);
        }
    }

    // Summary for batch mode
    if (rptFiles.length > 1) {
        const totalPages = allStats.reduce((sum, s) => sum + s.pagesExtracted, 0);
        const totalBytes = allStats.reduce((sum, s) => sum + s.bytesDecompressed, 0);
        const errors = allStats.filter(s => s.error !== null).length;
        console.log('');
        console.log('='.repeat(70));
        console.log(
            `SUMMARY: ${rptFiles.length} files, ${totalPages} pages extracted, ` +
            `${formatNumber(totalBytes)} bytes decompressed, ${errors} errors`
        );
    }
}

main();
