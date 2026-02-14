CLS
@Echo off
call ..\Migration_Environment.bat
:: --- 1. Capture Start Time ---
set "START_TIME=%TIME%"
set "LOG_FILE=Export_Indexed_Fields_LOG.txt"

echo Export Indexed Fields (C++) started at: %DATE% %START_TIME%
echo ---------------------------------------------------------------------------
echo Database: %SQL-SG-Database%
echo Output Folder: %Instances_Output_SG%
echo ---------------------------------------------------------------------------

rem Create output directory if it doesn't exist
if not exist "%Instances_Output_SG%" mkdir "%Instances_Output_SG%"

rem Run the Export Indexed Fields script (C++)
papyrus_export_indexed_fields.exe --server %SQLServer% --database %SQL-SG-Database% --windows-auth --output-dir "%Instances_Output_SG%"

:: --- 2. Capture End Time and Calculate Duration ---
echo ---------------------------------------------------------------------------
set "END_TIME=%TIME%"
echo Script finished at: %DATE% %END_TIME%

:: Robust calculation using New-TimeSpan to handle regional time formats
for /f "tokens=*" %%i in ('powershell -command "$start = [datetime]('%START_TIME%'.Replace(',', '.')); $end = [datetime]('%END_TIME%'.Replace(',', '.')); (New-TimeSpan -Start $start -End $end).ToString('hh\:mm\:ss')"') do set "DURATION=%%i"

echo Total Time Elapsed: %DURATION%
:: --- 3. Logging Section ---
echo [%DATE% %START_TIME%] Country: SG ^| DB: %SQL-SG-Database% ^| Duration: %DURATION% >> %LOG_FILE%

echo Log updated in %LOG_FILE%
pause
