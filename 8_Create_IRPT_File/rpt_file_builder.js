#!/usr/bin/env node
// rpt_file_builder.js - Create IntelliSTOR .RPT files from text pages and optional PDF/AFP
//
// Standalone Node.js CLI tool. Faithful port of the Python rpt_file_builder.py.
// No external dependencies (uses: fs, path, zlib).
//
// Usage: node rpt_file_builder.js [options] -o output.RPT <input_files...>

'use strict';

const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

// ============================================================================
// Constants
// ============================================================================

const RPTFILEHDR_SIZE   = 0x0F0;  // 240 bytes
const RPTINSTHDR_SIZE   = 0x0E0;  // 224 bytes
const TABLE_DIR_SIZE    = 0x030;  // 48 bytes (3 rows x 16 bytes)
const COMPRESSED_START  = 0x200;  // Compressed data always starts here
const RPTINSTHDR_OFFSET = 0x0F0;  // Base for all relative offsets

const ENDDATA_MARKER     = Buffer.from('ENDDATA\x00\x00');          // 9 bytes (7 + 2 null)
const SECTIONHDR_MARKER  = Buffer.from('SECTIONHDR\x00\x00\x00');  // 13 bytes (10 + 3 null)
const PAGETBLHDR_MARKER  = Buffer.from('PAGETBLHDR\x00\x00\x00');  // 13 bytes (10 + 3 null)
const BPAGETBLHDR_MARKER = Buffer.from('BPAGETBLHDR\x00\x00');     // 13 bytes (11 + 2 null)

// ============================================================================
// Data Structures
// ============================================================================

class SectionDef {
    constructor(sectionId, startPage, pageCount) {
        this.sectionId = sectionId;
        this.startPage = startPage;    // 1-based
        this.pageCount = pageCount;
    }
}

class PageInfo {
    constructor({ index, pageNumber, lineWidth, linesPerPage, uncompressedSize, compressedData, compressedSize }) {
        this.index = index;
        this.pageNumber = pageNumber;
        this.lineWidth = lineWidth;
        this.linesPerPage = linesPerPage;
        this.uncompressedSize = uncompressedSize;
        this.compressedData = compressedData;
        this.compressedSize = compressedSize;
    }
}

class BinaryChunkInfo {
    constructor({ index, uncompressedSize, compressedData, compressedSize }) {
        this.index = index;
        this.uncompressedSize = uncompressedSize;
        this.compressedData = compressedData;
        this.compressedSize = compressedSize;
    }
}

// ============================================================================
// Verification Classes (for reading built RPT back)
// ============================================================================

class RptHeader {
    constructor({ domainId, reportSpeciesId, timestamp, pageCount, sectionCount, binaryObjectCount, sectionDataOffset, pageTableOffset }) {
        this.domainId = domainId;
        this.reportSpeciesId = reportSpeciesId;
        this.timestamp = timestamp;
        this.pageCount = pageCount;
        this.sectionCount = sectionCount;
        this.binaryObjectCount = binaryObjectCount || 0;
        this.sectionDataOffset = sectionDataOffset || 0;
        this.pageTableOffset = pageTableOffset || 0;
    }
}

class SectionEntry {
    constructor(sectionId, startPage, pageCount) {
        this.sectionId = sectionId;
        this.startPage = startPage;
        this.pageCount = pageCount;
    }
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Format a number with comma separators.
 */
function formatNumber(n) {
    return n.toLocaleString('en-US');
}

/**
 * Recursively create directories (like mkdir -p).
 */
function mkdirp(dir) {
    try {
        fs.mkdirSync(dir, { recursive: true });
    } catch (e) {
        // Ignore if already exists
    }
}

/**
 * Generate current timestamp as "YYYY/MM/DD HH:MM:SS.mmm".
 */
function generateTimestamp() {
    const now = new Date();
    const yyyy = now.getFullYear();
    const mm = String(now.getMonth() + 1).padStart(2, '0');
    const dd = String(now.getDate()).padStart(2, '0');
    const hh = String(now.getHours()).padStart(2, '0');
    const mi = String(now.getMinutes()).padStart(2, '0');
    const ss = String(now.getSeconds()).padStart(2, '0');
    const ms = String(now.getMilliseconds()).padStart(3, '0');
    return `${yyyy}/${mm}/${dd} ${hh}:${mi}:${ss}.${ms}`;
}

/**
 * Find a Buffer marker inside another Buffer.
 * @param {Buffer} buf - Buffer to search in
 * @param {Buffer} marker - Marker to search for
 * @returns {number} Index of marker, or -1 if not found
 */
function findMarker(buf, marker) {
    return buf.indexOf(marker);
}

// ============================================================================
// Verification Functions (ported from rpt_section_reader.py)
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

/**
 * Read SECTIONHDR from an RPT file.
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
// Object Header Generation
// ============================================================================

/**
 * Generate an Object Header page for an embedded binary file.
 *
 * Mimics the format observed in production RPT files.
 *
 * @param {string} binaryPath - Path to the binary file (PDF/AFP)
 * @returns {Buffer} Object Header text content
 */
function generateObjectHeader(binaryPath) {
    const filename = path.basename(binaryPath);
    const mtime = fs.statSync(binaryPath).mtime;
    const yyyy = mtime.getFullYear();
    const mm = String(mtime.getMonth() + 1).padStart(2, '0');
    const dd = String(mtime.getDate()).padStart(2, '0');
    const hh = String(mtime.getHours()).padStart(2, '0');
    const mi = String(mtime.getMinutes()).padStart(2, '0');
    const ss = String(mtime.getSeconds()).padStart(2, '0');
    const mtimeStr = `${yyyy}${mm}${dd}${hh}${mi}${ss}`;

    const lines = [
        'StorQM PLUS Object Header Page:',
        `Object File Name: ${filename}`,
        `Object File Timestamp: ${mtimeStr}`,
    ];

    // Try to extract PDF metadata
    if (filename.toUpperCase().endsWith('.PDF')) {
        try {
            const fd = fs.openSync(binaryPath, 'r');
            const pdfHeaderBuf = Buffer.alloc(4096);
            fs.readSync(fd, pdfHeaderBuf, 0, 4096, 0);
            fs.closeSync(fd);

            const pdfText = pdfHeaderBuf.toString('latin1');

            const fieldNames = ['Title', 'Subject', 'Author', 'Creator',
                                'Producer', 'CreationDate', 'LastModifiedDate', 'Keywords'];
            for (const fieldName of fieldNames) {
                let value = '';
                const pattern = new RegExp(`/${fieldName}\\s*\\(([^)]*)\\)`);
                const m = pattern.exec(pdfText);
                if (m) {
                    value = m[1];
                } else if (pdfText.includes(`/${fieldName}`)) {
                    // Try parenthesized value on next chars
                    const idx = pdfText.indexOf(`/${fieldName}`);
                    const snippet = pdfText.slice(idx, idx + 200);
                    const m2 = /\(([^)]*)\)/.exec(snippet);
                    if (m2) {
                        value = m2[1];
                    }
                }
                lines.push(`PDF ${fieldName}: ${value}`);
            }
        } catch (e) {
            const fieldNames = ['Title', 'Subject', 'Author', 'Creator',
                                'Producer', 'CreationDate', 'LastModifiedDate', 'Keywords'];
            for (const fieldName of fieldNames) {
                lines.push(`PDF ${fieldName}: `);
            }
        }
    }

