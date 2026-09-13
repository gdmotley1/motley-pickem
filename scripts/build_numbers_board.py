"""Six numbered ways to draw "Everyone's numbers", against what is live now.

Grant, 2026-09-12, the night the record book shipped: "The hall of fame part is awesome.
Can we look at everyone's numbers part? It's a little clunky and hard to read, like, what
the record actually is. Like, the name and all is big. But, like, let's rework this section
and give me some options to pick from that are different and easier to read at a glance
and see, but while still being bold with the name and the number and all."

What was wrong with the live headlines, measured rather than guessed: the record's name was
13px condensed capitals with wide tracking, the smallest thing on the row, under a 21px name
and a 25px number; and everyone else ran together in one sentence that wraps mid-name. So
every option here makes the record's name a real heading, keeps the holder and the number
the boldest things in the row, and gives everyone else a fixed place.

The numbers come from the app's own src/lib/seasonRecords.js via scripts/numbers_model.mjs,
so nothing on the board can disagree with the Season tab.

    python scripts/build_numbers_board.py            # after node scripts/numbers_model.mjs
"""
from __future__ import annotations

import base64
import html
import json
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_recordbook_board as rb  # noqa: E402

ROOT = rb.ROOT
OUT = os.path.join(ROOT, "outputs", "numbers-board.html")
MODEL = json.load(open(os.path.join(ROOT, "outputs", "numbers_model.json"), encoding="utf-8"))
ART = os.path.join(ROOT, "src", "assets", "badges")
e = html.escape

NONE = {"worst_miss": "no misses yet"}


# ------------------------------------------------------------------------ pieces


def face(name, size):
    return rb.face(name, size)


def faces(people, size, cls="nb-faces"):
    return '<span class="%s">%s</span>' % (cls, "".join(face(p["name"], size) for p in people))


def names(people):
    return " &amp; ".join(e(p["name"]) for p in people)


def medal(key, size, open_=False):
    """The app's own .medal, drawing the art from a custom property so each badge is
    embedded once however many options use it."""
    return ('<span class="medal%s" style="--medal-size:%dpx" aria-hidden="true">'
            '<i style="background-image:var(--bd-%s)"></i></span>' % (" is-open" if open_ else "", size, key))


def title(text="Everyone's numbers"):
    return ('<div class="book-head"><p class="book-kick">The record book</p><h3>%s</h3></div>'
            % e(text))


def others(r):
    """Everyone who does not hold the record, in ranked order. A detail that only repeats
    the holder's ("Week 1", "in a row", "of 1") is dropped; one that differs stays."""
    lead_detail = r["headline"]["detail"]
    out = []
    for row in r["rows"]:
        if row["mark"]:
            continue
        if row["value"] is None:
            out.append({"name": row["name"], "value": None,
                        "text": row["detail"] or NONE.get(r["key"], "none yet"), "detail": ""})
        else:
            detail = "" if row["detail"] == lead_detail else row["detail"]
            out.append({"name": row["name"], "value": row["display"], "text": "", "detail": detail})
    return out


def next_line(r):
    """The next best, in one short line: "Next: James 179"."""
    rest = others(r)
    if not rest:
        return ""
    first = rest[0]
    same = [o for o in rest if (o["value"], o["text"], o["detail"]) == (first["value"], first["text"], first["detail"])]
    who = "Everyone else" if len(same) >= 3 else " &amp; ".join(e(o["name"]) for o in same)
    if first["value"] is None:
        return "%s: %s" % (who, e(first["text"]))
    tail = (" " + e(first["detail"])) if first["detail"] else ""
    if len(same) >= 3:
        return "%s: %s%s" % (who, e(first["value"]), tail)
    return "Next: %s <b>%s</b>%s" % (who, e(first["value"]), tail)


def cells(r, cls):
    rest = others(r)
    if not rest:
        return ""
    out = []
    for o in rest:
        if o["value"] is None:
            out.append('<div class="%s-cell is-none" data-fit><span>%s</span><b>%s</b></div>'
                       % (cls, e(o["name"]), e(o["text"])))
        else:
            out.append('<div class="%s-cell" data-fit><span>%s</span><b>%s</b>%s</div>'
                       % (cls, e(o["name"]), e(o["value"]),
                          '<em>%s</em>' % e(o["detail"]) if o["detail"] else ""))
    return '<div class="%s-rest" style="--n:%d">%s</div>' % (cls, len(rest), "".join(out))


