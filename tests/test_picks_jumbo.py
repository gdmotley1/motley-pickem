"""The Picks tab as the jumbotron Grant picked on 2026-09-13.

"lets do 1, build it": direction 1 of six, the Board's LED wall carried onto Picks so the two
tabs are one stadium. His request came with the rules that already worked, so those are
what is guarded here alongside the look: a list for choosing winners, tap to lift and place
for points, the spread sort on arrival, the loud Matchup pill (tests/test_preview_cta.py),
nothing under 13px.
"""
from __future__ import annotations

import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def picks():
    return read("src", "screens", "Picks.jsx")


def test_picks_and_the_board_share_one_led():
    """One stadium, not two copies of it: the lettering is a single component."""
    led = "import Led from '../components/Led.jsx'"
    assert led in picks(), "Picks is not drawing its numbers with the Board's LED"
    board = read("src", "screens", "Board.jsx")
    assert led in board, "the Board has stopped using the shared LED"
    assert "function Led(" not in board, "the Board grew its own copy of the LED again"


def test_winners_is_a_list_grouped_by_kickoff_day():
    """A card stack was tried for the twenty winners and failed in the hand."""
    body = picks()
    assert "byDay(games).map" in body, "the winners list is no longer grouped by kickoff day"
    assert body.count("<GameRow") == 2, "expected one GameRow for open games and one for kicked-off ones"


def test_points_are_still_tap_to_lift_and_place():
    body = picks()
    assert "function onRowTap(" in body
    assert "setLifted(id)" in body and "onMove(lifted, index)" in body
    pkg = json.loads(read("package.json"))
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    assert not any(d.startswith("@dnd-kit") for d in deps), "dragging is back; it was unusable on a phone"


def test_the_ranking_still_arrives_sorted_by_the_spread():
    body = picks()
    assert "const next = spreadOrder(cur)" in body, "the spread sort no longer runs on arrival"
    assert "Reset to spread" in body


def test_a_pick_lights_only_the_side_taken():
    body = picks()
    assert "dimmed={!!picked && picked !== game.away_abbr}" in body
    assert "dimmed={!!picked && picked !== game.home_abbr}" in body
    lamp = re.search(r"\{selected \? \((.*?)\) : \(", body, re.S)
    assert lamp and "tpick__lamp" in lamp.group(1), "the gold lamp is not tied to the chosen side"


def test_the_school_name_does_not_borrow_the_team_pickers_class():
    """The first render drew every school at 14px instead of 26: the span was .tpick__school,
    which the team picker in the account sheet already styles. The screenshot caught it; the
    measured font of the row, 26px on its parent, did not."""
    assert "tpick__school" not in picks()
    assert '<span className="tpick__label">{school}</span>' in picks()


def test_every_school_is_lit_in_its_own_colors():
    body = picks()
    assert "style={{ '--jb-team': schoolPanel(team, PANEL) }}" in body, "team panels lost their school colors"


def test_locked_in_is_one_screen_whichever_way_you_arrive():
    """The confirmation and the read-only ranking said the same thing in two layouts. Only
    arriving from the button plays the lock dropping shut."""
    body = picks()
    assert "if (phase === 'done' || phase === 'locked')" in body
    assert "fresh={phase === 'done'}" in body
    assert "initial={animate ? { scale: 0.55 } : false}" in body


def test_a_button_waiting_on_picks_is_dark_not_faded():
    """.btn:disabled fades to 0.38, which on the black wall turned dark lettering on dim
    amber into mud."""
    css = read("src", "app.css")
    m = re.search(r"^\.btn\.btn--led:disabled\s*\{(.*?)^\}", css, re.S | re.M)
    assert m and "opacity: 1" in m.group(1)


def test_nothing_on_the_picks_jumbotron_is_under_13px():
    css = read("src", "app.css")
    start = css.index("/* ================================================== picks: the jumbotron === */")
    block = css[start: css.index("/* ================================================== board: the jumbotron === */", start)]
    small = [s for s in re.findall(r"font-size:\s*(\d+(?:\.\d+)?)px", block) if float(s) < 13]
    assert not small, "under 13px on the Picks jumbotron: %s" % small
