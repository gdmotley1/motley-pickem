"""The gate for the record book.

Grant chose the seventeen entries off a ballot on 2026-09-12 and the layouts by number the
same evening: headlines for everyone's numbers (6), the trophy room for the Hall of fame
(7), the red panel for the Hall of shame (10). The badges are his art, from ChatGPT.

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

    for klass in ("eyebrow", "srow__ptslabel"):
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
