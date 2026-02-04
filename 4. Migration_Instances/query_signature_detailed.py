#!/usr/bin/env python3
"""
Detailed query to understand signature field mappings.
Focus on finding where section variables, report name, and report date are stored.
"""

import pymssql
import sys

SERVER = 'localhost'
PORT = 1433
DATABASE = 'iSTSGUAT'
USER = 'sa'
PASSWORD = 'Fvrpgr40'

def connect_db():
    print(f"Connecting to {SERVER}:{PORT}, database: {DATABASE}")
    try:
        conn = pymssql.connect(server=SERVER, port=PORT, database=DATABASE, user=USER, password=PASSWORD)
        print("✓ Connected!\n")
        return conn
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        sys.exit(1)

def query_signature_with_structure_fields(cursor, sign_id=1):
    """Join SIGNATURE -> SENSITIVE_FIELD -> FIELD to see actual field names."""

    print("="*100)
    print(f"SIGNATURE {sign_id}: Complete Field Mapping (SIGNATURE → SENSITIVE_FIELD → FIELD)")
    print("="*100)

    cursor.execute("""
        SELECT
            sig.SIGN_ID,
            sig.DOMAIN_ID,
            sig.REPORT_SPECIES_ID,
            sig.DESCRIPTION as SIG_DESC,
            sig.REPORT_DATE_TYPE,
            sf.LINE_ID,
            sf.FIELD_ID,
            sf.LINE_OF_OCCURENCE,
            sf.SENSITIVITY,
            f.STRUCTURE_DEF_ID,
            f.NAME as FIELD_NAME,
            f.IS_SIGNIFICANT,
            f.IS_INDEXED,
            f.START_COLUMN,
            f.END_COLUMN
        FROM SIGNATURE sig
        INNER JOIN SENSITIVE_FIELD sf ON sig.SIGN_ID = sf.SIGN_ID
        LEFT JOIN FIELD f ON sf.LINE_ID = f.LINE_ID
                          AND sf.FIELD_ID = f.FIELD_ID
        WHERE sig.SIGN_ID = %s
        ORDER BY sig.REPORT_SPECIES_ID, sf.LINE_ID, sf.FIELD_ID
    """, (sign_id,))

    rows = cursor.fetchall()
    print(f"\nFound {len(rows)} field mappings for SIGN_ID={sign_id}:\n")

    if len(rows) == 0:
        print("No results found. Try a different SIGN_ID.")
        return

    print(f"{'SPECIES_ID':<12} {'LINE_ID':<10} {'FIELD_ID':<10} {'FIELD_NAME':<30} {'IS_SIGNIF':<10} {'DATE_TYPE':<10} {'SENSITIVITY':<12}")
    print("-" * 100)

    for row in rows:
        species_id = row[2]
        line_id = row[5]
        field_id = row[6]
        field_name = str(row[10]).strip() if row[10] else "<NULL>"
        is_significant = row[11] if row[11] is not None else ""
        date_type = row[4]
        sensitivity = row[8]

        print(f"{species_id:<12} {line_id:<10} {field_id:<10} {field_name:<30} {is_significant:<10} {date_type:<10} {sensitivity:<12}")

def query_report_species_signatures(cursor):
    """Find which report species use which signatures."""

    print("\n" + "="*100)
    print("REPORT SPECIES → SIGNATURE Mapping")
    print("="*100)

    cursor.execute("""
        SELECT
            rsn.REPORT_SPECIES_ID,
            rsn.NAME as REPORT_NAME,
            s.SIGN_ID,
            s.DESCRIPTION as SIG_DESCRIPTION,
            s.REPORT_DATE_TYPE,
            COUNT(sf.FIELD_ID) as FIELD_COUNT
        FROM REPORT_SPECIES_NAME rsn
        INNER JOIN SIGNATURE s ON rsn.DOMAIN_ID = s.DOMAIN_ID
                               AND rsn.REPORT_SPECIES_ID = s.REPORT_SPECIES_ID
        LEFT JOIN SENSITIVE_FIELD sf ON s.SIGN_ID = sf.SIGN_ID
        WHERE rsn.REPORT_SPECIES_ID > 0
        GROUP BY rsn.REPORT_SPECIES_ID, rsn.NAME, s.SIGN_ID, s.DESCRIPTION, s.REPORT_DATE_TYPE
        ORDER BY rsn.REPORT_SPECIES_ID
    """)

    rows = cursor.fetchall()[:20]
    print(f"\nFound report species with signatures (first 20):\n")
    print(f"{'SPECIES_ID':<12} {'REPORT_NAME':<30} {'SIGN_ID':<10} {'DATE_TYPE':<12} {'FIELD_COUNT':<12}")
    print("-" * 90)

    for row in rows:
        report_name = str(row[1]).strip() if row[1] else ""
        print(f"{row[0]:<12} {report_name:<30} {row[2]:<10} {row[4]:<12} {row[5]:<12}")

