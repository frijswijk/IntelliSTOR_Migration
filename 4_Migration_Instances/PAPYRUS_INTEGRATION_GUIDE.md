# Papyrus RPT Page Extractor Integration Guide

## Overview

`papyrus_rpt_page_extractor.exe` is a specialized C++ application designed for seamless integration with Papyrus workflow systems. It extracts and segregates pages from IntelliSTOR `.rpt` files and writes output directly to file placeholders managed by Papyrus.

## Key Features

- **Minimal Startup Overhead**: Compiled C++ with zero process overhead (unlike Python/JavaScript)
- **Papyrus-Optimized**: Works directly with `%TMPFILE%` macros for file exchange
- **Default Behavior**: Concatenates all pages into a single `.txt` file
- **Binary Support**: Automatically writes PDF/AFP documents to output placeholder
- **Exit Codes**: Returns meaningful codes for Papyrus state transitions
- **Production-Ready**: 500+ concurrent user capable

## Compilation

### Windows (MSVC - Recommended for Papyrus)
```batch
cl.exe /O2 papyrus_rpt_page_extractor.cpp /Fe:papyrus_rpt_page_extractor.exe /link zlib.lib
```

### Windows (MinGW)
```bash
g++ -std=c++17 -O2 -o papyrus_rpt_page_extractor.exe papyrus_rpt_page_extractor.cpp -lz
```

### macOS/Linux
```bash
clang++ -std=c++17 -O2 -o papyrus_rpt_page_extractor papyrus_rpt_page_extractor.cpp -lz
# OR
g++ -std=c++17 -O2 -o papyrus_rpt_page_extractor papyrus_rpt_page_extractor.cpp -lz
```

## Papyrus Configuration

### 1. Define Class Attributes

Create a class derived from `ExternalApplication` or custom tool class with these attributes:

```
CLASS: RPTExtractor
  EXTENDS: ExternalApplication

ATTRIBUTES:
  InputRpt (Binary)           - Input .rpt file from document source
  SelectionRule (String)      - Selection rule specification (see below)
  ExtractedText (Binary)      - Output: Concatenated text pages
  ExtractedBinary (Binary)    - Output: PDF or AFP document
  ToolReturnCode (Integer)    - System attribute (auto-captured from process exit code)
```

### 2. Configure Shell Method

In the Class Editor, create a method with these properties:

**Method Properties:**
| Property | Value |
|----------|-------|
| Method Name | `ExtractPages` |
| Implementation | `Shell` |
| Program Name | `C:\Path\To\papyrus_rpt_page_extractor.exe` |
| Working Directory | `C:\Path\To\bin\` |
| Parameter Line | (see below) |

**Parameter Line (exact syntax):**
```
%TMPFILE/InputRpt/rpt% %SelectionRule% %TMPFILE/ExtractedText/txt% %TMPFILE/ExtractedBinary/pdf%
```

**How the Parameter Line Works:**

1. **`%TMPFILE/InputRpt/rpt%`**
   - Papyrus exports the `InputRpt` binary attribute to a temporary file
   - Replaces macro with the absolute path (e.g., `C:\Temp\tmp_xyz.rpt`)
   - Format hint (/rpt) tells Papyrus to expect an .rpt file

2. **`%SelectionRule%`**
   - Passes the String attribute as-is to specify which pages to extract
   - Selection rule format (see "Selection Rules" section below)

3. **`%TMPFILE/ExtractedText/txt%`**
   - Creates an empty temporary file for output
   - Replaces macro with the absolute path (e.g., `C:\Temp\tmp_abc.txt`)
   - After extraction completes, Papyrus reads this file and imports it into `ExtractedText`

4. **`%TMPFILE/ExtractedBinary/pdf%`**
   - Creates an empty temporary file for binary output
   - Replaces macro with absolute path (e.g., `C:\Temp\tmp_def.pdf`)
   - After extraction completes, Papyrus reads this file and imports it into `ExtractedBinary`
   - Format hint (/pdf) tells Papyrus this is binary data

## Selection Rules

The `SelectionRule` attribute controls which pages are extracted from the RPT file. Specify using one of these formats:

| Rule | Format | Description | Example |
|------|--------|-------------|---------|
| All Pages | `all` | Extract all pages (default) | `"all"` |
| Page Range | `pages:START-END` | Pages START through END (1-based, inclusive) | `"pages:10-20"` |
| Single Page | `pages:N` | Extract only page N | `"pages:5"` |
| One Section | `section:ID` | Extract pages for a specific section ID | `"section:14259"` |
| Multi-Section | `sections:ID1,ID2,...` | Multiple section IDs (comma-separated, no spaces) | `"sections:14259,14260,14261"` |

**Key Points:**
- Page numbers are 1-based and inclusive
- Section IDs must match those in the RPT file's SECTIONHDR
- Multiple section IDs are collected in the order specified
- Missing section IDs are silently skipped (unlike the full tool which requires finding at least one)
- No spaces in the rule format

### 3. Example Papyrus Workflows

#### Example 1: Extract All Pages (Basic)

```javascript
// Pseudocode for Papyrus workflow

