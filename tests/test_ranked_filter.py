"""The gate for the Setup screen's Ranked filter.

The logic is JavaScript, so the assertions live in tests/ranked_filter_check.mjs and this
module runs them under node and surfaces the output, the same way test_matchup.py does.
Keeping them inside the pytest run means `python -m pytest tests/ -q` stays the one gate.

No fixture and no network: the poll is a three-entry Map built in the check itself, which
is enough to pin the two things that actually matter. Rank 1 must survive a truthiness
test, and Ranked must AND with the conference chips rather than replace them.
"""
from __future__ import annotations

import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK = os.path.join(ROOT, "tests", "ranked_filter_check.mjs")

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not on PATH")


@needs_node
def test_ranked_filter():
    proc = subprocess.run(
        [node, CHECK], capture_output=True, text=True, cwd=ROOT, timeout=60
    )
    assert proc.returncode == 0, "\n" + proc.stdout + proc.stderr


def test_the_chip_is_wired_to_the_helpers():
    """The screen must use the shared helpers rather than re-deriving "is this ranked",
    which is how two places come to disagree about it."""
    with open(os.path.join(ROOT, "src", "screens", "Admin.jsx"), encoding="utf-8") as f:
        body = f.read()
    assert "hasRankedTeam" in body and "rankedCount" in body, (
        "Setup no longer uses the shared rank helpers"
    )
    assert "nRanked > 0 &&" in body, (
        'the Ranked chip must be hidden until the AP poll lands, or it reads '
        '"Ranked 0" and filters the pool to nothing when tapped'
    )
