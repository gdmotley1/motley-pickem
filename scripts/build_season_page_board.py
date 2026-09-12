"""Render the Season tab as it will be built: every choice from the record book boards in one
scrollable phone.

Grant's picks on 2026-09-12: the trophy room for the Hall of fame, "and I like the up for
grabs part"; the Hall of shame under it; and everyone's numbers as T2, "I like T2", the
table with the four names frozen down the left that swipes sideways. Then two changes to
T2: ESPN's abbreviations for teams ("Georgia Tech and Oklahoma State ... the abbreviation
that ESPN has for them"), applied to every team the table names, and the badges "a little
bigger", 30px to 44px.

Not a new round of options. It is the page he has already chosen, assembled, so the whole
tab is seen together once before it is built. The standings are the app's own markup, and
the sub line already counts finished weeks only, which is part of the fix.

    python scripts/build_season_page_board.py
"""
from __future__ import annotations

import html
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_recordbook_board as rb  # noqa: E402
import build_table_board as tb  # noqa: E402

ROOT = rb.ROOT
OUT = os.path.join(ROOT, "outputs", "season-page-board.html")
e = html.escape

STANDINGS = [(1, "James", 186), (1, "Grant", 186), (3, "Parker", 165), (4, "Nicole", 160)]


def standings():
    rows = "".join(
        '<div class="srow%s"><span class="srow__pos num">%d</span>%s<span class="srow__body">'
        '<span class="srow__name">%s</span></span><span><span class="srow__pts num">%d</span>'
        '<span class="srow__ptslabel">pts</span></span></div>'
        % (" is-leader" if rank == 1 else "", rank, rb.face(name, 36), name, pts)
        for rank, name, pts in STANDINGS)
    return (
        '<div class="screen"><p class="eyebrow">Season 2026</p>'
        '<div style="display:flex;align-items:flex-start;gap:10px"><h2 class="h1" style="flex:1">'
        'Season</h2></div><p class="sub">1 week in the books. Ties stand, so a week can be '
        'shared.</p></div><div class="stand">%s</div>' % rows)


def trophy_room():
    won = [a for a in rb.FAME if a[1]]
    grabs = [a for a in rb.FAME if not a[1]]
    stage = "".join(rb.fame_tile(bid, who, detail, 104) for bid, who, detail in won)
    sockets = "".join(
        '<div class="rkC-grab">%s<p>%s</p></div>' % (rb.medal(bid, 62, True), e(rb.BY_ID[bid][2]))
        for bid, _who, _detail in grabs)
    return (
        '<section class="rkC-stage"><p class="rk-kick">The record book</p><h3>Hall of fame</h3>'
        '<div class="rkC-won">%s</div><p class="rkC-sub">Up for grabs</p>'
        '<div class="rkC-grabs">%s</div></section>' % (stage, sockets)
        + rb.shame_block())


def page():
    inner = (standings() + '<div class="sp-gap"></div>' + trophy_room()
             + '<div class="rk-title"><p class="rk-kick">Everyone&apos;s numbers</p>'
               '<h3>The table</h3></div>' + tb.t2_table(44))
    return tb.phone(inner, "sp-phone")


