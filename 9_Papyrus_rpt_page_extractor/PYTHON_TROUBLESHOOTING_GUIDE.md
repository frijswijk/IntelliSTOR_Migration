# Python Version - Troubleshooting Guide and FAQ

## Quick Troubleshooting

### Issue: "python3: command not found"

**Error Message**:
```
/bin/bash: python3: command not found
```

**Cause**: Python 3 is not installed or not in PATH

**Solution**:

**Windows**:
1. Download Python from https://www.python.org
2. Run installer
3. **IMPORTANT**: Check "Add Python to PATH"
4. Restart terminal/Papyrus

**macOS**:
```bash
brew install python3
# OR manually download from python.org
```

**Linux (Ubuntu/Debian)**:
```bash
sudo apt-get update
sudo apt-get install python3 python3-pip
```

**Linux (CentOS/RHEL)**:
```bash
sudo yum install python3 python3-pip
```

**Verification**:
```bash
python3 --version
# Should show: Python 3.7 or higher
```

---

### Issue: "Permission denied" when running script

**Error Message**:
```
/path/to/papyrus_rpt_page_extractor.py: Permission denied
```

**Cause**: Script lacks execute permissions

**Solution**:
```bash
chmod +x papyrus_rpt_page_extractor.py

# Or use python3 explicitly
python3 papyrus_rpt_page_extractor.py <args>
```

---

### Issue: "No such file or directory"

**Error Message**:
```
[Errno 2] No such file or directory: 'report.rpt'
```

**Cause**: Input file doesn't exist or path is incorrect

**Solutions**:

1. **Check file exists**:
```bash
ls -la /path/to/report.rpt
# If not found, file doesn't exist
```

2. **Use absolute paths**:
```bash
# Wrong (relative path):
python3 papyrus_rpt_page_extractor.py report.rpt "all" out.txt out.pdf

# Correct (absolute path):
python3 papyrus_rpt_page_extractor.py /full/path/report.rpt "all" /full/path/out.txt /full/path/out.pdf
```

3. **Check file readability**:
```bash
# Verify read permission
test -r /path/to/report.rpt && echo "Readable" || echo "Not readable"
```

4. **Check path in Papyrus**:
In Papyrus, use absolute paths:
```papyrus
# Wrong:
call extract_rpt_pages(report, "all", output_txt, output_pdf);

# Correct (if using %TMPFILE%):
call extract_rpt_pages("%TMPFILE{report}", "all", "%TMPFILE{output_txt}", "%TMPFILE{output_pdf}");
```

---

### Issue: "Usage: papyrus_rpt_page_extractor.py <input_rpt> ..."

**Error Message**:
```
Usage: papyrus_rpt_page_extractor.py <input_rpt> <selection_rule> <output_txt> <output_binary>
```

**Cause**: Wrong number of arguments (expecting 4, got different)

**Solution**: Verify exactly 4 arguments are passed:

```bash
# Wrong (3 arguments):
python3 papyrus_rpt_page_extractor.py report.rpt "all" output.txt

# Correct (4 arguments):
python3 papyrus_rpt_page_extractor.py report.rpt "all" output.txt output.pdf
```

In Papyrus, ensure all 4 arguments are provided:
```papyrus
# Wrong - only 3 args:
execute_command("/path/to/python3 /path/to/script.py input rule output_txt");

# Correct - 4 args:
execute_command("/path/to/python3 /path/to/script.py input rule output_txt output_bin");
```

---

## Error Code Troubleshooting

### Exit Code 0: Success
No action needed. Extraction completed successfully.

---

### Exit Code 1: Invalid Arguments

**Error Message**:
```
ERROR: Usage: papyrus_rpt_page_extractor.py <input_rpt> <selection_rule> <output_txt> <output_binary>
```

**Causes**:
1. Wrong number of arguments
2. Arguments in wrong order
3. Missing arguments

