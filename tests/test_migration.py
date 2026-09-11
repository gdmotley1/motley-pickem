"""Pre-flight checks on the SQL migrations.

The migrations are applied by hand in the Supabase SQL Editor, so a syntax error costs a
round trip through Grant. These parse the files with libpg_query, the actual PostgreSQL
parser, and assert the security properties that must not regress.
"""
from __future__ import annotations

import glob
import os
import re
import sys

import pytest

pglast = pytest.importorskip("pglast", reason="pip install pglast")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIGRATIONS = sorted(glob.glob(os.path.join(ROOT, "migrations", "*.sql")))


@pytest.fixture(scope="module")
def init_sql():
    """Only for what lives in 001 and cannot move: table DDL, indexes, seed rows.

    For a function body use `body()` below. A later migration can replace a function,
    and reading 001 then guards whatever that function used to be.
    """
    path = os.path.join(ROOT, "migrations", "001_init.sql")
    with open(path, encoding="utf-8") as f:
        return f.read()


# --------------------------------------------- the definition the database actually runs

# Every migration except the generated ALL.sql, in the order Grant pastes them. ALL.sql
# holds a copy of all of them, so including it would resolve every function twice.
NUMBERED = [p for p in MIGRATIONS if re.match(r"\d+_", os.path.basename(p))]

FUNCTION_RE = (r"create\s+(?:or\s+replace\s+)?function\s+([a-z_]+)\s*\("
               r".*?\$\$(.*?)\$\$")


def _definitions():
    """Map each function name to the LAST migration defining it, and to that body.

    `apply_auto_picks` is the case that proved this is needed. 005 flipped the rule from
    the underdog to the favourite; 001 still holds the old body. The guard was pinned to
    001, so it stayed green while asserting the exact opposite of the live rule, and it
    would have failed if anyone had correctly updated 001. Resolve the effective
    definition here instead, so a guard always reads what the database runs.
    """
    found = {}
    for path in NUMBERED:
        with open(path, encoding="utf-8") as f:
            sql = f.read()
        for m in re.finditer(FUNCTION_RE, sql, re.S | re.I):
            found[m.group(1)] = (os.path.basename(path), m.group(2))
    return found


DEFINITIONS = _definitions()


def body(fn):
    """The body of `fn` after every later migration has had its say."""
    assert fn in DEFINITIONS, "%s is defined in no migration" % fn
    return DEFINITIONS[fn][1]


def source_of(fn):
    """The migration whose version of `fn` wins."""
    assert fn in DEFINITIONS, "%s is defined in no migration" % fn
    return DEFINITIONS[fn][0]


def test_guards_read_the_last_definition_of_a_redefined_function():
    """The resolver must beat 001 for every function a later migration replaced.

    This is the structural half of the fix. Without it `body()` could quietly start
    returning a superseded copy again, and every rule guarded below would be checking
    code the database no longer runs, with nothing going red.
    """
    seen = {}
    for path in NUMBERED:
        with open(path, encoding="utf-8") as f:
            sql = f.read()
        for name in re.findall(
                r"create\s+(?:or\s+replace\s+)?function\s+([a-z_]+)\s*\(", sql, re.I):
            seen.setdefault(name, []).append(os.path.basename(path))

    redefined = {n: paths for n, paths in seen.items() if len(paths) > 1}
    assert "apply_auto_picks" in redefined, \
        "005 replaces apply_auto_picks; if that stopped being true, read 005 again"
    for name, paths in sorted(redefined.items()):
        assert source_of(name) == paths[-1], (
            "%s resolves to %s but %s defines it last"
            % (name, source_of(name), paths[-1]))


def test_there_is_at_least_one_migration():
    assert MIGRATIONS, "no migrations found"


@pytest.mark.parametrize("path", MIGRATIONS, ids=os.path.basename)
def test_migration_parses(path):
    with open(path, encoding="utf-8") as f:
        pglast.parse_sql(f.read())


@pytest.mark.parametrize("path", MIGRATIONS, ids=os.path.basename)
def test_every_plpgsql_body_parses(path):
    with open(path, encoding="utf-8") as f:
        sql = f.read()
    funcs = re.findall(r"(create or replace function .*?\$\$.*?\$\$\s*;)",
                       sql, re.S | re.I)
    plp = [f for f in funcs if re.search(r"language\s+plpgsql", f, re.I)]
    for fn in plp:
        name = re.search(r"function\s+(\w+)", fn, re.I).group(1)
        try:
            pglast.parse_plpgsql(fn)
        except Exception as e:                          # noqa: BLE001
            pytest.fail("%s failed to parse: %s" % (name, e))


