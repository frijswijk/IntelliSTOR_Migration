# AFP Page Splitter - Technical Reference

This document describes the internal architecture, the AFP binary format as it applies to this tool, and the design decisions made. It is intended for developers extending the splitter or integrating it into other systems.

---

## 1. AFP Binary Format

AFP (Advanced Function Presentation) / MO:DCA (Mixed Object Document Content Architecture) is a binary document format used by IBM mainframe print systems.

### 1.1 Structured Field Layout

Every AFP record (called a "Structured Field") follows this layout:

```
Offset  Size  Field
------  ----  -----
0       1     Introducer byte: always 0x5A
1-2     2     Length (big-endian) - does NOT include the 0x5A byte
3       1     Class code: always 0xD3 for MO:DCA
4       1     Type code
5       1     Category code
6       1     Flags
7-8     2     Sequence counter (big-endian, 1-based)
9-16    8     Name field (EBCDIC, padded with 0x40 spaces) - for boundary records
17+     var   Structured field data (triplets, etc.)
```

**Total record size = 1 + Length**. The Length field value includes everything after the 0x5A byte (class/type/category, flags, sequence, name, data).

### 1.2 Record Separators

AFP files may or may not have `0x0D 0x0A` (CR/LF) bytes between records. This is **not defined by the specification** but varies by the system that produced the file:

| Origin | Separator |
|--------|-----------|
| Mainframe AFP (z/OS, CICS) | Typically no separator |
| AFP downloaded via FTP text mode | CR/LF between records |
| AFP Viewer / third-party tools | Varies |

The splitter auto-detects the convention by inspecting the byte immediately following the first record in the source file.

### 1.3 Key Structured Field Identifiers

Identified by the 3-byte combination `[ClassCode TypeCode CategoryCode]`:

| SFID | Abbreviation | Meaning |
|------|-------------|---------|
| `D3 A8 A8` | BDT | Begin Document |
| `D3 A9 A8` | EDT | End Document |
| `D3 A8 AF` | BPG | Begin Page |
| `D3 A9 AF` | EPG | End Page |
| `D3 A8 AD` | BNG | Begin Named Page Group |
| `D3 A9 AD` | ENG | End Named Page Group |
| `D3 A8 C9` | BAG | Begin Active Environment Group |
| `D3 A9 C9` | EAG | End Active Environment Group |
| `D3 A8 EB` | BRG | Begin Resource Group |
| `D3 A9 EB` | ERG | End Resource Group |
| `D3 A8 BB` | BDG | Begin Document Environment Group |
| `D3 A9 BB` | EDG | End Document Environment Group |
| `D3 AB CC` | MPS | Map Page Segment |
| `D3 AB D8` | MDD | Medium Descriptor |
| `D3 AB C3` | MCF | Map Coded Font |
| `D3 AF CC` | MPO | Map Page Overlay |
| `D3 AF D8` | MMO | Map Medium Overlay |
| `D3 EE 89` | IMM | Invoke Medium Map |
| `D3 A6 AF` | PGD | Page Descriptor |
| `D3 A8 9B` | BPT | Begin Presentation Text |
| `D3 EE 9B` | PTX | Presentation Text Data |
| `D3 A9 9B` | EPT | End Presentation Text |
| `D3 B2 EB` | TLE | Tag Logical Element (metadata index) |
| `D3 A7 88` | IOB | Include Object |

### 1.4 Document Structure Patterns

AFP files can have different structural patterns. The splitter handles all three:

**Pattern A - Full document envelope (e.g. AEP.afp):**
```
BDT  (Begin Document)
  BDG  (Begin Doc Env Group)
    MCF, MPO, MDD ...  (resource mappings)
  EDG  (End Doc Env Group)
  BPG  (Begin Page 1)
    PGD, BPT, PTX, ..., EPT
  EPG  (End Page 1)
  CRLF
  BPG  (Begin Page 2)
    ...
  EPG  (End Page 2)
  CRLF
EDT  (End Document)
```

**Pattern B - No document envelope (e.g. 26027272.AFP):**
```
MPS  (Map Page Segment - for page 1)
BPG  (Begin Page 1)
  PGD, BAG, BPT, PTX, ..., EPT, EAG
EPG  (End Page 1)
MPS  (Map Page Segment - for page 2)
BPG  (Begin Page 2)
  ...
EPG  (End Page 2)
```

