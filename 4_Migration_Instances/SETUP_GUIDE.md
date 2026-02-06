# Setup Guide for Extract_Instances.py

## Overview
This guide will help you set up and run Extract_Instances.py on a machine with SQL Server access.

---

## Step 1: Gather SQL Server Connection Information

Before starting, you need to know these details about your SQL Server:

### Required Information:
1. **Server Name/IP Address** - Example: `localhost`, `MYSERVER`, or `192.168.1.100`
2. **Port** - Usually `1433` (default)
3. **Database Name** - Example: `IntelliSTOR`
4. **Authentication Method** - Choose one:
   - **Windows Authentication** (if the Windows user has SQL Server access)
   - **SQL Server Authentication** (requires username and password)

### How to Find This Information:
- Open **SQL Server Management Studio (SSMS)** on the SQL Server machine
- Look at the connection dialog when you connect
- Server name is shown in the "Server name" field
- Database name is visible in the Object Explorer after connecting

---

## Step 2: Install Python (if not already installed)

### Check if Python is installed:
Open Command Prompt and run:
```cmd
python --version
```

If you see `Python 3.x.x`, you have Python installed. **You need Python 3.7 or higher.**

### If Python is NOT installed:
1. Download Python from: https://www.python.org/downloads/
2. Run the installer
3. **IMPORTANT**: Check the box "Add Python to PATH" during installation
4. Complete the installation
5. Verify by running `python --version` in a new Command Prompt

---

## Step 3: Copy Files to the SQL Server Machine

Copy these files to the SQL Server machine in the same folder:
- `Extract_Instances.py`
- `requirements.txt`
- `test_connection.py`
- `Report_Species.csv`

**Example folder structure:**
```
C:\MyProject\
├── Extract_Instances.py
├── test_connection.py
├── requirements.txt
└── Report_Species.csv
```

---

## Step 4: Install Python Dependencies

Open Command Prompt and navigate to your project folder:
```cmd
cd C:\MyProject
```

Install the required Python library:
```cmd
pip install -r requirements.txt
```

**What this installs:**
- `pymssql` - A Python library that allows Python to connect to SQL Server

### If you get an error:
Try using `pip3` instead of `pip`:
```cmd
pip3 install -r requirements.txt
```

Or install directly:
```cmd
pip install pymssql
```

---

## Step 5: Test the Connection

Before running the main script, test that Python can connect to SQL Server:

### Option A: Using Windows Authentication
```cmd
python test_connection.py --server localhost --database IntelliSTOR --windows-auth
```

### Option B: Using SQL Server Authentication
```cmd
python test_connection.py --server localhost --database IntelliSTOR --user sa --password YourPassword
```

**Note:** This only tests the connection. The actual extraction requires additional parameters (see next step).

**Replace:**
- `localhost` with your server name/IP
- `IntelliSTOR` with your database name
- `sa` and `YourPassword` with your SQL Server username and password

### Expected Output:
If successful, you'll see:
```
✓ Connection successful!
Database: IntelliSTOR
Server: localhost
```

If there's an error, the script will show what went wrong.

---

## Step 6: Run the Main Script

Once the connection test succeeds, run the main extraction script.

**IMPORTANT:** You must specify `--start-year` to filter which report instances to extract.

### Windows Authentication Example (extract from 2023 onwards):
```cmd
python Extract_Instances.py --server localhost --database IntelliSTOR --windows-auth --start-year 2023
```

### SQL Server Authentication Example (extract 2023-2024):
```cmd
python Extract_Instances.py --server localhost --database IntelliSTOR --user sa --password YourPassword --start-year 2023 --end-year 2024
```

### Using YEAR from Filename (instead of AS_OF_TIMESTAMP):
```cmd
python Extract_Instances.py --server localhost --database IntelliSTOR --windows-auth --start-year 2023 --year-from-filename
```

This extracts year from the first 2 characters of the filename:
- Filename: `24013001` → YEAR column: `2024`
- Filename: `23052045` → YEAR column: `2023`

### Quiet Mode (Single-Line Progress Counter):
```cmd
python Extract_Instances.py --server localhost --database IntelliSTOR --windows-auth --start-year 2023 --quiet
```

**Quiet mode benefits:**
- **No scrolling console output** - only one line that updates in place
- **Clean progress counter** showing current status
- **All logging still goes to Extract_Instances.log file** for debugging
- Perfect for production runs and large batches

**Console output in quiet mode:**
```
Processing 500 report species | Year filter: 2023+
Progress: 150/500 reports processed | 142 exported | 8 skipped

Completed: 500 reports processed | 478 exported | 22 skipped | 0 errors
```

The progress line updates continuously without scrolling.

