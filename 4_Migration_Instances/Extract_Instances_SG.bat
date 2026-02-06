CLS
@Echo off
call ..\Migration_Environment.bat
:: --- 1. Capture Start Time ---
set "START_TIME=%TIME%"
set "LOG_FILE=Extract_Instances_SG_LOG.txt"

echo Extract_Instances_SG Script started at: %DATE% %START_TIME%
echo -----------------------------------------------------------------------
echo Database: %SQL-SG-Database%
echo Input CSV: %Instances_Input_SG%
echo Output Folder: %Instances_Output_SG%
echo Start Year: %Instances_StartYear_SG%
echo -----------------------------------------------------------------------

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

rem Create output directory if it doesn't exist
if not exist "%Instances_Output_SG%" mkdir "%Instances_Output_SG%"

rem Run the Extract_Instances script
python Extract_Instances.py --server %SQLServer% --database %SQL-SG-Database% --windows-auth --input "%Instances_Input_SG%" --output "%Instances_Output_SG%" --start-year %Instances_StartYear_SG% --rptfolder "%RPT_FOLDER%" --quiet

:: --- 2. Capture End Time and Calculate Duration ---
echo -----------------------------------------------------------------------
set "END_TIME=%TIME%"
echo Script finished at: %DATE% %END_TIME%

:: Robust calculation using New-TimeSpan to handle regional time formats
for /f "tokens=*" %%i in ('powershell -command "$start = [datetime]('%START_TIME%'.Replace(',', '.')); $end = [datetime]('%END_TIME%'.Replace(',', '.')); (New-TimeSpan -Start $start -End $end).ToString('hh\:mm\:ss')"') do set "DURATION=%%i"

echo Total Time Elapsed: %DURATION%
:: --- 3. Logging Section ---
:: We use ^| to tell Batch these are literal characters, not command pipes.
echo [%DATE% %START_TIME%] Country: SG ^| DB: %SQL-SG-Database% ^| Start Year: %Instances_StartYear_SG% ^| Duration: %DURATION% >> "%LOG_FILE%"

echo Log updated in %LOG_FILE%
pause
