"""Pull a week of FBS college football games from ESPN's keyless scoreboard API.

Source of truth for games, kickoff times, spreads, and scores. See memory/decisions.md.
No API key, no account. groups=80 is FBS.

Usage:
    python scripts/fetch_slate.py --start 2026-09-03 --end 2026-09-06
    python scripts/fetch_slate.py --start 2026-09-03 --end 2026-09-06 --top 20
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import re
import sys
import urllib.error
import urllib.request

ESPN = ("https://site.api.espn.com/apis/site/v2/sports/football/college-football"
        "/scoreboard?groups=80&limit=400&dates={d}")
UNRANKED = 99
# ESPN conferenceId values that are FBS. Anything else (179 = Ohio Valley, etc.) is FCS.
FBS_CONFERENCES = {1, 4, 5, 8, 9, 12, 15, 17, 18, 37, 151}
PICKEM_TOKENS = ("EVEN", "PK", "PICK", "PICKEM")


# User-Agent handling is fussy and environment-dependent. Grant's sandbox egress proxy
# 403s browser-like UA strings, while some hosts 403 obviously-scripted ones. Try the
# variants in order rather than hard-coding a guess. {} means "send the library default".
UA_VARIANTS = (
    {},
    {"Accept": "application/json, text/plain, */*"},
    {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"),
     "Accept": "application/json, text/plain, */*"},
)


def _get(url: str, tries: int = 2) -> dict:
    last = None
    for _ in range(tries):
        for headers in UA_VARIANTS:
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=30) as r:
                    return json.load(r)
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
                last = e
    raise RuntimeError("ESPN fetch failed after %d rounds: %s (%s)" % (tries, url, last))


def _side(competitors: list, which: str) -> dict:
    for c in competitors:
        if c.get("homeAway") == which:
            return c
    return {}


def _spread(comp: dict, home_abbr: str, away_abbr: str) -> dict:
    """Return favorite / underdog / line. ESPN's `details` looks like 'LSU -10'."""
    odds_list = comp.get("odds") or []
    empty = {"details": None, "favorite": None, "underdog": None,
             "line": None, "over_under": None}
    if not odds_list:
        return empty

    o = odds_list[0]
    details = o.get("details")
    fav = None
    line = None

    # Preferred: ESPN's explicit favorite flags.
    if (o.get("homeTeamOdds") or {}).get("favorite"):
        fav = home_abbr
    elif (o.get("awayTeamOdds") or {}).get("favorite"):
        fav = away_abbr

    # Fallback: parse the abbreviation out of "ABBR -10.5".
    if details:
        text = details.strip()
        m = re.match(r"^([A-Za-z0-9&.\-' ]+?)\s+(-?\d+(?:\.\d+)?)$", text)
        if m:
            token = m.group(1).strip()
            line = abs(float(m.group(2)))
            if fav is None:
                if token == home_abbr:
                    fav = home_abbr
                elif token == away_abbr:
                    fav = away_abbr
        elif text.upper().replace("'", "") in PICKEM_TOKENS:
            line = 0.0

    if line is None and o.get("spread") is not None:
        try:
            line = abs(float(o["spread"]))
        except (TypeError, ValueError):
            line = None

    dog = None
    if fav == home_abbr:
        dog = away_abbr
    elif fav == away_abbr:
        dog = home_abbr

    return {"details": details, "favorite": fav, "underdog": dog,
            "line": line, "over_under": o.get("overUnder")}


def _rank(c: dict) -> int:
    return int((c.get("curatedRank") or {}).get("current") or UNRANKED)


def _score(side: dict):
    try:
        return int(side.get("score"))
    except (TypeError, ValueError):
        return None


def _team(side: dict) -> dict:
    t = side.get("team", {})
    return {
        "abbr": t.get("abbreviation", "?"),
        "school": t.get("location"),
        "name": t.get("displayName"),
        "logo": t.get("logo"),
        "color": t.get("color"),
        "rank": _rank(side),
        "record": next((r.get("summary") for r in (side.get("records") or [])), None),
        "score": _score(side),
        "conference_id": t.get("conferenceId"),
    }


def is_fbs(team: dict) -> bool:
    try:
        return int(team.get("conference_id")) in FBS_CONFERENCES
    except (TypeError, ValueError):
        return False


