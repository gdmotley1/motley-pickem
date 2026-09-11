"""The gate for push notifications.

Built 2026-09-11, after Week 1 went 80 for 80 and Week 2 sat at 0 of 80 with eleven hours
to the first kickoff. The PickNudge was already shipped for exactly that, but a nudge
lives inside the app nobody opened.

Two things here are worth more than the rest. The backlog guards, because without them
the very first run announces every week ever published to four phones at once, and that
is the kind of mistake you only get to make in front of your family once. And the rule
that a push must always produce a notification, because iOS revokes the subscription of
an app that takes a push and shows nothing.

The arithmetic in src/lib/push.js and static/sw.js runs under node in push_check.mjs,
the same way test_nudge.py does it.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHECK = os.path.join(ROOT, "tests", "push_check.mjs")
MIGRATION = os.path.join(ROOT, "migrations", "012_push.sql")

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not on PATH")


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def sql():
    return read("migrations", "012_push.sql")


@pytest.fixture(scope="module")
def sw():
    return read("static", "sw.js")


@pytest.fixture(scope="module")
def effective_push_due():
    """push_due's body from the LAST migration that defines it.

    012 wrote it and 013 replaced it. Reading 012 here would guard the version with the
    bug still in it, which is exactly the trap test_migration.py was fixed for earlier
    the same day.
    """
    sys.path.insert(0, os.path.join(ROOT, "tests"))
    import test_migration

    return test_migration.body("push_due")


@needs_node
def test_key_conversion_and_click_target():
    proc = subprocess.run([node, CHECK], capture_output=True, text=True, cwd=ROOT,
                          timeout=60)
    assert proc.returncode == 0, "\n" + proc.stdout + proc.stderr


# ------------------------------------------------------------------ the data layer

def test_the_new_tables_are_locked_down(sql):
    """Same posture as every other table: RLS on, no policies, nothing granted.

    A push subscription is the one row in this database that lets you reach someone's
    phone, so it gets the treatment the picks table gets.
    """
    for table in ("push_subscriptions", "push_log", "push_rank"):
        assert re.search(r"alter table %s\s+enable row level security" % table, sql), \
            "%s does not have RLS enabled" % table
    assert re.search(r"revoke all on push_subscriptions, push_log, push_rank\s+"
                     r"from anon, authenticated", sql), \
        "the push tables are readable by the anon key"
    assert "create policy" not in sql.lower(), \
        "a policy would open these up; the pattern here is RLS on with no policies"


def test_the_sender_functions_are_not_on_the_public_api(sql):
    """push_due tells you who is due and what it will say. push_failed deletes a
    subscription by endpoint. Neither belongs on a surface the anon key can reach, and
    the anon key ships in the browser bundle."""
    for fn in ("push_due()", "_push_live_ranks()", "push_sent(smallint, text, text)",
               "push_failed(text, int, text)", "push_refresh_ranks()"):
        assert re.search(r"revoke all on function %s\s+from public, anon, authenticated"
                         % re.escape(fn), sql), \
            "%s is reachable by clients" % fn
    for fn in ("push_due", "_push_live_ranks", "push_sent", "push_failed",
               "push_refresh_ranks"):
        assert not re.search(r"grant execute on function %s\b" % fn, sql), \
            "%s is granted to somebody" % fn


def test_every_player_facing_rpc_requires_a_session(sql):
    """The four a phone can call. Each must resolve the caller from their token and
    refuse without one, or any anon key holder could subscribe a device to any seat."""
    for fn in ("save_push_subscription", "delete_push_subscription", "my_push_state",
               "set_notify_prefs"):
        body = re.search(r"create or replace function %s.*?\$\$(.*?)\$\$" % fn,
                         sql, re.S | re.I)
        assert body, "%s is not defined" % fn
        assert "_player_for(p_token)" in body.group(1), "%s does not read the token" % fn
        assert "Not signed in" in body.group(1), "%s does not refuse a stranger" % fn


def test_unsubscribing_is_scoped_to_the_caller(sql):
    """Without the player_id clause, knowing an endpoint would be enough to turn off
    somebody else's reminders."""
    body = re.search(r"create or replace function delete_push_subscription.*?\$\$(.*?)\$\$",
                     sql, re.S | re.I).group(1)
    assert "player_id = me.id" in body, \
        "delete_push_subscription would delete another player's subscription"


def test_the_ledger_has_a_primary_key(sql):
    assert re.search(r"primary key \(player_id, kind, dedupe_key\)", sql), \
        "the dedupe ledger has no primary key on (player, kind, key)"


