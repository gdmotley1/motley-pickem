"""The wording Grant marked on the copy audit, held so it cannot quietly come back.

On 2026-09-14 he asked for an audit of "how things read", starting with "Went it alone"
("what is that. should be like went at it alone"), and marked twelve of its lines Change it
and one Keep it (https://claude.ai/code/artifact/6a71d168-1c73-4ee4-82d2-dc7239d89ec9). The
changes were not built until 2026-09-21, when he found the old wording still live.

The old phrases are banned from every file under src/, not from the one file each lived in,
so a line moved to another component is still caught. The arithmetic behind the new lines is
in tests/recap_check.mjs (who called which upset) and tests/records_check.mjs (the lost 20s).
"""
from __future__ import annotations

import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Old wording -> why it went. Each was on the audit and marked Change it.
BANNED = {
    "Went it alone": "the heading is Grant's own wording now: Went at it alone",
    "and how they went": "the line under Went at it alone is just who made the picks",
    "Went with somebody every time": "someone with no solo picks says No solo picks",
    "Had {pick}": "every other screen says Picked",
    "Nobody had ": "every other screen says picked",
    "times the lead changed hands": "the fact reads as a heading: Lead changes",
    "took the lead for good, at ": "the game goes on its own line: Game 14 of 20, TTU at ORST",
    "the most of anyone": "More than anyone goes on its own line",
    "finished next to you": "false for 3rd and 4th, who are compared with the winner",
    "`your ${": "You got 8, James got 17",
    "'you missed'": "You missed, capitalised like the rest of the line",
    "all four of you picked the same team": "Games you all picked the same team",
    "} held<": "3 won",
    "didn&rsquo;t<": "4 lost",
    "points between you, all gone": "Cost you 70 points combined",
    "Ties stand, so a week can be shared": "fine print; a shared week says Co-winners where it happens",
    ">Back<": "Behind, which cannot be read as a button",
    ".join(' & ')": "commas, then one ampersand: Grant, Parker & Nicole",
    "'none yet'": "None yet, capitalised like the name above it",
    "'no misses yet'": "No misses yet, capitalised like the name above it",
    "`on ${w.team}`": "the stake is the number column, so the note is the team alone",
}


def src_files():
    for base, _dirs, names in os.walk(os.path.join(ROOT, "src")):
        for name in names:
            if name.endswith((".js", ".jsx")):
                yield os.path.join(base, name)


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def test_the_old_wording_is_gone_from_every_screen():
    found = []
    files = list(src_files())
    assert len(files) > 20, "the walk found almost nothing under src/"
    for path in files:
        with open(path, encoding="utf-8") as f:
            body = f.read()
        for phrase, why in BANNED.items():
            if phrase in body:
                found.append("%s: %r is back (%s)" % (os.path.relpath(path, ROOT), phrase, why))
    assert not found, "\n".join(found)


def test_the_new_wording_is_what_grant_picked():
    week = read("src", "screens", "Week.jsx")
    for phrase in (
        ">Went at it alone<",
        'help="Picks nobody else in the family made."',
        "won, ${p.picks.length - p.right} lost",
        "'No solo picks'",
        "Picked {pick}",
        "Nobody picked {u.winner}",
        "'Lead changes'",
        "Game {race.lockedAt} of {steps.length}, {locked.label}",
        "'More than anyone'",
        "who won the week.",
        "`You got ${d.mine.confidence}`",
        "`${rival} got ${d.theirs.confidence}`",
        "'Games you all picked the same team'",
        "{held.length} won",
        "{burned.length} lost",
        "Cost you {a.total} points combined",
        "calledLine(called)",
    ):
        assert phrase in week, "the Week tab lost %r" % phrase
    season = read("src", "screens", "Season.jsx")
    assert ">Behind<" in season
    assert "in the books.`" in season
    records = read("src", "lib", "seasonRecords.js")
    assert "worst_miss: 'No misses yet'" in records
    assert "detail: w.team }" in records


def test_the_line_grant_kept_is_still_there():
    """Decided it was the one line he marked Keep it."""
    week = read("src", "screens", "Week.jsx")
    assert "<Title>Decided it</Title>" in week
    assert "Nothing did on its own." in week
