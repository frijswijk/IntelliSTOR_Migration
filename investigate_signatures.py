#!/usr/bin/env python3
"""Investigate signature tables and their relationships"""

import pymssql

# Connect to database
conn = pymssql.connect(
    server='localhost',
    port=1433,
    user='sa',
    password='Fvrpgr40',
    database='iSTSGUAT'
)

cursor = conn.cursor(as_dict=True)

print("=" * 80)
print("SIGNATURE TABLES INVESTIGATION")
print("=" * 80)

# Find all tables with 'SIGN' in the name
print("\n1. Tables with 'SIGN' in the name:")
print("-" * 80)
cursor.execute("""
    SELECT TABLE_NAME
    FROM INFORMATION_SCHEMA.TABLES
    WHERE TABLE_TYPE = 'BASE TABLE'
      AND TABLE_NAME LIKE '%SIGN%'
    ORDER BY TABLE_NAME
""")
sign_tables = cursor.fetchall()
for table in sign_tables:
    print(f"  - {table['TABLE_NAME']}")

# Get structure of key signature tables
signature_tables = ['SIGNATURE', 'SIGN_GEN_INFO', 'SENSITIVE_FIELD', 'LINE']

for table_name in signature_tables:
    print(f"\n2. Structure of {table_name}:")
    print("-" * 80)

    # Check if table exists
    cursor.execute(f"""
        SELECT COUNT(*) as cnt
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_NAME = '{table_name}'
    """)
    if cursor.fetchone()['cnt'] == 0:
        print(f"  ⚠ Table {table_name} does not exist")
        continue

    # Get columns
    cursor.execute(f"""
        SELECT
            COLUMN_NAME,
            DATA_TYPE,
            CHARACTER_MAXIMUM_LENGTH,
            IS_NULLABLE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = '{table_name}'
        ORDER BY ORDINAL_POSITION
    """)
    columns = cursor.fetchall()

    for col in columns:
        nullable = "NULL" if col['IS_NULLABLE'] == 'YES' else "NOT NULL"
        length = f"({col['CHARACTER_MAXIMUM_LENGTH']})" if col['CHARACTER_MAXIMUM_LENGTH'] else ""
        print(f"  {col['COLUMN_NAME']:30s} {col['DATA_TYPE']}{length:15s} {nullable}")

    # Get row count
    cursor.execute(f"SELECT COUNT(*) as cnt FROM {table_name}")
    count = cursor.fetchone()['cnt']
    print(f"\n  Total rows: {count:,}")

# Check for foreign key relationships
print("\n3. Foreign Key Relationships:")
print("-" * 80)
for table_name in signature_tables:
    cursor.execute(f"""
        SELECT COUNT(*) as cnt
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_NAME = '{table_name}'
    """)
    if cursor.fetchone()['cnt'] == 0:
        continue

    cursor.execute(f"""
        SELECT
            fk.name AS FK_NAME,
            OBJECT_NAME(fk.parent_object_id) AS TABLE_NAME,
            COL_NAME(fc.parent_object_id, fc.parent_column_id) AS COLUMN_NAME,
            OBJECT_NAME(fk.referenced_object_id) AS REFERENCED_TABLE,
            COL_NAME(fc.referenced_object_id, fc.referenced_column_id) AS REFERENCED_COLUMN
        FROM sys.foreign_keys AS fk
        INNER JOIN sys.foreign_key_columns AS fc
            ON fk.object_id = fc.constraint_object_id
        WHERE OBJECT_NAME(fk.parent_object_id) = '{table_name}'
           OR OBJECT_NAME(fk.referenced_object_id) = '{table_name}'
        ORDER BY TABLE_NAME, FK_NAME
    """)
    relationships = cursor.fetchall()

    if relationships:
        print(f"\n{table_name}:")
        for rel in relationships:
            print(f"  {rel['TABLE_NAME']}.{rel['COLUMN_NAME']} -> {rel['REFERENCED_TABLE']}.{rel['REFERENCED_COLUMN']}")

