# IntelliSTOR Signature Field Mapping Reference

## Overview

This document explains how IntelliSTOR defines which fields are used for report instances through the signature and field mapping system. This knowledge is critical for building a replacement ingestion routine that mimics IntelliSTOR's behavior.

**Key Concept**: The `SENSITIVITY` field in the `SENSITIVE_FIELD` table encodes the **role** of each field, determining whether it's used for the report name, report date, sections, or page numbers.

---

## Database Tables Involved

### 1. SIGNATURE Table
Master configuration table linking report species to field mappings.

| Column | Type | Description |
|--------|------|-------------|
| SIGN_ID | int | Primary key - signature identifier |
| DOMAIN_ID | int | Domain identifier (typically 1) |
| REPORT_SPECIES_ID | int | Which report type uses this signature |
| REPORT_DATE_TYPE | int | How report date is determined (see below) |
| POSITION | int | Position indicator |
| MATCHING | int | Matching criteria |
| LBD_OFFSETS | int | Last Business Day offset values |
| DESCRIPTION | char(50) | Optional description |

**REPORT_DATE_TYPE Values:**
- `0` = **Today** - Use current date
- `1` = **Last Business Day** - Calculate last business day
- `2` = **From Field** - Extract date from report content (uses SENSITIVE_FIELD with SENSITIVITY=2)

### 2. SENSITIVE_FIELD Table
Maps SIGN_ID to specific field coordinates and roles.

| Column | Type | Description |
|--------|------|-------------|
| SIGN_ID | int | FK to SIGNATURE table |
| LINE_ID | int | Line identifier in report structure |
| FIELD_ID | int | Field identifier within line |
| LINE_OF_OCCURENCE | int | Which occurrence of the line pattern |
| SENSITIVITY | int | **Field role code** (see below) |
| MINOR_VERSION | int | Version number |
| NAME | char | Field name (typically empty, join to FIELD for name) |

**SENSITIVITY Values (Field Role Codes):**
- `0` = Other sensitive/security fields
- `1` = **Report Name/ID field** (e.g., RptID001, ID001)
- `2` = **Report Date field** (e.g., RptDate001, RunDate001) - only used when REPORT_DATE_TYPE=2
- `3` = **Page Number field** (not commonly used in practice)
- `4` = **Section/Segment fields** (e.g., BrCode001, Seg01, SegCode)
- `65538` = Special/extended sensitivity (rare)

### 3. FIELD Table
Defines actual field properties in report structures.

| Column | Type | Description |
|--------|------|-------------|
| STRUCTURE_DEF_ID | int | Report structure identifier |
| LINE_ID | int | Line identifier |
| FIELD_ID | int | Field identifier |
| NAME | char | Field name (e.g., "BrCode001", "RptID001") |
| IS_SIGNIFICANT | bit | 1 = Potential section boundary field |
| IS_INDEXED | bit | 1 = Searchable via MAP index |
| START_COLUMN | int | Starting column (0-indexed) |
| END_COLUMN | int | Ending column |
| FIELD_TYPE_NAME | char | Field type |

---

## Field Role Mappings

### 1. Section Variables (e.g., BrCode001, Seg01)

**Purpose**: Define section boundaries for report segmentation and access control.

**How to find them:**
```sql
-- Get section fields for a report species
SELECT
    sf.LINE_ID,
    sf.FIELD_ID,
    f.NAME as FIELD_NAME,
    f.START_COLUMN,
    f.END_COLUMN
FROM SIGNATURE sig
JOIN SENSITIVE_FIELD sf ON sig.SIGN_ID = sf.SIGN_ID
JOIN FIELD f ON sf.LINE_ID = f.LINE_ID
             AND sf.FIELD_ID = f.FIELD_ID
             AND f.STRUCTURE_DEF_ID = (
                 SELECT STRUCTURE_DEF_ID
                 FROM REPORT_INSTANCE
                 WHERE REPORT_SPECIES_ID = sig.REPORT_SPECIES_ID
                 LIMIT 1
             )
WHERE sig.REPORT_SPECIES_ID = @species_id
  AND sf.SENSITIVITY = 4  -- Section fields
  AND f.IS_SIGNIFICANT = 1
ORDER BY sf.LINE_ID, sf.FIELD_ID  -- This defines the order!
```

