"""Numbered options for the whole record book, and the Season tab assembled from the picks.

Grant, 2026-09-12, opening a new chat after the sideways table was rejected: "I didn't like
some of the designs that you made, and I was unclear as to what you were gonna build. I
need specific examples in a one, a two, etcetera to pick from to tell you exactly what I
want."

So:
  1-6    everyone's numbers, six layouts, none of which scrolls sideways
  7-9    Hall of fame, 7 being the trophy room he picked last time
  10-12  Hall of shame, 10 being the red panel he picked last time

Every number is unique across the board. "Three, seven and ten" survives a voice message;
"numbers four" arrives as "numbers for". Every phone shows its whole section with no inner
scroll, because the last board hid half of each option behind a scroll inside a scroll. The
final phone assembles whatever is picked, in tab order, so what gets built is on screen
rather than described. Picks save to the artifact's db (picks/grant), the way the ballot did.

The numbers are real: pulled read-only from the live database, keeping only picks on games
that already have a winner, the same line get_season_picks draws. Week records use the
finished-week rule the build will ship: a week counts once all 20 games are graded or a later
week has graded games.

    python scripts/build_pickbook_board.py --pull   # refresh the snapshot, then build
    python scripts/build_pickbook_board.py          # rebuild from outputs/pickbook_snapshot.json
"""
from __future__ import annotations

import html
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_recordbook_board as rb  # noqa: E402

ROOT = rb.ROOT
OUT = os.path.join(ROOT, "outputs", "pickbook-board.html")
SNAP = os.path.join(ROOT, "outputs", "pickbook_snapshot.json")
e = html.escape

# ------------------------------------------------------------------------ the records

RECORDS = [
    ("best_week", "Most points in a week", "week"),
    ("best_record", "Best record in a week", "week"),
    ("low_week", "Fewest points in a week", "week"),
    ("streak", "Longest winning streak", "picks"),
    ("worst_miss", "Worst miss", "picks"),
    ("my_upset", "Biggest upset you called", "picks"),
    ("weeks_won", "Weeks won", "season"),
    ("season_record", "Season record", "season"),
]
GROUPS = [("week", "Week by week"), ("picks", "Pick by pick"), ("season", "All season")]
BAD = {"low_week", "worst_miss"}  # holding these is bad news: marked red, not gold
LOWER = {"low_week"}  # the smallest number holds it

# Easiest to hardest, which is also the order the trophy case fills up in.
FAME_ORDER = ["season_points", "margin", "big_upset", "only_one", "three_upsets",
              "two_td_upset", "win_by_20", "perfect_week"]
FAME_LABEL = {bid: rb.BY_ID[bid][2] for bid in FAME_ORDER}
WHAT = {
    "season_points": "Most points in the season",
    "margin": "Win a week by the most",
    "big_upset": "Call the season's biggest upset",
    "only_one": "Be the only one to pick a winner",
    "three_upsets": "Three underdogs right in one week",
    "two_td_upset": "Pick a 14-point underdog that wins",
    "win_by_20": "Win a week by 20 or more",
    "perfect_week": "Every game right in a week",
}

# The colour each of them already wears: the disc behind their logo on every screen.
PC = {name: rb.TEAMS[tid]["bg"] for name, tid in rb.TEAM.items()}

# Grant's ChatGPT art, one file per badge, matched to its prompt by eye on 2026-09-12. See
# inputs/badges/README.md. Every id in rb.BADGES must have one: a stand-in would silently
# put the CSS placeholder back on a board that says the art is real.
BADGE_DIR = os.path.join(ROOT, "inputs", "badges")
BADGE_PX = 320  # the biggest badge on any screen is 104px, so this is 3x for a phone


