"""The Picks tab, six ways: choosing winners, setting points and locking in.

Grant, 2026-09-13: "build an artifact with several wildly different directions, each a full
phone on real data ... Make it look like a million dollar job. One direction should match
the Board's jumbotron look so Picks and Board feel like one stadium, and the rest should be
genuinely different. Keep the rules that already work: a list for choosing winners, tap to
lift and place for points, auto-rank by spread, the loud matchup pill, nothing under 13px,
no sideways scrolling."

Every direction draws three phones from scripts/pickstab_kit.py, all Grant's real Week 1
card. Today's tab sits on top, unnumbered, from the harness screenshots in
outputs/harness/build_picks/ when they exist.

    python scripts/build_pickstab_board.py            # writes outputs/pickstab-board.html
    python scripts/build_pickstab_board.py --only jumbo
"""
from __future__ import annotations

import base64
import importlib
import io
import json
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pickstab_kit import CARD, FAVORITES, RANKED, ROOT, UNDERDOGS, e, logo_vars  # noqa: E402

OUT = os.path.join(ROOT, "outputs", "pickstab-board.html")
PUBLISH = os.path.join(ROOT, "outputs", "pickstab-board.publish.html")
DIRECTIONS = ["jumbo", "select", "faceoff", "gridiron", "broadcast", "whiteboard"]
SCREENS = [("winners", "Winners", "Midweek, 12 of 20 picked"), ("points", "Points", "Notre Dame lifted"), ("locked", "Locked in", "Saved")]
FONTS = ("https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@600;700;800;900"
         "&family=Saira:ital,wdth,wght@0,50..125,400..900;1,50..125,400..900"
         "&family=Archivo:ital,wdth,wght@0,62..125,400..900;1,62..125,400..900"
         "&family=Alfa+Slab+One"
         "&family=Anton&family=Barlow+Condensed:ital,wght@0,600;0,700;0,800;1,700;1,800"
         "&family=Permanent+Marker&family=Kalam:wght@400;700"
         "&family=Inter:wght@400;500;600;700;800&display=swap")
TODAY = os.path.join(ROOT, "outputs", "harness", "picks_shots")


def read(name):
    return open(os.path.join(ROOT, "scripts", name), encoding="utf-8").read()


def loaded(only=None):
    out = []
    for key in DIRECTIONS:
        if only and key not in only:
            continue
        py = os.path.join(ROOT, "scripts", "pickstab_%s.py" % key)
        css = os.path.join(ROOT, "scripts", "pickstab_%s.css" % key)
        if os.path.exists(py) and os.path.exists(css):
            out.append((key, importlib.import_module("pickstab_%s" % key), read("pickstab_%s.css" % key)))
    return out


def phones(key, mod):
    figs = []
    for screen, label, note in SCREENS:
        figs.append('<figure class="pb-shot"><figcaption><b>%s</b><span>%s</span></figcaption>'
                    '<div class="pb-phone" data-key="%s" data-screen="%s">%s</div></figure>'
                    % (label, note, key, screen, getattr(mod, screen)()))
    return "".join(figs)


def section(n, key, mod):
    return ('<section class="pb-dir" id="dir-%d" data-key="%s"><div class="pb-copy"><p class="pb-num">%d</p>'
            '<div class="pb-words"><h2>%s</h2><p class="pb-pitch">%s</p><p class="pb-built"><b>Built with</b>%s</p>'
            '<p class="pb-facts" data-facts>Measuring&hellip;</p></div></div>'
            '<div class="pb-phones">%s</div></section>'
            % (n, key, n, e(mod.NAME), mod.PITCH, mod.BUILT, phones(key, mod)))


