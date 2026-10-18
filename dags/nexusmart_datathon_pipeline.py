
from datetime import datetime, timedelta
from pathlib import Path
import csv
import logging
import os

import pymssql
from airflow import DAG
from airflow.operators.python import PythonOperator

DATA_DIR = Path("/usr/local/airflow/include/processed")

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

DIMENSIONS = [
    "DimDate",
    "DimCustomer",
    "DimProduct",
    "DimSeller",
    "DimLocation",
]


def get_connection():
    """Connect using credentials supplied through environment variables."""
    return pymssql.connect(
        server=os.environ["NEXUSMART_SQL_SERVER"],
        port=int(os.environ.get("NEXUSMART_SQL_PORT", "1433")),
        user=os.environ["NEXUSMART_SQL_USER"],
        password=os.environ["NEXUSMART_SQL_PASSWORD"],
        database=os.environ["NEXUSMART_SQL_DATABASE"],
        login_timeout=10,
        timeout=60,
    )


def extract():
    missing = [
        name for name in FILES
        if not (DATA_DIR / name).is_file()
    ]
    if missing:
        raise FileNotFoundError(f"Missing processed CSV files: {missing}")

    logging.info("Extract check passed: all %d CSV files are present.", len(FILES))


def validate_raw():
    total_rows = 0

    for filename in FILES:
        with (DATA_DIR / filename).open(
            "r", encoding="utf-8-sig", newline=""
        ) as file:
            reader = csv.reader(file)
            header = next(reader, None)

            if not header:
                raise ValueError(f"{filename} has no header.")

            rows = sum(1 for _ in reader)
            if rows == 0:
                raise ValueError(f"{filename} contains no data rows.")

            total_rows += rows
            logging.info(
                "Validated %s: %s rows, %s columns.",
                filename, rows, len(header)
            )

    logging.info("CSV validation passed. Total rows: %s", total_rows)


def clean():
    # The cleaning has already been performed in the project Python workflow.
    # This task verifies its nine processed outputs; it does not clean twice.
    for filename in FILES:
        if not (DATA_DIR / filename).is_file():
            raise FileNotFoundError(f"Processed output missing: {filename}")

    logging.info(
        "Cleaning-output check passed. Existing processed CSVs will be reused."
    )


def load_staging():
    # Verify existing staging instead of reloading populated tables.
    conn = get_connection()
    try:
        cursor = conn.cursor()
        for table in FILES.values():
            cursor.execute(f"SELECT COUNT_BIG(*) FROM stg.[{table}]")
            count = cursor.fetchone()[0]

            if count == 0:
                raise ValueError(f"stg.{table} is empty.")

            logging.info("Verified stg.%s: %s rows.", table, count)

        logging.info("All nine staging tables exist and contain data.")
    finally:
        conn.close()


def build_dimensions():
    # Dimensions already exist; validate them instead of recreating them.
    conn = get_connection()
    try:
        cursor = conn.cursor()

        for table in DIMENSIONS:
            cursor.execute(f"SELECT COUNT_BIG(*) FROM dw.[{table}]")
            count = cursor.fetchone()[0]

            if count == 0:
                raise ValueError(f"dw.{table} is empty.")

            logging.info("Verified dw.%s: %s rows.", table, count)

        unknown_checks = {
            "DimDate": "DateKey",
            "DimCustomer": "CustomerKey",
            "DimProduct": "ProductKey",
            "DimSeller": "SellerKey",
            "DimLocation": "LocationKey",
        }

        for table, key in unknown_checks.items():
            cursor.execute(
                f"SELECT COUNT_BIG(*) FROM dw.[{table}] WHERE [{key}] = 0"
            )
            count = cursor.fetchone()[0]

            if count != 1:
                raise ValueError(
                    f"dw.{table} should contain exactly one Unknown member "
                    f"with {key} = 0; found {count}."
                )

        logging.info("All five dimensions and their Unknown members verified.")
    finally:
        conn.close()