BODY = """
<header class="bd-top"><div class="bd-wrap">
  <p class="bd-kick">Motley Pick'em &middot; Season tab</p>
  <h1>The Season tab, as it will be built</h1>
  <p>Everything you picked, on one phone. <b>Scroll inside it</b> for the whole tab, and
    <b>swipe the table sideways</b> at the bottom.</p>
</div></header>
<div class="bd-wrap">
  <section class="bd-opt">
    <div class="bd-opt__grid">
      <div class="bd-opt__copy">
        <h2 class="sp-h">What changed since the table board</h2>
        <ul class="sp-list">
          <li><b>ESPN abbreviations.</b> Worst miss reads "on GT" and "on OKST". I did the same
            for Nevada in the upset column, which you may not have swiped to: it reads NEV,
            here and in the Hall of fame.</li>
          <li><b>Bigger badges in the table.</b> The headers go from 30px to 44px, and every
            column still fits.</li>
          <li><b>Two old labels caught by the 13px check.</b> The standings' "pts" was 9.5px and
            the "Season 2026" line was 11px. Both are 13px now. That second one is the same
            style at the top of every tab, so I would bump it everywhere.</li>
        </ul>
        <h2 class="sp-h">From top to bottom</h2>
        <ul class="sp-list">
          <li>Standings, as now. The line under the title counts finished weeks only.</li>
          <li>The trophy room: Hall of fame awards somebody holds, shown big, then the
            up for grabs row.</li>
          <li>The Hall of shame.</li>
          <li>Everyone's numbers, the table, names frozen down the left.</li>
        </ul>
        <p class="bd-opt__cost"><b>Still to come.</b> The form chart comes back once two weeks
          are finished. The badges are stand-ins until your ChatGPT art lands in
          <code>inputs/badges/</code>. Say build and I will put this in the app with the
          stand-ins, then swap each badge in as you send it.</p>
      </div>
      {{PAGE}}
    </div>
  </section>
</div>
"""

CSS = """
/* The tab's two existing labels under Grant's 13px floor, fixed here as they will be in the
   build: the eyebrow was 11px and the standings' "pts" 9.5px. */
.sp-phone .eyebrow { font-size: 13px; }
.sp-phone .srow__ptslabel { font-size: 13px; }
.sp-phone { height: 760px; }
.sp-gap { height: 18px; }
.sp-h { margin: 0 0 8px; font-family: var(--display); font-size: 19px; font-weight: 800; }
.sp-list { margin: 0 0 22px; padding-left: 20px; font-size: 15px; line-height: 1.6; color: var(--ink-2); max-width: 58ch; }
.sp-list li { margin-bottom: 6px; }
.sp-list b { color: var(--ink); }
.bd-opt__copy code { font-family: ui-monospace, monospace; font-size: 14px; background: var(--well); padding: 1px 5px; border-radius: 4px; }
"""


def build(standalone: bool) -> str:
    css = "".join(open(os.path.join(ROOT, "src", f), encoding="utf-8").read()
                  for f in ("theme.css", "app.css"))
    rk = open(os.path.join(ROOT, "scripts", "recordbook_board.css"), encoding="utf-8").read()
    rt = open(os.path.join(ROOT, "scripts", "table_board.css"), encoding="utf-8").read()
    logos = ":root{%s}" % "".join("--lg-%s:url(%s);" % (t, rb.logo(t)) for t in rb.TEAM.values())
    symbols = ('<svg width="0" height="0" style="position:absolute" aria-hidden="true">%s</svg>'
               % "".join('<symbol id="i-%s" viewBox="0 0 512 512">%s</symbol>' % (k, v)
                         for k, v in rb.MOD["icons"].items()))
    script = """<script>
  document.querySelectorAll('.rt-phone').forEach(function (ph) {
    var hdr = ph.querySelector('.apphdr');
    if (hdr && hdr.offsetHeight) ph.style.setProperty('--hdr', hdr.offsetHeight + 'px');
    // #tall shows the whole tab without the inner scroll, for a single full-length screenshot.
    if (location.hash === '#tall') { ph.style.height = 'auto'; ph.style.overflow = 'visible'; }
  });
</script>"""
    doc = ('<!doctype html>\n<meta charset="utf-8">\n'
           '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
           if standalone else "")
    return (doc + "<title>Season Tab Final</title>\n"
            '<link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..800'
            '&family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">\n'
            "<style>%s\n%s\n%s\n%s\n%s</style>%s" % (logos, css, rk, rt, CSS, symbols)
            + BODY.replace("{{PAGE}}", page()) + script)


if __name__ == "__main__":
    for path, standalone in ((OUT, True), (OUT.replace(".html", ".artifact.html"), False)):
        text = build(standalone)
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        print("wrote %s  (%.0f KB)" % (path, len(text.encode()) / 1024))