**Ordering**: Multiple section fields are ordered by:
1. `LINE_ID` (ascending) - which line in the report
2. `FIELD_ID` (ascending) - which field within the line

This creates a natural left-to-right, top-to-bottom ordering as fields appear in the report.

**Example**:
- First section field: `BrCode001` (LINE_ID=1, FIELD_ID=5)
- Second section field: `Seg01` (LINE_ID=1, FIELD_ID=6)

**Where extracted values go**: `SECTION.NAME` table
- Compound section names created by concatenating field values
- Example: BrCode="501", Seg="49" → SECTION.NAME = "501 49"

### 2. Report Name Variable (e.g., RptID001)

**Purpose**: Identifies which field contains the report identifier.

**How to find it:**
```sql
-- Get report name field for a report species
SELECT
    sf.LINE_ID,
    sf.FIELD_ID,
    f.NAME as FIELD_NAME,
    f.START_COLUMN,
    f.END_COLUMN
FROM SIGNATURE sig
JOIN SENSITIVE_FIELD sf ON sig.SIGN_ID = sf.SIGN_ID
JOIN FIELD f ON sf.LINE_ID = f.LINE_ID
             AND sf.FIELD_ID = f.FIELD_ID
             AND f.STRUCTURE_DEF_ID = (
                 SELECT STRUCTURE_DEF_ID
                 FROM REPORT_INSTANCE
                 WHERE REPORT_SPECIES_ID = sig.REPORT_SPECIES_ID
                 LIMIT 1
             )
WHERE sig.REPORT_SPECIES_ID = @species_id
  AND sf.SENSITIVITY = 1  -- Report Name field
```

**Typical field names**: RptID001, ID001, AMD002, OCGLTDRN

**Where extracted value goes**: `REPORT_SPECIES_NAME.NAME` table

### 3. Report Date Variable (e.g., RptDate001)

**Purpose**: Determines the "as of" date for the report instance.

**Three methods** (determined by `SIGNATURE.REPORT_DATE_TYPE`):

#### Method 1: Today (`REPORT_DATE_TYPE = 0`)
Use current system date when the report is processed.

```sql
-- No field lookup needed
AS_OF_TIMESTAMP = CURRENT_TIMESTAMP
```

#### Method 2: Last Business Day (`REPORT_DATE_TYPE = 1`)
Calculate the last business day based on system date and `LBD_OFFSETS`.

```sql
-- Apply business day calculation
AS_OF_TIMESTAMP = calculate_last_business_day(CURRENT_DATE, LBD_OFFSETS)
```

#### Method 3: From Field (`REPORT_DATE_TYPE = 2`)
Extract date from a specific field in the report content.

```sql
-- Get report date field
SELECT
    sf.LINE_ID,
    sf.FIELD_ID,
    f.NAME as FIELD_NAME,
    f.START_COLUMN,
    f.END_COLUMN
FROM SIGNATURE sig
JOIN SENSITIVE_FIELD sf ON sig.SIGN_ID = sf.SIGN_ID
JOIN FIELD f ON sf.LINE_ID = f.LINE_ID
             AND sf.FIELD_ID = f.FIELD_ID
             AND f.STRUCTURE_DEF_ID = (
                 SELECT STRUCTURE_DEF_ID
                 FROM REPORT_INSTANCE
                 WHERE REPORT_SPECIES_ID = sig.REPORT_SPECIES_ID
                 LIMIT 1
             )
WHERE sig.REPORT_SPECIES_ID = @species_id
  AND sf.SENSITIVITY = 2  -- Report Date field
```

**Typical field names**: RptDate001, RunDate001, PrtDate001

**Where extracted/calculated value goes**: `REPORT_INSTANCE.AS_OF_TIMESTAMP`

### 4. Page Number Field (SENSITIVITY = 3)

**Purpose**: Identifies which field contains page numbers (not commonly used in practice).

**Note**: This role exists in the system but is rarely implemented. Most reports handle pagination through other mechanisms.

---

## Complete Relationship Chain

