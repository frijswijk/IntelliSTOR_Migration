@echo off
REM ============================================================================
REM RPT File Builder Environment Variables - EXAMPLE
REM ============================================================================
REM
REM This is a template showing how to set environment variables for the
REM rpt_file_builder_wrapper.bat script.
REM
REM Copy the relevant sections to your Migration_Environment.bat file,
REM or create a separate environment file for RPT building tasks.
REM
REM ============================================================================

REM ----------------------------------------------------------------------------
REM Example 1: Build text-only RPT from a directory of pages
REM ----------------------------------------------------------------------------
set RPT_BUILDER_INPUT=C:\Reports\extracted\pages\
set RPT_BUILDER_OUTPUT=C:\Output\rebuilt_report.RPT
set RPT_SPECIES=49626
set RPT_DOMAIN=1

REM ----------------------------------------------------------------------------
REM Example 2: Build RPT from directory with embedded PDF binary
REM ----------------------------------------------------------------------------
REM set RPT_BUILDER_INPUT=C:\Reports\extracted\pages\
REM set RPT_BUILDER_OUTPUT=C:\Output\report_with_pdf.RPT
REM set RPT_SPECIES=52759
REM set RPT_DOMAIN=1
REM set RPT_BINARY=C:\Reports\binaries\report.pdf

REM ----------------------------------------------------------------------------
REM Example 3: Build RPT using template for metadata (roundtrip rebuild)
REM ----------------------------------------------------------------------------
REM set RPT_BUILDER_INPUT=C:\Reports\extracted\pages\
REM set RPT_BUILDER_OUTPUT=C:\Output\roundtrip.RPT
REM set RPT_SPECIES=49626
REM set RPT_DOMAIN=1
REM set RPT_TEMPLATE=C:\Reports\original.RPT

REM ----------------------------------------------------------------------------
REM Example 4: Build from specific page files (not a directory)
REM ----------------------------------------------------------------------------
REM set RPT_BUILDER_INPUT=C:\Reports\page_00001.txt C:\Reports\page_00002.txt
REM set RPT_BUILDER_OUTPUT=C:\Output\custom.RPT
REM set RPT_SPECIES=49626
REM set RPT_DOMAIN=1

REM ============================================================================
REM NOTES:
REM ============================================================================
REM
REM 1. Required Variables:
REM    - RPT_BUILDER_INPUT: Path to directory with page_*.txt files, or individual file paths
REM    - RPT_BUILDER_OUTPUT: Output .RPT file path
REM
REM 2. Optional Variables:
REM    - RPT_SPECIES: Report species ID (default: 0)
REM    - RPT_DOMAIN: Domain ID (default: 1)
REM    - RPT_BINARY: Path to PDF or AFP file to embed (optional)
REM    - RPT_TEMPLATE: Reference RPT to copy metadata from (optional)
REM
REM 3. Input Directory Structure (auto-detected):
REM    pages/
REM      ├── page_00001.txt
REM      ├── page_00002.txt
REM      ├── page_00003.txt
REM      ├── object_header.txt    (optional - becomes page 1 if binary present)
REM      └── report.pdf           (optional - auto-detected as binary)
REM
REM 4. Advanced Options (use command-line for these):
REM    --section SECTION_ID:START_PAGE:PAGE_COUNT
REM    --section-csv <file>
REM    --timestamp "YYYY/MM/DD HH:MM:SS.mmm"
REM    --line-width <n>
REM    --lines-per-page <n>
REM    --info (dry run)
REM    --verbose
REM
REM    For advanced options, use command-line directly:
REM    rpt_file_builder.exe --species 49626 --section 14259:1:10 -o output.RPT ./pages/
REM
REM 5. Use with wrapper script:
REM    call RPT_Builder_Environment_EXAMPLE.bat
REM    rpt_file_builder_wrapper.bat
REM
REM    Or directly from command line:
REM    rpt_file_builder_wrapper.bat ./pages/ output.RPT --species 49626 --domain 1
REM
REM ============================================================================

echo RPT Builder Environment Variables Set:
echo   RPT_BUILDER_INPUT=%RPT_BUILDER_INPUT%
echo   RPT_BUILDER_OUTPUT=%RPT_BUILDER_OUTPUT%
echo   RPT_SPECIES=%RPT_SPECIES%
echo   RPT_DOMAIN=%RPT_DOMAIN%
if "%RPT_BINARY%" NEQ "" echo   RPT_BINARY=%RPT_BINARY%
if "%RPT_TEMPLATE%" NEQ "" echo   RPT_TEMPLATE=%RPT_TEMPLATE%
echo.