# ------------------------------------------------------------------ security invariants

def test_rls_is_enabled_on_every_table(init_sql):
    tables = set(re.findall(r"create table if not exists (\w+)", init_sql, re.I))
    assert tables, "no tables found"
    for t in tables:
        assert re.search(r"alter table %s\s+enable row level security" % t,
                         init_sql, re.I), "RLS not enabled on %s" % t


def test_client_roles_have_no_direct_table_access(init_sql):
    """anon must reach the data only through SECURITY DEFINER functions."""
    assert re.search(r"revoke all on players.*?from anon, authenticated",
                     init_sql, re.I | re.S)
    # A bare table grant to anon would bypass every lock and visibility rule.
    bad = re.findall(r"grant\s+(?:select|insert|update|delete|all)\s+on\s+"
                     r"(?:table\s+)?(players|picks|games|weeks|sessions)\b",
                     init_sql, re.I)
    assert not bad, "direct table grant to a client role: %s" % bad


def test_no_temp_tables_inside_functions(init_sql):
    """A temp table created in a plpgsql function breaks plan caching on reuse."""
    assert "create temp table" not in init_sql.lower()


def test_pin_is_hashed_never_stored_raw(init_sql):
    assert "crypt(p_pin, gen_salt('bf'))" in init_sql
    # list_seats is the only public read of players and must not leak the hash. 009
    # redefines it, so this has to read the last copy rather than the one in 001.
    assert "pin_hash" not in body("list_seats")


def test_session_tokens_are_stored_hashed(init_sql):
    assert "encode(digest(tok, 'sha256'), 'hex')" in init_sql
    assert re.search(r"token_hash\s+text\s+primary key", init_sql, re.I)


def test_internal_helpers_are_not_callable_by_clients(init_sql):
    for fn in ("_player_for(text)", "_new_session(smallint)", "apply_auto_picks()"):
        assert re.search(r"revoke all on function %s\s+from public, anon, authenticated"
                         % re.escape(fn), init_sql, re.I), \
            "%s is exposed to clients" % fn


# ------------------------------------------------------------------ game rules

def test_kickoff_lock_is_enforced_in_sql():
    """The single rule that outranks everything: no writing a game that has started."""
    save = body("save_picks")
    assert "g.kickoff <= now()" in save, "no lock check in save_picks"
    assert "is locked and cannot be changed" in save
    assert "g.kickoff > now()" in save, "unlocked writes are not filtered by kickoff"


def test_board_hides_picks_until_kickoff():
    """009 redefined get_board and kept the gate. A guard pinned to 001 would not have
    noticed if it had dropped it, which is the whole reason this reads the last copy."""
    assert "g.kickoff <= now()" in body("get_board"), \
        "get_board would leak unplayed picks"


def test_auto_pick_takes_the_favourite():
    """Reversed on 2026-09-04: the favourite, not the underdog.

    This guard previously read 001 and asserted the underdog, which is what the rule was
    BEFORE Grant reversed it. It passed only because 001 still holds the superseded body,
    so it guarded dead code and taught the next reader the wrong rule. The decision is in
    memory/decisions.md; the live rule is in 005.
    """
    auto = body("apply_auto_picks")
    assert "favorite_abbr" in auto, "auto-pick must use the favourite"
    assert "underdog_abbr" not in auto, "auto-pick must never use the underdog"
    assert "home_abbr" in auto, "with no line there is no favourite: fall back to home"
    assert "min(c)" in auto, "auto-pick must use the lowest unused confidence"


def test_confidence_is_unique_per_player_per_week(init_sql):
    assert re.search(r"create unique index if not exists picks_one_value_per_week\s+"
                     r"on picks\(player_id, week_id, confidence\)", init_sql, re.I)


def test_slate_must_be_twenty_games():
    assert "<> 20" in body("publish_slate")


def test_only_admins_can_publish():
    assert "not me.is_admin" in body("publish_slate")


def test_seats_one_and_two_are_admins(init_sql):
    seed = re.search(r"insert into players \(id, is_admin, color\) values(.*?)on conflict",
                     init_sql, re.S | re.I).group(1)
    rows = re.findall(r"\((\d), (true|false),", seed)
    assert dict(rows) == {"1": "true", "2": "true", "3": "false", "4": "false"}


def test_a_claimed_seat_cannot_be_stolen():
    assert "where id = p_seat and name is null" in body("claim_seat")


# ------------------------------------------------- client / server drift

def _all_migration_sql():
    out = []
    for path in MIGRATIONS:
        with open(path, encoding="utf-8") as f:
            out.append(f.read())
    return "\n".join(out)


