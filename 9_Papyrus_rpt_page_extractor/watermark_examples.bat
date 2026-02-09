@echo off
REM ============================================================================
REM Watermark Examples for papyrus_rpt_page_extractor_v2
REM ============================================================================
REM
REM This batch file demonstrates various watermark configurations.
REM Uncomment the example you want to run.
REM

setlocal

REM ============================================================================
REM Configuration - EDIT THESE PATHS
REM ============================================================================

set EXTRACTOR=papyrus_rpt_page_extractor_v2.exe
set INPUT_RPT=test_input.rpt
set OUTPUT_TXT=output.txt
set OUTPUT_PDF=output.pdf

REM Watermark image paths - create or use your own
set WM_CONFIDENTIAL=watermarks\confidential.png
set WM_DRAFT=watermarks\draft.png
set WM_LOGO=watermarks\company_logo.png

REM ============================================================================
REM Example 1: No Watermark (Default Behavior)
REM ============================================================================
REM This works exactly like the original extractor

REM %EXTRACTOR% %INPUT_RPT% all %OUTPUT_TXT% %OUTPUT_PDF%

REM ============================================================================
REM Example 2: Simple Centered Watermark (30% opacity)
REM ============================================================================
REM Basic watermark with all default settings

REM %EXTRACTOR% %INPUT_RPT% all %OUTPUT_TXT% %OUTPUT_PDF% ^
REM   --WatermarkImage %WM_CONFIDENTIAL%

REM ============================================================================
REM Example 3: Top-Right Corner Logo (50% opacity)
REM ============================================================================
REM Company logo in top-right, semi-transparent

REM %EXTRACTOR% %INPUT_RPT% pages:1-10 %OUTPUT_TXT% %OUTPUT_PDF% ^
REM   --WatermarkImage %WM_LOGO% ^
REM   --WatermarkPosition TopRight ^
REM   --WatermarkOpacity 50 ^
REM   --WatermarkScale 0.6

REM ============================================================================
REM Example 4: Diagonal "CONFIDENTIAL" Banner (45 degrees)
REM ============================================================================
REM Classic diagonal watermark across the center

REM %EXTRACTOR% %INPUT_RPT% all %OUTPUT_TXT% %OUTPUT_PDF% ^
REM   --WatermarkImage %WM_CONFIDENTIAL% ^
REM   --WatermarkPosition Center ^
REM   --WatermarkRotation -45 ^
REM   --WatermarkOpacity 25 ^
REM   --WatermarkScale 1.8

REM ============================================================================
REM Example 5: Tiled/Repeated Watermark Pattern
REM ============================================================================
REM Creates a pattern of watermarks across the entire page

REM %EXTRACTOR% %INPUT_RPT% all %OUTPUT_TXT% %OUTPUT_PDF% ^
REM   --WatermarkImage %WM_CONFIDENTIAL% ^
REM   --WatermarkPosition Repeat ^
REM   --WatermarkOpacity 15 ^
REM   --WatermarkScale 0.4

REM ============================================================================
REM Example 6: Small Bottom-Right "DRAFT" Stamp
REM ============================================================================
REM Like a traditional stamp in the corner

REM %EXTRACTOR% %INPUT_RPT% sections:14259,14260 %OUTPUT_TXT% %OUTPUT_PDF% ^
REM   --WatermarkImage %WM_DRAFT% ^
REM   --WatermarkPosition BottomRight ^
REM   --WatermarkOpacity 75 ^
REM   --WatermarkScale 0.3

REM ============================================================================
REM Example 7: Prominent Centered Watermark (Large & Opaque)
REM ============================================================================
REM For very visible watermarking

REM %EXTRACTOR% %INPUT_RPT% all %OUTPUT_TXT% %OUTPUT_PDF% ^
REM   --WatermarkImage %WM_CONFIDENTIAL% ^
REM   --WatermarkPosition Center ^
REM   --WatermarkOpacity 60 ^
REM   --WatermarkScale 2.0

REM ============================================================================
REM Example 8: Rotated Top-Center Watermark
REM ============================================================================
REM Watermark at top, rotated 15 degrees

REM %EXTRACTOR% %INPUT_RPT% pages:1-5 %OUTPUT_TXT% %OUTPUT_PDF% ^
REM   --WatermarkImage %WM_LOGO% ^
REM   --WatermarkPosition TopCenter ^
REM   --WatermarkRotation 15 ^
REM   --WatermarkOpacity 40 ^
REM   --WatermarkScale 0.8

REM ============================================================================
REM Example 9: Subtle Bottom Watermark
REM ============================================================================
REM Very faint watermark at bottom center

REM %EXTRACTOR% %INPUT_RPT% all %OUTPUT_TXT% %OUTPUT_PDF% ^
REM   --WatermarkImage %WM_LOGO% ^
REM   --WatermarkPosition BottomCenter ^
REM   --WatermarkOpacity 20 ^
REM   --WatermarkScale 0.5

REM ============================================================================
REM Example 10: Multi-Page with Different Sections
REM ============================================================================
REM Extract specific sections with watermark

REM %EXTRACTOR% %INPUT_RPT% sections:14259,14260,14261 %OUTPUT_TXT% %OUTPUT_PDF% ^
REM   --WatermarkImage %WM_CONFIDENTIAL% ^
REM   --WatermarkPosition Center ^
REM   --WatermarkRotation -45 ^
REM   --WatermarkOpacity 30 ^
REM   --WatermarkScale 1.5

REM ============================================================================
REM Batch Processing Example
REM ============================================================================
REM Process multiple RPT files with the same watermark settings

REM for %%f in (*.rpt) do (
REM     echo Processing %%f...
REM     %EXTRACTOR% "%%f" all "%%~nf.txt" "%%~nf.pdf" ^
REM       --WatermarkImage %WM_CONFIDENTIAL% ^
REM       --WatermarkPosition Center ^
REM       --WatermarkRotation -45 ^
REM       --WatermarkOpacity 30
REM )

REM ============================================================================

echo.
echo To run an example, edit this batch file and uncomment the desired example.
echo.
echo Current configuration:
echo   Extractor: %EXTRACTOR%
echo   Input RPT: %INPUT_RPT%
echo   Output TXT: %OUTPUT_TXT%
echo   Output PDF: %OUTPUT_PDF%
echo.

endlocal
pause
