"""The gate for book mode, the Season tab's trophy case.

Grant picked option S6 off outputs/season-board.html on 2026-09-11 and asked for the
whole Season tab in it, the standings included, with the app "kinda go into a different
mode almost". So the attribute goes on `.app`, not on the screen: the header and the tab
bar are the case's frame, and a themed panel inside Slate chrome would read as a widget
rather than as a room you walked into.

The colour arithmetic and the palette contract live in tests/book_mode_check.mjs and run
under node, the same way test_nudge.py does. What is asserted here is the wiring, and the
one rule that is easy to break without noticing: the pick-making screens must stay Slate.
"""
from __future__ import annotations

import os
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK = os.path.join(ROOT, "tests", "book_mode_check.mjs")

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not on PATH")


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


@needs_node
def test_the_palette_and_the_colour_lift():
    proc = subprocess.run(
        [node, CHECK], capture_output=True, text=True, cwd=ROOT, timeout=60
    )
    assert proc.returncode == 0, "\n" + proc.stdout + proc.stderr


def test_the_mode_goes_on_the_shell_not_the_screen():
    """The whole point of the ask. On the screen it is a themed panel; on `.app` the
    header and the tab bar change with it and the app reads as a different mode."""
    body = read("src", "App.jsx")
    assert 'className="app" data-mode={mode}' in body, (
        "data-mode is no longer on the app shell, so the header and tab bar will stay "
        "Slate while the screen goes wood"
    )
    assert "tab === 'season' ? 'book' : undefined" in body, (
        "book mode is no longer bound to the Season tab"
    )


def test_only_the_season_tab_takes_the_mode():
    """Picks and the Board carry twenty games of red-and-green results and those two
    colours are the whole readout. Re-solving them against wood is real work and this
    change does not need it, so a second tab quietly opting in must fail here."""
    body = read("src", "App.jsx")
    line = [l for l in body.splitlines() if "? 'book'" in l]
    assert len(line) == 1, "expected exactly one place that decides book mode"
    for other in ("'picks'", "'board'", "'week'", "'admin'"):
        assert other not in line[0], (
            "%s is opting into book mode; only the Season tab may, until the good/bad "
            "pick colours are solved against wood" % other
        )


def test_the_chart_and_the_bars_lift_their_colours():
    """Three places put a seat colour on a dark ground in this mode, and all three were
    wrong on the first build: the chart lines in the felt well, the legend dots on wood,
    and the ranking bar fills in a wood track. A guard that checked one of them would
    have passed."""
    body = read("src", "screens", "Season.jsx")
    assert "from '../lib/onDark.js'" in body, "Season.jsx no longer lifts anything"
    assert body.count("onDark(") >= 3, (
        "expected onDark at all three dark-ground call sites (chart, legend, bars); "
        "found %d" % body.count("onDark(")
    )
    # The bars sit in --well, which is deeper than the felt, so they take their own ground.
    assert "onDark(p.color, '#241409')" in body, (
        "the ranking bars are being lifted against the felt rather than against the wood "
        "track they actually sit in"
    )
    assert "stroke={s.color}" not in body, "a chart line is still drawn in the raw seat colour"


def test_the_three_gradients_survive():
    """theme.css re-skins everything from flat tokens, which is most of the mode for free.
    These three cannot be tokens because a custom property here holds one colour, so they
    live in app.css and are the part that silently disappears if the block is trimmed."""
    css = read("src", "app.css")
    for sel, what in (
        (".app[data-mode='book'] {", "the wood grain on the case"),
        (".app[data-mode='book'] .apphdr", "the end grain on the header"),
        (".app[data-mode='book'] .tabbar", "the end grain on the tab bar"),
        (".app[data-mode='book'] .chartwrap", "the felt well the chart sits in"),
    ):
        assert sel in css, "%s is gone" % what
    # The plate is one rule covering three components; losing any one of them leaves a
    # flat brass rectangle next to two lit ones, which reads as a rendering bug.
    i = css.index(".app[data-mode='book'] .srow,")
    plate = css[i: css.index("}", i)]
    for cls in (".tile", ".wk"):
        assert cls in plate, "%s no longer gets the brass plate" % cls
