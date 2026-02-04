#!/usr/bin/env python3
"""Verify signature relationships before cleanup"""

import pymssql

conn = pymssql.connect(
    server='localhost',
    port=1433,
    user='sa',
    password='Fvrpgr40',
    database='iSTSGUAT'
)

cursor = conn.cursor(as_dict=True)

print("=" * 80)
print("SIGNATURE RELATIONSHIP VERIFICATION")
print("=" * 80)

# 1. Check LINES_IN_SIGN structure
print("\n1. LINES_IN_SIGN Table Structure:")
print("-" * 80)
cursor.execute("""
    SELECT
        COLUMN_NAME,
        DATA_TYPE,
        IS_NULLABLE
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'LINES_IN_SIGN'
    ORDER BY ORDINAL_POSITION
""")
lines_in_sign_cols = cursor.fetchall()

for col in lines_in_sign_cols:
    nullable = "NULL" if col['IS_NULLABLE'] == 'YES' else "NOT NULL"
    print(f"  {col['COLUMN_NAME']:30s} {col['DATA_TYPE']:15s} {nullable}")

# Get row count
cursor.execute("SELECT COUNT(*) as cnt FROM LINES_IN_SIGN")
print(f"\n  Total rows: {cursor.fetchone()['cnt']:,}")

# 2. Check if LINES_IN_SIGN links to SIGN_ID + MINOR_VERSION
print("\n2. Sample LINES_IN_SIGN records:")
print("-" * 80)
cursor.execute("""
    SELECT TOP 10 *
    FROM LINES_IN_SIGN
""")
sample = cursor.fetchall()
if sample:
    # Show first record's keys
    keys = list(sample[0].keys())
    print(f"  Columns: {', '.join(keys)}")
    for idx, rec in enumerate(sample[:5], 1):
        print(f"\n  Record {idx}:")
        for k, v in rec.items():
            print(f"    {k}: {v}")

# 3. Check if REPORT_INSTANCE references signatures
print("\n3. Checking REPORT_INSTANCE for signature references:")
print("-" * 80)
cursor.execute("""
    SELECT
        COLUMN_NAME,
        DATA_TYPE
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'REPORT_INSTANCE'
      AND (COLUMN_NAME LIKE '%SIGN%' OR COLUMN_NAME LIKE '%VERSION%')
    ORDER BY ORDINAL_POSITION
""")
ri_sign_cols = cursor.fetchall()

if ri_sign_cols:
    print("  Columns with 'SIGN' or 'VERSION' in name:")
    for col in ri_sign_cols:
        print(f"    {col['COLUMN_NAME']:30s} {col['DATA_TYPE']}")
else:
    print("  ✓ No SIGN or VERSION columns found in REPORT_INSTANCE")
    print("  → Report instances do NOT link to specific signature versions")

# 4. Check STRUCTURE_DEF table for signature links
print("\n4. Checking STRUCTURE_DEF for signature references:")
print("-" * 80)
cursor.execute("""
    SELECT
        COLUMN_NAME,
        DATA_TYPE
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'STRUCTURE_DEF'
      AND COLUMN_NAME LIKE '%SIGN%'
    ORDER BY ORDINAL_POSITION
""")
sd_sign_cols = cursor.fetchall()

if sd_sign_cols:
    print("  Columns with 'SIGN' in name:")
    for col in sd_sign_cols:
        print(f"    {col['COLUMN_NAME']:30s} {col['DATA_TYPE']}")
else:
    print("  ✓ No SIGN columns found in STRUCTURE_DEF")

# 5. Check which tables reference SIGNATURE
print("\n5. All tables with foreign keys to SIGNATURE:")
print("-" * 80)
cursor.execute("""
    SELECT
        OBJECT_NAME(fk.parent_object_id) AS TABLE_NAME,
        fk.name AS FK_NAME,
        COL_NAME(fc.parent_object_id, fc.parent_column_id) AS COLUMN_NAME,
        COL_NAME(fc.referenced_object_id, fc.referenced_column_id) AS REFERENCED_COLUMN
    FROM sys.foreign_keys AS fk
    INNER JOIN sys.foreign_key_columns AS fc
        ON fk.object_id = fc.constraint_object_id
    WHERE OBJECT_NAME(fk.referenced_object_id) = 'SIGNATURE'
    ORDER BY TABLE_NAME
""")
fk_to_signature = cursor.fetchall()

if fk_to_signature:
    for fk in fk_to_signature:
        print(f"  {fk['TABLE_NAME']}.{fk['COLUMN_NAME']} -> SIGNATURE.{fk['REFERENCED_COLUMN']}")
else:
    print("  ⚠ No explicit foreign keys found to SIGNATURE")
    print("  (This doesn't mean there are no relationships, they may not be enforced)")

# 6. Manual check - do child tables have matching columns?
print("\n6. Checking for implicit relationships (matching column names):")
print("-" * 80)

child_tables = ['SENSITIVE_FIELD', 'LINES_IN_SIGN', 'SIGN_GEN_INFO']

for table in child_tables:
    cursor.execute(f"""
        SELECT COUNT(*) as cnt
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = '{table}'
          AND COLUMN_NAME IN ('SIGN_ID', 'MINOR_VERSION')
    """)
    match_count = cursor.fetchone()['cnt']

    if match_count == 2:
        print(f"  ✓ {table} has both SIGN_ID and MINOR_VERSION")

        # Count records
        cursor.execute(f"SELECT COUNT(*) as cnt FROM {table}")
        row_count = cursor.fetchone()['cnt']

        # Check if all records match existing signatures
        cursor.execute(f"""
            SELECT COUNT(*) as orphan_count
            FROM {table} t
            WHERE NOT EXISTS (
                SELECT 1 FROM SIGNATURE s
                WHERE s.SIGN_ID = t.SIGN_ID
                  AND s.MINOR_VERSION = t.MINOR_VERSION
            )
        """)
        orphan_count = cursor.fetchone()['orphan_count']

        print(f"    Total records: {row_count:,}")
        print(f"    Orphaned records (no matching signature): {orphan_count:,}")

    elif match_count == 1:
        print(f"  ~ {table} has partial match (only SIGN_ID or MINOR_VERSION)")
    else:
        print(f"  ✗ {table} does NOT have SIGN_ID or MINOR_VERSION")

print("\n" + "=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)

cursor.close()
conn.close()
