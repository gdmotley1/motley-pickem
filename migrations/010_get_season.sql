-- The season tab needs the year broken down by week, and nothing returns that yet.
--
-- Paste into the Supabase SQL Editor. Safe to re-run. Read-only.
--
-- get_standings gives one cumulative row per player, which is enough for a leaderboard
-- and nothing else. Weeks won, form across the season, best and worst week, and season
-- ranking efficiency all need the same numbers cut per week, and none of them can be
-- recovered from a total after the fact.
--
-- Ranking efficiency is the reason this cannot be a client-side rollup of get_standings.
-- The ceiling for a week is the sum of the top `correct` confidence values in that week,
-- so a player who went 16-of-20 could at best have scored 200. That figure is a function
-- of one week's shape and does not survive being added up: a season ceiling is the sum
-- of the weekly ceilings, never a formula applied to season totals. So the split has to
-- happen in the query.
--
-- Only graded games count. A week in progress contributes whatever has finished, which
-- is what makes the form chart move on a Saturday rather than on Monday.
--
-- Visibility: this exposes points and records per player per week, all of which are
-- already public through get_standings. It deliberately does NOT expose pick_abbr or
-- confidence, so it cannot leak an unplayed pick the way a naive join over picks would.
-- The one rule that outranks everything is enforced in get_board, and this function
-- stays well clear of it by never returning a pick at all.

create or replace function get_season(p_token text)
returns table (
  player_id smallint, player_name text, player_color text, player_team text,
  week_no smallint, week_label text, points bigint, correct bigint, games bigint
) language plpgsql stable security definer set search_path = public, extensions as $$
declare me players;
begin
  me := _player_for(p_token);
  if me.id is null then raise exception 'Not signed in'; end if;
  return query
    select pl.id, pl.name, pl.color, pl.team_id,
           w.week_no, w.label,
           coalesce(sum(case when pk.pick_abbr = g.winner_abbr
                             then pk.confidence else 0 end), 0)::bigint,
           count(*) filter (where pk.pick_abbr = g.winner_abbr)::bigint,
           count(*)::bigint
      from players pl
      join picks pk  on pk.player_id = pl.id
      join games g   on g.id = pk.game_id and g.in_slate
                    and g.winner_abbr is not null
      join weeks w   on w.id = pk.week_id and w.published
     where pl.name is not null
     group by pl.id, pl.name, pl.color, pl.team_id, w.week_no, w.label
     order by w.week_no, 7 desc, 8 desc;
end $$;

revoke all on function get_season(text) from public;
grant execute on function get_season(text) to anon, authenticated;
