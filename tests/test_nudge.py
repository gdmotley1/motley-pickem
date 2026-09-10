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
