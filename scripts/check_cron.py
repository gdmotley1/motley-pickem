"""Is the auto-pick job actually scheduled inside Postgres?

Auto-picks are what let a player who missed a kickoff still submit their week. Migration
005 put them on pg_cron every five minutes rather than on the GitHub sync job, because
GitHub does not honour the schedule it is given: measured on 2026-09-04 over the whole
run history, a workflow asking for every 15 minutes delivered six runs 1.7 to 4.5 hours
apart. pg_cron is therefore the load-bearing path, and until migration 008 nothing
outside the SQL editor could see whether it was alive.

Usage:
    python scripts/check_cron.py

Exits non-zero if the job is missing, inactive, or its last run failed.
"""
from __future__ import annotations

import sys

from sync_supabase import Supabase, env, load_dotenv

JOB = "autopick-at-kickoff"
EXPECTED = "*/5 * * * *"

# pg_cron logs a run every five minutes, so anything much past that is a stalled job
# rather than one that simply has not come round yet.
STALE_MINUTES = 15


def main() -> int:
    load_dotenv()
    sb = Supabase(env("SUPABASE_URL"), env("SUPABASE_SERVICE_KEY"))
    try:
        rows = sb.rpc("cron_health")
    except RuntimeError as exc:
        if "PGRST202" in str(exc) or "does not exist" in str(exc):
            print("cron_health() is not in the database yet.\n"
                  "Paste migrations/008_cron_health.sql into the Supabase SQL Editor,\n"
                  "or run migrations/ALL.sql, then try again.", file=sys.stderr)
            return 2
        raise

    if not rows:
        print("FAIL: pg_cron has no jobs at all. Auto-picks are not running.",
              file=sys.stderr)
        return 1

    for job in rows:
        print("  %-22s %-14s active=%s  last=%s (%s min ago, %s)"
              % (job["jobname"], job["schedule"], job["active"],
                 job["last_start"], job["minutes_ago"], job["last_status"]))

    job = next((j for j in rows if j["jobname"] == JOB), None)
    if job is None:
        print("\nFAIL: no job named %r. Auto-picks are not scheduled." % JOB,
              file=sys.stderr)
        return 1

    problems = []
    if not job["active"]:
        problems.append("the job is present but INACTIVE")
    if job["schedule"] != EXPECTED:
        problems.append("schedule is %r, expected %r" % (job["schedule"], EXPECTED))
    if job["last_start"] is None:
        problems.append("it has never run")
    elif job["minutes_ago"] is not None and float(job["minutes_ago"]) > STALE_MINUTES:
        problems.append("last run was %s minutes ago, over the %d minute limit"
                        % (job["minutes_ago"], STALE_MINUTES))
    if job["last_status"] not in (None, "succeeded"):
        problems.append("last run finished %r" % job["last_status"])

    if problems:
        print("\nFAIL: " + "; ".join(problems), file=sys.stderr)
        return 1

    print("\nPASS: %s is active on %s and last ran %s minutes ago."
          % (JOB, EXPECTED, job["minutes_ago"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
