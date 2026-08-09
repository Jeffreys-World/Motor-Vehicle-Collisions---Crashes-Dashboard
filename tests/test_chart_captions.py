"""
Regression: ISSUE-007 — two charts had no text alternative of any kind.
Found by /qa on 2026-08-09.
Report: .gstack/qa-reports/qa-report-localhost-2026-08-09.md

Measured in the browser: 9 charts, 27 Plotly SVGs, and zero accessible names
between them. st.plotly_chart exposes no alt-text parameter and Plotly's SVG
output carries no role or aria-label, so the adjacent st.caption is the only
text alternative this stack can produce.

Seven sections had one. Charts 4 (Monthly volume) and 7 (When crashes happen)
had nothing, so a screen reader arrived at them and got a heading followed by
silence.

Honest limits of this test, stated rather than discovered later:

  - It checks the SOURCE, not the render. Several captions sit inside
    conditionals (charts 1, 2, 3), so this cannot prove one renders on every
    date range. It proves the section is not silent by construction.
  - A caption is not a label. It is adjacent text, not an accessible name bound
    to the graphic. This closes the "nothing at all" gap; it does not make the
    charts accessible, and the report says so.
"""

import re
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parent.parent / "app" / "streamlit_app.py"
SRC = APP.read_text(encoding="utf-8")

# Each numbered section runs from its subheader to the next one (or EOF).
_HEADINGS = list(re.finditer(r'st\.subheader\("(\d+)\.\s*([^"]+)"\)', SRC))


def _sections():
    for i, m in enumerate(_HEADINGS):
        start = m.end()
        end = _HEADINGS[i + 1].start() if i + 1 < len(_HEADINGS) else len(SRC)
        yield f"{m.group(1)}. {m.group(2)}", SRC[start:end]


def test_all_nine_sections_are_present():
    """Guards against a section being renumbered or dropped unnoticed."""
    assert len(_HEADINGS) == 9, f"expected 9 numbered sections, found {len(_HEADINGS)}"


@pytest.mark.parametrize("title,body", list(_sections()), ids=lambda v: v if isinstance(v, str) and v[:1].isdigit() else "")
def test_every_chart_section_has_a_caption(title, body):
    """No section may be text-silent: it is the only a11y lever available here."""
    assert "st.caption(" in body, (
        f"section {title!r} renders a chart with no caption. st.plotly_chart "
        "provides no alt text and Plotly's SVG is unlabelled, so a caption is "
        "the only text alternative a screen reader can reach."
    )


@pytest.mark.parametrize("title,body", list(_sections()), ids=lambda v: v if isinstance(v, str) and v[:1].isdigit() else "")
def test_added_captions_carry_no_hardcoded_figures(title, body):
    """The two captions added for ISSUE-007 must not become ISSUE-001.

    They sit under a date filter that changes every number on the page. A
    literal percentage or ratio typed into them would be a static claim beside
    a live figure, which is the bug ISSUE-001 and ISSUE-004 were both filed for.
    Only the two added captions are checked; the pre-existing ones compute their
    numbers from the query result, which is the correct pattern.
    """
    if not title.startswith(("4.", "7.")):
        pytest.skip("only the captions added by ISSUE-007 are covered")
    for cap in re.findall(r"st\.caption\((.*?)\)\n", body, re.DOTALL):
        assert not re.search(r"\d+(\.\d+)?\s*%", cap), (
            f"hardcoded percentage in section {title!r} caption"
        )
        assert "{" not in cap or "f\"" not in cap.split("{")[0][-3:], (
            f"section {title!r} caption should be a plain string, not an f-string "
            "interpolating a per-range figure"
        )
