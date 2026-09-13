"""The finished week on the Week tab: "Winner's colors", and the sections Grant picked.

Picked on 2026-09-12 off two boards: option 2 for the look, then sections 1, 2, 3, 6, 7, 8
and 9 in that order. He cut the ranking bars, "points left on the table", biggest miss and
best call. The numbers themselves are checked against the real Week 1 in
tests/recap_check.mjs; this file holds the shape of the screen.
"""
from __future__ import annotations

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def final_branch():
    body = read("src", "screens", "Week.jsx")
    start = body.index('<div className="wf">')
    return body[start: body.index("</div>", start)]


def test_the_sections_are_in_grants_order():
    order = ["<Hero", "<FinalTable", "<Decided", "<Upsets", "<Unfolded", "<YourWeek", "<Agreed",
             "<Alone", "<InNumbers"]
    branch = final_branch()
    at = [branch.find(tag) for tag in order]
    assert all(i >= 0 for i in at), "a section is missing: %s" % dict(zip(order, at))
    assert at == sorted(at), "the sections are out of the order Grant picked: %s" % order


def test_the_cut_sections_stay_cut():
    body = read("src", "screens", "Week.jsx")
    for gone in ("captured", "left on the table", "Biggest miss", "Best call", "function Ranking"):
        assert gone not in body, "%r is back on the Week tab; Grant cut it on 2026-09-12" % gone


def test_the_final_table_reads_the_scorebugs_own_object():
    """One scoreboard: the finished table and the live bug read the same weekScore, so they
    can never disagree about who is where."""
    body = read("src", "screens", "Week.jsx")
    assert "<FinalTable score={score}" in body
    table = body[body.index("function FinalTable"):]
    table = table[: table.index("\nfunction ", 10)]
    assert "score.players.map" in table, "the final table is deriving its own standings"


def test_only_a_finished_week_paints_the_chrome():
    """While a week is live the tab shows the Board's scorebug on Slate, so the header must
    not change color until every game is final, and never on another tab."""
    week = read("src", "screens", "Week.jsx")
    assert "if (!recap?.complete || !recap.leaders.length) return null" in week
    assert "useEffect(() => () => onSkin?.(null), [onSkin])" in week, "leaving the tab must clear the skin"
    app = read("src", "App.jsx")
    assert "const skin = tab === 'week' && weekSkin ? weekSkin : null" in app


def test_the_italic_it_is_set_in_is_actually_loaded():
    link = re.search(r'href="(https://fonts\.googleapis\.com/css2[^"]+)"', read("index.html")).group(1)
    assert "Archivo:ital," in link and ";1," in link, "the Archivo italic is not requested"
    assert "..900" in link, "the finished week sets 900; the request stops short of it"


def test_nothing_in_the_finished_week_is_under_13px():
    css = read("src", "app.css")
    start = css.index("/* ================================================ the finished week ==== */")
    block = css[start: css.index("/* The form chart.", start)]
    small = [s for s in re.findall(r"font-size:\s*(\d+(?:\.\d+)?)px", block) if float(s) < 13]
    assert not small, "under 13px in the finished week: %s" % small


def test_the_tab_only_ever_shows_a_finished_week():
    """Grant, 2026-09-12: "always have it lag a week". It opens on the newest finished
    week, and nothing on it can reach the week being played. The edges themselves are
    checked in tests/recap_check.mjs."""
    body = read("src", "screens", "Week.jsx")
    assert "const { latest } = weekNav(w, null)" in body, "the tab no longer opens on the newest finished week"
    assert "const nav = weekNav(weeks, viewId)" in body
    for gone in ("useLiveScores", "withLive", "getCurrentWeek"):
        assert gone not in body, "%s is back: the Week tab has no live week to follow" % gone
    nav = read("src", "lib", "weekNav.js")
    assert "export function recapWeeks" in nav
    app = read("src", "App.jsx")
    assert "<Week me={me} onSkin={setWeekSkin} />" in app, "App is handing the Week tab the current week again"
