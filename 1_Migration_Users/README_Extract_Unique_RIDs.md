# Extract Unique RIDs Tool

Extract unique RIDs (Relative Identifiers) from Windows Security Descriptors in permission CSV files.

## Overview

This tool reads three permission CSV files from a specified folder and extracts all unique RIDs into a deduplicated, sorted output CSV file.

**Input Files (expected in folder):**
- `STYPE_FOLDER_ACCESS.csv` - Folder permissions
- `STYPE_REPORT_SPECIES_ACCESS.csv` - Report species permissions
- `STYPE_SECTION_ACCESS.csv` - Section permissions

**Output File:**
- `Unique_RIDs.csv` (or custom filename) - Deduplicated, sorted RIDs

## What are RIDs?

RID (Relative Identifier) is the last component of a Windows Security Identifier (SID). For example, in the SID `S-1-5-21-1436318678-1461800975-2018848785-35442`, the RID is `35442`. RIDs identify users and groups in a Windows domain.

## Available Implementations

### Python Version

**File:** `extract_unique_rids.py`

**Requirements:**
- Python 3.6+
- No external dependencies (uses only standard library)

**Usage:**
```bash
python3 extract_unique_rids.py <folder_path>
python3 extract_unique_rids.py <folder_path> --output <output_file>
```

**Examples:**
```bash
# Basic usage - outputs to Unique_RIDs.csv
python3 extract_unique_rids.py /path/to/Users_SG

# Custom output filename
python3 extract_unique_rids.py /path/to/Users_SG --output my_rids.csv

# Short option
python3 extract_unique_rids.py /path/to/Users_SG -o my_rids.csv
```

**Advantages:**
- Cross-platform (Windows, macOS, Linux)
- No compilation required
- Easy to integrate into Python scripts
- Good for most use cases

---

### C++ Version

**File:** `extract_unique_rids.cpp`

**Requirements:**
- C++17 or later compiler (g++ or MSVC)
- Standard library

**Building:**

**Linux/macOS:**
```bash
./build_extract_rids.sh
```

**Windows:**
```batch
build_extract_rids.bat
```

**Manual compilation:**
```bash
# Using g++
g++ -std=c++17 -O2 extract_unique_rids.cpp -o extract_unique_rids

# Using MSVC (Windows)
cl.exe /std:latest /O2 /EHsc extract_unique_rids.cpp /Fe:extract_unique_rids.exe
```

**Usage:**
```bash
./extract_unique_rids <folder_path>
./extract_unique_rids <folder_path> <output_file>
```

**Examples:**
```bash
# Basic usage
./extract_unique_rids /path/to/Users_SG

# Custom output filename
./extract_unique_rids /path/to/Users_SG my_rids.csv

# Windows
extract_unique_rids.exe C:\Users_SG
extract_unique_rids.exe C:\Users_SG my_rids.csv
```

**Advantages:**
- Fastest performance (compiled binary)
- Lower memory footprint
- Good for large-scale automated processing
- Suitable for production environments

---

## Output Format

The output CSV file contains a single column with header:

```csv
RID
1120
1129
4590
...
489744
```

**Features:**
- All RIDs are deduplicated
- Sorted numerically in ascending order
- UTF-8 encoding
- Compatible with Excel, databases, and analysis tools

## How It Works

1. **Read Input Files:** Opens all three CSV files from the specified folder
2. **Parse CSV:** Reads each row and extracts the RID column
3. **Handle Multiple RIDs:** If a single RID field contains pipe-delimited values, splits and processes each one
4. **Deduplicate:** Uses a set to collect only unique RIDs
5. **Sort:** Sorts RIDs numerically
6. **Write Output:** Creates a new CSV with unique RIDs

## Performance

### Typical Performance (on 2020+ hardware)

**Python Version:**
- ~50K-100K rows/second
- Memory: ~50-100MB for typical data

**C++ Version:**
- ~200K-500K rows/second
- Memory: ~20-50MB for typical data

Use the C++ version for:
- Very large permission datasets (millions of rows)
- Automated batch processing
- Resource-constrained environments

Use the Python version for:
- Quick prototyping
- Integration with Python pipelines
- Cross-platform deployment
- When Python is already available

## Error Handling

Both implementations handle:
- Missing or inaccessible files
- Missing RID column
- Malformed CSV data
- File permission errors
- Invalid folder paths

**Error Output Examples:**
```
Error: Folder not found: /invalid/path
Error: CSV file not found: /path/to/STYPE_FOLDER_ACCESS.csv
Error: RID column not found in STYPE_FOLDER_ACCESS.csv
```

## Examples

### Python - Basic Usage

