"""Direction 5: Broadcast. The Saturday studio show's graphics package."""
from __future__ import annotations

from pickstab_kit import (CARD, CHECK, FAVORITES, LIFTED, PICKED_MIDWEEK, RANKED, UNDERDOGS, days, e, mark, me, more, rank_badge,
                          state, tabbar)
from pickstab_kit import winners as drawn

NAME = "Broadcast"
PITCH = ("The Saturday morning studio show. Glossy chrome and royal blue bars, logos that pop out of their plates, a red "
         "breaking-news tag. Every game is the matchup graphic the desk throws to before a pick, your points are a "
         "top-25 style poll, and locking in breaks into the show with your card and a ticker.")
BUILT = "Anton for the headlines and Barlow Condensed for the lower thirds, both new, over Inter. Chrome, royal blue, one red, one gold."

STAR = '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path d="m12 2.6 2.8 6 6.5.7-4.9 4.4 1.4 6.5L12 16.9l-5.8 3.3 1.4-6.5L2.7 9.3l6.5-.7Z" fill="currentColor"/></svg>'


def hdr():
    return ('<header class="bc-hdr"><span class="bc-hdr__title">Motley Pick&rsquo;em</span><span class="bc-hdr__week">Week 1</span>'
            '<span class="bc-hdr__me">%s<span>Grant</span></span></header>' % me(24))


def plate(c, s):
    t = c[s]
    st = state(c, s)
    return ('<button class="bc-plate %s" style="--c:%s;--c2:%s" aria-pressed="%s"><span class="bc-plate__logo">%s</span>%s'
            '<span class="bc-plate__name">%s</span><span class="bc-plate__pick" aria-hidden="true">%sPick</span></button>'
            % (st, t["loud"], t["deep"], "true" if st == "is-picked" else "false", mark(t["id"], 58), rank_badge(t, "bc-rank"),
               e(t["school"]), STAR))


def game(c):
    return ('<article class="bc-game" data-m="game"><div class="bc-strip"><span class="bc-when">%s</span><span class="bc-net">%s</span>'
            '<span class="bc-line">%s</span><button class="bc-cta" aria-label="Matchup preview: %s"><span class="bc-shine" aria-hidden="true"></span>Matchup &#9656;</button></div>'
            '<div class="bc-plates">%s<span class="bc-at" aria-hidden="true">%s</span>%s</div></article>'
            % (e(c["when"]), e(c["tv"]), e(c["spread"]), e(c["key"]), plate(c, "away"), "vs" if c["neutral"] else "at", plate(c, "home")))


def winners():
    segs = "".join('<i class="%s"></i>' % ("on" if i < PICKED_MIDWEEK else "") for i in range(len(CARD)))
    groups = "".join('<h3 class="bc-day"><span>%s</span></h3>%s' % (d, "".join(game(c) for c in rows)) for d, rows in days(drawn()))
    return ('<div class="bc">%s<div class="bc-l3"><div class="bc-l3__bar"><span class="bc-l3__tag">Your picks</span><span class="bc-l3__who">%s Grant</span>'
            '<span class="bc-l3__num"><b>%d</b>/20</span></div><div class="bc-segs" aria-hidden="true">%s</div></div>'
            '%s%s<div class="bc-go-wrap"><button class="bc-go" disabled>%d still to pick</button></div>%s</div>'
            % (hdr(), me(26), PICKED_MIDWEEK, segs, groups, more("bc"), len(CARD) - PICKED_MIDWEEK, tabbar("bc")))


def points():
    rows = []
    for c in RANKED:
        p = c["pick"]
        lifted = c["key"] == LIFTED
        rows.append('<li class="bc-row%s" data-m="rank" style="--c:%s"><button class="bc-row__hit"><span class="bc-pts">%d</span>'
                    '<span class="bc-row__logo">%s</span><span class="bc-who"><b>%s</b><span>over %s &middot; %s</span></span>'
                    '<span class="bc-cue">%s</span></button></li>'
                    % (" is-lifted" if lifted else "", p["loud"], c["pts"], mark(p["id"], 36, "lg"), e(p["school"]), e(c["opp"]["abbr"]),
                       e(c["spread"]), "On the move" if lifted else "Here"))
    lifted = next(c for c in CARD if c["key"] == LIFTED)
    return ('<div class="bc">%s<div class="bc-rankhead"><button class="bc-chip">&lsaquo; Winners</button><button class="bc-chip">Reset to spread</button></div>'
            '<div class="bc-title"><p class="bc-title__tag">Week 1</p><h2>Grant&rsquo;s<br>confidence poll</h2>'
            '<p class="bc-title__sub">Seeded by the spread: number one is worth <b>20</b>, the last spot <b>1</b>. Tap a team, then tap its new spot.</p></div>'
            '<ol class="bc-ranks">%s</ol>'
            '<div class="bc-lift"><span class="bc-lift__tag">Moving</span><span class="bc-lift__text"><span><b>%s</b>. Tap a row to give it those points.</span></span>'
            '<button class="bc-cancel">Cancel</button></div>%s</div>'
            % (hdr(), "".join(rows), e(lifted["pick"]["school"]), tabbar("bc")))


def locked():
    podium = "".join('<li class="bc-pod bc-pod--%d" style="--c:%s;--c2:%s"><span class="bc-pod__pts">%d</span><span class="bc-pod__logo">%s</span>'
                     '<span class="bc-pod__who"><b>%s</b><span>over %s</span></span></li>'
                     % (i + 1, c["pick"]["loud"], c["pick"]["deep"], c["pts"], mark(c["pick"]["id"], 52), e(c["pick"]["school"]), e(c["opp"]["abbr"]))
                     for i, c in enumerate(RANKED[:3]))
    rest = "".join('<li class="bc-sealed"><span class="bc-pts bc-pts--sm">%d</span><span class="bc-row__logo">%s</span>'
                   '<span class="bc-who"><b>%s</b><span>over %s &middot; %s</span></span></li>'
                   % (c["pts"], mark(c["pick"]["id"], 28, "lg"), e(c["pick"]["school"]), e(c["opp"]["abbr"]), e(c["when"])) for c in RANKED[3:])
    ticker = " &nbsp;&#9679;&nbsp; ".join(["Grant is locked in for Week 1", "%d favorites, %d underdogs" % (FAVORITES, UNDERDOGS),
                                          "Biggest bet: 20 on %s" % e(RANKED[0]["pick"]["school"]), "Picks can change until each kickoff"])
    return ('<div class="bc">%s<section class="bc-break"><p class="bc-break__tag"><span>Breaking</span>Picks desk</p>'
            '<div class="bc-break__card"><span class="bc-break__me">%s</span><div><p class="bc-break__kick">Grant&rsquo;s card</p>'
            '<h2>Locked in</h2></div></div><p class="bc-break__sub">Saved. Change any game right up until it kicks off.</p>'
            '<div class="bc-actions"><button class="bc-btn bc-btn--red">See the Board</button><button class="bc-btn">Change something</button></div></section>'
            '<h3 class="bc-day"><span>Top three</span></h3><ol class="bc-podium">%s</ol>'
            '<h3 class="bc-day"><span>The rest of the card</span></h3><ol class="bc-rest">%s</ol>'
            '<div class="bc-crawl"><span class="bc-crawl__k">Picks</span><div class="bc-crawl__win"><div class="bc-crawl__run"><span>%s</span>'
            '<span aria-hidden="true">%s</span></div></div></div>%s</div>'
            % (hdr(), me(64), podium, rest, ticker, ticker, tabbar("bc")))
