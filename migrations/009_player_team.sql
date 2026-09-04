-- Profile pictures: every player picks a school, and their avatar becomes that school's
-- mark on a colour it shows up on.
--
-- Paste into the Supabase SQL Editor. Safe to re-run.
--
-- Grant chose the treatment from outputs/avatar-board.html on 2026-09-04. The art is
-- already vendored: static/logos holds 139 marks, including Georgia College & State,
-- which is his alma mater and is in none of ESPN's lists. static/data/teams.json carries
-- the id, the background colour and which cut of the mark to use, all decided at build
-- time by scripts/build_team_library.py.
--
-- There is deliberately NO teams table. The 139 rows would triple the size of this paste
-- to buy a foreign key whose only job is rejecting an id the client never sends, and a
-- bad id already degrades safely: TeamLogo falls back to the abbreviation chip rather
-- than showing a broken image. The format check below is the guard instead.
--
-- Every function that returns a player row has to be dropped first. Postgres refuses to
-- change the return type of an existing function through CREATE OR REPLACE, which
-- migration 006 hit first and solved the same way.

alter table players add column if not exists team_id text;

-- ------------------------------------------------------------------ setting your team

-- Your own team only: p_token identifies the caller and there is no player argument, so
-- there is no way to spell "set someone else's". Passing null clears it and puts the
-- initial back.
create or replace function set_my_team(p_token text, p_team_id text)
returns void language plpgsql security definer set search_path = public, extensions as $$
declare me players;
begin
  me := _player_for(p_token);
  if me.id is null then raise exception 'Not signed in'; end if;
  if p_team_id is not null and p_team_id !~ '^[A-Za-z0-9_-]{1,16}$' then
    raise exception 'That is not a team id';
  end if;
  update players set team_id = p_team_id where id = me.id;
end $$;

revoke all on function set_my_team(text, text) from public;
grant execute on function set_my_team(text, text) to anon, authenticated;

-- ------------------------------------------------- player rows now carry the team

drop function if exists list_seats();
create or replace function list_seats()
returns table (id smallint, name text, is_admin boolean, claimed boolean,
               color text, team_id text)
language sql stable security definer set search_path = public, extensions as $$
  select p.id, p.name, p.is_admin, (p.name is not null), p.color, p.team_id
  from players p order by p.id
$$;

revoke all on function list_seats() from public;
grant execute on function list_seats() to anon, authenticated;

drop function if exists whoami(text);
create or replace function whoami(p_token text)
returns table (id smallint, name text, is_admin boolean, color text, team_id text)
language plpgsql security definer set search_path = public, extensions as $$
declare me players;
begin
  me := _player_for(p_token);
  if me.id is null then raise exception 'Not signed in'; end if;
  -- Still VOLATILE on purpose. Migration 004: a STABLE function cannot run this UPDATE,
  -- and it failed at call time rather than at creation, so sign-in broke on the live
  -- database with the seat already claimed.
  update sessions set last_seen = now()
    where token_hash = encode(digest(p_token, 'sha256'), 'hex');
  return query select me.id, me.name, me.is_admin, me.color, me.team_id;
end $$;

revoke all on function whoami(text) from public;
grant execute on function whoami(text) to anon, authenticated;

drop function if exists get_board(text, int);
create or replace function get_board(p_token text, p_week int)
returns table (
  game_id bigint, player_id smallint, player_name text, player_color text,
  player_team text, pick_abbr text, confidence smallint, auto boolean,
  correct boolean, points smallint
) language plpgsql stable security definer set search_path = public, extensions as $$
declare me players;
begin
  me := _player_for(p_token);
  if me.id is null then raise exception 'Not signed in'; end if;
  return query
    select g.id, pl.id, pl.name, pl.color, pl.team_id,
           pk.pick_abbr, pk.confidence, pk.auto,
           case when g.winner_abbr is null then null
                else pk.pick_abbr = g.winner_abbr end,
           case when g.winner_abbr is null then null
                when pk.pick_abbr = g.winner_abbr then pk.confidence
                else 0::smallint end
      from picks pk
      join games g   on g.id = pk.game_id
      join players pl on pl.id = pk.player_id
     where pk.week_id = p_week
       and g.in_slate
       and g.kickoff <= now()          -- the visibility rule, enforced here and nowhere else
     order by g.kickoff, pl.id;
end $$;

revoke all on function get_board(text, int) from public;
grant execute on function get_board(text, int) to anon, authenticated;

drop function if exists get_standings(text);
create or replace function get_standings(p_token text)
returns table (
  player_id smallint, player_name text, player_color text, player_team text,
  weeks_played bigint, correct bigint, games bigint, points bigint
) language plpgsql stable security definer set search_path = public, extensions as $$
declare me players;
begin
  me := _player_for(p_token);
  if me.id is null then raise exception 'Not signed in'; end if;
  return query
    select pl.id, pl.name, pl.color, pl.team_id,
           count(distinct pk.week_id),
           count(*) filter (where pk.pick_abbr = g.winner_abbr),
           count(*) filter (where g.winner_abbr is not null),
           coalesce(sum(case when pk.pick_abbr = g.winner_abbr
                             then pk.confidence else 0 end), 0)
      from players pl
      left join picks pk on pk.player_id = pl.id
      left join games g  on g.id = pk.game_id and g.in_slate
     where pl.name is not null
     group by pl.id, pl.name, pl.color, pl.team_id
     order by 8 desc, 6 desc;
end $$;

revoke all on function get_standings(text) from public;
grant execute on function get_standings(text) to anon, authenticated;
