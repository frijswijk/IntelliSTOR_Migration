@echo off
REM ============================================================================
REM RPT Page Extractor Environment Variables - EXAMPLE
REM ============================================================================
REM
REM This is a template showing how to set environment variables for the
REM papyrus_rpt_page_extractor.bat wrapper script.
REM
REM Copy the relevant sections to your Migration_Environment.bat file,
REM or create a separate environment file for RPT extraction tasks.
REM
REM ============================================================================

REM ----------------------------------------------------------------------------
REM Example 1: Extract Pages 1-5 from a single RPT file
REM ----------------------------------------------------------------------------
set RPT_INPUT=C:\Reports\sample.rpt
set RPT_SELECTION=pages:1-5
set RPT_OUTPUT_TXT=C:\Output\pages_1_5.txt
set RPT_OUTPUT_BINARY=C:\Output\pages_1_5.pdf

REM ----------------------------------------------------------------------------
REM Example 2: Extract specific sections
REM ----------------------------------------------------------------------------
REM set RPT_INPUT=C:\Reports\monthly_report.rpt
REM set RPT_SELECTION=sections:14259,14260,14261
REM set RPT_OUTPUT_TXT=C:\Output\sections.txt
REM set RPT_OUTPUT_BINARY=C:\Output\sections.pdf

REM ----------------------------------------------------------------------------
REM Example 3: Extract all pages (with watermark if configured)
REM ----------------------------------------------------------------------------
REM set RPT_INPUT=C:\Reports\full_report.rpt
REM set RPT_SELECTION=all
REM set RPT_OUTPUT_TXT=C:\Output\full_report.txt
REM set RPT_OUTPUT_BINARY=C:\Output\full_report.pdf

REM ----------------------------------------------------------------------------
REM Example 4: Using shorthand section syntax
REM ----------------------------------------------------------------------------
REM set RPT_INPUT=C:\Reports\report.rpt
REM set RPT_SELECTION=14259,14260
REM set RPT_OUTPUT_TXT=C:\Output\output.txt
REM set RPT_OUTPUT_BINARY=C:\Output\output.pdf

REM ----------------------------------------------------------------------------
REM Example 5: Multiple page ranges
REM ----------------------------------------------------------------------------
REM set RPT_INPUT=C:\Reports\large_report.rpt
REM set RPT_SELECTION=pages:1-5,10-20,50-60
REM set RPT_OUTPUT_TXT=C:\Output\selected_pages.txt
REM set RPT_OUTPUT_BINARY=C:\Output\selected_pages.pdf

REM ============================================================================
REM NOTES:
REM ============================================================================
REM
REM 1. Selection Rule Formats:
REM    - "all"                      - Extract all pages
REM    - "pages:1-5"                - Pages 1 through 5
REM    - "pages:1-5,10-20"          - Multiple page ranges
REM    - "sections:14259"           - Single section by ID
REM    - "sections:14259,14260"     - Multiple sections
REM    - "14259,14260"              - Shorthand for sections
REM
REM 2. PDF Features (requires QPDF in ./tools/ or system PATH):
REM    - Extracts selected pages from PDF binaries
REM    - Applies watermark if image found at ./tools/watermarks/confidential.png
REM    - Preserves page orientation (portrait/landscape)
REM    - Falls back to full PDF extraction if QPDF not available
REM
REM 3. Output Files:
REM    - TXT: Concatenated text pages with form-feed (0x0C) separators
REM    - Binary: PDF/AFP binary object(s)
REM
REM 4. Use with wrapper script:
REM    call RPT_Environment_EXAMPLE.bat
REM    papyrus_rpt_page_extractor.bat
REM
REM    Or directly from command line:
REM    papyrus_rpt_page_extractor.bat input.rpt "pages:1-5" output.txt output.pdf
REM
REM ============================================================================

echo RPT Environment Variables Set:
echo   RPT_INPUT=%RPT_INPUT%
echo   RPT_SELECTION=%RPT_SELECTION%
echo   RPT_OUTPUT_TXT=%RPT_OUTPUT_TXT%
echo   RPT_OUTPUT_BINARY=%RPT_OUTPUT_BINARY%
echo.
