-- Conferences on the pool, so the Setup screen can filter ninety games down to a few.
-- Paste into the Supabase SQL Editor after 006. Safe to re-run.
--
-- The pool is no longer the top forty by interest. scripts/suggest_slate.py now writes
-- every FBS game in the window, about ninety of them, including the ones with no posted
-- line. That was the only way Dad could reach a game the family cares about: the
-- 2026-09-05 week has 91 games, so fifty of them never reached his screen. West Georgia
-- at Kennesaw State, the game Grant named, ranked 39th of 70 alternates by interest with
-- a line posted at 22.5, so the cap alone put it out of reach.
--
-- Ninety rows is a long scroll on a phone, so the screen gained a search box and a
-- conference filter. games.home_conf and games.away_conf have existed since 001 and are
-- already populated by the sync job; get_pool simply never returned them.
--
-- Nothing here changes what a player can see. get_pool is still admin-only and still
-- refuses a non-admin token.

-- Dropped rather than replaced: the return type gains two columns, and Postgres refuses
-- to change the shape of an existing function in place. The grants go with it.
drop function if exists get_pool(text, int);

create function get_pool(p_token text, p_week int)
returns table (
  game_id bigint, kickoff timestamptz, locked boolean, in_slate boolean,
  home_id text, home_abbr text, home_school text, home_conf int,
  away_id text, away_abbr text, away_school text, away_conf int,
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
           g.home_id, g.home_abbr, g.home_school, g.home_conf,
           g.away_id, g.away_abbr, g.away_school, g.away_conf,
           g.neutral_site, g.tv, g.spread_line,
           g.favorite_abbr, g.underdog_abbr, g.over_under, g.tier,
           g.interest, g.featured
      from games g
     where g.week_id = p_week
     order by g.kickoff, g.id;
end $$;

revoke all on function get_pool(text, int) from public;
grant execute on function get_pool(text, int) to anon, authenticated;

-- The pool is fetched whole and filtered in the browser, so the only index that matters
-- is the one get_pool already uses to order the week.
create index if not exists games_week_kickoff_idx on games (week_id, kickoff);
