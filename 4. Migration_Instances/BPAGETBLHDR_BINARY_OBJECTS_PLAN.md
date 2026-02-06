# Plan: RPT Page Extractor — Binary Object (PDF/AFP) Support

## Discovery Summary

Investigation of `260271Q7.RPT` (species 52759, domain 1) reveals that RPT files can contain **embedded binary objects** (PDF or AFP documents) alongside text pages. The binary objects are stored as separate zlib-compressed streams interleaved with the text page streams, tracked by a previously-unknown **BPAGETBLHDR** structure in the file trailer.

### File Structure — `260271Q7.RPT` (38,829 bytes)

```
0x000-0x0EF  RPTFILEHDR    "RPTFILEHDR\t0001:52759\t2028/03/09 09:15:22.120"
0x0F0-0x1CF  RPTINSTHDR    Instance metadata
0x1D0-0x1FF  Table Directory (3 rows x 12 bytes):
               Row 0 (0x1D0): type=0x0102  count=2  offset=0x9641  → PAGETBLHDR
               Row 1 (0x1E0): type=0x0101  count=1  offset=0x961F  → SECTIONHDR
               Row 2 (0x1F0): type=0x0103  count=2  offset=0x9687  → BPAGETBLHDR ← NEW
0x200-0x305  Text page 1   [Object Header]  (262B zlib → 359B text)
0x306-0x4E40 Binary obj 1  [PDF part 1]     (19,259B zlib → 19,462B)
0x4E41-0x4F3C Text page 2  [Report page]    (252B zlib → 621B text)
0x4F3D-0x970E Binary obj 2 [PDF part 2]     (18,386B zlib → 19,463B)
0x970F        SECTIONHDR   + ENDDATA
0x9731        PAGETBLHDR   (2 × 24-byte entries) + ENDDATA
0x9777        BPAGETBLHDR  (2 × 16-byte entries) + ENDDATA
```

### Key Findings

1. **BPAGETBLHDR** — New marker in the trailer for binary object entries. 16-byte entries:
   ```
   [page_offset:4]        Byte offset relative to RPTINSTHDR (add 0xF0)
   [reserved:4]           Always 0
   [uncompressed_size:4]  Decompressed data size
   [compressed_size:4]    zlib stream size
   ```

2. **Table Directory Row 2** (0x1F0) — type=0x0103, count at 0x1F4, offset at 0x1F8. When count > 0, file has binary objects. Text-only RPTs (e.g. 260271NL.RPT) have count=0 and no BPAGETBLHDR.

3. **Binary objects interleaved** — Each text page's zlib stream is immediately followed by its corresponding binary object's zlib stream in file order.

4. **The binary objects concatenate to a single document** — The two blobs form a complete valid PDF-1.5 (38,925 bytes). The xref table in the last chunk references offsets relative to the combined document start.

5. **Object Header page** — Text page 1 starts with `"StorQM PLUS Object Header Page:"` and contains metadata about the embedded file (Object File Name, timestamps, PDF/AFP creator info). This is NOT a regular report page — it should be treated as a separate metadata section, not extracted as a report text page.

6. **AFP support** — Besides PDF, binary objects may be AFP (Advanced Function Presentation) documents. AFP files start with magic byte `0x5A` (Begin Structured Field Introducer). The Object Header's "Object File Name" field reveals the file type (`.PDF` or `.AFP`).

---

## Implementation Plan

### Files to Modify

| File | Change |
|------|--------|
| `rpt_section_reader.py` | Add `binary_object_count` to `RptHeader`, parse Table Directory Row 2 |
| `rpt_page_extractor.py` | Add BPAGETBLHDR parsing, binary extraction, Object Header detection, new CLI options |
| `rpt_page_extractor.js` | Same changes (JS port) |
| `rpt_page_extractor.cpp` | Same changes (C++ port) |
| `RPT_Page_Extractor.bat` | Add menu option 7 for binary object extraction |
| `RPT_Page_Extractor.sh` | Add menu option 7 for binary object extraction |
| `RPT_Page_Extractor.command` | Add menu option 7 for binary object extraction |
| `RPT_PAGE_EXTRACTOR_GUIDE.md` | Document binary object support and BPAGETBLHDR format |

---

### Step 1: Update `rpt_section_reader.py` — RptHeader + Table Directory

**File:** `/Volumes/acasis/projects/python/ocbc/IntelliSTOR_Migration/4. Migration_Instances/rpt_section_reader.py`

- Add field to `RptHeader` dataclass:
  ```python
  binary_object_count: int    # from Table Directory 0x1F4
  ```
- Update `parse_rpt_header()` to read 0x1F4 (`binary_object_count`) when `len(data) >= 0x200`

### Step 2: Add BPAGETBLHDR parsing to `rpt_page_extractor.py`

**File:** `/Volumes/acasis/projects/python/ocbc/IntelliSTOR_Migration/4. Migration_Instances/rpt_page_extractor.py`

- New dataclass `BinaryObjectEntry`:
  ```python
  @dataclass
  class BinaryObjectEntry:
      index: int               # 1-based
      page_offset: int         # Relative to RPTINSTHDR
      uncompressed_size: int
      compressed_size: int

      @property
      def absolute_offset(self) -> int:
          return self.page_offset + RPTINSTHDR_OFFSET
  ```

