@echo off
REM ============================================================================
REM Watermark Image Creator using ImageMagick
REM ============================================================================
REM
REM This script creates common watermark images for use with the
REM papyrus_rpt_page_extractor_v2 tool.
REM
REM Prerequisites: ImageMagick must be installed
REM Download from: https://imagemagick.org/
REM

setlocal

REM ============================================================================
REM Configuration
REM ============================================================================

REM Find ImageMagick executable
set MAGICK_EXE=magick.exe
if exist "tools\magick.exe" set MAGICK_EXE=tools\magick.exe
if exist "C:\Users\freddievr\imagemagick\magick.exe" set MAGICK_EXE=C:\Users\freddievr\imagemagick\magick.exe
if exist "C:\Program Files\ImageMagick\magick.exe" set MAGICK_EXE=C:\Program Files\ImageMagick\magick.exe

REM Output directory
set OUTPUT_DIR=watermarks
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

REM ============================================================================
REM Check for ImageMagick
REM ============================================================================

"%MAGICK_EXE%" -version >nul 2>&1
if errorlevel 1 (
    echo ERROR: ImageMagick not found!
    echo Please install ImageMagick from https://imagemagick.org/
    echo Or place magick.exe in the tools\ directory
    pause
    exit /b 1
)

echo Found ImageMagick: %MAGICK_EXE%
echo Output directory: %OUTPUT_DIR%
echo.

REM ============================================================================
REM Create "CONFIDENTIAL" Watermarks
REM ============================================================================

echo Creating CONFIDENTIAL watermarks...

REM Red "CONFIDENTIAL" - High visibility
"%MAGICK_EXE%" -size 2000x400 xc:none ^
  -font Arial-Bold -pointsize 120 -gravity center ^
  -fill "rgba(255,0,0,0.8)" -annotate +0+0 "CONFIDENTIAL" ^
  "%OUTPUT_DIR%\confidential_red.png"

REM Gray "CONFIDENTIAL" - Subtle
"%MAGICK_EXE%" -size 2000x400 xc:none ^
  -font Arial-Bold -pointsize 120 -gravity center ^
  -fill "rgba(128,128,128,0.7)" -annotate +0+0 "CONFIDENTIAL" ^
  "%OUTPUT_DIR%\confidential_gray.png"

REM Black "CONFIDENTIAL" with border
"%MAGICK_EXE%" -size 2000x400 xc:none ^
  -font Arial-Bold -pointsize 120 -gravity center ^
  -stroke "rgba(255,0,0,0.8)" -strokewidth 3 ^
  -fill "rgba(0,0,0,0.6)" -annotate +0+0 "CONFIDENTIAL" ^
  "%OUTPUT_DIR%\confidential_bordered.png"

echo   - confidential_red.png
echo   - confidential_gray.png
echo   - confidential_bordered.png

REM ============================================================================
REM Create "DRAFT" Watermarks
REM ============================================================================

echo Creating DRAFT watermarks...

REM Gray "DRAFT"
"%MAGICK_EXE%" -size 1500x300 xc:none ^
  -font Arial-Bold -pointsize 100 -gravity center ^
  -fill "rgba(128,128,128,0.6)" -annotate +0+0 "DRAFT" ^
  "%OUTPUT_DIR%\draft.png"

REM Blue "DRAFT"
"%MAGICK_EXE%" -size 1500x300 xc:none ^
  -font Arial-Bold -pointsize 100 -gravity center ^
  -fill "rgba(0,0,255,0.6)" -annotate +0+0 "DRAFT" ^
  "%OUTPUT_DIR%\draft_blue.png"

REM "DRAFT" with timestamp placeholder
"%MAGICK_EXE%" -size 1500x400 xc:none ^
  -font Arial-Bold -pointsize 100 -gravity north ^
  -fill "rgba(128,128,128,0.6)" -annotate +0+20 "DRAFT" ^
  -font Arial -pointsize 40 -gravity south ^
  -fill "rgba(128,128,128,0.5)" -annotate +0+20 "Not for Distribution" ^
  "%OUTPUT_DIR%\draft_with_text.png"

echo   - draft.png
echo   - draft_blue.png
echo   - draft_with_text.png

REM ============================================================================
REM Create "SAMPLE" Watermarks
REM ============================================================================

echo Creating SAMPLE watermarks...

REM Orange "SAMPLE"
"%MAGICK_EXE%" -size 1800x350 xc:none ^
  -font Arial-Bold -pointsize 110 -gravity center ^
  -fill "rgba(255,140,0,0.6)" -annotate +0+0 "SAMPLE" ^
  "%OUTPUT_DIR%\sample.png"

echo   - sample.png

REM ============================================================================
REM Create "COPY" Watermarks
REM ============================================================================

echo Creating COPY watermarks...

REM Simple "COPY"
"%MAGICK_EXE%" -size 1200x300 xc:none ^
  -font Arial-Bold -pointsize 90 -gravity center ^
  -fill "rgba(128,128,128,0.5)" -annotate +0+0 "COPY" ^
  "%OUTPUT_DIR%\copy.png"

