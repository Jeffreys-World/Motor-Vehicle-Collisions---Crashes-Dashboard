"""
Regression: ISSUE-004 — the reconciliation caption asserted a direction the
data contradicted. Found by /qa on 2026-08-09.
Report: .gstack/qa-reports/qa-report-localhost-2026-08-09.md

The caption under the headline read, as a hardcoded string:

    "The range shown here is narrower, and the gap is wider in it"

It sat directly above a live KPI computed from the selected date range. On the
default full range that sentence is true (44.2% against 39.8%). On a large
fraction of the ranges a visitor can actually select it is false. Measured
against the shipped Parquet (812,315 rows, 2019-2025):

    40% of the 84 month-length ranges       share < 39.8%
    50% of the 1,249 single days with a death
    all of 2025                              31.0% against 39.8%

So a visitor selecting 2025 read "the gap is wider in it" three inches from the
figure 31.0%. That is the same failure ISSUE-001 was filed for — two numbers for
one claim, and a reader who trusts neither — reintroduced by the sentence
written to fix ISSUE-001.

These tests lock the direction to a computation. The important one is
test_narrower_range_does_not_claim_wider: it fails against the old hardcoded
string, which is the definition of a regression test for this bug.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from data import (FULL_TABLE_DEATH_SHARE, GAP_EQUAL_TOLERANCE,  # noqa: E402
                  gap_direction)

# Measured from data/processed/crashes.parquet on 2026-08-09. Committed here so
# the test states the real ranges it is defending, not invented numbers.
FULL_RANGE_2019_2025 = 0.442
YEAR_2025 = 0.310
SINGLE_DAY_NO_UNLABELED_DEATHS = 0.0


def test_narrower_range_does_not_claim_wider():
    """The bug. 2025 is 31.0% against a 39.8% full table: narrower, not wider."""
    words = gap_direction(YEAR_2025)
    assert "narrower" in words
    assert "wider" not in words, (
        "the caption claimed the gap was wider on a range where it is narrower"
    )


def test_zero_share_day_does_not_claim_wider():
    """Half of all single days with a death have no unlabeled death at all."""
    assert "narrower" in gap_direction(SINGLE_DAY_NO_UNLABELED_DEATHS)


def test_wider_range_still_reads_wider():
    """The default full range must keep saying what was always true of it."""
    assert "wider" in gap_direction(FULL_RANGE_2019_2025)


def test_equal_within_tolerance_ranks_neither():
    """A hair either side of the full-table figure must not read as a gap."""
    assert "same" in gap_direction(FULL_TABLE_DEATH_SHARE)
    assert "same" in gap_direction(FULL_TABLE_DEATH_SHARE + GAP_EQUAL_TOLERANCE / 2)
    assert "same" in gap_direction(FULL_TABLE_DEATH_SHARE - GAP_EQUAL_TOLERANCE / 2)


@pytest.mark.parametrize("share,expected", [
    (FULL_TABLE_DEATH_SHARE + GAP_EQUAL_TOLERANCE * 1.01, "wider"),
    (FULL_TABLE_DEATH_SHARE - GAP_EQUAL_TOLERANCE * 1.01, "narrower"),
])
def test_tolerance_boundary_is_exclusive(share, expected):
    """Just outside the tolerance band, the direction must be stated again."""
    assert expected in gap_direction(share)


@pytest.mark.parametrize("share", [0.0, 0.1, 0.31, 0.398, 0.442, 0.9, 1.0])
def test_never_states_a_direction_it_cannot_support(share):
    """Whatever the range, exactly one of the three readings comes back."""
    words = gap_direction(share)
    hits = sum(w in words for w in ("wider", "narrower", "same"))
    assert hits == 1, f"ambiguous or empty direction for {share}: {words!r}"
    assert "range shown here" in words, "the wording must scope itself to the filter"
