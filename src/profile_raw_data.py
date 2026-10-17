
"""
NexusMart raw-data profiler
Reads the supplied CSVs without modifying them.
Outputs a baseline report for cleaning decisions.
"""

import csv
import hashlib
import json
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
REPORT_DIR = ROOT / "reports"
REPORT_PATH = REPORT_DIR / "raw_profile.json"

# Candidate identifiers from the official problem statement.
KEY_COLUMNS = {
    "customers.csv": ["customer_id"],
    "products.csv": ["product_id"],
    "sellers.csv": ["seller_id"],
    "locations.csv": ["city_id"],
    "orders.csv": ["order_id"],
    "order_items.csv": ["order_item_id"],
    "payments.csv": ["payment_id"],
    "shipping.csv": ["shipment_id"],
    "returns.csv": ["return_id"],
}


def profile_csv(path: Path) -> dict:
    row_count = 0
    blank_counts = Counter()
    key_counts = Counter()
    exact_row_hashes = set()
    exact_duplicate_rows = 0
    columns = []

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        columns = reader.fieldnames or []

        if not columns:
            raise ValueError(f"No header row found in {path.name}")

        key_columns = [
            col for col in KEY_COLUMNS.get(path.name, [])
            if col in columns
        ]

        for row in reader:
            row_count += 1

            for col in columns:
                value = row.get(col)
                if value is None or not value.strip():
                    blank_counts[col] += 1

            # Hash the entire row to detect exact duplicates
            canonical_row = json.dumps(
                [row.get(col) for col in columns],
                ensure_ascii=False,
                separators=(",", ":"),
            )
            row_hash = hashlib.sha256(
                canonical_row.encode("utf-8")
            ).digest()

            if row_hash in exact_row_hashes:
                exact_duplicate_rows += 1
            else:
                exact_row_hashes.add(row_hash)

            for col in key_columns:
                value = (row.get(col) or "").strip()
                if value:
                    key_counts[(col, value)] += 1

    duplicate_keys = {}
    for col in KEY_COLUMNS.get(path.name, []):
        if col in columns:
            duplicate_keys[col] = sum(
                count - 1
                for (key_col, _), count in key_counts.items()
                if key_col == col and count > 1
            )

    return {
        "file": path.name,
        "row_count": row_count,
        "columns": columns,
        "column_count": len(columns),
        "blank_values_by_column": {
            col: blank_counts[col]
            for col in columns
            if blank_counts[col] > 0
        },
        "exact_duplicate_rows_after_first_occurrence": (
            exact_duplicate_rows
        ),
        "duplicate_key_occurrences": duplicate_keys,
    }


def main():
    if not DATA_DIR.exists():
        raise FileNotFoundError(f"Data directory not found: {DATA_DIR}")

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    csv_files = sorted(DATA_DIR.glob("*.csv"))

    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {DATA_DIR}")

    results = []
    for path in csv_files:
        print(f"Profiling {path.name} ...")
        result = profile_csv(path)
        results.append(result)

        print(
            f"  Rows: {result['row_count']:,} | "
            f"Columns: {result['column_count']} | "
            f"Exact duplicate rows: "
            f"{result['exact_duplicate_rows_after_first_occurrence']:,}"
        )

    report = {
        "purpose": "Initial raw-data profiling; no source files modified",
        "files_profiled": len(results),
        "files": results,
    }

    REPORT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\nProfile saved to: {REPORT_PATH}")
    print("Raw source files were not modified.")


if __name__ == "__main__":
    main()
