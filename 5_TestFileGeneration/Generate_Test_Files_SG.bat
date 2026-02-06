CLS
@Echo off
call ..\Migration_Environment.bat
:: --- 1. Capture Start Time ---
set "START_TIME=%TIME%"
set "LOG_FILE=Generate_Test_Files_SG_LOG.txt"

echo Generate_Test_Files_SG Script started at: %DATE% %START_TIME%
echo -----------------------------------------------------------------------
echo Report Species CSV: %TestGen_ReportSpecies_SG%
echo Folder Extract: %TestGen_FolderExtract_SG%
echo Target Folder: %TestGen_TargetFolder_SG%
echo Max Species per Run: %TestGen_MaxSpecies%
echo -----------------------------------------------------------------------

rem Create target directory if it doesn't exist
if not exist "%TestGen_TargetFolder_SG%" mkdir "%TestGen_TargetFolder_SG%"

rem Run the Generate_Test_Files script
python Generate_Test_Files.py --ReportSpecies "%TestGen_ReportSpecies_SG%" --FolderExtract "%TestGen_FolderExtract_SG%" --TargetFolder "%TestGen_TargetFolder_SG%" --Number %TestGen_MaxSpecies% --quiet

:: --- 2. Capture End Time and Calculate Duration ---
echo -----------------------------------------------------------------------
set "END_TIME=%TIME%"
echo Script finished at: %DATE% %END_TIME%

:: Robust calculation using New-TimeSpan to handle regional time formats
for /f "tokens=*" %%i in ('powershell -command "$start = [datetime]('%START_TIME%'.Replace(',', '.')); $end = [datetime]('%END_TIME%'.Replace(',', '.')); (New-TimeSpan -Start $start -End $end).ToString('hh\:mm\:ss')"') do set "DURATION=%%i"

echo Total Time Elapsed: %DURATION%
:: --- 3. Logging Section ---
:: We use ^| to tell Batch these are literal characters, not command pipes.
echo [%DATE% %START_TIME%] Country: SG ^| Max Species: %TestGen_MaxSpecies% ^| Target: %TestGen_TargetFolder_SG% ^| Duration: %DURATION% >> "%LOG_FILE%"

echo Log updated in %LOG_FILE%
pause
