-- The notification wording Grant chose. Paste into the SQL Editor. Safe to re-run.
--
-- Picked on 2026-09-11 from the board that rendered all seven messages as real iOS
-- banners. His calls, by the numbering on that board: 1B, 2A, 3B, 4B, 5A.
--
--   1 heads-up   was  "Your picks are due"      / "20 games left, first one locks Fri 8:00 pm"
--               now  "20 games still open"     / "First one locks at 8:00 pm"
--   2 last call  unchanged
--   3 week live  was  "Week is live"            / "Week 2 is up. 20 games to pick."
--               now  "Week 2 is up"            / "The slate is posted. 20 games to pick."
--   4 results    was  "Week is in the books"    / "Week 2 is final. See where you landed."
--               now  "Week 2 is final"         / "See how everyone finished"
--   5 passed     unchanged
--
-- The pattern in 3 and 4 is worth naming, because it is the whole reason he changed them:
-- the week's own label moves UP into the title. "Week 2 is up" says more in the line iOS
-- renders in bold than "Week is live" does, and the body no longer has to repeat it.
--
-- The two buckets of notification 1 now have different shapes rather than one sentence
-- with a branch inside it, so they are written as two separate expressions.

create or replace function push_due()
returns table (player_id smallint, kind text, dedupe_key text,
               title text, body text, url text)
language plpgsql stable security definer set search_path = public, extensions as $$
begin
  return query

  -- 1 and 2. Pick reminders. The soonest game you can still pick, per player.
  with subscribed as (
    select p.* from players p
     where p.name is not null
       and exists (select 1 from push_subscriptions s where s.player_id = p.id)
  ),
  open_games as (
    select pl.id as player_id, w.id as week_id, g.id as game_id, g.kickoff,
           row_number() over (partition by pl.id order by g.kickoff)  as rn,
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
                then 'last' else 'heads' end as bucket,
           -- "1 game" reads as broken when it happens, and it will: the last unpicked
           -- game of a week is the commonest reminder there is.
           case when o.open_count = 1 then '' else 's' end as plural
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
               else n.open_count::text || ' game' || n.plural || ' still open'
          end)::text,
         (case when n.bucket = 'last'
               then n.open_count::text || ' game' || n.plural
                      || ' left, first one locks in '
                      || greatest(1, extract(epoch from n.kickoff - now())
                                     / 60)::int::text || ' minutes'
               -- Three hours out is always the same day, so the time alone is enough
               -- and naming the day would only make the line longer.
               else 'First one locks at '
                      || to_char(n.kickoff at time zone 'America/New_York', 'FMHH:MI am')
          end)::text,
         '/motley-pickem/?tab=picks'::text
    from next_open n
    left join today_count t on t.player_id = n.player_id
   where n.kickoff - now() <= _push_heads_up_window()
     and coalesce(t.n, 0) < _push_daily_cap()
     and not exists (select 1 from push_log l
                      where l.player_id = n.player_id and l.kind = 'pick_reminder'
                        and l.dedupe_key = n.game_id::text || ':' || n.bucket)

  union all

  -- 3. The week goes live. The label is in the title now, not the body.
  select pl.id, 'week_live'::text, w.id::text,
         (w.label || ' is up')::text,
         ('The slate is posted. ' || (select count(*) from games g
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

  -- 4. Results, once the last game of a week has graded. Same move: label into the title.
  select pl.id, 'week_results'::text, w.id::text,
         (w.label || ' is final')::text,
         'See how everyone finished'::text,
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

  -- 5. Someone passed you. Unchanged.
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
