cls
@Echo off
Call ..\Migration_environment.bat

:: --- 1. Capture Start Time ---
set "START_TIME=%TIME%"
set "LOG_FILE=Extract_FolderSpecies_CPP_LOG.txt"

echo Papyrus Extract Folder Species (C++) started at: %DATE% %START_TIME%
echo ---------------------------------------------------------------------------
papyrus_extract_folder_species.exe --server %SQLServer% --database %SQL-SG-Database% --windows-auth --output-dir %ReportSpecies_SG% --Country SG

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
