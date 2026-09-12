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
"""
from __future__ import annotations

import os
import re

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
    assert found, "no screen renders the scorebug at all any more"
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


def test_the_week_tab_still_has_both_of_its_call_sites():
    """The skeleton and the settled week. Named here rather than in the walk above,
    because the walk cannot know how many each screen is supposed to have."""
    sites = [f for f, _ in call_sites()]
    assert sites.count("Week.jsx") == 2, (
        "expected the scorebug at both Week call sites, the skeleton and the settled "
        "week; found %d" % sites.count("Week.jsx")
    )
    assert sites.count("Board.jsx") == 1, (
        "expected exactly one scorebug on the Board; found %d" % sites.count("Board.jsx")
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
