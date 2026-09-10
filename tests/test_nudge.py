"""The gate for the pick nudge.

Option A2, chosen 2026-09-10. The app had never asked anyone to do anything: no badge,
no deadline, no reminder, and an unused `untilLabel` in format.js whose comment described
a countdown chip that was never built. The state that made the case was live at the time,
with Week 2 published, the first kickoff 24.8 hours out and 0 of 80 picks submitted.

The arithmetic lives in tests/nudge_check.mjs and runs under node here, the same way
test_matchup.py does. What is asserted in Python is the wiring and the two rules that are
easy to break without noticing.
"""
from __future__ import annotations

import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK = os.path.join(ROOT, "tests", "nudge_check.mjs")

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not on PATH")


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


@needs_node
def test_nudge_arithmetic():
    proc = subprocess.run(
        [node, CHECK], capture_output=True, text=True, cwd=ROOT, timeout=60
    )
    assert proc.returncode == 0, "\n" + proc.stdout + proc.stderr


def test_the_board_actually_renders_it():
    """The call, not the import. A guard that only checks the import passes against a
    screen where the component was deleted from the tree, which is how the spread filter
    guard failed on 2026-09-10."""
    body = read("src", "screens", "Board.jsx")
    assert "<PickNudge" in body, "the Board no longer renders the nudge"
    assert "onNavigate?.('picks')" in body, (
        "the nudge's button no longer opens the Picks tab, which is the only thing it "
        "is for"
    )
    # Above the score: whatever the week has become, what you can still do comes first.
    assert body.index("<PickNudge") < body.index("<WeekScore"), (
        "the nudge must sit above the scorebug"
    )


def test_the_app_passes_navigation_down():
    body = read("src", "App.jsx")
    assert "onNavigate={setTab}" in body and "<Board" in body, (
        "Board needs onNavigate for the nudge's button to go anywhere"
    )


def test_the_exit_timeout_matches_the_css():
    """The card is unmounted on a timer rather than on transitionend, because a
    backgrounded tab pauses transitions and an element waiting on an event that never
    fires would sit there half-collapsed. That only works while the two agree."""
    js = read("src", "components", "PickNudge.jsx")
    css = read("src", "app.css")
    assert "const EXIT_MS = 260" in js, "EXIT_MS moved; re-check it against .nudge"
    assert "max-height 0.26s" in css, (
        "the nudge's collapse is no longer 260ms, so EXIT_MS in PickNudge.jsx is wrong"
    )


def test_the_entrance_never_starts_invisible():
    """CLAUDE.md's standing rule. A backgrounded tab pauses CSS animations, so anything
    that animates in from opacity 0 can be stranded invisible. This one starts at 0.55."""
    css = read("src", "app.css")
    block = css[css.index("@keyframes nudgeIn"):]
    block = block[: block.index("}\n}") + 3]
    assert "opacity: 0.55" in block, "nudgeIn must not start from opacity 0"
    assert "opacity: 0;" not in block, "nudgeIn starts invisible; see CLAUDE.md"


# ------------------------------------------------- the Week tab's scorebug

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
    assert "status === 'not started' && score" in body, (
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