    const text = lines.join('\n') + '\n';
    // Replace non-ASCII bytes with '?'
    const buf = Buffer.from(text, 'ascii');
    return buf;
}

// ============================================================================
// BCD Timestamp Encoding
// ============================================================================

/**
 * Encode a timestamp as BCD bytes matching the RPTINSTHDR format.
 *
 * Input: "YYYY/MM/DD HH:MM:SS.mmm" or similar
 * Output: 8-byte Buffer: [year_lo, year_hi, MM, DD, HH, MM, SS, 0x00]
 *         (year as uint16 LE)
 *
 * @param {string} timestampStr
 * @returns {Buffer} 8-byte timestamp buffer
 */
function encodeBcdTimestamp(timestampStr) {
    const m = /(\d{4})\/(\d{2})\/(\d{2})\s+(\d{2}):(\d{2}):(\d{2})/.exec(timestampStr);
    if (!m) {
        return Buffer.alloc(8);
    }

    const year = parseInt(m[1], 10);
    const month = parseInt(m[2], 10);
    const day = parseInt(m[3], 10);
    const hour = parseInt(m[4], 10);
    const minute = parseInt(m[5], 10);
    const second = parseInt(m[6], 10);

    const buf = Buffer.alloc(8);
    buf.writeUInt16LE(year, 0);  // Year as uint16 LE
    buf[2] = month;
    buf[3] = day;
    buf[4] = hour;
    buf[5] = minute;
    buf[6] = second;
    buf[7] = 0x00;
    return buf;
}

// ============================================================================
// Page Analysis
// ============================================================================

/**
 * Analyze a text page and compress it.
 *
 * Returns PageInfo with dimensions, sizes, and compressed data.
 *
 * @param {Buffer} pageData - Raw text page content
 * @param {number} index - 0-based index in text_pages list
 * @param {number} pageNumber - 1-based page number in the output RPT
 * @param {number|null} lineWidthOverride - Override line width for all pages
 * @param {number|null} linesPerPageOverride - Override lines per page for all pages
 * @returns {PageInfo}
 */
function analyzePage(pageData, index, pageNumber, lineWidthOverride, linesPerPageOverride) {
    // Replace bytes > 127 with '?' (0x3F)
    const cleaned = Buffer.from(pageData);
    for (let i = 0; i < cleaned.length; i++) {
        if (cleaned[i] > 127) {
            cleaned[i] = 0x3F;
        }
    }

    const text = cleaned.toString('ascii');
    // Match Python splitlines() behavior: trailing \n does NOT create empty entry
    const lines = text.split('\n');
    if (lines.length > 0 && lines[lines.length - 1] === '') {
        lines.pop();
    }
    let lineWidth = 0;
    for (const line of lines) {
        if (line.length > lineWidth) {
            lineWidth = line.length;
        }
    }
    let linesCount = lines.length;

    if (lineWidthOverride !== null && lineWidthOverride !== undefined) {
        lineWidth = lineWidthOverride;
    }
    if (linesPerPageOverride !== null && linesPerPageOverride !== undefined) {
        linesCount = linesPerPageOverride;
    }

    const compressed = zlib.deflateSync(pageData);

    return new PageInfo({
        index,
        pageNumber,
        lineWidth,
        linesPerPage: linesCount,
        uncompressedSize: pageData.length,
        compressedData: compressed,
        compressedSize: compressed.length,
    });
}

// ============================================================================
// Binary Object Chunking
// ============================================================================

/**
 * Split a binary file into numChunks roughly-equal chunks.
 *
 * The chunks concatenate to form the original file exactly.
 *
 * @param {string} binaryPath - Path to binary file
 * @param {number} numChunks - Number of chunks to create
 * @returns {Buffer[]}
 */
function chunkBinaryFile(binaryPath, numChunks) {
    const binaryData = fs.readFileSync(binaryPath);

    if (numChunks <= 0) {
        return [];
    }
    if (numChunks === 1) {
        return [binaryData];
    }

    const chunkSize = Math.floor(binaryData.length / numChunks);
    const chunks = [];
    let offset = 0;

    for (let i = 0; i < numChunks; i++) {
        if (i === numChunks - 1) {
            // Last chunk gets remaining bytes
            chunks.push(binaryData.slice(offset));
        } else {
            chunks.push(binaryData.slice(offset, offset + chunkSize));
            offset += chunkSize;
        }
    }

    return chunks;
}

// ============================================================================
// Compression
// ============================================================================

/**
 * Compress each binary chunk using zlib.
 *
 * @param {Buffer[]} chunks
 * @returns {BinaryChunkInfo[]}
 */
function compressChunks(chunks) {
    const result = [];
    for (let i = 0; i < chunks.length; i++) {
        const compressed = zlib.deflateSync(chunks[i]);
        result.push(new BinaryChunkInfo({
            index: i,
            uncompressedSize: chunks[i].length,
            compressedData: compressed,
            compressedSize: compressed.length,
        }));
    }
    return result;
}

// ============================================================================
// RPTFILEHDR Construction (0x000-0x0EF, 240 bytes)
// ============================================================================

/**
 * Build the 240-byte RPTFILEHDR block.
 *
 * @param {number} domainId - Domain ID (formatted as 4-digit zero-padded)
 * @param {number} speciesId - Report species ID
 * @param {string} timestamp - "YYYY/MM/DD HH:MM:SS.mmm"
 * @param {number} compressedDataEndRel - End of compressed data area, relative to RPTINSTHDR (0xF0)
 * @returns {Buffer} 240-byte RPTFILEHDR
 */
