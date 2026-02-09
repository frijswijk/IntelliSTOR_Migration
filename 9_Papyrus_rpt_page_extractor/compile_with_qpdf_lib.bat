@echo off
REM Compile papyrus_rpt_page_extractor_v2 with QPDF library support
REM This eliminates the need for qpdf.exe external call

set MINGW=C:\Users\freddievr\mingw64\bin
set QPDF=C:\Users\freddievr\qpdf-12.3.2-mingw64

echo Compiling with QPDF library support...
echo.

REM Add QPDF include and lib paths
set INCLUDES=-I"%QPDF%\include"
set LIBDIRS=-L"%QPDF%\lib"
set LIBS=-lqpdf -ljpeg -lz

REM Compile with QPDF library enabled
"%MINGW%\g++.exe" -std=c++17 -O2 ^
  -DUSE_QPDF_LIBRARY ^
  %INCLUDES% ^
  -o papyrus_rpt_page_extractor_v2_qpdflib.exe ^
  papyrus_rpt_page_extractor_v2.cpp ^
  %LIBDIRS% %LIBS% ^
  -static-libgcc -static-libstdc++

if errorlevel 1 (
    echo.
    echo ERROR: Compilation failed!
    pause
    exit /b 1
)

echo.
echo SUCCESS: papyrus_rpt_page_extractor_v2_qpdflib.exe created
echo.
echo This version uses QPDF C++ library (no external qpdf.exe needed)
echo.
pause
