# Papyrus RPT Page Extractor - Selection Rule Examples

## Overview

The `SelectionRule` parameter controls which pages are extracted from an RPT file. This document provides practical examples for common scenarios.

---

## Example 1: Extract All Pages

### Scenario
User uploads a complete RPT file and wants all pages extracted.

### Papyrus Code
```javascript
extractor.SelectionRule = "all";
extractor.ExtractPages();
```

### Command Line (Testing)
```bash
papyrus_rpt_page_extractor.exe input.rpt "all" output.txt output.pdf
```

### What Happens
- All pages from the RPT file are decompressed
- All pages concatenated into `output.txt` (separated by form-feed characters)
- Binary objects (if present) written to `output.pdf`

### Output Example
```
[Page 1 content]
<0x0C>
[Page 2 content]
<0x0C>
...
[Page 150 content]
```

---

## Example 2: Extract Specific Page Range

### Scenario
User wants only pages 10-20 from a 150-page RPT file (e.g., a summary section).

### Papyrus Code
```javascript
extractor.SelectionRule = "pages:10-20";
extractor.ExtractPages();
```

### Command Line (Testing)
```bash
papyrus_rpt_page_extractor.exe input.rpt "pages:10-20" output.txt output.pdf
```

### What Happens
- Only pages 10, 11, 12, ..., 20 are decompressed (11 pages total)
- These 11 pages concatenated into `output.txt`
- Performance: 10x faster than extracting all 150 pages
- Binary objects still included (if present)

### Return Code
- 0 = Success (pages 10-20 found and extracted)
- 7 = Error (no pages in that range exist)

---

## Example 3: Extract Single Page

### Scenario
User wants only the cover page (page 1) from an RPT file.

### Papyrus Code
```javascript
extractor.SelectionRule = "pages:1";
extractor.ExtractPages();
```

### Command Line (Testing)
```bash
papyrus_rpt_page_extractor.exe input.rpt "pages:1" output.txt output.pdf
```

### What Happens
- Only page 1 is decompressed
- Single page written to `output.txt` (no separators needed)
- Very fast execution (<100 ms typically)

---

## Example 4: Extract One Section

### Scenario
RPT file has multiple sections (e.g., section 14259, 14260, 14261). User wants only section 14259.

### Get Available Sections First
Use the reference tool to see what sections exist:
```bash
rpt_page_extractor --info input.rpt

# Output shows:
# Sections (3):
#   SECTION_ID  START_PAGE  PAGE_COUNT
#   ----------  ----------  ----------
#        14259           1          30
#        14260          31          25
#        14261          56          95
```

### Papyrus Code
```javascript
extractor.SelectionRule = "section:14259";
extractor.ExtractPages();
```

### Command Line (Testing)
```bash
papyrus_rpt_page_extractor.exe input.rpt "section:14259" output.txt output.pdf
```

### What Happens
- Pages 1-30 are extracted (section 14259 spans pages 1-30)
- 30 pages concatenated into `output.txt`
- Binary objects included if present

### Return Code
- 0 = Success (section 14259 found)
- 8 = Error (section 14259 not found in file)

---

## Example 5: Extract Multiple Sections

### Scenario
User wants pages from sections 14259 and 14261, skipping section 14260 in the middle.

### Papyrus Code
```javascript
// Comma-separated list, NO SPACES
extractor.SelectionRule = "sections:14259,14261";
extractor.ExtractPages();
```

### Command Line (Testing)
```bash
papyrus_rpt_page_extractor.exe input.rpt "sections:14259,14261" output.txt output.pdf
```

### What Happens
- Pages from section 14259 (pages 1-30) collected first
- Pages from section 14261 (pages 56-95) collected next
- Total 75 pages concatenated into `output.txt` in order
- Pages from section 14260 (pages 31-55) NOT included

### Output Example (Conceptual)
```
[Pages 1-30 from section 14259]
<0x0C>
[Pages 56-95 from section 14261]
```

### Return Code
- 0 = Success (both sections found)
- 8 = Error (neither section found)
- 0 = Partial success (one section found, other missing - still returns 0!)

---

## Example 6: Multiple Sections with Missing IDs