BEGIN Process
  // Create extractor instance
  RPTExtractor extractor = new RPTExtractor();
  
  // Step 1: Set input from incoming document
  extractor.InputRpt = incomingDocument.BinaryContent;  // From user upload
  extractor.SelectionRule = "all";                       // Extract all pages
  
  // Step 2: Call the shell method (this triggers C++ executable)
  extractor.ExtractPages();
  
  // Step 3: Check exit code and react
  IF extractor.ToolReturnCode == 0 THEN
    // Success: Text and binary extracted
    outputDocument.TextContent = extractor.ExtractedText;
    outputDocument.BinaryContent = extractor.ExtractedBinary;
    outputDocument.Status = "EXTRACTED";
    
  ELSE IF extractor.ToolReturnCode == 2 THEN
    // Input file error
    RAISE ERROR "Input RPT file cannot be opened or is corrupted";
    
  ELSE IF extractor.ToolReturnCode == 5 THEN
    // Invalid RPT format
    RAISE ERROR "File is not a valid IntelliSTOR RPT file";
    
  ELSE IF extractor.ToolReturnCode == 7 THEN
    // No text pages
    RAISE ERROR "RPT file contains no extractable text pages";
    
  ELSE
    // Other errors
    RAISE ERROR "RPT extraction failed with code " + extractor.ToolReturnCode;
  ENDIF;
  
  // Step 4: Optional: Save to document repository
  outputDocument.Save();

END Process
```

#### Example 2: Extract Pages by Range

```javascript
BEGIN Process
  RPTExtractor extractor = new RPTExtractor();
  extractor.InputRpt = incomingDocument.BinaryContent;
  extractor.SelectionRule = "pages:10-20";  // Extract only pages 10-20
  extractor.ExtractPages();
  
  IF extractor.ToolReturnCode == 0 THEN
    // Success: Pages 10-20 extracted
    outputDocument.TextContent = extractor.ExtractedText;
    outputDocument.Status = "EXTRACTED_RANGE";
  ELSE IF extractor.ToolReturnCode == 9 THEN
    // Invalid selection rule format
    RAISE ERROR "Invalid page range specification";
  ELSE
    RAISE ERROR "Extraction failed with code " + extractor.ToolReturnCode;
  ENDIF;
END Process
```

#### Example 3: Extract Pages by Section ID

```javascript
BEGIN Process
  RPTExtractor extractor = new RPTExtractor();
  extractor.InputRpt = incomingDocument.BinaryContent;
  
  // Extract only pages belonging to section 14259
  extractor.SelectionRule = "section:14259";
  extractor.ExtractPages();
  
  IF extractor.ToolReturnCode == 0 THEN
    // Success: Pages for section 14259 extracted
    outputDocument.TextContent = extractor.ExtractedText;
    outputDocument.SectionId = 14259;
    outputDocument.Status = "EXTRACTED_SECTION";
    
  ELSE IF extractor.ToolReturnCode == 8 THEN
    // Section ID not found
    RAISE ERROR "Section 14259 not found in this RPT file";
  ELSE
    RAISE ERROR "Extraction failed with code " + extractor.ToolReturnCode;
  ENDIF;