# Sample some SIGNATURE records to understand versioning
print("\n4. Sample SIGNATURE Records (to understand versioning):")
print("-" * 80)
cursor.execute("""
    SELECT COUNT(*) as cnt FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'SIGNATURE'
""")
if cursor.fetchone()['cnt'] > 0:
    cursor.execute("""
        SELECT TOP 20
            DOMAIN_ID,
            REPORT_SPECIES_ID,
            SIGN_ID,
            MINOR_VERSION,
            LAST_MODIFIED_DATE_TIME
        FROM SIGNATURE
        ORDER BY DOMAIN_ID, REPORT_SPECIES_ID, MINOR_VERSION DESC
    """)
    sigs = cursor.fetchall()

    if sigs:
        print(f"\n{'Domain':>8} | {'Species':>8} | {'Sign ID':>8} | {'MinVer':>8} | {'Modified On':20}")
        print("-" * 80)
        for sig in sigs:
            print(f"{sig['DOMAIN_ID']:8d} | {sig['REPORT_SPECIES_ID']:8d} | {sig['SIGN_ID']:8d} | "
                  f"{sig['MINOR_VERSION']:8d} | {str(sig['LAST_MODIFIED_DATE_TIME']):20s}")

    # Check how many versions exist per species
    print("\n5. Version counts per report species:")
    print("-" * 80)
    cursor.execute("""
        SELECT
            DOMAIN_ID,
            REPORT_SPECIES_ID,
            COUNT(*) as VERSION_COUNT,
            MAX(MINOR_VERSION) as MAX_VERSION,
            MIN(MINOR_VERSION) as MIN_VERSION
        FROM SIGNATURE
        GROUP BY DOMAIN_ID, REPORT_SPECIES_ID
        HAVING COUNT(*) > 1
        ORDER BY VERSION_COUNT DESC
    """)
    version_counts = cursor.fetchall()

    print(f"\n{'Domain':>8} | {'Species':>8} | {'Versions':>10} | {'Min Ver':>8} | {'Max Ver':>8}")
    print("-" * 80)

    total_species_with_versions = 0
    total_old_versions = 0

    for vc in version_counts[:20]:  # Show first 20
        print(f"{vc['DOMAIN_ID']:8d} | {vc['REPORT_SPECIES_ID']:8d} | {vc['VERSION_COUNT']:10d} | "
              f"{vc['MIN_VERSION']:8d} | {vc['MAX_VERSION']:8d}")
        total_species_with_versions += 1
        total_old_versions += (vc['VERSION_COUNT'] - 1)  # All except latest

    # Get totals
    cursor.execute("""
        SELECT
            COUNT(*) as total_signatures
        FROM SIGNATURE
    """)
    totals = cursor.fetchone()

    cursor.execute("""
        SELECT COUNT(*) as total_species
        FROM (
            SELECT DISTINCT DOMAIN_ID, REPORT_SPECIES_ID
            FROM SIGNATURE
        ) as t
    """)
    species_count = cursor.fetchone()['total_species']

    cursor.execute("""
        SELECT COUNT(*) as species_with_multiple_versions
        FROM (
            SELECT DOMAIN_ID, REPORT_SPECIES_ID
            FROM SIGNATURE
            GROUP BY DOMAIN_ID, REPORT_SPECIES_ID
            HAVING COUNT(*) > 1
        ) as t
    """)
    multi_version_count = cursor.fetchone()['species_with_multiple_versions']

    print("\n" + "=" * 80)
    print("SUMMARY:")
    print("=" * 80)
    print(f"Total report species with signatures: {species_count:,}")
    print(f"Total signature records: {totals['total_signatures']:,}")
    print(f"Species with multiple versions: {multi_version_count:,}")

    # Estimate how many old versions exist
    cursor.execute("""
        SELECT COUNT(*) as old_versions
        FROM SIGNATURE s1
        WHERE EXISTS (
            SELECT 1 FROM SIGNATURE s2
            WHERE s2.DOMAIN_ID = s1.DOMAIN_ID
              AND s2.REPORT_SPECIES_ID = s1.REPORT_SPECIES_ID
              AND s2.MINOR_VERSION > s1.MINOR_VERSION
        )
    """)
    old_versions = cursor.fetchone()['old_versions']
    print(f"Old signature versions (not latest): {old_versions:,}")
    print(f"Potential space savings if keeping only latest: {old_versions:,} records")

cursor.close()
conn.close()
