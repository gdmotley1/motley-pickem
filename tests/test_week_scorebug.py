"""The gate for the app's scoreboard.

Two decisions live here and both were reached by looking rather than reasoning.

The Week tab used to have its own light standings table. It now renders the same
<WeekScore> the Board does, reading the same weekScore() object, so the two screens cannot
drift about who is where.

And there is exactly ONE cut of it. For a day the Board took dark chrome with no record
column and the Week tab took the light cut with one, each with a real argument behind it.
Grant looked at the two side by side on 2026-09-11 and asked for them to match, so every
call site now passes `light` and `record`. The guards below walk the call sites rather
than naming Board and Week, so a third screen cannot quietly reintroduce a second look.

On 2026-09-12 two more joined them, both off Grant's phone on a live Saturday: a record
column that went ragged the first time one score had more digits than the rest, and a
two-pixel progress strip he could hardly see, replaced by the broadcast rail he picked.
"""
from __future__ import annotations

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def rules(css):
    """Every (selector, declarations) pair in a stylesheet, comments dropped.

    Walked rather than looked up by name, so a rule on the row added anywhere else in the
    file is checked as well. Inside @media or @keyframes the selector is the innermost one.
    """
    while "/*" in css:
        start = css.index("/*")
        css = css[:start] + css[css.index("*/", start) + 2:]
    found = []
    for chunk in css.split("}"):
        if "{" not in chunk:
            continue
        head, body = chunk.rsplit("{", 1)
        found.append((head.split("{")[-1].strip(), body))
    return found


def test_no_row_column_is_sized_by_its_own_content():
    """Nicole scored first on 2026-09-12 and her record sat 11.9px left of everyone else's.

    Each .bugrow is its own grid, so an `auto` track is sized to that one row's content: a
    two-digit score beside three one-digit scores drags every column to its left inboard on
    that row alone. Every track has to be a fixed length or the name's `1fr`."""
    grids = [
        (sel, body) for sel, body in rules(read("src", "app.css"))
        if ".bugrow" in sel and "grid-template-columns" in body
    ]
    assert grids, "no rule lays out the scorebug row any more; has it been renamed?"

    # Fixed cells only line up if every row fills the same cells. The skeleton used to
    # skip the record, which under fixed columns slides its dash 38px left of where the
    # score appears once the week starts: measured on the real component, 2026-09-12.
    jsx = read("src", "components", "WeekScore.jsx")
    at = jsx.index('className="bugrow__rec num"')
    condition = jsx[jsx.rindex("{record", 0, at):at]
    assert "skeleton" not in condition, (
        "the record cell is conditional on the skeleton again; a skeleton row must keep "
        "the cell, empty, or its dash leaves the score column"
    )

    for sel, body in grids:
        value = body.split("grid-template-columns:")[1].split(";")[0]
        for content_sized in ("auto", "min-content", "max-content", "fit-content"):
            assert content_sized not in value, (
                "%s sizes a column by its own row's content (%s). The columns go ragged "
                "the moment one score has more digits than the rest." % (sel, value.strip())
            )


def test_the_rail_can_be_seen_and_keeps_its_stripe():
    """Grant on the old 2px strip, 2026-09-12: "you can hardly see it. It looks bad." He
    picked the broadcast rail. It quietly goes back to looking broken two ways: somebody
    thins it, or the inline colour moves to the `background` shorthand, which resets
    background-image and deletes the stripe that tells a live run from a banked one."""
    css = rules(read("src", "app.css"))
    rail = [body for sel, body in css if sel == ".bugrail"]
    assert rail, "the rail is gone"
    height = int(rail[0].split("height:")[1].split("px")[0])
    assert height >= 10, "the rail is back down to %dpx" % height

    live = [body for sel, body in css if sel == ".bugrail__live"]
    assert live and "repeating-linear-gradient" in live[0], (
        "the live run lost its stripe, so it reads as banked"
    )

    jsx = read("src", "components", "WeekScore.jsx")
    rail_jsx = jsx[jsx.index('className="bugrail"'):]
    rail_jsx = rail_jsx[: rail_jsx.index("</span>")]
    assert "background:" not in rail_jsx, (
        "the rail's colour is set with the `background` shorthand, which wipes the "
        "stripe; use backgroundColor"
    )
    assert "backgroundColor: p.color" in rail_jsx, (
        "the rail no longer takes the player's colour"
    )


def test_gold_on_the_rail_only_sits_on_the_dark_well():
    """--lead measures 10.8:1 on --field-deep and about 1.5:1 on a light card. The leader's
    cap on the rail is the one place gold appears on the light cut, and that is only
    allowed because the light cut's well is --field-deep."""
    css = rules(read("src", "app.css"))
    cap = [body for sel, body in css if sel == ".bugrow.is-leader .bugrail::after"]
    assert cap and "var(--lead)" in cap[0], "the leader's rail lost its gold cap"
    well = [body for sel, body in css if sel == ".bug--light .bugrail"]
    assert well and "var(--field-deep)" in well[0], (
        "the light cut's rail is not on --field-deep, so its gold cap cannot be read"
    )