def ink_for(hexc):
    r, g, b = (int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5))
    lin = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return "#10151c" if 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b) > 0.4 else "#ffffff"


def team_bg(name):
    return rb.TEAMS[rb.TEAM[name]]["bg"]


# ----------------------------------------------------------------------- now (live)


def now():
    """What the Season tab draws today, in its own markup and classes."""
    recs = []
    for r in MODEL["numbers"]:
        h = r["headline"]
        if not h:
            recs.append('<div class="head is-open">%s<div class="head__body"><p class="head__k">%s</p>'
                        '<p class="head__wait">%s</p></div></div>'
                        % (medal(r["key"], 54, True), e(r["label"]), e(r["open"] or "Nobody yet")))
            continue
        recs.append(
            '<div class="head%s">%s<div class="head__body" data-fit><p class="head__k">%s</p>'
            '<p class="head__lead">%s<b>%s</b><span class="head__v num">%s</span>%s</p>%s</div></div>'
            % (" is-bad" if r["bad"] else "", medal(r["key"], 54), e(r["label"]),
               faces(h["leaders"], 28, "head__faces"), names(h["leaders"]), e(h["value"]),
               '<em>%s</em>' % e(h["detail"]) if h["detail"] else "",
               '<p class="head__rest">%s</p>' % e(h["rest"]) if h["rest"] else ""))
    return title() + '<div class="heads">%s</div>' % "".join(recs)


# ---------------------------------------------------------------- 1: title cards


def opt1():
    out = []
    for r in MODEL["numbers"]:
        h = r["headline"]
        cls = "nb1-card" + (" is-bad" if r["bad"] else "") + ("" if h else " is-open")
        hd = '<header class="nb1-hd">%s<h4>%s</h4></header>' % (medal(r["key"], 42, not h), e(r["label"]))
        if not h:
            out.append('<section class="%s">%s<p class="nb1-wait" data-fit>%s</p></section>'
                       % (cls, hd, e(r["open"] or "Nobody yet")))
            continue
        leads = "".join(
            '<div class="nb1-lead" data-fit>%s<div class="nb1-who"><b>%s</b>%s</div>'
            '<span class="nb1-v">%s</span></div>'
            % (face(p["name"], 42), e(p["name"]), '<em>%s</em>' % e(p["detail"]) if p["detail"] else "",
               e(p["display"])) for p in h["leaders"])
        out.append('<section class="%s">%s%s%s</section>' % (cls, hd, leads, cells(r, "nb1")))
    return title() + '<div class="nb1">%s</div>' % "".join(out)


# ------------------------------------------------------------- 2: scoreboard list


def opt2():
    out = []
    for i, r in enumerate(MODEL["numbers"]):
        h = r["headline"]
        top = ('<div class="nb2-top">%s<h4>%s</h4>%s</div>'
               % (medal(r["key"], 36, not h), e(r["label"]),
                  '<span class="nb2-chev" aria-hidden="true"></span>' if h else ""))
        if not h:
            out.append('<div class="nb2-row is-open">%s<p class="nb2-wait" data-fit>%s</p></div>'
                       % (top, e(r["open"] or "Nobody yet")))
            continue
        main = ('<div class="nb2-main" data-fit>%s<b class="nb2-name">%s</b><span class="nb2-num">'
                '<span class="nb2-v">%s</span>%s</span></div>'
                % (faces(h["leaders"], 32), names(h["leaders"]), e(h["value"]),
                   '<em>%s</em>' % e(h["detail"]) if h["detail"] else ""))
        ranks = "".join(
            '<li class="nb2-li%s" data-fit><span class="nb2-rank">%s</span>%s<span class="nb2-li-name">%s</span>'
            '<span class="nb2-li-v">%s%s</span></li>'
            % (" is-lead" if row["mark"] else "", row["rank"] or "&ndash;", face(row["name"], 24),
               e(row["name"]), e(row["display"] if row["value"] is not None else (row["detail"] or NONE.get(r["key"], "none yet"))),
               '<em>%s</em>' % e(row["detail"]) if row["value"] is not None and row["detail"] else "")
            for row in r["rows"])
        # The first record starts open so the board shows what a tap does.
        out.append('<div class="nb2-row%s%s" role="button" tabindex="0" aria-expanded="%s">%s%s'
                   '<ol class="nb2-all">%s</ol></div>'
                   % (" is-bad" if r["bad"] else "", " is-expanded" if i == 0 else "",
                      "true" if i == 0 else "false", top, main, ranks))
    return (title() + '<div class="nb2">%s</div>' % "".join(out)
            + '<p class="nb2-hint">Tap any record to see all four.</p>')


