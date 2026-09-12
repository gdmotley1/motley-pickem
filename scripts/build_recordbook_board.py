"""Render the reworked record book in three layouts, and write one badge prompt per record.

Grant, 2026-09-12, after the ballot: worst pick should "just say eight on Georgia Tech",
biggest blowout comes back "but change the name, say, biggest margin of victory in a week
and put that in the hall of fame". Everything he tapped Yes is in; anything unmarked is no.
"Rework the sections to look good and mark it up and show me. Give me a couple examples.
Remember, I don't want any tiny text." He will make the badge art himself in ChatGPT, one
image per record, "each one is gonna be unique, but they all need to fit the same style",
shiny, chrome, different colours: so this also writes those prompts.

WHAT IS IN, from ballot/grant in the ballot artifact's db, read 2026-09-12 20:35:
  shelf (every player)  most points in a week, best record in a week, fewest points in a
                        week, longest winning streak, worst pick, biggest upset you called,
                        weeks won, season record
  hall of fame          perfect week, only one who called it, most points in a season,
                        biggest upset called, won a week by 20 or more, two-touchdown upset,
                        three upsets in one week, biggest margin of victory in a week
  hall of shame         lost your 20
  out                   ten in a row, heartbreaker, your 20-pointers, the 7-point upset
                        floor, collapsed shelves, and everything he tapped No

The badges drawn here are placeholders in the colours the prompts ask for, so the layouts
can be judged before the real art exists. BADGES below is the single source for the board,
the prompts on it, and docs/badge-prompts.md.

    python scripts/build_recordbook_board.py
"""
from __future__ import annotations

import base64
import html
import io
import json
import os
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "outputs", "recordbook-board.html")
PROMPTS_MD = os.path.join(ROOT, "docs", "badge-prompts.md")

NAMES = ["Grant", "James", "Parker", "Nicole"]
TEAM = {"Grant": "8", "James": "2655", "Parker": "338", "Nicole": "61"}

# ------------------------------------------------------------------------ badges
# id, section, record name, enamel colour (words for the prompt, hex for the placeholder),
# emblem, placeholder glyph from the current icon set.
BADGES = [
    ("best_week", "shelf", "Most points in a week", "emerald green", "#0f9d58",
     "an American football with a bold upward arrow rising behind it", "points"),
    ("best_record", "shelf", "Best record in a week", "lemon yellow", "#f2c500",
     "one bold, thick checkmark", "week_record"),
    ("low_week", "shelf", "Fewest points in a week", "slate grey", "#6b7b8f",
     "an American football with a bold downward arrow falling behind it", "week_low"),
    ("streak", "shelf", "Longest winning streak", "blaze orange", "#ff6a13",
     "a tall, stylized flame", "streak"),
    ("worst_miss", "shelf", "Worst miss", "deep purple", "#6a2c91",
     "a thumbs-down hand", "worst_pick"),
    ("my_upset", "shelf", "Biggest upset you called", "electric teal", "#00a99d",
     "a single jagged lightning bolt", "upset"),
    ("weeks_won", "shelf", "Weeks won", "royal blue", "#2459e0",
     "a classic two-handled trophy cup", "weeks_won"),
    ("season_record", "shelf", "Season record", "rose pink", "#e05a8a",
     "a clipboard with three checkmarks on it", "record"),
    ("perfect_week", "fame", "Perfect week", "pearl white with a faint blue shimmer", "#e9eef5",
     "a brilliant-cut diamond", "perfect"),
    ("only_one", "fame", "Only one who called it", "ruby red", "#c0112f",
     "a single person silhouette standing in a cone of spotlight", "lone"),
    ("season_points", "fame", "Most points in a season", "jet black", "#15181c",
     "a championship ring with a large faceted stone", "points"),
    ("big_upset", "fame", "Biggest upset called", "lime green", "#6fbf0a",
     "a slingshot, pulled back and ready to fire", "upset"),
    ("win_by_20", "fame", "Won a week by 20 or more", "amber", "#f0a202",
     "a rocket blasting upward with a short flame trail", "blowout"),
    ("two_td_upset", "fame", "Two-touchdown upset", "cyan", "#16bde0",
     "two American footballs crossed like swords", "upset"),
    ("three_upsets", "fame", "Three upsets in one week", "violet", "#8b3fd9",
     "three lightning bolts fanned out side by side", "upset"),
    ("margin", "fame", "Biggest margin of victory in a week", "hot magenta", "#e0218a",
     "a winners' podium where the first-place block towers far above a short second-place "
     "block", "week_points"),
    ("lost_20", "shame", "Lost your 20", "rust red", "#9c3b1b",
     "a deflated, sagging American football", "week_low"),
]
BY_ID = {b[0]: b for b in BADGES}
LIGHT = {"best_record", "perfect_week", "big_upset", "win_by_20", "two_td_upset"}

