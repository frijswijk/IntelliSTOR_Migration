#!/usr/bin/env python3
"""
Query SIGNATURE and SENSITIVE_FIELD tables to find where field mappings are defined.
This investigates how the system knows which fields to use for:
- Section variables (BrCode001, Seg01)
- Report name variables (RptID001)
- Report date variables (RptDate001)
"""

import pymssql
import sys

# Connection details from DATABASE_REFERENCE.md
SERVER = 'localhost'
PORT = 1433
DATABASE = 'iSTSGUAT'
USER = 'sa'
PASSWORD = 'Fvrpgr40'

def connect_db():
    """Connect to the database."""
    print(f"Connecting to {SERVER}:{PORT}, database: {DATABASE}")
    try:
        conn = pymssql.connect(
            server=SERVER,
            port=PORT,
            database=DATABASE,
            user=USER,
            password=PASSWORD
        )
        print("✓ Connected successfully!\n")
        return conn
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        sys.exit(1)

def query_signature_tables(cursor):
    """Query SIGNATURE and related tables."""

    print("="*80)
    print("SIGNATURE TABLE - Signature Definitions")
    print("="*80)

    cursor.execute("""
        SELECT TOP 10
            SIGN_ID,
            DOMAIN_ID,
            REPORT_SPECIES_ID,
            DESCRIPTION,
            REPORT_DATE_TYPE,
            POSITION,
            MATCHING,
            LBD_OFFSETS
        FROM SIGNATURE
        ORDER BY SIGN_ID
    """)

    rows = cursor.fetchall()
    print(f"\nFound {len(rows)} signature records (showing first 10):\n")
    print(f"{'SIGN_ID':<10} {'DOMAIN_ID':<10} {'SPECIES_ID':<12} {'DESCRIPTION':<30} {'DATE_TYPE':<10} {'POSITION':<10}")
    print("-" * 90)
    for row in rows:
        desc = str(row[3]).strip() if row[3] else ""
        print(f"{row[0]:<10} {row[1]:<10} {row[2]:<12} {desc:<30} {row[4]:<10} {row[5]:<10}")

def query_sensitive_field(cursor):
    """Query SENSITIVE_FIELD table to see field mappings."""

    print("\n" + "="*80)
    print("SENSITIVE_FIELD TABLE - Field Mappings for Signatures")
    print("="*80)

    cursor.execute("""
        SELECT TOP 20
            SIGN_ID,
            LINE_ID,
            FIELD_ID,
            LINE_OF_OCCURENCE,
            NAME,
            SENSITIVITY,
            MINOR_VERSION
        FROM SENSITIVE_FIELD
        ORDER BY SIGN_ID, LINE_ID, FIELD_ID
    """)

    rows = cursor.fetchall()
    print(f"\nFound {len(rows)} sensitive field records (showing first 20):\n")
    print(f"{'SIGN_ID':<10} {'LINE_ID':<10} {'FIELD_ID':<10} {'LINE_OCCUR':<12} {'NAME':<30} {'SENSITIVITY':<12}")
    print("-" * 90)
    for row in rows:
        name = str(row[4]).strip() if row[4] else ""
        print(f"{row[0]:<10} {row[1]:<10} {row[2]:<10} {row[3]:<12} {name:<30} {row[5]:<12}")

def query_signature_with_fields(cursor):
    """Join SIGNATURE and SENSITIVE_FIELD to see complete mappings."""

    print("\n" + "="*80)
    print("SIGNATURE + SENSITIVE_FIELD JOIN - Complete Field Mappings")
    print("="*80)

    cursor.execute("""
        SELECT TOP 30
            s.SIGN_ID,
            s.DESCRIPTION,
            s.REPORT_DATE_TYPE,
            sf.LINE_ID,
            sf.FIELD_ID,
            sf.NAME as FIELD_NAME,
            sf.SENSITIVITY
        FROM SIGNATURE s
        LEFT JOIN SENSITIVE_FIELD sf ON s.SIGN_ID = sf.SIGN_ID
        ORDER BY s.SIGN_ID, sf.LINE_ID, sf.FIELD_ID
    """)

    rows = cursor.fetchall()
    print(f"\nFound {len(rows)} joined records (showing first 30):\n")
    print(f"{'SIGN_ID':<10} {'DESCRIPTION':<30} {'DATE_TYPE':<10} {'LINE_ID':<10} {'FIELD_ID':<10} {'FIELD_NAME':<30}")
    print("-" * 100)
    for row in rows:
        desc = str(row[1]).strip() if row[1] else ""
        field_name = str(row[5]).strip() if row[5] else ""
        line_id = row[3] if row[3] is not None else ""
        field_id = row[4] if row[4] is not None else ""
        print(f"{row[0]:<10} {desc:<30} {row[2]:<10} {str(line_id):<10} {str(field_id):<10} {field_name:<30}")

