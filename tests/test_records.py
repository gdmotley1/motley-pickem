"""The gate for the record book.

Grant chose the content on 2026-09-11: all four groups, and every record shows the holder
plus the chasing pack so that everybody sees where THEY are rather than only learning who
won it. That last part is a structural promise, not a styling choice, and it is what most
of tests/records_check.mjs is about.

The arithmetic runs under node there, against a hand-made three-player, three-week season
small enough to check on paper. What is asserted here is the wiring, and the two rules
that would be silently wrong: that the screen renders every group the library emits, and
that nothing reaches for the picks except through the one RPC that can only see finished
games.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK = os.path.join(ROOT, "tests", "records_check.mjs")

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


def test_every_group_the_library_emits_is_rendered():
    """Walked, not listed. A record whose group no section renders is computed, shipped
    in the bundle and invisible, and nothing about the screen looks broken. This reads the
    group names out of the library and requires each one to appear in GROUPS, which is
    what the screen maps over.
    """
    lib = read("src", "lib", "seasonRecords.js")
    emitted = set(re.findall(r"record\('[\w]+', '(\w+)'", lib))
    assert emitted, "no records are being emitted at all; has record() been renamed?"

    declared = set(re.findall(r"\['(\w+)', '[^']+'\]", lib.split("export const GROUPS")[1]))
    missing = emitted - declared
    assert not missing, (
        "these record groups are computed but no section renders them: %s"
        % ", ".join(sorted(missing))
    )
    unused = declared - emitted
    assert not unused, (
        "GROUPS declares %s but nothing is in it, so the screen will draw an empty heading"
        % ", ".join(sorted(unused))
    )


def test_the_screen_renders_the_book():
    body = read("src", "screens", "Season.jsx")
    assert "seasonRecords" in body, "the Season tab is not computing the record book"
    assert "GROUPS" in body, (
        "the screen is not mapping over GROUPS, so a new group would never appear"
    )
    assert "getSeasonPicks" in body or "picks" in body, "nothing fetches the picks"


def test_the_picks_come_only_from_the_guarded_rpc():
    """get_season_picks is the only function that can hand the client a whole season of
    pick_abbr and confidence, and it is safe because its join can only see finished games.
    A second route to the same data would not have that guarantee."""
    api = read("src", "lib", "api.js")
    assert "get_season_picks" in api, "api.js has no way to fetch the record book"
    # get_board is the only other function that returns picks, and it is per-week.
    pick_rpcs = set(re.findall(r"rpc\('(\w*(?:pick|board)\w*)'", api))
    assert pick_rpcs <= {"get_board", "save_picks", "get_season_picks", "my_picks"}, (
        "an unexpected pick-bearing RPC appeared in api.js: %s" % pick_rpcs
    )


def test_records_never_invent_a_value_for_someone_it_does_not_apply_to():
    """Nicole has no school, so Homer has nothing to say about her. Returning zero would
    sort her last and read as her being worst at it. The library returns null and sorts
    nulls last; this pins the behaviour in the source so it cannot be 'simplified' away."""
    lib = read("src", "lib", "seasonRecords.js")
    assert "value == null" in lib, "the null handling in standing() is gone"
    assert "nulls sort last" in lib.lower() or "Nulls sort last" in lib, (
        "the reason nulls sort last is no longer written down"
    )
