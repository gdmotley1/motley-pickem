"""Every team the setup screen can list must have a vendored mark.

`test_avatars` covers the 138-team FBS library, which is what the team PICKER offers,
and `test_smoke` covers the twenty games in the demo slate. Neither covered the POOL:
the ninety-odd games the setup screen lists so Dad can swap one in. About a third of a
week is an FBS side hosting an FCS side, and the visitor is in none of ESPN's FBS
groups, so `<TeamLogo>` fell back to a four-letter chip for 42 of them until 2026-09-10.
The gap was invisible to the gate because the fixture was never checked this way.

Offline: the fixture is a saved ESPN window pull, so this asserts against the same
ninety games without touching the network. Backfill with

    python scripts/fetch_opponent_logos.py

which reads the live pool; `--games tests/fixtures/slate_week01.json` does the fixture.
"""
from __future__ import annotations

import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from fetch_opponent_logos import have, id_from_logo  # noqa: E402

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "slate_week01.json")


@pytest.fixture(scope="module")
def window():
    with open(FIXTURE, encoding="utf-8") as f:
        return json.load(f)["games"]


def sides(games):
    for g in games:
        for side in ("home", "away"):
            t = g.get(side) or {}
            yield t.get("abbr"), id_from_logo(t.get("logo")), g.get("short_name")


def test_fixture_is_a_whole_window_not_a_slate(window):
    """A twenty-game slate would pass this file trivially and prove nothing. The point
    is the pool, which is every game in the week."""
    assert len(window) > 60, "expected a full window pull, got %d games" % len(window)


def test_every_team_in_the_window_has_an_espn_id(window):
    nameless = [(a, n) for a, tid, n in sides(window) if not tid]
    assert not nameless, "no ESPN team id parsed from the logo href for %s" % nameless[:5]


def test_every_team_in_the_window_has_a_vendored_logo(window):
    """The setup screen renders <TeamLogo> for both sides of every pooled game. A team
    with no file on disk renders its abbreviation in a chip instead of its mark."""
    missing = sorted({(a, tid) for a, tid, _ in sides(window) if tid and not have(tid)})
    assert not missing, (
        "%d team(s) would render as a chip on the setup screen: %s. "
        "Run `python scripts/fetch_opponent_logos.py`."
        % (len(missing), ", ".join("%s (%s)" % m for m in missing[:8]))
    )


def test_light_cut_is_enough_for_an_opponent(window):
    """<TeamLogo> always asks for `<id>.png`. The `-dark` variant exists only for
    <Avatar>, which can render a library team and nothing else, so an opponent outside
    the library never needs one and we do not pay 45KB each to vendor them."""
    src = os.path.join(ROOT, "src", "components", "TeamLogo.jsx")
    with open(src, encoding="utf-8") as f:
        body = f.read()
    assert "-dark" not in body, "TeamLogo now wants a dark cut; opponents only vendor light"
    assert "logos/${teamId}.png" in body, "TeamLogo no longer resolves logos/<id>.png"
