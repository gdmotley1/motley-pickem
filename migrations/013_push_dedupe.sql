-- push_due() never actually read the dedupe ledger. Paste into the SQL Editor.
--
-- Found live on 2026-09-11, minutes after the first real notification went out: running
-- the sender twice in a row sent "Week 2 is up" twice. 012's own comment claimed "the
-- dedupe ledger stops a repeat, and a recency clause stops a backlog", and only the
-- second half was ever written. The ledger was populated correctly by push_sent() and
-- then read by nobody.
--
-- What it would have cost. The scheduler is meant to run every five minutes:
--   - week_live, week_results and passed had NO limit whatsoever, so each would repeat
--     every run for as long as its recency window held. "Week 2 is up" is a 12 hour
--     window, which is about 144 notifications per phone.
--   - pick_reminder was accidentally survivable: the daily cap counts push_log rows in
--     the last 24 hours, so it would have stopped at 2 a day. Right for the wrong reason,
--     and the cap was never meant to be the thing preventing duplicates.
--
-- The fix is one `not exists` per branch, against (player_id, kind, dedupe_key), which is
-- exactly the primary key of push_log. The keys themselves were always correct, which is
-- why nothing else here has to change.

-- The bucket now has to be named before the select list rather than computed inside it,
-- because the dedupe key is built from it and the WHERE clause needs to see it too.
create or replace function push_due()
returns table (player_id smallint, kind text, dedupe_key text,
               title text, body text, url text)
language plpgsql stable security definer set search_path = public, extensions as $$
begin
  return query

  -- 1. Pick reminders. The soonest game you can still pick, per player.
  with subscribed as (
    select p.* from players p
     where p.name is not null
       and exists (select 1 from push_subscriptions s where s.player_id = p.id)
  ),
  open_games as (
    select pl.id as player_id, w.id as week_id, g.id as game_id, g.kickoff,
           row_number() over (partition by pl.id order by g.kickoff)  as rn,
           -- Counted per week, so a week published early cannot inflate the number
           -- shown for the week that is actually about to start.
           count(*)    over (partition by pl.id, w.id)                as open_count
      from subscribed pl
      join weeks w on w.published
      join games g on g.week_id = w.id and g.in_slate and g.kickoff > now()
      left join picks pk on pk.game_id = g.id and pk.player_id = pl.id
     where pl.notify_picks and pk.player_id is null
  ),
  next_open as (
    select o.*,
           case when o.kickoff - now() <= _push_last_call_window()
                then 'last' else 'heads' end as bucket
      from open_games o where o.rn = 1
  ),
  today_count as (
    select l.player_id, count(*) as n from push_log l
     where l.kind = 'pick_reminder' and l.sent_at > now() - interval '24 hours'
     group by l.player_id
  )
  select n.player_id,
         'pick_reminder'::text,
         (n.game_id::text || ':' || n.bucket)::text,
         (case when n.bucket = 'last'
               then 'Last call for your picks'
               else 'Your picks are due' end)::text,
         (n.open_count::text || ' game' || (case when n.open_count = 1 then '' else 's' end)
            || ' left, first one locks ' ||
            (case when n.bucket = 'last'
                  then 'in ' || greatest(1, extract(epoch from n.kickoff - now())
                                            / 60)::int::text || ' minutes'
                  else to_char(n.kickoff at time zone 'America/New_York',
                               'FMDy FMHH:MI am')
             end))::text,
         '/motley-pickem/?tab=picks'::text
    from next_open n
    left join today_count t on t.player_id = n.player_id
   where n.kickoff - now() <= _push_heads_up_window()
     and coalesce(t.n, 0) < _push_daily_cap()
     and not exists (select 1 from push_log l
                      where l.player_id = n.player_id and l.kind = 'pick_reminder'
                        and l.dedupe_key = n.game_id::text || ':' || n.bucket)

  union all

  -- 2. The week is live. Once per week per player, on publish.
  select pl.id, 'week_live'::text, w.id::text,
         'Week is live'::text,
         (w.label || ' is up. ' || (select count(*) from games g
                                     where g.week_id = w.id and g.in_slate)::text
            || ' games to pick.')::text,
         '/motley-pickem/?tab=picks'::text
    from players pl
    join weeks w on w.published and w.published_at > now() - interval '12 hours'
   where pl.name is not null and pl.notify_live
     and exists (select 1 from push_subscriptions s where s.player_id = pl.id)
     and not exists (select 1 from push_log l
                      where l.player_id = pl.id and l.kind = 'week_live'
                        and l.dedupe_key = w.id::text)

  union all

  -- 3. Results, once the last game of a week has graded.
  select pl.id, 'week_results'::text, w.id::text,
         'Week is in the books'::text,
         (w.label || ' is final. See where you landed.')::text,
         '/motley-pickem/?tab=week'::text
    from players pl
    join weeks w on w.published
   where pl.name is not null and pl.notify_results
     and exists (select 1 from push_subscriptions s where s.player_id = pl.id)
     and not exists (select 1 from games g
                      where g.week_id = w.id and g.in_slate and g.winner_abbr is null)
     and (select max(g.kickoff) from games g where g.week_id = w.id and g.in_slate)
           > now() - interval '12 hours'
     and not exists (select 1 from push_log l
                      where l.player_id = pl.id and l.kind = 'week_results'
                        and l.dedupe_key = w.id::text)

  union all

  -- 4. Someone passed you: you fell below your best rank so far this week.
  select r.player_id, 'passed'::text,
         (r.week_id::text || ':' || r.rank::text)::text,
         'You got passed'::text,
         ('You are now ' || (case r.rank when 1 then '1st' when 2 then '2nd'
                                         when 3 then '3rd' else '4th' end)
            || ' this week.')::text,
         '/motley-pickem/?tab=board'::text
    from _push_live_ranks() r
    join players pl on pl.id = r.player_id
    join push_rank pr on pr.player_id = r.player_id and pr.week_id = r.week_id
   where pl.notify_passed and r.rank > pr.rank
     and exists (select 1 from push_subscriptions s where s.player_id = r.player_id)
     and not exists (select 1 from push_log l
                      where l.player_id = r.player_id and l.kind = 'passed'
                        and l.dedupe_key = r.week_id::text || ':' || r.rank::text);
end $$;

revoke all on function push_due() from public, anon, authenticated;
