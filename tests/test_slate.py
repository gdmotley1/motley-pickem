"""The verification gate for slate building.

Runs against a saved ESPN fixture, never the live network, so it is deterministic and
works offline. Regenerate the fixture with:

    python scripts/fetch_slate.py --start 2026-09-03 --end 2026-09-06 \
        --out tests/fixtures/slate_week01.json
"""
from __future__ import annotations

import copy
import datetime as dt
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import fetch_slate                      # noqa: E402
import suggest_slate                    # noqa: E402

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "slate_week01.json")
DAD = os.path.join(ROOT, "inputs", "week01_resolved.json")


@pytest.fixture(scope="module")
def games():
    with open(FIXTURE, encoding="utf-8") as f:
        gs = json.load(f)["games"]
    for g in gs:                         # the fixture predates the featured flag
        g.setdefault("featured", False)
        g.setdefault("featured_rank", None)
    return gs


# ---------------------------------------------------------------- fixture sanity

def test_fixture_has_a_full_week(games):
    assert len(games) >= 60, "expected a full FBS week, got %d games" % len(games)


def test_every_game_has_both_teams_and_a_kickoff(games):
    for g in games:
        assert g["home"]["abbr"] and g["away"]["abbr"], g["short_name"]
        assert g["kickoff_utc"], g["short_name"]


def test_most_games_have_a_posted_line(games):
    withline = [g for g in games if g["odds"].get("line") is not None]
    assert len(withline) / len(games) > 0.85


# ---------------------------------------------------------------- spread parsing

def test_favorite_and_underdog_are_the_two_teams(games):
    for g in games:
        o = g["odds"]
        if o.get("favorite"):
            sides = {g["home"]["abbr"], g["away"]["abbr"]}
            assert o["favorite"] in sides, g["short_name"]
            assert o["underdog"] in sides, g["short_name"]
            assert o["favorite"] != o["underdog"], g["short_name"]


def test_line_is_never_negative(games):
    for g in games:
        line = g["odds"].get("line")
        if line is not None:
            assert line >= 0, "%s has line %s" % (g["short_name"], line)


def test_known_lines_parse_correctly(games):
    by_name = {g["short_name"]: g for g in games}
    lsu = by_name["CLEM @ LSU"]
    assert lsu["odds"]["line"] == 10.0
    assert lsu["odds"]["favorite"] == "LSU"
    assert lsu["odds"]["underdog"] == "CLEM"


# ------------------------------------------------------- conference id coercion
# ESPN returns conferenceId as a STRING. Comparing it to an int silently matched
# nothing and produced a slate with zero SEC games. Regression guard.

def test_conference_id_is_coerced_not_compared_raw(games):
    sec = [g for g in games if suggest_slate.is_sec(g)]
    assert len(sec) >= 8, "expected plenty of SEC games, found %d" % len(sec)


def test_georgia_is_detected_as_sec(games):
    uga = [g for g in games if suggest_slate.has_team(g, "UGA")]
    assert uga, "Georgia should be playing in this fixture"
    assert all(suggest_slate.is_sec(g) for g in uga)


def test_fbs_detection_handles_string_ids(games):
    fbs = [g for g in games
           if fetch_slate.is_fbs(g["home"]) and fetch_slate.is_fbs(g["away"])]
    assert len(fbs) >= 30


# ---------------------------------------------------------------- tier bucketing

@pytest.mark.parametrize("line,expected", [
    (0.0, "toss-up"), (1.5, "toss-up"), (4.0, "toss-up"),
    (4.5, "close"), (10.0, "close"),
    (10.5, "medium"), (18.0, "medium"),
    (18.5, "big"), (28.0, "big"),
    (28.5, "blowout"), (50.5, "blowout"),
])
def test_tier_boundaries(line, expected):
    g = {"odds": {"line": line}}
    assert suggest_slate.tier_of(g) == expected


def test_game_without_a_line_has_no_tier():
    assert suggest_slate.tier_of({"odds": {"line": None}}) is None


# ---------------------------------------------------------------- interest score

def test_blowouts_score_below_close_games(games):
    by_name = {g["short_name"]: g for g in games}
    close = by_name["CLEM @ LSU"]["interest"]          # LSU -10, ABC
    blowout = by_name["TNST @ UGA"]["interest"]        # UGA -46.5 vs FCS
    assert blowout < close, "a 46-point FCS game outranked a 10-point ABC game"


def test_fcs_games_are_penalised(games):
    fcs = [g for g in games
           if not (fetch_slate.is_fbs(g["home"]) and fetch_slate.is_fbs(g["away"]))]
    assert fcs, "fixture should contain FCS tune-up games"
    fbs_close = [g for g in games
                 if fetch_slate.is_fbs(g["home"]) and fetch_slate.is_fbs(g["away"])
                 and (g["odds"].get("line") or 99) <= 7]
    assert max(g["interest"] for g in fcs) < max(g["interest"] for g in fbs_close)


# ---------------------------------------------------------------- slate selection

@pytest.fixture(scope="module")
def slate(games):
    picked, reasons = suggest_slate.select_slate(games)
    return picked, reasons


def test_slate_is_exactly_twenty(slate):
    assert len(slate[0]) == suggest_slate.SLATE_SIZE


def test_slate_has_no_duplicates(slate):
    ids = [suggest_slate.gid(g) for g in slate[0]]
    assert len(set(ids)) == len(ids)


def test_georgia_is_always_included(slate):
    picked, reasons = slate
    assert any(suggest_slate.has_team(g, "UGA") for g in picked), \
        "Georgia must never be left out"


