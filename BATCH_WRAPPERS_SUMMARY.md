# Batch File Wrappers - Summary

## Overview

Created standardized batch file wrappers with time tracking, logging, and error handling for two key C++ executables in the IntelliSTOR Migration project.

## ✅ Files Created

### 9_Papyrus_rpt_page_extractor

**Wrapper Script:**
- `papyrus_rpt_page_extractor.bat` - Main wrapper with time tracking and logging

**Environment Template:**
- `RPT_Environment_EXAMPLE.bat` - Example environment variable configuration

**Documentation:**
- `PDF_SETUP_README.md` - PDF features setup guide
- `IMPLEMENTATION_COMPLETE.md` - PDF implementation summary
- `bundle_for_airgap.bat` - Deployment bundling script

### 8_Create_IRPT_File

**Wrapper Script:**
- `rpt_file_builder_wrapper.bat` - Main wrapper with time tracking and logging

**Environment Template:**
- `RPT_Builder_Environment_EXAMPLE.bat` - Example environment variable configuration

**Note:** The existing `RPT_File_Builder.bat` (interactive menu) is unchanged and still available for interactive use.

---

## 📋 Features

Both wrappers include:

✅ **Dual Input Methods**
- Command-line arguments (direct usage)
- Environment variables (batch job usage)

✅ **Time Tracking**
- Start/end timestamps
- Duration calculation using PowerShell
- Regional time format support

✅ **Error Handling**
- Exit code capture
- Meaningful error messages
- Input validation

✅ **Logging**
- Automatic log file creation
- Success/failure tracking
- Duration recording
- Timestamped entries

✅ **Integration**
- Calls `Migration_Environment.bat` if available
- Relative path support
- Compatible with existing infrastructure

---

## 🚀 Usage Examples

### papyrus_rpt_page_extractor.bat

**Command-Line Usage:**
```batch
cd C:\Users\freddievr\claude-projects\IntelliSTOR_Migration\9_Papyrus_rpt_page_extractor

REM Extract pages 1-5
papyrus_rpt_page_extractor.bat input.rpt "pages:1-5" output.txt output.pdf

REM Extract sections
papyrus_rpt_page_extractor.bat input.rpt "sections:14259,14260" output.txt output.pdf

REM Extract all pages
papyrus_rpt_page_extractor.bat input.rpt "all" output.txt output.pdf
```

**Environment Variable Usage:**
```batch
REM Set environment variables
set RPT_INPUT=C:\Reports\input.rpt
set RPT_SELECTION=pages:1-5
set RPT_OUTPUT_TXT=C:\Output\pages.txt
set RPT_OUTPUT_BINARY=C:\Output\pages.pdf

REM Run wrapper
papyrus_rpt_page_extractor.bat
```

**Log Output Example:**
```
[2026-02-08 14:30:15] RPT: input.rpt | Selection: pages:1-5 | Duration: 00:00:03 | Status: SUCCESS
```

---

### rpt_file_builder_wrapper.bat

**Command-Line Usage:**
```batch
cd C:\Users\freddievr\claude-projects\IntelliSTOR_Migration\8_Create_IRPT_File

REM Build from directory
rpt_file_builder_wrapper.bat ./pages/ output.RPT --species 49626 --domain 1

REM Build with embedded PDF
rpt_file_builder_wrapper.bat ./pages/ output.RPT --species 52759 --binary report.pdf

REM Build with template (roundtrip)
rpt_file_builder_wrapper.bat ./pages/ rebuilt.RPT --template original.RPT --species 49626
```

**Environment Variable Usage:**
```batch
REM Set environment variables
set RPT_BUILDER_INPUT=C:\Reports\pages\
set RPT_BUILDER_OUTPUT=C:\Output\rebuilt.RPT
set RPT_SPECIES=49626
set RPT_DOMAIN=1

REM Run wrapper
rpt_file_builder_wrapper.bat
```

**Log Output Example:**
```
[2026-02-08 14:35:22] Input: ./pages/ | Output: output.RPT | Duration: 00:00:05 | Status: SUCCESS
```

---

## 📊 Comparison with Original Pattern

Based on the `Extract_Users_Permissions` example pattern:

| Feature | Extract_Users_Permissions | New Wrappers | Status |
|---------|---------------------------|--------------|--------|
| CLS / @Echo off | ✅ | ✅ | Matched |
| Call Migration_Environment.bat | ✅ | ✅ | Matched |
| Start time tracking | ✅ | ✅ | Matched |
| End time tracking | ✅ | ✅ | Matched |
| Duration calculation (PowerShell) | ✅ | ✅ | Matched |
| Log file creation | ✅ | ✅ | Matched |
| Timestamped log entries | ✅ | ✅ | Matched |
| Pause at end | ✅ | ✅ | Matched |
| Exit code handling | ❌ | ✅ | Enhanced |
| Input validation | ❌ | ✅ | Enhanced |
| Dual input methods | ❌ | ✅ | Enhanced |
| Error messages | ❌ | ✅ | Enhanced |

**Enhancements over original:**
- ✅ Exit code capture and meaningful error messages
- ✅ Input file validation before execution
- ✅ Dual input method support (CLI + environment)
- ✅ File size display on success
- ✅ Executable existence check

---

## 📁 File Locations

### Papyrus RPT Page Extractor

