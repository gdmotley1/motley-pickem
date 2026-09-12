-- The record book needs the picks themselves, and nothing returns them for a whole season.
--
-- Paste into the Supabase SQL Editor. Safe to re-run. Read-only.
--
-- get_season aggregates: one row per player per week, points and correct and games. That
-- is everything a leaderboard needs and nothing a record book does. "Twenty points on a
-- loser", "the only one who called it", "the team that has cost you the most" and every
-- other record worth printing are properties of a single PICK on a single GAME, and an
-- aggregate has already thrown that away. No amount of client arithmetic gets it back.
--
-- WHY THIS RETURNS ROWS AND NOT ANSWERS
--
-- The obvious shape is a get_records() that computes each record in SQL and returns a
-- tidy list. It is the wrong shape here for one practical reason: every new record would
-- then be a migration, and a migration in this project is Grant pasting SQL into a web
-- console by hand. Records are the part of this app most likely to be added to on a whim
-- in November. Returning the rows means a new record is a JavaScript change that ships
-- with the next deploy, and it means seasonRecords() can be tested offline against a
-- fixture the way weekRecap and seasonStats already are.
--
-- The cost is the payload, and it is small: four players times twenty games times fifteen
-- regular season weeks is 1,200 rows at full season, and the columns are abbreviations
-- and smallints. Week 1 of 2026 is 80 rows.
--
-- VISIBILITY, WHICH IS THE PART THAT MATTERS
--
-- This function returns pick_abbr and confidence, which is exactly what the one rule that
-- outranks everything says you may not see for a game that has not started. It is safe
-- because of the join, not because of the caller:
--
--     g.winner_abbr is not null
--
-- A game has a winner only once it has finished, and a game cannot finish before it
-- kicks off. So every row this returns is a pick on a game whose kickoff is in the past,
-- which is the same set get_board already exposes and narrower than it: get_board reveals
-- at kickoff, this waits for the final. There is no parameter that widens it and no way
-- to ask for a game in progress. Removing that one predicate would leak every unplayed
-- pick in the season, so it is asserted in tests/test_migration.py.
--
-- in_slate keeps the alternates out, and weeks.published keeps out a week Dad has built
-- but not released.

create or replace function get_season_picks(p_token text)
returns table (
  week_no       smallint,
  week_label    text,
  game_id       bigint,
  kickoff       timestamptz,
  home_abbr     text,
  away_abbr     text,
  home_id       text,
  away_id       text,
  home_score    smallint,
  away_score    smallint,
  winner_abbr   text,
  favorite_abbr text,
  underdog_abbr text,
  spread_line   numeric,
  player_id     smallint,
  pick_abbr     text,
  confidence    smallint,
  auto          boolean
) language plpgsql stable security definer set search_path = public, extensions as $$
declare me players;
begin
  me := _player_for(p_token);
  if me.id is null then raise exception 'Not signed in'; end if;
  return query
    select w.week_no, w.label,
           g.id, g.kickoff,
           g.home_abbr, g.away_abbr, g.home_id, g.away_id,
           g.home_score, g.away_score,
           g.winner_abbr, g.favorite_abbr, g.underdog_abbr, g.spread_line,
           pk.player_id, pk.pick_abbr, pk.confidence, pk.auto
      from picks pk
      join games g  on g.id = pk.game_id
                   and g.in_slate
                   -- The whole safety property. See the note above before touching it.
                   and g.winner_abbr is not null
      join weeks w  on w.id = pk.week_id and w.published
      join players p on p.id = pk.player_id and p.name is not null
     order by w.week_no, g.kickoff, g.id, pk.player_id;
end $$;

revoke all on function get_season_picks(text) from public;
grant execute on function get_season_picks(text) to anon, authenticated;