# ------------------------------------------------------------------ 3: number tiles


def opt3():
    out = []
    for r in MODEL["numbers"]:
        h = r["headline"]
        cls = "nb3-tile" + (" is-bad" if r["bad"] else "") + ("" if h else " is-open")
        hd = '<div class="nb3-hd">%s<h4>%s</h4></div>' % (medal(r["key"], 34, not h), e(r["label"]))
        if not h:
            out.append('<section class="%s">%s<p class="nb3-wait" data-fit>%s</p></section>'
                       % (cls, hd, e(r["open"] or "Nobody yet")))
            continue
        nxt = next_line(r)
        out.append('<section class="%s">%s<p class="nb3-v" data-fit>%s%s</p><p class="nb3-who" data-fit>%s<b>%s</b></p>%s'
                   '</section>'
                   % (cls, hd, e(h["value"]), '<em>%s</em>' % e(h["detail"]) if h["detail"] else "",
                      faces(h["leaders"], 24), names(h["leaders"]),
                      '<p class="nb3-next" data-fit>%s</p>' % nxt if nxt else ""))
    return title() + '<div class="nb3">%s</div>' % "".join(out)


# ------------------------------------------------------------------ 4: ranked ladders


def opt4():
    out = []
    for r in MODEL["numbers"]:
        h = r["headline"]
        hd = '<header class="nb4-hd">%s<h4>%s</h4></header>' % (medal(r["key"], 38, not h), e(r["label"]))
        if not h:
            out.append('<section class="nb4-rec is-open">%s<p class="nb4-wait" data-fit>%s</p></section>'
                       % (hd, e(r["open"] or "Nobody yet")))
            continue
        lead_detail = h["detail"]
        rows = []
        for row in r["rows"]:
            lead = bool(row["mark"])
            if row["value"] is None:
                value = '<b class="is-none">%s</b>' % e(row["detail"] or NONE.get(r["key"], "none yet"))
            else:
                show = row["detail"] and (lead or row["detail"] != lead_detail)
                value = '<b>%s</b>%s' % (e(row["display"]), '<em>%s</em>' % e(row["detail"]) if show else "")
            rows.append('<li class="nb4-row%s" data-fit><span class="nb4-rank">%s</span>%s<span class="nb4-name">%s</span>'
                        '<span class="nb4-val">%s</span></li>'
                        % (" is-lead" if lead else "", row["rank"] or "&ndash;", face(row["name"], 34 if lead else 26),
                           e(row["name"]), value))
        out.append('<section class="nb4-rec%s">%s<ol class="nb4-list">%s</ol></section>'
                   % (" is-bad" if r["bad"] else "", hd, "".join(rows)))
    return title() + '<div class="nb4">%s</div>' % "".join(out)


# ------------------------------------------------------------ 5: team-colour banners


def opt5():
    out = []
    for r in MODEL["numbers"]:
        h = r["headline"]
        tab = '<div class="nb5-tab">%s<h4>%s</h4></div>' % (medal(r["key"], 38, not h), e(r["label"]))
        if not h:
            out.append('<section class="nb5-rec is-open">%s<p class="nb5-wait" data-fit>%s</p></section>'
                       % (tab, e(r["open"] or "Nobody yet")))
            continue
        banners = []
        for p in h["leaders"]:
            bg = "#4a1016" if r["bad"] else team_bg(p["name"])
            banners.append(
                '<div class="nb5-banner" style="--bn:%s;--bi:%s" data-fit>%s<div class="nb5-who"><b>%s</b>%s</div>'
                '<span class="nb5-v">%s</span></div>'
                % (bg, ink_for(bg), face(p["name"], 46), e(p["name"]),
                   '<em>%s</em>' % e(p["detail"]) if p["detail"] else "", e(p["display"])))
        out.append('<section class="nb5-rec%s">%s%s%s</section>'
                   % (" is-bad" if r["bad"] else "", tab, "".join(banners), cells(r, "nb5")))
    return title() + '<div class="nb5">%s</div>' % "".join(out)


