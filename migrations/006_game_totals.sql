-- The over/under, and a stop to the line being erased at kickoff.
-- Paste into the Supabase SQL Editor after 005. Safe to re-run.
--
-- Two things, both about the same column family.
--
-- 1. Games gain over_under. ESPN has carried it all along in odds[0].overUnder and
--    fetch_slate has been parsing it since the first slate build; it simply had nowhere
--    to land. The Board now shows the line and the total on every game.
--
-- 2. ESPN DROPS the odds block once a game goes final. Checked on 2026-09-04: every
--    completed game from 3 Sep came back with details: null and overUnder: null, while
--    every game still in `pre` carried both. The scores job upserts whatever ESPN last
--    said, so a finished game had its stored line overwritten with null. COLO @ GT was
--    already sitting in the database with spread_line null and favorite_abbr null,
--    having gone in at GT -6.5 before kickoff.
--
--    The fix is in scripts/sync_supabase.py, which now leaves the odds columns alone
--    for any game that is no longer `pre`. Nothing here can enforce that, because the
--    service key writes with RLS bypassed, but the column comment records the rule.
--
-- Nothing backfills the games that already lost their line: ESPN no longer has it.
-- Week 1's Thursday game is the only one affected.

alter table games add column if not exists over_under numeric(4,1);

comment on column games.over_under is
  'Pre-kickoff total from ESPN. Frozen once the game leaves state=pre: ESPN stops '
  'publishing odds for a finished game, so a refresh after kickoff would null it.';
comment on column games.spread_line is
  'Pre-kickoff line from ESPN. Frozen once the game leaves state=pre, same reason as '
  'over_under.';

-- ------------------------------------------------------------------ get_slate

-- Dropped rather than replaced: the return type gains a column, and Postgres refuses
-- to change the shape of an existing function in place. The grants go with it.
drop function if exists get_slate(text, int);

create function get_slate(p_token text, p_week int)
returns table (
  game_id bigint, kickoff timestamptz, locked boolean,
  home_id text, home_abbr text, home_school text, home_score smallint,
  away_id text, away_abbr text, away_school text, away_score smallint,
  neutral_site boolean, tv text, spread_line numeric, favorite_abbr text,
  underdog_abbr text, over_under numeric, tier text, state text, status_detail text,
  winner_abbr text, my_pick text, my_confidence smallint, my_auto boolean
) language plpgsql stable security definer set search_path = public, extensions as $$
declare me players;
begin
  me := _player_for(p_token);
  if me.id is null then raise exception 'Not signed in'; end if;
  return query
    select g.id, g.kickoff, (g.kickoff <= now()),
           g.home_id, g.home_abbr, g.home_school, g.home_score,
           g.away_id, g.away_abbr, g.away_school, g.away_score,
           g.neutral_site, g.tv, g.spread_line, g.favorite_abbr,
           g.underdog_abbr, g.over_under, g.tier, g.state, g.status_detail, g.winner_abbr,
           pk.pick_abbr, pk.confidence, pk.auto
      from games g
      join weeks w on w.id = g.week_id and w.published
      left join picks pk on pk.game_id = g.id and pk.player_id = me.id
     where g.week_id = p_week and g.in_slate
     order by g.kickoff, g.id;
end $$;

revoke all on function get_slate(text, int) from public;
grant execute on function get_slate(text, int) to anon, authenticated;

-- ------------------------------------------------------------------- get_pool

-- The Setup screen shows the same line and total while Dad is choosing the twenty.
drop function if exists get_pool(text, int);

create function get_pool(p_token text, p_week int)
returns table (
  game_id bigint, kickoff timestamptz, locked boolean, in_slate boolean,
  home_id text, home_abbr text, home_school text,
  away_id text, away_abbr text, away_school text,
  neutral_site boolean, tv text, spread_line numeric,
  favorite_abbr text, underdog_abbr text, over_under numeric, tier text,
  interest numeric, featured boolean
) language plpgsql stable security definer set search_path = public, extensions as $$
declare me players;
begin
  me := _player_for(p_token);
  if me.id is null or not me.is_admin then
    raise exception 'Only an admin can see the pool';
  end if;
  return query
    select g.id, g.kickoff, (g.kickoff <= now()), g.in_slate,
           g.home_id, g.home_abbr, g.home_school,
           g.away_id, g.away_abbr, g.away_school,
           g.neutral_site, g.tv, g.spread_line,
           g.favorite_abbr, g.underdog_abbr, g.over_under, g.tier,
           g.interest, g.featured
      from games g
     where g.week_id = p_week
     order by g.kickoff, g.id;
end $$;

revoke all on function get_pool(text, int) from public;
grant execute on function get_pool(text, int) to anon, authenticated;
