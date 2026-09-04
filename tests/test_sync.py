"""The weekly sync job's decision logic, without touching the network or the database."""
from __future__ import annotations

import datetime as dt
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import sync_supabase as sync  # noqa: E402


class FakeSB:
    """Records whether the job tried to publish, without a database."""

    def __init__(self, hours_to_kickoff=None, games=20):
        self.hours = hours_to_kickoff
        self.games = games
        self.published = False

    def select(self, table, query=""):
        when = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=self.hours)
        return [{"kickoff": when.isoformat()}] * self.games

    def _request(self, method, path, body=None, prefer=""):
        if method == "PATCH" and "weeks" in path and body.get("published"):
            self.published = True
        return None


def run(hours, games=20, already=False):
    sb = FakeSB(hours, games)
    sync.maybe_publish(sb, {"id": 1, "published": already})
    return sb.published


def test_a_week_far_from_kickoff_is_left_for_the_commissioner():
    assert run(72) is False
    assert run(sync.FALLBACK_PUBLISH_HOURS + 1) is False


def test_an_unpublished_week_near_kickoff_is_published_automatically():
    """Otherwise a busy commissioner means nobody in the family can pick at all."""
    assert run(sync.FALLBACK_PUBLISH_HOURS - 1) is True
    assert run(2) is True


def test_a_published_week_is_never_touched():
    """The commissioner's choices outrank the fallback, always."""
    assert run(2, already=True) is False
    assert run(72, already=True) is False


def test_an_incomplete_slate_is_never_published():
    for n in (0, 17, 19, 21):
        assert run(2, games=n) is False, "published a slate of %d" % n


@pytest.mark.parametrize("mode", ["slate", "scores"])
def test_both_modes_are_wired(mode):
    assert hasattr(sync, "sync_%s" % mode)


# ------------------------------------------------------------------- odds freeze

# ESPN drops the odds block the moment a game goes final. Verified on 2026-09-04: every
# completed game from 3 Sep returned details: null and overUnder: null, while every game
# still in `pre` carried both. The scores job upserts whatever ESPN last said, so a final
# was overwriting the stored line with nothing. COLO @ GT was found in the database with
# spread_line null and favorite_abbr null, having gone in at GT -6.5.


def a_game_row(state, line=6.5, total=51.5):
    return {
        "id": 401856776,
        "state": state,
        "home_score": 20,
        "spread_line": line,
        "favorite_abbr": "GT",
        "underdog_abbr": "COLO",
        "over_under": total,
    }


@pytest.mark.parametrize("state", [None, "pre"])
def test_odds_still_move_while_a_game_has_not_kicked_off(state):
    kept = sync.freeze_odds(a_game_row(state), state)
    assert kept["spread_line"] == 6.5
    assert kept["over_under"] == 51.5
    assert kept["favorite_abbr"] == "GT"


@pytest.mark.parametrize("state", ["in", "post"])
def test_a_kicked_off_game_never_has_its_odds_rewritten(state):
    """The whole point: ESPN's post-game nulls must not reach the database."""
    frozen = sync.freeze_odds(a_game_row(state, line=None, total=None), state)
    for column in sync.ODDS_COLUMNS:
        assert column not in frozen, "%s would overwrite the stored value" % column


def test_freezing_leaves_the_score_alone():
    frozen = sync.freeze_odds(a_game_row("post"), "post")
    assert frozen["home_score"] == 20
    assert frozen["state"] == "post"
    assert frozen["id"] == 401856776


def test_every_odds_column_the_row_builder_writes_is_frozen_together():
    """A new odds column added to game_row but not to ODDS_COLUMNS would leak through.

    Sentinel values that cannot appear anywhere else in the row, so the check finds the
    columns fed by the odds block rather than anything that merely looks like a team.
    """
    marks = {99.5, 88.5, "ZZFAV", "ZZDOG"}
    row = sync.game_row(
        {
            "espn_id": "1",
            "home": {"abbr": "GT"},
            "away": {"abbr": "COLO"},
            "kickoff_utc": "2026-09-04T00:00:00Z",
            "odds": {
                "line": 99.5,
                "favorite": "ZZFAV",
                "underdog": "ZZDOG",
                "over_under": 88.5,
            },
        },
        1,
        None,
    )
    from_odds = {k for k, v in row.items() if v in marks}
    assert from_odds == set(sync.ODDS_COLUMNS), (
        "game_row and ODDS_COLUMNS disagree; unfrozen: %s"
        % sorted(from_odds - set(sync.ODDS_COLUMNS))
    )


# --------------------------------------------------------------- seeding weeks

# scripts/seed_weeks.py creates a row for all fifteen regular season weeks up front and
# is safe to re-run. The property that makes it safe is that ensure_week never sends
# `published`: re-seeding must not unpublish a week the commissioner has already put in
# front of the family, and week 1 was live with twenty games when this was first run.


class RecordingSB:
    """Captures upsert payloads instead of talking to PostgREST."""

    def __init__(self, existing=None):
        self.existing = existing or []
        self.upserts = []

    def select(self, table, query=""):
        return self.existing

    def upsert(self, table, rows, on_conflict):
        self.upserts.append({"table": table, "rows": rows, "on_conflict": on_conflict})
        return rows


A_WEEK = {
    "week": 1,
    "label": "Week 1",
    "start": "2026-08-22T07:00:00Z",
    "end": "2026-09-08T06:59:00Z",
}


def test_reseeding_never_unpublishes_a_live_week():
    sb = RecordingSB(existing=[{"id": 1, "published": True}])
    sync.ensure_week(sb, 2026, A_WEEK)
    sent = sb.upserts[0]["rows"][0]
    assert "published" not in sent, "re-seeding would hide a published week from the family"
    assert "published_at" not in sent


def test_reseeding_updates_the_existing_row_rather_than_adding_one():
    sb = RecordingSB(existing=[{"id": 7, "published": False}])
    sync.ensure_week(sb, 2026, A_WEEK)
    sent = sb.upserts[0]
    assert sent["rows"][0]["id"] == 7, "a second row would orphan the week's games"
    assert sent["on_conflict"] == "season,week_no"


def test_a_brand_new_week_carries_the_espn_boundaries():
    sb = RecordingSB(existing=[])
    sync.ensure_week(sb, 2026, A_WEEK)
    sent = sb.upserts[0]["rows"][0]
    assert "id" not in sent, "serial id must be left to Postgres"
    assert sent["starts_at"] == A_WEEK["start"]
    assert sent["ends_at"] == A_WEEK["end"]
    assert sent["week_no"] == 1
