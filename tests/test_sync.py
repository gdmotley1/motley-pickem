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


# ---------------------------------------------------- the slate job freezes odds too
#
# freeze_odds being correct is only half of it: both jobs that upsert games have to
# actually call it. sync_scores has since migration 006; sync_slate did not, and nobody
# noticed because a fixed 40-game pool was built once on Monday and never rebuilt.
#
# Widening the pool to every game in the week changed that. Rebuilding mid-week to reach
# a game the commissioner asked for is now an ordinary thing to do, and on 2026-09-04 it
# would have nulled spread_line, favorite_abbr and over_under on 38 of the 40 week 1
# games the family had already picked, along with 80 stored picks priced against them.


class SlateRecorder(FakeSB):
    """Captures the rows sync_slate upserts. Distinct from the RecordingSB above,
    which models ensure_week rather than the games upsert."""

    def __init__(self, published):
        super().__init__(hours_to_kickoff=1, games=20)
        self._published = published
        self.rows = []
        self.batches = []

    def upsert(self, table, rows, on_conflict):
        # Batches are kept apart as well as accumulated: sync_slate sends two, and the
        # uniform-keys rule applies within each one rather than across both.
        if table == "games":
            self.batches.append(rows)
            self.rows.extend(rows)
        return [{"id": 1, "published": self._published}]

    def _request(self, method, path, body=None, prefer=""):
        if method == "PATCH" and "weeks" in path and (body or {}).get("published"):
            self.published = True
        return None


def a_pool_game(espn_id, state, line):
    """The shape suggest_slate.build hands back, trimmed to what game_row reads."""
    return {
        "espn_id": espn_id,
        "state": state,
        "kickoff_utc": "2026-09-05T16:00Z",
        "home": {"id": "84", "abbr": "IU", "school": "Indiana", "conference_id": "5"},
        "away": {"id": "249", "abbr": "UNT", "school": "North Texas", "conference_id": "151"},
        "odds": {"line": line, "favorite": "IU" if line else None,
                 "underdog": "UNT" if line else None, "over_under": 56.5 if line else None},
        "interest": 10.0,
        "featured": False,
    }


def run_slate(monkeypatch, pool_games, published):
    sb = SlateRecorder(published)
    slate = pool_games[:1]
    monkeypatch.setattr(sync, "build_pool", lambda *a, **k: {
        "slate": slate, "alternates": pool_games[1:]})
    monkeypatch.setattr(sync, "ensure_week", lambda *a, **k: {"id": 1, "published": published})
    monkeypatch.setattr(sync, "date_range", lambda w: (dt.date(2026, 9, 3), dt.date(2026, 9, 6)))
    monkeypatch.setattr(sync, "maybe_publish", lambda *a, **k: None)
    sync.sync_slate(sb, type("A", (), {"season": 2026})(), {"label": "Week 1"})
    run_slate.last = sb
    return {r["id"]: r for r in sb.rows}


@pytest.mark.parametrize("published", [True, False])
def test_rebuilding_a_week_never_nulls_the_line_on_a_played_game(monkeypatch, published):
    """ESPN returns no odds for a final, so the columns must be absent, not null."""
    rows = run_slate(monkeypatch, [
        a_pool_game(1, "pre", 6.5),      # still to play: ESPN's line is the live one
        a_pool_game(2, "post", None),    # already final: ESPN has dropped the block
    ], published)

    for column in sync.ODDS_COLUMNS:
        assert column not in rows[2], (
            "%s reached the upsert for a finished game and would overwrite the stored "
            "pre-kickoff value with null" % column)


@pytest.mark.parametrize("published", [True, False])
def test_rebuilding_a_week_still_updates_the_line_on_a_game_to_come(monkeypatch, published):
    """Freezing must not go so far that a line can never move before kickoff."""
    rows = run_slate(monkeypatch, [
        a_pool_game(1, "pre", 6.5),
        a_pool_game(2, "post", None),
    ], published)

    assert rows[1]["spread_line"] == 6.5
    assert rows[1]["favorite_abbr"] == "IU"
    assert rows[1]["over_under"] == 56.5


def test_rebuilding_a_published_week_leaves_the_slate_alone(monkeypatch):
    """The commissioner's twenty survive a rebuild; an unpublished week is re-picked."""
    games = [a_pool_game(1, "pre", 6.5), a_pool_game(2, "pre", 3.0)]

    published = run_slate(monkeypatch, games, True)
    assert all("in_slate" not in r for r in published.values()), (
        "a published week must not have in_slate written at all")

    draft = run_slate(monkeypatch, games, False)
    assert draft[1]["in_slate"] is True and draft[2]["in_slate"] is False


def test_each_upsert_batch_carries_identical_keys(monkeypatch):
    """PostgREST rejects a bulk insert whose objects differ in shape.

    Found in production on 2026-09-04, not by a test: freezing the odds on the finished
    games and not on the rest put two shapes in one batch, and the whole week 1 rebuild
    came back "PGRST102: All object keys must match". The week was left untouched, which
    is the only reason it was harmless. sync_scores has split its batches for this reason
    all along; sync_slate now does too.
    """
    run_slate(monkeypatch, [
        a_pool_game(1, "pre", 6.5),
        a_pool_game(2, "pre", 3.0),
        a_pool_game(3, "post", None),
        a_pool_game(4, "in", None),
    ], published=False)

    batches = [b for b in run_slate.last.batches if b]
    assert len(batches) == 2, "expected the played and unplayed games to go separately"
    for batch in batches:
        shapes = {frozenset(r) for r in batch}
        assert len(shapes) == 1, (
            "a batch mixed %d row shapes; PostgREST would reject the whole upsert"
            % len(shapes))

    # And the two batches really are different shapes, or the split proves nothing.
    assert frozenset(batches[0][0]) != frozenset(batches[1][0])
