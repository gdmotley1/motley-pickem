# -*- coding: utf-8 -*-
"""Render five ways of stepping the Week tab through previous weeks, as real phone screens.

Grant asked for arrows on the Week tab to look back at earlier weeks, and for options to
pick from. Per memory/ui-patterns.md that decision is made from rendered screens, not a
description: labelled A to E, at phone width, against the project's own tokens, using the
real Week 1 result.

    python scripts/build_weeknav_board.py                  # -> outputs/weeknav-board.html
    python scripts/build_weeknav_board.py --out other.html

Shares the phone chrome and Slate palette with build_recap_board.py rather than restating
it, so a change to one board cannot quietly drift from the other. Only the navigation
strips below are new.
"""
from __future__ import annotations

import argparse
import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from build_recap_board import CSS as BASE_CSS  # noqa: E402
from build_recap_board import PLAYERS, avatar, standing_rows  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Real weeks, from the weeks table and ESPN's calendar. Week 1 absorbed Week 0, which is
# why it is seventeen days long and why the label matters more than the dates.
WEEKS = [
    (1, "Week 1", "Aug 22 - Sep 8", "final"),
    (2, "Week 2", "Sep 8 - Sep 14", "unpublished"),
    (3, "Week 3", "Sep 15 - Sep 21", "empty"),
]

HEADLINE = "Grant takes it by 7"


def esc(s) -> str:
    return html.escape(str(s), quote=True)


CHEV_L = ('<svg viewBox="0 0 20 20" width="17" height="17" aria-hidden="true">'
          '<path d="M13 4 7 10l6 6" stroke="currentColor" stroke-width="2.2" '
          'stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>')
CHEV_R = ('<svg viewBox="0 0 20 20" width="17" height="17" aria-hidden="true">'
          '<path d="M7 4l6 6-6 6" stroke="currentColor" stroke-width="2.2" '
          'stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>')
CARET = ('<svg viewBox="0 0 20 20" width="13" height="13" aria-hidden="true">'
         '<path d="M5 8l5 5 5-5" stroke="currentColor" stroke-width="2.2" '
         'stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>')


def phone(label: str, body: str, note: str, cost: str) -> str:
    tabs = [("board", "Board"), ("picks", "Picks"), ("week", "Week"), ("season", "Season")]
    bar = "".join('<span class="tab%s">%s</span>' % (" is-on" if t == "week" else "", esc(n))
                  for t, n in tabs)
    return """
<figure class="opt">
  <figcaption class="opt__cap">%s</figcaption>
  <div class="phone">
    <div class="apphdr">
      <span><span class="apphdr__title">Motley Pick'em</span>
      <span class="apphdr__week">Week 2 &middot; 20 games</span></span>
      <span class="apphdr__me">%s<span>Grant</span></span>
    </div>
    <div class="phone__body">%s</div>
    <div class="tabbar">%s</div>
  </div>
  <p class="opt__cost">%s</p>
  <p class="opt__note">%s</p>
</figure>""" % (esc(label), avatar("Grant", "#B85C1F", "2751", "#ffc425", 24),
                body, bar, esc(cost), esc(note))


def head(eyebrow: str, title: str) -> str:
    return ('<div class="screen"><p class="eyebrow">%s</p><h1 class="h1">%s</h1></div>'
            % (esc(eyebrow), esc(title)))


TOP2 = PLAYERS[:2]


# --------------------------------------------------------------------------- options


def option_a() -> str:
    body = (
        '<div class="screen"><div class="navA">'
        '<button class="navA__b">%s</button>'
        '<p class="eyebrow navA__e">Week 1 &middot; final</p>'
        '<button class="navA__b is-off">%s</button>'
        '</div><h1 class="h1">%s</h1></div>' % (CHEV_L, CHEV_R, esc(HEADLINE))
        + standing_rows(PLAYERS))
    return phone(
        "A · Arrows on the eyebrow line",
        body,
        "Costs nothing. The arrows sit on the line the week label already uses, so the "
        "headline stays exactly where it is today. The tap targets are small for a "
        "one-handed thumb, and there is nowhere to put the date range.",
        "0px above the first name")


def option_b() -> str:
    body = (
        '<div class="navB">'
        '<button class="navB__b">%s</button>'
        '<span class="navB__mid"><b>Week 1</b><i>Aug 22 - Sep 8</i></span>'
        '<button class="navB__b is-off">%s</button>'
        '</div>' % (CHEV_L, CHEV_R)
        + head("Final", HEADLINE)
        + standing_rows(PLAYERS))
    return phone(
        "B · Its own pager bar",
        body,
        "A real row of its own, so both arrows are proper 44px targets and the date range "
        "fits under the label. The clearest of the five at a glance. It pushes the result "
        "down by about a line and a half.",
        "46px above the first name")


