"""The gate for the Setup screen's filters.

Three axes now cut the 91-game pool: conference, whether a team is ranked, and how big
the line is. They compose, so the gate has to cover both the pieces and the composition.

The logic is JavaScript, so the assertions live in tests/*_check.mjs and this module runs
them under node and surfaces the output, the same way test_matchup.py does. Keeping them
inside the pytest run means `python -m pytest tests/ -q` stays the one gate.

No fixture and no network: each check builds the handful of rows it needs. What is pinned
is the behaviour that is easy to get subtly wrong. Rank 1 must survive a truthiness test.
A game with no published line must fall in NO spread band rather than reading as a
toss-up. And every filter must AND with the others rather than replace them.
"""
from __future__ import annotations

import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RANKED = os.path.join(ROOT, "tests", "ranked_filter_check.mjs")
SPREAD = os.path.join(ROOT, "tests", "spread_filter_check.mjs")

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not on PATH")


def run(check):
    """Run one .mjs check and surface its own report on failure.

    The checks print a line each, so a failure reads as a list of what passed and what
    did not rather than as a bare non-zero exit.
    """
    proc = subprocess.run([node, check], capture_output=True, text=True, cwd=ROOT,
                          timeout=60)
    assert proc.returncode == 0, "\n" + proc.stdout + proc.stderr


@needs_node
def test_ranked_filter():
    run(RANKED)


@needs_node
def test_spread_bands():
    run(SPREAD)


def test_the_chips_are_wired_to_the_helpers():
    """The screen must use the shared helpers rather than re-deriving "is this ranked" or
    "is this close", which is how two places come to disagree about it."""
    with open(os.path.join(ROOT, "src", "screens", "Admin.jsx"), encoding="utf-8") as f:
        body = f.read()
    assert "hasRankedTeam" in body and "rankedCount" in body, (
        "Setup no longer uses the shared rank helpers"
    )
    assert "availableBands" in body, "Setup no longer builds the spread chips"
    # The call, not the import. The first version of this checked only that `inBand`
    # appeared somewhere in the file, and deleting the line that actually filters left
    # the import behind, so the guard passed against a screen whose spread chips did
    # nothing at all. Verified by deleting that line and watching this fail.
    assert "inBand(g, band)" in body, (
        "the spread chips are not wired to the filter: `inBand` is imported but the "
        "rows are never narrowed by it"
    )
    assert "hasRankedTeam(g, ranks)" in body, (
        "the Ranked chip is not wired to the filter"
    )
    assert "nRanked > 0 &&" in body, (
        'the Ranked chip must be hidden until the AP poll lands, or it reads '
        '"Ranked 0" and filters the pool to nothing when tapped'
    )