def query_field_definitions_by_structure(cursor, structure_def_id=0):
    """Show all fields for a structure, focusing on significant and indexed fields."""

    print("\n" + "="*100)
    print(f"FIELD Definitions for STRUCTURE_DEF_ID={structure_def_id}")
    print("="*100)

    cursor.execute("""
        SELECT
            LINE_ID,
            FIELD_ID,
            NAME,
            IS_SIGNIFICANT,
            IS_INDEXED,
            START_COLUMN,
            END_COLUMN,
            FIELD_TYPE_NAME
        FROM FIELD
        WHERE STRUCTURE_DEF_ID = %s
          AND (IS_SIGNIFICANT = 1 OR NAME LIKE '%%RptID%%' OR NAME LIKE '%%Date%%' OR NAME LIKE '%%BrCode%%' OR NAME LIKE '%%Seg%%')
        ORDER BY LINE_ID, FIELD_ID
    """, (structure_def_id,))

    rows = cursor.fetchall()[:50]
    print(f"\nFound {len(rows)} relevant fields (first 50):\n")
    print(f"{'LINE_ID':<10} {'FIELD_ID':<10} {'NAME':<35} {'IS_SIGNIF':<12} {'IS_INDEXED':<12} {'START':<8} {'END':<8}")
    print("-" * 100)

    for row in rows:
        name = str(row[2]).strip() if row[2] else ""
        print(f"{row[0]:<10} {row[1]:<10} {name:<35} {row[3]:<12} {row[4]:<12} {row[5]:<8} {row[6]:<8}")

def query_all_signatures_summary(cursor):
    """Get summary of all signatures."""

    print("\n" + "="*100)
    print("All SIGNATURE Records Summary")
    print("="*100)

    cursor.execute("""
        SELECT
            SIGN_ID,
            COUNT(DISTINCT REPORT_SPECIES_ID) as SPECIES_COUNT,
            MIN(REPORT_SPECIES_ID) as MIN_SPECIES,
            MAX(REPORT_SPECIES_ID) as MAX_SPECIES,
            MIN(REPORT_DATE_TYPE) as MIN_DATE_TYPE,
            MAX(REPORT_DATE_TYPE) as MAX_DATE_TYPE
        FROM SIGNATURE
        GROUP BY SIGN_ID
        ORDER BY SIGN_ID
    """)

    rows = cursor.fetchall()[:10]
    print(f"\nSignature summary (first 10):\n")
    print(f"{'SIGN_ID':<10} {'SPECIES_COUNT':<15} {'MIN_SPECIES':<15} {'MAX_SPECIES':<15} {'DATE_TYPE_RANGE':<20}")
    print("-" * 80)

    for row in rows:
        date_range = f"{row[4]}-{row[5]}" if row[4] == row[5] else f"{row[4]} to {row[5]}"
        print(f"{row[0]:<10} {row[1]:<15} {row[2]:<15} {row[3]:<15} {date_range:<20}")

def main():
    conn = connect_db()
    cursor = conn.cursor()

    try:
        # First, get summary of all signatures
        query_all_signatures_summary(cursor)

        # Check report species to signature mapping
        query_report_species_signatures(cursor)

        # Check fields for structure_def_id=0
        query_field_definitions_by_structure(cursor, structure_def_id=0)

        # Detailed mapping for SIGN_ID=1
        query_signature_with_structure_fields(cursor, sign_id=1)

        print("\n" + "="*100)
        print("KEY FINDINGS")
        print("="*100)
        print("""
The query results should show:

1. SIGNATURE.SIGN_ID links to multiple REPORT_SPECIES_ID values
2. SENSITIVE_FIELD maps SIGN_ID to (LINE_ID, FIELD_ID) pairs
3. FIELD table contains the actual field definitions with NAME column
4. IS_SIGNIFICANT=1 indicates section boundary fields (BrCode, Seg)
5. REPORT_DATE_TYPE indicates: 0=Today, 1=LastBusinessDay, 2=FromField

The field mapping chain:
SIGNATURE (SIGN_ID, REPORT_SPECIES_ID)
  → SENSITIVE_FIELD (SIGN_ID, LINE_ID, FIELD_ID)
    → FIELD (STRUCTURE_DEF_ID, LINE_ID, FIELD_ID, NAME)
        """)

    finally:
        cursor.close()
        conn.close()
        print("\n✓ Database connection closed.")

if __name__ == '__main__':
    main()