### With Custom Output Folder:
```cmd
python Extract_Instances.py --server localhost --database IntelliSTOR --windows-auth --start-year 2023 --output-dir C:\Output
```

### With All Custom Options:
```cmd
python Extract_Instances.py ^
    --server localhost ^
    --database IntelliSTOR ^
    --windows-auth ^
    --start-year 2023 ^
    --end-year 2025 ^
    --year-from-filename ^
    --input "C:\Data\Report_Species.csv" ^
    --output-dir "C:\Output"
```

**Note:** The `^` character continues the command on the next line in Windows Command Prompt

### Parameter Explanations:
- `--start-year 2023`: Only extract report instances with AS_OF_TIMESTAMP >= 2023-01-01
- `--end-year 2024`: Only extract report instances with AS_OF_TIMESTAMP < 2025-01-01 (up to end of 2024)
- `--year-from-filename`: Calculate YEAR column from filename (first 2 chars + "20") instead of from AS_OF_TIMESTAMP

---

## Step 7: Monitor Progress

The script will:
1. Create a log file: `Extract_Instances.log`
2. Create a progress file: `progress.txt`
3. Create CSV files for each report: `{ReportName}.csv`

You can:
- Watch the console output for real-time progress
- Open `Extract_Instances.log` in Notepad to see detailed logs
- Check `progress.txt` to see the last processed Report_Species_Id

### If the Script is Interrupted:
Just run the same command again - it will resume from where it left off!

---

## Troubleshooting

### Error: "No module named 'pymssql'"
**Solution:** Install pymssql:
```cmd
pip install pymssql
```

### Error: "Login failed for user..."
**Solution:**
- Verify your username and password are correct
- Try using Windows Authentication instead: `--windows-auth`
- Check that the user has permission to access the database

### Error: "Cannot open database 'IntelliSTOR'"
**Solution:**
- Verify the database name is correct
- Check that the database exists in SQL Server Management Studio
- Verify your user has access to that specific database

### Error: "Server not found or not accessible"
**Solution:**
- Verify the server name/IP is correct
- Check that SQL Server is running
- Verify SQL Server is configured to accept remote connections (if connecting remotely)
- Try using `localhost` if the script runs on the same machine as SQL Server
- Try adding the port explicitly: `--server localhost --port 1433`

### Error: "Invalid column name 'STRING_AGG'"
**Solution:**
- Your SQL Server version is older than 2017
- STRING_AGG requires SQL Server 2017 or later
- Contact support for a compatible version of the query

### Error: "File not found: Report_Species.csv"
**Solution:**
- Verify the file exists in the expected location
- Use the full path: `--input "C:\full\path\to\Report_Species.csv"`
- Check spelling and file extension

### Script runs but creates no output files
**Solution:**
- Check `Extract_Instances.log` for details
- Verify the database tables exist: REPORT_INSTANCE, RPTFILE_INSTANCE, etc.
- Verify there is data in these tables
- Try running `test_connection.py` to verify basic connectivity

---

## Common Command Examples

### Basic run with Windows Auth (from 2023 onwards):
```cmd
python Extract_Instances.py --server localhost --database IntelliSTOR --windows-auth --start-year 2023
```

### Run with SQL Server Auth (specific year range):
```cmd
python Extract_Instances.py --server SQLSERVER01 --database IntelliSTOR --user sqluser --password Pass123 --start-year 2023 --end-year 2024
```

### Run with YEAR from filename:
```cmd
python Extract_Instances.py --server localhost --database IntelliSTOR --windows-auth --start-year 2023 --year-from-filename
```

### Run with quiet mode (single-line progress):
```cmd
python Extract_Instances.py --server localhost --database IntelliSTOR --windows-auth --start-year 2023 --quiet
```

### Run with all custom options:
```cmd
python Extract_Instances.py ^
    --server 192.168.1.50 ^
    --port 1433 ^
    --database IntelliSTOR ^
    --user myuser ^
    --password mypass ^
    --start-year 2023 ^
    --end-year 2025 ^
    --year-from-filename ^
    --input "D:\Data\Report_Species.csv" ^
    --output-dir "D:\Output"
```

### View help:
```cmd
python Extract_Instances.py --help
```

---

## Understanding the New Features

### Year Filtering (--start-year and --end-year)
The script filters report instances based on the `AS_OF_TIMESTAMP` column in the database:
- `--start-year 2023`: Include only records where AS_OF_TIMESTAMP >= 2023-01-01 00:00:00
- `--end-year 2024`: Include only records where AS_OF_TIMESTAMP < 2025-01-01 00:00:00

