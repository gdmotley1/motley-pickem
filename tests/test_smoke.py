"""The offline demo week has to keep matching the RPC it stands in for.

`static/data/week01.json` is what the app renders when Supabase is absent: `npm run dev`
with no env vars, `?demo=1`, and the throwaway pages under `outputs/harness/`. Its whole
purpose, per the docstring on scripts/build_mock_data.py, is to be "the exact shape the
app receives from get_slate()" so the UI can be built against it honestly.

Nothing checked that, and it drifted twice in one session on 2026-09-04. `home_conf` and
`away_conf` were missing entirely, so the Setup screen's conference filter was dead
offline; and `tier` was read off a key suggest_slate never sets, so every demo game came
out untiered and the tier chip never rendered. Both were invisible until someone looked
at the screen, which is exactly the class of bug a demo fixture is supposed to prevent.

The gate for this project is the whole tests/ directory, not this file. Add a test
alongside every behaviour worth keeping. If a test is in the way, fix the code or change
the test deliberately. Never delete one to make the suite green.
"""
from __future__ import annotations

import json
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO = os.path.join(ROOT, "static", "data", "week01.json")
ALL_SQL = os.path.join(ROOT, "migrations", "ALL.sql")

# get_slate names these, but no stored row carries them: the mock synthesises them per
# request, the same way Postgres computes them per caller.
#   locked         is now() vs kickoff
#   my_*           is whichever player is asking
RUNTIME_ONLY = {"locked", "my_pick", "my_confidence", "my_auto"}


def get_slate_columns():
    """The column list of the LAST get_slate definition in the combined migration.

    Last, not first: 006 drops and recreates it to add over_under, and ALL.sql is
    generated in migration order, so the final definition is the live one.
    """
    with open(ALL_SQL, encoding="utf-8") as f:
        sql = f.read()
    blocks = re.findall(
        r"function get_slate\(p_token text, p_week int\)\s*returns table \((.*?)\)\s*language",
        sql,
        re.S,
    )
    assert blocks, "no get_slate definition found in ALL.sql"
    return [
        m.group(1)
        for m in re.finditer(r"(?:^|,)\s*([a-z_]+)\s+[a-z]", blocks[-1].replace("\n", " "))
    ]


@pytest.fixture(scope="module")
def demo():
    with open(DEMO, encoding="utf-8") as f:
        return json.load(f)


def test_the_demo_week_has_both_a_slate_and_alternates(demo):
    assert len(demo["slate"]) == 20, "the slate is always exactly 20 games"
    assert demo["alternates"], "the Setup screen needs the rest of the week to be useful"


def test_every_column_get_slate_returns_is_in_the_demo_week(demo):
    expected = set(get_slate_columns()) - RUNTIME_ONLY
    assert expected, "failed to parse get_slate's columns"
    for row in demo["slate"] + demo["alternates"]:
        missing = sorted(expected - set(row))
        assert not missing, (
            "%s @ %s is missing %s. Regenerate with `python scripts/build_mock_data.py` "
            "after changing the RPC's column list."
            % (row.get("away_abbr"), row.get("home_abbr"), missing)
        )


def test_the_demo_week_carries_what_the_setup_screen_filters_on(demo):
    """get_pool returns these and the conference chips are built from them. They are not
    in get_slate, so the check above would not catch them going missing again."""
    for row in demo["slate"] + demo["alternates"]:
        for col in ("home_conf", "away_conf", "interest", "featured"):
            assert col in row, "%s is absent from the demo week" % col
    conferences = {r["home_conf"] for r in demo["slate"]} | {r["away_conf"] for r in demo["slate"]}
    assert len(conferences - {None}) > 3, "a whole week should span more than three conferences"


def test_demo_tiers_are_real_and_agree_with_the_lines(demo):
    """`tier` was silently None on every row because build_mock_data read a key that
    suggest_slate never sets. A game with a line has a tier; one without cannot."""
    tiered = [r for r in demo["slate"] if r["tier"]]
    assert len(tiered) == 20, "every auto-selected game has a line and so has a tier"
    for row in demo["slate"] + demo["alternates"]:
        if row["spread_line"] is None:
            assert row["tier"] is None, (
                "%s @ %s has no line but claims tier %r"
                % (row["away_abbr"], row["home_abbr"], row["tier"])
            )


def test_every_demo_game_can_render_its_logos(demo):
    """TeamLogo files by ESPN team id. A missing id renders a monogram, which is a fine
    fallback for an FCS opponent and a bug for anything in the slate."""
    for row in demo["slate"]:
        for side in ("home", "away"):
            assert row["%s_id" % side], "%s has no ESPN team id" % row["%s_abbr" % side]
            path = os.path.join(ROOT, "static", "logos", "%s.png" % row["%s_id" % side])
            assert os.path.exists(path), (
                "%s (%s) has no vendored logo. Run `python scripts/build_mock_data.py`, "
                "which pulls anything missing." % (row["%s_abbr" % side], path)
            )
