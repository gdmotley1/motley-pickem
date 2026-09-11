"""The gate for the Week tab's scoreboard.

Two decisions live here and both were reached by looking rather than reasoning.

The tab used to have its own light standings table. It now renders the same <WeekScore>
the Board does, reading the same weekScore() object, so the two screens cannot drift
about who is where.

And it renders the LIGHT cut. The Board keeps the dark one, because twenty white game
cards underneath are exactly what a broadcast graphic is meant to sit on; the Week tab is
followed by Ranking, Your week, Upsets and the numbers, all light, so the same component
there read as a slab from another app.
"""
from __future__ import annotations

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()



def test_the_week_tab_uses_the_scorebug():
    """Grant asked on 2026-09-10 for the Week tab to carry the bug rather than its own
    light table. Both screens must read the same `weekScore` object, or they will
    eventually disagree about who is where."""
    body = read("src", "screens", "Week.jsx")
    # TWO call sites, not one. The first version of this guard only checked that
    # `<WeekScore` appeared somewhere, and the skeleton branch satisfied it: swapping the
    # settled week back to a light table left the guard green. Verified by doing exactly
    # that and watching it pass.
    assert body.count("<WeekScore") == 2, (
        "expected the scorebug at both call sites, the skeleton and the settled week; "
        "found %d" % body.count("<WeekScore")
    )
    assert "weekScore(games, rows, roster)" in body, (
        "the Week tab is deriving its own standings instead of reading weekScore"
    )
    assert "function Standings" not in body and "<Standings" not in body, (
        "the old light standings table is back; it and the bug would drift"
    )


def test_a_published_week_that_has_not_started_shows_the_frame():
    """The state Grant hit: Week 2 published, twenty games, nothing kicked off. The tab
    used to show an empty state, which reads as the feature being missing rather than as
    the week not having happened. The other two empty statuses genuinely have nothing to
    frame and keep their message."""
    body = read("src", "screens", "Week.jsx")
    assert "status === 'no results yet' && score" in body, (
        "a published-but-unstarted week no longer draws the skeleton"
    )
    assert "skeleton" in body, "the skeleton prop is not passed"
    for kept in ("'not published'", "'no slate yet'"):
        assert kept in body, "%s lost its empty state" % kept


def test_the_skeleton_shows_no_numbers_and_no_rank():
    """Everyone ties on zero before a game finishes, so a real rank prints "1" four times
    and a real score prints four zeroes. Both read as data rather than as an empty
    frame."""
    body = read("src", "components", "WeekScore.jsx")
    assert "{!skeleton && <span className=\"bugrow__seed num\">" in body, (
        "the skeleton is printing a rank nobody holds"
    )
    assert "{skeleton ? '—' : p.points}" in body, "the skeleton is printing scores"


def test_only_the_week_tab_pays_for_the_record_column():
    """A fifth column on a 390px phone costs the name its ellipsis, and the Board does not
    need one: the game cards underneath it ARE the record."""
    css = read("src", "app.css")
    assert ".bug--rec .bugrow" in css, "the record column is no longer opt-in"
    board = read("src", "screens", "Board.jsx")
    assert "record" not in board.split("<WeekScore")[1].split("/>")[0], (
        "the Board is asking for the record column"
    )


def test_the_two_screens_take_different_cuts():
    """The Board keeps the dark bug and the Week tab takes the light one. Getting this
    backwards is the whole bug Grant reported: a dark slab in a light screen."""
    week = read("src", "screens", "Week.jsx")
    board = read("src", "screens", "Board.jsx")
    assert week.count("light") >= 2, (
        "both Week call sites, the skeleton and the settled week, must ask for the light "
        "cut; found %d mentions" % week.count("light")
    )
    board_call = board.split("<WeekScore")[1].split("/>")[0]
    assert "light" not in board_call, (
        "the Board took the light cut; it keeps the dark one, because the game cards "
        "underneath are what a broadcast graphic is meant to sit on"
    )


def test_the_light_cut_exists_and_flips_the_chrome():
    css = read("src", "app.css")
    assert ".bug--light {" in css, "the light cut is gone"
    block = css[css.index(".bug--light {"):]
    block = block[: block.index("}") + 1]
    assert "var(--card)" in block, "the light cut is not on a card surface"


def test_gold_does_not_travel_to_the_light_cut():
    """--lead is #ffd25a: 10.8:1 on the bug's near-black and about 1.5:1 on a light card.
    The leader has to take a colour that is not already spoken for by right, wrong or
    live, which leaves the app's blue."""
    css = read("src", "app.css")
    i = css.index(".bug--light .bugrow.is-leader .bugrow__pts")
    rule = css[i: css.index("}", i)]
    assert "--accent-deep" in rule, "the light leader is not using the app's accent"
    assert "--lead" not in rule, "gold cannot be read on a light card"


def test_the_disc_ring_flips_too():
    """A white ring reads as nothing on a white card."""
    css = read("src", "app.css")
    i = css.index(".bug--light .bugrow__mark")
    rule = css[i: css.index("}", i)]
    assert "255, 255, 255" not in rule, "the light cut keeps a white ring on a white card"
