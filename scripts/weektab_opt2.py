"""Option 2, winner's colors: the athletic department's FINAL graphic, in the school colors
of whoever won the week. Week 1 is Grant's, so it is Arkansas."""
from __future__ import annotations

from weektab_common import (BY_NAME, MODEL, ME, PLAYERS, TEAMS, e, face, header, join_names, line,
                            mark, phone, tabbar)
from weektab_opt1 import chev

LEAD = [p for p in PLAYERS if p["rank"] == 1]


def _rgb(h):
    return [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]


def _sat(h):
    r, g, b = _rgb(h)
    mx, mn = max(r, g, b), min(r, g, b)
    light = (mx + mn) / 2
    return 0 if mx == mn else (mx - mn) / (1 - abs(2 * light - 1))


def _lum(h):
    lin = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in _rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def field_for(team_id):
    """The louder of a school's two colours, and the ink that reads on it. Arkansas is the
    cardinal, Tulane the green, Kennesaw State the gold, Georgia the red."""
    t = TEAMS[team_id]
    colour = max((t["bg"], t["alt"]), key=_sat)
    return colour, ("#111111" if _lum(colour) > 0.36 else "#ffffff")


FIELD, INK = field_for(LEAD[0]["team_id"])
SWATCHES = [(p["name"],) + field_for(p["team_id"]) for p in sorted(PLAYERS, key=lambda p: p["id"])]


def chips(stakes):
    return "".join(
        '<span class="wc-chip%s">%s<b>%d</b></span>' % ("" if s["won"] else " is-lost", face(s["name"], 24), s["confidence"])
        for s in stakes)


def plate(g):
    halves = []
    for s in (g["away"], g["home"]):
        won = s["abbr"] == g["winner"]
        halves.append('<span class="wc-half%s">%s<b>%s</b><strong>%d</strong></span>'
                      % ("" if won else " is-loser", mark(s["id"], 40), e(s["abbr"]), s["score"]))
    return '<div class="wc-plate">%s<span class="wc-plate__final">Final</span>%s</div>' % (halves[0], halves[1])


def stakes_line(stakes):
    groups = {}
    for s in stakes:
        groups.setdefault((not s["won"], s["pick"]), []).append(s)
    return "".join('<div class="wc-stake"><span>Had %s</span>%s</div>' % (e(pick), chips(rows))
                   for (_l, pick), rows in sorted(groups.items()))


def hero():
    p = LEAD[0]
    runner = next(x for x in PLAYERS if x["rank"] != 1)
    return ('<section class="wc-hero">'
            '<i class="wc-hero__mark" style="background-image:var(--lg-%s)" aria-hidden="true"></i>'
            '<div class="wc-pager"><span class="wc-arrow">%s</span><span class="wc-pager__mid">Week 1 %s</span>'
            '<span class="wc-arrow">%s</span></div>'
            '<p class="wc-back">Back to this week</p>'
            '<p class="wc-kick"><span>Week 1</span><span class="wc-kick__final">Final</span></p>'
            '<h2 class="wc-name">%s</h2><p class="wc-wins">wins the week</p>'
            '<p class="wc-score"><strong>%d</strong><span>by %d over %s</span></p></section>'
            % (p["team_id"], chev("left"), chev("down", 15), chev("right"),
               e(p["name"]), p["points"], MODEL["margin"], e(runner["name"])))


def standings():
    rows = "".join(
        '<div class="wc-row%s" style="--wc-slab:%s"><span class="wc-rank">%d</span>%s'
        '<span class="wc-who"><b>%s</b><span>%d-%d%s</span></span><strong>%d</strong></div>'
        % (" is-lead" if p["rank"] == 1 else "", TEAMS[p["team_id"]]["alt"], p["rank"], face(p["name"], 34),
           e(p["name"]), p["correct"], p["wrong"], " &middot; you" if p["name"] == ME else "", p["points"])
        for p in PLAYERS)
    return '<section class="wc-sec wc-sec--table"><div class="wc-table">%s</div></section>' % rows


def decided():
    out = []
    for d in MODEL["decisive"]:
        if d["shared"]:
            big = "%s tie on %d" % (join_names(d["leaders"]), d["points"])
        else:
            big = "%s takes it, %d&ndash;%d" % (d["leaders"][0], d["points"], d["next"]["points"])
        out.append('<article class="wc-game">%s<p class="wc-if">If %s wins</p><p class="wc-then">%s</p>%s</article>'
                   % (plate(d), e(d["instead"]), big, stakes_line(d["stakes"])))
    return '<section class="wc-sec"><h3 class="wc-title">Decided it</h3>%s</section>' % "".join(out)


def upsets():
    out = []
    for u in MODEL["upsets"]:
        called = ('<div class="wc-stake"><span>Had %s</span>%s</div>' % (e(u["winner"]), chips(u["called"]))
                  if u["called"] else '<p class="wc-nobody">Nobody had %s</p>' % e(u["winner"]))
        win = u["away"] if u["away"]["abbr"] == u["winner"] else u["home"]
        lose = u["home"] if win is u["away"] else u["away"]
        out.append('<article class="wc-upset">%s<div class="wc-upset__txt"><p class="wc-upset__hd"><b>%s</b>'
                   '<span class="wc-line">+%s</span></p><p class="wc-upset__sub">beat %s %d&ndash;%d</p>%s</div></article>'
                   % (mark(win["id"], 54), e(win["abbr"]), line(u["line"]), e(lose["abbr"]), win["score"],
                      lose["score"], called))
    return '<section class="wc-sec"><h3 class="wc-title">Upsets</h3>%s</section>' % "".join(out)


def left():
    rows = "".join(
        '<div class="wc-lrow%s"><span class="wc-rank">%d</span>%s<span class="wc-who"><b>%s</b>'
        '<span>%d of a possible %d</span></span><strong>%d</strong></div>'
        % (" is-lead" if p["rank"] == 1 else "", p["rank"], face(p["name"], 34), e(p["name"]), p["points"],
           p["ceiling"], p["left"])
        for p in MODEL["left"])
    return ('<section class="wc-sec"><h3 class="wc-title">Left on the table</h3>'
            '<p class="wc-help">What your right picks were worth, against ranking them perfectly.</p>'
            '<div class="wc-table">%s</div></section>' % rows)


def numbers():
    n = MODEL["numbers"]
    items = [
        (n["chalk"]["won"], "Favorites won", "of %d games" % n["chalk"]["of"]),
        (n["upsets"], "Upsets", "%s called %s" % (join_names(n["calledBy"]), join_names(u["winner"] for u in MODEL["upsets"] if u["called"]))),
        (len(n["sweeps"]), "All four got it right", ", ".join(n["sweeps"])),
        (len(n["whiffs"]), "Nobody got it right", ", ".join(n["whiffs"])),
    ]
    rows = "".join('<div class="wc-nrow"><strong>%d</strong><span class="wc-who"><b>%s</b><span>%s</span></span></div>'
                   % (v, e(k), e(s)) for v, k, s in items)
    return '<section class="wc-sec"><h3 class="wc-title">By the numbers</h3>%s</section>' % rows


def build():
    body = hero() + standings() + decided() + upsets() + left() + numbers()
    return phone("wc", header("wc-hdr") + body + tabbar("wc-tabs")).replace(
        'class="wt-phone wc"', 'class="wt-phone wc" style="--wc-field:%s;--wc-ink:%s"' % (FIELD, INK), 1)
