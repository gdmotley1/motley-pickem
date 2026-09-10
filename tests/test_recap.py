"""The verification gate for the week recap's arithmetic.

src/lib/weekRecap.js is JavaScript, so the assertions live in tests/recap_check.mjs and
this module runs them under node and surfaces the output, the same arrangement
test_matchup.py uses. Keeping them in the pytest run means `python -m pytest tests/ -q`
stays the one gate for the whole project.

The fixture is the real 2026 Week 1: tests/fixtures/week1_board.json holds the slate, the
board and the roster exactly as get_slate, get_board and list_seats return them, pulled
from the live database on 2026-09-10 once every game had been graded. Regenerate it only
if those functions change shape:

    python - <<'PY'
    import sys, os, json
    sys.path.insert(0, "scripts")
    from sync_supabase import Supabase, env, load_dotenv
    load_dotenv(".env")
    sb = Supabase(env("SUPABASE_URL"), env("SUPABASE_SERVICE_KEY"))
    # week_id 1, in_slate only, then shape to the three RPC payloads. See git history
    # for the full script; it is a straight column rename.
    PY

A real week rather than a synthetic one is deliberate. The recap's only claim is that it
describes what happened, so the numbers asserted are the ones the family actually saw.
A detector that drifts, drifts away from a week somebody remembers.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK = os.path.join(ROOT, "tests", "recap_check.mjs")
FIXTURE = os.path.join(ROOT, "tests", "fixtures", "week1_board.json")

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not on PATH")


def load():
    with open(FIXTURE, encoding="utf-8") as f:
        return json.load(f)


def test_fixture_is_a_complete_graded_week():
    fx = load()
    assert set(fx) == {"slate", "board", "seats"}
    assert len(fx["slate"]) == 20, "the house rule is exactly 20 games a week"
    assert all(g["winner_abbr"] for g in fx["slate"]), (
        "every game must be graded: the recap only renders on a finished week, so a "
        "fixture with an ungraded game would not exercise it"
    )
    assert len(fx["seats"]) == 4
    assert len(fx["board"]) == 80, "four players times twenty games"


def test_fixture_confidence_ladders_are_legal():
    """1..20 used exactly once each. If this breaks, the ceiling maths is meaningless."""
    fx = load()
    for seat in fx["seats"]:
        got = sorted(
            r["confidence"] for r in fx["board"] if r["player_id"] == seat["id"]
        )
        assert got == list(range(1, 21)), f"{seat['name']} has an illegal ladder: {got}"


@needs_node
def test_week_recap_arithmetic():
    proc = subprocess.run(
        [node, CHECK], capture_output=True, text=True, cwd=ROOT, timeout=60
    )
    # The .mjs prints one line per check, so a failure reads as a report rather than a
    # bare non-zero exit.
    assert proc.returncode == 0, "\n" + proc.stdout + proc.stderr