function buildRptfilehdr(domainId, speciesId, timestamp, compressedDataEndRel) {
    // Header line
    const domainStr = String(domainId).padStart(4, '0');
    const headerLine = `RPTFILEHDR\t${domainStr}:${speciesId}\t${timestamp}\x1a`;
    const buf = Buffer.alloc(RPTFILEHDR_SIZE);  // 240 bytes, zero-filled

    // Write header line
    const headerBytes = Buffer.from(headerLine, 'ascii');
    headerBytes.copy(buf, 0);

    // Fixed sub-header at 0xC0-0xEF
    // 0xC0: E0 00 05 01  (fixed prefix)
    buf.writeUInt32LE(0x010500E0, 0xC0);
    // 0xC4: 01 00 00 00  (constant 1)
    buf.writeUInt32LE(1, 0xC4);
    // 0xC8: E0 00 00 00  (pointer to 0xE0)
    buf.writeUInt32LE(0xE0, 0xC8);
    // 0xCC-0xD3: reserved (already zero)
    // 0xD4: "ENDHDR\x00\x00" (8 bytes)
    Buffer.from('ENDHDR\x00\x00').copy(buf, 0xD4);
    // 0xDC-0xDF: padding (already zero)
    // 0xE0: F0 00 00 00  (pointer to RPTINSTHDR)
    buf.writeUInt32LE(0xF0, 0xE0);
    // 0xE4: reserved (already zero)
    // 0xE8: compressed_data_end (relative to RPTINSTHDR)
    buf.writeUInt32LE(compressedDataEndRel, 0xE8);
    // 0xEC: reserved (already zero)

    return buf;
}

// ============================================================================
// RPTINSTHDR Construction (0x0F0-0x1CF, 224 bytes)
// ============================================================================

/**
 * Build the 224-byte RPTINSTHDR block.
 *
 * If a template is provided in spec, copy it and patch species_id and timestamps.
 * Otherwise, build from scratch with reasonable defaults.
 *
 * @param {object} spec - Build specification with template and metadata
 * @returns {Buffer} 224-byte RPTINSTHDR
 */
function buildRptinsthdr(spec) {
    if (spec.templateRptinsthdr && spec.templateRptinsthdr.length === RPTINSTHDR_SIZE) {
        // Use template as base, patch key fields
        const buf = Buffer.from(spec.templateRptinsthdr);

        // Patch species_id at relative offset 0x14
        buf.writeUInt32LE(spec.speciesId, 0x14);

        // Patch report timestamp at 0x18 (8 bytes)
        const tsBytes = encodeBcdTimestamp(spec.timestamp);
        tsBytes.copy(buf, 0x18);

        return buf;
    } else {
        // Build from scratch
        const buf = Buffer.alloc(RPTINSTHDR_SIZE);  // 224 bytes, zero-filled

        // 0x00: "RPTINSTHDR\x00\x00"
        Buffer.from('RPTINSTHDR\x00\x00').copy(buf, 0);
        // 0x0C: pointer back to RPTFILEHDR sub-header (0xE0)
        buf.writeUInt32LE(0xE0, 0x0C);
        // 0x10: instance number (always 1)
        buf.writeUInt32LE(1, 0x10);
        // 0x14: species_id
        buf.writeUInt32LE(spec.speciesId, 0x14);
        // 0x18: report timestamp (8 bytes BCD)
        const tsBytes = encodeBcdTimestamp(spec.timestamp);
        tsBytes.copy(buf, 0x18);
        // 0x22: creation timestamp (same format)
        tsBytes.copy(buf, 0x22);
        // 0x33: modification timestamp
        tsBytes.copy(buf, 0x33);
        // 0x40: fixed constants 01 01 00 00
        buf[0x40] = 0x01;
        buf[0x41] = 0x01;
        // 0xA0: report format info (0x0409 = 1033)
        buf.writeUInt32LE(0x0409, 0xA0);
        // 0xD0: "ENDHDR\x00\x00"
        Buffer.from('ENDHDR\x00\x00').copy(buf, 0xD0);

        return buf;
    }
}

// ============================================================================
// Compressed Data Assembly
// ============================================================================

/**
 * Assemble the compressed data area.
 *
 * Text-only: page1 + page2 + page3 + ...
 * With binary: page1 + bin1 + page2 + bin2 + ...
 *
 * @param {PageInfo[]} pageInfos
 * @param {BinaryChunkInfo[]|null} binaryChunks
 * @returns {{ data: Buffer, pageOffsets: number[], binaryOffsets: number[]|null }}
 */
function assembleCompressedData(pageInfos, binaryChunks) {
    const parts = [];
    const pageOffsets = [];
    const binaryOffsets = binaryChunks ? [] : null;

    let absPos = COMPRESSED_START;  // 0x200

    if (binaryChunks) {
        // Interleaved: text1, bin1, text2, bin2, ...
        for (let i = 0; i < pageInfos.length; i++) {
            const pageInfo = pageInfos[i];
            pageOffsets.push(absPos);
            parts.push(pageInfo.compressedData);
            absPos += pageInfo.compressedSize;

            if (i < binaryChunks.length) {
                binaryOffsets.push(absPos);
                parts.push(binaryChunks[i].compressedData);
                absPos += binaryChunks[i].compressedSize;
            }
        }
    } else {
        // Text-only: sequential
        for (const pageInfo of pageInfos) {
            pageOffsets.push(absPos);
            parts.push(pageInfo.compressedData);
            absPos += pageInfo.compressedSize;
        }
    }

    return {
        data: Buffer.concat(parts),
        pageOffsets,
        binaryOffsets,
    };
}

// ============================================================================
// Trailer Construction
// ============================================================================

/**
 * Build SECTIONHDR block: marker + triplets + ENDDATA.
 *
 * @param {SectionDef[]} sections
 * @returns {Buffer}
 */
function buildSectionhdr(sections) {
    const parts = [SECTIONHDR_MARKER]; // 13 bytes

    for (const sec of sections) {
        const entry = Buffer.alloc(12);
        entry.writeUInt32LE(sec.sectionId, 0);
        entry.writeUInt32LE(sec.startPage, 4);
        entry.writeUInt32LE(sec.pageCount, 8);
        parts.push(entry);
    }

    parts.push(ENDDATA_MARKER); // 9 bytes
    return Buffer.concat(parts);
}

/**
 * Build PAGETBLHDR block: marker + 24-byte entries + ENDDATA.
 *
 * Each entry: [page_offset_rel:4][pad:4][line_width:2][lines:2][uncomp:4][comp:4][pad:4]
 * page_offset_rel = absolute_offset - 0xF0
 *
 * @param {PageInfo[]} pageInfos
 * @param {number[]} pageOffsets - Absolute offsets for text pages
 * @returns {Buffer}
 */
