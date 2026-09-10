# -*- coding: utf-8 -*-
"""Render six type and colour treatments for the AP rank, in all three real contexts.

Grant chose option A from build_rank_board.py (nothing reserved for an unranked team) and
asked for choices on how the number itself should look.

    python scripts/build_rankstyle_board.py            # -> outputs/rankstyle-board.html

Each option is shown on a Board row, a Setup row and a pair of Picks tiles, because the
rank sits at three different sizes against three different backgrounds and a treatment
that works on one can disappear on another.

Real data: the live AP poll against the real Week 2 slate.

One thing the board exists to fix. `.aprank` sets no font-family, so today it inherits
Inter on the Board and in Setup and Archivo on the Picks tiles: the same number in two
typefaces depending on the screen. Every option below sets the face explicitly.
"""
from __future__ import annotations

import argparse
import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_recap_board import CSS as BASE_CSS  # noqa: E402
from build_theme_board import logo_uri  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (away, away_id, away_rank, home, home_id, home_rank, line)
BOARD = [
    ("OSU", "194", 1, "TEX", "251", 4, "TEX -1.5"),
    ("MIZ", "142", 23, "KU", "2305", None, "MIZ -5.5"),
    ("DUKE", "150", None, "ILL", "356", None, "ILL -6.0"),
]
SETUP = ("WKU", "98", None, "UGA", "61", 2, "UGA -40.5")
TILES = [("Alabama", "333", 12, True), ("Kentucky", "96", None, False)]


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def logo(team_id: str, size: int = 22) -> str:
    uri = logo_uri(team_id)
    if not uri:
        return '<span class="lg" style="width:%dpx;height:%dpx"></span>' % (size, size)
    return '<img class="lg" src="%s" width="%d" height="%d" alt="">' % (uri, size, size)


def rank(opt: str, n) -> str:
    if not n:
        return ""
    hashless = {"B", "C", "D", "E"}
    body = ("" if opt in hashless else '<i class="h">#</i>') + str(n)
    return '<span class="rk rk--%s">%s</span>' % (opt.lower(), body)


def side(opt: str, abbr: str, tid: str, n) -> str:
    return '<span class="side">%s%s%s</span>' % (logo(tid), rank(opt, n), esc(abbr))


def card(opt: str, title: str, spec: str, note: str) -> str:
    rows = "".join(
        '<div class="brow"><div class="brow__top">%s<span class="at">@</span>%s</div>'
        '<div class="brow__meta"><span class="chip">%s</span></div></div>'
        % (side(opt, g[0], g[1], g[2]), side(opt, g[3], g[4], g[5]), esc(g[6]))
        for g in BOARD)
    a, aid, ar, h, hid, hr, line = SETUP
    setup = ('<div class="srow2"><span class="box">&#10003;</span>'
             '<span class="srow2__body"><span class="srow2__match">%s<span class="at">@</span>%s</span>'
             '<span class="srow2__meta"><span class="chip">%s</span></span></span></div>'
             % (side(opt, a, aid, ar), side(opt, h, hid, hr), esc(line)))
    tiles = "".join(
        '<div class="tile2%s">%s<span class="tile2__name">%s%s</span></div>'
        % (" is-picked" if picked else "", logo(tid, 34), rank(opt, n), esc(school))
        for school, tid, n, picked in TILES)
    return """
<figure class="opt">
  <figcaption class="opt__cap">%s</figcaption>
  <p class="opt__spec">%s</p>
  <div class="phone">
    <div class="phone__body">
      <div class="screen"><p class="eyebrow">Board</p></div>
      <div class="rows">%s</div>
      <div class="screen"><p class="eyebrow" style="margin-top:12px">Setup</p></div>
      <div class="rows">%s</div>
      <div class="screen"><p class="eyebrow" style="margin-top:12px">Picks</p></div>
      <div class="tiles2">%s</div>
    </div>
  </div>
  <p class="opt__note">%s</p>
</figure>""" % (esc(title), esc(spec), rows, setup, tiles, esc(note))


