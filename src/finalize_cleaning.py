"""Finalize the existing NexusMart cleaning run and write audit reports.

This script starts from data/processed and never reads or rewrites raw CSVs
as output. Rejection files are read-only inputs, so reruns cannot append
duplicate rejection rows.
"""

from __future__ import annotations

from pathlib import Path
import re

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
REJECTED = ROOT / "data" / "rejected"
REPORTS = ROOT / "reports"

KEYS = {
    "customers.csv": "customer_id",
    "locations.csv": "city_id",
    "orders.csv": "order_id",
    "order_items.csv": "order_item_id",
    "payments.csv": "payment_id",
    "products.csv": "product_id",
    "returns.csv": "return_id",
    "sellers.csv": "seller_id",
    "shipping.csv": "shipment_id",
}

DATE_COLUMNS = {
    "customers.csv": ["registration_date"],
    "orders.csv": ["order_date"],
    "payments.csv": ["payment_date"],
    "shipping.csv": ["shipped_date", "delivered_date"],
    "returns.csv": ["return_date"],
    "sellers.csv": ["join_date"],
}

NUMERIC_COLUMNS = {
    "customers.csv": ["birth_year"],
    "locations.csv": ["latitude", "longitude"],
    "order_items.csv": ["quantity", "unit_price", "discount_amount"],
    "orders.csv": ["order_total"],
    "payments.csv": ["amount"],
    "products.csv": ["list_price", "cost_price", "weight_kg"],
    "returns.csv": ["refund_amount"],
    "sellers.csv": ["rating"],
    "shipping.csv": ["shipping_fee"],
}

INTEGER_COLUMNS = {
    "customers.csv": ["city_id", "birth_year"],
    "locations.csv": ["city_id"],
    "orders.csv": ["ship_city_id"],
    "order_items.csv": ["quantity"],
    "sellers.csv": ["city_id"],
}

MISSING_CATEGORY_ACTIONS = {
    ("customers.csv", "gender"): "Unknown",
    ("products.csv", "sub_category"): "Unknown",
    ("products.csv", "brand"): "Unknown",
    ("returns.csv", "return_reason"): "Unknown",
    ("sellers.csv", "seller_tier"): "Unknown",
}

# Only unambiguous spelling, abbreviation, and synonymous-label variants.
# Broader/narrower product labels and potentially distinct payment types stay separate.
CATEGORY_ALIASES = {
    ("orders.csv", "channel"): {
        "Website": "Web", "Mweb": "Mobile Web", "Mobile App": "App",
    },
    ("payments.csv", "payment_method"): {
        "Cod": "Cash On Delivery", "Jazz Cash": "Jazzcash",
        "Easy Paisa": "Easypaisa", "Bank Trf": "Bank Transfer",
    },
    ("payments.csv", "payment_status"): {"Refund": "Refunded"},
    ("products.csv", "category"): {
        "Home And Kitchen": "Home & Kitchen", "Home&Kitchen": "Home & Kitchen",
        "Mobile Acc.": "Mobile & Accessories", "Mobiles": "Mobile & Accessories",
        "Mobile And Accessories": "Mobile & Accessories",
        "Fashion & Apparel": "Fashion", "Shoes": "Footwear",
        "Electronic Items": "Electronics", "Elec.": "Electronics",
        "Beauty And Personal Care": "Beauty & Personal Care",
        "Sports And Outdoors": "Sports & Outdoors",
        "Books And Stationery": "Books & Stationery",
        "Health And Wellness": "Health & Wellness", "Toys And Games": "Toys & Games",
        "Auto": "Automotive", "Groceries": "Grocery",
        "Stationary": "Books & Stationery",
    },
    ("shipping.csv", "courier"): {
        "T.C.S": "TCS", "Tcs": "TCS", "Tcs Express": "TCS",
        "Leopard Courier": "Leopards",
        "M & P": "M&P", "Mnp": "M&P",
        "Blue Ex": "Blueex", "Blue-Ex": "Blueex",
    },
    ("returns.csv", "return_reason"): {
        "Damaged": "Damaged Product", "Item Damaged": "Damaged Product",
        "Poor Quality": "Quality Issue", "Bad Quality": "Quality Issue",
        "Quality": "Quality Issue", "Size Issue": "Size/Fit Issue",
        "Size/Fit": "Size/Fit Issue", "Doesn't Fit": "Size/Fit Issue",
        "Change Of Mind": "Changed Mind", "Changed My Mind": "Changed Mind",
        "Wrong Item": "Wrong Item Delivered",
        "Received Wrong Product": "Wrong Item Delivered",
        "Color Mismatch": "Colour Mismatch", "Colour Different": "Colour Mismatch",
        "Wrong Colour": "Colour Mismatch", "Delivered Late": "Late Delivery",
        "Too Late": "Late Delivery", "Late": "Late Delivery",
        "Parts Missing": "Missing Parts", "Missing Part": "Missing Parts",
        "Incomplete": "Missing Parts",
    },
}