# ------------------------------------------------------------------ 6: trophy grid


def opt6():
    out = []
    for r in MODEL["numbers"]:
        h = r["headline"]
        cls = "nb6-tile" + (" is-bad" if r["bad"] else "") + ("" if h else " is-open")
        if not h:
            out.append('<div class="%s">%s<p class="nb6-k">%s</p><p class="nb6-wait" data-fit>%s</p></div>'
                       % (cls, medal(r["key"], 66, True), e(r["label"]), e(r["open"] or "Nobody yet")))
            continue
        nxt = next_line(r)
        out.append('<div class="%s">%s<p class="nb6-k">%s</p><p class="nb6-v" data-fit>%s</p>%s'
                   '<p class="nb6-who" data-fit>%s<b>%s</b></p>%s</div>'
                   % (cls, medal(r["key"], 66), e(r["label"]), e(h["value"]),
                      '<p class="nb6-d">%s</p>' % e(h["detail"]) if h["detail"] else "",
                      faces(h["leaders"], 24), names(h["leaders"]),
                      '<p class="nb6-next" data-fit>%s</p>' % nxt if nxt else ""))
    return ('<section class="nb6"><p class="book-kick">The record book</p><h3 class="nb6-title">'
            'Everyone&rsquo;s numbers</h3><div class="nb6-grid">%s</div></section>' % "".join(out))


# ------------------------------------------------------------------------ the board

OPTIONS = [
    (1, "Title cards", opt1,
     "A card per record. Its name is the heading, the holder and the number are the "
     "biggest line, and everyone else gets a box of their own underneath. Everything shows, "
     "and it is the second longest."),
    (2, "Scoreboard list", opt2,
     "One tight row per record: what it is on top, who holds it and the number underneath. "
     "Tap a row for all four, ranked. About as long as today with the rows closed. Try it: "
     "the rows open."),
    (3, "Number tiles", opt3,
     "Two across. Each tile names the record, then the number huge, who holds it, and who "
     "is next. About as long as today."),
    (4, "Ranked ladders", opt4,
     "Every record ranks all four of you, first to last, with the leader's row the biggest. "
     "Nothing to decode, and the longest."),
    (5, "Team banners", opt5,
     "The loud one. The holder gets a banner in their school's colour with their name and "
     "number big across it, like a TV graphic. A bad-news record gets a red banner."),
    (6, "Trophy grid", opt6,
     "Built like the Hall of fame you liked: big badge, the record's name, the number, who "
     "holds it and who is next, two across on the same dark stage. The names are capitals, "
     "like the Hall of fame's."),
]


def phone(inner):
    return ('<div class="pk-phone"><div class="app" data-mode="book"><main class="app__body">'
            '<div class="app__page">%s</div></main></div></div>' % inner)


def eastern(iso):
    t = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    try:
        from zoneinfo import ZoneInfo
        t = t.astimezone(ZoneInfo("America/New_York"))
    except Exception:
        t = t.astimezone(timezone(timedelta(hours=-4)))
    return t.strftime("%A %I:%M %p").replace(" 0", " ").replace("AM", "am").replace("PM", "pm")