def test_every_branch_of_push_due_reads_the_ledger(effective_push_due):
    """The one that matters, and the one the first version of this test missed entirely.

    That version asserted push_log had a primary key. True, and worth nothing: push_due
    never read the table at all. Found live on 2026-09-11 by running the sender twice and
    getting "Week 2 is up" twice. On a five minute schedule week_live, week_results and
    passed had no limit whatsoever, so each would have repeated for the full length of
    its recency window, roughly 144 notifications per phone for week_live.

    So this checks the thing itself. Splitting on `union all` is what makes it
    per-branch: a single `not exists` anywhere in the function would satisfy a naive
    version of this test while three branches stayed broken.
    """
    branches = effective_push_due.split("union all")
    assert len(branches) == 4, \
        "expected 4 branches in push_due, found %d" % len(branches)

    for branch in branches:
        kind = re.search(r"'(pick_reminder|week_live|week_results|passed)'::text", branch)
        assert kind, "a branch of push_due names no kind"
        guard = re.search(
            r"not exists\s*\(\s*select 1 from push_log l\s+"
            r"where l\.player_id = .+?and l\.kind = '%s'\s+and l\.dedupe_key = "
            % kind.group(1),
            branch, re.S)
        assert guard, (
            "the %s branch does not check push_log, so it repeats on every run"
            % kind.group(1))


def test_the_daily_cap_is_not_the_thing_preventing_duplicates(effective_push_due):
    """pick_reminder survived the missing guard by accident: the daily cap counts
    push_log rows and so stopped at two a day. A cap on how often you may be nudged is
    not a dedupe, and the two must not be confused again."""
    reminders = effective_push_due.split("union all")[0]
    assert "_push_daily_cap()" in reminders, "the daily cap is gone"
    assert "l.dedupe_key" in reminders, \
        "pick_reminder leans on the daily cap instead of the ledger"


def test_every_kind_is_declared_and_emitted(sql):
    """Walks the check constraint rather than listing the kinds here.

    A fifth notification added to push_due with no matching kind in the constraint fails
    at INSERT time inside push_sent, which means it sends forever and never records that
    it did. This is the guard that catches that before it reaches a phone.
    """
    constraint = re.search(r"kind\s+text\s+not null check \(kind in\s*\((.*?)\)\)",
                           sql, re.S)
    assert constraint, "the kind constraint is not in the shape this guard expects"
    declared = set(re.findall(r"'([a-z_]+)'", constraint.group(1)))
    assert declared, "no kinds declared"

    due = re.search(r"create or replace function push_due\(\).*?\$\$(.*?)\$\$",
                    sql, re.S | re.I).group(1)
    # Each branch names its kind as a bare lowercase literal cast to text. Every other
    # ::text literal in push_due carries a space, a slash or a digit (the titles, the
    # bodies, the URLs), so this picks out the kinds and nothing else.
    emitted = set(re.findall(r"'([a-z_]+)'::text", due))

    assert declared == emitted, (
        "push_due emits %s but the constraint allows %s"
        % (sorted(emitted), sorted(declared))
    )


def test_the_announcements_cannot_blast_a_backlog(sql):
    """The one that would be unrecoverable in front of the family.

    On the first run the ledger is empty. Without a recency clause, 'week_live' matches
    every week ever published and 'week_results' every week ever graded, so fifteen weeks
    of announcements arrive at once on four phones.
    """
    due = re.search(r"create or replace function push_due\(\).*?\$\$(.*?)\$\$",
                    sql, re.S | re.I).group(1)
    branches = due.split("union all")
    live = next((b for b in branches if "'week_live'" in b), None)
    results = next((b for b in branches if "'week_results'" in b), None)
    assert live and results, "the announcement branches are not in the shape expected"

    assert re.search(r"published_at\s*>\s*now\(\)\s*-\s*interval", live), \
        "week_live has no recency guard: it would announce every published week"
    assert re.search(r"max\(g\.kickoff\).*?>\s*now\(\)\s*-\s*interval", results, re.S), \
        "week_results has no recency guard: it would announce every graded week"


def test_pick_reminders_never_chase_a_game_that_started(sql):
    """The nudge learned this first: a game you can no longer pick is not a reminder,
    it is a reproach. Also the daily cap, which is what keeps Saturday from buzzing."""
    due = re.search(r"create or replace function push_due\(\).*?\$\$(.*?)\$\$",
                    sql, re.S | re.I).group(1)
    reminders = due.split("union all")[0]
    assert "g.kickoff > now()" in reminders, \
        "pick reminders would count games that have already kicked off"
    assert "_push_daily_cap()" in reminders, "the daily cap is not applied"


