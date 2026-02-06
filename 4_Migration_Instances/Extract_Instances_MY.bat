CLS
@Echo off
call ..\Migration_Environment.bat
:: --- 1. Capture Start Time ---
set "START_TIME=%TIME%"
set "LOG_FILE=Extract_Instances_MY_LOG.txt"

echo Extract_Instances_MY Script started at: %DATE% %START_TIME%
echo -----------------------------------------------------------------------
echo Database: %SQL-MY-Database%
echo Input CSV: %Instances_Input_MY%
echo Output Folder: %Instances_Output_MY%
echo Start Year: %Instances_StartYear_MY%
echo -----------------------------------------------------------------------

rem Prompt for RPT folder (mandatory - SEGMENTS come from RPT file SECTIONHDR)
:ask_rptfolder_my
echo.
set /p "RPT_FOLDER=Enter RPT folder path (contains .RPT files for SEGMENTS extraction): "
if "%RPT_FOLDER%"=="" (
    echo ERROR: RPT folder is required for SEGMENTS extraction.
    goto ask_rptfolder_my
)
if not exist "%RPT_FOLDER%" (
    echo ERROR: Directory does not exist: %RPT_FOLDER%
    goto ask_rptfolder_my
)
echo RPT Folder: %RPT_FOLDER%

rem Create output directory if it doesn't exist
if not exist "%Instances_Output_MY%" mkdir "%Instances_Output_MY%"

rem Run the Extract_Instances script
python Extract_Instances.py --server %SQLServer% --database %SQL-MY-Database% --windows-auth --input "%Instances_Input_MY%" --output "%Instances_Output_MY%" --start-year %Instances_StartYear_MY% --rptfolder "%RPT_FOLDER%" --quiet

:: --- 2. Capture End Time and Calculate Duration ---
echo -----------------------------------------------------------------------
set "END_TIME=%TIME%"
echo Script finished at: %DATE% %END_TIME%

:: Robust calculation using New-TimeSpan to handle regional time formats
for /f "tokens=*" %%i in ('powershell -command "$start = [datetime]('%START_TIME%'.Replace(',', '.')); $end = [datetime]('%END_TIME%'.Replace(',', '.')); (New-TimeSpan -Start $start -End $end).ToString('hh\:mm\:ss')"') do set "DURATION=%%i"

echo Total Time Elapsed: %DURATION%
:: --- 3. Logging Section ---
:: We use ^| to tell Batch these are literal characters, not command pipes.
echo [%DATE% %START_TIME%] Country: MY ^| DB: %SQL-MY-Database% ^| Start Year: %Instances_StartYear_MY% ^| Duration: %DURATION% >> "%LOG_FILE%"

echo Log updated in %LOG_FILE%
pause
