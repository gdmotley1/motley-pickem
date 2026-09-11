"""The gate for the QA pass on 2026-09-10.

Grant asked for a sweep: every button, every back button, nothing clunky, no weird text.
Five things turned up, all of them by driving the real app in a mock build rather than by
reading it. None was visible in the source, and none would have been caught by any test
that existed.

This module pins the ones that are a shape rather than a string; tests/qa_check.mjs
covers the two pure functions under node.
"""
from __future__ import annotations

import glob
import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK = os.path.join(ROOT, "tests", "qa_check.mjs")

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not on PATH")


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


@needs_node
def test_qa_helpers():
    proc = subprocess.run(
        [node, CHECK], capture_output=True, text=True, cwd=ROOT, timeout=60
    )
    assert proc.returncode == 0, "\n" + proc.stdout + proc.stderr


def test_a_closed_week_is_not_zero_still_to_pick():
    """Open Picks on a Sunday and every game is locked, so `editable` is empty. The screen
    drew a progress bar at 0%, a counter reading "0/0" and a DISABLED button saying
    "0 still to pick": three ways of saying nothing while implying there is work to do."""
    body = read("src", "screens", "Picks.jsx")
    assert "const closed = total === 0" in body, "the closed week is no longer detected"
    assert "{!closed && (" in body, "the 0/0 progress header is back"
    assert "See the Board" in body, "a settled week needs somewhere to go"
    assert "Every game has kicked off. This week is settled." in body


def test_a_locked_row_with_no_pick_reads_as_english():
    """Until apply_auto_picks() runs, up to five minutes after kickoff, a locked game can
    genuinely have no pick. The rank list rendered that as "no pick over MIZ"."""
    body = read("src", "screens", "Picks.jsx")
    assert "{g.my_pick || 'No pick'}" in body
    assert "{g.my_pick && (" in body, (
        "the 'over X' clause must be conditional; with no pick there is nothing to be "
        "over"
    )


def test_no_source_file_renders_a_raw_exception():
    """Every screen used to do setError(e.message) and render it. On a dropped signal that
    reads "TypeError: Failed to fetch"; on a rejected RPC it can put the Supabase project
    URL on screen.

    The first version of this test named five screens. The app has more than five places
    that can fail, and the three it missed included SignIn.jsx, which is the screen every
    family member sees first and the one most likely to show an error at all. So it walks
    the tree now: a screen added next season is covered without anyone remembering to
    come back here.
    """
    offenders = []
    for path in sorted(glob.glob(os.path.join(ROOT, "src", "**", "*.jsx"), recursive=True)):
        rel = os.path.relpath(path, ROOT)
        with open(path, encoding="utf-8") as f:
            for n, line in enumerate(f, 1):
                if "setError(" in line and ".message" in line:
                    offenders.append("%s:%d %s" % (rel, n, line.strip()))
    assert not offenders, "raw exception text reaches the screen:\n  " + "\n  ".join(offenders)


def test_the_sign_in_screen_says_things_that_are_true_there():
    """friendly() offers two pieces of advice that are false on the sign-in screen: that
    "your picks are safe on this phone" (you have none yet) and to "tap your name at the
    top" (there is no name up there until you sign in). That screen passes atSignIn."""
    body = read("src", "screens", "SignIn.jsx")
    assert body.count("friendly(e, { atSignIn: true })") == 3, (
        "every failure on the sign-in screen has to be worded for that screen"
    )
    errors = read("src", "lib", "errors.js")
    assert "atSignIn" in errors, "friendly() no longer knows where it is being called"


def test_the_account_sheet_closes_with_a_word_that_is_true_everywhere():
    """"Keep picking" was the close button, shown from Week, Season and Setup too."""
    body = read("src", "App.jsx")
    # The rendered label, not the file: the comment explaining this fix names the old
    # wording, and a whole-file search failed on its own explanation.
    label = body.split('<button className="btn" onClick={onClose}>')[1].split("<")[0].strip()
    assert label == "Done", (
        'the account sheet closes with %r; it is opened from Week, Season and Setup too, '
        "so the word has to be true everywhere" % label
    )


def test_the_tv_slot_is_narrow_enough_to_need_short_names():
    """The fix is only correct while the slot is still small. If .grow__tv ever grows,
    the shortening is no longer earning anything and should be reconsidered."""
    css = read("src", "app.css")
    assert ".grow__tv" in css, "the TV slot is gone; tvLabel may be pointless now"
    body = read("src", "screens", "Picks.jsx")
    assert "tvLabel(game.tv)" in body, "the pick row is printing the raw network name"


def test_a_week_that_is_live_does_not_claim_it_has_not_started():
    """weekStatus() only sees slate_size and graded, so "graded == 0" was being labelled
    "not started". That is also every Saturday from the noon kickoffs until the first
    final: twenty games live, nothing final, and the Week tab reading "Not started yet"
    beside its own red "20 live" chip. The status string had to become true in both
    cases, and the heading, which does know, had to start splitting them."""
    nav = read("src", "lib", "weekNav.js")
    assert "'no results yet'" in nav, "the status claims to know something it cannot"
    assert "'not started'" not in nav

    body = read("src", "screens", "Week.jsx")
    assert "const underway = score.playing > 0" in body, (
        "the heading no longer distinguishes a live week from an untouched one"
    )
    head = body.split("<Screen eyebrow={label} title=")[1].split(">")[0]
    assert "underway" in head, "the skeleton heading is fixed text again: %s" % head