```
┌─────────────────────────────────────────────────────────────────┐
│ SIGNATURE                                                       │
│ ├─ SIGN_ID (PK)                                                 │
│ ├─ REPORT_SPECIES_ID (which report type)                        │
│ ├─ REPORT_DATE_TYPE (0=Today, 1=LBD, 2=FromField)              │
│ └─ LBD_OFFSETS (for Last Business Day calculation)             │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│ SENSITIVE_FIELD (field role mappings)                          │
│ ├─ SIGN_ID → SIGNATURE.SIGN_ID                                  │
│ ├─ SENSITIVITY (1=Name, 2=Date, 4=Section)                     │
│ ├─ LINE_ID, FIELD_ID (field coordinates)                       │
│ └─ LINE_OF_OCCURENCE                                            │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│ FIELD (actual field definitions)                               │
│ ├─ STRUCTURE_DEF_ID (report structure)                          │
│ ├─ LINE_ID, FIELD_ID (coordinates)                             │
│ ├─ NAME (field name: "BrCode001", "RptID001", etc.)           │
│ ├─ IS_SIGNIFICANT (1 = potential section field)                │
│ ├─ START_COLUMN, END_COLUMN (position in line)                 │
│ └─ FIELD_TYPE_NAME (data type)                                 │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
              Extracted Values:
              ├─ SECTION.NAME (section values)
              ├─ REPORT_SPECIES_NAME.NAME (report name)
              └─ REPORT_INSTANCE.AS_OF_TIMESTAMP (report date)
```

---

## Implementation Guide for New Ingestion Routine

### Step 1: Load Signature Configuration

For each report to be ingested:

```python
# Get signature configuration
signature = query_signature(report_species_id)
# Returns: {
#   sign_id: 1,
#   report_date_type: 2,  # From Field
#   lbd_offsets: 0,
#   structure_def_id: 0
# }
```

### Step 2: Determine Report Date Strategy

```python
if signature.report_date_type == 0:
    report_date = datetime.now()
elif signature.report_date_type == 1:
    report_date = calculate_last_business_day(signature.lbd_offsets)
elif signature.report_date_type == 2:
    # Extract from field - need to find the field
    date_field = query_sensitive_field(
        sign_id=signature.sign_id,
        sensitivity=2  # Report Date
    )
    report_date = extract_field_value(
        report_content,
        date_field.line_id,
        date_field.field_id,
        date_field.start_column,
        date_field.end_column
    )
```

### Step 3: Extract Report Name

```python
# Get report name field
name_field = query_sensitive_field(
    sign_id=signature.sign_id,
    sensitivity=1  # Report Name
)

report_name = extract_field_value(
    report_content,
    name_field.line_id,
    name_field.field_id,
    name_field.start_column,
    name_field.end_column
)
```

### Step 4: Extract Section Fields (Ordered)

```python
# Get section fields in correct order
section_fields = query_sensitive_fields_ordered(
    sign_id=signature.sign_id,
    sensitivity=4,  # Section fields
    order_by=['line_id', 'field_id']  # CRITICAL: Maintains order
)

# Extract values in order
section_values = []
for field in section_fields:
    value = extract_field_value(
        report_content,
        field.line_id,
        field.field_id,
        field.start_column,
        field.end_column
    )
    section_values.append(value)

# Create compound section name
section_name = ' '.join(section_values)  # e.g., "501 49"
```

### Step 5: Create Report Instance

```python
# Create report instance record
report_instance = {
    'domain_id': 1,
    'report_species_id': report_species_id,
    'as_of_timestamp': report_date,
    'structure_def_id': signature.structure_def_id,
    # ... other metadata
}

# Create section records
for section_value in unique_section_values:
    section = {
        'domain_id': 1,
        'report_species_id': report_species_id,
        'section_id': get_or_create_section_id(section_value),
        'name': section_value
    }
```

---

## SQL Query Templates

### Get Complete Signature Configuration

```sql
SELECT
    sig.SIGN_ID,
    sig.REPORT_SPECIES_ID,
    sig.REPORT_DATE_TYPE,
    sig.LBD_OFFSETS,
    sig.POSITION,
    sig.MATCHING,
    ri.STRUCTURE_DEF_ID
FROM SIGNATURE sig
LEFT JOIN (
    SELECT REPORT_SPECIES_ID, STRUCTURE_DEF_ID
    FROM REPORT_INSTANCE
    WHERE REPORT_SPECIES_ID = @species_id
    LIMIT 1
) ri ON sig.REPORT_SPECIES_ID = ri.REPORT_SPECIES_ID
WHERE sig.DOMAIN_ID = @domain_id
  AND sig.REPORT_SPECIES_ID = @species_id
```

