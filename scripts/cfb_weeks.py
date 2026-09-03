"""The real college football week calendar, straight from ESPN.

Week boundaries are not "Monday to Sunday". ESPN publishes the official ones and they
have genuine oddities that a hand-rolled calendar gets wrong:

  * Week 1 of 2026 runs 22 Aug to 8 Sep, seventeen days, because it absorbs Week 0.
  * Every boundary lands about 3am ET on a Monday, which is AFTER Sunday night games,
    so a late Sunday game belongs to the week that started six days earlier.
  * The boundary shifts an hour in November when daylight saving ends.

A Thursday game therefore belongs to the week that opened on the previous Monday, which
is the behaviour Grant asked for.

Usage:
    python scripts/cfb_weeks.py                       # show the season
    python scripts/cfb_weeks.py --for 2026-09-05      # which week is this date
    python scripts/cfb_weeks.py --current             # week in progress right now
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

from fetch_slate import _get

SEASON_URL = ("https://site.api.espn.com/apis/site/v2/sports/football/"
              "college-football/scoreboard?dates=%d")
CACHE = "inputs/cfb_calendar_%d.json"
REGULAR_SEASON = "Regular Season"


def _parse(iso: str) -> dt.datetime:
    return dt.datetime.fromisoformat(iso.replace("Z", "+00:00"))


def fetch_calendar(season: int, use_cache: bool = True) -> list:
    """[{week, label, start, end}] for the regular season, in order."""
    path = CACHE % season
    if use_cache and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            cached = json.load(f)
        if cached.get("weeks"):
            return cached["weeks"]

    payload = _get(SEASON_URL % season)
    groups = payload["leagues"][0].get("calendar") or []
    regular = next((g for g in groups if g.get("label") == REGULAR_SEASON), None)
    if not regular:
        raise RuntimeError("ESPN returned no regular-season calendar for %d" % season)

    weeks = []
    for entry in regular.get("entries", []):
        weeks.append({
            "week": int(entry["value"]),
            "label": entry.get("label") or ("Week %s" % entry["value"]),
            "start": entry["startDate"],
            "end": entry["endDate"],
        })
    weeks.sort(key=lambda w: w["week"])

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"season": season,
                   "fetched_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                   "weeks": weeks}, f, indent=1)
    return weeks


def week_for(when: dt.datetime, weeks: list):
    """The week containing an instant, or None if it falls outside the season.

    ESPN ends a week at HH:59 and opens the next at HH+1:00, leaving a 60 second hole
    every Monday morning. An instant inside that hole belongs to the week about to
    start, so the gap is snapped forward rather than returning nothing.
    """
    if when.tzinfo is None:
        when = when.replace(tzinfo=dt.timezone.utc)
    for w in weeks:
        if _parse(w["start"]) <= when <= _parse(w["end"]):
            return w
    upcoming = [w for w in weeks if _parse(w["start"]) > when]
    if upcoming and weeks and _parse(weeks[0]["start"]) <= when:
        return min(upcoming, key=lambda w: _parse(w["start"]))
    return None


def current_week(weeks: list, now: dt.datetime | None = None):
    return week_for(now or dt.datetime.now(dt.timezone.utc), weeks)


def next_week(weeks: list, now: dt.datetime | None = None):
    """The next week that has not started yet. Used to build a slate in advance."""
    now = now or dt.datetime.now(dt.timezone.utc)
    upcoming = [w for w in weeks if _parse(w["start"]) > now]
    return upcoming[0] if upcoming else None


def week_by_number(weeks: list, number: int):
    return next((w for w in weeks if w["week"] == number), None)


# A normal week spans eight calendar dates (Monday to Monday). Anything much longer is
# ESPN folding an extra weekend in, as Week 1 does with Week 0.
LONG_WEEK_DAYS = 9


def date_range(week: dict, max_days: int = LONG_WEEK_DAYS) -> tuple:
    """Inclusive UTC dates to query the scoreboard with, one call per day.

    The end is nudged back a second first: a week ends at 06:59Z, which is still the
    previous evening in the US and must not pull in an extra day of games.

    Long windows are clamped to their trailing days. Week 1 of 2026 runs 22 Aug to
    8 Sep and contains two separate weekends; pulling all of it would mix games from
    different Saturdays into one pool. A pick'em week is one weekend.
    """
    start = _parse(week["start"]).date()
    end = (_parse(week["end"]) - dt.timedelta(seconds=1)).date()
    span = (end - start).days + 1
    if span > max_days:
        start = end - dt.timedelta(days=max_days - 1)
    return start, end


def et(when: dt.datetime) -> dt.datetime:
    offset = 4 if 3 < when.month < 11 else 5
    return when - dt.timedelta(hours=offset)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--season", type=int, default=2026)
    p.add_argument("--for", dest="on", default=None, help="date, e.g. 2026-09-05")
    p.add_argument("--current", action="store_true")
    p.add_argument("--next", action="store_true")
    p.add_argument("--refresh", action="store_true", help="ignore the cached calendar")
    a = p.parse_args()

    weeks = fetch_calendar(a.season, use_cache=not a.refresh)

    def show(w):
        s, e = date_range(w)
        print("%-9s %s ET -> %s ET   (scoreboard days %s .. %s)" % (
            w["label"],
            et(_parse(w["start"])).strftime("%a %m/%d %I:%M%p"),
            et(_parse(w["end"])).strftime("%a %m/%d %I:%M%p"),
            s, e))

    if a.on:
        when = dt.datetime.fromisoformat(a.on).replace(tzinfo=dt.timezone.utc)
        w = week_for(when, weeks)
        if not w:
            print("%s is outside the regular season" % a.on, file=sys.stderr)
            return 1
        print("%s falls in:" % a.on)
        show(w)
        return 0

    if a.current or a.next:
        w = current_week(weeks) if a.current else next_week(weeks)
        if not w:
            print("no %s week" % ("current" if a.current else "next"), file=sys.stderr)
            return 1
        show(w)
        return 0

    print("%d regular season: %d weeks" % (a.season, len(weeks)))
    for w in weeks:
        show(w)
    if len(weeks) < 12:
        print("\nFAIL: only %d weeks, expected 14 or 15" % len(weeks), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
