@echo off
call ..\Migration_Environment.bat
echo.
echo ======================================================================
echo Environment Variable Test
echo ======================================================================
echo AFP_VersionCompare = %AFP_VersionCompare%
echo.
echo Command that would be executed (SG):
set "CMD=python Analyze_AFP_Resources.py --folder "%AFP_Source_SG%" --output-csv "%AFP_Output%\AFP_Resources_SG.csv" --namespace SG --quiet"
if /I "%AFP_VersionCompare%"=="Yes" (
    set "CMD=%CMD% --version-compare"
)
echo %CMD%
echo.
echo ======================================================================
pause
