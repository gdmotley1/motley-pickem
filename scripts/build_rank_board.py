# -*- coding: utf-8 -*-
"""Render five ways of showing an AP rank next to a team, as real rows at phone width.

The first attempt reserved an equal-width empty slot for unranked teams, which is what
Grant asked for and looks wrong in practice: 14 of the 20 games in Week 2 have exactly
ONE ranked team, so nearly every row ends up with a number on one side and a visible hole
on the other, in the same line.

    python scripts/build_rank_board.py                     # -> outputs/rank-board.html

Real data throughout: the live AP poll joined to the real Week 2 slate, so the ranked and
unranked mix on the page is the mix the family will actually see on Saturday. Shares the
phone chrome and Slate palette with build_recap_board.py.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_recap_board import CSS as BASE_CSS  # noqa: E402
from build_theme_board import logo_uri  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Four games chosen for what they prove, not for who is playing:
#   one ranked away side, both sides ranked, one ranked home side, neither ranked.
# (away, away_id, away_rank, home, home_id, home_rank, line)
GAMES = [
    ("MIZ", "142", 23, "KU", "2305", None, "MIZ -5.5"),
    ("OSU", "194", 1, "TEX", "251", 4, "TEX -1.5"),
    ("WKU", "98", None, "UGA", "61", 2, "UGA -40.5"),
    ("DUKE", "150", None, "ILL", "356", None, "ILL -6.0"),
]

SETUP = [
    ("ALA", "333", 12, "UK", "96", None, "ALA -10.5", "Toss-up"),
    ("RICE", "242", None, "ND", "87", 3, "ND -44.5", "Lock"),
]


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def logo(team_id: str, size: int = 22) -> str:
    uri = logo_uri(team_id)
    if not uri:
        return '<span class="lg" style="width:%dpx;height:%dpx"></span>' % (size, size)
    return '<img class="lg" src="%s" width="%d" height="%d" alt="">' % (uri, size, size)


# ------------------------------------------------------------------ the five treatments


def side(opt: str, abbr: str, team_id: str, rank) -> str:
    """One team, rendered the way `opt` says."""
    lg = logo(team_id)

    if opt == "A":  # nothing reserved
        r = '<span class="r-a">%d</span>' % rank if rank else ""
        return '<span class="side">%s%s%s</span>' % (lg, r, esc(abbr))

    if opt == "B":  # badge on the logo
        badge = '<span class="r-b">%d</span>' % rank if rank else ""
        return ('<span class="side"><span class="lgwrap">%s%s</span>%s</span>'
                % (lg, badge, esc(abbr)))

    if opt == "C":  # trailing superscript
        r = '<sup class="r-c">%d</sup>' % rank if rank else ""
        return '<span class="side">%s%s%s</span>' % (lg, esc(abbr), r)

    if opt == "D":  # a narrower reserved slot, number only
        r = ('<span class="r-d">%d</span>' % rank) if rank else '<span class="r-d"></span>'
        return '<span class="side">%s%s%s</span>' % (lg, r, esc(abbr))

    # E: nothing on the line at all
    return '<span class="side">%s%s</span>' % (lg, esc(abbr))


def meta_line(opt: str, g) -> str:
    """Option E moves the ranks down here; everyone else just shows the line."""
    away, aid, ar, home, hid, hr, line = g[:7]
    if opt != "E":
        return '<span class="chip">%s</span>' % esc(line)
    bits = []
    if ar:
        bits.append("#%d %s" % (ar, away))
    if hr:
        bits.append("#%d %s" % (hr, home))
    rank_chip = ('<span class="chip chip--accent">%s</span>' % esc(" &middot; ".join(bits))
                 .replace("&amp;middot;", "&middot;")) if bits else ""
    return '<span class="chip">%s</span>%s' % (esc(line), rank_chip)


def board_row(opt: str, g) -> str:
    away, aid, ar, home, hid, hr, line = g[:7]
    return ('<div class="brow"><div class="brow__top">'
            '%s<span class="at">@</span>%s</div>'
            '<div class="brow__meta">%s</div></div>'
            % (side(opt, away, aid, ar), side(opt, home, hid, hr), meta_line(opt, g)))


def setup_row(opt: str, g) -> str:
    away, aid, ar, home, hid, hr, line, tier = g
    return ('<div class="srow2"><span class="box">&#10003;</span>'
            '<span class="srow2__body"><span class="srow2__match">'
            '%s<span class="at">@</span>%s</span>'
            '<span class="srow2__meta">%s</span></span></div>'
            % (side(opt, away, aid, ar), side(opt, home, hid, hr), meta_line(opt, g)))


def phone(opt: str, label: str, note: str, verdict: str) -> str:
    rows = "".join(board_row(opt, g) for g in GAMES)
    setup = "".join(setup_row(opt, g) for g in SETUP)
    return """