function buildPagetblhdr(pageInfos, pageOffsets) {
    const parts = [PAGETBLHDR_MARKER]; // 13 bytes

    for (let i = 0; i < pageInfos.length; i++) {
        const pi = pageInfos[i];
        const absOffset = pageOffsets[i];
        const relOffset = absOffset - RPTINSTHDR_OFFSET;  // subtract 0xF0

        const entry = Buffer.alloc(24);
        entry.writeUInt32LE(relOffset, 0);       // page_offset (relative to RPTINSTHDR)
        entry.writeUInt32LE(0, 4);               // reserved
        entry.writeUInt16LE(pi.lineWidth, 8);    // line_width
        entry.writeUInt16LE(pi.linesPerPage, 10); // lines_per_page
        entry.writeUInt32LE(pi.uncompressedSize, 12); // uncompressed_size
        entry.writeUInt32LE(pi.compressedSize, 16);   // compressed_size
        entry.writeUInt32LE(0, 20);              // reserved
        parts.push(entry);
    }

    parts.push(ENDDATA_MARKER); // 9 bytes
    return Buffer.concat(parts);
}

/**
 * Build BPAGETBLHDR block: marker + 16-byte entries + ENDDATA.
 *
 * Each entry: [page_offset_rel:4][reserved:4][uncomp:4][comp:4]
 * page_offset_rel = absolute_offset - 0xF0
 *
 * @param {BinaryChunkInfo[]} binaryChunks
 * @param {number[]} binaryOffsets - Absolute offsets for binary chunks
 * @returns {Buffer}
 */
function buildBpagetblhdr(binaryChunks, binaryOffsets) {
    const parts = [BPAGETBLHDR_MARKER]; // 13 bytes

    for (let i = 0; i < binaryChunks.length; i++) {
        const chunk = binaryChunks[i];
        const absOffset = binaryOffsets[i];
        const relOffset = absOffset - RPTINSTHDR_OFFSET;

        const entry = Buffer.alloc(16);
        entry.writeUInt32LE(relOffset, 0);              // page_offset (relative to RPTINSTHDR)
        entry.writeUInt32LE(0, 4);                      // reserved
        entry.writeUInt32LE(chunk.uncompressedSize, 8); // uncompressed_size
        entry.writeUInt32LE(chunk.compressedSize, 12);  // compressed_size
        parts.push(entry);
    }

    parts.push(ENDDATA_MARKER); // 9 bytes
    return Buffer.concat(parts);
}

// ============================================================================
// Table Directory Construction (0x1D0-0x1FF, 48 bytes)
// ============================================================================

/**
 * Build the 48-byte Table Directory (3 rows x 16 bytes).
 *
 * All offsets are relative to RPTINSTHDR (0xF0).
 *
 * Row 0 (0x1D0): PAGETBLHDR reference - type=0x0102, page_count, pagetbl_off
 * Row 1 (0x1E0): SECTIONHDR reference - type=0x0101, section_count, sectionhdr_off
 * Row 2 (0x1F0): BPAGETBLHDR reference - type=0x0103, binary_count, bpagetbl_off (or all zeros)
 *
 * @param {number} pageCount
 * @param {number} sectionCount
 * @param {number} binaryCount
 * @param {number} sectionhdrAbs
 * @param {number} pagetblhdrAbs
 * @param {number} bpagetblhdrAbs
 * @param {Buffer|null} templateTableDir
 * @returns {Buffer} 48-byte Table Directory
 */
function buildTableDirectory(pageCount, sectionCount, binaryCount,
                             sectionhdrAbs, pagetblhdrAbs, bpagetblhdrAbs,
                             templateTableDir) {
    const buf = Buffer.alloc(TABLE_DIR_SIZE);  // 48 bytes, zero-filled

    // Extract type prefix bytes from template if available
    let typeExtra0 = 0; // bytes 2-3 of type field for Row 0
    let typeExtra1 = 0; // bytes 2-3 of type field for Row 1
    if (templateTableDir && templateTableDir.length >= TABLE_DIR_SIZE) {
        typeExtra0 = templateTableDir.readUInt16LE(2);
        typeExtra1 = templateTableDir.readUInt16LE(0x10 + 2);
    }

    // Row 0: PAGETBLHDR
    const pagetblRel = pagetblhdrAbs - RPTINSTHDR_OFFSET;
    buf[0] = 0x02;
    buf[1] = 0x01;
    buf.writeUInt16LE(typeExtra0, 2);
    buf.writeUInt32LE(pageCount, 4);
    buf.writeUInt32LE(pagetblRel, 8);
    // bytes 12-15: zero padding (already zero)

    // Row 1: SECTIONHDR
    const sectionhdrRel = sectionhdrAbs - RPTINSTHDR_OFFSET;
    buf[0x10] = 0x01;
    buf[0x11] = 0x01;
    buf.writeUInt16LE(typeExtra1, 0x12);
    buf.writeUInt32LE(sectionCount, 0x14);
    buf.writeUInt32LE(sectionhdrRel, 0x18);
    // bytes 0x1C-0x1F: zero padding (already zero)

    // Row 2: BPAGETBLHDR (or all zeros for text-only)
    if (binaryCount > 0) {
        const bpagetblRel = bpagetblhdrAbs - RPTINSTHDR_OFFSET;
        buf[0x20] = 0x03;
        buf[0x21] = 0x01;
        // bytes 0x22-0x23: zero (no template extra needed for BPAGETBLHDR)
        buf.writeUInt32LE(binaryCount, 0x24);
        buf.writeUInt32LE(bpagetblRel, 0x28);
    }

    return buf;
}

// ============================================================================
// Final Assembly
// ============================================================================

/**
 * Assemble all blocks into a complete RPT file.
 *
 * 1. Prepare all pages (including Object Header if binary)
 * 2. Analyze and compress text pages
 * 3. Chunk and compress binary file (if present)
 * 4. Assemble compressed data area
 * 5. Build trailer structures
 * 6. Calculate offsets and build Table Directory
 * 7. Build RPTFILEHDR and RPTINSTHDR
 * 8. Write the final RPT file
 *
 * @param {object} spec - Build specification
 * @param {string} outputPath - Output .RPT file path
 * @param {boolean} verbose - Show detailed build progress
 * @returns {number} Output file size in bytes
 */