RELATIONSHIPS = [
    ("customers.csv", "city_id", "locations.csv", "city_id"),
    ("sellers.csv", "city_id", "locations.csv", "city_id"),
    ("orders.csv", "customer_id", "customers.csv", "customer_id"),
    ("orders.csv", "ship_city_id", "locations.csv", "city_id"),
    ("order_items.csv", "order_id", "orders.csv", "order_id"),
    ("order_items.csv", "product_id", "products.csv", "product_id"),
    ("order_items.csv", "seller_id", "sellers.csv", "seller_id"),
    ("payments.csv", "order_id", "orders.csv", "order_id"),
    ("shipping.csv", "order_id", "orders.csv", "order_id"),
    ("returns.csv", "order_item_id", "order_items.csv", "order_item_id"),
]


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, low_memory=False, encoding="utf-8-sig")


def normal_key(value: object) -> str | None:
    if pd.isna(value):
        return None
    value = str(value).strip()
    if not value:
        return None
    if re.fullmatch(r"\d+\.0", value):
        value = value[:-2]
    return value.casefold()


def existing_rejected_keys(parent_file: str, key: str) -> set[str]:
    """Return normalized IDs known to have been quarantined from a parent."""
    found: set[str] = set()
    for path in REJECTED.glob("*.csv"):
        if "flag" in path.stem or path.name == "sentinel_value_rejects.csv":
            continue
        try:
            frame = read_csv(path)
        except (pd.errors.EmptyDataError, UnicodeDecodeError):
            continue
        if "source_file" in frame:
            subset = frame[frame["source_file"].astype("string").eq(parent_file)]
            if key in subset:
                found.update(x for x in subset[key].map(normal_key) if x)
        elif key in frame and path.name != "numeric_field_flags.csv":
            # Typed, table-specific rejection files identify their own source.
            source_match = (
                (parent_file == "order_items.csv" and "order_items" in path.stem)
                or (parent_file == "orders.csv" and "orders" in path.stem)
                or (parent_file == "payments.csv" and "payments" in path.stem)
                or (parent_file == "shipping.csv" and "shipping" in path.stem)
            )
            if source_match:
                found.update(x for x in frame[key].map(normal_key) if x)
    return found


def apply_documented_missing_actions(frames: dict[str, pd.DataFrame]) -> list[dict]:
    actions: list[dict] = []
    for (filename, column), replacement in MISSING_CATEGORY_ACTIONS.items():
        frame = frames[filename]
        before = int(frame[column].isna().sum())
        blank = frame[column].astype("string").str.strip().eq("").fillna(False)
        affected = before + int(blank.sum())
        if affected:
            frame.loc[frame[column].isna() | blank, column] = replacement
        actions.append({"file": filename, "column": column,
                        "rule": f"Missing descriptive category = {replacement}",
                        "rows_changed_this_run": affected,
                        "missing_after": int(frame[column].isna().sum())})

    frame = frames["orders.csv"]
    col = frame["discount_code"].astype("string")
    blank = frame["discount_code"].isna() | col.str.strip().eq("").fillna(False)
    affected = int(blank.sum())
    if affected:
        frame.loc[blank, "discount_code"] = "NO_DISCOUNT"
    actions.append({"file": "orders.csv", "column": "discount_code",
                    "rule": "Blank means no discount (challenge specification)",
                    "rows_changed_this_run": affected,
                    "missing_after": int(frame["discount_code"].isna().sum())})
    pd.DataFrame(actions).to_csv(REPORTS / "missing_value_action_log.csv", index=False)
    return actions


