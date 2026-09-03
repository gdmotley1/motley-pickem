"""Pre-flight checks on the SQL migrations.

The migrations are applied by hand in the Supabase SQL Editor, so a syntax error costs a
round trip through Grant. These parse the files with libpg_query, the actual PostgreSQL
parser, and assert the security properties that must not regress.
"""
from __future__ import annotations

import glob
import os
import re

import pytest

pglast = pytest.importorskip("pglast", reason="pip install pglast")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIGRATIONS = sorted(glob.glob(os.path.join(ROOT, "migrations", "*.sql")))


@pytest.fixture(scope="module")
def init_sql():
    path = os.path.join(ROOT, "migrations", "001_init.sql")
    with open(path, encoding="utf-8") as f:
        return f.read()


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
    # list_seats is the only public read of players and must not leak the hash.
    seats = re.search(r"create or replace function list_seats\(\).*?\$\$(.*?)\$\$",
                      init_sql, re.S | re.I).group(1)
    assert "pin_hash" not in seats


def test_session_tokens_are_stored_hashed(init_sql):
    assert "encode(digest(tok, 'sha256'), 'hex')" in init_sql
    assert re.search(r"token_hash\s+text\s+primary key", init_sql, re.I)


def test_internal_helpers_are_not_callable_by_clients(init_sql):
    for fn in ("_player_for(text)", "_new_session(smallint)", "apply_auto_picks()"):
        assert re.search(r"revoke all on function %s\s+from public, anon, authenticated"
                         % re.escape(fn), init_sql, re.I), \
            "%s is exposed to clients" % fn


# ------------------------------------------------------------------ game rules

def test_kickoff_lock_is_enforced_in_sql(init_sql):
    """The single rule that outranks everything: no writing a game that has started."""
    save = re.search(r"create or replace function save_picks.*?\$\$(.*?)\$\$",
                     init_sql, re.S | re.I).group(1)
    assert "g.kickoff <= now()" in save, "no lock check in save_picks"
    assert "is locked and cannot be changed" in save
    assert "g.kickoff > now()" in save, "unlocked writes are not filtered by kickoff"


def test_board_hides_picks_until_kickoff(init_sql):
    board = re.search(r"create or replace function get_board.*?\$\$(.*?)\$\$",
                      init_sql, re.S | re.I).group(1)
    assert "g.kickoff <= now()" in board, "get_board would leak unplayed picks"


def test_auto_pick_takes_the_underdog(init_sql):
    """Grant explicitly overrode 'favorite'. Guard it."""
    auto = re.search(r"create or replace function apply_auto_picks.*?\$\$(.*?)\$\$",
                     init_sql, re.S | re.I).group(1)
    assert "underdog_abbr" in auto, "auto-pick must use the underdog"
    assert "favorite_abbr" not in auto, "auto-pick must never use the favorite"
    assert "min(c)" in auto, "auto-pick must use the lowest unused confidence"


def test_confidence_is_unique_per_player_per_week(init_sql):
    assert re.search(r"create unique index if not exists picks_one_value_per_week\s+"
                     r"on picks\(player_id, week_id, confidence\)", init_sql, re.I)


def test_slate_must_be_twenty_games(init_sql):
    pub = re.search(r"create or replace function publish_slate.*?\$\$(.*?)\$\$",
                    init_sql, re.S | re.I).group(1)
    assert "<> 20" in pub


def test_only_admins_can_publish(init_sql):
    pub = re.search(r"create or replace function publish_slate.*?\$\$(.*?)\$\$",
                    init_sql, re.S | re.I).group(1)
    assert "not me.is_admin" in pub


def test_seats_one_and_two_are_admins(init_sql):
    seed = re.search(r"insert into players \(id, is_admin, color\) values(.*?)on conflict",
                     init_sql, re.S | re.I).group(1)
    rows = re.findall(r"\((\d), (true|false),", seed)
    assert dict(rows) == {"1": "true", "2": "true", "3": "false", "4": "false"}


def test_a_claimed_seat_cannot_be_stolen(init_sql):
    claim = re.search(r"create or replace function claim_seat.*?\$\$(.*?)\$\$",
                      init_sql, re.S | re.I).group(1)
    assert "where id = p_seat and name is null" in claim


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
    sql = _all_migration_sql()
    for fn in ("publish_slate", "get_pool"):
        body = re.search(
            r"create or replace function %s.*?\$\$(.*?)\$\$" % fn, sql, re.S | re.I
        )
        assert body, "%s is not defined" % fn
        assert "is_admin" in body.group(1), "%s does not check is_admin" % fn
