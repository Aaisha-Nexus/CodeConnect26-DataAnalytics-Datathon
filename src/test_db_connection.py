
import os

import pyodbc

driver = os.environ.get("NEXUSMART_SQL_DRIVER", "ODBC Driver 17 for SQL Server")
parts = [
    f"DRIVER={{{driver}}}",
    f"SERVER={os.environ['NEXUSMART_SQL_SERVER']}",
    f"DATABASE={os.environ.get('NEXUSMART_SQL_DATABASE', 'NexusMartDW')}",
]
user = os.environ.get("NEXUSMART_SQL_USER")
password = os.environ.get("NEXUSMART_SQL_PASSWORD")
if user and password:
    parts.extend((f"UID={user}", f"PWD={password}"))
else:
    parts.append("Trusted_Connection=yes")
parts.append("TrustServerCertificate=yes")
connection_string = ";".join(parts) + ";"

try:
    with pyodbc.connect(connection_string) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT DB_NAME()")
        print("Connected database:", cursor.fetchone()[0])

        cursor.execute("""
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = 'stg'
        """)
        print("Staging tables:", cursor.fetchone()[0])

except pyodbc.Error as error:
    print("Connection failed:")
    print(error)