### Get Field Mappings by Role

```sql
-- Universal query for any field role
SELECT
    sf.SENSITIVITY as ROLE,  -- 1=Name, 2=Date, 4=Section
    sf.LINE_ID,
    sf.FIELD_ID,
    sf.LINE_OF_OCCURENCE,
    f.NAME as FIELD_NAME,
    f.START_COLUMN,
    f.END_COLUMN,
    f.IS_SIGNIFICANT,
    f.FIELD_TYPE_NAME
FROM SIGNATURE sig
JOIN SENSITIVE_FIELD sf ON sig.SIGN_ID = sf.SIGN_ID
LEFT JOIN FIELD f ON sf.LINE_ID = f.LINE_ID
                  AND sf.FIELD_ID = f.FIELD_ID
                  AND f.STRUCTURE_DEF_ID = @structure_def_id
WHERE sig.SIGN_ID = @sign_id
  AND sf.SENSITIVITY = @role  -- 1, 2, or 4
ORDER BY sf.LINE_ID, sf.FIELD_ID
```

---

## Important Notes for Migration

### 1. Multiple STRUCTURE_DEF_ID per SIGN_ID
- A single `SIGN_ID` can be associated with multiple `REPORT_SPECIES_ID` values
- Each report species may use different `STRUCTURE_DEF_ID` values
- Always join to `REPORT_INSTANCE` to get the correct `STRUCTURE_DEF_ID` for field lookups

### 2. Order Matters for Section Fields
- **CRITICAL**: Section fields MUST be processed in `(LINE_ID, FIELD_ID)` order
- This order determines how compound section names are built
- Changing the order breaks section matching and access control

### 3. Field Names Are Not Reliable
- `SENSITIVE_FIELD.NAME` is typically empty
- Always join to `FIELD` table using `(LINE_ID, FIELD_ID, STRUCTURE_DEF_ID)` to get field names
- Field names can vary across different `STRUCTURE_DEF_ID` values even with same `(LINE_ID, FIELD_ID)`

### 4. IS_SIGNIFICANT Flag
- `FIELD.IS_SIGNIFICANT = 1` marks potential section boundary fields
- However, only fields referenced in `SENSITIVE_FIELD` with `SENSITIVITY = 4` are actually used
- Not all `IS_SIGNIFICANT = 1` fields are active section fields

### 5. SENSITIVITY as Role Identifier
- The `SENSITIVITY` field is the **definitive** indicator of field role
- Do not rely on field names alone (e.g., presence of "Date" in name)
- Use `SENSITIVITY` to filter fields by role

---

## Testing Recommendations

### 1. Verify Section Order
Test that section fields are extracted in the correct order:
```python
# Expected: ["BrCode001", "Seg01"]
# NOT: ["Seg01", "BrCode001"]
assert section_field_order == get_expected_order(report_species_id)
```

### 2. Validate Date Extraction
For each `REPORT_DATE_TYPE`:
- Type 0: Verify current date is used
- Type 1: Test Last Business Day calculation with various offsets
- Type 2: Verify correct field extraction and date parsing

### 3. Check Section Value Extraction
Ensure section values match existing `SECTION.NAME` entries:
```python
expected_sections = get_existing_sections(report_species_id)
extracted_sections = extract_sections(report_content)
assert set(extracted_sections) == set(expected_sections)
```

### 4. Report Name Consistency
Verify extracted report names match existing `REPORT_SPECIES_NAME.NAME` values:
```python
expected_name = get_report_name(report_species_id)
extracted_name = extract_report_name(report_content)
assert extracted_name == expected_name
```

---

## Additional Resources

- **Database Schema**: See `DATABASE_REFERENCE.md` for complete table definitions
- **Section Workflow**: See `SECTION_SEGMENT_WORKFLOW.md` for section segregation algorithm
- **Field Extraction**: Reference existing `intellistor_viewer.py` for field extraction patterns

---

## Document Metadata

- **Created**: 2025-02-04
- **Purpose**: IntelliSTOR Replacement - Field Mapping Reference
- **Status**: Based on live database analysis
- **Verified**: SENSITIVITY field roles confirmed through database queries