**Pattern C - Embedded resources with document envelope (e.g. Auction_res_index.afp):**
```
BFN  (Begin Font)                    \
  ...font object data...              |  Pre-BDT resources
EFN  (End Font)                      /
BDT  (Begin Document)
  BNG  (Begin Named Page Group)
    TLE  (Tag Logical Element - index metadata)
    BPG  (Begin Page 1)
      BAG, MCF, EAG, BDG, EDG, ...
    EPG  (End Page 1)
    BPG  (Begin Page 2)
      ...
    EPG  (End Page 2)
  ENG  (End Named Page Group)
  BNG  (Begin Named Page Group)
    ...
  ENG
EDT  (End Document)
```

Key differences:
- Pattern B has no BDT/EDT, no CRLF separators, and MPS records precede each page.
- Pattern C has embedded font resources **before** the BDT and uses named page groups (BNG/ENG) to group pages.
- The splitter always wraps output in BDT/EDT (creating them if absent in source).
- Inter-page records (like MPS, ENG/BNG) are captured and included in the output.
- Document preamble resources (fonts, overlays, environment groups) are automatically included when the source contains them (see section 3.6).

### 1.5 EBCDIC Encoding

Name fields in boundary records (BDT, EDT, BPG, EPG) use EBCDIC encoding (Code Page 037/500), padded to 8 bytes with `0x40` (EBCDIC space). The splitter derives the document name from the input filename, converting ASCII to EBCDIC.

Relevant EBCDIC ranges:
- `A-I` → `0xC1-0xC9`
- `J-R` → `0xD1-0xD9`
- `S-Z` → `0xE2-0xE9`
- `0-9` → `0xF0-0xF9`
- Space → `0x40`

---

## 2. Architecture

### 2.1 Class Diagram

```
AFPParser                        AFPSplitter
  - fileData_: vector<uint8_t>     - parser_: unique_ptr<AFPParser>
  - pages_: vector<AFPPage>        - inputFilename_: string
  - documentHeader_: vector        - lastError_: string
  - documentFooter_: vector
  - allResources_: vector          Methods:
                                     loadFile(filename)
  Methods:                           parsePageRanges(rangeStr)
    parse(filename)                  extractPages(ranges, output)
    getPage(pageNum)                 extractPagesWithResources(ranges, output)
    getRawData()
    getPreamble()                  AFPUtil (namespace)
    getPostamble()                   readUInt16BE / writeUInt16BE
                                     isValidAFP / trim / asciiToEbcdic

AFPPage                          PageRange
  - pageNumber: int                - start: int
  - startOffset: size_t           - end: int
  - endOffset: size_t             - normalize(maxPages)
  - actualPageStart: size_t
```

### 2.2 Source Files

| File | Responsibility |
|------|---------------|
| `afp_parser.h` | All struct/class declarations and the `AFPUtil` namespace |
| `afp_parser.cpp` | `AFPParser` (parsing), `AFPSplitter` (extraction), `AFPUtil` (utilities) |
| `afp_splitter.cpp` | CLI argument parsing, user output, `main()` |

### 2.3 Processing Pipeline

```
main()
  |
  v
AFPSplitter::loadFile(filename)
  |-> AFPParser::parse(filename)
  |     |-> Read entire file into fileData_
  |     |-> isValidAFP() - check 0x5A + 0xD3
  |     |-> parseStructuredFields()
  |           |-> Walk byte-by-byte looking for 0x5A introducer
  |           |-> On BPG: start tracking new page
  |           |-> On EPG: finalise page with startOffset/endOffset/actualPageStart
  |           |-> Store documentHeader_ (everything before first BPG)
  |           |-> Store documentFooter_ (everything after last EPG)
  |
  v
AFPSplitter::parsePageRanges("2-3,5")
  |-> Split by comma, parse start-end
  |-> Normalise: clamp, swap reversed
  |
  v
AFPSplitter::extractPagesWithResources(ranges, outputFile)
  |-> expandPageRanges() -> [2, 3, 5]
  |-> Detect CRLF convention from source
  |-> Derive document name from input filename (EBCDIC)
  |-> Write BDT (seq=1)
  |-> Include preamble resources (if source has BDT):
  |     |-> Walk preamble record by record
  |     |-> Copy all records except BDT/EDT/BNG/ENG
  |     |-> Renumber sequence counters
  |-> For each page:
  |     |-> Copy inter-page data (MPS, ENG/BNG, separators) with renumbered sequences
  |     |-> Copy page data (BPG through EPG) with renumbered sequences
  |-> Write EDT (seq=N)
  |-> Close file
```