def test_every_rpc_the_client_calls_exists_in_sql():
    """The Setup screen once called get_pool, which existed only in the local mock.

    It worked in development and would have failed against the real database. This walks
    src/lib/api.js for every rpc('name') and asserts a matching SQL function is defined.
    """
    api_path = os.path.join(ROOT, "src", "lib", "api.js")
    if not os.path.exists(api_path):
        pytest.skip("frontend not present")
    with open(api_path, encoding="utf-8") as f:
        api = f.read()

    called = sorted(set(re.findall(r"rpc\(\s*'([a-z_]+)'", api)))
    assert called, "no rpc calls found in api.js"

    sql = _all_migration_sql()
    defined = set(re.findall(r"create or replace function\s+([a-z_]+)\s*\(", sql, re.I))

    missing = [fn for fn in called if fn not in defined]
    assert not missing, (
        "client calls RPCs with no SQL definition: %s (defined: %s)"
        % (missing, sorted(defined))
    )


def test_admin_only_rpcs_check_is_admin():
    """Hiding the Setup tab is cosmetic. These are the real gate."""
    for fn in ("publish_slate", "get_pool", "cron_health"):
        # get_pool is defined three times (002, 006, 007). Scanning the concatenation
        # found the 002 copy, so this used to check a version nobody calls.
        assert "is_admin" in body(fn), "%s does not check is_admin" % fn


def test_combined_migration_is_up_to_date():
    """migrations/ALL.sql is what Grant actually pastes. It must never drift."""
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import build_combined_migration as combiner

    path = os.path.join(ROOT, "migrations", "ALL.sql")
    assert os.path.exists(path), "run python scripts/build_combined_migration.py"
    with open(path, encoding="utf-8") as f:
        on_disk = f.read()
    assert on_disk == combiner.build(), (
        "migrations/ALL.sql is stale. Regenerate it with "
        "python scripts/build_combined_migration.py"
    )


def test_combined_migration_parses_as_one_script():
    path = os.path.join(ROOT, "migrations", "ALL.sql")
    with open(path, encoding="utf-8") as f:
        pglast.parse_sql(f.read())


def test_security_definer_functions_can_reach_pgcrypto():
    """Supabase puts pgcrypto in `extensions`, not `public`.

    Pinning search_path to `public` alone made the whole migration fail on the very
    first function with "function digest(text, unknown) does not exist".
    """
    sql = _all_migration_sql()
    bare = re.findall(r"set search_path = public(?!\s*,)", sql)
    assert not bare, (
        "%d function(s) pin search_path to public alone; pgcrypto lives in "
        "extensions on Supabase" % len(bare)
    )
    defined = re.findall(r"security definer set search_path = ([a-z, ]+?) as", sql)
    assert defined, "no SECURITY DEFINER functions found"
    for path in defined:
        assert "extensions" in path, "search_path '%s' cannot reach pgcrypto" % path


def test_search_path_is_always_pinned():
    """An unpinned SECURITY DEFINER function is a privilege-escalation footgun."""
    sql = _all_migration_sql()
    for match in re.finditer(r"create or replace function\s+(\w+)(.{0,400}?)\$\$",
                             sql, re.S | re.I):
        name, head = match.group(1), match.group(2)
        if "security definer" in head.lower():
            assert "set search_path" in head.lower(), \
                "%s is SECURITY DEFINER with no pinned search_path" % name


def test_no_read_only_function_writes():
    """A STABLE or IMMUTABLE function that writes is accepted at creation and then
    fails at call time with "UPDATE is not allowed in a non-volatile function".

    whoami shipped this way and broke sign-in on the live database: the seat was
    claimed, whoami failed, and no session could start. Pattern tests cannot catch a
    semantic error like this, so this one checks volatility against the body.
    """
    sql = _all_migration_sql()
    offenders = []
    for m in re.finditer(r"create or replace function\s+(\w+)(.*?)\$\$(.*?)\$\$",
                         sql, re.S | re.I):
        name, head, body = m.group(1), m.group(2), m.group(3)
        read_only = re.search(r"\b(stable|immutable)\b", head, re.I)
        # No trailing \b: "update\s+\w\b" only matches a one-letter table name, so
        # "update sessions set" slipped straight through the first version of this test
        # and it passed while the bug was still live.
        writes = re.search(
            r"\b(?:insert\s+into|update\s+[a-z_.\"]+\s+set|delete\s+from)", body, re.I)
        if read_only and writes:
            offenders.append("%s is %s but writes: %r"
                             % (name, read_only.group(1).upper(), writes.group(0)))
    assert not offenders, "; ".join(offenders)
