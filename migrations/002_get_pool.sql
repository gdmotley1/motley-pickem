-- The commissioner's slate builder.
-- Paste into the Supabase SQL Editor after 001_init.sql. Safe to re-run.
--
-- 001 shipped without this: the Setup screen called get_pool, which existed only in the
-- local mock, so the screen worked in development and would have failed against the real
-- database. tests/test_migration.py now asserts every RPC the client calls exists here.

-- Every candidate game for a week, whether or not it made the slate. Admin only: the
-- pool reveals which games are under consideration before the week is published.
create or replace function get_pool(p_token text, p_week int)
returns table (
  game_id bigint, kickoff timestamptz, locked boolean, in_slate boolean,
  home_id text, home_abbr text, home_school text,
  away_id text, away_abbr text, away_school text,
  neutral_site boolean, tv text, spread_line numeric,
  favorite_abbr text, underdog_abbr text, tier text,
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
           g.favorite_abbr, g.underdog_abbr, g.tier,
           g.interest, g.featured
      from games g
     where g.week_id = p_week
     order by g.kickoff, g.id;
end $$;

revoke all on function get_pool(text, int) from public;
grant execute on function get_pool(text, int) to anon, authenticated;
