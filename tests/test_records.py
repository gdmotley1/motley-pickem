"""The gate for the record book.

Grant chose the seventeen entries off a ballot on 2026-09-12 and the layouts by number the
same evening: the trophy room for the Hall of fame (7), the red panel for the Hall of shame
(10), and ranked ladders for everyone's numbers (4, which replaced headlines once he saw
them live). The badges are his art, from ChatGPT.

The arithmetic runs under node in tests/records_check.mjs, against a three-player season
small enough to check on paper, including the half-played-week bug. What is asserted here
is the wiring, the art, the text floor, and the two rules that would be silently wrong:
that nothing reaches for the picks except through the RPC that can only see finished
games, and that a failed picks call cannot take the Season tab down.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK = os.path.join(ROOT, "tests", "records_check.mjs")
ART = os.path.join(ROOT, "src", "assets", "badges")

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not on PATH")


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


@needs_node
def test_the_record_arithmetic():
    proc = subprocess.run(
        [node, CHECK], capture_output=True, text=True, cwd=ROOT, timeout=60
    )
    assert proc.returncode == 0, "\n" + proc.stdout + proc.stderr


def test_the_screen_draws_all_three_parts_of_the_book():
    body = read("src", "screens", "Season.jsx")
    assert "seasonRecords(rows, picks, roster)" in body, "the Season tab is not building the book"
    for part in ("book.fame", "book.shame", "book.numbers"):
        assert part in body, "the Season tab no longer draws %s" % part
    # Order is the one Grant picked: fame, then shame, then everyone's numbers.
    at = [body.index("<HallOfFame"), body.index("<HallOfShame"), body.index("<Numbers")]
    assert at == sorted(at), "the three parts of the record book are out of order"


def test_a_failed_picks_call_cannot_take_down_the_season_tab():
    """The book is additive. Inside the Promise.all an erroring get_season_picks once
    replaced standings, form and everything else with an error message."""
    body = read("src", "screens", "Season.jsx")
    assert "api.getSeasonPicks().catch(" in body, (
        "the picks fetch no longer fails soft; one bad call blanks the whole Season tab"
    )


def test_the_picks_come_only_from_the_guarded_rpc():
    """get_season_picks is the only function that hands the client a season of pick_abbr
    and confidence, and it is safe because its join can only see finished games."""
    api = read("src", "lib", "api.js")
    assert "get_season_picks" in api, "api.js has no way to fetch the record book"
    pick_rpcs = set(re.findall(r"rpc\('(\w*(?:pick|board)\w*)'", api))
    assert pick_rpcs <= {"get_board", "save_picks", "get_season_picks", "my_picks"}, (
        "an unexpected pick-bearing RPC appeared in api.js: %s" % pick_rpcs
    )


def test_an_unclaimed_award_is_drawn_as_up_for_grabs():
    """Nobody has thrown a perfect week, so "Perfect week, 0, all four" would be an
    absence dressed as a statistic. It is an empty socket with a label instead."""
    body = read("src", "screens", "Season.jsx")
    assert "Up for grabs" in body, "unclaimed awards no longer say they are up for grabs"
    assert "a.claimed" in body, "the screen no longer tells a claimed award from an open one"


def test_the_record_book_css_has_no_tiny_text():
    """Grant, 2026-09-12: "Remember, I don't want any tiny text." The book before this one
    had 8.5px labels. Walks every font-size in the record book block, and the two labels
    elsewhere on the tab that were under the floor."""
    css = read("src", "app.css")
    start = css.index("the record book ==== */")
    block = css[start:]
    sizes = [float(s) for s in re.findall(r"font-size:\s*(\d+(?:\.\d+)?)px", block)]
    assert len(sizes) >= 15, "found only %d font sizes; did the block move?" % len(sizes)
    small = [s for s in sizes if s < 13]
    assert not small, "the record book has text under 13px: %s" % small

    # The standings' small label was .srow__ptslabel until they became trading cards.
    for klass in ("eyebrow", "scard__k"):
        rule = re.search(r"\n\.%s\s*\{(.*?)\}" % re.escape(klass), css, re.S)
        assert rule, ".%s is gone" % klass
        size = float(re.findall(r"font-size:\s*(\d+(?:\.\d+)?)px", rule.group(1))[-1])
        assert size >= 13, ".%s is %spx, under the 13px floor" % (klass, size)


def test_the_way_into_the_hall_of_fame_has_no_hard_edge():
    """Grant: "the transition from the season standings to the hall of fame is really
    rough." It was a near-black panel starting on a hard edge. The stage's background has
    to start transparent, so the dark comes up out of the page instead."""
    css = read("src", "app.css")
    rule = re.search(r"\n\.fame\s*\{(.*?)\n\}", css, re.S)
    assert rule, ".fame is gone"
    gradient = re.search(r"linear-gradient\(\s*180deg,\s*(rgba\([^)]*\)\s*\w*)", rule.group(1))
    assert gradient, "the stage no longer fades in from the top"
    assert re.fullmatch(r"rgba\([^)]*,\s*0\)\s*0(px)?", gradient.group(1).strip()), (
        "the stage's first colour stop is no longer transparent, so it starts on a hard "
        "edge under the standings again"
    )


Image = None
try:
    from PIL import Image  # noqa: F811
except ImportError:  # pragma: no cover
    pass
needs_pil = pytest.mark.skipif(Image is None, reason="pip install pillow")


@needs_pil
def test_every_badge_is_a_square_with_a_transparent_corner():
    files = sorted(f for f in os.listdir(ART) if f.endswith(".webp"))
    assert len(files) == 17, "expected 17 badges, found %d" % len(files)
    for name in files:
        im = Image.open(os.path.join(ART, name))
        assert im.size == (320, 320), "%s is %s, not 320x320" % (name, im.size)
        alpha = im.convert("RGBA").getchannel("A")
        assert alpha.getpixel((0, 0)) == 0, "%s has lost its transparent background" % name


@needs_pil
def test_the_shipped_badges_match_grants_art():
    """What ships is rebuilt from inputs/badges, byte for byte. A new PNG dropped into
    inputs without re-running the script would otherwise never reach a phone, and the
    tab would quietly keep the old art."""
    proc = subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "build_badges.py"), "--check"],
        capture_output=True, text=True, cwd=ROOT, timeout=180,
    )
    assert proc.returncode == 0, (
        "src/assets/badges is stale; run python scripts/build_badges.py\n" + proc.stdout
    )


def test_the_badge_list_is_the_same_in_the_script_and_the_book():
    """build_badges.py writes exactly the art the book can draw. Both lists are parsed out
    of their files rather than restated here."""
    script = read("scripts", "build_badges.py")
    ids = re.findall(r'"(\w+)"', script.split("IDS = [", 1)[1].split("]", 1)[0])
    lib = read("src", "lib", "seasonRecords.js")
    keys = re.findall(r"\{ key: '(\w+)'", lib)
    assert sorted(ids) == sorted(keys), (
        "scripts/build_badges.py and src/lib/seasonRecords.js disagree: %s"
        % sorted(set(ids) ^ set(keys))
    )


def test_the_game_icons_glyphs_are_gone():
    """The CC BY credit line was a condition of shipping game-icons.net artwork. That art
    is gone, so the credit went with it; this makes sure the art did not come back
    without it."""
    assert not os.path.exists(os.path.join(ROOT, "src", "lib", "badgeIcons.js"))
    for base, _dirs, files in os.walk(os.path.join(ROOT, "src")):
        for name in files:
            if name.endswith((".js", ".jsx")):
                assert "badgeIcons" not in read(os.path.relpath(os.path.join(base, name), ROOT)), (
                    "%s imports the old game-icons glyphs" % name
                )


def test_the_hall_of_fame_is_the_legends_poster():
    """Grant, 2026-09-13, off a board of five letterings: "lets do 5 but drop the record book
    part". HALL OF small over a huge slanted gold FAME in Anton, the awards and names in the
    same type, and no record book line above it."""
    season = read("src", "screens", "Season.jsx")
    assert '<span className="fame__t1">Hall of</span> <span className="fame__t2">fame</span>' in season
    # The rendered line, not the words: a comment elsewhere in the file says "The record book".
    assert ">The record book<" not in season and "book-kick" not in season, (
        "the record book line is back above the Hall of fame"
    )
    assert "__fame" not in season, "the lettering board's switch shipped"

    css = re.sub(r"/\*.*?\*/", "", read("src", "app.css"), flags=re.S)
    title = re.search(r"\n\.fame__title\s*\{(.*?)\}", css, re.S).group(1)
    assert "font-family: 'Anton'" in title, "the Hall of fame title is not in Anton"
    assert "skewX" in title
    big = re.search(r"\n\.fame__t2\s*\{(.*?)\}", css, re.S).group(1)
    assert float(re.findall(r"font-size:\s*(\d+)px", big)[-1]) >= 100, "FAME is no longer the huge line"
    for sel in (".award__k", ".fame__sub", ".grab p"):
        rule = re.search(r"\n%s\s*\{(.*?)\}" % re.escape(sel), css, re.S).group(1)
        assert "'Anton'" in rule, "%s is not in the poster's type" % sel
    # The Hall of shame shares .hold; only the Hall of fame's holders change.
    assert re.search(r"\n\.fame \.hold\s*\{[^}]*'Anton'", css), "the fame holders lost their type"
    assert "'Anton'" not in re.search(r"\n\.hold\s*\{(.*?)\}", css, re.S).group(1), (
        "the base .hold rule changed, which restyles the Hall of shame too"
    )
    assert "fame--v" not in css and ".book-kick" not in css, "the lettering board's rules shipped"
    assert re.search(r"\n\.fame\s*\{[^}]*overflow:\s*hidden", css), (
        "the burst of light behind the title is 520px wide; without overflow hidden the page scrolls sideways"
    )

    link = re.search(r'href="(https://fonts\.googleapis\.com/css2[^"]+)"', read("index.html")).group(1)
    assert "family=Anton" in link, "index.html does not load Anton, so the poster falls back to Impact"


def test_the_hall_of_fame_names_carry_no_team_logo():
    """Grant, 2026-09-25: "can we drop the logo from our team and just put the players
    name?" Under a badge on the lit stage the school mark was a second logo competing with
    the one the award is about. The Hall of shame keeps its faces, so the guard is that
    <Holders> can still draw them and that the fame is the caller opting out."""
    season = read("src", "screens", "Season.jsx")
    fame = season.split("function HallOfFame", 1)[1].split("function HallOfShame", 1)[0]
    assert "<Avatar" not in fame, "the Hall of fame is drawing a team logo again"
    assert re.search(r"<Holders people=\{a\.holders\} faces=\{false\}", fame), (
        "the Hall of fame's holders no longer opt out of the faces"
    )
    shame = season.split("function HallOfShame", 1)[1].split("\nfunction ", 1)[0]
    assert re.search(r"<Holders people=\{a\.holders\}(?![^/>]*faces)", shame), (
        "the Hall of shame lost its faces too; Grant only asked about the Hall of fame"
    )
    assert "hold__faces" in season, "the faces markup is gone, so the Hall of shame cannot draw them"


def test_the_trophy_room_lines_up():
    """Grant, 2026-09-25: "try to make everything uniform, like stuff being lined up ... take
    off the 'in a week' line on biggest margin of victory so it even".

    Three things hold it: the label is short enough to take two lines in a 178px card, two
    lines are held open so a one-line award does not ride up, and the two cards on a row are
    one subgrid so the badge, award, name and detail share a line even when a name wraps.
    Measured in outputs/harness at 390 and 375: every drift 0.0px, both branches of is-odd."""
    lib = read("src", "lib", "seasonRecords.js")
    fame = lib.split("export const FAME", 1)[1].split("]", 1)[0]
    labels = re.findall(r"label: '([^']+)'", fame)
    assert labels, "the Hall of fame list moved"
    # 25 chars is "Biggest margin of victory", the longest that still takes two lines in a
    # card at 390px. The 35-char version it replaced took three and was the one Grant saw.
    long = [x for x in labels if len(x) > 26]
    assert not long, "these award names will run to a third line in a card: %s" % long

    css = re.sub(r"/\*.*?\*/", "", read("src", "app.css"), flags=re.S)
    sub = re.search(r"@supports \(grid-template-rows: subgrid\)\s*\{\s*\.fame__won > \.award\s*\{(.*?)\}", css, re.S)
    assert sub, "the trophy room's cards are no longer a subgrid, so a wrapped name breaks the row"
    rule = sub.group(1)
    for want in ("grid-template-rows: subgrid", "grid-row: span 4", "row-gap: 0", "align-items: start"):
        assert want in rule, "the subgrid card lost %s" % want

    award = re.search(r"\n\.award__k\s*\{(.*?)\}", css, re.S).group(1)
    line = float(re.search(r"line-height:\s*([\d.]+)", award).group(1))
    hold = float(re.search(r"min-height:\s*([\d.]+)em", award).group(1))
    assert hold >= line * 2 - 0.01, (
        "the award name no longer holds two lines open, so Perfect week rides a line up"
    )
    grab = re.search(r"\n\.grab p\s*\{(.*?)\}", css, re.S).group(1)
    assert "min-height" in grab, "the up for grabs cells can step up and down again"
