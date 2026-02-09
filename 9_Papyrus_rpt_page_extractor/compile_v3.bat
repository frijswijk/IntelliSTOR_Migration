@echo off
REM ============================================================================
REM Compilation script for papyrus_rpt_page_extractor_v3.exe
REM Fully static build - QPDF, libjpeg, OpenSSL all linked in.
REM Single .exe, zero external DLLs needed.
REM ============================================================================

setlocal

REM Compiler location (MinGW-w64, WinLibs ucrt build)
set MINGW=C:\Users\freddievr\mingw64\bin

REM QPDF development files
set QPDF=C:\Users\freddievr\qpdf-12.3.2-mingw64

REM Source and output files (relative to this batch file location)
set SOURCE=%~dp0papyrus_rpt_page_extractor_v3.cpp
set SHIMS=%~dp0compat_shims.c
set OUTPUT=%~dp0papyrus_rpt_page_extractor_v3.exe

echo ============================================================================
echo Compiling Papyrus RPT Page Extractor V3 (Fully Static Build)
echo ============================================================================
echo Source:   %SOURCE%
echo Output:   %OUTPUT%
echo Compiler: %MINGW%\g++.exe
echo QPDF:     %QPDF%
echo.

REM Step 1: Compile compat shims (bridges MSYS2-built libs to WinLibs MinGW)
echo Compiling compatibility shims...
"%MINGW%\gcc.exe" -c -O2 "%SHIMS%" -o "%~dp0compat_shims.o"
if %errorlevel% neq 0 goto :error

REM Step 2: Compile and link everything statically
echo Compiling v3 (fully static)...
echo.

"%MINGW%\g++.exe" -std=c++17 -O2 -static ^
  -I"%QPDF%\include" ^
  -o "%OUTPUT%" ^
  "%SOURCE%" "%~dp0compat_shims.o" ^
  -L"%QPDF%\lib" -L"%MINGW%\..\lib" ^
  -lqpdf_static -ljpeg -lcrypto -lz ^
  -lws2_32 -lcrypt32 -ladvapi32 ^
  -Wl,--defsym=__imp__setjmp=__imp_setjmp ^
  -s

if %errorlevel% neq 0 (
    echo.
    echo ============================================================================
    echo ERROR: Compilation failed!
    echo ============================================================================
    echo.
    echo Prerequisites:
    echo   1. MinGW-w64 (WinLibs ucrt): %MINGW%
    echo   2. QPDF dev files:           %QPDF%
    echo   3. libjpeg-turbo static lib:  %MINGW%\..\lib\libjpeg.a
    echo   4. OpenSSL static lib:        %MINGW%\..\lib\libcrypto.a
    echo.
    echo If libjpeg.a or libcrypto.a are missing, download from MSYS2:
    echo   https://mirror.msys2.org/mingw/mingw64/mingw-w64-x86_64-libjpeg-turbo-3.1.3-1-any.pkg.tar.zst
    echo   https://mirror.msys2.org/mingw/mingw64/mingw-w64-x86_64-openssl-3.6.1-3-any.pkg.tar.zst
    echo Extract into %MINGW%\.. (the mingw64 folder)
    echo.
    goto :error
)

REM Cleanup temp object file
del "%~dp0compat_shims.o" >nul 2>&1

echo.
echo ============================================================================
echo SUCCESS: Fully static executable created
echo ============================================================================
echo File: %OUTPUT%
dir "%OUTPUT%" | find ".exe"
echo.
echo This is a single-file executable with NO external DLL dependencies:
echo   - QPDF library: statically linked
echo   - libjpeg: statically linked
echo   - OpenSSL crypto: statically linked
echo   - zlib: statically linked
echo   - No qpdf.exe, no ImageMagick, no DLLs needed
echo.
echo You can now run the extractor:
echo.
echo Basic usage (no watermark):
echo   %OUTPUT% input.rpt all output.txt output.pdf
echo.
echo With watermark:
echo   %OUTPUT% input.rpt all output.txt output.pdf ^
echo     --WatermarkImage confidential.png ^
echo     --WatermarkPosition BottomRight ^
echo     --WatermarkOpacity 30 ^
echo     --WatermarkScale 0.5
echo.

endlocal
exit /b 0

:error
del "%~dp0compat_shims.o" >nul 2>&1
endlocal
pause
exit /b 1