def badge_uri(bid):
    """Trim to the medallion, square it, 320px WebP with its alpha. The source is 1254px and
    2MB; a stage badge at 3x needs 312px."""
    import base64
    import io
    from PIL import Image

    path = os.path.join(BADGE_DIR, bid + ".png")
    if not os.path.exists(path):
        raise SystemExit("missing badge art: %s" % path)
    im = Image.open(path).convert("RGBA")
    box = im.getchannel("A").point(lambda v: 255 if v > 16 else 0).getbbox()
    im = im.crop(box)
    side = max(im.size)
    sq = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    sq.paste(im, ((side - im.size[0]) // 2, (side - im.size[1]) // 2))
    sq = sq.resize((BADGE_PX, BADGE_PX), Image.LANCZOS)
    buf = io.BytesIO()
    sq.save(buf, "WEBP", quality=90, method=6)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()


def badge(bid, size, open_=False):
    """The real badge. Unclaimed is the same art in grey inside a dashed socket, so you can
    see what is up for grabs rather than an empty hole."""
    return ('<span class="pk-badge%s" style="--size:%dpx" aria-hidden="true">'
            '<i style="background-image:var(--bd-%s)"></i></span>'
            % (" is-open" if open_ else "", size, bid))


# ------------------------------------------------------------------------ the data


def pull():
    """Read-only. SELECTs, nothing else, and never a PIN hash."""
    import sync_supabase as s

    s.load_dotenv(os.path.join(ROOT, ".env"))
    sb = s.Supabase(s.env("SUPABASE_URL"), s.env("SUPABASE_SERVICE_KEY"))
    games = sb.select("games", "select=id,week_id,kickoff,home_abbr,away_abbr,winner_abbr,"
                               "favorite_abbr,underdog_abbr,spread_line&in_slate=eq.true")
    graded = [g["id"] for g in games if g["winner_abbr"]]
    # Only picks on games that already have a winner, the same line get_season_picks draws,
    # so no pick for a game that has not kicked off ever reaches this file.
    picks = []
    for i in range(0, len(graded), 50):
        ids = ",".join(str(x) for x in graded[i:i + 50])
        picks += sb.select("picks", "select=player_id,game_id,week_id,pick_abbr,confidence"
                                    "&game_id=in.(%s)" % ids)
    snap = {
        "pulled_at": datetime.now(timezone.utc).isoformat(),
        "seats": sb.select("players", "select=id,name,team_id&order=id"),
        "weeks": sb.select("weeks", "select=id,week_no,label,published&order=week_no"),
        "games": games,
        "picks": picks,
    }
    os.makedirs(os.path.dirname(SNAP), exist_ok=True)
    with open(SNAP, "w", encoding="utf-8") as fh:
        json.dump(snap, fh, indent=1)
    print("pulled %d games (%d graded), %d picks" % (len(games), len(graded), len(picks)))


def fmt(n):
    return str(int(n)) if float(n).is_integer() else "%.1f" % n


def eastern(iso):
    t = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    try:
        from zoneinfo import ZoneInfo
        t = t.astimezone(ZoneInfo("America/New_York"))
    except Exception:  # no tz database on this machine: September is EDT
        t = t.astimezone(timezone(timedelta(hours=-4)))
    return t.strftime("%A %I:%M %p").replace(" 0", " ").replace("AM", "am").replace("PM", "pm")


def counts(names_in_order):
    c = Counter(names_in_order)
    seen = []
    for n in names_in_order:
        if n not in seen:
            seen.append(n)
    return [(n, c[n]) for n in seen]


def derive(snap):
    seats = sorted((p for p in snap["seats"] if p["name"]), key=lambda p: p["id"])
    names = [p["name"] for p in seats]
    who = {p["id"]: p["name"] for p in seats}
    weeks = {w["id"]: w for w in snap["weeks"] if w["published"]}
    games = {g["id"]: g for g in snap["games"] if g["week_id"] in weeks}
    graded = {i: g for i, g in games.items() if g["winner_abbr"]}
    order = sorted(weeks, key=lambda i: weeks[i]["week_no"])
    n_games = Counter(g["week_id"] for g in games.values())
    n_graded = Counter(g["week_id"] for g in graded.values())
    finished = [w for i, w in enumerate(order)
                if (n_games[w] >= 20 and n_graded[w] == n_games[w])
                or any(n_graded[x] for x in order[i + 1:])]
    label = {w: weeks[w]["label"] for w in order}
    week_no = {w: weeks[w]["week_no"] for w in order}

    picks = []
    for p in snap["picks"]:
        g = graded.get(p["game_id"])
        if not g or p["player_id"] not in who:
            continue
        spread = None if g["spread_line"] is None else abs(float(g["spread_line"]))
        picks.append({
            "who": who[p["player_id"]], "week": p["week_id"], "team": p["pick_abbr"],
            "stake": p["confidence"], "won": p["pick_abbr"] == g["winner_abbr"],
            "dog": spread is not None and p["pick_abbr"] == g["underdog_abbr"],
            "spread": spread, "game": g["id"],
            "ko": datetime.fromisoformat(g["kickoff"].replace("Z", "+00:00")),
        })
    picks.sort(key=lambda x: (x["ko"], x["game"]))

    wk = defaultdict(lambda: {"points": 0, "right": 0, "games": 0})
    for x in picks:
        r = wk[(x["week"], x["who"])]
        r["games"] += 1
        if x["won"]:
            r["right"] += 1
            r["points"] += x["stake"]

    def cell(v, display, detail, frac=0.0):
        return {"v": v, "display": display, "detail": detail, "frac": max(0.0, min(1.0, frac))}

    records = []
    for rid, name, group in RECORDS:
        rows = []
        for n in names:
            fw = [(w, wk[(w, n)]) for w in finished if wk[(w, n)]["games"]]
            mine = [x for x in picks if x["who"] == n]
            c = None
            if rid == "best_week" and fw:
                w, r = max(fw, key=lambda t: (t[1]["points"], week_no[t[0]]))
                c = cell(r["points"], str(r["points"]), label[w], r["points"] / 210)
            elif rid == "best_record" and fw:
                w, r = max(fw, key=lambda t: (t[1]["right"], week_no[t[0]]))
                c = cell(r["right"], "%d-%d" % (r["right"], r["games"] - r["right"]), label[w],
                         r["right"] / 20)
            elif rid == "low_week" and len(fw) >= 2:
                w, r = min(fw, key=lambda t: (t[1]["points"], -week_no[t[0]]))
                c = cell(r["points"], str(r["points"]), label[w], r["points"] / 210)
            elif rid == "streak" and mine:
                run = best = 0
                for x in mine:
                    run = run + 1 if x["won"] else 0
                    best = max(best, run)
                c = cell(best, str(best), "in a row")
            elif rid == "worst_miss" and mine:
                lost = [x for x in mine if not x["won"]]
                if lost:
                    x = max(lost, key=lambda x: (x["stake"], x["ko"]))
                    c = cell(x["stake"], str(x["stake"]), "on " + x["team"], x["stake"] / 20)
            elif rid == "my_upset" and mine:
                ups = [x for x in mine if x["won"] and x["dog"]]
                if ups:
                    x = max(ups, key=lambda x: (x["spread"], x["ko"]))
                    c = cell(x["spread"], "+" + fmt(x["spread"]), x["team"])
                else:
                    c = cell(None, "–", "none yet")
            elif rid == "weeks_won" and finished:
                won = sum(1 for w in finished if wk[(w, n)]["games"]
                          and wk[(w, n)]["points"] == max(wk[(w, q)]["points"] for q in names))
                c = cell(won, str(won), "of %d" % len(finished), won / len(finished))
            elif rid == "season_record" and mine:
                right = sum(1 for x in mine if x["won"])
                c = cell(right, "%d-%d" % (right, len(mine) - right), "", right / len(mine))
            rows.append(c or cell(None, "–", ""))

        vals = [r["v"] for r in rows if r["v"] is not None]
        top = max(vals) if vals else 0
        for r in rows:
            if rid in ("streak", "my_upset") and r["v"] is not None and top:
                r["frac"] = r["v"] / top  # no natural ceiling: scale to the leader
            if r["v"] is None:
                r["rank"] = None
            else:
                r["rank"] = 1 + sum(1 for v in vals if (v < r["v"] if rid in LOWER else v > r["v"]))
            r["mark"] = None
            if r["rank"] == 1:
                if rid in BAD:
                    r["mark"] = "worst"
                elif r["v"] > 0:
                    r["mark"] = "best"
        best_n = sum(1 for r in rows if r["mark"] == "best")
        for r in rows:
            r["tied"] = r["mark"] == "best" and best_n > 1

        open_ = None
        if not vals:
            if rid == "low_week":
                nxt = week_no[finished[-1]] + 1 if finished else 2
                open_ = "Starts once Week %d is final" % max(nxt, 2)
            else:
                open_ = "Nothing yet"
        records.append({"id": rid, "label": name, "group": group, "rows": rows, "open": open_})

    # ------------------------------------------------------------------ fame and shame
    totals = Counter()
    for x in picks:
        if x["won"]:
            totals[x["who"]] += x["stake"]
    ups = [x for x in picks if x["won"] and x["dog"]]
    fame = {}

    top = max(totals.values()) if totals else 0
    fame["season_points"] = ([(n, 1) for n in names if top and totals[n] == top],
                             "%d points" % top)

    margins = []
    for w in finished:
        pts = sorted(((wk[(w, n)]["points"], n) for n in names), reverse=True)
        if len(pts) > 1 and pts[0][0] > pts[1][0]:
            margins.append((pts[0][1], w, pts[0][0] - pts[1][0]))
    if margins:
        m = max(x[2] for x in margins)
        best = [x for x in margins if x[2] == m]
        fame["margin"] = (counts([x[0] for x in best]),
                          "Won %s by %d" % (label[best[0][1]], m) if len(best) == 1
                          else "%d points clear" % m)
    else:
        fame["margin"] = ([], "")

    if ups:
        m = max(x["spread"] for x in ups)
        best = [x for x in ups if x["spread"] == m]
        teams = list(dict.fromkeys(x["team"] for x in best))
        fame["big_upset"] = (counts([x["who"] for x in best]),
                             "%s +%s" % (" and ".join(teams), fmt(m)))
    else:
        fame["big_upset"] = ([], "")

    by_game = defaultdict(list)
    for x in picks:
        by_game[x["game"]].append(x)
    lone = []
    for xs in by_game.values():
        right = [x for x in xs if x["won"]]
        if len(right) == 1:
            lone.append(right[0])
    fame["only_one"] = (counts([x["who"] for x in lone]),
                        "%s, %s" % (lone[-1]["team"], label[lone[-1]["week"]]) if len(lone) == 1
                        else "%d games" % len(lone))

    three = [(n, w) for w in order for n in names
             if sum(1 for x in ups if x["who"] == n and x["week"] == w) >= 3]
    fame["three_upsets"] = (counts([n for n, _ in three]),
                            label[three[0][1]] if len(three) == 1 else "%d weeks" % len(three))

    two = [x for x in ups if x["spread"] >= 14]
    fame["two_td_upset"] = (counts([x["who"] for x in two]),
                            "%s +%s" % (two[0]["team"], fmt(two[0]["spread"])) if len(two) == 1
                            else "%d times" % len(two))

    by20 = [x for x in margins if x[2] >= 20]
    fame["win_by_20"] = (counts([x[0] for x in by20]),
                         "Won %s by %d" % (label[by20[0][1]], by20[0][2]) if len(by20) == 1
                         else "%d weeks" % len(by20))

    perfect = [(n, w) for w in finished for n in names
               if wk[(w, n)]["games"] >= 20 and wk[(w, n)]["right"] == wk[(w, n)]["games"]]
    fame["perfect_week"] = (counts([n for n, _ in perfect]),
                            label[perfect[0][1]] if len(perfect) == 1 else "%d weeks" % len(perfect))

    lost20 = [x for x in picks if x["stake"] == 20 and not x["won"]]
    shame = {"id": "lost_20", "label": rb.BY_ID["lost_20"][2],
             "holders": counts([x["who"] for x in lost20]),
             "detail": ("20 on %s, %s" % (lost20[0]["team"], label[lost20[0]["week"]])
                        if len(lost20) == 1 else "%d times" % len(lost20))}

    standings = []
    for n in sorted(names, key=lambda n: -totals[n]):
        standings.append((1 + sum(1 for q in names if totals[q] > totals[n]), n, totals[n]))

    cur = [w for w in order if n_graded[w] and w not in finished]
    return {
        "names": names,
        "records": records,
        "fame": [{"id": bid, "label": FAME_LABEL[bid], "holders": fame[bid][0],
                  "detail": fame[bid][1], "what": WHAT[bid]} for bid in FAME_ORDER],
        "shame": shame,
        "standings": standings,
        "finished": len(finished),
        "as_of": eastern(snap["pulled_at"]),
        "state": ("%s is final and %d of %s's %d games are in"
                  % (" and ".join(label[w] for w in finished) or "No week",
                     n_graded[cur[0]], label[cur[0]], n_games[cur[0]]) if cur
                  else "%d weeks are final" % len(finished)),
        "next_week": week_no[cur[0]] if cur else None,
    }


# ------------------------------------------------------------------------ pieces


def ranked(rec):
    """Seat-ordered rows, re-sorted best first. Nobody-yet rows go last."""
    pairs = list(zip(MODEL["names"], rec["rows"]))
    idx = {n: i for i, n in enumerate(MODEL["names"])}
    return sorted(pairs, key=lambda p: (p[1]["rank"] is None, p[1]["rank"] or 0, idx[p[0]]))


def mark(c):
    if c["v"] is None:
        return " is-none"
    return {"best": " is-best", "worst": " is-worst"}.get(c["mark"], "")


def title(text, kick="The record book"):
    return '<div class="rk-title"><p class="rk-kick">%s</p><h3>%s</h3></div>' % (e(kick), e(text))


def face(name, size):
    return rb.face(name, size)


def holders(hs, size=22):
    faces = "".join(face(n, size) for n, _ in hs)
    names = " &amp; ".join("%s%s" % (e(n), " &times;%d" % c if c > 1 else "") for n, c in hs)
    return ('<span class="rk-hold"><span class="rk-hold__faces">%s</span><span>%s</span></span>'
            % (faces, names))


def em(text):
    return '<em>%s</em>' % e(text) if text else ""


# ------------------------------------------------------------ 1: one table


def opt1():
    head = '<span class="pk1-corner" role="columnheader"></span>' + "".join(
        '<span class="pk1-who" role="columnheader" style="--pc:%s">%s<b>%s</b></span>'
        % (PC[n], face(n, 30), e(n)) for n in MODEL["names"])
    rows = []
    for r in MODEL["records"]:
        lab = '<span class="pk1-label" role="rowheader" data-fit>%s</span>' % e(r["label"])
        if r["open"]:
            rows.append('<div class="pk1-row is-open" role="row">%s<span class="pk1-wait" role="cell" '
                        'data-fit>%s</span></div>' % (lab, e(r["open"])))
            continue
        cells = "".join('<span class="pk1-cell%s" role="cell" data-fit><b>%s</b>%s</span>'
                        % (mark(c), e(c["display"]), em(c["detail"])) for c in r["rows"])
        rows.append('<div class="pk1-row%s" role="row">%s%s</div>'
                    % (" is-bad" if r["id"] in BAD else "", lab, cells))
    return (title("Everyone's numbers")
            + '<div class="pk1" role="table" aria-label="Everyone\'s numbers">'
              '<div class="pk1-head" role="row">%s</div>%s</div>' % (head, "".join(rows))
            + '<p class="pk-key"><span class="pk-key__best">Gold</span> is the best of the four. '
              '<span class="pk-key__worst">Red</span> is the worst miss.</p>')


# ------------------------------------------------------------ 2: three small tables


def opt2():
    out = [title("Everyone's numbers")]
    people = MODEL["names"]
    for gid, gname in GROUPS:
        recs = [r for r in MODEL["records"] if r["group"] == gid]
        hd = '<span class="pk2-corner"></span>' + "".join(
            '<span class="pk2-hd" data-fit>%s<span>%s</span></span>'
            % (badge(r["id"], 40, bool(r["open"])), e(r["label"])) for r in recs)
        body = []
        for i, n in enumerate(people):
            body.append('<span class="pk2-who" data-fit>%s<b>%s</b></span>' % (face(n, 26), e(n)))
            for j, r in enumerate(recs):
                if r["open"]:
                    if i == 0:
                        body.append('<span class="pk2-wait" style="grid-column:%d;grid-row:2 / span %d" '
                                    'data-fit>%s</span>' % (j + 2, len(people), e(r["open"])))
                    continue
                c = r["rows"][i]
                body.append('<span class="pk2-cell%s" data-fit><b>%s</b>%s</span>'
                            % (mark(c), e(c["display"]), em(c["detail"])))
        out.append('<p class="pk2-group">%s</p><div class="pk2-t" style="--cols:%d">%s%s</div>'
                   % (e(gname), len(recs), hd, "".join(body)))
    return "".join(out)


# ------------------------------------------------------------ 3: leaderboards


def opt3():
    cards = []
    for r in MODEL["records"]:
        hd = ('<header class="pk3-hd">%s<h4 data-fit>%s</h4></header>'
              % (badge(r["id"], 40, bool(r["open"])), e(r["label"])))
        if r["open"]:
            body = '<p class="pk3-wait" data-fit>%s</p>' % e(r["open"])
        else:
            lines = "".join(
                '<li class="pk3-line%s"><span class="pk3-rank">%s</span><span class="pk3-who" data-fit>'
                '<b>%s</b>%s</span><span class="pk3-val" data-fit>%s</span></li>'
                % (mark(c), c["rank"] if c["rank"] else "–", e(n), em(c["detail"]),
                   e(c["display"])) for n, c in ranked(r))
            body = '<ol class="pk3-list">%s</ol>' % lines
        cards.append('<section class="pk3-card%s%s">%s%s</section>'
                     % (" is-bad" if r["id"] in BAD else "", " is-open" if r["open"] else "", hd, body))
    return title("Everyone's numbers") + '<div class="pk3">%s</div>' % "".join(cards)


# ------------------------------------------------------------ 4: bar race


def opt4():
    recs = []
    for r in MODEL["records"]:
        hd = ('<header class="pk4-hd">%s<h4>%s</h4></header>'
              % (badge(r["id"], 38, bool(r["open"])), e(r["label"])))
        if r["open"]:
            recs.append('<section class="pk4-rec is-open">%s<p class="pk4-wait" data-fit>%s</p></section>'
                        % (hd, e(r["open"])))
            continue
        bars = "".join(
            '<div class="pk4-bar%s" style="--pc:%s;--f:%.3f">%s<b class="pk4-name" data-fit>%s</b>'
            '<span class="pk4-track"><i></i></span><span class="pk4-val" data-fit><b>%s</b>%s</span></div>'
            % (mark(c), PC[n], c["frac"], face(n, 26), e(n), e(c["display"]), em(c["detail"]))
            for n, c in ranked(r))
        recs.append('<section class="pk4-rec%s">%s<div class="pk4-bars">%s</div></section>'
                    % (" is-bad" if r["id"] in BAD else "", hd, bars))
    return title("Everyone's numbers") + '<div class="pk4">%s</div>' % "".join(recs)


# ------------------------------------------------------------ 5: tap a name


def phrase(c):
    if c["mark"] == "best":
        return '<span class="pk5-best">%s</span>' % ("Tied for best" if c["tied"] else "Best of the four")
    if c["mark"] == "worst":
        return '<span class="pk5-worst">Worst of the four</span>'
    return ""


def opt5(first="Grant"):
    people = MODEL["names"]
    tabs = "".join(
        '<button type="button" class="pk5-tab%s" role="tab" aria-selected="%s" data-who="%s" '
        'style="--pc:%s">%s<b>%s</b></button>'
        % (" is-on" if n == first else "", "true" if n == first else "false", e(n), PC[n],
           face(n, 32), e(n)) for n in people)
    panels = []
    for i, n in enumerate(people):
        rows = []
        for r in MODEL["records"]:
            c = r["rows"][i]
            if r["open"]:
                value, detail, cls, socket = "–", e(r["open"]), " is-none", True
            else:
                bits = [x for x in (e(c["detail"]) if c["detail"] else "", phrase(c)) if x]
                value, detail, cls, socket = c["display"], " &middot; ".join(bits), mark(c), c["v"] is None
            rows.append('<li class="pk5-row%s">%s<div class="pk5-txt" data-fit><p class="pk5-k">%s</p>'
                        '%s</div><p class="pk5-v" data-fit>%s</p></li>'
                        % (cls, badge(r["id"], 46, socket), e(r["label"]),
                           '<p class="pk5-d">%s</p>' % detail if detail else "", e(value)))
        panels.append('<div class="pk5-panel" data-who="%s"%s><p class="pk5-title">%s&rsquo;s numbers</p>'
                      '<ul class="pk5-list">%s</ul></div>'
                      % (e(n), "" if n == first else " hidden", e(n), "".join(rows)))
    return (title("Everyone's numbers")
            + '<div class="pk5"><div class="pk5-tabs" role="tablist">%s</div>%s</div>'
            % (tabs, "".join(panels)))


# ------------------------------------------------------------ 6: headlines

REST = {"best_week": "{v} ({d})", "best_record": "{v} ({d})", "low_week": "{v} ({d})",
        "streak": "{v}", "worst_miss": "{v} {d}", "my_upset": "{v} {d}", "weeks_won": "{v}",
        "season_record": "{v}"}


def join_names(ns):
    return ns[0] if len(ns) == 1 else "%s and %s" % (", ".join(ns[:-1]), ns[-1])


def opt6():
    recs = []
    for r in MODEL["records"]:
        rr = ranked(r)
        lead = [(n, c) for n, c in rr if c["mark"]]
        if r["open"] or not lead:
            recs.append('<section class="pk6-rec is-open">%s<div class="pk6-body" data-fit>'
                        '<p class="pk6-k">%s</p><p class="pk6-wait">%s</p></div></section>'
                        % (badge(r["id"], 54, True), e(r["label"]), e(r["open"] or "Nobody yet")))
            continue
        c0 = lead[0][1]
        same = len({c["detail"] for _, c in lead}) == 1
        lead_html = ('<p class="pk6-lead"><span class="pk6-faces">%s</span><b>%s</b>'
                     '<span class="pk6-v">%s</span>%s</p>'
                     % ("".join(face(n, 28) for n, _ in lead), " &amp; ".join(e(n) for n, _ in lead),
                        e(c0["display"]), em(c0["detail"]) if same else ""))
        groups = []
        for n, c in rr:
            if c["mark"]:
                continue
            key = (c["display"], c["detail"], c["v"] is None)
            if groups and groups[-1][0] == key:
                groups[-1][1].append(n)
            else:
                groups.append((key, [n]))
        rest = []
        for (disp, det, none), ns in groups:
            if none:
                rest.append("%s %s" % (join_names(ns), det or "none yet"))
                continue
            form = REST[r["id"]]
            # "James 179 (Week 1) · Parker 164 (Week 1)" says Week 1 four times when the
            # headline already said it once. Only a different week earns its brackets.
            if same and det == c0["detail"]:
                form = form.replace(" ({d})", "")
            rest.append("%s %s" % (join_names(ns), form.format(v=disp, d=det).strip()))
        recs.append('<section class="pk6-rec%s">%s<div class="pk6-body" data-fit><p class="pk6-k">%s</p>'
                    '%s<p class="pk6-rest">%s</p></div></section>'
                    % (" is-bad" if r["id"] in BAD else "", badge(r["id"], 54), e(r["label"]),
                       lead_html, " &middot; ".join(e(x) for x in rest)))
    return title("Everyone's numbers") + '<div class="pk6">%s</div>' % "".join(recs)


# ------------------------------------------------------------ 7: trophy room (last pick)


def fame_tile(a, size):
    return ('<div class="rkA-award">%s<p class="rkA-award__k">%s</p>%s<p class="rkA-award__d">%s</p></div>'
            % (badge(a["id"], size), e(a["label"]), holders(a["holders"]), e(a["detail"])))


def opt7():
    won = [a for a in MODEL["fame"] if a["holders"]]
    grabs = [a for a in MODEL["fame"] if not a["holders"]]
    cols = 2 if len(grabs) in (2, 4) else min(3, max(1, len(grabs)))
    sockets = "".join('<div class="rkC-grab">%s<p>%s</p></div>'
                      % (badge(a["id"], 62, True), e(a["label"])) for a in grabs)
    return ('<section class="rkC-stage"><p class="rk-kick">The record book</p><h3>Hall of fame</h3>'
            '<div class="rkC-won">%s</div><p class="rkC-sub">Up for grabs</p>'
            '<div class="rkC-grabs" style="grid-template-columns:repeat(%d,minmax(0,1fr))">%s</div></section>'
            % ("".join(fame_tile(a, 104) for a in won), cols, sockets))


# ------------------------------------------------------------ 8: trophy case


def opt8():
    slots = []
    for a in MODEL["fame"]:
        if a["holders"]:
            slots.append('<div class="pk8-slot is-won" data-fit>%s<p class="pk8-k">%s</p>%s'
                         '<p class="pk8-d">%s</p></div>'
                         % (badge(a["id"], 78), e(a["label"]), holders(a["holders"]), e(a["detail"])))
        else:
            slots.append('<div class="pk8-slot is-open" data-fit>%s<p class="pk8-k">%s</p>'
                         '<p class="pk8-grab">Up for grabs</p></div>'
                         % (badge(a["id"], 78, True), e(a["label"])))
    won = sum(1 for a in MODEL["fame"] if a["holders"])
    return ('<section class="pk8"><div class="pk8-hd"><p class="rk-kick">The record book</p>'
            '<h3>Hall of fame</h3><p class="pk8-count">%d of %d claimed</p></div>'
            '<div class="pk8-case">%s</div></section>' % (won, len(MODEL["fame"]), "".join(slots)))


# ------------------------------------------------------------ 9: plaques


def opt9():
    won = [a for a in MODEL["fame"] if a["holders"]]
    grabs = [a for a in MODEL["fame"] if not a["holders"]]
    plaques = "".join(
        '<article class="pk9-plaque">%s<div class="pk9-txt" data-fit><p class="pk9-k">%s</p>%s'
        '<p class="pk9-d">%s</p></div></article>'
        % (badge(a["id"], 70), e(a["label"]), holders(a["holders"], 24), e(a["detail"])) for a in won)
    chips = "".join('<div class="pk9-grab">%s<p data-fit>%s</p></div>'
                    % (badge(a["id"], 44, True), e(a["label"])) for a in grabs)
    return ('<section class="pk9"><div class="pk9-hd"><p class="rk-kick">The record book</p>'
            '<h3>Hall of fame</h3></div><div class="pk9-plaques">%s</div>'
            '<p class="pk9-sub">Up for grabs</p><div class="pk9-grabs">%s</div></section>'
            % (plaques, chips))


# ------------------------------------------------------------ 10-12: Hall of shame


def opt10():
    a = MODEL["shame"]
    if a["holders"]:
        body = ('%s<div><p class="rk-shame__k">%s</p>%s<p class="rk-shame__d">%s</p></div>'
                % (badge("lost_20", 76), e(a["label"]), holders(a["holders"], 24), e(a["detail"])))
    else:
        body = ('%s<div><p class="rk-shame__k">%s</p><p class="rk-shame__d">Nobody yet. Every 20 has '
                'won so far.</p></div>' % (badge("lost_20", 72, True), e(a["label"])))
    return ('<section class="rk-shame pk10"><div class="rk-shame__hd"><h3>Hall of shame</h3></div>'
            '<div class="rk-shame__row">%s</div></section>' % body)


def opt11():
    a = MODEL["shame"]
    if a["holders"]:
        mugs = "".join('<div class="pk11-mug">%s</div>' % face(n, 88) for n, _ in a["holders"])
        who = " &amp; ".join("%s%s" % (e(n), " &times;%d" % c if c > 1 else "") for n, c in a["holders"])
        inner = ('<div class="pk11-mugs">%s</div><p class="pk11-name">%s</p><p class="pk11-crime">%s</p>'
                 % (mugs, who, e(a["detail"])))
    else:
        inner = '<p class="pk11-crime">Nobody yet. Every 20 has won so far.</p>'
    return ('<section class="pk11"><div class="pk11-poster"><p class="pk11-top">Hall of shame</p>'
            '<p class="pk11-big">Lost your 20</p>%s</div></section>' % inner)


def opt12():
    a = MODEL["shame"]
    who = holders(a["holders"], 24) if a["holders"] else ""
    detail = a["detail"] if a["holders"] else "Nobody yet. Every 20 has won so far."
    return ('<section class="pk12"><div class="pk12-strip">%s<div class="pk12-txt" data-fit>'
            '<p class="pk12-k">Hall of shame</p><p class="pk12-award">%s</p>%s<p class="pk12-d">%s</p>'
            '</div></div></section>'
            % (badge("lost_20", 64, not a["holders"]), e(a["label"]), who, e(detail)))


# ------------------------------------------------------------------------ the board

PARTS = [
    ("numbers", "Everyone's numbers", "1 to 6",
     "Eight records for each of you. Last time's table made you swipe sideways. None of these do.",
     "1. It is the table you liked, turned so it fits, and all 32 numbers are on one screen.", [
         (1, "One table", opt1, None,
          "Records down the side, the four of you across the top. Gold is the best in each row, "
          "red is the worst miss."),
         (2, "Three small tables", opt2, None,
          "Last time's table split into three short ones, so nothing swipes: your names down the "
          "left, the records across the top."),
         (3, "Leaderboards", opt3, None,
          "Every record ranks the four of you, first to last, two cards to a row."),
         (4, "Bar race", opt4, None,
          "The loud one. Every record is a race, one bar each in the color behind your logo, "
          "leader on top."),
         (5, "Tap a name", opt5, None,
          "One person at a time, badges big. It opens on whoever is signed in, and you tap a "
          "logo to see someone else. Try it, the buttons work."),
         (6, "Headlines", opt6, None,
          "Each record names who holds it in big type, with everyone else underneath."),
     ]),
    ("fame", "Hall of fame", "7 to 9",
     "Eight awards. Four are claimed so far.",
     "7, still. It is your pick from last time, with this week's awards in it.", [
         (7, "Trophy room", opt7, "Your pick last time",
          "Claimed awards shown huge on a spotlit stage, then the up for grabs row you liked."),
         (8, "Trophy case", opt8, None,
          "All eight awards keep the same spot all season, easiest first. Claimed ones light up; "
          "the rest wait dark until someone earns them."),
         (9, "Plaques", opt9, None,
          "Claimed awards as plaques you can read at a glance: badge, award, who, and what they "
          "did. Up for grabs sits underneath."),
     ]),
    ("shame", "Hall of shame", "10 to 12",
     "One award, and since this afternoon it has a holder.",
     "10, your pick from last time. 11 if you want it to sting.", [
         (10, "Red panel", opt10, "Your pick last time",
          "The red panel under the Hall of fame, now with its first name on it."),
         (11, "Wanted poster", opt11, None,
          "A paper wanted poster with a mugshot. Loud and a little mean, on purpose."),
         (12, "Warning strip", opt12, None,
          "A slim hazard-striped strip. Says it and gets out of the way."),
     ]),
]


def phone(inner, cls=""):
    return ('<div class="pk-phone %s"><div class="app" data-mode="book"><main class="app__body">'
            '<div class="app__page">%s</div></main></div></div>' % (cls, inner))


def standings():
    rows = "".join(
        '<div class="srow%s"><span class="srow__pos num">%d</span>%s<span class="srow__body">'
        '<span class="srow__name">%s</span></span><span><span class="srow__pts num">%d</span>'
        '<span class="srow__ptslabel">pts</span></span></div>'
        % (" is-leader" if rank == 1 else "", rank, face(name, 36), e(name), pts)
        for rank, name, pts in MODEL["standings"])
    n = MODEL["finished"]
    return ('<div class="screen"><p class="eyebrow">Season 2026</p><h2 class="h1">Season</h2>'
            '<p class="sub">%d %s in the books. Ties stand, so a week can be shared.</p></div>'
            '<div class="stand">%s</div>' % (n, "week" if n == 1 else "weeks", rows))


def final_phone():
    hdr = ('<header class="apphdr"><div><span class="apphdr__title">Motley Pick&apos;em</span>'
           '<span class="apphdr__week">Week %s &middot; 20 games</span></div>'
           '<span class="apphdr__me">%s<span class="apphdr__name">Grant</span></span></header>'
           % (MODEL["next_week"] or "", face("Grant", 24)))
    form = ('<p class="pb-form-note" data-fit>The form chart goes here once Week %s is final.</p>'
            % (MODEL["next_week"] or 2))
    return ('<div class="pk-phone pk-phone--final"><div class="app" data-mode="book">%s'
            '<main class="app__body"><div class="app__page">%s%s<div data-slot="fame"></div>'
            '<div data-slot="shame"></div><div data-slot="numbers"></div></div></main></div></div>'
            % (hdr, standings(), form))


def board_body():
    parts = []
    for key, name, rng, about, take, options in PARTS:
        cards = []
        for n, oname, fn, was, what in options:
            cards.append(
                '<article class="pb-opt" data-part="%s" data-n="%d" id="opt-%d">'
                '<div class="pb-opt__hd"><span class="pb-num">%d</span><div class="pb-opt__names">'
                '<h3 class="pb-opt__name">%s</h3>%s</div></div>'
                '<p class="pb-opt__what">%s</p>'
                '<p class="pb-facts" data-facts>measuring&hellip;</p>'
                '<button type="button" class="pb-pick" aria-pressed="false">Pick %d</button>%s</article>'
                % (key, n, n, n, e(oname), '<p class="pb-was">%s</p>' % e(was) if was else "",
                   e(what), n, phone(fn())))
        parts.append(
            '<section class="pb-part" id="part-%s"><header class="pb-part__hd"><div>'
            '<p class="pb-part__range">Pick one: %s</p><h2>%s</h2><p class="pb-part__about">%s</p></div>'
            '<p class="pb-take"><b>My pick:</b> %s</p></header><div class="pb-grid">%s</div></section>'
            % (key, e(rng), e(name), e(about), e(take), "".join(cards)))

    return """
<header class="pb-top"><div class="pb-wrap">
  <p class="pb-kick">Motley Pick'em &middot; Season tab &middot; Record book</p>
  <h1>Pick your record book by number</h1>
  <p class="pb-lede">Three parts, one pick in each. Every phone below is the real thing: the
    app's own colors and type, this season's real numbers, <b>your 17 ChatGPT badges</b>,
    the whole section with nothing hidden, and nothing that swipes sideways. Tap
    <b>Pick</b> under the ones you want, or just send me the numbers, like
    &ldquo;1, 7, 10&rdquo;.</p>
  <p class="pb-asof">Numbers as of %(as_of)s. %(state)s, so the week records count
    finished weeks only.</p>
  <ol class="pb-map" aria-label="The Season tab, top to bottom">
    <li>Standings</li><li class="pb-arrow" aria-hidden="true">&rarr;</li>
    <li>Form chart <span>once Week %(next)s is final</span></li><li class="pb-arrow" aria-hidden="true">&rarr;</li>
    <li class="is-pick"><a href="#part-fame">Hall of fame <span>7 to 9</span></a></li><li class="pb-arrow" aria-hidden="true">&rarr;</li>
    <li class="is-pick"><a href="#part-shame">Hall of shame <span>10 to 12</span></a></li><li class="pb-arrow" aria-hidden="true">&rarr;</li>
    <li class="is-pick"><a href="#part-numbers">Everyone's numbers <span>1 to 6</span></a></li>
  </ol>
</div></header>

<main class="pb-wrap">
  %(parts)s

  <section class="pb-part pb-final" id="part-final">
    <header class="pb-part__hd"><div>
      <p class="pb-part__range">What gets built</p><h2>Your Season tab</h2>
      <p class="pb-part__about">Your picks, put together in the order they sit on the tab. It
        changes as you pick.</p></div></header>
    <div class="pb-final__grid">
      %(final)s
      <div class="pb-final__copy">
        <p class="pb-facts" data-final-facts>measuring&hellip;</p>
        <h3>After you pick</h3>
        <ul class="pb-next">
          <li>I build your three picks into the Season tab.</li>
          <li>The same build fixes the bug where a half-played week counted as finished. It is
            what had Nicole winning Week 2 after one game.</li>
          <li>The small &ldquo;pts&rdquo; under the standings and the &ldquo;Season 2026&rdquo;
            line go up to 13px, like everything here.</li>
          <li>Your 17 badges go in exactly as they look here: full color once someone holds
            the record, grey in a dashed ring while it is up for grabs.</li>
          <li>You see screenshots of the real tab before anything goes live.</li>
        </ul>
        <label class="pb-note" for="pb-note">Anything to change about the ones you picked?</label>
        <textarea id="pb-note" rows="4" placeholder="Optional. For example: 1, but make the numbers bigger."></textarea>
      </div>
    </div>
  </section>
</main>

<div class="pb-bar" role="status" aria-live="polite"><div class="pb-bar__in">
  <span class="pb-bar__k">Your picks</span>
  <a class="pb-slot" href="#part-numbers">Numbers <b data-bar="numbers">&ndash;</b></a>
  <a class="pb-slot" href="#part-fame">Fame <b data-bar="fame">&ndash;</b></a>
  <a class="pb-slot" href="#part-shame">Shame <b data-bar="shame">&ndash;</b></a>
  <span class="pb-save" data-save></span>
</div></div>
<pre id="pb-measure" hidden></pre>
""" % {"as_of": e(MODEL["as_of"]), "state": e(MODEL["state"]), "next": MODEL["next_week"] or 2,
       "parts": "".join(parts), "final": final_phone()}


def build(standalone: bool) -> str:
    css = "".join(open(os.path.join(ROOT, "src", f), encoding="utf-8").read()
                  for f in ("theme.css", "app.css"))
    rk = open(os.path.join(ROOT, "scripts", "recordbook_board.css"), encoding="utf-8").read()
    pk = open(os.path.join(ROOT, "scripts", "pickbook_board.css"), encoding="utf-8").read()
    js = open(os.path.join(ROOT, "scripts", "pickbook_board.js"), encoding="utf-8").read()
    logos = ":root{%s}" % "".join("--lg-%s:url(%s);" % (t, rb.logo(t)) for t in rb.TEAM.values())
    # Each badge once, as a custom property, however many times the board draws it.
    badges = ":root{%s}" % "".join("--bd-%s:url(%s);" % (b[0], BADGE_URI[b[0]]) for b in rb.BADGES)
    doc = ('<!doctype html>\n<html lang="en">\n<meta charset="utf-8">\n'
           '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
           if standalone else "")
    return (doc + "<title>Record Book Picks</title>\n"
            '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '<link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,400..800'
            '&family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">\n'
            "<style>%s\n%s\n%s\n%s\n%s</style>\n%s<script>%s</script>\n"
            % (logos, badges, css, rk, pk, board_body(), js))


if __name__ == "__main__":
    if "--pull" in sys.argv:
        pull()
    MODEL = derive(json.load(open(SNAP, encoding="utf-8")))
    BADGE_URI = {b[0]: badge_uri(b[0]) for b in rb.BADGES}
    print("badges: %d, %.0f KB embedded" % (len(BADGE_URI), sum(len(u) for u in BADGE_URI.values()) / 1024))
    for path, standalone in ((OUT, True), (OUT.replace(".html", ".artifact.html"), False)):
        page = build(standalone)
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(page)
        print("wrote %s  (%.0f KB)" % (path, len(page.encode()) / 1024))
    print(json.dumps({"as_of": MODEL["as_of"], "state": MODEL["state"],
                      "standings": MODEL["standings"],
                      "fame": [(a["id"], a["holders"], a["detail"]) for a in MODEL["fame"]],
                      "shame": (MODEL["shame"]["holders"], MODEL["shame"]["detail"])}, indent=1))
