"""Send the push notifications that migrations/012_push.sql says are due.

    python scripts/send_push.py --dry-run     # who is due, and what it would say
    python scripts/send_push.py               # actually send
    python scripts/send_push.py --test 1      # one test notification to seat 1

Where this runs matters, and it is worth being explicit about why.

The GitHub sync workflow is the obvious home and it is the wrong one. It asks for every
fifteen minutes Thursday through Sunday and does not get it: on the Thursday of week 1 it
ran at 22:42 UTC and then not again until 00:25. A reminder that is meant to land 45
minutes before kickoff cannot ride on a schedule with a 103 minute hole in it. That is the
same lesson `apply_auto_picks` already learned, which is why it moved to pg_cron in 005.

So in production this is a Supabase Edge Function on a pg_cron schedule. This file is the
version that runs from Grant's machine: it is how the chain gets proved end to end before
anything is deployed, and it stays afterwards as the way to send a test to a real phone
and as a manual backstop if the scheduler ever stops.

Both halves call the same SQL, so there is one definition of who is due and what it says.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys

from pywebpush import WebPushException, webpush

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sync_supabase import Supabase, env, load_dotenv  # noqa: E402

# Apple rejects a payload over 4KB outright. Nothing here comes close, but the cap is
# what stops a future notification from failing silently on iOS alone.
MAX_PAYLOAD = 3800

# How long the push service holds a message for a phone it cannot reach right now.
#
# pywebpush defaults this to 0, which means "deliver this instant or discard it forever".
# That is wrong for every notification this app sends: a phone that is locked, asleep,
# or off wifi for a moment silently loses the message, and the sender still sees a 201
# because Apple did accept it. Twenty minutes is longer than any realistic gap and still
# short enough that nothing arrives stale enough to mislead: a pick reminder that showed
# up an hour late would be pointing at a game that has already kicked off.
TTL_SECONDS = 20 * 60


def vapid():
    """The private key and subject, as pywebpush wants them."""
    return {
        "vapid_private_key": env("VAPID_PRIVATE_KEY"),
        "vapid_claims": {"sub": env("VAPID_SUBJECT")},
    }


def subscriptions(sb: Supabase) -> dict[int, list[dict]]:
    """Every stored device, grouped by player."""
    rows = sb.select("push_subscriptions", "select=player_id,endpoint,p256dh,auth")
    out: dict[int, list[dict]] = {}
    for r in rows:
        out.setdefault(r["player_id"], []).append(r)
    return out


def send_one(sub: dict, payload: dict) -> tuple[bool, int, str]:
    """Push to a single device. Returns (ok, status_code, error)."""
    body = json.dumps(payload)
    if len(body.encode("utf-8")) > MAX_PAYLOAD:
        return False, 0, "payload too large"
    info = {
        "endpoint": sub["endpoint"],
        "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
    }
    try:
        # Urgency high: these are time-boxed by a kickoff, so a phone in low-power mode
        # should wake for them rather than batch them up for later.
        webpush(subscription_info=info, data=body, ttl=TTL_SECONDS,
                headers={"Urgency": "high"}, **vapid())
        return True, 201, ""
    except WebPushException as e:
        code = getattr(e.response, "status_code", 0) or 0
        detail = str(e)[:200]
        return False, code, detail


def run(sb: Supabase, dry: bool) -> int:
    # Seed and advance the high-water marks BEFORE asking who is due, or the first live
    # week would have no baseline to compare against and "you got passed" would never
    # fire at all.
    if not dry:
        sb.rpc("push_refresh_ranks", {})

    due = sb.rpc("push_due", {}) or []
    if not due:
        print("nothing due")
        return 0

    devices = subscriptions(sb)
    sent = 0
    for row in due:
        player = row["player_id"]
        targets = devices.get(player, [])
        label = "%s -> seat %s: %s / %s" % (row["kind"], player, row["title"], row["body"])
        if dry:
            print("[dry run] %s  (%d device%s)"
                  % (label, len(targets), "" if len(targets) == 1 else "s"))
            continue

        payload = {"title": row["title"], "body": row["body"],
                   "url": row["url"], "kind": row["kind"]}
        delivered = False
        for sub in targets:
            ok, code, detail = send_one(sub, payload)
            if ok:
                delivered = True
            else:
                print("  FAILED %s (%s): %s" % (sub["endpoint"][:52], code, detail))
                sb.rpc("push_failed", {"p_endpoint": sub["endpoint"],
                                       "p_code": code, "p_error": detail})

        # The ledger row is written when at least one device took it. Writing it on a
        # total failure would silence the retry; not writing it when one of two phones
        # succeeded would send the other one a duplicate every five minutes.
        if delivered:
            sb.rpc("push_sent", {"p_player": player, "p_kind": row["kind"],
                                 "p_key": row["dedupe_key"]})
            sent += 1
            print("  sent %s" % label)

    print("%d notification%s sent" % (sent, "" if sent == 1 else "s"))
    return 0


def test_send(sb: Supabase, seat: int) -> int:
    """One notification to one seat, bypassing push_due entirely.

    This is the only thing that proves the whole chain: VAPID keys, the stored
    subscription, Apple's push service, the service worker, and a Home Screen install
    that is allowed to show it. Nothing is written to the ledger, so it can be repeated.
    """
    devices = subscriptions(sb).get(seat, [])
    if not devices:
        print("seat %s has no subscribed device. Turn reminders on in the app first."
              % seat)
        return 1
    # The title is the MESSAGE, never the app's name: iOS draws the name as the header
    # already, so "Motley Pick'em" here renders it twice on the lock screen.
    payload = {"title": "Reminders are on", "kind": "test",
               "body": "That is the only test. Real ones come when a kickoff is close.",
               "url": "/motley-pickem/"}
    ok_count = 0
    for sub in devices:
        ok, code, detail = send_one(sub, payload)
        print("  %s %s (%s) %s" % ("OK  " if ok else "FAIL", sub["endpoint"][:52],
                                   code, detail))
        if ok:
            ok_count += 1
        elif code in (404, 410):
            sb.rpc("push_failed", {"p_endpoint": sub["endpoint"],
                                   "p_code": code, "p_error": detail})
            print("       that subscription was dead and has been removed")
    print("%d of %d device(s) accepted it" % (ok_count, len(devices)))
    return 0 if ok_count else 1


def reminder_text(open_count: int, locks_at: str) -> tuple[str, str]:
    """The heads-up wording: title, body.

    A function rather than two format strings inline, so the gate can call it with 1 and
    with 20 instead of grepping this file for a line of source. The singular matters:
    the last unpicked game of a week is the commonest reminder there is, so "1 games
    still open" would be the version everybody sees.

    Must stay identical to the heads-up branch of push_due() in migrations/014.
    """
    return ("%d game%s still open" % (open_count, "" if open_count == 1 else "s"),
            "First one locks at %s" % locks_at)


def open_picks(sb: Supabase) -> list[dict]:
    """Per subscribed player: how many games they can still pick, and when the first
    of those locks. Mirrors the heads-up branch of push_due() minus its time window."""
    weeks = {w["id"] for w in sb.select("weeks", "select=id&published=is.true")}
    if not weeks:
        return []
    now = dt.datetime.now(dt.timezone.utc)
    games = [g for g in sb.select(
        "games", "select=id,week_id,kickoff&in_slate=eq.true&order=kickoff")
        if g["week_id"] in weeks
        and dt.datetime.fromisoformat(g["kickoff"].replace("Z", "+00:00")) > now]
    if not games:
        return []

    subscribed = {s["player_id"] for s in sb.select("push_subscriptions",
                                                    "select=player_id")}
    players = [p for p in sb.select("players", "select=id,name,notify_picks")
               if p["name"] and p.get("notify_picks") and p["id"] in subscribed]
    picked = {(p["player_id"], p["game_id"])
              for p in sb.select("picks", "select=player_id,game_id&limit=5000")}

    # Eastern is what the family reads kickoffs in, and it is what push_due formats to.
    et = dt.timezone(dt.timedelta(hours=-4))
    out = []
    for p in players:
        mine = [g for g in games if (p["id"], g["id"]) not in picked]
        if not mine:
            continue
        first = dt.datetime.fromisoformat(mine[0]["kickoff"].replace("Z", "+00:00"))
        out.append({
            "player_id": p["id"],
            "open_count": len(mine),
            "locks_at": first.astimezone(et).strftime("%I:%M %p").lstrip("0").lower(),
        })
    return out


def nudge(sb: Supabase, dry: bool) -> int:
    """Send the pick reminder NOW, to everyone who still owes picks.

    The scheduled one only fires inside the heads-up window, three hours before the next
    kickoff. This is the manual override for when somebody wants the family poked earlier
    than that, and it is the whole reason it exists: on 2026-09-11 Week 2 sat at 0 of 80
    picks at two in the afternoon with the window still three hours away.

    Deliberately does NOT write the dedupe ledger. A manual nudge is not the scheduled
    reminder and must not cancel it, so the real one still lands at its own time.

    Computed here rather than in a push_open_picks() RPC on purpose. Migrations are
    pasted into the SQL Editor by hand, and a manual override whose whole point is
    "right now" cannot be gated on a paste. The service key already bypasses RLS and this
    module already reads tables directly, so nothing new is being reached for. The
    wording is duplicated from push_due's heads-up branch and test_push.py holds the two
    together.
    """
    rows = open_picks(sb)
    if not rows:
        print("nobody has an unpicked game, or nobody is subscribed")
        return 0

    devices = subscriptions(sb)
    sent = 0
    for r in rows:
        targets = devices.get(r["player_id"], [])
        title, body = reminder_text(r["open_count"], r["locks_at"])
        payload = {"title": title, "body": body,
                   "url": "/motley-pickem/?tab=picks", "kind": "pick_reminder"}
        if dry:
            print("[dry run] seat %s: %s / %s  (%d device%s)"
                  % (r["player_id"], payload["title"], payload["body"],
                     len(targets), "" if len(targets) == 1 else "s"))
            continue
        for sub in targets:
            ok, code, detail = send_one(sub, payload)
            if ok:
                sent += 1
                print("  sent to seat %s: %s / %s"
                      % (r["player_id"], payload["title"], payload["body"]))
            else:
                print("  FAILED seat %s (%s): %s" % (r["player_id"], code, detail))
                sb.rpc("push_failed", {"p_endpoint": sub["endpoint"],
                                       "p_code": code, "p_error": detail})
    if not dry:
        print("%d notification%s sent" % (sent, "" if sent == 1 else "s"))
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true",
                   help="print who is due without sending or writing anything")
    p.add_argument("--test", type=int, metavar="SEAT",
                   help="send one test notification to this seat (1-4)")
    p.add_argument("--nudge", action="store_true",
                   help="send the pick reminder now, ignoring the heads-up window. "
                        "Does not write the ledger, so the scheduled one still fires.")
    a = p.parse_args()

    load_dotenv()
    sb = Supabase(env("SUPABASE_URL"), env("SUPABASE_SERVICE_KEY"))

    # Migrations are pasted into the Supabase SQL Editor by hand, so "I forgot to paste
    # it" is the single likeliest reason this script does not work. Say that, rather than
    # a PostgREST schema-cache traceback that reads like a bug in the sender.
    try:
        sb.rpc("push_due", {})
    except RuntimeError as e:
        if "PGRST202" in str(e):
            print("migrations/012_push.sql has not been applied to this project yet.\n"
                  "Paste it into the Supabase SQL Editor, then run this again.",
                  file=sys.stderr)
            return 2
        raise

    if a.test:
        return test_send(sb, a.test)
    if a.nudge:
        return nudge(sb, a.dry_run)
    return run(sb, a.dry_run)


if __name__ == "__main__":
    sys.exit(main())