RIM = {
    "shelf": "The rim is thick, polished mirror chrome with fine machined ridges around its "
             "edge.",
    "fame": "The rim is thick, polished gold chrome with fine machined ridges, wrapped by a "
            "slim raised gold laurel wreath, with one small raised star at the top of the rim.",
    "shame": "The rim is thick, dark gunmetal chrome, a little scuffed, and a thin hairline "
             "crack runs across the enamel.",
}


def prompt(b):
    _bid, section, _name, colour, _hex, emblem, _glyph = b
    return (
        "Create a single premium achievement badge icon for a college football pick'em app. "
        "It is a glossy, photorealistic 3D medallion, perfectly round and seen straight on, "
        "with no tilt or perspective. %s Inside the rim is a domed, glass-smooth enamel face "
        "in %s, with a raised, highly polished chrome emblem in the center: %s. Mirror-like "
        "chrome reflections, bright specular highlights, one crisp curved reflection across "
        "the upper left of the dome, beveled edges, rich saturated color and strong contrast "
        "between the emblem and the enamel. Soft studio lighting from the upper left. The "
        "emblem is bold and simple with thick, clean shapes, so the badge still reads clearly "
        "when shown very small, about 48 pixels wide. No text, letters, numbers or words "
        "anywhere. Transparent background, PNG, no cast shadow and no glow outside the rim, "
        "nothing else in the image. Square 1024 by 1024 canvas, badge centered and filling "
        "about 90 percent of it. This is one badge in a matching set of 17: every badge in "
        "the set has the same rim thickness, lighting, gloss and straight-on camera angle, "
        "and differs only in its rim finish, enamel color and emblem."
        # The record's name is deliberately NOT in the prompt: image models tend to letter a
        # title onto the art even when told not to. The file name says which badge it is.
        % (RIM[section], colour, emblem))


# ------------------------------------------------------------------ the season
# Real 2026 season, Week 1 final and Week 2 one game graded; week records count finished
# weeks only. Teams are ESPN's abbreviations (GT, OKST, NEV), per Grant, 2026-09-12. Worst miss (renamed from worst pick by Grant, 2026-09-12) says only what was
# put on whom.
SHELF_ROWS = ["best_week", "best_record", "low_week", "streak", "worst_miss", "my_upset",
              "weeks_won", "season_record"]
