"""The Board tab, six ways: scoreboards and score bugs, on an example Saturday night.

Grant, 2026-09-12: "make artifact ... look like a real college football scoreboard or like a
cartoon arcadey retro style scoreboard ... score bug. Want it to look really impressive.
... several wildly varying directions, and I'll select."

Every phone draws the same example from scripts/boardtab_data.py: Week 1's real picks,
frozen after game 15 of 20, with two live games whose in-game scores are invented.

    node scripts/weektab_model.mjs && python scripts/build_boardtab_board.py
"""
from __future__ import annotations

import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from boardtab_kit import logo_vars  # noqa: E402
from weektab_common import ROOT, e  # noqa: E402

OUT = os.path.join(ROOT, "outputs", "boardtab-board.html")
DIRECTIONS = ["jumbo", "arcade", "bug", "pinball", "bulbs", "flap"]
FONTS = ("https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@600;700;800;900"
         "&family=Press+Start+2P&family=Bangers&family=Barlow+Condensed:wght@600;700;800"
         "&family=Archivo:ital,wdth,wght@0,62..125,500..900;1,62..125,500..900"
         "&family=Inter:wght@400;500;600;700;800&display=swap")


def loaded():
    out = []
    for key in DIRECTIONS:
        path = os.path.join(ROOT, "scripts", "boardtab_%s.py" % key)
        css = os.path.join(ROOT, "scripts", "boardtab_%s.css" % key)
        if os.path.exists(path) and os.path.exists(css):
            out.append((key, importlib.import_module("boardtab_%s" % key), open(css, encoding="utf-8").read()))
    return out


def read(name):
    return open(os.path.join(ROOT, "scripts", name), encoding="utf-8").read()


def section(n, key, mod):
    return ('<section class="bb-dir" id="dir-%d" data-n="%d"><div class="bb-copy">'
            '<p class="bb-num">%d</p><h2>%s</h2><p class="bb-pitch">%s</p>'
            '<p class="bb-built"><b>Built with</b> %s</p><p class="bb-facts" data-facts>Measuring&hellip;</p></div>'
            '<div class="bb-stage"><div class="bb-phone" data-key="%s">%s</div></div></section>'
            % (n, n, n, e(mod.NAME), e(mod.PITCH), e(mod.BUILT), key, mod.build()))


def page(standalone):
    dirs = loaded()
    extra = ""
    if any(k in ("bulbs", "pinball") for k, _, _ in dirs):
        import weektab_bulbs
        extra = weektab_bulbs.defs()
    body = """
<header class="bb-hero">
  <div class="bb-lights" aria-hidden="true"><i></i><i></i><i></i><i></i></div>
  <p class="bb-kick">Motley Pick&rsquo;em &middot; The Board tab</p>
  <h1>The Board,<br>%(n)s ways</h1>
  <p class="bb-lede">Scoreboards and score bugs, from a stadium video wall to a 1989 cartridge. Every phone draws
    the same Saturday night: Week 1&rsquo;s real picks and schools, frozen after 15 of 20 games. The two live
    scores are made up for the example.</p>
  <ol class="bb-map">%(map)s</ol>
</header>
<main>%(sections)s</main>
<footer class="bb-foot"><p>Reply with a number, or mix them: the leaderboard from one with the game tiles from another.</p></footer>
""" % {"n": {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}.get(len(dirs), str(len(dirs))),
       "map": "".join('<li><a href="#dir-%d"><b>%d</b>%s</a></li>' % (i + 1, i + 1, e(m.NAME)) for i, (_, m, _) in enumerate(dirs)),
       "sections": "".join(section(i + 1, k, m) for i, (k, m, _) in enumerate(dirs))}
    doc = ('<!doctype html>\n<html lang="en">\n<meta charset="utf-8">\n'
           '<meta name="viewport" content="width=device-width,initial-scale=1">\n' if standalone else "")
    return (doc + "<title>Board Tab Scoreboards</title>\n"
            '<link rel="preconnect" href="https://fonts.googleapis.com">\n<link href="%s" rel="stylesheet">\n'
            "<style>%s\n%s\n%s\n%s</style>\n%s%s<script>%s</script>"
            % (FONTS, logo_vars(), read("boardtab_page.css"), read("weektab_base.css"),
               "\n".join(css for _, _, css in dirs), extra, body, read("boardtab_page.js")))


if __name__ == "__main__":
    for path, standalone in ((OUT, True), (OUT.replace(".html", ".artifact.html"), False)):
        html = page(standalone)
        open(path, "w", encoding="utf-8", newline="").write(html)
        print("wrote %s (%.0f KB)" % (path, len(html.encode()) / 1024))
