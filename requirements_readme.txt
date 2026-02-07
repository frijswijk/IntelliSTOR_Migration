Python Virtual Environment Setup
=================================

The venv/ folder is NOT included in the repository (.gitignore).
It must be recreated on each machine because it contains platform-specific
binaries (e.g., Mac arm64 vs Windows x64).

Setup Steps
-----------

1. Create the virtual environment (one-time, from the project root):

   Windows:
     python -m venv venv
     venv\Scripts\activate
     pip install -r requirements.txt

   macOS:
     python3 -m venv venv
     source venv/bin/activate
     pip install -r requirements.txt

2. Verify installation:

     python -c "import pymssql; import pytz; print('OK')"

Dependencies
------------

  pymssql   - Microsoft SQL Server database access
  pytz      - Timezone handling for date conversions

These are defined in requirements.txt at the project root.

Which Scripts Need the venv?
----------------------------

All Python scripts in this project require the venv to be activated.
The .command (macOS) and .bat (Windows) wrapper scripts activate it
automatically via:

  macOS:    source "${SCRIPT_DIR}/../venv/bin/activate"
  Windows:  call venv\Scripts\activate.bat

So double-clicking a .command or .bat file handles activation for you.
You only need to activate manually when running Python scripts directly
from the command line.
