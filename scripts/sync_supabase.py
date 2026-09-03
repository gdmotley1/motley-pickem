"""Push ESPN data into Supabase. This is the job that makes the app self-running.

Two modes:

  --mode slate    Build the week and its 40-game pool. Creates the weeks row, upserts
                  every candidate game, and pre-selects the best 20. Never touches
                  in_slate on a week the commissioner has already published, so a
                  refresh cannot undo his choices.

  --mode scores   Refresh kickoff times, spreads, live scores and finals for games
                  already in the database, then apply the underdog auto-picks for
                  anyone who missed a kickoff. Safe to run every few minutes.

Writes with the service_role key, which bypasses RLS. That key must never reach the
browser: it lives in the environment only.

Usage:
    python scripts/sync_supabase.py --mode slate  --next
    python scripts/sync_supabase.py --mode scores --current
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request

from cfb_weeks import current_week, date_range, fetch_calendar, next_week, week_by_number
from fetch_slate import is_fbs
from suggest_slate import build as build_pool
from suggest_slate import conf_id, tier_of


def env(name: str, required: bool = True) -> str:
    val = os.environ.get(name, "")
    if not val and required:
        print("Missing %s. Put it in .env or the job environment." % name, file=sys.stderr)
        raise SystemExit(2)
    return val


def load_dotenv(path: str = ".env") -> None:
    """Local convenience. In CI the values come from the job environment instead."""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


class Supabase:
    def __init__(self, url: str, key: str):
        self.url = url.rstrip("/")
        self.key = key

    def _request(self, method: str, path: str, body=None, prefer: str = ""):
        data = json.dumps(body).encode("utf-8") if body is not None else None
        headers = {
            "apikey": self.key,
            "Authorization": "Bearer " + self.key,
            "Content-Type": "application/json",
        }
        if prefer:
            headers["Prefer"] = prefer
        req = urllib.request.Request(self.url + path, data=data, headers=headers,
                                     method=method)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read().decode("utf-8")
                return json.loads(raw) if raw.strip() else None
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:400]
            raise RuntimeError("%s %s -> HTTP %s: %s" % (method, path, e.code, detail))

    def upsert(self, table: str, rows: list, on_conflict: str):
        if not rows:
            return []
        return self._request(
            "POST", "/rest/v1/%s?on_conflict=%s" % (table, on_conflict), rows,
            prefer="resolution=merge-duplicates,return=representation")

    def select(self, table: str, query: str = ""):
        return self._request("GET", "/rest/v1/%s?%s" % (table, query)) or []

    def rpc(self, fn: str, args: dict | None = None):
        return self._request("POST", "/rest/v1/rpc/%s" % fn, args or {})


def game_row(g: dict, week_id: int, in_slate: bool | None) -> dict:
    o = g.get("odds") or {}
    row = {
        "id": int(g["espn_id"]),
        "week_id": week_id,
        "home_id": g["home"].get("id"),
        "away_id": g["away"].get("id"),
        "home_abbr": g["home"]["abbr"],
        "away_abbr": g["away"]["abbr"],
        "home_school": g["home"].get("school"),
        "away_school": g["away"].get("school"),
        "home_conf": conf_id(g["home"]),
        "away_conf": conf_id(g["away"]),
        "kickoff": g["kickoff_utc"],
        "neutral_site": bool(g.get("neutral_site")),
        "tv": g.get("tv"),
        "spread_line": o.get("line"),
        "favorite_abbr": o.get("favorite"),
        "underdog_abbr": o.get("underdog"),
        "tier": tier_of(g),
        "interest": g.get("interest"),
        "featured": bool(g.get("featured")),
        "state": g.get("state") or "pre",
        "home_score": g["home"].get("score"),
        "away_score": g["away"].get("score"),
        "winner_abbr": g.get("winner"),
        "status_detail": g.get("status_detail"),
        "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    # ESPN gives no team id on the scoreboard, so read it out of the logo URL.
    for side in ("home", "away"):
        if not row["%s_id" % side]:
            import re
            m = re.search(r"/(\d+)\.png", g[side].get("logo") or "")
            row["%s_id" % side] = m.group(1) if m else None
    if in_slate is not None:
        row["in_slate"] = in_slate
    return row


def resolve_week(a) -> dict:
    weeks = fetch_calendar(a.season)
    if a.week:
        w = week_by_number(weeks, a.week)
    elif a.next:
        w = next_week(weeks)
    else:
        w = current_week(weeks)
    if not w:
        print("No matching week in the %d calendar." % a.season, file=sys.stderr)
        raise SystemExit(1)
    return w


def ensure_week(sb: Supabase, season: int, week: dict) -> dict:
    existing = sb.select("weeks", "season=eq.%d&week_no=eq.%d&select=*"
                         % (season, week["week"]))
    row = {
        "season": season,
        "week_no": week["week"],
        "label": week["label"],
        "starts_at": week["start"],
        "ends_at": week["end"],
    }
    if existing:
        row["id"] = existing[0]["id"]
    saved = sb.upsert("weeks", [row], "season,week_no")
    return saved[0] if saved else existing[0]


def sync_slate(sb: Supabase, a, week: dict) -> int:
    start, end = date_range(week)
    print("%s  %s .. %s" % (week["label"], start, end))

    wk = ensure_week(sb, a.season, week)
    print("week row id=%s published=%s" % (wk["id"], wk.get("published")))

    pool = build_pool(start, end, week)
    chosen = {int(g["espn_id"]) for g in pool["slate"]}
    everything = pool["slate"] + pool["alternates"]

    # A published week keeps whatever the commissioner chose. Refreshing spreads must
    # never silently reshuffle a slate the family is already picking against.
    published = bool(wk.get("published"))
    rows = [game_row(g, wk["id"], None if published else (int(g["espn_id"]) in chosen))
            for g in everything]

    sb.upsert("games", rows, "id")
    print("upserted %d games (%d pre-selected)%s"
          % (len(rows), len(chosen), " - slate preserved, week already published"
             if published else ""))
    return 0


def sync_scores(sb: Supabase, a, week: dict) -> int:
    start, end = date_range(week)
    wk = sb.select("weeks", "season=eq.%d&week_no=eq.%d&select=*" % (a.season, week["week"]))
    if not wk:
        print("Week %s is not in the database yet. Run --mode slate first."
              % week["label"], file=sys.stderr)
        return 1
    wk = wk[0]

    known = {int(g["id"]) for g in sb.select("games", "week_id=eq.%s&select=id" % wk["id"])}
    if not known:
        print("No games stored for %s yet." % week["label"], file=sys.stderr)
        return 1

    from fetch_slate import fetch
    live = [g for g in fetch(start, end) if int(g["espn_id"]) in known]

    # in_slate is deliberately omitted so a score refresh can never change the slate.
    rows = [game_row(g, wk["id"], None) for g in live]
    sb.upsert("games", rows, "id")

    finals = sum(1 for g in live if g.get("winner"))
    playing = sum(1 for g in live if g.get("state") == "in")
    print("%s: refreshed %d games (%d final, %d in progress)"
          % (week["label"], len(rows), finals, playing))

    # Anyone who missed a kickoff gets the underdog at their lowest unused value.
    filled = sb.rpc("apply_auto_picks")
    if isinstance(filled, int) and filled:
        print("auto-picked %d missing entries" % filled)
    return 0


def main() -> int:
    load_dotenv()
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=("slate", "scores"), required=True)
    p.add_argument("--week", type=int, default=None)
    p.add_argument("--current", action="store_true")
    p.add_argument("--next", action="store_true")
    p.add_argument("--season", type=int, default=2026)
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()

    week = resolve_week(a)
    if a.dry_run:
        start, end = date_range(week)
        print("[dry run] mode=%s %s (%s .. %s)" % (a.mode, week["label"], start, end))
        return 0

    sb = Supabase(env("SUPABASE_URL"), env("SUPABASE_SERVICE_KEY"))
    return sync_slate(sb, a, week) if a.mode == "slate" else sync_scores(sb, a, week)


if __name__ == "__main__":
    raise SystemExit(main())
