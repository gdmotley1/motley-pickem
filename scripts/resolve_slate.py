"""Resolve a hand-written slate (Dad's shorthand) to real ESPN games.

Dad writes his 20 as loose abbreviations, one per line, AWAY vs HOME:

    CLEM vs LSU
    OK ST vs TUL

This maps that to actual ESPN games so the backfill has real ids, kickoff times,
spreads, and results. It fails loudly on anything ambiguous rather than guessing.

Usage:
    python scripts/resolve_slate.py --slate inputs/week01_dad_slate.txt \
        --games inputs/slate_2026-09-03_2026-09-06.json --out inputs/week01_resolved.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys

from fetch_slate import et

# Dad's shorthand -> ESPN abbreviation. Only entries that are genuinely ambiguous or
# that differ from the obvious guess need to live here.
ALIASES = {
    "W GA": "WES", "WEST GA": "WES", "KENN ST": "KENN", "KENNESAW": "KENN",
    "OK": "OU", "OKLA": "OU", "OK ST": "OKST", "OKLA ST": "OKST",
    "N TX": "UNT", "NORTH TX": "UNT", "IND": "IU", "INDIANA": "IU",
    "ORE ST": "ORST", "ORE": "ORE", "BOISE ST": "BOIS", "BOISE": "BOIS",
    "TENN ST": "TNST", "TEX ST": "TXST", "TEX": "TEX",
    "COLO ST": "CSU", "COLO": "COLO",
    "S DAK ST": "SDST", "SD ST": "SDST", "NW": "NU", "NWESTERN": "NU",
    "WKY": "WKU", "W KY": "WKU",
    # Two different "TUL" teams appear on the same slate. Never guess these.
    "TULANE": "TULN", "TULSA": "TLSA",
}

# Where a bare token is dangerously ambiguous, require disambiguation by opponent.
AMBIGUOUS = {"TUL": {"DUKE": "TULN", "OKST": "TLSA"}}


def norm(tok: str) -> str:
    return re.sub(r"\s+", " ", tok.strip().upper())


def to_abbr(tok: str) -> str:
    t = norm(tok)
    return ALIASES.get(t, t.replace(" ", ""))


def parse_line(line: str):
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    parts = re.split(r"\s+(?:vs\.?|VS\.?|@|at|AT)\s+", line)
    if len(parts) != 2:
        raise ValueError("cannot split into two teams: %r" % line)
    return norm(parts[0]), norm(parts[1])


def find(games: list, a_raw: str, b_raw: str):
    """Match one shorthand pair against the real slate."""
    a, b = to_abbr(a_raw), to_abbr(b_raw)

    def resolve_ambiguous(tok, other):
        return AMBIGUOUS.get(tok, {}).get(other, tok)

    a = resolve_ambiguous(a, b)
    b = resolve_ambiguous(b, a)

    hits = [g for g in games
            if {g["home"]["abbr"], g["away"]["abbr"]} == {a, b}]
    if len(hits) == 1:
        return hits[0], None
    if len(hits) > 1:
        return None, "ambiguous: %d games match %s/%s" % (len(hits), a, b)

    # Second pass: match on school name, which survives abbreviation drift.
    def looks_like(team, tok):
        blob = "%s %s" % (team.get("school") or "", team.get("name") or "")
        return tok.replace(" ", "").lower() in blob.replace(" ", "").lower()

    loose = [g for g in games
             if (looks_like(g["away"], a_raw) and looks_like(g["home"], b_raw))
             or (looks_like(g["home"], a_raw) and looks_like(g["away"], b_raw))]
    if len(loose) == 1:
        return loose[0], None
    return None, "no match for %s (%s) vs %s (%s)" % (a_raw, a, b_raw, b)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--slate", required=True)
    p.add_argument("--games", required=True)
    p.add_argument("--out", default=None)
    p.add_argument("--expect", type=int, default=20)
    a = p.parse_args()

    games = json.load(open(a.games, encoding="utf-8"))["games"]
    raw = open(a.slate, encoding="utf-8").read().splitlines()

    resolved, errors = [], []
    for line in raw:
        pair = parse_line(line)
        if pair is None:
            continue
        try:
            g, err = find(games, *pair)
        except ValueError as e:
            errors.append(str(e))
            continue
        if err:
            errors.append("%-22s %s" % (line.strip(), err))
        else:
            resolved.append({"raw": line.strip(), "espn_id": g["espn_id"],
                             "short_name": g["short_name"], "name": g["name"],
                             "kickoff_utc": g["kickoff_utc"],
                             "odds": g["odds"], "tv": g.get("tv"),
                             "home": g["home"]["abbr"], "away": g["away"]["abbr"],
                             "interest": g.get("interest")})

    print("resolved %d of %d lines" % (len(resolved), len([l for l in raw if l.strip()])))
    for r in sorted(resolved, key=lambda x: x["kickoff_utc"]):
        od = r["odds"]["details"] or "no line"
        print("  %-18s -> %-16s %s ET  %-12s %s" % (
            r["raw"], r["short_name"], et(r["kickoff_utc"]).strftime("%a %m/%d %I:%M%p"),
            od, r.get("tv") or ""))

    if errors:
        print("\nUNRESOLVED (%d):" % len(errors), file=sys.stderr)
        for e in errors:
            print("  " + e, file=sys.stderr)

    ids = [r["espn_id"] for r in resolved]
    if len(set(ids)) != len(ids):
        print("\nFAIL: duplicate games in slate", file=sys.stderr)
        return 1
    if len(resolved) != a.expect:
        print("\nFAIL: expected %d games, resolved %d" % (a.expect, len(resolved)),
              file=sys.stderr)
        return 1

    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            json.dump({"count": len(resolved), "games": resolved}, f, indent=1)
        print("\nwrote %s" % a.out)
    print("\nOK: all %d games resolved, no duplicates" % len(resolved))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