def test_the_week_tab_leaves_the_live_week_to_the_board():
    """Grant, 2026-09-12: the Week tab shows finished weeks only, so the live scoreboard is
    the Board's alone. Until then the tab carried the bug too (asked for on 2026-09-10), in
    a skeleton and a week-in-progress branch. The finished table still reads the same
    `weekScore` object, so the two screens cannot disagree about who is where."""
    body = read("src", "screens", "Week.jsx")
    assert "<WeekScore" not in body, "the Week tab is drawing a live scoreboard again"
    assert "weekScore(graded.games, graded.rows, roster)" in body, (
        "the Week tab is deriving its own standings instead of reading weekScore"
    )
    assert "function Standings" not in body and "<Standings" not in body, (
        "the old light standings table is back; it and the bug would drift"
    )


def test_the_skeleton_shows_no_numbers_and_no_rank():
    """Everyone ties on zero before a game finishes, so a real rank prints "1" four times
    and a real score prints four zeroes. Both read as data rather than as an empty
    frame."""
    body = read("src", "components", "WeekScore.jsx")
    assert "{!skeleton && <span className=\"bugrow__seed num\">" in body, (
        "the skeleton is printing a rank nobody holds"
    )
    assert "{skeleton ? '—' : p.points}" in body, "the skeleton is printing scores"


def call_sites():
    """Every <WeekScore ... /> in every screen, as (screen, props-text) pairs.

    Walked, never enumerated. The version of this that named Board.jsx and Week.jsx by
    hand would have passed happily while a third screen shipped a fourth look.
    """
    found = []
    screens = os.path.join(ROOT, "src", "screens")
    for fname in sorted(os.listdir(screens)):
        if not fname.endswith(".jsx"):
            continue
        body = read("src", "screens", fname)
        for chunk in body.split("<WeekScore")[1:]:
            assert "/>" in chunk, "%s has a <WeekScore> that never closes" % fname
            found.append((fname, chunk.split("/>")[0]))
    # Empty since 2026-09-12: the Week tab shows finished weeks only and the Board became the
    # jumbotron, so no screen draws the scorebug card. Its pinned strip, ScoreBug, is still
    # the Board's. An empty walk is the expected answer now, not a broken one.
    return found


def test_the_record_column_stays_opt_in_in_the_css():
    """Every call site asks for it, but the cost stays visible at one selector rather than
    being folded into .bugrow, because a fifth column is what spends the name's width."""
    css = read("src", "app.css")
    assert ".bug--rec .bugrow" in css, "the record column is no longer opt-in"


def test_every_call_site_takes_the_same_cut():
    """Grant asked on 2026-09-11 for the Board's scoreboard to match the Week tab's. There
    is one scoreboard in this app: every call site passes both `light` and `record`, or
    two screens are showing the same numbers in two different skins again."""
    for fname, props in call_sites():
        for want in ("light", "record"):
            assert want in props, (
                "%s renders the scorebug without `%s`; every call site takes the light "
                "cut with the record column" % (fname, want)
            )


def test_no_screen_draws_the_old_scorebug_card():
    """The Week tab shows finished weeks only and the Board is the jumbotron, both since
    2026-09-12, and both read weekScore directly. A <WeekScore> card turning up on any
    screen again means two looks for one scoreboard. Walked, so a new screen counts too."""
    assert call_sites() == [], "a screen is drawing the old scorebug card again: %s" % [f for f, _ in call_sites()]


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


def test_the_skeleton_never_washes_out_what_is_already_known():
    """Grant called this on 2026-09-11: "dont grey out the current week colors".

    The skeleton draws for a published week with nothing final, which on the Week tab is
    the whole first half of every week, and it was desaturating each player's colour
    block and fading their name. Both are known long before kickoff. Dimming them says
    "provisional" about the one part of the row that is already certain, and it is the
    state the tab spends most of its life in.

    Only the score may dim, and only because it is rendering a dash.
    """
    css = read("src", "app.css")
    skeleton = [
        block for block in re.split(r"\n(?=\S)", css)
        if ".bugrow.is-skeleton" in block
    ]
    assert skeleton, "the skeleton no longer styles anything; has it been renamed?"
    body = "\n".join(skeleton)

    assert "filter:" not in body, (
        "the skeleton applies a filter again. saturate() on .bugrow__block is what "
        "washed out the team colours."
    )
    assert ".bugrow__name" not in body, (
        "the skeleton dims the player's name again; a name is known before kickoff"
    )
    assert ".bugrow__block" not in body, (
        "the skeleton styles the colour block again; its colour is known before kickoff"
    )
    assert ".bugrow__pts" in body, (
        "nothing marks the score as absent. The dash should stay dimmed."
    )
