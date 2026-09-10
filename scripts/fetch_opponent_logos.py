"""Vendor a logo for every team that can appear in the pool, not just the FBS 138.

    python scripts/fetch_opponent_logos.py --check     # report, download nothing
    python scripts/fetch_opponent_logos.py             # pull what is missing, from the DB
    python scripts/fetch_opponent_logos.py --games tests/fixtures/slate_week01.json

`fetch_teams.py` builds the 138-team FBS library and vendors those logos. That is the
right set for the TEAM PICKER, where you choose a profile picture, and the wrong set for
the SETUP SCREEN, which lists every FBS game in the window. About a third of week 2 is
an FBS side hosting an FCS side, and the visitor is in none of ESPN's FBS groups, so
`<TeamLogo>` fell back to a four-letter chip for 42 teams: Alabama State, Villanova,
Montana, Wofford and so on. Grant noticed on 2026-09-10 that "some aren't [showing] on
the full setup page". That is what this fixes.

Only the light cut is pulled. `<TeamLogo>` always asks for `<id>.png`; the `-dark`
variant exists solely for `<Avatar>`, which can only ever render a team from the library,
so an opponent never needs one. 42 more marks is about 1.9MB, against 28MB for all 622
non-FBS teams ESPN carries, which is why this is driven by what is actually in a pool
rather than by downloading the world.

Two sources of ids, because the two callers want different things:

  --from-db (default)  every team on a `games` row, which is exactly what the setup
                       screen can render. Needs SUPABASE_SERVICE_KEY, so it is a
                       maintenance command rather than part of the test gate.
  --games FILE...      a saved ESPN window pull. Offline, and what tests use.

`sync_supabase.py --mode slate` calls ensure_logos() itself, so a week built the normal
way vendors its own opponents and this script is only needed to backfill.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO_DIR = os.path.join(ROOT, "static", "logos")
LOGO_URL = "https://a.espncdn.com/i/teamlogos/ncaa/500/%s.png"

# Never set a browser-like User-Agent on an ESPN call. Grant's egress proxy 403s those
# while letting the urllib default through. See CLAUDE.md.


def id_from_logo(url: str | None) -> str | None:
    """ESPN files every mark as .../teamlogos/ncaa/500/<team_id>.png."""
    m = re.search(r"/(\d+)\.png", url or "")
    return m.group(1) if m else None


def have(team_id: str) -> bool:
    path = os.path.join(LOGO_DIR, "%s.png" % team_id)
    return os.path.exists(path) and os.path.getsize(path) > 0


def ensure_logos(pairs, quiet: bool = False) -> tuple[int, list]:
    """Download the light mark for any (team_id, abbr) that has none.

    Returns (pulled, failed). A failure is reported and never raised: a missing mark
    degrades to the abbreviation chip, which is ugly but not broken, and a network blip
    must not take a slate build down with it.
    """
    os.makedirs(LOGO_DIR, exist_ok=True)
    want = sorted({(str(t), a) for t, a in pairs if t and not have(str(t))})
    pulled, failed = 0, []
    for tid, abbr in want:
        try:
            with urllib.request.urlopen(LOGO_URL % tid, timeout=30) as r:
                data = r.read()
            if not data:
                raise ValueError("empty response")
            with open(os.path.join(LOGO_DIR, "%s.png" % tid), "wb") as f:
                f.write(data)
            pulled += 1
            if not quiet:
                print("  pulled %-6s %s (%.0f KB)" % (abbr or "?", tid, len(data) / 1024))
        except Exception as exc:                                        # noqa: BLE001
            failed.append((tid, abbr, str(exc)))
            print("  FAILED %-6s %s (%s)" % (abbr or "?", tid, exc), file=sys.stderr)
    return pulled, failed


def from_games_files(paths: list) -> list:
    """(id, abbr) for both sides of every game in a saved ESPN window pull."""
    pairs = []
    for p in paths:
        with open(p, encoding="utf-8") as f:
            payload = json.load(f)
        games = payload["games"] if isinstance(payload, dict) else payload
        for g in games:
            for side in ("home", "away"):
                t = g.get(side) or {}
                pairs.append((id_from_logo(t.get("logo")), t.get("abbr")))
    return pairs


def from_db() -> list:
    """(id, abbr) for both sides of every game row in Supabase."""
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    from sync_supabase import env, load_dotenv

    load_dotenv(os.path.join(ROOT, ".env"))
    url, key = env("SUPABASE_URL"), env("SUPABASE_SERVICE_KEY")
    req = urllib.request.Request(
        url.rstrip("/") + "/rest/v1/games?select=home_id,home_abbr,away_id,away_abbr",
        headers={"apikey": key, "Authorization": "Bearer " + key},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        rows = json.load(r)
    return [(g[s + "_id"], g[s + "_abbr"]) for g in rows for s in ("home", "away")]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true", help="report only, download nothing")
    p.add_argument("--games", nargs="+", metavar="FILE",
                   help="saved ESPN window pull(s) to read ids from, instead of the DB")
    a = p.parse_args()

    pairs = from_games_files(a.games) if a.games else from_db()
    known = {str(t) for t, _ in pairs if t}
    missing = sorted({(str(t), a2) for t, a2 in pairs if t and not have(str(t))})
    print("%d teams can appear in a pool, %d already vendored, %d missing"
          % (len(known), len(known) - len(missing), len(missing)))

    if a.check:
        for tid, abbr in missing:
            print("  missing %-6s %s" % (abbr or "?", tid))
        if missing:
            print("\nFAIL: %d team(s) would render as a chip. Run without --check."
                  % len(missing), file=sys.stderr)
            return 1
        print("OK")
        return 0

    pulled, failed = ensure_logos(missing)
    print("\npulled %d, %d failed" % (pulled, len(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
