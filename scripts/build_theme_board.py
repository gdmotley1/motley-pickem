"""Render the ten theme options as ten real pick screens, in one self-contained page.

This is the tool that produced the board Grant chose Slate from on 2026-09-04. It lives
here rather than in a scratch directory because memory/ui-patterns.md points at the
published board as the reference for any future theme work, and a reference nobody can
rebuild goes stale the first time a component changes.

    python scripts/build_theme_board.py                     # -> outputs/theme-board.html
    python scripts/build_theme_board.py --out somewhere.html

Static HTML with no JavaScript: the markup for a phone screen exists once below and is
stamped out ten times, so the page renders complete on load. That matters because it is
a contact sheet, and the first frame is the whole point.

Two things keep it honest:

  - Every token name matches the semantic contract in src/theme.css exactly, so a chosen
    theme is a copy-paste into the palette block rather than a translation.
  - The team logos are read from static/logos and inlined, downscaled, as data URIs. The
    page has to survive being opened anywhere, including as a published artifact whose
    content policy blocks every external image.

The component CSS is restated here against the same tokens rather than imported from
src/app.css. That is deliberate: the board needs each card to scope its own palette, and
a design tool that quietly drifts from production is less dangerous than one that breaks
production trying not to.
"""
from __future__ import annotations

import argparse
import base64
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO_DIR = os.path.join(ROOT, "static", "logos")

# Three real games from the 2026-09-05 slate, picked to exercise the states that matter:
# a selected away team, an unselected pair with an AP rank, and a selected home team.
# (abbr, school, espn_team_id, ap_rank)
GAMES = [
    (("TOL", "Toledo", "2649", None), ("MSU", "Michigan State", "127", None),
     "Fri 8:00 PM", "MSU -10", "FS1", "away"),
    (("MIA", "Miami", "2390", "7"), ("STAN", "Stanford", "24", None),
     "Fri 9:00 PM", "MIA -24.5", "ESPN", None),
    (("ECU", "East Carolina", "151", None), ("ALA", "Alabama", "333", "13"),
     "Sat 12:00 PM", "ALA -27.5", "ABC", "home"),
]

