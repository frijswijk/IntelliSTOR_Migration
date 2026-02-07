# Papyrus RPT Page Extractor - Quick Reference

## One-Minute Setup

### 1. Compile
```bash
# Windows MSVC
cl.exe /O2 papyrus_rpt_page_extractor.cpp /Fe:papyrus_rpt_page_extractor.exe /link zlib.lib

# macOS/Linux
g++ -std=c++17 -O2 -o papyrus_rpt_page_extractor papyrus_rpt_page_extractor.cpp -lz
```

### 2. In Papyrus Class Editor

**Method Setup:**
```
Name: ExtractPages
Type: Shell
Program: C:\path\to\papyrus_rpt_page_extractor.exe
Parameters: %TMPFILE/InputRpt/rpt% %SelectionRule% %TMPFILE/ExtractedText/txt% %TMPFILE/ExtractedBinary/pdf%
```

**Attributes:**
```
InputRpt (Binary)        -> Input .rpt file
SelectionRule (String)   -> Selection specification (see below)
ExtractedText (Binary)   -> Output: concatenated text pages
ExtractedBinary (Binary) -> Output: PDF/AFP document
ToolReturnCode (Integer) -> Exit code (0=success)
```

## Usage Example

```bash
# Extract all pages
papyrus_rpt_page_extractor.exe input.rpt "all" output.txt output.pdf

# Extract page range
papyrus_rpt_page_extractor.exe input.rpt "pages:10-20" output.txt output.pdf

# Extract single page
papyrus_rpt_page_extractor.exe input.rpt "pages:5" output.txt output.pdf

# Extract one section
papyrus_rpt_page_extractor.exe input.rpt "section:14259" output.txt output.pdf

# Extract multiple sections
papyrus_rpt_page_extractor.exe input.rpt "sections:14259,14260,14261" output.txt output.pdf
```

## Arguments

| Arg | Meaning | Example |
|-----|---------|---------|
| 1 | Input .rpt file | `260271NL.rpt` |
| 2 | Selection rule | See table below |
| 3 | Output text file | Concatenated pages |
| 4 | Output binary file | PDF or AFP |

## Selection Rules

| Rule | Format | Description | Example |
|------|--------|-------------|---------|
| All | `all` | Extract all pages | `all` |
| Page Range | `pages:START-END` | Pages START through END (1-based, inclusive) | `pages:10-20` |
| Single Page | `pages:N` | Extract only page N | `pages:5` |
| One Section | `section:ID` | Extract pages for section ID | `section:14259` |
| Multi-Section | `sections:ID1,ID2,...` | Multiple section IDs (comma-separated, no spaces) | `sections:14259,14260,14261` |

## Return Codes

| Code | Meaning |
|------|---------|
| 0 | ✅ Success |
| 1 | ❌ Invalid arguments |
| 2 | ❌ Cannot open input file |
| 3 | ❌ Cannot write text output |
| 4 | ❌ Cannot write binary output |
| 5 | ❌ Invalid RPT format |
| 6 | ❌ Decompression error |
| 7 | ❌ No text pages found |
| 8 | ❌ Section ID(s) not found |
| 9 | ❌ Invalid selection rule format |
| 10 | ❌ Unknown error |

## Output Format

**Text File** (ExtractedText):
- All selected pages concatenated
- Separated by form-feed (0x0C) + newline
- Plain text, ready for import

**Binary File** (ExtractedBinary):
- PDF or AFP format (auto-detected)
- Complete, ready-to-render document
- Original from IntelliSTOR RPT

## Performance

| Size | Time | Notes |
|------|------|-------|
| 100 KB | <100 ms | Instant |
| 1 MB | 200-500 ms | Fast |
| 10 MB | 1-2 sec | Good |
| 50 MB | 5-10 sec | Slower |

## Common Issues & Fixes

| Issue | Code | Fix |
|-------|------|-----|
| File not found | 2 | Check path exists |
| Not an RPT | 5 | Verify file format |
| Disk full | 3,4 | Free up space |
| Permission denied | 3,4 | Check write access |
| Corrupted RPT | 6 | Verify file integrity |
| Section not found | 8 | Use "all" to see sections |
| Bad rule format | 9 | Check selection rule syntax |

## State Transition in Papyrus

```
IF ToolReturnCode == 0 THEN -> SUCCESS_STATE
ELSE IF ToolReturnCode == 2 THEN -> FILE_ERROR_STATE
ELSE IF ToolReturnCode == 5 THEN -> INVALID_FORMAT_STATE
ELSE IF ToolReturnCode == 8 THEN -> SECTION_NOT_FOUND_STATE
ELSE -> ERROR_STATE
```

## Testing Standalone

```bash
# Test all pages
papyrus_rpt_page_extractor.exe sample.rpt all output.txt output.pdf
echo %ERRORLEVEL%  # Should print 0

# Test page range
papyrus_rpt_page_extractor.exe sample.rpt "pages:1-10" output.txt output.pdf
echo %ERRORLEVEL%

# Test section extraction
papyrus_rpt_page_extractor.exe sample.rpt "section:14259" output.txt output.pdf
echo %ERRORLEVEL%

# Test multi-section
papyrus_rpt_page_extractor.exe sample.rpt "sections:14259,14260" output.txt output.pdf
echo %ERRORLEVEL%
```

