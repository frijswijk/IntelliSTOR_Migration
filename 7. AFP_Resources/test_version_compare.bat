@echo off
REM Test script to demonstrate version comparison feature

echo ======================================================================
echo AFP Resource Analyzer - Version Comparison Test
echo ======================================================================
echo.

echo Test 1: Baseline (without version comparison)
echo ----------------------------------------------------------------------
python Analyze_AFP_Resources.py --folder "C:\Users\freddievr\Downloads\afp\afp" --output-csv "test_baseline.csv"
echo.

echo Test 2: With Version Comparison
echo ----------------------------------------------------------------------
python Analyze_AFP_Resources.py --folder "C:\Users\freddievr\Downloads\afp\afp" --output-csv "test_compare.csv" --version-compare
echo.

echo ======================================================================
echo Comparison Results
echo ======================================================================
echo.
echo Checking C04BAR10.RCS as example:
echo.
echo Baseline:
findstr "C04BAR10.RCS" test_baseline.csv
echo.
echo With Version Compare:
findstr "C04BAR10.RCS" test_compare.csv
echo.
echo ======================================================================
echo Test Complete
echo ======================================================================
pause