# Token names are src/theme.css's semantic contract, verbatim.
THEMES = [
    dict(n="01", name="Saturday, Sharpened", kind="light",
         note="The original warm palette with the softness taken out. Tighter corners, a real hairline, deeper ink.",
         display="'Bitter', Georgia, serif", rcard="10px", rin="8px",
         sh="0 1px 2px rgba(25,21,16,.06)",
         v=dict(field="#0f4433", page="#f4f0e7", card="#fffdf8", well="#e9e2d5",
                line="#d8d0bf", ink="#191510", ink2="#544e40", ink3="#8f8877",
                onfield="#eef5f1", onfield2="#9dbcac", accent="#b06d12", accentdeep="#8f560c",
                pickwash="#eaf4ee", pickedge="#1f7053", pick="#165741",
                good="#1f7053", bad="#9c2f1b")),
    dict(n="02", name="Box Score", kind="light",
         note="Newsprint. Hard rules, almost no radius, one red. The sharpest option here.",
         display="'Archivo', 'Helvetica Neue', sans-serif", rcard="2px", rin="2px", sh="none",
         v=dict(field="#16161a", page="#ffffff", card="#ffffff", well="#f0efec",
                line="#1a1a1a", ink="#0a0a0a", ink2="#3d3d3d", ink3="#767676",
                onfield="#ffffff", onfield2="#a8a8a8", accent="#b3261e", accentdeep="#8c1c16",
                pickwash="#fdf3f2", pickedge="#b3261e", pick="#b3261e",
                good="#177541", bad="#b3261e")),
    dict(n="03", name="Broadcast Graphite", kind="light",
         note="Cool grey chrome, one hard green. Reads like a lower third on a Saturday telecast.",
         display="'Archivo', 'Helvetica Neue', sans-serif", rcard="6px", rin="5px",
         sh="0 1px 2px rgba(20,24,27,.07)",
         v=dict(field="#1c2024", page="#f1f3f4", card="#ffffff", well="#e5e8ea",
                line="#d3d8dc", ink="#14181b", ink2="#4a5257", ink3="#6d767d",
                onfield="#f4f6f7", onfield2="#98a3aa", accent="#0a8f4d", accentdeep="#07713d",
                pickwash="#e9f7ef", pickedge="#0a8f4d", pick="#0a8f4d",
                good="#0a8f4d", bad="#c2372a")),
    dict(n="04", name="Paper & Ink", kind="light",
         note="Warm white, near-black, a single ink blue. Hairlines instead of shadows.",
         display="'Instrument Serif', Georgia, serif", rcard="4px", rin="3px", sh="none",
         v=dict(field="#1a1a18", page="#fbfaf7", card="#ffffff", well="#f0eee9",
                line="#ded9d0", ink="#14140f", ink2="#4c4a42", ink3="#7d7970",
                onfield="#faf9f6", onfield2="#a5a29a", accent="#22449c", accentdeep="#17347c",
                pickwash="#eef1fa", pickedge="#22449c", pick="#22449c",
                good="#177541", bad="#9c2f1b")),
    dict(n="05", name="Slate", kind="light &middot; SHIPPED",
         note="Cool blue-grey and a confident blue. Chosen 2026-09-04 and now live; see src/theme.css.",
         display="'Archivo', 'Helvetica Neue', sans-serif", rcard="10px", rin="8px",
         sh="0 1px 2px rgba(19,26,34,.06), 0 4px 10px rgba(19,26,34,.05)",
         v=dict(field="#28313d", page="#f3f6f8", card="#f8fafb", well="#e7ecf1",
                line="#dde4eb", ink="#131a22", ink2="#48535e", ink3="#5c6873",
                onfield="#f2f6fa", onfield2="#97a5b3", accent="#2f6fed", accentdeep="#1f56c4",
                pickwash="#eaf1fe", pickedge="#2f6fed", pick="#2f6fed",
                good="#177541", bad="#c33c2c")),
    dict(n="06", name="Bulldog", kind="light",
         note="Georgia red on black and bone. Condensed athletic type. Picks a side, on purpose.",
         display="'Oswald', 'Arial Narrow', sans-serif", rcard="8px", rin="6px",
         sh="0 1px 2px rgba(11,11,12,.08)",
         v=dict(field="#0b0b0c", page="#f7f5f3", card="#ffffff", well="#eceae6",
                line="#dbd7d2", ink="#131316", ink2="#4b4b50", ink3="#75757c",
                onfield="#f7f5f3", onfield2="#9b9ba1", accent="#ba0c2f", accentdeep="#8f0824",
                pickwash="#fdeff2", pickedge="#ba0c2f", pick="#ba0c2f",
                good="#177541", bad="#ba0c2f")),
    dict(n="07", name="Night Game", kind="dark",
         note="The original green after dark. Same family, far more contrast on a phone at 9pm.",
         display="'Bitter', Georgia, serif", rcard="12px", rin="9px",
         sh="0 1px 2px rgba(0,0,0,.4)",
         v=dict(field="#0a1a14", page="#0e1f18", card="#15291f", well="#1d3729",
                line="#26422f", ink="#eaf2ec", ink2="#b3c8bc", ink3="#8ba99a",
                onfield="#eaf2ec", onfield2="#7ea792", accent="#e0a53c", accentdeep="#f0b957",
                pickwash="#183a2a", pickedge="#3d9a70", pick="#3d9a70",
                good="#4fb083", bad="#e0705c")),
    dict(n="08", name="Turf", kind="dark",
         note="Deep navy with a lime that only appears on live numbers. Modern, a little loud.",
         display="'Archivo', 'Helvetica Neue', sans-serif", rcard="12px", rin="9px",
         sh="0 1px 2px rgba(0,0,0,.45)",
         v=dict(field="#0d1626", page="#0a1120", card="#121d2f", well="#1a2840",
                line="#22334f", ink="#e7eefb", ink2="#aebbd0", ink3="#8b9cb8",
                onfield="#e7eefb", onfield2="#8095b5", accent="#b6e02c", accentdeep="#c9ef4a",
                pickwash="#16303a", pickedge="#39c07f", pick="#39c07f",
                good="#39c07f", bad="#f0705f")),
    dict(n="09", name="Amber on Black", kind="dark",
         note="Warm black, and the amber the app already used promoted to the lead.",
         display="'Bitter', Georgia, serif", rcard="10px", rin="8px",
         sh="0 1px 2px rgba(0,0,0,.5)",
         v=dict(field="#100e0a", page="#141109", card="#1e1912", well="#2b241a",
                line="#352d21", ink="#f6efe1", ink2="#c2b7a3", ink3="#a1957f",
                onfield="#f6efe1", onfield2="#a3947a", accent="#f0a833", accentdeep="#ffbe52",
                pickwash="#33280f", pickedge="#f0a833", pick="#f0a833",
                good="#5fb383", bad="#e06a4e")),
    dict(n="10", name="Scoreboard", kind="dark",
         note="Stadium LED. Pure black, condensed caps, one hot orange. Maximum sharpness.",
         display="'Oswald', 'Arial Narrow', sans-serif", rcard="3px", rin="2px", sh="none",
         v=dict(field="#000000", page="#080808", card="#131313", well="#1e1e1e",
                line="#2c2c2c", ink="#ffffff", ink2="#c4c4c4", ink3="#9a9a9a",
                onfield="#ffffff", onfield2="#8a8a8a", accent="#ff6a13", accentdeep="#ff8438",
                pickwash="#2a1607", pickedge="#ff6a13", pick="#ff6a13",
                good="#3fbf72", bad="#ff4d4d")),
]