**Examples:**
- `--start-year 2023` (no end year) → All records from 2023 onwards
- `--start-year 2023 --end-year 2023` → Only records from year 2023
- `--start-year 2023 --end-year 2024` → Records from 2023 and 2024

### YEAR Column Calculation
The output CSV files include a YEAR column. You can choose how this is calculated:

**Default (from AS_OF_TIMESTAMP):**
```cmd
python Extract_Instances.py ... --start-year 2023
```
- Extracts year from the AS_OF_TIMESTAMP database field
- Example: AS_OF_TIMESTAMP = `2024-07-18 15:00:05.640` → YEAR = `2024`

**From Filename (--year-from-filename):**
```cmd
python Extract_Instances.py ... --start-year 2023 --year-from-filename
```
- Takes first 2 characters from FILENAME and prepends "20"
- Example: FILENAME = `24013001` → YEAR = `2024`
- Example: FILENAME = `23052045` → YEAR = `2023`

### Simplified Output Format
The CSV output files contain only essential columns (8 columns total):

1. **RPT_SPECIES_NAME**: Report species name from Report_Species.csv
2. **FILENAME**: Report filename from database
3. **Country**: Country code from Report_Species.csv
4. **YEAR**: Calculated year (from AS_OF_TIMESTAMP or filename based on flag)
5. **AS_OF_TIMESTAMP**: Timestamp of the report instance
6. **SEGMENT_NAME#...**: Segment information (pipe-separated, hash-delimited fields)
7. **REPORT_SPECIES_ID**: Report species ID from database
8. **REPORT_FILE_ID**: Report file ID from database

**Complete CSV Header:**
```
RPT_SPECIES_NAME,FILENAME,Country,YEAR,AS_OF_TIMESTAMP,SEGMENT_NAME#SEGMENT_NUMBER#PAGE_STREAM_INSTANCE_NUMBER#START_PAGE_NUMBER#NUMBER_OF_PAGES,REPORT_SPECIES_ID,REPORT_FILE_ID
```

**Sample Row:**
```csv
BC2060P,24013001.AFP,SG,2024,2024-07-18 15:00:05.640,501#1#1#1#5|502#2#1#6#3,0,25041540
```

---

## What to Expect

### During Execution (Normal Mode):
```
INFO - Connecting to SQL Server: localhost:1433, database: IntelliSTOR
INFO - Database connection established successfully
INFO - Loaded 500 report species from Report_Species.csv
INFO - Processing 500 report species (starting after ID 0)
INFO - Year filter: 2023+, YEAR column from: AS_OF_TIMESTAMP
INFO - Processing Report_Species_Id: 1, Name: BC2060P (1/500)
INFO - Query returned 5432 instances for BC2060P
INFO - Wrote 5432 rows to BC2060P.csv
INFO - Processing Report_Species_Id: 2, Name: BC2061P (2/500)
WARNING - Query returned 0 instances for BC2061P (year range: 2023+), updating In_Use=0
...
```

### During Execution (Quiet Mode with --quiet):
```
Processing 500 report species | Year filter: 2023+
Progress: 150/500 reports processed | 142 exported | 8 skipped
```

The progress line updates in place, showing real-time counts.

### After Completion:
```
INFO - ========================================
INFO - PROCESSING COMPLETE
INFO - Total reports processed: 500
INFO - Reports with instances: 478
INFO - Reports with no instances (In_Use set to 0): 22
INFO - Errors encountered: 0
INFO - ========================================
```

### Files Created:
- `Extract_Instances.log` - Detailed log file
- `progress.txt` - Progress tracking (contains last processed Report_Species_Id)
- `BC2060P.csv`, `BC2061P.csv`, etc. - One CSV file per report with instances

---

## Support

If you encounter issues:
1. Check `Extract_Instances.log` for detailed error messages
2. Verify all connection information is correct
3. Test basic connectivity with `test_connection.py`
4. Ensure SQL Server 2017 or later is being used
5. Verify the user has SELECT permissions on all required tables

---

## File Descriptions

| File | Purpose |
|------|---------|
| `Extract_Instances.py` | Main extraction script |
| `test_connection.py` | Connection testing utility |
| `requirements.txt` | Python dependencies list |
| `Report_Species.csv` | Input file with report species |
| `Extract_Instances.log` | Execution log (created at runtime) |
| `progress.txt` | Progress tracking (created at runtime) |
| `{ReportName}.csv` | Output files (one per report) |

---

## Quick Start Checklist

- [ ] Python 3.7+ installed
- [ ] Files copied to SQL Server machine
- [ ] `pip install -r requirements.txt` completed
- [ ] SQL Server connection info gathered
- [ ] `test_connection.py` runs successfully
- [ ] `Extract_Instances.py` running