EXTRA_CSS = """
/* build_recap_board's phone block defines --display but not --ui, so `var(--ui)` here was
   invalid at computed-value time and every option that asked for it silently fell back to
   inheritance: Inter on the board rows, Archivo inside the tile. Which is precisely the
   app bug this page is meant to show the fix for, reproduced by accident. */
.phone{--ui:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif}
.opt{width:352px}
.opt__spec{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:10.5px;
  color:var(--mark);margin:2px 2px 11px;font-weight:600;line-height:1.5}
.opt__note{margin-top:10px}
.phone{height:auto;min-height:0;padding-bottom:12px}
.phone .rows{padding:0 12px;display:grid;gap:7px}
.phone .brow,.phone .srow2{background:var(--card);border:1px solid var(--line);
  border-radius:var(--r-lg);padding:10px 12px;box-shadow:var(--sh-1)}
.phone .brow__top,.phone .srow2__match{display:flex;align-items:center;gap:6px;
  font-weight:700;font-size:13px}
.phone .brow__meta,.phone .srow2__meta{display:flex;gap:5px;margin-top:6px}
.phone .at{color:var(--ink-3);font-weight:600;font-size:12px}
.phone .side{display:inline-flex;align-items:center;gap:6px;min-width:0}
.phone .lg{display:block;object-fit:contain}
.phone .srow2{display:flex;align-items:center;gap:10px}
.phone .box{width:20px;height:20px;border-radius:5px;border:1.5px solid var(--line-strong);
  flex:none}
.phone .srow2__body{flex:1;min-width:0}
.phone .tiles2{padding:0 12px;display:grid;grid-template-columns:1fr 1fr;gap:8px}
.phone .tile2{background:var(--card);border:1px solid var(--line);border-radius:var(--r-lg);
  padding:11px 10px;display:flex;flex-direction:column;align-items:center;gap:7px}
.phone .tile2.is-picked{border-color:var(--pick-edge);background:var(--pick-wash);
  box-shadow:inset 0 0 0 1px var(--pick-edge)}
.phone .tile2__name{font-family:var(--display);font-size:12.5px;font-weight:700;
  text-align:center}

/* every option sets the face explicitly; that is half the point */
.phone .rk{font-variant-numeric:tabular-nums;flex:none}
.phone .rk .h{font-style:normal;opacity:.6}

/* A: as it ships today, but with the face pinned */
.phone .rk--a{font-family:var(--ui);font-size:10px;font-weight:800;color:var(--accent);
  margin-right:3px}
.phone .side .rk--a{margin-right:0}

/* B: quiet grey, no hash */
.phone .rk--b{font-family:var(--ui);font-size:10.5px;font-weight:700;color:var(--ink-3);
  margin-right:3px}
.phone .side .rk--b{margin-right:0}

/* C: the display face, matching the team names */
.phone .rk--c{font-family:var(--display);font-size:11.5px;font-weight:700;
  color:var(--accent);margin-right:3px}
.phone .side .rk--c{margin-right:0}

/* D: a solid chip */
.phone .rk--d{font-family:var(--ui);font-size:9px;font-weight:800;color:var(--on-field);
  background:var(--field);border-radius:4px;padding:1px 4px;line-height:1.5;
  margin-right:4px}
.phone .side .rk--d{margin-right:1px}

/* E: outlined */
.phone .rk--e{font-family:var(--ui);font-size:9px;font-weight:800;color:var(--accent-deep);
  border:1px solid var(--accent-bright);border-radius:4px;padding:0 3px;line-height:1.6;
  margin-right:4px}
.phone .side .rk--e{margin-right:1px}

/* F: poll gold against the cool palette */
.phone .rk--f{font-family:var(--ui);font-size:10px;font-weight:800;color:#a8710d;
  margin-right:3px}
.phone .side .rk--f{margin-right:0}
"""


