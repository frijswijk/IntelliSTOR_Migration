# Batch Files Update Summary

## Overview
All batch files across the IntelliSTOR Migration project have been standardized to use centralized environment variables from `Migration_Environment.bat`. This allows easy migration to different machines by updating only one configuration file.

**Date**: 2026-01-26

---

## ✅ Updated Files

### 1. Migration_Environment.bat (Central Configuration)
**Location**: `C:\Users\freddievr\claude-projects\IntelliSTOR_Migration\Migration_Environment.bat`

**New Environment Variables Added**:

#### Instances Extraction
```batch
set Instances_Input_SG=%ReportSpecies_SG%\Report_Species.csv
set Instances_Input_MY=%ReportSpecies_MY%\Report_Species.csv
set Instances_Output_SG=%Migration_data%\Instances_SG
set Instances_Output_MY=%Migration_data%\Instances_MY
set Instances_StartYear_SG=2020
set Instances_StartYear_MY=1900
```

#### Test File Generation
```batch
set TestGen_ReportSpecies_SG=%ReportSpecies_SG%\Report_Species.csv
set TestGen_ReportSpecies_MY=%ReportSpecies_MY%\Report_Species.csv
set TestGen_FolderExtract_SG=%Instances_Output_SG%
set TestGen_FolderExtract_MY=%Instances_Output_MY%
set TestGen_TargetFolder_SG=%Migration_data%\TestFiles_SG
set TestGen_TargetFolder_MY=%Migration_data%\TestFiles_MY
```

#### AFP Resources
```batch
set AFP_Source_SG=C:\Users\freddievr\Downloads\afp\afp
set AFP_Source_MY=C:\Users\freddievr\Downloads\afp\afp
set AFP_Output=%Migration_data%\AFP_Resources
```

#### Zip and Encrypt
```batch
set ZipEncrypt_SourceFolder_SG=%TestGen_TargetFolder_SG%
set ZipEncrypt_SourceFolder_MY=%TestGen_TargetFolder_MY%
set ZipEncrypt_OutputFolder_SG=%Migration_data%\EncryptedArchives_SG
set ZipEncrypt_OutputFolder_MY=%Migration_data%\EncryptedArchives_MY
set ZipEncrypt_SpeciesCSV_SG=%ReportSpecies_SG%\Report_Species.csv
set ZipEncrypt_SpeciesCSV_MY=%ReportSpecies_MY%\Report_Species.csv
set ZipEncrypt_InstancesFolder_SG=%Instances_Output_SG%
set ZipEncrypt_InstancesFolder_MY=%Instances_Output_MY%
set ZipEncrypt_Password=YourSecurePassword123
set ZipEncrypt_CompressionLevel=5
rem set ZipEncrypt_7zipPath=C:\Program Files\7-Zip\7z.exe
```

---

