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
import json
import os
import sys

from pywebpush import WebPushException, webpush

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sync_supabase import Supabase, env, load_dotenv  # noqa: E402

# Apple rejects a payload over 4KB outright. Nothing here comes close, but the cap is
# what stops a future notification from failing silently on iOS alone.
MAX_PAYLOAD = 3800


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
        webpush(subscription_info=info, data=body, **vapid())
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
    payload = {"title": "Motley Pick'em", "kind": "test",
               "body": "Reminders are working. This is the only test you will get.",
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


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true",
                   help="print who is due without sending or writing anything")
    p.add_argument("--test", type=int, metavar="SEAT",
                   help="send one test notification to this seat (1-4)")
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
    return run(sb, a.dry_run)


if __name__ == "__main__":
    sys.exit(main())