function buildRpt(spec, outputPath, verbose) {
    // ---- Prepare all text pages ----
    const allPages = [];
    if (spec.binaryFile && spec.objectHeaderPage) {
        // Object Header is page 1
        allPages.push(spec.objectHeaderPage);
    }
    for (const page of spec.textPages) {
        allPages.push(page);
    }

    const totalTextPages = allPages.length;
    if (verbose) {
        console.log(`  Text pages: ${totalTextPages}`);
        if (spec.binaryFile) {
            console.log(`  Binary file: ${spec.binaryFile}`);
        }
    }

    // ---- Analyze and compress text pages ----
    const pageInfos = [];
    for (let i = 0; i < allPages.length; i++) {
        const pi = analyzePage(allPages[i], i, i + 1,
                               spec.lineWidthOverride, spec.linesPerPageOverride);
        pageInfos.push(pi);
    }

    // ---- Chunk and compress binary file ----
    let binaryChunks = null;
    if (spec.binaryFile) {
        // Number of chunks = number of text pages
        const numChunks = totalTextPages;
        const rawChunks = chunkBinaryFile(spec.binaryFile, numChunks);
        binaryChunks = compressChunks(rawChunks);
        if (verbose) {
            const totalBinUncomp = binaryChunks.reduce((sum, c) => sum + c.uncompressedSize, 0);
            const totalBinComp = binaryChunks.reduce((sum, c) => sum + c.compressedSize, 0);
            console.log(`  Binary chunks: ${binaryChunks.length}, ` +
                        `uncomp=${formatNumber(totalBinUncomp)}, comp=${formatNumber(totalBinComp)}`);
        }
    }

    // ---- Assemble compressed data area ----
    const { data: compData, pageOffsets, binaryOffsets } =
        assembleCompressedData(pageInfos, binaryChunks);

    const compressedDataEndAbs = COMPRESSED_START + compData.length;
    const compressedDataEndRel = compressedDataEndAbs - RPTINSTHDR_OFFSET;

    if (verbose) {
        console.log(`  Compressed data: ${formatNumber(compData.length)} bytes ` +
                    `(0x${COMPRESSED_START.toString(16).toUpperCase()} - 0x${compressedDataEndAbs.toString(16).toUpperCase()})`);
    }

    // ---- Build trailer structures ----
    // Update section definitions if using default single section
    if (spec.sections.length === 1 && spec.sections[0].sectionId === 0) {
        spec.sections[0].pageCount = totalTextPages;
    }

    const sectionhdrBlock = buildSectionhdr(spec.sections);
    const pagetblhdrBlock = buildPagetblhdr(pageInfos, pageOffsets);

    let bpagetblhdrBlock = Buffer.alloc(0);
    let binaryCount = 0;
    if (binaryChunks && binaryOffsets) {
        binaryCount = binaryChunks.length;
        bpagetblhdrBlock = buildBpagetblhdr(binaryChunks, binaryOffsets);
    }

    // ---- Calculate absolute offsets for trailer structures ----
    const sectionhdrAbs = compressedDataEndAbs;
    const pagetblhdrAbs = sectionhdrAbs + sectionhdrBlock.length;
    const bpagetblhdrAbs = pagetblhdrAbs + pagetblhdrBlock.length;

    if (verbose) {
        console.log(`  SECTIONHDR at: 0x${sectionhdrAbs.toString(16).toUpperCase()}`);
        console.log(`  PAGETBLHDR at: 0x${pagetblhdrAbs.toString(16).toUpperCase()}`);
        if (binaryCount > 0) {
            console.log(`  BPAGETBLHDR at: 0x${bpagetblhdrAbs.toString(16).toUpperCase()}`);
        }
    }

    // ---- Build Table Directory ----
    const tableDir = buildTableDirectory(
        totalTextPages,
        spec.sections.length,
        binaryCount,
        sectionhdrAbs,
        pagetblhdrAbs,
        bpagetblhdrAbs,
        spec.templateTableDir || null
    );

    // ---- Build RPTFILEHDR ----
    const rptfilehdr = buildRptfilehdr(
        spec.domainId, spec.speciesId, spec.timestamp,
        compressedDataEndRel
    );

    // ---- Build RPTINSTHDR ----
    const rptinsthdr = buildRptinsthdr(spec);

    // ---- Final Assembly ----
    const outputParts = [
        rptfilehdr,       // 0x000 - 0x0EF (240 bytes)
        rptinsthdr,       // 0x0F0 - 0x1CF (224 bytes)
        tableDir,         // 0x1D0 - 0x1FF (48 bytes)
        compData,         // 0x200 - ...
        sectionhdrBlock,  // SECTIONHDR
        pagetblhdrBlock,  // PAGETBLHDR
    ];
    if (bpagetblhdrBlock.length > 0) {
        outputParts.push(bpagetblhdrBlock); // BPAGETBLHDR
    }

    const output = Buffer.concat(outputParts);

    // ---- Write output ----
    const outputDir = path.dirname(path.resolve(outputPath));
    mkdirp(outputDir);
    fs.writeFileSync(outputPath, output);

    console.log(`  Built RPT file: ${outputPath} (${formatNumber(output.length)} bytes)`);
    console.log(`  Pages: ${totalTextPages}, Sections: ${spec.sections.length}, ` +
                `Binary objects: ${binaryCount}`);

    return output.length;
}

// ============================================================================
// Verification
// ============================================================================

/**
 * Verify the built RPT file by reading it back with parseRptHeader.
 *
 * @param {string} outputPath - Path to the built RPT file
 * @param {boolean} verbose - Show detailed verification results
 * @returns {boolean} True if verification passed
 */