### 2. AFP_Resources Folder
**Location**: `C:\Users\freddievr\claude-projects\IntelliSTOR_Migration\AFP_Resources\`

#### Files Created:
- ✅ `Analyze_AFP_Resources.py` (604 lines) - Main analyzer tool
- ✅ `Analyze_AFP_Resources_SG.bat` - Singapore batch file
- ✅ `Analyze_AFP_Resources_MY.bat` - Malaysia batch file
- ✅ `README.md` - Complete documentation

**Features**:
- Auto-detects folder structure (flat vs. namespace)
- Tracks AFP resource versions (newest to oldest)
- Generates dynamic CSV with variable version columns
- Dual logging (console + file)
- Time tracking and execution logs

---

### 3. 4_Migration_Instances Folder
**Location**: `C:\Users\freddievr\claude-projects\IntelliSTOR_Migration\4_Migration_Instances\`

#### Files Updated:
- ✅ `Extract_Instances.SG.bat` - Upgraded from simple one-liner
- ✅ `Extract_Instances.MY.bat` - Upgraded from simple one-liner

**Before**:
```batch
python Extract_Instances.py --server localhost --database iSTSGUAT --windows-auth --input D:\python\FolderSpecies-DB\outputSG\Report_Species.csv --output outputSG --start-year 2020 --quiet
```

**After**:
- ✅ Uses environment variables
- ✅ Time tracking
- ✅ Execution logging
- ✅ Automatic directory creation
- ✅ Informative console output

---

### 4. 5_TestFileGeneration Folder
**Location**: `C:\Users\freddievr\claude-projects\IntelliSTOR_Migration\5_TestFileGeneration\`

#### Files Updated:
- ✅ `Generate_Test_Files_SG.bat` - Upgraded from simple one-liner
- ✅ `Generate_Test_Files_MY.bat` - Upgraded from simple one-liner (fixed typo: TestFilMY → TestFiles_MY)

**Before**:
```batch
python Generate_Test_Files.py --ReportSpecies D:\python\FolderSpecies-DB\outputSG\Report_Species.csv --FolderExtract D:\python\ReportInstance\outputSG --TargetFolder D:\python\TestData\TestFilesSG
```

**After**:
- ✅ Uses environment variables
- ✅ Time tracking
- ✅ Execution logging
- ✅ Automatic directory creation
- ✅ Informative console output

---

### 5. 6_ZipEncrypt Folder
**Location**: `C:\Users\freddievr\claude-projects\IntelliSTOR_Migration\6_ZipEncrypt\`

#### Files Created:
- ✅ `Batch_Zip_Encrypt_SG.bat` - NEW (Singapore encryption batch)
- ✅ `Batch_Zip_Encrypt_MY.bat` - NEW (Malaysia encryption batch)

**Features**:
- Password-protected 7z archive creation
- Configurable compression level
- Resume capability (handled by Python script)
- Automatic directory creation
- Time tracking and logging

---

## 🎯 Standard Features (All Batch Files)

All batch files now include:

### 1. Environment Variable Loading
```batch
call ..\Migration_Environment.bat
```

### 2. Time Tracking
```batch
set "START_TIME=%TIME%"
# ... script execution ...
set "END_TIME=%TIME%"
echo Total Time Elapsed: %DURATION%
```

### 3. Execution Logging
```batch
set "LOG_FILE=Script_Name_LOG.txt"
echo [%DATE% %START_TIME%] Country: XX | Details | Duration: %DURATION% >> "%LOG_FILE%"
```

### 4. Automatic Directory Creation
```batch
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"
```

### 5. Informative Console Output
```batch
echo Script started at: %DATE% %START_TIME%
echo -----------------------------------------------------------------------
echo Database: %SQL-XX-Database%
echo Output Folder: %Output_Path%
echo -----------------------------------------------------------------------
```

### 6. Duration Calculation
Uses PowerShell for robust time calculation handling regional formats:
```batch
for /f "tokens=*" %%i in ('powershell -command "$start = [datetime]('%START_TIME%'.Replace(',', '.')); $end = [datetime]('%END_TIME%'.Replace(',', '.')); (New-TimeSpan -Start $start -End $end).ToString('hh\:mm\:ss')"') do set "DURATION=%%i"
```

---

## 📝 Migration to New Machine

To use these scripts on a different machine, simply update `Migration_Environment.bat`:

### Change the Base Path
```batch
# Current (for this machine)
set Migration_data=D:\_IntelliSTOR_Migration\Migration_data

# For new machine (example)
set Migration_data=C:\_IntelliSTOR_Migration\Migration_data
```

### Update AFP Paths (if different)
```batch
set AFP_Source_SG=C:\NewPath\afp\afp
set AFP_Source_MY=C:\NewPath\afp\afp
```

### Update Password (for ZipEncrypt)
```batch
set ZipEncrypt_Password=NewSecurePassword456
```

### Update 7zip Path (if needed)
```batch
rem Uncomment and set if 7z.exe is not in PATH
set ZipEncrypt_7zipPath=C:\Program Files\7-Zip\7z.exe
```

---

## 📊 Execution Logs

Each batch file creates its own log file with execution history:

| Batch File | Log File |
|------------|----------|
| Extract_Users_permissions_SG.bat | Extract_Users_Permissions_SG_LOG.txt |
| Extract_Instances.SG.bat | Extract_Instances_SG_LOG.txt |
| Generate_Test_Files_SG.bat | Generate_Test_Files_SG_LOG.txt |
| Analyze_AFP_Resources_SG.bat | Analyze_AFP_Resources_SG_LOG.txt |
| Batch_Zip_Encrypt_SG.bat | Batch_Zip_Encrypt_SG_LOG.txt |
| *(same pattern for MY)* | *(same pattern for MY)* |
| Cleanup_Report_Instances.bat/.command | Cleanup_Report_Instances_LOG.txt |
| Cleanup_Old_Signatures.bat/.command | Cleanup_Old_Signatures_LOG.txt |
| Cleanup_Orphaned_Files.bat/.command | Cleanup_Orphaned_Files_LOG.txt |

**Log Format**:
```
[26-01-2026 14:15:32] Country: SG | DB: iSTSGUAT | Duration: 00:03:13
```

---

## 🔗 Dependencies Between Scripts

The migration workflow follows this sequence:

```
1. Extract_Users_Permissions
   └─> Outputs to: %Users-XX%

2. Extract_Instances
   └─> Reads from: %ReportSpecies_XX%\Report_Species.csv
   └─> Outputs to: %Instances_Output_XX%