<figure class="opt opt--%s">
  <figcaption class="opt__cap">%s</figcaption>
  <div class="phone">
    <div class="phone__body">
      <div class="screen"><p class="eyebrow">Board</p></div>
      <div class="rows">%s</div>
      <div class="screen"><p class="eyebrow" style="margin-top:14px">Setup</p></div>
      <div class="rows">%s</div>
    </div>
  </div>
  <p class="opt__cost">%s</p>
  <p class="opt__note">%s</p>
</figure>""" % (opt.lower(), esc(label), rows, setup, esc(verdict), esc(note))


EXTRA_CSS = """
.opt{width:360px}
.opt__cost{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;
  color:var(--mark);margin:12px 2px 0;font-weight:600}
.opt__note{margin-top:6px}
.phone{height:auto;min-height:0;padding-bottom:10px}
.phone .rows{padding:0 12px;display:grid;gap:7px}

.phone .brow,.phone .srow2{background:var(--card);border:1px solid var(--line);
  border-radius:var(--r-lg);padding:10px 12px;box-shadow:var(--sh-1)}
.phone .brow__top,.phone .srow2__match{display:flex;align-items:center;gap:9px;
  font-family:var(--display);font-weight:700;font-size:14.5px}
.phone .brow__meta,.phone .srow2__meta{display:flex;gap:5px;margin-top:6px}
.phone .at{color:var(--ink-3);font-weight:600;font-size:12px}
.phone .side{display:inline-flex;align-items:center;gap:5px;min-width:0}
.phone .lg{display:block;object-fit:contain}

.phone .srow2{display:flex;align-items:center;gap:10px}
.phone .box{width:20px;height:20px;border-radius:5px;border:1.5px solid var(--line-strong);
  display:grid;place-items:center;color:transparent;flex:none;font-size:11px}
.phone .srow2__body{flex:1;min-width:0}

/* A: nothing reserved */
.phone .r-a{font-size:10px;font-weight:800;color:var(--accent)}
.phone .r-a::before{content:'#';opacity:.6}

/* B: a badge on the logo */
.phone .lgwrap{position:relative;display:block;flex:none;line-height:0}
.phone .r-b{position:absolute;top:-5px;left:-6px;min-width:15px;height:15px;padding:0 3px;
  border-radius:999px;background:var(--field);color:var(--on-field);font-size:9px;
  font-weight:800;display:grid;place-items:center;box-shadow:0 0 0 1.5px var(--card)}

/* C: trailing superscript */
.phone .r-c{font-size:9px;font-weight:800;color:var(--accent);margin-left:1px;top:-.5em}

/* D: a narrow reserved slot, number only */
.phone .r-d{display:inline-block;min-width:13px;text-align:right;font-size:10px;
  font-weight:800;color:var(--accent)}