def option_c() -> str:
    body = (
        '<div class="navB">'
        '<button class="navB__b">%s</button>'
        '<button class="navB__mid navB__mid--tap"><b>Week 1 %s</b><i>Aug 22 - Sep 8</i></button>'
        '<button class="navB__b is-off">%s</button>'
        '</div>' % (CHEV_L, CARET, CHEV_R)
        + head("Final", HEADLINE)
        + standing_rows(TOP2)
        + '<div class="sheetdemo">'
          '<p class="sheetdemo__t">Jump to a week</p>'
          '<div class="wkpick"><span>Week 1</span><b>Grant &middot; 186</b></div>'
          '<div class="wkpick is-now"><span>Week 2</span><b>in progress</b></div>'
          '<div class="wkpick is-off"><span>Week 3</span><b>not played</b></div>'
          '<p class="sheetdemo__c">tapping the label opens this</p></div>')
    return phone(
        "C · Pager bar, and the label opens a picker",
        body,
        "Same bar as B, but the middle is a button. Tapping it opens a sheet listing every "
        "week with who won it, so week 12 is one tap rather than eleven. Costs the same "
        "height as B and roughly a Sheet's worth of extra work.",
        "46px above the first name")


def option_d() -> str:
    chips = "".join(
        '<span class="chip2%s">%s</span>'
        % (" is-on" if n == 1 else (" is-off" if n > 2 else ""), n)
        for n in range(1, 9))
    body = (
        '<div class="navD"><button class="navD__b">%s</button>'
        '<span class="navD__strip">%s</span>'
        '<button class="navD__b is-off">%s</button></div>' % (CHEV_L, chips, CHEV_R)
        + head("Week 1 · final", HEADLINE)
        + standing_rows(PLAYERS))
    return phone(
        "D · Week numbers, arrows at the ends",
        body,
        "The whole season at a glance, greyed where nothing has been played. Good for a "
        "long season and the fastest way to see how far along you are. Fifteen numbers is "
        "a lot of small targets on a phone, and it reads more like a calendar than a "
        "result.",
        "44px above the first name")


def option_e() -> str:
    body = (
        '<div class="navE">'
        '<button class="navE__b">%s</button>'
        '<span class="navE__mid">Week 1 <i>final</i></span>'
        '<button class="navE__b is-off">%s</button>'
        '</div>' % (CHEV_L, CHEV_R)
        + head("Final", HEADLINE)
        + standing_rows(PLAYERS)
        + '<div class="screen"><h3 class="h2">Ranking</h3>'
          '<p class="sub">Points banked against the most that ranking could have been '
          'worth.</p></div>')
    return phone(
        "E · A pager that stays put as you scroll",
        body,
        "B, but pinned under the header so the arrows are still there twelve rows down "
        "the recap. Best on the long screens this tab now has. It is the only option that "
        "costs its height permanently rather than once, and it needs the Portal helper "
        "because a fixed strip inside the screen wrapper anchors to the page, not the "
        "screen.",
        "46px, and it never scrolls away")


def states() -> str:
    """The four states any of these has to survive, rendered once."""
    def mini(cap, inner):
        return ('<figure class="state"><figcaption>%s</figcaption>'
                '<div class="statebox">%s</div></figure>' % (esc(cap), inner))

    return "".join([
        mini("A finished week", '<div class="navB navB--mini">'
             '<button class="navB__b">%s</button>'
             '<span class="navB__mid"><b>Week 1</b><i>final</i></span>'
             '<button class="navB__b is-off">%s</button></div>' % (CHEV_L, CHEV_R)),
        mini("The week in progress, and where the forward arrow stops",
             '<div class="navB navB--mini">'
             '<button class="navB__b">%s</button>'
             '<span class="navB__mid"><b>Week 2</b><i>in progress</i></span>'
             '<button class="navB__b is-off">%s</button></div>' % (CHEV_L, CHEV_R)),
        mini("A week Dad never published", '<div class="navB navB--mini">'
             '<button class="navB__b">%s</button>'
             '<span class="navB__mid"><b>Week 2</b><i>not published</i></span>'
             '<button class="navB__b is-off">%s</button></div>'
             '<p class="stnote">The screen below says so rather than showing four zeroes.</p>'
             % (CHEV_L, CHEV_R)),
        mini("Back at Week 1, nowhere left to go",
             '<div class="navB navB--mini">'
             '<button class="navB__b is-off">%s</button>'
             '<span class="navB__mid"><b>Week 1</b><i>Aug 22 - Sep 8</i></span>'
             '<button class="navB__b">%s</button></div>' % (CHEV_L, CHEV_R)),
        mini("Looking at a past week, with a way back",
             '<div class="navB navB--mini">'
             '<button class="navB__b">%s</button>'
             '<span class="navB__mid"><b>Week 1</b><i>final</i></span>'
             '<button class="navB__b">%s</button></div>'
             '<p class="stnote"><span class="backnow">Back to this week</span> appears '
             'whenever you are not on the current one.</p>' % (CHEV_L, CHEV_R)),
    ])


