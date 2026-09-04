"""Render every profile-picture option at the sizes the app actually uses.

    python scripts/build_avatar_board.py            # -> outputs/avatar-board.html

Grant asked on 2026-09-04 for football-themed profile pictures picked from a set pack.
The pack is already in the repo: static/logos holds all 138 FBS marks and
inputs/fbs_teams.json holds each school's own brand colours. So the open question is not
"where do we get art" but "which treatment survives the app".

That is the whole reason this board exists. <Avatar> renders at 22px on the Board, which
is the screen the family stares at all Saturday, and a logo that reads beautifully in a
picker at 56px can be an unidentifiable smudge at 22. Every option here is therefore
rendered at 22, 36 and 56 together, on the real chrome colour, so the 22px column is
impossible to skip past.

The sample teams are chosen to be unflattering on purpose: two clean letterforms and two
busy marks. A contact sheet that only shows the easy cases is a sales brochure.

Static HTML, logos inlined as data URIs, so the page opens anywhere.
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO_DIR = os.path.join(ROOT, "static", "logos")
TEAMS = os.path.join(ROOT, "inputs", "fbs_teams.json")
OUT = os.path.join(ROOT, "outputs", "avatar-board.html")

# The four seats, with the colours already assigned in migrations/001_init.sql.
SEATS = [("Grant", "#c8551b"), ("James", "#1f7a4d"),
         ("Parker", "#2f6fb0"), ("Nicole", "#b0234b")]

# Deliberately mixed: two clean letterforms, two busy marks. If a treatment only works
# for the first two, that is the finding.
SAMPLE_ABBRS = ["UGA", "MICH", "COLO", "STAN"]

SIZES = [22, 36, 56]
SIZE_NOTE = {22: "Board", 36: "Standings", 56: "Profile"}

OPTIONS = [
    ("today", "What you have now",
     "Initial on your assigned colour. Reads at every size. No football in it at all."),
    ("logo-plain", "Team mark on a light disc",
     "Cleanest look. Busy marks go to mush at 22px, and two people picking the same "
     "school become indistinguishable."),
    ("logo-team", "Team mark on that school's own colour",
     "The most football of the lot. Contrast is out of your hands: it is whatever the "
     "school's brand happens to be."),
    ("logo-ring", "Team mark, ring in your colour",
     "The ring keeps four people apart even when two pick the same school. Costs a "
     "couple of pixels of mark at 22px."),
    ("initial-team", "Your initial, your team's colour",
     "Always legible, because it is still a letter. The mark appears only where there "
     "is room for it."),
    ("icon", "Neutral football icons",
     "No allegiances. Everyone equal, and nothing to argue about at Thanksgiving."),
]

# Simple enough to still read as a shape at 22px.
ICONS = {
    "ball": ("<ellipse cx='12' cy='12' rx='9' ry='5.6'/>"
             "<path d='M3.2 12h17.6M9 8.6v6.8M15 8.6v6.8' stroke='#fff' "
             "stroke-width='1.4' fill='none'/>"),
    "helmet": ("<path d='M4 13a8 8 0 0116 0v3h-6l-1.5 2H7a3 3 0 01-3-3z'/>"
               "<path d='M4.6 15.4H14' stroke='#fff' stroke-width='1.4' fill='none'/>"),
    "goal": ("<path d='M6 5v14M18 5v14M6 9h12M12 9v10' stroke='#fff' stroke-width='1.9' "
             "fill='none' stroke-linecap='round'/>"),
    "pennant": ("<path d='M6 4v16' stroke='#fff' stroke-width='1.7' "
                "stroke-linecap='round'/><path d='M7.2 5.2l10.6 3.4-10.6 3.4z' "
                "fill='#fff'/>"),
}
ICON_ORDER = ["ball", "helmet", "goal", "pennant"]


def load_teams():
    with open(TEAMS, encoding="utf-8") as f:
        data = json.load(f)
    teams = data if isinstance(data, list) else data.get("teams", [])
    by_abbr = {t["abbr"]: t for t in teams}
    missing = [a for a in SAMPLE_ABBRS if a not in by_abbr]
    if missing:
        raise SystemExit("no such team abbr: %s" % ", ".join(missing))
    return [by_abbr[a] for a in SAMPLE_ABBRS]


def logo_uri(team_id):
    """Inlined at 128px so the 56px sample stays crisp on a 2x screen."""
    from PIL import Image

    path = os.path.join(LOGO_DIR, "%s.png" % team_id)
    if not os.path.exists(path):
        raise SystemExit("missing logo %s. Run: python scripts/fetch_teams.py" % path)
    im = Image.open(path).convert("RGBA")
    im.thumbnail((128, 128), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def avatar(kind, seat, team, uri, size, idx):
    who, color = seat
    s = size
    base = ("display:inline-grid;place-items:center;border-radius:50%%;flex:none;"
            "overflow:hidden;width:%dpx;height:%dpx;" % (s, s))
    letter = ("font-family:Archivo,system-ui,sans-serif;font-weight:700;color:#fff;"
              "line-height:1;font-size:%.1fpx;" % (s * 0.42))
    team_color = team.get("color") or "#333333"

    if kind == "today":
        return ("<span style='%s%sbackground:%s'>%s</span>"
                % (base, letter, color, who[0].upper()))
    if kind == "logo-plain":
        return ("<span style='%sbackground:#f2f4f7'><img src='%s' "
                "style='width:74%%;height:74%%;object-fit:contain'></span>" % (base, uri))
    if kind == "logo-team":
        return ("<span style='%sbackground:%s'><img src='%s' "
                "style='width:72%%;height:72%%;object-fit:contain'></span>"
                % (base, team_color, uri))
    if kind == "logo-ring":
        ring = max(1.5, s * 0.075)
        return ("<span style='%sbackground:#f2f4f7;box-shadow:inset 0 0 0 %.1fpx %s'>"
                "<img src='%s' style='width:66%%;height:66%%;object-fit:contain'></span>"
                % (base, ring, color, uri))
    if kind == "initial-team":
        return ("<span style='%s%sbackground:%s'>%s</span>"
                % (base, letter, team_color, who[0].upper()))
    if kind == "icon":
        glyph = ICONS[ICON_ORDER[idx % len(ICON_ORDER)]]
        d = s * 0.62
        return ("<span style='%sbackground:%s'><svg viewBox='0 0 24 24' width='%.0f' "
                "height='%.0f' fill='#fff'>%s</svg></span>" % (base, color, d, d, glyph))
    raise AssertionError(kind)


def build():
    teams = load_teams()
    uris = [logo_uri(t["id"]) for t in teams]

    rows = []
    for kind, title, note in OPTIONS:
        cells = []
        for size in SIZES:
            marks = "".join(avatar(kind, SEATS[i], teams[i], uris[i], size, i)
                            for i in range(len(SEATS)))
            cells.append("<div class='sz'><div class='row'>%s</div>"
                         "<div class='cap'>%dpx &middot; %s</div></div>"
                         % (marks, size, SIZE_NOTE[size]))
        rows.append("<section class='opt'><header><h2>%s</h2><p>%s</p></header>"
                    "<div class='sizes'>%s</div></section>"
                    % (title, note, "".join(cells)))

    names = " &middot; ".join("%s = %s" % (SEATS[i][0], teams[i]["school"])
                              for i in range(len(SEATS)))
    return TEMPLATE % {"rows": "".join(rows), "names": names}


TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Profile picture options</title>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;700;800&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root { --field:#28313d; --page:#f6f7f9; --card:#fff; --ink:#1a222c;
          --ink2:#5b6675; --ink3:#8a94a3; --line:#e3e7ec; }
  * { box-sizing:border-box }
  body { margin:0; background:var(--page); color:var(--ink);
         font-family:Inter,system-ui,sans-serif; }
  header.top { background:var(--field); color:#fff; padding:22px 24px; }
  header.top h1 { font-family:Archivo,sans-serif; margin:0 0 4px; font-size:21px; }
  header.top p { margin:0; opacity:.72; font-size:13px; max-width:78ch; line-height:1.5; }
  .wrap { padding:20px; display:grid; gap:14px; max-width:1060px; margin:0 auto; }
  .opt { background:var(--card); border:1px solid var(--line); border-radius:14px;
         padding:16px 18px; }
  .opt header h2 { font-family:Archivo,sans-serif; font-size:16px; margin:0 0 3px; }
  .opt header p { margin:0 0 14px; font-size:12.5px; color:var(--ink2); max-width:64ch;
                  line-height:1.5; }
  .sizes { display:flex; gap:24px; flex-wrap:wrap; align-items:flex-end; }
  .sz { background:var(--field); border-radius:10px; padding:12px 14px 8px; }
  .row { display:flex; gap:10px; align-items:center; min-height:58px; }
  .cap { margin-top:7px; font-size:10px; letter-spacing:.07em; text-transform:uppercase;
         color:#93a0b1; font-weight:600; }
  .foot { font-size:12px; color:var(--ink3); padding:0 4px 26px; text-align:center; }
</style></head><body>
<header class="top">
  <h1>Profile pictures &middot; six options</h1>
  <p>Rendered on the real chrome colour at the three sizes the app uses. The 22px column is the Board, the screen everyone watches on Saturday, and it is the one that decides this.</p>
</header>
<div class="wrap">%(rows)s</div>
<p class="foot">Sample teams: %(names)s &mdash; two clean letterforms, two busy marks, on purpose.</p>
</body></html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    html = build()
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(html)
    print("wrote %s (%.0f KB)" % (a.out, len(html) / 1024))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
