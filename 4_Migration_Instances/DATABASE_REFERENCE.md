# IntelliSTOR MS SQL Database Reference

## Connection Details

```
Server: localhost
Port: 1433
Database: iSTSGUAT
User: sa
Password: Fvrpgr40
```

### Python Connection (pymssql)

```python
import pymssql

conn = pymssql.connect(
    server='localhost',
    port=1433,
    user='sa',
    password='Fvrpgr40',
    database='iSTSGUAT'
)
cursor = conn.cursor(as_dict=True)
```

### Command Line (sqlcmd)

```bash
sqlcmd -S localhost -U sa -P Fvrpgr40 -d iSTSGUAT
```

---

## Key Tables

### REPORT_INSTANCE
Primary key for a report instance (a specific run of a report).

| Column | Type | Description |
|--------|------|-------------|
| DOMAIN_ID | int | Domain identifier (usually 1) |
| REPORT_SPECIES_ID | int | Report type identifier |
| AS_OF_TIMESTAMP | datetime | When the report was generated |
| STRUCTURE_DEF_ID | int | FK to structure definition |
| RPT_FILE_SIZE_KB | int | Spool file size |
| MAP_FILE_SIZE_KB | int | MAP file size |

**Composite PK:** (DOMAIN_ID, REPORT_SPECIES_ID, AS_OF_TIMESTAMP)

### REPORT_SPECIES_NAME
Maps report names to species IDs.

| Column | Type | Description |
|--------|------|-------------|
| DOMAIN_ID | int | Domain identifier |
| REPORT_SPECIES_ID | int | Report type identifier |
| NAME | varchar | Report name (e.g., 'CDU100P') |

### SST_STORAGE
Links report instances to MAP files.

| Column | Type | Description |
|--------|------|-------------|
| DOMAIN_ID | int | Domain identifier |
| REPORT_SPECIES_ID | int | Report type identifier |
| AS_OF_TIMESTAMP | datetime | Timestamp |
| MAP_FILE_ID | int | FK to MAPFILE |

### MAPFILE
MAP file metadata.

| Column | Type | Description |
|--------|------|-------------|
| MAP_FILE_ID | int | Primary key |
| FILENAME | varchar | MAP file name (e.g., '25001002.MAP') |
| LOCATION_ID | int | Storage location |

### RPTFILE_INSTANCE
Links report instances to spool files.

| Column | Type | Description |
|--------|------|-------------|
| DOMAIN_ID | int | Domain identifier |
| REPORT_SPECIES_ID | int | Report type identifier |
| AS_OF_TIMESTAMP | datetime | Timestamp |
| RPT_FILE_ID | int | FK to RPTFILE |

### RPTFILE
Spool file metadata.

| Column | Type | Description |
|--------|------|-------------|
| RPT_FILE_ID | int | Primary key |
| FILENAME | varchar | Spool file name |
| LOCATION_ID | int | Storage location |

### REPORT_INSTANCE_SEGMENT
Ingestion arrival chunks (concatenation segments from spool arrivals) per report instance.
**Note:** This table does NOT define section segregation. Section segregation comes from RPT file SECTIONHDR.

| Column | Type | Description |
|--------|------|-------------|
| DOMAIN_ID | int | Domain identifier |
| REPORT_SPECIES_ID | int | Report type identifier |
| AS_OF_TIMESTAMP | datetime | Timestamp |
| SEGMENT_NUMBER | int | Sequential arrival chunk index (0, 1, 2...) |
| START_PAGE_NUMBER | int | First page of this arrival chunk in concatenated spool |
| NUMBER_OF_PAGES | int | Page count in this arrival chunk |

### LINE
Line definitions for report structure.

| Column | Type | Description |
|--------|------|-------------|
| STRUCTURE_DEF_ID | int | Structure identifier |
| LINE_ID | int | Line identifier |
| NAME | varchar | Line name |
| TEMPLATE | varchar | Pattern template (A=alpha, 9=digit) |