## Files

| File | Purpose |
|------|---------|
| `papyrus_rpt_page_extractor.cpp` | Source code (802 lines) |
| `papyrus_rpt_page_extractor.exe` | Compiled (Windows) |
| `papyrus_rpt_page_extractor` | Compiled (Linux/Mac) |
| `PAPYRUS_INTEGRATION_GUIDE.md` | Full documentation |
| `PAPYRUS_QUICK_REFERENCE.md` | This file |

## Key Features vs Full Tool

| Feature | Full Tool | Papyrus Version |
|---------|-----------|-----------------|
| CLI Options | Many (--pages, --section-id, etc.) | Simple (selection rules) |
| Default Behavior | Individual page files | Concatenated text |
| Output Mode | --page-concat optional | Always concatenates |
| Binary Handling | Optional flags | Always extracts both |
| Use Case | Standalone CLI | Papyrus integration |
| Page Selection | Via CLI flags | Via selection rule string |
| Section Support | ✅ Yes | ✅ Yes (new!) |
| Page Range Support | ✅ Yes | ✅ Yes (new!) |

## Selection Rule Examples in Papyrus

```javascript
// Extract all pages
extractor.SelectionRule = "all";
extractor.ExtractPages();

// Extract pages 10-20
extractor.SelectionRule = "pages:10-20";
extractor.ExtractPages();

// Extract single page
extractor.SelectionRule = "pages:5";
extractor.ExtractPages();

// Extract one section
extractor.SelectionRule = "section:14259";
extractor.ExtractPages();

// Extract multiple sections (pages collected in order)
extractor.SelectionRule = "sections:14259,14260,14261";
extractor.ExtractPages();
```

## Papyrus Parameter Line Explained

```
%TMPFILE/InputRpt/rpt% %SelectionRule% %TMPFILE/ExtractedText/txt% %TMPFILE/ExtractedBinary/pdf%
     ↓                       ↓                 ↓                        ↓
   Input RPT        Selection rule       Output TXT                Output PDF/AFP
  (Binary)          (String value)      (Binary attr)             (Binary attr)
  
  Papyrus:                    Papyrus:         Papyrus:                Papyrus:
  1. Exports InputRpt to:     Passes string    1. Creates empty file    1. Creates empty file
     /tmp/xyz.rpt            "pages:10-20"    /tmp/abc.txt            /tmp/def.pdf
  2. Replaces with path                       2. After execution,      2. After execution,
     /tmp/xyz.rpt            "all"            reads /tmp/abc.txt       reads /tmp/def.pdf
                       or:                     3. Imports to            3. Imports to
                       "section:14259"        ExtractedText            ExtractedBinary
```

## Next Steps

1. **Compile** the executable for your platform
2. **Place** in a directory accessible to Papyrus
3. **Create** class with attributes and method
4. **Test** with different selection rules
5. **Deploy** to production
6. **Monitor** performance for 500 concurrent users

## Architecture

```
Papyrus Workflow
       ↓
 [Call ExtractPages()]
       ↓
 [Export InputRpt to TMPFILE → /tmp/input.rpt]
 [Create empty TMPFILE → /tmp/output.txt]
 [Create empty TMPFILE → /tmp/output.pdf]
       ↓
 [Execute C++ program with 4 arguments]
   Arg 1: /tmp/input.rpt
   Arg 2: "pages:10-20" (or "all", "section:14259", etc.)
   Arg 3: /tmp/output.txt
   Arg 4: /tmp/output.pdf
       ↓
 [C++ reads /tmp/input.rpt]
 [C++ parses selection rule]
 [C++ selects pages (10-20, or section pages, etc.)]
 [C++ decompresses selected pages]
 [C++ writes /tmp/output.txt (concatenated pages)]
 [C++ decompresses binary objects (if any)]
 [C++ writes /tmp/output.pdf (binary doc)]
 [C++ returns exit code]
       ↓
 [Papyrus reads /tmp/output.txt → ExtractedText]
 [Papyrus reads /tmp/output.pdf → ExtractedBinary]
 [ToolReturnCode = exit code]
       ↓
 [Workflow continues based on return code]
```

## Tips for 500 Concurrent Users

1. **Use multiple worker processes** (5-10) instead of 1
2. **Load balance** extractions across workers
3. **Queue long-running jobs** for background processing
4. **Monitor disk I/O** - it's the bottleneck
5. **Pre-create output directories** to reduce overhead
6. **Use local SSD** for temporary files, not network
7. **Set reasonable timeouts** (30-60 seconds per extraction)
8. **Clean up temp files** after Papyrus imports them
9. **Use sections for large RPT files** to reduce memory usage
10. **Test selection rules** before going to production

## Contact

For issues, check:
- `PAPYRUS_INTEGRATION_GUIDE.md` - Full troubleshooting section
- `rpt_page_extractor.cpp` - Reference implementation
- `RPT_PAGE_EXTRACTOR_GUIDE.md` - Full RPT tool documentation
- Log files in temp directory (if ENABLE_LOGGING=true)

---

**Version:** 2.0 | **Date:** 2025-02-07 | **Status:** Production Ready
**New in 2.0:** Support for section IDs and page ranges in selection rules!