EXTRA_CSS = """
.opt__cost{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11px;
  color:var(--mark);margin:12px 2px 0;font-weight:600}
.opt__note{margin-top:6px}
.states{display:flex;flex-wrap:wrap;gap:16px}
.state{margin:0;width:330px}
.state figcaption{font-size:12.5px;font-weight:600;color:var(--ink-2);margin-bottom:7px}
.statebox{background:#f3f6f8;border:1px solid #dde4eb;border-radius:10px;padding:10px;
  color-scheme:light}
.stnote{margin:8px 2px 0;font-size:12px;color:var(--ink-3);line-height:1.5}
.backnow{display:inline-block;padding:2px 9px;border-radius:999px;background:#eaf1fe;
  color:#1f56c4;font-size:11px;font-weight:700}

/* --- the navigation strips, scoped to the phone so they use the Slate tokens --- */
.phone .navA{display:flex;align-items:center;gap:6px;margin-bottom:2px}
.phone .navA__e{margin:0;flex:1;text-align:center}
.phone .navA__b{display:grid;place-items:center;width:28px;height:28px;border-radius:50%;
  background:var(--well);color:var(--ink-2);border:0;flex:none}
.phone .navA__b.is-off{opacity:.32}

.phone .navB,.statebox .navB{display:flex;align-items:center;gap:8px;padding:7px 12px;
  border-bottom:1px solid var(--line,#dde4eb);background:var(--card,#f8fafb)}
.phone .navB__b,.statebox .navB__b{display:grid;place-items:center;width:36px;height:36px;
  border-radius:50%;background:var(--well,#e7ecf1);color:var(--ink-2,#48535e);border:0;flex:none}
.phone .navB__b.is-off,.statebox .navB__b.is-off{opacity:.3}
.phone .navB__mid,.statebox .navB__mid{flex:1;text-align:center;display:block;border:0;
  background:none;padding:0}
.phone .navB__mid b,.statebox .navB__mid b{display:block;font-family:var(--display,inherit);
  font-weight:700;font-size:15px;color:var(--ink,#131a22)}
.phone .navB__mid i,.statebox .navB__mid i{display:block;font-style:normal;font-size:11px;
  color:var(--ink-3,#5c6873);margin-top:1px}
.phone .navB__mid--tap b{color:var(--accent-deep)}
.navB--mini{border-radius:8px;border:1px solid #dde4eb}

.phone .navD{display:flex;align-items:center;gap:6px;padding:7px 10px;
  border-bottom:1px solid var(--line);background:var(--card)}
.phone .navD__b{display:grid;place-items:center;width:30px;height:30px;border-radius:50%;
  background:var(--well);color:var(--ink-2);border:0;flex:none}
.phone .navD__b.is-off{opacity:.3}
.phone .navD__strip{flex:1;display:flex;gap:5px;overflow:hidden;justify-content:center}
.phone .chip2{display:grid;place-items:center;width:29px;height:29px;border-radius:8px;
  background:var(--sunk);color:var(--ink-2);font-size:12.5px;font-weight:700;flex:none}
.phone .chip2.is-on{background:var(--field);color:var(--on-field)}
.phone .chip2.is-off{opacity:.35}

.phone .navE{display:flex;align-items:center;gap:8px;padding:7px 12px;
  background:var(--card-a,rgba(248,250,251,.96));border-bottom:1px solid var(--line);
  position:relative}
.phone .navE::after{content:'stays put';position:absolute;right:10px;top:-7px;
  background:var(--accent);color:#fff;font-size:8px;font-weight:700;letter-spacing:.06em;
  text-transform:uppercase;padding:1px 6px;border-radius:999px}
.phone .navE__b{display:grid;place-items:center;width:34px;height:34px;border-radius:50%;
  background:var(--well);color:var(--ink-2);border:0;flex:none}
.phone .navE__b.is-off{opacity:.3}
.phone .navE__mid{flex:1;text-align:center;font-family:var(--display);font-weight:700;
  font-size:15px}
.phone .navE__mid i{font-style:normal;font-weight:600;font-size:11px;color:var(--ink-3);
  margin-left:5px}

.phone .sheetdemo{margin:14px 12px 0;padding:11px 12px;border-radius:12px 12px 0 0;
  background:var(--surface);border:1px solid var(--line);border-bottom:0}
.phone .sheetdemo__t{margin:0 0 8px;font-family:var(--display);font-weight:700;font-size:14px}
.phone .sheetdemo__c{margin:9px 0 0;font-size:10px;color:var(--ink-3);text-align:center;
  font-style:italic}
.phone .wkpick{display:flex;justify-content:space-between;align-items:center;padding:8px 9px;
  border-radius:7px;background:var(--sunk);margin-bottom:5px;font-size:12.5px}
.phone .wkpick span{font-weight:700}
.phone .wkpick b{color:var(--ink-3);font-weight:600}
.phone .wkpick.is-now{background:var(--accent-wash)}
.phone .wkpick.is-now b{color:var(--accent-deep)}
.phone .wkpick.is-off{opacity:.5}
"""