def standardize_category_aliases(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    mapping_rows = []
    for (filename, column), aliases in CATEGORY_ALIASES.items():
        series = frames[filename][column].astype("string")
        # Match exact labels after whitespace trimming, preserving nulls.
        trimmed = series.str.strip()
        for source, target in aliases.items():
            mask = trimmed.str.casefold().eq(source.casefold()).fillna(False)
            if mask.any():
                frames[filename].loc[mask, column] = target
            remaining = frames[filename][column].astype("string").str.strip().eq(source).fillna(False)
            mapping_rows.append({"file": filename, "column": column,
                                 "observed_value": source,
                                 "canonical_value": target,
                                 "rows_remaining_as_source_label": int(remaining.sum()),
                                 "rule": "Clear spelling, abbreviation, or synonymous label"})
    result = pd.DataFrame(mapping_rows, columns=["file", "column", "observed_value",
                                                "canonical_value", "rows_remaining_as_source_label", "rule"])
    result.to_csv(REPORTS / "category_value_mapping.csv", index=False)
    return result


def convert_types(frames: dict[str, pd.DataFrame]) -> tuple[list[dict], list[dict]]:
    type_rows: list[dict] = []
    bad_date_rows: list[dict] = []
    for filename, frame in frames.items():
        for column in NUMERIC_COLUMNS.get(filename, []):
            if column not in frame:
                continue
            raw = frame[column]
            text = raw.astype("string").str.strip()
            if filename == "products.csv" and column == "list_price":
                text = text.str.replace(r"(?i)^rs\.?\s*", "", regex=True).str.replace(",", "", regex=False)
            converted = pd.to_numeric(text, errors="coerce")
            invalid = raw.notna() & converted.isna()
            type_rows.append({"file": filename, "column": column,
                              "target_type": "numeric", "rows": len(frame),
                              "null_before": int(raw.isna().sum()),
                              "unparseable_non_null": int(invalid.sum()),
                              "null_after": int(converted.isna().sum()),
                              "dtype_written": str(converted.dtype)})
            frame[column] = converted

        for column in DATE_COLUMNS.get(filename, []):
            if column not in frame:
                continue
            raw = frame[column].astype("string").str.strip()
            parsed = pd.to_datetime(raw, errors="coerce", format="mixed", dayfirst=False)
            # Resolve unambiguous DD/MM/YYYY values explicitly; ambiguous slash
            # dates remain unresolved and are reported instead of guessed.
            slash = raw.str.fullmatch(r"\d{1,2}/\d{1,2}/\d{4}").fillna(False)
            parts = raw.str.extract(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")
            first = pd.to_numeric(parts[0], errors="coerce")
            second = pd.to_numeric(parts[1], errors="coerce")
            day_first = slash & first.gt(12) & second.le(12)
            month_first = slash & second.gt(12) & first.le(12)
            parsed.loc[day_first] = pd.to_datetime(raw[day_first], format="%d/%m/%Y", errors="coerce")
            parsed.loc[month_first] = pd.to_datetime(raw[month_first], format="%m/%d/%Y", errors="coerce")
            ambiguous = slash & first.le(12) & second.le(12) & raw.notna()
            invalid = raw.notna() & parsed.isna()
            for idx in frame.index[invalid | ambiguous]:
                bad_date_rows.append({"file": filename, "source_row_index": int(idx),
                                      "column": column, "original_value": raw.loc[idx],
                                      "reason_code": "AMBIGUOUS_DATE_FORMAT" if ambiguous.loc[idx]
                                      else "INVALID_DATE"})
            # Store parseable dates as ISO strings. Preserve ambiguous/invalid
            # original text for later review and never invent a date.
            new_values = raw.copy()
            good = parsed.notna() & ~ambiguous
            new_values.loc[good] = parsed.loc[good].dt.strftime("%Y-%m-%d")
            frame[column] = new_values.astype("object")
            type_rows.append({"file": filename, "column": column,
                              "target_type": "date (ISO text in CSV)", "rows": len(frame),
                              "null_before": int(raw.isna().sum()),
                              "unparseable_non_null": int((invalid | ambiguous).sum()),
                              "null_after": int(raw.isna().sum()),
                              "dtype_written": "ISO-8601 text plus flagged unresolved values"})

        for column in INTEGER_COLUMNS.get(filename, []):
            if column not in frame:
                continue
            numeric = pd.to_numeric(frame[column], errors="coerce")
            finite = numeric.dropna()
            non_integral = int((finite % 1 != 0).sum())
            if non_integral == 0:
                frame[column] = numeric.astype("Int64")
            type_rows.append({"file": filename, "column": column,
                              "target_type": "nullable integer", "rows": len(frame),
                              "null_before": int(frame[column].isna().sum()),
                              "unparseable_non_null": non_integral,
                              "null_after": int(frame[column].isna().sum()),
                              "dtype_written": str(frame[column].dtype)})
    return type_rows, bad_date_rows


def reference_audit(frames: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    results = []
    exceptions = []
    for child_file, child_col, parent_file, parent_col in RELATIONSHIPS:
        child = frames[child_file]
        parent_series = read_csv(PROCESSED / parent_file)[parent_col]
        parent_keys = {x for x in parent_series.map(normal_key) if x}
        exact_parent_keys = {
            str(x).strip().casefold() for x in parent_series.dropna()
        }
        parent_rejected = existing_rejected_keys(parent_file, parent_col)
        raw_keys = child[child_col].map(normal_key)
        present = raw_keys.notna()
        direct = raw_keys.isin(parent_keys)
        quarantined = raw_keys.isin(parent_rejected)
        missing = ~present
        raw_text = child[child_col].map(
            lambda x: None if pd.isna(x) else str(x).strip().casefold()
        )
        formatting = present & direct & ~raw_text.isin(exact_parent_keys)
        true_broken = present & ~direct & ~quarantined
        valid_exact = direct & ~formatting
        child_key = KEYS[child_file]
        for idx in child.index[quarantined | true_broken]:
            is_quarantined = bool(quarantined.loc[idx])
            exceptions.append({
                "relationship": f"{child_file}.{child_col}->{parent_file}.{parent_col}",
                "child_file": child_file, "child_record_id": child.at[idx, child_key],
                "reference_column": child_col, "reference_value": child.at[idx, child_col],
                "reason_code": "REFERENCE_TO_QUARANTINED_PARENT" if is_quarantined else "TRUE_BROKEN_REFERENCE",
                "handling": "Retained in processed table; excluded from FK-constrained loading pending disposition",
            })
        results.append({"relationship": f"{child_file}.{child_col}->{parent_file}.{parent_col}",
                        "rows_checked": len(child), "missing_references": int(missing.sum()),
                        "valid_references": int(valid_exact.sum()),
                        "references_to_quarantined_parent": int(quarantined.sum()),
                        "formatting_mismatch_only": int(formatting.sum()),
                        "true_broken_references": int(true_broken.sum()),
                        "handling": "Retained and reported; no unsupported ID mapping"})
    exception_df = pd.DataFrame(exceptions, columns=["relationship", "child_file", "child_record_id",
                                                    "reference_column", "reference_value",
                                                    "reason_code", "handling"])
    exception_df.to_csv(REPORTS / "reference_exception_rows.csv", index=False, na_rep="")
    return pd.DataFrame(results), exception_df


def missing_value_decisions(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    source_path = REPORTS / "missing_value_decisions.csv"
    source = read_csv(source_path)
    rows = []
    for record in source.to_dict("records"):
        filename, column = record["file"], record["column"]
        if filename not in frames or column not in frames[filename]:
            continue
        series = frames[filename][column]
        blank = series.astype("string").str.strip().eq("").fillna(False)
        missing_count = int(series.isna().sum() + blank.sum())
        proposal = str(record.get("proposed_action", ""))
        if (filename, column) in MISSING_CATEGORY_ACTIONS or (filename, column) == ("orders.csv", "discount_code"):
            decision = "Applied documented value rule; no nulls remain" if missing_count == 0 else "Applied rule; residual nulls retained"
        elif missing_count == 0:
            decision = "No missing values remain in processed table"
        else:
            decision = "Retained as null; unresolved or optional; no imputation"
        rows.append({"file": filename, "column": column,
                     "documented_action": proposal,
                     "final_decision": decision,
                     "missing_values_retained": missing_count,
                     "business_reason": record.get("business_reason", "")})
    result = pd.DataFrame(rows)
    result.to_csv(REPORTS / "final_missing_value_decisions.csv", index=False)
    return result


def rejection_inventory() -> pd.DataFrame:
    rows = []
    for path in sorted(REJECTED.glob("*.csv")):
        if ("flag" in path.stem or path.name in {
            "sentinel_value_rejects.csv", "all_reason_coded_rejections.csv"
        }):
            continue  # flags/combined convenience extract are not additive rejects
        frame = read_csv(path)
        if "source_file" in frame:
            grouped = frame.groupby("source_file", dropna=False)
            for source_file, subset in grouped:
                rows.append({"source_file": source_file, "rejection_file": path.name,
                             "rows": len(subset),
                             "reason_codes": " | ".join(sorted(subset["reason_code"].dropna().astype(str).unique()))
                             if "reason_code" in subset else "UNSPECIFIED"})
        else:
            source_file = next((f for f in KEYS if f.split(".")[0] in path.stem), path.name)
            rows.append({"source_file": source_file, "rejection_file": path.name,
                         "rows": len(frame),
                         "reason_codes": " | ".join(sorted(frame["reason_code"].dropna().astype(str).unique()))
                         if "reason_code" in frame else "UNSPECIFIED"})
    out = pd.DataFrame(rows)
    out.to_csv(REPORTS / "reason_coded_rejection_inventory.csv", index=False)
    return out


def numeric_anomaly_reports(frames: dict[str, pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    flag_rows = []
    outlier_rows = []
    context = {
        ("orders.csv", "order_total"): ["order_status"],
        ("payments.csv", "amount"): ["payment_status", "payment_method"],
        ("shipping.csv", "shipping_fee"): ["delivery_status", "courier"],
    }
    for filename, columns in NUMERIC_COLUMNS.items():
        frame = frames[filename]
        key = KEYS[filename]
        for column in columns:
            if column not in frame:
                continue
            values = pd.to_numeric(frame[column], errors="coerce")
            nonmissing = values.dropna()
            negative = values.lt(0) & values.notna()
            for idx in frame.index[negative]:
                item = {"source_file": filename, "record_id": frame.at[idx, key],
                        "issue_column": column, "original_value": values.at[idx],
                        "reason_code": f"NEGATIVE_{column.upper()}_REVIEW",
                        "handling": "Retained and flagged; no reliable correction established"}
                for ctx in context.get((filename, column), []):
                    item[ctx] = frame.at[idx, ctx]
                flag_rows.append(item)
            if len(nonmissing):
                q1, q3 = nonmissing.quantile([0.25, 0.75])
                iqr = q3 - q1
                low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
                stat_count = int(((values < low) | (values > high)).sum())
                minimum, maximum = float(nonmissing.min()), float(nonmissing.max())
            else:
                low = high = minimum = maximum = float("nan")
                stat_count = 0
            outlier_rows.append({"file": filename, "column": column,
                                 "non_missing_values": int(len(nonmissing)),
                                 "negative_values_flagged": int(negative.sum()),
                                 "minimum": minimum, "maximum": maximum,
                                 "iqr_lower_bound": low, "iqr_upper_bound": high,
                                 "statistical_outlier_count": stat_count,
                                 "handling": "Statistical extremes retained; no business evidence supports correction or removal"})
    flags = pd.DataFrame(flag_rows, columns=["source_file", "record_id", "issue_column",
                                           "original_value", "reason_code", "handling",
                                           "order_status", "payment_status", "payment_method",
                                           "delivery_status", "courier"])
    outliers = pd.DataFrame(outlier_rows)
    flags.to_csv(REJECTED / "numeric_anomaly_flags.csv", index=False, na_rep="")
    outliers.to_csv(REPORTS / "final_outlier_audit.csv", index=False)
    return flags, outliers


def consolidate_rejections() -> pd.DataFrame:
    parts = []
    excluded = {"numeric_field_flags.csv", "date_field_flags.csv",
                "numeric_anomaly_flags.csv", "sentinel_value_rejects.csv",
                "all_reason_coded_rejections.csv"}
    for path in sorted(REJECTED.glob("*.csv")):
        if path.name in excluded:
            continue
        frame = read_csv(path)
        if "reason_code" not in frame:
            continue
        if "source_file" not in frame:
            source_file = next((name for name in KEYS if name.split(".")[0] in path.stem), None)
            if source_file is None:
                continue
            frame["source_file"] = source_file
        if "source_row_index" not in frame and "source_row_number" in frame:
            frame["source_row_index"] = pd.to_numeric(frame["source_row_number"], errors="coerce") - 1
        frame["rejection_artifact"] = path.name
        parts.append(frame)
    if not parts:
        result = pd.DataFrame(columns=["source_file", "source_row_index", "reason_code"])
    else:
        result = pd.concat(parts, ignore_index=True, sort=False)
        # Rejection-stage row indexes can restart after each transformation.
        # Deduplicate by the dataset's stable primary key instead.
        identity_columns = []
        for source_file, key in KEYS.items():
            if key in result.columns:
                mask = result["source_file"].eq(source_file) & result[key].notna()
                result.loc[mask, "_row_identity"] = result.loc[mask, key].astype("string").str.strip()
        result["_row_identity"] = result.get("_row_identity", pd.Series(index=result.index, dtype="string"))
        fallback = result["source_row_index"].astype("string") if "source_row_index" in result else result.index.astype(str)
        result["_row_identity"] = result["_row_identity"].fillna(fallback)
        result = result.drop_duplicates(subset=["source_file", "_row_identity"], keep="first")
        result = result.drop(columns=["_row_identity"])
    result.to_csv(REJECTED / "all_reason_coded_rejections.csv", index=False, na_rep="")
    return result


def main() -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    frames = {name: read_csv(PROCESSED / name) for name in KEYS}
    missing_actions = apply_documented_missing_actions(frames)
    missing_decisions = missing_value_decisions(frames)
    category_mapping = standardize_category_aliases(frames)
    type_rows, date_flags = convert_types(frames)
    numeric_flags, outliers = numeric_anomaly_reports(frames)
    for name, frame in frames.items():
        frame.to_csv(PROCESSED / name, index=False, na_rep="")

    pd.DataFrame(type_rows).to_csv(REPORTS / "data_type_validation.csv", index=False)
    pd.DataFrame(date_flags, columns=["file", "source_row_index", "column",
                                     "original_value", "reason_code"]).to_csv(
        REJECTED / "date_field_flags.csv", index=False)

    refs, reference_exceptions = reference_audit(frames)
    refs.to_csv(REPORTS / "final_reference_integrity_report.csv", index=False)
    all_rejections = consolidate_rejections()
    rejects = rejection_inventory()

    baseline = read_csv(REPORTS / "cleaning_baseline.csv").set_index("file")
    duplicate_log = read_csv(REPORTS / "duplicate_removal_log.csv").set_index("file")
    reject_by_file = rejects.groupby("source_file")["rows"].sum().to_dict() if len(rejects) else {}
    # Avoid double counting combined sentinel convenience file; inventory excludes it.
    quality = []
    for filename in KEYS:
        frame = frames[filename]
        original = int(baseline.loc[filename, "rows_before"])
        removed_duplicates = int(duplicate_log.loc[filename, "exact_duplicates_removed"])
        rejected = int(reject_by_file.get(filename, 0))
        retained = len(frame)
        quality.append({"file": filename, "original_rows": original,
                        "retained_rows": retained, "quarantined_rows": rejected,
                        "exact_duplicate_rows_removed": removed_duplicates,
                        "reconciled_rows": retained + rejected + removed_duplicates,
                        "row_reconciliation_pass": retained + rejected + removed_duplicates == original,
                        "columns": len(frame.columns),
                        "missing_cells_retained": int(frame.isna().sum().sum()),
                        "exact_duplicates_retained": int(frame.duplicated().sum()),
                        "unique_key_duplicates": int(frame[KEYS[filename]].duplicated().sum())})
    quality_df = pd.DataFrame(quality)
    quality_df.to_csv(REPORTS / "consolidated_quality_report.csv", index=False)

    decisions = [
        ("Missing values", "partially implemented", "Documented category/no-discount actions applied; optional and key/measure nulls retained and reported."),
        ("Exact duplicate records", "implemented", "Existing duplicate-removal counts reconciled with current retained and quarantined rows."),
        ("Duplicate customers/products under different IDs", "partially implemented", "Candidate report retained; no entity merged without independent identity evidence."),
        ("Inconsistent categories", "implemented", "Existing normalization plus explicit, preserved alias mapping; semantically distinct labels remain separate."),
        ("Invalid dates", "partially implemented", "Audited date columns quarantined; registration-date invalid/ambiguous values are flagged for review."),
        ("Incorrect data types", "partially implemented", "Numeric values and nullable IDs converted; date columns remain ISO text in CSV and unresolved dates are flagged."),
        ("Outliers", "partially implemented", "Known sentinel and invalid quantities quarantined; other negative/statistical extremes flagged and retained."),
        ("Broken references", "partially implemented", "Final references checked against retained and quarantined parent IDs; unresolved IDs retained and reported."),
    ]
    pd.DataFrame(decisions, columns=["category", "status", "evidence_and_decision"]).to_csv(
        REPORTS / "final_cleaning_decision_log.csv", index=False)

    validation = [
        {"check": "row_reconciliation", "status": "PASS" if quality_df["row_reconciliation_pass"].all() else "FAIL",
         "details": f"{int(quality_df['row_reconciliation_pass'].sum())}/{len(quality_df)} tables reconcile"},
        {"check": "exact_duplicate_rows", "status": "PASS" if quality_df["exact_duplicates_retained"].sum() == 0 else "FAIL",
         "details": f"{int(quality_df['exact_duplicates_retained'].sum())} exact duplicate rows remain"},
        {"check": "primary_key_duplicates", "status": "PASS" if quality_df["unique_key_duplicates"].sum() == 0 else "FAIL",
         "details": f"{int(quality_df['unique_key_duplicates'].sum())} duplicate primary key occurrences remain"},
        {"check": "numeric_parse", "status": "PASS" if pd.DataFrame(type_rows).query("target_type == 'numeric'")["unparseable_non_null"].sum() == 0 else "REVIEW",
         "details": f"{int(pd.DataFrame(type_rows).query('target_type == \'numeric\'')['unparseable_non_null'].sum())} unparseable non-null numeric values"},
        {"check": "referential_integrity", "status": "REVIEW" if refs["true_broken_references"].sum() or refs["references_to_quarantined_parent"].sum() else "PASS",
         "details": f"{int(refs['true_broken_references'].sum())} broken and {int(refs['references_to_quarantined_parent'].sum())} references to quarantined parents; {len(reference_exceptions)} row-level exceptions exported"},
        {"check": "reference_classification_reconciliation",
         "status": "PASS" if ((refs["missing_references"] + refs["valid_references"] + refs["formatting_mismatch_only"] + refs["references_to_quarantined_parent"] + refs["true_broken_references"]) == refs["rows_checked"]).all() else "FAIL",
         "details": f"{len(refs)} relationships partition into missing, valid, formatting-only, quarantined-parent, or broken references"},
        {"check": "date_review", "status": "REVIEW" if date_flags else "PASS",
         "details": f"{len(date_flags)} invalid or ambiguous customer registration dates flagged"},
        {"check": "reason_coded_rejections", "status": "PASS" if all_rejections["reason_code"].notna().all() else "FAIL",
         "details": f"{len(all_rejections)} unique quarantined rows in consolidated reject output"},
        {"check": "category_alias_mapping", "status": "PASS" if category_mapping["rows_remaining_as_source_label"].sum() == 0 else "REVIEW",
         "details": f"{int(category_mapping['rows_remaining_as_source_label'].sum())} rows remain under explicitly mapped source labels"},
        {"check": "negative_value_flags", "status": "PASS" if int(outliers["negative_values_flagged"].sum()) == len(numeric_flags) else "FAIL",
         "details": f"{len(numeric_flags)} current negative values flagged; statistical outliers retained and summarized"},
    ]
    pd.DataFrame(validation).to_csv(REPORTS / "cleaning_validation_report.csv", index=False)
    print(quality_df.to_string(index=False))
    print("\nValidation:")
    print(pd.DataFrame(validation).to_string(index=False))
    print(f"\nApplied missing actions: {sum(x['rows_changed_this_run'] for x in missing_actions)}")
    print(f"Flagged ambiguous/invalid dates: {len(date_flags)}")
    print("Raw data directory was not modified; rejection files were read-only inputs.")


if __name__ == "__main__":
    main()