END Process
```

#### Example 4: Extract Multiple Sections

```javascript
BEGIN Process
  RPTExtractor extractor = new RPTExtractor();
  extractor.InputRpt = incomingDocument.BinaryContent;
  
  // Extract pages for multiple sections (comma-separated, no spaces)
  extractor.SelectionRule = "sections:14259,14260,14261";
  extractor.ExtractPages();
  
  IF extractor.ToolReturnCode == 0 THEN
    // Success: Pages from all 3 sections extracted
    // (even if one or two section IDs were missing, extraction succeeds
    //  if at least some section IDs were found)
    outputDocument.TextContent = extractor.ExtractedText;
    outputDocument.Status = "EXTRACTED_SECTIONS";
    
  ELSE IF extractor.ToolReturnCode == 8 THEN
    // None of the section IDs were found
    RAISE ERROR "No matching sections found in RPT file";
  ELSE
    RAISE ERROR "Extraction failed with code " + extractor.ToolReturnCode;
  ENDIF;
END Process
```

#### Example 5: Dynamic Selection Based on Document Type

```javascript
BEGIN Process
  RPTExtractor extractor = new RPTExtractor();
  extractor.InputRpt = incomingDocument.BinaryContent;
  
  // Dynamically set selection rule based on document attributes
  IF incomingDocument.DocumentType == "FULL_REPORT" THEN
    extractor.SelectionRule = "all";
  ELSE IF incomingDocument.DocumentType == "SUMMARY" THEN
    extractor.SelectionRule = "pages:1-5";
  ELSE IF incomingDocument.DocumentType == "SECTION_REPORT" THEN
    // Use section ID from document metadata
    extractor.SelectionRule = "section:" + incomingDocument.SectionId;
  ELSE
    extractor.SelectionRule = "all";
  ENDIF;
  
  extractor.ExtractPages();
  
  IF extractor.ToolReturnCode == 0 THEN
    outputDocument.TextContent = extractor.ExtractedText;
    outputDocument.BinaryContent = extractor.ExtractedBinary;
    outputDocument.Status = "EXTRACTED";
  ELSE
    RAISE ERROR "Extraction failed for " + incomingDocument.DocumentType;
  ENDIF;
END Process
```

## Return Codes and Error Handling

| Code | Meaning | Action in Papyrus |
|------|---------|------------------|
| 0 | Success | Proceed to next step |
| 1 | Invalid arguments | Logic error in shell method setup |
| 2 | Cannot open input RPT | Invalid/corrupted file, user error |
| 3 | Cannot write text output | Disk permission or space issue |
| 4 | Cannot write binary output | Disk permission or space issue |
| 5 | Invalid RPT format | File is not a valid .rpt file |
| 6 | Decompression error | Corrupted compressed data in RPT |
| 7 | No text pages found | RPT file contains no text data (empty) |
| 8 | Section ID(s) not found | Requested section IDs don't exist in file |
| 9 | Invalid selection rule format | Selection rule syntax is incorrect |
| 10 | Unknown error | Unhandled exception |

### Setting Up State Transitions

Use `ToolReturnCode` in Papyrus state transitions:

```
State: ProcessingRPT
  Event: Change
  Trigger: %ToolReturnCode% == 0
  Target State: ExtractedSuccessfully

State: ProcessingRPT
  Event: Change
  Trigger: %ToolReturnCode% == 2
  Target State: InputFileError
  
State: ProcessingRPT
  Event: Change
  Trigger: %ToolReturnCode% == 5
  Target State: InvalidRPTFormat
