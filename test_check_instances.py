#!/usr/bin/env python3
"""Quick script to check what report instances exist in the database"""

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

print("Checking report instances in the database...")
print("=" * 80)

# Check all instances
query = """
SELECT
    ri.DOMAIN_ID,
    ri.REPORT_SPECIES_ID,
    ri.AS_OF_TIMESTAMP,
    rsn.NAME as REPORT_NAME
FROM REPORT_INSTANCE ri
LEFT JOIN REPORT_SPECIES_NAME rsn
    ON ri.DOMAIN_ID = rsn.DOMAIN_ID
    AND ri.REPORT_SPECIES_ID = rsn.REPORT_SPECIES_ID
ORDER BY ri.AS_OF_TIMESTAMP
"""

cursor.execute(query)
instances = cursor.fetchall()

print(f"\nTotal instances found: {len(instances)}")
print("=" * 80)

if instances:
    print("\nAll Report Instances:")
    print("-" * 80)
    for idx, inst in enumerate(instances, 1):
        ts = inst['AS_OF_TIMESTAMP']
        print(f"{idx:3d}. {inst['REPORT_NAME']:20s} | {ts} | Species: {inst['REPORT_SPECIES_ID']}")

    # Check for future instances
    now = datetime.now()
    future_instances = [i for i in instances if i['AS_OF_TIMESTAMP'] > now]

    if future_instances:
        print("\n" + "=" * 80)
        print(f"Future/Test Instances (after {now.date()}): {len(future_instances)}")
        print("-" * 80)
        for inst in future_instances:
            ts = inst['AS_OF_TIMESTAMP']
            print(f"  {inst['REPORT_NAME']:20s} | {ts} | Species: {inst['REPORT_SPECIES_ID']}")

cursor.close()
conn.close()
