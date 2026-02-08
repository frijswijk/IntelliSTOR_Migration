@echo off
REM bundle_for_airgap.bat - Prepare extractor for airgap deployment
REM Creates a deployment package with QPDF bundled

setlocal

echo ======================================================================
echo Papyrus RPT Page Extractor - Airgap Bundling
echo ======================================================================
echo.
echo This script will create a deployment-ready package with:
echo   - papyrus_rpt_page_extractor.exe
echo   - QPDF for PDF page extraction
echo   - Watermark directory structure
echo.

REM Check if extractor exists
if not exist "papyrus_rpt_page_extractor.exe" (
    echo ERROR: papyrus_rpt_page_extractor.exe not found
    echo Please compile first using compile.bat
    echo.
    pause
    exit /b 1
)

REM Create tools directory structure
echo Creating directory structure...
if not exist "tools" mkdir tools
if not exist "tools\watermarks" mkdir tools\watermarks

REM Copy QPDF if available
set QPDF_SOURCE=C:\Users\freddievr\qpdf-12.3.2-mingw64\bin\qpdf.exe

if exist "%QPDF_SOURCE%" (
    echo Copying QPDF...
    copy /Y "%QPDF_SOURCE%" tools\qpdf.exe >nul
    if %ERRORLEVEL% equ 0 (
        echo   [OK] QPDF bundled successfully
    ) else (
        echo   [WARNING] Failed to copy QPDF
    )
) else (
    echo   [WARNING] QPDF not found at: %QPDF_SOURCE%
    echo   PDF page extraction will not work without QPDF
    echo   The extractor will still work but will extract full PDFs
)

REM Check for ImageMagick (optional)
set MAGICK_SOURCE=C:\Users\freddievr\imagemagick\magick.exe

if exist "%MAGICK_SOURCE%" (
    echo.
    echo ImageMagick found at: %MAGICK_SOURCE%
    echo Do you want to bundle ImageMagick for watermarking? (Y/N)
    set /p BUNDLE_MAGICK=Choice:
    if /i "%BUNDLE_MAGICK%"=="Y" (
        echo Copying ImageMagick...
        copy /Y "%MAGICK_SOURCE%" tools\magick.exe >nul
        if %ERRORLEVEL% equ 0 (
            echo   [OK] ImageMagick bundled successfully
        )
    )
)

REM Create watermark placeholder
echo.
echo Creating watermark placeholder...
echo Place your watermark PNG files in: tools\watermarks\ > tools\watermarks\README.txt
echo. >> tools\watermarks\README.txt
echo Supported formats: >> tools\watermarks\README.txt
echo   - confidential.png >> tools\watermarks\README.txt
echo   - internal.png >> tools\watermarks\README.txt
echo   - draft.png >> tools\watermarks\README.txt
echo. >> tools\watermarks\README.txt
echo Recommended size: 600x200 pixels, transparent PNG >> tools\watermarks\README.txt

REM Summary
echo.
echo ======================================================================
echo Bundle Summary
echo ======================================================================
echo.

if exist "papyrus_rpt_page_extractor.exe" (
    for %%A in (papyrus_rpt_page_extractor.exe) do echo Extractor:     %%~zA bytes
)

if exist "tools\qpdf.exe" (
    for %%A in (tools\qpdf.exe) do echo QPDF:          %%~zA bytes
) else (
    echo QPDF:          NOT BUNDLED
)

if exist "tools\magick.exe" (
    for %%A in (tools\magick.exe) do echo ImageMagick:   %%~zA bytes
) else (
    echo ImageMagick:   NOT BUNDLED
)

echo.
echo Directory structure:
echo   9_Papyrus_rpt_page_extractor\
echo     papyrus_rpt_page_extractor.exe
echo     tools\
echo       qpdf.exe (if bundled)
echo       magick.exe (if bundled)
echo       watermarks\
echo         (place PNG files here)
echo.

if exist "tools\qpdf.exe" (
    echo [OK] Ready for airgap deployment with PDF page extraction support
) else (
    echo [WARNING] PDF page extraction will NOT work without QPDF
    echo          The extractor will copy full PDFs instead
)

echo.
echo To deploy to airgap machine:
echo   1. Copy this entire folder to the target machine
echo   2. Place watermark PNGs in tools\watermarks\ (optional)
echo   3. Test with: papyrus_rpt_page_extractor.exe --help
echo.

pause
endlocal
