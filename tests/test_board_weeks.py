"""The Board steps back through the weeks that have been played. Added 2026-09-28.

Grant: "can we make it we can see the previous week's boards?" The Week tab already lags a
week and shows recaps; this is the scoreboard itself, every tile and every pick, for a week
that is over.

Four things here are load-bearing and easy to undo by accident: the viewed week stays local
to the screen, the arrow never walks forward into a week nobody can see yet, the jump list
never calls a leader a winner, and the header names the week actually on screen.
"""
from __future__ import annotations

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def test_the_viewed_week_is_local_to_the_board():
    """weekId in App is one setting shared with Picks and Setup. Stepping it from here would
    mean settling an argument about last week and then finding the whole slate locked on
    Picks. The same rule the Week tab has had since 2026-09-10."""
    body = read("src", "screens", "Board.jsx")
    assert "const [viewId, setViewId] = useState(null)" in body
    assert "const view = viewId ?? weekId" in body, (
        "the Board no longer falls back to the week App resolved, so it would pin itself to "
        "the remembered id before get_current_week answers"
    )
    assert re.search(r"api\.getSlate\(view\).*api\.getBoard\(view\)", body), (
        "the slate is still loaded for App's week, not the one being viewed"
    )
    assert "}, [view])" in body, "the fetch no longer re-runs when the viewed week changes"
    app = read("src", "App.jsx")
    assert "onWeek={setBoardWeek}" in app
    assert "setWeekId" not in read("src", "screens", "Board.jsx"), "the Board is writing App's week"


def test_the_arrow_never_walks_into_a_week_nobody_can_see():
    """Which weeks are reachable is boardNav's, not the screen's. The edges themselves are
    checked in tests/recap_check.mjs."""
    body = read("src", "screens", "Board.jsx")
    assert "boardNav(weeks, weekId, view)" in body
    nav = read("src", "lib", "weekNav.js")
    assert "export function boardWeeks" in nav and "export function boardNav" in nav
    fn = nav.split("export function boardWeeks", 1)[1].split("\n/**", 1)[0]
    assert "Number(w.week_no) <= upto" in fn, (
        "the cap on the week being played is gone: a slate the sync job published early "
        "would sit one tap forward with every pick hidden"
    )
    assert "w.published" in fn and "Number(w.slate_size) > 0" in fn


def test_the_pager_is_one_control_shared_with_the_week_tab():
    pager = read("src", "components", "WeekPager.jsx")
    assert "wknav__arrow" in pager and "wknav__mid" in pager
    for screen in ("Board.jsx", "Week.jsx"):
        body = read("src", "screens", screen)
        assert "import WeekPager from '../components/WeekPager.jsx'" in body, screen
        assert "function Pager(" not in body, f"{screen} has grown its own pager again"
    # The jumbotron styling has to reach both. It was scoped to .wf-top when only the Week
    # tab had a pager.
    css = read("src", "app.css")
    assert ".jb .wknav--hero {" in css and ".wf-top .wknav--hero" not in css


def test_the_jump_list_never_calls_a_leader_a_winner():
    """The Board can reach the week being played, and a name and a number in the place a
    winner goes reads as a week somebody won. An unfinished week shows its status instead."""
    pager = read("src", "components", "WeekPager.jsx")
    lst = pager[pager.index("function WeekList("):]
    assert "finished && !finished.has(w.id) ? weekStatus(w) : null" in lst
    assert re.search(r"\{live \|\|", lst), "the status no longer wins over the winner line"
    board = read("src", "screens", "Board.jsx")
    assert "finished={new Set(nav.list.filter(isComplete).map((w) => w.id))}" in board, (
        "the Board stopped telling the list which weeks are actually over"
    )


def test_the_header_names_the_week_on_screen():
    """Week 4 in the header over a board showing Week 3 is the mismatch this exists to
    stop. Reported up rather than read down, because weekId still means the week being
    played for Picks and Setup."""
    board = read("src", "screens", "Board.jsx")
    assert "onWeek?.(nav.current || null)" in board
    assert "useEffect(() => () => onWeek?.(null), [onWeek])" in board, (
        "leaving the tab must hand the header back"
    )
    app = read("src", "App.jsx")
    assert "const shownWeek = (tab === 'board' && boardWeek) || week" in app
    assert "${shownWeek.label}" in app and "${shownWeek.slate_size} games" in app


def test_the_strip_carries_the_dates_and_the_pager_survives_a_load():
    """Same call Grant made for the Week strip on 2026-09-25: the pager directly above
    already says Week 3, so the cell says when the week ran. And stepping weeks must not
    take the control you just used off the screen while the next board loads."""
    body = read("src", "screens", "Board.jsx")
    strip = body.split('<div className="jb-strip">\n', 1)[1].split("</div>", 1)[0]
    assert "{dates || label}" in strip, "the Board's strip is repeating the pager's week name"
    assert "dateRangeLabel(games.map((g) => g.kickoff))" in body
    spinner = body.split("if (!games || !rows || !roster)", 1)[1].split("const teamOf", 1)[0]
    assert "{pager}" in spinner and "<Spinner />" in spinner
    # The nudge is the one thing that comes before it: what you can still do about the week.
    main = body[body.index("const finals = games.filter"):]
    at = [main.find(tag) for tag in ("<PickNudge", "{pager}", '<div className="jb-wall">')]
    assert all(i >= 0 for i in at) and at == sorted(at), (
        "the board's top is out of order: the nudge, then the pager, then the wall (%s)" % at
    )
