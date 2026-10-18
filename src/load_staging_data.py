
import csv
import logging
import os
from pathlib import Path

import pyodbc

# Project paths
PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data" / "processed"
LOG_DIR = PROJECT_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    filename=LOG_DIR / "staging_load.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

def get_connection_string():
    """Build a SQL Server connection string from environment settings."""
    driver = os.environ.get("NEXUSMART_SQL_DRIVER", "ODBC Driver 17 for SQL Server")
    server = os.environ["NEXUSMART_SQL_SERVER"]
    database = os.environ.get("NEXUSMART_SQL_DATABASE", "NexusMartDW")
    parts = [f"DRIVER={{{driver}}}", f"SERVER={server}", f"DATABASE={database}"]

    user = os.environ.get("NEXUSMART_SQL_USER")
    password = os.environ.get("NEXUSMART_SQL_PASSWORD")
    if user and password:
        parts.extend((f"UID={user}", f"PWD={password}"))
    else:
        parts.append("Trusted_Connection=yes")

    parts.append("TrustServerCertificate=yes")
    return ";".join(parts) + ";"

# CSV filename: SQL staging table
FILES = {
    "customers.csv": "Customers",
    "locations.csv": "Locations",
    "orders.csv": "Orders",
    "order_items.csv": "OrderItems",
    "payments.csv": "Payments",
    "products.csv": "Products",
    "returns.csv": "Returns",
    "sellers.csv": "Sellers",
    "shipping.csv": "Shipping",
}

BATCH_SIZE = 5000


def main():
    conn = pyodbc.connect(get_connection_string())
    cursor = conn.cursor()

    try:
        cursor.fast_executemany = True

        # Safety check: do not append duplicate data.
        for table in FILES.values():
            cursor.execute(f"SELECT COUNT_BIG(*) FROM stg.[{table}]")
            existing = cursor.fetchone()[0]

            if existing:
                raise RuntimeError(
                    f"stg.{table} already contains {existing:,} rows. "
                    "No files were loaded. Check before proceeding."
                )

        # Validate all files and headers before loading anything.
        headers_by_file = {}

        for filename, table in FILES.items():
            path = DATA_DIR / filename

            if not path.is_file():
                raise FileNotFoundError(f"Missing CSV: {path}")

            with path.open(
                "r", encoding="utf-8-sig", newline=""
            ) as file:
                reader = csv.reader(file)
                headers = next(reader, None)

            if not headers:
                raise ValueError(f"{filename} is empty or has no header.")

            cursor.execute(
                """
                SELECT COLUMN_NAME
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = 'stg'
                  AND TABLE_NAME = ?
                ORDER BY ORDINAL_POSITION
                """,
                table,
            )
            sql_columns = [row[0] for row in cursor.fetchall()]

            if headers != sql_columns:
                raise ValueError(
                    f"Header mismatch for {filename} -> stg.{table}\n"
                    f"CSV: {headers}\nSQL: {sql_columns}"
                )

            headers_by_file[filename] = headers

        print("Pre-check passed: all 9 files and table headers match.")

        for filename, table in FILES.items():
            path = DATA_DIR / filename
            headers = headers_by_file[filename]
            columns_sql = ", ".join(f"[{col}]" for col in headers)
            placeholders = ", ".join("?" for _ in headers)

            insert_sql = (
                f"INSERT INTO stg.[{table}] ({columns_sql}) "
                f"VALUES ({placeholders})"
            )

            loaded = 0
            batch = []

            print(f"Loading {filename} -> stg.{table} ...")
            logging.info("Started %s -> stg.%s", filename, table)

            try:
                with path.open(
                    "r", encoding="utf-8-sig", newline=""
                ) as file:
                    reader = csv.DictReader(file)

                    for row in reader:
                        batch.append(
                            tuple(
                                row[column] if row[column] is not None else ""
                                for column in headers
                            )
                        )

                        if len(batch) >= BATCH_SIZE:
                            cursor.executemany(insert_sql, batch)
                            loaded += len(batch)
                            batch.clear()

                    if batch:
                        cursor.executemany(insert_sql, batch)
                        loaded += len(batch)

                cursor.execute(f"SELECT COUNT_BIG(*) FROM stg.[{table}]")
                actual = cursor.fetchone()[0]

                if actual != loaded:
                    raise RuntimeError(
                        f"Count mismatch for stg.{table}: "
                        f"inserted {loaded:,}, table contains {actual:,}"
                    )

                conn.commit()
                print(f"  OK: {loaded:,} rows loaded and verified.")
                logging.info(
                    "Completed %s -> stg.%s: %s rows",
                    filename, table, loaded
                )

            except Exception:
                conn.rollback()
                logging.exception("Failed loading %s -> stg.%s", filename, table)
                raise

        print("\nAll 9 staging tables loaded successfully.")

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