function verifyRpt(outputPath, verbose) {
    const fd = fs.openSync(outputPath, 'r');
    let headerData;
    try {
        headerData = Buffer.alloc(0x200);
        fs.readSync(fd, headerData, 0, 0x200, 0);
    } finally {
        fs.closeSync(fd);
    }

    const header = parseRptHeader(headerData);
    if (header === null) {
        process.stderr.write(`  VERIFY FAIL: Not a valid RPT file\n`);
        return false;
    }

    if (verbose) {
        console.log(`\n  Verification:`);
        console.log(`    Domain: ${header.domainId}, Species: ${header.reportSpeciesId}`);
        console.log(`    Timestamp: ${header.timestamp}`);
        console.log(`    Pages: ${header.pageCount}, Sections: ${header.sectionCount}`);
        console.log(`    Binary objects: ${header.binaryObjectCount}`);
    }

    // Verify we can read sections
    const { sections } = readSectionhdr(outputPath);
    if (verbose) {
        console.log(`    Sections read back: ${sections.length}`);
        for (const s of sections) {
            console.log(`      Section ${s.sectionId}: pages ${s.startPage}-${s.startPage + s.pageCount - 1}`);
        }
    }

    // Try to decompress first page data for deeper verification
    try {
        const fileData = fs.readFileSync(outputPath);
        const ptPos = fileData.indexOf('PAGETBLHDR', 0, 'ascii');
        if (ptPos !== -1 && header.pageCount > 0) {
            const entryStart = ptPos + 13;
            const entrySize = 24;

            // Read first page entry
            const firstOffset = entryStart;
            if (firstOffset + entrySize <= fileData.length) {
                const pageOffsetRel = fileData.readUInt32LE(firstOffset);
                const uncompSize = fileData.readUInt32LE(firstOffset + 12);
                const compSize = fileData.readUInt32LE(firstOffset + 16);
                const absOffset = pageOffsetRel + RPTINSTHDR_OFFSET;

                if (absOffset + compSize <= fileData.length) {
                    const compressed = fileData.slice(absOffset, absOffset + compSize);
                    const decompressed = zlib.inflateSync(compressed);
                    if (verbose) {
                        console.log(`    Page table entries: ${header.pageCount}`);
                        const preview = decompressed.slice(0, 80).toString('ascii').replace(/[^ -~]/g, '?');
                        console.log(`    First page preview: ${preview}...`);
                    }

                    // Read last page entry
                    if (header.pageCount > 1) {
                        const lastOffset = entryStart + (header.pageCount - 1) * entrySize;
                        if (lastOffset + entrySize <= fileData.length) {
                            const lastPageOffsetRel = fileData.readUInt32LE(lastOffset);
                            const lastCompSize = fileData.readUInt32LE(lastOffset + 16);
                            const lastAbsOffset = lastPageOffsetRel + RPTINSTHDR_OFFSET;

                            if (lastAbsOffset + lastCompSize <= fileData.length) {
                                const lastCompressed = fileData.slice(lastAbsOffset, lastAbsOffset + lastCompSize);
                                const lastDecompressed = zlib.inflateSync(lastCompressed);
                                if (verbose) {
                                    const lastPreview = lastDecompressed.slice(0, 80).toString('ascii').replace(/[^ -~]/g, '?');
                                    console.log(`    Last page preview: ${lastPreview}...`);
                                }
                            }
                        }
                    }
                }
            }
        }
    } catch (e) {
        if (verbose) {
            console.log(`    (Deep verification failed: ${e.message})`);
        }
    }

    if (verbose) {
        console.log(`    Verification: PASSED`);
    }
    return true;
}

// ============================================================================
// Input Collection
// ============================================================================

/**
 * Parse a section CSV file (exported by rpt_page_extractor --export-sections).
 *
 * @param {string} csvPath - Path to CSV file
 * @returns {{ sections: SectionDef[], speciesId: number|null }}
 */
function parseSectionCsv(csvPath) {
    const content = fs.readFileSync(csvPath, 'utf-8');
    const lines = content.split(/\r?\n/).filter(line => line.trim().length > 0);

    if (lines.length < 2) {
        process.stderr.write(`ERROR: CSV file is empty or has no data rows: ${csvPath}\n`);
        process.exit(1);
    }

    // Parse header row
    const headers = lines[0].split(',').map(h => h.trim());
    const requiredCols = ['Section_Id', 'Start_Page', 'Pages'];
    const missing = requiredCols.filter(c => !headers.includes(c));
    if (missing.length > 0) {
        process.stderr.write(`ERROR: CSV missing required columns: ${missing.join(', ')}\n`);
        process.stderr.write(`  Expected: Report_Species_Id,Section_Id,Start_Page,Pages\n`);
        process.exit(1);
    }

    const sectionIdIdx = headers.indexOf('Section_Id');
    const startPageIdx = headers.indexOf('Start_Page');
    const pagesIdx = headers.indexOf('Pages');
    const speciesIdx = headers.indexOf('Report_Species_Id');

    const sections = [];
    let speciesId = null;

    for (let rowNum = 1; rowNum < lines.length; rowNum++) {
        const cols = lines[rowNum].split(',').map(c => c.trim());
        if (cols.length < headers.length) continue;

        const sid = parseInt(cols[sectionIdIdx], 10);
        const sp = parseInt(cols[startPageIdx], 10);
        const pc = parseInt(cols[pagesIdx], 10);

        if (isNaN(sid) || isNaN(sp) || isNaN(pc)) {
            process.stderr.write(`ERROR: Invalid CSV row ${rowNum + 1}: non-numeric values\n`);
            process.exit(1);
        }

        sections.push(new SectionDef(sid, sp, pc));

        // Auto-override species from first data row
        if (rowNum === 1 && speciesIdx !== -1) {
            const csvSpecies = parseInt(cols[speciesIdx], 10);
            if (!isNaN(csvSpecies) && csvSpecies !== 0) {
                speciesId = csvSpecies;
            }
        }
    }

    return { sections, speciesId };
}

/**
 * Collect and validate all input files, returning a spec object.
 *
 * Handles both directory input (scan for page_NNNNN.txt, object_header.txt,
 * *.pdf, *.afp) and individual file inputs.
 *
 * @param {object} args - Parsed command-line arguments
 * @returns {object} Build specification
 */