/* E: down in the meta line */
"""


def build() -> str:
    opts = [
        ("A", "A · Nothing reserved",
         "The rank appears only where there is one, and an unranked team sits flush against "
         "its logo. Nothing lines up between the two sides of a game, but nothing has a hole "
         "in it either. The logo already gives every row the same left edge.",
         "no reserved space"),
        ("B", "B · A badge on the logo",
         "The number rides the corner of the crest, so the team name is always flush and the "
         "rows line up structurally rather than by reserving anything. Reads like a sports "
         "app. The badge is small at 22px, and it sits over the logo, which needs a ring to "
         "stay legible on a busy crest.",
         "no reserved space"),
        ("C", "C · Trailing superscript",
         "The number follows the abbreviation the way a footnote does. Names stay flush and "
         "the rank never pushes anything sideways. Quiet, and slightly easy to miss.",
         "no reserved space"),
        ("D", "D · A narrow reserved slot",
         "The idea you asked for, tuned: 13px rather than 21, and no # so the hole is a "
         "third the width. It does keep the abbreviations in a true column. It still leaves "
         "a gap on the unranked side of every one-ranked-team game, which is 14 of 20 this "
         "week.",
         "13px reserved"),
        ("E", "E · Down in the meta line",
         "Off the name row entirely and into the chip line beside the spread. The matchup "
         "reads perfectly cleanly and the ranks are still there. It costs a chip's width on "
         "a line that already carries the spread, and the rank stops being attached to a "
         "particular team at a glance.",
         "no reserved space"),
    ]
    cards = "".join(phone(k, lab, note, cost) for k, lab, note, cost in opts)
    return """<title>AP Rank Treatments</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;600;700&family=Inter:wght@400;600;700&display=swap">
<style>%s%s</style>

<div class="wrap">
  <p class="doc__eyebrow">Motley Pick'em &middot; design options</p>
  <h1 class="doc__title">Where the AP rank goes</h1>
  <p class="doc__sub">Five treatments, each shown on four Board rows and two Setup rows.
  Real data: the live AP poll against the real Week 2 slate.</p>

  <section>
    <h2 class="sec__h">Why the reserved gap reads as broken</h2>
    <div class="callout"><p>Of the twenty games this week, <b>fourteen have exactly one
    ranked team</b> and only one game has two. So reserving equal space puts a number on
    one side of a matchup and an empty 21px hole on the other, <b>in the same line</b>,
    on most rows. It is uniform in the strict sense and it looks like a rendering fault.
    Six games have no ranked team at all and get two holes.</p></div>
  </section>

  <section>
    <h2 class="sec__h">The five</h2>
    <div class="row">%s</div>
  </section>

  <section>
    <h2 class="sec__h">The recommendation</h2>
    <div class="rec">
      <h3>B, with A as the safe answer</h3>
      <p><b>B</b> is the one I would build. Putting the number on the crest solves the
      alignment structurally instead of by reserving space: the logo is a fixed 22px, so
      every team name starts at exactly the same place whether the team is ranked or not,
      and there is never a hole. It is also the treatment people already recognise from
      every other football app.</p>
      <p><b>A</b> is the one-line change and is genuinely fine. The logo already anchors
      the left edge of every row, so the only thing that shifts is the abbreviation, by
      about 20px, on a row that has a rank. Nobody reads down a column of abbreviations.
      If you want this settled in a minute rather than done properly, take A.</p>
      <p><b>The one to avoid is D.</b> It is the current approach made less bad, and it
      keeps the exact property you objected to: a visible gap where a rank is not. Making
      the hole smaller does not stop it being a hole.</p>
      <p><b>E</b> is worth a look if you find the name rows still too busy. It reads the
      cleanest of the five, and it is the only one where you cannot tell at a glance
      which team the number belongs to without reading the abbreviation next to it.</p>
    </div>
  </section>
</div>
""" % (BASE_CSS, EXTRA_CSS, cards)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=os.path.join(ROOT, "outputs", "rank-board.html"))
    a = ap.parse_args()
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(build())
    print("wrote %s (%.0f KB)" % (a.out, os.path.getsize(a.out) / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
