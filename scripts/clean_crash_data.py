"""
Cleaning pipeline for NYC Open Data's "Motor Vehicle Collisions - Crashes" dataset
(Socrata ID h9gi-nx95).

Usage:
    python clean_crash_data.py <input.xlsx or .csv> <output_prefix>

Produces:
    <output_prefix>.csv          - cleaned data, ready for the Streamlit/Plotly pipeline
    <output_prefix>.xlsx         - same data + a "Cleaning summary" sheet, for manual review
    <output_prefix>_log.json     - machine-readable cleaning log

Designed to be reusable: rerun this unchanged against the full multi-year pull later,
not just this sample.
"""
import sys
import json
import pandas as pd
import numpy as np

NYC_LAT_RANGE = (40.4, 40.95)
NYC_LON_RANGE = (-74.3, -73.65)

STREET_COLS = ["on_street_name", "off_street_name", "cross_street_name"]
FACTOR_COLS = [f"contributing_factor_vehicle_{i}" for i in range(1, 6)]
VEHICLE_COLS = ["vehicle_type_code1", "vehicle_type_code2",
                "vehicle_type_code_3", "vehicle_type_code_4", "vehicle_type_code_5"]
COUNT_COLS = [
    "number_of_persons_injured", "number_of_persons_killed",
    "number_of_pedestrians_injured", "number_of_pedestrians_killed",
    "number_of_cyclist_injured", "number_of_cyclist_killed",
    "number_of_motorist_injured", "number_of_motorist_killed",
]
TEXT_COLS = STREET_COLS + FACTOR_COLS + VEHICLE_COLS + ["borough"]


def clean_crash_data(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    log = {"input_rows": len(df)}
    df = df.copy()

    # --- Dates & times: Excel serial numbers -> real datetime ---------------
    if np.issubdtype(df["crash_date"].dtype, np.number):
        dates = pd.to_datetime(df["crash_date"], unit="D", origin="1899-12-30")
    else:
        dates = pd.to_datetime(df["crash_date"], errors="coerce")

    if np.issubdtype(df["crash_time"].dtype, np.number):
        secs = (df["crash_time"] * 24 * 3600).round().astype("Int64")
        time_str = pd.to_datetime(secs, unit="s", errors="coerce").dt.strftime("%H:%M")
    else:
        time_str = df["crash_time"].astype(str)

    df["crash_date"] = dates.dt.date
    df["crash_time"] = time_str
    df["crash_datetime"] = pd.to_datetime(
        dates.dt.strftime("%Y-%m-%d") + " " + time_str, errors="coerce"
    )
    log["date_range"] = [str(dates.min().date()), str(dates.max().date())]
    year_counts = dates.dt.year.value_counts().sort_index()
    log["rows_per_year"] = {str(k): int(v) for k, v in year_counts.items()}

    # --- Duplicates -----------------------------------------------------------
    before = len(df)
    df = df.drop_duplicates()
    df = df.drop_duplicates(subset=["collision_id"], keep="first")
    log["duplicate_rows_dropped"] = before - len(df)

    # --- Text columns: trim whitespace, normalize dtype, keep NaN as NaN -----
    for col in TEXT_COLS:
        df[col] = df[col].apply(lambda v: str(v).strip() if pd.notna(v) else pd.NA)
        df[col] = df[col].replace({"": pd.NA, "nan": pd.NA})

    # --- Borough / zip: leave missing as missing (do not guess) --------------
    missing_borough = df["borough"].isna().sum()
    missing_zip = df["zip_code"].isna().sum()
    recoverable_via_geocoding = int(
        (df["borough"].isna() & df["latitude"].notna() & df["longitude"].notna()).sum()
    )
    df["zip_code"] = df["zip_code"].apply(
        lambda v: str(int(v)) if pd.notna(v) else pd.NA
    )
    log["missing_borough"] = int(missing_borough)
    log["missing_zip_code"] = int(missing_zip)
    log["borough_missing_but_recoverable_via_lat_long"] = recoverable_via_geocoding

    # --- Coordinates: null out (0,0)/out-of-bounds, add a usability flag -----
    bad_coord = (
        df["latitude"].notna()
        & df["longitude"].notna()
        & (
            (df["latitude"] < NYC_LAT_RANGE[0]) | (df["latitude"] > NYC_LAT_RANGE[1])
            | (df["longitude"] < NYC_LON_RANGE[0]) | (df["longitude"] > NYC_LON_RANGE[1])
        )
    )
    log["invalid_coordinates_nulled"] = int(bad_coord.sum())
    df.loc[bad_coord, ["latitude", "longitude", "location"]] = np.nan
    df["has_valid_location"] = df["latitude"].notna() & df["longitude"].notna()

    # --- Injury/fatality counts: force numeric, missing -> 0 (assumption) ----
    for col in COUNT_COLS:
        missing = df[col].isna().sum()
        if missing:
            log.setdefault("count_columns_filled_with_zero", {})[col] = int(missing)
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    # --- Sparse-by-design columns: leave untouched, just document ------------
    log["sparse_by_design_columns"] = FACTOR_COLS[1:] + VEHICLE_COLS[1:]

    col_order = [
        "collision_id", "crash_date", "crash_time", "crash_datetime",
        "borough", "zip_code", "latitude", "longitude", "has_valid_location", "location",
        "on_street_name", "cross_street_name", "off_street_name",
        *COUNT_COLS, *FACTOR_COLS, *VEHICLE_COLS,
    ]
    df = df[[c for c in col_order if c in df.columns]]

    log["output_rows"] = len(df)
    log["output_columns"] = len(df.columns)
    return df, log


def main():
    if len(sys.argv) != 3:
        print("Usage: python clean_crash_data.py <input.xlsx|csv> <output_prefix>")
        sys.exit(1)
    in_path, out_prefix = sys.argv[1], sys.argv[2]

    df = pd.read_csv(in_path) if in_path.endswith(".csv") else pd.read_excel(in_path)
    cleaned, log = clean_crash_data(df)

    cleaned.to_csv(f"{out_prefix}.csv", index=False)
    with open(f"{out_prefix}_log.json", "w") as f:
        json.dump(log, f, indent=2)

    print(json.dumps(log, indent=2))


if __name__ == "__main__":
    main()