def parse_event(e: dict):
    comps = e.get("competitions") or []
    if not comps:
        return None
    comp = comps[0]
    cs = comp.get("competitors") or []
    home_side, away_side = _side(cs, "home"), _side(cs, "away")
    if not home_side or not away_side:
        return None

    home, away = _team(home_side), _team(away_side)
    status = (comp.get("status") or {}).get("type") or {}
    casts = comp.get("broadcasts") or []
    tv = next((n for b in casts for n in (b.get("names") or [])), None)

    completed = bool(status.get("completed"))
    winner = None
    if completed and home["score"] is not None and away["score"] is not None:
        if home["score"] != away["score"]:
            winner = home["abbr"] if home["score"] > away["score"] else away["abbr"]

    return {
        "espn_id": e.get("id"),
        "name": e.get("name"),
        "short_name": e.get("shortName"),
        "kickoff_utc": e.get("date"),
        "neutral_site": bool(comp.get("neutralSite")),
        "conference_game": bool(comp.get("conferenceCompetition")),
        "tv": tv,
        "home": home,
        "away": away,
        "odds": _spread(comp, home["abbr"], away["abbr"]),
        "state": status.get("state"),          # pre | in | post
        "completed": completed,
        "status_detail": status.get("shortDetail"),
        "winner": winner,
    }


def interest(g: dict) -> float:
    """Score a game for the auto-suggested 20. Higher is more watchable.

    Tuned against the real 2026-09-05 slate. The first cut ranked 40-point blowouts
    (UNT at Indiana, Ball State at Ohio State) in the top five because a top-5 team's
    ranking bonus swamped a spread penalty that merely bottomed out at zero. Big lines
    now subtract outright, and FCS opponents take a hard hit.
    """
    hr, ar = g["home"]["rank"], g["away"]["rank"]
    s = 0.0

    for r in (hr, ar):
        if r < UNRANKED:
            s += (26 - r) * 1.6
    if hr < UNRANKED and ar < UNRANKED:            # ranked vs ranked is the marquee case
        s += 40

    line = g["odds"].get("line")
    if line is not None:
        line = float(line)
        s += 46.0 * math.exp(-((line / 9.0) ** 1.4))   # tight lines are worth watching
        if line > 18.0:
            s -= (line - 18.0) * 1.6                   # and blowouts actively hurt

    if not (is_fbs(g["home"]) and is_fbs(g["away"])):
        s -= 35                                        # FCS tune-up game

    if g["conference_game"]:
        s += 14
    if g["neutral_site"]:
        s += 6

    tv = (g.get("tv") or "").upper()
    if "+" in tv:
        s -= 6                                         # streaming-only tier
    elif any(k in tv for k in ("ABC", "CBS", "NBC", "FOX")):
        s += 16
    elif any(k in tv for k in ("ESPN", "BTN", "SECN", "FS1")):
        s += 8
    return round(s, 2)


def daterange(a: dt.date, b: dt.date):
    d = a
    while d <= b:
        yield d
        d += dt.timedelta(days=1)


def fetch(start: dt.date, end: dt.date) -> list:
    seen, games = set(), []
    for d in daterange(start, end):
        payload = _get(ESPN.format(d=d.strftime("%Y%m%d")))
        for e in payload.get("events", []):
            g = parse_event(e)
            if g and g["espn_id"] not in seen:
                seen.add(g["espn_id"])
                g["interest"] = interest(g)
                games.append(g)
    games.sort(key=lambda g: g["kickoff_utc"] or "")
    return games


def et(iso: str) -> dt.datetime:
    """ESPN returns UTC. Eastern is UTC-4 during the regular season (EDT through Nov 1)."""
    k = dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    offset = 4 if 3 < k.month < 11 else 5
    return k - dt.timedelta(hours=offset)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--out", default=None)
    p.add_argument("--top", type=int, default=0, help="print the N most interesting games")
    a = p.parse_args()

    games = fetch(dt.date.fromisoformat(a.start), dt.date.fromisoformat(a.end))
    if not games:
        print("No games returned. Check the date range.", file=sys.stderr)
        return 1

    out = a.out or "inputs/slate_%s_%s.json" % (a.start, a.end)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"fetched_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                   "start": a.start, "end": a.end, "count": len(games),
                   "games": games}, f, indent=1)
    print("%d games -> %s" % (len(games), out))

    if a.top:
        print("\nTop %d by interest score:" % a.top)
        for g in sorted(games, key=lambda x: -x["interest"])[:a.top]:
            od = g["odds"]["details"] or "no line"
            print("  %6.1f  %-16s %s ET  %-12s %s" % (
                g["interest"], g["short_name"], et(g["kickoff_utc"]).strftime("%a %I:%M%p"),
                od, g.get("tv") or ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