SHELF = {
    "Grant": {"best_week": ("186", "Week 1"), "best_record": ("16-4", "Week 1"),
              "low_week": (None, "After two weeks"), "streak": ("8", "in a row"),
              "worst_miss": ("8", "on GT"), "my_upset": ("+1.5", "NEV"),
              "weeks_won": ("1", "of 1"), "season_record": ("16-5", "this season")},
    "James": {"best_week": ("179", "Week 1"), "best_record": ("16-4", "Week 1"),
              "low_week": (None, "After two weeks"), "streak": ("10", "in a row"),
              "worst_miss": ("17", "on GT"), "my_upset": (None, "None yet"),
              "weeks_won": ("0", "of 1"), "season_record": ("17-4", "this season")},
    "Parker": {"best_week": ("164", "Week 1"), "best_record": ("12-8", "Week 1"),
               "low_week": (None, "After two weeks"), "streak": ("4", "in a row"),
               "worst_miss": ("10", "on GT"), "my_upset": (None, "None yet"),
               "weeks_won": ("0", "of 1"), "season_record": ("13-8", "this season")},
    "Nicole": {"best_week": ("147", "Week 1"), "best_record": ("10-10", "Week 1"),
               "low_week": (None, "After two weeks"), "streak": ("6", "in a row"),
               "worst_miss": ("15", "on OKST"), "my_upset": ("+1.5", "NEV"),
               "weeks_won": ("0", "of 1"), "season_record": ("11-10", "this season")},
}
RANK = {"James": 1, "Grant": 1, "Parker": 3, "Nicole": 4}
POINTS = {"James": 186, "Grant": 186, "Parker": 165, "Nicole": 160}

# award id -> (holders, detail) ; empty holders = up for grabs
FAME = [
    ("season_points", ["Grant", "James"], "186 points"),
    ("big_upset", ["Grant", "Nicole"], "NEV +1.5"),
    ("margin", ["Grant"], "Won Week 1 by 7"),
    ("perfect_week", [], "Every game right in a week"),
    ("only_one", [], "The only one to pick a winner"),
    ("win_by_20", [], "Finish a week 20 points clear"),
    ("two_td_upset", [], "Pick a 14-point underdog that wins"),
    ("three_upsets", [], "Three underdogs right in one week"),
]
SHAME = [("lost_20", [], "Nobody yet. Every 20 has won so far.")]


# ------------------------------------------------------------------ app sources


def app_module():
    # src/lib/badgeIcons.js was deleted when Grant's real badge art shipped (2026-09-12).
    # Only the old stand-in boards used its glyphs; without it they draw empty medals.
    path = os.path.join(ROOT, "src", "lib", "badgeIcons.js")
    if not os.path.exists(path):
        return {"icons": {}}
    script = ("const m = await import(process.argv[1]);"
              "console.log(JSON.stringify({icons: m.ICONS}))")
    url = "file:///" + path.replace(os.sep, "/")
    out = subprocess.run(["node", "--input-type=module", "-e", script, url],
                         capture_output=True, text=True, encoding="utf-8", check=True)
    return json.loads(out.stdout)


MOD = app_module()
TEAMS = {t["id"]: t for t in json.load(
    open(os.path.join(ROOT, "static", "data", "teams.json"), encoding="utf-8"))}
e = html.escape


