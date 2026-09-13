"""Direction 1: Jumbotron. The Board's LED wall, so Picks and Board are one stadium."""
from __future__ import annotations

from pickstab_kit import (CARD, CHECK, FAVORITES, LIFTED, LOCK, PICKED_MIDWEEK, RANKED, UNDERDOGS, days, e, header, mark,
                          more, rank_badge, state, tabbar)
from pickstab_kit import winners as drawn

NAME = "Jumbotron"
PITCH = ("The Board&rsquo;s video wall carried onto Picks, so the two tabs are one stadium. Every team is a lit panel in its "
         "school&rsquo;s colors; tap one and it lights gold while the other side goes dark. Points are LED numbers on the "
         "same leaderboard rows the Board uses, and locking in gets the marquee and a crawl.")
BUILT = ("The shipped Board skin: Big Shoulders Display lettering, the LED dot mask on every big number, the amber tab bar. "
         "No new fonts.")


def led(text, cls=""):
    return '<span class="jt-led %s"><span>%s</span></span>' % (cls, e(str(text)))


def team(c, side):
    s = c[side]
    st = state(c, side)
    lamp = ('<span class="jt-lamp">%sPick</span>' % (CHECK % (15, 15))) if st == "is-picked" else '<span class="jt-ring" aria-hidden="true"></span>'
    return ('<button class="jt-team %s" style="--t:%s" aria-pressed="%s">%s<span class="jt-name">%s<span>%s</span></span>%s</button>'
            % (st, s["deep"], "true" if st == "is-picked" else "false", mark(s["id"], 36), rank_badge(s, "jt-rank"), e(s["school"]), lamp))


def game(c):
    return ('<article class="jt-game%s" data-m="game"><div class="jt-meta"><span class="jt-when">%s</span>'
            '<span class="jt-tv">%s</span><span class="jt-line">%s</span>'
            '<button class="jt-cta" aria-label="Matchup preview: %s"><span class="jt-shine" aria-hidden="true"></span>Matchup<b aria-hidden="true">&rsaquo;</b></button></div>'
            '%s%s</article>'
            % (" is-done" if c["chosen"] else "", e(c["when"]), e(c["tv"]), e(c["spread"]), e(c["key"]), team(c, "away"), team(c, "home")))


def winners_meter():
    return "".join('<i class="%s"></i>' % ("on" if i < PICKED_MIDWEEK else "") for i in range(len(CARD)))


def winners():
    groups = "".join('<h3 class="jt-day"><span>%s</span></h3>%s' % (d, "".join(game(c) for c in rows)) for d, rows in days(drawn()))
    return ('<div class="jt">%s<div class="jt-top"><div class="jt-count">%s<span>of 20<br>picked</span></div>'
            '<div class="jt-meter" aria-hidden="true">%s</div></div>'
            '<div class="jt-wall">%s%s</div>'
            '<div class="jt-go-wrap"><button class="jt-go" disabled>%d still to pick</button></div>%s</div>'
            % (header("jt"), led(PICKED_MIDWEEK, "jt-led--gold jt-big"), winners_meter(), groups, more("jt"),
               len(CARD) - PICKED_MIDWEEK, tabbar("jt")))


def points():
    rows = []
    for c in RANKED:
        lifted = c["key"] == LIFTED
        cue = '<span class="jt-cue is-moving">Moving</span>' if lifted else '<span class="jt-cue">Here</span>'
        rows.append('<li class="jt-row%s" data-m="rank" style="--t:%s"><button class="jt-row__hit">%s%s'
                    '<span class="jt-who"><b>%s</b><span>over %s &middot; %s</span></span>%s</button></li>'
                    % (" is-lifted" if lifted else " is-target", c["pick"]["deep"], led(c["pts"], "jt-pts"), mark(c["pick"]["id"], 30),
                       e(c["pick"]["abbr"]), e(c["opp"]["abbr"]), e(c["spread"]), cue))
    lifted = next(c for c in CARD if c["key"] == LIFTED)
    return ('<div class="jt jt--rank">%s<div class="jt-rankhead"><button class="jt-chip">&lsaquo; Winners</button>'
            '<button class="jt-chip">Reset to spread</button></div>'
            '<div class="jt-intro"><h2>Most sure at the top</h2><p>Already sorted by the spread, so the top game is worth '
            '<b>20</b> and the bottom <b>1</b>. Tap a game to move it.</p></div>'
            '<div class="jt-wall"><ol class="jt-ranks">%s</ol></div>'
            '<div class="jt-lift"><span>Moving <b>%s</b>. Tap a row to give it those points.</span><button class="jt-cancel">Cancel</button></div>%s</div>'
            % (header("jt"), "".join(rows), e(lifted["pick"]["school"]), tabbar("jt")))


def locked():
    rows = "".join('<li class="jt-sealed" style="--t:%s">%s%s<span class="jt-who"><b>%s</b><span>over %s</span></span>'
                   '<span class="jt-kick">%s</span></li>'
                   % (c["pick"]["deep"], led(c["pts"], "jt-pts jt-pts--sm"), mark(c["pick"]["id"], 26), e(c["pick"]["abbr"]),
                      e(c["opp"]["abbr"]), e(c["when"])) for c in RANKED)
    top = RANKED[0]
    crawl = " &nbsp;&#9670;&nbsp; ".join([
        "Grant is locked in", "%d favorites" % FAVORITES, "%d underdogs" % UNDERDOGS,
        "20 on %s" % e(top["pick"]["abbr"]), "Changes allowed until each kickoff"])
    return ('<div class="jt jt--done">%s<section class="jt-marquee"><div class="jt-bulbs" aria-hidden="true"></div>'
            '<div class="jt-marquee__in"><span class="jt-lock">%s</span>'
            '<h2 class="jt-headline"><span class="jt-led jt-led--gold"><span>Picks</span></span> <span class="jt-led jt-led--gold"><span>are in</span></span></h2>'
            '<p>Saved. Change any game right up until it kicks off.</p>'
            '<div class="jt-actions"><button class="jt-btn jt-btn--gold">See the big board</button><button class="jt-btn">Change something</button></div></div></section>'
            '<div class="jt-wall"><h3 class="jt-day"><span>Your card</span></h3><ol class="jt-sealeds">%s</ol></div>'
            '<div class="jt-crawl"><span class="jt-crawl__k">Locked</span><div class="jt-crawl__win"><div class="jt-crawl__run">'
            '<span>%s</span><span aria-hidden="true">%s</span></div></div></div>%s</div>'
            % (header("jt"), LOCK % (44, 44), rows, crawl, crawl, tabbar("jt")))
