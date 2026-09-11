-- Push notifications. Paste into the Supabase SQL Editor. Safe to re-run.
--
-- Why this exists: Week 1 went 80 for 80, and then Week 2 sat at 0 of 80 with the first
-- kickoff eleven hours out. The PickNudge shipped on 2026-09-10 for exactly that, but a
-- nudge lives inside the app nobody opened. This is the part that reaches a phone that
-- is in a pocket.
--
-- There is no App Store involved. Web Push is a browser standard: the phone hands us a
-- subscription, we encrypt a payload and POST it to the URL in that subscription, and
-- Apple's push service delivers it. On iOS it only works for a site added to the Home
-- Screen, which is how all four of them already run it (confirmed 2026-09-11).
--
-- This migration is the data layer only. It stores subscriptions, remembers what has
-- already been sent, and decides WHO is due for WHAT. It does not send anything: the
-- encryption lives in the sender, because Postgres has no business doing ECDH.

-- ---------------------------------------------------------------- subscriptions

-- One row per device, not per player. A phone and an iPad are two subscriptions for the
-- same person, and both should buzz. The endpoint is the natural key: the browser hands
-- back the same one for the same install, so re-subscribing updates rather than doubles.
create table if not exists push_subscriptions (
  id          bigserial   primary key,
  player_id   smallint    not null references players(id) on delete cascade,
  endpoint    text        not null unique,
  p256dh      text        not null,        -- the device's public key, base64url
  auth        text        not null,        -- the device's auth secret, base64url
  created_at  timestamptz not null default now(),
  last_sent   timestamptz,
  last_error  text,
  -- A dead endpoint returns 404 or 410 forever. The sender deletes on those outright;
  -- this counts the softer failures so a device that is merely broken can be spotted.
  failures    smallint    not null default 0
);
create index if not exists push_subs_player on push_subscriptions(player_id);

-- ---------------------------------------------------------------- preferences

-- Per player, not per device: turning results off on your phone should turn it off
-- everywhere. All four default on, because a player who went to the trouble of granting
-- notification permission has already said yes to the idea.
alter table players add column if not exists notify_picks   boolean not null default true;
alter table players add column if not exists notify_live    boolean not null default true;
alter table players add column if not exists notify_results boolean not null default true;
alter table players add column if not exists notify_passed  boolean not null default true;

-- ---------------------------------------------------------------- the dedupe ledger

-- The scheduler runs every five minutes and asks the same question every time. Without
-- this, "you have games to pick" would fire twelve times an hour. A row here means "this
-- player has already been told this exact thing", and the primary key is the guard.
create table if not exists push_log (
  player_id   smallint    not null references players(id) on delete cascade,
  kind        text        not null check (kind in
                ('pick_reminder', 'week_live', 'week_results', 'passed')),
  dedupe_key  text        not null,
  sent_at     timestamptz not null default now(),
  primary key (player_id, kind, dedupe_key)
);
create index if not exists push_log_sent on push_log(sent_at desc);

-- ---------------------------------------------------------------- rank snapshot

-- "Someone passed you" needs a before to compare against, and standings are computed on
-- the fly rather than stored. This holds each player's BEST rank so far this week, and
-- the notification fires when they fall below it. A high-water mark rather than a
-- previous value, because it is self-limiting: there are only three drops available in
-- a four-person pool, so nobody can be buzzed about this more than three times a week
-- however many times the lead changes hands.
create table if not exists push_rank (
  player_id  smallint    not null references players(id) on delete cascade,
  week_id    int         not null references weeks(id)   on delete cascade,
  rank       smallint    not null,
  updated_at timestamptz not null default now(),
  primary key (player_id, week_id)
);

-- ---------------------------------------------------------------- lock it all down

alter table push_subscriptions enable row level security;
alter table push_log           enable row level security;
alter table push_rank          enable row level security;

-- Same posture as every other table here: RLS on, no policies, so anon and authenticated
-- get nothing at all and every legitimate path is a SECURITY DEFINER function.
revoke all on push_subscriptions, push_log, push_rank from anon, authenticated;

-- ---------------------------------------------------------------- tuning

-- How far ahead the two pick reminders land. The heads-up is "you could still be doing
-- something else"; the last call is "you cannot". Both are measured against the soonest
-- game you can still pick, so they re-arm across the week: a Friday night game gets its
-- own pair, and Saturday morning's games get theirs.
create or replace function _push_heads_up_window() returns interval
  language sql immutable as $$ select interval '3 hours' $$;
create or replace function _push_last_call_window() returns interval
  language sql immutable as $$ select interval '45 minutes' $$;

-- Nobody gets buzzed about picks more than twice in a day, however many kickoffs the
-- day holds. Grant chose the cadence that follows the next kickoff; this is the ceiling
-- that keeps it from becoming a Saturday of buzzing.
create or replace function _push_daily_cap() returns int
  language sql immutable as $$ select 2 $$;

