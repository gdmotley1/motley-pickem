"""Option 5, the stat sheet: the week as the official printout from the press box. Green-bar
tractor-feed paper, a two-color ribbon (black for points won, red for wagers lost), and a
rubber FINAL stamp. Everything sits on one 24px line, so the green bands stay true."""
from __future__ import annotations

from weektab_common import MODEL, ME, PLAYERS, e, header, join_names, line, phone, tabbar


def wagers(stakes):
    return "&nbsp; ".join('<span class="%s">%s&nbsp;%d</span>' % ("" if s["won"] else "ss-red", e(s["name"].upper()), s["confidence"])
                          for s in stakes)


def stake_lines(stakes):
    groups = {}
    for s in stakes:
        groups.setdefault((not s["won"], s["pick"]), []).append(s)
    return "".join('<p class="ss-in">Had %s: %s</p>' % (e(pick), wagers(rows)) for (_l, pick), rows in sorted(groups.items()))


def score(g):
    a, h = g["away"], g["home"]
    return '%s %d &nbsp;at&nbsp; %s %d' % (e(a["abbr"]), a["score"], e(h["abbr"]), h["score"])


def rule(title):
    return '<h3 class="ss-rule"><span>%s</span><i></i></h3>' % title


def standings():
    rows = "".join(
        '<div class="ss-t ss-t--std"><span>%d</span><b>%s%s</b><span>%d-%d</span><b>%d</b><span>%s</span></div>'
        % (p["rank"], e(p["name"].upper()), " *" if p["name"] == ME else "", p["correct"], p["wrong"], p["points"],
           "--" if p["behind"] == 0 else "-%d" % p["behind"])
        for p in PLAYERS)
    return (rule("Final standings") +
            '<div class="ss-t ss-t--std ss-t--hd"><span>Pos</span><span>Player</span><span>W-L</span><span>Pts</span><span>Back</span></div>'
            + rows + '<p class="ss-foot">* You</p>')


def decided():
    out = [rule("Decided it")]
    for i, d in enumerate(MODEL["decisive"]):
        if d["shared"]:
            what = 'If %s had won, %s tie on %d.' % (e(d["instead"]), e(join_names(n.upper() for n in d["leaders"])), d["points"])
        else:
            what = 'If %s had won, %s takes the week, %d to %d.' % (e(d["instead"]), e(d["leaders"][0].upper()), d["points"], d["next"]["points"])
        out.append('<div class="ss-block"><p class="ss-b">%s</p><p class="ss-in">%s</p>%s</div>' % (score(d), what, stake_lines(d["stakes"])))
    return "".join(out)


def upsets():
    out = [rule("Upsets")]
    for u in MODEL["upsets"]:
        who = ('<p class="ss-in">Had %s: %s</p>' % (e(u["winner"]), wagers(u["called"])) if u["called"]
               else '<p class="ss-in">Nobody had %s.</p>' % e(u["winner"]))
        out.append('<div class="ss-block"><p class="ss-b ss-split"><span>%s</span><span>+%s</span></p>%s</div>'
                   % (score(u), line(u["line"]), who))
    return "".join(out)


def left():
    rows = "".join('<div class="ss-t ss-t--left"><b>%s</b><span>%d</span><span>%d</span><b>%d</b></div>'
                   % (e(p["name"].upper()), p["points"], p["ceiling"], p["left"]) for p in MODEL["left"])
    return (rule("Points left on the table") +
            '<p class="ss-note">Your right picks, ranked perfectly, against what you got.</p>'
            '<div class="ss-t ss-t--left ss-t--hd"><span>Player</span><span>Got</span><span>Of</span><span>Left</span></div>' + rows)


def numbers():
    n = MODEL["numbers"]
    called = "%s called %s" % (join_names(x.upper() for x in n["calledBy"]), join_names(u["winner"] for u in MODEL["upsets"] if u["called"]))
    items = [
        ("Favorites won", "%d of %d" % (n["chalk"]["won"], n["chalk"]["of"]), ""),
        ("Upsets", str(n["upsets"]), called),
        ("All four right", str(len(n["sweeps"])), " ".join(n["sweeps"])),
        ("Nobody right", str(len(n["whiffs"])), " ".join(n["whiffs"])),
    ]
    rows = "".join('<p class="ss-lead"><span>%s</span><i></i><b>%s</b></p>%s'
                   % (e(k), e(v), '<p class="ss-in">%s</p>' % e(s) if s else "") for k, v, s in items)
    return rule("The week") + rows


def build():
    top = ('<div class="ss-pager"><span class="ss-btn">&lt; Prev</span><span class="ss-mid"><b>Week 1 v</b><span>Final</span></span>'
           '<span class="ss-btn">Next &gt;</span></div><p class="ss-backbtn">Back to this week</p>'
           '<div class="ss-head"><p class="ss-split"><span>Motley Pick&rsquo;em</span><span>Page 1</span></p>'
           '<p>Official week summary</p><p>Week 1 &middot; 2026 &middot; %d games</p>'
           '<span class="ss-stamp" aria-hidden="true">Final</span></div>'
           '<h2 class="ss-headline">%s wins<br>week 1 by %d</h2>'
           % (MODEL["week"]["slate"], e(MODEL["leaders"][0]), MODEL["margin"]))
    sheet = top + standings() + decided() + upsets() + left() + numbers() + '<p class="ss-end">*** End of report ***</p>'
    paper = '<div class="ss-desk"><div class="ss-paper"><i class="ss-feed"></i><div class="ss-sheet">%s</div><i class="ss-feed"></i></div></div>' % sheet
    return phone("ss", header("ss-hdr") + paper + tabbar("ss-tabs"))
