"""
Regression: ISSUE-005 — nine charts were one Streamlit release from breaking.
Found by /qa on 2026-08-09.
Report: .gstack/qa-reports/qa-report-localhost-2026-08-09.md

Every st.plotly_chart call passed use_container_width=True, deprecated in
Streamlit 1.61.1 with a removal date of 2025-12-31 that has already passed. The
pin was streamlit>=1.40,<2 and Community Cloud auto-redeploys on every push, so
a release inside the pin would have removed the argument and taken all nine
charts down on the public URL with no commit on our side.

This is a source-text test rather than a behavioural one on purpose. The failure
mode is not "the app is wrong today" — it renders fine. It is "someone adds the
argument back, or relaxes the floor, and nothing goes red until a Streamlit
release lands on the deployed URL". The only place to catch that is the source.

The floor assertion is the half that actually matters. Dropping the argument
means relying on width defaulting to "stretch", which does not exist at 1.40, so
the call sites and the pin are coupled. Separating them turns a loud future
breakage into a silent layout regression now.
"""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"
REQUIREMENTS = ROOT / "requirements.txt"

# Version at which `width=` exists on st.plotly_chart and defaults to "stretch".
MIN_STREAMLIT_MAJOR_MINOR = (1, 61)


@pytest.mark.parametrize("path", sorted(APP.glob("*.py")), ids=lambda p: p.name)
def test_no_use_container_width_anywhere_in_app(path):
    """The deprecated argument must not come back."""
    hits = [
        f"{path.name}:{i}"
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if "use_container_width" in line
    ]
    assert not hits, (
        "use_container_width is deprecated with a removal date already passed; "
        f"omit it and let width default to 'stretch'. Found at: {hits}"
    )


def test_streamlit_floor_supports_the_width_default():
    """The pin must guarantee the default the call sites now rely on."""
    text = REQUIREMENTS.read_text(encoding="utf-8")
    m = re.search(r"^streamlit>=(\d+)\.(\d+)", text, re.MULTILINE)
    assert m, "requirements.txt must pin a streamlit lower bound"
    floor = (int(m.group(1)), int(m.group(2)))
    assert floor >= MIN_STREAMLIT_MAJOR_MINOR, (
        f"streamlit floor {floor} is below {MIN_STREAMLIT_MAJOR_MINOR}, where "
        "st.plotly_chart has no width= parameter. A bare st.plotly_chart(fig) "
        "there renders at natural width instead of filling the column."
    )


def test_every_plotly_call_is_bare_or_explicit():
    """No call may rely on a default that differs across the allowed range."""
    src = (APP / "streamlit_app.py").read_text(encoding="utf-8")
    calls = re.findall(r"st\.plotly_chart\((.*?)\)\n", src, re.DOTALL)
    assert calls, "expected to find st.plotly_chart calls to check"
    for c in calls:
        assert "use_container_width" not in c, f"deprecated kwarg in: {c[:60]}"
