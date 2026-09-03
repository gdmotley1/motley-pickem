"""Turn a generated pool into the exact shape the app receives from get_slate().

Lets the whole UI be built and demoed before the database exists, and keeps the mock
honest: if the RPC's column list changes, this is the one place to change with it.

Usage:
    python scripts/build_mock_data.py --pool outputs/week01_pool.json \
        --out static/data/week01.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request


def team_id_from_logo(team: dict):
    """ESPN files every logo as .../teamlogos/ncaa/500/<team_id>.png.

    The scoreboard payload has no team id field, but it does carry the logo href, so the
    id can be read straight out of it. This is the only way to identify FCS opponents,
    which are absent from the FBS team library but do appear on Dad's slates.
    """
    m = re.search(r"/(\d+)\.png", team.get("logo") or "")
    return m.group(1) if m else None


def row(g: dict) -> dict:
    """One game in get_slate() column order. my_* are filled in by the mock at runtime."""
    o = g.get("odds") or {}
    return {
        "game_id": int(g["espn_id"]),
        "kickoff": g["kickoff_utc"],
        "home_id": team_id_from_logo(g["home"]),
        "home_abbr": g["home"]["abbr"],
        "home_school": g["home"].get("school"),
        "home_logo": g["home"].get("logo"),
        "home_rank": None if g["home"].get("rank", 99) >= 99 else g["home"]["rank"],
        "home_record": g["home"].get("record"),
        "home_color": g["home"].get("color"),
        "home_score": g["home"].get("score"),
        "away_id": team_id_from_logo(g["away"]),
        "away_abbr": g["away"]["abbr"],
        "away_school": g["away"].get("school"),
        "away_logo": g["away"].get("logo"),
        "away_rank": None if g["away"].get("rank", 99) >= 99 else g["away"]["rank"],
        "away_record": g["away"].get("record"),
        "away_color": g["away"].get("color"),
        "away_score": g["away"].get("score"),
        "neutral_site": bool(g.get("neutral_site")),
        "tv": g.get("tv"),
        "spread_line": o.get("line"),
        "favorite_abbr": o.get("favorite"),
        "underdog_abbr": o.get("underdog"),
        "tier": g.get("tier"),
        "interest": g.get("interest"),
        "featured": bool(g.get("featured")),
        "state": g.get("state") or "pre",
        "status_detail": g.get("status_detail"),
        "winner_abbr": g.get("winner"),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--pool", default="outputs/week01_pool.json")
    p.add_argument("--out", default="static/data/week01.json")
    p.add_argument("--teams", default="inputs/fbs_teams.json")
    a = p.parse_args()

    with open(a.pool, encoding="utf-8") as f:
        pool = json.load(f)

    # ESPN team ids are not on the scoreboard payload, so map them from the team library
    # by abbreviation. Logos are filed by id, and a missing id means a missing logo.
    ids = {}
    if os.path.exists(a.teams):
        with open(a.teams, encoding="utf-8") as f:
            for t in json.load(f)["teams"]:
                ids[t["abbr"]] = t["id"]

    def fill(g):
        r = row(g)
        r["home_id"] = r["home_id"] or ids.get(r["home_abbr"])
        r["away_id"] = r["away_id"] or ids.get(r["away_abbr"])
        return r

    slate = [fill(g) for g in pool["slate"]]
    alternates = [fill(g) for g in pool["alternates"]]

    missing = [r["home_abbr"] if not r["home_id"] else r["away_abbr"]
               for r in slate if not r["home_id"] or not r["away_id"]]
    if missing:
        print("FAIL: no ESPN team id for: %s" % sorted(set(missing)), file=sys.stderr)
        return 1

    # Anything not already vendored (FCS opponents, mostly) gets pulled down now so the
    # app never hotlinks ESPN at pick time.
    need = []
    for r in slate + alternates:
        for side in ("home", "away"):
            tid, url = r["%s_id" % side], r["%s_logo" % side]
            if tid and url and not os.path.exists("static/logos/%s.png" % tid):
                need.append((tid, url))
    for tid, url in sorted(set(need)):
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = resp.read()
            with open("static/logos/%s.png" % tid, "wb") as fh:
                fh.write(data)
            print("  pulled missing logo %s" % tid)
        except Exception as exc:  # noqa: BLE001
            print("  could not pull logo %s (%s)" % (tid, exc), file=sys.stderr)

    wk = pool.get("week") or {}
    payload = {
        "week": {"id": 1, "season": 2026,
                 "week_no": wk.get("week"),
                 "label": wk.get("label") or "This week",
                 "published": True},
        "slate": slate,
        "alternates": alternates,
    }
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1)

    with_logo = sum(1 for r in slate if r["home_id"] and r["away_id"])
    print("wrote %s: %d slate, %d alternates, %d/%d slate games with both logos"
          % (a.out, len(slate), len(alternates), with_logo, len(slate)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
