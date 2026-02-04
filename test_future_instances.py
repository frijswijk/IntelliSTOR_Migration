#!/usr/bin/env python3
"""Check for future/test instances in the database"""

import pymssql
from datetime import datetime

# Connect to database
conn = pymssql.connect(
    server='localhost',
    port=1433,
    user='sa',
    password='Fvrpgr40',
    database='iSTSGUAT'
)

cursor = conn.cursor(as_dict=True)

print("Checking for future/test report instances...")
print("=" * 80)

# Check for future instances (after 2025)
query = """
SELECT
    ri.DOMAIN_ID,
    ri.REPORT_SPECIES_ID,
    ri.AS_OF_TIMESTAMP,
    rsn.NAME as REPORT_NAME,
    ri.RPT_FILE_SIZE_KB,
    ri.MAP_FILE_SIZE_KB
FROM REPORT_INSTANCE ri
LEFT JOIN REPORT_SPECIES_NAME rsn
    ON ri.DOMAIN_ID = rsn.DOMAIN_ID
    AND ri.REPORT_SPECIES_ID = rsn.REPORT_SPECIES_ID
WHERE ri.AS_OF_TIMESTAMP >= '2026-01-01'
ORDER BY ri.AS_OF_TIMESTAMP
"""

cursor.execute(query)
future_instances = cursor.fetchall()

print(f"\nInstances from 2026-01-01 onwards: {len(future_instances)}")
print("=" * 80)

if future_instances:
    print("\nFuture/Test Instances:")
    print("-" * 80)
    for idx, inst in enumerate(future_instances, 1):
        ts = inst['AS_OF_TIMESTAMP']
        print(f"{idx:3d}. {inst['REPORT_NAME']:30s} | {ts} | "
              f"Species: {inst['REPORT_SPECIES_ID']:5d} | "
              f"RPT: {inst['RPT_FILE_SIZE_KB']:6d}KB | MAP: {inst['MAP_FILE_SIZE_KB']:6d}KB")
else:
    print("\n✓ No future instances found (all instances are before 2026-01-01)")

# Also check latest instance date
query2 = """
SELECT MAX(AS_OF_TIMESTAMP) as latest_date
FROM REPORT_INSTANCE
"""
cursor.execute(query2)
result = cursor.fetchone()
print(f"\n\nLatest instance date in database: {result['latest_date']}")

# Check earliest instance date
query3 = """
SELECT MIN(AS_OF_TIMESTAMP) as earliest_date
FROM REPORT_INSTANCE
"""
cursor.execute(query3)
result = cursor.fetchone()
print(f"Earliest instance date in database: {result['earliest_date']}")

cursor.close()
conn.close()
