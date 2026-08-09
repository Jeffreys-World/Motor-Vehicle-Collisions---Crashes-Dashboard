"""
NYC crash dashboard. The charts are evidence for a claim, not a gallery.

The claim: the borough bar chart that opens almost every NYC crash dashboard
silently drops 30.5% of crashes and 39.8% of the deaths, because unlabeled rows
concentrate on limited-access highways outside precinct street-grid geocoding.

Data source is resolved at runtime by app/data.py, so connecting the real pull
later is a file appearing rather than a code change. Until then the app runs on a
development fixture and says so loudly — see the NOT-REAL-DATA banner.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data import (DATA_THROUGH, PULLED_ON, build_view, date_bounds,
                  get_connection, query, resolve_source)

st.set_page_config(page_title="NYC crash data: the borough gap",
                   page_icon="🚦", layout="wide")

# Muted, colour-blind-safe. Unlabeled is deliberately the loudest colour: it is
# the subject of the project, not a residual category.
C_CRASH, C_INJURY, C_DEATH = "#4C78A8", "#F58518", "#B4232C"
C_UNLABELED, C_LABELED = "#B4232C", "#7F9DB9"

src = resolve_source()

# ---------------------------------------------------------------- no data yet
if src.kind == "none":
    st.title("The borough bar chart drops 40% of NYC's traffic deaths")
    st.error("No data file found. Run `py scripts/pull_data.py` to build "
             "`data/processed/crashes.parquet`.", icon="🗄️")
    st.stop()

con = get_connection(src.reader)
lo, hi = date_bounds(con)

# ------------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("Filters")
    # Bounds derive from the DATA, never from today(), so a range that returns
    # zero rows cannot be selected.
    picked = st.date_input(
        "Date range", value=(lo, hi), min_value=lo, max_value=hi,
        help=f"Data covers {lo:%Y-%m-%d} to {hi:%Y-%m-%d}. Bounds come from the "
             f"data, not from today.",
    )
    # st.date_input in range mode returns a 1-TUPLE between the first and second
    # click. Unpacking straight into two names raises
    # "ValueError: not enough values to unpack (expected 2, got 1)" and replaces
    # the whole dashboard with a traceback — on the first click of the only
    # filter in the app. Normalise the shape BEFORE unpacking, not after.
    if isinstance(picked, (list, tuple)):
        if len(picked) >= 2:
            date_from, date_to = picked[0], picked[1]
        elif len(picked) == 1:
            date_from = date_to = picked[0]   # mid-selection: show that one day
        else:
            date_from, date_to = lo, hi       # cleared: fall back to full range
    else:
        date_from = date_to = picked          # single date object
    st.caption(f"Source: {src.label}")

build_view(con, date_from, date_to)
key = (src.kind, str(date_from), str(date_to))

kpi = query(con, "kpis", key).iloc[0]

# ----------------------------------------------------------------- the claim
st.title("The borough bar chart drops 40% of NYC's traffic deaths")
st.caption(f"Snapshot: data through {DATA_THROUGH}, pulled {PULLED_ON}. "
           f"NYC's feed was last updated 2026-06-15.")

if not src.trustworthy:
    st.error(
        f"**Running on the {src.label}, not real data.** Every number on this page "
        "is a placeholder: 89% of these rows are from 2021 because the original "
        "API pull had no `$order` clause. The layout is real; the numbers are not. "
        "Do not quote anything here.", icon="⚠️",
    )

if kpi.crashes == 0:
    st.warning("No crashes in this date range. Widen it in the sidebar.", icon="📭")
    st.stop()

unlabeled_share = kpi.unlabeled_crashes / kpi.crashes
death_share = (kpi.unlabeled_killed / kpi.killed) if kpi.killed else 0.0

a, b, c, d = st.columns(4)
a.metric("Crashes", f"{int(kpi.crashes):,}")
b.metric("Injured", f"{int(kpi.injured):,}")
c.metric("Killed", f"{int(kpi.killed):,}")
d.metric("Deaths in unlabeled rows", f"{death_share:.1%}",
         f"{int(kpi.unlabeled_killed):,} of {int(kpi.killed):,}",
         delta_color="inverse")

st.divider()

# ------------------------------------------------------- 1. borough, the point
st.subheader("1. Crashes by borough, with the dropped rows shown")
bor = query(con, "borough", key)
st.markdown(
    f"**{int(kpi.unlabeled_crashes):,} crashes ({unlabeled_share:.1%}) carry no borough.** "
    "Most dashboards drop them silently. Here they are the first bar."
)
fig = px.bar(bor, x="borough", y="crashes",
             color=bor.is_unlabeled.map({True: "No borough recorded", False: "Borough recorded"}),
             color_discrete_map={"No borough recorded": C_UNLABELED,
                                 "Borough recorded": C_LABELED},
             labels={"crashes": "Crashes", "borough": "", "color": ""})
fig.update_layout(height=380, legend_title_text="", margin=dict(t=10))
st.plotly_chart(fig, use_container_width=True)

lab = bor[~bor.is_unlabeled]
unl = bor[bor.is_unlabeled]
if not unl.empty and lab.crashes.sum():
    r_unl = unl.killed.sum() / unl.crashes.sum() * 1000
    r_lab = lab.killed.sum() / lab.crashes.sum() * 1000
    st.caption(f"Fatality rate: **{r_unl:.2f}** per 1,000 unlabeled crashes vs "
               f"**{r_lab:.2f}** labeled — {r_unl / r_lab:.2f}x. "
               "The dropped rows are the deadlier ones.")

# ------------------------------------------------- 2. why they go missing
st.subheader("2. Why those rows have no borough")
streets = query(con, "unlabeled_streets", key)
if streets.empty:
    st.info("No unlabeled rows with a street name in this range.")
else:
    fig = px.bar(streets.sort_values("crashes"), x="crashes", y="street",
                 orientation="h", labels={"crashes": "Crashes", "street": ""})
    fig.update_traces(marker_color=C_UNLABELED)
    fig.update_layout(height=380, margin=dict(t=10))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Limited-access highways, which sit outside the precinct street "
               "grid that assigns a borough. The gap is structural, not random.")

st.divider()

# --------------------------------------------- 3-4. the honest trend charts
st.subheader("3. Crashes, injuries and deaths do not move together")
yr = query(con, "trend_yearly", key)
if len(yr) > 1:
    base = yr.iloc[0]
    idx = pd.DataFrame({
        "year": yr.year,
        "Crashes": yr.crashes / base.crashes * 100,
        "Injured": yr.injured / base.injured * 100 if base.injured else 0,
        "Killed": yr.killed / base.killed * 100 if base.killed else 0,
    }).melt("year", var_name="series", value_name="index")
    fig = px.line(idx, x="year", y="index", color="series", markers=True,
                  color_discrete_map={"Crashes": C_CRASH, "Injured": C_INJURY,
                                      "Killed": C_DEATH},
                  labels={"index": f"Indexed to {int(base.year)} = 100",
                          "year": "", "series": ""})
    fig.add_hline(y=100, line_dash="dot", line_color="#999")
    fig.update_layout(height=380, margin=dict(t=10))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("A crash-volume line alone invites 'the streets got safer'. Indexing "
               "all three against the same baseline shows reported crashes falling "
               "far faster than deaths, which points at reporting, not safety.")
else:
    st.info("Need more than one year in range to show a trend.")

st.subheader("4. Monthly volume")
mon = query(con, "trend_monthly", key)
fig = px.line(mon, x="month", y=["crashes", "injured"],
              color_discrete_sequence=[C_CRASH, C_INJURY],
              labels={"value": "Count", "month": "", "variable": ""})
fig.update_layout(height=320, margin=dict(t=10))
st.plotly_chart(fig, use_container_width=True)

st.divider()

# ------------------------------------------------------ 5-6. categorical
left, right = st.columns(2)
with left:
    st.subheader("5. Contributing factors")
    fac = query(con, "factors", key)
    fig = px.bar(fac.sort_values("crashes"), x="crashes", y="factor",
                 orientation="h", labels={"crashes": "Crashes", "factor": ""})
    fig.update_traces(marker_color=C_CRASH)
    fig.update_layout(height=420, margin=dict(t=10))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("'Unspecified' is consistently near the top. Another place this "
               "dataset records an absence rather than a cause.")

with right:
    st.subheader("6. Who gets hurt")
    vic = query(con, "victims", key)
    fig = go.Figure()
    fig.add_bar(name="Injured", x=vic.victim_type, y=vic.injured, marker_color=C_INJURY)
    fig.add_bar(name="Killed", x=vic.victim_type, y=vic.killed, marker_color=C_DEATH)
    fig.update_layout(barmode="group", height=420, margin=dict(t=10),
                      yaxis_type="log", yaxis_title="Count (log scale)")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Log scale: deaths are ~0.16% of crashes, so a linear axis renders "
               "the fatality bars invisible.")

st.divider()

# ---------------------------------------------------------- 7. day x hour
st.subheader("7. When crashes happen")
heat = query(con, "heat_day_hour", key)
if heat.empty:
    st.info("No timestamped crashes in this range.")
else:
    piv = (heat.pivot_table(index="dayname", columns="hour",
                            values="crashes", aggfunc="sum")
                .reindex(["Monday", "Tuesday", "Wednesday", "Thursday",
                          "Friday", "Saturday", "Sunday"]))
    fig = px.imshow(piv, aspect="auto", color_continuous_scale="Blues",
                    labels=dict(x="Hour", y="", color="Crashes"))
    fig.update_layout(height=360, margin=dict(t=10))
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------- 8-9. geography
st.subheader("8. Where crashes cluster")
geo = query(con, "geo_density", key)
if geo.empty:
    st.info("No crashes with usable coordinates in this range.")
else:
    fig = px.scatter_map(geo, lat="lat_bin", lon="lon_bin", size="crashes",
                         color="crashes", color_continuous_scale="YlOrRd",
                         zoom=9, height=520, map_style="carto-positron",
                         hover_data={"crashes": True, "killed": True})
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Binned to ~100m cells ({len(geo):,} cells), not raw points. "
               "Plotting every crash individually hangs the browser.")

st.subheader("9. Severity outliers")
sev = query(con, "severity", key)
if sev.empty:
    st.info("No crashes with usable coordinates and casualties in this range.")
else:
    sev = sev.assign(outcome=lambda d: d.killed.gt(0).map({True: "Fatal", False: "Injury only"}))
    fig = px.scatter(sev, x="crash_date", y="injured", color="outcome", size="injured",
                     color_discrete_map={"Fatal": C_DEATH, "Injury only": C_LABELED},
                     hover_data=["street", "borough", "killed"],
                     labels={"injured": "People injured", "crash_date": "", "outcome": ""})
    fig.update_layout(height=400, margin=dict(t=10))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Every fatal crash, plus a bounded sample of injury-only crashes. "
               "An unweighted sample would render almost no fatalities.")

st.divider()
st.caption("Source: NYC Open Data, Motor Vehicle Collisions - Crashes "
           "(Socrata h9gi-nx95). Code: github.com/Jeffreys-World/"
           "Motor-Vehicle-Collisions---Crashes-Dashboard")
