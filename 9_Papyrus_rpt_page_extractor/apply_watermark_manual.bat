@echo off
REM Manual Watermark Application Script
REM Usage: apply_watermark_manual.bat <input.pdf> <output.pdf> <watermark.png>
REM
REM Example:
REM   apply_watermark_manual.bat F:\RPT\260271Q7.PDF F:\RPT\260271Q7_watermarked.PDF F:\RPT\confidential.png

setlocal

if "%~3"=="" (
    echo Usage: %~nx0 input.pdf output.pdf watermark.png
    echo.
    echo Example:
    echo   %~nx0 F:\RPT\input.PDF F:\RPT\output.PDF F:\RPT\confidential.png
    pause
    exit /b 1
)

set INPUT_PDF=%~1
set OUTPUT_PDF=%~2
set WATERMARK_IMG=%~3

REM Tool paths
set MAGICK=C:\Users\freddievr\imagemagick\magick.exe
set QPDF=C:\Users\freddievr\qpdf-12.3.2-mingw64\bin\qpdf.exe

REM Check if tools exist
if not exist "%MAGICK%" (
    echo ERROR: ImageMagick not found at %MAGICK%
    pause
    exit /b 1
)

if not exist "%QPDF%" (
    echo ERROR: QPDF not found at %QPDF%
    pause
    exit /b 1
)

if not exist "%INPUT_PDF%" (
    echo ERROR: Input PDF not found: %INPUT_PDF%
    pause
    exit /b 1
)

if not exist "%WATERMARK_IMG%" (
    echo ERROR: Watermark image not found: %WATERMARK_IMG%
    pause
    exit /b 1
)

echo ============================================================================
echo Applying Watermark
echo ============================================================================
echo Input PDF: %INPUT_PDF%
echo Output PDF: %OUTPUT_PDF%
echo Watermark: %WATERMARK_IMG%
echo.

REM Step 1: Prepare watermark image (resize, rotate, set opacity)
echo Step 1: Preparing watermark image...
set PROCESSED_WM=%TEMP%\watermark_processed.png
"%MAGICK%" "%WATERMARK_IMG%" -resize 300 -rotate -45 -alpha set -channel A -evaluate multiply 0.3 +channel "%PROCESSED_WM%"
if errorlevel 1 (
    echo ERROR: Failed to process watermark image
    pause
    exit /b 1
)

REM Step 2: Create watermark PDF
echo Step 2: Creating watermark PDF...
set WATERMARK_PDF=%TEMP%\watermark.pdf
"%MAGICK%" -size 612x792 xc:none "%PROCESSED_WM%" -gravity center -composite "%WATERMARK_PDF%"
if errorlevel 1 (
    echo ERROR: Failed to create watermark PDF
    pause
    exit /b 1
)

REM Step 3: Apply watermark to PDF using QPDF overlay
echo Step 3: Applying watermark to PDF...
"%QPDF%" "%INPUT_PDF%" --overlay "%WATERMARK_PDF%" --to=1-z --repeat=1-z -- "%OUTPUT_PDF%"
if errorlevel 1 (
    echo ERROR: Failed to apply watermark
    pause
    exit /b 1
)

REM Cleanup
del "%PROCESSED_WM%" 2>nul
del "%WATERMARK_PDF%" 2>nul

echo.
echo ============================================================================
echo SUCCESS: Watermarked PDF created
echo ============================================================================
echo Output: %OUTPUT_PDF%
echo.

endlocal