### FIELD
Field definitions within lines.

| Column | Type | Description |
|--------|------|-------------|
| STRUCTURE_DEF_ID | int | Structure identifier |
| LINE_ID | int | Line identifier |
| FIELD_ID | int | Field identifier |
| NAME | varchar | Field name (e.g., 'ACCOUNT_NO') |
| START_COLUMN | int | Starting column (0-indexed) |
| END_COLUMN | int | Ending column |
| IS_INDEXED | bit | 1 = searchable via MAP index |
| IS_SIGNIFICANT | bit | 1 = section boundary field |

### SECTION
Section definitions (branches) for a report type.

| Column | Type | Description |
|--------|------|-------------|
| DOMAIN_ID | int | Domain identifier |
| REPORT_SPECIES_ID | int | Report type identifier |
| SECTION_ID | int | Section identifier |
| NAME | varchar | Section name (e.g., '501', 'UBF NY') |

### STYPE_SECTION
Section permissions (Windows ACLs).

| Column | Type | Description |
|--------|------|-------------|
| REPORT_SPECIES_ID | int | Report type identifier |
| SECTION_ID | int | Section identifier |
| VALUE | varbinary | Windows Security Descriptor |

---

## Common Queries

### Get Report Instance by Name
```sql
SELECT ri.*
FROM REPORT_INSTANCE ri
JOIN REPORT_SPECIES_NAME rsn ON ri.DOMAIN_ID = rsn.DOMAIN_ID
    AND ri.REPORT_SPECIES_ID = rsn.REPORT_SPECIES_ID
WHERE rsn.NAME LIKE '%CDU100P%'
ORDER BY ri.AS_OF_TIMESTAMP DESC;
```

### Get MAP File for Instance
```sql
SELECT mf.FILENAME, mf.LOCATION_ID
FROM SST_STORAGE sst
JOIN MAPFILE mf ON sst.MAP_FILE_ID = mf.MAP_FILE_ID
WHERE sst.DOMAIN_ID = 1
  AND sst.REPORT_SPECIES_ID = @species_id
  AND sst.AS_OF_TIMESTAMP = @timestamp;
```

### Get Spool File for Instance
```sql
SELECT rf.FILENAME, rf.LOCATION_ID
FROM RPTFILE_INSTANCE rfi
JOIN RPTFILE rf ON rfi.RPT_FILE_ID = rf.RPT_FILE_ID
WHERE rfi.DOMAIN_ID = 1
  AND rfi.REPORT_SPECIES_ID = @species_id
  AND rfi.AS_OF_TIMESTAMP = @timestamp;
```

### Get Segments for Instance
```sql
SELECT SEGMENT_NUMBER, START_PAGE_NUMBER, NUMBER_OF_PAGES
FROM REPORT_INSTANCE_SEGMENT
WHERE DOMAIN_ID = 1
  AND REPORT_SPECIES_ID = @species_id
  AND AS_OF_TIMESTAMP = @timestamp
ORDER BY SEGMENT_NUMBER;
```

### Get Indexed Fields for Structure
```sql
SELECT f.LINE_ID, f.FIELD_ID, f.NAME, f.START_COLUMN, f.END_COLUMN
FROM FIELD f
WHERE f.STRUCTURE_DEF_ID = @structure_def_id
  AND f.IS_INDEXED = 1
ORDER BY f.LINE_ID, f.FIELD_ID;
```

### Get Significant Fields (Section Boundaries)
```sql
SELECT f.LINE_ID, f.FIELD_ID, f.NAME, f.START_COLUMN, f.END_COLUMN
FROM FIELD f
WHERE f.STRUCTURE_DEF_ID = @structure_def_id
  AND f.IS_SIGNIFICANT = 1
ORDER BY f.LINE_ID, f.FIELD_ID;
```