def _uri(im, width=390, scale=1.5):
    im = im.convert("RGB")
    w, h = im.size
    im = im.resize((round(width * scale), round(h * width * scale / w)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=80, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode(), round(im.size[1] / scale)


def _choose_cut(im):
    """Today's winners list is 3,398 px. Keep what the directions draw: the top of the tab and
    its first six games, then the end of the list with its button and the tab bar."""
    from PIL import ImageDraw

    top, gap, bottom = 1062 * 2, 44 * 2, 150 * 2
    out = Image.new("RGB", (im.width, top + gap + bottom), (238, 241, 245))
    out.paste(im.crop((0, 0, im.width, top)), (0, 0))
    out.paste(im.crop((0, im.height - bottom, im.width, im.height)), (0, top + gap))
    d = ImageDraw.Draw(out)
    y = top + gap // 2
    for x in range(24, im.width - 24, 28):
        d.line((x, y, x + 14, y), fill=(150, 158, 170), width=4)
    return out


def today():
    paths = [os.path.join(TODAY, "picks_%s.png" % s) for s in ("choose", "rank", "locked")]
    if not all(os.path.exists(x) for x in paths):
        return ""
    shots = [_uri(_choose_cut(Image.open(paths[0])))] + [_uri(Image.open(x)) for x in paths[1:]]
    labels = [("Winners", "First six games, then the end of the list"), ("Points", "Notre Dame lifted"), ("Locked in", "Saved")]
    figs = "".join('<figure class="pb-shot"><figcaption><b>%s</b><span>%s</span></figcaption>'
                   '<div class="pb-phone pb-phone--img"><img src="%s" width="390" height="%d" alt="Today&rsquo;s %s screen"></div></figure>'
                   % (label, note, uri, h, label) for (uri, h), (label, note) in zip(shots, labels))
    return ('<section class="pb-dir pb-today" id="today"><div class="pb-copy"><p class="pb-num pb-num--today">Now</p>'
            '<div class="pb-words"><h2>What ships today</h2><p class="pb-pitch">%s</p></div></div>'
            '<div class="pb-phones">%s</div></section>' % (TODAY_FACTS, figs))


TODAY_FACTS = ("Measured on your real Week&nbsp;1 card at 390&nbsp;px: a game is 146&nbsp;px, so 20 games alone take 3,120&nbsp;px. "
               "The team names are 12.5&nbsp;px, the Matchup pill is 22&nbsp;px tall with a 10&nbsp;px label, the TV chip is 9.5&nbsp;px "
               "and the HERE and MOVING cues are 10&nbsp;px, all under your 13&nbsp;px floor.")


def page(standalone, only=None):
    dirs = loaded(only)
    top = RANKED[0]
    body = """
<header class="pb-hero">
  <div class="pb-rig" aria-hidden="true"><i></i><i></i><i></i><i></i></div>
  <p class="pb-kick">Motley Pick&rsquo;em &middot; The Picks tab</p>
  <h1>Your picks,<br>%(n)s ways</h1>
  <p class="pb-lede">Choosing winners, setting points and locking in, drawn on your real Week&nbsp;1 card: the games, TV,
    spreads and AP ranks as they were, and your own %(fav)d favorites, %(dog)d underdogs and 20 on %(top)s.
    Every direction keeps the rules that work: a list for winners, tap to lift and place for points, sorted by the
    spread on arrival, the loud Matchup pill, nothing under 13px and nothing that scrolls sideways.</p>
  <ol class="pb-map">%(map)s</ol>
</header>
<main>%(today)s%(sections)s</main>
<footer class="pb-foot"><p>Reply with a number. Or mix them: the winners list from one, the points from another.</p></footer>
""" % {"n": {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven"}.get(len(dirs), str(len(dirs))),
       "fav": FAVORITES, "dog": UNDERDOGS, "top": e(top["pick"]["school"]),
       "map": "".join('<li><a href="#dir-%d"><b>%d</b>%s</a></li>' % (i + 1, i + 1, e(m.NAME)) for i, (_, m, _) in enumerate(dirs)),
       "today": today(),
       "sections": "".join(section(i + 1, k, m) for i, (k, m, _) in enumerate(dirs))}
    doc = '<!doctype html>\n<html lang="en">\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1">\n' if standalone else ""
    return (doc + "<title>Picks Tab, Six Ways</title>\n"
            '<link rel="preconnect" href="https://fonts.googleapis.com">\n<link href="%s" rel="stylesheet">\n'
            "<style>%s\n%s\n%s</style>\n%s<script>%s</script>"
            % (FONTS, logo_vars(), read("pickstab_page.css"), "\n".join(css for _, _, css in dirs), body, read("pickstab_page.js")))


if __name__ == "__main__":
    only = None
    if "--only" in sys.argv:
        only = set(sys.argv[sys.argv.index("--only") + 1].split(","))
    open(OUT, "w", encoding="utf-8", newline="").write(page(True, only))
    if not only:
        open(PUBLISH, "w", encoding="utf-8", newline="").write(page(False))
    print("wrote", OUT, "directions:", [k for k, _, _ in loaded(only)], "cards", len(CARD))
