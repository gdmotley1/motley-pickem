"""Build the FBS team library: ids, names, abbreviations, colors, conferences, logos.

Two ESPN sources are joined because neither alone is enough:

  1. site API `/teams?limit=900` returns all 760 NCAA teams with logos and colors,
     but has no conference field and cannot be filtered to FBS (`groups` is ignored).
  2. core API `/groups/80/children` lists the 11 FBS conferences, and each conference's
     `/teams` gives the team ids in it.

Joining them yields FBS-only teams tagged with conference. Logo URLs follow the pattern
`a.espncdn.com/i/teamlogos/ncaa/500/<team_id>.png`, with a `500-dark` variant.

Usage:
    python scripts/fetch_teams.py --out inputs/fbs_teams.json
    python scripts/fetch_teams.py --out inputs/fbs_teams.json --download static/logos
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request

from fetch_slate import _get

ALL_TEAMS = ("https://site.api.espn.com/apis/site/v2/sports/football/"
             "college-football/teams?limit=900")
CORE = "https://sports.core.api.espn.com/v2/sports/football/leagues/college-football"
LOGO = "https://a.espncdn.com/i/teamlogos/ncaa/500/%s.png"
LOGO_DARK = "https://a.espncdn.com/i/teamlogos/ncaa/500-dark/%s.png"

CONFERENCE_NAMES = {
    1: "ACC", 4: "Big 12", 5: "Big Ten", 8: "SEC", 9: "Pac-12",
    12: "Conference USA", 15: "MAC", 17: "Mountain West",
    18: "FBS Independents", 37: "Sun Belt", 151: "American",
}


def all_teams() -> dict:
    """Every NCAA team the site API knows, keyed by team id."""
    payload = _get(ALL_TEAMS)
    out = {}
    for entry in payload["sports"][0]["leagues"][0].get("teams", []):
        t = entry.get("team") or {}
        tid = str(t.get("id"))
        logos = t.get("logos") or []

        def pick(rel):
            for L in logos:
                if rel in (L.get("rel") or []):
                    return L.get("href")
            return None

        out[tid] = {
            "id": tid,
            "abbr": t.get("abbreviation"),
            "school": t.get("location"),
            "mascot": t.get("name"),
            "display": t.get("displayName"),
            "short": t.get("shortDisplayName"),
            "slug": t.get("slug"),
            "color": "#" + (t.get("color") or "222222"),
            "alt_color": "#" + (t.get("alternateColor") or "eeeeee"),
            "logo": pick("default") or (LOGO % tid),
            "logo_dark": pick("dark") or (LOGO_DARK % tid),
        }
    return out


def fbs_conference_members() -> dict:
    """team id -> conference id, for the 11 FBS conferences."""
    kids = _get("%s/seasons/2026/types/2/groups/80/children?limit=50" % CORE)
    members = {}
    for item in kids.get("items", []):
        ref = item.get("$ref", "")
        m = re.search(r"/groups/(\d+)", ref)
        if not m:
            continue
        conf_id = int(m.group(1))
        url = ref.replace("http://", "https://").split("?")[0] + "/teams?limit=50"
        try:
            teams = _get(url)
        except RuntimeError as e:
            print("WARNING: conference %s teams unavailable (%s)" % (conf_id, e),
                  file=sys.stderr)
            continue
        for t in teams.get("items", []):
            tm = re.search(r"/teams/(\d+)", t.get("$ref", ""))
            if tm:
                members[tm.group(1)] = conf_id
    return members


def download_logos(teams: list, dest: str) -> int:
    os.makedirs(dest, exist_ok=True)
    saved = 0
    for t in teams:
        for key, suffix in (("logo", ""), ("logo_dark", "-dark")):
            url = t.get(key)
            if not url:
                continue
            path = os.path.join(dest, "%s%s.png" % (t["id"], suffix))
            if os.path.exists(path) and os.path.getsize(path) > 0:
                saved += 1
                continue
            try:
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=30) as r:
                    data = r.read()
                if data:
                    with open(path, "wb") as f:
                        f.write(data)
                    saved += 1
            except Exception as e:                      # noqa: BLE001
                print("  logo failed %s (%s)" % (t["abbr"], e), file=sys.stderr)
    return saved


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="inputs/fbs_teams.json")
    p.add_argument("--download", default=None, help="directory to save logo PNGs into")
    a = p.parse_args()

    everything = all_teams()
    members = fbs_conference_members()
    print("site API: %d teams | core API: %d FBS members across %d conferences"
          % (len(everything), len(members), len(set(members.values()))))

    teams = []
    for tid, conf_id in members.items():
        t = everything.get(tid)
        if not t:
            print("  WARNING: FBS team id %s missing from site API" % tid, file=sys.stderr)
            continue
        t = dict(t)
        t["conference_id"] = conf_id
        t["conference"] = CONFERENCE_NAMES.get(conf_id, str(conf_id))
        teams.append(t)
    teams.sort(key=lambda t: (t["conference"], t["school"] or ""))

    by_conf = {}
    for t in teams:
        by_conf[t["conference"]] = by_conf.get(t["conference"], 0) + 1
    print("\nFBS teams by conference:")
    for c in sorted(by_conf):
        print("  %-18s %3d" % (c, by_conf[c]))
    print("  %-18s %3d" % ("TOTAL", len(teams)))

    missing = [t["abbr"] for t in teams if not t.get("logo")]
    if missing:
        print("\nFAIL: %d teams without a logo: %s" % (len(missing), missing[:10]),
              file=sys.stderr)
        return 1

    with open(a.out, "w", encoding="utf-8") as f:
        json.dump({"count": len(teams), "teams": teams}, f, indent=1)
    print("\nwrote %s" % a.out)

    if a.download:
        n = download_logos(teams, a.download)
        print("logos on disk: %d of %d expected" % (n, len(teams) * 2))
        if n < len(teams) * 2:
            print("FAIL: some logos missing", file=sys.stderr)
            return 1

    if len(teams) < 130:
        print("\nFAIL: only %d FBS teams, expected ~134" % len(teams), file=sys.stderr)
        return 1
    print("\nOK: %d FBS teams with logos" % len(teams))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
