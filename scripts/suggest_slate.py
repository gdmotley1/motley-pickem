"""Build the weekly game pool and the auto-selected 20 for Dad to approve.

Produces a POOL of 40 games. The best 20 are pre-selected; the other 20 are alternates
the admin screen can swap in with one tap.

Selection order, per Grant on 2026-09-03:
  1. Georgia's game. Always, no matter the spread.
  2. Enough more SEC games to reach 5 SEC games total.
  3. Fill to 20 across certainty tiers so confidence points stay meaningful.
     A confidence pool needs a gradient: some safe 20-point locks, a big middle, a few
     toss-ups. Neither "20 most competitive" nor ESPN's featured list gives you that.

Sources are keyless ESPN endpoints. The featured list is ESPN's own editorially
maintained top-games list, which refreshes weekly on its own:
    site.api.espn.com/apis/v2/scoreboard/header?sport=football&league=college-football
It returns a fixed 25 games spanning about a week and a half and ignores limit/dates
params, so we filter to the target window ourselves.

Usage:
    python scripts/suggest_slate.py --start 2026-09-03 --end 2026-09-06
    python scripts/suggest_slate.py --start 2026-09-03 --end 2026-09-06 --out outputs/w1.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys

from fetch_slate import _get, et, fetch

FEATURED = ("https://site.api.espn.com/apis/v2/scoreboard/header"
            "?sport=football&league=college-football")

SLATE_SIZE = 20
POOL_SIZE = 40

SEC_CONFERENCE_ID = 8
SEC_MINIMUM = 5                 # SEC games guaranteed in the 20, Georgia counting as one
ALWAYS_INCLUDE = ("UGA",)       # abbreviations that are never left out

# Certainty tiers, shaped from Dad's real 2026-09-05 slate:
# 3 toss-ups, 7 close, 3 medium, 4 big, 3 blowouts.
# (label, inclusive upper bound on the line, target count)
TIERS = (
    ("toss-up", 4.0, 3),
    ("close", 10.0, 7),
    ("medium", 18.0, 3),
    ("big", 28.0, 4),
    ("blowout", 999.0, 3),
)


def featured_ids() -> list:
    """ESPN's curated top games, in their own editorial order."""
    payload = _get(FEATURED)
    ids = []
    for sport in payload.get("sports", []):
        for league in sport.get("leagues", []):
            for e in league.get("events", []):
                eid = str(e.get("id")) if e.get("id") is not None else None
                if eid and eid not in ids:
                    ids.append(eid)
    return ids


def tier_of(g: dict):
    """Certainty tier for a game. A game with no posted line is unusable for a pool."""
    line = g["odds"].get("line")
    if line is None:
        return None
    for label, upper, _ in TIERS:
        if float(line) <= upper:
            return label
    return None


def conf_id(team: dict):
    """ESPN returns conferenceId as a string. Compare as int or nothing matches."""
    try:
        return int(team.get("conference_id"))
    except (TypeError, ValueError):
        return None


def is_sec(g: dict) -> bool:
    return any(conf_id(g[s]) == SEC_CONFERENCE_ID for s in ("home", "away"))


def has_team(g: dict, abbr: str) -> bool:
    return abbr in (g["home"]["abbr"], g["away"]["abbr"])


def gid(g: dict) -> str:
    return str(g["espn_id"])


def rank_key(g: dict):
    """Featured games win ties; interest score orders the rest."""
    return (not g.get("featured"), -g["interest"])


def select_slate(games: list):
    """Return (slate of 20, why each game is in it)."""
    usable = [g for g in games if tier_of(g)]
    chosen, reasons = [], {}

    def take(g, why):
        if gid(g) not in reasons:
            chosen.append(g)
            reasons[gid(g)] = why

    # 1. Always-include teams.
    for abbr in ALWAYS_INCLUDE:
        for g in sorted((x for x in usable if has_team(x, abbr)), key=rank_key):
            take(g, "always %s" % abbr)
            break

    # 2. Top up to the SEC minimum.
    sec_have = sum(1 for g in chosen if is_sec(g))
    for g in sorted((x for x in usable if is_sec(x)), key=rank_key):
        if sec_have >= SEC_MINIMUM:
            break
        if gid(g) not in reasons:
            take(g, "SEC")
            sec_have += 1

    # 3. Fill the certainty tiers, crediting whatever the forced picks already covered.
    buckets = {label: [] for label, _, _ in TIERS}
    for g in usable:
        buckets[tier_of(g)].append(g)
    for label in buckets:
        buckets[label].sort(key=rank_key)

    for label, _, want in TIERS:
        already = sum(1 for g in chosen if tier_of(g) == label)
        for g in buckets[label]:
            if already >= want or len(chosen) >= SLATE_SIZE:
                break
            if gid(g) not in reasons:
                take(g, label)
                already += 1

    # 4. Backfill if a light week left a tier short.
    for g in sorted(usable, key=rank_key):
        if len(chosen) >= SLATE_SIZE:
            break
        if gid(g) not in reasons:
            take(g, "backfill")

    return chosen[:SLATE_SIZE], reasons