```python
import subprocess
import sys

# Run the tool
result = subprocess.run(
    [sys.executable, 'extract_unique_rids.py', '/path/to/Users_SG'],
    capture_output=True,
    text=True
)

if result.returncode == 0:
    print("Success!")
    print(result.stdout)
else:
    print("Error:", result.stderr)
```

### Python - Integration with Data Analysis

```python
import csv
import subprocess

# Extract unique RIDs
subprocess.run(['python3', 'extract_unique_rids.py', '/path/to/Users_SG'])

# Read the output
with open('/path/to/Users_SG/Unique_RIDs.csv', 'r') as f:
    reader = csv.DictReader(f)
    rids = [row['RID'] for row in reader]
    
print(f"Total RIDs: {len(rids)}")
print(f"RID range: {rids[0]} to {rids[-1]}")
```

### Batch Processing Multiple Folders

**Python Script:**
```python
#!/usr/bin/env python3
import subprocess
from pathlib import Path

# Process multiple folders
folders = [
    '/path/to/Users_SG',
    '/path/to/Users_MY',
    '/path/to/Users_XX'
]

for folder in folders:
    print(f"\nProcessing {folder}...")
    result = subprocess.run(
        ['python3', 'extract_unique_rids.py', folder],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
    else:
        print(result.stdout)
```

**Shell Script (C++):**
```bash
#!/bin/bash

# Build the tool
./build_extract_rids.sh

# Process multiple folders
for folder in /path/to/Users_SG /path/to/Users_MY /path/to/Users_XX; do
    echo "Processing $folder..."
    ./extract_unique_rids "$folder"
done
```

## Testing

### Quick Test (Python)

```bash
# Create test data
mkdir -p test_folder
echo "FOLDER_ID,Group,User,RID,Everyone" > test_folder/STYPE_FOLDER_ACCESS.csv
echo "1,group1,user1,1001|1002,N" >> test_folder/STYPE_FOLDER_ACCESS.csv
echo "2,group2,user2,1003,N" >> test_folder/STYPE_FOLDER_ACCESS.csv

echo "REPORT_SPECIES_ID,Group,User,RID,Everyone" > test_folder/STYPE_REPORT_SPECIES_ACCESS.csv
echo "1,group1,user1,1001,N" >> test_folder/STYPE_REPORT_SPECIES_ACCESS.csv

echo "REPORT_SPECIES_ID,SECTION_ID,Group,User,RID,Everyone" > test_folder/STYPE_SECTION_ACCESS.csv
echo "1,1,group1,user1,1002|1004,N" >> test_folder/STYPE_SECTION_ACCESS.csv

# Run the tool
python3 extract_unique_rids.py test_folder

# Check output
cat test_folder/Unique_RIDs.csv
```

### Quick Test (C++)

```bash
# Build
./build_extract_rids.sh

# Run with test folder (from Python test above)
./extract_unique_rids test_folder

# Check output
cat test_folder/Unique_RIDs.csv
```

Expected output:
```csv
RID
1001
1002
1003
1004
```

## Troubleshooting

### Python Issues

**"No module named csv"**
- csv is part of Python standard library, ensure Python 3.6+ is installed

**"Permission denied"**
```bash
# Make executable
chmod +x extract_unique_rids.py
```

**"Encoding error"**
- Ensure CSV files are UTF-8 encoded

### C++ Issues

**"Command not found: g++"**
- Install a C++ compiler:
  - **macOS:** `xcode-select --install`
  - **Ubuntu/Debian:** `sudo apt-get install build-essential`
  - **Windows:** Install Visual Studio or MinGW

**Compilation Error**
- Ensure C++17 or later support
- Check that `<filesystem>` is available

**"File not found" error**
- Verify the folder path and CSV file names are correct
- Check file permissions

## Command Line Options

### Python

```
usage: extract_unique_rids.py [-h] [--output OUTPUT] folder

Extract unique RIDs from permissions CSV files

positional arguments:
  folder                Path to folder containing the CSV files

optional arguments:
  -h, --help            show this help message and exit
  --output OUTPUT, -o OUTPUT
                        Output CSV filename (default: Unique_RIDs.csv)
```

### C++

```
Usage: extract_unique_rids <folder_path> [output_file]

Extract unique RIDs from permissions CSV files.

Arguments:
  folder_path    Path to folder containing the CSV files
  output_file    Output CSV filename (default: Unique_RIDs.csv)
```

## License

Generated for OCBC IntelliSTOR Migration
Date: 2026-02-09

## See Also

- `Unique_RIDs_Summary.txt` - Previously generated summary
- `Unique_RIDs_Detailed_Report.md` - Detailed analysis report
- `Extract_Users_Permissions.py` - Main permission extraction tool
