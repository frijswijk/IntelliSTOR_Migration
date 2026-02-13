import pymssql
conn = pymssql.connect('localhost', 'sa', 'Fvrpgr40', 'iSTSGUAT')
c = conn.cursor()
c.execute("SELECT REPORT_SPECIES_ID, RTRIM(NAME) FROM REPORT_SPECIES_NAME WHERE REPORT_SPECIES_ID IN (1285, 1346)")
for r in c.fetchall():
    print(r)
conn.close()