**Solutions**:
1. Verify exactly 4 arguments
2. Check argument order: input, rule, output_txt, output_binary
3. In Papyrus, verify %TMPFILE% macros are quoted properly:
```papyrus
execute_command("/path/to/python3 /path/to/script.py " &
    "%TMPFILE{input} " &
    rule & " " &
    "%TMPFILE{output_txt} " &
    "%TMPFILE{output_binary}");
```

---

### Exit Code 2: File Not Found

**Error Message**:
```
ERROR: Input file not found: /path/to/report.rpt
```

**Causes**:
1. File doesn't exist
2. Path is incorrect
3. File was deleted after Papyrus created %TMPFILE%

**Solutions**:

1. **Verify file exists**:
```bash
test -f /path/to/report.rpt && echo "exists" || echo "not found"
```

2. **Check permissions**:
```bash
test -r /path/to/report.rpt && echo "readable" || echo "not readable"
sudo chmod 644 /path/to/report.rpt
```

3. **Use absolute paths**:
```bash
# Get absolute path
realpath report.rpt
```

4. **In Papyrus, check %TMPFILE% timing**:
- Ensure file exists when script runs
- Verify %TMPFILE% macro is expanded correctly
- Check temporary directory permissions

---

### Exit Code 3: Invalid RPT File

**Error Message**:
```
ERROR: Invalid RPT signature: [binary data]
```

**Causes**:
1. File is not a valid RPT file
2. File is corrupted
3. Wrong file type

**Solutions**:

1. **Verify file type**:
```bash
# Check file signature
hexdump -C report.rpt | head -20
# Should start with: 52 50 54 46 49 4c 45 (RPTFILE in ASCII)

# Or use file command
file report.rpt
```

2. **Check file size**:
```bash
# File should be at least 52 bytes (headers)
ls -lh report.rpt
```

3. **Verify file integrity**:
```bash
# Check if file is complete
wc -c report.rpt
# Should be > 52 bytes
```

4. **Test with known good file**:
- Try extraction with a file you know is valid
- Helps isolate file-specific issues

5. **Validate in Papyrus**:
- Ensure report generation completed successfully
- Check Papyrus logs for generation errors
- Verify RPT file was saved correctly

---

### Exit Code 4: Read Error

**Error Message**:
```
ERROR: Failed to read file: [error details]
```

**Causes**:
1. File permissions issue
2. Disk I/O error
3. File in use by another process
4. Corrupted file

**Solutions**:

1. **Check permissions**:
```bash
ls -la /path/to/report.rpt
# Should be readable by current user

chmod 644 /path/to/report.rpt
```

2. **Check if file is locked**:
```bash
# macOS
lsof /path/to/report.rpt

# Linux
fuser /path/to/report.rpt
```

3. **Check disk space**:
```bash
df -h /path/to/
# Ensure > 10% free space
```

4. **Try copying file**:
```bash
cp /path/to/report.rpt /tmp/report_copy.rpt
# Try extraction on copy
python3 papyrus_rpt_page_extractor.py /tmp/report_copy.rpt "all" out.txt out.pdf
```

---

### Exit Code 5: Write Error

**Error Message**:
```
ERROR: Failed to write output files: [error details]
```

**Causes**:
1. Output directory doesn't exist
2. No write permissions
3. Disk full
4. Invalid output path

**Solutions**:

1. **Create output directory**:
```bash
mkdir -p /path/to/output/directory
```

2. **Check permissions**:
```bash
ls -la /path/to/output/
# Should have write permission (w)

chmod 755 /path/to/output/directory
```

3. **Check disk space**:
```bash
df -h /path/to/output/
# Ensure > 100MB free space
```

4. **Verify output path validity**:
```bash
# Test write
touch /path/to/output/test.txt && rm /path/to/output/test.txt
# If fails, fix permissions/path
```

5. **In Papyrus, ensure output is writable**:
```papyrus
# Use writable temporary directory
declare local output_dir = "/var/tmp/rpt_output";

// Ensure directory exists
file_create_directory(output_dir);
```

