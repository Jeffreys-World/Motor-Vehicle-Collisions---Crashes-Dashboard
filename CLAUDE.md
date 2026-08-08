# Instructions for Claude Code

This repo builds an NYC Motor Vehicle Collisions dashboard whose point is a finding, not a
chart gallery: **the standard borough bar chart drops 30.5% of crashes and 39.8% of NYC's
traffic deaths.** The full design, including 17 numbered decisions from a CEO review, an
eng review, and two outside-voice passes, lives in
`~/.gstack/projects/Jeffreys-World-GitHub/jeffrey-main-design-20260808-094610.md`.
Read it before writing code.

This repo will be shown to hiring managers, so process and documentation matter as much as
the working code.

## Non-negotiables

These came out of review and reversing them silently would undo real work.

1. **The point-in-polygon join runs OFFLINE.** `borough_recovered` and `borough_source` are
   baked into the committed Parquet. The deployed app needs no spatial extension, no
   geopandas, and no network call. Never add geo dependencies to `requirements.txt`.
2. **Never overwrite `borough` in place.** Recovered values go in `borough_recovered` with
   `borough_source` in (`reported`, `recovered`, `unrecoverable`). Overwriting would repeat
   the exact sin this project documents.
3. **The agreement check is a build gate, not a statistic.** Run the join on the 1,533,614
   rows that have both a reported borough and coordinates. Expect high-90s%. Below ~90%
   means the CRS or axis order is wrong (DCP shapefile is EPSG:2263 in feet, the Open Data
   GeoJSON is EPSG:4326; `Point` takes `(lon, lat)`), not that the method is weak. Do not
   write down any recovery number until this passes.
4. **Use the paginated `.csv` resource endpoint, never the bulk export.** The bulk
   `rows.csv?accessType=DOWNLOAD` returns a different schema: uppercase, space-separated,
   `MM/DD/YYYY` dates. Pagination is fine; `$offset=2,200,000` returns in about a second.
5. **Every request carries `$order=crash_date`.** Without a stable sort, Socrata pagination
   repeats and drops rows. This is the bug that produced the 89%-one-year sample.
6. **Reindex every chunk to an expected column list at the pull boundary.** The API omits
   null keys entirely, so chunks arrive with different column sets.
7. **Report the recovery as a three-way slice** (reported / recovered-surface-street /
   recovered-highway). Collapsing it into one corrected ranking makes the chart rank
   boroughs partly by highway mileage, which is not what a reader thinks they are seeing.
8. **The freshness line is static.** "Data through 2026-06-11, pulled 2026-08-08." Never
   fetch `rowsUpdatedAt` at runtime, and never render a counter that grows over time.

## Git workflow

- Commit every logical change: the smallest change that leaves the repo working.
- Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
- Commit bodies explain **why**, not what. The diff already shows what.
- Never commit `.env`, tokens, or `data/raw/`.
- **Sequencing (design decision 16):** `pull -> clean -> polygon join -> schema frozen ->
  ONE Parquet commit -> then chart branches`. Streamlit auto-redeploys on every push to
  `main`, so a chart branch merged before the Parquet exists puts a `FileNotFoundError` on
  the public URL. Until the Parquet lands, stack chart branches on each other.
- Every re-bake of the Parquet is another permanent ~35 MB blob in history. Freeze the
  schema first.
- Tag the finished state `v1.0`.

## Python on this machine

- Python 3.12 is reachable as **`py`**, not `python`. The `python` on PATH is the Microsoft
  Store stub that prints an install message and exits.
- **Never write `py` inside a script, Makefile, or GitHub Actions workflow.** Ubuntu runners
  have no `py` launcher. README prose only.
- This network intercepts TLS: `uv` needs `--system-certs` (or `UV_SYSTEM_CERTS=1`) to reach
  PyPI. `curl` to the Socrata API is unaffected.

## Testing

Run: `py -m pytest`

- **Assert against committed aggregates, not sampled rows.** Deaths are 0.16% of the table,
  so any fixture small enough to commit has near-zero deaths and the 1.51x ratio becomes
  noise. The pipeline emits `data/processed/finding_aggregate.csv` (a few KB) and tests
  assert on that.
- The year-skew regression test asserts over the committed `rows_per_year` log, not a live
  pull. Keep a live-pull version as a manual script.
- **CRITICAL regression test:** `clean_crash_data.py` must not silently drop
  `borough_recovered` / `borough_source`. Its `col_order` filter is an allowlist and now
  raises on unexpected columns rather than dropping them.
- Write a test for both paths of every new conditional. Write a regression test for every
  bug fixed.

## Known bugs in the existing cleaner

`scripts/clean_crash_data.py` was written against an 8,000-row Excel sample and has three
bugs on the real API path. Fix them before the first full pull:

1. **Latitude/longitude are never coerced to numeric.** Only `COUNT_COLS` gets
   `pd.to_numeric`. The API returns numerics as strings, so the bbox comparison is
   `str < float` on object dtype: TypeError.
2. **Ragged chunks.** See non-negotiable 6.
3. **Ordering bug.** `borough_missing_but_recoverable_via_lat_long` is computed *before*
   bad coordinates are nulled, so the headline recoverable count currently includes `(0,0)`
   rows. Move it after the scrub and regenerate every number that depends on it.

## Skill routing

When the user's request matches an available skill, invoke it via the Skill tool. When in
doubt, invoke the skill.

- Product ideas/brainstorming -> /office-hours
- Strategy/scope -> /plan-ceo-review
- Architecture -> /plan-eng-review
- Bugs/errors -> /investigate
- QA/testing site behavior -> /qa or /qa-only
- Code review/diff check -> /review
- Visual polish -> /design-review
- Ship/deploy/PR -> /ship or /land-and-deploy
