# The borough bar chart drops 40% of NYC's traffic deaths

An analysis of NYC's Motor Vehicle Collisions data (Socrata `h9gi-nx95`, 2,269,187 crashes,
July 2012 to June 2026), plus the dashboard that shows its work.

> **Status: in progress.** The finding below is measured and verified. The dashboard and the
> borough recovery are being built. See [the roadmap](#roadmap).

## The finding

Almost every NYC crash dashboard opens with a bar chart of crashes by borough. That chart
silently drops every row where NYPD did not record a borough. Measured against the full
table:

| | rows | deaths | fatality rate |
|---|---|---|---|
| Borough **labeled** | 1,577,812 | 2,176 | 1.379 per 1,000 |
| Borough **NULL** | 691,375 (30.5%) | 1,441 | **2.084 per 1,000** |
| | | **39.8% of all deaths** | **1.51x deadlier** |

The unlabeled crashes are not random. Their top streets are the Belt Parkway (13,399),
the Long Island Expressway (9,777), the BQE (9,646), Grand Central Parkway (8,431), FDR
Drive (7,264), the Cross Bronx (6,040), and the Major Deegan (5,819). Limited-access
highways, sitting outside the precinct street-grid geocoding that assigns a borough.

So the standard chart is not merely incomplete. It is **biased toward surface streets**,
and it discards the roads where crashes are most likely to kill someone.

Most of those rows carry usable latitude and longitude, which means the borough can be
recovered by a point-in-polygon join against NYC borough boundaries. That recovery, and
its accuracy check, is what this repo is being built to do.

### What is NOT claimed yet

- **The recovery yield is unmeasured.** Counting rows that *have coordinates* is not the
  same as counting rows that *match a polygon*. Shoreline-clipped boundaries drop
  water-adjacent highway rows, which is exactly the population being recovered. The real
  number goes here once the join runs.
- **The method is unvalidated until the agreement check passes.** 1,533,614 rows carry both
  a reported borough and usable coordinates. Running the same join on those gives an
  agreement rate. If it comes back below ~90%, the coordinate reference system or axis
  order is wrong, not the method. That check gates the finding.

## Prior work

The single-road version of this observation is already published.
[AEE Law](https://aeelaw.com/data/belt-parkway-crash-data/) noted that "the borough field is
blank for 98.7 percent of Belt Parkway rows... almost certainly a geocoding gap for a
limited-access highway," and declined to go further.
[Aleksey Bilogur's 2016 notebook](https://github.com/ResidentMario/motor-vehicle-collisions)
counted 184,301 missing boroughs and listed geocoding recovery as an approach he did not
implement.

The citywide quantification, the fatality differential, and the recovery are the parts that
were not done.

## The bug in my first pull

My first attempt at this dataset pulled 8,000 rows and **7,146 of them (89%) were from
2021**. Not a sampling choice: the request had no `$order` clause, and Socrata returns rows
in storage order, so `$limit=8000` grabbed the first 8,000 rows as stored rather than a
sample of anything. Every time-based chart built on that file was meaningless.

The fix is one parameter. The lesson is that a plausible-looking file is not a valid one,
and the only reason I caught it was plotting a year histogram before trusting the data.

That file is still in `data/raw/sample_8k_skewed.csv` (gitignored) as the before-picture.

## Data

**Source:** [NYC Open Data, Motor Vehicle Collisions - Crashes](https://data.cityofnewyork.us/Public-Safety/Motor-Vehicle-Collisions-Crashes/h9gi-nx95)

**Snapshot:** data through 2026-06-11. The upstream feed's `rowsUpdatedAt` is 2026-06-15, so
NYC's own updater is behind. Charts ending in June 2026 are correct, not broken.

**Known quality issues, all handled in `scripts/clean_crash_data.py`:**
- Borough missing on 30.5% of rows (the finding above)
- Coordinates missing or `(0,0)` on a further slice; these are nulled, not guessed
- Street names arrive with inconsistent trailing whitespace, so `"BELT PARKWAY"` appears as
  two distinct values (13,399 padded and 6,889 unpadded). A naive "top dangerous streets"
  chart double-counts it.
- The API omits null keys entirely, so paginated chunks have ragged column sets

## Setup

```bash
py -m venv venv
venv\Scripts\activate          # Windows;  source venv/bin/activate elsewhere
py -m pip install -r requirements.txt -r requirements-dev.txt
copy .env.example .env         # then paste your NYC Open Data app token
streamlit run app/streamlit_app.py
```

Note: on this machine Python is reachable as `py`, not `python`. The `python` on PATH is the
Microsoft Store stub. `py` is used in docs only, never inside a script or CI workflow
(GitHub Actions runners have no `py` launcher).

## Roadmap

| Stage | Status |
|---|---|
| Repo scaffold, deployable placeholder app | **done** |
| `pull_data.py`, stable-ordered multi-year pull | in progress |
| Cleaner hardened for API dtypes and ragged chunks | in progress |
| Borough recovery + agreement check (build gate) | not started |
| Nine charts: line, categorical, heatmaps, scatter | not started |
| Live on Streamlit Community Cloud | not started |

## License

Data is public, published by the City of New York. Code is MIT.
