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


def test_the_chart_lifts_its_colours():
    """Two places still put a seat colour on a dark ground: the chart lines in the well
    and the legend dots beside it. There were three until the ranking bars were cut on
    2026-09-11; the guard said three and correctly failed when one went away, which is
    the whole reason to spell the number out rather than write >= 1."""
    body = read("src", "screens", "Season.jsx")
    assert "from '../lib/onDark.js'" in body, "Season.jsx no longer lifts anything"
    assert body.count("onDark(") == 2, (
        "expected onDark at both dark-ground call sites, the chart and the legend; "
        "found %d" % body.count("onDark(")
    )
    assert "stroke={s.color}" not in body, "a chart line is still drawn in the raw seat colour"


def test_book_mode_re_resolves_the_inherited_text_colour():
    """`body` sets `color: var(--ink)` and resolves it against Slate's near-black. Custom
    properties cascade into this subtree; an already-computed `color` does not re-resolve,
    so without this line the whole screen inherits Slate's dark ink onto dark wool.

    It was invisible under the wood palette because the plates were light brass and dark
    ink was correct on them. Wool made every surface dark and the title, three of the four
    names and every number on a badge went dark-on-dark at once.
    """
    css = read("src", "app.css")
    i = css.index(".app[data-mode='book'] {")
    block = css[i: css.index("}", i)]
    assert "color: var(--ink)" in block, (
        "the book scope no longer re-resolves `color`, so everything that does not set "
        "its own colour will inherit Slate's ink onto dark wool"
    )


def test_no_section_of_app_css_is_duplicated():
    """This shipped. Three byte-identical copies of the BOOK MODE block and three
    different record-book blocks were live on 2026-09-11, two of them dead code, because
    an index-based edit inserted where it meant to replace and nobody looked.

    Duplicate CSS is not a style problem: the last copy silently wins, so editing the
    first one changes nothing and the next person loses an hour to it.
    """
    css = read("src", "app.css")
    for marker in (
        "BOOK MODE  ·  the trophy case",
        "BOOK MODE  ·  what a flat token cannot say",
        "the record book ==== */",
        "the week's scorebug ==== */",
        "==== standings",
    ):
        n = css.count(marker)
        assert n <= 1, (
            "%r appears %d times in app.css. A duplicated section means the last copy "
            "wins and edits to the others do nothing." % (marker, n)
        )


def test_the_wool_and_the_chart_well_survive():
    """theme.css re-skins everything from flat tokens, which is most of the mode for free.
    What a custom property cannot hold lives in app.css and is the part that silently
    disappears if the block is trimmed.

    The header's and tab bar's own wool went on 2026-09-13, when every tab took the
    jumbotron's black header, and the standings became trading cards on the jumbotron the
    same day (tests/test_jumbotron_everywhere.py), so neither is book mode's any more."""
    css = read("src", "app.css")
    for sel, what in (
        (".app[data-mode='book'] {", "the wool on the case"),
        (".app[data-mode='book'] .chartwrap", "the well the chart sits in"),
    ):
        assert sel in css, "%s is gone" % what
    for gone in (".app[data-mode='book'] .apphdr", ".app[data-mode='book'] .tabbar"):
        assert gone not in css, "%s is back: Season would wear a different header from every other tab" % gone
