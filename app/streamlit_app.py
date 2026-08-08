"""
NYC crash dashboard — Phase 1 placeholder.

Deliberately reads NO data file and makes NO network call. It exists so the
Streamlit Community Cloud deploy is proven working before the pipeline lands
(design decision 16). Chart branches stack on each other until the Parquet
schema is frozen and committed once; merging one early would put a
FileNotFoundError on the public URL.

    PHASE 1 (here)          PHASE 2-3                    PHASE 4-7
    ┌──────────────┐        ┌──────────────────┐         ┌──────────────┐
    │ finding only │  ───▶  │ pull → clean →   │  ───▶   │ 9 charts     │
    │ no data read │        │ join → FREEZE →  │         │ read parquet │
    └──────────────┘        │ one parquet commit│        └──────────────┘
                            └──────────────────┘
"""

import streamlit as st

# Measured against the full Socrata table h9gi-nx95 on 2026-08-08 via the
# aggregation API, not from a local file. Once the pipeline lands these move
# into data/processed/finding_aggregate.csv and are read, not hardcoded.
TOTAL_ROWS = 2_269_187
LABELED_ROWS, LABELED_DEATHS = 1_577_812, 2_176
NULL_ROWS, NULL_DEATHS = 691_375, 1_441
# Labeled AND coordinates inside the NYC bbox. This is the agreement-check
# denominator. It is NOT 1,577,812 — that figure is labeled rows regardless of
# coordinates, and conflating the two is a mistake this project made twice.
VALIDATION_SET = 1_533_614

# Static by design. Never fetch rowsUpdatedAt at runtime, and never render a
# counter that grows over time — it turns into an abandonment signal.
DATA_THROUGH = "2026-06-11"
PULLED_ON = "2026-08-08"

st.set_page_config(page_title="NYC crash data: the borough gap", page_icon="🚦", layout="wide")

st.title("The borough bar chart drops 40% of NYC's traffic deaths")
st.caption(
    f"Snapshot: data through {DATA_THROUGH}, pulled {PULLED_ON}. "
    f"NYC's own feed was last updated 2026-06-15."
)

st.warning(
    "**Phase 1.** The finding below is measured and verified. The dashboard is being built. "
    "This page reads no data file yet, on purpose.",
    icon="🚧",
)

labeled_rate = LABELED_DEATHS / LABELED_ROWS * 1_000
null_rate = NULL_DEATHS / NULL_ROWS * 1_000

c1, c2, c3 = st.columns(3)
c1.metric("Crashes with no borough label", f"{NULL_ROWS:,}", f"{NULL_ROWS/TOTAL_ROWS:.1%} of all crashes")
c2.metric("Their share of all traffic deaths", f"{NULL_DEATHS/(NULL_DEATHS+LABELED_DEATHS):.1%}", f"{NULL_DEATHS:,} deaths")
c3.metric("Fatality rate vs labeled crashes", f"{null_rate/labeled_rate:.2f}x", f"{null_rate:.2f} vs {labeled_rate:.2f} per 1,000")

st.markdown(
    f"""
Almost every NYC crash dashboard opens with a bar chart of crashes by borough. That chart
silently drops every row where NYPD recorded no borough — **{NULL_ROWS:,} crashes, {NULL_ROWS/TOTAL_ROWS:.1%}
of the table.**

Those rows are not random. Their top streets are the Belt Parkway, the Long Island
Expressway, the BQE, Grand Central Parkway, FDR Drive, the Cross Bronx and the Major
Deegan: limited-access highways, outside the precinct street-grid geocoding that assigns a
borough. So the standard chart is not just incomplete, it is **biased toward surface
streets**, and it discards the roads where a crash is most likely to kill someone.

Most of those rows carry usable coordinates, so the borough can be recovered with a
point-in-polygon join. That recovery, and the accuracy check that has to pass before any
recovered number is published, is what this project is being built to do.
"""
)

with st.expander("What is not claimed yet"):
    st.markdown(
        f"""
- **The recovery yield is unmeasured.** Counting rows that *have coordinates* is not the
  same as counting rows that *match a polygon*. Shoreline-clipped boundaries drop
  water-adjacent highway rows, which is exactly the population being recovered.
- **The method is unvalidated until the agreement check passes.** {VALIDATION_SET:,}
  rows carry both a reported borough and usable coordinates. Running the same join on those
  yields an agreement rate. Below ~90% means the coordinate reference system or axis order
  is wrong, not that the method is weak. That check gates the finding.
"""
    )

st.divider()
st.caption(
    "Source: NYC Open Data, Motor Vehicle Collisions - Crashes (Socrata h9gi-nx95), "
    f"{TOTAL_ROWS:,} crashes, July 2012 to June 2026."
)
