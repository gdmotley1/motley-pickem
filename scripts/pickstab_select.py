"""Direction 2: Select screen. The college football video game's team-select menus."""
from __future__ import annotations

from pickstab_kit import (CARD, CHECK, FAVORITES, LIFTED, PICKED_MIDWEEK, RANKED, UNDERDOGS, days, e, header, mark, more,
                          rank_badge, state, tabbar)
from pickstab_kit import me
from pickstab_kit import winners as drawn

NAME = "Select screen"
PITCH = ("The team-select screen from a college football video game. Every game is a head-to-head with big logos lit in "
         "each school&rsquo;s colors and a VS badge between them; the team you take gets the volt frame and the "
         "Selected ribbon. Points become your depth chart, and locking in is the save screen.")
BUILT = "Saira, a variable width face set condensed and italic like a game menu, with Inter underneath. Angled panels, one volt accent."


def side(c, s):
    t = c[s]
    st = state(c, s)
    return ('<button class="ss-side %s" style="--c:%s;--c2:%s" aria-pressed="%s">%s%s<span class="ss-school">%s</span>'
            '<span class="ss-sel" aria-hidden="true">%sSelected</span></button>'
            % (st, t["deep"], t["loud"], "true" if st == "is-picked" else "false", rank_badge(t, "ss-rank"),
               mark(t["id"], 62), e(t["school"]), CHECK % (13, 13)))


def game(c):
    return ('<article class="ss-game" data-m="game"><div class="ss-meta"><span class="ss-when">%s</span><span class="ss-tv">%s</span>'
            '<span class="ss-line">%s</span><button class="ss-cta" aria-label="Matchup preview: %s"><span class="ss-shine" aria-hidden="true"></span>Matchup</button></div>'
            '<div class="ss-vs">%s<span class="ss-versus" aria-hidden="true"><b>%s</b></span>%s</div></article>'
            % (e(c["when"]), e(c["tv"]), e(c["spread"]), e(c["key"]), side(c, "away"), "VS" if c["neutral"] else "AT", side(c, "home")))


def winners():
    segs = "".join('<i class="%s"></i>' % ("on" if i < PICKED_MIDWEEK else "") for i in range(len(CARD)))
    groups = "".join('<h3 class="ss-day"><span>%s</span></h3>%s' % (d, "".join(game(c) for c in rows)) for d, rows in days(drawn()))
    return ('<div class="ss">%s<div class="ss-mode"><h2>Select<br>winners</h2><p class="ss-count"><b>%d</b><span>/20</span></p></div>'
            '<div class="ss-segs" aria-hidden="true">%s</div>%s%s'
            '<div class="ss-go-wrap"><button class="ss-go" disabled>%d still to pick</button></div>%s</div>'
            % (header("ss"), PICKED_MIDWEEK, segs, groups, more("ss"), len(CARD) - PICKED_MIDWEEK, tabbar("ss")))


def points():
    rows = []
    for c in RANKED:
        lifted = c["key"] == LIFTED
        rows.append('<li class="ss-row%s" data-m="rank" style="--c:%s;--c2:%s"><button class="ss-row__hit"><span class="ss-pts">%d</span>%s'
                    '<span class="ss-who"><b>%s</b><span>over %s &middot; %s</span></span><span class="ss-cue">%s</span></button></li>'
                    % (" is-lifted" if lifted else "", c["pick"]["deep"], c["pick"]["loud"], c["pts"], mark(c["pick"]["id"], 34),
                       e(c["pick"]["school"]), e(c["opp"]["abbr"]), e(c["spread"]), "Swap" if lifted else "Here"))
    lifted = next(c for c in CARD if c["key"] == LIFTED)
    return ('<div class="ss">%s<div class="ss-rankhead"><button class="ss-chip">&lsaquo; Winners</button><button class="ss-chip">Reset to spread</button></div>'
            '<div class="ss-intro"><h2>Depth chart</h2><p>Sorted by the spread when you got here: the top spot is worth <b>20</b>, '
            'the bottom <b>1</b>. Tap a team, then tap the spot it should take.</p></div>'
            '<ol class="ss-ranks">%s</ol>'
            '<div class="ss-lift"><span>Moving <b>%s</b>. Tap a spot to give it those points.</span><button class="ss-cancel">Cancel</button></div>%s</div>'
            % (header("ss"), "".join(rows), e(lifted["pick"]["school"]), tabbar("ss")))


def locked():
    top = RANKED[0]
    tiles = [(FAVORITES, "Favorites"), (UNDERDOGS, "Underdogs"), (20, "On %s" % top["pick"]["abbr"])]
    rows = "".join('<li class="ss-sealed" style="--c:%s"><span class="ss-pts ss-pts--sm">%d</span>%s<span class="ss-who"><b>%s</b>'
                   '<span>over %s</span></span><span class="ss-kick">%s</span></li>'
                   % (c["pick"]["loud"], c["pts"], mark(c["pick"]["id"], 28), e(c["pick"]["abbr"]), e(c["opp"]["abbr"]), e(c["when"]))
                   for c in RANKED)
    return ('<div class="ss">%s<section class="ss-save" style="--c:%s;--c2:%s">'
            '<i class="ss-save__mark" style="background-image:var(--lgd-%s)" aria-hidden="true"></i>'
            '<p class="ss-save__kick">%s Grant &middot; Week 1</p><h2 class="ss-save__h">Locked<br>in</h2>'
            '<p class="ss-save__sub">Card saved. Change any game right up until it kicks off.</p>'
            '<div class="ss-tiles">%s</div>'
            '<div class="ss-actions"><button class="ss-btn ss-btn--volt">See the Board</button><button class="ss-btn">Change picks</button></div></section>'
            '<h3 class="ss-day ss-day--list"><span>Your depth chart</span></h3><ol class="ss-sealeds">%s</ol>%s</div>'
            % (header("ss"), top["pick"]["deep"], top["pick"]["loud"], top["pick"]["id"], me(26),
               "".join('<span class="ss-tile"><b>%d</b><span>%s</span></span>' % (n, e(l)) for n, l in tiles), rows, tabbar("ss")))
