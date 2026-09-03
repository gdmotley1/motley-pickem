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