---

## 3. Key Design Decisions

### 3.1 Page Offset Model

The parser stores three offsets per page:

| Field | Meaning |
|-------|---------|
| `startOffset` | For page 1: same as `actualPageStart`. For pages 2+: last byte of previous page's EPG record. |
| `actualPageStart` | The 0x5A byte of this page's BPG record. |
| `endOffset` | Last byte (inclusive) of this page's EPG record. |

The **inter-page gap** is the data between `startOffset + 1` and `actualPageStart - 1` (inclusive). This gap contains:
- CRLF separators (if the source uses them)
- MPS (Map Page Segment) records that map resources for the upcoming page
- Any other inter-page structured fields

This model allows the extraction function to include inter-page records without needing to identify each record type individually.

### 3.2 CRLF Auto-Detection

Rather than assuming a separator convention, the splitter checks the bytes immediately following the first structured field in the source:

```cpp
size_t afterFirstRecord = pos + 1 + recordLength;
if (rawData[afterFirstRecord] == 0x0D && rawData[afterFirstRecord+1] == 0x0A) {
    useCRLF = true;
}
```

When `useCRLF` is true:
- CRLF is written between BDT and the first page (if no inter-page data exists)
- CRLF is written between the last page and EDT
- CRLF is written after EDT
- Inter-page data already includes source CRLF so no explicit separator is needed between pages

When `useCRLF` is false:
- No separators are written anywhere
- Records are immediately adjacent in the output

### 3.3 Sequence Counter Renumbering

AFP records have a 16-bit sequence counter at bytes 7-8 (relative to the 0x5A). The splitter renumbers all output records sequentially starting from 1:

```
BDT              -> seq 1
BFN (preamble)   -> seq 2        (only if source has preamble resources)
...              -> seq ...
EFN (preamble)   -> seq K
MPS (p2)         -> seq K+1
BPG (p2)         -> seq K+2
PTX              -> seq K+3
...
EPG (p2)         -> seq N
MPS (p3)         -> seq N+1
...
EDT              -> seq M
```

To avoid false positives (0x5A bytes appearing inside record data), the renumbering loop validates both the 0x5A introducer **and** the 0xD3 class code at offset +3:

```cpp
if (data[pos] == 0x5A && data[pos + 3] == 0xD3) {
    // This is a real AFP record, renumber it
}
```

### 3.4 Document Name Derivation

The output BDT/EDT name field is derived from the input filename:
1. Strip directory path
2. Strip file extension
3. Convert to uppercase
4. Convert each character to EBCDIC (Code Page 037)
5. Truncate or pad to exactly 8 bytes (pad with 0x40 EBCDIC space)

Example: `26027272.AFP` becomes `F2F6F0F2 F7F2F7F2` (EBCDIC "26027272").

### 3.5 Parser Off-by-One

The parser advances with `offset += field.length` instead of `offset += field.length + 1`. Since `field.length` is the Length field value (excludes the 0x5A byte), the record occupies bytes `[offset, offset + field.length]`, and `offset` after the advance points to the **last byte** of the current record rather than the first byte of the next one.

This is compensated by the scanning loop: the next iteration sees a non-0x5A byte and increments past it (and past any CRLF). This is intentional and should be preserved as-is to avoid cascading changes to the page offset model.

### 3.6 Preamble Resource Inclusion

The document preamble (`documentHeader_` / `getPreamble()`) contains everything from the start of the file up to the first BPG record. Depending on the file pattern, this preamble may contain:

| Pattern | Preamble contents |
|---------|-------------------|
| A (AEP.afp) | BDT, MPS, resource mappings |
| B (26027272.AFP) | MPS only (no BDT) |
| C (Auction_res_index.afp) | Font objects (BFN..EFN), BDT, BNG, TLE |

The extraction function automatically detects whether the preamble contains a BDT record. This distinguishes Pattern A/C files (global document resources) from Pattern B files (page-specific data only):

- **BDT present**: The preamble contains document-level resources. All records are copied to the output **except** BDT, EDT, BNG, and ENG (which the splitter manages itself). This preserves embedded fonts, coded font maps, overlay definitions, document environment groups, and TLE metadata.
- **BDT absent**: The preamble contains page-specific data (e.g. MPS for page 1) that is already handled by the inter-page data logic. No preamble records are copied.

Each preamble record is copied individually with its sequence counter renumbered and CRLF separators matching the source convention. Source CRLF bytes between preamble records are skipped (the splitter writes its own separators).