function collectInputs(args) {
    const spec = {
        speciesId: args.species,
        domainId: args.domain,
        timestamp: args.timestamp || generateTimestamp(),
        textPages: [],            // Array of Buffer (raw text content per page)
        sections: [],             // Array of SectionDef
        binaryFile: null,         // Path to PDF/AFP to embed
        objectHeaderPage: null,   // Buffer: Object Header text content
        templateRptinsthdr: null, // Buffer: 224-byte RPTINSTHDR from template
        templateTableDir: null,   // Buffer: 48-byte Table Directory from template
        lineWidthOverride: args.lineWidth || null,
        linesPerPageOverride: args.linesPerPage || null,
    };

    // Load template RPTINSTHDR if provided
    if (args.template) {
        if (!fs.existsSync(args.template)) {
            process.stderr.write(`ERROR: Template file not found: ${args.template}\n`);
            process.exit(1);
        }
        const fd = fs.openSync(args.template, 'r');
        const tplData = Buffer.alloc(COMPRESSED_START);
        const bytesRead = fs.readSync(fd, tplData, 0, COMPRESSED_START, 0);
        fs.closeSync(fd);

        if (bytesRead >= COMPRESSED_START) {
            spec.templateRptinsthdr = tplData.slice(RPTINSTHDR_OFFSET, RPTINSTHDR_OFFSET + RPTINSTHDR_SIZE);
            spec.templateTableDir = tplData.slice(RPTINSTHDR_OFFSET + RPTINSTHDR_SIZE, COMPRESSED_START);
        }
    }

    // Collect text pages
    const inputFiles = args.inputFiles;
    const textPages = [];
    let binaryFile = args.binary || null;
    let objectHeaderFile = args.objectHeader || null;

    if (inputFiles.length === 1 && fs.existsSync(inputFiles[0]) && fs.statSync(inputFiles[0]).isDirectory()) {
        // Directory mode: scan for page_NNNNN.txt, object_header.txt, *.pdf, *.afp
        const directory = inputFiles[0];
        const allEntries = fs.readdirSync(directory).sort();
        const pageFiles = allEntries
            .filter(f => /^page_\d+\.txt$/i.test(f))
            .map(f => path.join(directory, f));

        const objHeaderPath = path.join(directory, 'object_header.txt');

        // Auto-detect binary file if not specified
        if (!binaryFile) {
            for (const ext of ['*.pdf', '*.PDF', '*.afp', '*.AFP']) {
                const extPattern = ext.slice(1); // remove leading *
                const found = allEntries.filter(f => f.endsWith(extPattern));
                if (found.length > 0) {
                    binaryFile = path.join(directory, found[0]);
                    break;
                }
            }
        }

        // Load object header if present and binary file exists
        if (fs.existsSync(objHeaderPath) && binaryFile) {
            if (!objectHeaderFile) {
                objectHeaderFile = objHeaderPath;
            }
        }

        if (pageFiles.length === 0) {
            process.stderr.write(`ERROR: No page_*.txt files found in ${directory}\n`);
            process.exit(1);
        }

        for (const pf of pageFiles) {
            textPages.push(fs.readFileSync(pf));
        }
    } else {
        // Individual file mode: collect .txt files in order
        for (const fpath of inputFiles) {
            if (!fs.existsSync(fpath)) {
                process.stderr.write(`ERROR: Input file not found: ${fpath}\n`);
                process.exit(1);
            }
            if (fpath.toLowerCase().endsWith('.txt')) {
                textPages.push(fs.readFileSync(fpath));
            }
            // Skip non-txt files (binary files should use --binary flag)
        }
    }

    if (textPages.length === 0) {
        process.stderr.write('ERROR: At least 1 text page required\n');
        process.exit(1);
    }

    // Load object header
    if (objectHeaderFile) {
        if (!fs.existsSync(objectHeaderFile)) {
            process.stderr.write(`ERROR: Object header file not found: ${objectHeaderFile}\n`);
            process.exit(1);
        }
        spec.objectHeaderPage = fs.readFileSync(objectHeaderFile);
    }

    // Binary file
    if (binaryFile) {
        if (!fs.existsSync(binaryFile)) {
            process.stderr.write(`ERROR: Binary file not found: ${binaryFile}\n`);
            process.exit(1);
        }
        spec.binaryFile = binaryFile;
        // Generate object header if not provided
        if (!spec.objectHeaderPage) {
            spec.objectHeaderPage = generateObjectHeader(binaryFile);
        }
    }

    spec.textPages = textPages;

    // Parse section specifications
    if (args.section && args.section.length > 0) {
        for (const secSpec of args.section) {
            const parts = secSpec.split(':');
            if (parts.length !== 3) {
                process.stderr.write(`ERROR: Invalid section spec: ${secSpec} (expected SECTION_ID:START_PAGE:PAGE_COUNT)\n`);
                process.exit(1);
            }
            const sid = parseInt(parts[0], 10);
            const sp = parseInt(parts[1], 10);
            const pc = parseInt(parts[2], 10);
            if (isNaN(sid) || isNaN(sp) || isNaN(pc)) {
                process.stderr.write(`ERROR: Invalid section spec values: ${secSpec}\n`);
                process.exit(1);
            }
            spec.sections.push(new SectionDef(sid, sp, pc));
        }
    } else if (args.sectionCsv) {
        // Import sections from CSV (exported by rpt_page_extractor --export-sections)
        const { sections: csvSections, speciesId: csvSpecies } = parseSectionCsv(args.sectionCsv);
        spec.sections = csvSections;

        if (csvSpecies !== null && spec.speciesId === 0) {
            spec.speciesId = csvSpecies;
            console.log(`  Using species ${csvSpecies} from CSV`);
        }

        if (spec.sections.length === 0) {
            process.stderr.write(`ERROR: No sections found in CSV: ${args.sectionCsv}\n`);
            process.exit(1);
        }
        console.log(`  Loaded ${spec.sections.length} sections from ${args.sectionCsv}`);
    } else {
        // Default: single section covering all pages
        let totalPages = textPages.length;
        if (spec.binaryFile && spec.objectHeaderPage) {
            totalPages += 1; // Object Header is page 1
        }
        spec.sections.push(new SectionDef(0, 1, totalPages));
    }

    return spec;
}

// ============================================================================
// CLI
// ============================================================================

/**
 * Print usage/help text.
 */
function printHelp() {
    console.log(`Usage: node rpt_file_builder.js [options] -o output.RPT <input_files...>

Create IntelliSTOR .RPT files from text pages and optional PDF/AFP.

Options:
  -o, --output <file>          Output .RPT file path (required)
  --species <id>               Report species ID (default: 0)
  --domain <id>                Domain ID (default: 1)
  --timestamp <str>            Report timestamp (default: current time)
                               Format: "YYYY/MM/DD HH:MM:SS.mmm"
  --binary <file>              Path to PDF or AFP file to embed as binary object
  --object-header <file>       Path to text file for Object Header page (page 1)
  --section <spec>             Section spec: "SECTION_ID:START_PAGE:PAGE_COUNT"
                               (can repeat)
  --section-csv <file>         CSV file with sections
                               (Report_Species_Id,Section_Id,Start_Page,Pages)
                               Alternative to repeating --section.
  --line-width <n>             Override line width for all pages
  --lines-per-page <n>         Override lines per page for all pages
  --template <file>            Reference .RPT file to copy RPTINSTHDR metadata from
  --info                       Dry run: show what would be built without writing
  -v, --verbose                Show detailed build progress
  -h, --help                   Show this help message

Examples:
  # Build text-only RPT from page files
  node rpt_file_builder.js --species 49626 --domain 1 \\
    -o output.RPT page_00001.txt page_00002.txt

  # Build from a directory of extracted pages
  node rpt_file_builder.js --species 49626 -o output.RPT ./extracted/260271NL/

  # Build RPT with embedded PDF
  node rpt_file_builder.js --species 52759 --domain 1 \\
    --binary HKCIF001_016_20280309.PDF \\
    -o output.RPT object_header.txt page_00002.txt

  # Build with template (roundtrip)
  node rpt_file_builder.js --template original.RPT \\
    --species 49626 -o rebuilt.RPT ./extracted/original/

  # Build RPT with multiple sections
  node rpt_file_builder.js --species 12345 \\
    --section 14259:1:10 --section 14260:11:5 \\
    -o output.RPT page_*.txt

  # Build RPT with sections from CSV (exported by rpt_page_extractor --export-sections)
  node rpt_file_builder.js --section-csv sections.csv \\
    -o output.RPT ./extracted/260271NL/`);
}

