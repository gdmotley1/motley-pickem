"""The sync workflow's schedules, checked against the steps that claim to run them.

GitHub dispatches a scheduled run by putting the cron string in github.event.schedule,
and every step in sync.yml decides whether to act by comparing against that literal. So
a cron and its step are one fact written in two places, and nothing in GitHub complains
when they stop agreeing: the schedule fires, no step matches, the job goes green having
done nothing at all.

That is a quiet enough failure to be worth a test. It is the same shape as the bug these
tests were written for, where a game went ungraded because no job ever ran in the window
it needed.
"""
from __future__ import annotations

import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIVE = os.path.join(ROOT, ".github", "workflows", "sync.yml")
DOCS = os.path.join(ROOT, "docs", "workflows", "sync.yml")


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def crons(text):
    return re.findall(r"^\s*-\s*cron:\s*'([^']+)'", text, re.M)


def conditions(text):
    """Every cron string a step's `if:` compares github.event.schedule against."""
    return set(re.findall(r"github\.event\.schedule\s*==\s*'([^']+)'", text))


def test_the_workflow_is_where_github_actually_looks_for_it():
    assert os.path.exists(LIVE), ".github/workflows/sync.yml is what GitHub runs"


def test_the_documented_copy_matches_the_one_that_runs():
    """docs/workflows/ is the editable copy. A drift there is a lie in the docs."""
    assert read(DOCS) == read(LIVE)


def test_every_schedule_has_a_step_that_runs_on_it():
    """A cron with no matching step fires on time and does nothing, green."""
    text = read(LIVE)
    listening = conditions(text)
    for cron in crons(text):
        assert cron in listening, (
            "cron %r fires but no step's `if:` matches it, so the run does nothing" % cron)


def test_every_step_condition_matches_a_real_schedule():
    """The mirror image: a step waiting on a cron that was edited away never runs."""
    text = read(LIVE)
    scheduled = set(crons(text))
    for cron in conditions(text):
        assert cron in scheduled, (
            "a step waits on cron %r, which is no longer scheduled" % cron)


def test_scores_are_graded_on_every_day_of_the_week():
    """The Labor Day bug: Week 1 of 2026 ends 3am ET Tuesday and holds a Monday night
    game, so a Thursday-through-Sunday schedule reached it only after --current had
    already rolled on to Week 2. The sweep in sync_supabase.py finds a stranded game,
    but only if some job runs. Every weekday needs score coverage."""
    text = read(LIVE)
    scores = [c for c in crons(text) if c in conditions(text)
              and c.split()[1] != "12"]  # the 12:00 one builds the slate, not scores
    covered = set()
    for cron in scores:
        days = cron.split()[4]
        if days == "*":
            covered = set(range(7))
            break
        for part in days.split(","):
            covered.add(int(part))
    missing = sorted(set(range(7)) - covered)
    assert not missing, "no scores job runs on cron weekday(s) %s" % missing
