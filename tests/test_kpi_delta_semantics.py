"""
Regression: ISSUE-006 — the KPI rendered a trend arrow on a static composition.
Found by /qa on 2026-08-09.
Report: .gstack/qa-reports/qa-report-localhost-2026-08-09.md

st.metric's delta slot means "this changed". The page put "830 of 1,877" in it,
which is a share written out, not a change. Streamlit parsed the leading number,
read it as positive, and drew an upward arrow — so the page said "up 830" about
a figure that has no earlier value anywhere on the page. On a single-day filter
it drew an upward arrow beside "0 of 1".

Source-text test on purpose, same reasoning as ISSUE-005: the app is correct
today, and the regression would be someone deleting one keyword. Nothing would
fail, no console error, no traceback — the arrow would simply come back and the
page would resume implying a trend that does not exist.
"""

import re
from pathlib import Path

APP = Path(__file__).resolve().parent.parent / "app" / "streamlit_app.py"


def _death_share_metric_call() -> str:
    """The st.metric call whose delta carries a composition rather than a change."""
    src = APP.read_text(encoding="utf-8")
    m = re.search(r"\.metric\(\s*\"Deaths in unlabeled rows.*?\n(?:.*?\n)*?.*?\)\n",
                  src)
    assert m, "could not locate the unlabeled-deaths metric call"
    return m.group(0)


def test_delta_arrow_is_disabled():
    """The arrow must stay off while the delta carries a composition."""
    call = _death_share_metric_call()
    assert 'delta_arrow="off"' in call, (
        "the delta slot holds 'N of M', a composition, not a change. Without "
        'delta_arrow="off" Streamlit renders an upward arrow and the page '
        "implies a rise against a period it never shows."
    )


def test_delta_still_carries_the_composition():
    """Fixing the arrow must not silently drop the numerator and denominator."""
    call = _death_share_metric_call()
    assert "unlabeled_killed" in call and "kpi.killed" in call, (
        "the 'N of M' breakdown is what makes the percentage checkable; "
        "removing it would trade one problem for a worse one"
    )


def test_inverse_colour_is_preserved():
    """The figure is bad news and must not quietly become neutral."""
    assert 'delta_color="inverse"' in _death_share_metric_call()