echo   - copy.png

REM ============================================================================
REM Create "DO NOT DISTRIBUTE" Watermarks
REM ============================================================================

echo Creating DO NOT DISTRIBUTE watermarks...

REM Red "DO NOT DISTRIBUTE"
"%MAGICK_EXE%" -size 2200x350 xc:none ^
  -font Arial-Bold -pointsize 90 -gravity center ^
  -fill "rgba(255,0,0,0.65)" -annotate +0+0 "DO NOT DISTRIBUTE" ^
  "%OUTPUT_DIR%\do_not_distribute.png"

echo   - do_not_distribute.png

REM ============================================================================
REM Create "INTERNAL USE ONLY" Watermarks
REM ============================================================================

echo Creating INTERNAL USE ONLY watermarks...

REM Blue "INTERNAL USE ONLY"
"%MAGICK_EXE%" -size 2200x350 xc:none ^
  -font Arial-Bold -pointsize 85 -gravity center ^
  -fill "rgba(0,0,139,0.6)" -annotate +0+0 "INTERNAL USE ONLY" ^
  "%OUTPUT_DIR%\internal_use_only.png"

echo   - internal_use_only.png

REM ============================================================================
REM Create Small Stamp-Style Watermarks
REM ============================================================================

echo Creating stamp-style watermarks...

REM Small "CONFIDENTIAL" stamp
"%MAGICK_EXE%" -size 800x200 xc:none ^
  -font Arial-Bold -pointsize 50 -gravity center ^
  -stroke "rgba(255,0,0,0.8)" -strokewidth 2 ^
  -fill "rgba(255,0,0,0.2)" -annotate +0+0 "CONFIDENTIAL" ^
  -bordercolor "rgba(255,0,0,0.8)" -border 5x5 ^
  "%OUTPUT_DIR%\stamp_confidential.png"

REM Small "APPROVED" stamp
"%MAGICK_EXE%" -size 600x200 xc:none ^
  -font Arial-Bold -pointsize 50 -gravity center ^
  -stroke "rgba(0,128,0,0.8)" -strokewidth 2 ^
  -fill "rgba(0,128,0,0.3)" -annotate +0+0 "APPROVED" ^
  -bordercolor "rgba(0,128,0,0.8)" -border 5x5 ^
  "%OUTPUT_DIR%\stamp_approved.png"

REM Small "VOID" stamp
"%MAGICK_EXE%" -size 600x200 xc:none ^
  -font Arial-Bold -pointsize 60 -gravity center ^
  -stroke "rgba(255,0,0,0.8)" -strokewidth 3 ^
  -fill "rgba(255,0,0,0.2)" -annotate +0+0 "VOID" ^
  -bordercolor "rgba(255,0,0,0.8)" -border 5x5 ^
  "%OUTPUT_DIR%\stamp_void.png"

echo   - stamp_confidential.png
echo   - stamp_approved.png
echo   - stamp_void.png

REM ============================================================================
REM Create Diagonal Pattern Watermarks (for Repeat mode)
REM ============================================================================

echo Creating pattern watermarks for Repeat mode...

REM Small "CONFIDENTIAL" for tiling
"%MAGICK_EXE%" -size 800x200 xc:none ^
  -font Arial-Bold -pointsize 45 -gravity center ^
  -fill "rgba(200,0,0,0.15)" -annotate +0+0 "CONFIDENTIAL" ^
  "%OUTPUT_DIR%\pattern_confidential.png"

REM Small "DRAFT" for tiling
"%MAGICK_EXE%" -size 600x150 xc:none ^
  -font Arial-Bold -pointsize 40 -gravity center ^
  -fill "rgba(128,128,128,0.15)" -annotate +0+0 "DRAFT" ^
  "%OUTPUT_DIR%\pattern_draft.png"

echo   - pattern_confidential.png
echo   - pattern_draft.png

REM ============================================================================
REM Summary
REM ============================================================================

echo.
echo ============================================================================
echo Watermark images created successfully in: %OUTPUT_DIR%\
echo ============================================================================
echo.
echo Standard watermarks (for Center, TopRight, etc.):
echo   - confidential_red.png, confidential_gray.png, confidential_bordered.png
echo   - draft.png, draft_blue.png, draft_with_text.png
echo   - sample.png, copy.png
echo   - do_not_distribute.png, internal_use_only.png
echo.
echo Stamp watermarks (for BottomRight with small scale):
echo   - stamp_confidential.png, stamp_approved.png, stamp_void.png
echo.
echo Pattern watermarks (for Repeat mode with small scale):
echo   - pattern_confidential.png, pattern_draft.png
echo.
echo Usage example:
echo   papyrus_rpt_page_extractor_v2.exe input.rpt all output.txt output.pdf ^
echo     --WatermarkImage %OUTPUT_DIR%\confidential_red.png ^
echo     --WatermarkPosition Center --WatermarkRotation -45 --WatermarkOpacity 30
echo.

endlocal
pause