-- ---------------------------------------------------------------- player-facing RPCs

-- Store the subscription the browser handed back. Re-subscribing on the same device
-- overwrites, and a device that was someone else's (a shared iPad, a seat switch) moves
-- to the player who just signed in rather than notifying the wrong person.
create or replace function save_push_subscription(
  p_token text, p_endpoint text, p_p256dh text, p_auth text)
returns void language plpgsql security definer set search_path = public, extensions as $$
declare me players;
begin
  me := _player_for(p_token);
  if me.id is null then raise exception 'Not signed in'; end if;
  if p_endpoint is null or p_endpoint !~ '^https://' then
    raise exception 'That is not a push endpoint';
  end if;
  insert into push_subscriptions (player_id, endpoint, p256dh, auth)
       values (me.id, p_endpoint, p_p256dh, p_auth)
  on conflict (endpoint) do update
     set player_id  = excluded.player_id,
         p256dh     = excluded.p256dh,
         auth       = excluded.auth,
         failures   = 0,
         last_error = null;
end $$;

revoke all on function save_push_subscription(text, text, text, text) from public;
grant execute on function save_push_subscription(text, text, text, text)
  to anon, authenticated;

-- Turning reminders off on this device. Scoped to the caller so one player cannot
-- unsubscribe another.
create or replace function delete_push_subscription(p_token text, p_endpoint text)
returns void language plpgsql security definer set search_path = public, extensions as $$
declare me players;
begin
  me := _player_for(p_token);
  if me.id is null then raise exception 'Not signed in'; end if;
  delete from push_subscriptions
   where endpoint = p_endpoint and player_id = me.id;
end $$;

revoke all on function delete_push_subscription(text, text) from public;
grant execute on function delete_push_subscription(text, text) to anon, authenticated;

-- What the Reminders sheet renders. `subscribed` is about THIS device; the four flags
-- are about the player everywhere.
create or replace function my_push_state(p_token text, p_endpoint text)
returns table (subscribed boolean, notify_picks boolean, notify_live boolean,
               notify_results boolean, notify_passed boolean)
language plpgsql stable security definer set search_path = public, extensions as $$
declare me players;
begin
  me := _player_for(p_token);
  if me.id is null then raise exception 'Not signed in'; end if;
  return query
    select exists (select 1 from push_subscriptions s
                    where s.player_id = me.id and s.endpoint = p_endpoint),
           me.notify_picks, me.notify_live, me.notify_results, me.notify_passed;
end $$;

revoke all on function my_push_state(text, text) from public;
grant execute on function my_push_state(text, text) to anon, authenticated;

create or replace function set_notify_prefs(
  p_token text, p_picks boolean, p_live boolean, p_results boolean, p_passed boolean)
returns void language plpgsql security definer set search_path = public, extensions as $$
declare me players;
begin
  me := _player_for(p_token);
  if me.id is null then raise exception 'Not signed in'; end if;
  update players
     set notify_picks   = coalesce(p_picks,   notify_picks),
         notify_live    = coalesce(p_live,    notify_live),
         notify_results = coalesce(p_results, notify_results),
         notify_passed  = coalesce(p_passed,  notify_passed)
   where id = me.id;
end $$;

revoke all on function set_notify_prefs(text, boolean, boolean, boolean, boolean)
  from public;
grant execute on function set_notify_prefs(text, boolean, boolean, boolean, boolean)
  to anon, authenticated;

-- ---------------------------------------------------------------- the live weekly rank

-- Used by the "passed" branch and by the snapshot that feeds it. Empty unless a week has
-- at least one graded game AND at least one still to come: a finished week is what the
-- results notification is for, and nobody needs telling they were passed by the game
-- that ended the week.
create or replace function _push_live_ranks()
returns table (player_id smallint, week_id int, points bigint, rank smallint)
language sql stable security definer set search_path = public, extensions as $$
  with live_week as (
    select w.id from weeks w
     where w.published
       and exists (select 1 from games g
                    where g.week_id = w.id and g.in_slate and g.winner_abbr is not null)
       and exists (select 1 from games g
                    where g.week_id = w.id and g.in_slate and g.winner_abbr is null)
     order by w.week_no desc limit 1
  )
  select pl.id, lw.id,
         coalesce(sum(case when pk.pick_abbr = g.winner_abbr
                           then pk.confidence else 0 end), 0),
         rank() over (order by coalesce(sum(case when pk.pick_abbr = g.winner_abbr
                                                 then pk.confidence else 0 end), 0) desc
                     )::smallint
    from live_week lw
    cross join players pl
    left join picks pk on pk.player_id = pl.id and pk.week_id = lw.id
    left join games g  on g.id = pk.game_id and g.in_slate
   where pl.name is not null
   group by pl.id, lw.id
$$;

-- ---------------------------------------------------------------- who is due, and why

