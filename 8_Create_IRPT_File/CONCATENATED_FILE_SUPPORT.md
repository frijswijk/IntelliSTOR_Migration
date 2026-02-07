# Concatenated File Support for rpt_file_builder

## Overview

The `rpt_file_builder.exe` now supports **single concatenated text files** as input, automatically detecting and splitting them by form-feed characters (`\f` or `0x0C`).

## Key Features

✅ **Auto-detection**: Automatically detects form-feed characters in single input files
✅ **Page splitting**: Splits concatenated content into individual pages
✅ **Section support**: Full support for `--section` flags even with concatenated files
✅ **Backward compatible**: Still supports individual page files and directory mode

## Usage Modes

### Mode 1: Single Concatenated File (NEW!)

When you provide a **single .txt file** containing multiple pages separated by form-feed characters:

```batch
rpt_file_builder.exe --species 1346 --domain 1 \
  -o output.RPT concatenated_pages.txt
```

**The builder will:**
1. Detect form-feed characters (`\f` or `0x0C`)
2. Automatically split into individual pages
3. Build the RPT file with all pages

**Output:**
```
Detected concatenated file with form-feeds: split into 7 pages
Building RPT file: output.RPT
  Built RPT file: output.RPT (6,519 bytes)
  Pages: 7, Sections: 1, Binary objects: 0
```

### Mode 2: Concatenated File with Sections (NEW!)

Define sections even when using a concatenated file:

```batch
rpt_file_builder.exe --species 1346 --domain 1 \
  --section "55737:1:3" \
  --section "14260:4:4" \
  -o output.RPT concatenated_pages.txt
```

**Section format:** `SECTION_ID:START_PAGE:PAGE_COUNT`
- `55737:1:3` = Section 55737 starts at page 1, contains 3 pages
- `14260:4:4` = Section 14260 starts at page 4, contains 4 pages

**Result:**
```
Sections (2):
  SECTION_ID  START_PAGE  PAGE_COUNT
------------  ----------  ----------
       55737           1           3
       14260           4           4
```

### Mode 3: Concatenated File with Binary Object

Include a PDF/AFP in the concatenated workflow:

```batch
rpt_file_builder.exe --species 52759 --domain 1 \
  --binary document.PDF \
  -o output.RPT concatenated_pages.txt
```

**The builder will:**
1. Split the concatenated text by form-feeds
2. Auto-generate an Object Header page (page 1)
3. Embed the PDF as binary objects
4. Interleave binary chunks with text pages

### Mode 4: Individual Page Files (Original)

Still supported! Provide multiple individual .txt files:

```batch
rpt_file_builder.exe --species 1346 --domain 1 \
  -o output.RPT page_00001.txt page_00002.txt page_00003.txt
```

### Mode 5: Directory Mode (Original)

Still supported! Scan a directory for `page_*.txt` files:

```batch
rpt_file_builder.exe --species 1346 --domain 1 \
  -o output.RPT ./extracted/260271Q7/
```

## Form-Feed Format

### What is a Form-Feed?

A **form-feed** character is:
- ASCII character `0x0C` (decimal 12)
- Escape sequence: `\f`
- Often appears as `^L` in text editors

### How Pages Are Separated

The builder splits concatenated files at each form-feed character:

```
Page 1 content here...
Line 2 of page 1
<FORM-FEED>
Page 2 content starts here...
<FORM-FEED>
Page 3 content...
```

### Form-Feed Detection

The builder automatically:
1. Reads the single input .txt file
2. Scans for form-feed characters (`0x0C`)
3. If found: splits into pages
4. If not found: treats entire file as a single page

## Workflow Examples

### Example 1: Extract → Modify → Rebuild

**Step 1: Extract with papyrus_rpt_page_extractor**
```batch
papyrus_rpt_page_extractor.exe input.rpt "all" extracted.txt extracted.pdf
```
Output: `extracted.txt` (all pages concatenated with form-feeds)

**Step 2: Rebuild with rpt_file_builder**
```batch
rpt_file_builder.exe --species 1346 --domain 1 \
  --binary extracted.pdf \
  -o rebuilt.RPT extracted.txt
```
Output: Valid RPT file with all pages and embedded PDF

### Example 2: Extract Sections → Rebuild with Same Sections

**Step 1: Extract specific sections**
```batch
papyrus_rpt_page_extractor.exe input.rpt "55737,14260" extracted.txt extracted.pdf
```
Output: 7 pages (3 from section 55737 + 4 from section 14260)

**Step 2: Rebuild with section definitions**
```batch
rpt_file_builder.exe --species 1346 --domain 1 \
  --section "55737:1:3" \
  --section "14260:4:4" \
  -o rebuilt.RPT extracted.txt
```
Output: RPT file with 2 sections matching original structure

### Example 3: Full Roundtrip Verification

**Extract:**
```batch
papyrus_rpt_page_extractor.exe original.rpt "all" extracted.txt extracted.pdf
```

**Rebuild:**
```batch
rpt_file_builder.exe --species 52759 --domain 1 \
  --binary extracted.pdf \
  -o rebuilt.RPT extracted.txt
```

**Verify:**
```batch
papyrus_rpt_page_extractor.exe rebuilt.rpt "all" verify.txt verify.pdf
```