def query_field_table_for_signature_fields(cursor):
    """Query FIELD table to see field definitions."""

    print("\n" + "="*80)
    print("FIELD TABLE - Looking for IS_SIGNIFICANT fields (Section variables)")
    print("="*80)

    cursor.execute("""
        SELECT TOP 20
            STRUCTURE_DEF_ID,
            LINE_ID,
            FIELD_ID,
            NAME,
            IS_SIGNIFICANT,
            IS_INDEXED,
            START_COLUMN,
            END_COLUMN
        FROM FIELD
        WHERE IS_SIGNIFICANT = 1
        ORDER BY STRUCTURE_DEF_ID, LINE_ID, FIELD_ID
    """)

    rows = cursor.fetchall()
    print(f"\nFound {len(rows)} significant fields (showing first 20):\n")
    print(f"{'STRUCT_ID':<12} {'LINE_ID':<10} {'FIELD_ID':<10} {'NAME':<30} {'IS_SIGNIF':<12} {'START_COL':<10} {'END_COL':<10}")
    print("-" * 100)
    for row in rows:
        name = str(row[3]).strip() if row[3] else ""
        print(f"{row[0]:<12} {row[1]:<10} {row[2]:<10} {name:<30} {row[4]:<12} {row[6]:<10} {row[7]:<10}")

def query_report_species_name_relationship(cursor):
    """Check how REPORT_SPECIES_NAME relates to SIGNATURE."""

    print("\n" + "="*80)
    print("Checking relationship: REPORT_SPECIES_NAME → SIGNATURE")
    print("="*80)

    # Get a sample report species
    cursor.execute("""
        SELECT TOP 5
            rsn.DOMAIN_ID,
            rsn.REPORT_SPECIES_ID,
            rsn.NAME as REPORT_NAME,
            s.SIGN_ID,
            s.DESCRIPTION
        FROM REPORT_SPECIES_NAME rsn
        LEFT JOIN SIGNATURE s ON rsn.DOMAIN_ID = s.DOMAIN_ID
                              AND rsn.REPORT_SPECIES_ID = s.REPORT_SPECIES_ID
        WHERE s.SIGN_ID IS NOT NULL
        ORDER BY rsn.REPORT_SPECIES_ID
    """)

    rows = cursor.fetchall()
    print(f"\nFound {len(rows)} report species with signatures:\n")
    print(f"{'DOMAIN_ID':<12} {'SPECIES_ID':<12} {'REPORT_NAME':<30} {'SIGN_ID':<10} {'SIGN_DESC':<30}")
    print("-" * 100)
    for row in rows:
        report_name = str(row[2]).strip() if row[2] else ""
        sign_desc = str(row[4]).strip() if row[4] else ""
        print(f"{row[0]:<12} {row[1]:<12} {report_name:<30} {row[3]:<10} {sign_desc:<30}")

def main():
    conn = connect_db()
    cursor = conn.cursor()

    try:
        query_signature_tables(cursor)
        query_sensitive_field(cursor)
        query_signature_with_fields(cursor)
        query_field_table_for_signature_fields(cursor)
        query_report_species_name_relationship(cursor)

        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        print("""
Based on the queries above, we should now understand:

1. SIGNATURE table defines signature configurations (SIGN_ID is primary key)
2. SENSITIVE_FIELD links SIGN_ID to specific LINE_ID/FIELD_ID combinations
3. FIELD table contains field definitions where IS_SIGNIFICANT=1 marks section fields
4. SIGNATURE.REPORT_DATE_TYPE indicates how dates are determined

The key relationships:
- SIGNATURE (SIGN_ID) → SENSITIVE_FIELD (maps to LINE_ID/FIELD_ID)
- REPORT_SPECIES (via DOMAIN_ID, REPORT_SPECIES_ID) → SIGNATURE
- FIELD.IS_SIGNIFICANT = 1 indicates section boundary fields (like BrCode, Seg)
        """)

    finally:
        cursor.close()
        conn.close()
        print("\n✓ Database connection closed.")

if __name__ == '__main__':
    main()