```

## Output Format

### Text Output (ExtractedText)

- **Format**: Plain text with form-feed (0x0C) separators
- **Content**: All pages concatenated in order
- **Page Separator**: Form-feed character + newline between pages
- **Use Cases**:
  - Direct import into document management systems
  - OCR post-processing
  - Full-text search indexing
  - Archive and retrieval systems

**Example file structure:**
```
[Page 1 Content]
[0x0C]
[Page 2 Content]
[0x0C]
[Page 3 Content]
```

### Binary Output (ExtractedBinary)

- **Format**: Auto-detected PDF or AFP
- **Detection**:
  - PDF magic bytes: `%PDF...`
  - AFP magic byte: `0x5A` (Structured Field Introducer)
- **Content**: Complete binary document, ready for rendering
- **Use Cases**:
  - Print-ready documents
  - Distribution systems
  - Archive with original formatting
  - Specialized AFP processors

## Performance Characteristics

### Execution Time Estimates

| File Size | Pages | Typical Time | Notes |
|-----------|-------|--------------|-------|
| 100 KB | 5 | <100 ms | Very fast |
| 1 MB | 50 | 200-500 ms | Fast |
| 10 MB | 500 | 1-2 sec | Acceptable |
| 50 MB | 2500 | 5-10 sec | Slower, watch memory |
| 100 MB | 5000 | 10-20 sec | Consider chunking |

### Memory Usage

- **Peak Memory**: Proportional to largest compressed page
- **Typical**: 10-50 MB for average documents
- **Max Safe**: ~500 MB per process
- **Recommendation**: Monitor for 500 concurrent users

### Scaling for 500 Concurrent Users

**Option 1: Process Pool**
- Run multiple instances in parallel
- Use load balancer to distribute requests
- Recommended: 5-10 worker processes

**Option 2: Sequential Queue**
- Queue extractions with worker thread pool
- Single bottleneck (sequential processing)
- Simpler but slower

**Option 3: Hybrid**
- Lightweight documents (< 10 MB): Process immediately
- Heavy documents (> 10 MB): Queue for background processing
- Recommended approach

## Integration with 4_Migration_Instances Workflow

This tool is designed to work with your existing migration setup:

### Folder Structure
```
4_Migration_Instances/
├── papyrus_rpt_page_extractor.exe    (Compiled binary)
├── papyrus_rpt_page_extractor.cpp    (Source)
├── rpt_page_extractor.cpp            (Reference implementation)
├── PAPYRUS_INTEGRATION_GUIDE.md      (This file)
└── results/
    └── [Papyrus-extracted files]
```

### Workflow Integration Points

1. **Input**: RPT files from your migration source (260271NL.RPT, 251110OD.RPT, etc.)
2. **Processing**: Papyrus shell method calls this executable
3. **Output**: Text and binary files ready for downstream processing

### Environment Variables (Optional)

You can set these in Papyrus or system environment:

```
RPT_EXTRACTOR_PATH=C:\IntelliSTOR_Migration\4_Migration_Instances\papyrus_rpt_page_extractor.exe
RPT_DEBUG=0  (Set to 1 for verbose logging)
```

## Testing and Verification

### Standalone Testing (Before Papyrus Integration)

```bash
# Test with sample RPT file
papyrus_rpt_page_extractor.exe ^
  "C:\path\to\260271NL.rpt" ^
  "all" ^
  "C:\output\extracted.txt" ^
  "C:\output\extracted.pdf"

