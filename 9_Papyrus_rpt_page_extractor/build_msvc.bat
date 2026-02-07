@echo off
REM ============================================================================
REM Visual Studio 2022 Build Script for papyrus_rpt_page_extractor.exe
REM ============================================================================

setlocal

echo ============================================================================
echo Building with Visual Studio 2022 MSVC
echo ============================================================================
echo.

REM Set up Visual Studio environment
echo Setting up Visual Studio 2022 environment...
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat" x64
echo.

REM Compile
echo Compiling papyrus_rpt_page_extractor.cpp...
echo Command: cl /EHsc /O2 /MT papyrus_rpt_page_extractor.cpp /Fe:papyrus_rpt_page_extractor.exe
echo.

cl /EHsc /O2 /MT papyrus_rpt_page_extractor.cpp /Fe:papyrus_rpt_page_extractor.exe /nologo

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================================================
    echo [SUCCESS] Build completed successfully!
    echo ============================================================================
    echo.

    if exist papyrus_rpt_page_extractor.exe (
        echo Executable: papyrus_rpt_page_extractor.exe
        for %%F in (papyrus_rpt_page_extractor.exe) do (
            echo File size: %%~zF bytes
        )
        echo.
        echo The executable is ready for distribution to airgap machines.
        echo.

        REM Clean up intermediate files
        if exist papyrus_rpt_page_extractor.obj del papyrus_rpt_page_extractor.obj
        echo Cleaned up intermediate files.
        echo.
    )
) else (
    echo.
    echo [ERROR] Compilation failed!
    echo.
)

pause