/**
 * Parse command-line arguments (no external deps).
 *
 * @param {string[]} argv - process.argv.slice(2)
 * @returns {object} Parsed arguments
 */
function parseArgs(argv) {
    const args = {
        inputFiles: [],
        output: null,
        species: 0,
        domain: 1,
        timestamp: null,
        binary: null,
        objectHeader: null,
        section: [],          // array of "ID:START:COUNT" strings
        sectionCsv: null,
        lineWidth: null,
        linesPerPage: null,
        template: null,
        info: false,
        verbose: false,
        help: false,
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
        } else if (arg === '--verbose' || arg === '-v') {
            args.verbose = true;
            i++;
        } else if (arg === '--output' || arg === '-o') {
            i++;
            if (i >= argv.length) {
                process.stderr.write('Error: --output requires a file path\n');
                process.exit(1);
            }
            args.output = argv[i];
            i++;
        } else if (arg === '--species') {
            i++;
            if (i >= argv.length) {
                process.stderr.write('Error: --species requires a numeric value\n');
                process.exit(1);
            }
            args.species = parseInt(argv[i], 10);
            if (isNaN(args.species)) {
                process.stderr.write(`Error: Invalid species ID: ${argv[i]}\n`);
                process.exit(1);
            }
            i++;
        } else if (arg === '--domain') {
            i++;
            if (i >= argv.length) {
                process.stderr.write('Error: --domain requires a numeric value\n');
                process.exit(1);
            }
            args.domain = parseInt(argv[i], 10);
            if (isNaN(args.domain)) {
                process.stderr.write(`Error: Invalid domain ID: ${argv[i]}\n`);
                process.exit(1);
            }
            i++;
        } else if (arg === '--timestamp') {
            i++;
            if (i >= argv.length) {
                process.stderr.write('Error: --timestamp requires a value\n');
                process.exit(1);
            }
            args.timestamp = argv[i];
            i++;
        } else if (arg === '--binary') {
            i++;
            if (i >= argv.length) {
                process.stderr.write('Error: --binary requires a file path\n');
                process.exit(1);
            }
            args.binary = argv[i];
            i++;
        } else if (arg === '--object-header') {
            i++;
            if (i >= argv.length) {
                process.stderr.write('Error: --object-header requires a file path\n');
                process.exit(1);
            }
            args.objectHeader = argv[i];
            i++;
        } else if (arg === '--section') {
            i++;
            if (i >= argv.length) {
                process.stderr.write('Error: --section requires a spec value (SECTION_ID:START_PAGE:PAGE_COUNT)\n');
                process.exit(1);
            }
            args.section.push(argv[i]);
            i++;
        } else if (arg === '--section-csv') {
            i++;
            if (i >= argv.length) {
                process.stderr.write('Error: --section-csv requires a file path\n');
                process.exit(1);
            }
            args.sectionCsv = argv[i];
            i++;
        } else if (arg === '--line-width') {
            i++;
            if (i >= argv.length) {
                process.stderr.write('Error: --line-width requires a numeric value\n');
                process.exit(1);
            }
            args.lineWidth = parseInt(argv[i], 10);
            if (isNaN(args.lineWidth)) {
                process.stderr.write(`Error: Invalid line width: ${argv[i]}\n`);
                process.exit(1);
            }
            i++;
        } else if (arg === '--lines-per-page') {
            i++;
            if (i >= argv.length) {
                process.stderr.write('Error: --lines-per-page requires a numeric value\n');
                process.exit(1);
            }
            args.linesPerPage = parseInt(argv[i], 10);
            if (isNaN(args.linesPerPage)) {
                process.stderr.write(`Error: Invalid lines per page: ${argv[i]}\n`);
                process.exit(1);
            }
            i++;
        } else if (arg === '--template') {
            i++;
            if (i >= argv.length) {
                process.stderr.write('Error: --template requires a file path\n');
                process.exit(1);
            }
            args.template = argv[i];
            i++;
        } else if (arg.startsWith('--')) {
            process.stderr.write(`Error: Unknown option: ${arg}\n`);
            process.exit(1);
        } else {
            // Positional argument (input file path)
            args.inputFiles.push(arg);
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

    // Validate: output required
    if (!args.output && !args.info) {
        process.stderr.write('Error: -o/--output is required\n');
        process.stderr.write('Use --help for usage information.\n');
        process.exit(1);
    }

    // Validate: input files required
    if (args.inputFiles.length === 0) {
        process.stderr.write('Error: At least one input file or directory is required\n');
        process.stderr.write('Use --help for usage information.\n');
        process.exit(1);
    }

    // Validate: section/section-csv mutually exclusive
    if (args.section.length > 0 && args.sectionCsv) {
        process.stderr.write('Error: Cannot use both --section and --section-csv\n');
        process.exit(1);
    }

    if (args.sectionCsv && !fs.existsSync(args.sectionCsv)) {
        process.stderr.write(`Error: Section CSV file not found: ${args.sectionCsv}\n`);
        process.exit(1);
    }

    // Collect inputs
    const spec = collectInputs(args);

    if (args.info) {
        console.log(`\nBuild plan:`);
        console.log(`  Species: ${spec.speciesId}, Domain: ${spec.domainId}`);
        console.log(`  Timestamp: ${spec.timestamp}`);
        console.log(`  Text pages: ${spec.textPages.length}`);
        if (spec.binaryFile) {
            const binSize = fs.statSync(spec.binaryFile).size;
            console.log(`  Binary file: ${spec.binaryFile} (${formatNumber(binSize)} bytes)`);
            if (spec.objectHeaderPage) {
                console.log(`  Object Header: ${spec.objectHeaderPage.length} bytes`);
            }
        }
        console.log(`  Sections: ${spec.sections.length}`);
        for (const s of spec.sections) {
            console.log(`    ${s.sectionId}: pages ${s.startPage}-${s.startPage + s.pageCount - 1}`);
        }
        console.log(`  Template: ${spec.templateRptinsthdr ? 'yes' : 'no'}`);
        console.log(`  Output: ${args.output}`);
        return;
    }

    // Build
    console.log(`\nBuilding RPT file: ${args.output}`);
    const fileSize = buildRpt(spec, args.output, args.verbose);

    // Verify
    verifyRpt(args.output, args.verbose);
}

main();