def build(start: dt.date, end: dt.date) -> dict:
    games = fetch(start, end)

    try:
        feat_order = featured_ids()
    except RuntimeError as e:
        print("WARNING: featured list unavailable (%s). Using interest score only."
              % e, file=sys.stderr)
        feat_order = []
    feat_rank = {eid: i for i, eid in enumerate(feat_order)}
    for g in games:
        g["featured"] = gid(g) in feat_rank
        g["featured_rank"] = feat_rank.get(gid(g))

    slate, reasons = select_slate(games)
    picked = {gid(g) for g in slate}

    alternates = sorted((g for g in games if gid(g) not in picked and tier_of(g)),
                        key=rank_key)[:POOL_SIZE - len(slate)]

    for g in slate:
        g["selected"] = True
        g["reason"] = reasons.get(gid(g))
    for g in alternates:
        g["selected"] = False
        g["reason"] = None

    slate.sort(key=lambda g: g["kickoff_utc"] or "")
    return {
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "window": {"start": start.isoformat(), "end": end.isoformat()},
        "featured_in_window": sum(1 for g in games if g["featured"]),
        "total_games": len(games),
        "sec_games": sum(1 for g in slate if is_sec(g)),
        "slate": slate,
        "alternates": alternates,
        "pool_size": len(slate) + len(alternates),
    }


def fmt(g: dict) -> str:
    tag = "*" if g.get("featured") else " "
    sec = "SEC" if is_sec(g) else "   "
    return "%s %-16s %s ET %-12s %-9s %-8s %s %6.1f  %s" % (
        tag, g["short_name"], et(g["kickoff_utc"]).strftime("%a %m/%d %I:%M%p"),
        g["odds"].get("details") or "no line", (g.get("tv") or "")[:9],
        tier_of(g) or "-", sec, g["interest"], g.get("reason") or "")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--start", required=True)
    p.add_argument("--end", required=True)
    p.add_argument("--out", default=None)
    p.add_argument("--alts", type=int, default=6, help="how many alternates to print")
    a = p.parse_args()

    res = build(dt.date.fromisoformat(a.start), dt.date.fromisoformat(a.end))
    print("pool of %d from %d games (%d ESPN-featured in window), %d SEC in the 20"
          % (res["pool_size"], res["total_games"], res["featured_in_window"],
             res["sec_games"]))

    print("\nAUTO-SELECTED 20 (* = ESPN featured)")
    print("  %-16s %-18s %-12s %-9s %-8s %3s %6s  %s"
          % ("GAME", "KICKOFF", "LINE", "TV", "TIER", "SEC", "SCORE", "WHY"))
    for g in res["slate"]:
        print(fmt(g))

    counts = {}
    for g in res["slate"]:
        counts[tier_of(g)] = counts.get(tier_of(g), 0) + 1
    print("\ntier mix: " + "  ".join("%s=%d" % (lbl, counts.get(lbl, 0))
                                    for lbl, _, _ in TIERS))

    if a.alts:
        print("\nALTERNATES (%d total, swappable in the admin screen):"
              % len(res["alternates"]))
        for g in res["alternates"][:a.alts]:
            print(fmt(g))

    ok = True
    if len(res["slate"]) != SLATE_SIZE:
        print("\nFAIL: slate has %d games, expected %d"
              % (len(res["slate"]), SLATE_SIZE), file=sys.stderr)
        ok = False
    if res["sec_games"] < SEC_MINIMUM:
        print("\nFAIL: only %d SEC games, expected at least %d"
              % (res["sec_games"], SEC_MINIMUM), file=sys.stderr)
        ok = False
    for abbr in ALWAYS_INCLUDE:
        played = any(has_team(g, abbr) for g in res["slate"] + res["alternates"])
        if played and not any(has_team(g, abbr) for g in res["slate"]):
            print("\nFAIL: %s plays this week but is not in the slate" % abbr,
                  file=sys.stderr)
            ok = False
    if not ok:
        return 1

    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=1)
        print("\nwrote %s" % a.out)
    print("\nOK: %d selected, %d alternates, %d SEC, Georgia included"
          % (len(res["slate"]), len(res["alternates"]), res["sec_games"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
