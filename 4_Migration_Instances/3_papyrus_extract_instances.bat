CLS
@Echo off
call ..\Migration_Environment.bat
:: --- 1. Capture Start Time ---
set "START_TIME=%TIME%"
set "LOG_FILE=Extract_Instances_CPP_LOG.txt"

echo Extract Instances (C++) started at: %DATE% %START_TIME%
echo ---------------------------------------------------------------------------
echo Database: %SQL-SG-Database%
echo Input CSV: %Instances_Input_SG%
echo Output Folder: %Instances_Output_SG%
echo Start Year: %Instances_StartYear_SG%
echo End   Year: %Instances_EndYear_SG%
echo ---------------------------------------------------------------------------

rem Prompt for RPT folder (mandatory - SEGMENTS come from RPT file SECTIONHDR)
:ask_rptfolder_sg
echo.
set /p "RPT_FOLDER=Enter RPT folder path (contains .RPT files for SEGMENTS extraction): "
if "%RPT_FOLDER%"=="" (
    echo ERROR: RPT folder is required for SEGMENTS extraction.
    goto ask_rptfolder_sg
)
if not exist "%RPT_FOLDER%" (
    echo ERROR: Directory does not exist: %RPT_FOLDER%
    goto ask_rptfolder_sg
)
echo RPT Folder: %RPT_FOLDER%

rem Prompt for MAP folder (mandatory - Indexes come from MAP file)
:ask_mapfolder
echo.
set /p "MAP_FOLDER=Enter MAP folder path (contains .MAP files for Index extraction): "
if "%MAP_FOLDER%"=="" (
    echo ERROR: MAP folder is required for Index extraction.
    goto ask_mapfolder
)
if not exist "%MAP_FOLDER%" (
    echo ERROR: Directory does not exist: %MAP_FOLDER%
    goto ask_mapfolder
)
echo MAP Folder: %MAP_FOLDER%

rem Create output directory if it doesn't exist
if not exist "%Instances_Output_SG%" mkdir "%Instances_Output_SG%"

rem Run the Extract_Instances script (C++)
papyrus_extract_instances.exe --server %SQLServer% --database %SQL-SG-Database% --windows-auth --input "%Instances_Input_SG%" --output-dir "%Instances_Output_SG%" --start-year %Instances_StartYear_SG% --end-year %Instances_EndYear_SG% --timezone "Asia/Singapore" --rptfolder "%RPT_FOLDER%" --mapfolder "%MAP_FOLDER%" --quiet

:: --- 2. Capture End Time and Calculate Duration ---
echo ---------------------------------------------------------------------------
set "END_TIME=%TIME%"
echo Script finished at: %DATE% %END_TIME%

:: Robust calculation using New-TimeSpan to handle regional time formats
for /f "tokens=*" %%i in ('powershell -command "$start = [datetime]('%START_TIME%'.Replace(',', '.')); $end = [datetime]('%END_TIME%'.Replace(',', '.')); (New-TimeSpan -Start $start -End $end).ToString('hh\:mm\:ss')"') do set "DURATION=%%i"

echo Total Time Elapsed: %DURATION%
:: --- 3. Logging Section ---
echo [%DATE% %START_TIME%] Country: SG ^| DB: %SQL-SG-Database% ^| Start Year: %Instances_StartYear_SG% ^| Duration: %DURATION% >> %LOG_FILE%

echo Log updated in %LOG_FILE%
pause
