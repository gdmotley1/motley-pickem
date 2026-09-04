#!/usr/bin/env python3
"""Create a row for every regular season week, empty, ahead of the games.

The season's shape is known in August; its contents are not. Which twenty games are worth
picking in week 9 depends on records that do not exist yet, so the pool for a week is
built the week of, by `sync_supabase.py --mode slate`. What this script does is make the
weeks themselves exist up front, so a week is never missing when something goes looking
for it.

That matters because the slate cron is not reliable. The `0 12 * * 2,3,4` schedule in
.github/workflows/sync.yml had not fired once as of 2026-09-04: every scheduled run in
the history was a `*/15` score refresh, and week 2 did not exist four days before week 1
was due to end. A row per week means the calendar is settled once, from ESPN, rather than
depending on a job firing on the right morning.

An empty week is harmless everywhere it is visible. `get_slate` joins on `weeks.published`
and returns nothing, so the Board shows its "Nothing published" state. `maybe_publish`
refuses to publish anything that is not exactly twenty games, so a week with none can
never auto-publish. Nothing is shown to a player until a slate is built and published.

Boundaries come from ESPN's published calendar, never arithmetic: week 1 of 2026 is
seventeen days because it absorbs week 0, and the boundary hour shifts when daylight
saving ends. See scripts/cfb_weeks.py.

    python scripts/seed_weeks.py --dry-run     # show what would change
    python scripts/seed_weeks.py               # create the season

Safe to re-run. Re-running refreshes each week's label and boundaries from ESPN and
touches nothing else: `ensure_week` omits `published` from the payload, so a week the
commissioner has already published stays published, and no games are ever touched.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cfb_weeks import fetch_calendar  # noqa: E402
from sync_supabase import Supabase, ensure_week, env, load_dotenv  # noqa: E402


def main() -> int:
    load_dotenv()
    p = argparse.ArgumentParser()
    p.add_argument("--season", type=int, default=2026)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()

    calendar = fetch_calendar(a.season)
    if not calendar:
        print("ESPN returned no calendar for %d" % a.season, file=sys.stderr)
        return 1

    print("%d regular season weeks, %s to %s"
          % (len(calendar), calendar[0]["start"][:10], calendar[-1]["end"][:10]))

    if a.dry_run:
        for w in calendar:
            print("  [dry run] week %-2s %-8s %s -> %s"
                  % (w["week"], w["label"], w["start"][:10], w["end"][:10]))
        return 0

    sb = Supabase(env("SUPABASE_URL"), env("SUPABASE_SERVICE_KEY"))

    made = kept = 0
    for w in calendar:
        before = sb.select("weeks", "season=eq.%d&week_no=eq.%d&select=id"
                           % (a.season, w["week"]))
        row = ensure_week(sb, a.season, w)
        if before:
            kept += 1
        else:
            made += 1
        games = sb.select("games", "week_id=eq.%s&in_slate=is.true&select=id" % row["id"])
        print("  id=%-3s %-8s published=%-5s slate=%2d  %s"
              % (row["id"], row["label"], row["published"], len(games),
                 "existing" if before else "created"))

    print("%d created, %d already there" % (made, kept))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
