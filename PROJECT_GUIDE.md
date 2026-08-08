# Project guide: repo creation → final execution

Structured around repeated **branch → commit → push → Pull Request → merge**
cycles on purpose — the goal here is as much GitHub practice as it is a
finished dashboard. Each phase below names the skill it's rehearsing.

---

## Phase 1 — Create the repo on GitHub
*Skill: repo creation*

1. github.com → **New repository**
2. Name it (e.g. `nyc-crash-dashboard`), add a short description, choose Public (good for a portfolio) or Private.
3. Leave "Initialize with README / .gitignore / license" **unchecked** — you already have these, and checking them creates a conflicting first commit you'd have to merge before you could push.
4. Copy the HTTPS clone URL from the green **Code** button.

## Phase 2 — Clone it and make your first commit
*Skill: clone, status, add, commit, push*

```bash
git clone https://github.com/Jeffreys-World/Motor-Vehicle-Collisions---Crashes-Dashboard.git
cd Motor-Vehicle-Collisions---Crashes-Dashboard
```
Unzip the project scaffold I gave you into this folder (or drag the files into it in VS Code) so `scripts/`, `app/`, `data/`, etc. all land inside the cloned repo.

```bash
git status                 # everything shows as untracked - this is what "new files" looks like to git
git add .
git commit -m "Initial commit: project scaffold (scripts, app stub, docs)"
git push -u origin main
```
Refresh the GitHub page — your files are live.

## Phase 3 — Local environment
*Not a git step, but required before anything below works*

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # paste your NYC Open Data app token in
streamlit run app/streamlit_app.py   # confirms the seeded sample works
```

## Phase 4 — Branch: pull the real data
*Skill: branching, debugging on a branch, PR, merge*

```bash
git checkout -b data-pipeline
python scripts/pull_data.py --start-year 2019 --end-year 2025 --out data/raw/crashes_raw.csv
python scripts/clean_crash_data.py data/raw/crashes_raw.csv data/processed/crashes_cleaned
```
I haven't been able to test `pull_data.py` against the live API myself, so this is the likeliest place to hit a real bug — if it errors, that's a normal part of the process, not a sign something's badly wrong. Fix it, then:
```bash
python scripts/audit_columns.py data/processed/crashes_cleaned.csv
```
Update `DATA_DICTIONARY.md`'s missing-% numbers with the real output (they're currently from the skewed 8K sample). Then:
```bash
git add scripts/ DATA_DICTIONARY.md
git commit -m "fix: get pull_data.py working against the live API"
git commit -m "docs: refresh DATA_DICTIONARY.md with real 2019-2025 stats"
git push -u origin data-pipeline
```
On GitHub: **Compare & pull request** → write a short description of what changed → **Merge pull request** → **Delete branch**. Locally:
```bash
git checkout main
git pull
git branch -d data-pipeline
```

*(Optional extra practice: before starting, open a GitHub **Issue** titled "Get real data pipeline working," then reference it in your PR description as `Closes #1` — GitHub auto-closes the issue when the PR merges.)*

## Phases 5–8 — One branch per chart group
*Skill: repeating the branch → commit → PR → merge cycle until it's automatic*

Same pattern four more times, each on `app/streamlit_app.py` (or a `charts.py` helper module if you want to split it up):

| Branch | Charts |
|---|---|
| `charts/line` | Monthly crash volume, injury trend |
| `charts/categorical` | Borough bar, contributing-factor bar, victim-type pie |
| `charts/heatmaps` | Day × hour heat map, geo density heat map |
| `charts/scatter` | Crash locations, severity outliers |

For each: `git checkout -b <branch>` → build the chart(s) → `streamlit run app/streamlit_app.py` to check it renders → commit (small, specific messages — `feat: add borough bar chart`, not one giant "added stuff") → push → PR → merge → delete branch → `git checkout main && git pull` before starting the next one.

## Phase 9 — Wrap up
*Skill: tagging a release*

Update the chart roadmap table in `README.md` (all rows → Done), commit that on a short-lived `docs/final-readme` branch or directly to `main` if you're comfortable with that for docs-only changes. Then:
```bash
git tag -a v1.0 -m "All 9 charts implemented"
git push --tags
```
That gives you a permanent, linkable snapshot of the finished state.

## Phase 10 — Optional: deploy
*Skill: connecting a GitHub repo to an external service*

[share.streamlit.io](https://share.streamlit.io) → sign in with GitHub → pick this repo → set `app/streamlit_app.py` as the entry point → add `NYC_OPEN_DATA_APP_TOKEN` under the app's **Secrets** (never commit it) → deploy. Every future push to `main` auto-redeploys — a good excuse to keep committing.

---

### Quick reference: commands you'll reuse constantly
```bash
git status                  # what's changed
git add <path>               # stage specific files (prefer this over blind `git add .`)
git commit -m "message"      # commit staged changes
git push                     # push current branch
git checkout -b <name>       # new branch
git checkout main            # switch back
git pull                     # sync main after a merge
git log --oneline -10        # recent history, one line each
```
