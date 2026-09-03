"""The college football week calendar.

Runs against a saved copy of ESPN's published calendar, so it is deterministic and works
offline. Refresh with: python scripts/cfb_weeks.py --refresh
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import cfb_weeks  # noqa: E402

FIXTURE = os.path.join(ROOT, "tests", "fixtures", "cfb_calendar_2026.json")


@pytest.fixture(scope="module")
def weeks():
    with open(FIXTURE, encoding="utf-8") as f:
        return json.load(f)["weeks"]


def utc(s):
    return dt.datetime.fromisoformat(s).replace(tzinfo=dt.timezone.utc)


def test_a_full_regular_season(weeks):
    assert 14 <= len(weeks) <= 16, "got %d weeks" % len(weeks)
    assert [w["week"] for w in weeks] == list(range(1, len(weeks) + 1))


def test_weeks_abut_with_espns_one_minute_boundary(weeks):
    """ESPN ends a week at HH:59 and opens the next at HH+1:00, so there is a 60s hole."""
    for a, b in zip(weeks, weeks[1:]):
        gap = (cfb_weeks._parse(b["start"]) - cfb_weeks._parse(a["end"])).total_seconds()
        assert gap == 60, "gap of %ss between %s and %s" % (gap, a["label"], b["label"])


def test_the_minute_long_boundary_hole_snaps_to_the_next_week(weeks):
    """A lookup inside that hole must not come back empty."""
    for a, b in zip(weeks, weeks[1:]):
        inside = cfb_weeks._parse(a["end"]) + dt.timedelta(seconds=30)
        w = cfb_weeks.week_for(inside, weeks)
        assert w is not None, "no week for the boundary after %s" % a["label"]
        assert w["week"] == b["week"]


def test_every_instant_in_the_season_lands_in_exactly_one_week(weeks):
    cursor = cfb_weeks._parse(weeks[0]["start"])
    last = cfb_weeks._parse(weeks[-1]["end"])
    while cursor < last:
        hits = [w for w in weeks
                if cfb_weeks._parse(w["start"]) <= cursor <= cfb_weeks._parse(w["end"])]
        assert len(hits) == 1, "%s matched %d weeks" % (cursor, len(hits))
        assert cfb_weeks.week_for(cursor, weeks) == hits[0]
        cursor += dt.timedelta(hours=6)


# --------------------------------------------------------------- the real cutoffs

def test_the_slate_grant_gave_us_is_week_one_not_week_two(weeks):
    """The app hard-coded 'Week 2' and was wrong: ESPN's Week 1 absorbs Week 0."""
    w = cfb_weeks.week_for(utc("2026-09-05T19:30:00"), weeks)
    assert w and w["week"] == 1, "got %s" % (w and w["label"])


def test_a_thursday_night_game_belongs_to_the_week_that_opened_that_monday(weeks):
    thursday = utc("2026-09-17T23:30:00")           # Thu of Week 3
    w = cfb_weeks.week_for(thursday, weeks)
    assert w["week"] == 3
    assert cfb_weeks._parse(w["start"]).weekday() == 0, "week should open on a Monday"
    assert cfb_weeks._parse(w["start"]) < thursday


def test_a_late_sunday_game_stays_in_the_week_that_is_ending(weeks):
    """Boundaries land ~3am ET Monday, after Sunday night football finishes."""
    sunday_night = utc("2026-09-14T02:00:00")        # 10pm ET Sunday
    w = cfb_weeks.week_for(sunday_night, weeks)
    assert w["week"] == 2, "got %s" % w["label"]


def test_the_boundary_shifts_when_daylight_saving_ends(weeks):
    """Weeks 1-9 end at 06:59Z, later ones at 07:59Z. A fixed offset would drift."""
    ends = {w["week"]: cfb_weeks._parse(w["end"]).hour for w in weeks}
    assert ends[3] != ends[len(weeks)], "expected a DST shift in the boundary hour"


# --------------------------------------------------------------- query ranges

def test_a_normal_week_is_not_clamped(weeks):
    w = cfb_weeks.week_by_number(weeks, 5)
    start, end = cfb_weeks.date_range(w)
    assert (end - start).days + 1 <= cfb_weeks.LONG_WEEK_DAYS


def test_the_seventeen_day_week_one_is_clamped_to_one_weekend(weeks):
    w = cfb_weeks.week_by_number(weeks, 1)
    raw = (cfb_weeks._parse(w["end"]).date() - cfb_weeks._parse(w["start"]).date()).days
    assert raw > 14, "Week 1 of 2026 should be the long one"
    start, end = cfb_weeks.date_range(w)
    assert (end - start).days + 1 == cfb_weeks.LONG_WEEK_DAYS


def test_the_clamped_week_one_still_covers_every_game_dad_picked(weeks):
    path = os.path.join(ROOT, "inputs", "week01_resolved.json")
    if not os.path.exists(path):
        pytest.skip("dad's resolved slate not built")
    with open(path, encoding="utf-8") as f:
        games = json.load(f)["games"]
    start, end = cfb_weeks.date_range(cfb_weeks.week_by_number(weeks, 1))
    for g in games:
        d = cfb_weeks._parse(g["kickoff_utc"]).date()
        assert start <= d <= end, "%s on %s falls outside %s..%s" % (
            g["short_name"], d, start, end)