**Compare:**
```batch
diff extracted.txt verify.txt  # Should be identical
diff extracted.pdf verify.pdf  # Should be identical
```

## Section Support Details

### Defining Multiple Sections

You can define as many sections as needed:

```batch
rpt_file_builder.exe --species 1346 \
  --section "124525:1:110" \
  --section "68102:111:1" \
  --section "55737:114:3" \
  --section "14259:117:2204" \
  -o output.RPT concatenated.txt
```

### Section Validation

The builder validates:
- ✅ Section IDs are valid (non-negative integers)
- ✅ Start pages are sequential (no gaps or overlaps allowed)
- ✅ Page counts match the total number of pages extracted

### Auto-Section Generation

If you don't provide `--section` flags:
- A **single default section** (ID=0) is created automatically
- It covers all pages: `0:1:<page_count>`

## Compatible with Python Tools

The C++ builder is 100% compatible with the Python extractor:

| Tool | Language | Input | Output |
|------|----------|-------|--------|
| `papyrus_rpt_page_extractor.exe` | C++ | RPT file | Concatenated .txt with form-feeds |
| `rpt_file_builder.exe` | C++ | Concatenated .txt | RPT file |
| `rpt_page_extractor.py --page-concat` | Python | RPT file | Concatenated .txt with form-feeds |
| `rpt_file_builder.py` | Python | Individual pages or directory | RPT file |

**Note:** The Python builder does NOT yet support concatenated files directly. Use the C++ version for this workflow.

## Technical Details

### Form-Feed Splitting Algorithm

1. Read entire input file into memory
2. Scan for form-feed characters (`0x0C`)
3. Split at each form-feed position
4. Skip form-feed character and any trailing newline (`\n` or `\r\n`)
5. Collect segments as individual pages
6. Remaining content after last form-feed becomes final page

### Page Boundaries

The builder handles these form-feed patterns:
- `\f` (single form-feed)
- `\f\n` (form-feed + LF)
- `\f\r\n` (form-feed + CRLF)
- `\r\n\f\r\n` (CRLF + form-feed + CRLF)

All variations are correctly recognized and split.

## Command-Line Reference

### Options Summary

| Option | Type | Description |
|--------|------|-------------|
| `-o, --output` | required | Output RPT file path |
| `--species` | int | Report species ID (default: 0) |
| `--domain` | int | Domain ID (default: 1) |
| `--section` | repeatable | Section spec: `ID:START:COUNT` |
| `--binary` | path | PDF or AFP file to embed |
| `input_files` | positional | Single concatenated .txt, multiple .txt files, or directory |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (file not found, invalid input, etc.) |

## Testing

### Verify Form-Feed Detection

Check if your file has form-feeds:

**Windows (PowerShell):**
```powershell
Get-Content concatenated.txt -Raw | Select-String "`f"
```

**Linux/macOS:**
```bash
od -c concatenated.txt | grep "\\f"
```

**Hex dump:**
```bash
hexdump -C concatenated.txt | grep "0c"
```

### Test Concatenated File Workflow

**Test file creation:**
```batch
echo Page 1 content > test.txt
echo. >> test.txt
echo ^L >> test.txt
echo Page 2 content >> test.txt
```

**Build RPT:**
```batch
rpt_file_builder.exe --species 1 -o test.RPT test.txt
```

**Expected output:**
```
Detected concatenated file with form-feeds: split into 2 pages
Building RPT file: test.RPT
  Built RPT file: test.RPT (...bytes)
  Pages: 2, Sections: 1, Binary objects: 0
```

## Troubleshooting

### "No pages detected"
- Check if file contains form-feed characters
- Verify file is not empty
- Try with individual page files instead

### "Pages don't match sections"
- Verify section start pages and counts add up to total pages
- Use `--info` mode to preview without building

### "Sections overlap"
- Section ranges must be sequential without gaps
- Example: `1:1:5` then `2:6:3` (NOT `2:5:3`)

## Migration Guide

### From Individual Files to Concatenated

**Old workflow:**
```batch
# Extract to individual files
rpt_page_extractor.py input.rpt --output ./extracted/

# Build from individual files
rpt_file_builder.exe --species 1346 -o output.RPT ./extracted/input/
```

**New workflow:**
```batch
# Extract to single concatenated file
papyrus_rpt_page_extractor.exe input.rpt "all" extracted.txt extracted.pdf

# Build from single concatenated file
rpt_file_builder.exe --species 1346 --binary extracted.pdf -o output.RPT extracted.txt
```

**Benefits:**
- ✅ Simpler file management (2 files instead of hundreds)
- ✅ Easier to edit/modify content
- ✅ Faster file I/O
- ✅ Better for airgap transfers

## For Airgap Deployment

Copy both executables to your airgap machine:
```
✓ papyrus_rpt_page_extractor.exe (1.3 MB)
✓ rpt_file_builder.exe (1.5 MB)
```

Both are:
- Statically linked (no DLL dependencies)
- Standalone executables
- Windows 7 SP1+ compatible
- No installation required

**Full workflow on airgap machine:**
1. Extract: `papyrus_rpt_page_extractor.exe input.rpt "all" data.txt data.pdf`
2. Edit: Modify `data.txt` as needed
3. Rebuild: `rpt_file_builder.exe --species 1346 --binary data.pdf -o new.rpt data.txt`