VARS = [("field", "--field"), ("page", "--page"), ("card", "--card"), ("well", "--well"),
        ("line", "--line"), ("ink", "--ink"), ("ink2", "--ink-2"), ("ink3", "--ink-3"),
        ("onfield", "--on-field"), ("onfield2", "--on-field-2"), ("accent", "--accent"),
        ("accentdeep", "--accent-deep"), ("pickwash", "--pick-wash"),
        ("pickedge", "--pick-edge"), ("pick", "--pick"), ("good", "--good"), ("bad", "--bad")]

SWATCHES = [("field", "chrome"), ("page", "page"), ("card", "card"),
            ("accent", "accent"), ("pick", "pick")]


def logo_uri(team_id: str) -> str:
    """A team's mark, downscaled and inlined. 76px covers the 32px it renders at on 2x."""
    from PIL import Image

    path = os.path.join(LOGO_DIR, "%s.png" % team_id)
    if not os.path.exists(path):
        raise SystemExit("missing logo %s. Run: python scripts/fetch_teams.py" % path)
    im = Image.open(path).convert("RGBA")
    im.thumbnail((76, 76), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def theme_css(t: dict) -> str:
    body = ["  --display: %s;" % t["display"], "  --r-card: %s;" % t["rcard"],
            "  --r-in: %s;" % t["rin"], "  --sh: %s;" % t["sh"]]
    body += ["  %s: %s;" % (var, t["v"][key]) for key, var in VARS]
    return ".t%s {\n%s\n}" % (t["n"], "\n".join(body))


def team_html(team, picked_side, side) -> str:
    abbr, school, _tid, rank = team
    on = " is-picked" if picked_side == side else ""
    ring = '<span class="ring"></span>' if picked_side == side else ""
    rk = '<span class="rk">%s</span>' % rank if rank else ""
    return ('<div class="tpick%s"><span class="logo lg-%s"></span>'
            '<span class="tname">%s%s</span>%s</div>' % (on, abbr, rk, school, ring))


def screen_html() -> str:
    rows = []
    for away, home, when, spread, tv, picked in GAMES:
        rows.append(
            '      <div class="grow">\n'
            '        <div class="gmeta"><span>%s</span><span class="dot">&middot;</span>\n'
            '          <span class="spread num">%s</span>\n'
            '          <span class="tv">%s</span><span class="prev">Preview</span></div>\n'
            '        <div class="gteams">%s<span class="at">@</span>%s</div>\n'
            '      </div>' % (when, spread, tv,
                              team_html(away, picked, "away"), team_html(home, picked, "home")))
    return '''    <div class="phone">
      <div class="hdr">
        <div><span class="hdr-t">Motley Pick&rsquo;em</span>
          <span class="hdr-w">Week 2 &middot; 20 games</span></div>
        <span class="hdr-me"><span class="av">G</span>Grant</span>
      </div>
      <div class="body">
        <div class="prog-row"><span class="prog"><span class="prog-f"></span></span>
          <span class="prog-n num">7/20</span></div>
%s
        <div class="cta"><span class="btn">Rank my 20 picks</span></div>
      </div>
      <div class="tabs"><span class="tab is-on">Picks</span><span class="tab">Board</span>
        <span class="tab">Standings</span><span class="tab">Setup</span></div>
    </div>''' % "\n".join(rows)


def card_html(t: dict, screen: str) -> str:
    sw = "".join('<span class="sw"><i style="background:%s"></i><b>%s</b></span>'
                 % (t["v"][k], label) for k, label in SWATCHES)
    face = t["display"].split(",")[0].replace("'", "")
    return ('  <section class="card t%s">\n'
            '    <header class="cap"><span class="num-badge">%s</span>\n'
            '      <div class="cap-t"><h2>%s</h2><p>%s</p></div>\n'
            '      <span class="kind">%s</span></header>\n%s\n'
            '    <footer class="spec"><div class="sws">%s</div>\n'
            '      <div class="meta"><span>%s</span><span>radius %s</span></div></footer>\n'
            '  </section>' % (t["n"], t["n"], t["name"], t["note"], t["kind"], screen,
                              sw, face, t["rcard"]))


def build() -> str:
    ids = {}
    for away, home, *_ in GAMES:
        for abbr, _school, tid, _rank in (away, home):
            ids[abbr] = tid
    logo_css = "\n".join(".lg-%s{background-image:url(%s)}" % (a, logo_uri(t))
                         for a, t in sorted(ids.items()))
    screen = screen_html()
    cards = "\n".join(card_html(t, screen) for t in THEMES)
    themes = "\n".join(theme_css(t) for t in THEMES)
    css = io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               "theme_board.css"), encoding="utf-8").read()
    return TEMPLATE.format(css=css, logo_css=logo_css, themes=themes, cards=cards,
                           dark=", ".join(".t%s .phone" % t["n"] for t in THEMES
                                          if t["kind"].startswith("dark")))