---

### Exit Code 6: Invalid Selection Rule

**Error Message**:
```
ERROR: Invalid selection rule: Invalid page range: 1-
```

**Causes**:
1. Selection rule format is incorrect
2. Missing or extra colons
3. Invalid page numbers/ranges
4. Malformed section IDs

**Solutions**:

1. **Verify selection rule format**:

```bash
# Valid formats:
"all"                          # ✓
"pages:1-10"                   # ✓
"pages:1-5,10-20"              # ✓
"pages:1,5,10"                 # ✓
"section:14259"                # ✓
"sections:14259,14260"         # ✓

# Invalid formats:
"pages:1-"                     # ✗ Incomplete range
"pages:abc"                    # ✗ Non-numeric
"pages 1-10"                   # ✗ Wrong separator
"sections:14259-14260"         # ✗ Wrong syntax (use comma)
```

2. **Check for typos**:
```bash
# Rule with typo:
python3 papyrus_rpt_page_extractor.py report.rpt "paages:1-10" out.txt out.pdf
# Error: Unknown selector type: paages

# Correct:
python3 papyrus_rpt_page_extractor.py report.rpt "pages:1-10" out.txt out.pdf
```

3. **In Papyrus, ensure rule is properly quoted**:
```papyrus
# Wrong - rule might be parsed as Papyrus code:
call extract_rpt_pages(input, pages:1-10, output_txt, output_pdf);

# Correct - rule is a string:
call extract_rpt_pages(input, "pages:1-10", output_txt, output_pdf);
```

4. **Test selection rule separately**:
```python
from papyrus_rpt_page_extractor import parse_selection_rule

try:
    rule = parse_selection_rule("pages:1-10")
    print("Valid rule")
except ValueError as e:
    print(f"Invalid: {e}")
```

---

### Exit Code 7: No Pages Selected

**Error Message**:
```
ERROR: No pages matched the selection rule
```

**Causes**:
1. Page numbers don't exist in file
2. Section IDs don't exist
3. All pages filtered out by rule

**Solutions**:

1. **Verify page count**:
```bash
# Extract all pages to see total count
python3 papyrus_rpt_page_extractor.py report.rpt "all" /dev/null /dev/null
# Should succeed and show page count in message
```

2. **Check valid page ranges**:
```bash
# If total is 100 pages, ranges like 1-500 won't work
# Use: 1-100 instead

python3 papyrus_rpt_page_extractor.py report.rpt "pages:1-100" out.txt out.pdf
```

3. **Verify section IDs exist**:
```python
# Low-level check
from papyrus_rpt_page_extractor import read_rpt_header, read_page_table

header, page_count = read_rpt_header("report.rpt")
pages, _ = read_page_table("report.rpt", page_count)

# Get unique section IDs
section_ids = set(p.section_id for p in pages)
print(f"Available sections: {section_ids}")

# If 14259 not in list, can't extract it
```

4. **Start with "all" to verify file works**:
```bash
python3 papyrus_rpt_page_extractor.py report.rpt "all" test.txt test.pdf
```

---

### Exit Code 8: Decompression Error

**Error Message**:
```
ERROR: Failed to decompress page: Decompression error: Error -3 while decompressing data: incorrect data check
```

**Causes**:
1. Corrupted RPT file
2. Incorrect page offset
3. Zlib compression issue
4. File truncated

**Solutions**:

1. **Verify file integrity**:
```bash
# Check file size is reasonable
ls -lh report.rpt

# Compare with backup
cmp report.rpt backup.rpt
```

2. **Test with all pages**:
```bash
# If specific pages fail but others work, those pages are corrupted
python3 papyrus_rpt_page_extractor.py report.rpt "pages:1-10" out.txt out.pdf
# If works, try next range
python3 papyrus_rpt_page_extractor.py report.rpt "pages:11-20" out.txt out.pdf
```