def build_fact():
    # The fact table is populated already. Verify its grain and measures.
    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT_BIG(*),
                COUNT(DISTINCT OrderItemID),
                COUNT(DISTINCT OrderID)
            FROM dw.FactSales
        """)
        rows, distinct_items, distinct_orders = cursor.fetchone()

        if rows == 0:
            raise ValueError("dw.FactSales is empty.")

        if rows != distinct_items:
            raise ValueError(
                f"FactSales grain violation: {rows} rows but "
                f"{distinct_items} distinct OrderItemID values."
            )

        cursor.execute("""
            SELECT
                SUM(GrossAmount),
                SUM(DiscountAmount),
                SUM(NetAmount),
                SUM(CostAmount)
            FROM dw.FactSales
        """)
        measures = cursor.fetchone()

        logging.info(
            "FactSales verified: rows=%s, distinct order items=%s, "
            "distinct orders=%s.",
            rows, distinct_items, distinct_orders
        )
        logging.info(
            "FactSales totals: GrossAmount=%s, DiscountAmount=%s, "
            "NetAmount=%s, CostAmount=%s.",
            *measures
        )
    finally:
        conn.close()


def quality_checks():
    conn = get_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT_BIG(*) AS FactRows,
                COUNT(DISTINCT OrderItemID) AS DistinctOrderItems,
                SUM(CASE WHEN DateKey = 0 THEN 1 ELSE 0 END) AS UnknownDates,
                SUM(CASE WHEN CustomerKey = 0 THEN 1 ELSE 0 END) AS UnknownCustomers,
                SUM(CASE WHEN ProductKey = 0 THEN 1 ELSE 0 END) AS UnknownProducts,
                SUM(CASE WHEN SellerKey = 0 THEN 1 ELSE 0 END) AS UnknownSellers,
                SUM(CASE WHEN LocationKey = 0 THEN 1 ELSE 0 END) AS UnknownLocations
            FROM dw.FactSales
        """)
        result = cursor.fetchone()

        names = [
            "FactRows", "DistinctOrderItems", "UnknownDates",
            "UnknownCustomers", "UnknownProducts", "UnknownSellers",
            "UnknownLocations",
        ]
        summary = dict(zip(names, result))
        logging.info("FactSales quality summary: %s", summary)

        if summary["FactRows"] != summary["DistinctOrderItems"]:
            raise ValueError("Duplicate OrderItemID values exist in FactSales.")

        cursor.execute("""
            SELECT COUNT_BIG(*)
            FROM stg.OrderItems oi
            LEFT JOIN stg.Orders o ON o.order_id = oi.order_id
            WHERE o.order_id IS NULL
        """)
        missing_orders = cursor.fetchone()[0]

        if missing_orders:
            logging.warning(
                "%s staged order-item rows have no matching staged order. "
                "This is a known reconciliation issue; investigate it in "
                "the data-quality report rather than silently dropping rows.",
                missing_orders
            )

        cursor.execute("""
            SELECT COUNT_BIG(*)
            FROM dw.FactSales f
            LEFT JOIN dw.DimDate d ON d.DateKey = f.DateKey
            LEFT JOIN dw.DimCustomer c ON c.CustomerKey = f.CustomerKey
            LEFT JOIN dw.DimProduct p ON p.ProductKey = f.ProductKey
            LEFT JOIN dw.DimSeller s ON s.SellerKey = f.SellerKey
            LEFT JOIN dw.DimLocation l ON l.LocationKey = f.LocationKey
            WHERE d.DateKey IS NULL
               OR c.CustomerKey IS NULL
               OR p.ProductKey IS NULL
               OR s.SellerKey IS NULL
               OR l.LocationKey IS NULL
        """)
        orphan_keys = cursor.fetchone()[0]

        logging.info("FactSales rows with unresolved dimension keys: %s", orphan_keys)

        if orphan_keys:
            raise ValueError(
                f"FactSales contains {orphan_keys} unresolved dimension keys."
            )

        logging.info("Warehouse quality checks passed.")
    finally:
        conn.close()


default_args = {
    "owner": "codeconnect",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}

with DAG(
    dag_id="nexusmart_datathon_pipeline",
    description="NexusMart staging and warehouse validation pipeline",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["nexusmart", "codeconnect", "data-quality"],
) as dag:

    t_extract = PythonOperator(
        task_id="extract", python_callable=extract
    )
    t_validate = PythonOperator(
        task_id="validate_raw", python_callable=validate_raw
    )
    t_clean = PythonOperator(
        task_id="clean", python_callable=clean
    )
    t_load = PythonOperator(
        task_id="load_staging", python_callable=load_staging
    )
    t_dimensions = PythonOperator(
        task_id="build_dimensions", python_callable=build_dimensions
    )
    t_fact = PythonOperator(
        task_id="build_fact", python_callable=build_fact
    )
    t_quality = PythonOperator(
        task_id="quality_checks", python_callable=quality_checks
    )

    t_extract >> t_validate >> t_clean >> t_load >> t_dimensions >> t_fact >> t_quality