TEMPLATE = """<title>Pick'em Theme Board</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;700;800\
&family=Bitter:wght@600;700;800&family=Inter:wght@400;500;600;700;800&family=Instrument+Serif\
&family=JetBrains+Mono:wght@400;700&family=Oswald:wght@500;600;700&display=swap">
<style>
{css}

{logo_css}

{themes}

/* A dark theme's chrome is nearly the board colour, so give those phones an edge. */
{dark} {{ box-shadow: 0 0 0 1px var(--board-line), 0 10px 30px rgba(0,0,0,.35); }}
</style>

<div class="wrap">
  <header class="intro">
    <p class="eyebrow">Motley Pick&rsquo;em &middot; theme options</p>
    <h1>Ten ways to sharpen the app</h1>
    <p>Every screen below is the real pick flow: the same header, progress bar, game cards,
      pick state, Preview pill and tab bar, with nothing changed but the tokens. Toledo at
      Michigan State and East Carolina at Alabama are picked so you can see the selected
      state, and Miami carries its AP rank.</p>
    <p class="how">05 Slate is the one that shipped. Token names match the semantic contract
      in src/theme.css exactly, so any of these is a copy-paste into the palette block.</p>
  </header>
  <div class="grid">
{cards}
  </div>
</div>
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "outputs", "theme-board.html"))
    a = ap.parse_args()
    html = build()
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    io.open(a.out, "w", encoding="utf-8", newline="\n").write(html)
    print("wrote %s (%.0f KB, %d themes)" % (a.out, len(html.encode()) / 1024, len(THEMES)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