# Check exit code
echo %ERRORLEVEL%
```

### In Papyrus

```
1. Upload an .rpt file through Papyrus
2. Trigger the ExtractPages() method
3. Monitor ToolReturnCode value
4. Verify ExtractedText and ExtractedBinary attributes are populated
5. Check output in document archive
```

## Troubleshooting

### "Cannot open input RPT file" (Exit Code 2)

**Causes:**
- File path is incorrect
- File permissions are restricted
- File is currently locked by another process

**Solutions:**
- Verify file exists: `dir "C:\path\file.rpt"`
- Check permissions: file should be readable by Papyrus service account
- Ensure no other program is accessing the .rpt file

### "Invalid RPT file format" (Exit Code 5)

**Causes:**
- File is not a valid IntelliSTOR .rpt file
- File is corrupted or truncated
- File header is malformed

**Solutions:**
- Use the reference `rpt_page_extractor --info` to verify file structure
- Test with known good .rpt files
- Check file integrity (size, last modified date)

### "Cannot write output file" (Exit Code 3 or 4)

**Causes:**
- Output directory doesn't exist
- No write permissions
- Disk is full
- Path contains invalid characters

**Solutions:**
- Pre-create output directory
- Check `TMPDIR` permissions
- Verify disk space (`df -h` on Linux/Mac, `dir C:\` on Windows)
- Ensure Papyrus service account has write access

### Slow Performance (> 10 seconds)

**Causes:**
- Very large RPT files (> 50 MB)
- Slow disk I/O
- Network latency (if files on network share)
- System resource contention

**Solutions:**
- Use local SSD for temporary files
- Implement extraction queuing for large batches
- Schedule batch extractions during off-peak hours
- Monitor system resources (CPU, RAM, disk I/O)

## Advanced Configuration

### Custom Processing Rules

Modify `papyrus_rpt_page_extractor.cpp` to support custom rules:

```cpp
// In papyrus_extract_rpt function:
if (segment_rule == "no_binary") {
    // Skip binary extraction
    bin_out.close();
    return 0;
}
else if (segment_rule == "section_14259") {
    // Extract only pages for section 14259
    // (requires section parsing logic)
}
```

Then recompile and redeploy.

### Batch Processing

Create a wrapper batch file:

```batch
@echo off
REM Batch process multiple RPT files for Papyrus

setlocal enabledelayedexpansion

FOR %%F IN (*.rpt) DO (
    echo Processing %%F...
    papyrus_rpt_page_extractor.exe "%%F" "all" "%%~nF.txt" "%%~nF.pdf"
    IF !ERRORLEVEL! NEQ 0 (
        echo ERROR processing %%F (code !ERRORLEVEL!)
    ) ELSE (
        echo SUCCESS: %%F processed
    )
)
```

## Performance Optimization Tips

1. **Use Local Storage**: Copy RPT files to local drive before processing
2. **Parallel Processing**: Run multiple extractor instances with different input files
3. **Memory Tuning**: Monitor page decompression for large files
4. **Caching**: Cache frequently-used RPT metadata
5. **Async Processing**: Queue large extractions for background processing

## Dependencies

### Runtime Requirements

- **Windows**: zlib1.dll (or static-linked)
- **macOS/Linux**: libz (system library)
- **C++ Runtime**: MSVC runtime (Windows), glibc (Linux)

### Compile-Time Requirements

- **C++17 Compiler**: MSVC, GCC 7+, or Clang 5+
- **zlib Development Headers**: zlib.h
- **Standard Library**: filesystem, iostream, etc.

### Optional

- **Papyrus**: 2020 SP1 or later
- **ExternalApplication Class**: For integration framework

## Support and Maintenance

### Logging and Debugging

Enable debug logging by modifying source:

```cpp
// In papyrus_rpt_page_extractor.cpp
static constexpr bool ENABLE_LOGGING = true;  // Change from false to true
```

Recompile and run. Debug messages will appear in `stderr`.

### Version Information

```cpp
// Version: 1.0
// Release: 2025-02-07
// Base: rpt_page_extractor.cpp (C++17 port)
// Optimization: Papyrus-specific file handling
```

### Contact and Issues

For issues with:
- **RPT file parsing**: Check rpt_page_extractor.cpp documentation
- **Papyrus integration**: Verify parameter line syntax and attributes
- **Build/compilation**: Ensure C++17 compiler and zlib installed

## See Also

- `rpt_page_extractor.cpp` - Full-featured CLI tool with advanced options
- `rpt_page_extractor.py` - Python reference implementation
- `RPT_PAGE_EXTRACTOR_GUIDE.md` - Original extraction tool guide
- `EXTRACT_INSTANCES_DOCUMENTATION.md` - Migration workflow documentation