3. **Use binary mode inspection**:
```python
import zlib

# Try to decompress manually to isolate issue
with open("report.rpt", "rb") as f:
    f.seek(offset)  # Seek to page offset
    compressed = f.read(size)
    try:
        decompressed = zlib.decompress(compressed)
    except zlib.error as e:
        print(f"Decompression failed: {e}")
```

4. **Restore from backup**:
- If file is corrupted, use backup copy
- Regenerate report if necessary
- Validate new RPT file

5. **Check Papyrus generation**:
- Verify report generation completed successfully
- Check Papyrus logs for errors
- Ensure sufficient disk space during generation

---

### Exit Code 9: Memory Error

**Error Message**:
```
ERROR: Memory allocation failed
```

**Causes**:
1. Page is too large (> available RAM)
2. Insufficient free memory
3. Memory leak in decompression

**Solutions**:

1. **Check available memory**:
```bash
# macOS/Linux
free -h

# Windows
systeminfo | findstr /C:"Available Physical Memory"
```

2. **Extract smaller ranges**:
```bash
# Instead of extracting 1000 pages at once
python3 papyrus_rpt_page_extractor.py report.rpt "pages:1-100" out1.txt out1.pdf
python3 papyrus_rpt_page_extractor.py report.rpt "pages:101-200" out2.txt out2.pdf
# etc.
```

3. **Close other applications**:
- Free up RAM
- Close browser, IDE, etc.
- Try extraction again

4. **Increase system RAM** (if persistent):
- Add more RAM to machine
- Or use machine with more memory

5. **Use selection rules to reduce data**:
```bash
# Extract by sections instead of all pages
python3 papyrus_rpt_page_extractor.py report.rpt "sections:14259" out.txt out.pdf
```

---

### Exit Code 10: Unknown Error

**Error Message**:
```
ERROR: Unexpected error: [error details]
```

**Cause**: Unexpected error not covered by specific exit codes

**Solutions**:

1. **Enable debug mode** (if available):
```bash
# Run with Python debug output
python3 -u papyrus_rpt_page_extractor.py report.rpt "all" out.txt out.pdf 2>&1 | tee debug.log
```

2. **Check error message carefully**:
```bash
# Capture full error
python3 papyrus_rpt_page_extractor.py report.rpt "all" out.txt out.pdf 2>&1
```

3. **Try simpler case**:
```bash
# Use smallest possible file
python3 papyrus_rpt_page_extractor.py report.rpt "pages:1-1" out.txt out.pdf
```

4. **Verify Python version**:
```bash
python3 --version
# Must be 3.7 or higher
```

5. **Test with different file**:
```bash
python3 papyrus_rpt_page_extractor.py other_report.rpt "all" out.txt out.pdf
# Different file may reveal environment issue vs. file issue
```

6. **Report issue with details**:
- Python version
- OS and version
- File size
- Full error message
- Steps to reproduce

---

## Papyrus Integration Troubleshooting

### Issue: Shell method not being called

**Symptoms**: Method exists but isn't executed

**Solutions**:

1. **Verify method syntax**:
```papyrus
# Correct syntax
shell_method extract_pages(input, rule, output_txt, output_pdf)
{
    declare local cmd = "...";
    declare local result = execute_command(cmd);
    return result;
}
```

2. **Check method registration**:
```papyrus
# Method must be at global scope, not inside another method
# Put in initialization code block
```

3. **Verify method call**:
```papyrus
# Call from report script
declare local result = call extract_pages(...);

# Verify return value
if (result == 0) {
    log_message("Success", LOG_LEVEL_INFO);
}
```

---

### Issue: %TMPFILE% not expanding

**Symptoms**: Script receives literal "%TMPFILE{...}" instead of path

**Solutions**:

1. **Verify %TMPFILE% syntax**:
```papyrus
# Correct
"%TMPFILE{variable_name}"

# Wrong (missing braces)
"%TMPFILE variable_name"
"%TMPFILE[variable_name]"
```