```
9_Papyrus_rpt_page_extractor/
  ├── papyrus_rpt_page_extractor.exe     (C++ executable)
  ├── papyrus_rpt_page_extractor.bat     (NEW: Wrapper script)
  ├── RPT_Environment_EXAMPLE.bat        (NEW: Environment template)
  ├── bundle_for_airgap.bat              (NEW: Deployment script)
  ├── papyrus_rpt_page_extractor_LOG.txt (Created on first run)
  ├── PDF_SETUP_README.md                (NEW: Setup guide)
  ├── IMPLEMENTATION_COMPLETE.md         (NEW: Implementation summary)
  ├── PDF_FEATURE_IMPLEMENTATION.md      (Existing)
  ├── pdf_page_extraction_example.cpp    (Existing)
  └── compile.bat                         (Existing)
```

### RPT File Builder

```
8_Create_IRPT_File/
  ├── rpt_file_builder.exe               (C++ executable)
  ├── rpt_file_builder_wrapper.bat       (NEW: Non-interactive wrapper)
  ├── RPT_Builder_Environment_EXAMPLE.bat (NEW: Environment template)
  ├── rpt_file_builder_LOG.txt           (Created on first run)
  ├── RPT_File_Builder.bat               (Existing: Interactive menu)
  ├── rpt_file_builder.py                (Existing: Python version)
  └── RPT_FILE_BUILDER_GUIDE.md          (Existing)
```

---

## 🔧 Integration with Migration_Environment.bat

Both wrappers check for and load `Migration_Environment.bat` from the parent directory:

```batch
if exist "..\Migration_Environment.bat" (
    call ..\Migration_Environment.bat
)
```

**Expected location:**
```
IntelliSTOR_Migration/
  ├── Migration_Environment.bat          (Parent environment file)
  ├── 8_Create_IRPT_File/
  │   └── rpt_file_builder_wrapper.bat   (Calls parent ..\Migration_Environment.bat)
  └── 9_Papyrus_rpt_page_extractor/
      └── papyrus_rpt_page_extractor.bat (Calls parent ..\Migration_Environment.bat)
```

---

## 📝 Log File Format

Both wrappers create log files in the same directory as the executable:

**papyrus_rpt_page_extractor_LOG.txt:**
```
[2026-02-08 14:30:15] RPT: input.rpt | Selection: pages:1-5 | Duration: 00:00:03 | Status: SUCCESS
[2026-02-08 14:35:42] RPT: report.rpt | Selection: sections:14259 | Duration: 00:00:02 | Status: SUCCESS
[2026-02-08 14:40:10] RPT: test.rpt | Selection: all | Duration: 00:00:01 | Status: FAILED (Exit Code 2)
```

**rpt_file_builder_LOG.txt:**
```
[2026-02-08 14:32:18] Input: ./pages/ | Output: output.RPT | Duration: 00:00:05 | Status: SUCCESS
[2026-02-08 14:38:55] Input: ./extracted/ | Output: rebuilt.RPT | Duration: 00:00:08 | Status: SUCCESS
[2026-02-08 14:42:33] Input: ./test/ | Output: test.RPT | Duration: 00:00:01 | Status: FAILED (Exit Code 3)
```

---

## 🎯 Use Cases

### Development/Testing (Command-Line)

Quick testing with different parameters:
```batch
papyrus_rpt_page_extractor.bat test.rpt "pages:1-3" out.txt out.pdf
```

### Production/Automation (Environment Variables)

Set up in Migration_Environment.bat or calling script:
```batch
call Migration_Environment.bat
set RPT_INPUT=%SOURCE_DIR%\report_%DATE:~-4,4%%DATE:~-10,2%%DATE:~-7,2%.rpt
set RPT_SELECTION=all
set RPT_OUTPUT_TXT=%OUTPUT_DIR%\report.txt
set RPT_OUTPUT_BINARY=%OUTPUT_DIR%\report.pdf
papyrus_rpt_page_extractor.bat
```

### Batch Processing (Loop)

Process multiple files:
```batch
for %%F in (C:\Reports\*.rpt) do (
    papyrus_rpt_page_extractor.bat "%%F" "all" "%%~nF.txt" "%%~nF.pdf"
)
```

---

## 📚 Documentation

Each wrapper includes:

1. **Inline Help** - Usage examples in script comments
2. **Error Messages** - Clear guidance when parameters are missing
3. **Environment Examples** - Template files showing variable usage
4. **Log Files** - Automatic execution tracking

**View Help:**
```batch
REM Open the .bat file in a text editor to see usage examples
notepad papyrus_rpt_page_extractor.bat

REM Or run without parameters to see error message with usage
papyrus_rpt_page_extractor.bat
```

---

## ✅ Testing Checklist

### papyrus_rpt_page_extractor.bat

- [x] Script created
- [x] Environment template created
- [ ] Test with command-line arguments
- [ ] Test with environment variables
- [ ] Verify log file creation
- [ ] Test error handling (missing file)
- [ ] Test with PDF extraction
- [ ] Test duration calculation

### rpt_file_builder_wrapper.bat

- [x] Script created
- [x] Environment template created
- [ ] Test with command-line arguments
- [ ] Test with environment variables
- [ ] Verify log file creation
- [ ] Test error handling (missing input)
- [ ] Test directory input
- [ ] Test file list input
- [ ] Test duration calculation

---

## 🚀 Next Steps

1. **Test the wrappers** with sample data
2. **Update Migration_Environment.bat** to include RPT-related environment variables if needed
3. **Integrate into automation scripts** for production workflows
4. **Document in main project README** if not already done

---

**Created:** 2026-02-08
**Pattern:** Based on Extract_Users_Permissions.bat example
**Status:** Ready for testing and integration
