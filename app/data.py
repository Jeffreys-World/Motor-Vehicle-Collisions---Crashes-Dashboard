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
#
# UPSTREAM_THROUGH describes the SOURCE dataset, not what this app ships. Do not
# show it as the app's coverage: the shipped slice is 2019-2025, so a header
# reading "data through 2026-06-11" over charts that stop in 2025 is simply
# false. Coverage is derived from the data itself (see date_bounds).
# Found by /qa on 2026-08-09 (ISSUE-002).
UPSTREAM_THROUGH = "2026-06-11"
UPSTREAM_UPDATED = "2026-06-15"
PULLED_ON = "2026-08-08"

# The full-table (2012-2026) share of deaths that fall in unlabeled rows — the
# figure the headline's "40%" rounds. Static by design: it describes the SOURCE
# table, not the shipped 2019-2025 slice. Only ever COMPARED against the live
# per-range figure, never presented as describing what is on screen.
FULL_TABLE_DEATH_SHARE = 0.398

# Below this, the two figures are called equal rather than ranked. Half a
# percentage point: narrow enough that a real gap still reads as a gap, wide
# enough that float noise never flips the wording.
GAP_EQUAL_TOLERANCE = 0.005


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


def normalize_date_range(picked, lo, hi):
    """Coerce whatever st.date_input returns into exactly (date_from, date_to).

    Extracted so it can be tested without a browser. In range mode
    st.date_input returns a 1-TUPLE between the first and second click, and
    unpacking that straight into two names raises

        ValueError: not enough values to unpack (expected 2, got 1)

    which replaced the entire dashboard with a traceback on the first click of
    the only filter in the app. Found by /qa on 2026-08-09.

        two dates  -> (a, b)
        one date   -> (a, a)     mid-selection: show that single day
        cleared    -> (lo, hi)   fall back to the full range
        bare date  -> (d, d)
    """
    if isinstance(picked, (list, tuple)):
        if len(picked) >= 2:
            return picked[0], picked[1]
        if len(picked) == 1:
            return picked[0], picked[0]
        return lo, hi
    if picked is None:
        return lo, hi
    return picked, picked


def gap_direction(death_share: float,
                  full_table_share: float = FULL_TABLE_DEATH_SHARE,
                  tolerance: float = GAP_EQUAL_TOLERANCE) -> str:
    """Which way the selected range's death gap runs against the full table.

    Extracted so it can be tested without a browser, the same reason
    normalize_date_range lives here: streamlit_app.py executes at module scope,
    so a test cannot import anything defined in it.

    The page used to STATE the direction — "the range shown here is narrower,
    and the gap is wider in it" — directly above the live figure. That sentence
    is false on 40% of month-length ranges, on half of all single days, and on
    the whole of 2025 (31.0% against 39.8%). A hardcoded directional claim
    inches from the number that contradicts it is precisely the bug the caption
    was written to fix (ISSUE-001). Found by /qa on 2026-08-09.

    Returns the words, not a sign, so the call site cannot re-introduce the
    claim by mapping the sign back to prose incorrectly.
    """
    gap = death_share - full_table_share
    if abs(gap) < tolerance:
        return "about the same in the range shown here"
    return ("wider in the range shown here" if gap > 0
            else "narrower in the range shown here")


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