def test_a_dead_endpoint_is_deleted_rather_than_retried(sql):
    """410 Gone is ordinary here, not exceptional: on iOS it is what deleting and
    re-adding the Home Screen icon does. Retrying one forever is how a sender ends up
    hammering Apple with requests that can never succeed."""
    body = re.search(r"create or replace function push_failed.*?\$\$(.*?)\$\$",
                     sql, re.S | re.I).group(1)
    assert "p_code in (404, 410)" in body and "delete from push_subscriptions" in body, \
        "push_failed does not prune a permanently dead endpoint"


def test_the_rank_baseline_is_a_high_water_mark(sql):
    """`least` is what makes 'you got passed' self-limiting. With a plain overwrite the
    baseline follows you down and back up, and a Saturday of lead changes becomes a
    Saturday of notifications."""
    body = re.search(r"create or replace function push_refresh_ranks.*?\$\$(.*?)\$\$",
                     sql, re.S | re.I).group(1)
    assert "least(push_rank.rank, excluded.rank)" in body, \
        "push_refresh_ranks does not keep the best rank, so 'passed' can repeat"


# ------------------------------------------------------------------ the worker

def test_a_push_always_becomes_a_notification(sw):
    """iOS revokes the subscription of an app that receives a push and shows nothing.

    So the handler must have no path that skips showNotification, including the one where
    the payload is missing or unparseable.
    """
    handler = re.search(r"self\.addEventListener\('push'.*?\n\}\)", sw, re.S)
    assert handler, "there is no push handler"
    body = handler.group(0)
    assert "showNotification" in body, "the push handler shows nothing"
    assert "return" not in body.split("showNotification")[0], \
        "the push handler can return before showing a notification"
    assert "FALLBACK" in sw, "there is no fallback for an unreadable payload"


def test_the_click_target_is_never_taken_on_trust(sw):
    """The payload is ours, but a notification click opens a window."""
    click = re.search(r"self\.addEventListener\('notificationclick'.*?\n\}\)", sw, re.S)
    assert click, "there is no notificationclick handler"
    assert "sameOriginPath" in sw, "the click target is not sanitised anywhere"
    assert "data.url" not in click.group(0), \
        "notificationclick reads the payload URL directly instead of the sanitised one"


def test_the_worker_still_names_no_third_party_host(sw):
    """012 added push, and the push endpoint is at Apple or Google. None of that belongs
    in here: the worker only ever renders what the browser already decrypted."""
    for host in ("supabase.co", "espn.com", "push.apple.com", "fcm.googleapis.com"):
        assert host not in sw, "%s is named in the service worker" % host


# ------------------------------------------------------------------ the sender

def test_the_ledger_is_written_only_when_something_was_delivered():
    """Both directions are bugs. Recording a send that failed silences the retry.
    Not recording one that partly succeeded sends the working phone a duplicate every
    five minutes for as long as the other one stays broken.
    """
    src = read("scripts", "send_push.py")
    assert re.search(r"if delivered:\s*\n\s*sb\.rpc\(\"push_sent\"", src), \
        "push_sent is not gated on an actual delivery"


def test_the_sender_reports_a_failure_back_to_the_database():
    src = read("scripts", "send_push.py")
    assert 'sb.rpc("push_failed"' in src, "failures are never reported, so nothing prunes"


def test_the_payload_is_capped_below_apples_limit():
    """Apple rejects anything over 4KB outright, and the rejection is per-device."""
    src = read("scripts", "send_push.py")
    cap = re.search(r"MAX_PAYLOAD = (\d+)", src)
    assert cap, "there is no payload cap"
    assert int(cap.group(1)) < 4096, "the cap is at or above Apple's 4KB limit"


def test_the_private_key_is_never_written_to_disk_by_the_generator():
    """A private key a script drops on disk is a private key that gets committed one day.
    vapid_keys.py prints and nothing else."""
    src = read("scripts", "vapid_keys.py")
    assert not re.search(r"open\([^)]*['\"]w['\"]", src), \
        "vapid_keys.py writes a file; it must only print"


def test_the_vapid_private_key_is_not_in_the_bundle_or_the_repo():
    """VITE_ prefixed vars are inlined into the client bundle. The private key must never
    carry that prefix, and no source file may name it outside the sender."""
    for rel in ("src/lib/push.js", "src/lib/api.js", "src/App.jsx"):
        body = read(*rel.split("/"))
        assert "VAPID_PRIVATE" not in body, "%s references the VAPID private key" % rel
    assert "VITE_VAPID_PRIVATE_KEY" not in read("scripts", "vapid_keys.py"), \
        "the private key must never be given a VITE_ prefix"


# ------------------------------------------------------------------ the client