def build() -> str:
    return """<title>Week Tab Navigation</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;600;700&family=Inter:wght@400;600;700&display=swap">
<style>%s%s</style>

<div class="wrap">
  <p class="doc__eyebrow">Motley Pick'em &middot; design options</p>
  <h1 class="doc__title">Stepping back through previous weeks</h1>
  <p class="doc__sub">Five ways to put arrows on the Week tab, rendered at phone width with
  the real Week 1 result. The number under each is how much room it takes above the first
  name in the table, which is the thing worth spending carefully.</p>

  <section>
    <h2 class="sec__h">One decision to make first</h2>
    <div class="callout"><p>The week the app is showing is currently <b>one setting shared
    by every tab</b>. Arrowing back on the Week tab would drag the Picks and Board tabs to
    that old week too, so you could open Picks and find yourself looking at Week 1 with
    everything locked. <b>The week you are browsing has to be local to this screen</b>, and
    reset to the current week when you leave it. That is true for all five options below
    and is most of the work in any of them.</p></div>
  </section>

  <section>
    <h2 class="sec__h">The states it has to handle</h2>
    <p class="sec__lede">Shown on option B's bar, but every option needs all five. The
    greyed arrow is the one that has nowhere to go.</p>
    <div class="states">%s</div>
  </section>

  <section>
    <h2 class="sec__h">The five</h2>
    <div class="row">%s%s%s</div>
    <div class="row" style="margin-top:30px">%s%s</div>
  </section>

  <section>
    <h2 class="sec__h">The recommendation</h2>
    <div class="rec">
      <h3>B, and C if you want it to still be good in November</h3>
      <p><b>B</b> is the one I would build. Both arrows are full-size targets, the week and
      its dates read at a glance, and it costs one row you only pay for once. On a screen
      whose whole job is "which week am I looking at", making that unmissable is worth 46
      pixels.</p>
      <p><b>C</b> is B plus a tap on the label to jump anywhere. It matters more the longer
      the season gets: by week 12, getting back to week 3 is eleven taps in B and one in C.
      It is the same bar, so you can start with B and add the picker later without
      redesigning anything.</p>
      <p><b>A</b> is free and I would still avoid it. The arrows land on the 11px eyebrow
      line, which makes them about 28px of target on a control your mom has to hit
      one-handed, and there is nowhere for the dates to go.</p>
      <p><b>The one to avoid is D.</b> Fifteen numbered chips reads like a calendar rather
      than a result, and it is fifteen small targets where the screen only ever needs
      "back one". It looks best right now, with one week played, and gets worse every week.</p>
      <p><b>E</b> only earns its keep if you find yourself deep in a recap wanting to
      switch weeks. It costs its height on every screen and needs the Portal helper, since
      a fixed strip inside the screen wrapper anchors to the page rather than the screen.
      Worth knowing it exists; not worth it yet.</p>
    </div>
  </section>
</div>
""" % (BASE_CSS, EXTRA_CSS, states(),
       option_a(), option_b(), option_c(), option_d(), option_e())


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=os.path.join(ROOT, "outputs", "weeknav-board.html"))
    a = ap.parse_args()
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(build())
    print("wrote %s (%.0f KB)" % (a.out, os.path.getsize(a.out) / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