3. Generate_Test_Files
   └─> Reads from: %ReportSpecies_XX%\Report_Species.csv
   └─> Reads from: %Instances_Output_XX%
   └─> Outputs to: %TestGen_TargetFolder_XX%

4. Batch_Zip_Encrypt
   └─> Reads from: %TestGen_TargetFolder_XX%
   └─> Reads from: %ReportSpecies_XX%\Report_Species.csv
   └─> Reads from: %Instances_Output_XX%
   └─> Outputs to: %ZipEncrypt_OutputFolder_XX%

5. Analyze_AFP_Resources (Independent)
   └─> Reads from: %AFP_Source_XX%
   └─> Outputs to: %AFP_Output%
```

---

## 🎉 Benefits

### Before Update
- ❌ Hard-coded paths in each batch file
- ❌ No execution logging
- ❌ No time tracking
- ❌ Inconsistent format
- ❌ Difficult to migrate to new machines

### After Update
- ✅ Centralized configuration
- ✅ Complete execution logging
- ✅ Time tracking for all scripts
- ✅ Consistent format across all batch files
- ✅ Easy migration - update one file only
- ✅ Automatic directory creation
- ✅ Informative console output

---

## 📁 Complete File Structure

```
IntelliSTOR_Migration\
├── Migration_Environment.bat              # ← CENTRAL CONFIG (update this only)
├── BATCH_FILES_UPDATE_SUMMARY.md         # ← This file
│
├── 1_Migration_Users\
│   └── Extract_Users_permissions_SG.bat  # (Already existed - no changes)
│
├── 4_Migration_Instances\
│   ├── Extract_Instances.SG.bat          # ✅ UPDATED
│   └── Extract_Instances.MY.bat          # ✅ UPDATED
│
├── 5_TestFileGeneration\
│   ├── Generate_Test_Files_SG.bat        # ✅ UPDATED
│   └── Generate_Test_Files_MY.bat        # ✅ UPDATED
│
├── 6_ZipEncrypt\
│   ├── Batch_Zip_Encrypt_SG.bat          # ✅ CREATED
│   └── Batch_Zip_Encrypt_MY.bat          # ✅ CREATED
│
├── 7_AFP_Resources\
│   ├── Analyze_AFP_Resources.py          # ✅ CREATED
│   ├── Analyze_AFP_Resources_SG.bat      # ✅ CREATED
│   ├── Analyze_AFP_Resources_MY.bat      # ✅ CREATED
│   └── README.md                          # ✅ CREATED
│
└── 98_Cleanup_DB\
    ├── cleanup_report_instances.py        # ✅ MOVED from root
    ├── cleanup_old_signatures.py          # ✅ MOVED from root
    ├── cleanup_orphaned_files.py          # ✅ MOVED from root
    ├── verify_signature_relationships.py  # ✅ MOVED from root
    ├── Cleanup_Report_Instances.bat       # ✅ MOVED from root
    ├── Cleanup_Report_Instances.command   # ✅ MOVED from root
    ├── Cleanup_Old_Signatures.bat         # ✅ MOVED from root
    ├── Cleanup_Old_Signatures.command     # ✅ MOVED from root
    ├── Cleanup_Orphaned_Files.bat         # ✅ MOVED from root
    ├── Cleanup_Orphaned_Files.command     # ✅ MOVED from root
    ├── DELETE_FUTURE_INSTANCES.bat        # ✅ MOVED from root
    ├── DELETE_FUTURE_INSTANCES.command     # ✅ MOVED from root
    ├── SIGNATURE_CLEANUP_ANALYSIS.md      # ✅ MOVED from root
    └── SIGNATURE_CLEANUP_README.md        # ✅ MOVED from root
```

---

## ✅ Testing Checklist

When migrating to a new machine:

1. ☐ Update `Migration_Environment.bat` with new paths
2. ☐ Test Extract_Users_permissions_XX.bat
3. ☐ Test Extract_Instances.XX.bat
4. ☐ Test Generate_Test_Files_XX.bat
5. ☐ Test Analyze_AFP_Resources_XX.bat
6. ☐ Test Batch_Zip_Encrypt_XX.bat
7. ☐ Test Cleanup_Report_Instances.bat/.command (in 98_Cleanup_DB)
8. ☐ Verify all log files are created
8. ☐ Verify output directories are created automatically
9. ☐ Check execution logs for duration tracking

---

## 📞 Support

For issues or questions:
- Check individual README files in each folder
- Review log files (*_LOG.txt) for execution history
- Verify paths in Migration_Environment.bat

**Author**: Generated for OCBC IntelliSTOR Migration
**Date**: 2026-01-26