def body():
    cards = "".join(
        '<article class="pb-opt" data-part="numbers" data-n="%d" id="opt-%d"><div class="pb-opt__hd">'
        '<span class="pb-num">%d</span><div class="pb-opt__names"><h3 class="pb-opt__name">%s</h3></div></div>'
        '<p class="pb-opt__what">%s</p><p class="pb-facts" data-facts>measuring&hellip;</p>'
        '<button type="button" class="pb-pick" aria-pressed="false">Pick %d</button>%s</article>'
        % (n, n, n, e(name), e(what), n, phone(fn())) for n, name, fn, what in OPTIONS)
    return """
<header class="pb-top"><div class="pb-wrap">
  <p class="pb-kick">Motley Pick'em &middot; Season tab &middot; Everyone's numbers</p>
  <h1>Everyone's numbers, six ways</h1>
  <p class="pb-lede">You said it is hard to tell what each record actually is. In all six the
    <b>record's name is a real heading</b>, big and plain, and the <b>holder's name and the
    number stay the boldest things</b> on it. Your badges, the real numbers, nothing that
    swipes sideways. Tap <b>Pick</b> under the one you want, or just send me the number.</p>
  <p class="pb-asof">Numbers as of %(asof)s, straight from the app's own record book code.</p>
</div></header>

<main class="pb-wrap">
  <section class="pb-part nb-now" id="now">
    <header class="pb-part__hd"><div>
      <p class="pb-part__range">For comparison</p><h2>What is live now</h2>
      <p class="pb-part__about">The problem, measured: the record's name is 13px capitals with
        wide spacing, the smallest thing on the row, sitting over a 21px name and a 25px
        number. And everyone else runs together in one sentence that wraps in the middle of a
        name.</p></div></header>
    <div class="pb-grid"><article class="pb-opt"><p class="pb-facts" data-facts>measuring&hellip;</p>%(now)s</article></div>
  </section>

  <section class="pb-part" id="part-numbers">
    <header class="pb-part__hd"><div>
      <p class="pb-part__range">Pick one: 1 to 6</p><h2>Six ways to read it</h2>
      <p class="pb-part__about">Every one fits a 375px phone with nothing under 13px, measured
        under each phone.</p></div>
      <p class="pb-take"><b>My pick:</b> 3. Every tile reads top to bottom as "what, how many,
        who", with the number the first thing you see, at about the same length as today and
        nothing behind a tap. If you want all four numbers on show for every record, 1.</p></header>
    <div class="pb-grid">%(cards)s</div>
  </section>

  <section class="pb-part" id="part-note">
    <header class="pb-part__hd"><div><p class="pb-part__range">Optional</p>
      <h2>Anything to change about the one you pick?</h2></div></header>
    <textarea id="pb-note" rows="3" placeholder="For example: 1, but put the badge on the right."></textarea>
  </section>
</main>

<div class="pb-bar" role="status" aria-live="polite"><div class="pb-bar__in">
  <span class="pb-bar__k">Your pick</span>
  <a class="pb-slot" href="#part-numbers">Everyone's numbers <b data-bar="numbers">&ndash;</b></a>
  <span class="pb-save" data-save></span>
</div></div>
<pre id="pb-measure" hidden></pre>
""" % {"asof": e(eastern(MODEL["pulled_at"])), "now": phone(now()), "cards": cards}


def build(standalone):
    css = "".join(open(os.path.join(ROOT, "src", f), encoding="utf-8").read() for f in ("theme.css", "app.css"))
    chrome = open(os.path.join(ROOT, "scripts", "pickbook_board.css"), encoding="utf-8").read()
    mine = open(os.path.join(ROOT, "scripts", "numbers_board.css"), encoding="utf-8").read()
    js = open(os.path.join(ROOT, "scripts", "numbers_board.js"), encoding="utf-8").read()
    logos = ":root{%s}" % "".join("--lg-%s:url(%s);" % (t, rb.logo(t)) for t in rb.TEAM.values())
    keys = sorted({r["key"] for r in MODEL["numbers"]})
    badges = ":root{%s}" % "".join(
        "--bd-%s:url(data:image/webp;base64,%s);" % (k, base64.b64encode(open(os.path.join(ART, k + ".webp"), "rb").read()).decode())
        for k in keys)
    doc = ('<!doctype html>\n<html lang="en">\n<meta charset="utf-8">\n'
           '<meta name="viewport" content="width=device-width,initial-scale=1">\n' if standalone else "")
    return (doc + "<title>Everyone's Numbers Picks</title>\n"
            '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '<link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..800'
            '&family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">\n'
            "<style>%s\n%s\n%s\n%s\n%s</style>\n%s<script>%s</script>\n"
            % (logos, badges, css, chrome, mine, body(), js))


if __name__ == "__main__":
    for path, standalone in ((OUT, True), (OUT.replace(".html", ".artifact.html"), False)):
        page = build(standalone)
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(page)
        print("wrote %s  (%.0f KB)" % (path, len(page.encode()) / 1024))