-- Everything the sender needs, one row per (player, kind) that is ready to go out. The
-- sender fans each row across that player's devices, so this does not join
-- subscriptions: it only requires that at least one exists.
--
-- Every branch is guarded twice. The dedupe ledger stops a repeat, and a recency clause
-- stops a backlog: without it the very first run would announce every week ever
-- published and every result ever graded, all at once, to four phones.
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
    select * from open_games where rn = 1
  ),
  today_count as (
    select l.player_id, count(*) as n from push_log l
     where l.kind = 'pick_reminder' and l.sent_at > now() - interval '24 hours'
     group by l.player_id
  )
  select n.player_id,
         'pick_reminder'::text,
         n.game_id::text || ':' ||
           (case when n.kickoff - now() <= _push_last_call_window()
                 then 'last' else 'heads' end),
         (case when n.kickoff - now() <= _push_last_call_window()
               then 'Last call for your picks'
               else 'Your picks are due' end)::text,
         (n.open_count::text || ' game' || (case when n.open_count = 1 then '' else 's' end)
            || ' left, first one locks ' ||
            (case when n.kickoff - now() <= _push_last_call_window()
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

  union all

  -- 2. The week is live. Fires once per week per player, on publish. The 12 hour clause
  -- is the backlog guard: on the first run after this ships, only a week published
  -- today can qualify, not all fifteen.
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

  union all

  -- 3. Results, once the last game of a week has graded. Same backlog guard, measured
  -- off the last kickoff rather than a publish time.
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

  union all

  -- 4. Someone passed you: you fell below your best rank so far this week. The dedupe
  -- key carries the rank, so each position is announced at most once.
  select r.player_id, 'passed'::text,
         r.week_id::text || ':' || r.rank::text,
         'You got passed'::text,
         ('You are now ' || (case r.rank when 1 then '1st' when 2 then '2nd'
                                         when 3 then '3rd' else '4th' end)
            || ' this week.')::text,
         '/motley-pickem/?tab=board'::text
    from _push_live_ranks() r
    join players pl on pl.id = r.player_id
    join push_rank pr on pr.player_id = r.player_id and pr.week_id = r.week_id
   where pl.notify_passed and r.rank > pr.rank
     and exists (select 1 from push_subscriptions s where s.player_id = r.player_id);
end $$;

-- ---------------------------------------------------------------- sender bookkeeping

-- Called after a successful send. Writing the ledger row is what stops the next run
-- five minutes later from saying the same thing again, so the sender must call this
-- even when only some of a player's devices accepted the message.
create or replace function push_sent(p_player smallint, p_kind text, p_key text)
returns void language plpgsql security definer set search_path = public, extensions as $$
begin
  insert into push_log (player_id, kind, dedupe_key) values (p_player, p_kind, p_key)
  on conflict do nothing;
  update push_subscriptions set last_sent = now(), failures = 0, last_error = null
   where player_id = p_player;
  -- Telling someone they are 3rd makes 3rd the new high-water mark, or the next drop
  -- would be measured against a position they no longer hold.
  if p_kind = 'passed' then
    update push_rank pr set rank = split_part(p_key, ':', 2)::smallint, updated_at = now()
     where pr.player_id = p_player and pr.week_id = split_part(p_key, ':', 1)::int;
  end if;
end $$;

-- Called for an endpoint the push service rejected. 404 and 410 mean the subscription is
-- gone for good, which on iOS is what deleting and re-adding the Home Screen icon does,
-- so it is ordinary rather than exceptional. Anything else is recorded and retried.
create or replace function push_failed(p_endpoint text, p_code int, p_error text)
returns void language plpgsql security definer set search_path = public, extensions as $$
begin
  if p_code in (404, 410) then
    delete from push_subscriptions where endpoint = p_endpoint;
  else
    update push_subscriptions
       set failures = least(failures + 1, 32767), last_error = p_error
     where endpoint = p_endpoint;
  end if;
end $$;

-- Keeps the high-water mark current, and seeds it the first time a week goes live so the
-- first drop compares against a real position rather than against nothing. `least` is
-- what makes it a high-water mark: a better rank lowers it, a worse one never raises it.
-- Run by the sender on every pass, before push_due().
create or replace function push_refresh_ranks()
returns void language plpgsql security definer set search_path = public, extensions as $$
begin
  insert into push_rank (player_id, week_id, rank)
    select r.player_id, r.week_id, r.rank from _push_live_ranks() r
  on conflict (player_id, week_id) do update
     set rank = least(push_rank.rank, excluded.rank), updated_at = now();
end $$;

-- None of these are for clients. The sender authenticates with the service key, which
-- bypasses RLS and these grants alike; revoking keeps them off the public API surface.
revoke all on function push_due()                        from public, anon, authenticated;
revoke all on function _push_live_ranks()                from public, anon, authenticated;
revoke all on function push_sent(smallint, text, text)   from public, anon, authenticated;
revoke all on function push_failed(text, int, text)      from public, anon, authenticated;
revoke all on function push_refresh_ranks()              from public, anon, authenticated;