def test_sec_minimum_is_met(slate):
    n = sum(1 for g in slate[0] if suggest_slate.is_sec(g))
    assert n >= suggest_slate.SEC_MINIMUM, "only %d SEC games" % n


def test_every_selected_game_has_a_line(slate):
    for g in slate[0]:
        assert g["odds"].get("line") is not None, g["short_name"]


def test_tier_mix_matches_targets(slate):
    counts = {}
    for g in slate[0]:
        counts[suggest_slate.tier_of(g)] = counts.get(suggest_slate.tier_of(g), 0) + 1
    for label, _, want in suggest_slate.TIERS:
        assert counts.get(label, 0) >= want - 1, \
            "tier %s had %d, wanted about %d" % (label, counts.get(label, 0), want)


def test_slate_is_not_all_blowouts(slate):
    """The failure mode that made ESPN's raw featured list unusable."""
    lines = [g["odds"]["line"] for g in slate[0]]
    assert sum(1 for x in lines if x > 24) <= 7, \
        "too many blowouts: %s" % sorted(lines, reverse=True)


# ---------------------------------------------------------------- dad's slate

@pytest.mark.skipif(not os.path.exists(DAD), reason="dad's resolved slate not built")
def test_dads_twenty_all_resolved():
    with open(DAD, encoding="utf-8") as f:
        d = json.load(f)
    assert d["count"] == 20
    ids = [g["espn_id"] for g in d["games"]]
    assert len(set(ids)) == 20, "duplicate games in dad's slate"


@pytest.mark.skipif(not os.path.exists(DAD), reason="dad's resolved slate not built")
def test_the_two_tulanes_are_not_confused():
    """TULN at Duke and OKST at Tulsa both read as 'TUL' in Dad's shorthand."""
    with open(DAD, encoding="utf-8") as f:
        by = {g["short_name"]: g for g in json.load(f)["games"]}
    assert "TULN @ DUKE" in by, "Tulane at Duke missing"
    assert "OKST @ TLSA" in by, "Oklahoma State at Tulsa missing"


# ---------------------------------------------------------------- the whole pool

WINDOW = (dt.date(2026, 9, 3), dt.date(2026, 9, 6))


def build_from(gs):
    """The real build(), with the two network calls stubbed out by the fixture.

    Games are deep-copied by the caller: build() writes featured, selected and reason
    back onto whatever it is handed, and `games` is shared with every test above.
    """
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(suggest_slate, "fetch", lambda start, end: gs)
        mp.setattr(suggest_slate, "featured_ids", lambda: [])
        return suggest_slate.build(*WINDOW)


@pytest.fixture(scope="module")
def pool(games):
    return build_from(copy.deepcopy(games))


def test_pool_holds_every_game_in_the_window(pool, games):
    assert pool["pool_size"] == len(games)
    assert len(pool["slate"]) + len(pool["alternates"]) == len(games)


def test_pool_is_not_capped(pool):
    """The cap that hid fifty of the ninety-one games in the 2026-09-05 week.

    Dad could not reach a game outside the top forty by interest, which is most of the
    ones a family actually asks for by name. Asserting the constant is gone as well as
    the count, because a cap reintroduced quietly is exactly how this regressed.
    """
    assert not hasattr(suggest_slate, "POOL_SIZE"),         "a pool cap is back: Dad can no longer reach every game"
    assert len(pool["alternates"]) > 40


def test_slate_and_alternates_never_overlap(pool):
    picked = {suggest_slate.gid(g) for g in pool["slate"]}
    spare = {suggest_slate.gid(g) for g in pool["alternates"]}
    assert not (picked & spare)
    assert len(picked) + len(spare) == pool["pool_size"]


def test_a_game_with_no_line_stays_in_the_pool(games):
    """West Georgia at Kennesaw State, the game Grant named.

    Checked live on 2026-09-04: it had no posted line, and so did ten other games that
    week, every one of them already final. ESPN drops the odds block once a game ends,
    which is why a pool rebuilt mid-weekend used to lose the games already played: the
    old alternates were filtered through tier_of(), which needs a line.

    The fixture was saved while the line was still up, so the missing line is constructed
    here rather than waiting for ESPN to drop one again. Kennesaw's own exclusion from the
    old pool was the forty-game cap, not this; test_pool_is_not_capped covers that.
    """
    doctored = copy.deepcopy(games)
    target = next(g for g in doctored if "KENN" in (g["home"]["abbr"], g["away"]["abbr"]))
    target["odds"] = {"line": None, "favorite": None, "underdog": None, "over_under": None}
    assert suggest_slate.tier_of(target) is None, "a game with no line cannot be tiered"

    built = build_from(doctored)
    reachable = {suggest_slate.gid(g) for g in built["slate"] + built["alternates"]}
    assert suggest_slate.gid(target) in reachable,         "a game with no line must still be one Dad can add"


def test_a_game_with_no_line_is_never_auto_selected(games):
    """It can be added by hand, but it must not land in the twenty on its own.

    Confidence points need a certainty gradient, and a game with no line cannot be
    placed on one. This is also what keeps the auto-pick rule honest: with no favourite
    it would fall back to the home team.
    """
    doctored = copy.deepcopy(games)
    for g in doctored:
        g["odds"] = {"line": None, "favorite": None, "underdog": None, "over_under": None}

    built = build_from(doctored)
    assert built["slate"] == [], "no game has a line, so nothing can be auto-selected"
    assert len(built["alternates"]) == len(games), "every game is still addable by hand"


def test_every_auto_selected_game_still_has_a_line(pool):
    for g in pool["slate"]:
        assert g["odds"].get("line") is not None, g["short_name"]
        assert suggest_slate.tier_of(g) is not None, g["short_name"]