### Scenario
User requests sections 14259, 99999 (doesn't exist), and 14261.

### Papyrus Code
```javascript
// Section 99999 doesn't exist in the file, but request it anyway
extractor.SelectionRule = "sections:14259,99999,14261";
extractor.ExtractPages();
```

### What Happens
- Section 14259 found → pages 1-30 collected ✓
- Section 99999 NOT found → silently skipped ✓
- Section 14261 found → pages 56-95 collected ✓
- **Total:** 75 pages extracted (sections 14259 + 14261)
- **Return Code:** 0 (Success, because at least one section was found)

### Key Difference from Reference Tool
The reference tool requires ALL section IDs to exist. The Papyrus version gracefully skips missing IDs and succeeds as long as at least one is found.

---

## Example 7: Dynamic Selection Based on Document Properties

### Scenario
Workflow needs different extraction strategies based on document type.

### Papyrus Code
```javascript
// Determine selection rule based on document properties
IF incomingDocument.Type == "FULL_REPORT" THEN
  extractor.SelectionRule = "all";
  
ELSE IF incomingDocument.Type == "EXECUTIVE_SUMMARY" THEN
  extractor.SelectionRule = "pages:1-5";  // First 5 pages only
  
ELSE IF incomingDocument.Type == "SECTION_EXTRACT" THEN
  // Section ID stored in document metadata
  extractor.SelectionRule = "section:" + incomingDocument.SectionId;
  
ELSE IF incomingDocument.Type == "MULTI_SECTION" THEN
  // Multiple sections stored as comma-separated string
  // Example: metadata contains "14259,14260,14261"
  extractor.SelectionRule = "sections:" + incomingDocument.SectionIds;
  
ELSE
  extractor.SelectionRule = "all";  // Default to all pages
ENDIF;

extractor.ExtractPages();
```

### Performance Implications
- "EXECUTIVE_SUMMARY": 5-page extract → ~50ms execution
- "FULL_REPORT": All pages → 1-5 second execution depending on file size
- "SECTION_EXTRACT": One section → 200-500ms depending on section size

---

## Example 8: Error Handling for Selection Rules

### Scenario
Handle common errors that might occur with selection rules.

### Papyrus Code
```javascript
// Attempt extraction with error handling
extractor.SelectionRule = "pages:10-20";
extractor.ExtractPages();

IF extractor.ToolReturnCode == 0 THEN
  // Success
  outputDocument.Content = extractor.ExtractedText;
  outputDocument.Status = "SUCCESS";
  
ELSE IF extractor.ToolReturnCode == 9 THEN
  // Invalid selection rule format
  // Likely causes: malformed string, wrong syntax
  RAISE ERROR "Invalid selection rule format: " + extractor.SelectionRule;
  
ELSE IF extractor.ToolReturnCode == 8 THEN
  // Section ID not found
  // Likely causes: wrong section ID, section doesn't exist
  RAISE ERROR "Requested section not found in RPT file";
  
ELSE IF extractor.ToolReturnCode == 7 THEN
  // No text pages in range
  // Likely causes: page range exceeds file, all pages are binary
  RAISE ERROR "No text pages found in selection";
  
ELSE IF extractor.ToolReturnCode == 2 THEN
  // Cannot open input file
  RAISE ERROR "Input RPT file is invalid or inaccessible";
  
ELSE
  RAISE ERROR "Extraction failed with code " + extractor.ToolReturnCode;
ENDIF;
```

---

## Example 9: Complex Workflow with Fallback

### Scenario
Try to extract by section, fallback to all pages if section not found.

### Papyrus Code
```javascript
// Attempt section-based extraction
sectionId = incomingDocument.SectionId;  // e.g., 14259
extractor.SelectionRule = "section:" + sectionId;
extractor.ExtractPages();

IF extractor.ToolReturnCode == 0 THEN
  // Section extraction succeeded
  outputDocument.Content = extractor.ExtractedText;
  outputDocument.ExtractionType = "SECTION";
  
ELSE IF extractor.ToolReturnCode == 8 THEN
  // Section not found, fallback to all pages
  LOG "Section " + sectionId + " not found, extracting all pages";
  extractor.SelectionRule = "all";
  extractor.ExtractPages();
  
  IF extractor.ToolReturnCode == 0 THEN
    outputDocument.Content = extractor.ExtractedText;
    outputDocument.ExtractionType = "FULL";
  ELSE
    RAISE ERROR "Extraction failed even with fallback";
  ENDIF;
  
ELSE
  // Other errors
  RAISE ERROR "Extraction failed: code " + extractor.ToolReturnCode;
ENDIF;
```

---

## Example 10: Batch Processing with Selection Rules

### Scenario
Process multiple RPT files with different selection rules.

### Papyrus Code
```javascript
// Configuration table mapping file types to selection rules
rules = {
  "INVOICE": "pages:1-1",
  "FULL_REPORT": "all",
  "SUMMARY": "pages:1-10",
  "SECTION_14259": "section:14259",
  "SECTIONS_COMBINED": "sections:14259,14260,14261"
};

// Process each document
FOR EACH document IN documents DO
  extractor = new RPTExtractor();
  extractor.InputRpt = document.BinaryContent;
  
  // Look up selection rule for this document type
  IF rules.ContainsKey(document.Type) THEN
    extractor.SelectionRule = rules[document.Type];
  ELSE
    extractor.SelectionRule = "all";  // Default
  ENDIF;
  
  extractor.ExtractPages();
  
  IF extractor.ToolReturnCode == 0 THEN
    document.ExtractedText = extractor.ExtractedText;
    document.Status = "EXTRACTED";
  ELSE
    document.Status = "FAILED";
    document.ErrorCode = extractor.ToolReturnCode;
  ENDIF;
ENDFOR;
```

---

## Selection Rule Syntax Quick Reference

| Rule | Syntax | Notes |
|------|--------|-------|
| All | `all` | Extracts all pages in RPT file |
| Range | `pages:10-20` | 1-based, inclusive (pages 10 through 20) |
| Single | `pages:5` | Only page 5 |
| Section | `section:14259` | Only pages in that section |
| Sections | `sections:14259,14260,14261` | Multiple sections, comma-separated, NO SPACES |

---

## Common Mistakes and Fixes

### Mistake 1: Spaces in Multi-Section Rule
```javascript
// ❌ WRONG - has spaces after commas
extractor.SelectionRule = "sections:14259, 14260, 14261";

// ✅ CORRECT - no spaces
extractor.SelectionRule = "sections:14259,14260,14261";
```

### Mistake 2: Wrong Case in Rule Name
```javascript
// ❌ WRONG - wrong case
extractor.SelectionRule = "Pages:10-20";  // Should be lowercase "pages"
extractor.SelectionRule = "Section:14259"; // Should be lowercase "section"

// ✅ CORRECT - lowercase
extractor.SelectionRule = "pages:10-20";
extractor.SelectionRule = "section:14259";
```

### Mistake 3: Mixing Rule Types
```javascript
// ❌ WRONG - can't mix pages and sections
extractor.SelectionRule = "pages:10-20 section:14259";

// ✅ CORRECT - choose one approach
extractor.SelectionRule = "pages:10-20";      // Use pages
// OR
extractor.SelectionRule = "section:14259";    // Use section
```

### Mistake 4: Invalid Page Range
```javascript
// ❌ WRONG - end before start
extractor.SelectionRule = "pages:20-10";

// ✅ CORRECT - start before end
extractor.SelectionRule = "pages:10-20";
```

### Mistake 5: Non-existent Section Without Fallback
```javascript
// ❌ PROBLEMATIC - will fail if section doesn't exist
extractor.SelectionRule = "section:99999";
extractor.ExtractPages();
if (extractor.ToolReturnCode != 0) ...  // Unhandled error

// ✅ BETTER - handle missing section gracefully
extractor.SelectionRule = "section:99999";
extractor.ExtractPages();
if (extractor.ToolReturnCode == 8) {
  // Section not found, retry with all pages
  extractor.SelectionRule = "all";
  extractor.ExtractPages();
}
```

---

## Performance Characteristics by Selection Rule

| Rule | Typical Performance | Notes |
|------|-------------------|-------|
| `all` (150 pages) | 1-2 seconds | Full file processing |
| `pages:1-5` | 100-200 ms | Fast, only 5 pages |
| `pages:75` | 50-100 ms | Single page, very fast |
| `section:14259` (30 pages) | 300-500 ms | Section extraction |
| `sections:14259,14260` (55 pages) | 600-800 ms | Multiple sections |

Use page ranges or sections for better performance on large RPT files!

---

## Real-World Example: Loan Document Processing

### Scenario
Process loan application documents in an RPT file:
- Page 1: Cover page
- Pages 2-5: Personal information section (section 14259)
- Pages 6-15: Financial information section (section 14260)
- Pages 16+: Supporting documents section (section 14261)

### Papyrus Workflow
```javascript
// Step 1: Extract cover page
cover.SelectionRule = "pages:1";
cover.ExtractPages();

// Step 2: Extract personal information
personal.SelectionRule = "section:14259";
personal.ExtractPages();

// Step 3: Extract financial information
financial.SelectionRule = "section:14260";
financial.ExtractPages();

// Step 4: Extract supporting documents
supporting.SelectionRule = "section:14261";
supporting.ExtractPages();

// All completed in parallel or sequence based on workflow requirements
```

### Performance
- Cover page extraction: ~50ms
- Personal info: ~300ms
- Financial info: ~400ms
- Supporting: ~500ms
- **Total: ~1.25 seconds** for full loan document processing

Compare to extracting all pages at once: ~3 seconds (2.4x slower!)

---

## Testing Selection Rules

### Quick Test Script
```bash
#!/bin/bash
# Test all selection rule formats

echo "Testing: all"
papyrus_rpt_page_extractor.exe test.rpt "all" out1.txt out1.pdf

echo "Testing: pages:1-10"
papyrus_rpt_page_extractor.exe test.rpt "pages:1-10" out2.txt out2.pdf

echo "Testing: pages:5"
papyrus_rpt_page_extractor.exe test.rpt "pages:5" out3.txt out3.pdf

echo "Testing: section:14259"
papyrus_rpt_page_extractor.exe test.rpt "section:14259" out4.txt out4.pdf

echo "Testing: sections:14259,14260"
papyrus_rpt_page_extractor.exe test.rpt "sections:14259,14260" out5.txt out5.pdf

echo "All tests completed"
```

---

## Summary

Selection rules provide flexible, efficient page extraction from RPT files:

- **"all"** - Complete file extraction
- **"pages:X-Y"** - Extract specific range (fast!)
- **"pages:N"** - Extract single page (fastest!)
- **"section:ID"** - Extract by section
- **"sections:ID1,ID2,..."** - Extract multiple sections

Choose the right rule for your use case to optimize performance and reduce resource consumption!