### Get Line Templates
```sql
SELECT LINE_ID, NAME, TEMPLATE
FROM LINE
WHERE STRUCTURE_DEF_ID = @structure_def_id
ORDER BY LINE_ID;
```

### Get Sections with Permissions
```sql
SELECT s.SECTION_ID, s.NAME, ss.VALUE as ACL
FROM SECTION s
LEFT JOIN STYPE_SECTION ss ON s.REPORT_SPECIES_ID = ss.REPORT_SPECIES_ID
    AND s.SECTION_ID = ss.SECTION_ID
WHERE s.DOMAIN_ID = 1
  AND s.REPORT_SPECIES_ID = @species_id
ORDER BY s.SECTION_ID;
```

### Find All January 2025 Instances
```sql
SELECT ri.REPORT_SPECIES_ID, rsn.NAME, ri.AS_OF_TIMESTAMP,
       ri.STRUCTURE_DEF_ID, ri.RPT_FILE_SIZE_KB, ri.MAP_FILE_SIZE_KB
FROM REPORT_INSTANCE ri
JOIN REPORT_SPECIES_NAME rsn ON ri.DOMAIN_ID = rsn.DOMAIN_ID
    AND ri.REPORT_SPECIES_ID = rsn.REPORT_SPECIES_ID
WHERE ri.DOMAIN_ID = 1
  AND ri.AS_OF_TIMESTAMP >= '2025-01-01'
  AND ri.AS_OF_TIMESTAMP < '2025-02-01'
ORDER BY ri.AS_OF_TIMESTAMP;
```

### Count MAP Files by Date
```sql
SELECT CAST(AS_OF_TIMESTAMP AS DATE) as report_date, COUNT(*) as count
FROM REPORT_INSTANCE
WHERE DOMAIN_ID = 1
GROUP BY CAST(AS_OF_TIMESTAMP AS DATE)
ORDER BY report_date DESC;
```

---

## Schema Relationships

```
REPORT_INSTANCE
    ├── STRUCTURE_DEF_ID ──► LINE ──► FIELD
    │                              (IS_INDEXED, IS_SIGNIFICANT)
    │
    ├── SST_STORAGE ──► MAPFILE (binary index)
    │
    ├── RPTFILE_INSTANCE ──► RPTFILE (spool file)
    │
    └── REPORT_INSTANCE_SEGMENT (ingestion arrival chunks)

REPORT_SPECIES_NAME ──► REPORT_SPECIES_ID

SECTION ──► STYPE_SECTION (permissions)
```

---

## Field Flags Explained

### IS_INDEXED = 1
- Field values are extracted and stored in MAP file index
- Used for searching (e.g., find all pages with ACCOUNT_NO = 'xxx')
- **No permission check** - direct data lookup

### IS_SIGNIFICANT = 1
- Field defines section boundaries (typically BRANCH)
- Used for section segregation and permission control
- Values stored in SECTION table
- Permissions in STYPE_SECTION.VALUE (Windows ACL)

### Combined Flags
- A field can have both flags (indexed AND significant)
- Multiple IS_SIGNIFICANT fields create compound section names (e.g., "501 49")

---

## File Locations

| Type | Location |
|------|----------|
| MAP Files | `/Volumes/X9Pro/OCBC/250_MapFiles/` |
| Sample Spool Files | `Report_TXT_Viewer/` |

---

## Python Integration

See `intellistor_viewer.py` for complete implementation:

```python
from intellistor_viewer import DatabaseAccess, Config

config = Config()
db = DatabaseAccess(config)
db.connect()

# Get report species ID
species_id = db.get_report_species_id_by_name('CDU100P')

# Get latest instance
instance = db.get_report_instance(species_id)

# Get MAP filename
map_file = db.get_map_filename(instance)

# Get indexed fields
fields = db.get_field_definitions(instance.structure_def_id, indexed_only=True)

db.close()
```
