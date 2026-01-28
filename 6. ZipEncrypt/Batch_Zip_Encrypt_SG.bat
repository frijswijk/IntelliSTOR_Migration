CLS
@Echo off
call ..\Migration_Environment.bat
:: --- 1. Capture Start Time ---
set "START_TIME=%TIME%"
set "LOG_FILE=Batch_Zip_Encrypt_SG_LOG.txt"

echo Batch_Zip_Encrypt_SG Script started at: %DATE% %START_TIME%
echo -----------------------------------------------------------------------
echo Source Folder: %ZipEncrypt_SourceFolder_SG%
echo Output Folder: %ZipEncrypt_OutputFolder_SG%
echo Species CSV: %ZipEncrypt_SpeciesCSV_SG%
echo Instances Folder: %ZipEncrypt_InstancesFolder_SG%
echo Compression Level: %ZipEncrypt_CompressionLevel%
echo Max Species per Run: %ZipEncrypt_MaxSpecies%
echo Delete After Compress: %ZipEncrypt_DeleteAfterCompress%
echo Password Protected: Yes
echo -----------------------------------------------------------------------

rem Create output directory if it doesn't exist
if not exist "%ZipEncrypt_OutputFolder_SG%" mkdir "%ZipEncrypt_OutputFolder_SG%"

rem Run the batch_zip_encrypt script
rem Note: If 7zip path is set, add: --7zip-path "%ZipEncrypt_7zipPath%"
python batch_zip_encrypt.py --source-folder "%ZipEncrypt_SourceFolder_SG%" --output-folder "%ZipEncrypt_OutputFolder_SG%" --password "%ZipEncrypt_Password%" --species-csv "%ZipEncrypt_SpeciesCSV_SG%" --instances-folder "%ZipEncrypt_InstancesFolder_SG%" --compression-level %ZipEncrypt_CompressionLevel% --max-species %ZipEncrypt_MaxSpecies% --delete-after-compress %ZipEncrypt_DeleteAfterCompress% --quiet

:: --- 2. Capture End Time and Calculate Duration ---
echo -----------------------------------------------------------------------
set "END_TIME=%TIME%"
echo Script finished at: %DATE% %END_TIME%

:: Robust calculation using New-TimeSpan to handle regional time formats
for /f "tokens=*" %%i in ('powershell -command "$start = [datetime]('%START_TIME%'.Replace(',', '.')); $end = [datetime]('%END_TIME%'.Replace(',', '.')); (New-TimeSpan -Start $start -End $end).ToString('hh\:mm\:ss')"') do set "DURATION=%%i"

echo Total Time Elapsed: %DURATION%
:: --- 3. Logging Section ---
:: We use ^| to tell Batch these are literal characters, not command pipes.
echo [%DATE% %START_TIME%] Country: SG ^| Compression: %ZipEncrypt_CompressionLevel% ^| Max Species: %ZipEncrypt_MaxSpecies% ^| Delete: %ZipEncrypt_DeleteAfterCompress% ^| Duration: %DURATION% >> "%LOG_FILE%"

echo Log updated in %LOG_FILE%
pause