def test_permission_is_only_ever_requested_from_a_tap():
    """iOS denies a requestPermission() that did not come from a user gesture, and a
    denial is permanent: there is no second chance from script, ever. So the call must
    live in the enable path and nowhere that runs on load."""
    push = read("src", "lib", "push.js")
    assert "requestPermission" in push
    status = re.search(r"export async function pushStatus\(\)[\s\S]*?\n\}", push).group(0)
    assert "requestPermission" not in status, \
        "pushStatus runs on load and must never prompt"


def test_a_denied_permission_says_what_to_do_about_it():
    """An app that offers a button which silently does nothing is worse than one that
    explains. Settings is the only route back."""
    push = read("src", "lib", "push.js")
    assert "Settings" in push, "nothing tells a denied user where to turn it back on"


def test_the_home_screen_requirement_is_explained():
    """The commonest failure by far is opening the link in Safari instead of tapping the
    icon, and it presents as 'reminders are not supported', which is useless."""
    push = read("src", "lib", "push.js")
    assert "Home Screen" in push, "the iOS install requirement is never explained"


def test_the_sheet_is_actually_rendered():
    """The call, not the import. A guard that only checks the import passes against a
    screen where the component was deleted from the tree, which is how the spread filter
    guard failed on 2026-09-10."""
    app = read("src", "App.jsx")
    assert "<RemindersSheet" in app, "App no longer renders the reminders sheet"
    assert "onReminders" in app, "nothing opens the reminders sheet"


def test_the_subscription_follows_a_seat_switch():
    """This app is built around handing the phone over. Without a re-save on sign-in the
    endpoint still belongs to the previous player and the notifications arrive under the
    wrong name."""
    app = read("src", "App.jsx")
    assert "syncSubscription" in app, "nothing re-points the subscription after sign-in"


def test_a_message_is_held_rather_than_discarded():
    """pywebpush defaults ttl to 0, which means "deliver this instant or discard it".

    That is wrong for every notification here. A phone that is locked, asleep, or off
    wifi for a moment loses the message, and the sender still sees a 201 because Apple
    did accept it. The first live test push vanished exactly this way.
    """
    src = read("scripts", "send_push.py")
    ttl = re.search(r"TTL_SECONDS = ([^\n]+)", src)
    assert ttl, "there is no TTL"
    assert "ttl=TTL_SECONDS" in src, "the TTL is defined but never passed to webpush"
    seconds = eval(ttl.group(1).split("#")[0].strip())  # noqa: S307 - our own literal
    assert seconds > 0, "ttl=0 discards a message the instant it cannot be delivered"
    assert seconds <= 3600, (
        "a pick reminder held longer than an hour arrives pointing at a game that has "
        "already kicked off"
    )


def test_no_notification_title_repeats_the_app_name(sql, sw):
    """iOS draws the app's name as the notification header, from the Home Screen install.

    A title of "Motley Pick'em" therefore renders the name twice, which is what the very
    first test push to reach a phone actually looked like. A title is the MESSAGE, never
    the sender.

    Walks all three places a title can come from rather than naming the two that were
    wrong: push_due's branches, the worker's fallback, and the test payload.
    """
    name_bits = re.compile(r"motley|pick'?em", re.I)

    # Every prose literal in push_due, not just the ones cast straight to ::text. The
    # first version of this matched `'...'::text` and so missed both pick-reminder
    # titles, which sit inside a CASE and are cast after it: the guard was checking two
    # of the five branches and looked like it was checking all of them.
    #
    # "Prose" is any literal containing a space. That takes in titles and bodies, skips
    # the kind names (no spaces) and the URLs (which legitimately contain "pickem" and
    # are never shown to anyone).
    due = re.search(r"create or replace function push_due\(\).*?\$\$(.*?)\$\$",
                    sql, re.S | re.I).group(1)
    titles = [t.replace("''", "'")
              for t in re.findall(r"'((?:[^']|'')*)'", due)
              if " " in t and not t.startswith("/")]
    assert len(titles) >= 5, \
        "found only %d prose literals in push_due; has its shape changed?" % len(titles)

    # Either quote style, or the guard trips its own shape check on the very mutation it
    # exists to catch and reports the wrong reason.
    fallback = re.search(r"""const FALLBACK = \{\s*title:\s*(['"])(.+?)\1""", sw)
    assert fallback, "the worker fallback title is not in the shape expected"
    titles.append(fallback.group(2))

    send = read("scripts", "send_push.py")
    test_title = re.search(r"""["']title["']:\s*(['"])(.+?)\1,\s*["']kind["']""", send)
    assert test_title, "the test payload title is not in the shape expected"
    titles.append(test_title.group(2))

    offenders = [t for t in titles if name_bits.search(t)]
    assert not offenders, (
        "these titles repeat the app name, which iOS already shows: %s" % offenders
    )
