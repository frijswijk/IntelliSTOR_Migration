@echo off
REM Wrapper to apply watermark from C++ program
REM Usage: apply_watermark_wrapper.bat <input.pdf> <output.pdf> <watermark.png> <rotation> <opacity> <gravity> <scale>

set INPUT_PDF=%~1
set OUTPUT_PDF=%~2
set WATERMARK_IMG=%~3
set ROTATION=%~4
set OPACITY=%~5
set GRAVITY=%~6
set SCALE_PERCENT=%~7

REM Calculate resize value based on scale percentage (base size 300 pixels)
REM Scale percent: 100 = 1.0, 200 = 2.0, 50 = 0.5
set /a RESIZE_WIDTH=300*%SCALE_PERCENT%/100
if "%RESIZE_WIDTH%"=="" set RESIZE_WIDTH=300
if %RESIZE_WIDTH% LSS 50 set RESIZE_WIDTH=50

REM Tool paths
set MAGICK=C:\Users\freddievr\imagemagick\magick.exe
set QPDF=C:\Users\freddievr\qpdf-12.3.2-mingw64\bin\qpdf.exe

REM Step 1: Prepare watermark image
set PROCESSED_WM=%TEMP%\watermark_processed_%RANDOM%.png
echo Step 1: Processing watermark image... >&2
"%MAGICK%" "%WATERMARK_IMG%" -resize %RESIZE_WIDTH% -rotate %ROTATION% "%PROCESSED_WM%"
if errorlevel 1 (
    echo ERROR: Failed to process watermark image >&2
    exit /b 1
)

REM Step 2: Create watermark PDF
set WATERMARK_PDF=%TEMP%\watermark_%RANDOM%.pdf
echo Step 2: Creating watermark PDF... >&2
"%MAGICK%" -size 612x792 xc:none "%PROCESSED_WM%" -gravity %GRAVITY% -compose dissolve -define compose:args=%OPACITY% -composite "%WATERMARK_PDF%"
if errorlevel 1 (
    echo ERROR: Failed to create watermark PDF >&2
    del "%PROCESSED_WM%" 2>nul
    exit /b 1
)

REM Step 3: Apply watermark to PDF using QPDF overlay
echo Step 3: Applying watermark overlay... >&2
"%QPDF%" "%INPUT_PDF%" --overlay "%WATERMARK_PDF%" --to=1-z --repeat=1-z -- "%OUTPUT_PDF%"
set RESULT=%ERRORLEVEL%
if not %RESULT%==0 (
    echo ERROR: Failed to apply watermark overlay >&2
)

REM Cleanup
del "%PROCESSED_WM%" 2>nul
del "%WATERMARK_PDF%" 2>nul

exit /b %RESULT%