- New function `read_binary_page_table(filepath, count) -> List[BinaryObjectEntry]`:
  - Scan for `b'BPAGETBLHDR'` marker
  - Skip marker (11 bytes) + 2 null bytes = 13 bytes
  - Read `count` × 16-byte entries
  - Parse each: `page_offset(u32), reserved(u32), uncompressed_size(u32), compressed_size(u32)`

### Step 3: Object Header detection and extraction

- New function `parse_object_header(page_content: bytes) -> dict`:
  - Detect pages starting with `"StorQM PLUS Object Header Page:"`
  - Parse key-value pairs: `Object File Name`, `Object File Timestamp`, `PDF Title`, `PDF Creator`, etc.
  - Return metadata dict (or `None` if not an Object Header page)

- New function `detect_binary_type(data: bytes) -> str`:
  - Check magic bytes of the first decompressed binary object:
    - `%PDF` → `".pdf"`
    - `0x5A` + AFP structured field → `".afp"`
    - fallback → use extension from Object Header's "Object File Name" if available
    - final fallback → `".bin"`

### Step 4: Binary object decompression and assembly

- New function `decompress_binary_objects(filepath, entries) -> List[Tuple[int, bytes]]`:
  - Same pattern as existing `decompress_pages()` but uses `BinaryObjectEntry`

- New function `assemble_binary_document(objects: List[Tuple[int, bytes]], object_header: dict) -> Tuple[bytes, str, str]`:
  - Concatenates all decompressed binary blobs in order
  - Detects format via `detect_binary_type()`
  - Determines output filename from Object Header's "Object File Name" (fallback: `{rpt_name}_binary{ext}`)
  - Returns `(combined_bytes, filename, format_description)`

### Step 5: Update `extract_rpt()` function

- After reading header, check `header.binary_object_count > 0`
- Read BPAGETBLHDR entries via `read_binary_page_table()`
- **Object Header separation**: Detect text page 1 as Object Header; do NOT include it in regular text page output. Instead, save it as `object_header.txt` in the output dir for reference.
- **Binary extraction**: Decompress binary objects, assemble into single document, save with proper filename/extension
- **`--info` mode**: Show binary object table and Object Header metadata
- New CLI flags:
  - `--binary-only` — extract only the binary document (skip text pages)
  - `--no-binary` — extract only text pages (skip binary objects)
  - Default (no flag): extract **both** — text pages AND binary document as separate files in the same output directory. This produces e.g. `page_00002.txt` + `HKCIF001_016_20280309.PDF` side by side.

### Step 6: Update `--info` display

When binary objects are present, show:
```
  Binary Objects (2):  [BPAGETBLHDR]
    INDEX    OFFSET  UNCOMP_SIZE  COMP_SIZE
  -------  --------  -----------  ---------
        1  0x000306       19,462     19,259
        2  0x004F3D       19,463     18,386

  Object Header:
    File Name: HKCIF001_016_20280309.PDF
    Timestamp: 20260127090844
    Creator: JasperReports Library version 7.0.1
    Producer: OpenPDF 1.3.32

  Assembled document: PDF (38,925 bytes)
```

### Step 7: Update launcher scripts (.bat, .sh, .command)

- Add menu option 7: "Extract binary objects (PDF/AFP) from an RPT file"
- This option calls: `python3 rpt_page_extractor.py --binary-only --output <dir> <file>`

### Step 8: Port to JavaScript and C++ versions

Apply identical logic to:
- `rpt_page_extractor.js` — use `zlib.inflateSync()`, `Buffer.indexOf()` for marker scanning
- `rpt_page_extractor.cpp` — use `uncompress()`, `std::search()` for marker scanning

### Step 9: Update documentation

Update `RPT_PAGE_EXTRACTOR_GUIDE.md`:
- BPAGETBLHDR format reference (16-byte entry layout)
- Table Directory Row 2 (type=0x0103) documentation
- Object Header page format and metadata fields
- Binary object extraction examples (PDF and AFP)
- New CLI options (`--binary-only`, `--no-binary`)
- Magic byte detection table (PDF: `%PDF`, AFP: `0x5A`)

---

## Verification

1. **Info mode with binary RPT**: `python3 rpt_page_extractor.py --info 260271Q7.RPT`
   - Should show text page table, binary object table, and Object Header metadata
2. **Full extraction (default)**: Produces both text pages AND binary document as separate files
   - Output: `object_header.txt`, `page_00002.txt`, `HKCIF001_016_20280309.PDF`
   - When RPT has PDF/AFP + text, default always outputs both (2+ files)
3. **Assembled PDF valid**: The output `.pdf` must open in a PDF viewer
4. **Binary-only mode**: `--binary-only` outputs only the PDF/AFP document
5. **No-binary mode**: `--no-binary` outputs only text pages
6. **Text-only RPT regression**: `260271NL.RPT` (no BPAGETBLHDR) still works unchanged
7. **Cross-implementation**: Python, JS, C++ produce identical output files
8. **Batch mode**: `--folder` correctly handles mixed text-only and binary-containing RPT files
9. **AFP detection**: If an RPT with AFP binary objects is found, it correctly saves as `.afp`