def logo(team_id, px=72):
    from PIL import Image

    t = TEAMS[team_id]
    name = "%s-dark" % team_id if t.get("cut") == "dark" else team_id
    im = Image.open(os.path.join(ROOT, "static", "logos", "%s.png" % name)).convert("RGBA")
    im.thumbnail((px, px), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def face(name, size):
    t = TEAMS[TEAM[name]]
    n = round(size * 0.72)
    return ('<span class="avatar avatar--team rk-face" style="width:%dpx;height:%dpx;'
            'background:%s"><i class="rk-mk" style="width:%dpx;height:%dpx;'
            'background-image:var(--lg-%s)"></i></span>' % (size, size, t["bg"], n, n, t["id"]))


def medal(bid, size, open_=False):
    """A stand-in for Grant's badge: the rim finish and enamel colour its prompt asks for,
    with the current icon set's glyph in the middle until the real art lands."""
    _id, section, _n, _c, hexc, _em, glyph = BY_ID[bid]
    ink = "#1b1f24" if bid in LIGHT else "#ffffff"
    return ('<span class="rk-medal rk-medal--%s%s" style="--size:%dpx;--enamel:%s;--glyph:%s">'
            '<span class="rk-medal__enamel"><svg viewBox="0 0 512 512" aria-hidden="true">'
            '<use href="#i-%s"/></svg></span></span>'
            % (section, " is-open" if open_ else "", size, hexc, ink, glyph))


def holders(names, size=22):
    faces = "".join(face(n, size) for n in names)
    return ('<span class="rk-hold"><span class="rk-hold__faces">%s</span><span>%s</span></span>'
            % (faces, " &amp; ".join(names)))


def phone(inner):
    return ('<div class="rk-phone"><div class="app" data-mode="book"><main class="app__body">'
            '<div class="app__page">%s</div></main></div></div>' % inner)


def title(text, kicker=None, cls=""):
    k = '<p class="rk-kick">%s</p>' % e(kicker) if kicker else ""
    return '<div class="rk-title %s">%s<h3>%s</h3></div>' % (cls, k, e(text))


# --------------------------------------------------------------- A: the case


def shelf_card(name, band=False):
    rows = []
    for rid in SHELF_ROWS:
        value, detail = SHELF[name][rid]
        rows.append(
            '<div class="rkA-row%s">%s<div class="rkA-txt"><p class="rkA-k">%s</p>'
            '<p class="rkA-d">%s</p></div><p class="rkA-v num">%s</p></div>'
            % (" is-open" if value is None else "", medal(rid, 46, value is None),
               e(BY_ID[rid][2]), e(detail), e(value) if value else "&ndash;"))
    t = TEAMS[TEAM[name]]
    style = (' style="--band:%s"' % t.get("alt", "#223")) if band else ""
    return ('<section class="rkA-shelf%s"%s><div class="rkA-hd">%s<h3>%s</h3>'
            '<span class="rkA-pts num">%d<small>pts</small></span></div>%s</section>'
            % (" has-band" if band else "", style, face(name, 40), name, POINTS[name],
               "".join(rows)))


def fame_tile(bid, who, detail, size=84):
    open_ = not who
    return ('<div class="rkA-award%s">%s<p class="rkA-award__k">%s</p>%s<p class="rkA-award__d">%s</p>'
            '</div>' % (" is-open" if open_ else "", medal(bid, size, open_), e(BY_ID[bid][2]),
                        '<p class="rkA-grab">Up for grabs</p>' if open_ else holders(who),
                        e(detail)))


def shame_block(size=72):
    bid, who, detail = SHAME[0]
    return ('<section class="rk-shame"><div class="rk-shame__hd"><h3>Hall of shame</h3></div>'
            '<div class="rk-shame__row">%s<div><p class="rk-shame__k">%s</p><p class="rk-shame__d">%s'
            '</p></div></div></section>' % (medal(bid, size, not who), e(BY_ID[bid][2]), e(detail)))


def option_a():
    shelves = "".join(shelf_card(n) for n in ["Grant", "James", "Parker", "Nicole"])
    fame = "".join(fame_tile(*a) for a in FAME)
    return phone(title("Shelves", "Everyone's numbers") + '<div class="rkA-shelves">%s</div>'
                 % shelves + title("Hall of fame", "The record book", "is-fame")
                 + '<div class="rkA-fame">%s</div>' % fame + shame_block())


# ------------------------------------------------------------ B: head to head


def option_b():
    head = "".join('<span class="rkB-col">%s<b>%s</b></span>' % (face(n, 30), n) for n in NAMES)
    rows = []
    for rid in SHELF_ROWS:
        cells = []
        for n in NAMES:
            value, detail = SHELF[n][rid]
            cells.append('<span class="rkB-cell%s"><b class="num">%s</b><em>%s</em></span>'
                         % (" is-open" if value is None else "",
                            e(value) if value else "&ndash;", e(detail)))
        rows.append('<div class="rkB-rec"><div class="rkB-rec__hd">%s<p>%s</p></div>'
                    '<div class="rkB-cells">%s</div></div>'
                    % (medal(rid, 40), e(BY_ID[rid][2]), "".join(cells)))
    plaques = "".join(
        '<div class="rkB-plaque%s">%s<div class="rkB-plaque__txt"><p class="rkB-plaque__k">%s</p>'
        '%s<p class="rkB-plaque__d">%s</p></div></div>'
        % (" is-open" if not who else "", medal(bid, 64, not who), e(BY_ID[bid][2]),
           holders(who, 24) if who else '<p class="rkA-grab">Up for grabs</p>', e(detail))
        for bid, who, detail in FAME)
    return phone(title("Head to head", "Everyone's numbers")
                 + '<div class="rkB-sticky">%s</div><div class="rkB-recs">%s</div>'
                 % (head, "".join(rows))
                 + title("Hall of fame", "The record book", "is-fame")
                 + '<div class="rkB-plaques">%s</div>' % plaques + shame_block(64))


# ------------------------------------------------------------ C: trophy room


def option_c():
    won = [a for a in FAME if a[1]]
    open_ = [a for a in FAME if not a[1]]
    stage = "".join(fame_tile(bid, who, detail, 104) for bid, who, detail in won)
    grabs = "".join(
        '<div class="rkC-grab">%s<p>%s</p><em>%s</em></div>' % (medal(bid, 62, True), e(BY_ID[bid][2]), e(detail))
        for bid, _who, detail in open_)
    shelves = "".join(shelf_card(n, band=True) for n in ["Grant", "James", "Parker", "Nicole"])
    return phone(
        '<section class="rkC-stage"><p class="rk-kick">The record book</p><h3>Hall of fame</h3>'
        '<div class="rkC-won">%s</div><p class="rkC-sub">Up for grabs</p>'
        '<div class="rkC-grabs">%s</div></section>' % (stage, grabs)
        + shame_block()
        + title("Shelves", "Everyone's numbers") + '<div class="rkA-shelves">%s</div>' % shelves)


OPTIONS = [
    ("A", "The case", option_a,
     "Shelves first, one card each with all eight records written out, then the Hall of fame "
     "two across with big badges, then the Hall of shame. The closest to what you have been "
     "picking, made big.",
     "3,891px tall at phone width, the longest: four shelves of eight rows is 32 rows "
     "before the Hall of fame starts."),
    ("B", "Head to head", option_b,
     "Every record once, with all four of your numbers side by side under it, so you can "
     "compare at a glance. The Hall of fame is a column of plaques: badge, award, who holds "
     "it, and what they did.",
     "2,445px tall, about 1,450px shorter than A, and the easiest to compare. Four numbers "
     "across a phone leaves each person about 80px, so details are one or two words, like "
     "GT."),
    ("C", "Trophy room", option_c,
     "The loud one. The Hall of fame leads, on a spotlit stage with the awards somebody "
     "holds shown huge and the rest waiting in a row of empty sockets. Then shame, then "
     "shelves, each headed in that person's school colour.",
     "3,809px tall. The most dramatic, and the Hall of fame gets seen first by everyone. "
     "Early in the season most awards are unclaimed, so the stage is three badges and a row "
     "of sockets."),
]


def prompts_html():
    groups = [("shelf", "On everyone's shelf"), ("fame", "Hall of fame"), ("shame", "Hall of shame")]
    out = []
    n = 0
    for section, heading in groups:
        cards = []
        for b in BADGES:
            if b[1] != section:
                continue
            n += 1
            cards.append(
                '<article class="rk-prompt"><div class="rk-prompt__hd">%s<div><p class="rk-prompt__n">%d. %s'
                '</p><p class="rk-prompt__f">Save as <code>%s.png</code></p></div></div>'
                '<textarea readonly rows="7" aria-label="Prompt for %s">%s</textarea>'
                '<button type="button" class="rk-copy">Copy prompt</button></article>'
                % (medal(b[0], 52), n, e(b[2]), b[0], e(b[2]), e(prompt(b))))
        out.append('<h3 class="rk-prompts__g">%s</h3>%s' % (heading, "".join(cards)))
    return "".join(out)


def prompts_md():
    lines = [
        "# Badge prompts",
        "",
        "One ChatGPT image prompt per record-book badge, 17 in all. Written 2026-09-12 from",
        "`scripts/build_recordbook_board.py`, which is the source: edit the list there and",
        "rebuild rather than editing this file.",
        "",
        "How to run them:",
        "",
        "1. Run all 17 in one ChatGPT conversation, starting with #1, so it keeps the style.",
        "2. If one drifts, reply: \"Match the first badge exactly: same rim, lighting, gloss and",
        "   angle. Only the enamel color and emblem change.\"",
        "3. Download each as PNG with a transparent background and save it to",
        "   `inputs/badges/` under the file name given below.",
        "",
        "Three rim finishes tell the sections apart: chrome for everyone's shelf, gold with a",
        "laurel wreath for the Hall of fame, and dark cracked gunmetal for the Hall of shame.",
        "",
    ]
    n = 0
    for section, heading in (("shelf", "On everyone's shelf"), ("fame", "Hall of fame"),
                             ("shame", "Hall of shame")):
        lines += ["## %s" % heading, ""]
        for b in BADGES:
            if b[1] != section:
                continue
            n += 1
            lines += ["### %d. %s" % (n, b[2]), "", "Save as `inputs/badges/%s.png`" % b[0], "",
                      "```text", prompt(b), "```", ""]
    return "\n".join(lines)


def build(standalone: bool) -> str:
    css = "".join(open(os.path.join(ROOT, "src", f), encoding="utf-8").read()
                  for f in ("theme.css", "app.css"))
    board = open(os.path.join(ROOT, "scripts", "recordbook_board.css"), encoding="utf-8").read()
    body = open(os.path.join(ROOT, "scripts", "recordbook_board.html"), encoding="utf-8").read()
    logos = ":root{%s}" % "".join("--lg-%s:url(%s);" % (t, logo(t)) for t in TEAM.values())
    symbols = ('<svg width="0" height="0" style="position:absolute" aria-hidden="true">%s</svg>'
               % "".join('<symbol id="i-%s" viewBox="0 0 512 512">%s</symbol>' % (k, v)
                         for k, v in MOD["icons"].items()))
    opts = "".join(
        '<section class="bd-opt" id="opt-%s"><div class="bd-opt__hd"><span class="bd-opt__k">%s</span>'
        '<h2>%s</h2><span class="bd-opt__px" data-measure>&hellip;</span></div>'
        '<div class="bd-opt__grid"><div class="bd-opt__copy"><p>%s</p><p class="bd-opt__cost">'
        '<b>Cost.</b> %s</p></div>%s</div></section>'
        % (k, k, e(t), e(what), e(cost), fn()) for k, t, fn, what, cost in OPTIONS)
    doc = ('<!doctype html>\n<meta charset="utf-8">\n'
           '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
           if standalone else "")
    return (doc + "<title>Record Book Layouts</title>\n"
            '<link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..800'
            '&family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">\n'
            "<style>%s\n%s\n%s</style>%s" % (logos, css, board, symbols)
            + body.replace("{{OPTIONS}}", opts).replace("{{PROMPTS}}", prompts_html())
            .replace("{{COUNT}}", str(len(BADGES))))


if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    for path, standalone in ((OUT, True), (OUT.replace(".html", ".artifact.html"), False)):
        page = build(standalone)
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(page)
        print("wrote %s  (%.0f KB)" % (path, len(page.encode()) / 1024))
    with open(PROMPTS_MD, "w", encoding="utf-8", newline="") as fh:
        fh.write(prompts_md())
    print("wrote %s  (%d prompts)" % (PROMPTS_MD, len(BADGES)))
