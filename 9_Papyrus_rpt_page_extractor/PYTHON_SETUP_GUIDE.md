# Python Setup and Installation Guide

## Overview

This guide covers setting up the Python version of the Papyrus RPT Page Extractor on Windows, macOS, and Linux systems.

## System Requirements

### Minimum Requirements
- **Python**: 3.7 or higher
- **Disk Space**: 10MB for script and dependencies
- **RAM**: 512MB minimum, 2GB recommended
- **OS**: Windows 7+, macOS 10.12+, or any modern Linux

### Recommended Requirements
- **Python**: 3.9 or higher
- **Disk Space**: 100MB for virtual environment
- **RAM**: 4GB or more
- **Modern OS**: Windows 10+, macOS 11+, Linux with glibc 2.17+

## Installation Steps

### Step 1: Verify Python Installation

#### Windows
```cmd
python --version
python -m pip --version
```

If not installed, download from [python.org](https://www.python.org) and install.

#### macOS
```bash
python3 --version
python3 -m pip --version
```

If not available, install via Homebrew:
```bash
brew install python3
```

#### Linux
```bash
python3 --version
python3 -m pip --version
```

If not available:
```bash
# Ubuntu/Debian
sudo apt-get install python3 python3-pip

# CentOS/RHEL
sudo yum install python3 python3-pip

# Fedora
sudo dnf install python3 python3-pip
```

### Step 2: Create Virtual Environment (Recommended)

#### Windows
```cmd
# Create virtual environment
python -m venv rpt_extractor_env

# Activate it
rpt_extractor_env\Scripts\activate

# Verify
python --version
```

#### macOS and Linux
```bash
# Create virtual environment
python3 -m venv rpt_extractor_env

# Activate it
source rpt_extractor_env/bin/activate

# Verify
python --version
```

### Step 3: Install the Script

#### Option A: Direct Installation

```bash
# Copy the script
cp papyrus_rpt_page_extractor.py /usr/local/bin/
chmod +x /usr/local/bin/papyrus_rpt_page_extractor.py

# Or on Windows
copy papyrus_rpt_page_extractor.py C:\Program Files\Python39\Scripts\
```

#### Option B: Virtual Environment Installation

```bash
# Copy to virtual environment
cp papyrus_rpt_page_extractor.py /path/to/rpt_extractor_env/bin/
chmod +x /path/to/rpt_extractor_env/bin/papyrus_rpt_page_extractor.py
```

#### Option C: Direct Papyrus Integration

```bash
# Copy directly to Papyrus bin directory
cp papyrus_rpt_page_extractor.py /path/to/papyrus/bin/
chmod +x /path/to/papyrus/bin/papyrus_rpt_page_extractor.py
```

### Step 4: Verify Installation

```bash
# Test the script
python papyrus_rpt_page_extractor.py

# Expected output (exit code 1):
# Usage: papyrus_rpt_page_extractor.py <input_rpt> <selection_rule> <output_txt> <output_binary>
```

## Platform-Specific Setup

### Windows Setup

#### Prerequisites
- Python 3.7+ from [python.org](https://www.python.org)
- Administrative access to install software

#### Installation Steps

1. **Download Python**:
   - Visit https://www.python.org/downloads/
   - Download Python 3.9+ installer
   - **Important**: Check "Add Python to PATH" during installation

2. **Verify Installation**:
   ```cmd
   python --version
   python -m pip --version
   ```

3. **Create Virtual Environment**:
   ```cmd
   python -m venv rpt_extractor_env
   rpt_extractor_env\Scripts\activate
   ```

4. **Install Script**:
   ```cmd
   copy papyrus_rpt_page_extractor.py rpt_extractor_env\Scripts\
   ```

5. **Test**:
   ```cmd
   python papyrus_rpt_page_extractor.py
   ```

#### Windows Batch Wrapper (Optional)

Create `papyrus_rpt_page_extractor.bat`:

```batch
@echo off
REM Windows batch wrapper for Python script
setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set PYTHON_VENV=%SCRIPT_DIR%rpt_extractor_env\Scripts\python.exe

if not exist "%PYTHON_VENV%" (
    echo Virtual environment not found at %PYTHON_VENV%
    exit /b 1
)

"%PYTHON_VENV%" "%SCRIPT_DIR%papyrus_rpt_page_extractor.py" %*
exit /b %errorlevel%
```

Usage in Papyrus:
```papyrus
shell_method extract_rpt_pages(input, rule, output_txt, output_bin)
{
    execute_command("papyrus_rpt_page_extractor.bat %TMPFILE{input} " & rule & 
        " %TMPFILE{output_txt} %TMPFILE{output_bin}");
}
```

### macOS Setup

#### Prerequisites
- Xcode Command Line Tools
- Python 3.7+ (via Homebrew recommended)

#### Installation Steps

1. **Install Python via Homebrew** (Recommended):
   ```bash
   brew install python3
   python3 --version
   ```

   Or install manually from [python.org](https://www.python.org)

2. **Create Virtual Environment**:
   ```bash
   python3 -m venv rpt_extractor_env
   source rpt_extractor_env/bin/activate
   ```

3. **Install Script**:
   ```bash
   cp papyrus_rpt_page_extractor.py rpt_extractor_env/bin/
   chmod +x rpt_extractor_env/bin/papyrus_rpt_page_extractor.py
   ```

4. **Create Symlink** (Optional):
   ```bash
   sudo ln -s /path/to/rpt_extractor_env/bin/papyrus_rpt_page_extractor.py \
       /usr/local/bin/papyrus_rpt_page_extractor.py
   ```

5. **Test**:
   ```bash
   source rpt_extractor_env/bin/activate
   python papyrus_rpt_page_extractor.py
   ```

#### macOS Shell Script Wrapper

Create `papyrus_rpt_page_extractor.sh`:

```bash
#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_VENV="$SCRIPT_DIR/rpt_extractor_env/bin/python3"

if [ ! -f "$PYTHON_VENV" ]; then
    echo "Virtual environment not found at $PYTHON_VENV"
    exit 1
fi

"$PYTHON_VENV" "$SCRIPT_DIR/papyrus_rpt_page_extractor.py" "$@"
exit $?
```

Make executable:
```bash
chmod +x papyrus_rpt_page_extractor.sh
```

### Linux Setup

#### Prerequisites
- Python 3.7+ (usually pre-installed)
- pip package manager
- Standard development tools

#### Installation Steps (Ubuntu/Debian)

1. **Install Python**:
   ```bash
   sudo apt-get update
   sudo apt-get install python3 python3-pip python3-venv
   python3 --version
   ```

2. **Create Virtual Environment**:
   ```bash
   python3 -m venv rpt_extractor_env
   source rpt_extractor_env/bin/activate
   ```

3. **Install Script**:
   ```bash
   cp papyrus_rpt_page_extractor.py rpt_extractor_env/bin/
   chmod +x rpt_extractor_env/bin/papyrus_rpt_page_extractor.py
   ```

4. **Install System-wide** (Optional):
   ```bash
   sudo cp papyrus_rpt_page_extractor.py /usr/local/bin/
   sudo chmod +x /usr/local/bin/papyrus_rpt_page_extractor.py
   ```

5. **Test**:
   ```bash
   python3 papyrus_rpt_page_extractor.py
   ```

#### Installation Steps (CentOS/RHEL)

```bash
# Install Python and tools
sudo yum install python3 python3-pip python3-devel

# Create virtual environment
python3 -m venv rpt_extractor_env
source rpt_extractor_env/bin/activate

# Install script
cp papyrus_rpt_page_extractor.py rpt_extractor_env/bin/
chmod +x rpt_extractor_env/bin/papyrus_rpt_page_extractor.py
```

#### Linux Systemd Service (Optional)

Create `/etc/systemd/system/rpt-extractor.service`:

```ini
[Unit]
Description=Papyrus RPT Page Extractor
After=network.target

[Service]
Type=simple
User=papyrus
WorkingDirectory=/opt/papyrus
ExecStart=/opt/papyrus/rpt_extractor_env/bin/python3 /opt/papyrus/bin/papyrus_rpt_page_extractor.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable rpt-extractor
sudo systemctl start rpt-extractor
```

## Integration with Papyrus

### Locating Papyrus Installation

#### Windows
```cmd
where papyrus
# Typical: C:\Program Files\Papyrus\bin\
```

#### macOS
```bash
which papyrus
# Typical: /usr/local/bin/papyrus or /opt/papyrus/bin/
```

#### Linux
```bash
which papyrus
# Typical: /usr/local/bin/papyrus or /opt/papyrus/bin/
```

### Adding to Papyrus PATH

Edit Papyrus configuration:

```papyrus
# In papyrus.cfg or environment
PAPYRUS_PYTHON_BIN=/path/to/python3
PAPYRUS_RPT_EXTRACTOR=/path/to/papyrus_rpt_page_extractor.py
```

### Testing Papyrus Integration

```papyrus
# Test shell method
shell_method test_rpt_extraction()
{
    # This assumes extract_rpt_pages is properly registered
    log_message("Testing RPT extraction", LOG_LEVEL_INFO);
}

# Call test
call test_rpt_extraction();
```

## Troubleshooting Installation

### Issue: "python: command not found"

**Windows**:
- Reinstall Python and select "Add Python to PATH"
- Or manually add Python directory to PATH

**macOS/Linux**:
```bash
# Check if python3 is available
which python3

# If not found, install Python
# macOS: brew install python3
# Ubuntu: sudo apt-get install python3
```

### Issue: "Permission denied" when running script

```bash
# Fix file permissions
chmod +x papyrus_rpt_page_extractor.py

# Or explicitly use python3
python3 papyrus_rpt_page_extractor.py
```

### Issue: Virtual environment activation fails

```bash
# Recreate virtual environment
rm -rf rpt_extractor_env
python3 -m venv rpt_extractor_env
source rpt_extractor_env/bin/activate
```

### Issue: Import errors in Papyrus

**Check**:
1. Python path is correct in Papyrus config
2. Virtual environment is activated
3. Script has execute permissions
4. Papyrus can read the script file

```bash
# Test manually
python3 papyrus_rpt_page_extractor.py "test.rpt" "all" "out.txt" "out.bin"
```

### Issue: "No such file or directory" in Papyrus

**Check that**:
1. Full paths are used in shell commands
2. %TMPFILE% macro is properly escaped
3. Papyrus user has read/write permissions

## Performance Optimization

### Python Optimization

1. **Use PyPy** (optional, faster execution):
   ```bash
   # Install PyPy
   brew install pypy3  # macOS
   
   # Create virtual environment with PyPy
   pypy3 -m venv rpt_extractor_pypy
   source rpt_extractor_pypy/bin/activate
   ```

2. **Enable Python optimizations**:
   ```bash
   # Use -O flag for optimizations
   python3 -O papyrus_rpt_page_extractor.py ...
   ```

3. **Profile your usage**:
   ```bash
   python3 -m cProfile papyrus_rpt_page_extractor.py report.rpt "all" out.txt out.bin
   ```

### System Optimization

1. **Increase file descriptor limits** (Linux):
   ```bash
   ulimit -n 65536
   ```

2. **Tune I/O for large files**:
   ```bash
   # Increase page cache
   sysctl -w vm.dirty_ratio=5
   ```

## Security Considerations

### File Permissions

```bash
# Restrict to owner only
chmod 700 rpt_extractor_env/
chmod 700 papyrus_rpt_page_extractor.py

# Set Papyrus user ownership
sudo chown papyrus:papyrus papyrus_rpt_page_extractor.py
```

### Input Validation

The script validates:
- File paths exist and are readable
- Selection rules are properly formatted
- Output directories are writable
- File sizes are within limits

### Secure Temporary Files

Temporary files from Papyrus `%TMPFILE%` are:
- Created in system temp directory with secure permissions
- Automatically cleaned up after use
- Not readable by other users

## Verification Checklist

After installation, verify:

- [ ] Python 3.7+ is installed
- [ ] Virtual environment is created (optional)
- [ ] Script is in the correct location
- [ ] Script has execute permissions
- [ ] Script can be called from Papyrus
- [ ] Sample RPT file processes correctly
- [ ] Output files are created
- [ ] Exit codes are correct

## Quick Start Commands

### Windows
```cmd
python -m venv rpt_env
rpt_env\Scripts\activate
copy papyrus_rpt_page_extractor.py rpt_env\Scripts\
python papyrus_rpt_page_extractor.py test.rpt "all" out.txt out.bin
```

### macOS
```bash
python3 -m venv rpt_env
source rpt_env/bin/activate
cp papyrus_rpt_page_extractor.py rpt_env/bin/
chmod +x rpt_env/bin/papyrus_rpt_page_extractor.py
python3 papyrus_rpt_page_extractor.py test.rpt "all" out.txt out.bin
```

### Linux
```bash
python3 -m venv rpt_env
source rpt_env/bin/activate
cp papyrus_rpt_page_extractor.py rpt_env/bin/
chmod +x rpt_env/bin/papyrus_rpt_page_extractor.py
python3 papyrus_rpt_page_extractor.py test.rpt "all" out.txt out.bin
```

## Next Steps

1. Review the main README for usage examples
2. Configure Papyrus integration
3. Test with your RPT files
4. Review troubleshooting guide if needed
5. Consult Papyrus documentation for shell method configuration

## Support Resources

- **Python Documentation**: https://docs.python.org/3/
- **Papyrus Documentation**: Refer to your Papyrus installation
- **Troubleshooting**: See main README file
- **Issues**: Check the issue tracker or documentation

## Version Information

- **Python Version**: Compatible with 3.7+
- **Tested on**: Python 3.7, 3.8, 3.9, 3.10, 3.11, 3.12
- **Last Updated**: 2025
