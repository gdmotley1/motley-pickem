-- Missed picks fill with the FAVORITE, and they land at kickoff on their own.
-- Paste into the Supabase SQL Editor. Safe to re-run.
--
-- Two changes, both decided on 2026-09-04.
--
-- 1. The rule flips from underdog to favourite. The underdog was originally chosen so
--    that forgetting genuinely cost you something; Grant decided that is not the pool
--    he wants and that the favourite is fairer. The sting stays mild either way,
--    because a missed game is still assigned the LOWEST confidence value that player
--    has not spent, so it is worth almost nothing whichever side it lands on.
--
--    With no line posted there is no favourite, so it falls back to the home team.
--    That mirrors the old rule taking the road team when there was no underdog.
--
-- 2. It stops waiting on the GitHub sync job. That workflow asks for every 15 minutes
--    Thursday through Sunday and does not get it: on the Thursday of week 1 it ran at
--    22:42 UTC and then not again until 00:25. Nothing in this function needs ESPN,
--    since favorite_abbr and kickoff are already columns, so pg_cron runs it here
--    every five minutes. A missed pick now appears within five minutes of kickoff
--    whether or not anything outside Supabase is working.
--
-- Also fixes a latent halt. The loop used EXIT when a player had no confidence value
-- left, which abandoned every remaining row rather than that one player's row, so a
-- single odd case could silently stop auto-picks for everybody.

create or replace function apply_auto_picks()
returns int language plpgsql security definer set search_path = public, extensions as $$
declare r record; v_conf smallint; n int := 0;
begin
  for r in
    select g.id as game_id, g.week_id, pl.id as player_id,
           coalesce(g.favorite_abbr, g.home_abbr) as pick
      from games g
      join weeks w  on w.id = g.week_id and w.published
      cross join players pl
      left join picks pk on pk.game_id = g.id and pk.player_id = pl.id
     where g.in_slate and g.kickoff <= now()
       and pl.name is not null and pk.player_id is null
     order by g.kickoff
  loop
    select min(c) into v_conf
      from generate_series(1, 20) c
     where c not in (select confidence from picks
                      where player_id = r.player_id and week_id = r.week_id);
    -- CONTINUE, not EXIT: one player with nothing left must not stop everyone else.
    continue when v_conf is null;
    insert into picks (player_id, game_id, week_id, pick_abbr, confidence, auto)
      values (r.player_id, r.game_id, r.week_id, r.pick, v_conf, true)
    on conflict do nothing;
    n := n + 1;
  end loop;
  return n;
end $$;

-- ------------------------------------------------------------------ scheduling

create extension if not exists pg_cron;

-- Every five minutes, all year round. It is a handful of rows against an index, and
-- out of season there is never an unpicked published game for it to find, so it costs
-- nothing to leave running. Scheduling by name replaces the job rather than adding a
-- second one, which is what keeps this file safe to re-run.
select cron.schedule('autopick-at-kickoff', '*/5 * * * *', $job$select apply_auto_picks()$job$);
