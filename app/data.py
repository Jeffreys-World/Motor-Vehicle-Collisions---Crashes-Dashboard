"""
Data access. One seam between the app and whatever is backing it.

The app is being built before the real pull exists, so the source is resolved at
runtime rather than hardcoded:

    data/processed/crashes.parquet   -> PRODUCTION. The real multi-year pull.
    data/raw/sample_8k_skewed.csv    -> DEV FIXTURE. Right schema, garbage numbers.
    (neither)                        -> NO_DATA. App renders the finding only.

Swapping to real data at the end is therefore a file appearing, not a code change.

    ┌──────────────────┐
    │ resolve_source() │──► Source(kind, reader, label, trustworthy)
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐   base_view.sql   ┌───────────────────┐
    │ get_connection() │──────────────────►│ crashes_filtered  │
    │ (st.cache_res.)  │  $source bound     │  (shared view)    │
    └──────────────────┘                    └─────────┬─────────┘
                                                      │
                                      every chart query selects from here

WHY the dev fixture is not trustworthy: it is 8,000 rows of which 7,146 (89%)
are from 2021, because the original Socrata request carried no $order and got
storage-order rows. Its schema is correct; its distributions are meaningless.
`Source.trustworthy` is False for it, and the UI must surface that. Never publish
a number computed from it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import duckdb
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
SQL_DIR = ROOT / "sql"

PARQUET = ROOT / "data" / "processed" / "crashes.parquet"
FIXTURE = ROOT / "data" / "raw" / "sample_8k_skewed.csv"

# Static by design. Never fetch rowsUpdatedAt at runtime and never render a
# counter that grows over time — it becomes an abandonment signal on a link
# somebody opens months from now.
DATA_THROUGH = "2026-06-11"
PULLED_ON = "2026-08-08"


@dataclass(frozen=True)
class Source:
    kind: str            # "parquet" | "fixture" | "none"
    reader: str          # a DuckDB table function, or "" when kind == "none"
    label: str           # human-readable, shown in the UI
    trustworthy: bool    # False means: render, but never let a number be quoted


def resolve_source() -> Source:
    if PARQUET.exists():
        return Source("parquet", f"read_parquet('{PARQUET.as_posix()}')",
                      "full multi-year pull", True)
    if FIXTURE.exists():
        return Source("fixture", f"read_csv_auto('{FIXTURE.as_posix()}')",
                      "8,000-row development fixture", False)
    return Source("none", "", "no data file present", False)


@st.cache_resource(show_spinner=False)
def get_connection(reader: str) -> duckdb.DuckDBPyConnection:
    """One in-process DuckDB connection, reused across Streamlit reruns.

    Keyed on `reader` so dropping the real Parquet in rebuilds the view instead
    of silently serving the fixture from a stale cache.
    """
    con = duckdb.connect(database=":memory:")
    # Two names on purpose. `crashes_base` wraps the reader; `crashes_raw` adds
    # the recovery columns on top. Defining crashes_raw in terms of itself is a
    # self-reference DuckDB rejects with "infinite recursion detected".
    con.execute(f"CREATE OR REPLACE VIEW crashes_base AS SELECT * FROM {reader}")
    _ensure_recovery_columns(con)
    return con


def _ensure_recovery_columns(con: duckdb.DuckDBPyConnection) -> None:
    """Make the schema stable whether or not the borough recovery has run yet.

    The recovery adds `borough_recovered` and `borough_source`. Until it does,
    synthesise them so every downstream query is valid: `reported` where NYPD
    gave us a borough, NULL where it did not. Nothing is invented — a row with
    no borough stays unlabeled, which is the honest state and the finding itself.
    """
    cols = {r[0] for r in con.execute("DESCRIBE crashes_base").fetchall()}
    if "borough_source" in cols:
        con.execute("CREATE OR REPLACE VIEW crashes_raw AS SELECT * FROM crashes_base")
        return
    con.execute(
        """
        CREATE OR REPLACE VIEW crashes_raw AS
        SELECT *,
               borough AS borough_recovered,
               CASE WHEN borough IS NOT NULL THEN 'reported' END AS borough_source
        FROM crashes_base
        """
    )


def read_sql(name: str) -> str:
    return (SQL_DIR / f"{name}.sql").read_text(encoding="utf-8")


def date_bounds(con: duckdb.DuckDBPyConnection) -> tuple[date, date]:
    """Bounds come from the DATA, never from today().

    The upstream feed stopped at 2026-06-11. A picker defaulting to "last 30
    days" would return zero rows and read as a broken app.
    """
    lo, hi = con.execute(
        "SELECT min(crash_date), max(crash_date) FROM crashes_raw"
    ).fetchone()
    return lo, hi


def build_view(con: duckdb.DuckDBPyConnection, date_from: date, date_to: date) -> None:
    """(Re)create `crashes_filtered` for the user's date range.

    The dates go through a one-row `filter_params` table rather than into the
    view's SQL text. DuckDB refuses to prepare a CREATE VIEW statement, and
    string-formatting user input into SQL is the injection seam we are avoiding.
    INSERT *can* be prepared, so the values stay bound.
    """
    con.execute("CREATE TABLE IF NOT EXISTS filter_params (date_from DATE, date_to DATE)")
    con.execute("DELETE FROM filter_params")
    con.execute("INSERT INTO filter_params VALUES (?, ?)", [date_from, date_to])
    con.execute(read_sql("base_view"))


@st.cache_data(show_spinner=False)
def query(_con: duckdb.DuckDBPyConnection, name: str, cache_key: tuple):
    """Run a named chart query against the shared view.

    `_con` is underscore-prefixed so Streamlit does not try to hash the
    connection. `cache_key` carries the values that actually change the result
    (source + date range), so the cache invalidates when they do.
    """
    return _con.execute(read_sql(name)).df()