def build() -> str:
    opts = [
        ("A", "A · What ships today",
         "Inter 10px / 800 · --accent · faded #",
         "The current look, with the typeface pinned so it stops changing between screens. "
         "Blue is already carrying the eyebrow, every spread, the lock notice and the "
         "leader row, so the rank joins a crowd."),
        ("B", "B · Quiet grey, no hash",
         "Inter 10.5px / 700 · --ink-3 · no #",
         "Drops out of the way and lets the crest and the name lead. The rank becomes "
         "something you read when you look for it. Least likely to ever feel out of "
         "place, and the easiest to miss."),
        ("C", "C · The display face",
         "Archivo 11.5px / 700 · --accent · no #",
         "The same typeface as the team names beside it, one step down in size. Reads as "
         "part of the name rather than an annotation bolted to it. The most typographic "
         "of the six."),
        ("D", "D · A solid chip",
         "Inter 9px / 800 · white on --field · 4px radius",
         "Unmistakably a rank and impossible to confuse with a score or a spread. It also "
         "adds a third filled shape to a row that already has a crest and a chip, which "
         "is the risk."),
        ("E", "E · Outlined",
         "Inter 9px / 800 · --accent-deep on a hairline box",
         "The chip's shape without its weight. Holds together on both the white card and "
         "the blue picked tile. Two hairlines on one row can read as busy at 9px."),
        ("F", "F · Poll gold",
         "Inter 10px / 800 · warm amber · faded #",
         "The one option that is not blue. Against a deliberately cool palette a warm "
         "number reads instantly as its own kind of information, and it is the only "
         "treatment here that never competes with the pick state. Needs a new semantic "
         "token in theme.css, which is a four-line change."),
    ]
    cards = "".join(card(k, t, spec, note) for k, t, spec, note in opts)
    return """<title>AP Rank Styling</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;600;700&family=Inter:wght@400;600;700;800&display=swap">
<style>%s%s</style>

<div class="wrap">
  <p class="doc__eyebrow">Motley Pick'em &middot; design options</p>
  <h1 class="doc__title">How the rank should look</h1>
  <p class="doc__sub">Six treatments, each on a Board row, a Setup row and a pair of Picks
  tiles, because the rank sits at three sizes against three backgrounds and something that
  works on a white card can vanish on a blue one. Live AP poll, real Week 2 slate.</p>

  <section>
    <h2 class="sec__h">A bug worth knowing about first</h2>
    <div class="callout"><p><b>The rank is currently in two different typefaces.</b>
    <code>.aprank</code> sets no font-family, so it inherits: Inter on the Board and in
    Setup, Archivo on the Picks tiles. Nobody would spot it side by side, and it is exactly
    the kind of thing that makes a component feel not quite right. Every option below sets
    the face explicitly, so picking any of them fixes it.</p></div>
  </section>

  <section>
    <h2 class="sec__h">The six</h2>
    <div class="row">%s</div>
  </section>

  <section>
    <h2 class="sec__h">The recommendation</h2>
    <div class="rec">
      <h3>C, or F if you want the rank to stand on its own</h3>
      <p><b>C</b> is the one I would build. Setting the rank in Archivo, the same face as
      the team name it is attached to, is what stops it looking bolted on. At 11.5px
      against a 13px name it reads as part of the same object rather than an annotation,
      and dropping the # removes a character that was only ever there to explain what the
      number meant.</p>
      <p><b>F</b> is the interesting one. Everything on this palette is blue: the eyebrow,
      every spread, the lock notice, the leader row, the pick state. A warm number is the
      only treatment here that is instantly its own kind of information and can never be
      mistaken for a selection. It costs a new semantic token, which
      <code>memory/ui-patterns.md</code> already records as a change you were considering
      anyway.</p>
      <p><b>B</b> is the safe pick if the honest answer is that the rank is nice to have
      rather than something you use. It will never look wrong.</p>
      <p><b>The one to avoid is D.</b> On the Board a row already carries two crests and a
      spread chip; a filled badge makes three competing shapes, and at 9px the white
      number on slate is the least legible of the six.</p>
    </div>
  </section>
</div>
""" % (BASE_CSS, EXTRA_CSS, cards)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=os.path.join(ROOT, "outputs", "rankstyle-board.html"))
    a = ap.parse_args()
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(build())
    print("wrote %s (%.0f KB)" % (a.out, os.path.getsize(a.out) / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