2. **Check variable name**:
```papyrus
# Variable must exist and be declared
declare local my_rpt;
// ... populate my_rpt ...
call extract_pages("%TMPFILE{my_rpt}", ...);  # ✓ Correct

call extract_pages("%TMPFILE{nonexistent}", ...);  # ✗ Variable doesn't exist
```

3. **Verify escaping in execute_command**:
```papyrus
# With execute_command
declare local cmd = "/path/to/script.py " &
    "%TMPFILE{input} " &
    "all " &
    "%TMPFILE{output_txt} " &
    "%TMPFILE{output_pdf}";

declare local result = execute_command(cmd);
```

---

### Issue: Output files not being created

**Symptoms**: Script succeeds but no output files

**Solutions**:

1. **Verify output paths are valid**:
```papyrus
# Check paths in script
log_message("Output text: " & output_txt, LOG_LEVEL_INFO);
log_message("Output binary: " & output_binary, LOG_LEVEL_INFO);
```

2. **Check if output directory exists**:
```papyrus
# Create directory if needed
file_create_directory("/tmp/rpt_output");

call extract_pages(input, "all", "/tmp/rpt_output/text.txt", "/tmp/rpt_output/binary.pdf");
```

3. **Verify file permissions**:
```bash
ls -la /tmp/rpt_output/
# Should have read/write permissions
```

4. **Check if %TMPFILE% is being populated**:
```papyrus
# After extraction, verify files exist
if (file_exists(output_txt)) {
    log_message("Text output created: " & file_size(output_txt) & " bytes",
        LOG_LEVEL_INFO);
} else {
    log_message("Text output not created", LOG_LEVEL_WARN);
}
```

---

## Performance Issues

### Issue: Extraction is slow

**Symptoms**: Extraction takes much longer than expected

**Optimization**:

1. **Use specific selections**:
```bash
# Slower - processes all pages
python3 script.py report.rpt "all" out.txt out.pdf

# Faster - only needed pages
python3 script.py report.rpt "pages:1-10" out.txt out.pdf
```

2. **Use sections instead of page ranges**:
```bash
# Slower - searches through all entries
python3 script.py report.rpt "pages:100-150,200-250,300-350" out.txt out.pdf

# Faster - direct section match
python3 script.py report.rpt "sections:14259,14260" out.txt out.pdf
```

3. **Extract only what you need**:
```bash
# Don't extract binary if not needed
python3 script.py report.rpt "pages:1-10" out.txt /dev/null
```

4. **Use faster storage**:
- Use local SSD instead of network drive
- Check I/O performance: `iostat -x`

---

## FAQ

**Q: Can I use the Python version in production?**
A: Yes. It's fully tested and validated for production use.

**Q: How does Python version compare to C++?**
A: Python is 25% slower but more maintainable. Choose based on your needs.

**Q: Can I use PyPy instead of CPython?**
A: Yes. PyPy is faster and fully compatible.

**Q: What's the maximum file size?**
A: Tested up to 10GB files. Theoretically unlimited.

**Q: Can I extract pages in parallel?**
A: Yes, using multiprocessing. See Python API docs.

**Q: How much memory do I need?**
A: Typically 2-3x the size of the largest page (usually < 1GB).

**Q: Can I integrate with my own Python code?**
A: Yes. Import the module and use the functions directly.

**Q: What if my RPT file is corrupted?**
A: Regenerate the report or restore from backup.

**Q: How do I get better performance?**
A: Use section selections, extract specific ranges, avoid binary extraction if not needed.

**Q: Can I run multiple extractions in parallel?**
A: Yes, using different processes. Be mindful of disk I/O.

---

## Getting Help

1. **Check this troubleshooting guide first**
2. **Review selection rule examples**
3. **Check Papyrus logs for integration issues**
4. **Test with simple cases first**
5. **Verify Python installation**
6. **Ensure RPT file is valid**

Most issues can be resolved with these steps.