---

## 4. Extraction Modes

### 4.1 `extractPagesWithResources()` (Default)

The default mode. Produces a clean, standalone AFP file:

```
[BDT] [preamble resources] [inter-page data] [BPG..EPG] [inter-page data] [BPG..EPG] ... [EDT]
```

- Creates synthetic BDT and EDT records with derived document name
- Includes document preamble resources when the source has them (fonts, overlays, environment groups)
- Copies inter-page data (MPS, ENG/BNG, source separators) for each page
- Renumbers all sequence counters from 1
- Respects source CRLF convention

CLI: `afp_splitter.exe input.afp 2-3 output.afp`

### 4.2 `extractPages()` (Raw Mode)

Copies raw data from the source file:

```
[everything before first requested page] [page data...] [postamble]
```

- Preserves original document envelope (BDT/BDG/etc.)
- Includes all pages before the first requested page (by design)
- Does not renumber sequence counters
- Useful when you want to preserve the full document context

CLI: `afp_splitter.exe input.afp 2-3 output.afp --raw`

---

## 5. Integration Guide

### 5.1 Using as a Library

The classes can be used directly without the CLI. Example:

```cpp
#include "afp_parser.h"

AFPSplitter splitter;
if (!splitter.loadFile("input.afp")) {
    // handle error: splitter.getLastError()
}

int totalPages = splitter.getPageCount();

std::vector<PageRange> ranges = splitter.parsePageRanges("2-3");
// or construct manually:
// ranges.push_back(PageRange(2, 3));

if (!splitter.extractPagesWithResources(ranges, "output.afp")) {
    // handle error: splitter.getLastError()
}
```

### 5.2 Accessing Parsed Data

The `AFPParser` exposes raw data and page metadata:

```cpp
AFPParser parser;
parser.parse("input.afp");

// Iterate pages
for (const auto& page : parser.getAllPages()) {
    // page.pageNumber, page.startOffset, page.endOffset, page.actualPageStart
}

// Access raw bytes
const auto& raw = parser.getRawData();
// raw[page.actualPageStart] == 0x5A (BPG introducer)

// Document header (everything before first page)
const auto& header = parser.getPreamble();

// Document footer (everything after last page)
const auto& footer = parser.getPostamble();
```

### 5.3 Build Integration

To embed in another project, include these files:
- `afp_parser.h`
- `afp_parser.cpp`

Compile with C++17 (`-std=c++17`). No external dependencies.

---

## 6. Known Limitations and Future Work

### 6.1 Current Limitations

- **Page 1 inter-page data**: If the first requested page is page 1 in the source, any records preceding it (e.g. MPS in Pattern B files) are not included. These records live in the document header, which may also contain BDT/BDG that should not be duplicated.
- **Named Page Groups (BNG/ENG)**: Inter-page BNG/ENG records are preserved as part of inter-page data, but the splitter does not reconstruct group boundaries to match the original grouping. The output may contain partial groups.
- **Preamble includes all resources**: When preamble resources are included, all document-level resources are copied regardless of whether the extracted pages actually reference them. This is safe (unused resources are ignored by viewers) but may result in larger output files than strictly necessary.
- **TLE metadata**: TLE (Tag Logical Element) records in the preamble are preserved in the output. TLE records are parsed but not used for page filtering. They are available in `AFPPage::tleIndexes` for future use.

### 6.2 Extending the Splitter

**Adding TLE-based extraction:**
1. In `parseStructuredFields()`, when a TLE record is found, parse its key/value and store in `page.tleIndexes`.
2. Add a new extraction method that filters pages by TLE values instead of page numbers.
3. Reuse `extractPagesWithResources()` with the filtered page list.

**Selective resource inclusion:**
1. During preamble inclusion, parse each resource record to determine which fonts/overlays it defines.
2. Cross-reference against the MCF/MPO/MPS records in the extracted pages.
3. Only include resources that are actually referenced by the extracted pages (reduces output size for large resource blocks).

**Supporting page groups:**
1. Track BNG/ENG boundaries in the parser alongside BPG/EPG.
2. When extracting, include the BNG before the first page in a group and ENG after the last.

**Merging multiple AFP files:**
1. Load each source file with separate `AFPParser` instances.
2. Write a single BDT, then pages from each source with renumbered sequences, then EDT.
3. Handle CRLF convention conflicts (use the convention of the first source, or force one convention).
